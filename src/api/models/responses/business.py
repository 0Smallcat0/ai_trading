"""業務響應模型

此模組定義了業務相關的響應模型，包括批量操作響應等。
"""

from typing import Any, Dict, List
from pydantic import BaseModel, Field, ConfigDict, field_validator


class BulkOperationResponse(BaseModel):
    """批量操作響應

    用於批量操作（如批量創建、更新、刪除）的響應格式。

    Attributes:
        total_items: 總項目數
        successful_items: 成功項目數
        failed_items: 失敗項目數
        success_rate: 成功率
        errors: 錯誤詳情列表
        execution_time: 執行時間（秒）

    Example:
        >>> response = BulkOperationResponse(
        ...     total_items=100,
        ...     successful_items=95,
        ...     failed_items=5,
        ...     success_rate=0.95,
        ...     errors=[{"item_id": "item_1", "error": "資料格式錯誤"}],
        ...     execution_time=2.5
        ... )
    """

    total_items: int = Field(description="總項目數", example=100, ge=0)

    successful_items: int = Field(description="成功項目數", example=95, ge=0)

    failed_items: int = Field(description="失敗項目數", example=5, ge=0)

    success_rate: float = Field(description="成功率", example=0.95, ge=0.0, le=1.0)

    errors: List[Dict[str, Any]] = Field(
        description="錯誤詳情列表",
        example=[
            {"item_id": "item_1", "error": "資料格式錯誤"},
            {"item_id": "item_2", "error": "重複資料"},
        ],
    )

    execution_time: float = Field(description="執行時間（秒）", example=2.5, ge=0.0)

    @field_validator("success_rate")
    @classmethod
    # pylint: disable=missing-type-doc
    def validate_success_rate(cls, v: float, info) -> float:
        """驗證成功率

        Args:
            v: 成功率值
            info: 驗證上下文

        Returns:
            float: 驗證後的成功率

        Raises:
            ValueError: 當成功率與項目數不一致時
        """
        if "total_items" in info.data and "successful_items" in info.data:
            total = info.data["total_items"]
            successful = info.data["successful_items"]
            if total > 0:
                expected_rate = successful / total
                if abs(v - expected_rate) > 0.001:  # 允許小數點誤差
                    raise ValueError(f"成功率應為 {expected_rate:.3f}，但得到 {v}")
        return v

    @field_validator("failed_items")
    @classmethod
    # pylint: disable=missing-type-doc
    def validate_failed_items(cls, v: int, info) -> int:
        """驗證失敗項目數

        Args:
            v: 失敗項目數
            info: 驗證上下文

        Returns:
            int: 驗證後的失敗項目數
        """
        if "total_items" in info.data and "successful_items" in info.data:
            total = info.data["total_items"]
            successful = info.data["successful_items"]
            expected_failed = total - successful
            if v != expected_failed:
                raise ValueError(f"失敗項目數應為 {expected_failed}，但得到 {v}")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_items": 100,
                "successful_items": 95,
                "failed_items": 5,
                "success_rate": 0.95,
                "errors": [
                    {"item_id": "item_1", "error": "資料格式錯誤"},
                    {"item_id": "item_2", "error": "重複資料"},
                ],
                "execution_time": 2.5,
            }
        }
    )
