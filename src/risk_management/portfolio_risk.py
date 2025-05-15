"""
投資組合風險管理模組

此模組實現了投資組合級別的風險管理策略，包括分散化、相關性分析和風險平價等。
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.core.logger import logger


class PortfolioRiskManager:
    """
    投資組合風險管理器

    管理投資組合級別的風險，包括分散化、相關性和集中度等。
    """

    def __init__(
        self, max_position_percent: float = 0.2, max_sector_percent: float = 0.4
    ):
        """
        初始化投資組合風險管理器

        Args:
            max_position_percent: 單一倉位最大百分比，例如 0.2 表示 20%
            max_sector_percent: 單一行業最大百分比，例如 0.4 表示 40%
        """
        self.max_position_percent = min(abs(max_position_percent), 1.0)
        self.max_sector_percent = min(abs(max_sector_percent), 1.0)

        # 投資組合持倉
        self.positions: Dict[str, Dict[str, Any]] = {}

        # 行業分類
        self.sector_mapping: Dict[str, str] = {}

        logger.info(
            f"初始化投資組合風險管理器: 單一倉位最大 {self.max_position_percent:.2%}, 單一行業最大 {self.max_sector_percent:.2%}"
        )

    def add_position(
        self, symbol: str, value: float, sector: Optional[str] = None
    ) -> bool:
        """
        添加倉位

        Args:
            symbol: 股票代碼
            value: 倉位價值
            sector: 行業分類

        Returns:
            bool: 是否成功添加
        """
        # 檢查是否已存在
        if symbol in self.positions:
            logger.warning(f"倉位 {symbol} 已存在，請使用 update_position 方法更新")
            return False

        # 添加倉位
        self.positions[symbol] = {"value": value, "sector": sector}

        # 更新行業映射
        if sector:
            self.sector_mapping[symbol] = sector

        logger.info(f"添加倉位: {symbol}, 價值: {value}, 行業: {sector}")
        return True

    def update_position(
        self, symbol: str, value: float, sector: Optional[str] = None
    ) -> bool:
        """
        更新倉位

        Args:
            symbol: 股票代碼
            value: 倉位價值
            sector: 行業分類

        Returns:
            bool: 是否成功更新
        """
        # 檢查是否存在
        if symbol not in self.positions:
            logger.warning(f"倉位 {symbol} 不存在，請使用 add_position 方法添加")
            return False

        # 更新倉位
        self.positions[symbol]["value"] = value

        # 更新行業
        if sector:
            self.positions[symbol]["sector"] = sector
            self.sector_mapping[symbol] = sector

        logger.info(f"更新倉位: {symbol}, 價值: {value}, 行業: {sector}")
        return True

    def remove_position(self, symbol: str) -> bool:
        """
        移除倉位

        Args:
            symbol: 股票代碼

        Returns:
            bool: 是否成功移除
        """
        # 檢查是否存在
        if symbol not in self.positions:
            logger.warning(f"倉位 {symbol} 不存在")
            return False

        # 移除倉位
        del self.positions[symbol]

        # 移除行業映射
        if symbol in self.sector_mapping:
            del self.sector_mapping[symbol]

        logger.info(f"移除倉位: {symbol}")
        return True

    def get_portfolio_value(self) -> float:
        """
        獲取投資組合總價值

        Returns:
            float: 投資組合總價值
        """
        return sum(position["value"] for position in self.positions.values())

    def get_position_weights(self) -> Dict[str, float]:
        """
        獲取倉位權重

        Returns:
            Dict[str, float]: 倉位權重字典
        """
        portfolio_value = self.get_portfolio_value()
        if portfolio_value == 0:
            return {symbol: 0.0 for symbol in self.positions}

        return {
            symbol: position["value"] / portfolio_value
            for symbol, position in self.positions.items()
        }

    def get_sector_weights(self) -> Dict[str, float]:
        """
        獲取行業權重

        Returns:
            Dict[str, float]: 行業權重字典
        """
        portfolio_value = self.get_portfolio_value()
        if portfolio_value == 0:
            return {}

        # 計算每個行業的總價值
        sector_values = {}
        for symbol, position in self.positions.items():
            sector = position.get("sector")
            if sector:
                if sector not in sector_values:
                    sector_values[sector] = 0.0
                sector_values[sector] += position["value"]

        # 計算行業權重
        return {
            sector: value / portfolio_value for sector, value in sector_values.items()
        }

    def check_position_limit(self, symbol: str, value: float) -> bool:
        """
        檢查倉位限制

        Args:
            symbol: 股票代碼
            value: 倉位價值

        Returns:
            bool: 是否符合倉位限制
        """
        # 計算新的投資組合總價值
        current_value = self.get_portfolio_value()
        if symbol in self.positions:
            current_value -= self.positions[symbol]["value"]
        new_value = current_value + value

        # 計算新的倉位權重
        weight = value / new_value if new_value > 0 else 0.0

        # 檢查是否超過限制
        if weight > self.max_position_percent:
            logger.warning(
                f"倉位 {symbol} 權重 {weight:.2%} 超過限制 {self.max_position_percent:.2%}"
            )
            return False

        return True

    def check_sector_limit(
        self, symbol: str, value: float, sector: Optional[str] = None
    ) -> bool:
        """
        檢查行業限制

        Args:
            symbol: 股票代碼
            value: 倉位價值
            sector: 行業分類

        Returns:
            bool: 是否符合行業限制
        """
        # 如果沒有指定行業，則使用現有的行業映射
        if not sector and symbol in self.sector_mapping:
            sector = self.sector_mapping[symbol]

        # 如果沒有行業信息，則不進行檢查
        if not sector:
            return True

        # 計算新的投資組合總價值
        current_value = self.get_portfolio_value()
        if symbol in self.positions:
            current_value -= self.positions[symbol]["value"]
        new_value = current_value + value

        # 計算新的行業總價值
        sector_value = (
            sum(
                position["value"]
                for s, position in self.positions.items()
                if position.get("sector") == sector and s != symbol
            )
            + value
        )

        # 計算新的行業權重
        weight = sector_value / new_value if new_value > 0 else 0.0

        # 檢查是否超過限制
        if weight > self.max_sector_percent:
            logger.warning(
                f"行業 {sector} 權重 {weight:.2%} 超過限制 {self.max_sector_percent:.2%}"
            )
            return False

        return True

    def check_all_limits(
        self, symbol: str, value: float, sector: Optional[str] = None
    ) -> bool:
        """
        檢查所有限制

        Args:
            symbol: 股票代碼
            value: 倉位價值
            sector: 行業分類

        Returns:
            bool: 是否符合所有限制
        """
        # 檢查倉位限制
        if not self.check_position_limit(symbol, value):
            return False

        # 檢查行業限制
        if not self.check_sector_limit(symbol, value, sector):
            return False

        return True

    def get_diversification_score(self) -> float:
        """
        獲取分散化得分

        Returns:
            float: 分散化得分，範圍 0-1，越高越分散
        """
        weights = list(self.get_position_weights().values())
        if not weights:
            return 0.0

        # 計算赫芬達爾-赫希曼指數 (HHI)
        hhi = sum(w * w for w in weights)

        # 轉換為分散化得分
        # 完全集中 (HHI = 1) -> 得分 = 0
        # 完全分散 (HHI = 1/n) -> 得分 = 1
        n = len(weights)
        min_hhi = 1 / n if n > 0 else 0

        # 線性映射
        score = 1 - (hhi - min_hhi) / (1 - min_hhi) if n > 1 else 0

        return max(0.0, min(1.0, score))

    def get_sector_diversification_score(self) -> float:
        """
        獲取行業分散化得分

        Returns:
            float: 行業分散化得分，範圍 0-1，越高越分散
        """
        weights = list(self.get_sector_weights().values())
        if not weights:
            return 0.0

        # 計算赫芬達爾-赫希曼指數 (HHI)
        hhi = sum(w * w for w in weights)

        # 轉換為分散化得分
        n = len(weights)
        min_hhi = 1 / n if n > 0 else 0

        # 線性映射
        score = 1 - (hhi - min_hhi) / (1 - min_hhi) if n > 1 else 0

        return max(0.0, min(1.0, score))

    def get_portfolio_stats(self) -> Dict[str, Any]:
        """
        獲取投資組合統計信息

        Returns:
            Dict[str, Any]: 投資組合統計信息
        """
        portfolio_value = self.get_portfolio_value()
        position_weights = self.get_position_weights()
        sector_weights = self.get_sector_weights()

        return {
            "portfolio_value": portfolio_value,
            "position_count": len(self.positions),
            "sector_count": len(sector_weights),
            "position_weights": position_weights,
            "sector_weights": sector_weights,
            "diversification_score": self.get_diversification_score(),
            "sector_diversification_score": self.get_sector_diversification_score(),
            "max_position_weight": (
                max(position_weights.values()) if position_weights else 0.0
            ),
            "max_sector_weight": (
                max(sector_weights.values()) if sector_weights else 0.0
            ),
        }


class DiversificationManager:
    """
    分散化管理器

    管理投資組合的分散化，包括股票數量、行業分布和相關性等。
    """

    def __init__(self, min_stocks: int = 5, max_correlation: float = 0.7):
        """
        初始化分散化管理器

        Args:
            min_stocks: 最小股票數量
            max_correlation: 最大相關性
        """
        self.min_stocks = max(min_stocks, 1)
        self.max_correlation = min(max(max_correlation, 0.0), 1.0)

        logger.info(
            f"初始化分散化管理器: 最小股票數量 {self.min_stocks}, 最大相關性 {self.max_correlation}"
        )

    def check_diversification(self, portfolio: Dict[str, float]) -> bool:
        """
        檢查分散化

        Args:
            portfolio: 投資組合，股票代碼到權重的映射

        Returns:
            bool: 是否符合分散化要求
        """
        # 檢查股票數量
        if len(portfolio) < self.min_stocks:
            logger.warning(
                f"投資組合股票數量 {len(portfolio)} 少於最小要求 {self.min_stocks}"
            )
            return False

        return True

    def suggest_diversification(
        self, portfolio: Dict[str, float], candidates: List[str]
    ) -> List[str]:
        """
        建議分散化

        Args:
            portfolio: 投資組合，股票代碼到權重的映射
            candidates: 候選股票列表

        Returns:
            List[str]: 建議添加的股票列表
        """
        # 檢查是否需要添加股票
        if len(portfolio) >= self.min_stocks:
            return []

        # 計算需要添加的股票數量
        to_add = self.min_stocks - len(portfolio)

        # 從候選列表中選擇
        suggestions = candidates[:to_add]

        logger.info(f"建議添加 {len(suggestions)} 支股票以增加分散化: {suggestions}")

        return suggestions


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
            f"初始化相關性分析器: 股票數量 {len(price_data)}, 回顧期間 {lookback_period}"
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

        logger.info(f"更新價格資料: {symbol}")


class RiskParityStrategy:
    """
    風險平價策略

    根據風險貢獻平衡投資組合權重。
    """

    def __init__(self, price_data: Dict[str, pd.DataFrame], lookback_period: int = 252):
        """
        初始化風險平價策略

        Args:
            price_data: 價格資料，股票代碼到價格資料的映射
            lookback_period: 回顧期間
        """
        self.price_data = price_data
        self.lookback_period = lookback_period

        logger.info(
            f"初始化風險平價策略: 股票數量 {len(price_data)}, 回顧期間 {lookback_period}"
        )

    def calculate_weights(self) -> Dict[str, float]:
        """
        計算風險平價權重

        Returns:
            Dict[str, float]: 股票代碼到權重的映射
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

        # 計算協方差矩陣
        cov_matrix = returns_df.cov()

        # 計算波動率
        volatilities = np.sqrt(np.diag(cov_matrix))

        # 計算風險平價權重
        weights = 1 / volatilities
        weights = weights / np.sum(weights)

        # 轉換為字典
        weight_dict = {
            symbol: weight for symbol, weight in zip(returns.keys(), weights)
        }

        return weight_dict

    def update_price_data(self, symbol: str, data: pd.DataFrame) -> None:
        """
        更新價格資料

        Args:
            symbol: 股票代碼
            data: 價格資料
        """
        self.price_data[symbol] = data

        logger.info(f"更新價格資料: {symbol}")


class SectorExposureManager:
    """
    行業暴露管理器

    管理投資組合的行業暴露。
    """

    def __init__(self, sector_limits: Dict[str, float]):
        """
        初始化行業暴露管理器

        Args:
            sector_limits: 行業限制，行業到最大權重的映射
        """
        self.sector_limits = {
            sector: min(abs(limit), 1.0) for sector, limit in sector_limits.items()
        }

        logger.info(f"初始化行業暴露管理器: 行業限制 {self.sector_limits}")

    def check_sector_exposure(
        self, portfolio: Dict[str, Dict[str, Any]]
    ) -> Dict[str, bool]:
        """
        檢查行業暴露

        Args:
            portfolio: 投資組合，股票代碼到詳細信息的映射

        Returns:
            Dict[str, bool]: 行業到是否符合限制的映射
        """
        # 計算投資組合總價值
        portfolio_value = sum(position["value"] for position in portfolio.values())

        # 計算每個行業的總價值
        sector_values = {}
        for position in portfolio.values():
            sector = position.get("sector")
            if sector:
                if sector not in sector_values:
                    sector_values[sector] = 0.0
                sector_values[sector] += position["value"]

        # 計算行業權重
        sector_weights = (
            {sector: value / portfolio_value for sector, value in sector_values.items()}
            if portfolio_value > 0
            else {}
        )

        # 檢查是否符合限制
        results = {}
        for sector, weight in sector_weights.items():
            limit = self.sector_limits.get(
                sector, 1.0
            )  # 如果沒有設置限制，則默認為 100%
            results[sector] = weight <= limit

        return results

    def get_sector_adjustments(
        self, portfolio: Dict[str, Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        獲取行業調整建議

        Args:
            portfolio: 投資組合，股票代碼到詳細信息的映射

        Returns:
            Dict[str, float]: 行業到調整量的映射，正值表示增加，負值表示減少
        """
        # 計算投資組合總價值
        portfolio_value = sum(position["value"] for position in portfolio.values())

        # 計算每個行業的總價值
        sector_values = {}
        for position in portfolio.values():
            sector = position.get("sector")
            if sector:
                if sector not in sector_values:
                    sector_values[sector] = 0.0
                sector_values[sector] += position["value"]

        # 計算行業權重
        sector_weights = (
            {sector: value / portfolio_value for sector, value in sector_values.items()}
            if portfolio_value > 0
            else {}
        )

        # 計算調整量
        adjustments = {}
        for sector, weight in sector_weights.items():
            limit = self.sector_limits.get(sector, 1.0)
            if weight > limit:
                # 需要減少
                adjustments[sector] = (limit - weight) * portfolio_value

        return adjustments


class ConcentrationRiskManager:
    """
    集中度風險管理器

    管理投資組合的集中度風險。
    """

    def __init__(self, max_position_percent: float = 0.2, max_positions: int = 20):
        """
        初始化集中度風險管理器

        Args:
            max_position_percent: 單一倉位最大百分比，例如 0.2 表示 20%
            max_positions: 最大倉位數量
        """
        self.max_position_percent = min(abs(max_position_percent), 1.0)
        self.max_positions = max(int(max_positions), 1)

        logger.info(
            f"初始化集中度風險管理器: 單一倉位最大 {self.max_position_percent:.2%}, 最大倉位數量 {self.max_positions}"
        )

    def check_concentration(self, portfolio: Dict[str, float]) -> bool:
        """
        檢查集中度

        Args:
            portfolio: 投資組合，股票代碼到權重的映射

        Returns:
            bool: 是否符合集中度要求
        """
        # 檢查倉位數量
        if len(portfolio) > self.max_positions:
            logger.warning(
                f"投資組合倉位數量 {len(portfolio)} 超過最大限制 {self.max_positions}"
            )
            return False

        # 檢查單一倉位權重
        for symbol, weight in portfolio.items():
            if weight > self.max_position_percent:
                logger.warning(
                    f"倉位 {symbol} 權重 {weight:.2%} 超過限制 {self.max_position_percent:.2%}"
                )
                return False

        return True

    def get_concentration_adjustments(
        self, portfolio: Dict[str, float]
    ) -> Dict[str, float]:
        """
        獲取集中度調整建議

        Args:
            portfolio: 投資組合，股票代碼到權重的映射

        Returns:
            Dict[str, float]: 股票代碼到調整量的映射，正值表示增加，負值表示減少
        """
        adjustments = {}

        # 檢查單一倉位權重
        for symbol, weight in portfolio.items():
            if weight > self.max_position_percent:
                # 需要減少
                adjustments[symbol] = self.max_position_percent - weight

        # 如果倉位數量超過限制，建議減少權重最小的倉位
        if len(portfolio) > self.max_positions:
            # 按權重排序
            sorted_positions = sorted(portfolio.items(), key=lambda x: x[1])

            # 需要減少的倉位數量
            to_reduce = len(portfolio) - self.max_positions

            # 建議減少權重最小的倉位
            for i in range(to_reduce):
                symbol, weight = sorted_positions[i]
                adjustments[symbol] = -weight  # 完全減少

        return adjustments
