"""券商連接 API

此模組實現券商連接相關的 API 端點，包括券商認證、帳戶資訊查詢、
持倉查詢和訂單管理等功能。

主要功能：
- 券商認證 API
- 帳戶資訊 API  
- 持倉查詢 API
- 訂單管理 API
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer

from src.api.models.responses import APIResponse
from src.api.utils.security import get_current_user
from .models import (
    BrokerAuthRequest,
    BrokerAuthResponse,
    AccountInfoResponse,
    PositionResponse,
    OrderResponse,
    BrokerType,
    OrderStatus,
    OrderSide,
    OrderType,
)

logger = logging.getLogger(__name__)
security = HTTPBearer()

# 創建路由器
router = APIRouter()

# 模擬券商連接狀態
_broker_sessions: Dict[str, Dict[str, Any]] = {}


@router.post("/auth", response_model=APIResponse[BrokerAuthResponse])
async def authenticate_broker(
    request: BrokerAuthRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """券商認證 API
    
    建立與券商的連接並進行身份認證。
    
    Args:
        request: 券商認證請求
        current_user: 當前用戶
        
    Returns:
        APIResponse[BrokerAuthResponse]: 認證結果
        
    Raises:
        HTTPException: 認證失敗時拋出
    """
    try:
        logger.info(
            "用戶 %s 嘗試連接券商 %s", 
            current_user.get("username"), 
            request.broker_type
        )
        
        # 模擬券商認證邏輯
        # 在實際實現中，這裡會調用真實的券商 API
        if not _validate_broker_credentials(request):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="券商認證失敗，請檢查帳號密碼"
            )
        
        # 生成會話 ID
        session_id = f"{request.broker_type}_{current_user['user_id']}_{datetime.now().timestamp()}"
        expires_at = datetime.now() + timedelta(hours=8)
        
        # 儲存會話資訊
        _broker_sessions[session_id] = {
            "user_id": current_user["user_id"],
            "broker_type": request.broker_type,
            "username": request.username,
            "expires_at": expires_at,
            "created_at": datetime.now()
        }
        
        response_data = BrokerAuthResponse(
            success=True,
            session_id=session_id,
            broker_type=request.broker_type,
            expires_at=expires_at,
            message="券商認證成功"
        )
        
        logger.info(
            "用戶 %s 成功連接券商 %s，會話 ID: %s", 
            current_user.get("username"), 
            request.broker_type,
            session_id
        )
        
        return APIResponse(
            success=True,
            data=response_data,
            message="券商認證成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("券商認證過程中發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="券商認證服務暫時不可用"
        )


@router.get("/account-info", response_model=APIResponse[AccountInfoResponse])
async def get_account_info(
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """獲取帳戶資訊 API
    
    查詢券商帳戶的基本資訊，包括資金狀況、保證金等。
    
    Args:
        session_id: 券商會話 ID
        current_user: 當前用戶
        
    Returns:
        APIResponse[AccountInfoResponse]: 帳戶資訊
        
    Raises:
        HTTPException: 會話無效或查詢失敗時拋出
    """
    try:
        # 驗證會話
        session = _validate_session(session_id, current_user["user_id"])
        
        # 模擬獲取帳戶資訊
        # 在實際實現中，這裡會調用券商 API 獲取真實數據
        account_info = AccountInfoResponse(
            account_id=f"ACC_{session['broker_type']}_{current_user['user_id']}",
            account_name=current_user.get("username", "Unknown"),
            broker_type=session["broker_type"],
            total_equity=1000000.00,
            available_cash=500000.00,
            margin_used=200000.00,
            margin_available=300000.00,
            buying_power=800000.00,
            unrealized_pnl=15000.00,
            realized_pnl=25000.00,
            last_updated=datetime.now()
        )
        
        return APIResponse(
            success=True,
            data=account_info,
            message="帳戶資訊獲取成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取帳戶資訊時發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="帳戶資訊服務暫時不可用"
        )


@router.get("/positions", response_model=APIResponse[List[PositionResponse]])
async def get_positions(
    session_id: str,
    symbol: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """獲取持倉資訊 API
    
    查詢當前的持倉狀況，可以查詢全部或指定股票的持倉。
    
    Args:
        session_id: 券商會話 ID
        symbol: 股票代碼（可選）
        current_user: 當前用戶
        
    Returns:
        APIResponse[List[PositionResponse]]: 持倉列表
        
    Raises:
        HTTPException: 會話無效或查詢失敗時拋出
    """
    try:
        # 驗證會話
        session = _validate_session(session_id, current_user["user_id"])
        
        # 模擬持倉數據
        positions = [
            PositionResponse(
                symbol="2330.TW",
                quantity=1000,
                average_price=587.50,
                current_price=595.00,
                market_value=595000.00,
                unrealized_pnl=7500.00,
                unrealized_pnl_percent=1.28,
                side=OrderSide.BUY,
                last_updated=datetime.now()
            ),
            PositionResponse(
                symbol="0050.TW",
                quantity=500,
                average_price=142.30,
                current_price=141.80,
                market_value=70900.00,
                unrealized_pnl=-250.00,
                unrealized_pnl_percent=-0.35,
                side=OrderSide.BUY,
                last_updated=datetime.now()
            )
        ]
        
        # 如果指定了股票代碼，則過濾結果
        if symbol:
            positions = [pos for pos in positions if pos.symbol == symbol]
        
        return APIResponse(
            success=True,
            data=positions,
            message=f"持倉資訊獲取成功，共 {len(positions)} 筆"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取持倉資訊時發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="持倉資訊服務暫時不可用"
        )


@router.get("/orders", response_model=APIResponse[List[OrderResponse]])
async def get_orders(
    session_id: str,
    status_filter: Optional[OrderStatus] = None,
    symbol: Optional[str] = None,
    limit: int = 100,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """獲取訂單列表 API
    
    查詢訂單歷史，支援按狀態和股票代碼過濾。
    
    Args:
        session_id: 券商會話 ID
        status_filter: 訂單狀態過濾
        symbol: 股票代碼過濾
        limit: 返回數量限制
        current_user: 當前用戶
        
    Returns:
        APIResponse[List[OrderResponse]]: 訂單列表
        
    Raises:
        HTTPException: 會話無效或查詢失敗時拋出
    """
    try:
        # 驗證會話
        session = _validate_session(session_id, current_user["user_id"])
        
        # 模擬訂單數據
        orders = [
            OrderResponse(
                order_id="ORD_001",
                symbol="2330.TW",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=1000,
                price=590.00,
                status=OrderStatus.FILLED,
                filled_quantity=1000,
                filled_price=589.50,
                commission=295.00,
                created_at=datetime.now() - timedelta(hours=2),
                updated_at=datetime.now() - timedelta(hours=1)
            ),
            OrderResponse(
                order_id="ORD_002",
                symbol="0050.TW",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=500,
                status=OrderStatus.PENDING,
                filled_quantity=0,
                commission=0.00,
                created_at=datetime.now() - timedelta(minutes=30),
                updated_at=datetime.now() - timedelta(minutes=30)
            )
        ]
        
        # 應用過濾條件
        if status_filter:
            orders = [order for order in orders if order.status == status_filter]
        if symbol:
            orders = [order for order in orders if order.symbol == symbol]
        
        # 限制返回數量
        orders = orders[:limit]
        
        return APIResponse(
            success=True,
            data=orders,
            message=f"訂單資訊獲取成功，共 {len(orders)} 筆"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取訂單資訊時發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="訂單資訊服務暫時不可用"
        )


def _validate_broker_credentials(request: BrokerAuthRequest) -> bool:
    """驗證券商憑證
    
    Args:
        request: 券商認證請求
        
    Returns:
        bool: 驗證是否成功
    """
    # 模擬驗證邏輯
    # 在實際實現中，這裡會調用真實的券商認證 API
    
    # 簡單的模擬驗證：用戶名不能為空，密碼長度至少 6 位
    if not request.username or len(request.password) < 6:
        return False
    
    # 模擬不同券商的特殊要求
    if request.broker_type == BrokerType.FUBON:
        return request.api_key is not None
    elif request.broker_type == BrokerType.CATHAY:
        return len(request.password) >= 8
    
    return True


def _validate_session(session_id: str, user_id: str) -> Dict[str, Any]:
    """驗證券商會話
    
    Args:
        session_id: 會話 ID
        user_id: 用戶 ID
        
    Returns:
        Dict[str, Any]: 會話資訊
        
    Raises:
        HTTPException: 會話無效時拋出
    """
    session = _broker_sessions.get(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的券商會話"
        )
    
    if session["user_id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="會話不屬於當前用戶"
        )
    
    if datetime.now() > session["expires_at"]:
        # 清理過期會話
        del _broker_sessions[session_id]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="券商會話已過期"
        )
    
    return session
