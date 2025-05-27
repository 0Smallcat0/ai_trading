"""警報管理 API

此模組實現警報管理相關的 API 端點，包括創建、查詢、確認和解決警報。
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Path, status
from pydantic import BaseModel, Field

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.core.system_monitoring_service import SystemMonitoringService
from .models import AlertRuleRequest, AlertUpdateRequest

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化系統監控服務
monitoring_service = SystemMonitoringService()


# ==================== 響應模型 ====================


class AlertRule(BaseModel):
    """警報規則響應模型
    
    此模型定義了警報規則的詳細資訊。
    
    Attributes:
        id: 規則 ID
        name: 規則名稱
        description: 規則描述
        metric_type: 監控指標類型
        threshold_type: 閾值類型
        threshold_value: 閾值
        comparison_operator: 比較運算符
        severity: 警報嚴重程度
        notification_channels: 通知渠道
        enabled: 是否啟用
        suppression_duration: 抑制時間（秒）
        created_at: 創建時間
        updated_at: 更新時間
        last_triggered: 最後觸發時間
        trigger_count: 觸發次數
    """
    id: str = Field(..., description="規則 ID")
    name: str = Field(..., description="規則名稱")
    description: Optional[str] = Field(default=None, description="規則描述")
    metric_type: str = Field(..., description="監控指標類型")
    threshold_type: str = Field(..., description="閾值類型")
    threshold_value: float = Field(..., description="閾值")
    comparison_operator: str = Field(..., description="比較運算符")
    severity: str = Field(..., description="警報嚴重程度")
    notification_channels: List[str] = Field(..., description="通知渠道")
    enabled: bool = Field(..., description="是否啟用")
    suppression_duration: int = Field(..., description="抑制時間（秒）")
    created_at: datetime = Field(..., description="創建時間")
    updated_at: Optional[datetime] = Field(default=None, description="更新時間")
    last_triggered: Optional[datetime] = Field(default=None, description="最後觸發時間")
    trigger_count: int = Field(..., description="觸發次數")


class AlertRecord(BaseModel):
    """警報記錄響應模型
    
    此模型定義了警報記錄的詳細資訊。
    
    Attributes:
        id: 警報 ID
        rule_id: 規則 ID
        rule_name: 規則名稱
        severity: 嚴重程度
        title: 警報標題
        message: 警報訊息
        metric_value: 觸發時的指標值
        threshold_value: 閾值
        status: 警報狀態
        created_at: 創建時間
        acknowledged_at: 確認時間
        acknowledged_by: 確認人
        resolved_at: 解決時間
        resolved_by: 解決人
        notification_sent: 是否已發送通知
    """
    id: str = Field(..., description="警報 ID")
    rule_id: str = Field(..., description="規則 ID")
    rule_name: str = Field(..., description="規則名稱")
    severity: str = Field(..., description="嚴重程度")
    title: str = Field(..., description="警報標題")
    message: str = Field(..., description="警報訊息")
    metric_value: float = Field(..., description="觸發時的指標值")
    threshold_value: float = Field(..., description="閾值")
    status: str = Field(..., description="警報狀態")
    created_at: datetime = Field(..., description="創建時間")
    acknowledged_at: Optional[datetime] = Field(default=None, description="確認時間")
    acknowledged_by: Optional[str] = Field(default=None, description="確認人")
    resolved_at: Optional[datetime] = Field(default=None, description="解決時間")
    resolved_by: Optional[str] = Field(default=None, description="解決人")
    notification_sent: bool = Field(..., description="是否已發送通知")


# ==================== API 端點 ====================


@router.post(
    "/rules",
    response_model=APIResponse[AlertRule],
    responses=COMMON_RESPONSES,
    summary="創建警報規則",
    description="創建新的警報規則",
)
async def create_alert_rule(request: AlertRuleRequest):
    """創建警報規則
    
    此端點用於創建新的警報規則，用於監控系統指標並觸發警報。
    
    Args:
        request: 警報規則創建請求資料
        
    Returns:
        APIResponse[AlertRule]: 包含創建的警報規則詳情的 API 回應
        
    Raises:
        HTTPException: 當警報規則創建失敗時
        
    Example:
        POST /api/monitoring/alerts/rules
        {
            "name": "CPU 使用率警報",
            "metric_type": "cpu_usage",
            "threshold_type": "percentage",
            "threshold_value": 80.0,
            "comparison_operator": ">",
            "severity": "WARNING",
            "notification_channels": ["email"]
        }
    """
    try:
        # 創建警報規則
        rule_data = _build_alert_rule_data(request)
        rule_id = monitoring_service.create_alert_rule(rule_data)

        # 獲取創建的規則詳情
        rule_details = monitoring_service.get_alert_rule(rule_id)
        
        if not rule_details:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="警報規則創建成功但無法獲取詳情"
            )

        # 轉換為響應模型
        response_data = _convert_to_alert_rule_response(rule_details)

        return APIResponse(
            success=True,
            message="警報規則創建成功",
            data=response_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("創建警報規則失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"創建警報規則失敗: {str(e)}"
        ) from e


@router.get(
    "/rules",
    response_model=APIResponse[List[AlertRule]],
    responses=COMMON_RESPONSES,
    summary="查詢警報規則列表",
    description="查詢警報規則列表，支援分頁和篩選",
)
async def get_alert_rules(
    page: int = Query(default=1, ge=1, description="頁碼"),
    page_size: int = Query(default=20, ge=1, le=100, description="每頁數量"),
    enabled: Optional[bool] = Query(default=None, description="是否啟用篩選"),
    severity: Optional[str] = Query(default=None, description="嚴重程度篩選"),
    metric_type: Optional[str] = Query(default=None, description="指標類型篩選"),
):
    """查詢警報規則列表
    
    此端點用於查詢警報規則列表，支援多種篩選條件和分頁。
    
    Args:
        page: 頁碼
        page_size: 每頁數量
        enabled: 是否啟用篩選
        severity: 嚴重程度篩選
        metric_type: 指標類型篩選
        
    Returns:
        APIResponse[List[AlertRule]]: 包含警報規則列表的 API 回應
        
    Raises:
        HTTPException: 當查詢失敗時
    """
    try:
        # 構建篩選條件
        filters = _build_alert_rule_filters(enabled, severity, metric_type)

        # 獲取警報規則列表
        rules_data = monitoring_service.get_alert_rules_list(
            page=page, page_size=page_size, filters=filters
        )

        # 轉換為響應模型
        rules_list = [
            _convert_to_alert_rule_response(rule)
            for rule in rules_data.get("rules", [])
        ]

        return APIResponse(
            success=True,
            message=f"獲取到 {len(rules_list)} 個警報規則",
            data=rules_list
        )

    except Exception as e:
        logger.error("查詢警報規則列表失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢警報規則列表失敗: {str(e)}"
        ) from e


@router.get(
    "/",
    response_model=APIResponse[List[AlertRecord]],
    responses=COMMON_RESPONSES,
    summary="查詢警報記錄",
    description="查詢警報記錄，支援分頁和篩選",
)
async def get_alerts(
    page: int = Query(default=1, ge=1, description="頁碼"),
    page_size: int = Query(default=20, ge=1, le=100, description="每頁數量"),
    severity: Optional[str] = Query(default=None, description="嚴重程度篩選"),
    alert_type: Optional[str] = Query(default=None, description="警報類型篩選"),
    acknowledged: Optional[bool] = Query(default=None, description="是否已確認篩選"),
    resolved: Optional[bool] = Query(default=None, description="是否已解決篩選"),
    start_time: Optional[str] = Query(default=None, description="開始時間 (ISO 8601)"),
    end_time: Optional[str] = Query(default=None, description="結束時間 (ISO 8601)"),
):
    """查詢警報記錄
    
    此端點用於查詢警報記錄，支援多種篩選條件和分頁。
    
    Args:
        page: 頁碼
        page_size: 每頁數量
        severity: 嚴重程度篩選
        alert_type: 警報類型篩選
        acknowledged: 是否已確認篩選
        resolved: 是否已解決篩選
        start_time: 開始時間
        end_time: 結束時間
        
    Returns:
        APIResponse[List[AlertRecord]]: 包含警報記錄列表的 API 回應
        
    Raises:
        HTTPException: 當查詢失敗時
    """
    try:
        # 構建篩選條件
        filters = _build_alert_filters(
            severity, alert_type, acknowledged, resolved, start_time, end_time
        )

        # 獲取警報記錄列表
        alerts_data = monitoring_service.get_alerts_list(
            page=page, page_size=page_size, filters=filters
        )

        # 轉換為響應模型
        alerts_list = [
            _convert_to_alert_record_response(alert)
            for alert in alerts_data.get("alerts", [])
        ]

        return APIResponse(
            success=True,
            message=f"獲取到 {len(alerts_list)} 個警報記錄",
            data=alerts_list
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("查詢警報記錄失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢警報記錄失敗: {str(e)}"
        ) from e


@router.put(
    "/{alert_id}",
    response_model=APIResponse[AlertRecord],
    responses=COMMON_RESPONSES,
    summary="更新警報狀態",
    description="更新警報的確認或解決狀態",
)
async def update_alert(
    alert_id: str = Path(..., description="警報 ID"),
    request: AlertUpdateRequest = None
):
    """更新警報狀態
    
    此端點用於更新警報的確認或解決狀態。
    
    Args:
        alert_id: 警報 ID
        request: 警報更新請求資料
        
    Returns:
        APIResponse[AlertRecord]: 包含更新後警報詳情的 API 回應
        
    Raises:
        HTTPException: 當警報不存在或更新失敗時
    """
    try:
        # 檢查警報是否存在
        existing_alert = monitoring_service.get_alert_details(alert_id)
        if not existing_alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"警報 {alert_id} 不存在"
            )

        # 構建更新數據
        update_data = _build_alert_update_data(request)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="沒有提供任何更新數據"
            )

        # 執行警報更新
        success, message = monitoring_service.update_alert(alert_id, update_data)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"警報更新失敗: {message}"
            )

        # 獲取更新後的警報詳情
        updated_alert = monitoring_service.get_alert_details(alert_id)
        response_data = _convert_to_alert_record_response(updated_alert)

        return APIResponse(
            success=True,
            message="警報更新成功",
            data=response_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("更新警報失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新警報失敗: {str(e)}"
        ) from e


# ==================== 輔助函數 ====================


def _build_alert_rule_data(request: AlertRuleRequest) -> dict:
    """構建警報規則數據字典"""
    return {
        "name": request.name,
        "description": request.description,
        "metric_type": request.metric_type,
        "threshold_type": request.threshold_type,
        "threshold_value": request.threshold_value,
        "comparison_operator": request.comparison_operator,
        "severity": request.severity,
        "notification_channels": request.notification_channels,
        "enabled": request.enabled,
        "suppression_duration": request.suppression_duration,
    }


def _build_alert_rule_filters(
    enabled: Optional[bool],
    severity: Optional[str],
    metric_type: Optional[str]
) -> dict:
    """構建警報規則篩選條件"""
    filters = {}
    if enabled is not None:
        filters["enabled"] = enabled
    if severity:
        filters["severity"] = severity
    if metric_type:
        filters["metric_type"] = metric_type
    return filters


def _build_alert_filters(
    severity: Optional[str],
    alert_type: Optional[str],
    acknowledged: Optional[bool],
    resolved: Optional[bool],
    start_time: Optional[str],
    end_time: Optional[str]
) -> dict:
    """構建警報篩選條件"""
    filters = {}
    if severity:
        filters["severity"] = severity
    if alert_type:
        filters["alert_type"] = alert_type
    if acknowledged is not None:
        filters["acknowledged"] = acknowledged
    if resolved is not None:
        filters["resolved"] = resolved
    if start_time:
        try:
            filters["start_time"] = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="開始時間格式錯誤，請使用 ISO 8601 格式"
            ) from e
    if end_time:
        try:
            filters["end_time"] = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="結束時間格式錯誤，請使用 ISO 8601 格式"
            ) from e
    return filters


def _build_alert_update_data(request: AlertUpdateRequest) -> dict:
    """構建警報更新數據"""
    update_data = {}
    if request.acknowledged is not None:
        update_data["acknowledged"] = request.acknowledged
        if request.acknowledged and request.acknowledged_by:
            update_data["acknowledged_by"] = request.acknowledged_by
            update_data["acknowledged_at"] = datetime.now()
    if request.resolved is not None:
        update_data["resolved"] = request.resolved
        if request.resolved and request.resolved_by:
            update_data["resolved_by"] = request.resolved_by
            update_data["resolved_at"] = datetime.now()
    if request.notes is not None:
        update_data["notes"] = request.notes
    return update_data


def _convert_to_alert_rule_response(rule_details: dict) -> AlertRule:
    """將警報規則詳情轉換為響應模型"""
    return AlertRule(
        id=rule_details["id"],
        name=rule_details["name"],
        description=rule_details.get("description"),
        metric_type=rule_details["metric_type"],
        threshold_type=rule_details["threshold_type"],
        threshold_value=rule_details["threshold_value"],
        comparison_operator=rule_details["comparison_operator"],
        severity=rule_details["severity"],
        notification_channels=rule_details["notification_channels"],
        enabled=rule_details["enabled"],
        suppression_duration=rule_details["suppression_duration"],
        created_at=rule_details["created_at"],
        updated_at=rule_details.get("updated_at"),
        last_triggered=rule_details.get("last_triggered"),
        trigger_count=rule_details.get("trigger_count", 0),
    )


def _convert_to_alert_record_response(alert_details: dict) -> AlertRecord:
    """將警報記錄詳情轉換為響應模型"""
    return AlertRecord(
        id=alert_details["id"],
        rule_id=alert_details["rule_id"],
        rule_name=alert_details["rule_name"],
        severity=alert_details["severity"],
        title=alert_details["title"],
        message=alert_details["message"],
        metric_value=alert_details["metric_value"],
        threshold_value=alert_details["threshold_value"],
        status=alert_details["status"],
        created_at=alert_details["created_at"],
        acknowledged_at=alert_details.get("acknowledged_at"),
        acknowledged_by=alert_details.get("acknowledged_by"),
        resolved_at=alert_details.get("resolved_at"),
        resolved_by=alert_details.get("resolved_by"),
        notification_sent=alert_details.get("notification_sent", False),
    )
