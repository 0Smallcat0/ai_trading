"""
風險管理 API 路由 - 主路由模組

此模組作為風險管理 API 的主入口，整合各個子模組的路由。
模組化分割完成後，整合以下子模組：
- parameters: 風險參數管理 API
- metrics: 風險指標管理 API
- controls: 風控機制管理 API
- alerts: 風險警報管理 API
"""

import logging
from fastapi import APIRouter

# 匯入子模組路由
from src.api.routers.risk_management.parameters import router as parameters_router
from src.api.routers.risk_management.metrics import router as metrics_router
from src.api.routers.risk_management.controls import router as controls_router
from src.api.routers.risk_management.alerts import router as alerts_router

logger = logging.getLogger(__name__)
router = APIRouter()

# 整合子模組路由
router.include_router(
    parameters_router,
    prefix="/parameters",
    tags=["風險參數管理"]
)

router.include_router(
    metrics_router,
    prefix="/metrics",
    tags=["風險指標管理"]
)

router.include_router(
    controls_router,
    prefix="/controls",
    tags=["風控機制管理"]
)

router.include_router(
    alerts_router,
    prefix="/alerts",
    tags=["風險警報管理"]
)


@router.get("/health")
async def health_check():
    """
    風險管理系統健康檢查端點
    
    Returns:
        dict: 健康狀態資訊
    """
    return {"status": "healthy", "message": "風險管理系統運行正常"}


# 原有的請求模型、響應模型和 API 端點已移動到對應的子模組中
# 此檔案現在只作為主路由模組，整合各個子模組的路由
