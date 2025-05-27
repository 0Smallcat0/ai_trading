"""
Phase 5.3 監控與告警系統 API 路由

此模組實現了 Phase 5.3 監控與告警系統的 API 端點，包括：
- Prometheus 指標收集
- 智能告警管理
- Grafana 儀表板管理
- 健康檢查服務
- 即時數據推送（WebSocket）

遵循 RESTful API 設計原則和 Phase 5.3 開發標準。
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Query,
    WebSocket,
    WebSocketDisconnect,
    BackgroundTasks,
)
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
import asyncio

from src.core.auth import get_current_user
from src.core.logger import logger
from src.monitoring.prometheus_collector import PrometheusCollector
from src.monitoring.intelligent_alert_manager import (
    IntelligentAlertManager,
    AlertSeverity,
    AlertStatus,
)
from src.monitoring.grafana_config import GrafanaConfigManager
from src.monitoring.health_checker import HealthChecker
from src.monitoring.notification_services import NotificationServices

# 設置路由和日誌
router = APIRouter(prefix="/api/v1/monitoring", tags=["monitoring-v2"])
module_logger = logging.getLogger(__name__)

# 全域監控服務實例
prometheus_collector = PrometheusCollector()
alert_manager = IntelligentAlertManager()
grafana_manager = GrafanaConfigManager()
health_checker = HealthChecker()
notification_service = NotificationServices()


# ==================== 請求模型 ====================


class AlertRuleCreateRequest(BaseModel):
    """創建告警規則請求模型"""

    name: str = Field(..., description="規則名稱")
    description: str = Field(..., description="規則描述")
    metric_name: str = Field(..., description="監控指標名稱")
    operator: str = Field(..., description="比較運算符")
    threshold_value: float = Field(..., description="閾值")
    severity: str = Field(..., description="嚴重程度")
    enabled: bool = Field(default=True, description="是否啟用")
    notification_channels: List[str] = Field(
        default=["webhook"], description="通知渠道"
    )


class NotificationTestRequest(BaseModel):
    """通知測試請求模型"""

    channel: str = Field(..., description="通知渠道")
    message: str = Field(..., description="測試訊息")


# ==================== 啟動和關閉事件 ====================


@router.on_event("startup")
async def startup_monitoring_services():
    """
    啟動監控服務
    """
    try:
        # 啟動 Prometheus 指標收集
        prometheus_collector.start_collection()
        module_logger.info("Prometheus 指標收集已啟動")

        # 啟動智能告警管理器
        alert_manager.start()
        module_logger.info("智能告警管理器已啟動")

        # 啟動健康檢查服務
        health_checker.start()
        module_logger.info("健康檢查服務已啟動")

    except Exception as e:
        module_logger.error(f"啟動監控服務失敗: {e}")


@router.on_event("shutdown")
async def shutdown_monitoring_services():
    """
    關閉監控服務
    """
    try:
        prometheus_collector.stop_collection()
        alert_manager.stop()
        health_checker.stop()
        module_logger.info("監控服務已關閉")

    except Exception as e:
        module_logger.error(f"關閉監控服務失敗: {e}")


# ==================== 健康檢查端點 ====================


@router.get("/health")
async def health_check():
    """
    系統健康檢查端點

    Returns:
        Dict: 健康狀態資訊
    """
    try:
        overall_health = health_checker.get_overall_health()
        health_summary = health_checker.get_health_summary()

        return {
            "status": overall_health.status.value,
            "score": overall_health.score,
            "message": overall_health.message,
            "timestamp": datetime.now().isoformat(),
            "details": health_summary,
        }
    except Exception as e:
        module_logger.error(f"健康檢查失敗: {e}")
        raise HTTPException(status_code=500, detail="健康檢查失敗")


@router.get("/health/detailed")
async def detailed_health_check(current_user: dict = Depends(get_current_user)):
    """
    詳細健康檢查

    Args:
        current_user: 當前用戶

    Returns:
        Dict: 詳細健康狀態資訊
    """
    try:
        # 執行完整健康檢查
        results = health_checker.run_all_checks()
        overall_health = health_checker.get_overall_health()

        # 轉換結果格式
        detailed_results = {}
        for name, result in results.items():
            detailed_results[name] = {
                "status": result.status.value,
                "score": result.score,
                "message": result.message,
                "details": result.details,
                "duration": result.duration,
                "timestamp": result.timestamp.isoformat(),
            }

        return {
            "overall": {
                "status": overall_health.status.value,
                "score": overall_health.score,
                "message": overall_health.message,
            },
            "checks": detailed_results,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        module_logger.error(f"詳細健康檢查失敗: {e}")
        raise HTTPException(status_code=500, detail="詳細健康檢查失敗")


# ==================== Prometheus 指標端點 ====================


@router.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """
    獲取 Prometheus 格式指標

    Returns:
        PlainTextResponse: Prometheus 格式的指標數據
    """
    try:
        metrics_data = prometheus_collector.get_metrics()
        content_type = prometheus_collector.get_content_type()

        return PlainTextResponse(content=metrics_data, media_type=content_type)

    except Exception as e:
        module_logger.error(f"獲取 Prometheus 指標失敗: {e}")
        raise HTTPException(status_code=500, detail="獲取 Prometheus 指標失敗")


@router.get("/metrics/names")
async def get_metric_names(current_user: dict = Depends(get_current_user)):
    """
    獲取可用的指標名稱列表

    Args:
        current_user: 當前用戶

    Returns:
        Dict: 指標名稱列表
    """
    try:
        metric_names = prometheus_collector.get_metric_names()

        return {
            "metric_names": metric_names,
            "total": len(metric_names),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        module_logger.error(f"獲取指標名稱失敗: {e}")
        raise HTTPException(status_code=500, detail="獲取指標名稱失敗")


@router.post("/metrics/record/api")
async def record_api_metrics(
    method: str,
    endpoint: str,
    status_code: int,
    duration: float,
    current_user: dict = Depends(get_current_user),
):
    """
    記錄 API 請求指標

    Args:
        method: HTTP 方法
        endpoint: API 端點
        status_code: HTTP 狀態碼
        duration: 請求持續時間
        current_user: 當前用戶

    Returns:
        Dict: 操作結果
    """
    try:
        prometheus_collector.record_api_request(method, endpoint, status_code, duration)

        return {"message": "API 指標記錄成功", "timestamp": datetime.now().isoformat()}

    except Exception as e:
        module_logger.error(f"記錄 API 指標失敗: {e}")
        raise HTTPException(status_code=500, detail="記錄 API 指標失敗")


@router.post("/metrics/record/trading")
async def record_trading_metrics(
    order_type: str,
    status: str,
    latency: Optional[float] = None,
    current_user: dict = Depends(get_current_user),
):
    """
    記錄交易指標

    Args:
        order_type: 訂單類型
        status: 訂單狀態
        latency: 訂單延遲（可選）
        current_user: 當前用戶

    Returns:
        Dict: 操作結果
    """
    try:
        prometheus_collector.record_trading_order(order_type, status, latency)

        return {"message": "交易指標記錄成功", "timestamp": datetime.now().isoformat()}

    except Exception as e:
        module_logger.error(f"記錄交易指標失敗: {e}")
        raise HTTPException(status_code=500, detail="記錄交易指標失敗")


# ==================== 告警管理端點 ====================


@router.get("/alerts")
async def get_alerts(
    current_user: dict = Depends(get_current_user),
    status: Optional[str] = Query(None, description="告警狀態過濾"),
    severity: Optional[str] = Query(None, description="嚴重程度過濾"),
    limit: int = Query(50, description="返回數量限制"),
):
    """
    獲取告警列表

    Args:
        current_user: 當前用戶
        status: 告警狀態過濾
        severity: 嚴重程度過濾
        limit: 返回數量限制

    Returns:
        Dict: 告警列表
    """
    try:
        # 從智能告警管理器獲取告警
        active_alerts = list(alert_manager.active_alerts.values())

        # 應用過濾條件
        if status:
            active_alerts = [
                alert for alert in active_alerts if alert.status.value == status
            ]

        if severity:
            active_alerts = [
                alert for alert in active_alerts if alert.severity.value == severity
            ]

        # 限制返回數量
        active_alerts = active_alerts[:limit]

        # 轉換為字典格式
        alerts_data = []
        for alert in active_alerts:
            alerts_data.append(
                {
                    "id": alert.id,
                    "rule_id": alert.rule_id,
                    "rule_name": alert.rule_name,
                    "severity": alert.severity.value,
                    "status": alert.status.value,
                    "title": alert.title,
                    "message": alert.message,
                    "metric_value": alert.metric_value,
                    "threshold_value": alert.threshold_value,
                    "created_at": alert.created_at.isoformat(),
                    "escalation_level": alert.escalation_level,
                    "labels": alert.labels,
                    "annotations": alert.annotations,
                }
            )

        return {
            "alerts": alerts_data,
            "total": len(alerts_data),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        module_logger.error(f"獲取告警列表失敗: {e}")
        raise HTTPException(status_code=500, detail="獲取告警列表失敗")


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str, current_user: dict = Depends(get_current_user)
):
    """
    確認告警

    Args:
        alert_id: 告警ID
        current_user: 當前用戶

    Returns:
        Dict: 操作結果
    """
    try:
        # 從智能告警管理器確認告警
        if alert_id in alert_manager.active_alerts:
            alert = alert_manager.active_alerts[alert_id]
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.now()
            alert.acknowledged_by = current_user.get("username", "unknown")

            return {"message": "告警確認成功", "alert_id": alert_id}
        else:
            raise HTTPException(status_code=404, detail="告警不存在")

    except Exception as e:
        module_logger.error(f"確認告警失敗: {e}")
        raise HTTPException(status_code=500, detail="確認告警失敗")


@router.get("/alerts/rules")
async def get_alert_rules(current_user: dict = Depends(get_current_user)):
    """
    獲取告警規則列表

    Args:
        current_user: 當前用戶

    Returns:
        Dict: 告警規則列表
    """
    try:
        rules_data = []
        for rule in alert_manager.rules.values():
            rules_data.append(
                {
                    "id": rule.id,
                    "name": rule.name,
                    "description": rule.description,
                    "metric_name": rule.metric_name,
                    "operator": rule.operator,
                    "threshold_value": rule.threshold_value,
                    "severity": rule.severity.value,
                    "enabled": rule.enabled,
                    "notification_channels": rule.notification_channels,
                    "created_at": rule.created_at.isoformat(),
                    "updated_at": (
                        rule.updated_at.isoformat() if rule.updated_at else None
                    ),
                }
            )

        return {
            "rules": rules_data,
            "total": len(rules_data),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        module_logger.error(f"獲取告警規則失敗: {e}")
        raise HTTPException(status_code=500, detail="獲取告警規則失敗")


# ==================== Grafana 管理端點 ====================


@router.get("/grafana/dashboards")
async def get_grafana_dashboards(current_user: dict = Depends(get_current_user)):
    """
    獲取 Grafana 儀表板列表

    Args:
        current_user: 當前用戶

    Returns:
        Dict: 儀表板列表
    """
    try:
        dashboards = grafana_manager.get_dashboard_list()

        return {
            "dashboards": dashboards,
            "total": len(dashboards),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        module_logger.error(f"獲取 Grafana 儀表板失敗: {e}")
        raise HTTPException(status_code=500, detail="獲取 Grafana 儀表板失敗")


@router.post("/grafana/dashboards/deploy")
async def deploy_grafana_dashboards(
    current_user: dict = Depends(get_current_user),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    部署 Grafana 儀表板模板

    Args:
        current_user: 當前用戶
        background_tasks: 背景任務

    Returns:
        Dict: 部署結果
    """
    try:
        # 在背景執行部署任務
        def deploy_task():
            try:
                results = grafana_manager.deploy_all_templates()
                module_logger.info(f"Grafana 儀表板部署完成: {results}")
            except Exception as e:
                module_logger.error(f"Grafana 儀表板部署失敗: {e}")

        background_tasks.add_task(deploy_task)

        return {
            "message": "Grafana 儀表板部署已啟動",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        module_logger.error(f"啟動 Grafana 儀表板部署失敗: {e}")
        raise HTTPException(status_code=500, detail="啟動 Grafana 儀表板部署失敗")


@router.get("/grafana/templates")
async def get_grafana_templates(current_user: dict = Depends(get_current_user)):
    """
    獲取可用的 Grafana 模板列表

    Args:
        current_user: 當前用戶

    Returns:
        Dict: 模板列表
    """
    try:
        templates = grafana_manager.get_available_templates()

        return {
            "templates": templates,
            "total": len(templates),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        module_logger.error(f"獲取 Grafana 模板失敗: {e}")
        raise HTTPException(status_code=500, detail="獲取 Grafana 模板失敗")


@router.get("/grafana/test")
async def test_grafana_connection(current_user: dict = Depends(get_current_user)):
    """
    測試 Grafana 連接

    Args:
        current_user: 當前用戶

    Returns:
        Dict: 連接測試結果
    """
    try:
        is_connected = grafana_manager.test_connection()

        return {
            "connected": is_connected,
            "message": "Grafana 連接正常" if is_connected else "Grafana 連接失敗",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        module_logger.error(f"測試 Grafana 連接失敗: {e}")
        raise HTTPException(status_code=500, detail="測試 Grafana 連接失敗")


# ==================== 通知服務端點 ====================


@router.get("/notifications/channels")
async def get_notification_channels(current_user: dict = Depends(get_current_user)):
    """
    獲取通知渠道狀態

    Args:
        current_user: 當前用戶

    Returns:
        Dict: 通知渠道狀態
    """
    try:
        channel_status = notification_service.get_channel_status()
        enabled_channels = notification_service.get_enabled_channels()

        return {
            "channels": channel_status,
            "enabled_channels": enabled_channels,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        module_logger.error(f"獲取通知渠道狀態失敗: {e}")
        raise HTTPException(status_code=500, detail="獲取通知渠道狀態失敗")


@router.post("/notifications/test")
async def test_notification_channels(
    request: NotificationTestRequest, current_user: dict = Depends(get_current_user)
):
    """
    測試通知渠道

    Args:
        request: 通知測試請求
        current_user: 當前用戶

    Returns:
        Dict: 測試結果
    """
    try:
        # 準備測試數據
        test_data = {
            "alert_id": "test-alert",
            "title": "通知測試",
            "message": request.message,
            "severity": "INFO",
            "created_at": datetime.now().isoformat(),
        }

        # 發送測試通知
        success = notification_service.send_notification(request.channel, test_data)

        return {
            "success": success,
            "channel": request.channel,
            "message": "測試通知發送成功" if success else "測試通知發送失敗",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        module_logger.error(f"測試通知渠道失敗: {e}")
        raise HTTPException(status_code=500, detail="測試通知渠道失敗")


@router.post("/notifications/test/all")
async def test_all_notification_channels(
    current_user: dict = Depends(get_current_user),
):
    """
    測試所有通知渠道

    Args:
        current_user: 當前用戶

    Returns:
        Dict: 測試結果
    """
    try:
        test_results = notification_service.test_all_channels()

        return {
            "results": test_results,
            "total_channels": len(test_results),
            "successful_channels": sum(1 for result in test_results.values() if result),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        module_logger.error(f"測試所有通知渠道失敗: {e}")
        raise HTTPException(status_code=500, detail="測試所有通知渠道失敗")


# ==================== WebSocket 即時數據推送 ====================


class ConnectionManager:
    """WebSocket 連接管理器"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """接受 WebSocket 連接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        module_logger.info(
            f"WebSocket 連接已建立，當前連接數: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        """斷開 WebSocket 連接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            module_logger.info(
                f"WebSocket 連接已斷開，當前連接數: {len(self.active_connections)}"
            )

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """發送個人訊息"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            module_logger.error(f"發送 WebSocket 訊息失敗: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        """廣播訊息給所有連接"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)

        # 移除斷開的連接
        for connection in disconnected:
            self.disconnect(connection)


# 全域連接管理器
connection_manager = ConnectionManager()


@router.websocket("/ws/monitoring")
async def websocket_monitoring_endpoint(websocket: WebSocket):
    """
    WebSocket 即時監控數據推送端點

    Args:
        websocket: WebSocket 連接
    """
    await connection_manager.connect(websocket)

    try:
        while True:
            # 每5秒推送一次監控數據
            await asyncio.sleep(5)

            # 獲取最新監控數據
            overall_health = health_checker.get_overall_health()
            health_summary = health_checker.get_health_summary()
            active_alerts = list(alert_manager.active_alerts.values())

            # 構建推送數據
            push_data = {
                "type": "monitoring_update",
                "timestamp": datetime.now().isoformat(),
                "health": {
                    "status": overall_health.status.value,
                    "score": overall_health.score,
                    "message": overall_health.message,
                    "details": health_summary,
                },
                "alerts": {
                    "total": len(active_alerts),
                    "critical": len(
                        [
                            a
                            for a in active_alerts
                            if a.severity == AlertSeverity.CRITICAL
                        ]
                    ),
                    "warning": len(
                        [
                            a
                            for a in active_alerts
                            if a.severity == AlertSeverity.WARNING
                        ]
                    ),
                },
                "services": {
                    "prometheus_collector": prometheus_collector.is_healthy(),
                    "alert_manager": alert_manager.is_running,
                    "health_checker": health_checker.is_running,
                    "grafana_manager": grafana_manager.is_healthy(),
                },
            }

            await connection_manager.send_personal_message(
                json.dumps(push_data), websocket
            )

    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        module_logger.error(f"WebSocket 錯誤: {e}")
        connection_manager.disconnect(websocket)
