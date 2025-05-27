"""
交易歷史查詢 API

此模組實現交易歷史相關的 API 端點，包括交易記錄查詢、執行歷史等。
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Path, status

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.core.trade_execution_service import TradeExecutionService
from .models import TradeExecutionResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化交易執行服務
trade_service = TradeExecutionService()


@router.get(
    "/history",
    response_model=APIResponse[List[TradeExecutionResponse]],
    responses=COMMON_RESPONSES,
    summary="交易歷史記錄",
    description="查詢交易執行歷史記錄",
)
async def get_trade_history(
    page: int = Query(default=1, ge=1, description="頁碼"),
    page_size: int = Query(default=20, ge=1, le=100, description="每頁數量"),
    symbol: Optional[str] = Query(default=None, description="股票代碼篩選"),
    action: Optional[str] = Query(default=None, description="交易動作篩選"),
    portfolio_id: Optional[str] = Query(default=None, description="投資組合 ID 篩選"),
    start_date: Optional[str] = Query(default=None, description="開始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="結束日期 (YYYY-MM-DD)"),
):
    """查詢交易歷史記錄
    
    此端點用於查詢交易執行的歷史記錄，支援多種篩選條件和分頁。
    
    Args:
        page: 頁碼
        page_size: 每頁數量
        symbol: 股票代碼篩選
        action: 交易動作篩選
        portfolio_id: 投資組合 ID 篩選
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        APIResponse[List[TradeExecutionResponse]]: 包含交易歷史記錄的 API 回應
        
    Raises:
        HTTPException: 當查詢失敗時
        
    Example:
        GET /api/trading/history?symbol=2330.TW&start_date=2024-01-01&end_date=2024-12-31
    """
    try:
        # 構建篩選條件
        filters = _build_history_filters(
            symbol, action, portfolio_id, start_date, end_date
        )

        # 獲取交易歷史
        history_data = trade_service.get_execution_history(
            page=page, page_size=page_size, filters=filters
        )

        # 轉換為響應模型
        executions_list = [
            _convert_to_execution_response(execution)
            for execution in history_data.get("executions", [])
        ]

        return APIResponse(
            success=True,
            message=f"獲取到 {len(executions_list)} 筆交易記錄",
            data=executions_list
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("查詢交易歷史失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢交易歷史失敗: {str(e)}",
        ) from e


@router.get(
    "/orders/{order_id}/executions",
    response_model=APIResponse[List[TradeExecutionResponse]],
    responses=COMMON_RESPONSES,
    summary="查詢訂單執行記錄",
    description="查詢特定訂單的執行記錄",
)
async def get_order_executions(order_id: str = Path(..., description="訂單 ID")):
    """查詢訂單執行記錄
    
    此端點用於查詢特定訂單的所有執行記錄。
    
    Args:
        order_id: 訂單 ID
        
    Returns:
        APIResponse[List[TradeExecutionResponse]]: 包含訂單執行記錄的 API 回應
        
    Raises:
        HTTPException: 當訂單不存在或查詢失敗時
    """
    try:
        # 檢查訂單是否存在
        order_details = trade_service.get_order_details(order_id)
        if not order_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"訂單 {order_id} 不存在"
            )

        # 獲取訂單執行記錄
        executions_data = trade_service.get_execution_history(
            filters={"order_id": order_id}
        )

        # 轉換為響應模型
        executions_list = [
            _convert_to_execution_response(execution)
            for execution in executions_data.get("executions", [])
        ]

        return APIResponse(
            success=True,
            message=f"訂單 {order_id} 有 {len(executions_list)} 筆執行記錄",
            data=executions_list
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("查詢訂單執行記錄失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢訂單執行記錄失敗: {str(e)}",
        ) from e


@router.get(
    "/executions/{execution_id}",
    response_model=APIResponse[TradeExecutionResponse],
    responses=COMMON_RESPONSES,
    summary="查詢執行詳情",
    description="查詢特定執行記錄的詳細信息",
)
async def get_execution_details(execution_id: str = Path(..., description="執行 ID")):
    """查詢執行詳情
    
    此端點用於查詢特定執行記錄的詳細信息。
    
    Args:
        execution_id: 執行 ID
        
    Returns:
        APIResponse[TradeExecutionResponse]: 包含執行詳情的 API 回應
        
    Raises:
        HTTPException: 當執行記錄不存在或查詢失敗時
    """
    try:
        # 獲取執行詳情
        execution_details = trade_service.get_execution_details(execution_id)

        if not execution_details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"執行記錄 {execution_id} 不存在"
            )

        # 轉換為響應模型
        response_data = _convert_to_execution_response(execution_details)

        return APIResponse(
            success=True,
            message="執行詳情獲取成功",
            data=response_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("查詢執行詳情失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢執行詳情失敗: {str(e)}",
        ) from e


@router.get(
    "/portfolio/{portfolio_id}/history",
    response_model=APIResponse[List[TradeExecutionResponse]],
    responses=COMMON_RESPONSES,
    summary="查詢投資組合交易歷史",
    description="查詢特定投資組合的交易歷史記錄",
)
async def get_portfolio_trade_history(
    portfolio_id: str = Path(..., description="投資組合 ID"),
    page: int = Query(default=1, ge=1, description="頁碼"),
    page_size: int = Query(default=20, ge=1, le=100, description="每頁數量"),
    symbol: Optional[str] = Query(default=None, description="股票代碼篩選"),
    action: Optional[str] = Query(default=None, description="交易動作篩選"),
    start_date: Optional[str] = Query(default=None, description="開始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="結束日期 (YYYY-MM-DD)"),
):
    """查詢投資組合交易歷史
    
    此端點用於查詢特定投資組合的交易歷史記錄。
    
    Args:
        portfolio_id: 投資組合 ID
        page: 頁碼
        page_size: 每頁數量
        symbol: 股票代碼篩選
        action: 交易動作篩選
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        APIResponse[List[TradeExecutionResponse]]: 包含投資組合交易歷史的 API 回應
        
    Raises:
        HTTPException: 當查詢失敗時
    """
    try:
        # 構建篩選條件（包含投資組合 ID）
        filters = _build_history_filters(
            symbol, action, portfolio_id, start_date, end_date
        )

        # 獲取交易歷史
        history_data = trade_service.get_execution_history(
            page=page, page_size=page_size, filters=filters
        )

        # 轉換為響應模型
        executions_list = [
            _convert_to_execution_response(execution)
            for execution in history_data.get("executions", [])
        ]

        return APIResponse(
            success=True,
            message=f"投資組合 {portfolio_id} 有 {len(executions_list)} 筆交易記錄",
            data=executions_list
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("查詢投資組合交易歷史失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查詢投資組合交易歷史失敗: {str(e)}",
        ) from e


# ==================== 輔助函數 ====================


def _build_history_filters(
    symbol: Optional[str],
    action: Optional[str],
    portfolio_id: Optional[str],
    start_date: Optional[str],
    end_date: Optional[str]
) -> dict:
    """構建交易歷史篩選條件
    
    Args:
        symbol: 股票代碼
        action: 交易動作
        portfolio_id: 投資組合 ID
        start_date: 開始日期
        end_date: 結束日期
        
    Returns:
        dict: 篩選條件字典
        
    Raises:
        HTTPException: 當日期格式錯誤時
    """
    filters = {}
    
    if symbol:
        filters["symbol"] = symbol
    if action:
        filters["action"] = action
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


def _convert_to_execution_response(execution_details: dict) -> TradeExecutionResponse:
    """將執行詳情轉換為響應模型
    
    Args:
        execution_details: 執行詳情字典
        
    Returns:
        TradeExecutionResponse: 交易執行響應模型
    """
    return TradeExecutionResponse(
        execution_id=execution_details["execution_id"],
        order_id=execution_details["order_id"],
        symbol=execution_details["symbol"],
        action=execution_details["action"],
        quantity=execution_details["quantity"],
        price=execution_details["price"],
        amount=execution_details["amount"],
        commission=execution_details["commission"],
        tax=execution_details["tax"],
        net_amount=execution_details["net_amount"],
        execution_time=execution_details["execution_time"],
        broker=execution_details["broker"],
        execution_venue=execution_details["execution_venue"],
    )
