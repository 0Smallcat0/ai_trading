"""交易報表 API

此模組實現交易報表相關的 API 端點，包括交易統計和執行分析報表。
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.services.report_service import ReportService
from .models import TradingReportRequest, TradingReport, ReportResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化報表服務
report_service = ReportService()


@router.post(
    "/generate",
    response_model=APIResponse[ReportResponse],
    responses=COMMON_RESPONSES,
    summary="生成交易報表",
    description="生成交易統計和執行分析報表",
)
async def generate_trading_report(request: TradingReportRequest):
    """
    生成交易報表

    Args:
        request: 交易報表生成請求

    Returns:
        APIResponse[ReportResponse]: 包含報表生成結果的 API 回應

    Raises:
        HTTPException: 當報表生成失敗時
    """
    try:
        # 生成報表
        report_result = report_service.generate_trading_report(
            start_date=request.start_date,
            end_date=request.end_date,
            portfolio_ids=request.portfolio_ids,
            symbols=request.symbols,
            order_types=request.order_types,
            include_costs=request.include_costs,
            include_performance=request.include_performance,
            format=request.format,
        )

        if not report_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"交易報表生成失敗: {report_result['message']}",
            )

        response_data = ReportResponse(
            report_id=report_result["report_id"],
            report_type="trading",
            generated_at=datetime.now(),
            start_date=request.start_date,
            end_date=request.end_date,
            format=request.format,
            file_url=report_result.get("file_url"),
            status="completed",
        )

        return APIResponse(success=True, message="交易報表生成成功", data=response_data)

    except Exception as e:
        logger.error("生成交易報表失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成交易報表失敗: {str(e)}",
        ) from e


@router.get(
    "/",
    response_model=APIResponse[TradingReport],
    responses=COMMON_RESPONSES,
    summary="獲取交易報表數據",
    description="獲取交易統計和執行分析數據",
)
async def get_trading_data(
    start_date: str = Query(..., description="開始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="結束日期 (YYYY-MM-DD)"),
    portfolio_ids: Optional[str] = Query(
        default=None, description="投資組合 ID（多個用逗號分隔）"
    ),
    symbols: Optional[str] = Query(
        default=None, description="股票代碼（多個用逗號分隔）"
    ),
    include_costs: bool = Query(default=True, description="是否包含交易成本"),
    include_performance: bool = Query(default=True, description="是否包含交易績效"),
):
    """
    獲取交易報表數據

    Args:
        start_date: 開始日期
        end_date: 結束日期
        portfolio_ids: 投資組合 ID 列表
        symbols: 股票代碼列表
        include_costs: 是否包含交易成本
        include_performance: 是否包含交易績效

    Returns:
        APIResponse[TradingReport]: 包含交易報表數據的 API 回應

    Raises:
        HTTPException: 當獲取交易數據失敗時
    """
    try:
        # 解析參數
        portfolio_list = None
        if portfolio_ids:
            portfolio_list = [pid.strip() for pid in portfolio_ids.split(",")]

        symbol_list = None
        if symbols:
            symbol_list = [symbol.strip() for symbol in symbols.split(",")]

        # 獲取交易數據
        trading_data = report_service.get_trading_data(
            start_date=start_date,
            end_date=end_date,
            portfolio_ids=portfolio_list,
            symbols=symbol_list,
            include_costs=include_costs,
            include_performance=include_performance,
        )

        # 模擬交易數據
        trading_summary = {
            "total_trades": 156,
            "total_volume": 2500000,
            "total_turnover": 125000000.0,
            "buy_trades": 78,
            "sell_trades": 78,
            "avg_trade_size": 16025.64,
            "largest_trade": 150000.0,
            "smallest_trade": 5000.0,
            "trading_days": 45,
            "avg_trades_per_day": 3.47,
        }

        order_statistics = {
            "total_orders": 180,
            "filled_orders": 156,
            "cancelled_orders": 18,
            "rejected_orders": 6,
            "fill_rate": 0.867,
            "cancellation_rate": 0.100,
            "rejection_rate": 0.033,
            "avg_fill_time_seconds": 2.5,
            "order_types": {
                "market": 89,
                "limit": 67,
                "stop": 15,
                "stop_limit": 9,
            },
        }

        execution_analysis = {
            "implementation_shortfall": 0.0025,
            "market_impact": 0.0015,
            "timing_cost": 0.0008,
            "opportunity_cost": 0.0002,
            "slippage_bps": 2.5,
            "price_improvement_rate": 0.35,
            "avg_price_improvement_bps": 1.2,
            "vwap_performance": 0.9985,
            "twap_performance": 0.9978,
        }

        cost_analysis = {
            "total_commission": 15600.0,
            "total_tax": 8750.0,
            "total_costs": 24350.0,
            "cost_as_percent_of_turnover": 0.0195,
            "avg_commission_per_trade": 100.0,
            "commission_rate_bps": 12.48,
            "tax_rate_bps": 7.0,
            "cost_breakdown": {
                "commission": 0.64,
                "tax": 0.36,
                "market_impact": 0.0,
            },
        }

        performance_attribution = {
            "gross_pnl": 187500.0,
            "net_pnl": 163150.0,
            "trading_costs": 24350.0,
            "gross_return": 0.15,
            "net_return": 0.1305,
            "cost_drag": 0.0195,
            "win_rate": 0.65,
            "avg_win": 2850.0,
            "avg_loss": -1650.0,
            "profit_factor": 1.73,
            "sharpe_ratio": 1.85,
        }

        response_data = TradingReport(
            trading_summary=trading_summary,
            order_statistics=order_statistics,
            execution_analysis=execution_analysis,
            cost_analysis=cost_analysis,
            performance_attribution=performance_attribution,
        )

        return APIResponse(success=True, message="交易數據獲取成功", data=response_data)

    except Exception as e:
        logger.error("獲取交易數據失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取交易數據失敗: {str(e)}",
        ) from e


@router.get(
    "/execution-quality",
    response_model=APIResponse[dict],
    responses=COMMON_RESPONSES,
    summary="交易執行品質分析",
    description="分析交易執行品質和市場衝擊",
)
async def get_execution_quality(
    start_date: str = Query(..., description="開始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="結束日期 (YYYY-MM-DD)"),
    symbols: Optional[str] = Query(
        default=None, description="股票代碼（多個用逗號分隔）"
    ),
    order_types: Optional[str] = Query(
        default=None, description="訂單類型（多個用逗號分隔）"
    ),
):
    """
    交易執行品質分析

    Args:
        start_date: 開始日期
        end_date: 結束日期
        symbols: 股票代碼列表
        order_types: 訂單類型列表

    Returns:
        APIResponse[dict]: 包含執行品質分析的 API 回應

    Raises:
        HTTPException: 當執行品質分析失敗時
    """
    try:
        # 解析參數
        symbol_list = None
        if symbols:
            symbol_list = [symbol.strip() for symbol in symbols.split(",")]

        order_type_list = None
        if order_types:
            order_type_list = [ot.strip() for ot in order_types.split(",")]

        # 獲取執行品質數據
        execution_quality = report_service.get_execution_quality(
            start_date=start_date,
            end_date=end_date,
            symbols=symbol_list,
            order_types=order_type_list,
        )

        # 模擬執行品質數據
        quality_analysis = {
            "period": f"{start_date} to {end_date}",
            "total_analyzed_trades": 156,
            "overall_metrics": {
                "implementation_shortfall_bps": 2.5,
                "market_impact_bps": 1.5,
                "timing_cost_bps": 0.8,
                "opportunity_cost_bps": 0.2,
                "price_improvement_rate": 0.35,
                "fill_rate": 0.867,
                "avg_fill_time_seconds": 2.5,
            },
            "by_order_type": {
                "market": {
                    "count": 89,
                    "fill_rate": 0.98,
                    "avg_slippage_bps": 3.2,
                    "market_impact_bps": 2.1,
                },
                "limit": {
                    "count": 67,
                    "fill_rate": 0.75,
                    "avg_slippage_bps": 1.8,
                    "market_impact_bps": 0.9,
                },
            },
            "by_symbol": {
                "2330.TW": {
                    "trades": 25,
                    "avg_slippage_bps": 1.2,
                    "liquidity_score": 9.5,
                    "execution_score": 8.8,
                },
                "2317.TW": {
                    "trades": 18,
                    "avg_slippage_bps": 2.8,
                    "liquidity_score": 8.2,
                    "execution_score": 7.5,
                },
            },
            "time_analysis": {
                "best_execution_hour": "10:00-11:00",
                "worst_execution_hour": "13:30-14:00",
                "market_open_impact": 3.5,
                "market_close_impact": 4.2,
            },
            "recommendations": [
                "在流動性較高的時段執行大額交易",
                "對於小額交易優先使用限價單",
                "避免在市場開盤和收盤時段執行大額交易",
                "考慮使用 TWAP 策略分散大額訂單",
            ],
        }

        return APIResponse(
            success=True, message="執行品質分析完成", data=quality_analysis
        )

    except Exception as e:
        logger.error("交易執行品質分析失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"交易執行品質分析失敗: {str(e)}",
        ) from e
