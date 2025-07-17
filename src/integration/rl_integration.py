# -*- coding: utf-8 -*-
"""
強化學習框架整合適配器

此模組將強化學習框架整合到原始項目中，
擴展原始項目的RL模組並提供統一的RL代理接口。

主要功能：
- RL代理系統整合
- TradeMaster框架適配
- 自適應學習機制整合
- 原始RL模組擴展
- 性能監控和優化

整合策略：
- 擴展原始項目的quant_brain/rl模組
- 整合TradeMaster專業框架
- 提供統一的RL代理接口
- 保持與原始項目的兼容性
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import numpy as np
import pandas as pd

# 設定日誌
logger = logging.getLogger(__name__)


class ReinforcementLearningAdapter:
    """
    強化學習框架整合適配器
    
    將強化學習框架整合到原始項目中
    """
    
    def __init__(self, config):
        """
        初始化強化學習適配器
        
        Args:
            config: 整合配置
        """
        self.config = config
        self.initialized = False
        
        # RL組件
        self.rl_agents = {}
        self.environments = {}
        self.trainers = {}
        
        # TradeMaster整合
        self.trademaster_integration = None
        
        # 自適應學習
        self.adaptive_manager = None
        self.concept_drift_detector = None
        
        # 原始項目RL模組
        self.legacy_rl_module = None
        
        logger.info("強化學習適配器初始化")
    
    def initialize(self) -> bool:
        """
        初始化強化學習系統
        
        Returns:
            是否初始化成功
        """
        try:
            # 檢查原始項目RL模組
            if not self._check_legacy_rl_module():
                logger.warning("原始項目RL模組檢查失敗，繼續初始化")
            
            # 初始化RL環境
            if not self._initialize_rl_environments():
                return False
            
            # 初始化RL代理
            if not self._initialize_rl_agents():
                return False
            
            # 初始化TradeMaster整合
            if not self._initialize_trademaster_integration():
                logger.warning("TradeMaster整合初始化失敗，使用基礎RL功能")
            
            # 初始化自適應學習
            if not self._initialize_adaptive_learning():
                logger.warning("自適應學習初始化失敗，使用基礎學習功能")
            
            # 初始化訓練器
            if not self._initialize_trainers():
                return False
            
            self.initialized = True
            logger.info("強化學習系統初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"強化學習系統初始化失敗: {e}")
            return False
    
    def _check_legacy_rl_module(self) -> bool:
        """檢查原始項目RL模組"""
        try:
            # 嘗試導入原始項目的RL模組
            import sys
            from pathlib import Path
            
            legacy_path = Path(self.config.legacy_project_path)
            rl_module_path = legacy_path / "quant_brain" / "rl"
            
            if rl_module_path.exists():
                # 添加到sys.path
                sys.path.insert(0, str(legacy_path))
                
                try:
                    import quant_brain.rl as legacy_rl
                    self.legacy_rl_module = legacy_rl
                    logger.info("原始項目RL模組載入成功")
                    return True
                except ImportError as e:
                    logger.warning(f"原始項目RL模組導入失敗: {e}")
                    return False
            else:
                logger.warning("原始項目RL模組不存在")
                return False
                
        except Exception as e:
            logger.error(f"檢查原始項目RL模組失敗: {e}")
            return False
    
    def _initialize_rl_environments(self) -> bool:
        """初始化RL環境"""
        try:
            from ..reinforcement_learning.environments.stock_trading_env import StockTradingEnvironment
            from ..reinforcement_learning.environments.portfolio_env import PortfolioEnvironment
            
            # 創建股票交易環境
            stock_env_config = {
                'initial_balance': 1000000.0,
                'transaction_cost': 0.001,
                'max_position': 1.0,
                'lookback_window': 30
            }
            
            self.environments['stock_trading'] = StockTradingEnvironment(stock_env_config)
            
            # 創建投資組合環境
            portfolio_env_config = {
                'initial_balance': 1000000.0,
                'max_assets': 10,
                'rebalance_frequency': 'daily'
            }
            
            self.environments['portfolio'] = PortfolioEnvironment(portfolio_env_config)
            
            logger.info(f"已初始化 {len(self.environments)} 個RL環境")
            return True
            
        except ImportError as e:
            logger.error(f"RL環境模組導入失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"RL環境初始化失敗: {e}")
            return False
    
    def _initialize_rl_agents(self) -> bool:
        """初始化RL代理"""
        try:
            from ..reinforcement_learning.agents.ppo_agent import PPOAgent
            from ..agents.personas.rl_agent import RLAgentWrapper
            
            # 創建PPO代理
            ppo_config = {
                'learning_rate': 0.0003,
                'batch_size': 64,
                'gamma': 0.99,
                'clip_epsilon': 0.2,
                'entropy_coef': 0.01,
                'value_coef': 0.5
            }
            
            # 為每個環境創建代理
            for env_name, environment in self.environments.items():
                try:
                    # 創建PPO代理
                    ppo_agent = PPOAgent(
                        observation_space=environment.observation_space,
                        action_space=environment.action_space,
                        config=ppo_config
                    )
                    
                    # 包裝為統一代理接口
                    rl_wrapper_config = {
                        'name': f'RL代理_{env_name}',
                        'weight': 0.2,
                        'environment': env_name,
                        'training_enabled': True
                    }
                    
                    rl_wrapper = RLAgentWrapper(ppo_agent, rl_wrapper_config)
                    
                    self.rl_agents[f'ppo_{env_name}'] = {
                        'agent': ppo_agent,
                        'wrapper': rl_wrapper,
                        'environment': environment
                    }
                    
                    logger.info(f"PPO代理創建成功: {env_name}")
                    
                except Exception as e:
                    logger.error(f"PPO代理創建失敗 {env_name}: {e}")
            
            logger.info(f"已初始化 {len(self.rl_agents)} 個RL代理")
            return True
            
        except ImportError as e:
            logger.error(f"RL代理模組導入失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"RL代理初始化失敗: {e}")
            return False
    
    def _initialize_trademaster_integration(self) -> bool:
        """初始化TradeMaster整合"""
        try:
            from ..reinforcement_learning.trademaster_integration import TradeMasterIntegration
            
            trademaster_config = {
                'framework': 'trademaster',
                'environment_type': 'portfolio',
                'agent_type': 'ppo',
                'data_source': 'yahoo',
                'training_episodes': 1000
            }
            
            self.trademaster_integration = TradeMasterIntegration(trademaster_config)
            
            # 初始化TradeMaster組件
            if self.trademaster_integration.initialize():
                logger.info("TradeMaster整合初始化成功")
                return True
            else:
                logger.warning("TradeMaster整合初始化失敗")
                return False
                
        except ImportError as e:
            logger.warning(f"TradeMaster模組不可用: {e}")
            return False
        except Exception as e:
            logger.error(f"TradeMaster整合初始化失敗: {e}")
            return False
    
    def _initialize_adaptive_learning(self) -> bool:
        """初始化自適應學習"""
        try:
            from ..reinforcement_learning.adaptive.adaptive_learning_manager import AdaptiveLearningManager
            from ..reinforcement_learning.adaptive.concept_drift_detector import ConceptDriftDetector
            
            # 創建概念漂移檢測器
            drift_config = {
                'window_size': 1000,
                'threshold': 0.05,
                'test_method': 'ks_test'
            }
            
            self.concept_drift_detector = ConceptDriftDetector(drift_config)
            
            # 創建自適應學習管理器
            adaptive_config = {
                'drift_detector': self.concept_drift_detector,
                'adaptation_threshold': 0.1,
                'min_samples': 100,
                'max_models': 5
            }
            
            self.adaptive_manager = AdaptiveLearningManager(adaptive_config)
            
            logger.info("自適應學習系統初始化成功")
            return True
            
        except ImportError as e:
            logger.warning(f"自適應學習模組不可用: {e}")
            return False
        except Exception as e:
            logger.error(f"自適應學習初始化失敗: {e}")
            return False
    
    def _initialize_trainers(self) -> bool:
        """初始化訓練器"""
        try:
            from ..reinforcement_learning.training.rl_trainer import RLTrainer
            
            # 為每個代理創建訓練器
            for agent_name, agent_info in self.rl_agents.items():
                try:
                    trainer_config = {
                        'max_episodes': 1000,
                        'max_steps_per_episode': 1000,
                        'save_frequency': 100,
                        'evaluation_frequency': 50,
                        'early_stopping': True,
                        'patience': 100
                    }
                    
                    trainer = RLTrainer(
                        agent=agent_info['agent'],
                        environment=agent_info['environment'],
                        config=trainer_config
                    )
                    
                    self.trainers[agent_name] = trainer
                    logger.info(f"訓練器創建成功: {agent_name}")
                    
                except Exception as e:
                    logger.error(f"訓練器創建失敗 {agent_name}: {e}")
            
            logger.info(f"已初始化 {len(self.trainers)} 個訓練器")
            return True
            
        except ImportError as e:
            logger.error(f"訓練器模組導入失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"訓練器初始化失敗: {e}")
            return False
    
    def get_rl_agent(self, agent_name: str) -> Optional[Any]:
        """獲取RL代理"""
        agent_info = self.rl_agents.get(agent_name)
        return agent_info['wrapper'] if agent_info else None
    
    def get_all_rl_agents(self) -> List[Any]:
        """獲取所有RL代理包裝器"""
        return [info['wrapper'] for info in self.rl_agents.values()]
    
    def train_agent(self, agent_name: str, episodes: int = 1000) -> bool:
        """
        訓練RL代理
        
        Args:
            agent_name: 代理名稱
            episodes: 訓練輪數
            
        Returns:
            是否訓練成功
        """
        try:
            if agent_name not in self.trainers:
                logger.error(f"訓練器不存在: {agent_name}")
                return False
            
            trainer = self.trainers[agent_name]
            
            # 開始訓練
            training_result = trainer.train(episodes)
            
            if training_result['success']:
                logger.info(f"代理訓練成功: {agent_name}")
                return True
            else:
                logger.error(f"代理訓練失敗: {agent_name}")
                return False
                
        except Exception as e:
            logger.error(f"代理訓練失敗 {agent_name}: {e}")
            return False
    
    def make_rl_decision(self, agent_name: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用RL代理做決策
        
        Args:
            agent_name: 代理名稱
            market_data: 市場數據
            
        Returns:
            決策結果
        """
        try:
            if agent_name not in self.rl_agents:
                logger.error(f"RL代理不存在: {agent_name}")
                return self._create_no_action_decision()
            
            agent_wrapper = self.rl_agents[agent_name]['wrapper']
            
            # 轉換市場數據格式
            formatted_data = self._format_market_data_for_rl(market_data)
            
            # 獲取投資組合狀態
            portfolio_state = self._get_portfolio_state()
            
            # 做出決策
            decision = agent_wrapper.make_decision(formatted_data, portfolio_state)
            
            # 轉換為原始項目兼容格式
            legacy_decision = self._convert_rl_decision_to_legacy(decision, market_data.get('symbol', ''))
            
            return legacy_decision
            
        except Exception as e:
            logger.error(f"RL決策失敗 {agent_name}: {e}")
            return self._create_no_action_decision()
    
    def _format_market_data_for_rl(self, market_data: Dict[str, Any]) -> Any:
        """為RL代理格式化市場數據"""
        try:
            from ..agents.base import MarketData
            
            return MarketData(
                symbol=market_data.get('symbol', ''),
                current_price=market_data.get('price', 0.0),
                volume=market_data.get('volume', 0),
                data=pd.DataFrame(market_data.get('historical_data', [])),
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"RL市場數據格式化失敗: {e}")
            return None
    
    def _get_portfolio_state(self) -> Dict[str, Any]:
        """獲取投資組合狀態"""
        try:
            # 這裡應該從投資組合管理器獲取實際狀態
            return {
                'total_value': 1000000.0,
                'cash': 500000.0,
                'positions': {},
                'available_margin': 500000.0
            }
            
        except Exception as e:
            logger.error(f"獲取投資組合狀態失敗: {e}")
            return {}
    
    def _convert_rl_decision_to_legacy(self, decision: Any, symbol: str) -> Dict[str, Any]:
        """轉換RL決策為原始項目格式"""
        try:
            return {
                'symbol': symbol,
                'action': decision.action,
                'quantity': decision.quantity,
                'price': decision.price,
                'confidence': decision.confidence,
                'timestamp': datetime.now().isoformat(),
                'source': 'reinforcement_learning',
                'reasoning': decision.reasoning,
                'metadata': {
                    'agent_type': 'rl_agent',
                    'algorithm': 'ppo',
                    'training_episodes': getattr(decision, 'training_episodes', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"RL決策格式轉換失敗: {e}")
            return self._create_no_action_decision()
    
    def _create_no_action_decision(self) -> Dict[str, Any]:
        """創建無動作決策"""
        return {
            'symbol': '',
            'action': 'hold',
            'quantity': 0,
            'price': 0.0,
            'confidence': 0.0,
            'timestamp': datetime.now().isoformat(),
            'source': 'reinforcement_learning',
            'reasoning': 'RL系統錯誤或無法做出決策',
            'metadata': {'error': True}
        }
    
    def get_rl_status(self) -> Dict[str, Any]:
        """獲取RL系統狀態"""
        try:
            status = {
                'initialized': self.initialized,
                'environments': len(self.environments),
                'agents': len(self.rl_agents),
                'trainers': len(self.trainers),
                'trademaster_available': self.trademaster_integration is not None,
                'adaptive_learning_available': self.adaptive_manager is not None,
                'legacy_rl_module_available': self.legacy_rl_module is not None
            }
            
            # 獲取代理詳細狀態
            status['agent_details'] = {}
            for agent_name, agent_info in self.rl_agents.items():
                try:
                    wrapper = agent_info['wrapper']
                    agent_status = wrapper.get_agent_status()
                    status['agent_details'][agent_name] = agent_status
                except Exception as e:
                    status['agent_details'][agent_name] = {'error': str(e)}
            
            return status
            
        except Exception as e:
            logger.error(f"獲取RL狀態失敗: {e}")
            return {'error': str(e)}
    
    def health_check(self) -> bool:
        """健康檢查"""
        try:
            if not self.initialized:
                return False
            
            # 檢查環境
            if not self.environments:
                return False
            
            # 檢查代理
            if not self.rl_agents:
                return False
            
            # 檢查訓練器
            if not self.trainers:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"RL健康檢查失敗: {e}")
            return False
    
    def shutdown(self):
        """關閉RL系統"""
        try:
            logger.info("正在關閉強化學習系統...")
            
            # 關閉訓練器
            for trainer_name, trainer in self.trainers.items():
                try:
                    if hasattr(trainer, 'stop_training'):
                        trainer.stop_training()
                    logger.info(f"訓練器已關閉: {trainer_name}")
                except Exception as e:
                    logger.error(f"訓練器關閉失敗 {trainer_name}: {e}")
            
            # 關閉代理
            for agent_name, agent_info in self.rl_agents.items():
                try:
                    wrapper = agent_info['wrapper']
                    if hasattr(wrapper, 'shutdown'):
                        wrapper.shutdown()
                    logger.info(f"RL代理已關閉: {agent_name}")
                except Exception as e:
                    logger.error(f"RL代理關閉失敗 {agent_name}: {e}")
            
            # 關閉TradeMaster整合
            if self.trademaster_integration:
                try:
                    if hasattr(self.trademaster_integration, 'shutdown'):
                        self.trademaster_integration.shutdown()
                    logger.info("TradeMaster整合已關閉")
                except Exception as e:
                    logger.error(f"TradeMaster整合關閉失敗: {e}")
            
            # 清理資源
            self.rl_agents.clear()
            self.environments.clear()
            self.trainers.clear()
            
            self.initialized = False
            logger.info("強化學習系統已關閉")
            
        except Exception as e:
            logger.error(f"強化學習系統關閉失敗: {e}")
