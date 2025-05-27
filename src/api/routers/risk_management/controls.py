"""風控機制管理 API

此模組實現風控機制管理相關的 API 端點，包括風控機制狀態查詢和切換。
"""

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, status

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.core.risk_management_service import RiskManagementService
from .models import RiskControlToggleRequest, RiskControlStatus

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化風險管理服務
risk_service = RiskManagementService()


@router.get(
    "/status",
    response_model=APIResponse[List[RiskControlStatus]],
    responses=COMMON_RESPONSES,
    summary="獲取風控機制狀態",
    description="獲取所有風控機制的當前狀態",
)
async def get_risk_control_status():
    """
    獲取風控機制狀態

    Returns:
        APIResponse[List[RiskControlStatus]]: 包含所有風控機制狀態的 API 回應

    Raises:
        HTTPException: 當獲取風控機制狀態失敗時
    """
    try:
        # 獲取風控機制狀態
        control_status_list = risk_service.get_risk_control_status()

        # 如果沒有數據，返回預設狀態
        if not control_status_list:
            control_status_list = [
                {
                    "control_name": "stop_loss",
                    "enabled": True,
                    "status": "active",
                    "last_triggered": None,
                    "trigger_count": 0,
                    "description": "停損機制",
                },
                {
                    "control_name": "take_profit",
                    "enabled": True,
                    "status": "active",
                    "last_triggered": None,
                    "trigger_count": 0,
                    "description": "停利機制",
                },
                {
                    "control_name": "position_limit",
                    "enabled": True,
                    "status": "active",
                    "last_triggered": None,
                    "trigger_count": 0,
                    "description": "部位限制",
                },
                {
                    "control_name": "var_monitoring",
                    "enabled": True,
                    "status": "active",
                    "last_triggered": None,
                    "trigger_count": 0,
                    "description": "VaR 監控",
                },
                {
                    "control_name": "drawdown_protection",
                    "enabled": True,
                    "status": "active",
                    "last_triggered": None,
                    "trigger_count": 0,
                    "description": "回撤保護",
                },
                {
                    "control_name": "correlation_check",
                    "enabled": True,
                    "status": "active",
                    "last_triggered": None,
                    "trigger_count": 0,
                    "description": "相關性檢查",
                },
                {
                    "control_name": "sector_limit",
                    "enabled": True,
                    "status": "active",
                    "last_triggered": None,
                    "trigger_count": 0,
                    "description": "行業限制",
                },
                {
                    "control_name": "emergency_stop",
                    "enabled": False,
                    "status": "inactive",
                    "last_triggered": None,
                    "trigger_count": 0,
                    "description": "緊急停止",
                },
            ]

        # 轉換為響應模型
        response_data = [
            RiskControlStatus(**control) for control in control_status_list
        ]

        return APIResponse(
            success=True,
            message=f"獲取到 {len(response_data)} 個風控機制狀態",
            data=response_data,
        )

    except Exception as e:
        logger.error("獲取風控機制狀態失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取風控機制狀態失敗: {str(e)}",
        ) from e


@router.post(
    "/toggle",
    response_model=APIResponse[RiskControlStatus],
    responses=COMMON_RESPONSES,
    summary="切換風控機制",
    description="啟用或停用特定的風控機制",
)
async def toggle_risk_control(request: RiskControlToggleRequest):
    """
    切換風控機制

    Args:
        request: 風控機制切換請求

    Returns:
        APIResponse[RiskControlStatus]: 包含切換後風控機制狀態的 API 回應

    Raises:
        HTTPException: 當切換風控機制失敗時
    """
    try:
        # 執行風控機制切換
        success, message = risk_service.toggle_risk_control(
            control_name=request.control_name,
            enabled=request.enabled,
            reason=request.reason,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"風控機制切換失敗: {message}",
            )

        # 獲取更新後的風控機制狀態
        control_status = risk_service.get_risk_control_status(request.control_name)

        if not control_status:
            # 如果沒有找到，創建預設狀態
            control_status = {
                "control_name": request.control_name,
                "enabled": request.enabled,
                "status": "active" if request.enabled else "inactive",
                "last_triggered": None,
                "trigger_count": 0,
                "description": f"{request.control_name} 風控機制",
            }

        response_data = RiskControlStatus(**control_status)

        action = "啟用" if request.enabled else "停用"
        return APIResponse(
            success=True,
            message=f"風控機制 {request.control_name} {action}成功",
            data=response_data,
        )

    except Exception as e:
        logger.error("切換風控機制失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"切換風控機制失敗: {str(e)}",
        ) from e


@router.post(
    "/emergency-stop",
    response_model=APIResponse[dict],
    responses=COMMON_RESPONSES,
    summary="緊急停止",
    description="立即停止所有交易活動",
)
async def emergency_stop():
    """
    緊急停止

    Returns:
        APIResponse[dict]: 包含緊急停止結果的 API 回應

    Raises:
        HTTPException: 當緊急停止失敗時
    """
    try:
        # 執行緊急停止
        success, message = risk_service.emergency_stop()

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"緊急停止失敗: {message}",
            )

        response_data = {
            "emergency_stop_activated": True,
            "activated_at": datetime.now(),
            "message": "所有交易活動已停止",
            "affected_systems": [
                "交易執行系統",
                "策略執行系統",
                "自動下單系統",
            ],
        }

        return APIResponse(success=True, message="緊急停止執行成功", data=response_data)

    except Exception as e:
        logger.error("緊急停止失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"緊急停止失敗: {str(e)}",
        ) from e


@router.post(
    "/resume",
    response_model=APIResponse[dict],
    responses=COMMON_RESPONSES,
    summary="恢復交易",
    description="恢復交易活動（解除緊急停止）",
)
async def resume_trading():
    """
    恢復交易

    Returns:
        APIResponse[dict]: 包含恢復交易結果的 API 回應

    Raises:
        HTTPException: 當恢復交易失敗時
    """
    try:
        # 執行恢復交易
        success, message = risk_service.resume_trading()

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"恢復交易失敗: {message}",
            )

        response_data = {
            "trading_resumed": True,
            "resumed_at": datetime.now(),
            "message": "交易活動已恢復",
            "restored_systems": [
                "交易執行系統",
                "策略執行系統",
                "自動下單系統",
            ],
        }

        return APIResponse(success=True, message="交易恢復成功", data=response_data)

    except Exception as e:
        logger.error("恢復交易失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"恢復交易失敗: {str(e)}",
        ) from e
