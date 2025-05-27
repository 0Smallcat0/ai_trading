"""
投資組合分析核心計算引擎

提供 VaR 計算、效率前緣、績效歸因、再平衡等核心金融計算功能。
"""

import numpy as np
import pandas as pd
from scipy import optimize, stats
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class VaRMethod(Enum):
    """VaR 計算方法枚舉"""

    HISTORICAL = "historical"
    PARAMETRIC = "parametric"
    MONTE_CARLO = "monte_carlo"


class OptimizationObjective(Enum):
    """優化目標枚舉"""

    MAX_SHARPE = "max_sharpe"
    MIN_VOLATILITY = "min_volatility"
    RISK_PARITY = "risk_parity"
    MAX_DIVERSIFICATION = "max_diversification"


@dataclass
class PortfolioMetrics:
    """投資組合指標數據類"""

    returns: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    var_95: float
    var_99: float
    expected_shortfall: float
    beta: float
    alpha: float
    information_ratio: float
    tracking_error: float


@dataclass
class RiskDecomposition:
    """風險分解數據類"""

    market_risk: float
    credit_risk: float
    liquidity_risk: float
    operational_risk: float
    total_risk: float
    diversification_ratio: float


class PortfolioAnalytics:
    """投資組合分析核心類"""

    def __init__(self, risk_free_rate: float = 0.02):
        """初始化投資組合分析器

        Args:
            risk_free_rate: 無風險利率，預設 2%
        """
        self.risk_free_rate = risk_free_rate
        self.simulation_count = 10000

    def calculate_var(
        self,
        returns: pd.Series,
        confidence_level: float = 0.95,
        method: VaRMethod = VaRMethod.HISTORICAL,
    ) -> float:
        """計算風險值 (Value at Risk)

        Args:
            returns: 報酬率序列
            confidence_level: 信心水準，預設 95%
            method: 計算方法

        Returns:
            VaR 值
        """
        if returns.empty:
            return 0.0

        try:
            if method == VaRMethod.HISTORICAL:
                return self._historical_var(returns, confidence_level)
            elif method == VaRMethod.PARAMETRIC:
                return self._parametric_var(returns, confidence_level)
            elif method == VaRMethod.MONTE_CARLO:
                return self._monte_carlo_var(returns, confidence_level)
            else:
                raise ValueError(f"不支援的 VaR 計算方法: {method}")

        except Exception as e:
            logger.error(f"VaR 計算失敗: {e}")
            return 0.0

    def _historical_var(self, returns: pd.Series, confidence_level: float) -> float:
        """歷史模擬法計算 VaR"""
        percentile = (1 - confidence_level) * 100
        return -np.percentile(returns, percentile)

    def _parametric_var(self, returns: pd.Series, confidence_level: float) -> float:
        """參數法計算 VaR"""
        mean = returns.mean()
        std = returns.std()
        z_score = stats.norm.ppf(1 - confidence_level)
        return -(mean + z_score * std)

    def _monte_carlo_var(self, returns: pd.Series, confidence_level: float) -> float:
        """Monte Carlo 模擬法計算 VaR"""
        mean = returns.mean()
        std = returns.std()

        # 生成隨機模擬
        simulated_returns = np.random.normal(mean, std, self.simulation_count)
        percentile = (1 - confidence_level) * 100
        return -np.percentile(simulated_returns, percentile)

    def calculate_expected_shortfall(
        self, returns: pd.Series, confidence_level: float = 0.95
    ) -> float:
        """計算預期損失 (Expected Shortfall/CVaR)

        Args:
            returns: 報酬率序列
            confidence_level: 信心水準

        Returns:
            預期損失值
        """
        if returns.empty:
            return 0.0

        try:
            var = self.calculate_var(returns, confidence_level, VaRMethod.HISTORICAL)
            tail_losses = returns[returns <= -var]
            return -tail_losses.mean() if not tail_losses.empty else 0.0

        except Exception as e:
            logger.error(f"預期損失計算失敗: {e}")
            return 0.0

    def stress_test(
        self,
        portfolio_weights: np.ndarray,
        returns_matrix: pd.DataFrame,
        stress_scenarios: Dict[str, Dict[str, float]],
    ) -> Dict[str, float]:
        """壓力測試

        Args:
            portfolio_weights: 投資組合權重
            returns_matrix: 資產報酬率矩陣
            stress_scenarios: 壓力情境字典

        Returns:
            各情境下的投資組合損失
        """
        results = {}

        try:
            for scenario_name, shocks in stress_scenarios.items():
                stressed_returns = returns_matrix.copy()

                # 應用壓力衝擊
                for asset, shock in shocks.items():
                    if asset in stressed_returns.columns:
                        stressed_returns[asset] = stressed_returns[asset] + shock

                # 計算投資組合報酬
                portfolio_returns = (stressed_returns * portfolio_weights).sum(axis=1)
                results[scenario_name] = portfolio_returns.sum()

        except Exception as e:
            logger.error(f"壓力測試失敗: {e}")

        return results

    def calculate_efficient_frontier(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        num_points: int = 100,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """計算效率前緣

        Args:
            expected_returns: 預期報酬率向量
            cov_matrix: 共變異數矩陣
            num_points: 前緣點數

        Returns:
            (報酬率, 風險, 權重矩陣)
        """
        try:
            n_assets = len(expected_returns)

            # 設定約束條件
            constraints = [
                {"type": "eq", "fun": lambda x: np.sum(x) - 1}  # 權重總和為1
            ]

            bounds = tuple((0, 1) for _ in range(n_assets))  # 權重範圍 0-1

            # 計算最小風險和最大報酬
            min_vol_result = self._minimize_volatility(
                expected_returns, cov_matrix, constraints, bounds
            )
            max_ret_result = self._maximize_return(
                expected_returns, cov_matrix, constraints, bounds
            )

            min_ret = min_vol_result["fun"]
            max_ret = max_ret_result["fun"]

            # 生成目標報酬率序列
            target_returns = np.linspace(min_ret, max_ret, num_points)

            frontier_volatility = []
            frontier_weights = []

            for target_ret in target_returns:
                # 添加報酬率約束
                ret_constraint = {
                    "type": "eq",
                    "fun": lambda x, target=target_ret: np.dot(x, expected_returns)
                    - target,
                }

                all_constraints = constraints + [ret_constraint]

                result = optimize.minimize(
                    self._portfolio_volatility,
                    x0=np.array([1 / n_assets] * n_assets),
                    args=(cov_matrix,),
                    method="SLSQP",
                    bounds=bounds,
                    constraints=all_constraints,
                )

                if result.success:
                    frontier_volatility.append(result.fun)
                    frontier_weights.append(result.x)
                else:
                    frontier_volatility.append(np.nan)
                    frontier_weights.append(np.array([np.nan] * n_assets))

            return (
                np.array(target_returns),
                np.array(frontier_volatility),
                np.array(frontier_weights),
            )

        except Exception as e:
            logger.error(f"效率前緣計算失敗: {e}")
            return np.array([]), np.array([]), np.array([])

    def optimize_portfolio(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        objective: OptimizationObjective = OptimizationObjective.MAX_SHARPE,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """投資組合優化

        Args:
            expected_returns: 預期報酬率向量
            cov_matrix: 共變異數矩陣
            objective: 優化目標
            constraints: 額外約束條件

        Returns:
            優化結果字典
        """
        try:
            n_assets = len(expected_returns)

            # 基本約束條件
            base_constraints = [{"type": "eq", "fun": lambda x: np.sum(x) - 1}]

            # 添加自定義約束
            if constraints:
                if "max_weight" in constraints:
                    max_weight = constraints["max_weight"]
                    bounds = tuple((0, max_weight) for _ in range(n_assets))
                else:
                    bounds = tuple((0, 1) for _ in range(n_assets))

                if "min_weight" in constraints:
                    min_weights = constraints["min_weight"]
                    bounds = tuple(
                        (min_weights.get(i, 0), bounds[i][1]) for i in range(n_assets)
                    )
            else:
                bounds = tuple((0, 1) for _ in range(n_assets))

            # 根據目標選擇優化函數
            if objective == OptimizationObjective.MAX_SHARPE:
                result = self._maximize_sharpe_ratio(
                    expected_returns, cov_matrix, base_constraints, bounds
                )
            elif objective == OptimizationObjective.MIN_VOLATILITY:
                result = self._minimize_volatility(
                    expected_returns, cov_matrix, base_constraints, bounds
                )
            elif objective == OptimizationObjective.RISK_PARITY:
                result = self._risk_parity_optimization(
                    expected_returns, cov_matrix, base_constraints, bounds
                )
            elif objective == OptimizationObjective.MAX_DIVERSIFICATION:
                result = self._maximize_diversification(
                    expected_returns, cov_matrix, base_constraints, bounds
                )
            else:
                raise ValueError(f"不支援的優化目標: {objective}")

            if result["success"]:
                weights = result["x"]
                portfolio_return = np.dot(weights, expected_returns)
                portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_vol

                return {
                    "success": True,
                    "weights": weights,
                    "expected_return": portfolio_return,
                    "volatility": portfolio_vol,
                    "sharpe_ratio": sharpe_ratio,
                    "objective_value": result["fun"],
                }
            else:
                return {"success": False, "message": result.get("message", "優化失敗")}

        except Exception as e:
            logger.error(f"投資組合優化失敗: {e}")
            return {"success": False, "message": str(e)}

    def _portfolio_volatility(
        self, weights: np.ndarray, cov_matrix: np.ndarray
    ) -> float:
        """計算投資組合波動率"""
        return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))

    def _portfolio_return(
        self, weights: np.ndarray, expected_returns: np.ndarray
    ) -> float:
        """計算投資組合預期報酬率"""
        return np.dot(weights, expected_returns)

    def _sharpe_ratio(
        self, weights: np.ndarray, expected_returns: np.ndarray, cov_matrix: np.ndarray
    ) -> float:
        """計算夏普比率（負值用於最大化）"""
        portfolio_return = self._portfolio_return(weights, expected_returns)
        portfolio_vol = self._portfolio_volatility(weights, cov_matrix)
        return -(portfolio_return - self.risk_free_rate) / portfolio_vol

    def _maximize_sharpe_ratio(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: List[Dict],
        bounds: Tuple,
    ) -> Dict[str, Any]:
        """最大化夏普比率"""
        n_assets = len(expected_returns)
        initial_guess = np.array([1 / n_assets] * n_assets)

        result = optimize.minimize(
            self._sharpe_ratio,
            x0=initial_guess,
            args=(expected_returns, cov_matrix),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        return result

    def _minimize_volatility(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: List[Dict],
        bounds: Tuple,
    ) -> Dict[str, Any]:
        """最小化波動率"""
        n_assets = len(expected_returns)
        initial_guess = np.array([1 / n_assets] * n_assets)

        result = optimize.minimize(
            self._portfolio_volatility,
            x0=initial_guess,
            args=(cov_matrix,),
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        return result

    def _maximize_return(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: List[Dict],
        bounds: Tuple,
    ) -> Dict[str, Any]:
        """最大化報酬率"""
        n_assets = len(expected_returns)
        initial_guess = np.array([1 / n_assets] * n_assets)

        result = optimize.minimize(
            lambda x: -self._portfolio_return(x, expected_returns),
            x0=initial_guess,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        return result

    def _risk_parity_optimization(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: List[Dict],
        bounds: Tuple,
    ) -> Dict[str, Any]:
        """風險平價優化"""

        def risk_parity_objective(weights):
            portfolio_vol = self._portfolio_volatility(weights, cov_matrix)
            marginal_contrib = np.dot(cov_matrix, weights) / portfolio_vol
            contrib = weights * marginal_contrib
            return np.sum((contrib - contrib.mean()) ** 2)

        n_assets = len(expected_returns)
        initial_guess = np.array([1 / n_assets] * n_assets)

        result = optimize.minimize(
            risk_parity_objective,
            x0=initial_guess,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        return result

    def _maximize_diversification(
        self,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        constraints: List[Dict],
        bounds: Tuple,
    ) -> Dict[str, Any]:
        """最大化分散化比率"""

        def diversification_ratio(weights):
            portfolio_vol = self._portfolio_volatility(weights, cov_matrix)
            weighted_avg_vol = np.dot(weights, np.sqrt(np.diag(cov_matrix)))
            return -weighted_avg_vol / portfolio_vol  # 負值用於最大化

        n_assets = len(expected_returns)
        initial_guess = np.array([1 / n_assets] * n_assets)

        result = optimize.minimize(
            diversification_ratio,
            x0=initial_guess,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        return result

    def brinson_attribution(
        self,
        portfolio_weights: np.ndarray,
        benchmark_weights: np.ndarray,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray,
    ) -> Dict[str, float]:
        """Brinson 績效歸因分析

        Args:
            portfolio_weights: 投資組合權重
            benchmark_weights: 基準權重
            portfolio_returns: 投資組合報酬率
            benchmark_returns: 基準報酬率

        Returns:
            歸因分析結果
        """
        try:
            # 資產配置效應 (Asset Allocation Effect)
            weight_diff = portfolio_weights - benchmark_weights
            allocation_effect = np.sum(weight_diff * benchmark_returns)

            # 選股效應 (Stock Selection Effect)
            return_diff = portfolio_returns - benchmark_returns
            selection_effect = np.sum(benchmark_weights * return_diff)

            # 交互效應 (Interaction Effect)
            interaction_effect = np.sum(weight_diff * return_diff)

            # 總超額報酬
            total_excess = allocation_effect + selection_effect + interaction_effect

            return {
                "allocation_effect": allocation_effect,
                "selection_effect": selection_effect,
                "interaction_effect": interaction_effect,
                "total_excess_return": total_excess,
            }

        except Exception as e:
            logger.error(f"Brinson 歸因分析失敗: {e}")
            return {
                "allocation_effect": 0.0,
                "selection_effect": 0.0,
                "interaction_effect": 0.0,
                "total_excess_return": 0.0,
            }

    def calculate_tracking_error(
        self, portfolio_returns: pd.Series, benchmark_returns: pd.Series
    ) -> float:
        """計算追蹤誤差

        Args:
            portfolio_returns: 投資組合報酬率序列
            benchmark_returns: 基準報酬率序列

        Returns:
            追蹤誤差（年化）
        """
        try:
            if len(portfolio_returns) != len(benchmark_returns):
                raise ValueError("投資組合和基準報酬率序列長度不一致")

            excess_returns = portfolio_returns - benchmark_returns
            tracking_error = excess_returns.std() * np.sqrt(252)  # 年化

            return tracking_error

        except Exception as e:
            logger.error(f"追蹤誤差計算失敗: {e}")
            return 0.0

    def calculate_information_ratio(
        self, portfolio_returns: pd.Series, benchmark_returns: pd.Series
    ) -> float:
        """計算資訊比率

        Args:
            portfolio_returns: 投資組合報酬率序列
            benchmark_returns: 基準報酬率序列

        Returns:
            資訊比率
        """
        try:
            excess_returns = portfolio_returns - benchmark_returns
            active_return = excess_returns.mean() * 252  # 年化
            tracking_error = self.calculate_tracking_error(
                portfolio_returns, benchmark_returns
            )

            if tracking_error == 0:
                return 0.0

            return active_return / tracking_error

        except Exception as e:
            logger.error(f"資訊比率計算失敗: {e}")
            return 0.0

    def calculate_beta(
        self, portfolio_returns: pd.Series, market_returns: pd.Series
    ) -> float:
        """計算投資組合 Beta

        Args:
            portfolio_returns: 投資組合報酬率序列
            market_returns: 市場報酬率序列

        Returns:
            Beta 值
        """
        try:
            if len(portfolio_returns) != len(market_returns):
                raise ValueError("投資組合和市場報酬率序列長度不一致")

            covariance = np.cov(portfolio_returns, market_returns)[0, 1]
            market_variance = np.var(market_returns)

            if market_variance == 0:
                return 0.0

            return covariance / market_variance

        except Exception as e:
            logger.error(f"Beta 計算失敗: {e}")
            return 0.0

    def calculate_alpha(
        self,
        portfolio_returns: pd.Series,
        market_returns: pd.Series,
        beta: Optional[float] = None,
    ) -> float:
        """計算投資組合 Alpha

        Args:
            portfolio_returns: 投資組合報酬率序列
            market_returns: 市場報酬率序列
            beta: Beta 值，如未提供則自動計算

        Returns:
            Alpha 值（年化）
        """
        try:
            if beta is None:
                beta = self.calculate_beta(portfolio_returns, market_returns)

            portfolio_return = portfolio_returns.mean() * 252  # 年化
            market_return = market_returns.mean() * 252  # 年化

            expected_return = self.risk_free_rate + beta * (
                market_return - self.risk_free_rate
            )
            alpha = portfolio_return - expected_return

            return alpha

        except Exception as e:
            logger.error(f"Alpha 計算失敗: {e}")
            return 0.0

    def suggest_rebalancing(
        self,
        current_weights: np.ndarray,
        target_weights: np.ndarray,
        threshold: float = 0.05,
        transaction_costs: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """再平衡建議

        Args:
            current_weights: 當前權重
            target_weights: 目標權重
            threshold: 觸發閾值
            transaction_costs: 交易成本（可選）

        Returns:
            再平衡建議
        """
        try:
            weight_diff = np.abs(current_weights - target_weights)
            max_deviation = np.max(weight_diff)

            # 檢查是否需要再平衡
            needs_rebalancing = max_deviation > threshold

            if not needs_rebalancing:
                return {
                    "needs_rebalancing": False,
                    "max_deviation": max_deviation,
                    "threshold": threshold,
                    "trades": [],
                }

            # 計算交易建議
            trades = []
            for i, (current, target) in enumerate(zip(current_weights, target_weights)):
                trade_amount = target - current

                if abs(trade_amount) > threshold:
                    trade_cost = 0.0
                    if transaction_costs is not None and i < len(transaction_costs):
                        trade_cost = abs(trade_amount) * transaction_costs[i]

                    trades.append(
                        {
                            "asset_index": i,
                            "current_weight": current,
                            "target_weight": target,
                            "trade_amount": trade_amount,
                            "trade_cost": trade_cost,
                            "action": "buy" if trade_amount > 0 else "sell",
                        }
                    )

            # 計算總交易成本
            total_cost = sum(trade["trade_cost"] for trade in trades)

            return {
                "needs_rebalancing": True,
                "max_deviation": max_deviation,
                "threshold": threshold,
                "trades": trades,
                "total_transaction_cost": total_cost,
                "number_of_trades": len(trades),
            }

        except Exception as e:
            logger.error(f"再平衡建議計算失敗: {e}")
            return {"needs_rebalancing": False, "error": str(e)}

    def calculate_portfolio_metrics(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
        market_returns: Optional[pd.Series] = None,
    ) -> PortfolioMetrics:
        """計算完整的投資組合指標

        Args:
            returns: 投資組合報酬率序列
            benchmark_returns: 基準報酬率序列（可選）
            market_returns: 市場報酬率序列（可選）

        Returns:
            投資組合指標
        """
        try:
            # 基本指標
            annual_return = returns.mean() * 252
            annual_volatility = returns.std() * np.sqrt(252)
            sharpe_ratio = (annual_return - self.risk_free_rate) / annual_volatility

            # 最大回撤
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_drawdown = drawdown.min()

            # VaR 和 ES
            var_95 = self.calculate_var(returns, 0.95)
            var_99 = self.calculate_var(returns, 0.99)
            expected_shortfall = self.calculate_expected_shortfall(returns, 0.95)

            # 相對指標
            beta = 0.0
            alpha = 0.0
            information_ratio = 0.0
            tracking_error = 0.0

            if market_returns is not None:
                beta = self.calculate_beta(returns, market_returns)
                alpha = self.calculate_alpha(returns, market_returns, beta)

            if benchmark_returns is not None:
                information_ratio = self.calculate_information_ratio(
                    returns, benchmark_returns
                )
                tracking_error = self.calculate_tracking_error(
                    returns, benchmark_returns
                )

            return PortfolioMetrics(
                returns=annual_return,
                volatility=annual_volatility,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                var_95=var_95,
                var_99=var_99,
                expected_shortfall=expected_shortfall,
                beta=beta,
                alpha=alpha,
                information_ratio=information_ratio,
                tracking_error=tracking_error,
            )

        except Exception as e:
            logger.error(f"投資組合指標計算失敗: {e}")
            return PortfolioMetrics(
                returns=0.0,
                volatility=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                var_95=0.0,
                var_99=0.0,
                expected_shortfall=0.0,
                beta=0.0,
                alpha=0.0,
                information_ratio=0.0,
                tracking_error=0.0,
            )

    def decompose_risk(
        self,
        weights: np.ndarray,
        cov_matrix: np.ndarray,
        factor_loadings: Optional[np.ndarray] = None,
    ) -> RiskDecomposition:
        """風險分解分析

        Args:
            weights: 投資組合權重
            cov_matrix: 共變異數矩陣
            factor_loadings: 因子載荷矩陣（可選）

        Returns:
            風險分解結果
        """
        try:
            total_risk = self._portfolio_volatility(weights, cov_matrix)

            # 簡化的風險分解（實際應用中需要更複雜的模型）
            # 這裡使用模擬數據作為示例
            market_risk = total_risk * 0.6  # 假設60%為市場風險
            credit_risk = total_risk * 0.2  # 假設20%為信用風險
            liquidity_risk = total_risk * 0.15  # 假設15%為流動性風險
            operational_risk = total_risk * 0.05  # 假設5%為操作風險

            # 分散化比率
            individual_vols = np.sqrt(np.diag(cov_matrix))
            weighted_avg_vol = np.dot(weights, individual_vols)
            diversification_ratio = (
                weighted_avg_vol / total_risk if total_risk > 0 else 1.0
            )

            return RiskDecomposition(
                market_risk=market_risk,
                credit_risk=credit_risk,
                liquidity_risk=liquidity_risk,
                operational_risk=operational_risk,
                total_risk=total_risk,
                diversification_ratio=diversification_ratio,
            )

        except Exception as e:
            logger.error(f"風險分解分析失敗: {e}")
            return RiskDecomposition(
                market_risk=0.0,
                credit_risk=0.0,
                liquidity_risk=0.0,
                operational_risk=0.0,
                total_risk=0.0,
                diversification_ratio=1.0,
            )
