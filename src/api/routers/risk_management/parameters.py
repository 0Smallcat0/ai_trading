"""風險參數管理 API

此模組實現風險參數管理相關的 API 端點，包括參數設定、獲取和更新。
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.core.risk_management_service import RiskManagementService
from .models import RiskParametersRequest, RiskParameters

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化風險管理服務
risk_service = RiskManagementService()


@router.post(
    "/",
    response_model=APIResponse[RiskParameters],
    responses=COMMON_RESPONSES,
    summary="設定風險參數",
    description="設定或更新風險管理參數配置",
)
async def set_risk_parameters(request: RiskParametersRequest):
    """
    設定風險參數

    Args:
        request: 風險參數設定請求

    Returns:
        APIResponse[RiskParameters]: 包含設定後風險參數的 API 回應

    Raises:
        HTTPException: 當參數設定失敗時
    """
    try:
        # 轉換請求為參數字典
        parameters = {
            "stop_loss_type": request.stop_loss_type,
            "stop_loss_value": request.stop_loss_value,
            "take_profit_type": request.take_profit_type,
            "take_profit_value": request.take_profit_value,
            "max_position_size": request.max_position_size,
            "max_portfolio_risk": request.max_portfolio_risk,
            "max_daily_loss": request.max_daily_loss,
            "max_drawdown": request.max_drawdown,
            "var_confidence_level": request.var_confidence_level,
            "var_time_horizon": request.var_time_horizon,
            "var_method": request.var_method,
            "max_correlation": request.max_correlation,
            "correlation_lookback": request.correlation_lookback,
            "max_sector_exposure": request.max_sector_exposure,
            "max_single_stock": request.max_single_stock,
        }

        # 設定風險參數
        success = risk_service.set_risk_parameters(parameters)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="風險參數設定失敗",
            )

        # 獲取更新後的參數
        updated_params = risk_service.get_risk_parameters()

        response_data = RiskParameters(
            **updated_params,
            updated_at=datetime.now(),
            updated_by="system",  # 這裡應該從認證中獲取用戶信息
        )

        return APIResponse(success=True, message="風險參數設定成功", data=response_data)

    except Exception as e:
        logger.error("設定風險參數失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"設定風險參數失敗: {str(e)}",
        ) from e


@router.get(
    "/",
    response_model=APIResponse[RiskParameters],
    responses=COMMON_RESPONSES,
    summary="獲取風險參數",
    description="獲取當前的風險管理參數配置",
)
async def get_risk_parameters():
    """
    獲取風險參數

    Returns:
        APIResponse[RiskParameters]: 包含當前風險參數的 API 回應

    Raises:
        HTTPException: 當參數獲取失敗時
    """
    try:
        # 獲取風險參數
        parameters = risk_service.get_risk_parameters()

        if not parameters:
            # 返回預設參數
            parameters = {
                "stop_loss_type": "percent",
                "stop_loss_value": 0.05,
                "take_profit_type": "percent",
                "take_profit_value": 0.1,
                "max_position_size": 0.1,
                "max_portfolio_risk": 0.02,
                "max_daily_loss": 0.05,
                "max_drawdown": 0.15,
                "var_confidence_level": 0.95,
                "var_time_horizon": 1,
                "var_method": "historical",
                "max_correlation": 0.7,
                "correlation_lookback": 60,
                "max_sector_exposure": 0.3,
                "max_single_stock": 0.15,
            }

        response_data = RiskParameters(
            **parameters, updated_at=datetime.now(), updated_by="system"
        )

        return APIResponse(success=True, message="風險參數獲取成功", data=response_data)

    except Exception as e:
        logger.error("獲取風險參數失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取風險參數失敗: {str(e)}",
        ) from e


@router.put(
    "/",
    response_model=APIResponse[RiskParameters],
    responses=COMMON_RESPONSES,
    summary="更新風險參數",
    description="更新現有的風險管理參數配置",
)
async def update_risk_parameters(request: RiskParametersRequest):
    """
    更新風險參數

    Args:
        request: 風險參數更新請求

    Returns:
        APIResponse[RiskParameters]: 包含更新後風險參數的 API 回應

    Raises:
        HTTPException: 當參數更新失敗時
    """
    try:
        # 獲取當前參數
        current_params = risk_service.get_risk_parameters()

        # 更新參數
        updated_params = {
            **current_params,
            "stop_loss_type": request.stop_loss_type,
            "stop_loss_value": request.stop_loss_value,
            "take_profit_type": request.take_profit_type,
            "take_profit_value": request.take_profit_value,
            "max_position_size": request.max_position_size,
            "max_portfolio_risk": request.max_portfolio_risk,
            "max_daily_loss": request.max_daily_loss,
            "max_drawdown": request.max_drawdown,
            "var_confidence_level": request.var_confidence_level,
            "var_time_horizon": request.var_time_horizon,
            "var_method": request.var_method,
            "max_correlation": request.max_correlation,
            "correlation_lookback": request.correlation_lookback,
            "max_sector_exposure": request.max_sector_exposure,
            "max_single_stock": request.max_single_stock,
        }

        # 設定更新後的參數
        success = risk_service.set_risk_parameters(updated_params)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="風險參數更新失敗",
            )

        response_data = RiskParameters(
            **updated_params, updated_at=datetime.now(), updated_by="system"
        )

        return APIResponse(success=True, message="風險參數更新成功", data=response_data)

    except Exception as e:
        logger.error("更新風險參數失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新風險參數失敗: {str(e)}",
        ) from e
