"""
集中度風險管理模組

此模組實現了投資組合的集中度風險控制。
"""

from typing import Dict

from src.core.logger import logger


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
            "初始化集中度風險管理器: 單一倉位最大 %s, 最大倉位數量 %s",
            f"{self.max_position_percent:.2%}",
            self.max_positions,
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
                "投資組合倉位數量 %s 超過最大限制 %s",
                len(portfolio),
                self.max_positions,
            )
            return False

        # 檢查單一倉位權重
        for symbol, weight in portfolio.items():
            if weight > self.max_position_percent:
                logger.warning(
                    "倉位 %s 權重 %s 超過限制 %s",
                    symbol,
                    f"{weight:.2%}",
                    f"{self.max_position_percent:.2%}",
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

    def get_concentration_metrics(self, portfolio: Dict[str, float]) -> Dict[str, float]:
        """
        獲取集中度指標

        Args:
            portfolio: 投資組合，股票代碼到權重的映射

        Returns:
            Dict[str, float]: 集中度指標
        """
        if not portfolio:
            return {
                "herfindahl_index": 0.0,
                "effective_positions": 0.0,
                "max_weight": 0.0,
                "top_5_concentration": 0.0,
                "position_count": 0,
            }

        weights = list(portfolio.values())

        # 赫芬達爾指數
        herfindahl_index = sum(w * w for w in weights)

        # 有效倉位數量
        effective_positions = 1 / herfindahl_index if herfindahl_index > 0 else 0

        # 最大權重
        max_weight = max(weights)

        # 前5大持股集中度
        sorted_weights = sorted(weights, reverse=True)
        top_5_concentration = sum(sorted_weights[:5])

        return {
            "herfindahl_index": herfindahl_index,
            "effective_positions": effective_positions,
            "max_weight": max_weight,
            "top_5_concentration": top_5_concentration,
            "position_count": len(portfolio),
        }

    def suggest_rebalancing(
        self, portfolio: Dict[str, float], target_concentration: float = 0.1
    ) -> Dict[str, float]:
        """
        建議再平衡

        Args:
            portfolio: 投資組合，股票代碼到權重的映射
            target_concentration: 目標集中度

        Returns:
            Dict[str, float]: 建議的新權重
        """
        if not portfolio:
            return portfolio

        # 如果集中度已經符合要求，返回原權重
        metrics = self.get_concentration_metrics(portfolio)
        if metrics["herfindahl_index"] <= target_concentration:
            return portfolio

        # 建議等權重分配
        equal_weight = 1.0 / len(portfolio)
        rebalanced_portfolio = {symbol: equal_weight for symbol in portfolio}

        logger.info(
            "建議再平衡: 當前集中度 %s, 目標集中度 %s",
            f"{metrics['herfindahl_index']:.4f}",
            f"{target_concentration:.4f}",
        )

        return rebalanced_portfolio

    def update_limits(self, max_position_percent: float = None, max_positions: int = None) -> None:
        """
        更新限制

        Args:
            max_position_percent: 新的單一倉位最大百分比
            max_positions: 新的最大倉位數量
        """
        if max_position_percent is not None:
            self.max_position_percent = min(abs(max_position_percent), 1.0)
            logger.info("更新單一倉位最大百分比: %s", f"{self.max_position_percent:.2%}")

        if max_positions is not None:
            self.max_positions = max(int(max_positions), 1)
            logger.info("更新最大倉位數量: %s", self.max_positions)
