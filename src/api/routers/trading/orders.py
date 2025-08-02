"""訂單管理 API

此模組實現訂單相關的 API 端點，包括創建、查詢、修改和取消訂單。
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Path, status

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.core.trade_execution_service import TradeExecutionService
from .models import OrderRequest, OrderUpdateRequest, OrderResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化交易執行服務
trade_service = TradeExecutionService()


@router.post(
    "/orders",
    response_model=APIResponse[OrderResponse],
    responses=COMMON_RESPONSES,
    summary="創建交易訂單",
    description="創建新的交易訂單，支援多種訂單類型",
)
async def create_order(request: OrderRequest):
    """創建交易訂單

    此端點用於創建新的交易訂單，支援市價單、限價單、停損單等多種類型。

    Args:
        request: 訂單請求資料

    Returns:
        APIResponse[OrderResponse]: 包含創建的訂單詳情

    Raises:
        HTTPException: 當訂單創建失敗時

    Example:
        POST /api/trading/orders
        {
            "symbol": "2330.TW",
            "action": "buy",
            "quantity": 1000,
            "order_type": "limit",
            "price": 500.0
        }
    """
    try:
        # 構建訂單數據
        order_data = _build_order_data(request)

        # 提交訂單
        success, message, order_id = trade_service.submit_order(order_data)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"訂單創建失敗: {message}",
            )

        # 獲取創建的訂單詳情
        order_details = trade_service.get_order_details(order_id)

        if not order_details:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="訂單創建成功但無法獲取詳情",
            )

        # 轉換為響應模型
        response_data = _convert_to_order_response(order_details)

        return APIResponse(success=True, message="訂單創建成功", data=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("創建訂單失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"創建訂單失敗: {str(e)}",
        ) from e


@router.get(
    "/orders",
    response_model=APIResponse[List[OrderResponse]],
    responses=COMMON_RESPONSES,
    summary="查詢訂單列表",
    description="查詢訂單列表，支援分頁和篩選",
)
async def get_orders(
    page: int = Query(default=1, ge=1, description="頁碼"),
    page_size: int = Query(default=20, ge=1, le=100, description="每頁數量"),
    order_status: Optional[str] = Query(default=None, description="訂單狀態篩選"),
    symbol: Optional[str] = Query(default=None, description="股票代碼篩選"),
    action: Optional[str] = Query(default=None, description="交易動作篩選"),
    order_type: Optional[str] = Query(default=None, description="訂單類型篩選"),
    portfolio_id: Optional[str] = Query(default=None, description="投資組合 ID 篩選"),
    start_date: Optional[str] = Query(
        default=None, description="開始日期 (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(default=None, description="結束日期 (YYYY-MM-DD)"),
):
    """查詢訂單列表

    此端點用於查詢訂單列表，支援多種篩選條件和分頁。

    Args:
        page: 頁碼
        page_size: 每頁數量
        order_status: 訂單狀態篩選
        symbol: 股票代碼篩選
        action: 交易動作篩選
        order_type: 訂單類型篩選
        portfolio_id: 投資組合 ID 篩選
        start_date: 開始日期
        end_date: 結束日期

    Returns:
        APIResponse[List[OrderResponse]]: 包含訂單列表的 API 回應

    Raises:
        HTTPException: 當查詢失敗時
    """
    try:
        # 構建篩選條件
        filters = _build_order_filters(
            order_status, symbol, action, order_type, portfolio_id, start_date, end_date
        )

        # 獲取訂單列表
        orders_data = trade_service.get_orders_list(
            page=page, page_size=page_size, filters=filters
        )

        # 轉換為響應模型
        orders_list = [
            _convert_to_order_response(order) for order in orders_data.get("orders", [])
        ]

        return APIResponse(
            success=True, message=f"獲取到 {len(orders_list)} 個訂單", data=orders_list
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("查詢訂單列表失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢訂單列表失敗: {str(e)}",
        ) from e


@router.get(
    "/orders/{order_id}",
    response_model=APIResponse[OrderResponse],
    responses=COMMON_RESPONSES,
    summary="查詢特定訂單詳情",
    description="根據訂單 ID 查詢特定訂單的詳細信息",
)
async def get_order_details(order_id: str = Path(..., description="訂單 ID")):
    """查詢特定訂單詳情

    此端點用於根據訂單 ID 查詢特定訂單的詳細信息。

    Args:
        order_id: 訂單 ID

    Returns:
        APIResponse[OrderResponse]: 包含訂單詳情的 API 回應

    Raises:
        HTTPException: 當訂單不存在或查詢失敗時
    """
    try:
        # 獲取訂單詳情
        order_details = trade_service.get_order_details(order_id)

        if not order_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"訂單 {order_id} 不存在"
            )

        # 轉換為響應模型
        response_data = _convert_to_order_response(order_details)

        return APIResponse(success=True, message="訂單詳情獲取成功", data=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("查詢訂單詳情失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢訂單詳情失敗: {str(e)}",
        ) from e


@router.put(
    "/orders/{order_id}",
    response_model=APIResponse[OrderResponse],
    responses=COMMON_RESPONSES,
    summary="修改訂單",
    description="修改現有訂單的參數",
)
async def update_order(
    order_id: str = Path(..., description="訂單 ID"), request: OrderUpdateRequest = None
):
    """修改訂單

    此端點用於修改現有訂單的參數，只有特定狀態的訂單可以修改。

    Args:
        order_id: 訂單 ID
        request: 訂單更新請求資料

    Returns:
        APIResponse[OrderResponse]: 包含更新後訂單詳情的 API 回應

    Raises:
        HTTPException: 當訂單不存在、狀態不允許修改或修改失敗時
    """
    try:
        # 檢查訂單是否存在
        existing_order = trade_service.get_order_details(order_id)
        if not existing_order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"訂單 {order_id} 不存在"
            )

        # 檢查訂單狀態是否可修改
        if existing_order["status"] not in ["pending", "submitted", "partially_filled"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"訂單狀態為 {existing_order['status']}，無法修改",
            )

        # 構建更新數據
        update_data = _build_update_data(request)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="沒有提供任何更新數據"
            )

        # 執行訂單修改
        success, message = trade_service.update_order(order_id, update_data)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"訂單修改失敗: {message}",
            )

        # 獲取更新後的訂單詳情
        updated_order = trade_service.get_order_details(order_id)
        response_data = _convert_to_order_response(updated_order)

        return APIResponse(success=True, message="訂單修改成功", data=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("修改訂單失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"修改訂單失敗: {str(e)}",
        ) from e


# ==================== 輔助函數 ====================


def _build_order_data(request: OrderRequest) -> dict:
    """構建訂單數據字典

    Args:
        request: 訂單請求

    Returns:
        dict: 訂單數據字典
    """
    return {
        "symbol": request.symbol,
        "action": request.action,
        "quantity": request.quantity,
        "order_type": request.order_type,
        "price": request.price,
        "stop_price": request.stop_price,
        "time_in_force": request.time_in_force,
        "portfolio_id": request.portfolio_id,
        "notes": request.notes,
    }


def _build_order_filters(
    order_status: Optional[str],
    symbol: Optional[str],
    action: Optional[str],
    order_type: Optional[str],
    portfolio_id: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str],
) -> dict:
    """構建訂單篩選條件

    Args:
        order_status: 訂單狀態
        symbol: 股票代碼
        action: 交易動作
        order_type: 訂單類型
        portfolio_id: 投資組合 ID
        start_date: 開始日期
        end_date: 結束日期

    Returns:
        dict: 篩選條件字典

    Raises:
        HTTPException: 當日期格式錯誤時
    """
    filters = {}

    if order_status:
        filters["status"] = order_status
    if symbol:
        filters["symbol"] = symbol
    if action:
        filters["action"] = action
    if order_type:
        filters["order_type"] = order_type
    if portfolio_id:
        filters["portfolio_id"] = portfolio_id

    if start_date:
        try:
            filters["start_date"] = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="開始日期格式錯誤，請使用 YYYY-MM-DD 格式",
            ) from e

    if end_date:
        try:
            filters["end_date"] = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="結束日期格式錯誤，請使用 YYYY-MM-DD 格式",
            ) from e

    return filters


def _build_update_data(request: OrderUpdateRequest) -> dict:
    """構建訂單更新數據

    Args:
        request: 訂單更新請求

    Returns:
        dict: 更新數據字典
    """
    update_data = {}

    if request.quantity is not None:
        update_data["quantity"] = request.quantity
    if request.price is not None:
        update_data["price"] = request.price
    if request.stop_price is not None:
        update_data["stop_price"] = request.stop_price
    if request.time_in_force is not None:
        update_data["time_in_force"] = request.time_in_force
    if request.notes is not None:
        update_data["notes"] = request.notes

    return update_data


def _convert_to_order_response(order_details: dict) -> OrderResponse:
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
        remaining_quantity=order_details["quantity"]
        - order_details.get("filled_quantity", 0),
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
