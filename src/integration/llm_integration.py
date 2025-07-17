# -*- coding: utf-8 -*-
"""
LLM策略整合模組

此模組實現現有LLM策略與多代理系統的無縫整合，
提供統一的策略協調和執行機制。

核心功能：
- LLM策略與多代理決策的協調
- 策略權重動態調整
- 決策融合和衝突解決
- 性能監控和優化
- 策略學習和適應

整合架構：
- LLM策略作為特殊代理參與決策
- 多代理協調機制統一管理
- 動態權重基於策略績效調整
- 實時監控和反饋優化
"""

import logging
import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# 導入現有LLM策略
from ..strategy.llm_integration import LLMStrategy
from ..strategy.llm_strategies import (
    TrendFollowingStrategy,
    MeanReversionStrategy,
    BreakoutStrategy,
    SentimentStrategy,
    MacroEconomicStrategy
)

# 導入多代理系統
from ..agents.base import TradingAgent, AgentDecision
from ..coordination import DecisionCoordinator, CoordinatedDecision

# 設定日誌
logger = logging.getLogger(__name__)


class LLMIntegrationMode(Enum):
    """LLM整合模式枚舉"""
    PARALLEL = "parallel"           # 並行模式：LLM策略與代理並行決策
    HIERARCHICAL = "hierarchical"   # 階層模式：LLM策略作為上層決策
    COLLABORATIVE = "collaborative" # 協作模式：LLM策略參與協作決策
    ADVISORY = "advisory"           # 顧問模式：LLM策略提供建議
    HYBRID = "hybrid"               # 混合模式：根據情況動態選擇


@dataclass
class LLMStrategyWrapper:
    """LLM策略包裝器"""
    strategy_name: str
    strategy_instance: Any
    weight: float = 1.0
    performance_history: List[float] = None
    last_decision: Optional[Dict[str, Any]] = None
    is_active: bool = True
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.performance_history is None:
            self.performance_history = []
        if self.metadata is None:
            self.metadata = {}


class LLMAgentAdapter(TradingAgent):
    """
    LLM策略代理適配器 - 將LLM策略包裝為代理。
    
    使LLM策略能夠參與多代理協作決策流程。
    """
    
    def __init__(
        self,
        llm_strategy: Any,
        strategy_name: str,
        agent_id: Optional[str] = None
    ) -> None:
        """
        初始化LLM策略代理適配器。
        
        Args:
            llm_strategy: LLM策略實例
            strategy_name: 策略名稱
            agent_id: 代理ID
        """
        super().__init__(
            agent_id=agent_id or f"llm_{strategy_name}",
            name=f"LLM_{strategy_name}",
            investment_style=self._infer_investment_style(strategy_name),
            risk_preference=self._infer_risk_preference(strategy_name)
        )
        
        self.llm_strategy = llm_strategy
        self.strategy_name = strategy_name
        self.decision_history: List[AgentDecision] = []
        
        logger.info(f"創建LLM策略代理適配器: {strategy_name}")
    
    def _infer_investment_style(self, strategy_name: str):
        """推斷投資風格"""
        from ..agents.base import InvestmentStyle
        
        style_mapping = {
            'trend_following': InvestmentStyle.TECHNICAL,
            'mean_reversion': InvestmentStyle.VALUE,
            'breakout': InvestmentStyle.TECHNICAL,
            'sentiment': InvestmentStyle.ARBITRAGE,
            'macro_economic': InvestmentStyle.RISK_PARITY
        }
        
        return style_mapping.get(strategy_name.lower(), InvestmentStyle.TECHNICAL)
    
    def _infer_risk_preference(self, strategy_name: str):
        """推斷風險偏好"""
        from ..agents.base import RiskPreference
        
        risk_mapping = {
            'trend_following': RiskPreference.MODERATE,
            'mean_reversion': RiskPreference.CONSERVATIVE,
            'breakout': RiskPreference.AGGRESSIVE,
            'sentiment': RiskPreference.MODERATE,
            'macro_economic': RiskPreference.CONSERVATIVE
        }
        
        return risk_mapping.get(strategy_name.lower(), RiskPreference.MODERATE)
    
    def make_decision(
        self,
        data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]] = None
    ) -> AgentDecision:
        """
        生成投資決策。
        
        Args:
            data: 市場數據
            market_context: 市場上下文
            
        Returns:
            AgentDecision: 投資決策
        """
        try:
            # 調用LLM策略生成決策
            llm_decision = self.llm_strategy.generate_decision(data, market_context)
            
            # 轉換為AgentDecision格式
            agent_decision = self._convert_llm_decision(llm_decision, market_context)
            
            # 記錄決策歷史
            self.decision_history.append(agent_decision)
            
            # 保持歷史記錄在合理範圍內
            if len(self.decision_history) > 1000:
                self.decision_history = self.decision_history[-500:]
            
            return agent_decision
            
        except Exception as e:
            logger.error(f"LLM策略 {self.strategy_name} 決策生成失敗: {e}")
            return self._create_neutral_decision(market_context)
    
    def _convert_llm_decision(
        self,
        llm_decision: Dict[str, Any],
        market_context: Optional[Dict[str, Any]]
    ) -> AgentDecision:
        """轉換LLM決策為AgentDecision格式"""
        
        symbol = market_context.get('symbol', 'UNKNOWN') if market_context else 'UNKNOWN'
        
        # 提取決策信息
        action = llm_decision.get('action', 0)  # -1, 0, 1
        confidence = llm_decision.get('confidence', 0.5)
        reasoning = llm_decision.get('reasoning', f"LLM策略 {self.strategy_name} 決策")
        expected_return = llm_decision.get('expected_return', 0.0)
        risk_assessment = llm_decision.get('risk_assessment', 0.5)
        position_size = llm_decision.get('position_size', 0.1)
        
        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=datetime.now(),
            symbol=symbol,
            action=action,
            confidence=confidence,
            reasoning=reasoning,
            expected_return=expected_return,
            risk_assessment=risk_assessment,
            position_size=position_size,
            metadata={
                'strategy_name': self.strategy_name,
                'llm_decision': llm_decision,
                'adapter_version': '1.0'
            }
        )
    
    def _create_neutral_decision(self, market_context: Optional[Dict[str, Any]]) -> AgentDecision:
        """創建中性決策"""
        symbol = market_context.get('symbol', 'UNKNOWN') if market_context else 'UNKNOWN'
        
        return AgentDecision(
            agent_id=self.agent_id,
            timestamp=datetime.now(),
            symbol=symbol,
            action=0,
            confidence=0.5,
            reasoning=f"LLM策略 {self.strategy_name} 決策失敗，保持中性",
            expected_return=0.0,
            risk_assessment=0.5,
            position_size=0.0
        )
    
    def get_performance_metrics(self) -> Dict[str, float]:
        """獲取績效指標"""
        if not self.decision_history:
            return {}
        
        # 計算基本績效指標
        decisions = self.decision_history[-100:]  # 最近100個決策
        
        total_decisions = len(decisions)
        buy_decisions = sum(1 for d in decisions if d.action == 1)
        sell_decisions = sum(1 for d in decisions if d.action == -1)
        hold_decisions = sum(1 for d in decisions if d.action == 0)
        
        avg_confidence = np.mean([d.confidence for d in decisions])
        avg_expected_return = np.mean([d.expected_return for d in decisions])
        avg_risk_assessment = np.mean([d.risk_assessment for d in decisions])
        
        return {
            'total_decisions': total_decisions,
            'buy_ratio': buy_decisions / total_decisions if total_decisions > 0 else 0,
            'sell_ratio': sell_decisions / total_decisions if total_decisions > 0 else 0,
            'hold_ratio': hold_decisions / total_decisions if total_decisions > 0 else 0,
            'avg_confidence': avg_confidence,
            'avg_expected_return': avg_expected_return,
            'avg_risk_assessment': avg_risk_assessment
        }


class LLMIntegration:
    """
    LLM策略整合器 - 整合現有LLM策略與多代理系統。
    
    提供統一的策略管理、決策協調和性能優化機制。
    
    Attributes:
        integration_mode (LLMIntegrationMode): 整合模式
        llm_strategies (Dict[str, LLMStrategyWrapper]): LLM策略集合
        llm_agents (Dict[str, LLMAgentAdapter]): LLM代理適配器集合
        decision_coordinator (DecisionCoordinator): 決策協調器
    """
    
    def __init__(
        self,
        integration_mode: LLMIntegrationMode = LLMIntegrationMode.COLLABORATIVE,
        enable_auto_weight_adjustment: bool = True,
        performance_window: int = 50
    ) -> None:
        """
        初始化LLM策略整合器。
        
        Args:
            integration_mode: 整合模式
            enable_auto_weight_adjustment: 是否啟用自動權重調整
            performance_window: 績效評估窗口
        """
        self.integration_mode = integration_mode
        self.enable_auto_weight_adjustment = enable_auto_weight_adjustment
        self.performance_window = performance_window
        
        # LLM策略管理
        self.llm_strategies: Dict[str, LLMStrategyWrapper] = {}
        self.llm_agents: Dict[str, LLMAgentAdapter] = {}
        
        # 決策協調
        self.decision_coordinator: Optional[DecisionCoordinator] = None
        
        # 性能追蹤
        self.performance_history: Dict[str, List[float]] = {}
        self.integration_stats = {
            'total_integrations': 0,
            'successful_decisions': 0,
            'failed_decisions': 0,
            'avg_decision_time': 0.0,
            'strategy_weights': {}
        }
        
        logger.info(f"初始化LLM策略整合器: {integration_mode.value}")
    
    def register_llm_strategy(
        self,
        strategy_name: str,
        strategy_instance: Any,
        initial_weight: float = 1.0
    ) -> bool:
        """
        註冊LLM策略。
        
        Args:
            strategy_name: 策略名稱
            strategy_instance: 策略實例
            initial_weight: 初始權重
            
        Returns:
            bool: 註冊是否成功
        """
        try:
            # 創建策略包裝器
            wrapper = LLMStrategyWrapper(
                strategy_name=strategy_name,
                strategy_instance=strategy_instance,
                weight=initial_weight
            )
            
            # 創建代理適配器
            adapter = LLMAgentAdapter(
                llm_strategy=strategy_instance,
                strategy_name=strategy_name
            )
            
            # 註冊策略和代理
            self.llm_strategies[strategy_name] = wrapper
            self.llm_agents[strategy_name] = adapter
            
            # 初始化性能歷史
            self.performance_history[strategy_name] = []
            
            logger.info(f"註冊LLM策略: {strategy_name}")
            return True
            
        except Exception as e:
            logger.error(f"註冊LLM策略失敗 {strategy_name}: {e}")
            return False

    def unregister_llm_strategy(self, strategy_name: str) -> bool:
        """
        取消註冊LLM策略。

        Args:
            strategy_name: 策略名稱

        Returns:
            bool: 取消註冊是否成功
        """
        try:
            if strategy_name in self.llm_strategies:
                del self.llm_strategies[strategy_name]

            if strategy_name in self.llm_agents:
                del self.llm_agents[strategy_name]

            if strategy_name in self.performance_history:
                del self.performance_history[strategy_name]

            logger.info(f"取消註冊LLM策略: {strategy_name}")
            return True

        except Exception as e:
            logger.error(f"取消註冊LLM策略失敗 {strategy_name}: {e}")
            return False

    def set_decision_coordinator(self, coordinator: DecisionCoordinator) -> None:
        """設置決策協調器"""
        self.decision_coordinator = coordinator
        logger.info("設置決策協調器")

    async def generate_integrated_decision(
        self,
        symbol: str,
        market_data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]] = None,
        multi_agent_decisions: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        生成整合決策。

        Args:
            symbol: 交易標的
            market_data: 市場數據
            market_context: 市場上下文
            multi_agent_decisions: 多代理決策

        Returns:
            Dict[str, Any]: 整合決策結果
        """
        try:
            start_time = datetime.now()

            # 1. 收集LLM策略決策
            llm_decisions = await self._collect_llm_decisions(
                symbol, market_data, market_context
            )

            # 2. 根據整合模式處理決策
            if self.integration_mode == LLMIntegrationMode.PARALLEL:
                result = await self._parallel_integration(
                    llm_decisions, multi_agent_decisions
                )
            elif self.integration_mode == LLMIntegrationMode.HIERARCHICAL:
                result = await self._hierarchical_integration(
                    llm_decisions, multi_agent_decisions
                )
            elif self.integration_mode == LLMIntegrationMode.COLLABORATIVE:
                result = await self._collaborative_integration(
                    llm_decisions, multi_agent_decisions
                )
            elif self.integration_mode == LLMIntegrationMode.ADVISORY:
                result = await self._advisory_integration(
                    llm_decisions, multi_agent_decisions
                )
            else:  # HYBRID
                result = await self._hybrid_integration(
                    llm_decisions, multi_agent_decisions
                )

            # 3. 更新統計
            decision_time = (datetime.now() - start_time).total_seconds()
            self._update_integration_stats(decision_time, True)

            # 4. 更新策略權重
            if self.enable_auto_weight_adjustment:
                await self._update_strategy_weights(result)

            return result

        except Exception as e:
            logger.error(f"生成整合決策失敗 {symbol}: {e}")
            self._update_integration_stats(0, False)
            return {
                'symbol': symbol,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def _collect_llm_decisions(
        self,
        symbol: str,
        market_data: pd.DataFrame,
        market_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """收集LLM策略決策"""
        llm_decisions = {}

        for strategy_name, wrapper in self.llm_strategies.items():
            if not wrapper.is_active:
                continue

            try:
                # 使用代理適配器生成決策
                agent = self.llm_agents[strategy_name]
                decision = agent.make_decision(market_data, market_context)

                llm_decisions[strategy_name] = {
                    'decision': decision,
                    'weight': wrapper.weight,
                    'strategy_type': strategy_name
                }

                # 更新包裝器
                wrapper.last_decision = decision.__dict__

            except Exception as e:
                logger.warning(f"LLM策略 {strategy_name} 決策失敗: {e}")

        return llm_decisions

    async def _parallel_integration(
        self,
        llm_decisions: Dict[str, Any],
        multi_agent_decisions: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """並行整合模式"""
        # LLM策略和多代理決策並行，最後統一協調

        all_decisions = {}

        # 添加LLM決策
        for strategy_name, decision_info in llm_decisions.items():
            all_decisions[f"llm_{strategy_name}"] = decision_info['decision']

        # 添加多代理決策
        if multi_agent_decisions:
            all_decisions.update(multi_agent_decisions)

        # 使用決策協調器統一協調
        if self.decision_coordinator and all_decisions:
            coordinated = self.decision_coordinator.coordinate_decisions(
                all_decisions, list(all_decisions.keys())[0]
            )

            return {
                'integration_mode': 'parallel',
                'coordinated_decision': coordinated,
                'llm_decisions': len(llm_decisions),
                'agent_decisions': len(multi_agent_decisions) if multi_agent_decisions else 0,
                'final_action': coordinated.final_action,
                'final_confidence': coordinated.final_confidence
            }

        return {
            'integration_mode': 'parallel',
            'error': 'No valid decisions to coordinate'
        }

    async def _hierarchical_integration(
        self,
        llm_decisions: Dict[str, Any],
        multi_agent_decisions: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """階層整合模式"""
        # LLM策略作為上層決策，多代理決策作為下層參考

        # 1. 首先協調LLM策略決策
        llm_only_decisions = {
            name: info['decision'] for name, info in llm_decisions.items()
        }

        llm_coordinated = None
        if self.decision_coordinator and llm_only_decisions:
            llm_coordinated = self.decision_coordinator.coordinate_decisions(
                llm_only_decisions, list(llm_only_decisions.keys())[0]
            )

        # 2. 如果LLM決策信心度不足，參考多代理決策
        if (llm_coordinated and llm_coordinated.final_confidence < 0.7 and
            multi_agent_decisions):

            # 結合多代理決策進行二次協調
            combined_decisions = llm_only_decisions.copy()
            combined_decisions.update(multi_agent_decisions)

            final_coordinated = self.decision_coordinator.coordinate_decisions(
                combined_decisions, list(combined_decisions.keys())[0]
            )

            return {
                'integration_mode': 'hierarchical',
                'llm_coordinated': llm_coordinated,
                'final_coordinated': final_coordinated,
                'used_agent_backup': True,
                'final_action': final_coordinated.final_action,
                'final_confidence': final_coordinated.final_confidence
            }

        return {
            'integration_mode': 'hierarchical',
            'llm_coordinated': llm_coordinated,
            'used_agent_backup': False,
            'final_action': llm_coordinated.final_action if llm_coordinated else 0,
            'final_confidence': llm_coordinated.final_confidence if llm_coordinated else 0.5
        }

    async def _collaborative_integration(
        self,
        llm_decisions: Dict[str, Any],
        multi_agent_decisions: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """協作整合模式"""
        # LLM策略和多代理平等參與協作決策

        # 將LLM策略決策轉換為標準格式
        collaborative_decisions = {}

        for strategy_name, decision_info in llm_decisions.items():
            collaborative_decisions[f"llm_{strategy_name}"] = decision_info['decision']

        # 添加多代理決策
        if multi_agent_decisions:
            collaborative_decisions.update(multi_agent_decisions)

        # 應用策略權重
        weighted_decisions = {}
        for name, decision in collaborative_decisions.items():
            if name.startswith('llm_'):
                strategy_name = name[4:]  # 移除'llm_'前綴
                if strategy_name in self.llm_strategies:
                    weight = self.llm_strategies[strategy_name].weight
                    weighted_decisions[name] = decision
                    # 這裡可以根據權重調整決策的影響力
            else:
                weighted_decisions[name] = decision

        # 協調決策
        if self.decision_coordinator and weighted_decisions:
            coordinated = self.decision_coordinator.coordinate_decisions(
                weighted_decisions, list(weighted_decisions.keys())[0]
            )

            return {
                'integration_mode': 'collaborative',
                'coordinated_decision': coordinated,
                'total_participants': len(weighted_decisions),
                'llm_participants': len(llm_decisions),
                'agent_participants': len(multi_agent_decisions) if multi_agent_decisions else 0,
                'final_action': coordinated.final_action,
                'final_confidence': coordinated.final_confidence
            }

        return {
            'integration_mode': 'collaborative',
            'error': 'No valid decisions to coordinate'
        }

    async def _advisory_integration(
        self,
        llm_decisions: Dict[str, Any],
        multi_agent_decisions: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """顧問整合模式"""
        # LLM策略提供建議，多代理決策為主

        # 1. 首先協調多代理決策
        agent_coordinated = None
        if self.decision_coordinator and multi_agent_decisions:
            agent_coordinated = self.decision_coordinator.coordinate_decisions(
                multi_agent_decisions, list(multi_agent_decisions.keys())[0]
            )

        # 2. LLM策略提供建議和風險評估
        llm_advice = {}
        for strategy_name, decision_info in llm_decisions.items():
            decision = decision_info['decision']
            llm_advice[strategy_name] = {
                'recommended_action': decision.action,
                'confidence': decision.confidence,
                'risk_assessment': decision.risk_assessment,
                'reasoning': decision.reasoning
            }

        # 3. 基於LLM建議調整最終決策
        final_action = agent_coordinated.final_action if agent_coordinated else 0
        final_confidence = agent_coordinated.final_confidence if agent_coordinated else 0.5

        # 如果LLM策略普遍不同意，降低信心度
        if llm_advice:
            llm_actions = [advice['recommended_action'] for advice in llm_advice.values()]
            llm_avg_action = np.mean(llm_actions)

            if abs(llm_avg_action - final_action) > 0.5:  # 意見分歧較大
                final_confidence *= 0.8  # 降低信心度

        return {
            'integration_mode': 'advisory',
            'agent_coordinated': agent_coordinated,
            'llm_advice': llm_advice,
            'final_action': final_action,
            'final_confidence': final_confidence,
            'advice_applied': len(llm_advice) > 0
        }

    async def _hybrid_integration(
        self,
        llm_decisions: Dict[str, Any],
        multi_agent_decisions: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """混合整合模式"""
        # 根據市場條件和決策質量動態選擇整合模式

        # 評估決策質量
        llm_quality = self._assess_llm_decision_quality(llm_decisions)
        agent_quality = self._assess_agent_decision_quality(multi_agent_decisions)

        # 根據質量選擇模式
        if llm_quality > 0.8 and agent_quality < 0.6:
            # LLM策略質量高，使用階層模式
            return await self._hierarchical_integration(llm_decisions, multi_agent_decisions)
        elif agent_quality > 0.8 and llm_quality < 0.6:
            # 多代理質量高，使用顧問模式
            return await self._advisory_integration(llm_decisions, multi_agent_decisions)
        elif abs(llm_quality - agent_quality) < 0.2:
            # 質量相近，使用協作模式
            return await self._collaborative_integration(llm_decisions, multi_agent_decisions)
        else:
            # 默認使用並行模式
            return await self._parallel_integration(llm_decisions, multi_agent_decisions)

    def _assess_llm_decision_quality(self, llm_decisions: Dict[str, Any]) -> float:
        """評估LLM決策質量"""
        if not llm_decisions:
            return 0.0

        total_quality = 0.0
        for decision_info in llm_decisions.values():
            decision = decision_info['decision']

            # 基於信心度、一致性等評估質量
            confidence_score = decision.confidence

            # 檢查決策的合理性
            reasonableness_score = 1.0
            if abs(decision.action) > 1 or decision.confidence < 0 or decision.confidence > 1:
                reasonableness_score = 0.0

            # 綜合評分
            quality = (confidence_score + reasonableness_score) / 2
            total_quality += quality

        return total_quality / len(llm_decisions)

    def _assess_agent_decision_quality(self, multi_agent_decisions: Optional[Dict[str, Any]]) -> float:
        """評估多代理決策質量"""
        if not multi_agent_decisions:
            return 0.0

        total_quality = 0.0
        for decision in multi_agent_decisions.values():
            # 類似的質量評估邏輯
            confidence_score = getattr(decision, 'confidence', 0.5)
            reasonableness_score = 1.0

            if hasattr(decision, 'action'):
                if abs(decision.action) > 1:
                    reasonableness_score = 0.0

            quality = (confidence_score + reasonableness_score) / 2
            total_quality += quality

        return total_quality / len(multi_agent_decisions)

    async def _update_strategy_weights(self, integration_result: Dict[str, Any]) -> None:
        """更新策略權重"""
        try:
            # 基於整合結果的成功程度調整權重
            success_indicator = integration_result.get('final_confidence', 0.5)

            for strategy_name, wrapper in self.llm_strategies.items():
                # 記錄績效
                self.performance_history[strategy_name].append(success_indicator)

                # 保持歷史記錄在合理範圍內
                if len(self.performance_history[strategy_name]) > self.performance_window:
                    self.performance_history[strategy_name] = \
                        self.performance_history[strategy_name][-self.performance_window:]

                # 計算新權重
                recent_performance = self.performance_history[strategy_name][-10:]  # 最近10次
                avg_performance = np.mean(recent_performance) if recent_performance else 0.5

                # 權重調整（簡化版本）
                new_weight = max(0.1, min(2.0, avg_performance * 2))
                wrapper.weight = new_weight

                logger.debug(f"更新策略 {strategy_name} 權重: {new_weight:.3f}")

        except Exception as e:
            logger.error(f"更新策略權重失敗: {e}")

    def _update_integration_stats(self, decision_time: float, success: bool) -> None:
        """更新整合統計"""
        self.integration_stats['total_integrations'] += 1

        if success:
            self.integration_stats['successful_decisions'] += 1
        else:
            self.integration_stats['failed_decisions'] += 1

        # 更新平均決策時間
        total_integrations = self.integration_stats['total_integrations']
        current_avg = self.integration_stats['avg_decision_time']
        self.integration_stats['avg_decision_time'] = (
            (current_avg * (total_integrations - 1) + decision_time) / total_integrations
        )

        # 更新策略權重統計
        self.integration_stats['strategy_weights'] = {
            name: wrapper.weight for name, wrapper in self.llm_strategies.items()
        }

    def get_integration_status(self) -> Dict[str, Any]:
        """獲取整合狀態"""
        return {
            'integration_mode': self.integration_mode.value,
            'registered_strategies': list(self.llm_strategies.keys()),
            'active_strategies': [
                name for name, wrapper in self.llm_strategies.items()
                if wrapper.is_active
            ],
            'strategy_weights': {
                name: wrapper.weight for name, wrapper in self.llm_strategies.items()
            },
            'performance_history_length': {
                name: len(history) for name, history in self.performance_history.items()
            },
            'integration_stats': self.integration_stats,
            'auto_weight_adjustment': self.enable_auto_weight_adjustment
        }

    def get_strategy_performance(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """獲取策略績效"""
        if strategy_name not in self.llm_strategies:
            return None

        wrapper = self.llm_strategies[strategy_name]
        agent = self.llm_agents[strategy_name]

        return {
            'strategy_name': strategy_name,
            'current_weight': wrapper.weight,
            'is_active': wrapper.is_active,
            'performance_history': self.performance_history[strategy_name],
            'agent_metrics': agent.get_performance_metrics(),
            'last_decision': wrapper.last_decision,
            'metadata': wrapper.metadata
        }

    def set_strategy_weight(self, strategy_name: str, weight: float) -> bool:
        """手動設置策略權重"""
        if strategy_name not in self.llm_strategies:
            logger.error(f"策略 {strategy_name} 不存在")
            return False

        try:
            self.llm_strategies[strategy_name].weight = max(0.0, weight)
            logger.info(f"設置策略 {strategy_name} 權重為 {weight}")
            return True
        except Exception as e:
            logger.error(f"設置策略權重失敗: {e}")
            return False

    def activate_strategy(self, strategy_name: str) -> bool:
        """激活策略"""
        if strategy_name not in self.llm_strategies:
            return False

        self.llm_strategies[strategy_name].is_active = True
        logger.info(f"激活策略: {strategy_name}")
        return True

    def deactivate_strategy(self, strategy_name: str) -> bool:
        """停用策略"""
        if strategy_name not in self.llm_strategies:
            return False

        self.llm_strategies[strategy_name].is_active = False
        logger.info(f"停用策略: {strategy_name}")
        return True

    def clear_performance_history(self, strategy_name: Optional[str] = None) -> None:
        """清除績效歷史"""
        if strategy_name:
            if strategy_name in self.performance_history:
                self.performance_history[strategy_name].clear()
                logger.info(f"清除策略 {strategy_name} 績效歷史")
        else:
            for history in self.performance_history.values():
                history.clear()
            logger.info("清除所有策略績效歷史")

    async def initialize_default_strategies(self) -> None:
        """初始化默認LLM策略"""
        try:
            # 創建默認策略實例
            default_strategies = {
                'trend_following': TrendFollowingStrategy(),
                'mean_reversion': MeanReversionStrategy(),
                'breakout': BreakoutStrategy(),
                'sentiment': SentimentStrategy(),
                'macro_economic': MacroEconomicStrategy()
            }

            # 註冊策略
            for name, strategy in default_strategies.items():
                success = self.register_llm_strategy(name, strategy)
                if success:
                    logger.info(f"初始化默認策略: {name}")
                else:
                    logger.warning(f"初始化默認策略失敗: {name}")

            logger.info("默認LLM策略初始化完成")

        except Exception as e:
            logger.error(f"初始化默認策略失敗: {e}")

    def __str__(self) -> str:
        """字符串表示"""
        return (f"LLMIntegration(mode={self.integration_mode.value}, "
                f"strategies={len(self.llm_strategies)}, "
                f"active={len([w for w in self.llm_strategies.values() if w.is_active])})")
