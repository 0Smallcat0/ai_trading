"""投資組合風險分析服務模組

此模組提供投資組合風險分析相關的服務功能，包括：
- VaR (Value at Risk) 計算
- 風險指標計算
- 壓力測試
- 風險報告生成

這個模組專門處理投資組合的風險管理功能。
"""

from typing import Dict, List, Optional, Any
import logging
from datetime import datetime

import pandas as pd
import numpy as np

from .core import PortfolioServiceCore

# 設定日誌
logger = logging.getLogger(__name__)


class PortfolioRiskAnalysisService:
    """投資組合風險分析服務"""

    def __init__(self, core_service: Optional[PortfolioServiceCore] = None):
        """初始化風險分析服務

        Args:
            core_service: 核心服務實例，如果為 None 則創建新實例
        """
        if core_service is None:
            self.core = PortfolioServiceCore()
        else:
            self.core = core_service

    def calculate_var(
        self,
        portfolio_id: str,
        confidence_level: float = 0.05,
        time_horizon: int = 1,
        method: str = "historical"
    ) -> Dict[str, Any]:
        """計算投資組合 VaR

        Args:
            portfolio_id: 投資組合ID
            confidence_level: 信心水準（預設 5%）
            time_horizon: 時間範圍（天數）
            method: 計算方法 ('historical', 'parametric', 'monte_carlo')

        Returns:
            VaR 計算結果
        """
        try:
            portfolio = self.core.get_portfolio(portfolio_id)
            if not portfolio:
                return {"error": f"投資組合不存在: {portfolio_id}"}

            # 獲取歷史收益率資料（這裡使用模擬資料）
            symbols = portfolio.get_symbols()
            returns_data = self._get_portfolio_returns(symbols, days=252)

            if returns_data.empty:
                return {"error": "無法獲取收益率資料"}

            # 計算投資組合收益率
            weights = np.array([h.weight for h in portfolio.holdings])
            portfolio_returns = (returns_data * weights).sum(axis=1)

            # 根據方法計算 VaR
            if method == "historical":
                var_result = self._calculate_historical_var(
                    portfolio_returns, confidence_level, time_horizon
                )
            elif method == "parametric":
                var_result = self._calculate_parametric_var(
                    portfolio_returns, confidence_level, time_horizon
                )
            elif method == "monte_carlo":
                var_result = self._calculate_monte_carlo_var(
                    returns_data, weights, confidence_level, time_horizon
                )
            else:
                return {"error": f"未知的 VaR 計算方法: {method}"}

            # 添加額外資訊
            var_result.update({
                "portfolio_id": portfolio_id,
                "portfolio_name": portfolio.name,
                "confidence_level": confidence_level,
                "time_horizon": time_horizon,
                "method": method,
                "portfolio_value": portfolio.total_value,
                "calculated_at": datetime.now().isoformat()
            })

            return var_result

        except Exception as e:
            logger.error(f"計算 VaR 錯誤: {e}")
            return {"error": f"VaR 計算失敗: {e}"}

    def _calculate_historical_var(
        self,
        returns: pd.Series,
        confidence_level: float,
        time_horizon: int
    ) -> Dict[str, float]:
        """歷史模擬法計算 VaR"""
        # 調整時間範圍
        adjusted_returns = returns * np.sqrt(time_horizon)

        # 計算 VaR
        var_value = np.percentile(adjusted_returns, confidence_level * 100)

        # 計算 CVaR (Expected Shortfall)
        cvar_value = adjusted_returns[adjusted_returns <= var_value].mean()

        return {
            "var": abs(var_value),
            "cvar": abs(cvar_value),
            "var_percentage": abs(var_value),
            "cvar_percentage": abs(cvar_value)
        }

    def _calculate_parametric_var(
        self,
        returns: pd.Series,
        confidence_level: float,
        time_horizon: int
    ) -> Dict[str, float]:
        """參數法計算 VaR（假設正態分佈）"""
        from scipy import stats

        # 計算統計量
        mean_return = returns.mean()
        std_return = returns.std()

        # 調整時間範圍
        adjusted_mean = mean_return * time_horizon
        adjusted_std = std_return * np.sqrt(time_horizon)

        # 計算 VaR
        z_score = stats.norm.ppf(confidence_level)
        var_value = -(adjusted_mean + z_score * adjusted_std)

        # 計算 CVaR（正態分佈下的解析解）
        cvar_value = -(adjusted_mean - adjusted_std * stats.norm.pdf(z_score) / confidence_level)

        return {
            "var": max(0, var_value),
            "cvar": max(0, cvar_value),
            "var_percentage": max(0, var_value),
            "cvar_percentage": max(0, cvar_value)
        }

    def _calculate_monte_carlo_var(
        self,
        returns_data: pd.DataFrame,
        weights: np.ndarray,
        confidence_level: float,
        time_horizon: int,
        n_simulations: int = 10000
    ) -> Dict[str, float]:
        """蒙地卡羅模擬法計算 VaR"""
        # 計算協方差矩陣
        cov_matrix = returns_data.cov().values
        mean_returns = returns_data.mean().values

        # 蒙地卡羅模擬
        simulated_returns = []

        # 使用加密安全的隨機數生成器
        rng = np.random.default_rng()  # 使用新的隨機數生成器

        for _ in range(n_simulations):
            # 生成隨機收益率 - 使用加密安全的隨機數生成器
            random_returns = rng.multivariate_normal(
                mean_returns * time_horizon,
                cov_matrix * time_horizon
            )

            # 計算投資組合收益率
            portfolio_return = np.dot(weights, random_returns)
            simulated_returns.append(portfolio_return)

        simulated_returns = np.array(simulated_returns)

        # 計算 VaR 和 CVaR
        var_value = np.percentile(simulated_returns, confidence_level * 100)
        cvar_value = simulated_returns[simulated_returns <= var_value].mean()

        return {
            "var": abs(var_value),
            "cvar": abs(cvar_value),
            "var_percentage": abs(var_value),
            "cvar_percentage": abs(cvar_value),
            "n_simulations": n_simulations
        }

    def calculate_risk_metrics(
        self,
        portfolio_id: str,
        benchmark_returns: pd.Series = None
    ) -> Dict[str, Any]:
        """計算綜合風險指標

        Args:
            portfolio_id: 投資組合ID
            benchmark_returns: 基準收益率

        Returns:
            風險指標字典
        """
        try:
            portfolio = self.core.get_portfolio(portfolio_id)
            if not portfolio:
                return {"error": f"投資組合不存在: {portfolio_id}"}

            # 獲取投資組合收益率
            symbols = portfolio.get_symbols()
            returns_data = self._get_portfolio_returns(symbols, days=252)

            if returns_data.empty:
                return {"error": "無法獲取收益率資料"}

            weights = np.array([h.weight for h in portfolio.holdings])
            portfolio_returns = (returns_data * weights).sum(axis=1)

            # 計算基本風險指標
            metrics = {
                "portfolio_id": portfolio_id,
                "portfolio_name": portfolio.name,
                "calculated_at": datetime.now().isoformat()
            }

            # 波動率
            metrics["daily_volatility"] = portfolio_returns.std()
            metrics["annual_volatility"] = portfolio_returns.std() * np.sqrt(252)

            # 最大回撤
            cumulative_returns = (1 + portfolio_returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - running_max) / running_max
            metrics["max_drawdown"] = drawdown.min()

            # VaR 指標
            var_5 = self._calculate_historical_var(portfolio_returns, 0.05, 1)
            var_1 = self._calculate_historical_var(portfolio_returns, 0.01, 1)

            metrics["var_5_percent"] = var_5["var"]
            metrics["cvar_5_percent"] = var_5["cvar"]
            metrics["var_1_percent"] = var_1["var"]
            metrics["cvar_1_percent"] = var_1["cvar"]

            # 下行風險
            negative_returns = portfolio_returns[portfolio_returns < 0]
            if len(negative_returns) > 0:
                metrics["downside_deviation"] = negative_returns.std() * np.sqrt(252)
                metrics["downside_frequency"] = len(negative_returns) / len(portfolio_returns)
            else:
                metrics["downside_deviation"] = 0.0
                metrics["downside_frequency"] = 0.0

            # 如果有基準，計算相對風險指標
            if benchmark_returns is not None and not benchmark_returns.empty:
                # 對齊時間序列
                aligned_data = pd.DataFrame({
                    'portfolio': portfolio_returns,
                    'benchmark': benchmark_returns
                }).dropna()

                if not aligned_data.empty:
                    excess_returns = aligned_data['portfolio'] - aligned_data['benchmark']
                    metrics["tracking_error"] = excess_returns.std() * np.sqrt(252)
                    metrics["information_ratio"] = (
                        excess_returns.mean() * 252 / metrics["tracking_error"]
                        if metrics["tracking_error"] > 0 else 0
                    )

                    # Beta
                    covariance = aligned_data['portfolio'].cov(aligned_data['benchmark'])
                    benchmark_variance = aligned_data['benchmark'].var()
                    metrics["beta"] = covariance / benchmark_variance if benchmark_variance > 0 else 1.0

            return metrics

        except Exception as e:
            logger.error(f"計算風險指標錯誤: {e}")
            return {"error": f"風險指標計算失敗: {e}"}

    def stress_test(
        self,
        portfolio_id: str,
        scenarios: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """投資組合壓力測試

        Args:
            portfolio_id: 投資組合ID
            scenarios: 壓力測試情境列表

        Returns:
            壓力測試結果
        """
        try:
            portfolio = self.core.get_portfolio(portfolio_id)
            if not portfolio:
                return {"error": f"投資組合不存在: {portfolio_id}"}

            if scenarios is None:
                # 預設壓力測試情境
                scenarios = [
                    {"name": "市場崩盤", "market_shock": -0.20, "volatility_shock": 2.0},
                    {"name": "溫和衰退", "market_shock": -0.10, "volatility_shock": 1.5},
                    {"name": "通膨上升", "market_shock": -0.05, "volatility_shock": 1.2},
                    {"name": "利率上升", "market_shock": -0.08, "volatility_shock": 1.3},
                ]

            # 獲取當前投資組合資料
            symbols = portfolio.get_symbols()
            returns_data = self._get_portfolio_returns(symbols, days=252)
            weights = np.array([h.weight for h in portfolio.holdings])

            stress_results = []

            for scenario in scenarios:
                scenario_result = {
                    "scenario_name": scenario["name"],
                    "market_shock": scenario.get("market_shock", 0),
                    "volatility_shock": scenario.get("volatility_shock", 1),
                }

                # 應用壓力情境
                shocked_returns = returns_data.copy()

                # 市場衝擊
                if "market_shock" in scenario:
                    shocked_returns += scenario["market_shock"] / 252  # 分散到每日

                # 波動率衝擊
                if "volatility_shock" in scenario:
                    shocked_returns *= scenario["volatility_shock"]

                # 計算壓力情境下的投資組合表現
                portfolio_returns = (shocked_returns * weights).sum(axis=1)

                # 計算壓力測試指標
                scenario_result.update({
                    "portfolio_return": portfolio_returns.sum(),
                    "portfolio_volatility": portfolio_returns.std() * np.sqrt(252),
                    "max_drawdown": self._calculate_max_drawdown(portfolio_returns),
                    "var_5_percent": abs(np.percentile(portfolio_returns, 5)),
                    "worst_day": portfolio_returns.min(),
                    "best_day": portfolio_returns.max(),
                })

                # 計算價值變化
                portfolio_value_change = scenario_result["portfolio_return"] * portfolio.total_value
                scenario_result["portfolio_value_change"] = portfolio_value_change
                scenario_result["portfolio_value_after"] = portfolio.total_value + portfolio_value_change

                stress_results.append(scenario_result)

            return {
                "portfolio_id": portfolio_id,
                "portfolio_name": portfolio.name,
                "current_value": portfolio.total_value,
                "stress_test_date": datetime.now().isoformat(),
                "scenarios": stress_results
            }

        except Exception as e:
            logger.error(f"壓力測試錯誤: {e}")
            return {"error": f"壓力測試失敗: {e}"}

    def _get_portfolio_returns(self, symbols: List[str], days: int = 252) -> pd.DataFrame:
        """獲取投資組合收益率資料（模擬）"""
        # 這裡使用模擬資料，實際應用中應該從資料庫或API獲取真實資料
        returns_data = {}

        for symbol in symbols:
            # 使用加密安全的隨機數生成器
            # 為每個股票使用一致的種子，但使用安全的隨機數生成器
            seed = hash(symbol) % 2**32
            rng = np.random.default_rng(seed)  # 使用新的隨機數生成器
            daily_returns = rng.normal(0.0008, 0.02, days)  # 年化8%收益，20%波動
            returns_data[symbol] = daily_returns

        return pd.DataFrame(returns_data)

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """計算最大回撤"""
        cumulative_returns = (1 + returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        return drawdown.min()
