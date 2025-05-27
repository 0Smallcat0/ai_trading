"""風險管理系統路由模組

此模組聚合所有風險管理相關的 API 路由，提供統一的入口點。
"""

import logging
from fastapi import APIRouter

from .parameters import router as parameters_router
from .metrics import router as metrics_router
from .controls import router as controls_router
from .alerts import router as alerts_router

logger = logging.getLogger(__name__)

# 創建主路由器
router = APIRouter(prefix="/risk", tags=["風險管理"])

# 包含所有子路由
router.include_router(parameters_router, prefix="/parameters", tags=["風險參數"])
router.include_router(metrics_router, prefix="/metrics", tags=["風險指標"])
router.include_router(controls_router, prefix="/controls", tags=["風控機制"])
router.include_router(alerts_router, prefix="/alerts", tags=["風險警報"])

# 導出所有模型供外部使用
from .models import (
    RiskParametersRequest,
    RiskControlToggleRequest,
    AlertAcknowledgeRequest,
    RiskParameters,
    RiskMetrics,
    RiskControlStatus,
    RiskAlert,
)

__all__ = [
    "router",
    "RiskParametersRequest",
    "RiskControlToggleRequest",
    "AlertAcknowledgeRequest",
    "RiskParameters",
    "RiskMetrics",
    "RiskControlStatus",
    "RiskAlert",
]
