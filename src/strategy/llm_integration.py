# -*- coding: utf-8 -*-
"""
LLM策略整合模組

此模組負責將LLM策略整合到現有的交易流程中。

主要功能：
- LLM策略與傳統策略的融合
- 多策略決策聚合
- 實時決策輔助
- 信號權重分配
- 風險評估整合
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
from dataclasses import dataclass

from .base import Strategy
from .llm.base import LLMStrategy
from ..api.llm_connector import LLMManager, LLMRequest

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class DecisionContext:
    """決策上下文"""
    market_data: pd.DataFrame
    news_data: Optional[pd.DataFrame] = None
    technical_indicators: Optional[Dict[str, Any]] = None
    risk_metrics: Optional[Dict[str, Any]] = None
    market_sentiment: Optional[str] = None
    volatility: Optional[float] = None


@dataclass
class StrategySignal:
    """策略信號"""
    strategy_name: str
    signal: int  # 1=買入, -1=賣出, 0=觀望
    confidence: float  # 0-1
    reasoning: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AggregatedDecision:
    """聚合決策"""
    final_signal: int
    confidence: float
    contributing_strategies: List[StrategySignal]
    risk_assessment: Dict[str, Any]
    execution_recommendation: str


class LLMStrategyIntegrator:
    """LLM策略整合器"""

    def __init__(
        self,
        llm_manager: LLMManager,
        traditional_strategies: Optional[List[Strategy]] = None,
        llm_strategies: Optional[List[LLMStrategy]] = None,
        integration_config: Optional[Dict[str, Any]] = None
    ):
        """初始化LLM策略整合器。

        Args:
            llm_manager: LLM管理器
            traditional_strategies: 傳統策略列表
            llm_strategies: LLM策略列表
            integration_config: 整合配置
        """
        self.llm_manager = llm_manager
        self.traditional_strategies = traditional_strategies or []
        self.llm_strategies = llm_strategies or []
        self.config = integration_config or self._get_default_config()
        
        # 策略權重
        self.strategy_weights = self.config.get('strategy_weights', {})
        
        # 決策閾值
        self.decision_threshold = self.config.get('decision_threshold', 0.6)
        
        # 風險控制參數
        self.risk_config = self.config.get('risk_control', {})

    def _get_default_config(self) -> Dict[str, Any]:
        """獲取默認配置。

        Returns:
            默認配置字典
        """
        return {
            'strategy_weights': {
                'llm_weight': 0.4,
                'technical_weight': 0.3,
                'fundamental_weight': 0.2,
                'sentiment_weight': 0.1
            },
            'decision_threshold': 0.6,
            'risk_control': {
                'max_position_size': 0.1,
                'stop_loss_threshold': 0.05,
                'volatility_adjustment': True
            },
            'signal_aggregation': {
                'method': 'weighted_average',
                'confidence_weighting': True,
                'outlier_detection': True
            }
        }

    async def generate_integrated_decision(
        self,
        context: DecisionContext,
        stock_symbol: str
    ) -> AggregatedDecision:
        """生成整合決策。

        Args:
            context: 決策上下文
            stock_symbol: 股票代碼

        Returns:
            聚合決策

        Raises:
            Exception: 當決策生成失敗時
        """
        try:
            logger.info(f"開始生成整合決策: {stock_symbol}")
            
            # 收集所有策略信號
            all_signals = []
            
            # 執行傳統策略
            traditional_signals = await self._execute_traditional_strategies(context)
            all_signals.extend(traditional_signals)
            
            # 執行LLM策略
            llm_signals = await self._execute_llm_strategies(context, stock_symbol)
            all_signals.extend(llm_signals)
            
            # 聚合信號
            aggregated_signal = self._aggregate_signals(all_signals)
            
            # 風險評估
            risk_assessment = self._assess_risk(context, aggregated_signal)
            
            # 生成執行建議
            execution_recommendation = self._generate_execution_recommendation(
                aggregated_signal, risk_assessment
            )
            
            # 構建最終決策
            decision = AggregatedDecision(
                final_signal=aggregated_signal,
                confidence=self._calculate_overall_confidence(all_signals),
                contributing_strategies=all_signals,
                risk_assessment=risk_assessment,
                execution_recommendation=execution_recommendation
            )
            
            logger.info(f"整合決策生成完成: {stock_symbol}, 信號={aggregated_signal}")
            return decision
            
        except Exception as e:
            logger.error(f"生成整合決策失敗: {e}")
            raise

    async def _execute_traditional_strategies(
        self,
        context: DecisionContext
    ) -> List[StrategySignal]:
        """執行傳統策略。

        Args:
            context: 決策上下文

        Returns:
            策略信號列表
        """
        signals = []
        
        for strategy in self.traditional_strategies:
            try:
                # 生成策略信號
                strategy_signals = strategy.generate_signals(context.market_data)
                
                if not strategy_signals.empty:
                    latest_signal = strategy_signals.iloc[-1]
                    
                    signal = StrategySignal(
                        strategy_name=strategy.name,
                        signal=int(latest_signal.get('signal', 0)),
                        confidence=float(latest_signal.get('confidence', 0.5)),
                        reasoning=f"傳統策略 {strategy.name} 分析結果",
                        metadata={
                            'strategy_type': 'traditional',
                            'indicators': latest_signal.to_dict()
                        }
                    )
                    
                    signals.append(signal)
                    
            except Exception as e:
                logger.warning(f"執行傳統策略 {strategy.name} 失敗: {e}")
        
        return signals

    async def _execute_llm_strategies(
        self,
        context: DecisionContext,
        stock_symbol: str
    ) -> List[StrategySignal]:
        """執行LLM策略。

        Args:
            context: 決策上下文
            stock_symbol: 股票代碼

        Returns:
            策略信號列表
        """
        signals = []
        
        for strategy in self.llm_strategies:
            try:
                # 準備LLM策略數據
                strategy_data = self._prepare_llm_data(context, stock_symbol)
                
                # 生成策略信號
                strategy_signals = strategy.generate_signals(strategy_data)
                
                if not strategy_signals.empty:
                    latest_signal = strategy_signals.iloc[-1]
                    
                    signal = StrategySignal(
                        strategy_name=strategy.name,
                        signal=int(latest_signal.get('signal', 0)),
                        confidence=float(latest_signal.get('confidence', 0.5)),
                        reasoning=str(latest_signal.get('reasoning', '')),
                        metadata={
                            'strategy_type': 'llm',
                            'prediction': latest_signal.get('prediction', ''),
                            'llm_output': latest_signal.get('raw_output', '')
                        }
                    )
                    
                    signals.append(signal)
                    
            except Exception as e:
                logger.warning(f"執行LLM策略 {strategy.name} 失敗: {e}")
        
        return signals

    def _prepare_llm_data(
        self,
        context: DecisionContext,
        stock_symbol: str
    ) -> pd.DataFrame:
        """準備LLM策略數據。

        Args:
            context: 決策上下文
            stock_symbol: 股票代碼

        Returns:
            準備好的數據DataFrame
        """
        # 複製市場數據
        data = context.market_data.copy()
        
        # 添加股票代碼
        data['stock_code'] = stock_symbol
        
        # 添加新聞數據
        if context.news_data is not None:
            # 合併新聞數據
            data = data.join(context.news_data, how='left')
        
        # 添加技術指標
        if context.technical_indicators:
            for indicator, values in context.technical_indicators.items():
                if isinstance(values, (list, np.ndarray, pd.Series)):
                    data[indicator] = values
        
        # 添加市場情緒
        if context.market_sentiment:
            data['market_sentiment'] = context.market_sentiment
        
        # 添加波動率
        if context.volatility:
            data['volatility'] = context.volatility
        
        return data

    def _aggregate_signals(self, signals: List[StrategySignal]) -> int:
        """聚合信號。

        Args:
            signals: 策略信號列表

        Returns:
            聚合後的信號
        """
        if not signals:
            return 0
        
        method = self.config.get('signal_aggregation', {}).get('method', 'weighted_average')
        
        if method == 'weighted_average':
            return self._weighted_average_aggregation(signals)
        elif method == 'majority_vote':
            return self._majority_vote_aggregation(signals)
        elif method == 'confidence_weighted':
            return self._confidence_weighted_aggregation(signals)
        else:
            return self._simple_average_aggregation(signals)

    def _weighted_average_aggregation(self, signals: List[StrategySignal]) -> int:
        """加權平均聚合。

        Args:
            signals: 策略信號列表

        Returns:
            聚合信號
        """
        total_weight = 0.0
        weighted_sum = 0.0
        
        for signal in signals:
            # 獲取策略權重
            weight = self._get_strategy_weight(signal.strategy_name, signal.metadata)
            
            # 考慮置信度
            if self.config.get('signal_aggregation', {}).get('confidence_weighting', True):
                weight *= signal.confidence
            
            weighted_sum += signal.signal * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0
        
        average_signal = weighted_sum / total_weight
        
        # 轉換為離散信號
        if average_signal > self.decision_threshold:
            return 1
        elif average_signal < -self.decision_threshold:
            return -1
        else:
            return 0

    def _majority_vote_aggregation(self, signals: List[StrategySignal]) -> int:
        """多數投票聚合。

        Args:
            signals: 策略信號列表

        Returns:
            聚合信號
        """
        votes = {'buy': 0, 'sell': 0, 'hold': 0}
        
        for signal in signals:
            weight = self._get_strategy_weight(signal.strategy_name, signal.metadata)
            
            if signal.signal > 0:
                votes['buy'] += weight
            elif signal.signal < 0:
                votes['sell'] += weight
            else:
                votes['hold'] += weight
        
        # 找出最高票數
        max_vote = max(votes.values())
        if votes['buy'] == max_vote:
            return 1
        elif votes['sell'] == max_vote:
            return -1
        else:
            return 0

    def _confidence_weighted_aggregation(self, signals: List[StrategySignal]) -> int:
        """置信度加權聚合。

        Args:
            signals: 策略信號列表

        Returns:
            聚合信號
        """
        total_confidence = 0.0
        weighted_sum = 0.0
        
        for signal in signals:
            confidence_weight = signal.confidence ** 2  # 平方增強高置信度信號的影響
            weighted_sum += signal.signal * confidence_weight
            total_confidence += confidence_weight
        
        if total_confidence == 0:
            return 0
        
        average_signal = weighted_sum / total_confidence
        
        # 轉換為離散信號
        if average_signal > 0.3:
            return 1
        elif average_signal < -0.3:
            return -1
        else:
            return 0

    def _simple_average_aggregation(self, signals: List[StrategySignal]) -> int:
        """簡單平均聚合。

        Args:
            signals: 策略信號列表

        Returns:
            聚合信號
        """
        if not signals:
            return 0
        
        average_signal = sum(signal.signal for signal in signals) / len(signals)
        
        if average_signal > 0.3:
            return 1
        elif average_signal < -0.3:
            return -1
        else:
            return 0

    def _get_strategy_weight(self, strategy_name: str, metadata: Optional[Dict[str, Any]]) -> float:
        """獲取策略權重。

        Args:
            strategy_name: 策略名稱
            metadata: 元數據

        Returns:
            策略權重
        """
        # 檢查是否有特定策略權重
        if strategy_name in self.strategy_weights:
            return self.strategy_weights[strategy_name]
        
        # 根據策略類型獲取權重
        if metadata and 'strategy_type' in metadata:
            strategy_type = metadata['strategy_type']
            type_weights = self.config.get('strategy_weights', {})
            
            if strategy_type == 'llm':
                return type_weights.get('llm_weight', 0.4)
            elif strategy_type == 'traditional':
                return type_weights.get('technical_weight', 0.3)
        
        # 默認權重
        return 1.0

    def _calculate_overall_confidence(self, signals: List[StrategySignal]) -> float:
        """計算整體置信度。

        Args:
            signals: 策略信號列表

        Returns:
            整體置信度
        """
        if not signals:
            return 0.0
        
        # 加權平均置信度
        total_weight = 0.0
        weighted_confidence = 0.0
        
        for signal in signals:
            weight = self._get_strategy_weight(signal.strategy_name, signal.metadata)
            weighted_confidence += signal.confidence * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        return weighted_confidence / total_weight

    def _assess_risk(
        self,
        context: DecisionContext,
        signal: int
    ) -> Dict[str, Any]:
        """評估風險。

        Args:
            context: 決策上下文
            signal: 交易信號

        Returns:
            風險評估結果
        """
        risk_assessment = {
            'overall_risk': 'medium',
            'volatility_risk': 'medium',
            'market_risk': 'medium',
            'position_size_recommendation': 0.05,
            'stop_loss_recommendation': 0.03,
            'risk_factors': []
        }
        
        # 波動率風險
        if context.volatility:
            if context.volatility > 0.3:
                risk_assessment['volatility_risk'] = 'high'
                risk_assessment['risk_factors'].append('高波動率')
                risk_assessment['position_size_recommendation'] *= 0.5
            elif context.volatility < 0.1:
                risk_assessment['volatility_risk'] = 'low'
                risk_assessment['position_size_recommendation'] *= 1.2
        
        # 市場情緒風險
        if context.market_sentiment:
            if context.market_sentiment in ['極度恐慌', '恐慌']:
                risk_assessment['market_risk'] = 'high'
                risk_assessment['risk_factors'].append('負面市場情緒')
            elif context.market_sentiment in ['極度貪婪', '貪婪']:
                risk_assessment['market_risk'] = 'high'
                risk_assessment['risk_factors'].append('過度樂觀情緒')
        
        # 綜合風險評級
        risk_factors_count = len(risk_assessment['risk_factors'])
        if risk_factors_count >= 3:
            risk_assessment['overall_risk'] = 'high'
        elif risk_factors_count <= 1:
            risk_assessment['overall_risk'] = 'low'
        
        return risk_assessment

    def _generate_execution_recommendation(
        self,
        signal: int,
        risk_assessment: Dict[str, Any]
    ) -> str:
        """生成執行建議。

        Args:
            signal: 交易信號
            risk_assessment: 風險評估

        Returns:
            執行建議
        """
        if signal == 0:
            return "建議觀望，等待更明確的信號"
        
        risk_level = risk_assessment.get('overall_risk', 'medium')
        position_size = risk_assessment.get('position_size_recommendation', 0.05)
        
        if signal == 1:  # 買入信號
            if risk_level == 'low':
                return f"建議買入，建議倉位: {position_size:.1%}"
            elif risk_level == 'medium':
                return f"謹慎買入，建議倉位: {position_size:.1%}，密切監控"
            else:
                return f"高風險環境，如買入請控制倉位在 {position_size:.1%} 以下"
        
        else:  # 賣出信號
            if risk_level == 'low':
                return f"建議賣出，建議倉位: {position_size:.1%}"
            elif risk_level == 'medium':
                return f"謹慎賣出，建議倉位: {position_size:.1%}，注意止損"
            else:
                return f"高風險環境，建議減倉或止損"

    def get_integration_status(self) -> Dict[str, Any]:
        """獲取整合狀態。

        Returns:
            整合狀態字典
        """
        return {
            'traditional_strategies_count': len(self.traditional_strategies),
            'llm_strategies_count': len(self.llm_strategies),
            'strategy_weights': self.strategy_weights,
            'decision_threshold': self.decision_threshold,
            'risk_config': self.risk_config,
            'llm_manager_status': self.llm_manager.get_status() if self.llm_manager else None
        }
