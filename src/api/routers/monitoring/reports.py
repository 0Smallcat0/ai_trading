"""監控報表 API

此模組實現監控報表相關的 API 端點，包括系統報表、效能分析等功能。
"""

import logging
from datetime import datetime
from typing import List, Optional, Any

from fastapi import APIRouter, HTTPException, Query, status, BackgroundTasks
from pydantic import BaseModel, Field

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.core.system_monitoring_service import SystemMonitoringService
from .models import SystemReportRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化系統監控服務
monitoring_service = SystemMonitoringService()


# ==================== 響應模型 ====================


class TradingPerformanceMetrics(BaseModel):
    """交易效能指標響應模型
    
    此模型定義了交易系統效能指標的詳細資訊。
    
    Attributes:
        timestamp: 時間戳
        api_latency_avg: API 平均延遲 (ms)
        api_latency_p95: API P95 延遲 (ms)
        api_latency_p99: API P99 延遲 (ms)
        trading_tps: 交易吞吐量 (TPS)
        order_success_rate: 訂單成功率 (%)
        execution_success_rate: 執行成功率 (%)
        error_rate: 錯誤率 (%)
        timeout_rate: 超時率 (%)
        active_connections: 活躍連接數
        queue_length: 佇列長度
        cache_hit_rate: 快取命中率 (%)
    """
    timestamp: datetime = Field(..., description="時間戳")
    api_latency_avg: float = Field(..., description="API 平均延遲 (ms)")
    api_latency_p95: float = Field(..., description="API P95 延遲 (ms)")
    api_latency_p99: float = Field(..., description="API P99 延遲 (ms)")
    trading_tps: float = Field(..., description="交易吞吐量 (TPS)")
    order_success_rate: float = Field(..., description="訂單成功率 (%)")
    execution_success_rate: float = Field(..., description="執行成功率 (%)")
    error_rate: float = Field(..., description="錯誤率 (%)")
    timeout_rate: float = Field(..., description="超時率 (%)")
    active_connections: int = Field(..., description="活躍連接數")
    queue_length: int = Field(..., description="佇列長度")
    cache_hit_rate: float = Field(..., description="快取命中率 (%)")


class SystemStatusReport(BaseModel):
    """系統狀態報告響應模型
    
    此模型定義了系統狀態報告的詳細資訊。
    
    Attributes:
        report_id: 報告 ID
        generated_at: 生成時間
        period_start: 統計期間開始
        period_end: 統計期間結束
        summary: 摘要信息字典
        resource_usage: 資源使用統計字典
        performance_metrics: 效能指標字典
        alert_statistics: 警報統計字典
        recommendations: 建議列表
    """
    report_id: str = Field(..., description="報告 ID")
    generated_at: datetime = Field(..., description="生成時間")
    period_start: datetime = Field(..., description="統計期間開始")
    period_end: datetime = Field(..., description="統計期間結束")
    summary: dict = Field(..., description="摘要信息")
    resource_usage: dict = Field(..., description="資源使用統計")
    performance_metrics: dict = Field(..., description="效能指標")
    alert_statistics: dict = Field(..., description="警報統計")
    recommendations: List[str] = Field(..., description="建議列表")


class ReportGenerationTask(BaseModel):
    """報表生成任務響應模型
    
    此模型定義了報表生成任務的資訊。
    
    Attributes:
        task_id: 任務 ID
        report_type: 報表類型
        status: 任務狀態
        created_at: 創建時間
        completed_at: 完成時間
        file_path: 報表檔案路徑
        file_size: 檔案大小
        report_format: 報表格式
        progress: 進度百分比
    """
    task_id: str = Field(..., description="任務 ID")
    report_type: str = Field(..., description="報表類型")
    status: str = Field(..., description="任務狀態")
    created_at: datetime = Field(..., description="創建時間")
    completed_at: Optional[datetime] = Field(default=None, description="完成時間")
    file_path: Optional[str] = Field(default=None, description="報表檔案路徑")
    file_size: Optional[int] = Field(default=None, description="檔案大小")
    report_format: str = Field(..., description="報表格式")
    progress: float = Field(default=0.0, description="進度百分比")


# ==================== API 端點 ====================


@router.get(
    "/performance",
    response_model=APIResponse[List[TradingPerformanceMetrics]],
    responses=COMMON_RESPONSES,
    summary="交易效能指標",
    description="獲取交易系統效能指標，包括 API 延遲、吞吐量、成功率等",
)
async def get_trading_performance(
    time_range: str = Query(default="1h", description="時間範圍 (1h/24h/7d)"),
    interval: str = Query(default="5m", description="數據間隔 (1m/5m/15m/1h)"),
):
    """獲取交易效能指標
    
    此端點用於獲取交易系統的效能指標，包括延遲、吞吐量等。
    
    Args:
        time_range: 時間範圍，支援 1h、24h、7d
        interval: 數據間隔，支援 1m、5m、15m、1h
        
    Returns:
        APIResponse[List[TradingPerformanceMetrics]]: 包含交易效能指標列表的 API 回應
        
    Raises:
        HTTPException: 當參數無效或獲取數據失敗時
        
    Example:
        GET /api/monitoring/reports/performance?time_range=24h&interval=15m
    """
    try:
        # 解析時間範圍
        time_ranges = {
            "1h": 3600,
            "24h": 86400,
            "7d": 604800
        }

        if time_range not in time_ranges:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"無效的時間範圍，支援: {', '.join(time_ranges.keys())}"
            )

        # 解析數據間隔
        intervals = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600
        }

        if interval not in intervals:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"無效的數據間隔，支援: {', '.join(intervals.keys())}"
            )

        # 計算查詢時間範圍
        end_time = datetime.now()
        start_time = datetime.fromtimestamp(end_time.timestamp() - time_ranges[time_range])

        # 獲取交易效能數據
        performance_data = monitoring_service.get_trading_performance_metrics(
            start_time=start_time,
            end_time=end_time,
            interval_seconds=intervals[interval]
        )

        # 轉換為響應模型
        metrics_list = []
        for data in performance_data:
            metrics = TradingPerformanceMetrics(
                timestamp=data["timestamp"],
                api_latency_avg=data["api_latency_avg"],
                api_latency_p95=data["api_latency_p95"],
                api_latency_p99=data["api_latency_p99"],
                trading_tps=data["trading_tps"],
                order_success_rate=data["order_success_rate"],
                execution_success_rate=data["execution_success_rate"],
                error_rate=data["error_rate"],
                timeout_rate=data["timeout_rate"],
                active_connections=data["active_connections"],
                queue_length=data["queue_length"],
                cache_hit_rate=data["cache_hit_rate"]
            )
            metrics_list.append(metrics)

        return APIResponse(
            success=True,
            message=f"獲取到 {len(metrics_list)} 個交易效能數據點",
            data=metrics_list
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取交易效能指標失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取交易效能指標失敗: {str(e)}"
        ) from e


@router.post(
    "/generate",
    response_model=APIResponse[ReportGenerationTask],
    responses=COMMON_RESPONSES,
    summary="生成系統報表",
    description="生成系統狀態報表",
)
async def generate_system_report(
    background_tasks: BackgroundTasks,
    request: SystemReportRequest
):
    """生成系統報表
    
    此端點用於生成系統狀態報表，支援多種報表類型和格式。
    
    Args:
        background_tasks: 背景任務
        request: 系統報表請求資料
        
    Returns:
        APIResponse[ReportGenerationTask]: 包含報表生成任務資訊的 API 回應
        
    Raises:
        HTTPException: 當報表生成失敗時
        
    Example:
        POST /api/monitoring/reports/generate
        {
            "report_type": "comprehensive",
            "period_start": "2024-01-01T00:00:00Z",
            "period_end": "2024-01-31T23:59:59Z",
            "report_format": "pdf"
        }
    """
    try:
        # 構建報表參數
        report_params = {
            "report_type": request.report_type,
            "period_start": request.period_start,
            "period_end": request.period_end,
            "include_details": request.include_details,
            "report_format": request.report_format
        }

        # 創建報表生成任務
        task_id = monitoring_service.create_report_generation_task(report_params)

        # 添加背景任務
        background_tasks.add_task(
            monitoring_service.execute_report_generation_task,
            task_id
        )

        # 獲取任務詳情
        task_details = monitoring_service.get_report_generation_task(task_id)

        # 轉換為響應模型
        generation_task = ReportGenerationTask(
            task_id=task_details["task_id"],
            report_type=task_details["report_type"],
            status=task_details["status"],
            created_at=task_details["created_at"],
            completed_at=task_details.get("completed_at"),
            file_path=task_details.get("file_path"),
            file_size=task_details.get("file_size"),
            report_format=task_details["report_format"],
            progress=task_details.get("progress", 0.0)
        )

        return APIResponse(
            success=True,
            message="報表生成任務已創建",
            data=generation_task
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("創建報表生成任務失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"創建報表生成任務失敗: {str(e)}"
        ) from e


@router.get(
    "/status",
    response_model=APIResponse[SystemStatusReport],
    responses=COMMON_RESPONSES,
    summary="系統狀態報告",
    description="獲取系統狀態的綜合報告",
)
async def get_system_status_report(
    period_hours: int = Query(default=24, ge=1, le=168, description="統計期間（小時）"),
    include_details: bool = Query(default=True, description="是否包含詳細資訊"),
):
    """獲取系統狀態報告
    
    此端點用於獲取系統狀態的綜合報告，包括資源使用、效能指標等。
    
    Args:
        period_hours: 統計期間（小時）
        include_details: 是否包含詳細資訊
        
    Returns:
        APIResponse[SystemStatusReport]: 包含系統狀態報告的 API 回應
        
    Raises:
        HTTPException: 當獲取報告失敗時
    """
    try:
        # 計算統計期間
        end_time = datetime.now()
        start_time = datetime.fromtimestamp(end_time.timestamp() - period_hours * 3600)

        # 獲取系統狀態報告
        report_data = monitoring_service.generate_system_status_report(
            period_start=start_time,
            period_end=end_time,
            include_details=include_details
        )

        # 轉換為響應模型
        status_report = SystemStatusReport(
            report_id=report_data["report_id"],
            generated_at=report_data["generated_at"],
            period_start=report_data["period_start"],
            period_end=report_data["period_end"],
            summary=report_data["summary"],
            resource_usage=report_data["resource_usage"],
            performance_metrics=report_data["performance_metrics"],
            alert_statistics=report_data["alert_statistics"],
            recommendations=report_data["recommendations"]
        )

        return APIResponse(
            success=True,
            message="系統狀態報告獲取成功",
            data=status_report
        )

    except Exception as e:
        logger.error("獲取系統狀態報告失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取系統狀態報告失敗: {str(e)}"
        ) from e


@router.get(
    "/tasks/{task_id}",
    response_model=APIResponse[ReportGenerationTask],
    responses=COMMON_RESPONSES,
    summary="查詢報表生成任務狀態",
    description="查詢報表生成任務的狀態和進度",
)
async def get_report_generation_task_status(task_id: str):
    """查詢報表生成任務狀態
    
    此端點用於查詢報表生成任務的狀態和進度。
    
    Args:
        task_id: 任務 ID
        
    Returns:
        APIResponse[ReportGenerationTask]: 包含報表生成任務狀態的 API 回應
        
    Raises:
        HTTPException: 當任務不存在或查詢失敗時
    """
    try:
        # 獲取任務詳情
        task_details = monitoring_service.get_report_generation_task(task_id)

        if not task_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"報表生成任務 {task_id} 不存在"
            )

        # 轉換為響應模型
        generation_task = ReportGenerationTask(
            task_id=task_details["task_id"],
            report_type=task_details["report_type"],
            status=task_details["status"],
            created_at=task_details["created_at"],
            completed_at=task_details.get("completed_at"),
            file_path=task_details.get("file_path"),
            file_size=task_details.get("file_size"),
            report_format=task_details["report_format"],
            progress=task_details.get("progress", 0.0)
        )

        return APIResponse(
            success=True,
            message="報表生成任務狀態獲取成功",
            data=generation_task
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("查詢報表生成任務狀態失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢報表生成任務狀態失敗: {str(e)}"
        ) from e


@router.get(
    "/history",
    response_model=APIResponse[List[ReportGenerationTask]],
    responses=COMMON_RESPONSES,
    summary="查詢報表歷史",
    description="查詢歷史報表生成記錄",
)
async def get_report_history(
    page: int = Query(default=1, ge=1, description="頁碼"),
    page_size: int = Query(default=20, ge=1, le=100, description="每頁數量"),
    report_type: Optional[str] = Query(default=None, description="報表類型篩選"),
    status: Optional[str] = Query(default=None, description="狀態篩選"),
):
    """查詢報表歷史
    
    此端點用於查詢歷史報表生成記錄。
    
    Args:
        page: 頁碼
        page_size: 每頁數量
        report_type: 報表類型篩選
        status: 狀態篩選
        
    Returns:
        APIResponse[List[ReportGenerationTask]]: 包含報表歷史記錄的 API 回應
        
    Raises:
        HTTPException: 當查詢失敗時
    """
    try:
        # 構建篩選條件
        filters = {}
        if report_type:
            filters["report_type"] = report_type
        if status:
            filters["status"] = status

        # 獲取報表歷史
        history_data = monitoring_service.get_report_generation_history(
            page=page, page_size=page_size, filters=filters
        )

        # 轉換為響應模型
        history_list = []
        for task_data in history_data.get("tasks", []):
            task = ReportGenerationTask(
                task_id=task_data["task_id"],
                report_type=task_data["report_type"],
                status=task_data["status"],
                created_at=task_data["created_at"],
                completed_at=task_data.get("completed_at"),
                file_path=task_data.get("file_path"),
                file_size=task_data.get("file_size"),
                report_format=task_data["report_format"],
                progress=task_data.get("progress", 0.0)
            )
            history_list.append(task)

        return APIResponse(
            success=True,
            message=f"獲取到 {len(history_list)} 個報表歷史記錄",
            data=history_list
        )

    except Exception as e:
        logger.error("查詢報表歷史失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢報表歷史失敗: {str(e)}"
        ) from e
