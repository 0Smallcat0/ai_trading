# -*- coding: utf-8 -*-
"""統一錯誤處理工具模組

此模組提供統一的錯誤處理功能，避免在各個模組中重複實現相同的錯誤處理邏輯。
整合了異常分類、重試機制、錯誤日誌記錄等常用錯誤處理模式。

主要功能：
- 統一異常類別定義
- 錯誤分類和處理策略
- 重試機制和退避策略
- 錯誤日誌記錄標準化
- 異常鏈處理

Example:
    基本使用：
    ```python
    from src.utils.error_handling_utils import handle_with_retry, ErrorCategory
    
    @handle_with_retry(max_retries=3, error_categories=[ErrorCategory.NETWORK])
    def api_call():
        # 可能失敗的 API 調用
        pass
    ```

Note:
    此模組整合了原本分散在各個模組中的錯誤處理邏輯，
    提供統一的介面和最佳實踐。
"""

import logging
import time
import functools
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

# 設定日誌
logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """錯誤分類枚舉"""
    NETWORK = "network"
    DATABASE = "database"
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    EXTERNAL_API = "external_api"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """錯誤嚴重程度枚舉"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """錯誤上下文資訊"""
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    module: str
    function: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class BaseError(Exception):
    """統一錯誤基類"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        """初始化錯誤
        
        Args:
            message: 錯誤訊息
            category: 錯誤分類
            severity: 錯誤嚴重程度
            details: 額外詳細資訊
            original_error: 原始異常
        """
        self.message = message
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.original_error = original_error
        self.timestamp = datetime.now()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "original_error": str(self.original_error) if self.original_error else None
        }


class NetworkError(BaseError):
    """網路錯誤"""
    
    def __init__(self, message: str = "網路連接錯誤", **kwargs):
        super().__init__(message, ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, **kwargs)


class DatabaseError(BaseError):
    """資料庫錯誤"""
    
    def __init__(self, message: str = "資料庫操作錯誤", **kwargs):
        super().__init__(message, ErrorCategory.DATABASE, ErrorSeverity.HIGH, **kwargs)


class ValidationError(BaseError):
    """驗證錯誤"""
    
    def __init__(self, message: str = "資料驗證失敗", **kwargs):
        super().__init__(message, ErrorCategory.VALIDATION, ErrorSeverity.LOW, **kwargs)


class AuthenticationError(BaseError):
    """認證錯誤"""
    
    def __init__(self, message: str = "認證失敗", **kwargs):
        super().__init__(message, ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, **kwargs)


class AuthorizationError(BaseError):
    """授權錯誤"""
    
    def __init__(self, message: str = "權限不足", **kwargs):
        super().__init__(message, ErrorCategory.AUTHORIZATION, ErrorSeverity.HIGH, **kwargs)


class BusinessLogicError(BaseError):
    """業務邏輯錯誤"""
    
    def __init__(self, message: str = "業務邏輯錯誤", **kwargs):
        super().__init__(message, ErrorCategory.BUSINESS_LOGIC, ErrorSeverity.MEDIUM, **kwargs)


class SystemRuntimeError(BaseError):
    """系統運行時錯誤"""

    def __init__(self, message: str = "系統錯誤", **kwargs):
        super().__init__(message, ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL, **kwargs)


class ExternalAPIError(BaseError):
    """外部 API 錯誤"""
    
    def __init__(self, message: str = "外部 API 調用失敗", **kwargs):
        super().__init__(message, ErrorCategory.EXTERNAL_API, ErrorSeverity.MEDIUM, **kwargs)


class ErrorClassifier:
    """錯誤分類器"""
    
    ERROR_PATTERNS = {
        ErrorCategory.NETWORK: [
            "connection", "timeout", "network", "socket", "dns", "ssl", "tls"
        ],
        ErrorCategory.DATABASE: [
            "database", "sql", "connection pool", "deadlock", "constraint", "integrity"
        ],
        ErrorCategory.VALIDATION: [
            "validation", "invalid", "format", "required", "missing", "type"
        ],
        ErrorCategory.AUTHENTICATION: [
            "authentication", "login", "password", "token", "unauthorized", "credential"
        ],
        ErrorCategory.AUTHORIZATION: [
            "authorization", "permission", "access", "forbidden", "privilege"
        ],
        ErrorCategory.EXTERNAL_API: [
            "api", "http", "rest", "response", "status code", "service unavailable"
        ]
    }
    
    @classmethod
    def classify_error(cls, error: Exception) -> ErrorCategory:
        """分類錯誤
        
        Args:
            error: 異常對象
            
        Returns:
            ErrorCategory: 錯誤分類
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        for category, patterns in cls.ERROR_PATTERNS.items():
            if any(pattern in error_str or pattern in error_type for pattern in patterns):
                return category
        
        return ErrorCategory.UNKNOWN
    
    @classmethod
    def is_retryable(cls, category: ErrorCategory) -> bool:
        """判斷錯誤是否可重試
        
        Args:
            category: 錯誤分類
            
        Returns:
            bool: 是否可重試
        """
        retryable_categories = {
            ErrorCategory.NETWORK,
            ErrorCategory.EXTERNAL_API,
            ErrorCategory.DATABASE  # 某些資料庫錯誤可重試
        }
        return category in retryable_categories


@dataclass
class RetryConfig:
    """重試配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_categories: Optional[List[ErrorCategory]] = None
    
    def __post_init__(self):
        if self.retryable_categories is None:
            self.retryable_categories = [
                ErrorCategory.NETWORK,
                ErrorCategory.EXTERNAL_API,
                ErrorCategory.DATABASE
            ]


class RetryHandler:
    """重試處理器"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
    
    def calculate_delay(self, attempt: int) -> float:
        """計算延遲時間
        
        Args:
            attempt: 嘗試次數（從 0 開始）
            
        Returns:
            float: 延遲秒數
        """
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # 添加 50% 的隨機抖動
        
        return delay
    
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """判斷是否應該重試
        
        Args:
            error: 異常對象
            attempt: 當前嘗試次數
            
        Returns:
            bool: 是否應該重試
        """
        if attempt >= self.config.max_retries:
            return False
        
        category = ErrorClassifier.classify_error(error)
        return category in self.config.retryable_categories


def handle_with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    error_categories: Optional[List[ErrorCategory]] = None
):
    """重試裝飾器
    
    Args:
        max_retries: 最大重試次數
        base_delay: 基礎延遲時間
        error_categories: 可重試的錯誤分類
        
    Returns:
        function: 裝飾後的函數
        
    Example:
        @handle_with_retry(max_retries=3, error_categories=[ErrorCategory.NETWORK])
        def api_call():
            # 可能失敗的 API 調用
            pass
    """
    config = RetryConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        retryable_categories=error_categories
    )
    retry_handler = RetryHandler(config)
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not retry_handler.should_retry(e, attempt):
                        logger.error(
                            "函數 %s 執行失敗，不可重試: %s",
                            func.__name__, e
                        )
                        raise e from e
                    
                    if attempt < max_retries:
                        delay = retry_handler.calculate_delay(attempt)
                        logger.warning(
                            "函數 %s 執行失敗 (嘗試 %d/%d)，%s 秒後重試: %s",
                            func.__name__, attempt + 1, max_retries + 1, delay, e
                        )
                        time.sleep(delay)
            
            # 理論上不會到達這裡
            raise last_exception
        
        return wrapper
    return decorator


class ErrorLogger:
    """錯誤日誌記錄器"""
    
    @staticmethod
    def log_error(
        error: Exception,
        context: Optional[ErrorContext] = None,
        logger_instance: Optional[logging.Logger] = None
    ):
        """記錄錯誤
        
        Args:
            error: 異常對象
            context: 錯誤上下文
            logger_instance: 日誌記錄器實例
        """
        if logger_instance is None:
            logger_instance = logger
        
        if isinstance(error, BaseError):
            error_data = error.to_dict()
        else:
            category = ErrorClassifier.classify_error(error)
            error_data = {
                "message": str(error),
                "category": category.value,
                "type": type(error).__name__,
                "timestamp": datetime.now().isoformat()
            }
        
        if context:
            error_data.update({
                "module": context.module,
                "function": context.function,
                "user_id": context.user_id,
                "request_id": context.request_id,
                "additional_data": context.additional_data
            })
        
        logger_instance.error(
            "錯誤詳情: %s",
            error_data,
            exc_info=True
        )


def create_error_context(
    module: str,
    function: str,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    **kwargs
) -> ErrorContext:
    """創建錯誤上下文
    
    Args:
        module: 模組名稱
        function: 函數名稱
        user_id: 用戶 ID
        request_id: 請求 ID
        **kwargs: 額外資料
        
    Returns:
        ErrorContext: 錯誤上下文
    """
    return ErrorContext(
        timestamp=datetime.now(),
        category=ErrorCategory.UNKNOWN,
        severity=ErrorSeverity.MEDIUM,
        module=module,
        function=function,
        user_id=user_id,
        request_id=request_id,
        additional_data=kwargs
    )
