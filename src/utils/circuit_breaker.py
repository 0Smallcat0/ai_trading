"""
熔斷器模組

此模組提供熔斷器模式的實現，用於防止系統反覆調用可能失敗的操作。
當失敗率達到閾值時，熔斷器會進入打開狀態，阻止後續調用。
"""

import functools
import logging
import threading
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

# 導入日誌模組
try:
    from src.logging import LogCategory, get_logger

    logger = get_logger("circuit_breaker", category=LogCategory.SYSTEM)
except ImportError:
    # 如果無法導入自定義日誌模組，則使用標準日誌模組
    logger = logging.getLogger("circuit_breaker")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)

# 定義類型變量
T = TypeVar("T")


class CircuitState(Enum):
    """熔斷器狀態"""

    CLOSED = "closed"  # 關閉狀態，允許調用
    OPEN = "open"  # 打開狀態，阻止調用
    HALF_OPEN = "half_open"  # 半開狀態，允許有限調用


class CircuitBreaker:
    """熔斷器類"""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
        failure_window_size: int = 10,
        exclude_exceptions: Optional[List[type]] = None,
    ):
        """
        初始化熔斷器

        Args:
            name: 熔斷器名稱
            failure_threshold: 失敗閾值，連續失敗次數達到此值時熔斷器打開
            recovery_timeout: 恢復超時時間（秒），熔斷器打開後經過此時間進入半開狀態
            half_open_max_calls: 半開狀態下允許的最大調用次數
            failure_window_size: 失敗窗口大小，用於計算失敗率
            exclude_exceptions: 不計入失敗的異常類型列表
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.failure_window_size = failure_window_size
        self.exclude_exceptions = exclude_exceptions or []

        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time = 0
        self.last_state_change_time = time.time()
        self.half_open_calls = 0
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.recent_failures: List[float] = []  # 最近的失敗時間戳
        self.recent_successes: List[float] = []  # 最近的成功時間戳

        self.lock = threading.RLock()

        logger.info(
            f"初始化熔斷器 '{name}': 失敗閾值={failure_threshold}, 恢復超時={recovery_timeout}秒"
        )

    def allow_request(self) -> bool:
        """
        檢查是否允許請求

        Returns:
            bool: 是否允許請求
        """
        with self.lock:
            self._update_state()

            if self.state == CircuitState.CLOSED:
                return True
            elif self.state == CircuitState.OPEN:
                return False
            elif self.state == CircuitState.HALF_OPEN:
                return self.half_open_calls < self.half_open_max_calls

            # 不應該到達這裡
            return False

    def on_success(self) -> None:
        """記錄成功調用"""
        with self.lock:
            self.total_calls += 1
            self.successful_calls += 1
            current_time = time.time()
            self.recent_successes.append(current_time)

            # 保持窗口大小
            if len(self.recent_successes) > self.failure_window_size:
                self.recent_successes.pop(0)

            if self.state == CircuitState.HALF_OPEN:
                self.successes += 1
                self.half_open_calls += 1

                # 如果半開狀態下成功次數達到閾值，則關閉熔斷器
                if self.successes >= self.half_open_max_calls:
                    self._transition_to_closed()
            else:
                # 重置失敗計數
                self.failures = 0

    def on_failure(self, exception: Exception) -> None:
        """
        記錄失敗調用

        Args:
            exception: 異常
        """
        # 檢查是否是排除的異常
        if any(isinstance(exception, exc_type) for exc_type in self.exclude_exceptions):
            logger.debug(f"熔斷器 '{self.name}' 忽略異常: {type(exception).__name__}")
            return

        with self.lock:
            self.total_calls += 1
            self.failed_calls += 1
            current_time = time.time()
            self.last_failure_time = current_time
            self.recent_failures.append(current_time)

            # 保持窗口大小
            if len(self.recent_failures) > self.failure_window_size:
                self.recent_failures.pop(0)

            if self.state == CircuitState.CLOSED:
                self.failures += 1

                # 如果失敗次數達到閾值，則打開熔斷器
                if self.failures >= self.failure_threshold:
                    self._transition_to_open()
            elif self.state == CircuitState.HALF_OPEN:
                # 半開狀態下任何失敗都會重新打開熔斷器
                self._transition_to_open()

    def _update_state(self) -> None:
        """更新熔斷器狀態"""
        current_time = time.time()

        # 如果熔斷器處於打開狀態且已經過了恢復超時時間，則進入半開狀態
        if (
            self.state == CircuitState.OPEN
            and current_time - self.last_state_change_time >= self.recovery_timeout
        ):
            self._transition_to_half_open()

    def _transition_to_open(self) -> None:
        """轉換到打開狀態"""
        if self.state != CircuitState.OPEN:
            logger.warning(
                f"熔斷器 '{self.name}' 狀態從 {self.state.value} 變更為 {CircuitState.OPEN.value}"
            )
            self.state = CircuitState.OPEN
            self.last_state_change_time = time.time()
            self.failures = 0
            self.successes = 0
            self.half_open_calls = 0

    def _transition_to_half_open(self) -> None:
        """轉換到半開狀態"""
        if self.state != CircuitState.HALF_OPEN:
            logger.info(
                f"熔斷器 '{self.name}' 狀態從 {self.state.value} 變更為 {CircuitState.HALF_OPEN.value}"
            )
            self.state = CircuitState.HALF_OPEN
            self.last_state_change_time = time.time()
            self.failures = 0
            self.successes = 0
            self.half_open_calls = 0

    def _transition_to_closed(self) -> None:
        """轉換到關閉狀態"""
        if self.state != CircuitState.CLOSED:
            logger.info(
                f"熔斷器 '{self.name}' 狀態從 {self.state.value} 變更為 {CircuitState.CLOSED.value}"
            )
            self.state = CircuitState.CLOSED
            self.last_state_change_time = time.time()
            self.failures = 0
            self.successes = 0
            self.half_open_calls = 0

    def reset(self) -> None:
        """重置熔斷器"""
        with self.lock:
            logger.info(f"重置熔斷器 '{self.name}'")
            self.state = CircuitState.CLOSED
            self.failures = 0
            self.successes = 0
            self.last_failure_time = 0
            self.last_state_change_time = time.time()
            self.half_open_calls = 0
            self.recent_failures = []
            self.recent_successes = []

    def get_state(self) -> CircuitState:
        """
        獲取當前狀態

        Returns:
            CircuitState: 當前狀態
        """
        with self.lock:
            self._update_state()
            return self.state

    def get_metrics(self) -> Dict[str, Any]:
        """
        獲取熔斷器指標

        Returns:
            Dict[str, Any]: 熔斷器指標
        """
        with self.lock:
            self._update_state()

            # 計算失敗率
            failure_rate = 0.0
            if self.total_calls > 0:
                failure_rate = self.failed_calls / self.total_calls

            # 計算最近的失敗率
            recent_failure_rate = 0.0
            recent_calls = len(self.recent_failures) + len(self.recent_successes)
            if recent_calls > 0:
                recent_failure_rate = len(self.recent_failures) / recent_calls

            return {
                "name": self.name,
                "state": self.state.value,
                "failures": self.failures,
                "successes": self.successes,
                "total_calls": self.total_calls,
                "successful_calls": self.successful_calls,
                "failed_calls": self.failed_calls,
                "failure_rate": failure_rate,
                "recent_failure_rate": recent_failure_rate,
                "last_failure_time": self.last_failure_time,
                "last_state_change_time": self.last_state_change_time,
                "time_in_current_state": time.time() - self.last_state_change_time,
            }


class CircuitBreakerRegistry:
    """熔斷器註冊表"""

    def __init__(self):
        """初始化熔斷器註冊表"""
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.lock = threading.RLock()

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
        failure_window_size: int = 10,
        exclude_exceptions: Optional[List[type]] = None,
    ) -> CircuitBreaker:
        """
        獲取或創建熔斷器

        Args:
            name: 熔斷器名稱
            failure_threshold: 失敗閾值
            recovery_timeout: 恢復超時時間（秒）
            half_open_max_calls: 半開狀態下允許的最大調用次數
            failure_window_size: 失敗窗口大小
            exclude_exceptions: 不計入失敗的異常類型列表

        Returns:
            CircuitBreaker: 熔斷器
        """
        with self.lock:
            if name not in self.circuit_breakers:
                self.circuit_breakers[name] = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    half_open_max_calls=half_open_max_calls,
                    failure_window_size=failure_window_size,
                    exclude_exceptions=exclude_exceptions,
                )
            return self.circuit_breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """
        獲取熔斷器

        Args:
            name: 熔斷器名稱

        Returns:
            Optional[CircuitBreaker]: 熔斷器，如果不存在則返回 None
        """
        return self.circuit_breakers.get(name)

    def get_all(self) -> Dict[str, CircuitBreaker]:
        """
        獲取所有熔斷器

        Returns:
            Dict[str, CircuitBreaker]: 所有熔斷器
        """
        return self.circuit_breakers.copy()

    def reset_all(self) -> None:
        """重置所有熔斷器"""
        for circuit_breaker in self.circuit_breakers.values():
            circuit_breaker.reset()


# 創建全局熔斷器註冊表
circuit_breaker_registry = CircuitBreakerRegistry()


def with_circuit_breaker(
    name: str,
    fallback_value: Any = None,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    half_open_max_calls: int = 1,
    failure_window_size: int = 10,
    exclude_exceptions: Optional[List[type]] = None,
    logger_name: Optional[str] = None,
    error_code_prefix: str = "SYS-CIRCUIT",
    raise_on_open: bool = False,
):
    """
    熔斷器裝飾器

    當函式執行失敗次數達到閾值時，熔斷器會打開，阻止後續調用

    Args:
        name: 熔斷器名稱
        fallback_value: 熔斷器打開時的返回值
        failure_threshold: 失敗閾值
        recovery_timeout: 恢復超時時間（秒）
        half_open_max_calls: 半開狀態下允許的最大調用次數
        failure_window_size: 失敗窗口大小
        exclude_exceptions: 不計入失敗的異常類型列表
        logger_name: 日誌記錄器名稱，如果為 None 則使用函數所在模組的名稱
        error_code_prefix: 錯誤代碼前綴
        raise_on_open: 熔斷器打開時是否拋出異常

    Returns:
        function: 裝飾後的函式

    Example:
        @with_circuit_breaker("api_call", fallback_value={"status": "error"})
        def call_external_api():
            # 調用外部 API
            pass
    """
    # 獲取或創建熔斷器
    circuit_breaker = circuit_breaker_registry.get_or_create(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        half_open_max_calls=half_open_max_calls,
        failure_window_size=failure_window_size,
        exclude_exceptions=exclude_exceptions,
    )

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
            # 檢查是否允許請求
        """
        wrapper


        Returns:
            T:
        """
            if not circuit_breaker.allow_request():
                if raise_on_open:
                    func_logger.warning(
                        f"{error_code_prefix}-001: 熔斷器 '{name}' 已打開，拒絕調用函數 {qualname}"
                    )
                    raise CircuitBreakerOpenError(f"熔斷器 '{name}' 已打開")
                else:
                    func_logger.warning(
                        f"{error_code_prefix}-002: 熔斷器 '{name}' 已打開，返回備援值"
                    )
                    return cast(T, fallback_value)

            try:
                # 執行函數
                result = func(*args, **kwargs)

                # 記錄成功
                circuit_breaker.on_success()

                return result
            except Exception as e:
                # 記錄失敗
                circuit_breaker.on_failure(e)

                # 記錄錯誤
                func_logger.error(
                    f"{error_code_prefix}-003: 函數 {qualname} 執行失敗: {type(e).__name__}: {str(e)}"
                )

                # 重新拋出異常
                raise

        return wrapper

    return decorator


class CircuitBreakerOpenError(Exception):
    """熔斷器打開錯誤"""


# 導出模組內容
__all__ = [
    "CircuitState",
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "with_circuit_breaker",
    "CircuitBreakerOpenError",
    "circuit_breaker_registry",
]
