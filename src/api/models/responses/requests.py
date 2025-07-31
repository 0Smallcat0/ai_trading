"""請求模型

此模組定義了請求相關的模型，包括分頁請求參數等。
"""

from pydantic import BaseModel, Field, ConfigDict, field_validator


class PaginationRequest(BaseModel):
    """分頁請求參數

    用於接收分頁查詢的請求參數。

    Attributes:
        page: 頁碼
        page_size: 每頁大小
        sort_by: 排序欄位
        sort_order: 排序順序

    Example:
        >>> request = PaginationRequest(
        ...     page=1,
        ...     page_size=20,
        ...     sort_by="created_at",
        ...     sort_order="desc"
        ... )
    """

    page: int = Field(default=1, description="頁碼", example=1, ge=1)

    page_size: int = Field(default=20, description="每頁大小", example=20, ge=1, le=100)

    sort_by: str = Field(default="id", description="排序欄位", example="created_at")

    sort_order: str = Field(default="asc", description="排序順序", example="desc")

    @field_validator("sort_order")
    @classmethod
    # pylint: disable=missing-type-doc
    def validate_sort_order(cls, v: str) -> str:
        """驗證排序順序

        Args:
            v: 排序順序值

        Returns:
            str: 驗證後的排序順序

        Raises:
            ValueError: 當排序順序不是 'asc' 或 'desc' 時
        """
        if v.lower() not in ["asc", "desc"]:
            raise ValueError("排序順序必須是 'asc' 或 'desc'")
        return v.lower()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "page_size": 20,
                "sort_by": "created_at",
                "sort_order": "desc",
            }
        }
    )
