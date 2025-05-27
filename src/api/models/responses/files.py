"""檔案相關響應模型

此模組定義了檔案操作相關的響應模型，包括檔案上傳響應、
匯出響應等。
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator


class FileUploadResponse(BaseModel):
    """檔案上傳響應

    檔案上傳操作的響應格式。

    Attributes:
        filename: 檔案名稱
        file_size: 檔案大小（位元組）
        file_type: 檔案 MIME 類型
        file_path: 檔案存儲路徑
        upload_time: 上傳時間
        checksum: 檔案校驗和

    Example:
        >>> response = FileUploadResponse(
        ...     filename="data.csv",
        ...     file_size=1024000,
        ...     file_type="text/csv",
        ...     file_path="/uploads/2024/12/data.csv",
        ...     checksum="md5:abc123def456"
        ... )
    """

    filename: str = Field(description="檔案名稱", example="data.csv")

    file_size: int = Field(description="檔案大小（位元組）", example=1024000, ge=0)

    file_type: str = Field(description="檔案類型", example="text/csv")

    file_path: str = Field(description="檔案路徑", example="/uploads/2024/12/data.csv")

    upload_time: datetime = Field(default_factory=datetime.now, description="上傳時間")

    checksum: Optional[str] = Field(
        default=None, description="檔案校驗和", example="md5:abc123def456"
    )

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        json_schema_extra={
            "example": {
                "filename": "data.csv",
                "file_size": 1024000,
                "file_type": "text/csv",
                "file_path": "/uploads/2024/12/data.csv",
                "upload_time": "2024-12-20T10:30:00Z",
                "checksum": "md5:abc123def456",
            }
        },
    )


class ExportResponse(BaseModel):
    """匯出響應

    資料匯出操作的響應格式。

    Attributes:
        export_id: 匯出任務 ID
        format: 匯出格式
        status: 匯出狀態
        download_url: 下載連結
        file_size: 檔案大小
        expires_at: 連結過期時間
        created_at: 創建時間

    Example:
        >>> response = ExportResponse(
        ...     export_id="export_123456",
        ...     format="csv",
        ...     status="completed",
        ...     download_url="/api/v1/exports/export_123456/download",
        ...     file_size=2048000
        ... )
    """

    export_id: str = Field(description="匯出任務 ID", example="export_123456")

    format: str = Field(description="匯出格式", example="csv")

    status: str = Field(description="匯出狀態", example="completed")

    download_url: Optional[str] = Field(
        default=None,
        description="下載連結",
        example="/api/v1/exports/export_123456/download",
    )

    file_size: Optional[int] = Field(
        default=None, description="檔案大小", example=2048000, ge=0
    )

    expires_at: Optional[datetime] = Field(
        default=None, description="連結過期時間", example="2024-12-21T10:30:00Z"
    )

    created_at: datetime = Field(default_factory=datetime.now, description="創建時間")

    @field_validator("format")
    @classmethod
    # pylint: disable=missing-type-doc
    def validate_format(cls, v: str) -> str:
        """驗證匯出格式

        Args:
            v: 匯出格式

        Returns:
            str: 驗證後的格式

        Raises:
            ValueError: 當格式不支援時
        """
        allowed_formats = ["csv", "xlsx", "json", "pdf"]
        if v.lower() not in allowed_formats:
            raise ValueError(f"不支援的匯出格式: {v}，支援的格式: {allowed_formats}")
        return v.lower()

    @field_validator("status")
    @classmethod
    # pylint: disable=missing-type-doc
    def validate_status(cls, v: str) -> str:
        """驗證匯出狀態

        Args:
            v: 匯出狀態

        Returns:
            str: 驗證後的狀態

        Raises:
            ValueError: 當狀態不正確時
        """
        allowed_statuses = ["pending", "processing", "completed", "failed", "expired"]
        if v.lower() not in allowed_statuses:
            raise ValueError(f"不正確的匯出狀態: {v}，允許的狀態: {allowed_statuses}")
        return v.lower()

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        json_schema_extra={
            "example": {
                "export_id": "export_123456",
                "format": "csv",
                "status": "completed",
                "download_url": "/api/v1/exports/export_123456/download",
                "file_size": 2048000,
                "expires_at": "2024-12-21T10:30:00Z",
                "created_at": "2024-12-20T10:30:00Z",
            }
        },
    )
