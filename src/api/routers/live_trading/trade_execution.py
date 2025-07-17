"""實時交易執行 API

此模組實現實時交易執行相關的 API 端點，包括下單、撤單、
修改訂單和一鍵平倉等核心交易功能。

主要功能：
- 下單 API
- 撤單 API
- 修改訂單 API
- 一鍵平倉 API
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, status

from src.api.models.responses import APIResponse
from src.api.utils.security import get_current_user
from .models import (
    PlaceOrderRequest,
    PlaceOrderResponse,
    CancelOrderRequest,
    ModifyOrderRequest,
    CloseAllPositionsRequest,
    OrderResponse,
    OrderStatus,
    OrderSide,
    OrderType,
)

logger = logging.getLogger(__name__)

# 創建路由器
router = APIRouter()

# 模擬訂單存儲
_active_orders: Dict[str, Dict[str, Any]] = {}


@router.post("/place-order", response_model=APIResponse[PlaceOrderResponse])
async def place_order(
    request: PlaceOrderRequest,
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """下單 API
    
    執行股票買賣訂單，支援市價單、限價單、停損單等多種訂單類型。
    
    Args:
        request: 下單請求
        session_id: 券商會話 ID
        current_user: 當前用戶
        
    Returns:
        APIResponse[PlaceOrderResponse]: 下單結果
        
    Raises:
        HTTPException: 下單失敗時拋出
    """
    try:
        logger.info(
            "用戶 %s 嘗試下單: %s %s %d 股 %s",
            current_user.get("username"),
            request.side.value,
            request.symbol,
            request.quantity,
            request.order_type.value
        )
        
        # 驗證券商會話（這裡簡化處理）
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="需要有效的券商會話"
            )
        
        # 執行風險檢查
        risk_check_result = await _perform_risk_check(request, current_user)
        if not risk_check_result["approved"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"風險檢查未通過: {risk_check_result['message']}"
            )
        
        # 生成訂單 ID
        order_id = f"ORD_{uuid.uuid4().hex[:8].upper()}"
        
        # 模擬下單邏輯
        order_details = await _execute_order(request, order_id, current_user)
        
        # 儲存訂單資訊
        _active_orders[order_id] = {
            "order_id": order_id,
            "user_id": current_user["user_id"],
            "session_id": session_id,
            "request": request.dict(),
            "status": order_details.status,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        response = PlaceOrderResponse(
            success=True,
            order_id=order_id,
            message="訂單提交成功",
            order_details=order_details
        )
        
        logger.info(
            "用戶 %s 下單成功，訂單 ID: %s",
            current_user.get("username"),
            order_id
        )
        
        return APIResponse(
            success=True,
            data=response,
            message="訂單提交成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("下單過程中發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="下單服務暫時不可用"
        )


@router.post("/cancel-order", response_model=APIResponse[Dict[str, Any]])
async def cancel_order(
    request: CancelOrderRequest,
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """撤單 API
    
    取消指定的未成交訂單。
    
    Args:
        request: 撤單請求
        session_id: 券商會話 ID
        current_user: 當前用戶
        
    Returns:
        APIResponse[Dict[str, Any]]: 撤單結果
        
    Raises:
        HTTPException: 撤單失敗時拋出
    """
    try:
        logger.info(
            "用戶 %s 嘗試撤單: %s",
            current_user.get("username"),
            request.order_id
        )
        
        # 驗證訂單存在且屬於當前用戶
        order = _active_orders.get(request.order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="訂單不存在"
            )
        
        if order["user_id"] != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="無權限操作此訂單"
            )
        
        if order["status"] in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="訂單已完成或已取消，無法撤單"
            )
        
        # 模擬撤單邏輯
        success = await _cancel_order_with_broker(request.order_id, session_id)
        
        if success:
            # 更新訂單狀態
            order["status"] = OrderStatus.CANCELLED
            order["updated_at"] = datetime.now()
            
            logger.info(
                "用戶 %s 撤單成功: %s",
                current_user.get("username"),
                request.order_id
            )
            
            return APIResponse(
                success=True,
                data={"order_id": request.order_id, "status": "cancelled"},
                message="撤單成功"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="撤單失敗，訂單可能已部分成交"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("撤單過程中發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="撤單服務暫時不可用"
        )


@router.post("/modify-order", response_model=APIResponse[OrderResponse])
async def modify_order(
    request: ModifyOrderRequest,
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """修改訂單 API
    
    修改指定訂單的數量、價格等參數。
    
    Args:
        request: 修改訂單請求
        session_id: 券商會話 ID
        current_user: 當前用戶
        
    Returns:
        APIResponse[OrderResponse]: 修改後的訂單資訊
        
    Raises:
        HTTPException: 修改失敗時拋出
    """
    try:
        logger.info(
            "用戶 %s 嘗試修改訂單: %s",
            current_user.get("username"),
            request.order_id
        )
        
        # 驗證訂單存在且屬於當前用戶
        order = _active_orders.get(request.order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="訂單不存在"
            )
        
        if order["user_id"] != current_user["user_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="無權限操作此訂單"
            )
        
        if order["status"] != OrderStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只能修改待執行的訂單"
            )
        
        # 模擬修改訂單邏輯
        updated_order = await _modify_order_with_broker(request, session_id)
        
        # 更新本地訂單資訊
        if request.quantity:
            order["request"]["quantity"] = request.quantity
        if request.price:
            order["request"]["price"] = float(request.price)
        if request.stop_price:
            order["request"]["stop_price"] = float(request.stop_price)
        
        order["updated_at"] = datetime.now()
        
        logger.info(
            "用戶 %s 修改訂單成功: %s",
            current_user.get("username"),
            request.order_id
        )
        
        return APIResponse(
            success=True,
            data=updated_order,
            message="訂單修改成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("修改訂單過程中發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="修改訂單服務暫時不可用"
        )


@router.post("/close-all-positions", response_model=APIResponse[List[PlaceOrderResponse]])
async def close_all_positions(
    request: CloseAllPositionsRequest,
    session_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """一鍵平倉 API
    
    快速平倉所有或指定的持倉部位。
    
    Args:
        request: 平倉請求
        session_id: 券商會話 ID
        current_user: 當前用戶
        
    Returns:
        APIResponse[List[PlaceOrderResponse]]: 平倉訂單列表
        
    Raises:
        HTTPException: 平倉失敗時拋出
    """
    try:
        logger.info(
            "用戶 %s 執行一鍵平倉，標的: %s",
            current_user.get("username"),
            request.symbols or "全部"
        )
        
        # 獲取當前持倉（模擬）
        positions = await _get_current_positions(session_id, current_user)
        
        # 過濾需要平倉的持倉
        if request.symbols:
            positions = [pos for pos in positions if pos["symbol"] in request.symbols]
        
        if not positions:
            return APIResponse(
                success=True,
                data=[],
                message="沒有需要平倉的持倉"
            )
        
        # 執行平倉訂單
        close_orders = []
        for position in positions:
            try:
                # 創建平倉訂單請求
                close_request = PlaceOrderRequest(
                    symbol=position["symbol"],
                    side=OrderSide.SELL if position["side"] == "BUY" else OrderSide.BUY,
                    order_type=request.order_type,
                    quantity=abs(position["quantity"]),
                    price=position.get("current_price") if request.order_type == OrderType.LIMIT else None
                )
                
                # 執行平倉訂單
                order_id = f"CLOSE_{uuid.uuid4().hex[:8].upper()}"
                order_details = await _execute_order(close_request, order_id, current_user)
                
                close_response = PlaceOrderResponse(
                    success=True,
                    order_id=order_id,
                    message=f"{position['symbol']} 平倉訂單提交成功",
                    order_details=order_details
                )
                
                close_orders.append(close_response)
                
            except Exception as e:
                logger.error("平倉 %s 時發生錯誤: %s", position["symbol"], e)
                close_response = PlaceOrderResponse(
                    success=False,
                    order_id=None,
                    message=f"{position['symbol']} 平倉失敗: {str(e)}"
                )
                close_orders.append(close_response)
        
        successful_orders = [order for order in close_orders if order.success]
        
        logger.info(
            "用戶 %s 一鍵平倉完成，成功 %d 筆，失敗 %d 筆",
            current_user.get("username"),
            len(successful_orders),
            len(close_orders) - len(successful_orders)
        )
        
        return APIResponse(
            success=True,
            data=close_orders,
            message=f"平倉完成，成功 {len(successful_orders)} 筆"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("一鍵平倉過程中發生錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="一鍵平倉服務暫時不可用"
        )


async def _perform_risk_check(request: PlaceOrderRequest, user: Dict[str, Any]) -> Dict[str, Any]:
    """執行風險檢查
    
    Args:
        request: 下單請求
        user: 用戶資訊
        
    Returns:
        Dict[str, Any]: 風險檢查結果
    """
    # 模擬風險檢查邏輯
    # 在實際實現中，這裡會調用風險管理模組
    
    # 簡單的風險檢查規則
    max_single_order_value = 1000000  # 單筆訂單最大金額
    order_value = request.quantity * (request.price or 100)  # 估算訂單金額
    
    if order_value > max_single_order_value:
        return {
            "approved": False,
            "message": f"單筆訂單金額超過限制 {max_single_order_value:,.0f}"
        }
    
    return {
        "approved": True,
        "message": "風險檢查通過"
    }


async def _execute_order(request: PlaceOrderRequest, order_id: str, user: Dict[str, Any]) -> OrderResponse:
    """執行訂單
    
    Args:
        request: 下單請求
        order_id: 訂單 ID
        user: 用戶資訊
        
    Returns:
        OrderResponse: 訂單詳情
    """
    # 模擬訂單執行邏輯
    # 在實際實現中，這裡會調用券商 API 執行真實訂單
    
    # 模擬不同訂單類型的處理
    if request.order_type == OrderType.MARKET:
        # 市價單立即成交
        status = OrderStatus.FILLED
        filled_quantity = request.quantity
        filled_price = request.price or 100.0  # 模擬市價
    else:
        # 限價單等待成交
        status = OrderStatus.PENDING
        filled_quantity = 0
        filled_price = None
    
    return OrderResponse(
        order_id=order_id,
        symbol=request.symbol,
        side=request.side,
        order_type=request.order_type,
        quantity=request.quantity,
        price=request.price,
        stop_price=request.stop_price,
        status=status,
        filled_quantity=filled_quantity,
        filled_price=filled_price,
        commission=request.quantity * 0.1425 * 0.001,  # 模擬手續費
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


async def _cancel_order_with_broker(order_id: str, session_id: str) -> bool:
    """向券商發送撤單請求
    
    Args:
        order_id: 訂單 ID
        session_id: 券商會話 ID
        
    Returns:
        bool: 撤單是否成功
    """
    # 模擬券商撤單 API 調用
    # 在實際實現中，這裡會調用真實的券商撤單 API
    return True


async def _modify_order_with_broker(request: ModifyOrderRequest, session_id: str) -> OrderResponse:
    """向券商發送修改訂單請求
    
    Args:
        request: 修改訂單請求
        session_id: 券商會話 ID
        
    Returns:
        OrderResponse: 修改後的訂單資訊
    """
    # 模擬券商修改訂單 API 調用
    # 在實際實現中，這裡會調用真實的券商修改訂單 API
    
    order = _active_orders.get(request.order_id)
    original_request = order["request"]
    
    return OrderResponse(
        order_id=request.order_id,
        symbol=original_request["symbol"],
        side=OrderSide(original_request["side"]),
        order_type=OrderType(original_request["order_type"]),
        quantity=request.quantity or original_request["quantity"],
        price=request.price or original_request.get("price"),
        stop_price=request.stop_price or original_request.get("stop_price"),
        status=OrderStatus.PENDING,
        filled_quantity=0,
        commission=0.0,
        created_at=order["created_at"],
        updated_at=datetime.now()
    )


async def _get_current_positions(session_id: str, user: Dict[str, Any]) -> List[Dict[str, Any]]:
    """獲取當前持倉
    
    Args:
        session_id: 券商會話 ID
        user: 用戶資訊
        
    Returns:
        List[Dict[str, Any]]: 持倉列表
    """
    # 模擬持倉數據
    return [
        {
            "symbol": "2330.TW",
            "quantity": 1000,
            "side": "BUY",
            "current_price": 595.0
        },
        {
            "symbol": "0050.TW",
            "quantity": 500,
            "side": "BUY",
            "current_price": 141.8
        }
    ]
