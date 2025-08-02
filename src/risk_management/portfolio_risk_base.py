"""
投資組合風險管理基礎模組

此模組實現了核心的投資組合風險管理功能。
"""

from typing import Any, Dict, Optional

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
            "初始化投資組合風險管理器: 單一倉位最大 %s, 單一行業最大 %s",
            f"{self.max_position_percent:.2%}",
            f"{self.max_sector_percent:.2%}",
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
            logger.warning("倉位 %s 已存在，請使用 update_position 方法更新", symbol)
            return False

        # 添加倉位
        self.positions[symbol] = {"value": value, "sector": sector}

        # 更新行業映射
        if sector:
            self.sector_mapping[symbol] = sector

        logger.info("添加倉位: %s, 價值: %s, 行業: %s", symbol, value, sector)
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
            logger.warning("倉位 %s 不存在，請使用 add_position 方法添加", symbol)
            return False

        # 更新倉位
        self.positions[symbol]["value"] = value

        # 更新行業
        if sector:
            self.positions[symbol]["sector"] = sector
            self.sector_mapping[symbol] = sector

        logger.info("更新倉位: %s, 價值: %s, 行業: %s", symbol, value, sector)
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
            logger.warning("倉位 %s 不存在", symbol)
            return False

        # 移除倉位
        del self.positions[symbol]

        # 移除行業映射
        if symbol in self.sector_mapping:
            del self.sector_mapping[symbol]

        logger.info("移除倉位: %s", symbol)
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
                "倉位 %s 權重 %s 超過限制 %s",
                symbol,
                f"{weight:.2%}",
                f"{self.max_position_percent:.2%}",
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
                "行業 %s 權重 %s 超過限制 %s",
                sector,
                f"{weight:.2%}",
                f"{self.max_sector_percent:.2%}",
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
