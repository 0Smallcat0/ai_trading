"""
重試機制模組

此模組提供增強的重試機制，用於處理可能失敗的操作。
包含多種重試策略和回退機制，以及錯誤分類和處理。
"""

import functools
import logging
import random
import time
from typing import Any, Callable, List, Optional, Type, TypeVar, cast

# 導入日誌模組
try:
    from src.logging import LogCategory, get_logger

    logger = get_logger("retry", category=LogCategory.SYSTEM)
except ImportError:
    # 如果無法導入自定義日誌模組，則使用標準日誌模組
    logger = logging.getLogger("retry")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)

# 定義類型變量
T = TypeVar("T")


class RetryStrategy:
    """重試策略基類"""

    def __init__(self, max_retries: int = 3):
        """
        初始化重試策略

        Args:
            max_retries: 最大重試次數
        """
        self.max_retries = max_retries

    def get_delay(self, retry_count: int) -> float:
        """
        獲取重試延遲時間

        Args:
            retry_count: 當前重試次數

        Returns:
            float: 延遲時間（秒）
        """
        raise NotImplementedError("子類必須實現 get_delay 方法")


class ConstantRetryStrategy(RetryStrategy):
    """固定間隔重試策略"""

    def __init__(self, delay: float = 1.0, max_retries: int = 3):
        """
        初始化固定間隔重試策略

        Args:
            delay: 固定延遲時間（秒）
            max_retries: 最大重試次數
        """
        super().__init__(max_retries)
        self.delay = delay

    def get_delay(self, retry_count: int) -> float:
        """
        獲取重試延遲時間

        Args:
            retry_count: 當前重試次數

        Returns:
            float: 延遲時間（秒）
        """
        return self.delay


class LinearRetryStrategy(RetryStrategy):
    """線性增長重試策略"""

    def __init__(
        self, initial_delay: float = 1.0, increment: float = 1.0, max_retries: int = 3
    ):
        """
        初始化線性增長重試策略

        Args:
            initial_delay: 初始延遲時間（秒）
            increment: 每次重試的增量（秒）
            max_retries: 最大重試次數
        """
        super().__init__(max_retries)
        self.initial_delay = initial_delay
        self.increment = increment

    def get_delay(self, retry_count: int) -> float:
        """
        獲取重試延遲時間

        Args:
            retry_count: 當前重試次數

        Returns:
            float: 延遲時間（秒）
        """
        return self.initial_delay + (retry_count * self.increment)


class ExponentialRetryStrategy(RetryStrategy):
    """指數增長重試策略"""

    def __init__(
        self,
        initial_delay: float = 1.0,
        factor: float = 2.0,
        max_retries: int = 3,
        jitter: bool = True,
        max_delay: Optional[float] = None,
    ):
        """
        初始化指數增長重試策略

        Args:
            initial_delay: 初始延遲時間（秒）
            factor: 指數因子
            max_retries: 最大重試次數
            jitter: 是否添加隨機抖動
            max_delay: 最大延遲時間（秒），如果為 None 則無上限
        """
        super().__init__(max_retries)
        self.initial_delay = initial_delay
        self.factor = factor
        self.jitter = jitter
        self.max_delay = max_delay

    def get_delay(self, retry_count: int) -> float:
        """
        獲取重試延遲時間

        Args:
            retry_count: 當前重試次數

        Returns:
            float: 延遲時間（秒）
        """
        delay = self.initial_delay * (self.factor**retry_count)

        # 應用最大延遲限制
        if self.max_delay is not None:
            delay = min(delay, self.max_delay)

        # 添加隨機抖動（0-25%）
        if self.jitter:
            delay = delay * (1 + random.uniform(0, 0.25))

        return delay


def retry(
    max_retries: int = 3,
    retry_strategy: Optional[RetryStrategy] = None,
    retry_on_exceptions: Optional[List[Type[Exception]]] = None,
    retry_if_result: Optional[Callable[[Any], bool]] = None,
    fallback_result: Any = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    logger_name: Optional[str] = None,
    error_code_prefix: str = "SYS-RETRY",
    raise_on_max_retries: bool = False,
):
    """
    增強的重試裝飾器

    當函式執行失敗時，根據指定的策略自動重試

    Args:
        max_retries: 最大重試次數，預設為 3
        retry_strategy: 重試策略，如果為 None 則使用指數重試策略
        retry_on_exceptions: 需要重試的異常類型列表，如果為 None 則重試所有異常
        retry_if_result: 根據結果決定是否重試的函數，如果為 None 則不根據結果重試
        fallback_result: 所有重試失敗後的返回值，如果為 None 則拋出最後一個異常
        on_retry: 每次重試前調用的函數，接收重試次數、異常和延遲時間
        logger_name: 日誌記錄器名稱，如果為 None 則使用函數所在模組的名稱
        error_code_prefix: 錯誤代碼前綴
        raise_on_max_retries: 是否在達到最大重試次數後拋出異常

    Returns:
        function: 裝飾後的函式

    Example:
        @retry(max_retries=5, retry_strategy=ExponentialRetryStrategy(initial_delay=0.5, factor=2))
        def unstable_function():
            # 可能失敗的函式
            pass
    """
    # 如果未指定重試策略，則使用指數重試策略
    if retry_strategy is None:
        retry_strategy = ExponentialRetryStrategy(
            initial_delay=1.0, factor=2.0, max_retries=max_retries
        )

    # 確保重試策略的最大重試次數與裝飾器參數一致
    retry_strategy.max_retries = max_retries

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # 獲取函數的完整限定名稱
    """
    decorator

    Args:
        func:

    Returns:
        Callable[...]:
    """
        module_name = func.__module__
        qualname = f"{module_name}.{func.__qualname__}"

        # 設置日誌記錄器
        func_logger = logger
        if logger_name:
            try:
                from src.logging import get_logger

                func_logger = get_logger(logger_name)
            except ImportError:
                func_logger = logging.getLogger(logger_name)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
        """
        wrapper


        Returns:
            T:
        """
            last_exception = None
            for retry_count in range(retry_strategy.max_retries + 1):
                try:
                    # 執行函數
                    result = func(*args, **kwargs)

                    # 檢查結果是否需要重試
                    if retry_if_result and retry_count < retry_strategy.max_retries:
                        if retry_if_result(result):
                            delay = retry_strategy.get_delay(retry_count)
                            func_logger.warning(
                                f"{error_code_prefix}-001: 函數 {qualname} 返回需要重試的結果，"
                                f"將在 {delay:.2f} 秒後進行第 {retry_count + 1} 次重試"
                            )

                            # 調用重試回調
                            if on_retry:
                                on_retry(
                                    retry_count,
                                    Exception("Result requires retry"),
                                    delay,
                                )

                            time.sleep(delay)
                            continue

                    # 返回成功結果
                    return result

                except Exception as e:
                    last_exception = e

                    # 檢查是否是需要重試的異常類型
                    should_retry = True
                    if retry_on_exceptions:
                        should_retry = any(
                            isinstance(e, exc_type) for exc_type in retry_on_exceptions
                        )

                    if should_retry and retry_count < retry_strategy.max_retries:
                        delay = retry_strategy.get_delay(retry_count)
                        func_logger.warning(
                            f"{error_code_prefix}-002: 函數 {qualname} 執行失敗 ({type(e).__name__}: {str(e)})，"
                            f"將在 {delay:.2f} 秒後進行第 {retry_count + 1} 次重試"
                        )

                        # 調用重試回調
                        if on_retry:
                            on_retry(retry_count, e, delay)

                        time.sleep(delay)
                    else:
                        # 如果不需要重試或已達最大重試次數，則記錄錯誤並跳出循環
                        if retry_count == retry_strategy.max_retries:
                            func_logger.error(
                                f"{error_code_prefix}-003: 函數 {qualname} 執行失敗 {retry_strategy.max_retries} 次，"
                                f"放棄重試: {type(last_exception).__name__}: {str(last_exception)}"
                            )
                        else:
                            func_logger.error(
                                f"{error_code_prefix}-004: 函數 {qualname} 執行失敗，"
                                f"異常類型不在重試列表中: {type(e).__name__}: {str(e)}"
                            )
                        break

            # 所有重試都失敗
            if last_exception is not None:
                if raise_on_max_retries:
                    raise last_exception
                return fallback_result

            # 不應該到達這裡，但為了類型檢查
            return cast(T, fallback_result)

        return wrapper

    return decorator


# 導出模組內容
__all__ = [
    "RetryStrategy",
    "ConstantRetryStrategy",
    "LinearRetryStrategy",
    "ExponentialRetryStrategy",
    "retry",
]
