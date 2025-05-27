"""
系統監控 API 路由 - 主路由模組

此模組作為系統監控 API 的主入口，整合各個子模組的路由。
模組化分割完成後，將整合以下子模組：
- system_resources: 系統資源監控 API
- alerts: 警報管理 API
- logs: 日誌管理 API
- health_reports: 健康檢查與報告 API
"""

import logging
from fastapi import APIRouter

# 匯入子模組路由
from src.api.routers.monitoring.system import router as system_router
from src.api.routers.monitoring.alerts import router as alerts_router
from src.api.routers.monitoring.logs import router as logs_router
from src.api.routers.monitoring.reports import router as reports_router

logger = logging.getLogger(__name__)
router = APIRouter()

# 整合子模組路由
router.include_router(
    system_router,
    prefix="/system",
    tags=["系統資源監控"]
)

router.include_router(
    alerts_router,
    prefix="/alerts",
    tags=["警報管理"]
)

router.include_router(
    logs_router,
    prefix="/logs",
    tags=["日誌管理"]
)

router.include_router(
    reports_router,
    prefix="/reports",
    tags=["監控報告"]
)


@router.get("/health")
async def health_check():
    """
    基本健康檢查端點

    Returns:
        dict: 健康狀態資訊
    """
    return {"status": "healthy", "message": "監控系統運行正常"}
