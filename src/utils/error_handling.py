"""
錯誤處理模組

此模組提供統一的錯誤處理機制，包括錯誤代碼、錯誤分類、錯誤報告等功能。
"""

import functools
import json
import logging
import os
import sys
import time
import traceback
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Union, cast

# 導入日誌模組
try:
    from src.logging import LogCategory, get_logger

    logger = get_logger("error_handling", category=LogCategory.ERROR)
except ImportError:
    # 如果無法導入自定義日誌模組，則使用標準日誌模組
    logger = logging.getLogger("error_handling")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)

# 定義類型變量
T = TypeVar("T")


class ErrorSeverity(Enum):
    """錯誤嚴重程度"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """錯誤類別"""

    SYSTEM = "system"
    DATA = "data"
    MODEL = "model"
    TRADE = "trade"
    EVENT = "event"
    INTEGRATION = "integration"
    SECURITY = "security"
    NETWORK = "network"
    DATABASE = "database"
    API = "api"
    USER = "user"
    UNKNOWN = "unknown"


class ErrorCode:
    """錯誤代碼類"""

    def __init__(
        self,
        code: str,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        http_status: Optional[int] = None,
        description: str = "",
        resolution: str = "",
    ):
        """
        初始化錯誤代碼

        Args:
            code: 錯誤代碼
            message: 錯誤消息
            category: 錯誤類別
            severity: 錯誤嚴重程度
            http_status: HTTP 狀態碼
            description: 錯誤描述
            resolution: 解決方案
        """
        self.code = code
        self.message = message
        self.category = category
        self.severity = severity
        self.http_status = http_status
        self.description = description
        self.resolution = resolution

    def __str__(self) -> str:
        """
        轉換為字符串

        Returns:
            str: 字符串表示
        """
        return f"{self.code}: {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典

        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "code": self.code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "http_status": self.http_status,
            "description": self.description,
            "resolution": self.resolution,
        }


class AppError(Exception):
    """應用錯誤類"""

    def __init__(
        self,
        error_code: Union[ErrorCode, str],
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        """
        初始化應用錯誤

        Args:
            error_code: 錯誤代碼或錯誤代碼字符串
            message: 錯誤消息，如果為 None 則使用錯誤代碼的消息
            details: 錯誤詳細信息
            cause: 原因異常
        """
        if isinstance(error_code, str):
            # 如果是字符串，則嘗試從錯誤代碼註冊表中獲取
            error_code_obj = error_code_registry.get(error_code)
            if error_code_obj is None:
                # 如果找不到，則創建一個臨時錯誤代碼
                error_code_obj = ErrorCode(
                    code=error_code,
                    message=message or "未知錯誤",
                    category=ErrorCategory.UNKNOWN,
                    severity=ErrorSeverity.ERROR,
                )
        else:
            error_code_obj = error_code

        self.error_code = error_code_obj
        self.message = message or error_code_obj.message
        self.details = details or {}
        self.cause = cause
        self.timestamp = time.time()
        self.traceback = traceback.format_exc() if sys.exc_info()[0] else None

        # 調用父類初始化
        super().__init__(self.message)

    def __str__(self) -> str:
        """
        轉換為字符串

        Returns:
            str: 字符串表示
        """
        return f"{self.error_code.code}: {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典

        Returns:
            Dict[str, Any]: 字典表示
        """
        result = {
            "error_code": self.error_code.code,
            "message": self.message,
            "category": self.error_code.category.value,
            "severity": self.error_code.severity.value,
            "timestamp": self.timestamp,
            "details": self.details,
        }

        if self.cause:
            result["cause"] = str(self.cause)

        if self.traceback:
            result["traceback"] = self.traceback

        return result

    def to_json(self, indent: Optional[int] = None) -> str:
        """
        轉換為 JSON 字符串

        Args:
            indent: 縮進

        Returns:
            str: JSON 字符串
        """
        return json.dumps(self.to_dict(), indent=indent)

    def log(self, logger_name: Optional[str] = None) -> None:
        """
        記錄錯誤

        Args:
            logger_name: 日誌記錄器名稱，如果為 None 則使用默認日誌記錄器
        """
        log = logger
        if logger_name:
            try:
                from src.logging import get_logger

                log = get_logger(logger_name)
            except ImportError:
                log = logging.getLogger(logger_name)

        # 根據嚴重程度選擇日誌級別
        if self.error_code.severity == ErrorSeverity.INFO:
            log.info(str(self), extra={"error": self.to_dict()})
        elif self.error_code.severity == ErrorSeverity.WARNING:
            log.warning(str(self), extra={"error": self.to_dict()})
        elif self.error_code.severity == ErrorSeverity.CRITICAL:
            log.critical(str(self), extra={"error": self.to_dict()})
        else:
            log.error(str(self), extra={"error": self.to_dict()})


class ErrorCodeRegistry:
    """錯誤代碼註冊表"""

    def __init__(self):
        """初始化錯誤代碼註冊表"""
        self.error_codes: Dict[str, ErrorCode] = {}

    def register(self, error_code: ErrorCode) -> None:
        """
        註冊錯誤代碼

        Args:
            error_code: 錯誤代碼
        """
        self.error_codes[error_code.code] = error_code

    def get(self, code: str) -> Optional[ErrorCode]:
        """
        獲取錯誤代碼

        Args:
            code: 錯誤代碼字符串

        Returns:
            Optional[ErrorCode]: 錯誤代碼，如果不存在則返回 None
        """
        return self.error_codes.get(code)

    def load_from_file(self, file_path: str) -> None:
        """
        從文件加載錯誤代碼

        Args:
            file_path: 文件路徑
        """
        if not os.path.exists(file_path):
            logger.warning(f"錯誤代碼文件不存在: {file_path}")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for code_data in data:
                code = code_data.get("code")
                message = code_data.get("message", "")
                category_value = code_data.get("category", "unknown")
                severity_value = code_data.get("severity", "error")
                http_status = code_data.get("http_status")
                description = code_data.get("description", "")
                resolution = code_data.get("resolution", "")

                # 解析類別和嚴重程度
                try:
                    category = ErrorCategory(category_value)
                except ValueError:
                    category = ErrorCategory.UNKNOWN

                try:
                    severity = ErrorSeverity(severity_value)
                except ValueError:
                    severity = ErrorSeverity.ERROR

                # 創建錯誤代碼
                error_code = ErrorCode(
                    code=code,
                    message=message,
                    category=category,
                    severity=severity,
                    http_status=http_status,
                    description=description,
                    resolution=resolution,
                )

                # 註冊錯誤代碼
                self.register(error_code)

            logger.info(f"從文件加載了 {len(data)} 個錯誤代碼: {file_path}")
        except Exception as e:
            logger.error(f"加載錯誤代碼文件失敗: {str(e)}")


def handle_errors(
    error_handler: Optional[Callable[[Exception], Any]] = None,
    reraise: bool = True,
    log_errors: bool = True,
    logger_name: Optional[str] = None,
    default_return: Any = None,
):
    """
    錯誤處理裝飾器

    Args:
        error_handler: 錯誤處理函數，接收異常並返回處理結果
        reraise: 是否重新拋出異常
        log_errors: 是否記錄錯誤
        logger_name: 日誌記錄器名稱，如果為 None 則使用函數所在模組的名稱
        default_return: 發生錯誤時的默認返回值

    Returns:
        function: 裝飾後的函式

    Example:
        @handle_errors(reraise=False, default_return={"status": "error"})
        def process_data():
            # 處理數據
            pass
    """

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
                # 執行函數
                return func(*args, **kwargs)
            except Exception as e:
                # 記錄錯誤
                if log_errors:
                    if isinstance(e, AppError):
                        e.log(logger_name)
                    else:
                        func_logger.error(
                            f"函數 {qualname} 執行異常: {type(e).__name__}: {str(e)}",
                            exc_info=True,
                        )

                # 調用錯誤處理函數
                if error_handler:
                    try:
                        result = error_handler(e)
                        return cast(T, result)
                    except Exception as handler_error:
                        func_logger.error(
                            f"錯誤處理函數執行異常: {type(handler_error).__name__}: {str(handler_error)}",
                            exc_info=True,
                        )

                # 重新拋出異常或返回默認值
                if reraise:
                    raise
                return cast(T, default_return)

        return wrapper

    return decorator


# 創建全局錯誤代碼註冊表
error_code_registry = ErrorCodeRegistry()


# 導出模組內容
__all__ = [
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorCode",
    "AppError",
    "ErrorCodeRegistry",
    "handle_errors",
    "error_code_registry",
]
