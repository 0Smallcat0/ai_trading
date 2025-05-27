"""
波動率計算模組

此模組實現了波動率計算功能。
"""

from typing import Dict, Optional

import numpy as np
import pandas as pd

from src.core.logger import logger


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
            "初始化波動率計算器: 資產數量 %s, 數據點數量 %s",
            len(returns.columns),
            len(returns),
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

    def calculate_ewm_volatility(
        self, span: int = 20, annualize: bool = True
    ) -> pd.Series:
        """
        計算指數加權移動平均波動率

        Args:
            span: 跨度
            annualize: 是否年化

        Returns:
            pd.Series: 指數加權移動平均波動率
        """
        # 計算投資組合收益率
        portfolio_returns = self._calculate_portfolio_returns()

        # 計算指數加權移動平均標準差
        ewm_volatility = portfolio_returns.ewm(span=span).std()

        # 年化
        if annualize:
            # 假設 252 個交易日
            ewm_volatility = ewm_volatility * np.sqrt(252)

        return ewm_volatility

    def calculate_garch_volatility(self, p: int = 1, q: int = 1) -> pd.Series:
        """
        計算 GARCH 模型波動率

        Args:
            p: GARCH 模型的 p 參數
            q: GARCH 模型的 q 參數

        Returns:
            pd.Series: GARCH 波動率

        Note:
            這是一個簡化的 GARCH 實現，實際應用中建議使用專業的 GARCH 庫
        """
        # 計算投資組合收益率
        portfolio_returns = self._calculate_portfolio_returns()

        # 簡化的 GARCH(1,1) 實現
        returns_squared = portfolio_returns**2
        
        # 初始化參數
        omega = 0.01  # 常數項
        alpha = 0.1   # ARCH 項係數
        beta = 0.8    # GARCH 項係數
        
        # 初始化條件方差
        conditional_variance = pd.Series(index=portfolio_returns.index, dtype=float)
        conditional_variance.iloc[0] = returns_squared.iloc[0]
        
        # 計算條件方差
        for i in range(1, len(portfolio_returns)):
            conditional_variance.iloc[i] = (
                omega + 
                alpha * returns_squared.iloc[i-1] + 
                beta * conditional_variance.iloc[i-1]
            )
        
        # 計算波動率（條件方差的平方根）
        garch_volatility = np.sqrt(conditional_variance)
        
        # 年化
        garch_volatility = garch_volatility * np.sqrt(252)

        return garch_volatility

    def calculate_realized_volatility(self, window: int = 252) -> pd.Series:
        """
        計算已實現波動率

        Args:
            window: 計算窗口

        Returns:
            pd.Series: 已實現波動率
        """
        # 計算投資組合收益率
        portfolio_returns = self._calculate_portfolio_returns()

        # 計算滾動已實現波動率
        realized_volatility = portfolio_returns.rolling(window=window).apply(
            lambda x: np.sqrt(np.sum(x**2) * 252)
        )

        return realized_volatility

    def calculate_volatility_metrics(self) -> Dict[str, float]:
        """
        計算波動率相關指標

        Returns:
            Dict[str, float]: 波動率指標字典
        """
        portfolio_returns = self._calculate_portfolio_returns()
        
        return {
            "volatility": self.calculate_volatility(),
            "volatility_daily": self.calculate_volatility(annualize=False),
            "volatility_rolling_20": self.calculate_rolling_volatility(20).iloc[-1],
            "volatility_rolling_60": self.calculate_rolling_volatility(60).iloc[-1],
            "volatility_ewm_20": self.calculate_ewm_volatility(20).iloc[-1],
            "skewness": portfolio_returns.skew(),
            "kurtosis": portfolio_returns.kurtosis(),
        }

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
