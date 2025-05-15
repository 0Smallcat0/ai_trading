"""
熔斷機制模組

此模組實現了各種熔斷機制，用於在風險超過閾值時自動停止交易。
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from src.core.logger import logger


class CircuitBreaker(ABC):
    """
    熔斷機制抽象基類

    所有熔斷機制都應繼承此類並實現其抽象方法。
    """

    def __init__(self, name: str):
        """
        初始化熔斷機制

        Args:
            name: 熔斷機制名稱
        """
        self.name = name
        self.triggered = False
        self.trigger_time = None
        self.trigger_reason = None

        logger.info(f"初始化熔斷機制: {name}")

    @abstractmethod
    def check(self, **kwargs) -> bool:
        """
        檢查是否應該觸發熔斷

        Args:
            **kwargs: 其他參數

        Returns:
            bool: 是否應該觸發熔斷
        """

    def trigger(self, reason: str) -> None:
        """
        觸發熔斷

        Args:
            reason: 觸發原因
        """
        self.triggered = True
        self.trigger_time = datetime.now()
        self.trigger_reason = reason

        logger.warning(f"熔斷機制 '{self.name}' 已觸發: {reason}")

    def reset(self) -> None:
        """
        重置熔斷
        """
        self.triggered = False
        self.trigger_time = None
        self.trigger_reason = None

        logger.info(f"熔斷機制 '{self.name}' 已重置")

    def get_status(self) -> Dict[str, Any]:
        """
        獲取熔斷狀態

        Returns:
            Dict[str, Any]: 熔斷狀態
        """
        return {
            "name": self.name,
            "triggered": self.triggered,
            "trigger_time": (
                self.trigger_time.isoformat() if self.trigger_time else None
            ),
            "trigger_reason": self.trigger_reason,
        }


class DrawdownCircuitBreaker(CircuitBreaker):
    """
    回撤熔斷機制

    當回撤超過閾值時觸發熔斷。
    """

    def __init__(self, max_drawdown: float, lookback_period: int = 0):
        """
        初始化回撤熔斷機制

        Args:
            max_drawdown: 最大回撤閾值，例如 0.1 表示 10%
            lookback_period: 回顧期間，如果為 0 則檢查整個歷史
        """
        super().__init__("回撤熔斷")
        self.max_drawdown = abs(max_drawdown)
        self.lookback_period = lookback_period

        logger.info(
            f"初始化回撤熔斷機制: 最大回撤 {self.max_drawdown:.2%}, 回顧期間 {self.lookback_period}"
        )

    def check(self, **kwargs) -> bool:
        """
        檢查是否應該觸發熔斷

        Args:
            **kwargs: 其他參數，必須包含 'returns' 或 'equity_curve'

        Returns:
            bool: 是否應該觸發熔斷
        """
        # 如果已經觸發，則直接返回 True
        if self.triggered:
            return True

        # 獲取收益率或權益曲線
        returns = kwargs.get("returns")
        equity_curve = kwargs.get("equity_curve")

        if returns is None and equity_curve is None:
            raise ValueError("必須提供 'returns' 或 'equity_curve' 參數")

        # 計算回撤
        if equity_curve is not None:
            # 使用權益曲線計算回撤
            if self.lookback_period > 0 and len(equity_curve) > self.lookback_period:
                equity_curve = equity_curve.iloc[-self.lookback_period :]

            # 計算歷史最高點
            running_max = equity_curve.cummax()

            # 計算回撤
            drawdown = (equity_curve / running_max) - 1

            # 計算最大回撤
            max_drawdown = drawdown.min()
        else:
            # 使用收益率計算回撤
            if self.lookback_period > 0 and len(returns) > self.lookback_period:
                returns = returns.iloc[-self.lookback_period :]

            # 計算累積收益率
            cumulative_returns = (1 + returns).cumprod()

            # 計算歷史最高點
            running_max = cumulative_returns.cummax()

            # 計算回撤
            drawdown = (cumulative_returns / running_max) - 1

            # 計算最大回撤
            max_drawdown = drawdown.min()

        # 檢查是否超過閾值
        if abs(max_drawdown) > self.max_drawdown:
            self.trigger(
                f"回撤 {abs(max_drawdown):.2%} 超過閾值 {self.max_drawdown:.2%}"
            )
            return True

        return False


class VolatilityCircuitBreaker(CircuitBreaker):
    """
    波動率熔斷機制

    當波動率超過閾值時觸發熔斷。
    """

    def __init__(self, max_volatility: float, window: int = 20, annualize: bool = True):
        """
        初始化波動率熔斷機制

        Args:
            max_volatility: 最大波動率閾值，例如 0.2 表示 20%
            window: 窗口大小
            annualize: 是否年化
        """
        super().__init__("波動率熔斷")
        self.max_volatility = abs(max_volatility)
        self.window = max(window, 2)
        self.annualize = annualize

        logger.info(
            f"初始化波動率熔斷機制: 最大波動率 {self.max_volatility:.2%}, 窗口大小 {self.window}, 年化 {self.annualize}"
        )

    def check(self, **kwargs) -> bool:
        """
        檢查是否應該觸發熔斷

        Args:
            **kwargs: 其他參數，必須包含 'returns'

        Returns:
            bool: 是否應該觸發熔斷
        """
        # 如果已經觸發，則直接返回 True
        if self.triggered:
            return True

        # 獲取收益率
        returns = kwargs.get("returns")

        if returns is None:
            raise ValueError("必須提供 'returns' 參數")

        # 確保有足夠的數據
        if len(returns) < self.window:
            return False

        # 計算波動率
        volatility = returns.iloc[-self.window :].std()

        # 年化
        if self.annualize:
            # 假設 252 個交易日
            volatility = volatility * np.sqrt(252)

        # 檢查是否超過閾值
        if volatility > self.max_volatility:
            self.trigger(f"波動率 {volatility:.2%} 超過閾值 {self.max_volatility:.2%}")
            return True

        return False


class LossCircuitBreaker(CircuitBreaker):
    """
    虧損熔斷機制

    當虧損超過閾值時觸發熔斷。
    """

    def __init__(
        self,
        max_daily_loss: float,
        max_weekly_loss: float = 0.0,
        max_monthly_loss: float = 0.0,
    ):
        """
        初始化虧損熔斷機制

        Args:
            max_daily_loss: 最大日虧損閾值，例如 0.02 表示 2%
            max_weekly_loss: 最大週虧損閾值，例如 0.05 表示 5%
            max_monthly_loss: 最大月虧損閾值，例如 0.1 表示 10%
        """
        super().__init__("虧損熔斷")
        self.max_daily_loss = abs(max_daily_loss)
        self.max_weekly_loss = abs(max_weekly_loss)
        self.max_monthly_loss = abs(max_monthly_loss)

        logger.info(
            f"初始化虧損熔斷機制: 最大日虧損 {self.max_daily_loss:.2%}, 最大週虧損 {self.max_weekly_loss:.2%}, 最大月虧損 {self.max_monthly_loss:.2%}"
        )

    def check(self, **kwargs) -> bool:
        """
        檢查是否應該觸發熔斷

        Args:
            **kwargs: 其他參數，必須包含 'returns' 或 'equity_curve'

        Returns:
            bool: 是否應該觸發熔斷
        """
        # 如果已經觸發，則直接返回 True
        if self.triggered:
            return True

        # 獲取收益率或權益曲線
        returns = kwargs.get("returns")
        equity_curve = kwargs.get("equity_curve")

        if returns is None and equity_curve is None:
            raise ValueError("必須提供 'returns' 或 'equity_curve' 參數")

        # 使用收益率計算虧損
        if returns is not None:
            # 檢查日虧損
            if len(returns) > 0 and self.max_daily_loss > 0:
                daily_return = returns.iloc[-1]
                if daily_return < 0 and abs(daily_return) > self.max_daily_loss:
                    self.trigger(
                        f"日虧損 {abs(daily_return):.2%} 超過閾值 {self.max_daily_loss:.2%}"
                    )
                    return True

            # 檢查週虧損
            if len(returns) >= 5 and self.max_weekly_loss > 0:
                weekly_return = (1 + returns.iloc[-5:]).prod() - 1
                if weekly_return < 0 and abs(weekly_return) > self.max_weekly_loss:
                    self.trigger(
                        f"週虧損 {abs(weekly_return):.2%} 超過閾值 {self.max_weekly_loss:.2%}"
                    )
                    return True

            # 檢查月虧損
            if len(returns) >= 21 and self.max_monthly_loss > 0:
                monthly_return = (1 + returns.iloc[-21:]).prod() - 1
                if monthly_return < 0 and abs(monthly_return) > self.max_monthly_loss:
                    self.trigger(
                        f"月虧損 {abs(monthly_return):.2%} 超過閾值 {self.max_monthly_loss:.2%}"
                    )
                    return True

        # 使用權益曲線計算虧損
        if equity_curve is not None:
            # 檢查日虧損
            if len(equity_curve) > 1 and self.max_daily_loss > 0:
                daily_return = equity_curve.iloc[-1] / equity_curve.iloc[-2] - 1
                if daily_return < 0 and abs(daily_return) > self.max_daily_loss:
                    self.trigger(
                        f"日虧損 {abs(daily_return):.2%} 超過閾值 {self.max_daily_loss:.2%}"
                    )
                    return True

            # 檢查週虧損
            if len(equity_curve) > 5 and self.max_weekly_loss > 0:
                weekly_return = equity_curve.iloc[-1] / equity_curve.iloc[-6] - 1
                if weekly_return < 0 and abs(weekly_return) > self.max_weekly_loss:
                    self.trigger(
                        f"週虧損 {abs(weekly_return):.2%} 超過閾值 {self.max_weekly_loss:.2%}"
                    )
                    return True

            # 檢查月虧損
            if len(equity_curve) > 21 and self.max_monthly_loss > 0:
                monthly_return = equity_curve.iloc[-1] / equity_curve.iloc[-22] - 1
                if monthly_return < 0 and abs(monthly_return) > self.max_monthly_loss:
                    self.trigger(
                        f"月虧損 {abs(monthly_return):.2%} 超過閾值 {self.max_monthly_loss:.2%}"
                    )
                    return True

        return False


class TimeCircuitBreaker(CircuitBreaker):
    """
    時間熔斷機制

    在特定時間觸發熔斷。
    """

    def __init__(
        self, start_time: str, end_time: str, days: Optional[List[int]] = None
    ):
        """
        初始化時間熔斷機制

        Args:
            start_time: 開始時間，格式為 "HH:MM"
            end_time: 結束時間，格式為 "HH:MM"
            days: 生效的星期幾，例如 [0, 1, 2, 3, 4] 表示週一至週五，如果為 None 則每天生效
        """
        super().__init__("時間熔斷")
        self.start_time = start_time
        self.end_time = end_time
        self.days = days

        logger.info(
            f"初始化時間熔斷機制: 開始時間 {self.start_time}, 結束時間 {self.end_time}, 生效日 {self.days}"
        )

    def check(self, **kwargs) -> bool:
        """
        檢查是否應該觸發熔斷

        Args:
            **kwargs: 其他參數，可以包含 'current_time'

        Returns:
            bool: 是否應該觸發熔斷
        """
        # 如果已經觸發，則直接返回 True
        if self.triggered:
            return True

        # 獲取當前時間
        current_time = kwargs.get("current_time", datetime.now())

        # 檢查星期幾
        if self.days is not None and current_time.weekday() not in self.days:
            return False

        # 解析開始時間和結束時間
        start_hour, start_minute = map(int, self.start_time.split(":"))
        end_hour, end_minute = map(int, self.end_time.split(":"))

        # 創建開始時間和結束時間
        start_datetime = current_time.replace(
            hour=start_hour, minute=start_minute, second=0, microsecond=0
        )
        end_datetime = current_time.replace(
            hour=end_hour, minute=end_minute, second=0, microsecond=0
        )

        # 檢查是否在時間範圍內
        if start_datetime <= current_time <= end_datetime:
            self.trigger(
                f"當前時間 {current_time.strftime('%H:%M')} 在熔斷時間範圍內 ({self.start_time} - {self.end_time})"
            )
            return True

        return False


class CompositeCircuitBreaker(CircuitBreaker):
    """
    組合熔斷機制

    組合多個熔斷機制，任一機制觸發即觸發熔斷。
    """

    def __init__(self, circuit_breakers: List[CircuitBreaker]):
        """
        初始化組合熔斷機制

        Args:
            circuit_breakers: 熔斷機制列表
        """
        super().__init__("組合熔斷")
        self.circuit_breakers = circuit_breakers

        breaker_names = [breaker.name for breaker in circuit_breakers]
        logger.info(f"初始化組合熔斷機制: {breaker_names}")

    def check(self, **kwargs) -> bool:
        """
        檢查是否應該觸發熔斷

        Args:
            **kwargs: 其他參數

        Returns:
            bool: 是否應該觸發熔斷
        """
        # 如果已經觸發，則直接返回 True
        if self.triggered:
            return True

        # 檢查所有熔斷機制
        for breaker in self.circuit_breakers:
            try:
                if breaker.check(**kwargs):
                    self.trigger(
                        f"熔斷機制 '{breaker.name}' 已觸發: {breaker.trigger_reason}"
                    )
                    return True
            except Exception as e:
                logger.error(f"檢查熔斷機制 '{breaker.name}' 時發生錯誤: {e}")

        return False

    def reset(self) -> None:
        """
        重置熔斷
        """
        super().reset()

        # 重置所有熔斷機制
        for breaker in self.circuit_breakers:
            breaker.reset()

    def get_status(self) -> Dict[str, Any]:
        """
        獲取熔斷狀態

        Returns:
            Dict[str, Any]: 熔斷狀態
        """
        status = super().get_status()

        # 添加所有熔斷機制的狀態
        status["circuit_breakers"] = [
            breaker.get_status() for breaker in self.circuit_breakers
        ]

        return status
