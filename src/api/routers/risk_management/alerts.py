"""風險警報管理 API

此模組實現風險警報管理相關的 API 端點，包括警報查詢、確認和管理。
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Path, status

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.core.risk_management_service import RiskManagementService
from .models import AlertAcknowledgeRequest, RiskAlert

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化風險管理服務
risk_service = RiskManagementService()


@router.get(
    "/",
    response_model=APIResponse[List[RiskAlert]],
    responses=COMMON_RESPONSES,
    summary="獲取風險警報",
    description="獲取風險警報列表，支援篩選條件",
)
async def get_risk_alerts(
    severity: Optional[str] = Query(default=None, description="嚴重程度篩選"),
    alert_type: Optional[str] = Query(default=None, description="警報類型篩選"),
    acknowledged: Optional[bool] = Query(default=None, description="是否已確認篩選"),
    resolved: Optional[bool] = Query(default=None, description="是否已解決篩選"),
    limit: int = Query(default=50, ge=1, le=200, description="返回數量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
):
    """
    獲取風險警報

    Args:
        severity: 嚴重程度篩選 (low/medium/high/critical)
        alert_type: 警報類型篩選
        acknowledged: 是否已確認篩選
        resolved: 是否已解決篩選
        limit: 返回數量限制
        offset: 偏移量

    Returns:
        APIResponse[List[RiskAlert]]: 包含風險警報列表的 API 回應

    Raises:
        HTTPException: 當獲取風險警報失敗時
    """
    try:
        # 構建篩選條件
        filters = {}
        if severity:
            filters["severity"] = severity
        if alert_type:
            filters["alert_type"] = alert_type
        if acknowledged is not None:
            filters["acknowledged"] = acknowledged
        if resolved is not None:
            filters["resolved"] = resolved

        # 獲取風險警報
        alerts = risk_service.get_risk_alerts(
            filters=filters, limit=limit, offset=offset
        )

        # 如果沒有數據，返回模擬警報
        if not alerts:
            alerts = [
                {
                    "id": "alert_001",
                    "alert_type": "position_limit",
                    "severity": "high",
                    "title": "部位限制超標",
                    "message": "台積電部位超過單一股票限制 15%",
                    "symbol": "2330.TW",
                    "portfolio_id": "portfolio_001",
                    "metric_value": 0.18,
                    "threshold_value": 0.15,
                    "created_at": datetime.now() - timedelta(hours=2),
                    "acknowledged": False,
                    "acknowledged_at": None,
                    "acknowledged_by": None,
                    "resolved": False,
                    "resolved_at": None,
                },
                {
                    "id": "alert_002",
                    "alert_type": "var_breach",
                    "severity": "critical",
                    "title": "VaR 超標",
                    "message": "投資組合 VaR 超過設定閾值",
                    "symbol": None,
                    "portfolio_id": "portfolio_001",
                    "metric_value": 0.035,
                    "threshold_value": 0.025,
                    "created_at": datetime.now() - timedelta(hours=1),
                    "acknowledged": True,
                    "acknowledged_at": datetime.now() - timedelta(minutes=30),
                    "acknowledged_by": "risk_manager",
                    "resolved": False,
                    "resolved_at": None,
                },
                {
                    "id": "alert_003",
                    "alert_type": "drawdown",
                    "severity": "medium",
                    "title": "回撤警告",
                    "message": "投資組合回撤達到 8%",
                    "symbol": None,
                    "portfolio_id": "portfolio_002",
                    "metric_value": 0.08,
                    "threshold_value": 0.10,
                    "created_at": datetime.now() - timedelta(minutes=30),
                    "acknowledged": False,
                    "acknowledged_at": None,
                    "acknowledged_by": None,
                    "resolved": False,
                    "resolved_at": None,
                },
            ]

        # 應用篩選條件
        if severity:
            alerts = [alert for alert in alerts if alert.get("severity") == severity]
        if alert_type:
            alerts = [
                alert for alert in alerts if alert.get("alert_type") == alert_type
            ]
        if acknowledged is not None:
            alerts = [
                alert for alert in alerts if alert.get("acknowledged") == acknowledged
            ]
        if resolved is not None:
            alerts = [alert for alert in alerts if alert.get("resolved") == resolved]

        # 應用分頁
        total_alerts = len(alerts)
        alerts = alerts[offset : offset + limit]

        # 轉換為響應模型
        response_data = [RiskAlert(**alert) for alert in alerts]

        return APIResponse(
            success=True,
            message=f"獲取到 {len(response_data)} 個風險警報（總計 {total_alerts} 個）",
            data=response_data,
        )

    except Exception as e:
        logger.error("獲取風險警報失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取風險警報失敗: {str(e)}",
        ) from e


@router.get(
    "/{alert_id}",
    response_model=APIResponse[RiskAlert],
    responses=COMMON_RESPONSES,
    summary="獲取特定風險警報",
    description="根據警報 ID 獲取特定的風險警報詳情",
)
async def get_risk_alert(alert_id: str = Path(..., description="警報 ID")):
    """
    獲取特定風險警報

    Args:
        alert_id: 警報 ID

    Returns:
        APIResponse[RiskAlert]: 包含風險警報詳情的 API 回應

    Raises:
        HTTPException: 當獲取風險警報失敗時
    """
    try:
        # 獲取特定警報
        alert = risk_service.get_risk_alert(alert_id)

        if not alert:
            # 模擬警報數據
            alert = {
                "id": alert_id,
                "alert_type": "position_limit",
                "severity": "high",
                "title": "部位限制超標",
                "message": "台積電部位超過單一股票限制 15%",
                "symbol": "2330.TW",
                "portfolio_id": "portfolio_001",
                "metric_value": 0.18,
                "threshold_value": 0.15,
                "created_at": datetime.now() - timedelta(hours=2),
                "acknowledged": False,
                "acknowledged_at": None,
                "acknowledged_by": None,
                "resolved": False,
                "resolved_at": None,
            }

        response_data = RiskAlert(**alert)

        return APIResponse(
            success=True, message=f"警報 {alert_id} 獲取成功", data=response_data
        )

    except Exception as e:
        logger.error("獲取風險警報失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取風險警報失敗: {str(e)}",
        ) from e


@router.post(
    "/acknowledge",
    response_model=APIResponse[dict],
    responses=COMMON_RESPONSES,
    summary="確認風險警報",
    description="確認一個或多個風險警報",
)
async def acknowledge_alerts(request: AlertAcknowledgeRequest):
    """
    確認風險警報

    Args:
        request: 警報確認請求

    Returns:
        APIResponse[dict]: 包含確認結果的 API 回應

    Raises:
        HTTPException: 當確認風險警報失敗時
    """
    try:
        # 執行警報確認
        success_count = 0
        failed_alerts = []

        for alert_id in request.alert_ids:
            success = risk_service.acknowledge_alert(
                alert_id=alert_id,
                acknowledged_by=request.acknowledged_by,
                notes=request.notes,
            )

            if success:
                success_count += 1
            else:
                failed_alerts.append(alert_id)

        response_data = {
            "total_alerts": len(request.alert_ids),
            "acknowledged_count": success_count,
            "failed_count": len(failed_alerts),
            "failed_alerts": failed_alerts,
            "acknowledged_by": request.acknowledged_by,
            "acknowledged_at": datetime.now(),
            "notes": request.notes,
        }

        if failed_alerts:
            return APIResponse(
                success=False,
                message=f"部分警報確認失敗：{success_count}/{len(request.alert_ids)} 成功",
                data=response_data,
            )

        return APIResponse(
            success=True,
            message=f"成功確認 {success_count} 個警報",
            data=response_data,
        )

    except Exception as e:
        logger.error("確認風險警報失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"確認風險警報失敗: {str(e)}",
        ) from e


@router.delete(
    "/{alert_id}",
    response_model=APIResponse[dict],
    responses=COMMON_RESPONSES,
    summary="刪除風險警報",
    description="刪除特定的風險警報",
)
async def delete_risk_alert(alert_id: str = Path(..., description="警報 ID")):
    """
    刪除風險警報

    Args:
        alert_id: 警報 ID

    Returns:
        APIResponse[dict]: 包含刪除結果的 API 回應

    Raises:
        HTTPException: 當刪除風險警報失敗時
    """
    try:
        # 執行警報刪除
        success = risk_service.delete_alert(alert_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"警報 {alert_id} 不存在或刪除失敗",
            )

        response_data = {
            "alert_id": alert_id,
            "deleted": True,
            "deleted_at": datetime.now(),
        }

        return APIResponse(
            success=True, message=f"警報 {alert_id} 刪除成功", data=response_data
        )

    except Exception as e:
        logger.error("刪除風險警報失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除風險警報失敗: {str(e)}",
        ) from e
