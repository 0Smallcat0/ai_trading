"""
風險值 (VaR) 計算模組

此模組實現了風險值和條件風險值的計算功能。
"""

from typing import Dict, Optional

import numpy as np
import pandas as pd

from src.core.logger import logger


class ValueAtRisk:
    """
    風險值 (VaR) 計算器

    計算投資組合的風險值。
    """

    def __init__(
        self, returns: pd.DataFrame, weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化風險值計算器

        Args:
            returns: 收益率 DataFrame，每列為一個資產
            weights: 權重字典，資產代碼到權重的映射
        """
        self.returns = returns

        # 如果沒有提供權重，則使用等權重
        if weights is None:
            self.weights = {col: 1.0 / len(returns.columns) for col in returns.columns}
        else:
            # 確保權重和為 1
            total_weight = sum(weights.values())
            self.weights = (
                {k: v / total_weight for k, v in weights.items()}
                if total_weight > 0
                else weights
            )

        logger.info(
            "初始化風險值計算器: 資產數量 %s, 數據點數量 %s",
            len(returns.columns),
            len(returns),
        )

    def calculate_var_historical(self, confidence: float = 0.95) -> float:
        """
        使用歷史模擬法計算風險值

        Args:
            confidence: 置信水平，例如 0.95 表示 95%

        Returns:
            float: 風險值
        """
        # 計算投資組合收益率
        portfolio_returns = self._calculate_portfolio_returns()

        # 計算分位數
        var = portfolio_returns.quantile(1 - confidence)

        return abs(var)

    def calculate_var_parametric(self, confidence: float = 0.95) -> float:
        """
        使用參數法計算風險值

        Args:
            confidence: 置信水平，例如 0.95 表示 95%

        Returns:
            float: 風險值
        """
        # 計算投資組合收益率
        portfolio_returns = self._calculate_portfolio_returns()

        # 計算平均收益率和標準差
        mean_return = portfolio_returns.mean()
        std_return = portfolio_returns.std()

        # 計算 z 值
        z = np.abs(np.percentile(np.random.normal(0, 1, 10000), (1 - confidence) * 100))

        # 計算風險值
        var = mean_return - z * std_return

        return abs(var)

    def calculate_var_monte_carlo(
        self, confidence: float = 0.95, simulations: int = 10000
    ) -> float:
        """
        使用蒙特卡洛模擬法計算風險值

        Args:
            confidence: 置信水平，例如 0.95 表示 95%
            simulations: 模擬次數

        Returns:
            float: 風險值
        """
        # 計算投資組合收益率
        portfolio_returns = self._calculate_portfolio_returns()

        # 計算平均收益率和標準差
        mean_return = portfolio_returns.mean()
        std_return = portfolio_returns.std()

        # 使用加密安全的隨機數生成器
        rng = np.random.default_rng()
        random_returns = rng.normal(mean_return, std_return, simulations)

        # 計算分位數
        var = np.percentile(random_returns, (1 - confidence) * 100)

        return abs(var)

    def _calculate_portfolio_returns(self) -> pd.Series:
        """
        計算投資組合收益率

        Returns:
            pd.Series: 投資組合收益率
        """
        # 確保所有資產都在收益率 DataFrame 中
        weights = {k: v for k, v in self.weights.items() if k in self.returns.columns}

        # 計算投資組合收益率
        portfolio_returns = pd.Series(0.0, index=self.returns.index)
        for asset, weight in weights.items():
            portfolio_returns += self.returns[asset] * weight

        return portfolio_returns


class ConditionalValueAtRisk:
    """
    條件風險值 (CVaR) 計算器

    計算投資組合的條件風險值。
    """

    def __init__(
        self, returns: pd.DataFrame, weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化條件風險值計算器

        Args:
            returns: 收益率 DataFrame，每列為一個資產
            weights: 權重字典，資產代碼到權重的映射
        """
        self.returns = returns

        # 如果沒有提供權重，則使用等權重
        if weights is None:
            self.weights = {col: 1.0 / len(returns.columns) for col in returns.columns}
        else:
            # 確保權重和為 1
            total_weight = sum(weights.values())
            self.weights = (
                {k: v / total_weight for k, v in weights.items()}
                if total_weight > 0
                else weights
            )

        # 創建風險值計算器
        self.var_calculator = ValueAtRisk(returns, weights)

        logger.info(
            "初始化條件風險值計算器: 資產數量 %s, 數據點數量 %s",
            len(returns.columns),
            len(returns),
        )

    def calculate_cvar_historical(self, confidence: float = 0.95) -> float:
        """
        使用歷史模擬法計算條件風險值

        Args:
            confidence: 置信水平，例如 0.95 表示 95%

        Returns:
            float: 條件風險值
        """
        # 計算投資組合收益率
        portfolio_returns = self._calculate_portfolio_returns()

        # 計算風險值
        var = self.var_calculator.calculate_var_historical(confidence)

        # 計算條件風險值
        cvar = portfolio_returns[portfolio_returns <= -var].mean()

        return abs(cvar)

    def calculate_cvar_parametric(self, confidence: float = 0.95) -> float:
        """
        使用參數法計算條件風險值

        Args:
            confidence: 置信水平，例如 0.95 表示 95%

        Returns:
            float: 條件風險值
        """
        # 計算投資組合收益率
        portfolio_returns = self._calculate_portfolio_returns()

        # 計算平均收益率和標準差
        mean_return = portfolio_returns.mean()
        std_return = portfolio_returns.std()

        # 計算 z 值 - 使用加密安全的隨機數生成器
        rng = np.random.default_rng()
        z = np.abs(np.percentile(rng.normal(0, 1, 10000), (1 - confidence) * 100))

        # 計算條件風險值
        cvar = mean_return - std_return * np.exp(-(z**2) / 2) / (
            (1 - confidence) * np.sqrt(2 * np.pi)
        )

        return abs(cvar)

    def _calculate_portfolio_returns(self) -> pd.Series:
        """
        計算投資組合收益率

        Returns:
            pd.Series: 投資組合收益率
        """
        # 確保所有資產都在收益率 DataFrame 中
        weights = {k: v for k, v in self.weights.items() if k in self.returns.columns}

        # 計算投資組合收益率
        portfolio_returns = pd.Series(0.0, index=self.returns.index)
        for asset, weight in weights.items():
            portfolio_returns += self.returns[asset] * weight

        return portfolio_returns
