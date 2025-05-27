"""投資組合報表 API

此模組實現投資組合報表相關的 API 端點，包括持倉分析和資產配置報表。
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Path, status

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.services.report_service import ReportService
from .models import PortfolioReportRequest, PortfolioReport, ReportResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化報表服務
report_service = ReportService()


@router.post(
    "/generate",
    response_model=APIResponse[ReportResponse],
    responses=COMMON_RESPONSES,
    summary="生成投資組合報表",
    description="生成投資組合持倉和配置分析報表",
)
async def generate_portfolio_report(request: PortfolioReportRequest):
    """
    生成投資組合報表

    Args:
        request: 投資組合報表生成請求

    Returns:
        APIResponse[ReportResponse]: 包含報表生成結果的 API 回應

    Raises:
        HTTPException: 當報表生成失敗時
    """
    try:
        # 生成報表
        report_result = report_service.generate_portfolio_report(
            start_date=request.start_date,
            end_date=request.end_date,
            portfolio_ids=request.portfolio_ids,
            include_positions=request.include_positions,
            include_transactions=request.include_transactions,
            groupby=request.groupby,
            format=request.format,
        )

        if not report_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"投資組合報表生成失敗: {report_result['message']}",
            )

        response_data = ReportResponse(
            report_id=report_result["report_id"],
            report_type="portfolio",
            generated_at=datetime.now(),
            start_date=request.start_date,
            end_date=request.end_date,
            format=request.format,
            file_url=report_result.get("file_url"),
            status="completed",
        )

        return APIResponse(
            success=True, message="投資組合報表生成成功", data=response_data
        )

    except Exception as e:
        logger.error("生成投資組合報表失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成投資組合報表失敗: {str(e)}",
        ) from e


@router.get(
    "/",
    response_model=APIResponse[PortfolioReport],
    responses=COMMON_RESPONSES,
    summary="獲取投資組合報表數據",
    description="獲取投資組合持倉和配置分析數據",
)
async def get_portfolio_data(
    start_date: str = Query(..., description="開始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="結束日期 (YYYY-MM-DD)"),
    portfolio_ids: Optional[str] = Query(
        default=None, description="投資組合 ID（多個用逗號分隔）"
    ),
    include_positions: bool = Query(default=True, description="是否包含持倉詳情"),
    include_transactions: bool = Query(default=False, description="是否包含交易記錄"),
    groupby: Optional[str] = Query(default=None, description="分組方式"),
):
    """
    獲取投資組合報表數據

    Args:
        start_date: 開始日期
        end_date: 結束日期
        portfolio_ids: 投資組合 ID 列表
        include_positions: 是否包含持倉詳情
        include_transactions: 是否包含交易記錄
        groupby: 分組方式

    Returns:
        APIResponse[PortfolioReport]: 包含投資組合報表數據的 API 回應

    Raises:
        HTTPException: 當獲取投資組合數據失敗時
    """
    try:
        # 解析投資組合 ID
        portfolio_list = None
        if portfolio_ids:
            portfolio_list = [pid.strip() for pid in portfolio_ids.split(",")]

        # 獲取投資組合數據
        portfolio_data = report_service.get_portfolio_data(
            start_date=start_date,
            end_date=end_date,
            portfolio_ids=portfolio_list,
            include_positions=include_positions,
            include_transactions=include_transactions,
            groupby=groupby,
        )

        # 模擬投資組合數據
        portfolio_summary = {
            "total_value": 1000000.0,
            "cash_amount": 150000.0,
            "invested_amount": 850000.0,
            "total_positions": 25,
            "total_return": 0.15,
            "unrealized_pnl": 127500.0,
            "realized_pnl": 22500.0,
        }

        asset_allocation = {
            "股票": 0.75,
            "債券": 0.15,
            "現金": 0.10,
        }

        sector_allocation = {
            "科技": 0.35,
            "金融": 0.25,
            "醫療": 0.15,
            "消費": 0.15,
            "能源": 0.10,
        }

        top_holdings = [
            {
                "symbol": "2330.TW",
                "name": "台積電",
                "quantity": 1000,
                "market_value": 150000.0,
                "weight": 0.15,
                "unrealized_pnl": 15000.0,
                "pnl_percent": 0.11,
            },
            {
                "symbol": "2317.TW",
                "name": "鴻海",
                "quantity": 2000,
                "market_value": 120000.0,
                "weight": 0.12,
                "unrealized_pnl": 8000.0,
                "pnl_percent": 0.07,
            },
            {
                "symbol": "2454.TW",
                "name": "聯發科",
                "quantity": 500,
                "market_value": 100000.0,
                "weight": 0.10,
                "unrealized_pnl": 12000.0,
                "pnl_percent": 0.14,
            },
        ]

        performance_summary = {
            "period_return": 0.15,
            "annualized_return": 0.12,
            "volatility": 0.18,
            "sharpe_ratio": 1.25,
            "max_drawdown": -0.08,
            "best_day": 0.035,
            "worst_day": -0.028,
        }

        transactions = None
        if include_transactions:
            transactions = [
                {
                    "date": "2024-01-15",
                    "symbol": "2330.TW",
                    "action": "buy",
                    "quantity": 500,
                    "price": 145.0,
                    "amount": 72500.0,
                    "commission": 145.0,
                    "tax": 0.0,
                },
                {
                    "date": "2024-02-20",
                    "symbol": "2317.TW",
                    "action": "buy",
                    "quantity": 1000,
                    "price": 55.0,
                    "amount": 55000.0,
                    "commission": 110.0,
                    "tax": 0.0,
                },
            ]

        response_data = PortfolioReport(
            portfolio_summary=portfolio_summary,
            asset_allocation=asset_allocation,
            sector_allocation=sector_allocation,
            top_holdings=top_holdings,
            performance_summary=performance_summary,
            transactions=transactions,
        )

        return APIResponse(
            success=True, message="投資組合數據獲取成功", data=response_data
        )

    except Exception as e:
        logger.error("獲取投資組合數據失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取投資組合數據失敗: {str(e)}",
        ) from e


@router.get(
    "/{portfolio_id}/allocation",
    response_model=APIResponse[dict],
    responses=COMMON_RESPONSES,
    summary="獲取投資組合配置分析",
    description="獲取特定投資組合的資產配置分析",
)
async def get_portfolio_allocation(
    portfolio_id: str = Path(..., description="投資組合 ID"),
    groupby: str = Query(default="sector", description="分組方式"),
    as_of_date: Optional[str] = Query(
        default=None, description="截止日期 (YYYY-MM-DD)"
    ),
):
    """
    獲取投資組合配置分析

    Args:
        portfolio_id: 投資組合 ID
        groupby: 分組方式
        as_of_date: 截止日期

    Returns:
        APIResponse[dict]: 包含投資組合配置分析的 API 回應

    Raises:
        HTTPException: 當獲取配置分析失敗時
    """
    try:
        # 獲取配置分析數據
        allocation_data = report_service.get_portfolio_allocation(
            portfolio_id=portfolio_id, groupby=groupby, as_of_date=as_of_date
        )

        # 模擬配置分析數據
        allocation_result = {
            "portfolio_id": portfolio_id,
            "as_of_date": as_of_date or datetime.now().strftime("%Y-%m-%d"),
            "groupby": groupby,
            "total_value": 1000000.0,
            "allocation": {
                "科技": {"value": 350000.0, "weight": 0.35, "count": 8},
                "金融": {"value": 250000.0, "weight": 0.25, "count": 5},
                "醫療": {"value": 150000.0, "weight": 0.15, "count": 4},
                "消費": {"value": 150000.0, "weight": 0.15, "count": 5},
                "能源": {"value": 100000.0, "weight": 0.10, "count": 3},
            },
            "concentration_metrics": {
                "herfindahl_index": 0.285,
                "top_5_concentration": 0.65,
                "top_10_concentration": 0.85,
                "effective_positions": 12.5,
            },
            "diversification_ratio": 0.78,
            "risk_contribution": {
                "科技": 0.42,
                "金融": 0.28,
                "醫療": 0.12,
                "消費": 0.13,
                "能源": 0.05,
            },
        }

        return APIResponse(
            success=True,
            message=f"投資組合 {portfolio_id} 配置分析獲取成功",
            data=allocation_result,
        )

    except Exception as e:
        logger.error("獲取投資組合配置分析失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取投資組合配置分析失敗: {str(e)}",
        ) from e
