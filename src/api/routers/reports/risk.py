"""風險報表 API

此模組實現風險報表相關的 API 端點，包括風險分析和壓力測試報表。
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.services.report_service import ReportService
from .models import RiskReportRequest, RiskReport, ReportResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化報表服務
report_service = ReportService()


@router.post(
    "/generate",
    response_model=APIResponse[ReportResponse],
    responses=COMMON_RESPONSES,
    summary="生成風險報表",
    description="生成投資組合風險分析報表",
)
async def generate_risk_report(request: RiskReportRequest):
    """
    生成風險報表

    Args:
        request: 風險報表生成請求

    Returns:
        APIResponse[ReportResponse]: 包含報表生成結果的 API 回應

    Raises:
        HTTPException: 當報表生成失敗時
    """
    try:
        # 生成報表
        report_result = report_service.generate_risk_report(
            start_date=request.start_date,
            end_date=request.end_date,
            portfolio_ids=request.portfolio_ids,
            risk_metrics=request.risk_metrics,
            confidence_levels=request.confidence_levels,
            include_stress_test=request.include_stress_test,
            format=request.format,
        )

        if not report_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"風險報表生成失敗: {report_result['message']}",
            )

        response_data = ReportResponse(
            report_id=report_result["report_id"],
            report_type="risk",
            generated_at=datetime.now(),
            start_date=request.start_date,
            end_date=request.end_date,
            format=request.format,
            file_url=report_result.get("file_url"),
            status="completed",
        )

        return APIResponse(success=True, message="風險報表生成成功", data=response_data)

    except Exception as e:
        logger.error("生成風險報表失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成風險報表失敗: {str(e)}",
        ) from e


@router.get(
    "/",
    response_model=APIResponse[RiskReport],
    responses=COMMON_RESPONSES,
    summary="獲取風險報表數據",
    description="獲取投資組合風險分析數據",
)
async def get_risk_data(
    start_date: str = Query(..., description="開始日期 (YYYY-MM-DD)"),
    end_date: str = Query(..., description="結束日期 (YYYY-MM-DD)"),
    portfolio_ids: Optional[str] = Query(
        default=None, description="投資組合 ID（多個用逗號分隔）"
    ),
    confidence_levels: str = Query(
        default="0.95,0.99", description="信心水準（多個用逗號分隔）"
    ),
    include_stress_test: bool = Query(default=False, description="是否包含壓力測試"),
):
    """
    獲取風險報表數據

    Args:
        start_date: 開始日期
        end_date: 結束日期
        portfolio_ids: 投資組合 ID 列表
        confidence_levels: 信心水準列表
        include_stress_test: 是否包含壓力測試

    Returns:
        APIResponse[RiskReport]: 包含風險報表數據的 API 回應

    Raises:
        HTTPException: 當獲取風險數據失敗時
    """
    try:
        # 解析參數
        portfolio_list = None
        if portfolio_ids:
            portfolio_list = [pid.strip() for pid in portfolio_ids.split(",")]

        confidence_list = [float(cl.strip()) for cl in confidence_levels.split(",")]

        # 獲取風險數據
        risk_data = report_service.get_risk_data(
            start_date=start_date,
            end_date=end_date,
            portfolio_ids=portfolio_list,
            confidence_levels=confidence_list,
            include_stress_test=include_stress_test,
        )

        # 模擬風險數據
        risk_summary = {
            "total_portfolio_value": 1000000.0,
            "volatility": 0.18,
            "beta": 1.15,
            "correlation_with_market": 0.85,
            "max_drawdown": -0.08,
            "current_drawdown": -0.02,
            "risk_score": 7.5,
        }

        var_analysis = {
            "var_95": -25000.0,
            "var_99": -45000.0,
            "cvar_95": -35000.0,
            "cvar_99": -55000.0,
            "var_95_percent": -0.025,
            "var_99_percent": -0.045,
            "cvar_95_percent": -0.035,
            "cvar_99_percent": -0.055,
        }

        stress_test_results = None
        if include_stress_test:
            stress_test_results = {
                "scenarios": {
                    "market_crash_2008": {"portfolio_loss": -0.35, "var_breach": True},
                    "covid_crash_2020": {"portfolio_loss": -0.28, "var_breach": True},
                    "interest_rate_shock": {"portfolio_loss": -0.15, "var_breach": False},
                    "sector_rotation": {"portfolio_loss": -0.12, "var_breach": False},
                },
                "worst_case_scenario": "market_crash_2008",
                "probability_of_var_breach": 0.15,
                "expected_shortfall": -0.42,
            }

        concentration_analysis = {
            "sector_concentration": {
                "科技": 0.35,
                "金融": 0.25,
                "醫療": 0.15,
                "消費": 0.15,
                "能源": 0.10,
            },
            "top_holdings_concentration": {
                "top_5": 0.65,
                "top_10": 0.85,
                "top_20": 0.95,
            },
            "herfindahl_index": 0.285,
            "effective_positions": 12.5,
            "concentration_risk_score": 6.8,
        }

        correlation_matrix = [
            [1.0, 0.75, 0.65, 0.55, 0.45],
            [0.75, 1.0, 0.70, 0.60, 0.50],
            [0.65, 0.70, 1.0, 0.65, 0.55],
            [0.55, 0.60, 0.65, 1.0, 0.60],
            [0.45, 0.50, 0.55, 0.60, 1.0],
        ]

        risk_decomposition = {
            "systematic_risk": 0.65,
            "idiosyncratic_risk": 0.35,
            "factor_contributions": {
                "market_factor": 0.45,
                "size_factor": 0.15,
                "value_factor": 0.10,
                "momentum_factor": 0.08,
                "quality_factor": 0.12,
                "residual": 0.10,
            },
            "sector_contributions": {
                "科技": 0.42,
                "金融": 0.28,
                "醫療": 0.12,
                "消費": 0.13,
                "能源": 0.05,
            },
        }

        response_data = RiskReport(
            risk_summary=risk_summary,
            var_analysis=var_analysis,
            stress_test_results=stress_test_results,
            concentration_analysis=concentration_analysis,
            correlation_matrix=correlation_matrix,
            risk_decomposition=risk_decomposition,
        )

        return APIResponse(success=True, message="風險數據獲取成功", data=response_data)

    except Exception as e:
        logger.error("獲取風險數據失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取風險數據失敗: {str(e)}",
        ) from e


@router.get(
    "/stress-test",
    response_model=APIResponse[dict],
    responses=COMMON_RESPONSES,
    summary="執行壓力測試",
    description="對投資組合執行各種壓力測試情境",
)
async def run_stress_test(
    portfolio_ids: Optional[str] = Query(
        default=None, description="投資組合 ID（多個用逗號分隔）"
    ),
    scenarios: Optional[str] = Query(
        default=None, description="測試情境（多個用逗號分隔）"
    ),
    custom_shocks: Optional[str] = Query(
        default=None, description="自定義衝擊（JSON 格式）"
    ),
):
    """
    執行壓力測試

    Args:
        portfolio_ids: 投資組合 ID 列表
        scenarios: 測試情境列表
        custom_shocks: 自定義衝擊參數

    Returns:
        APIResponse[dict]: 包含壓力測試結果的 API 回應

    Raises:
        HTTPException: 當壓力測試失敗時
    """
    try:
        # 解析參數
        portfolio_list = None
        if portfolio_ids:
            portfolio_list = [pid.strip() for pid in portfolio_ids.split(",")]

        scenario_list = None
        if scenarios:
            scenario_list = [scenario.strip() for scenario in scenarios.split(",")]

        # 執行壓力測試
        stress_test_result = report_service.run_stress_test(
            portfolio_ids=portfolio_list,
            scenarios=scenario_list,
            custom_shocks=custom_shocks,
        )

        # 模擬壓力測試結果
        test_results = {
            "test_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "portfolios_tested": portfolio_list or ["all"],
            "scenarios_tested": scenario_list
            or [
                "market_crash_2008",
                "covid_crash_2020",
                "interest_rate_shock",
                "sector_rotation",
            ],
            "results": {
                "market_crash_2008": {
                    "portfolio_loss_percent": -35.2,
                    "portfolio_loss_amount": -352000.0,
                    "var_breach": True,
                    "recovery_time_days": 180,
                    "worst_position": "2330.TW",
                    "worst_position_loss": -45.8,
                },
                "covid_crash_2020": {
                    "portfolio_loss_percent": -28.5,
                    "portfolio_loss_amount": -285000.0,
                    "var_breach": True,
                    "recovery_time_days": 120,
                    "worst_position": "2317.TW",
                    "worst_position_loss": -38.2,
                },
                "interest_rate_shock": {
                    "portfolio_loss_percent": -15.3,
                    "portfolio_loss_amount": -153000.0,
                    "var_breach": False,
                    "recovery_time_days": 60,
                    "worst_position": "金融股",
                    "worst_position_loss": -25.1,
                },
            },
            "summary": {
                "worst_scenario": "market_crash_2008",
                "average_loss": -26.3,
                "scenarios_breaching_var": 2,
                "estimated_recovery_time": 120,
                "risk_adjusted_return": -0.85,
            },
            "recommendations": [
                "考慮增加防禦性資產配置",
                "降低科技股集中度",
                "增加對沖工具使用",
                "設定更嚴格的停損機制",
            ],
        }

        return APIResponse(
            success=True, message="壓力測試執行成功", data=test_results
        )

    except Exception as e:
        logger.error("執行壓力測試失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"執行壓力測試失敗: {str(e)}",
        ) from e
