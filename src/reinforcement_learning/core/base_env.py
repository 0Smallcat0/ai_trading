# -*- coding: utf-8 -*-
"""
基礎環境類

此模組定義了強化學習環境的基礎抽象類，
提供統一的接口標準和通用功能。

主要功能：
- 統一的環境接口
- 標準化的觀察和動作空間
- 通用的獎勵計算機制
- 環境狀態管理
- 數據預處理和後處理

設計原則：
- 遵循OpenAI Gym標準
- 支援TradeMaster擴展
- 模組化和可擴展
- 高性能和穩定性
"""

import logging
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
import gym
from gym import spaces

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class EnvironmentConfig:
    """環境配置類"""
    name: str
    initial_balance: float = 1000000.0
    transaction_cost: float = 0.001
    max_position: float = 1.0
    lookback_window: int = 30
    features: List[str] = None
    normalize: bool = True
    random_seed: Optional[int] = None


@dataclass
class EnvironmentState:
    """環境狀態類"""
    current_step: int
    balance: float
    positions: Dict[str, float]
    portfolio_value: float
    market_data: pd.DataFrame
    features: np.ndarray
    done: bool = False


class BaseEnvironment(gym.Env, ABC):
    """
    基礎環境抽象類
    
    定義了所有強化學習交易環境的通用接口和功能。
    所有具體環境都應該繼承此類並實現抽象方法。
    """
    
    def __init__(self, config: EnvironmentConfig):
        """
        初始化基礎環境
        
        Args:
            config: 環境配置
        """
        super().__init__()
        
        self.config = config
        self.state = None
        self.data = None
        
        # 設定隨機種子
        if config.random_seed is not None:
            np.random.seed(config.random_seed)
        
        # 初始化空間（子類需要實現）
        self.observation_space = None
        self.action_space = None
        
        # 性能統計
        self.episode_rewards = []
        self.episode_lengths = []
        self.total_episodes = 0
        
        logger.info(f"初始化環境: {config.name}")
    
    @abstractmethod
    def _create_observation_space(self) -> spaces.Space:
        """創建觀察空間（子類實現）"""
        pass
    
    @abstractmethod
    def _create_action_space(self) -> spaces.Space:
        """創建動作空間（子類實現）"""
        pass
    
    @abstractmethod
    def _get_observation(self) -> np.ndarray:
        """獲取當前觀察（子類實現）"""
        pass
    
    @abstractmethod
    def _calculate_reward(self, action: np.ndarray) -> float:
        """計算獎勵（子類實現）"""
        pass
    
    @abstractmethod
    def _execute_action(self, action: np.ndarray) -> Dict[str, Any]:
        """執行動作（子類實現）"""
        pass
    
    @abstractmethod
    def _is_done(self) -> bool:
        """判斷是否結束（子類實現）"""
        pass
    
    def reset(self) -> np.ndarray:
        """
        重置環境
        
        Returns:
            初始觀察
        """
        try:
            # 重置狀態
            self.state = EnvironmentState(
                current_step=0,
                balance=self.config.initial_balance,
                positions={},
                portfolio_value=self.config.initial_balance,
                market_data=self.data,
                features=np.array([])
            )
            
            # 獲取初始觀察
            observation = self._get_observation()
            
            logger.debug(f"環境重置完成，初始觀察形狀: {observation.shape}")
            return observation
            
        except Exception as e:
            logger.error(f"環境重置失敗: {e}")
            raise
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """
        執行一步
        
        Args:
            action: 動作
            
        Returns:
            (觀察, 獎勵, 是否結束, 信息)
        """
        try:
            # 驗證動作
            if not self.action_space.contains(action):
                logger.warning(f"無效動作: {action}")
                action = np.clip(action, self.action_space.low, self.action_space.high)
            
            # 執行動作
            action_info = self._execute_action(action)
            
            # 計算獎勵
            reward = self._calculate_reward(action)
            
            # 更新狀態
            self.state.current_step += 1
            
            # 檢查是否結束
            done = self._is_done()
            self.state.done = done
            
            # 獲取新觀察
            observation = self._get_observation()
            
            # 準備信息
            info = {
                'step': self.state.current_step,
                'balance': self.state.balance,
                'portfolio_value': self.state.portfolio_value,
                'positions': self.state.positions.copy(),
                'action_info': action_info
            }
            
            # 如果結束，記錄統計信息
            if done:
                self._record_episode_stats(reward)
            
            return observation, reward, done, info
            
        except Exception as e:
            logger.error(f"環境步驟執行失敗: {e}")
            raise
    
    def render(self, mode: str = 'human') -> Optional[np.ndarray]:
        """
        渲染環境
        
        Args:
            mode: 渲染模式
            
        Returns:
            渲染結果（如果需要）
        """
        if mode == 'human':
            print(f"Step: {self.state.current_step}")
            print(f"Balance: ${self.state.balance:,.2f}")
            print(f"Portfolio Value: ${self.state.portfolio_value:,.2f}")
            print(f"Positions: {self.state.positions}")
            print("-" * 50)
        
        return None
    
    def close(self):
        """關閉環境"""
        logger.info(f"關閉環境: {self.config.name}")
    
    def seed(self, seed: Optional[int] = None) -> List[int]:
        """
        設定隨機種子
        
        Args:
            seed: 隨機種子
            
        Returns:
            種子列表
        """
        if seed is not None:
            np.random.seed(seed)
            self.config.random_seed = seed
        
        return [seed]
    
    def set_data(self, data: pd.DataFrame):
        """
        設定市場數據
        
        Args:
            data: 市場數據DataFrame
        """
        try:
            # 驗證數據格式
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in data.columns]
            
            if missing_columns:
                raise ValueError(f"缺少必要的數據列: {missing_columns}")
            
            # 數據預處理
            self.data = self._preprocess_data(data)
            
            # 創建觀察和動作空間
            if self.observation_space is None:
                self.observation_space = self._create_observation_space()
            
            if self.action_space is None:
                self.action_space = self._create_action_space()
            
            logger.info(f"設定市場數據完成，數據形狀: {self.data.shape}")
            
        except Exception as e:
            logger.error(f"設定市場數據失敗: {e}")
            raise
    
    def _preprocess_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        數據預處理
        
        Args:
            data: 原始數據
            
        Returns:
            預處理後的數據
        """
        try:
            # 複製數據避免修改原始數據
            processed_data = data.copy()
            
            # 排序數據
            if 'date' in processed_data.columns:
                processed_data = processed_data.sort_values('date')
            
            # 計算技術指標
            processed_data = self._calculate_technical_indicators(processed_data)
            
            # 數據標準化
            if self.config.normalize:
                processed_data = self._normalize_data(processed_data)
            
            # 處理缺失值
            processed_data = processed_data.fillna(method='forward').fillna(0)
            
            return processed_data
            
        except Exception as e:
            logger.error(f"數據預處理失敗: {e}")
            raise
    
    def _calculate_technical_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        計算技術指標
        
        Args:
            data: 市場數據
            
        Returns:
            包含技術指標的數據
        """
        try:
            # 移動平均
            data['ma_5'] = data['close'].rolling(window=5).mean()
            data['ma_10'] = data['close'].rolling(window=10).mean()
            data['ma_20'] = data['close'].rolling(window=20).mean()
            
            # RSI
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            data['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = data['close'].ewm(span=12).mean()
            exp2 = data['close'].ewm(span=26).mean()
            data['macd'] = exp1 - exp2
            data['macd_signal'] = data['macd'].ewm(span=9).mean()
            
            # 布林帶
            data['bb_middle'] = data['close'].rolling(window=20).mean()
            bb_std = data['close'].rolling(window=20).std()
            data['bb_upper'] = data['bb_middle'] + (bb_std * 2)
            data['bb_lower'] = data['bb_middle'] - (bb_std * 2)
            
            # 價格變化率
            data['price_change'] = data['close'].pct_change()
            data['volume_change'] = data['volume'].pct_change()
            
            return data
            
        except Exception as e:
            logger.error(f"技術指標計算失敗: {e}")
            return data
    
    def _normalize_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        數據標準化
        
        Args:
            data: 原始數據
            
        Returns:
            標準化後的數據
        """
        try:
            # 選擇需要標準化的列
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            
            # 排除不需要標準化的列
            exclude_columns = ['date', 'symbol']
            normalize_columns = [col for col in numeric_columns if col not in exclude_columns]
            
            # Z-score標準化
            for col in normalize_columns:
                if data[col].std() > 0:
                    data[col] = (data[col] - data[col].mean()) / data[col].std()
            
            return data
            
        except Exception as e:
            logger.error(f"數據標準化失敗: {e}")
            return data
    
    def _record_episode_stats(self, final_reward: float):
        """
        記錄回合統計信息
        
        Args:
            final_reward: 最終獎勵
        """
        try:
            self.episode_rewards.append(final_reward)
            self.episode_lengths.append(self.state.current_step)
            self.total_episodes += 1
            
            # 保持統計信息在合理範圍內
            if len(self.episode_rewards) > 1000:
                self.episode_rewards = self.episode_rewards[-1000:]
                self.episode_lengths = self.episode_lengths[-1000:]
            
            logger.debug(f"回合 {self.total_episodes} 完成，獎勵: {final_reward:.4f}")
            
        except Exception as e:
            logger.error(f"記錄回合統計失敗: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        獲取環境統計信息
        
        Returns:
            統計信息字典
        """
        if not self.episode_rewards:
            return {}
        
        return {
            'total_episodes': self.total_episodes,
            'avg_reward': np.mean(self.episode_rewards),
            'std_reward': np.std(self.episode_rewards),
            'max_reward': np.max(self.episode_rewards),
            'min_reward': np.min(self.episode_rewards),
            'avg_length': np.mean(self.episode_lengths),
            'recent_avg_reward': np.mean(self.episode_rewards[-10:]) if len(self.episode_rewards) >= 10 else np.mean(self.episode_rewards)
        }
