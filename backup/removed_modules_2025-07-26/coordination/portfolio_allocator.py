# -*- coding: utf-8 -*-
"""
投資組合分配器模組

此模組實現多層次投資組合配置和風險管理機制，
整合多代理決策並優化資產配置。

核心功能：
- 多層次資產配置
- 風險預算管理
- 動態再平衡
- 流動性管理
- 相關性分析

配置策略：
- 戰略資產配置（Strategic Asset Allocation）
- 戰術資產配置（Tactical Asset Allocation）
- 風險平價配置（Risk Parity）
- 最大分散化配置（Maximum Diversification）
- 最小方差配置（Minimum Variance）
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict
import scipy.optimize as sco
from scipy import linalg
import warnings

from .decision_coordinator import CoordinatedDecision

# 設定日誌
logger = logging.getLogger(__name__)

# 忽略優化警告
warnings.filterwarnings('ignore', category=RuntimeWarning)


class AllocationMethod(Enum):
    """配置方法枚舉"""
    STRATEGIC = "strategic"                   # 戰略配置
    TACTICAL = "tactical"                     # 戰術配置
    RISK_PARITY = "risk_parity"              # 風險平價
    MAX_DIVERSIFICATION = "max_diversification"  # 最大分散化
    MIN_VARIANCE = "min_variance"            # 最小方差
    MEAN_REVERSION = "mean_reversion"        # 均值回歸
    MOMENTUM = "momentum"                    # 動量策略


class RiskBudgetMethod(Enum):
    """風險預算方法枚舉"""
    EQUAL_RISK = "equal_risk"                # 等風險
    VOLATILITY_TARGET = "volatility_target"  # 波動率目標
    VAR_BUDGET = "var_budget"                # VaR預算
    EXPECTED_SHORTFALL = "expected_shortfall"  # 期望損失
    MAXIMUM_DRAWDOWN = "maximum_drawdown"    # 最大回撤


@dataclass
class AssetAllocation:
    """資產配置結果"""
    symbol: str
    target_weight: float                     # 目標權重
    current_weight: float                    # 當前權重
    weight_change: float                     # 權重變化
    risk_contribution: float                 # 風險貢獻
    expected_return: float                   # 期望收益率
    volatility: float                        # 波動率
    sharpe_ratio: float                      # 夏普比率
    liquidity_score: float                   # 流動性評分
    allocation_reason: str                   # 配置原因
    metadata: Dict[str, Any]                 # 額外信息


@dataclass
class PortfolioAllocation:
    """投資組合配置結果"""
    timestamp: datetime
    allocation_method: AllocationMethod
    total_portfolio_value: float
    target_allocations: Dict[str, AssetAllocation]
    risk_metrics: Dict[str, float]
    performance_metrics: Dict[str, float]
    rebalancing_needed: bool
    rebalancing_cost: float
    liquidity_constraints: Dict[str, Any]
    allocation_confidence: float
    reasoning: str
    metadata: Dict[str, Any]


class PortfolioAllocator:
    """
    投資組合分配器 - 多層次資產配置和風險管理的核心組件。
    
    負責將協調後的投資決策轉換為具體的資產配置，
    並進行風險管理和動態再平衡。
    
    Attributes:
        allocation_method (AllocationMethod): 配置方法
        risk_budget_method (RiskBudgetMethod): 風險預算方法
        target_volatility (float): 目標波動率
        max_position_size (float): 最大單一倉位
        min_position_size (float): 最小單一倉位
        rebalance_threshold (float): 再平衡閾值
        transaction_cost (float): 交易成本
        liquidity_requirement (float): 流動性要求
    """
    
    def __init__(
        self,
        allocation_method: AllocationMethod = AllocationMethod.RISK_PARITY,
        risk_budget_method: RiskBudgetMethod = RiskBudgetMethod.VOLATILITY_TARGET,
        target_volatility: float = 0.12,
        max_position_size: float = 0.3,
        min_position_size: float = 0.01,
        rebalance_threshold: float = 0.05,
        transaction_cost: float = 0.001,
        liquidity_requirement: float = 0.1
    ) -> None:
        """
        初始化投資組合分配器。
        
        Args:
            allocation_method: 配置方法
            risk_budget_method: 風險預算方法
            target_volatility: 目標年化波動率
            max_position_size: 最大單一倉位比例
            min_position_size: 最小單一倉位比例
            rebalance_threshold: 再平衡閾值
            transaction_cost: 交易成本比例
            liquidity_requirement: 流動性要求比例
        """
        self.allocation_method = allocation_method
        self.risk_budget_method = risk_budget_method
        self.target_volatility = target_volatility
        self.max_position_size = max_position_size
        self.min_position_size = min_position_size
        self.rebalance_threshold = rebalance_threshold
        self.transaction_cost = transaction_cost
        self.liquidity_requirement = liquidity_requirement
        
        # 投資組合狀態
        self.current_allocations: Dict[str, AssetAllocation] = {}
        self.portfolio_value = 1000000.0  # 默認100萬投資組合
        self.cash_position = 0.1  # 10%現金倉位
        
        # 歷史數據和統計
        self.allocation_history: List[PortfolioAllocation] = []
        self.return_history: Dict[str, List[float]] = defaultdict(list)
        self.correlation_matrix: Optional[pd.DataFrame] = None
        self.covariance_matrix: Optional[pd.DataFrame] = None
        
        # 風險模型參數
        self.lookback_period = 252  # 一年數據
        self.half_life = 63  # 季度半衰期
        self.min_correlation_periods = 30
        
        # 配置統計
        self.allocation_stats = {
            'total_allocations': 0,
            'rebalances': 0,
            'average_turnover': 0.0,
            'total_transaction_costs': 0.0,
            'risk_budget_utilization': 0.0
        }
        
        logger.info(f"初始化投資組合分配器: {allocation_method.value}")
    
    def allocate_portfolio(
        self,
        coordinated_decisions: Dict[str, CoordinatedDecision],
        market_data: Optional[Dict[str, pd.DataFrame]] = None,
        portfolio_value: Optional[float] = None
    ) -> PortfolioAllocation:
        """
        執行投資組合配置。
        
        Args:
            coordinated_decisions: 協調後的投資決策
            market_data: 市場數據
            portfolio_value: 投資組合總價值
            
        Returns:
            PortfolioAllocation: 投資組合配置結果
        """
        try:
            # 更新投資組合價值
            if portfolio_value:
                self.portfolio_value = portfolio_value
            
            # 更新市場數據和風險模型
            if market_data:
                self._update_risk_models(market_data)
            
            # 提取投資信號
            investment_signals = self._extract_investment_signals(coordinated_decisions)
            
            # 計算期望收益率
            expected_returns = self._calculate_expected_returns(investment_signals, market_data)
            
            # 執行資產配置優化
            if self.allocation_method == AllocationMethod.STRATEGIC:
                target_weights = self._strategic_allocation(expected_returns, investment_signals)
            elif self.allocation_method == AllocationMethod.TACTICAL:
                target_weights = self._tactical_allocation(expected_returns, investment_signals)
            elif self.allocation_method == AllocationMethod.RISK_PARITY:
                target_weights = self._risk_parity_allocation(expected_returns, investment_signals)
            elif self.allocation_method == AllocationMethod.MAX_DIVERSIFICATION:
                target_weights = self._max_diversification_allocation(expected_returns)
            elif self.allocation_method == AllocationMethod.MIN_VARIANCE:
                target_weights = self._min_variance_allocation(expected_returns)
            elif self.allocation_method == AllocationMethod.MEAN_REVERSION:
                target_weights = self._mean_reversion_allocation(expected_returns, market_data)
            else:  # MOMENTUM
                target_weights = self._momentum_allocation(expected_returns, market_data)
            
            # 應用約束條件
            constrained_weights = self._apply_allocation_constraints(target_weights)
            
            # 計算風險指標
            risk_metrics = self._calculate_portfolio_risk_metrics(constrained_weights)
            
            # 檢查再平衡需求
            rebalancing_analysis = self._analyze_rebalancing_needs(constrained_weights)
            
            # 創建資產配置對象
            asset_allocations = self._create_asset_allocations(
                constrained_weights, expected_returns, investment_signals
            )
            
            # 計算績效指標
            performance_metrics = self._calculate_performance_metrics(constrained_weights, expected_returns)
            
            # 生成配置結果
            portfolio_allocation = PortfolioAllocation(
                timestamp=datetime.now(),
                allocation_method=self.allocation_method,
                total_portfolio_value=self.portfolio_value,
                target_allocations=asset_allocations,
                risk_metrics=risk_metrics,
                performance_metrics=performance_metrics,
                rebalancing_needed=rebalancing_analysis['needed'],
                rebalancing_cost=rebalancing_analysis['cost'],
                liquidity_constraints=self._assess_liquidity_constraints(constrained_weights),
                allocation_confidence=self._calculate_allocation_confidence(investment_signals),
                reasoning=self._generate_allocation_reasoning(constrained_weights, risk_metrics),
                metadata={
                    'method': self.allocation_method.value,
                    'risk_budget_method': self.risk_budget_method.value,
                    'target_volatility': self.target_volatility,
                    'num_assets': len(constrained_weights)
                }
            )
            
            # 更新歷史和統計
            self._update_allocation_history(portfolio_allocation)
            self._update_allocation_stats(portfolio_allocation)
            
            return portfolio_allocation
            
        except Exception as e:
            logger.error(f"投資組合配置失敗: {e}")
            return self._create_default_allocation(coordinated_decisions)
    
    def _extract_investment_signals(
        self,
        coordinated_decisions: Dict[str, CoordinatedDecision]
    ) -> Dict[str, Dict[str, float]]:
        """提取投資信號"""
        signals = {}
        
        for symbol, decision in coordinated_decisions.items():
            signals[symbol] = {
                'action': float(decision.final_action),
                'confidence': decision.final_confidence,
                'position_size': decision.final_position_size,
                'expected_return': getattr(decision, 'expected_return', 0.0),
                'risk_assessment': getattr(decision, 'risk_assessment', 0.5),
                'coordination_confidence': decision.coordination_confidence
            }
        
        return signals

    def _update_risk_models(self, market_data: Dict[str, pd.DataFrame]) -> None:
        """更新風險模型"""
        try:
            # 收集收益率數據
            returns_data = {}

            for symbol, data in market_data.items():
                if 'close' in data.columns and len(data) > 1:
                    returns = data['close'].pct_change().dropna()
                    if len(returns) >= self.min_correlation_periods:
                        returns_data[symbol] = returns.tail(self.lookback_period)

            if len(returns_data) < 2:
                logger.warning("風險模型更新：數據不足")
                return

            # 創建收益率矩陣
            returns_df = pd.DataFrame(returns_data)
            returns_df = returns_df.dropna()

            if len(returns_df) < self.min_correlation_periods:
                logger.warning("風險模型更新：有效數據不足")
                return

            # 計算指數加權相關性矩陣
            self.correlation_matrix = self._calculate_ewm_correlation(returns_df)

            # 計算協方差矩陣
            volatilities = returns_df.std() * np.sqrt(252)  # 年化波動率
            vol_matrix = np.outer(volatilities, volatilities)
            self.covariance_matrix = self.correlation_matrix * vol_matrix

            logger.info(f"風險模型更新完成：{len(returns_data)}個資產")

        except Exception as e:
            logger.error(f"風險模型更新失敗: {e}")

    def _calculate_ewm_correlation(self, returns_df: pd.DataFrame) -> pd.DataFrame:
        """計算指數加權移動相關性"""
        # 使用指數加權移動平均計算相關性
        ewm_cov = returns_df.ewm(halflife=self.half_life).cov()

        # 提取最新的協方差矩陣
        latest_cov = ewm_cov.iloc[-len(returns_df.columns):, :]

        # 轉換為相關性矩陣
        std_matrix = np.sqrt(np.diag(latest_cov))
        correlation_matrix = latest_cov / np.outer(std_matrix, std_matrix)

        return correlation_matrix

    def _calculate_expected_returns(
        self,
        investment_signals: Dict[str, Dict[str, float]],
        market_data: Optional[Dict[str, pd.DataFrame]]
    ) -> Dict[str, float]:
        """計算期望收益率"""
        expected_returns = {}

        for symbol, signals in investment_signals.items():
            # 基於信號的期望收益率
            signal_return = signals['action'] * signals['confidence'] * 0.1  # 基礎10%年化收益率

            # 調整期望收益率
            if signals['expected_return'] > 0:
                expected_returns[symbol] = signals['expected_return']
            else:
                expected_returns[symbol] = signal_return

            # 風險調整
            risk_adjustment = 1.0 - signals['risk_assessment']
            expected_returns[symbol] *= risk_adjustment

        return expected_returns

    def _strategic_allocation(
        self,
        expected_returns: Dict[str, float],
        investment_signals: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """戰略資產配置"""
        # 基於長期期望收益率的配置
        total_expected_return = sum(max(0, ret) for ret in expected_returns.values())

        if total_expected_return == 0:
            # 等權重配置
            equal_weight = 1.0 / len(expected_returns)
            return {symbol: equal_weight for symbol in expected_returns.keys()}

        # 按期望收益率比例配置
        weights = {}
        for symbol, expected_return in expected_returns.items():
            if expected_return > 0:
                weights[symbol] = expected_return / total_expected_return
            else:
                weights[symbol] = 0.0

        return weights

    def _tactical_allocation(
        self,
        expected_returns: Dict[str, float],
        investment_signals: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """戰術資產配置"""
        # 基於短期信號的動態配置
        weights = {}
        total_signal_strength = 0.0

        # 計算信號強度
        for symbol, signals in investment_signals.items():
            signal_strength = abs(signals['action']) * signals['confidence']
            total_signal_strength += signal_strength

        if total_signal_strength == 0:
            return self._strategic_allocation(expected_returns, investment_signals)

        # 按信號強度分配權重
        for symbol, signals in investment_signals.items():
            signal_strength = abs(signals['action']) * signals['confidence']
            base_weight = signal_strength / total_signal_strength

            # 根據行動方向調整
            if signals['action'] > 0:
                weights[symbol] = base_weight
            else:
                weights[symbol] = base_weight * 0.1  # 減少空頭倉位

        return weights

    def _risk_parity_allocation(
        self,
        expected_returns: Dict[str, float],
        investment_signals: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        """風險平價配置"""
        symbols = list(expected_returns.keys())

        if self.covariance_matrix is None or len(symbols) < 2:
            # 等權重配置
            equal_weight = 1.0 / len(symbols)
            return {symbol: equal_weight for symbol in symbols}

        try:
            # 提取相關資產的協方差矩陣
            available_symbols = [s for s in symbols if s in self.covariance_matrix.index]
            if len(available_symbols) < 2:
                equal_weight = 1.0 / len(symbols)
                return {symbol: equal_weight for symbol in symbols}

            cov_subset = self.covariance_matrix.loc[available_symbols, available_symbols]

            # 風險平價優化
            def risk_parity_objective(weights):
                portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_subset.values, weights)))
                risk_contributions = weights * np.dot(cov_subset.values, weights) / portfolio_vol
                target_risk = portfolio_vol / len(weights)
                return np.sum((risk_contributions - target_risk) ** 2)

            # 約束條件
            constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
            bounds = [(0.01, 0.5) for _ in available_symbols]

            # 初始權重
            initial_weights = np.array([1.0 / len(available_symbols)] * len(available_symbols))

            # 優化
            result = sco.minimize(
                risk_parity_objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )

            if result.success:
                weights = {}
                for i, symbol in enumerate(available_symbols):
                    weights[symbol] = result.x[i]

                # 為不在協方差矩陣中的資產分配最小權重
                for symbol in symbols:
                    if symbol not in weights:
                        weights[symbol] = self.min_position_size

                return weights
            else:
                logger.warning("風險平價優化失敗，使用等權重")
                equal_weight = 1.0 / len(symbols)
                return {symbol: equal_weight for symbol in symbols}

        except Exception as e:
            logger.error(f"風險平價配置失敗: {e}")
            equal_weight = 1.0 / len(symbols)
            return {symbol: equal_weight for symbol in symbols}

    def _max_diversification_allocation(self, expected_returns: Dict[str, float]) -> Dict[str, float]:
        """最大分散化配置"""
        symbols = list(expected_returns.keys())

        if self.correlation_matrix is None or len(symbols) < 2:
            equal_weight = 1.0 / len(symbols)
            return {symbol: equal_weight for symbol in symbols}

        try:
            available_symbols = [s for s in symbols if s in self.correlation_matrix.index]
            if len(available_symbols) < 2:
                equal_weight = 1.0 / len(symbols)
                return {symbol: equal_weight for symbol in symbols}

            corr_subset = self.correlation_matrix.loc[available_symbols, available_symbols]

            # 最大分散化比率優化
            def diversification_ratio(weights):
                weighted_avg_vol = np.sum(weights)  # 假設所有資產波動率為1
                portfolio_vol = np.sqrt(np.dot(weights, np.dot(corr_subset.values, weights)))
                return -weighted_avg_vol / portfolio_vol  # 負號因為要最大化

            constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
            bounds = [(0.01, 0.5) for _ in available_symbols]
            initial_weights = np.array([1.0 / len(available_symbols)] * len(available_symbols))

            result = sco.minimize(
                diversification_ratio,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )

            if result.success:
                weights = {}
                for i, symbol in enumerate(available_symbols):
                    weights[symbol] = result.x[i]

                for symbol in symbols:
                    if symbol not in weights:
                        weights[symbol] = self.min_position_size

                return weights
            else:
                equal_weight = 1.0 / len(symbols)
                return {symbol: equal_weight for symbol in symbols}

        except Exception as e:
            logger.error(f"最大分散化配置失敗: {e}")
            equal_weight = 1.0 / len(symbols)
            return {symbol: equal_weight for symbol in symbols}

    def _min_variance_allocation(self, expected_returns: Dict[str, float]) -> Dict[str, float]:
        """最小方差配置"""
        symbols = list(expected_returns.keys())

        if self.covariance_matrix is None or len(symbols) < 2:
            equal_weight = 1.0 / len(symbols)
            return {symbol: equal_weight for symbol in symbols}

        try:
            available_symbols = [s for s in symbols if s in self.covariance_matrix.index]
            if len(available_symbols) < 2:
                equal_weight = 1.0 / len(symbols)
                return {symbol: equal_weight for symbol in symbols}

            cov_subset = self.covariance_matrix.loc[available_symbols, available_symbols]

            # 最小方差優化
            def portfolio_variance(weights):
                return np.dot(weights, np.dot(cov_subset.values, weights))

            constraints = [{'type': 'eq', 'fun': lambda w: np.sum(w) - 1}]
            bounds = [(0.01, 0.5) for _ in available_symbols]
            initial_weights = np.array([1.0 / len(available_symbols)] * len(available_symbols))

            result = sco.minimize(
                portfolio_variance,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )

            if result.success:
                weights = {}
                for i, symbol in enumerate(available_symbols):
                    weights[symbol] = result.x[i]

                for symbol in symbols:
                    if symbol not in weights:
                        weights[symbol] = self.min_position_size

                return weights
            else:
                equal_weight = 1.0 / len(symbols)
                return {symbol: equal_weight for symbol in symbols}

        except Exception as e:
            logger.error(f"最小方差配置失敗: {e}")
            equal_weight = 1.0 / len(symbols)
            return {symbol: equal_weight for symbol in symbols}

    def _mean_reversion_allocation(
        self,
        expected_returns: Dict[str, float],
        market_data: Optional[Dict[str, pd.DataFrame]]
    ) -> Dict[str, float]:
        """均值回歸配置"""
        if not market_data:
            return self._strategic_allocation(expected_returns, {})

        weights = {}
        total_reversion_signal = 0.0

        # 計算均值回歸信號
        for symbol, data in market_data.items():
            if symbol in expected_returns and 'close' in data.columns and len(data) >= 20:
                prices = data['close'].tail(20)
                current_price = prices.iloc[-1]
                mean_price = prices.mean()

                # 均值回歸信號：價格偏離均值越多，信號越強
                reversion_signal = abs(mean_price - current_price) / mean_price
                total_reversion_signal += reversion_signal
                weights[symbol] = reversion_signal

        # 標準化權重
        if total_reversion_signal > 0:
            weights = {symbol: weight / total_reversion_signal for symbol, weight in weights.items()}
        else:
            equal_weight = 1.0 / len(expected_returns)
            weights = {symbol: equal_weight for symbol in expected_returns.keys()}

        return weights

    def _momentum_allocation(
        self,
        expected_returns: Dict[str, float],
        market_data: Optional[Dict[str, pd.DataFrame]]
    ) -> Dict[str, float]:
        """動量配置"""
        if not market_data:
            return self._strategic_allocation(expected_returns, {})

        weights = {}
        momentum_scores = {}

        # 計算動量分數
        for symbol, data in market_data.items():
            if symbol in expected_returns and 'close' in data.columns and len(data) >= 20:
                prices = data['close'].tail(20)

                # 多期間動量
                momentum_1m = (prices.iloc[-1] / prices.iloc[-5] - 1) if len(prices) >= 5 else 0
                momentum_3m = (prices.iloc[-1] / prices.iloc[-15] - 1) if len(prices) >= 15 else 0

                # 綜合動量分數
                momentum_score = momentum_1m * 0.6 + momentum_3m * 0.4
                momentum_scores[symbol] = max(0, momentum_score)  # 只考慮正動量

        # 轉換為權重
        total_momentum = sum(momentum_scores.values())
        if total_momentum > 0:
            weights = {symbol: score / total_momentum for symbol, score in momentum_scores.items()}
        else:
            equal_weight = 1.0 / len(expected_returns)
            weights = {symbol: equal_weight for symbol in expected_returns.keys()}

        return weights

    def _apply_allocation_constraints(self, target_weights: Dict[str, float]) -> Dict[str, float]:
        """應用配置約束條件"""
        constrained_weights = {}

        # 應用最小最大權重約束
        for symbol, weight in target_weights.items():
            constrained_weight = max(self.min_position_size, min(self.max_position_size, weight))
            constrained_weights[symbol] = constrained_weight

        # 重新標準化
        total_weight = sum(constrained_weights.values())
        if total_weight > 0:
            constrained_weights = {k: v / total_weight for k, v in constrained_weights.items()}

        # 保留現金倉位
        cash_weight = self.liquidity_requirement
        adjustment_factor = 1.0 - cash_weight
        constrained_weights = {k: v * adjustment_factor for k, v in constrained_weights.items()}

        return constrained_weights

    def _calculate_portfolio_risk_metrics(self, weights: Dict[str, float]) -> Dict[str, float]:
        """計算投資組合風險指標"""
        risk_metrics = {}

        if self.covariance_matrix is not None:
            # 提取可用資產的權重
            available_symbols = [s for s in weights.keys() if s in self.covariance_matrix.index]

            if len(available_symbols) >= 2:
                weight_vector = np.array([weights.get(s, 0) for s in available_symbols])
                cov_subset = self.covariance_matrix.loc[available_symbols, available_symbols]

                # 投資組合波動率
                portfolio_variance = np.dot(weight_vector, np.dot(cov_subset.values, weight_vector))
                portfolio_volatility = np.sqrt(portfolio_variance)

                risk_metrics['portfolio_volatility'] = portfolio_volatility
                risk_metrics['portfolio_variance'] = portfolio_variance

                # 風險貢獻
                marginal_risk = np.dot(cov_subset.values, weight_vector) / portfolio_volatility
                risk_contributions = weight_vector * marginal_risk

                risk_metrics['max_risk_contribution'] = np.max(risk_contributions)
                risk_metrics['risk_concentration'] = np.sum(risk_contributions ** 2)

                # 分散化比率
                weighted_avg_vol = np.sum(weight_vector * np.sqrt(np.diag(cov_subset.values)))
                risk_metrics['diversification_ratio'] = weighted_avg_vol / portfolio_volatility
            else:
                risk_metrics['portfolio_volatility'] = self.target_volatility
                risk_metrics['portfolio_variance'] = self.target_volatility ** 2
                risk_metrics['max_risk_contribution'] = 1.0 / len(weights)
                risk_metrics['risk_concentration'] = 1.0 / len(weights)
                risk_metrics['diversification_ratio'] = 1.0
        else:
            # 默認風險指標
            risk_metrics['portfolio_volatility'] = self.target_volatility
            risk_metrics['portfolio_variance'] = self.target_volatility ** 2
            risk_metrics['max_risk_contribution'] = max(weights.values()) if weights else 0.0
            risk_metrics['risk_concentration'] = sum(w ** 2 for w in weights.values())
            risk_metrics['diversification_ratio'] = 1.0

        # 風險預算利用率
        risk_metrics['risk_budget_utilization'] = risk_metrics['portfolio_volatility'] / self.target_volatility

        return risk_metrics

    def _analyze_rebalancing_needs(self, target_weights: Dict[str, float]) -> Dict[str, Any]:
        """分析再平衡需求"""
        rebalancing_needed = False
        total_turnover = 0.0

        for symbol, target_weight in target_weights.items():
            current_weight = 0.0
            if symbol in self.current_allocations:
                current_weight = self.current_allocations[symbol].current_weight

            weight_diff = abs(target_weight - current_weight)
            total_turnover += weight_diff

            if weight_diff > self.rebalance_threshold:
                rebalancing_needed = True

        # 計算交易成本
        transaction_cost = total_turnover * self.transaction_cost * self.portfolio_value

        return {
            'needed': rebalancing_needed,
            'turnover': total_turnover,
            'cost': transaction_cost,
            'cost_ratio': transaction_cost / self.portfolio_value
        }

    def _create_asset_allocations(
        self,
        target_weights: Dict[str, float],
        expected_returns: Dict[str, float],
        investment_signals: Dict[str, Dict[str, float]]
    ) -> Dict[str, AssetAllocation]:
        """創建資產配置對象"""
        asset_allocations = {}

        for symbol, target_weight in target_weights.items():
            current_weight = 0.0
            if symbol in self.current_allocations:
                current_weight = self.current_allocations[symbol].current_weight

            weight_change = target_weight - current_weight

            # 計算風險貢獻（簡化）
            risk_contribution = target_weight  # 簡化實現

            # 獲取資產特性
            expected_return = expected_returns.get(symbol, 0.0)
            signals = investment_signals.get(symbol, {})
            volatility = signals.get('risk_assessment', 0.2) * 0.3  # 簡化波動率估算

            # 計算夏普比率
            sharpe_ratio = expected_return / volatility if volatility > 0 else 0.0

            # 流動性評分（簡化）
            liquidity_score = 0.8  # 默認高流動性

            # 配置原因
            allocation_reason = self._generate_allocation_reason(
                symbol, target_weight, weight_change, signals
            )

            asset_allocations[symbol] = AssetAllocation(
                symbol=symbol,
                target_weight=target_weight,
                current_weight=current_weight,
                weight_change=weight_change,
                risk_contribution=risk_contribution,
                expected_return=expected_return,
                volatility=volatility,
                sharpe_ratio=sharpe_ratio,
                liquidity_score=liquidity_score,
                allocation_reason=allocation_reason,
                metadata={
                    'signals': signals,
                    'allocation_method': self.allocation_method.value
                }
            )

        return asset_allocations

    def _generate_allocation_reason(
        self,
        symbol: str,
        target_weight: float,
        weight_change: float,
        signals: Dict[str, float]
    ) -> str:
        """生成配置原因"""
        if abs(weight_change) < 0.01:
            return f"維持{target_weight:.1%}配置"

        action = signals.get('action', 0)
        confidence = signals.get('confidence', 0.5)

        if weight_change > 0.05:
            if action > 0 and confidence > 0.7:
                return f"強烈買入信號，增加至{target_weight:.1%}"
            else:
                return f"配置優化，增加至{target_weight:.1%}"
        elif weight_change < -0.05:
            if action < 0 or confidence < 0.3:
                return f"信號轉弱，減少至{target_weight:.1%}"
            else:
                return f"風險管理，減少至{target_weight:.1%}"
        else:
            return f"微調至{target_weight:.1%}"

    def _calculate_performance_metrics(
        self,
        weights: Dict[str, float],
        expected_returns: Dict[str, float]
    ) -> Dict[str, float]:
        """計算績效指標"""
        # 投資組合期望收益率
        portfolio_return = sum(weights.get(symbol, 0) * ret for symbol, ret in expected_returns.items())

        # 其他績效指標（簡化）
        performance_metrics = {
            'expected_return': portfolio_return,
            'expected_sharpe_ratio': portfolio_return / self.target_volatility if self.target_volatility > 0 else 0.0,
            'tracking_error': 0.02,  # 簡化假設
            'information_ratio': portfolio_return / 0.02 if portfolio_return != 0 else 0.0,
            'max_expected_drawdown': self.target_volatility * 2.0  # 簡化估算
        }

        return performance_metrics

    def _assess_liquidity_constraints(self, weights: Dict[str, float]) -> Dict[str, Any]:
        """評估流動性約束"""
        # 簡化的流動性評估
        total_illiquid_weight = 0.0
        liquidity_issues = []

        for symbol, weight in weights.items():
            # 假設權重超過20%的倉位流動性較差
            if weight > 0.2:
                total_illiquid_weight += weight - 0.2
                liquidity_issues.append(f"{symbol}: {weight:.1%}")

        return {
            'total_illiquid_weight': total_illiquid_weight,
            'liquidity_issues': liquidity_issues,
            'cash_requirement_met': self.cash_position >= self.liquidity_requirement,
            'liquidity_score': max(0.0, 1.0 - total_illiquid_weight)
        }

    def _calculate_allocation_confidence(self, investment_signals: Dict[str, Dict[str, float]]) -> float:
        """計算配置信心度"""
        if not investment_signals:
            return 0.5

        confidences = [signals.get('confidence', 0.5) for signals in investment_signals.values()]
        coordination_confidences = [signals.get('coordination_confidence', 0.5) for signals in investment_signals.values()]

        # 綜合信心度
        avg_confidence = np.mean(confidences)
        avg_coordination_confidence = np.mean(coordination_confidences)

        return (avg_confidence + avg_coordination_confidence) / 2

    def _generate_allocation_reasoning(
        self,
        weights: Dict[str, float],
        risk_metrics: Dict[str, float]
    ) -> str:
        """生成配置推理"""
        method_name = self.allocation_method.value.replace('_', ' ').title()

        portfolio_vol = risk_metrics.get('portfolio_volatility', 0.0)
        diversification_ratio = risk_metrics.get('diversification_ratio', 1.0)

        reasoning = f"{method_name}配置策略："
        reasoning += f"目標波動率{self.target_volatility:.1%}，"
        reasoning += f"實際波動率{portfolio_vol:.1%}，"
        reasoning += f"分散化比率{diversification_ratio:.2f}，"
        reasoning += f"配置{len(weights)}個資產"

        return reasoning

    def _create_default_allocation(
        self,
        coordinated_decisions: Dict[str, CoordinatedDecision]
    ) -> PortfolioAllocation:
        """創建默認配置"""
        symbols = list(coordinated_decisions.keys())
        equal_weight = 1.0 / len(symbols) if symbols else 0.0

        default_allocations = {}
        for symbol in symbols:
            default_allocations[symbol] = AssetAllocation(
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
            allocation_method=self.allocation_method,
            total_portfolio_value=self.portfolio_value,
            target_allocations=default_allocations,
            risk_metrics={'portfolio_volatility': self.target_volatility},
            performance_metrics={'expected_return': 0.05},
            rebalancing_needed=True,
            rebalancing_cost=0.0,
            liquidity_constraints={'liquidity_score': 0.8},
            allocation_confidence=0.5,
            reasoning="配置失敗，使用默認等權重配置",
            metadata={'error': True}
        )

    def _update_allocation_history(self, allocation: PortfolioAllocation) -> None:
        """更新配置歷史"""
        self.allocation_history.append(allocation)

        # 保持歷史記錄在合理範圍內
        if len(self.allocation_history) > 1000:
            self.allocation_history = self.allocation_history[-500:]

        # 更新當前配置
        self.current_allocations = allocation.target_allocations

    def _update_allocation_stats(self, allocation: PortfolioAllocation) -> None:
        """更新配置統計"""
        self.allocation_stats['total_allocations'] += 1

        if allocation.rebalancing_needed:
            self.allocation_stats['rebalances'] += 1

        # 更新平均換手率
        if len(self.allocation_history) > 1:
            prev_allocation = self.allocation_history[-2]
            turnover = self._calculate_turnover(prev_allocation, allocation)

            total_allocations = self.allocation_stats['total_allocations']
            current_avg = self.allocation_stats['average_turnover']
            self.allocation_stats['average_turnover'] = (
                (current_avg * (total_allocations - 1) + turnover) / total_allocations
            )

        # 更新交易成本
        self.allocation_stats['total_transaction_costs'] += allocation.rebalancing_cost

        # 更新風險預算利用率
        risk_utilization = allocation.risk_metrics.get('risk_budget_utilization', 1.0)
        self.allocation_stats['risk_budget_utilization'] = risk_utilization

    def _calculate_turnover(
        self,
        prev_allocation: PortfolioAllocation,
        current_allocation: PortfolioAllocation
    ) -> float:
        """計算換手率"""
        turnover = 0.0

        all_symbols = set(prev_allocation.target_allocations.keys()) | set(current_allocation.target_allocations.keys())

        for symbol in all_symbols:
            prev_weight = prev_allocation.target_allocations.get(symbol, AssetAllocation(
                symbol=symbol, target_weight=0.0, current_weight=0.0, weight_change=0.0,
                risk_contribution=0.0, expected_return=0.0, volatility=0.0, sharpe_ratio=0.0,
                liquidity_score=0.0, allocation_reason="", metadata={}
            )).target_weight

            current_weight = current_allocation.target_allocations.get(symbol, AssetAllocation(
                symbol=symbol, target_weight=0.0, current_weight=0.0, weight_change=0.0,
                risk_contribution=0.0, expected_return=0.0, volatility=0.0, sharpe_ratio=0.0,
                liquidity_score=0.0, allocation_reason="", metadata={}
            )).target_weight

            turnover += abs(current_weight - prev_weight)

        return turnover / 2  # 除以2因為買入和賣出重複計算

    def get_allocation_stats(self) -> Dict[str, Any]:
        """獲取配置統計"""
        return self.allocation_stats.copy()

    def get_allocation_history(self, limit: Optional[int] = None) -> List[PortfolioAllocation]:
        """獲取配置歷史"""
        if limit:
            return self.allocation_history[-limit:]
        return self.allocation_history.copy()

    def set_portfolio_value(self, value: float) -> None:
        """設定投資組合價值"""
        self.portfolio_value = max(0.0, value)
        logger.info(f"投資組合價值設定為 {value:,.0f}")

    def __str__(self) -> str:
        """字符串表示"""
        return (f"PortfolioAllocator(method={self.allocation_method.value}, "
                f"value={self.portfolio_value:,.0f}, "
                f"allocations={self.allocation_stats['total_allocations']})")
