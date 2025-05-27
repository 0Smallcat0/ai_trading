"""
交易統計分析 API

此模組實現交易統計相關的 API 端點，包括訂單統計、績效分析等。
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.core.trade_execution_service import TradeExecutionService

logger = logging.getLogger(__name__)
router = APIRouter()

# 初始化交易執行服務
trade_service = TradeExecutionService()


# ==================== 響應模型 ====================


class OrderStatistics(BaseModel):
    """訂單統計響應模型

    此模型定義了訂單統計的詳細資訊。

    Attributes:
        total_orders: 總訂單數
        pending_orders: 待處理訂單
        filled_orders: 已成交訂單
        cancelled_orders: 已取消訂單
        rejected_orders: 已拒絕訂單
        success_rate: 成功率
        avg_fill_time_seconds: 平均成交時間（秒）
        total_volume: 總交易量
        total_amount: 總交易金額
        total_commission: 總手續費
        total_tax: 總交易稅
        period_start: 統計期間開始
        period_end: 統計期間結束
    """

    total_orders: int = Field(..., description="總訂單數")
    pending_orders: int = Field(..., description="待處理訂單")
    filled_orders: int = Field(..., description="已成交訂單")
    cancelled_orders: int = Field(..., description="已取消訂單")
    rejected_orders: int = Field(..., description="已拒絕訂單")
    success_rate: float = Field(..., description="成功率")
    avg_fill_time_seconds: float = Field(..., description="平均成交時間（秒）")
    total_volume: int = Field(..., description="總交易量")
    total_amount: float = Field(..., description="總交易金額")
    total_commission: float = Field(..., description="總手續費")
    total_tax: float = Field(..., description="總交易稅")
    period_start: datetime = Field(..., description="統計期間開始")
    period_end: datetime = Field(..., description="統計期間結束")


class TradingStatusResponse(BaseModel):
    """交易狀態響應模型

    此模型定義了交易系統的狀態資訊。

    Attributes:
        is_simulation_mode: 是否為模擬交易模式
        broker_connected: 券商是否連接
        current_broker: 當前券商
        trading_session: 交易時段
        market_status: 市場狀態
        pending_orders_count: 待處理訂單數量
        today_orders_count: 今日訂單數量
        today_executions_count: 今日成交數量
        available_cash: 可用資金
        total_position_value: 總持倉價值
        last_update: 最後更新時間
    """

    is_simulation_mode: bool = Field(..., description="是否為模擬交易模式")
    broker_connected: bool = Field(..., description="券商是否連接")
    current_broker: str = Field(..., description="當前券商")
    trading_session: str = Field(..., description="交易時段")
    market_status: str = Field(..., description="市場狀態")
    pending_orders_count: int = Field(..., description="待處理訂單數量")
    today_orders_count: int = Field(..., description="今日訂單數量")
    today_executions_count: int = Field(..., description="今日成交數量")
    available_cash: float = Field(..., description="可用資金")
    total_position_value: float = Field(..., description="總持倉價值")
    last_update: datetime = Field(..., description="最後更新時間")


# ==================== API 端點 ====================


@router.get(
    "/statistics",
    response_model=APIResponse[OrderStatistics],
    responses=COMMON_RESPONSES,
    summary="獲取訂單統計",
    description="獲取指定時間範圍內的訂單統計信息",
)
async def get_order_statistics(
    start_date: Optional[str] = Query(
        default=None, description="開始日期 (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(default=None, description="結束日期 (YYYY-MM-DD)"),
    symbol: Optional[str] = Query(default=None, description="股票代碼篩選"),
    portfolio_id: Optional[str] = Query(default=None, description="投資組合 ID 篩選"),
):
    """獲取訂單統計

    此端點用於獲取指定時間範圍內的訂單統計信息。

    Args:
        start_date: 開始日期
        end_date: 結束日期
        symbol: 股票代碼篩選
        portfolio_id: 投資組合 ID 篩選

    Returns:
        APIResponse[OrderStatistics]: 包含訂單統計的 API 回應

    Raises:
        HTTPException: 當獲取統計失敗時

    Example:
        GET /api/trading/statistics?start_date=2024-01-01&end_date=2024-12-31
    """
    try:
        # 構建篩選條件
        filters = _build_statistics_filters(start_date, end_date, symbol, portfolio_id)

        # 獲取訂單統計
        statistics_data = trade_service.get_order_statistics(filters)

        # 轉換為響應模型
        response_data = OrderStatistics(
            total_orders=statistics_data["total_orders"],
            pending_orders=statistics_data["pending_orders"],
            filled_orders=statistics_data["filled_orders"],
            cancelled_orders=statistics_data["cancelled_orders"],
            rejected_orders=statistics_data["rejected_orders"],
            success_rate=statistics_data["success_rate"],
            avg_fill_time_seconds=statistics_data["avg_fill_time_seconds"],
            total_volume=statistics_data["total_volume"],
            total_amount=statistics_data["total_amount"],
            total_commission=statistics_data["total_commission"],
            total_tax=statistics_data["total_tax"],
            period_start=statistics_data["period_start"],
            period_end=statistics_data["period_end"],
        )

        return APIResponse(success=True, message="訂單統計獲取成功", data=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取訂單統計失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取訂單統計失敗: {str(e)}",
        ) from e


@router.get(
    "/performance",
    response_model=APIResponse[dict],
    responses=COMMON_RESPONSES,
    summary="獲取交易績效",
    description="獲取交易績效分析數據",
)
async def get_trading_performance(
    start_date: Optional[str] = Query(
        default=None, description="開始日期 (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(default=None, description="結束日期 (YYYY-MM-DD)"),
    portfolio_id: Optional[str] = Query(default=None, description="投資組合 ID 篩選"),
):
    """獲取交易績效

    此端點用於獲取交易績效分析數據，包括收益率、夏普比率等指標。

    Args:
        start_date: 開始日期
        end_date: 結束日期
        portfolio_id: 投資組合 ID 篩選

    Returns:
        APIResponse[dict]: 包含交易績效數據的 API 回應

    Raises:
        HTTPException: 當獲取績效失敗時
    """
    try:
        # 構建篩選條件
        filters = _build_statistics_filters(start_date, end_date, None, portfolio_id)

        # 獲取交易績效
        performance_data = trade_service.get_trading_performance(filters)

        return APIResponse(
            success=True, message="交易績效獲取成功", data=performance_data
        )

    except Exception as e:
        logger.error("獲取交易績效失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取交易績效失敗: {str(e)}",
        ) from e


@router.get(
    "/summary",
    response_model=APIResponse[dict],
    responses=COMMON_RESPONSES,
    summary="獲取交易摘要",
    description="獲取交易活動的摘要信息",
)
async def get_trading_summary():
    """獲取交易摘要

    此端點用於獲取當前交易活動的摘要信息。

    Returns:
        APIResponse[dict]: 包含交易摘要的 API 回應

    Raises:
        HTTPException: 當獲取摘要失敗時
    """
    try:
        # 獲取交易狀態
        trading_status = trade_service.get_trading_status()

        # 獲取今日統計
        today_filters = {
            "start_date": datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            ),
            "end_date": datetime.now(),
        }
        today_statistics = trade_service.get_order_statistics(today_filters)

        # 構建摘要數據
        summary_data = {
            "trading_status": {
                "is_simulation_mode": trading_status["is_simulation_mode"],
                "broker_connected": trading_status["broker_connected"],
                "market_status": trading_status["market_status"],
                "available_cash": trading_status["available_cash"],
                "total_position_value": trading_status["total_position_value"],
            },
            "today_statistics": {
                "total_orders": today_statistics["total_orders"],
                "filled_orders": today_statistics["filled_orders"],
                "total_volume": today_statistics["total_volume"],
                "total_amount": today_statistics["total_amount"],
                "success_rate": today_statistics["success_rate"],
            },
        }

        return APIResponse(success=True, message="交易摘要獲取成功", data=summary_data)

    except Exception as e:
        logger.error("獲取交易摘要失敗: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"獲取交易摘要失敗: {str(e)}",
        ) from e


# ==================== 輔助函數 ====================


def _build_statistics_filters(
    start_date: Optional[str],
    end_date: Optional[str],
    symbol: Optional[str],
    portfolio_id: Optional[str],
) -> dict:
    """構建統計篩選條件

    Args:
        start_date: 開始日期
        end_date: 結束日期
        symbol: 股票代碼
        portfolio_id: 投資組合 ID

    Returns:
        dict: 篩選條件字典

    Raises:
        HTTPException: 當日期格式錯誤時
    """
    filters = {}

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

    if symbol:
        filters["symbol"] = symbol
    if portfolio_id:
        filters["portfolio_id"] = portfolio_id

    return filters
