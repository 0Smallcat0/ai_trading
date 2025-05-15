"""
風險指標計算模組

此模組實現了各種風險指標的計算，包括 VaR、最大回撤、波動率等。
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime, timedelta

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
            f"初始化風險指標計算器: 數據點數量 {len(returns)}, 無風險利率 {risk_free_rate:.2%}"
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
            f"初始化風險值計算器: 資產數量 {len(returns.columns)}, 數據點數量 {len(returns)}"
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

        # 生成隨機收益率
        random_returns = np.random.normal(mean_return, std_return, simulations)

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
            f"初始化條件風險值計算器: 資產數量 {len(returns.columns)}, 數據點數量 {len(returns)}"
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

        # 計算 z 值
        z = np.abs(np.percentile(np.random.normal(0, 1, 10000), (1 - confidence) * 100))

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


class MaximumDrawdown:
    """
    最大回撤計算器

    計算投資組合的最大回撤。
    """

    def __init__(
        self, returns: pd.DataFrame, weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化最大回撤計算器

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
            f"初始化最大回撤計算器: 資產數量 {len(returns.columns)}, 數據點數量 {len(returns)}"
        )

    def calculate_max_drawdown(self) -> float:
        """
        計算最大回撤

        Returns:
            float: 最大回撤
        """
        # 計算投資組合收益率
        portfolio_returns = self._calculate_portfolio_returns()

        # 計算累積收益率
        cumulative_returns = (1 + portfolio_returns).cumprod()

        # 計算歷史最高點
        running_max = cumulative_returns.cummax()

        # 計算回撤
        drawdown = (cumulative_returns / running_max) - 1

        # 計算最大回撤
        max_drawdown = drawdown.min()

        return abs(max_drawdown)

    def calculate_drawdown_periods(self) -> List[Dict[str, Any]]:
        """
        計算回撤期間

        Returns:
            List[Dict[str, Any]]: 回撤期間列表，每個元素包含開始日期、結束日期、回撤幅度和持續天數
        """
        # 計算投資組合收益率
        portfolio_returns = self._calculate_portfolio_returns()

        # 計算累積收益率
        cumulative_returns = (1 + portfolio_returns).cumprod()

        # 計算歷史最高點
        running_max = cumulative_returns.cummax()

        # 計算回撤
        drawdown = (cumulative_returns / running_max) - 1

        # 找出回撤期間
        drawdown_periods = []
        in_drawdown = False
        start_date = None
        peak_value = None

        for date, value in drawdown.items():
            if value < 0 and not in_drawdown:
                # 開始回撤
                in_drawdown = True
                start_date = date
                peak_value = running_max[date]
            elif value == 0 and in_drawdown:
                # 結束回撤
                in_drawdown = False
                end_date = date

                # 計算回撤幅度和持續天數
                trough_value = cumulative_returns.loc[start_date:end_date].min()
                drawdown_amount = (trough_value / peak_value) - 1
                duration = (end_date - start_date).days

                # 添加到回撤期間列表
                drawdown_periods.append(
                    {
                        "start_date": start_date,
                        "end_date": end_date,
                        "drawdown": abs(drawdown_amount),
                        "duration": duration,
                    }
                )

        # 如果仍在回撤中，則添加當前回撤
        if in_drawdown:
            end_date = drawdown.index[-1]
            trough_value = cumulative_returns.loc[start_date:end_date].min()
            drawdown_amount = (trough_value / peak_value) - 1
            duration = (end_date - start_date).days

            drawdown_periods.append(
                {
                    "start_date": start_date,
                    "end_date": end_date,
                    "drawdown": abs(drawdown_amount),
                    "duration": duration,
                }
            )

        # 按回撤幅度降序排序
        drawdown_periods.sort(key=lambda x: x["drawdown"], reverse=True)

        return drawdown_periods

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


class VolatilityCalculator:
    """
    波動率計算器

    計算投資組合的波動率。
    """

    def __init__(
        self, returns: pd.DataFrame, weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化波動率計算器

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
            f"初始化波動率計算器: 資產數量 {len(returns.columns)}, 數據點數量 {len(returns)}"
        )

    def calculate_volatility(self, annualize: bool = True) -> float:
        """
        計算波動率

        Args:
            annualize: 是否年化

        Returns:
            float: 波動率
        """
        # 計算投資組合收益率
        portfolio_returns = self._calculate_portfolio_returns()

        # 計算標準差
        volatility = portfolio_returns.std()

        # 年化
        if annualize:
            # 假設 252 個交易日
            volatility = volatility * np.sqrt(252)

        return volatility

    def calculate_asset_volatilities(self, annualize: bool = True) -> Dict[str, float]:
        """
        計算各資產的波動率

        Args:
            annualize: 是否年化

        Returns:
            Dict[str, float]: 資產代碼到波動率的映射
        """
        # 計算各資產的標準差
        volatilities = self.returns.std()

        # 年化
        if annualize:
            # 假設 252 個交易日
            volatilities = volatilities * np.sqrt(252)

        return volatilities.to_dict()

    def calculate_rolling_volatility(
        self, window: int = 20, annualize: bool = True
    ) -> pd.Series:
        """
        計算滾動波動率

        Args:
            window: 窗口大小
            annualize: 是否年化

        Returns:
            pd.Series: 滾動波動率
        """
        # 計算投資組合收益率
        portfolio_returns = self._calculate_portfolio_returns()

        # 計算滾動標準差
        rolling_volatility = portfolio_returns.rolling(window=window).std()

        # 年化
        if annualize:
            # 假設 252 個交易日
            rolling_volatility = rolling_volatility * np.sqrt(252)

        return rolling_volatility

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
