# -*- coding: utf-8 -*-
"""
基礎代理類

此模組定義了強化學習代理的基礎抽象類，
提供統一的接口標準和通用功能。

主要功能：
- 統一的代理接口
- 模型管理和持久化
- 訓練和推理模式切換
- 性能監控和統計
- 超參數管理

設計原則：
- 算法無關的抽象接口
- 支援多種RL算法
- 模組化和可擴展
- 高性能和穩定性
"""

import logging
import numpy as np
import torch
import pickle
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import gym

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """代理配置類"""
    name: str
    algorithm: str
    learning_rate: float = 3e-4
    batch_size: int = 64
    buffer_size: int = 100000
    gamma: float = 0.99
    tau: float = 0.005
    exploration_noise: float = 0.1
    policy_noise: float = 0.2
    noise_clip: float = 0.5
    policy_freq: int = 2
    device: str = "auto"
    random_seed: Optional[int] = None


@dataclass
class TrainingStats:
    """訓練統計類"""
    episode: int = 0
    total_steps: int = 0
    episode_reward: float = 0.0
    episode_length: int = 0
    loss: float = 0.0
    q_value: float = 0.0
    policy_loss: float = 0.0
    value_loss: float = 0.0
    exploration_rate: float = 0.0


class BaseRLAgent(ABC):
    """
    基礎RL代理抽象類
    
    定義了所有強化學習代理的通用接口和功能。
    所有具體代理都應該繼承此類並實現抽象方法。
    """
    
    def __init__(self, observation_space: gym.Space, action_space: gym.Space, config: AgentConfig):
        """
        初始化基礎代理
        
        Args:
            observation_space: 觀察空間
            action_space: 動作空間
            config: 代理配置
        """
        self.observation_space = observation_space
        self.action_space = action_space
        self.config = config
        
        # 設定設備
        self.device = self._setup_device(config.device)
        
        # 設定隨機種子
        if config.random_seed is not None:
            self._set_random_seed(config.random_seed)
        
        # 初始化模型（子類實現）
        self.policy_net = None
        self.target_net = None
        self.optimizer = None
        
        # 訓練狀態
        self.training_mode = True
        self.total_steps = 0
        self.episode_count = 0
        
        # 統計信息
        self.training_stats = []
        self.performance_history = []
        
        logger.info(f"初始化代理: {config.name} ({config.algorithm})")
    
    @abstractmethod
    def _build_networks(self):
        """構建神經網絡（子類實現）"""
        pass
    
    @abstractmethod
    def select_action(self, observation: np.ndarray, deterministic: bool = False) -> np.ndarray:
        """選擇動作（子類實現）"""
        pass
    
    @abstractmethod
    def update(self, batch: Dict[str, np.ndarray]) -> Dict[str, float]:
        """更新模型（子類實現）"""
        pass
    
    @abstractmethod
    def save_model(self, path: str):
        """保存模型（子類實現）"""
        pass
    
    @abstractmethod
    def load_model(self, path: str):
        """加載模型（子類實現）"""
        pass
    
    def _setup_device(self, device: str) -> torch.device:
        """
        設定計算設備
        
        Args:
            device: 設備字符串
            
        Returns:
            PyTorch設備對象
        """
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        torch_device = torch.device(device)
        logger.info(f"使用設備: {torch_device}")
        
        return torch_device
    
    def _set_random_seed(self, seed: int):
        """
        設定隨機種子
        
        Args:
            seed: 隨機種子
        """
        np.random.seed(seed)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
        
        logger.info(f"設定隨機種子: {seed}")
    
    def set_training_mode(self, training: bool = True):
        """
        設定訓練模式
        
        Args:
            training: 是否為訓練模式
        """
        self.training_mode = training
        
        if self.policy_net is not None:
            if training:
                self.policy_net.train()
            else:
                self.policy_net.eval()
        
        logger.debug(f"設定訓練模式: {training}")
    
    def get_action_probabilities(self, observation: np.ndarray) -> np.ndarray:
        """
        獲取動作概率分布
        
        Args:
            observation: 觀察
            
        Returns:
            動作概率分布
        """
        # 默認實現，子類可以覆蓋
        action = self.select_action(observation, deterministic=True)
        
        # 對於連續動作空間，返回確定性動作
        if isinstance(self.action_space, gym.spaces.Box):
            return action
        
        # 對於離散動作空間，返回one-hot編碼
        if isinstance(self.action_space, gym.spaces.Discrete):
            probs = np.zeros(self.action_space.n)
            probs[int(action)] = 1.0
            return probs
        
        return action
    
    def get_q_values(self, observation: np.ndarray) -> np.ndarray:
        """
        獲取Q值
        
        Args:
            observation: 觀察
            
        Returns:
            Q值數組
        """
        # 默認實現，子類可以覆蓋
        if hasattr(self, 'q_net') and self.q_net is not None:
            with torch.no_grad():
                obs_tensor = torch.FloatTensor(observation).unsqueeze(0).to(self.device)
                q_values = self.q_net(obs_tensor)
                return q_values.cpu().numpy().flatten()
        
        # 如果沒有Q網絡，返回零數組
        if isinstance(self.action_space, gym.spaces.Discrete):
            return np.zeros(self.action_space.n)
        else:
            return np.zeros(self.action_space.shape[0])
    
    def record_training_stats(self, stats: TrainingStats):
        """
        記錄訓練統計信息
        
        Args:
            stats: 訓練統計
        """
        self.training_stats.append(stats)
        
        # 保持統計信息在合理範圍內
        if len(self.training_stats) > 10000:
            self.training_stats = self.training_stats[-10000:]
        
        logger.debug(f"記錄訓練統計: Episode {stats.episode}, Reward {stats.episode_reward:.4f}")
    
    def get_training_stats(self, last_n: int = 100) -> Dict[str, Any]:
        """
        獲取訓練統計信息
        
        Args:
            last_n: 最近N個回合
            
        Returns:
            統計信息字典
        """
        if not self.training_stats:
            return {}
        
        recent_stats = self.training_stats[-last_n:]
        
        rewards = [stat.episode_reward for stat in recent_stats]
        lengths = [stat.episode_length for stat in recent_stats]
        losses = [stat.loss for stat in recent_stats if stat.loss > 0]
        
        stats_dict = {
            'total_episodes': len(self.training_stats),
            'recent_episodes': len(recent_stats),
            'avg_reward': np.mean(rewards) if rewards else 0.0,
            'std_reward': np.std(rewards) if rewards else 0.0,
            'max_reward': np.max(rewards) if rewards else 0.0,
            'min_reward': np.min(rewards) if rewards else 0.0,
            'avg_length': np.mean(lengths) if lengths else 0.0,
            'avg_loss': np.mean(losses) if losses else 0.0,
            'total_steps': self.total_steps
        }
        
        return stats_dict
    
    def save_config(self, path: str):
        """
        保存配置
        
        Args:
            path: 保存路徑
        """
        try:
            config_dict = asdict(self.config)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置已保存到: {path}")
            
        except Exception as e:
            logger.error(f"保存配置失敗: {e}")
            raise
    
    def load_config(self, path: str) -> AgentConfig:
        """
        加載配置
        
        Args:
            path: 配置文件路徑
            
        Returns:
            代理配置
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            
            config = AgentConfig(**config_dict)
            logger.info(f"配置已從 {path} 加載")
            
            return config
            
        except Exception as e:
            logger.error(f"加載配置失敗: {e}")
            raise
    
    def save_training_stats(self, path: str):
        """
        保存訓練統計
        
        Args:
            path: 保存路徑
        """
        try:
            stats_data = [asdict(stat) for stat in self.training_stats]
            
            with open(path, 'wb') as f:
                pickle.dump(stats_data, f)
            
            logger.info(f"訓練統計已保存到: {path}")
            
        except Exception as e:
            logger.error(f"保存訓練統計失敗: {e}")
            raise
    
    def load_training_stats(self, path: str):
        """
        加載訓練統計
        
        Args:
            path: 統計文件路徑
        """
        try:
            with open(path, 'rb') as f:
                stats_data = pickle.load(f)
            
            self.training_stats = [TrainingStats(**stat) for stat in stats_data]
            logger.info(f"訓練統計已從 {path} 加載")
            
        except Exception as e:
            logger.error(f"加載訓練統計失敗: {e}")
            raise
    
    def reset_stats(self):
        """重置統計信息"""
        self.training_stats.clear()
        self.performance_history.clear()
        self.total_steps = 0
        self.episode_count = 0
        
        logger.info("統計信息已重置")
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        獲取模型信息
        
        Returns:
            模型信息字典
        """
        info = {
            'algorithm': self.config.algorithm,
            'observation_space': str(self.observation_space),
            'action_space': str(self.action_space),
            'device': str(self.device),
            'training_mode': self.training_mode,
            'total_steps': self.total_steps,
            'episode_count': self.episode_count
        }
        
        # 添加網絡參數信息
        if self.policy_net is not None:
            total_params = sum(p.numel() for p in self.policy_net.parameters())
            trainable_params = sum(p.numel() for p in self.policy_net.parameters() if p.requires_grad)
            
            info.update({
                'total_parameters': total_params,
                'trainable_parameters': trainable_params
            })
        
        return info
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.config.name} ({self.config.algorithm})"
    
    def __repr__(self) -> str:
        """詳細字符串表示"""
        return f"BaseRLAgent(name='{self.config.name}', algorithm='{self.config.algorithm}', device='{self.device}')"
