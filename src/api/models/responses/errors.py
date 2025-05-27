"""錯誤響應模型

此模組定義了各種錯誤響應的模型，包括通用錯誤響應、
驗證錯誤響應等。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ErrorResponse(BaseModel):
    """錯誤響應格式

    標準的錯誤響應格式，用於所有 API 錯誤情況。

    Attributes:
        success: 請求是否成功（錯誤時為 False）
        error_code: HTTP 錯誤代碼
        message: 錯誤訊息
        details: 錯誤詳細資訊
        timestamp: 錯誤發生時間
        request_id: 請求 ID

    Example:
        >>> error = ErrorResponse(
        ...     error_code=400,
        ...     message="請求參數錯誤",
        ...     details={"field": "email", "error": "格式不正確"}
        ... )
    """

    success: bool = Field(default=False, description="請求是否成功")

    error_code: int = Field(description="錯誤代碼", example=400)

    message: str = Field(description="錯誤訊息", example="請求參數錯誤")

    details: Optional[Dict[str, Any]] = Field(default=None, description="錯誤詳細資訊")

    timestamp: datetime = Field(
        default_factory=datetime.now, description="錯誤發生時間"
    )

    request_id: Optional[str] = Field(default=None, description="請求 ID")

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        json_schema_extra={
            "example": {
                "success": False,
                "error_code": 400,
                "message": "請求參數錯誤",
                "details": {"field": "email", "error": "格式不正確"},
                "timestamp": "2024-12-20T10:30:00Z",
                "request_id": "req_123456789",
            }
        },
    )


class ValidationErrorDetail(BaseModel):
    """驗證錯誤詳情

    單個欄位的驗證錯誤詳細資訊。

    Attributes:
        field: 錯誤欄位名稱
        message: 錯誤訊息
        value: 導致錯誤的值

    Example:
        >>> detail = ValidationErrorDetail(
        ...     field="email",
        ...     message="郵箱格式不正確",
        ...     value="invalid-email"
        ... )
    """

    field: str = Field(description="錯誤欄位", example="email")

    message: str = Field(description="錯誤訊息", example="郵箱格式不正確")

    value: Optional[Any] = Field(
        default=None, description="錯誤值", example="invalid-email"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "field": "email",
                "message": "郵箱格式不正確",
                "value": "invalid-email",
            }
        }
    )


class ValidationErrorResponse(ErrorResponse):
    """驗證錯誤響應

    當請求參數驗證失敗時使用的響應格式。

    Attributes:
        error_code: 錯誤代碼（固定為 422）
        message: 錯誤訊息
        validation_errors: 驗證錯誤詳情列表

    Example:
        >>> response = ValidationErrorResponse(
        ...     message="請求參數驗證失敗",
        ...     validation_errors=[
        ...         ValidationErrorDetail(
        ...             field="email",
        ...             message="郵箱格式不正確",
        ...             value="invalid-email"
        ...         )
        ...     ]
        ... )
    """

    error_code: int = Field(default=422, description="錯誤代碼")

    message: str = Field(default="請求參數驗證失敗", description="錯誤訊息")

    validation_errors: List[ValidationErrorDetail] = Field(
        description="驗證錯誤詳情列表"
    )

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        json_schema_extra={
            "example": {
                "success": False,
                "error_code": 422,
                "message": "請求參數驗證失敗",
                "validation_errors": [
                    {
                        "field": "email",
                        "message": "郵箱格式不正確",
                        "value": "invalid-email",
                    },
                    {"field": "password", "message": "密碼長度不足", "value": "123"},
                ],
                "timestamp": "2024-12-20T10:30:00Z",
                "request_id": "req_123456789",
            }
        },
    )


# 常用錯誤響應範例
COMMON_ERROR_RESPONSES = {
    400: {
        "description": "請求錯誤",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "error_code": 400,
                    "message": "請求參數錯誤",
                    "timestamp": "2024-12-20T10:30:00Z",
                }
            }
        },
    },
    401: {
        "description": "未授權",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "error_code": 401,
                    "message": "未授權訪問",
                    "timestamp": "2024-12-20T10:30:00Z",
                }
            }
        },
    },
    403: {
        "description": "禁止訪問",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "error_code": 403,
                    "message": "權限不足",
                    "timestamp": "2024-12-20T10:30:00Z",
                }
            }
        },
    },
    404: {
        "description": "資源不存在",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "error_code": 404,
                    "message": "資源不存在",
                    "timestamp": "2024-12-20T10:30:00Z",
                }
            }
        },
    },
    422: {
        "description": "驗證錯誤",
        "model": ValidationErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "error_code": 422,
                    "message": "請求參數驗證失敗",
                    "validation_errors": [
                        {
                            "field": "email",
                            "message": "郵箱格式不正確",
                            "value": "invalid-email",
                        }
                    ],
                    "timestamp": "2024-12-20T10:30:00Z",
                }
            }
        },
    },
    500: {
        "description": "內部服務器錯誤",
        "model": ErrorResponse,
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "error_code": 500,
                    "message": "內部服務器錯誤",
                    "timestamp": "2024-12-20T10:30:00Z",
                }
            }
        },
    },
}
