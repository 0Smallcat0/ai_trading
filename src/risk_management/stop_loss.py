"""
停損策略模組

此模組實現了各種停損策略，用於控制交易風險。
"""

import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple

from src.core.logger import logger


class StopLossStrategy(ABC):
    """
    停損策略抽象基類

    所有停損策略都應繼承此類並實現其抽象方法。
    """

    def __init__(self, name: str):
        """
        初始化停損策略

        Args:
            name: 策略名稱
        """
        self.name = name
        logger.info(f"初始化停損策略: {name}")

    @abstractmethod
    def calculate_stop_loss(self, entry_price: float, **kwargs) -> float:
        """
        計算停損價格

        Args:
            entry_price: 進場價格
            **kwargs: 其他參數

        Returns:
            float: 停損價格
        """
        pass

    @abstractmethod
    def should_stop_out(
        self, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """
        判斷是否應該停損

        Args:
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            bool: 是否應該停損
        """
        pass

    def update(self, current_price: float, **kwargs) -> None:
        """
        更新停損策略

        Args:
            current_price: 當前價格
            **kwargs: 其他參數
        """
        pass


class PercentStopLoss(StopLossStrategy):
    """
    百分比停損策略

    根據進場價格的百分比設置停損價格。
    """

    def __init__(self, percent: float, is_long: bool = True):
        """
        初始化百分比停損策略

        Args:
            percent: 停損百分比，例如 0.05 表示 5%
            is_long: 是否為多頭倉位，如果為 False 則為空頭倉位
        """
        super().__init__("百分比停損")
        self.percent = abs(percent)
        self.is_long = is_long
        logger.info(
            f"初始化百分比停損策略: {self.percent:.2%}, {'多頭' if is_long else '空頭'}"
        )

    def calculate_stop_loss(self, entry_price: float, **kwargs) -> float:
        """
        計算停損價格

        Args:
            entry_price: 進場價格
            **kwargs: 其他參數

        Returns:
            float: 停損價格
        """
        if self.is_long:
            # 多頭倉位，停損價格低於進場價格
            return entry_price * (1 - self.percent)
        else:
            # 空頭倉位，停損價格高於進場價格
            return entry_price * (1 + self.percent)

    def should_stop_out(
        self, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """
        判斷是否應該停損

        Args:
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            bool: 是否應該停損
        """
        stop_price = self.calculate_stop_loss(entry_price)

        if self.is_long:
            # 多頭倉位，當前價格低於停損價格時停損
            return current_price <= stop_price
        else:
            # 空頭倉位，當前價格高於停損價格時停損
            return current_price >= stop_price


class ATRStopLoss(StopLossStrategy):
    """
    ATR 停損策略

    根據 ATR（真實波動幅度均值）設置停損價格。
    """

    def __init__(self, atr_multiple: float, atr_period: int = 14, is_long: bool = True):
        """
        初始化 ATR 停損策略

        Args:
            atr_multiple: ATR 乘數，例如 2.0 表示 2 倍 ATR
            atr_period: ATR 計算週期
            is_long: 是否為多頭倉位，如果為 False 則為空頭倉位
        """
        super().__init__("ATR停損")
        self.atr_multiple = abs(atr_multiple)
        self.atr_period = atr_period
        self.is_long = is_long
        logger.info(
            f"初始化 ATR 停損策略: {self.atr_multiple} 倍 ATR, 週期 {self.atr_period}, {'多頭' if is_long else '空頭'}"
        )

    def calculate_stop_loss(self, entry_price: float, **kwargs) -> float:
        """
        計算停損價格

        Args:
            entry_price: 進場價格
            **kwargs: 其他參數，必須包含 'atr' 或 'price_data'

        Returns:
            float: 停損價格
        """
        # 獲取 ATR 值
        atr = kwargs.get("atr")
        if atr is None:
            price_data = kwargs.get("price_data")
            if price_data is None:
                raise ValueError("必須提供 'atr' 或 'price_data' 參數")

            # 計算 ATR
            atr = self._calculate_atr(price_data)

        if self.is_long:
            # 多頭倉位，停損價格低於進場價格
            return entry_price - (self.atr_multiple * atr)
        else:
            # 空頭倉位，停損價格高於進場價格
            return entry_price + (self.atr_multiple * atr)

    def should_stop_out(
        self, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """
        判斷是否應該停損

        Args:
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數，必須包含 'atr' 或 'price_data'

        Returns:
            bool: 是否應該停損
        """
        stop_price = self.calculate_stop_loss(entry_price, **kwargs)

        if self.is_long:
            # 多頭倉位，當前價格低於停損價格時停損
            return current_price <= stop_price
        else:
            # 空頭倉位，當前價格高於停損價格時停損
            return current_price >= stop_price

    def _calculate_atr(self, price_data: pd.DataFrame) -> float:
        """
        計算 ATR

        Args:
            price_data: 價格資料，必須包含 'high', 'low', 'close' 欄位

        Returns:
            float: ATR 值
        """
        # 確保價格資料包含必要欄位
        required_columns = ["high", "low", "close"]
        if not all(col in price_data.columns for col in required_columns):
            raise ValueError(f"價格資料必須包含 {required_columns} 欄位")

        # 計算真實波動幅度 (TR)
        high = price_data["high"].values
        low = price_data["low"].values
        close = price_data["close"].values

        tr1 = np.abs(high[1:] - low[1:])
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])

        tr = np.maximum(np.maximum(tr1, tr2), tr3)

        # 計算 ATR
        atr = (
            np.mean(tr[-self.atr_period :])
            if len(tr) >= self.atr_period
            else np.mean(tr)
        )

        return atr


class TimeBasedStopLoss(StopLossStrategy):
    """
    時間基礎停損策略

    根據持倉時間設置停損。
    """

    def __init__(self, max_holding_days: int):
        """
        初始化時間基礎停損策略

        Args:
            max_holding_days: 最大持倉天數
        """
        super().__init__("時間停損")
        self.max_holding_days = max_holding_days
        logger.info(f"初始化時間停損策略: 最大持倉 {self.max_holding_days} 天")

    def calculate_stop_loss(self, entry_price: float, **kwargs) -> float:
        """
        計算停損價格

        對於時間基礎停損，此方法不適用，返回 0

        Args:
            entry_price: 進場價格
            **kwargs: 其他參數

        Returns:
            float: 停損價格 (0)
        """
        return 0.0

    def should_stop_out(
        self, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """
        判斷是否應該停損

        Args:
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數，必須包含 'entry_date' 和 'current_date'

        Returns:
            bool: 是否應該停損
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

        # 判斷是否超過最大持倉天數
        return holding_days >= self.max_holding_days


class TrailingStopLoss(StopLossStrategy):
    """
    追蹤停損策略

    根據價格的最高點（多頭）或最低點（空頭）設置動態停損價格。
    """

    def __init__(self, percent: float, is_long: bool = True):
        """
        初始化追蹤停損策略

        Args:
            percent: 追蹤停損百分比，例如 0.05 表示 5%
            is_long: 是否為多頭倉位，如果為 False 則為空頭倉位
        """
        super().__init__("追蹤停損")
        self.percent = abs(percent)
        self.is_long = is_long
        self.highest_price = 0.0
        self.lowest_price = float("inf")
        logger.info(
            f"初始化追蹤停損策略: {self.percent:.2%}, {'多頭' if is_long else '空頭'}"
        )

    def calculate_stop_loss(self, entry_price: float, **kwargs) -> float:
        """
        計算停損價格

        Args:
            entry_price: 進場價格
            **kwargs: 其他參數，可以包含 'highest_price' 或 'lowest_price'

        Returns:
            float: 停損價格
        """
        # 獲取最高價和最低價
        highest_price = kwargs.get("highest_price", self.highest_price)
        lowest_price = kwargs.get("lowest_price", self.lowest_price)

        if self.is_long:
            # 多頭倉位，停損價格為最高價的一定百分比
            return highest_price * (1 - self.percent)
        else:
            # 空頭倉位，停損價格為最低價的一定百分比
            return lowest_price * (1 + self.percent)

    def should_stop_out(
        self, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """
        判斷是否應該停損

        Args:
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            bool: 是否應該停損
        """
        # 更新最高價和最低價
        self.update(current_price)

        stop_price = self.calculate_stop_loss(entry_price)

        if self.is_long:
            # 多頭倉位，當前價格低於停損價格時停損
            return current_price <= stop_price
        else:
            # 空頭倉位，當前價格高於停損價格時停損
            return current_price >= stop_price

    def update(self, current_price: float, **kwargs) -> None:
        """
        更新追蹤停損策略

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


class VolatilityStopLoss(StopLossStrategy):
    """
    波動率停損策略

    根據價格波動率設置停損價格。
    """

    def __init__(
        self,
        volatility_multiple: float,
        lookback_period: int = 20,
        is_long: bool = True,
    ):
        """
        初始化波動率停損策略

        Args:
            volatility_multiple: 波動率乘數，例如 2.0 表示 2 倍標準差
            lookback_period: 回顧期間，用於計算波動率
            is_long: 是否為多頭倉位，如果為 False 則為空頭倉位
        """
        super().__init__("波動率停損")
        self.volatility_multiple = abs(volatility_multiple)
        self.lookback_period = lookback_period
        self.is_long = is_long
        logger.info(
            f"初始化波動率停損策略: {self.volatility_multiple} 倍波動率, 回顧期間 {self.lookback_period}, {'多頭' if is_long else '空頭'}"
        )

    def calculate_stop_loss(self, entry_price: float, **kwargs) -> float:
        """
        計算停損價格

        Args:
            entry_price: 進場價格
            **kwargs: 其他參數，必須包含 'volatility' 或 'price_data'

        Returns:
            float: 停損價格
        """
        # 獲取波動率
        volatility = kwargs.get("volatility")
        if volatility is None:
            price_data = kwargs.get("price_data")
            if price_data is None:
                raise ValueError("必須提供 'volatility' 或 'price_data' 參數")

            # 計算波動率
            volatility = self._calculate_volatility(price_data)

        if self.is_long:
            # 多頭倉位，停損價格低於進場價格
            return entry_price - (self.volatility_multiple * volatility)
        else:
            # 空頭倉位，停損價格高於進場價格
            return entry_price + (self.volatility_multiple * volatility)

    def should_stop_out(
        self, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """
        判斷是否應該停損

        Args:
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數，必須包含 'volatility' 或 'price_data'

        Returns:
            bool: 是否應該停損
        """
        stop_price = self.calculate_stop_loss(entry_price, **kwargs)

        if self.is_long:
            # 多頭倉位，當前價格低於停損價格時停損
            return current_price <= stop_price
        else:
            # 空頭倉位，當前價格高於停損價格時停損
            return current_price >= stop_price

    def _calculate_volatility(self, price_data: pd.DataFrame) -> float:
        """
        計算波動率

        Args:
            price_data: 價格資料，必須包含 'close' 欄位

        Returns:
            float: 波動率
        """
        # 確保價格資料包含必要欄位
        if "close" not in price_data.columns:
            raise ValueError("價格資料必須包含 'close' 欄位")

        # 計算收益率
        returns = price_data["close"].pct_change().dropna()

        # 計算波動率
        volatility = returns.std() * np.sqrt(252)  # 年化波動率

        # 轉換為價格單位
        price_volatility = price_data["close"].iloc[-1] * volatility

        return price_volatility


class SupportResistanceStopLoss(StopLossStrategy):
    """
    支撐阻力停損策略

    根據支撐位（多頭）或阻力位（空頭）設置停損價格。
    """

    def __init__(self, is_long: bool = True, buffer_percent: float = 0.01):
        """
        初始化支撐阻力停損策略

        Args:
            is_long: 是否為多頭倉位，如果為 False 則為空頭倉位
            buffer_percent: 緩衝百分比，例如 0.01 表示 1%
        """
        super().__init__("支撐阻力停損")
        self.is_long = is_long
        self.buffer_percent = buffer_percent
        logger.info(
            f"初始化支撐阻力停損策略: {'多頭' if is_long else '空頭'}, 緩衝 {self.buffer_percent:.2%}"
        )

    def calculate_stop_loss(self, entry_price: float, **kwargs) -> float:
        """
        計算停損價格

        Args:
            entry_price: 進場價格
            **kwargs: 其他參數，必須包含 'support_level' 或 'resistance_level'

        Returns:
            float: 停損價格
        """
        if self.is_long:
            # 多頭倉位，停損價格為支撐位
            support_level = kwargs.get("support_level")
            if support_level is None:
                raise ValueError("多頭倉位必須提供 'support_level' 參數")

            # 添加緩衝
            return support_level * (1 - self.buffer_percent)
        else:
            # 空頭倉位，停損價格為阻力位
            resistance_level = kwargs.get("resistance_level")
            if resistance_level is None:
                raise ValueError("空頭倉位必須提供 'resistance_level' 參數")

            # 添加緩衝
            return resistance_level * (1 + self.buffer_percent)

    def should_stop_out(
        self, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """
        判斷是否應該停損

        Args:
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數，必須包含 'support_level' 或 'resistance_level'

        Returns:
            bool: 是否應該停損
        """
        stop_price = self.calculate_stop_loss(entry_price, **kwargs)

        if self.is_long:
            # 多頭倉位，當前價格低於停損價格時停損
            return current_price <= stop_price
        else:
            # 空頭倉位，當前價格高於停損價格時停損
            return current_price >= stop_price


class MultipleStopLoss(StopLossStrategy):
    """
    多重停損策略

    組合多個停損策略，任一策略觸發即停損。
    """

    def __init__(self, strategies: List[StopLossStrategy]):
        """
        初始化多重停損策略

        Args:
            strategies: 停損策略列表
        """
        super().__init__("多重停損")
        self.strategies = strategies
        strategy_names = [strategy.name for strategy in strategies]
        logger.info(f"初始化多重停損策略: {strategy_names}")

    def calculate_stop_loss(self, entry_price: float, **kwargs) -> float:
        """
        計算停損價格

        返回最嚴格的停損價格

        Args:
            entry_price: 進場價格
            **kwargs: 其他參數

        Returns:
            float: 停損價格
        """
        # 獲取所有策略的停損價格
        stop_prices = []
        for strategy in self.strategies:
            try:
                stop_price = strategy.calculate_stop_loss(entry_price, **kwargs)
                stop_prices.append(stop_price)
            except Exception as e:
                logger.warning(f"計算停損價格時發生錯誤: {e}")

        if not stop_prices:
            return 0.0

        # 判斷是多頭還是空頭
        is_long = kwargs.get("is_long", True)

        if is_long:
            # 多頭倉位，返回最高的停損價格
            return max(stop_prices)
        else:
            # 空頭倉位，返回最低的停損價格
            return min(stop_prices)

    def should_stop_out(
        self, entry_price: float, current_price: float, **kwargs
    ) -> bool:
        """
        判斷是否應該停損

        任一策略觸發即停損

        Args:
            entry_price: 進場價格
            current_price: 當前價格
            **kwargs: 其他參數

        Returns:
            bool: 是否應該停損
        """
        # 更新所有策略
        for strategy in self.strategies:
            strategy.update(current_price, **kwargs)

        # 檢查是否有任一策略觸發停損
        for strategy in self.strategies:
            try:
                if strategy.should_stop_out(entry_price, current_price, **kwargs):
                    logger.info(f"觸發停損策略: {strategy.name}")
                    return True
            except Exception as e:
                logger.warning(f"檢查停損時發生錯誤: {e}")

        return False

    def update(self, current_price: float, **kwargs) -> None:
        """
        更新多重停損策略

        Args:
            current_price: 當前價格
            **kwargs: 其他參數
        """
        # 更新所有策略
        for strategy in self.strategies:
            strategy.update(current_price, **kwargs)
