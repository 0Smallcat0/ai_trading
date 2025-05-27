"""分頁響應模型

此模組定義了分頁相關的響應模型，包括分頁元資訊、
分頁響應格式等。
"""

from datetime import datetime
from typing import List, Generic, TypeVar
from pydantic import BaseModel, Field, ConfigDict, field_validator

# 泛型類型變數
T = TypeVar("T")


class PaginationMeta(BaseModel):
    """分頁元資訊

    包含分頁查詢的元資訊，如當前頁碼、總頁數等。

    Attributes:
        page: 當前頁碼（從 1 開始）
        page_size: 每頁項目數
        total_items: 總項目數
        total_pages: 總頁數
        has_next: 是否有下一頁
        has_prev: 是否有上一頁

    Example:
        >>> meta = PaginationMeta(
        ...     page=1,
        ...     page_size=20,
        ...     total_items=150,
        ...     total_pages=8,
        ...     has_next=True,
        ...     has_prev=False
        ... )
    """

    page: int = Field(
        description="當前頁碼",
        example=1,
        ge=1
    )

    page_size: int = Field(
        description="每頁項目數",
        example=20,
        ge=1,
        le=100
    )

    total_items: int = Field(
        description="總項目數",
        example=150,
        ge=0
    )

    total_pages: int = Field(
        description="總頁數",
        example=8,
        ge=0
    )

    has_next: bool = Field(
        description="是否有下一頁",
        example=True
    )

    has_prev: bool = Field(
        description="是否有上一頁",
        example=False
    )

    @field_validator('total_pages')
    @classmethod
    # pylint: disable=missing-type-doc
    def validate_total_pages(cls, v: int, info) -> int:
        """驗證總頁數

        Args:
            v: 總頁數值
            info: 驗證上下文

        Returns:
            int: 驗證後的總頁數

        Raises:
            ValueError: 當總頁數與其他欄位不一致時
        """
        if 'page_size' in info.data and 'total_items' in info.data:
            page_size = info.data['page_size']
            total_items = info.data['total_items']
            expected_pages = (
                (total_items + page_size - 1) // page_size
                if page_size > 0 else 0
            )
            if v != expected_pages:
                raise ValueError(f"總頁數應為 {expected_pages}，但得到 {v}")
        return v

    @field_validator('has_next')
    @classmethod
    # pylint: disable=missing-type-doc
    def validate_has_next(cls, v: bool, info) -> bool:
        """驗證是否有下一頁

        Args:
            v: 是否有下一頁的值
            info: 驗證上下文

        Returns:
            bool: 驗證後的值
        """
        if 'page' in info.data and 'total_pages' in info.data:
            page = info.data['page']
            total_pages = info.data['total_pages']
            expected_has_next = page < total_pages
            if v != expected_has_next:
                raise ValueError(f"has_next 應為 {expected_has_next}")
        return v

    @field_validator('has_prev')
    @classmethod
    # pylint: disable=missing-type-doc
    def validate_has_prev(cls, v: bool, info) -> bool:
        """驗證是否有上一頁

        Args:
            v: 是否有上一頁的值
            info: 驗證上下文

        Returns:
            bool: 驗證後的值
        """
        if 'page' in info.data:
            page = info.data['page']
            expected_has_prev = page > 1
            if v != expected_has_prev:
                raise ValueError(f"has_prev 應為 {expected_has_prev}")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "page": 1,
                "page_size": 20,
                "total_items": 150,
                "total_pages": 8,
                "has_next": True,
                "has_prev": False
            }
        }
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """分頁響應格式

    用於返回分頁查詢結果的標準格式。

    Attributes:
        success: 請求是否成功
        message: 響應訊息
        data: 分頁資料列表
        pagination: 分頁資訊
        timestamp: 響應時間戳

    Example:
        >>> response = PaginatedResponse[dict](
        ...     success=True,
        ...     message="資料獲取成功",
        ...     data=[{"id": 1, "name": "item1"}],
        ...     pagination=PaginationMeta(
        ...         page=1, page_size=20, total_items=150,
        ...         total_pages=8, has_next=True, has_prev=False
        ...     )
        ... )
    """

    success: bool = Field(
        default=True,
        description="請求是否成功"
    )

    message: str = Field(
        description="響應訊息",
        example="資料獲取成功"
    )

    data: List[T] = Field(
        description="分頁資料列表"
    )

    pagination: PaginationMeta = Field(
        description="分頁資訊"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="響應時間戳"
    )

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()},
        json_schema_extra={
            "example": {
                "success": True,
                "message": "資料獲取成功",
                "data": [
                    {"id": 1, "name": "item1"},
                    {"id": 2, "name": "item2"}
                ],
                "pagination": {
                    "page": 1,
                    "page_size": 20,
                    "total_items": 150,
                    "total_pages": 8,
                    "has_next": True,
                    "has_prev": False
                },
                "timestamp": "2024-12-20T10:30:00Z"
            }
        }
    )


def create_pagination_meta(
    page: int,
    page_size: int,
    total_items: int
) -> PaginationMeta:
    """創建分頁元資訊

    根據分頁參數計算並創建分頁元資訊。

    Args:
        page: 當前頁碼
        page_size: 每頁大小
        total_items: 總項目數

    Returns:
        PaginationMeta: 分頁元資訊

    Example:
        >>> meta = create_pagination_meta(1, 20, 150)
        >>> assert meta.total_pages == 8
        >>> assert meta.has_next is True
        >>> assert meta.has_prev is False
    """
    total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0
    has_next = page < total_pages
    has_prev = page > 1

    return PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev
    )
