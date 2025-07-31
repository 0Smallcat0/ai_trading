# -*- coding: utf-8 -*-
"""
強化學習代理包裝器

此模組將強化學習代理包裝為多代理系統中的一個代理，
實現與其他投資大師代理的協作。

主要功能：
- RL代理包裝和適配
- 決策格式轉換
- 性能監控和統計
- 與協調機制整合
- 自適應學習能力

整合特色：
- 無縫整合到多代理系統
- 保持RL代理的學習能力
- 支援多種RL算法
- 提供統一的決策接口
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import gym
from gym import spaces

from ..base import BaseAgent, AgentConfig, Decision, MarketData, PortfolioState
from ...reinforcement_learning.core.base_agent import BaseRLAgent
from ...reinforcement_learning.adaptive_learning import AdaptiveLearningManager, AdaptiveConfig

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class RLAgentConfig(AgentConfig):
    """RL代理配置"""
    rl_algorithm: str = "PPO"
    observation_window: int = 30
    action_scaling: float = 1.0
    reward_scaling: float = 1.0
    adaptive_learning: bool = True
    performance_tracking: bool = True
    
    # 自適應學習配置
    online_learning: bool = True
    drift_detection: bool = True
    model_selection: bool = False


class RLAgentWrapper(BaseAgent):
    """
    強化學習代理包裝器
    
    將RL代理包裝為多代理系統中的一個代理
    """
    
    def __init__(self, rl_agent: BaseRLAgent, config: RLAgentConfig):
        """
        初始化RL代理包裝器
        
        Args:
            rl_agent: 強化學習代理
            config: 配置參數
        """
        super().__init__(config)
        
        self.rl_agent = rl_agent
        self.rl_config = config
        
        # 觀察和動作空間
        self.observation_dim = None
        self.action_dim = None
        
        # 數據預處理
        self.observation_buffer = []
        self.feature_columns = [
            'open', 'high', 'low', 'close', 'volume',
            'ma_5', 'ma_10', 'ma_20', 'rsi', 'macd'
        ]
        
        # 自適應學習
        if config.adaptive_learning:
            adaptive_config = AdaptiveConfig(
                online_learning_enabled=config.online_learning,
                drift_detection_enabled=config.drift_detection,
                model_selection_enabled=config.model_selection
            )
            self.adaptive_manager = AdaptiveLearningManager(rl_agent, adaptive_config)
        else:
            self.adaptive_manager = None
        
        # 性能追蹤
        self.decision_history = []
        self.performance_metrics = {
            'total_decisions': 0,
            'profitable_decisions': 0,
            'average_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0
        }
        
        logger.info(f"RL代理包裝器初始化完成: {config.name} ({config.rl_algorithm})")
    
    def make_decision(self, market_data: MarketData, portfolio_state: PortfolioState) -> Decision:
        """
        做出投資決策
        
        Args:
            market_data: 市場數據
            portfolio_state: 投資組合狀態
            
        Returns:
            投資決策
        """
        try:
            # 準備觀察數據
            observation = self._prepare_observation(market_data, portfolio_state)
            
            if observation is None:
                return self._create_hold_decision("insufficient_data")
            
            # 使用RL代理選擇動作
            action = self.rl_agent.select_action(observation, deterministic=not self.rl_agent.training_mode)
            
            # 轉換動作為決策
            decision = self._convert_action_to_decision(action, market_data, portfolio_state)
            
            # 記錄決策
            self._record_decision(decision, observation, action)
            
            # 更新性能指標
            self._update_performance_metrics(decision, portfolio_state)
            
            return decision
            
        except Exception as e:
            logger.error(f"RL代理決策失敗: {e}")
            return self._create_hold_decision("error")
    
    def _prepare_observation(self, market_data: MarketData, portfolio_state: PortfolioState) -> Optional[np.ndarray]:
        """
        準備觀察數據
        
        Args:
            market_data: 市場數據
            portfolio_state: 投資組合狀態
            
        Returns:
            觀察向量
        """
        try:
            # 獲取市場數據特徵
            market_features = self._extract_market_features(market_data)
            
            if market_features is None:
                return None
            
            # 獲取投資組合特徵
            portfolio_features = self._extract_portfolio_features(portfolio_state)
            
            # 合併特徵
            observation = np.concatenate([market_features, portfolio_features])
            
            # 標準化
            observation = self._normalize_observation(observation)
            
            return observation
            
        except Exception as e:
            logger.error(f"準備觀察數據失敗: {e}")
            return None
    
    def _extract_market_features(self, market_data: MarketData) -> Optional[np.ndarray]:
        """提取市場特徵"""
        try:
            if not hasattr(market_data, 'data') or market_data.data.empty:
                return None
            
            # 獲取最新的市場數據
            latest_data = market_data.data.tail(self.rl_config.observation_window)
            
            if len(latest_data) < self.rl_config.observation_window:
                return None
            
            # 提取特徵
            features = []
            
            for col in self.feature_columns:
                if col in latest_data.columns:
                    values = latest_data[col].values
                    features.extend(values)
                else:
                    # 如果缺少某個特徵，用零填充
                    features.extend([0.0] * self.rl_config.observation_window)
            
            return np.array(features, dtype=np.float32)
            
        except Exception as e:
            logger.error(f"提取市場特徵失敗: {e}")
            return None
    
    def _extract_portfolio_features(self, portfolio_state: PortfolioState) -> np.ndarray:
        """提取投資組合特徵"""
        try:
            features = [
                portfolio_state.total_value / 1000000.0,  # 標準化總價值
                portfolio_state.cash / portfolio_state.total_value,  # 現金比例
                len(portfolio_state.positions),  # 持倉數量
                portfolio_state.daily_return,  # 日收益率
                portfolio_state.total_return,  # 總收益率
            ]
            
            # 添加持倉權重（取前5大持倉）
            position_weights = []
            if portfolio_state.positions:
                sorted_positions = sorted(
                    portfolio_state.positions.items(),
                    key=lambda x: abs(x[1].market_value),
                    reverse=True
                )
                
                for i in range(5):
                    if i < len(sorted_positions):
                        weight = sorted_positions[i][1].market_value / portfolio_state.total_value
                        position_weights.append(weight)
                    else:
                        position_weights.append(0.0)
            else:
                position_weights = [0.0] * 5
            
            features.extend(position_weights)
            
            return np.array(features, dtype=np.float32)
            
        except Exception as e:
            logger.error(f"提取投資組合特徵失敗: {e}")
            return np.zeros(10, dtype=np.float32)
    
    def _normalize_observation(self, observation: np.ndarray) -> np.ndarray:
        """標準化觀察數據"""
        try:
            # 簡單的標準化：限制在[-1, 1]範圍內
            observation = np.clip(observation, -10, 10)
            observation = observation / 10.0
            
            return observation
            
        except Exception as e:
            logger.error(f"觀察數據標準化失敗: {e}")
            return observation
    
    def _convert_action_to_decision(
        self, 
        action: np.ndarray, 
        market_data: MarketData, 
        portfolio_state: PortfolioState
    ) -> Decision:
        """
        轉換RL動作為投資決策
        
        Args:
            action: RL動作
            market_data: 市場數據
            portfolio_state: 投資組合狀態
            
        Returns:
            投資決策
        """
        try:
            # 根據動作空間類型處理
            if isinstance(self.rl_agent.action_space, spaces.Box):
                # 連續動作空間
                return self._convert_continuous_action(action, market_data, portfolio_state)
            else:
                # 離散動作空間
                return self._convert_discrete_action(action, market_data, portfolio_state)
                
        except Exception as e:
            logger.error(f"動作轉換失敗: {e}")
            return self._create_hold_decision("conversion_error")
    
    def _convert_continuous_action(
        self, 
        action: np.ndarray, 
        market_data: MarketData, 
        portfolio_state: PortfolioState
    ) -> Decision:
        """轉換連續動作"""
        try:
            # 假設動作格式：[動作類型, 倉位比例]
            action_type = action[0]  # -1到1，負數賣出，正數買入
            position_ratio = abs(action[1]) * self.rl_config.action_scaling  # 0到1，倉位比例
            
            # 限制倉位比例
            position_ratio = np.clip(position_ratio, 0.0, 1.0)
            
            # 確定動作類型
            if action_type > 0.1:
                action_name = "buy"
                confidence = min(action_type, 1.0)
            elif action_type < -0.1:
                action_name = "sell"
                confidence = min(abs(action_type), 1.0)
            else:
                action_name = "hold"
                confidence = 0.5
            
            # 計算目標權重
            if action_name == "buy":
                target_weight = position_ratio
            elif action_name == "sell":
                target_weight = max(0.0, portfolio_state.positions.get(market_data.symbol, 0) - position_ratio)
            else:
                target_weight = portfolio_state.positions.get(market_data.symbol, 0)
            
            return Decision(
                symbol=market_data.symbol,
                action=action_name,
                quantity=0,  # 將由執行器計算
                price=market_data.current_price,
                confidence=confidence,
                reasoning=f"RL決策: {action_name}, 目標權重: {target_weight:.2%}",
                metadata={
                    'agent_type': 'reinforcement_learning',
                    'algorithm': self.rl_config.rl_algorithm,
                    'target_weight': target_weight,
                    'raw_action': action.tolist()
                }
            )
            
        except Exception as e:
            logger.error(f"連續動作轉換失敗: {e}")
            return self._create_hold_decision("continuous_conversion_error")
    
    def _convert_discrete_action(
        self, 
        action: np.ndarray, 
        market_data: MarketData, 
        portfolio_state: PortfolioState
    ) -> Decision:
        """轉換離散動作"""
        try:
            action_idx = int(action[0]) if isinstance(action, np.ndarray) else int(action)
            
            # 動作映射
            action_map = {
                0: ("sell", 0.8),
                1: ("hold", 0.5),
                2: ("buy", 0.8)
            }
            
            action_name, confidence = action_map.get(action_idx, ("hold", 0.5))
            
            return Decision(
                symbol=market_data.symbol,
                action=action_name,
                quantity=0,  # 將由執行器計算
                price=market_data.current_price,
                confidence=confidence,
                reasoning=f"RL決策: {action_name} (動作索引: {action_idx})",
                metadata={
                    'agent_type': 'reinforcement_learning',
                    'algorithm': self.rl_config.rl_algorithm,
                    'action_index': action_idx,
                    'raw_action': action.tolist() if isinstance(action, np.ndarray) else action
                }
            )
            
        except Exception as e:
            logger.error(f"離散動作轉換失敗: {e}")
            return self._create_hold_decision("discrete_conversion_error")
    
    def _create_hold_decision(self, reason: str) -> Decision:
        """創建持有決策"""
        return Decision(
            symbol="",
            action="hold",
            quantity=0,
            price=0.0,
            confidence=0.5,
            reasoning=f"RL代理持有決策: {reason}",
            metadata={
                'agent_type': 'reinforcement_learning',
                'algorithm': self.rl_config.rl_algorithm,
                'reason': reason
            }
        )
    
    def _record_decision(self, decision: Decision, observation: np.ndarray, action: np.ndarray):
        """記錄決策"""
        try:
            decision_record = {
                'timestamp': pd.Timestamp.now(),
                'decision': decision,
                'observation': observation,
                'action': action,
                'agent_name': self.config.name
            }
            
            self.decision_history.append(decision_record)
            
            # 保持歷史記錄在合理範圍內
            if len(self.decision_history) > 10000:
                self.decision_history = self.decision_history[-10000:]
            
            # 如果啟用自適應學習，添加經驗
            if self.adaptive_manager:
                experience = {
                    'states': observation,
                    'actions': action,
                    'rewards': 0.0,  # 將在後續更新
                    'next_states': observation,  # 將在下次決策時更新
                    'dones': False
                }
                
                # 這裡需要實現經驗的完整記錄邏輯
                # self.adaptive_manager.step(experience, performance_metrics)
            
        except Exception as e:
            logger.error(f"記錄決策失敗: {e}")
    
    def _update_performance_metrics(self, decision: Decision, portfolio_state: PortfolioState):
        """更新性能指標"""
        try:
            self.performance_metrics['total_decisions'] += 1
            
            # 這裡需要實現更詳細的性能計算邏輯
            # 包括收益率、夏普比率、最大回撤等
            
        except Exception as e:
            logger.error(f"更新性能指標失敗: {e}")
    
    def update_from_feedback(self, feedback: Dict[str, Any]):
        """
        從反饋中學習
        
        Args:
            feedback: 反饋信息
        """
        try:
            if self.adaptive_manager and 'reward' in feedback:
                # 更新最近的經驗記錄
                if self.decision_history:
                    last_record = self.decision_history[-1]
                    
                    # 創建完整的經驗
                    experience = {
                        'states': last_record['observation'],
                        'actions': last_record['action'],
                        'rewards': feedback['reward'] * self.rl_config.reward_scaling,
                        'next_states': feedback.get('next_observation', last_record['observation']),
                        'dones': feedback.get('done', False)
                    }
                    
                    # 性能指標
                    performance_metrics = {
                        'reward': feedback['reward'],
                        'loss': feedback.get('loss', 0.0),
                        'accuracy': feedback.get('accuracy', 0.0)
                    }
                    
                    # 執行自適應學習步驟
                    self.adaptive_manager.step(experience, performance_metrics)
            
        except Exception as e:
            logger.error(f"從反饋學習失敗: {e}")
    
    def get_agent_status(self) -> Dict[str, Any]:
        """獲取代理狀態"""
        status = super().get_agent_status()
        
        # 添加RL特定狀態
        status.update({
            'rl_algorithm': self.rl_config.rl_algorithm,
            'training_mode': self.rl_agent.training_mode,
            'total_steps': self.rl_agent.total_steps,
            'episode_count': self.rl_agent.episode_count,
            'decision_count': len(self.decision_history),
            'performance_metrics': self.performance_metrics.copy()
        })
        
        # 添加自適應學習狀態
        if self.adaptive_manager:
            status['adaptive_status'] = self.adaptive_manager.get_adaptation_status()
        
        return status
    
    def save_model(self, path: str):
        """保存RL模型"""
        try:
            self.rl_agent.save_model(path)
            logger.info(f"RL模型已保存: {path}")
        except Exception as e:
            logger.error(f"保存RL模型失敗: {e}")
    
    def load_model(self, path: str):
        """加載RL模型"""
        try:
            self.rl_agent.load_model(path)
            logger.info(f"RL模型已加載: {path}")
        except Exception as e:
            logger.error(f"加載RL模型失敗: {e}")
    
    def set_training_mode(self, training: bool = True):
        """設定訓練模式"""
        self.rl_agent.set_training_mode(training)
        logger.info(f"RL代理訓練模式: {training}")
    
    def get_recent_decisions(self, count: int = 10) -> List[Dict[str, Any]]:
        """獲取最近的決策記錄"""
        return self.decision_history[-count:] if self.decision_history else []
