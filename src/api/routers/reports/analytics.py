"""分析報表 API

此模組實現分析報表相關的 API 端點，包括因子分析和歸因分析報表。
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.services.report_service import ReportService
from .models import AnalyticsReportRequest, AnalyticsReport, ReportResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化報表服務
report_service = ReportService()


@router.post(
    "/generate",
    response_model=APIResponse[ReportResponse],
    responses=COMMON_RESPONSES,
    summary="生成分析報表",
    description="生成因子分析和歸因分析報表",
)
async def generate_analytics_report(request: AnalyticsReportRequest):
    """
    生成分析報表

    Args:
        request: 分析報表生成請求

    Returns:
        APIResponse[ReportResponse]: 包含報表生成結果的 API 回應

    Raises:
        HTTPException: 當報表生成失敗時
    """
    try:
        # 生成報表
        report_result = report_service.generate_analytics_report(
            start_date=request.start_date,
            end_date=request.end_date,
            analysis_type=request.analysis_type,
            symbols=request.symbols,
            factors=request.factors,
            include_predictions=request.include_predictions,
            format=request.format,
        )

        if not report_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"分析報表生成失敗: {report_result['message']}",
            )

        response_data = ReportResponse(
            report_id=report_result["report_id"],
            report_type="analytics",
            generated_at=datetime.now(),
            start_date=request.start_date,
            end_date=request.end_date,
            format=request.format,
            file_url=report_result.get("file_url"),
            status="completed",
        )

        return APIResponse(success=True, message="分析報表生成成功", data=response_data)

    except Exception as e:
        logger.error("生成分析報表失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成分析報表失敗: {str(e)}",
        ) from e


@router.get(
    "/factor-analysis",
    response_model=APIResponse[dict],
    responses=COMMON_RESPONSES,
    summary="因子分析",
    description="執行投資組合的因子曝險分析",
)
async def get_factor_analysis(
    start_date: str = Query(..., description="開始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="結束日期 (YYYY-MM-DD)"),
    portfolio_ids: Optional[str] = Query(
        default=None, description="投資組合 ID（多個用逗號分隔）"
    ),
    factors: Optional[str] = Query(
        default=None, description="分析因子（多個用逗號分隔）"
    ),
):
    """
    因子分析

    Args:
        start_date: 開始日期
        end_date: 結束日期
        portfolio_ids: 投資組合 ID 列表
        factors: 分析因子列表

    Returns:
        APIResponse[dict]: 包含因子分析結果的 API 回應

    Raises:
        HTTPException: 當因子分析失敗時
    """
    try:
        # 解析參數
        portfolio_list = None
        if portfolio_ids:
            portfolio_list = [pid.strip() for pid in portfolio_ids.split(",")]

        factor_list = None
        if factors:
            factor_list = [factor.strip() for factor in factors.split(",")]
        else:
            factor_list = [
                "market",
                "size",
                "value",
                "momentum",
                "quality",
                "volatility",
            ]

        # 執行因子分析
        factor_analysis = report_service.get_factor_analysis(
            start_date=start_date,
            end_date=end_date,
            portfolio_ids=portfolio_list,
            factors=factor_list,
        )

        # 模擬因子分析結果
        analysis_result = {
            "analysis_period": f"{start_date} to {end_date}",
            "portfolios_analyzed": portfolio_list or ["all"],
            "factors_analyzed": factor_list,
            "factor_exposures": {
                "market": 1.15,
                "size": -0.25,
                "value": 0.35,
                "momentum": 0.18,
                "quality": 0.42,
                "volatility": -0.15,
            },
            "factor_returns": {
                "market": 0.08,
                "size": -0.02,
                "value": 0.05,
                "momentum": 0.03,
                "quality": 0.06,
                "volatility": -0.01,
            },
            "factor_contributions": {
                "market": 0.092,
                "size": 0.005,
                "value": 0.0175,
                "momentum": 0.0054,
                "quality": 0.0252,
                "volatility": 0.0015,
                "alpha": 0.025,
            },
            "r_squared": 0.85,
            "tracking_error": 0.08,
            "active_risk": 0.12,
            "factor_risk": 0.10,
            "specific_risk": 0.07,
            "risk_decomposition": {
                "systematic_risk": 0.75,
                "idiosyncratic_risk": 0.25,
            },
            "style_analysis": {
                "growth_tilt": 0.65,
                "value_tilt": 0.35,
                "large_cap_bias": 0.78,
                "quality_bias": 0.68,
            },
        }

        return APIResponse(success=True, message="因子分析完成", data=analysis_result)

    except Exception as e:
        logger.error("因子分析失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"因子分析失敗: {str(e)}",
        ) from e


@router.get(
    "/attribution",
    response_model=APIResponse[dict],
    responses=COMMON_RESPONSES,
    summary="績效歸因分析",
    description="執行投資組合的績效歸因分析",
)
async def get_attribution_analysis(
    start_date: str = Query(..., description="開始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="結束日期 (YYYY-MM-DD)"),
    portfolio_ids: Optional[str] = Query(
        default=None, description="投資組合 ID（多個用逗號分隔）"
    ),
    benchmark: str = Query(default="TAIEX", description="基準指數"),
    attribution_method: str = Query(
        default="brinson", description="歸因方法 (brinson/fama_french)"
    ),
):
    """
    績效歸因分析

    Args:
        start_date: 開始日期
        end_date: 結束日期
        portfolio_ids: 投資組合 ID 列表
        benchmark: 基準指數
        attribution_method: 歸因方法

    Returns:
        APIResponse[dict]: 包含績效歸因分析結果的 API 回應

    Raises:
        HTTPException: 當績效歸因分析失敗時
    """
    try:
        # 解析參數
        portfolio_list = None
        if portfolio_ids:
            portfolio_list = [pid.strip() for pid in portfolio_ids.split(",")]

        # 執行績效歸因分析
        attribution_analysis = report_service.get_attribution_analysis(
            start_date=start_date,
            end_date=end_date,
            portfolio_ids=portfolio_list,
            benchmark=benchmark,
            attribution_method=attribution_method,
        )

        # 模擬績效歸因分析結果
        analysis_result = {
            "analysis_period": f"{start_date} to {end_date}",
            "portfolio_return": 0.15,
            "benchmark_return": 0.10,
            "excess_return": 0.05,
            "attribution_method": attribution_method,
            "sector_attribution": {
                "科技": {
                    "portfolio_weight": 0.35,
                    "benchmark_weight": 0.30,
                    "portfolio_return": 0.18,
                    "benchmark_return": 0.15,
                    "allocation_effect": 0.0075,
                    "selection_effect": 0.0105,
                    "interaction_effect": 0.0015,
                    "total_effect": 0.0195,
                },
                "金融": {
                    "portfolio_weight": 0.25,
                    "benchmark_weight": 0.28,
                    "portfolio_return": 0.12,
                    "benchmark_return": 0.08,
                    "allocation_effect": -0.0024,
                    "selection_effect": 0.0112,
                    "interaction_effect": -0.0012,
                    "total_effect": 0.0076,
                },
                "醫療": {
                    "portfolio_weight": 0.15,
                    "benchmark_weight": 0.12,
                    "portfolio_return": 0.20,
                    "benchmark_return": 0.14,
                    "allocation_effect": 0.0042,
                    "selection_effect": 0.0072,
                    "interaction_effect": 0.0018,
                    "total_effect": 0.0132,
                },
            },
            "summary": {
                "total_allocation_effect": 0.0093,
                "total_selection_effect": 0.0289,
                "total_interaction_effect": 0.0021,
                "total_active_return": 0.0403,
                "unexplained_return": 0.0097,
            },
            "factor_attribution": {
                "market_timing": 0.015,
                "security_selection": 0.025,
                "asset_allocation": 0.008,
                "currency_effect": 0.002,
            },
            "risk_attribution": {
                "systematic_risk_contribution": 0.75,
                "idiosyncratic_risk_contribution": 0.25,
                "factor_risk_contributions": {
                    "market": 0.45,
                    "size": 0.08,
                    "value": 0.12,
                    "momentum": 0.06,
                    "quality": 0.04,
                },
            },
        }

        return APIResponse(
            success=True, message="績效歸因分析完成", data=analysis_result
        )

    except Exception as e:
        logger.error("績效歸因分析失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"績效歸因分析失敗: {str(e)}",
        ) from e


@router.get(
    "/correlation",
    response_model=APIResponse[dict],
    responses=COMMON_RESPONSES,
    summary="相關性分析",
    description="執行投資組合的相關性分析",
)
async def get_correlation_analysis(
    start_date: str = Query(..., description="開始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="結束日期 (YYYY-MM-DD)"),
    symbols: Optional[str] = Query(
        default=None, description="股票代碼（多個用逗號分隔）"
    ),
    method: str = Query(default="pearson", description="相關性計算方法"),
    rolling_window: Optional[int] = Query(
        default=None, description="滾動窗口期間（天）"
    ),
):
    """
    相關性分析

    Args:
        start_date: 開始日期
        end_date: 結束日期
        symbols: 股票代碼列表
        method: 相關性計算方法
        rolling_window: 滾動窗口期間

    Returns:
        APIResponse[dict]: 包含相關性分析結果的 API 回應

    Raises:
        HTTPException: 當相關性分析失敗時
    """
    try:
        # 解析參數
        symbol_list = None
        if symbols:
            symbol_list = [symbol.strip() for symbol in symbols.split(",")]

        # 執行相關性分析
        correlation_analysis = report_service.get_correlation_analysis(
            start_date=start_date,
            end_date=end_date,
            symbols=symbol_list,
            method=method,
            rolling_window=rolling_window,
        )

        # 模擬相關性分析結果
        analysis_result = {
            "analysis_period": f"{start_date} to {end_date}",
            "symbols_analyzed": symbol_list or ["portfolio_holdings"],
            "correlation_method": method,
            "rolling_window_days": rolling_window,
            "correlation_matrix": [
                [1.0, 0.75, 0.65, 0.55, 0.45],
                [0.75, 1.0, 0.70, 0.60, 0.50],
                [0.65, 0.70, 1.0, 0.65, 0.55],
                [0.55, 0.60, 0.65, 1.0, 0.60],
                [0.45, 0.50, 0.55, 0.60, 1.0],
            ],
            "correlation_statistics": {
                "average_correlation": 0.62,
                "max_correlation": 0.75,
                "min_correlation": 0.45,
                "correlation_std": 0.08,
            },
            "cluster_analysis": {
                "num_clusters": 3,
                "clusters": {
                    "cluster_1": ["2330.TW", "2454.TW"],
                    "cluster_2": ["2317.TW", "2382.TW"],
                    "cluster_3": ["2891.TW"],
                },
                "silhouette_score": 0.68,
            },
            "diversification_metrics": {
                "diversification_ratio": 0.78,
                "effective_number_of_assets": 12.5,
                "concentration_index": 0.285,
            },
            "time_varying_correlations": {
                "correlation_trend": "increasing",
                "correlation_volatility": 0.15,
                "regime_changes": [
                    {"date": "2024-02-15", "type": "increase"},
                    {"date": "2024-03-20", "type": "decrease"},
                ],
            },
        }

        return APIResponse(success=True, message="相關性分析完成", data=analysis_result)

    except Exception as e:
        logger.error("相關性分析失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"相關性分析失敗: {str(e)}",
        ) from e
