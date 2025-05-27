"""報表查詢系統路由模組

此模組聚合所有報表查詢相關的 API 路由，提供統一的入口點。
"""

import logging
from fastapi import APIRouter

from .performance import router as performance_router
from .portfolio import router as portfolio_router
from .risk import router as risk_router
from .trading import router as trading_router
from .analytics import router as analytics_router

logger = logging.getLogger(__name__)

# 創建主路由器
router = APIRouter(prefix="/reports", tags=["報表查詢"])

# 包含所有子路由
router.include_router(performance_router, prefix="/performance", tags=["績效報表"])
router.include_router(portfolio_router, prefix="/portfolio", tags=["投資組合報表"])
router.include_router(risk_router, prefix="/risk", tags=["風險報表"])
router.include_router(trading_router, prefix="/trading", tags=["交易報表"])
router.include_router(analytics_router, prefix="/analytics", tags=["分析報表"])

# 導出所有模型供外部使用
from .models import (
    ReportRequest,
    PerformanceReportRequest,
    PortfolioReportRequest,
    RiskReportRequest,
    TradingReportRequest,
    AnalyticsReportRequest,
    ReportResponse,
    PerformanceReport,
    PortfolioReport,
    RiskReport,
    TradingReport,
    AnalyticsReport,
)

__all__ = [
    "router",
    "ReportRequest",
    "PerformanceReportRequest",
    "PortfolioReportRequest",
    "RiskReportRequest",
    "TradingReportRequest",
    "AnalyticsReportRequest",
    "ReportResponse",
    "PerformanceReport",
    "PortfolioReport",
    "RiskReport",
    "TradingReport",
    "AnalyticsReport",
]
