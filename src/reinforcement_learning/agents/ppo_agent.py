# -*- coding: utf-8 -*-
"""
PPO代理實現

此模組實現了Proximal Policy Optimization (PPO)算法，
基於原始項目的PPO實現進行增強和優化。

主要功能：
- PPO算法實現
- 策略和價值網絡
- 經驗緩衝區管理
- 訓練和推理
- 模型保存和加載

技術特色：
- 基於Stable-Baselines3的穩定實現
- 支援連續和離散動作空間
- 自適應學習率調整
- 完善的日誌記錄
"""

import logging
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from torch.distributions import Normal, Categorical
from typing import Dict, List, Any, Optional, Tuple
import gym
from collections import deque
import pickle

from ..core.base_agent import BaseRLAgent, AgentConfig, TrainingStats

# 設定日誌
logger = logging.getLogger(__name__)


class PolicyNetwork(nn.Module):
    """策略網絡"""
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256, is_continuous: bool = True):
        """
        初始化策略網絡
        
        Args:
            state_dim: 狀態維度
            action_dim: 動作維度
            hidden_dim: 隱藏層維度
            is_continuous: 是否為連續動作空間
        """
        super(PolicyNetwork, self).__init__()
        
        self.is_continuous = is_continuous
        
        # 共享特徵提取層
        self.feature_layers = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        
        if is_continuous:
            # 連續動作空間：輸出均值和標準差
            self.mean_layer = nn.Linear(hidden_dim, action_dim)
            self.log_std_layer = nn.Linear(hidden_dim, action_dim)
        else:
            # 離散動作空間：輸出動作概率
            self.action_layer = nn.Linear(hidden_dim, action_dim)
    
    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        前向傳播
        
        Args:
            state: 狀態張量
            
        Returns:
            動作分布參數
        """
        features = self.feature_layers(state)
        
        if self.is_continuous:
            mean = self.mean_layer(features)
            log_std = self.log_std_layer(features)
            log_std = torch.clamp(log_std, -20, 2)  # 限制標準差範圍
            return mean, log_std
        else:
            action_logits = self.action_layer(features)
            return action_logits, None
    
    def get_action_and_log_prob(self, state: torch.Tensor, deterministic: bool = False):
        """
        獲取動作和對數概率
        
        Args:
            state: 狀態張量
            deterministic: 是否確定性選擇
            
        Returns:
            (動作, 對數概率)
        """
        if self.is_continuous:
            mean, log_std = self.forward(state)
            std = torch.exp(log_std)
            
            if deterministic:
                action = mean
                log_prob = None
            else:
                dist = Normal(mean, std)
                action = dist.sample()
                log_prob = dist.log_prob(action).sum(dim=-1)
            
            # 將動作限制在[-1, 1]範圍內
            action = torch.tanh(action)
            
            return action, log_prob
        else:
            action_logits, _ = self.forward(state)
            
            if deterministic:
                action = torch.argmax(action_logits, dim=-1)
                log_prob = None
            else:
                dist = Categorical(logits=action_logits)
                action = dist.sample()
                log_prob = dist.log_prob(action)
            
            return action, log_prob


class ValueNetwork(nn.Module):
    """價值網絡"""
    
    def __init__(self, state_dim: int, hidden_dim: int = 256):
        """
        初始化價值網絡
        
        Args:
            state_dim: 狀態維度
            hidden_dim: 隱藏層維度
        """
        super(ValueNetwork, self).__init__()
        
        self.network = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
    
    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """
        前向傳播
        
        Args:
            state: 狀態張量
            
        Returns:
            狀態價值
        """
        return self.network(state)


class PPOBuffer:
    """PPO經驗緩衝區"""
    
    def __init__(self, capacity: int, state_dim: int, action_dim: int, device: torch.device):
        """
        初始化緩衝區
        
        Args:
            capacity: 緩衝區容量
            state_dim: 狀態維度
            action_dim: 動作維度
            device: 計算設備
        """
        self.capacity = capacity
        self.device = device
        self.ptr = 0
        self.size = 0
        
        # 緩衝區數據
        self.states = torch.zeros((capacity, state_dim), dtype=torch.float32, device=device)
        self.actions = torch.zeros((capacity, action_dim), dtype=torch.float32, device=device)
        self.rewards = torch.zeros(capacity, dtype=torch.float32, device=device)
        self.next_states = torch.zeros((capacity, state_dim), dtype=torch.float32, device=device)
        self.dones = torch.zeros(capacity, dtype=torch.bool, device=device)
        self.log_probs = torch.zeros(capacity, dtype=torch.float32, device=device)
        self.values = torch.zeros(capacity, dtype=torch.float32, device=device)
        self.advantages = torch.zeros(capacity, dtype=torch.float32, device=device)
        self.returns = torch.zeros(capacity, dtype=torch.float32, device=device)
    
    def add(self, state: np.ndarray, action: np.ndarray, reward: float, 
            next_state: np.ndarray, done: bool, log_prob: float, value: float):
        """
        添加經驗
        
        Args:
            state: 狀態
            action: 動作
            reward: 獎勵
            next_state: 下一狀態
            done: 是否結束
            log_prob: 對數概率
            value: 狀態價值
        """
        self.states[self.ptr] = torch.FloatTensor(state).to(self.device)
        self.actions[self.ptr] = torch.FloatTensor(action).to(self.device)
        self.rewards[self.ptr] = reward
        self.next_states[self.ptr] = torch.FloatTensor(next_state).to(self.device)
        self.dones[self.ptr] = done
        self.log_probs[self.ptr] = log_prob
        self.values[self.ptr] = value
        
        self.ptr = (self.ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)
    
    def compute_gae(self, gamma: float = 0.99, gae_lambda: float = 0.95):
        """
        計算廣義優勢估計(GAE)
        
        Args:
            gamma: 折扣因子
            gae_lambda: GAE參數
        """
        advantages = torch.zeros_like(self.rewards)
        last_advantage = 0
        
        for t in reversed(range(self.size)):
            if t == self.size - 1:
                next_value = 0
            else:
                next_value = self.values[t + 1]
            
            delta = self.rewards[t] + gamma * next_value * (1 - self.dones[t]) - self.values[t]
            advantages[t] = last_advantage = delta + gamma * gae_lambda * (1 - self.dones[t]) * last_advantage
        
        self.advantages[:self.size] = advantages[:self.size]
        self.returns[:self.size] = self.advantages[:self.size] + self.values[:self.size]
    
    def get_batch(self, batch_size: int) -> Dict[str, torch.Tensor]:
        """
        獲取批次數據
        
        Args:
            batch_size: 批次大小
            
        Returns:
            批次數據字典
        """
        indices = torch.randint(0, self.size, (batch_size,), device=self.device)
        
        return {
            'states': self.states[indices],
            'actions': self.actions[indices],
            'rewards': self.rewards[indices],
            'next_states': self.next_states[indices],
            'dones': self.dones[indices],
            'log_probs': self.log_probs[indices],
            'values': self.values[indices],
            'advantages': self.advantages[indices],
            'returns': self.returns[indices]
        }
    
    def clear(self):
        """清空緩衝區"""
        self.ptr = 0
        self.size = 0


class PPOAgent(BaseRLAgent):
    """
    PPO代理實現
    
    基於Proximal Policy Optimization算法的強化學習代理
    """
    
    def __init__(self, observation_space: gym.Space, action_space: gym.Space, config: AgentConfig):
        """
        初始化PPO代理
        
        Args:
            observation_space: 觀察空間
            action_space: 動作空間
            config: 代理配置
        """
        super().__init__(observation_space, action_space, config)
        
        # 確定動作空間類型
        self.is_continuous = isinstance(action_space, gym.spaces.Box)
        
        # 網絡維度
        self.state_dim = observation_space.shape[0]
        if self.is_continuous:
            self.action_dim = action_space.shape[0]
        else:
            self.action_dim = action_space.n
        
        # PPO特定參數
        self.clip_epsilon = 0.2
        self.entropy_coef = 0.01
        self.value_coef = 0.5
        self.max_grad_norm = 0.5
        self.ppo_epochs = 10
        self.gae_lambda = 0.95
        
        # 構建網絡
        self._build_networks()
        
        # 經驗緩衝區
        self.buffer = PPOBuffer(
            capacity=config.buffer_size,
            state_dim=self.state_dim,
            action_dim=self.action_dim,
            device=self.device
        )
        
        logger.info(f"PPO代理初始化完成，狀態維度: {self.state_dim}, 動作維度: {self.action_dim}")
    
    def _build_networks(self):
        """構建神經網絡"""
        # 策略網絡
        self.policy_net = PolicyNetwork(
            state_dim=self.state_dim,
            action_dim=self.action_dim,
            hidden_dim=256,
            is_continuous=self.is_continuous
        ).to(self.device)
        
        # 價值網絡
        self.value_net = ValueNetwork(
            state_dim=self.state_dim,
            hidden_dim=256
        ).to(self.device)
        
        # 優化器
        self.policy_optimizer = optim.Adam(self.policy_net.parameters(), lr=self.config.learning_rate)
        self.value_optimizer = optim.Adam(self.value_net.parameters(), lr=self.config.learning_rate)
        
        logger.info("PPO網絡構建完成")
    
    def select_action(self, observation: np.ndarray, deterministic: bool = False) -> np.ndarray:
        """
        選擇動作
        
        Args:
            observation: 觀察
            deterministic: 是否確定性選擇
            
        Returns:
            動作
        """
        with torch.no_grad():
            state = torch.FloatTensor(observation).unsqueeze(0).to(self.device)
            action, _ = self.policy_net.get_action_and_log_prob(state, deterministic)
            
            if self.is_continuous:
                return action.cpu().numpy().flatten()
            else:
                return action.cpu().numpy()
    
    def get_action_and_value(self, observation: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """
        獲取動作、價值和對數概率
        
        Args:
            observation: 觀察
            
        Returns:
            (動作, 價值, 對數概率)
        """
        with torch.no_grad():
            state = torch.FloatTensor(observation).unsqueeze(0).to(self.device)
            action, log_prob = self.policy_net.get_action_and_log_prob(state, deterministic=False)
            value = self.value_net(state)
            
            if self.is_continuous:
                action_np = action.cpu().numpy().flatten()
            else:
                action_np = action.cpu().numpy()
            
            return action_np, value.item(), log_prob.item() if log_prob is not None else 0.0
    
    def update(self, batch: Dict[str, np.ndarray]) -> Dict[str, float]:
        """
        更新模型
        
        Args:
            batch: 批次數據
            
        Returns:
            訓練統計信息
        """
        # 計算GAE
        self.buffer.compute_gae(self.config.gamma, self.gae_lambda)
        
        total_policy_loss = 0
        total_value_loss = 0
        total_entropy = 0
        
        # PPO更新
        for _ in range(self.ppo_epochs):
            batch_data = self.buffer.get_batch(self.config.batch_size)
            
            # 計算當前策略的動作概率
            if self.is_continuous:
                mean, log_std = self.policy_net(batch_data['states'])
                std = torch.exp(log_std)
                dist = Normal(mean, std)
                new_log_probs = dist.log_prob(batch_data['actions']).sum(dim=-1)
                entropy = dist.entropy().sum(dim=-1).mean()
            else:
                action_logits, _ = self.policy_net(batch_data['states'])
                dist = Categorical(logits=action_logits)
                new_log_probs = dist.log_prob(batch_data['actions'].long())
                entropy = dist.entropy().mean()
            
            # 計算比率
            ratio = torch.exp(new_log_probs - batch_data['log_probs'])
            
            # 計算策略損失
            advantages = batch_data['advantages']
            advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
            
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()
            
            # 計算價值損失
            values = self.value_net(batch_data['states']).squeeze()
            value_loss = F.mse_loss(values, batch_data['returns'])
            
            # 總損失
            total_loss = policy_loss + self.value_coef * value_loss - self.entropy_coef * entropy
            
            # 更新策略網絡
            self.policy_optimizer.zero_grad()
            policy_loss.backward(retain_graph=True)
            torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), self.max_grad_norm)
            self.policy_optimizer.step()
            
            # 更新價值網絡
            self.value_optimizer.zero_grad()
            value_loss.backward()
            torch.nn.utils.clip_grad_norm_(self.value_net.parameters(), self.max_grad_norm)
            self.value_optimizer.step()
            
            total_policy_loss += policy_loss.item()
            total_value_loss += value_loss.item()
            total_entropy += entropy.item()
        
        # 清空緩衝區
        self.buffer.clear()
        
        return {
            'policy_loss': total_policy_loss / self.ppo_epochs,
            'value_loss': total_value_loss / self.ppo_epochs,
            'entropy': total_entropy / self.ppo_epochs,
            'total_loss': (total_policy_loss + total_value_loss) / self.ppo_epochs
        }
    
    def save_model(self, path: str):
        """
        保存模型
        
        Args:
            path: 保存路徑
        """
        try:
            checkpoint = {
                'policy_net_state_dict': self.policy_net.state_dict(),
                'value_net_state_dict': self.value_net.state_dict(),
                'policy_optimizer_state_dict': self.policy_optimizer.state_dict(),
                'value_optimizer_state_dict': self.value_optimizer.state_dict(),
                'config': self.config,
                'total_steps': self.total_steps,
                'episode_count': self.episode_count
            }
            
            torch.save(checkpoint, path)
            logger.info(f"PPO模型已保存到: {path}")
            
        except Exception as e:
            logger.error(f"保存PPO模型失敗: {e}")
            raise
    
    def load_model(self, path: str):
        """
        加載模型
        
        Args:
            path: 模型路徑
        """
        try:
            checkpoint = torch.load(path, map_location=self.device)
            
            self.policy_net.load_state_dict(checkpoint['policy_net_state_dict'])
            self.value_net.load_state_dict(checkpoint['value_net_state_dict'])
            self.policy_optimizer.load_state_dict(checkpoint['policy_optimizer_state_dict'])
            self.value_optimizer.load_state_dict(checkpoint['value_optimizer_state_dict'])
            
            self.total_steps = checkpoint.get('total_steps', 0)
            self.episode_count = checkpoint.get('episode_count', 0)
            
            logger.info(f"PPO模型已從 {path} 加載")
            
        except Exception as e:
            logger.error(f"加載PPO模型失敗: {e}")
            raise
