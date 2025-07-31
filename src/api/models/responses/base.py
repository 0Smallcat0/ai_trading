"""基礎響應模型

此模組定義了 API 響應的基礎模型，包括標準響應格式、
響應狀態枚舉等核心組件。
"""

from datetime import datetime
from typing import Dict, Optional, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

# 泛型類型變數
T = TypeVar("T")


class ResponseStatus(str, Enum):
    """響應狀態枚舉

    定義 API 響應的標準狀態值，用於統一響應格式。
    """

    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class APIResponse(BaseModel, Generic[T]):
    """標準 API 響應格式

    所有 API 端點的標準響應格式，確保響應的一致性。
    支援泛型，可以指定 data 欄位的具體類型。

    Attributes:
        success: 請求是否成功
        message: 響應訊息
        data: 響應資料，支援泛型
        timestamp: 響應時間戳
        request_id: 請求 ID，用於追蹤和除錯

    Example:
        >>> response = APIResponse[dict](
        ...     success=True,
        ...     message="操作成功",
        ...     data={"user_id": 123}
        ... )
    """

    success: bool = Field(description="請求是否成功", example=True)

    message: str = Field(description="響應訊息", example="操作成功")

    data: Optional[T] = Field(default=None, description="響應資料")

    timestamp: datetime = Field(default_factory=datetime.now, description="響應時間戳")

    request_id: Optional[str] = Field(default=None, description="請求 ID，用於追蹤")

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "success": True,
                "message": "操作成功",
                "data": {},
                "timestamp": "2024-12-20T10:30:00Z",
                "request_id": "req_123456789",
            }
        },
    )


class HealthCheckResponse(BaseModel):
    """健康檢查響應

    系統健康檢查的標準響應格式，包含各個服務組件的狀態。

    Attributes:
        status: 整體服務狀態
        version: 服務版本
        timestamp: 檢查時間
        services: 各服務狀態字典
        uptime: 系統運行時間

    Example:
        >>> health = HealthCheckResponse(
        ...     status="healthy",
        ...     version="1.0.0",
        ...     services={"database": "healthy", "cache": "healthy"}
        ... )
    """

    status: str = Field(description="服務狀態", example="healthy")

    version: str = Field(description="服務版本", example="1.0.0")

    timestamp: datetime = Field(default_factory=datetime.now, description="檢查時間")

    services: Dict[str, str] = Field(
        description="各服務狀態",
        example={"database": "healthy", "cache": "healthy", "trading_api": "healthy"},
    )

    uptime: Optional[str] = Field(
        default=None, description="運行時間", example="2 days, 3 hours, 45 minutes"
    )

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        json_schema_extra={
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-12-20T10:30:00Z",
                "services": {
                    "database": "healthy",
                    "cache": "healthy",
                    "trading_api": "healthy",
                },
                "uptime": "2 days, 3 hours, 45 minutes",
            }
        },
    )


class MetricsResponse(BaseModel):
    """指標響應

    系統監控指標的響應格式，用於性能監控和告警。

    Attributes:
        metric_name: 指標名稱
        value: 指標值
        unit: 指標單位
        timestamp: 指標時間戳
        labels: 指標標籤

    Example:
        >>> metrics = MetricsResponse(
        ...     metric_name="api_requests_total",
        ...     value=12345,
        ...     unit="requests",
        ...     labels={"method": "GET", "endpoint": "/api/v1/users"}
        ... )
    """

    metric_name: str = Field(description="指標名稱", example="api_requests_total")

    value: float = Field(description="指標值", example=12345.0)

    unit: Optional[str] = Field(default=None, description="單位", example="requests")

    timestamp: datetime = Field(default_factory=datetime.now, description="指標時間戳")

    labels: Optional[Dict[str, str]] = Field(
        default=None,
        description="指標標籤",
        example={"method": "GET", "endpoint": "/api/v1/users"},
    )

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        json_schema_extra={
            "example": {
                "metric_name": "api_requests_total",
                "value": 12345.0,
                "unit": "requests",
                "timestamp": "2024-12-20T10:30:00Z",
                "labels": {"method": "GET", "endpoint": "/api/v1/users"},
            }
        },
    )


class OperationResult(BaseModel):
    """操作結果

    通用操作結果的響應格式，適用於 CRUD 操作等。

    Attributes:
        operation: 操作類型
        success: 操作是否成功
        affected_count: 影響的記錄數
        resource_id: 資源 ID
        message: 操作結果訊息

    Example:
        >>> result = OperationResult(
        ...     operation="create_user",
        ...     success=True,
        ...     affected_count=1,
        ...     resource_id="user_123",
        ...     message="用戶創建成功"
        ... )
    """

    operation: str = Field(description="操作類型", example="create_user")

    success: bool = Field(description="操作是否成功", example=True)

    affected_count: Optional[int] = Field(
        default=None, description="影響的記錄數", example=1
    )

    resource_id: Optional[str] = Field(
        default=None, description="資源 ID", example="user_123"
    )

    message: str = Field(description="操作結果訊息", example="用戶創建成功")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "operation": "create_user",
                "success": True,
                "affected_count": 1,
                "resource_id": "user_123",
                "message": "用戶創建成功",
            }
        }
    )
