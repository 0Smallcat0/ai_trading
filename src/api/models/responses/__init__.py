"""API 響應模型包

此包包含了所有 API 響應的標準格式，確保 API 回應的一致性和可預測性。
包含成功響應、錯誤響應、分頁響應等標準格式。

模組結構：
- base: 基礎響應模型
- pagination: 分頁相關模型
- errors: 錯誤響應模型
- business: 業務響應模型
"""

# 基礎響應模型
from .base import (
    ResponseStatus,
    APIResponse,
    HealthCheckResponse,
    MetricsResponse,
    OperationResult,
)

# 分頁響應模型
from .pagination import (
    PaginationMeta,
    PaginatedResponse,
    create_pagination_meta,
)

# 請求模型
from .requests import (
    PaginationRequest,
)

# 錯誤響應模型
from .errors import (
    ErrorResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
    COMMON_ERROR_RESPONSES,
)

# 業務響應模型
from .business import (
    BulkOperationResponse,
)

# 檔案響應模型
from .files import (
    FileUploadResponse,
    ExportResponse,
)

# 常用響應範例（合併所有響應範例）
COMMON_RESPONSES = {
    200: {
        "description": "成功",
        "model": APIResponse,
        "content": {
            "application/json": {
                "example": {
                    "success": True,
                    "message": "操作成功",
                    "data": {},
                    "timestamp": "2024-12-20T10:30:00Z",
                }
            }
        },
    },
    **COMMON_ERROR_RESPONSES,
}

# 導出所有模型
__all__ = [
    # 基礎響應模型
    "ResponseStatus",
    "APIResponse",
    "HealthCheckResponse",
    "MetricsResponse",
    "OperationResult",
    # 分頁響應模型
    "PaginationMeta",
    "PaginatedResponse",
    "create_pagination_meta",
    # 請求模型
    "PaginationRequest",
    # 錯誤響應模型
    "ErrorResponse",
    "ValidationErrorDetail",
    "ValidationErrorResponse",
    "COMMON_ERROR_RESPONSES",
    # 業務響應模型
    "BulkOperationResponse",
    # 檔案響應模型
    "FileUploadResponse",
    "ExportResponse",
    # 響應範例
    "COMMON_RESPONSES",
]
