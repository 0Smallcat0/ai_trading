"""
備援機制模組

此模組提供備援機制，用於在主要操作失敗時提供替代方案。
包含多種備援策略和錯誤處理機制。
"""

import functools
import logging
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

# 導入日誌模組
try:
    from src.logging import LogCategory, get_logger

    logger = get_logger("fallback", category=LogCategory.SYSTEM)
except ImportError:
    # 如果無法導入自定義日誌模組，則使用標準日誌模組
    logger = logging.getLogger("fallback")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)

# 定義類型變量
T = TypeVar("T")


class FallbackStrategy:
    """備援策略基類"""

    def __init__(self, name: str):
        """
        初始化備援策略

        Args:
            name: 策略名稱
        """
        self.name = name
        self.last_error = None
        self.last_error_time = None
        self.error_count = 0
        self.success_count = 0

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """
        執行備援策略

        Args:
            *args: 位置參數
            **kwargs: 關鍵字參數

        Returns:
            Any: 執行結果
        """
        raise NotImplementedError("子類必須實現 execute 方法")

    def record_error(self, error: Exception) -> None:
        """
        記錄錯誤

        Args:
            error: 錯誤
        """
        self.last_error = error
        self.last_error_time = time.time()
        self.error_count += 1

    def record_success(self) -> None:
        """記錄成功"""
        self.success_count += 1

    def get_status(self) -> Dict[str, Any]:
        """
        獲取策略狀態

        Returns:
            Dict[str, Any]: 策略狀態
        """
        return {
            "name": self.name,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "last_error": str(self.last_error) if self.last_error else None,
            "last_error_time": self.last_error_time,
        }


class FunctionFallbackStrategy(FallbackStrategy):
    """函數備援策略"""

    def __init__(self, name: str, func: Callable[..., Any]):
        """
        初始化函數備援策略

        Args:
            name: 策略名稱
            func: 備援函數
        """
        super().__init__(name)
        self.func = func

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """
        執行備援函數

        Args:
            *args: 位置參數
            **kwargs: 關鍵字參數

        Returns:
            Any: 執行結果
        """
        try:
            result = self.func(*args, **kwargs)
            self.record_success()
            return result
        except Exception as e:
            self.record_error(e)
            raise


class ValueFallbackStrategy(FallbackStrategy):
    """值備援策略"""

    def __init__(self, name: str, value: Any):
        """
        初始化值備援策略

        Args:
            name: 策略名稱
            value: 備援值
        """
        super().__init__(name)
        self.value = value

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """
        返回備援值

        Args:
            *args: 位置參數
            **kwargs: 關鍵字參數

        Returns:
            Any: 備援值
        """
        self.record_success()
        return self.value


class ChainFallbackStrategy(FallbackStrategy):
    """鏈式備援策略"""

    def __init__(self, name: str, strategies: List[FallbackStrategy]):
        """
        初始化鏈式備援策略

        Args:
            name: 策略名稱
            strategies: 備援策略列表
        """
        super().__init__(name)
        self.strategies = strategies

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """
        依次執行備援策略，直到成功或全部失敗

        Args:
            *args: 位置參數
            **kwargs: 關鍵字參數

        Returns:
            Any: 執行結果

        Raises:
            Exception: 如果所有策略都失敗，則拋出最後一個異常
        """
        last_exception = None
        for strategy in self.strategies:
            try:
                result = strategy.execute(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"備援策略 '{strategy.name}' 執行失敗: {str(e)}，嘗試下一個策略"
                )

        # 所有策略都失敗
        if last_exception:
            self.record_error(last_exception)
            raise last_exception

        # 不應該到達這裡，但為了類型檢查
        return None


class FallbackManager:
    """備援管理器"""

    def __init__(self):
        """初始化備援管理器"""
        self.strategies: Dict[str, FallbackStrategy] = {}
        self.default_strategy: Optional[str] = None

    def register_strategy(
        self, strategy: FallbackStrategy, is_default: bool = False
    ) -> None:
        """
        註冊備援策略

        Args:
            strategy: 備援策略
            is_default: 是否設為默認策略
        """
        self.strategies[strategy.name] = strategy
        if is_default:
            self.default_strategy = strategy.name

    def get_strategy(self, name: Optional[str] = None) -> Optional[FallbackStrategy]:
        """
        獲取備援策略

        Args:
            name: 策略名稱，如果為 None 則返回默認策略

        Returns:
            Optional[FallbackStrategy]: 備援策略，如果找不到則返回 None
        """
        if name is None:
            if self.default_strategy:
                return self.strategies.get(self.default_strategy)
            return None
        return self.strategies.get(name)

    def execute_strategy(
        self, name: Optional[str] = None, *args: Any, **kwargs: Any
    ) -> Any:
        """
        執行備援策略

        Args:
            name: 策略名稱，如果為 None 則使用默認策略
            *args: 位置參數
            **kwargs: 關鍵字參數

        Returns:
            Any: 執行結果

        Raises:
            ValueError: 如果找不到指定的策略
            Exception: 如果策略執行失敗
        """
        strategy = self.get_strategy(name)
        if strategy is None:
            raise ValueError(f"找不到備援策略: {name or '默認策略'}")

        return strategy.execute(*args, **kwargs)

    def get_all_strategies(self) -> Dict[str, FallbackStrategy]:
        """
        獲取所有備援策略

        Returns:
            Dict[str, FallbackStrategy]: 所有備援策略
        """
        return self.strategies.copy()


def with_fallback(
    fallback_strategy: Union[FallbackStrategy, Callable[..., Any], Any],
    logger_name: Optional[str] = None,
    error_code_prefix: str = "SYS-FALLBACK",
):
    """
    備援裝飾器

    當函式執行失敗時，使用備援策略

    Args:
        fallback_strategy: 備援策略、函數或值
        logger_name: 日誌記錄器名稱，如果為 None 則使用函數所在模組的名稱
        error_code_prefix: 錯誤代碼前綴

    Returns:
        function: 裝飾後的函式

    Example:
        @with_fallback(lambda x, y: 0)
        def divide(x, y):
            return x / y
    """
    # 將備援策略轉換為 FallbackStrategy 對象
    if isinstance(fallback_strategy, FallbackStrategy):
        strategy = fallback_strategy
    elif callable(fallback_strategy):
        strategy = FunctionFallbackStrategy("function_fallback", fallback_strategy)
    else:
        strategy = ValueFallbackStrategy("value_fallback", fallback_strategy)

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
            try:
                # 執行原函數
                return func(*args, **kwargs)
            except Exception as e:
                # 記錄錯誤
                func_logger.error(
                    f"{error_code_prefix}-001: 函數 {qualname} 執行失敗，使用備援策略: "
                    f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                )

                # 執行備援策略
                try:
                    result = strategy.execute(*args, **kwargs)
                    func_logger.info(
                        f"{error_code_prefix}-002: 備援策略 '{strategy.name}' 執行成功"
                    )
                    return cast(T, result)
                except Exception as fallback_error:
                    # 備援策略也失敗
                    func_logger.error(
                        f"{error_code_prefix}-003: 備援策略 '{strategy.name}' 執行失敗: "
                        f"{type(fallback_error).__name__}: {str(fallback_error)}\n{traceback.format_exc()}"
                    )
                    raise fallback_error

        return wrapper

    return decorator


# 創建全局備援管理器
fallback_manager = FallbackManager()


# 導出模組內容
__all__ = [
    "FallbackStrategy",
    "FunctionFallbackStrategy",
    "ValueFallbackStrategy",
    "ChainFallbackStrategy",
    "FallbackManager",
    "with_fallback",
    "fallback_manager",
]
