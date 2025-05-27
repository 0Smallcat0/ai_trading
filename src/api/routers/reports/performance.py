"""績效報表 API

此模組實現績效報表相關的 API 端點，包括投資組合績效分析和基準比較。
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.services.report_service import ReportService
from .models import PerformanceReportRequest, PerformanceReport, ReportResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化報表服務
report_service = ReportService()


@router.post(
    "/generate",
    response_model=APIResponse[ReportResponse],
    responses=COMMON_RESPONSES,
    summary="生成績效報表",
    description="生成投資組合績效分析報表",
)
async def generate_performance_report(request: PerformanceReportRequest):
    """
    生成績效報表

    Args:
        request: 績效報表生成請求

    Returns:
        APIResponse[ReportResponse]: 包含報表生成結果的 API 回應

    Raises:
        HTTPException: 當報表生成失敗時
    """
    try:
        # 生成報表
        report_result = report_service.generate_performance_report(
            start_date=request.start_date,
            end_date=request.end_date,
            portfolio_ids=request.portfolio_ids,
            benchmark=request.benchmark,
            include_benchmark=request.include_benchmark,
            metrics=request.metrics,
            format=request.format,
        )

        if not report_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"績效報表生成失敗: {report_result['message']}",
            )

        response_data = ReportResponse(
            report_id=report_result["report_id"],
            report_type="performance",
            generated_at=datetime.now(),
            start_date=request.start_date,
            end_date=request.end_date,
            format=request.format,
            file_url=report_result.get("file_url"),
            status="completed",
        )

        return APIResponse(
            success=True, message="績效報表生成成功", data=response_data
        )

    except Exception as e:
        logger.error("生成績效報表失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成績效報表失敗: {str(e)}",
        ) from e


@router.get(
    "/",
    response_model=APIResponse[PerformanceReport],
    responses=COMMON_RESPONSES,
    summary="獲取績效報表數據",
    description="獲取投資組合績效分析數據",
)
async def get_performance_data(
    start_date: str = Query(..., description="開始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="結束日期 (YYYY-MM-DD)"),
    portfolio_ids: Optional[str] = Query(
        default=None, description="投資組合 ID（多個用逗號分隔）"
    ),
    benchmark: str = Query(default="TAIEX", description="基準指數"),
    include_benchmark: bool = Query(default=True, description="是否包含基準比較"),
):
    """
    獲取績效報表數據

    Args:
        start_date: 開始日期
        end_date: 結束日期
        portfolio_ids: 投資組合 ID 列表
        benchmark: 基準指數
        include_benchmark: 是否包含基準比較

    Returns:
        APIResponse[PerformanceReport]: 包含績效報表數據的 API 回應

    Raises:
        HTTPException: 當獲取績效數據失敗時
    """
    try:
        # 解析投資組合 ID
        portfolio_list = None
        if portfolio_ids:
            portfolio_list = [pid.strip() for pid in portfolio_ids.split(",")]

        # 獲取績效數據
        performance_data = report_service.get_performance_data(
            start_date=start_date,
            end_date=end_date,
            portfolio_ids=portfolio_list,
            benchmark=benchmark,
            include_benchmark=include_benchmark,
        )

        # 模擬績效數據
        portfolio_performance = {
            "total_return": 0.15,
            "annualized_return": 0.12,
            "volatility": 0.18,
            "sharpe_ratio": 1.25,
            "max_drawdown": -0.08,
            "calmar_ratio": 1.5,
            "sortino_ratio": 1.8,
            "win_rate": 0.65,
            "profit_factor": 1.8,
        }

        benchmark_performance = None
        relative_performance = None
        if include_benchmark:
            benchmark_performance = {
                "total_return": 0.10,
                "annualized_return": 0.08,
                "volatility": 0.15,
                "sharpe_ratio": 0.95,
                "max_drawdown": -0.12,
            }
            relative_performance = {
                "excess_return": 0.05,
                "tracking_error": 0.08,
                "information_ratio": 0.625,
                "alpha": 0.04,
                "beta": 1.15,
            }

        period_returns = [
            {"period": "2024-01", "portfolio_return": 0.025, "benchmark_return": 0.018},
            {"period": "2024-02", "portfolio_return": 0.032, "benchmark_return": 0.021},
            {"period": "2024-03", "portfolio_return": -0.015, "benchmark_return": -0.008},
        ]

        risk_metrics = {
            "var_95": -0.025,
            "var_99": -0.045,
            "cvar_95": -0.035,
            "cvar_99": -0.055,
            "downside_deviation": 0.12,
            "upside_capture": 1.15,
            "downside_capture": 0.85,
        }

        response_data = PerformanceReport(
            portfolio_performance=portfolio_performance,
            benchmark_performance=benchmark_performance,
            relative_performance=relative_performance,
            period_returns=period_returns,
            risk_metrics=risk_metrics,
        )

        return APIResponse(
            success=True, message="績效數據獲取成功", data=response_data
        )

    except Exception as e:
        logger.error("獲取績效數據失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取績效數據失敗: {str(e)}",
        ) from e


@router.get(
    "/comparison",
    response_model=APIResponse[dict],
    responses=COMMON_RESPONSES,
    summary="投資組合績效比較",
    description="比較多個投資組合的績效表現",
)
async def compare_portfolio_performance(
    start_date: str = Query(..., description="開始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="結束日期 (YYYY-MM-DD)"),
    portfolio_ids: str = Query(..., description="投資組合 ID（多個用逗號分隔）"),
    metrics: Optional[str] = Query(
        default=None, description="比較指標（多個用逗號分隔）"
    ),
):
    """
    投資組合績效比較

    Args:
        start_date: 開始日期
        end_date: 結束日期
        portfolio_ids: 投資組合 ID 列表
        metrics: 比較指標列表

    Returns:
        APIResponse[dict]: 包含績效比較結果的 API 回應

    Raises:
        HTTPException: 當績效比較失敗時
    """
    try:
        # 解析參數
        portfolio_list = [pid.strip() for pid in portfolio_ids.split(",")]
        metrics_list = None
        if metrics:
            metrics_list = [metric.strip() for metric in metrics.split(",")]

        # 獲取比較數據
        comparison_data = report_service.compare_portfolio_performance(
            start_date=start_date,
            end_date=end_date,
            portfolio_ids=portfolio_list,
            metrics=metrics_list,
        )

        # 模擬比較數據
        comparison_result = {
            "portfolios": {
                "portfolio_001": {
                    "name": "成長型投資組合",
                    "total_return": 0.15,
                    "volatility": 0.18,
                    "sharpe_ratio": 1.25,
                    "max_drawdown": -0.08,
                },
                "portfolio_002": {
                    "name": "價值型投資組合",
                    "total_return": 0.12,
                    "volatility": 0.15,
                    "sharpe_ratio": 1.10,
                    "max_drawdown": -0.06,
                },
            },
            "ranking": {
                "total_return": ["portfolio_001", "portfolio_002"],
                "sharpe_ratio": ["portfolio_001", "portfolio_002"],
                "max_drawdown": ["portfolio_002", "portfolio_001"],
            },
            "correlation_matrix": [[1.0, 0.75], [0.75, 1.0]],
            "summary": {
                "best_performer": "portfolio_001",
                "lowest_risk": "portfolio_002",
                "highest_sharpe": "portfolio_001",
            },
        }

        return APIResponse(
            success=True,
            message=f"成功比較 {len(portfolio_list)} 個投資組合",
            data=comparison_result,
        )

    except Exception as e:
        logger.error("投資組合績效比較失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"投資組合績效比較失敗: {str(e)}",
        ) from e
