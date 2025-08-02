"""
交易系統路由模組

此模組聚合所有交易相關的 API 路由，提供統一的入口點。
"""

import logging
from fastapi import APIRouter

from .orders import router as orders_router
from .execution import router as execution_router
from .history import router as history_router
from .statistics import router as statistics_router

logger = logging.getLogger(__name__)

# 創建主路由器
router = APIRouter(prefix="/trading", tags=["交易系統"])

# 包含所有子路由
router.include_router(orders_router, tags=["訂單管理"])
router.include_router(execution_router, tags=["交易執行"])
router.include_router(history_router, tags=["交易歷史"])
router.include_router(statistics_router, tags=["交易統計"])

# 導出所有模型供外部使用
from .models import (
    OrderRequest,
    OrderUpdateRequest,
    TradingModeRequest,
    BatchOrderRequest,
    OrderResponse,
    TradeExecutionResponse,
)

__all__ = [
    "router",
    "OrderRequest",
    "OrderUpdateRequest",
    "TradingModeRequest",
    "BatchOrderRequest",
    "OrderResponse",
    "TradeExecutionResponse",
]
