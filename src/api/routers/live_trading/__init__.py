"""Live Trading API 模組

此模組提供實時交易相關的 API 端點，包括券商連接、交易執行、風險控制和通知功能。
這是系統的盈利核心模組，提供完整的實時交易能力。

主要功能：
- 券商連接管理
- 實時交易執行
- 風險控制機制
- 實時通知系統

Example:
    使用 Live Trading API：
    ```python
    from src.api.routers.live_trading import router
    
    app.include_router(router, prefix="/api/v1/live-trading")
    ```

Note:
    此模組包含高風險的實時交易功能，需要嚴格的權限控制和風險管理。
"""

import logging
from fastapi import APIRouter

# 導入子路由
from .broker_connection import router as broker_router
from .trade_execution import router as execution_router
from .risk_control import router as risk_router
from .notifications import router as notifications_router

logger = logging.getLogger(__name__)

# 創建主路由器
router = APIRouter(prefix="/live-trading", tags=["實時交易"])

# 包含所有子路由
router.include_router(broker_router, prefix="/broker", tags=["券商連接"])
router.include_router(execution_router, prefix="/execution", tags=["交易執行"])
router.include_router(risk_router, prefix="/risk", tags=["風險控制"])
router.include_router(notifications_router, prefix="/notifications", tags=["實時通知"])

# 導出所有模型供外部使用
from .models import (
    # 券商連接模型
    BrokerAuthRequest,
    BrokerAuthResponse,
    AccountInfoResponse,
    PositionResponse,
    OrderResponse,
    
    # 交易執行模型
    PlaceOrderRequest,
    PlaceOrderResponse,
    CancelOrderRequest,
    ModifyOrderRequest,
    CloseAllPositionsRequest,
    
    # 風險控制模型
    RiskCheckRequest,
    RiskCheckResponse,
    EmergencyStopRequest,
    FundMonitorResponse,
    
    # 通知模型
    TradeNotification,
    RiskAlert,
    SystemStatusNotification,
)

__all__ = [
    "router",
    # 券商連接模型
    "BrokerAuthRequest",
    "BrokerAuthResponse", 
    "AccountInfoResponse",
    "PositionResponse",
    "OrderResponse",
    
    # 交易執行模型
    "PlaceOrderRequest",
    "PlaceOrderResponse",
    "CancelOrderRequest",
    "ModifyOrderRequest",
    "CloseAllPositionsRequest",
    
    # 風險控制模型
    "RiskCheckRequest",
    "RiskCheckResponse",
    "EmergencyStopRequest",
    "FundMonitorResponse",
    
    # 通知模型
    "TradeNotification",
    "RiskAlert",
    "SystemStatusNotification",
]
