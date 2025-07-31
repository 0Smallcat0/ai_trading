"""
速率限制器模組

此模組提供 API 請求速率限制功能，防止超過 API 提供商的請求限制。

主要功能：
- 限制 API 請求頻率
- 支援多種限制策略（固定窗口、滑動窗口）
- 支援自動重試和退避策略
"""

import logging
import random
import threading
import time
from collections import deque
from typing import Optional

# 設定日誌
logger = logging.getLogger(__name__)


class RateLimiter:
    """API 請求速率限制器"""

    def __init__(
        self,
        max_calls: int,
        period: float,
        retry_count: int = 3,
        retry_backoff: float = 2.0,
        jitter: float = 0.1,
        strategy: str = "sliding_window",
    ):
        """
        初始化速率限制器

        Args:
            max_calls: 在指定時間段內允許的最大請求數
            period: 時間段長度（秒）
            retry_count: 重試次數
            retry_backoff: 重試退避因子
            jitter: 隨機抖動因子
            strategy: 限制策略，可選 'fixed_window', 'sliding_window'
        """
        self.max_calls = max_calls
        self.period = period
        self.retry_count = retry_count
        self.retry_backoff = retry_backoff
        self.jitter = jitter
        self.strategy = strategy
        self.lock = threading.RLock()

        # 用於記錄請求時間戳
        self.request_timestamps = deque()

        # 用於固定窗口策略
        self.window_start = time.time()
        self.call_count = 0

    def __enter__(self):
        """進入上下文管理器時調用"""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器時調用"""

    def acquire(self):
        """
        獲取請求許可，如果超過速率限制則等待

        Returns:
            bool: 是否成功獲取許可
        """
        retry = 0
        while retry <= self.retry_count:
            with self.lock:
                if self._can_proceed():
                    self._record_request()
                    return True

                # 計算需要等待的時間
                wait_time = self._calculate_wait_time()

            if retry == self.retry_count:
                logger.warning(f"已達最大重試次數 {self.retry_count}，放棄請求")
                raise Exception("Rate limit exceeded")

            # 添加隨機抖動
            jitter_value = random.uniform(0, self.jitter * wait_time)
            # 計算退避時間
            backoff_time = wait_time * (self.retry_backoff**retry) + jitter_value

            logger.debug(
                f"速率限制：等待 {backoff_time:.2f} 秒後重試 (重試 {retry+1}/{self.retry_count})"
            )
            time.sleep(backoff_time)
            retry += 1

        return False

    def _can_proceed(self) -> bool:
        """
        檢查是否可以繼續請求

        Returns:
            bool: 是否可以繼續請求
        """
        if self.strategy == "fixed_window":
            return self._fixed_window_check()
        else:  # sliding_window
            return self._sliding_window_check()

    def _fixed_window_check(self) -> bool:
        """
        固定窗口檢查

        Returns:
            bool: 是否可以繼續請求
        """
        current_time = time.time()
        # 檢查是否需要重置窗口
        if current_time - self.window_start > self.period:
            self.window_start = current_time
            self.call_count = 0

        return self.call_count < self.max_calls

    def _sliding_window_check(self) -> bool:
        """
        滑動窗口檢查

        Returns:
            bool: 是否可以繼續請求
        """
        current_time = time.time()
        # 移除過期的時間戳
        while (
            self.request_timestamps
            and current_time - self.request_timestamps[0] > self.period
        ):
            self.request_timestamps.popleft()

        return len(self.request_timestamps) < self.max_calls

    def _record_request(self):
        """記錄請求"""
        current_time = time.time()
        if self.strategy == "fixed_window":
            self.call_count += 1
        else:  # sliding_window
            self.request_timestamps.append(current_time)

    def _calculate_wait_time(self) -> float:
        """
        計算需要等待的時間

        Returns:
            float: 需要等待的時間（秒）
        """
        if self.strategy == "fixed_window":
            # 計算當前窗口剩餘時間
            current_time = time.time()
            elapsed = current_time - self.window_start
            return max(0, self.period - elapsed)
        else:  # sliding_window
            if not self.request_timestamps:
                return 0

            # 計算最早的請求何時過期
            current_time = time.time()
            oldest_timestamp = self.request_timestamps[0]
            return max(0, self.period - (current_time - oldest_timestamp))


class AdaptiveRateLimiter(RateLimiter):
    """自適應速率限制器，根據 API 響應動態調整速率"""

    def __init__(
        self,
        max_calls: int,
        period: float,
        retry_count: int = 3,
        retry_backoff: float = 2.0,
        jitter: float = 0.1,
        strategy: str = "sliding_window",
        min_calls: int = 1,
        increase_factor: float = 1.1,
        decrease_factor: float = 0.5,
    ):
        """
        初始化自適應速率限制器

        Args:
            max_calls: 在指定時間段內允許的最大請求數
            period: 時間段長度（秒）
            retry_count: 重試次數
            retry_backoff: 重試退避因子
            jitter: 隨機抖動因子
            strategy: 限制策略，可選 'fixed_window', 'sliding_window'
            min_calls: 最小請求數
            increase_factor: 增加因子
            decrease_factor: 減少因子
        """
        super().__init__(
            max_calls, period, retry_count, retry_backoff, jitter, strategy
        )
        self.min_calls = min_calls
        self.increase_factor = increase_factor
        self.decrease_factor = decrease_factor
        self.current_max_calls = max_calls
        self.success_count = 0
        self.failure_count = 0

    def report_success(self):
        """報告請求成功"""
        with self.lock:
            self.success_count += 1
            # 每 10 次成功請求，嘗試增加速率
            if self.success_count >= 10:
                self.current_max_calls = min(
                    self.max_calls, int(self.current_max_calls * self.increase_factor)
                )
                logger.debug(
                    f"增加速率限制：{self.current_max_calls} 請求/{self.period}秒"
                )
                self.success_count = 0
                self.failure_count = 0

    def report_failure(self, status_code: Optional[int] = None):
        """
        報告請求失敗

        Args:
            status_code: HTTP 狀態碼
        """
        with self.lock:
            self.failure_count += 1
            # 如果是 429 (Too Many Requests) 或連續失敗，立即減少速率
            if status_code == 429 or self.failure_count >= 3:
                self.current_max_calls = max(
                    self.min_calls, int(self.current_max_calls * self.decrease_factor)
                )
                logger.warning(
                    f"減少速率限制：{self.current_max_calls} 請求/{self.period}秒"
                )
                self.success_count = 0
                self.failure_count = 0

    def _can_proceed(self) -> bool:
        """
        檢查是否可以繼續請求

        Returns:
            bool: 是否可以繼續請求
        """
        if self.strategy == "fixed_window":
            current_time = time.time()
            # 檢查是否需要重置窗口
            if current_time - self.window_start > self.period:
                self.window_start = current_time
                self.call_count = 0

            return self.call_count < self.current_max_calls
        else:  # sliding_window
            current_time = time.time()
            # 移除過期的時間戳
            while (
                self.request_timestamps
                and current_time - self.request_timestamps[0] > self.period
            ):
                self.request_timestamps.popleft()

            return len(self.request_timestamps) < self.current_max_calls
