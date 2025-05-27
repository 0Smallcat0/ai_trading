"""
交易執行 API 路由 - 主路由模組

此模組作為交易執行 API 的主入口，整合各個子模組的路由。
模組化分割完成後，整合以下子模組：
- orders: 訂單管理 API
- execution: 交易執行 API
- history: 交易歷史 API
- statistics: 交易統計 API
"""

import logging
from fastapi import APIRouter

# 匯入子模組路由
from src.api.routers.trading.orders import router as orders_router
from src.api.routers.trading.execution import router as execution_router
from src.api.routers.trading.history import router as history_router
from src.api.routers.trading.statistics import router as statistics_router

logger = logging.getLogger(__name__)
router = APIRouter()

# 整合子模組路由
router.include_router(orders_router, prefix="/orders", tags=["訂單管理"])

router.include_router(execution_router, prefix="/execution", tags=["交易執行"])

router.include_router(history_router, prefix="/history", tags=["交易歷史"])

router.include_router(statistics_router, prefix="/statistics", tags=["交易統計"])


@router.get("/health")
async def health_check():
    """
    交易執行系統健康檢查端點

    Returns:
        dict: 健康狀態資訊
    """
    return {"status": "healthy", "message": "交易執行系統運行正常"}


# 原有的請求模型、響應模型和 API 端點已移動到對應的子模組中
# 此檔案現在只作為主路由模組，整合各個子模組的路由
