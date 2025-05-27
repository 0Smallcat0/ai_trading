"""系統資源監控 API

此模組實現系統資源監控相關的 API 端點，包括 CPU、記憶體、磁碟、網路等指標監控。
"""

import logging
from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.core.system_monitoring_service import SystemMonitoringService

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化系統監控服務
monitoring_service = SystemMonitoringService()


# ==================== 響應模型 ====================


class SystemResourceMetrics(BaseModel):
    """系統資源指標響應模型

    此模型定義了系統資源監控的詳細指標。

    Attributes:
        timestamp: 時間戳
        cpu_usage: CPU 使用率 (%)
        memory_usage: 記憶體使用率 (%)
        memory_total: 總記憶體 (bytes)
        memory_available: 可用記憶體 (bytes)
        disk_usage: 磁碟使用率 (%)
        disk_total: 總磁碟空間 (bytes)
        disk_free: 可用磁碟空間 (bytes)
        network_io_sent: 網路發送 (bytes)
        network_io_recv: 網路接收 (bytes)
        load_average: 系統負載平均值
        process_count: 進程數量
    """

    timestamp: datetime = Field(..., description="時間戳")
    cpu_usage: float = Field(..., description="CPU 使用率 (%)")
    memory_usage: float = Field(..., description="記憶體使用率 (%)")
    memory_total: int = Field(..., description="總記憶體 (bytes)")
    memory_available: int = Field(..., description="可用記憶體 (bytes)")
    disk_usage: float = Field(..., description="磁碟使用率 (%)")
    disk_total: int = Field(..., description="總磁碟空間 (bytes)")
    disk_free: int = Field(..., description="可用磁碟空間 (bytes)")
    network_io_sent: int = Field(..., description="網路發送 (bytes)")
    network_io_recv: int = Field(..., description="網路接收 (bytes)")
    load_average: List[float] = Field(..., description="系統負載平均值")
    process_count: int = Field(..., description="進程數量")


class TradingPerformanceMetrics(BaseModel):
    """交易效能指標響應模型

    此模型定義了交易系統效能監控的詳細指標。

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


class SystemHealthStatus(BaseModel):
    """系統健康狀態響應模型

    此模型定義了系統整體健康狀態的資訊。

    Attributes:
        overall_status: 整體狀態
        health_score: 健康分數 (0-100)
        components: 組件狀態字典
        last_check: 最後檢查時間
        uptime_seconds: 運行時間（秒）
        system_info: 系統信息字典
        active_alerts: 活躍警報數量
        critical_issues: 嚴重問題列表
    """

    overall_status: str = Field(..., description="整體狀態")
    health_score: float = Field(..., description="健康分數 (0-100)")
    components: dict = Field(..., description="組件狀態")
    last_check: datetime = Field(..., description="最後檢查時間")
    uptime_seconds: int = Field(..., description="運行時間（秒）")
    system_info: dict = Field(..., description="系統信息")
    active_alerts: int = Field(..., description="活躍警報數量")
    critical_issues: List[str] = Field(..., description="嚴重問題列表")


# ==================== API 端點 ====================


@router.get(
    "/resources",
    response_model=APIResponse[List[SystemResourceMetrics]],
    responses=COMMON_RESPONSES,
    summary="系統資源監控",
    description="獲取系統資源使用情況，包括 CPU、記憶體、磁碟、網路等指標",
)
async def get_system_resources(
    time_range: str = Query(default="1h", description="時間範圍 (1h/24h/7d)"),
    interval: str = Query(default="5m", description="數據間隔 (1m/5m/15m/1h)"),
):
    """獲取系統資源監控數據

    此端點用於獲取系統資源的歷史監控數據，支援不同的時間範圍和數據間隔。

    Args:
        time_range: 時間範圍，支援 1h、24h、7d
        interval: 數據間隔，支援 1m、5m、15m、1h

    Returns:
        APIResponse[List[SystemResourceMetrics]]: 包含系統資源指標列表的 API 回應

    Raises:
        HTTPException: 當參數無效或獲取數據失敗時

    Example:
        GET /api/monitoring/system/resources?time_range=24h&interval=15m
    """
    try:
        # 解析時間範圍
        time_ranges = {
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
        }

        if time_range not in time_ranges:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"無效的時間範圍，支援: {', '.join(time_ranges.keys())}",
            )

        # 解析數據間隔
        intervals = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
        }

        if interval not in intervals:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"無效的數據間隔，支援: {', '.join(intervals.keys())}",
            )

        # 計算查詢時間範圍
        end_time = datetime.now()
        start_time = end_time - time_ranges[time_range]

        # 獲取系統資源數據
        resource_data = monitoring_service.get_system_resource_metrics(
            start_time=start_time, end_time=end_time, interval=intervals[interval]
        )

        # 轉換為響應模型
        metrics_list = []
        for data in resource_data:
            metrics = SystemResourceMetrics(
                timestamp=data["timestamp"],
                cpu_usage=data["cpu_usage"],
                memory_usage=data["memory_usage"],
                memory_total=data["memory_total"],
                memory_available=data["memory_available"],
                disk_usage=data["disk_usage"],
                disk_total=data["disk_total"],
                disk_free=data["disk_free"],
                network_io_sent=data["network_io_sent"],
                network_io_recv=data["network_io_recv"],
                load_average=data["load_average"],
                process_count=data["process_count"],
            )
            metrics_list.append(metrics)

        return APIResponse(
            success=True,
            message=f"獲取到 {len(metrics_list)} 個系統資源數據點",
            data=metrics_list,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取系統資源監控數據失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取系統資源監控數據失敗: {str(e)}",
        ) from e


@router.get(
    "/health",
    response_model=APIResponse[SystemHealthStatus],
    responses=COMMON_RESPONSES,
    summary="系統健康檢查",
    description="獲取系統整體健康狀態和組件狀態",
)
async def get_system_health():
    """獲取系統健康狀態

    此端點用於獲取系統的整體健康狀態，包括各組件的狀態和健康分數。

    Returns:
        APIResponse[SystemHealthStatus]: 包含系統健康狀態的 API 回應

    Raises:
        HTTPException: 當獲取健康狀態失敗時

    Example:
        GET /api/monitoring/system/health
    """
    try:
        # 獲取系統健康狀態
        health_data = monitoring_service.get_system_health_status()

        # 轉換為響應模型
        health_status = SystemHealthStatus(
            overall_status=health_data["overall_status"],
            health_score=health_data["health_score"],
            components=health_data["components"],
            last_check=health_data["last_check"],
            uptime_seconds=health_data["uptime_seconds"],
            system_info=health_data["system_info"],
            active_alerts=health_data["active_alerts"],
            critical_issues=health_data["critical_issues"],
        )

        return APIResponse(
            success=True, message="系統健康狀態獲取成功", data=health_status
        )

    except Exception as e:
        logger.error("獲取系統健康狀態失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取系統健康狀態失敗: {str(e)}",
        ) from e


@router.get(
    "/current",
    response_model=APIResponse[SystemResourceMetrics],
    responses=COMMON_RESPONSES,
    summary="當前系統資源狀態",
    description="獲取當前系統資源的即時狀態",
)
async def get_current_system_status():
    """獲取當前系統資源狀態

    此端點用於獲取系統資源的即時狀態，不需要歷史數據。

    Returns:
        APIResponse[SystemResourceMetrics]: 包含當前系統資源指標的 API 回應

    Raises:
        HTTPException: 當獲取當前狀態失敗時

    Example:
        GET /api/monitoring/system/current
    """
    try:
        # 獲取當前系統資源狀態
        current_data = monitoring_service.get_current_system_metrics()

        # 轉換為響應模型
        current_metrics = SystemResourceMetrics(
            timestamp=current_data["timestamp"],
            cpu_usage=current_data["cpu_usage"],
            memory_usage=current_data["memory_usage"],
            memory_total=current_data["memory_total"],
            memory_available=current_data["memory_available"],
            disk_usage=current_data["disk_usage"],
            disk_total=current_data["disk_total"],
            disk_free=current_data["disk_free"],
            network_io_sent=current_data["network_io_sent"],
            network_io_recv=current_data["network_io_recv"],
            load_average=current_data["load_average"],
            process_count=current_data["process_count"],
        )

        return APIResponse(
            success=True, message="當前系統資源狀態獲取成功", data=current_metrics
        )

    except Exception as e:
        logger.error("獲取當前系統資源狀態失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取當前系統資源狀態失敗: {str(e)}",
        ) from e


@router.get(
    "/trading/performance",
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

    此端點用於獲取交易系統的效能指標，包括 API 延遲、吞吐量、成功率等。

    Args:
        time_range: 時間範圍，支援 1h、24h、7d
        interval: 數據間隔，支援 1m、5m、15m、1h

    Returns:
        APIResponse[List[TradingPerformanceMetrics]]: 包含交易效能指標列表的 API 回應

    Raises:
        HTTPException: 當參數無效或獲取數據失敗時

    Example:
        GET /api/monitoring/system/trading/performance?time_range=24h&interval=15m
    """
    try:
        # 解析時間範圍
        time_ranges = {
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
        }

        if time_range not in time_ranges:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"無效的時間範圍，支援: {', '.join(time_ranges.keys())}",
            )

        # 解析數據間隔
        intervals = {
            "1m": timedelta(minutes=1),
            "5m": timedelta(minutes=5),
            "15m": timedelta(minutes=15),
            "1h": timedelta(hours=1),
        }

        if interval not in intervals:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"無效的數據間隔，支援: {', '.join(intervals.keys())}",
            )

        # 計算查詢時間範圍
        end_time = datetime.now()
        start_time = end_time - time_ranges[time_range]

        # 獲取交易效能數據
        performance_data = monitoring_service.get_trading_performance_metrics(
            start_time=start_time, end_time=end_time, interval=intervals[interval]
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
                cache_hit_rate=data["cache_hit_rate"],
            )
            metrics_list.append(metrics)

        return APIResponse(
            success=True,
            message=f"獲取到 {len(metrics_list)} 個交易效能數據點",
            data=metrics_list,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取交易效能指標失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取交易效能指標失敗: {str(e)}",
        ) from e
