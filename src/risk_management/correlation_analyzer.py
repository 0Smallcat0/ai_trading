"""
相關性分析模組

此模組實現了投資組合中股票之間的相關性分析功能。
"""

from typing import Dict, List, Tuple

import pandas as pd

from src.core.logger import logger


class CorrelationAnalyzer:
    """
    相關性分析器

    分析投資組合中股票之間的相關性。
    """

    def __init__(self, price_data: Dict[str, pd.DataFrame], lookback_period: int = 252):
        """
        初始化相關性分析器

        Args:
            price_data: 價格資料，股票代碼到價格資料的映射
            lookback_period: 回顧期間
        """
        self.price_data = price_data
        self.lookback_period = lookback_period

        # 計算相關性矩陣
        self.correlation_matrix = self._calculate_correlation_matrix()

        logger.info(
            "初始化相關性分析器: 股票數量 %s, 回顧期間 %s",
            len(price_data),
            lookback_period,
        )

    def _calculate_correlation_matrix(self) -> pd.DataFrame:
        """
        計算相關性矩陣

        Returns:
            pd.DataFrame: 相關性矩陣
        """
        # 提取收益率
        returns = {}
        for symbol, data in self.price_data.items():
            if "close" in data.columns:
                # 使用最近的數據
                recent_data = (
                    data.iloc[-self.lookback_period :]
                    if len(data) > self.lookback_period
                    else data
                )
                returns[symbol] = recent_data["close"].pct_change().dropna()

        # 創建收益率 DataFrame
        returns_df = pd.DataFrame(returns)

        # 計算相關性矩陣
        correlation_matrix = returns_df.corr()

        return correlation_matrix

    def get_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        獲取兩支股票之間的相關性

        Args:
            symbol1: 第一支股票代碼
            symbol2: 第二支股票代碼

        Returns:
            float: 相關性係數
        """
        if (
            symbol1 not in self.correlation_matrix.index
            or symbol2 not in self.correlation_matrix.columns
        ):
            return 0.0

        return self.correlation_matrix.loc[symbol1, symbol2]

    def get_average_correlation(self, symbol: str) -> float:
        """
        獲取一支股票與其他所有股票的平均相關性

        Args:
            symbol: 股票代碼

        Returns:
            float: 平均相關性係數
        """
        if symbol not in self.correlation_matrix.index:
            return 0.0

        # 獲取與該股票的所有相關性
        correlations = self.correlation_matrix.loc[symbol].drop(symbol)

        # 計算平均值
        return correlations.mean()

    def get_highly_correlated_pairs(
        self, threshold: float = 0.7
    ) -> List[Tuple[str, str, float]]:
        """
        獲取高度相關的股票對

        Args:
            threshold: 相關性閾值

        Returns:
            List[Tuple[str, str, float]]: 高度相關的股票對列表，每個元素為 (股票1, 股票2, 相關性)
        """
        pairs = []

        # 獲取上三角矩陣的索引
        symbols = self.correlation_matrix.index
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                symbol1 = symbols[i]
                symbol2 = symbols[j]
                correlation = self.correlation_matrix.loc[symbol1, symbol2]

                # 檢查是否超過閾值
                if abs(correlation) >= threshold:
                    pairs.append((symbol1, symbol2, correlation))

        # 按相關性降序排序
        pairs.sort(key=lambda x: abs(x[2]), reverse=True)

        return pairs

    def get_correlation_matrix(self) -> pd.DataFrame:
        """
        獲取相關性矩陣

        Returns:
            pd.DataFrame: 相關性矩陣
        """
        return self.correlation_matrix.copy()

    def get_correlation_stats(self) -> Dict[str, float]:
        """
        獲取相關性統計信息

        Returns:
            Dict[str, float]: 相關性統計信息
        """
        # 獲取上三角矩陣的相關性值（排除對角線）
        correlations = []
        symbols = self.correlation_matrix.index
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                correlation = self.correlation_matrix.iloc[i, j]
                if not pd.isna(correlation):
                    correlations.append(correlation)

        if not correlations:
            return {
                "mean_correlation": 0.0,
                "median_correlation": 0.0,
                "max_correlation": 0.0,
                "min_correlation": 0.0,
                "std_correlation": 0.0,
            }

        correlations_series = pd.Series(correlations)

        return {
            "mean_correlation": correlations_series.mean(),
            "median_correlation": correlations_series.median(),
            "max_correlation": correlations_series.max(),
            "min_correlation": correlations_series.min(),
            "std_correlation": correlations_series.std(),
        }

    def find_diversification_candidates(
        self,
        current_portfolio: List[str],
        candidates: List[str],
        max_correlation: float = 0.5,
    ) -> List[str]:
        """
        尋找分散化候選股票

        Args:
            current_portfolio: 當前投資組合股票列表
            candidates: 候選股票列表
            max_correlation: 最大相關性閾值

        Returns:
            List[str]: 建議的分散化候選股票
        """
        diversification_candidates = []

        for candidate in candidates:
            if candidate in current_portfolio:
                continue

            # 計算與投資組合中所有股票的平均相關性
            correlations = []
            for portfolio_stock in current_portfolio:
                correlation = self.get_correlation(candidate, portfolio_stock)
                if not pd.isna(correlation):
                    correlations.append(abs(correlation))

            if correlations:
                avg_correlation = sum(correlations) / len(correlations)
                if avg_correlation <= max_correlation:
                    diversification_candidates.append(candidate)

        # 按平均相關性排序（越低越好）
        diversification_candidates.sort(
            key=lambda x: sum(
                abs(self.get_correlation(x, stock))
                for stock in current_portfolio
                if not pd.isna(self.get_correlation(x, stock))
            )
            / len(current_portfolio)
        )

        return diversification_candidates

    def update_price_data(self, symbol: str, data: pd.DataFrame) -> None:
        """
        更新價格資料

        Args:
            symbol: 股票代碼
            data: 價格資料
        """
        self.price_data[symbol] = data

        # 重新計算相關性矩陣
        self.correlation_matrix = self._calculate_correlation_matrix()

        logger.info("更新價格資料: %s", symbol)

    def add_stock(self, symbol: str, data: pd.DataFrame) -> None:
        """
        添加新股票

        Args:
            symbol: 股票代碼
            data: 價格資料
        """
        if symbol not in self.price_data:
            self.price_data[symbol] = data
            # 重新計算相關性矩陣
            self.correlation_matrix = self._calculate_correlation_matrix()
            logger.info("添加新股票: %s", symbol)
        else:
            logger.warning("股票 %s 已存在", symbol)

    def remove_stock(self, symbol: str) -> None:
        """
        移除股票

        Args:
            symbol: 股票代碼
        """
        if symbol in self.price_data:
            del self.price_data[symbol]
            # 重新計算相關性矩陣
            self.correlation_matrix = self._calculate_correlation_matrix()
            logger.info("移除股票: %s", symbol)
        else:
            logger.warning("股票 %s 不存在", symbol)

    def get_portfolio_correlation_risk(
        self, portfolio_weights: Dict[str, float]
    ) -> float:
        """
        計算投資組合相關性風險

        Args:
            portfolio_weights: 投資組合權重

        Returns:
            float: 相關性風險得分，範圍 0-1，越高風險越大
        """
        if not portfolio_weights:
            return 0.0

        # 計算加權平均相關性
        total_correlation = 0.0
        total_weight = 0.0

        symbols = list(portfolio_weights.keys())
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                if i != j:
                    weight1 = portfolio_weights[symbol1]
                    weight2 = portfolio_weights[symbol2]
                    correlation = abs(self.get_correlation(symbol1, symbol2))

                    if not pd.isna(correlation):
                        total_correlation += weight1 * weight2 * correlation
                        total_weight += weight1 * weight2

        if total_weight == 0:
            return 0.0

        avg_correlation = total_correlation / total_weight
        return min(1.0, max(0.0, avg_correlation))
