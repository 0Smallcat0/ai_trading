"""日誌查詢 API

此模組實現日誌查詢相關的 API 端點，包括日誌搜尋、篩選、匯出等功能。
"""

import logging
from datetime import datetime
from typing import List, Optional, Any

from fastapi import APIRouter, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel, Field

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.core.system_monitoring_service import SystemMonitoringService
from .models import LogQueryRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化系統監控服務
monitoring_service = SystemMonitoringService()


# ==================== 響應模型 ====================


class LogEntry(BaseModel):
    """日誌條目響應模型

    此模型定義了日誌條目的詳細資訊。

    Attributes:
        id: 日誌 ID
        timestamp: 時間戳
        level: 日誌級別
        module: 模組名稱
        message: 日誌訊息
        details: 詳細信息字典
        user_id: 用戶 ID
        session_id: 會話 ID
        request_id: 請求 ID
    """

    id: str = Field(..., description="日誌 ID")
    timestamp: datetime = Field(..., description="時間戳")
    level: str = Field(..., description="日誌級別")
    module: str = Field(..., description="模組名稱")
    message: str = Field(..., description="日誌訊息")
    details: Optional[dict] = Field(default=None, description="詳細信息")
    user_id: Optional[str] = Field(default=None, description="用戶 ID")
    session_id: Optional[str] = Field(default=None, description="會話 ID")
    request_id: Optional[str] = Field(default=None, description="請求 ID")


class LogStatistics(BaseModel):
    """日誌統計響應模型

    此模型定義了日誌統計的詳細資訊。

    Attributes:
        total_logs: 總日誌數量
        level_distribution: 日誌級別分佈
        module_distribution: 模組分佈
        time_range_start: 統計時間範圍開始
        time_range_end: 統計時間範圍結束
        error_rate: 錯誤率
        warning_rate: 警告率
    """

    total_logs: int = Field(..., description="總日誌數量")
    level_distribution: dict = Field(..., description="日誌級別分佈")
    module_distribution: dict = Field(..., description="模組分佈")
    time_range_start: datetime = Field(..., description="統計時間範圍開始")
    time_range_end: datetime = Field(..., description="統計時間範圍結束")
    error_rate: float = Field(..., description="錯誤率")
    warning_rate: float = Field(..., description="警告率")


class LogExportTask(BaseModel):
    """日誌匯出任務響應模型

    此模型定義了日誌匯出任務的資訊。

    Attributes:
        task_id: 任務 ID
        status: 任務狀態
        created_at: 創建時間
        completed_at: 完成時間
        file_path: 匯出檔案路徑
        file_size: 檔案大小
        record_count: 記錄數量
        export_format: 匯出格式
    """

    task_id: str = Field(..., description="任務 ID")
    status: str = Field(..., description="任務狀態")
    created_at: datetime = Field(..., description="創建時間")
    completed_at: Optional[datetime] = Field(default=None, description="完成時間")
    file_path: Optional[str] = Field(default=None, description="匯出檔案路徑")
    file_size: Optional[int] = Field(default=None, description="檔案大小")
    record_count: Optional[int] = Field(default=None, description="記錄數量")
    export_format: str = Field(..., description="匯出格式")


# ==================== API 端點 ====================


@router.get(
    "/",
    response_model=APIResponse[List[LogEntry]],
    responses=COMMON_RESPONSES,
    summary="日誌查詢和管理",
    description="查詢系統日誌，支援分頁、級別篩選、關鍵字搜尋等",
)
async def get_logs(
    page: int = Query(default=1, ge=1, description="頁碼"),
    page_size: int = Query(default=50, ge=1, le=1000, description="每頁數量"),
    log_level: Optional[str] = Query(default=None, description="日誌級別篩選"),
    module: Optional[str] = Query(default=None, description="模組名稱篩選"),
    keyword: Optional[str] = Query(default=None, description="關鍵字搜尋"),
    start_time: Optional[str] = Query(default=None, description="開始時間 (ISO 8601)"),
    end_time: Optional[str] = Query(default=None, description="結束時間 (ISO 8601)"),
):
    """查詢系統日誌

    此端點用於查詢系統日誌，支援多種篩選條件和分頁。

    Args:
        page: 頁碼
        page_size: 每頁數量
        log_level: 日誌級別篩選
        module: 模組名稱篩選
        keyword: 關鍵字搜尋
        start_time: 開始時間
        end_time: 結束時間

    Returns:
        APIResponse[List[LogEntry]]: 包含日誌條目列表的 API 回應

    Raises:
        HTTPException: 當查詢失敗時

    Example:
        GET /api/monitoring/logs?log_level=ERROR&module=trading&keyword=timeout
    """
    try:
        # 解析時間參數
        parsed_start_time = None
        parsed_end_time = None

        if start_time:
            try:
                parsed_start_time = datetime.fromisoformat(
                    start_time.replace("Z", "+00:00")
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="開始時間格式錯誤，請使用 ISO 8601 格式",
                ) from e

        if end_time:
            try:
                parsed_end_time = datetime.fromisoformat(
                    end_time.replace("Z", "+00:00")
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="結束時間格式錯誤，請使用 ISO 8601 格式",
                ) from e

        # 驗證時間範圍
        if (
            parsed_start_time
            and parsed_end_time
            and parsed_end_time <= parsed_start_time
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="結束時間必須大於開始時間",
            )

        # 驗證日誌級別
        if log_level:
            allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if log_level.upper() not in allowed_levels:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"無效的日誌級別，支援: {', '.join(allowed_levels)}",
                )
            log_level = log_level.upper()

        # 構建查詢條件
        query_params = {
            "page": page,
            "page_size": page_size,
            "log_level": log_level,
            "module": module,
            "keyword": keyword,
            "start_time": parsed_start_time,
            "end_time": parsed_end_time,
        }

        # 查詢日誌
        logs_data = monitoring_service.query_logs(**query_params)

        # 轉換為響應模型
        log_entries = []
        for log_data in logs_data.get("logs", []):
            log_entry = LogEntry(
                id=log_data["id"],
                timestamp=log_data["timestamp"],
                level=log_data["level"],
                module=log_data["module"],
                message=log_data["message"],
                details=log_data.get("details"),
                user_id=log_data.get("user_id"),
                session_id=log_data.get("session_id"),
                request_id=log_data.get("request_id"),
            )
            log_entries.append(log_entry)

        return APIResponse(
            success=True,
            message=f"獲取到 {len(log_entries)} 條日誌記錄",
            data=log_entries,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("查詢日誌失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢日誌失敗: {str(e)}",
        ) from e


@router.get(
    "/statistics",
    response_model=APIResponse[LogStatistics],
    responses=COMMON_RESPONSES,
    summary="日誌統計",
    description="獲取日誌統計信息",
)
async def get_log_statistics(
    start_time: Optional[str] = Query(default=None, description="開始時間 (ISO 8601)"),
    end_time: Optional[str] = Query(default=None, description="結束時間 (ISO 8601)"),
):
    """獲取日誌統計

    此端點用於獲取指定時間範圍內的日誌統計信息。

    Args:
        start_time: 開始時間
        end_time: 結束時間

    Returns:
        APIResponse[LogStatistics]: 包含日誌統計的 API 回應

    Raises:
        HTTPException: 當獲取統計失敗時
    """
    try:
        # 解析時間參數
        parsed_start_time = None
        parsed_end_time = None

        if start_time:
            try:
                parsed_start_time = datetime.fromisoformat(
                    start_time.replace("Z", "+00:00")
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="開始時間格式錯誤，請使用 ISO 8601 格式",
                ) from e

        if end_time:
            try:
                parsed_end_time = datetime.fromisoformat(
                    end_time.replace("Z", "+00:00")
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="結束時間格式錯誤，請使用 ISO 8601 格式",
                ) from e

        # 獲取日誌統計
        stats_data = monitoring_service.get_log_statistics(
            start_time=parsed_start_time, end_time=parsed_end_time
        )

        # 轉換為響應模型
        statistics = LogStatistics(
            total_logs=stats_data["total_logs"],
            level_distribution=stats_data["level_distribution"],
            module_distribution=stats_data["module_distribution"],
            time_range_start=stats_data["time_range_start"],
            time_range_end=stats_data["time_range_end"],
            error_rate=stats_data["error_rate"],
            warning_rate=stats_data["warning_rate"],
        )

        return APIResponse(success=True, message="日誌統計獲取成功", data=statistics)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取日誌統計失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取日誌統計失敗: {str(e)}",
        ) from e


@router.post(
    "/export",
    response_model=APIResponse[LogExportTask],
    responses=COMMON_RESPONSES,
    summary="匯出日誌",
    description="匯出日誌到檔案",
)
async def export_logs(
    background_tasks: BackgroundTasks,
    log_level: Optional[str] = Query(default=None, description="日誌級別篩選"),
    module: Optional[str] = Query(default=None, description="模組名稱篩選"),
    keyword: Optional[str] = Query(default=None, description="關鍵字搜尋"),
    start_time: Optional[str] = Query(default=None, description="開始時間 (ISO 8601)"),
    end_time: Optional[str] = Query(default=None, description="結束時間 (ISO 8601)"),
    export_format: str = Query(default="csv", description="匯出格式 (csv/json/excel)"),
):
    """匯出日誌

    此端點用於匯出符合條件的日誌到檔案，支援多種格式。

    Args:
        background_tasks: 背景任務
        log_level: 日誌級別篩選
        module: 模組名稱篩選
        keyword: 關鍵字搜尋
        start_time: 開始時間
        end_time: 結束時間
        export_format: 匯出格式

    Returns:
        APIResponse[LogExportTask]: 包含匯出任務資訊的 API 回應

    Raises:
        HTTPException: 當匯出失敗時
    """
    try:
        # 驗證匯出格式
        allowed_formats = ["csv", "json", "excel"]
        if export_format.lower() not in allowed_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"無效的匯出格式，支援: {', '.join(allowed_formats)}",
            )

        # 解析時間參數
        parsed_start_time = None
        parsed_end_time = None

        if start_time:
            try:
                parsed_start_time = datetime.fromisoformat(
                    start_time.replace("Z", "+00:00")
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="開始時間格式錯誤，請使用 ISO 8601 格式",
                ) from e

        if end_time:
            try:
                parsed_end_time = datetime.fromisoformat(
                    end_time.replace("Z", "+00:00")
                )
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="結束時間格式錯誤，請使用 ISO 8601 格式",
                ) from e

        # 構建匯出參數
        export_params = {
            "log_level": log_level,
            "module": module,
            "keyword": keyword,
            "start_time": parsed_start_time,
            "end_time": parsed_end_time,
            "export_format": export_format.lower(),
        }

        # 創建匯出任務
        task_id = monitoring_service.create_log_export_task(export_params)

        # 添加背景任務
        background_tasks.add_task(monitoring_service.execute_log_export_task, task_id)

        # 獲取任務詳情
        task_details = monitoring_service.get_log_export_task(task_id)

        # 轉換為響應模型
        export_task = LogExportTask(
            task_id=task_details["task_id"],
            status=task_details["status"],
            created_at=task_details["created_at"],
            completed_at=task_details.get("completed_at"),
            file_path=task_details.get("file_path"),
            file_size=task_details.get("file_size"),
            record_count=task_details.get("record_count"),
            export_format=task_details["export_format"],
        )

        return APIResponse(success=True, message="日誌匯出任務已創建", data=export_task)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("創建日誌匯出任務失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"創建日誌匯出任務失敗: {str(e)}",
        ) from e


@router.get(
    "/export/{task_id}",
    response_model=APIResponse[LogExportTask],
    responses=COMMON_RESPONSES,
    summary="查詢匯出任務狀態",
    description="查詢日誌匯出任務的狀態",
)
async def get_export_task_status(task_id: str):
    """查詢匯出任務狀態

    此端點用於查詢日誌匯出任務的狀態和進度。

    Args:
        task_id: 任務 ID

    Returns:
        APIResponse[LogExportTask]: 包含匯出任務狀態的 API 回應

    Raises:
        HTTPException: 當任務不存在或查詢失敗時
    """
    try:
        # 獲取任務詳情
        task_details = monitoring_service.get_log_export_task(task_id)

        if not task_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"匯出任務 {task_id} 不存在",
            )

        # 轉換為響應模型
        export_task = LogExportTask(
            task_id=task_details["task_id"],
            status=task_details["status"],
            created_at=task_details["created_at"],
            completed_at=task_details.get("completed_at"),
            file_path=task_details.get("file_path"),
            file_size=task_details.get("file_size"),
            record_count=task_details.get("record_count"),
            export_format=task_details["export_format"],
        )

        return APIResponse(
            success=True, message="匯出任務狀態獲取成功", data=export_task
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("查詢匯出任務狀態失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢匯出任務狀態失敗: {str(e)}",
        ) from e
