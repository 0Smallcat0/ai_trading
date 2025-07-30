# -*- coding: utf-8 -*-
"""
多代理系統整合適配器

此模組將多代理交易系統整合到原始項目中，
提供統一的代理管理和決策協調接口。

主要功能：
- 代理系統初始化和管理
- 決策協調和融合
- 投資組合管理整合
- 原始項目API適配
- 性能監控和統計

整合策略：
- 將代理決策轉換為原始項目兼容的交易信號
- 整合到原始項目的規則系統中
- 保持原始項目的交易執行流程
- 提供統一的監控和管理界面
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import numpy as np

# 設定日誌
logger = logging.getLogger(__name__)


class MultiAgentSystemAdapter:
    """
    多代理系統整合適配器
    
    將多代理交易系統整合到原始項目中
    """
    
    def __init__(self, config):
        """
        初始化多代理系統適配器
        
        Args:
            config: 整合配置
        """
        self.config = config
        self.initialized = False
        
        # 代理管理
        self.agent_manager = None
        self.active_agents = {}
        self.agent_configs = {}
        
        # 決策協調
        self.decision_coordinator = None
        self.decision_history = []
        
        # 投資組合整合
        self.portfolio_manager = None
        
        # 原始項目整合
        self.legacy_adapter = None
        
        logger.info("多代理系統適配器初始化")
    
    def initialize(self) -> bool:
        """
        初始化多代理系統
        
        Returns:
            是否初始化成功
        """
        try:
            # 初始化代理管理器
            if not self._initialize_agent_manager():
                return False
            
            # 初始化決策協調器
            if not self._initialize_decision_coordinator():
                return False
            
            # 初始化投資組合管理器
            if not self._initialize_portfolio_manager():
                return False
            
            # 設置原始項目整合
            if not self._setup_legacy_integration():
                return False
            
            # 創建默認代理
            if not self._create_default_agents():
                return False
            
            self.initialized = True
            logger.info("多代理系統初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"多代理系統初始化失敗: {e}")
            return False
    
    def _initialize_agent_manager(self) -> bool:
        """初始化代理管理器"""
        try:
            from ..agents.agent_manager import AgentManager
            from ..agents.config import AgentConfig
            
            # 創建代理管理器配置
            manager_config = {
                'max_agents': 10,
                'decision_timeout': 30,
                'coordination_method': 'weighted_voting',
                'performance_tracking': True
            }
            
            self.agent_manager = AgentManager(manager_config)
            logger.info("代理管理器初始化成功")
            return True
            
        except ImportError as e:
            logger.error(f"代理管理器模組導入失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"代理管理器初始化失敗: {e}")
            return False
    
    def _initialize_decision_coordinator(self) -> bool:
        """初始化決策協調器"""
        try:
            from ..agents.coordination.decision_coordinator import DecisionCoordinator
            from ..agents.coordination.voting_strategies import WeightedVotingStrategy
            
            # 創建投票策略
            voting_strategy = WeightedVotingStrategy()
            
            # 創建決策協調器
            self.decision_coordinator = DecisionCoordinator(
                voting_strategy=voting_strategy,
                confidence_threshold=0.6,
                consensus_required=False
            )
            
            logger.info("決策協調器初始化成功")
            return True
            
        except ImportError as e:
            logger.error(f"決策協調器模組導入失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"決策協調器初始化失敗: {e}")
            return False
    
    def _initialize_portfolio_manager(self) -> bool:
        """初始化投資組合管理器"""
        try:
            from ..portfolio.portfolio_manager import PortfolioManager
            from ..portfolio.config import PortfolioConfig
            
            # 創建投資組合配置
            portfolio_config = PortfolioConfig(
                initial_capital=1000000.0,
                max_position_size=0.1,
                risk_tolerance=0.05,
                rebalance_frequency='daily'
            )
            
            self.portfolio_manager = PortfolioManager(portfolio_config)
            logger.info("投資組合管理器初始化成功")
            return True
            
        except ImportError as e:
            logger.error(f"投資組合管理器模組導入失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"投資組合管理器初始化失敗: {e}")
            return False
    
    def _setup_legacy_integration(self) -> bool:
        """設置原始項目整合"""
        try:
            # 這裡將在後續實現與原始項目的具體整合邏輯
            logger.info("原始項目整合設置完成")
            return True
            
        except Exception as e:
            logger.error(f"原始項目整合設置失敗: {e}")
            return False
    
    def _create_default_agents(self) -> bool:
        """創建默認代理"""
        try:
            # 創建巴菲特代理
            if not self._create_buffett_agent():
                logger.warning("巴菲特代理創建失敗")
            
            # 創建索羅斯代理
            if not self._create_soros_agent():
                logger.warning("索羅斯代理創建失敗")
            
            # 創建西蒙斯代理
            if not self._create_simons_agent():
                logger.warning("西蒙斯代理創建失敗")
            
            # 創建達里奧代理
            if not self._create_dalio_agent():
                logger.warning("達里奧代理創建失敗")
            
            logger.info(f"已創建 {len(self.active_agents)} 個默認代理")
            return True
            
        except Exception as e:
            logger.error(f"默認代理創建失敗: {e}")
            return False
    
    def _create_buffett_agent(self) -> bool:
        """創建巴菲特代理"""
        try:
            from ..agents.personas.buffett_agent import BuffettAgent, BuffettConfig
            
            config = BuffettConfig(
                name="巴菲特代理",
                weight=0.3,
                min_holding_period=365,
                value_threshold=0.7,
                quality_score_threshold=0.8
            )
            
            agent = BuffettAgent(config)
            self.agent_manager.register_agent(agent)
            self.active_agents['buffett'] = agent
            
            logger.info("巴菲特代理創建成功")
            return True
            
        except Exception as e:
            logger.error(f"巴菲特代理創建失敗: {e}")
            return False
    
    def _create_soros_agent(self) -> bool:
        """創建索羅斯代理"""
        try:
            from ..agents.personas.soros_agent import SorosAgent, SorosConfig
            
            config = SorosConfig(
                name="索羅斯代理",
                weight=0.25,
                reflexivity_threshold=0.6,
                momentum_window=20,
                volatility_threshold=0.3
            )
            
            agent = SorosAgent(config)
            self.agent_manager.register_agent(agent)
            self.active_agents['soros'] = agent
            
            logger.info("索羅斯代理創建成功")
            return True
            
        except Exception as e:
            logger.error(f"索羅斯代理創建失敗: {e}")
            return False
    
    def _create_simons_agent(self) -> bool:
        """創建西蒙斯代理"""
        try:
            from ..agents.personas.simons_agent import SimonsAgent, SimonsConfig
            
            config = SimonsConfig(
                name="西蒙斯代理",
                weight=0.25,
                signal_threshold=0.65,
                lookback_period=50,
                model_update_frequency=10
            )
            
            agent = SimonsAgent(config)
            self.agent_manager.register_agent(agent)
            self.active_agents['simons'] = agent
            
            logger.info("西蒙斯代理創建成功")
            return True
            
        except Exception as e:
            logger.error(f"西蒙斯代理創建失敗: {e}")
            return False
    
    def _create_dalio_agent(self) -> bool:
        """創建達里奧代理"""
        try:
            from ..agents.personas.dalio_agent import DalioAgent, DalioConfig
            
            config = DalioConfig(
                name="達里奧代理",
                weight=0.2,
                diversification_threshold=0.8,
                risk_parity_enabled=True,
                rebalance_frequency=30
            )
            
            agent = DalioAgent(config)
            self.agent_manager.register_agent(agent)
            self.active_agents['dalio'] = agent
            
            logger.info("達里奧代理創建成功")
            return True
            
        except Exception as e:
            logger.error(f"達里奧代理創建失敗: {e}")
            return False
    
    def make_trading_decision(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        做出交易決策
        
        Args:
            symbol: 股票代碼
            market_data: 市場數據
            
        Returns:
            交易決策
        """
        try:
            if not self.initialized:
                logger.error("多代理系統未初始化")
                return self._create_no_action_decision()
            
            # 轉換市場數據格式
            formatted_data = self._format_market_data(market_data)
            
            # 獲取投資組合狀態
            portfolio_state = self.portfolio_manager.get_current_state()
            
            # 收集所有代理的決策
            agent_decisions = []
            for agent_name, agent in self.active_agents.items():
                try:
                    decision = agent.make_decision(formatted_data, portfolio_state)
                    agent_decisions.append(decision)
                    logger.debug(f"{agent_name} 決策: {decision.action}")
                except Exception as e:
                    logger.error(f"{agent_name} 決策失敗: {e}")
            
            # 協調決策
            if agent_decisions:
                final_decision = self.decision_coordinator.coordinate_decisions(agent_decisions)
                
                # 轉換為原始項目兼容格式
                legacy_decision = self._convert_to_legacy_format(final_decision, symbol)
                
                # 記錄決策歷史
                self._record_decision(symbol, agent_decisions, final_decision)
                
                return legacy_decision
            else:
                logger.warning("沒有代理提供決策")
                return self._create_no_action_decision()
                
        except Exception as e:
            logger.error(f"交易決策失敗: {e}")
            return self._create_no_action_decision()
    
    def _format_market_data(self, market_data: Dict[str, Any]) -> Any:
        """格式化市場數據"""
        try:
            # 將原始項目的市場數據格式轉換為代理系統兼容格式
            from ..agents.base import MarketData
            
            return MarketData(
                symbol=market_data.get('symbol', ''),
                current_price=market_data.get('price', 0.0),
                volume=market_data.get('volume', 0),
                data=pd.DataFrame(market_data.get('historical_data', [])),
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"市場數據格式化失敗: {e}")
            return None
    
    def _convert_to_legacy_format(self, decision: Any, symbol: str) -> Dict[str, Any]:
        """轉換為原始項目兼容格式"""
        try:
            # 轉換決策格式以兼容原始項目
            legacy_decision = {
                'symbol': symbol,
                'action': decision.action,  # buy, sell, hold
                'quantity': decision.quantity,
                'price': decision.price,
                'confidence': decision.confidence,
                'timestamp': datetime.now().isoformat(),
                'source': 'multi_agent_system',
                'reasoning': decision.reasoning,
                'metadata': {
                    'agent_count': len(self.active_agents),
                    'decision_method': 'weighted_voting',
                    'confidence_threshold': 0.6
                }
            }
            
            return legacy_decision
            
        except Exception as e:
            logger.error(f"決策格式轉換失敗: {e}")
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
            'source': 'multi_agent_system',
            'reasoning': '系統錯誤或無法做出決策',
            'metadata': {'error': True}
        }
    
    def _record_decision(self, symbol: str, agent_decisions: List[Any], final_decision: Any):
        """記錄決策歷史"""
        try:
            decision_record = {
                'timestamp': datetime.now(),
                'symbol': symbol,
                'agent_decisions': [
                    {
                        'agent': decision.metadata.get('agent_name', 'unknown'),
                        'action': decision.action,
                        'confidence': decision.confidence,
                        'reasoning': decision.reasoning
                    }
                    for decision in agent_decisions
                ],
                'final_decision': {
                    'action': final_decision.action,
                    'confidence': final_decision.confidence,
                    'reasoning': final_decision.reasoning
                }
            }
            
            self.decision_history.append(decision_record)
            
            # 保持歷史記錄在合理範圍內
            if len(self.decision_history) > 1000:
                self.decision_history = self.decision_history[-1000:]
                
        except Exception as e:
            logger.error(f"決策記錄失敗: {e}")
    
    def get_agent_status(self) -> Dict[str, Any]:
        """獲取代理狀態"""
        try:
            status = {
                'initialized': self.initialized,
                'active_agents': len(self.active_agents),
                'agent_details': {},
                'recent_decisions': len(self.decision_history),
                'system_health': 'healthy' if self.initialized else 'error'
            }
            
            # 獲取每個代理的詳細狀態
            for agent_name, agent in self.active_agents.items():
                try:
                    agent_status = agent.get_agent_status()
                    status['agent_details'][agent_name] = agent_status
                except Exception as e:
                    status['agent_details'][agent_name] = {'error': str(e)}
            
            return status
            
        except Exception as e:
            logger.error(f"獲取代理狀態失敗: {e}")
            return {'error': str(e)}
    
    def health_check(self) -> bool:
        """健康檢查"""
        try:
            if not self.initialized:
                return False
            
            # 檢查代理管理器
            if not self.agent_manager:
                return False
            
            # 檢查活躍代理
            if not self.active_agents:
                return False
            
            # 檢查決策協調器
            if not self.decision_coordinator:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"健康檢查失敗: {e}")
            return False
    
    def shutdown(self):
        """關閉多代理系統"""
        try:
            logger.info("正在關閉多代理系統...")
            
            # 關閉所有代理
            for agent_name, agent in self.active_agents.items():
                try:
                    if hasattr(agent, 'shutdown'):
                        agent.shutdown()
                    logger.info(f"代理已關閉: {agent_name}")
                except Exception as e:
                    logger.error(f"代理關閉失敗 {agent_name}: {e}")
            
            # 清理資源
            self.active_agents.clear()
            self.decision_history.clear()
            
            self.initialized = False
            logger.info("多代理系統已關閉")
            
        except Exception as e:
            logger.error(f"多代理系統關閉失敗: {e}")
