"""
停利策略模組

此模組實現了各種停利策略，用於獲利了結。
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from src.core.logger import logger


class TakeProfitStrategy(ABC):
    """
    停利策略抽象基類

    所有停利策略都應繼承此類並實現其抽象方法。
    """

    def __init__(self, name: str):
        """
        初始化停利策略

        Args:
            name: 策略名稱
        """
        self.name = name
        logger.info(f"初始化停利策略: {name}")

    @abstractmethod
    def calculate_take_profit(self, entry_price: float, **kwargs) -> float:
        """
        計算停利價格

        Args:
            entry_price: 進場價格
            **kwargs: 其他參數

        Returns:
            float: 停利價格
        """

    @abstractmethod
    def should_take_profit(
        self, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """
        判斷是否應該停利

        Args:
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            bool: 是否應該停利
        """

    def update(self, current_price: float, **kwargs) -> None:
        """
        更新停利策略

        Args:
            current_price: 當前價格
            **kwargs: 其他參數
        """


class PercentTakeProfit(TakeProfitStrategy):
    """
    百分比停利策略

    根據進場價格的百分比設置停利價格。
    """

    def __init__(self, percent: float, is_long: bool = True):
        """
        初始化百分比停利策略

        Args:
            percent: 停利百分比，例如 0.1 表示 10%
            is_long: 是否為多頭倉位，如果為 False 則為空頭倉位
        """
        super().__init__("百分比停利")
        self.percent = abs(percent)
        self.is_long = is_long
        logger.info(
            f"初始化百分比停利策略: {self.percent:.2%}, {'多頭' if is_long else '空頭'}"
        )

    def calculate_take_profit(self, entry_price: float, **kwargs) -> float:
        """
        計算停利價格

        Args:
            entry_price: 進場價格
            **kwargs: 其他參數

        Returns:
            float: 停利價格
        """
        if self.is_long:
            # 多頭倉位，停利價格高於進場價格
            return entry_price * (1 + self.percent)
        else:
            # 空頭倉位，停利價格低於進場價格
            return entry_price * (1 - self.percent)

    def should_take_profit(
        self, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """
        判斷是否應該停利

        Args:
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            bool: 是否應該停利
        """
        take_profit_price = self.calculate_take_profit(entry_price)

        if self.is_long:
            # 多頭倉位，當前價格高於停利價格時停利
            return current_price >= take_profit_price
        else:
            # 空頭倉位，當前價格低於停利價格時停利
            return current_price <= take_profit_price


class TargetTakeProfit(TakeProfitStrategy):
    """
    目標價停利策略

    根據預設的目標價格設置停利。
    """

    def __init__(self, target_price: float, is_long: bool = True):
        """
        初始化目標價停利策略

        Args:
            target_price: 目標價格
            is_long: 是否為多頭倉位，如果為 False 則為空頭倉位
        """
        super().__init__("目標價停利")
        self.target_price = target_price
        self.is_long = is_long
        logger.info(
            f"初始化目標價停利策略: {self.target_price}, {'多頭' if is_long else '空頭'}"
        )

    def calculate_take_profit(self, entry_price: float, **kwargs) -> float:
        """
        計算停利價格

        Args:
            entry_price: 進場價格
            **kwargs: 其他參數

        Returns:
            float: 停利價格
        """
        return self.target_price

    def should_take_profit(
        self, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """
        判斷是否應該停利

        Args:
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            bool: 是否應該停利
        """
        if self.is_long:
            # 多頭倉位，當前價格高於目標價格時停利
            return current_price >= self.target_price
        else:
            # 空頭倉位，當前價格低於目標價格時停利
            return current_price <= self.target_price


class TrailingTakeProfit(TakeProfitStrategy):
    """
    追蹤停利策略

    根據價格的最高點（多頭）或最低點（空頭）設置動態停利價格。
    """

    def __init__(
        self, percent: float, is_long: bool = True, activation_percent: float = 0.0
    ):
        """
        初始化追蹤停利策略

        Args:
            percent: 追蹤停利百分比，例如 0.05 表示 5%
            is_long: 是否為多頭倉位，如果為 False 則為空頭倉位
            activation_percent: 啟動百分比，例如 0.1 表示當獲利達到 10% 時才啟動追蹤停利
        """
        super().__init__("追蹤停利")
        self.percent = abs(percent)
        self.is_long = is_long
        self.activation_percent = abs(activation_percent)
        self.highest_price = 0.0
        self.lowest_price = float("inf")
        self.activated = False
        logger.info(
            f"初始化追蹤停利策略: {self.percent:.2%}, {'多頭' if is_long else '空頭'}, 啟動百分比: {self.activation_percent:.2%}"
        )

    def calculate_take_profit(self, entry_price: float, **kwargs) -> float:
        """
        計算停利價格

        Args:
            entry_price: 進場價格
            **kwargs: 其他參數，可以包含 'highest_price' 或 'lowest_price'

        Returns:
            float: 停利價格
        """
        # 檢查是否已啟動
        if not self.activated:
            if self.is_long:
                # 多頭倉位，檢查是否達到啟動條件
                activation_price = entry_price * (1 + self.activation_percent)
                if self.highest_price >= activation_price:
                    self.activated = True
                    logger.info(
                        f"追蹤停利已啟動: 價格 {self.highest_price} >= 啟動價格 {activation_price}"
                    )
                else:
                    # 未啟動，返回一個很高的價格
                    return float("inf")
            else:
                # 空頭倉位，檢查是否達到啟動條件
                activation_price = entry_price * (1 - self.activation_percent)
                if self.lowest_price <= activation_price:
                    self.activated = True
                    logger.info(
                        f"追蹤停利已啟動: 價格 {self.lowest_price} <= 啟動價格 {activation_price}"
                    )
                else:
                    # 未啟動，返回一個很低的價格
                    return 0.0

        # 獲取最高價和最低價
        highest_price = kwargs.get("highest_price", self.highest_price)
        lowest_price = kwargs.get("lowest_price", self.lowest_price)

        if self.is_long:
            # 多頭倉位，停利價格為最高價的一定百分比
            return highest_price * (1 - self.percent)
        else:
            # 空頭倉位，停利價格為最低價的一定百分比
            return lowest_price * (1 + self.percent)

    def should_take_profit(
        self, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """
        判斷是否應該停利

        Args:
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            bool: 是否應該停利
        """
        # 更新最高價和最低價
        self.update(current_price)

        take_profit_price = self.calculate_take_profit(entry_price)

        if self.is_long:
            # 多頭倉位，當前價格低於停利價格時停利（價格回落）
            return self.activated and current_price <= take_profit_price
        else:
            # 空頭倉位，當前價格高於停利價格時停利（價格反彈）
            return self.activated and current_price >= take_profit_price

    def update(self, current_price: float, **kwargs) -> None:
        """
        更新追蹤停利策略

        Args:
            current_price: 當前價格
            **kwargs: 其他參數
        """
        if self.is_long:
            # 多頭倉位，更新最高價
            self.highest_price = max(self.highest_price, current_price)
        else:
            # 空頭倉位，更新最低價
            self.lowest_price = min(self.lowest_price, current_price)


class RiskRewardTakeProfit(TakeProfitStrategy):
    """
    風險報酬比停利策略

    根據風險報酬比設置停利價格。
    """

    def __init__(self, risk_reward_ratio: float, is_long: bool = True):
        """
        初始化風險報酬比停利策略

        Args:
            risk_reward_ratio: 風險報酬比，例如 2.0 表示獲利目標是風險的 2 倍
            is_long: 是否為多頭倉位，如果為 False 則為空頭倉位
        """
        super().__init__("風險報酬比停利")
        self.risk_reward_ratio = abs(risk_reward_ratio)
        self.is_long = is_long
        logger.info(
            f"初始化風險報酬比停利策略: {self.risk_reward_ratio}, {'多頭' if is_long else '空頭'}"
        )

    def calculate_take_profit(self, entry_price: float, **kwargs) -> float:
        """
        計算停利價格

        Args:
            entry_price: 進場價格
            **kwargs: 其他參數，必須包含 'stop_loss_price'

        Returns:
            float: 停利價格
        """
        stop_loss_price = kwargs.get("stop_loss_price")
        if stop_loss_price is None:
            raise ValueError("必須提供 'stop_loss_price' 參數")

        if self.is_long:
            # 多頭倉位，計算風險
            risk = entry_price - stop_loss_price
            # 計算獲利目標
            reward = risk * self.risk_reward_ratio
            # 計算停利價格
            return entry_price + reward
        else:
            # 空頭倉位，計算風險
            risk = stop_loss_price - entry_price
            # 計算獲利目標
            reward = risk * self.risk_reward_ratio
            # 計算停利價格
            return entry_price - reward

    def should_take_profit(
        self, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """
        判斷是否應該停利

        Args:
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數，必須包含 'stop_loss_price'

        Returns:
            bool: 是否應該停利
        """
        take_profit_price = self.calculate_take_profit(entry_price, **kwargs)

        if self.is_long:
            # 多頭倉位，當前價格高於停利價格時停利
            return current_price >= take_profit_price
        else:
            # 空頭倉位，當前價格低於停利價格時停利
            return current_price <= take_profit_price


class TimeBasedTakeProfit(TakeProfitStrategy):
    """
    時間基礎停利策略

    根據持倉時間設置停利。
    """

    def __init__(
        self, target_days: int, min_profit_percent: float = 0.0, is_long: bool = True
    ):
        """
        初始化時間基礎停利策略

        Args:
            target_days: 目標持倉天數
            min_profit_percent: 最小獲利百分比，例如 0.05 表示 5%
            is_long: 是否為多頭倉位，如果為 False 則為空頭倉位
        """
        super().__init__("時間停利")
        self.target_days = target_days
        self.min_profit_percent = abs(min_profit_percent)
        self.is_long = is_long
        logger.info(
            f"初始化時間停利策略: 目標持倉 {self.target_days} 天, 最小獲利 {self.min_profit_percent:.2%}, {'多頭' if is_long else '空頭'}"
        )

    def calculate_take_profit(self, entry_price: float, **kwargs) -> float:
        """
        計算停利價格

        對於時間基礎停利，此方法返回最小獲利價格

        Args:
            entry_price: 進場價格
            **kwargs: 其他參數

        Returns:
            float: 停利價格
        """
        if self.is_long:
            # 多頭倉位，停利價格高於進場價格
            return entry_price * (1 + self.min_profit_percent)
        else:
            # 空頭倉位，停利價格低於進場價格
            return entry_price * (1 - self.min_profit_percent)

    def should_take_profit(
        self, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """
        判斷是否應該停利

        Args:
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數，必須包含 'entry_date' 和 'current_date'

        Returns:
            bool: 是否應該停利
        """
        entry_date = kwargs.get("entry_date")
        current_date = kwargs.get("current_date")

        if entry_date is None or current_date is None:
            raise ValueError("必須提供 'entry_date' 和 'current_date' 參數")

        # 確保日期格式正確
        if isinstance(entry_date, str):
            entry_date = datetime.strptime(entry_date, "%Y-%m-%d").date()
        if isinstance(current_date, str):
            current_date = datetime.strptime(current_date, "%Y-%m-%d").date()

        # 計算持倉天數
        holding_days = (current_date - entry_date).days

        # 計算當前獲利百分比
        if self.is_long:
            profit_percent = (current_price - entry_price) / entry_price
        else:
            profit_percent = (entry_price - current_price) / entry_price

        # 判斷是否達到目標持倉天數且獲利達到最小要求
        return (
            holding_days >= self.target_days
            and profit_percent >= self.min_profit_percent
        )


class MultipleTakeProfit(TakeProfitStrategy):
    """
    多重停利策略

    組合多個停利策略，任一策略觸發即停利。
    """

    def __init__(self, strategies: List[TakeProfitStrategy]):
        """
        初始化多重停利策略

        Args:
            strategies: 停利策略列表
        """
        super().__init__("多重停利")
        self.strategies = strategies
        strategy_names = [strategy.name for strategy in strategies]
        logger.info(f"初始化多重停利策略: {strategy_names}")

    def calculate_take_profit(self, entry_price: float, **kwargs) -> float:
        """
        計算停利價格

        返回最寬鬆的停利價格

        Args:
            entry_price: 進場價格
            **kwargs: 其他參數

        Returns:
            float: 停利價格
        """
        # 獲取所有策略的停利價格
        take_profit_prices = []
        for strategy in self.strategies:
            try:
                take_profit_price = strategy.calculate_take_profit(
                    entry_price, **kwargs
                )
                take_profit_prices.append(take_profit_price)
            except Exception as e:
                logger.warning(f"計算停利價格時發生錯誤: {e}")

        if not take_profit_prices:
            return float("inf") if kwargs.get("is_long", True) else 0.0

        # 判斷是多頭還是空頭
        is_long = kwargs.get("is_long", True)

        if is_long:
            # 多頭倉位，返回最低的停利價格
            return min(take_profit_prices)
        else:
            # 空頭倉位，返回最高的停利價格
            return max(take_profit_prices)

    def should_take_profit(
        self, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """
        判斷是否應該停利

        任一策略觸發即停利

        Args:
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            bool: 是否應該停利
        """
        # 更新所有策略
        for strategy in self.strategies:
            strategy.update(current_price, **kwargs)

        # 檢查是否有任一策略觸發停利
        for strategy in self.strategies:
            try:
                if strategy.should_take_profit(entry_price, current_price, **kwargs):
                    logger.info(f"觸發停利策略: {strategy.name}")
                    return True
            except Exception as e:
                logger.warning(f"檢查停利時發生錯誤: {e}")

        return False

    def update(self, current_price: float, **kwargs) -> None:
        """
        更新多重停利策略

        Args:
            current_price: 當前價格
            **kwargs: 其他參數
        """
        # 更新所有策略
        for strategy in self.strategies:
            strategy.update(current_price, **kwargs)
