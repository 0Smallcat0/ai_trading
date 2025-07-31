"""
基礎風險指標計算模組

此模組實現了基礎的風險指標計算功能。
"""

from typing import Dict

import numpy as np
import pandas as pd

from src.core.logger import logger


class RiskMetricsCalculator:
    """
    風險指標計算器

    計算各種風險指標。
    """

    def __init__(self, returns: pd.Series, risk_free_rate: float = 0.0):
        """
        初始化風險指標計算器

        Args:
            returns: 收益率序列
            risk_free_rate: 無風險利率，例如 0.02 表示 2%
        """
        self.returns = returns
        self.risk_free_rate = risk_free_rate

        logger.info(
            "初始化風險指標計算器: 數據點數量 %s, 無風險利率 %s",
            len(returns),
            f"{risk_free_rate:.2%}",
        )

    def calculate_volatility(self, annualize: bool = True) -> float:
        """
        計算波動率

        Args:
            annualize: 是否年化

        Returns:
            float: 波動率
        """
        # 計算標準差
        volatility = self.returns.std()

        # 年化
        if annualize:
            # 假設 252 個交易日
            volatility = volatility * np.sqrt(252)

        return volatility

    def calculate_sharpe_ratio(self, annualize: bool = True) -> float:
        """
        計算夏普比率

        Args:
            annualize: 是否年化

        Returns:
            float: 夏普比率
        """
        # 計算超額收益率
        excess_returns = self.returns - self.risk_free_rate / 252

        # 計算平均超額收益率
        mean_excess_return = excess_returns.mean()

        # 計算波動率
        volatility = self.calculate_volatility(annualize=False)

        # 計算夏普比率
        sharpe_ratio = mean_excess_return / volatility if volatility > 0 else 0.0

        # 年化
        if annualize:
            sharpe_ratio = sharpe_ratio * np.sqrt(252)

        return sharpe_ratio

    def calculate_sortino_ratio(self, annualize: bool = True) -> float:
        """
        計算索提諾比率

        Args:
            annualize: 是否年化

        Returns:
            float: 索提諾比率
        """
        # 計算超額收益率
        excess_returns = self.returns - self.risk_free_rate / 252

        # 計算平均超額收益率
        mean_excess_return = excess_returns.mean()

        # 計算下行波動率
        downside_returns = excess_returns[excess_returns < 0]
        downside_volatility = (
            downside_returns.std() if len(downside_returns) > 0 else 0.0
        )

        # 計算索提諾比率
        sortino_ratio = (
            mean_excess_return / downside_volatility if downside_volatility > 0 else 0.0
        )

        # 年化
        if annualize:
            sortino_ratio = sortino_ratio * np.sqrt(252)

        return sortino_ratio

    def calculate_max_drawdown(self) -> float:
        """
        計算最大回撤

        Returns:
            float: 最大回撤
        """
        # 計算累積收益率
        cumulative_returns = (1 + self.returns).cumprod()

        # 計算歷史最高點
        running_max = cumulative_returns.cummax()

        # 計算回撤
        drawdown = (cumulative_returns / running_max) - 1

        # 計算最大回撤
        max_drawdown = drawdown.min()

        return abs(max_drawdown)

    def calculate_calmar_ratio(self, annualize: bool = True) -> float:
        """
        計算卡爾馬比率

        Args:
            annualize: 是否年化

        Returns:
            float: 卡爾馬比率
        """
        # 計算年化收益率
        annual_return = self.returns.mean() * 252

        # 計算最大回撤
        max_drawdown = self.calculate_max_drawdown()

        # 計算卡爾馬比率
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0.0

        return calmar_ratio

    def calculate_var(self, confidence: float = 0.95) -> float:
        """
        計算風險值 (VaR)

        Args:
            confidence: 置信水平，例如 0.95 表示 95%

        Returns:
            float: 風險值
        """
        # 計算分位數
        var = self.returns.quantile(1 - confidence)

        return abs(var)

    def calculate_cvar(self, confidence: float = 0.95) -> float:
        """
        計算條件風險值 (CVaR)

        Args:
            confidence: 置信水平，例如 0.95 表示 95%

        Returns:
            float: 條件風險值
        """
        # 計算風險值
        var = self.calculate_var(confidence)

        # 計算條件風險值
        cvar = self.returns[self.returns <= -var].mean()

        return abs(cvar)

    def calculate_omega_ratio(self, threshold: float = 0.0) -> float:
        """
        計算歐米茄比率

        Args:
            threshold: 閾值，例如 0.0 表示 0%

        Returns:
            float: 歐米茄比率
        """
        # 計算超過閾值的收益
        gains = self.returns[self.returns > threshold] - threshold

        # 計算低於閾值的損失
        losses = threshold - self.returns[self.returns <= threshold]

        # 計算歐米茄比率
        omega_ratio = gains.sum() / losses.sum() if losses.sum() > 0 else float("inf")

        return omega_ratio

    def calculate_all_metrics(self) -> Dict[str, float]:
        """
        計算所有風險指標

        Returns:
            Dict[str, float]: 風險指標字典
        """
        return {
            "volatility": self.calculate_volatility(),
            "sharpe_ratio": self.calculate_sharpe_ratio(),
            "sortino_ratio": self.calculate_sortino_ratio(),
            "max_drawdown": self.calculate_max_drawdown(),
            "calmar_ratio": self.calculate_calmar_ratio(),
            "var_95": self.calculate_var(0.95),
            "cvar_95": self.calculate_cvar(0.95),
            "omega_ratio": self.calculate_omega_ratio(),
        }
