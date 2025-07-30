# -*- coding: utf-8 -*-
"""
投資組合管理整合模組

此模組實現現有投資組合管理系統與多代理協作機制的整合，
提供統一的投資組合管理和優化功能。

核心功能：
- 投資組合管理系統與多代理決策的整合
- 統一的資產配置和再平衡機制
- 多層次風險管理和控制
- 實時績效監控和優化
- 動態投資組合調整

整合架構：
- 多代理決策輸入投資組合管理
- 協調決策轉換為具體配置
- 風險管理約束和優化
- 實時監控和調整機制
"""

import logging
import asyncio
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

# 導入現有投資組合管理
from ..portfolio import PortfolioManager, Portfolio, Position
from ..portfolio.optimization import PortfolioOptimizer
from ..portfolio.rebalancing import RebalancingEngine

# 導入多代理協作組件
from ..coordination import PortfolioAllocator, PortfolioAllocation, AssetAllocation
from ..coordination.decision_coordinator import CoordinatedDecision

# 設定日誌
logger = logging.getLogger(__name__)


class IntegrationMode(Enum):
    """整合模式枚舉"""
    OVERRIDE = "override"           # 覆蓋模式：多代理決策完全覆蓋現有配置
    BLEND = "blend"                 # 混合模式：多代理決策與現有配置混合
    ADVISORY = "advisory"           # 顧問模式：多代理決策作為建議
    CONSTRAINT = "constraint"       # 約束模式：多代理決策作為約束條件
    ADAPTIVE = "adaptive"           # 自適應模式：根據績效動態調整


@dataclass
class IntegrationConfig:
    """整合配置"""
    mode: IntegrationMode = IntegrationMode.BLEND
    blend_ratio: float = 0.5                    # 混合比例
    rebalance_threshold: float = 0.05           # 再平衡閾值
    max_position_change: float = 0.1            # 最大倉位變化
    risk_budget_utilization: float = 0.8       # 風險預算利用率
    performance_lookback: int = 30              # 績效回看期間
    enable_auto_rebalance: bool = True          # 是否啟用自動再平衡
    enable_risk_override: bool = True           # 是否啟用風險覆蓋


@dataclass
class IntegrationMetrics:
    """整合指標"""
    total_integrations: int = 0
    successful_integrations: int = 0
    rebalance_count: int = 0
    avg_integration_time: float = 0.0
    portfolio_value_change: float = 0.0
    risk_adjusted_return: float = 0.0
    tracking_error: float = 0.0
    information_ratio: float = 0.0
    last_update: datetime = None


class PortfolioIntegration:
    """
    投資組合管理整合器 - 整合現有投資組合管理與多代理協作。
    
    提供統一的投資組合管理、資產配置和風險控制機制。
    
    Attributes:
        portfolio_manager (PortfolioManager): 投資組合管理器
        portfolio_allocator (PortfolioAllocator): 多代理投資組合分配器
        optimizer (PortfolioOptimizer): 投資組合優化器
        rebalancing_engine (RebalancingEngine): 再平衡引擎
        config (IntegrationConfig): 整合配置
    """
    
    def __init__(
        self,
        portfolio_manager: PortfolioManager,
        portfolio_allocator: Optional[PortfolioAllocator] = None,
        config: Optional[IntegrationConfig] = None
    ) -> None:
        """
        初始化投資組合管理整合器。
        
        Args:
            portfolio_manager: 現有投資組合管理器
            portfolio_allocator: 多代理投資組合分配器
            config: 整合配置
        """
        self.portfolio_manager = portfolio_manager
        self.portfolio_allocator = portfolio_allocator or PortfolioAllocator()
        self.config = config or IntegrationConfig()
        
        # 創建優化器和再平衡引擎
        self.optimizer = PortfolioOptimizer()
        self.rebalancing_engine = RebalancingEngine()
        
        # 整合狀態
        self.integration_metrics = IntegrationMetrics()
        self.last_allocation: Optional[PortfolioAllocation] = None
        self.allocation_history: List[PortfolioAllocation] = []
        
        # 績效追蹤
        self.performance_history: List[Dict[str, float]] = []
        self.benchmark_returns: List[float] = []
        
        # 風險管理
        self.risk_limits = {
            'max_position_size': 0.2,
            'max_sector_exposure': 0.3,
            'max_volatility': 0.15,
            'max_drawdown': 0.1
        }
        
        logger.info("初始化投資組合管理整合器")
    
    async def integrate_portfolio_decisions(
        self,
        coordinated_decisions: Dict[str, CoordinatedDecision],
        market_data: Optional[Dict[str, pd.DataFrame]] = None,
        force_rebalance: bool = False
    ) -> Dict[str, Any]:
        """
        整合投資組合決策。
        
        Args:
            coordinated_decisions: 協調後的投資決策
            market_data: 市場數據
            force_rebalance: 是否強制再平衡
            
        Returns:
            Dict[str, Any]: 整合結果
        """
        try:
            start_time = datetime.now()
            logger.info("開始整合投資組合決策...")
            
            # 1. 生成多代理投資組合配置
            multi_agent_allocation = await self._generate_multi_agent_allocation(
                coordinated_decisions, market_data
            )
            
            # 2. 獲取當前投資組合狀態
            current_portfolio = self.portfolio_manager.get_portfolio()
            
            # 3. 根據整合模式處理配置
            integrated_allocation = await self._integrate_allocations(
                multi_agent_allocation, current_portfolio
            )
            
            # 4. 風險檢查和約束
            risk_adjusted_allocation = await self._apply_risk_constraints(
                integrated_allocation
            )
            
            # 5. 優化配置
            optimized_allocation = await self._optimize_allocation(
                risk_adjusted_allocation, market_data
            )
            
            # 6. 檢查是否需要再平衡
            rebalance_needed = await self._check_rebalance_need(
                optimized_allocation, current_portfolio, force_rebalance
            )
            
            # 7. 執行再平衡（如果需要）
            execution_result = None
            if rebalance_needed:
                execution_result = await self._execute_rebalance(
                    optimized_allocation, current_portfolio
                )
            
            # 8. 更新統計和歷史
            integration_time = (datetime.now() - start_time).total_seconds()
            await self._update_integration_metrics(
                integration_time, execution_result is not None
            )
            
            # 9. 記錄配置歷史
            self.last_allocation = optimized_allocation
            self.allocation_history.append(optimized_allocation)
            
            # 保持歷史記錄在合理範圍內
            if len(self.allocation_history) > 1000:
                self.allocation_history = self.allocation_history[-500:]
            
            result = {
                'integration_mode': self.config.mode.value,
                'multi_agent_allocation': multi_agent_allocation,
                'integrated_allocation': integrated_allocation,
                'optimized_allocation': optimized_allocation,
                'rebalance_needed': rebalance_needed,
                'execution_result': execution_result,
                'integration_time': integration_time,
                'portfolio_value': current_portfolio.total_value if current_portfolio else 0,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info("投資組合決策整合完成")
            return result
            
        except Exception as e:
            logger.error(f"投資組合決策整合失敗: {e}")
            await self._update_integration_metrics(0, False)
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _generate_multi_agent_allocation(
        self,
        coordinated_decisions: Dict[str, CoordinatedDecision],
        market_data: Optional[Dict[str, pd.DataFrame]]
    ) -> PortfolioAllocation:
        """生成多代理投資組合配置"""
        try:
            # 使用多代理投資組合分配器生成配置
            allocation = self.portfolio_allocator.allocate_portfolio(
                coordinated_decisions, market_data
            )
            
            logger.info(f"生成多代理配置: {len(allocation.target_allocations)} 個資產")
            return allocation
            
        except Exception as e:
            logger.error(f"生成多代理配置失敗: {e}")
            # 返回默認配置
            return self._create_default_allocation(coordinated_decisions)
    
    def _create_default_allocation(
        self,
        coordinated_decisions: Dict[str, CoordinatedDecision]
    ) -> PortfolioAllocation:
        """創建默認配置"""
        symbols = list(coordinated_decisions.keys())
        equal_weight = 1.0 / len(symbols) if symbols else 0.0
        
        target_allocations = {}
        for symbol in symbols:
            target_allocations[symbol] = AssetAllocation(
                symbol=symbol,
                target_weight=equal_weight,
                current_weight=0.0,
                weight_change=equal_weight,
                risk_contribution=equal_weight,
                expected_return=0.05,
                volatility=0.2,
                sharpe_ratio=0.25,
                liquidity_score=0.8,
                allocation_reason="默認等權重配置",
                metadata={}
            )
        
        return PortfolioAllocation(
            timestamp=datetime.now(),
            allocation_method=self.portfolio_allocator.allocation_method,
            total_portfolio_value=self.portfolio_manager.get_portfolio().total_value,
            target_allocations=target_allocations,
            risk_metrics={'portfolio_volatility': 0.15},
            performance_metrics={'expected_return': 0.05},
            rebalancing_needed=True,
            rebalancing_cost=0.0,
            liquidity_constraints={'liquidity_score': 0.8},
            allocation_confidence=0.5,
            reasoning="默認配置",
            metadata={'error_fallback': True}
        )

    async def _integrate_allocations(
        self,
        multi_agent_allocation: PortfolioAllocation,
        current_portfolio: Portfolio
    ) -> PortfolioAllocation:
        """整合配置"""
        try:
            if self.config.mode == IntegrationMode.OVERRIDE:
                # 完全使用多代理配置
                return multi_agent_allocation

            elif self.config.mode == IntegrationMode.BLEND:
                # 混合現有配置和多代理配置
                return await self._blend_allocations(
                    multi_agent_allocation, current_portfolio
                )

            elif self.config.mode == IntegrationMode.ADVISORY:
                # 多代理配置作為建議，保持現有配置為主
                return await self._advisory_integration(
                    multi_agent_allocation, current_portfolio
                )

            elif self.config.mode == IntegrationMode.CONSTRAINT:
                # 多代理配置作為約束條件
                return await self._constraint_integration(
                    multi_agent_allocation, current_portfolio
                )

            else:  # ADAPTIVE
                # 自適應模式
                return await self._adaptive_integration(
                    multi_agent_allocation, current_portfolio
                )

        except Exception as e:
            logger.error(f"整合配置失敗: {e}")
            return multi_agent_allocation

    async def _blend_allocations(
        self,
        multi_agent_allocation: PortfolioAllocation,
        current_portfolio: Portfolio
    ) -> PortfolioAllocation:
        """混合配置"""
        blend_ratio = self.config.blend_ratio

        # 獲取當前權重
        current_weights = {}
        if current_portfolio and current_portfolio.positions:
            total_value = current_portfolio.total_value
            for symbol, position in current_portfolio.positions.items():
                current_weights[symbol] = position.market_value / total_value

        # 混合權重
        blended_allocations = {}
        all_symbols = set(multi_agent_allocation.target_allocations.keys()) | set(current_weights.keys())

        for symbol in all_symbols:
            # 多代理權重
            ma_weight = 0.0
            if symbol in multi_agent_allocation.target_allocations:
                ma_weight = multi_agent_allocation.target_allocations[symbol].target_weight

            # 當前權重
            current_weight = current_weights.get(symbol, 0.0)

            # 混合權重
            blended_weight = ma_weight * blend_ratio + current_weight * (1 - blend_ratio)

            # 創建混合配置
            if symbol in multi_agent_allocation.target_allocations:
                original_allocation = multi_agent_allocation.target_allocations[symbol]
                blended_allocations[symbol] = AssetAllocation(
                    symbol=symbol,
                    target_weight=blended_weight,
                    current_weight=current_weight,
                    weight_change=blended_weight - current_weight,
                    risk_contribution=original_allocation.risk_contribution,
                    expected_return=original_allocation.expected_return,
                    volatility=original_allocation.volatility,
                    sharpe_ratio=original_allocation.sharpe_ratio,
                    liquidity_score=original_allocation.liquidity_score,
                    allocation_reason=f"混合配置({blend_ratio:.0%}多代理+{1-blend_ratio:.0%}現有)",
                    metadata=original_allocation.metadata
                )
            else:
                # 只在當前投資組合中的資產
                blended_allocations[symbol] = AssetAllocation(
                    symbol=symbol,
                    target_weight=blended_weight,
                    current_weight=current_weight,
                    weight_change=blended_weight - current_weight,
                    risk_contribution=blended_weight,
                    expected_return=0.05,
                    volatility=0.2,
                    sharpe_ratio=0.25,
                    liquidity_score=0.8,
                    allocation_reason="保持現有配置",
                    metadata={'blend_only': True}
                )

        # 創建混合配置結果
        return PortfolioAllocation(
            timestamp=datetime.now(),
            allocation_method=multi_agent_allocation.allocation_method,
            total_portfolio_value=multi_agent_allocation.total_portfolio_value,
            target_allocations=blended_allocations,
            risk_metrics=multi_agent_allocation.risk_metrics,
            performance_metrics=multi_agent_allocation.performance_metrics,
            rebalancing_needed=True,
            rebalancing_cost=multi_agent_allocation.rebalancing_cost,
            liquidity_constraints=multi_agent_allocation.liquidity_constraints,
            allocation_confidence=multi_agent_allocation.allocation_confidence * 0.8,  # 混合降低信心度
            reasoning=f"混合配置(比例{blend_ratio:.0%}): {multi_agent_allocation.reasoning}",
            metadata={'integration_mode': 'blend', 'blend_ratio': blend_ratio}
        )

    async def _advisory_integration(
        self,
        multi_agent_allocation: PortfolioAllocation,
        current_portfolio: Portfolio
    ) -> PortfolioAllocation:
        """顧問整合模式"""
        # 保持現有配置為主，多代理配置作為調整建議

        current_weights = {}
        if current_portfolio and current_portfolio.positions:
            total_value = current_portfolio.total_value
            for symbol, position in current_portfolio.positions.items():
                current_weights[symbol] = position.market_value / total_value

        advisory_allocations = {}

        # 基於多代理建議微調現有配置
        for symbol, current_weight in current_weights.items():
            adjustment = 0.0

            # 如果多代理有建議
            if symbol in multi_agent_allocation.target_allocations:
                ma_allocation = multi_agent_allocation.target_allocations[symbol]
                ma_weight = ma_allocation.target_weight

                # 計算建議調整幅度（限制在±5%以內）
                suggested_change = ma_weight - current_weight
                adjustment = max(-0.05, min(0.05, suggested_change))

            adjusted_weight = current_weight + adjustment

            advisory_allocations[symbol] = AssetAllocation(
                symbol=symbol,
                target_weight=adjusted_weight,
                current_weight=current_weight,
                weight_change=adjustment,
                risk_contribution=adjusted_weight,
                expected_return=0.05,
                volatility=0.2,
                sharpe_ratio=0.25,
                liquidity_score=0.8,
                allocation_reason=f"顧問調整: {adjustment:+.1%}",
                metadata={'advisory_mode': True}
            )

        return PortfolioAllocation(
            timestamp=datetime.now(),
            allocation_method=multi_agent_allocation.allocation_method,
            total_portfolio_value=current_portfolio.total_value if current_portfolio else 0,
            target_allocations=advisory_allocations,
            risk_metrics={'portfolio_volatility': 0.12},
            performance_metrics={'expected_return': 0.06},
            rebalancing_needed=any(abs(alloc.weight_change) > 0.01 for alloc in advisory_allocations.values()),
            rebalancing_cost=0.001,
            liquidity_constraints={'liquidity_score': 0.9},
            allocation_confidence=0.8,
            reasoning="顧問模式：基於多代理建議微調現有配置",
            metadata={'integration_mode': 'advisory'}
        )

    async def _constraint_integration(
        self,
        multi_agent_allocation: PortfolioAllocation,
        current_portfolio: Portfolio
    ) -> PortfolioAllocation:
        """約束整合模式"""
        # 使用多代理配置作為約束條件優化現有配置

        # 提取約束條件
        constraints = {}
        for symbol, allocation in multi_agent_allocation.target_allocations.items():
            # 將多代理權重作為目標約束
            constraints[symbol] = {
                'min_weight': max(0, allocation.target_weight - 0.05),
                'max_weight': allocation.target_weight + 0.05,
                'target_weight': allocation.target_weight
            }

        # 基於約束優化配置
        constrained_allocations = {}
        total_constraint_weight = sum(c['target_weight'] for c in constraints.values())

        if total_constraint_weight > 0:
            # 標準化約束權重
            for symbol, constraint in constraints.items():
                normalized_weight = constraint['target_weight'] / total_constraint_weight

                constrained_allocations[symbol] = AssetAllocation(
                    symbol=symbol,
                    target_weight=normalized_weight,
                    current_weight=0.0,  # 將在後續更新
                    weight_change=normalized_weight,
                    risk_contribution=normalized_weight,
                    expected_return=0.05,
                    volatility=0.2,
                    sharpe_ratio=0.25,
                    liquidity_score=0.8,
                    allocation_reason=f"約束優化: 目標{normalized_weight:.1%}",
                    metadata={'constraint_mode': True, 'constraint': constraint}
                )

        return PortfolioAllocation(
            timestamp=datetime.now(),
            allocation_method=multi_agent_allocation.allocation_method,
            total_portfolio_value=multi_agent_allocation.total_portfolio_value,
            target_allocations=constrained_allocations,
            risk_metrics=multi_agent_allocation.risk_metrics,
            performance_metrics=multi_agent_allocation.performance_metrics,
            rebalancing_needed=True,
            rebalancing_cost=multi_agent_allocation.rebalancing_cost,
            liquidity_constraints=multi_agent_allocation.liquidity_constraints,
            allocation_confidence=0.85,
            reasoning="約束模式：基於多代理約束優化配置",
            metadata={'integration_mode': 'constraint', 'constraints': constraints}
        )

    async def _adaptive_integration(
        self,
        multi_agent_allocation: PortfolioAllocation,
        current_portfolio: Portfolio
    ) -> PortfolioAllocation:
        """自適應整合模式"""
        # 根據歷史績效動態選擇整合策略

        # 評估多代理配置的歷史績效
        ma_performance = self._evaluate_multi_agent_performance()

        # 評估現有投資組合績效
        portfolio_performance = self._evaluate_portfolio_performance()

        # 根據績效選擇整合策略
        if ma_performance > portfolio_performance + 0.02:  # 多代理明顯更好
            return multi_agent_allocation  # 使用覆蓋模式
        elif portfolio_performance > ma_performance + 0.02:  # 現有投資組合更好
            return await self._advisory_integration(multi_agent_allocation, current_portfolio)
        else:  # 績效相近
            return await self._blend_allocations(multi_agent_allocation, current_portfolio)

    def _evaluate_multi_agent_performance(self) -> float:
        """評估多代理配置績效"""
        if not self.allocation_history:
            return 0.05  # 默認5%收益率

        # 計算最近配置的平均預期收益率
        recent_allocations = self.allocation_history[-10:]  # 最近10次配置
        avg_expected_return = np.mean([
            alloc.performance_metrics.get('expected_return', 0.05)
            for alloc in recent_allocations
        ])

        return avg_expected_return

    def _evaluate_portfolio_performance(self) -> float:
        """評估投資組合績效"""
        if not self.performance_history:
            return 0.04  # 默認4%收益率

        # 計算最近績效的平均值
        recent_performance = self.performance_history[-30:]  # 最近30天
        if recent_performance:
            avg_return = np.mean([p.get('daily_return', 0) for p in recent_performance])
            return avg_return * 252  # 年化收益率

        return 0.04

    async def _apply_risk_constraints(
        self,
        allocation: PortfolioAllocation
    ) -> PortfolioAllocation:
        """應用風險約束"""
        try:
            risk_adjusted_allocations = {}

            for symbol, asset_allocation in allocation.target_allocations.items():
                adjusted_weight = asset_allocation.target_weight

                # 應用最大倉位限制
                if adjusted_weight > self.risk_limits['max_position_size']:
                    adjusted_weight = self.risk_limits['max_position_size']
                    logger.warning(f"限制 {symbol} 倉位至 {adjusted_weight:.1%}")

                # 創建風險調整後的配置
                risk_adjusted_allocations[symbol] = AssetAllocation(
                    symbol=symbol,
                    target_weight=adjusted_weight,
                    current_weight=asset_allocation.current_weight,
                    weight_change=adjusted_weight - asset_allocation.current_weight,
                    risk_contribution=asset_allocation.risk_contribution,
                    expected_return=asset_allocation.expected_return,
                    volatility=asset_allocation.volatility,
                    sharpe_ratio=asset_allocation.sharpe_ratio,
                    liquidity_score=asset_allocation.liquidity_score,
                    allocation_reason=f"風險調整: {asset_allocation.allocation_reason}",
                    metadata={**asset_allocation.metadata, 'risk_adjusted': True}
                )

            # 重新標準化權重
            total_weight = sum(alloc.target_weight for alloc in risk_adjusted_allocations.values())
            if total_weight > 0:
                for allocation_obj in risk_adjusted_allocations.values():
                    allocation_obj.target_weight /= total_weight
                    allocation_obj.weight_change = allocation_obj.target_weight - allocation_obj.current_weight

            # 創建風險調整後的配置
            return PortfolioAllocation(
                timestamp=datetime.now(),
                allocation_method=allocation.allocation_method,
                total_portfolio_value=allocation.total_portfolio_value,
                target_allocations=risk_adjusted_allocations,
                risk_metrics=allocation.risk_metrics,
                performance_metrics=allocation.performance_metrics,
                rebalancing_needed=allocation.rebalancing_needed,
                rebalancing_cost=allocation.rebalancing_cost,
                liquidity_constraints=allocation.liquidity_constraints,
                allocation_confidence=allocation.allocation_confidence,
                reasoning=f"風險調整: {allocation.reasoning}",
                metadata={**allocation.metadata, 'risk_constraints_applied': True}
            )

        except Exception as e:
            logger.error(f"應用風險約束失敗: {e}")
            return allocation

    async def _optimize_allocation(
        self,
        allocation: PortfolioAllocation,
        market_data: Optional[Dict[str, pd.DataFrame]]
    ) -> PortfolioAllocation:
        """優化配置"""
        try:
            # 使用投資組合優化器進一步優化
            symbols = list(allocation.target_allocations.keys())
            target_weights = [alloc.target_weight for alloc in allocation.target_allocations.values()]

            # 簡化的優化（實際應用中會更複雜）
            optimized_weights = await self._simple_optimization(symbols, target_weights, market_data)

            # 創建優化後的配置
            optimized_allocations = {}
            for i, symbol in enumerate(symbols):
                original_allocation = allocation.target_allocations[symbol]
                optimized_weight = optimized_weights[i]

                optimized_allocations[symbol] = AssetAllocation(
                    symbol=symbol,
                    target_weight=optimized_weight,
                    current_weight=original_allocation.current_weight,
                    weight_change=optimized_weight - original_allocation.current_weight,
                    risk_contribution=original_allocation.risk_contribution,
                    expected_return=original_allocation.expected_return,
                    volatility=original_allocation.volatility,
                    sharpe_ratio=original_allocation.sharpe_ratio,
                    liquidity_score=original_allocation.liquidity_score,
                    allocation_reason=f"優化: {original_allocation.allocation_reason}",
                    metadata={**original_allocation.metadata, 'optimized': True}
                )

            return PortfolioAllocation(
                timestamp=datetime.now(),
                allocation_method=allocation.allocation_method,
                total_portfolio_value=allocation.total_portfolio_value,
                target_allocations=optimized_allocations,
                risk_metrics=allocation.risk_metrics,
                performance_metrics=allocation.performance_metrics,
                rebalancing_needed=allocation.rebalancing_needed,
                rebalancing_cost=allocation.rebalancing_cost,
                liquidity_constraints=allocation.liquidity_constraints,
                allocation_confidence=min(1.0, allocation.allocation_confidence * 1.1),  # 優化提升信心度
                reasoning=f"優化: {allocation.reasoning}",
                metadata={**allocation.metadata, 'optimization_applied': True}
            )

        except Exception as e:
            logger.error(f"優化配置失敗: {e}")
            return allocation

    async def _simple_optimization(
        self,
        symbols: List[str],
        target_weights: List[float],
        market_data: Optional[Dict[str, pd.DataFrame]]
    ) -> List[float]:
        """簡化的投資組合優化"""
        # 這是一個簡化的優化實現
        # 實際應用中會使用更複雜的優化算法

        # 應用基本約束
        optimized_weights = []
        for weight in target_weights:
            # 確保權重在合理範圍內
            optimized_weight = max(0.01, min(0.3, weight))
            optimized_weights.append(optimized_weight)

        # 標準化權重
        total_weight = sum(optimized_weights)
        if total_weight > 0:
            optimized_weights = [w / total_weight for w in optimized_weights]

        return optimized_weights

    async def _check_rebalance_need(
        self,
        target_allocation: PortfolioAllocation,
        current_portfolio: Portfolio,
        force_rebalance: bool
    ) -> bool:
        """檢查是否需要再平衡"""
        if force_rebalance:
            return True

        if not current_portfolio or not current_portfolio.positions:
            return True

        # 計算當前權重
        total_value = current_portfolio.total_value
        current_weights = {}
        for symbol, position in current_portfolio.positions.items():
            current_weights[symbol] = position.market_value / total_value

        # 檢查權重偏差
        max_deviation = 0.0
        for symbol, target_alloc in target_allocation.target_allocations.items():
            current_weight = current_weights.get(symbol, 0.0)
            deviation = abs(target_alloc.target_weight - current_weight)
            max_deviation = max(max_deviation, deviation)

        # 如果最大偏差超過閾值，需要再平衡
        return max_deviation > self.config.rebalance_threshold

    async def _execute_rebalance(
        self,
        target_allocation: PortfolioAllocation,
        current_portfolio: Portfolio
    ) -> Dict[str, Any]:
        """執行再平衡"""
        try:
            logger.info("執行投資組合再平衡...")

            # 使用再平衡引擎執行
            rebalance_orders = self.rebalancing_engine.generate_rebalance_orders(
                current_portfolio, target_allocation
            )

            # 模擬執行訂單
            execution_results = {}
            total_cost = 0.0

            for order in rebalance_orders:
                # 這裡應該調用實際的交易執行系統
                execution_result = {
                    'symbol': order.symbol,
                    'action': order.action,
                    'quantity': order.quantity,
                    'price': order.price,
                    'status': 'executed',
                    'execution_time': datetime.now().isoformat()
                }

                execution_results[order.symbol] = execution_result
                total_cost += order.quantity * order.price * 0.001  # 假設0.1%交易成本

            # 更新投資組合
            await self._update_portfolio_positions(target_allocation)

            # 更新統計
            self.integration_metrics.rebalance_count += 1

            result = {
                'rebalance_orders': len(rebalance_orders),
                'execution_results': execution_results,
                'total_cost': total_cost,
                'status': 'success',
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"再平衡執行完成: {len(rebalance_orders)} 筆訂單")
            return result

        except Exception as e:
            logger.error(f"執行再平衡失敗: {e}")
            return {
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def _update_portfolio_positions(self, target_allocation: PortfolioAllocation) -> None:
        """更新投資組合倉位"""
        try:
            # 這裡應該更新實際的投資組合倉位
            # 目前只是記錄目標配置

            for symbol, allocation in target_allocation.target_allocations.items():
                # 模擬更新倉位
                logger.debug(f"更新 {symbol} 倉位至 {allocation.target_weight:.2%}")

            logger.info("投資組合倉位更新完成")

        except Exception as e:
            logger.error(f"更新投資組合倉位失敗: {e}")

    async def _update_integration_metrics(self, integration_time: float, success: bool) -> None:
        """更新整合指標"""
        try:
            self.integration_metrics.total_integrations += 1

            if success:
                self.integration_metrics.successful_integrations += 1

            # 更新平均整合時間
            total = self.integration_metrics.total_integrations
            current_avg = self.integration_metrics.avg_integration_time
            self.integration_metrics.avg_integration_time = (
                (current_avg * (total - 1) + integration_time) / total
            )

            # 更新其他指標
            if self.portfolio_manager:
                portfolio = self.portfolio_manager.get_portfolio()
                if portfolio:
                    self.integration_metrics.portfolio_value_change = portfolio.total_value

            self.integration_metrics.last_update = datetime.now()

        except Exception as e:
            logger.error(f"更新整合指標失敗: {e}")

    def get_integration_status(self) -> Dict[str, Any]:
        """獲取整合狀態"""
        return {
            'integration_mode': self.config.mode.value,
            'config': {
                'blend_ratio': self.config.blend_ratio,
                'rebalance_threshold': self.config.rebalance_threshold,
                'max_position_change': self.config.max_position_change,
                'enable_auto_rebalance': self.config.enable_auto_rebalance
            },
            'metrics': {
                'total_integrations': self.integration_metrics.total_integrations,
                'successful_integrations': self.integration_metrics.successful_integrations,
                'success_rate': (
                    self.integration_metrics.successful_integrations /
                    max(1, self.integration_metrics.total_integrations)
                ),
                'rebalance_count': self.integration_metrics.rebalance_count,
                'avg_integration_time': self.integration_metrics.avg_integration_time,
                'portfolio_value': self.integration_metrics.portfolio_value_change
            },
            'last_allocation': {
                'timestamp': self.last_allocation.timestamp.isoformat() if self.last_allocation else None,
                'assets': len(self.last_allocation.target_allocations) if self.last_allocation else 0,
                'confidence': self.last_allocation.allocation_confidence if self.last_allocation else 0
            },
            'risk_limits': self.risk_limits,
            'allocation_history_length': len(self.allocation_history)
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """獲取績效摘要"""
        if not self.performance_history:
            return {'error': 'No performance data available'}

        recent_performance = self.performance_history[-30:]  # 最近30天

        daily_returns = [p.get('daily_return', 0) for p in recent_performance]

        return {
            'period_days': len(recent_performance),
            'total_return': sum(daily_returns),
            'avg_daily_return': np.mean(daily_returns),
            'volatility': np.std(daily_returns),
            'sharpe_ratio': (
                np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
                if np.std(daily_returns) > 0 else 0
            ),
            'max_drawdown': self._calculate_max_drawdown(daily_returns),
            'win_rate': sum(1 for r in daily_returns if r > 0) / len(daily_returns),
            'best_day': max(daily_returns) if daily_returns else 0,
            'worst_day': min(daily_returns) if daily_returns else 0
        }

    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """計算最大回撤"""
        if not returns:
            return 0.0

        cumulative = np.cumprod([1 + r for r in returns])
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max

        return abs(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0

    def update_performance(self, daily_return: float, portfolio_value: float) -> None:
        """更新績效數據"""
        performance_record = {
            'date': datetime.now().date().isoformat(),
            'daily_return': daily_return,
            'portfolio_value': portfolio_value,
            'timestamp': datetime.now().isoformat()
        }

        self.performance_history.append(performance_record)

        # 保持歷史記錄在合理範圍內
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-500:]

    def set_risk_limits(self, risk_limits: Dict[str, float]) -> None:
        """設置風險限制"""
        self.risk_limits.update(risk_limits)
        logger.info(f"更新風險限制: {risk_limits}")

    def set_integration_config(self, config: IntegrationConfig) -> None:
        """設置整合配置"""
        self.config = config
        logger.info(f"更新整合配置: {config.mode.value}")

    def get_allocation_history(self, limit: Optional[int] = None) -> List[PortfolioAllocation]:
        """獲取配置歷史"""
        if limit:
            return self.allocation_history[-limit:]
        return self.allocation_history.copy()

    def clear_history(self) -> None:
        """清除歷史記錄"""
        self.allocation_history.clear()
        self.performance_history.clear()
        self.integration_metrics = IntegrationMetrics()
        logger.info("清除投資組合整合歷史記錄")

    async def force_rebalance(self) -> Dict[str, Any]:
        """強制執行再平衡"""
        if not self.last_allocation:
            return {'error': 'No target allocation available'}

        current_portfolio = self.portfolio_manager.get_portfolio()
        return await self._execute_rebalance(self.last_allocation, current_portfolio)

    def __str__(self) -> str:
        """字符串表示"""
        return (f"PortfolioIntegration(mode={self.config.mode.value}, "
                f"integrations={self.integration_metrics.total_integrations}, "
                f"rebalances={self.integration_metrics.rebalance_count})")
