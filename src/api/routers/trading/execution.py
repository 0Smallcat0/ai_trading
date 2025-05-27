"""
交易執行 API

此模組實現交易執行相關的 API 端點，包括訂單取消、批量操作、交易模式切換等。
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, Path, status

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.core.trade_execution_service import TradeExecutionService
from .models import (
    BatchOrderRequest, TradingModeRequest, OrderResponse,
    TradeExecutionResponse, TradingStatusResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化交易執行服務
trade_service = TradeExecutionService()


@router.delete(
    "/orders/{order_id}",
    response_model=APIResponse[OrderResponse],
    responses=COMMON_RESPONSES,
    summary="取消訂單",
    description="取消指定的訂單",
)
async def cancel_order(order_id: str = Path(..., description="訂單 ID")):
    """取消訂單

    此端點用於取消指定的訂單，只有特定狀態的訂單可以取消。

    Args:
        order_id: 訂單 ID

    Returns:
        APIResponse[OrderResponse]: 包含取消後訂單詳情的 API 回應

    Raises:
        HTTPException: 當訂單不存在、狀態不允許取消或取消失敗時

    Example:
        DELETE /api/trading/orders/ORDER123
    """
    try:
        # 檢查訂單是否存在
        existing_order = trade_service.get_order_details(order_id)
        if not existing_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"訂單 {order_id} 不存在"
            )

        # 檢查訂單狀態是否可取消
        if existing_order["status"] not in ["pending", "submitted", "partially_filled"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"訂單狀態為 {existing_order['status']}，無法取消",
            )

        # 執行訂單取消
        success, message = trade_service.cancel_order(order_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"訂單取消失敗: {message}",
            )

        # 獲取取消後的訂單詳情
        cancelled_order = trade_service.get_order_details(order_id)
        response_data = _convert_to_order_response(cancelled_order)

        return APIResponse(
            success=True,
            message="訂單取消成功",
            data=response_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("取消訂單失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消訂單失敗: {str(e)}",
        ) from e


@router.post(
    "/orders/batch",
    response_model=APIResponse[List[OrderResponse]],
    responses=COMMON_RESPONSES,
    summary="批量創建訂單",
    description="批量創建多個訂單，支援全部執行或全部不執行模式",
)
async def create_batch_orders(request: BatchOrderRequest):
    """批量創建訂單

    此端點用於批量創建多個訂單，可以選擇全部執行或全部不執行模式。

    Args:
        request: 批量訂單請求資料

    Returns:
        APIResponse[List[OrderResponse]]: 包含創建的訂單列表的 API 回應

    Raises:
        HTTPException: 當批量訂單創建失敗時

    Example:
        POST /api/trading/orders/batch
        {
            "orders": [
                {"symbol": "2330.TW", "action": "buy", "quantity": 1000, "order_type": "market"},
                {"symbol": "2317.TW", "action": "sell", "quantity": 500, "order_type": "limit", "price": 100.0}
            ],
            "execute_all_or_none": true
        }
    """
    try:
        created_orders = []
        failed_orders = []

        # 如果是全部執行或全部不執行模式，先驗證所有訂單
        if request.execute_all_or_none:
            for i, order_request in enumerate(request.orders):
                try:
                    # 驗證訂單（不實際創建）
                    order_data = _build_order_data_from_request(order_request)
                    is_valid, validation_message = trade_service.validate_order(order_data)

                    if not is_valid:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"批量訂單創建失敗（全部執行或全部不執行模式），"
                                   f"第 {i + 1} 個訂單驗證失敗: {validation_message}",
                        )
                except Exception as order_error:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"批量訂單創建失敗（全部執行或全部不執行模式），"
                               f"第 {i + 1} 個訂單異常: {str(order_error)}",
                    ) from order_error

        # 創建所有訂單
        for i, order_request in enumerate(request.orders):
            try:
                order_data = _build_order_data_from_request(order_request)
                success, message, order_id = trade_service.submit_order(order_data)

                if success:
                    order_details = trade_service.get_order_details(order_id)
                    if order_details:
                        created_orders.append(_convert_to_order_response(order_details))
                else:
                    failed_orders.append({
                        "index": i + 1,
                        "error": message,
                        "order_data": order_data
                    })

            except Exception as order_error:
                failed_orders.append({
                    "index": i + 1,
                    "error": str(order_error),
                    "order_data": order_request.dict()
                })

        # 處理結果
        if request.execute_all_or_none and failed_orders:
            # 如果是全部執行或全部不執行模式且有失敗，回滾所有已創建的訂單
            for created_order in created_orders:
                try:
                    trade_service.cancel_order(created_order.order_id)
                except Exception as rollback_error:
                    logger.error("回滾訂單失敗: %s", rollback_error)

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"批量訂單創建失敗，已回滾所有訂單。失敗數量: {len(failed_orders)}",
            )

        if failed_orders and not request.execute_all_or_none:
            logger.warning("部分訂單創建失敗: %s", failed_orders)

        return APIResponse(
            success=True,
            message=f"批量訂單創建完成，成功: {len(created_orders)}，失敗: {len(failed_orders)}",
            data=created_orders
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("批量創建訂單失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量創建訂單失敗: {str(e)}",
        ) from e


@router.post(
    "/mode",
    response_model=APIResponse[TradingStatusResponse],
    responses=COMMON_RESPONSES,
    summary="切換交易模式",
    description="在模擬交易和實盤交易之間切換",
)
async def switch_trading_mode(request: TradingModeRequest):
    """切換交易模式

    此端點用於在模擬交易和實盤交易模式之間切換。

    Args:
        request: 交易模式切換請求資料

    Returns:
        APIResponse[TradingStatusResponse]: 包含切換後交易狀態的 API 回應

    Raises:
        HTTPException: 當模式切換失敗時

    Example:
        POST /api/trading/mode
        {
            "is_simulation": true,
            "reason": "測試新策略"
        }
    """
    try:
        # 執行模式切換
        success, message = trade_service.switch_trading_mode(
            is_simulation=request.is_simulation
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"交易模式切換失敗: {message}",
            )

        # 獲取切換後的交易狀態
        trading_status = trade_service.get_trading_status()
        response_data = _convert_to_trading_status_response(trading_status)

        mode_text = "模擬交易" if request.is_simulation else "實盤交易"
        return APIResponse(
            success=True,
            message=f"已切換至{mode_text}模式",
            data=response_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("切換交易模式失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"切換交易模式失敗: {str(e)}",
        ) from e


@router.get(
    "/status",
    response_model=APIResponse[TradingStatusResponse],
    responses=COMMON_RESPONSES,
    summary="獲取交易狀態",
    description="獲取當前交易系統的狀態信息",
)
async def get_trading_status():
    """獲取交易狀態

    此端點用於獲取當前交易系統的狀態信息，包括交易模式、連接狀態等。

    Returns:
        APIResponse[TradingStatusResponse]: 包含交易狀態的 API 回應

    Raises:
        HTTPException: 當獲取狀態失敗時
    """
    try:
        # 獲取交易狀態
        trading_status = trade_service.get_trading_status()
        response_data = _convert_to_trading_status_response(trading_status)

        return APIResponse(
            success=True,
            message="交易狀態獲取成功",
            data=response_data
        )

    except Exception as e:
        logger.error("獲取交易狀態失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取交易狀態失敗: {str(e)}",
        ) from e


# ==================== 輔助函數 ====================


def _build_order_data_from_request(order_request) -> dict:
    """從訂單請求構建訂單數據

    Args:
        order_request: 訂單請求對象

    Returns:
        dict: 訂單數據字典
    """
    return {
        "symbol": order_request.symbol,
        "action": order_request.action,
        "quantity": order_request.quantity,
        "order_type": order_request.order_type,
        "price": order_request.price,
        "stop_price": order_request.stop_price,
        "time_in_force": order_request.time_in_force,
        "portfolio_id": order_request.portfolio_id,
        "notes": order_request.notes,
    }


def _convert_to_order_response(order_details: dict):
    """將訂單詳情轉換為響應模型

    Args:
        order_details: 訂單詳情字典

    Returns:
        OrderResponse: 訂單響應模型
    """
    return OrderResponse(
        order_id=order_details["order_id"],
        symbol=order_details["symbol"],
        action=order_details["action"],
        quantity=order_details["quantity"],
        filled_quantity=order_details.get("filled_quantity", 0),
        remaining_quantity=order_details["quantity"] - order_details.get("filled_quantity", 0),
        order_type=order_details["order_type"],
        price=order_details.get("price"),
        stop_price=order_details.get("stop_price"),
        filled_price=order_details.get("filled_price"),
        time_in_force=order_details["time_in_force"],
        status=order_details["status"],
        portfolio_id=order_details.get("portfolio_id"),
        created_at=order_details["created_at"],
        updated_at=order_details.get("updated_at"),
        filled_at=order_details.get("filled_at"),
        error_message=order_details.get("error_message"),
        commission=order_details.get("commission"),
        tax=order_details.get("tax"),
        net_amount=order_details.get("net_amount"),
        notes=order_details.get("notes"),
    )


def _convert_to_trading_status_response(status_data: dict):
    """將交易狀態數據轉換為響應模型

    Args:
        status_data: 交易狀態數據字典

    Returns:
        TradingStatusResponse: 交易狀態響應模型
    """
    return TradingStatusResponse(
        is_simulation_mode=status_data["is_simulation_mode"],
        broker_connected=status_data["broker_connected"],
        current_broker=status_data["current_broker"],
        trading_session=status_data["trading_session"],
        market_status=status_data["market_status"],
        pending_orders_count=status_data["pending_orders_count"],
        today_orders_count=status_data["today_orders_count"],
        today_executions_count=status_data["today_executions_count"],
        available_cash=status_data["available_cash"],
        total_position_value=status_data["total_position_value"],
        last_update=status_data["last_update"],
    )
