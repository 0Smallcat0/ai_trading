"""監控系統路由模組

此模組聚合所有監控相關的 API 路由，提供統一的入口點。
"""

import logging
from fastapi import APIRouter

from .system import router as system_router
from .alerts import router as alerts_router
from .logs import router as logs_router
from .reports import router as reports_router

logger = logging.getLogger(__name__)

# 創建主路由器
router = APIRouter(prefix="/monitoring", tags=["監控系統"])

# 包含所有子路由
router.include_router(system_router, prefix="/system", tags=["系統監控"])
router.include_router(alerts_router, prefix="/alerts", tags=["警報管理"])
router.include_router(logs_router, prefix="/logs", tags=["日誌管理"])
router.include_router(reports_router, prefix="/reports", tags=["監控報表"])

# 導出所有模型供外部使用
from .models import (
    AlertRuleRequest,
    LogQueryRequest,
    AlertUpdateRequest,
    SystemReportRequest,
)

__all__ = [
    "router",
    "AlertRuleRequest",
    "LogQueryRequest",
    "AlertUpdateRequest",
    "SystemReportRequest",
]
