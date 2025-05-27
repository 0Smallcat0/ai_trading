"""
行業暴露管理模組

此模組實現了投資組合的行業暴露管理和集中度風險控制。

注意：ConcentrationRiskManager 已移至 concentration_risk_manager.py
為了向後相容性，仍可從此模組導入。
"""

from typing import Any, Dict, List

from src.core.logger import logger

# 為了向後相容性，重新導出 ConcentrationRiskManager
from .concentration_risk_manager import ConcentrationRiskManager

__all__ = ["SectorExposureManager", "ConcentrationRiskManager"]


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

        logger.info("初始化行業暴露管理器: 行業限制 %s", self.sector_limits)

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

    def get_sector_weights(
        self, portfolio: Dict[str, Dict[str, Any]]
    ) -> Dict[str, float]:
        """
        獲取行業權重

        Args:
            portfolio: 投資組合，股票代碼到詳細信息的映射

        Returns:
            Dict[str, float]: 行業權重
        """
        # 計算投資組合總價值
        portfolio_value = sum(position["value"] for position in portfolio.values())

        if portfolio_value == 0:
            return {}

        # 計算每個行業的總價值
        sector_values = {}
        for position in portfolio.values():
            sector = position.get("sector")
            if sector:
                if sector not in sector_values:
                    sector_values[sector] = 0.0
                sector_values[sector] += position["value"]

        # 計算行業權重
        return {
            sector: value / portfolio_value for sector, value in sector_values.items()
        }

    def get_sector_exposure_report(
        self, portfolio: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        獲取行業暴露報告

        Args:
            portfolio: 投資組合，股票代碼到詳細信息的映射

        Returns:
            Dict[str, Any]: 行業暴露報告
        """
        sector_weights = self.get_sector_weights(portfolio)
        sector_compliance = self.check_sector_exposure(portfolio)
        sector_adjustments = self.get_sector_adjustments(portfolio)

        # 計算違規行業
        violations = [
            sector for sector, compliant in sector_compliance.items() if not compliant
        ]

        # 計算行業集中度
        weights = list(sector_weights.values())
        sector_concentration = sum(w * w for w in weights) if weights else 0.0

        return {
            "sector_weights": sector_weights,
            "sector_compliance": sector_compliance,
            "sector_adjustments": sector_adjustments,
            "violations": violations,
            "sector_concentration": sector_concentration,
            "sector_count": len(sector_weights),
            "max_sector_weight": max(weights) if weights else 0.0,
        }

    def update_sector_limits(self, new_limits: Dict[str, float]) -> None:
        """
        更新行業限制

        Args:
            new_limits: 新的行業限制
        """
        self.sector_limits.update(
            {sector: min(abs(limit), 1.0) for sector, limit in new_limits.items()}
        )
        logger.info("更新行業限制: %s", new_limits)

    def add_sector_limit(self, sector: str, limit: float) -> None:
        """
        添加行業限制

        Args:
            sector: 行業名稱
            limit: 限制比例
        """
        self.sector_limits[sector] = min(abs(limit), 1.0)
        logger.info("添加行業限制: %s = %s", sector, limit)

    def remove_sector_limit(self, sector: str) -> None:
        """
        移除行業限制

        Args:
            sector: 行業名稱
        """
        if sector in self.sector_limits:
            del self.sector_limits[sector]
            logger.info("移除行業限制: %s", sector)
        else:
            logger.warning("行業限制不存在: %s", sector)
