"""
報表查詢 API 路由 - 主路由模組

此模組作為報表查詢 API 的主入口，整合各個子模組的路由。
模組化分割完成後，整合以下子模組：
- performance: 績效報表 API
- portfolio: 投資組合報表 API
- risk: 風險報表 API
- trading: 交易報表 API
- analytics: 分析報表 API
"""

import logging
from fastapi import APIRouter

# 匯入子模組路由
from src.api.routers.reports.performance import router as performance_router
from src.api.routers.reports.portfolio import router as portfolio_router
from src.api.routers.reports.risk import router as risk_router
from src.api.routers.reports.trading import router as trading_router
from src.api.routers.reports.analytics import router as analytics_router

logger = logging.getLogger(__name__)
router = APIRouter()

# 整合子模組路由
router.include_router(performance_router, prefix="/performance", tags=["績效報表"])

router.include_router(portfolio_router, prefix="/portfolio", tags=["投資組合報表"])

router.include_router(risk_router, prefix="/risk", tags=["風險報表"])

router.include_router(trading_router, prefix="/trading", tags=["交易報表"])

router.include_router(analytics_router, prefix="/analytics", tags=["分析報表"])


@router.get("/health")
async def health_check():
    """
    報表查詢系統健康檢查端點

    Returns:
        dict: 健康狀態資訊
    """
    return {"status": "healthy", "message": "報表查詢系統運行正常"}


# 原有的請求模型、響應模型和 API 端點已移動到對應的子模組中
# 此檔案現在只作為主路由模組，整合各個子模組的路由
