"""風險指標管理 API

此模組實現風險指標管理相關的 API 端點，包括風險指標計算和查詢。
"""

import logging
from datetime import datetime
from typing import Dict, List, Any

from fastapi import APIRouter, HTTPException, Query, Path, status

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.core.risk_management_service import RiskManagementService
from .models import RiskMetrics

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化風險管理服務
risk_service = RiskManagementService()


@router.get(
    "/",
    response_model=APIResponse[RiskMetrics],
    responses=COMMON_RESPONSES,
    summary="獲取風險指標",
    description="獲取整體投資組合的風險指標",
)
async def get_risk_metrics(
    lookback_days: int = Query(default=252, ge=30, le=1000, description="回看天數")
):
    """
    獲取風險指標

    Args:
        lookback_days: 回看天數，用於計算風險指標

    Returns:
        APIResponse[RiskMetrics]: 包含風險指標的 API 回應

    Raises:
        HTTPException: 當獲取風險指標失敗時
    """
    try:
        # 計算風險指標
        calculated_metrics = risk_service.calculate_risk_metrics(
            symbol=None, lookback_days=lookback_days  # 整體投資組合
        )

        # 獲取投資組合基本信息（模擬數據）
        portfolio_info = {
            "portfolio_value": 1000000.0,
            "cash_amount": 150000.0,
            "invested_amount": 850000.0,
            "leverage_ratio": 1.0,
            "daily_pnl": 2500.0,
            "daily_pnl_percent": 0.25,
            "total_return": 0.15,
            "annualized_return": 0.12,
        }

        # 模擬集中度和相關性數據
        sector_exposure = {
            "科技": 0.35,
            "金融": 0.25,
            "醫療": 0.15,
            "消費": 0.15,
            "能源": 0.10,
        }

        top_holdings = [
            {"symbol": "2330.TW", "name": "台積電", "weight": 0.15, "value": 150000},
            {"symbol": "2317.TW", "name": "鴻海", "weight": 0.12, "value": 120000},
            {"symbol": "2454.TW", "name": "聯發科", "weight": 0.10, "value": 100000},
        ]

        # 合併所有指標
        response_data = RiskMetrics(
            **portfolio_info,
            volatility=calculated_metrics.get("volatility", 0.15),
            sharpe_ratio=calculated_metrics.get("sharpe_ratio", 1.2),
            max_drawdown=calculated_metrics.get("max_drawdown", -0.08),
            current_drawdown=calculated_metrics.get("current_drawdown", -0.02),
            var_95=calculated_metrics.get("var_95", -0.025),
            var_99=calculated_metrics.get("var_99", -0.045),
            cvar_95=calculated_metrics.get("cvar_95", -0.035),
            cvar_99=calculated_metrics.get("cvar_99", -0.055),
            concentration_risk=0.35,  # 最大行業曝險
            sector_exposure=sector_exposure,
            top_holdings=top_holdings,
            avg_correlation=0.45,
            max_correlation=0.78,
            correlation_risk_score=6.5,
            calculated_at=datetime.now(),
        )

        return APIResponse(success=True, message="風險指標獲取成功", data=response_data)

    except Exception as e:
        logger.error("獲取風險指標失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取風險指標失敗: {str(e)}",
        ) from e


@router.get(
    "/portfolio/{portfolio_id}",
    response_model=APIResponse[RiskMetrics],
    responses=COMMON_RESPONSES,
    summary="獲取投資組合風險指標",
    description="獲取特定投資組合的風險指標",
)
async def get_portfolio_risk_metrics(
    portfolio_id: str = Path(..., description="投資組合 ID"),
    lookback_days: int = Query(default=252, ge=30, le=1000, description="回看天數"),
):
    """
    獲取投資組合風險指標

    Args:
        portfolio_id: 投資組合 ID
        lookback_days: 回看天數，用於計算風險指標

    Returns:
        APIResponse[RiskMetrics]: 包含投資組合風險指標的 API 回應

    Raises:
        HTTPException: 當獲取風險指標失敗時
    """
    try:
        # 檢查投資組合是否存在（這裡應該調用投資組合服務）
        # portfolio = portfolio_service.get_portfolio(portfolio_id)
        # if not portfolio:
        #     raise HTTPException(status_code=404, detail="投資組合不存在")

        # 計算特定投資組合的風險指標
        calculated_metrics = risk_service.calculate_risk_metrics(
            symbol=None, lookback_days=lookback_days  # 可以擴展為特定投資組合
        )

        # 模擬投資組合特定數據
        portfolio_info = {
            "portfolio_value": 500000.0,
            "cash_amount": 75000.0,
            "invested_amount": 425000.0,
            "leverage_ratio": 1.0,
            "daily_pnl": 1250.0,
            "daily_pnl_percent": 0.25,
            "total_return": 0.12,
            "annualized_return": 0.10,
        }

        sector_exposure = {
            "科技": 0.40,
            "金融": 0.30,
            "醫療": 0.20,
            "消費": 0.10,
        }

        top_holdings = [
            {"symbol": "2330.TW", "name": "台積電", "weight": 0.20, "value": 100000},
            {"symbol": "2317.TW", "name": "鴻海", "weight": 0.15, "value": 75000},
        ]

        response_data = RiskMetrics(
            **portfolio_info,
            volatility=calculated_metrics.get("volatility", 0.18),
            sharpe_ratio=calculated_metrics.get("sharpe_ratio", 1.0),
            max_drawdown=calculated_metrics.get("max_drawdown", -0.10),
            current_drawdown=calculated_metrics.get("current_drawdown", -0.03),
            var_95=calculated_metrics.get("var_95", -0.030),
            var_99=calculated_metrics.get("var_99", -0.050),
            cvar_95=calculated_metrics.get("cvar_95", -0.040),
            cvar_99=calculated_metrics.get("cvar_99", -0.060),
            concentration_risk=0.40,
            sector_exposure=sector_exposure,
            top_holdings=top_holdings,
            avg_correlation=0.50,
            max_correlation=0.80,
            correlation_risk_score=7.0,
            calculated_at=datetime.now(),
        )

        return APIResponse(
            success=True,
            message=f"投資組合 {portfolio_id} 風險指標獲取成功",
            data=response_data,
        )

    except Exception as e:
        logger.error("獲取投資組合風險指標失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取投資組合風險指標失敗: {str(e)}",
        ) from e


@router.get(
    "/symbol/{symbol}",
    response_model=APIResponse[Dict[str, Any]],
    responses=COMMON_RESPONSES,
    summary="獲取單一股票風險指標",
    description="獲取特定股票的風險指標",
)
async def get_symbol_risk_metrics(
    symbol: str = Path(..., description="股票代碼"),
    lookback_days: int = Query(default=252, ge=30, le=1000, description="回看天數"),
):
    """
    獲取單一股票風險指標

    Args:
        symbol: 股票代碼
        lookback_days: 回看天數，用於計算風險指標

    Returns:
        APIResponse[Dict[str, Any]]: 包含股票風險指標的 API 回應

    Raises:
        HTTPException: 當獲取風險指標失敗時
    """
    try:
        # 計算特定股票的風險指標
        calculated_metrics = risk_service.calculate_risk_metrics(
            symbol=symbol, lookback_days=lookback_days
        )

        # 模擬股票特定風險指標
        symbol_metrics = {
            "symbol": symbol,
            "volatility": calculated_metrics.get("volatility", 0.25),
            "beta": calculated_metrics.get("beta", 1.2),
            "var_95": calculated_metrics.get("var_95", -0.035),
            "var_99": calculated_metrics.get("var_99", -0.055),
            "max_drawdown": calculated_metrics.get("max_drawdown", -0.15),
            "correlation_with_market": calculated_metrics.get("correlation", 0.75),
            "liquidity_risk": calculated_metrics.get("liquidity_risk", 0.15),
            "calculated_at": datetime.now(),
        }

        return APIResponse(
            success=True,
            message=f"股票 {symbol} 風險指標獲取成功",
            data=symbol_metrics,
        )

    except Exception as e:
        logger.error("獲取股票風險指標失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取股票風險指標失敗: {str(e)}",
        ) from e
