"""異常處理工具

此模組提供 API 異常處理相關的工具，包括自定義異常類、異常處理器等。
"""

from datetime import datetime
from typing import Dict, Any, Optional
import logging

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError as PydanticValidationError

from src.api.models.responses import (
    ErrorResponse,
    ValidationErrorResponse,
    ValidationErrorDetail,
)

logger = logging.getLogger(__name__)


class APIException(Exception):
    """API 自定義異常基類"""

    def __init__(
        self,
        message: str,
        error_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(APIException):
    """認證錯誤"""

    def __init__(
        self, message: str = "認證失敗", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, 401, details)


class AuthorizationError(APIException):
    """授權錯誤"""

    def __init__(
        self, message: str = "權限不足", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, 403, details)


class DataValidationError(APIException):
    """資料驗證錯誤"""

    def __init__(
        self, message: str = "資料驗證失敗", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, 422, details)


class NotFoundError(APIException):
    """資源不存在錯誤"""

    def __init__(
        self, message: str = "資源不存在", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, 404, details)


class ConflictError(APIException):
    """衝突錯誤"""

    def __init__(
        self, message: str = "資源衝突", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, 409, details)


class RateLimitError(APIException):
    """速率限制錯誤"""

    def __init__(
        self, message: str = "請求過於頻繁", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, 429, details)


class BusinessLogicError(APIException):
    """業務邏輯錯誤"""

    def __init__(
        self, message: str = "業務邏輯錯誤", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, 400, details)


class ExternalServiceError(APIException):
    """外部服務錯誤"""

    def __init__(
        self, message: str = "外部服務錯誤", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, 502, details)


class DatabaseError(APIException):
    """資料庫錯誤"""

    def __init__(
        self, message: str = "資料庫操作失敗", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, 500, details)


def setup_exception_handlers(app: FastAPI):
    """設定異常處理器"""

    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """API 自定義異常處理器"""
        logger.error(
            "API 異常: %s",
            exc.message,
            extra={
                "error_code": exc.error_code,
                "details": exc.details,
                "path": request.url.path,
                "method": request.method,
            },
        )

        response_obj = ErrorResponse(
            success=False,
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            request_id=getattr(request.state, "request_id", None),
        )

        return JSONResponse(
            status_code=exc.error_code, content=response_obj.model_dump(mode="json")
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """HTTP 異常處理器"""
        logger.warning(
            "HTTP 異常: %s",
            exc.detail,
            extra={
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
            },
        )

        response_obj = ErrorResponse(
            success=False,
            error_code=exc.status_code,
            message=exc.detail,
            request_id=getattr(request.state, "request_id", None),
        )

        return JSONResponse(
            status_code=exc.status_code, content=response_obj.model_dump(mode="json")
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """請求驗證異常處理器"""
        validation_errors = []

        for error in exc.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            validation_errors.append(
                ValidationErrorDetail(
                    field=field_path, message=error["msg"], value=error.get("input")
                )
            )

        logger.warning(
            "請求驗證失敗: %d 個錯誤",
            len(validation_errors),
            extra={
                "path": request.url.path,
                "method": request.method,
                "errors": [err.dict() for err in validation_errors],
            },
        )

        response_obj = ValidationErrorResponse(
            success=False,
            error_code=422,
            message="請求參數驗證失敗",
            validation_errors=validation_errors,
            request_id=getattr(request.state, "request_id", None),
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=response_obj.model_dump(mode="json"),
        )

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_exception_handler(
        request: Request, exc: PydanticValidationError
    ):
        """Pydantic 驗證異常處理器"""
        validation_errors = []

        for error in exc.errors():
            field_path = " -> ".join(str(loc) for loc in error["loc"])
            validation_errors.append(
                ValidationErrorDetail(
                    field=field_path, message=error["msg"], value=error.get("input")
                )
            )

        logger.warning(
            "資料驗證失敗: %d 個錯誤",
            len(validation_errors),
            extra={
                "path": request.url.path,
                "method": request.method,
                "errors": [err.dict() for err in validation_errors],
            },
        )

        response_obj = ValidationErrorResponse(
            success=False,
            error_code=422,
            message="資料驗證失敗",
            validation_errors=validation_errors,
            request_id=getattr(request.state, "request_id", None),
        )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=response_obj.model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """通用異常處理器"""
        logger.error(
            "未處理的異常: %s",
            str(exc),
            exc_info=True,
            extra={
                "path": request.url.path,
                "method": request.method,
                "exception_type": type(exc).__name__,
            },
        )

        response_obj = ErrorResponse(
            success=False,
            error_code=500,
            message="內部服務器錯誤",
            request_id=getattr(request.state, "request_id", None),
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=response_obj.model_dump(mode="json"),
        )


class ExceptionLogger:
    """異常日誌記錄器"""

    @staticmethod
    def log_exception(
        exc: Exception,
        request: Request,
        user_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ):
        """記錄異常詳細資訊

        Args:
            exc: 異常對象
            request: 請求對象
            user_id: 用戶 ID
            additional_context: 額外上下文資訊
        """
        context = {
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "path": request.url.path,
            "method": request.method,
            "query_params": dict(request.query_params),
            "headers": dict(request.headers),
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
        }

        if additional_context:
            context.update(additional_context)

        logger.error("異常詳情: %s", context, exc_info=True)


class ErrorTracker:
    """錯誤追蹤器"""

    def __init__(self):
        self.error_counts = {}
        self.error_details = []

    def track_error(
        self,
        error_type: str,
        error_message: str,
        endpoint: str,
        user_id: Optional[str] = None,
    ):
        """追蹤錯誤

        Args:
            error_type: 錯誤類型
            error_message: 錯誤訊息
            endpoint: 端點
            user_id: 用戶 ID
        """
        error_key = f"{error_type}:{endpoint}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

        self.error_details.append(
            {
                "error_type": error_type,
                "error_message": error_message,
                "endpoint": endpoint,
                "user_id": user_id,
                "timestamp": datetime.now(),
                "count": self.error_counts[error_key],
            }
        )

        # 保持最近 1000 條錯誤記錄
        if len(self.error_details) > 1000:
            self.error_details = self.error_details[-1000:]

    def get_error_statistics(self) -> Dict[str, Any]:
        """獲取錯誤統計

        Returns:
            Dict[str, Any]: 錯誤統計資訊
        """
        total_errors = sum(self.error_counts.values())

        # 按錯誤類型統計
        error_type_counts = {}
        for error_detail in self.error_details:
            error_type = error_detail["error_type"]
            error_type_counts[error_type] = error_type_counts.get(error_type, 0) + 1

        # 按端點統計
        endpoint_counts = {}
        for error_detail in self.error_details:
            endpoint = error_detail["endpoint"]
            endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + 1

        return {
            "total_errors": total_errors,
            "error_type_counts": error_type_counts,
            "endpoint_counts": endpoint_counts,
            "recent_errors": self.error_details[-10:],  # 最近 10 個錯誤
            "top_error_endpoints": sorted(
                endpoint_counts.items(), key=lambda x: x[1], reverse=True
            )[
                :5
            ],  # 錯誤最多的 5 個端點
        }

    def clear_statistics(self):
        """清除統計資料"""
        self.error_counts.clear()
        self.error_details.clear()


# 全域錯誤追蹤器實例
error_tracker = ErrorTracker()


class RetryableError(APIException):
    """可重試錯誤"""

    def __init__(
        self,
        message: str = "操作失敗，請重試",
        retry_after: int = 60,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, 503, details)
        self.retry_after = retry_after


class MaintenanceError(APIException):
    """維護模式錯誤"""

    def __init__(
        self,
        message: str = "系統維護中，請稍後再試",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, 503, details)


def handle_database_error(func):
    """資料庫錯誤處理裝飾器"""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error("資料庫操作錯誤: %s", e)
            raise DatabaseError(f"資料庫操作失敗: {str(e)}") from e

    return wrapper


def handle_external_service_error(service_name: str):
    """外部服務錯誤處理裝飾器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error("%s 服務錯誤: %s", service_name, e)
                raise ExternalServiceError(f"{service_name} 服務不可用: {str(e)}") from e

        return wrapper

    return decorator
