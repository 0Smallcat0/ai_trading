"""交易系統共用模型

此模組定義了交易系統中使用的所有 Pydantic 模型，包括請求模型和響應模型。
"""

import logging
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


# ==================== 請求模型 ====================


class OrderRequest(BaseModel):
    """交易訂單請求模型

    此模型定義了創建交易訂單時需要的所有參數。

    Attributes:
        symbol: 股票代碼，例如 "2330.TW"
        action: 交易動作，buy 或 sell
        quantity: 交易數量，必須大於 0
        order_type: 訂單類型（market, limit, stop 等）
        price: 價格，限價單必填
        stop_price: 停損價格，停損單必填
        time_in_force: 有效期限
        portfolio_id: 投資組合 ID
        notes: 備註

    Example:
        >>> order = OrderRequest(
        ...     symbol="2330.TW",
        ...     action="buy",
        ...     quantity=1000,
        ...     order_type="limit",
        ...     price=500.0
        ... )
    """

    symbol: str = Field(..., description="股票代碼", example="2330.TW")
    action: str = Field(..., description="交易動作 (buy/sell)")
    quantity: int = Field(..., gt=0, description="交易數量")
    order_type: str = Field(..., description="訂單類型")
    price: Optional[float] = Field(default=None, gt=0, description="價格（限價單必填）")
    stop_price: Optional[float] = Field(default=None, gt=0, description="停損價格")
    time_in_force: str = Field(default="day", description="有效期限")
    portfolio_id: Optional[str] = Field(default=None, description="投資組合 ID")
    notes: Optional[str] = Field(default=None, description="備註")

    @validator("action")
    def validate_action(cls, v):  # pylint: disable=no-self-argument
        """驗證交易動作

        Args:
            v: 待驗證的交易動作

        Returns:
            str: 驗證通過的交易動作

        Raises:
            ValueError: 當交易動作不在允許列表中時
        """
        allowed_actions = ["buy", "sell"]
        if v.lower() not in allowed_actions:
            raise ValueError(f'交易動作必須是: {", ".join(allowed_actions)}')
        return v.lower()

    @validator("order_type")
    def validate_order_type(cls, v):  # pylint: disable=no-self-argument
        """驗證訂單類型

        Args:
            v: 待驗證的訂單類型

        Returns:
            str: 驗證通過的訂單類型

        Raises:
            ValueError: 當訂單類型不在允許列表中時
        """
        allowed_types = ["market", "limit", "stop", "stop_limit", "trailing_stop"]
        if v.lower() not in allowed_types:
            raise ValueError(f'訂單類型必須是: {", ".join(allowed_types)}')
        return v.lower()

    @validator("time_in_force")
    def validate_time_in_force(cls, v):  # pylint: disable=no-self-argument
        """驗證有效期限

        Args:
            v: 待驗證的有效期限

        Returns:
            str: 驗證通過的有效期限

        Raises:
            ValueError: 當有效期限不在允許列表中時
        """
        allowed_tif = ["day", "gtc", "ioc", "fok"]
        if v.lower() not in allowed_tif:
            raise ValueError(f'有效期限必須是: {", ".join(allowed_tif)}')
        return v.lower()

    @validator("price")
    def validate_price_for_limit_order(
        cls, v, values
    ):  # pylint: disable=no-self-argument
        """驗證限價單必須有價格

        Args:
            v: 價格值
            values: 其他欄位值

        Returns:
            float: 驗證通過的價格

        Raises:
            ValueError: 當限價單沒有指定價格時
        """
        if values.get("order_type") in ["limit", "stop_limit"] and v is None:
            raise ValueError("限價單和停損限價單必須指定價格")
        return v

    @validator("stop_price")
    def validate_stop_price_for_stop_order(
        cls, v, values
    ):  # pylint: disable=no-self-argument
        """驗證停損單必須有停損價格

        Args:
            v: 停損價格值
            values: 其他欄位值

        Returns:
            float: 驗證通過的停損價格

        Raises:
            ValueError: 當停損單沒有指定停損價格時
        """
        if (
            values.get("order_type") in ["stop", "stop_limit", "trailing_stop"]
            and v is None
        ):
            raise ValueError("停損單必須指定停損價格")
        return v


class OrderUpdateRequest(BaseModel):
    """訂單修改請求模型

    此模型定義了修改現有訂單時可以更新的欄位。

    Attributes:
        quantity: 新的交易數量
        price: 新的價格
        stop_price: 新的停損價格
        time_in_force: 新的有效期限
        notes: 修改備註

    Note:
        所有欄位都是可選的，只有提供的欄位會被更新
    """

    quantity: Optional[int] = Field(default=None, gt=0, description="新的交易數量")
    price: Optional[float] = Field(default=None, gt=0, description="新的價格")
    stop_price: Optional[float] = Field(default=None, gt=0, description="新的停損價格")
    time_in_force: Optional[str] = Field(default=None, description="新的有效期限")
    notes: Optional[str] = Field(default=None, description="修改備註")

    @validator("time_in_force")
    def validate_time_in_force(cls, v):  # pylint: disable=no-self-argument
        """驗證有效期限

        Args:
            v: 待驗證的有效期限

        Returns:
            str: 驗證通過的有效期限

        Raises:
            ValueError: 當有效期限不在允許列表中時
        """
        if v is not None:
            allowed_tif = ["day", "gtc", "ioc", "fok"]
            if v.lower() not in allowed_tif:
                raise ValueError(f'有效期限必須是: {", ".join(allowed_tif)}')
            return v.lower()
        return v


class TradingModeRequest(BaseModel):
    """交易模式切換請求模型

    此模型定義了切換交易模式時需要的參數。

    Attributes:
        is_simulation: 是否為模擬交易模式
        reason: 切換原因
    """

    is_simulation: bool = Field(..., description="是否為模擬交易模式")
    reason: Optional[str] = Field(default=None, description="切換原因")


class BatchOrderRequest(BaseModel):
    """批量訂單請求模型

    此模型定義了批量創建訂單時需要的參數。

    Attributes:
        orders: 訂單列表，最多 50 個
        execute_all_or_none: 是否全部執行或全部不執行
    """

    orders: List[OrderRequest] = Field(
        ..., min_items=1, max_items=50, description="訂單列表"
    )
    execute_all_or_none: bool = Field(
        default=False, description="是否全部執行或全部不執行"
    )


# ==================== 響應模型 ====================


class OrderResponse(BaseModel):
    """訂單響應模型

    此模型定義了訂單的詳細資訊，用於 API 回應。

    Attributes:
        order_id: 訂單的唯一識別碼
        symbol: 股票代碼
        action: 交易動作
        quantity: 交易數量
        filled_quantity: 已成交數量
        remaining_quantity: 剩餘數量
        order_type: 訂單類型
        price: 價格
        stop_price: 停損價格
        filled_price: 成交價格
        time_in_force: 有效期限
        status: 訂單狀態
        portfolio_id: 投資組合 ID
        created_at: 創建時間
        updated_at: 更新時間
        filled_at: 成交時間
        error_message: 錯誤訊息
        commission: 手續費
        tax: 交易稅
        net_amount: 淨金額
        notes: 備註
    """

    order_id: str = Field(..., description="訂單 ID")
    symbol: str = Field(..., description="股票代碼")
    action: str = Field(..., description="交易動作")
    quantity: int = Field(..., description="交易數量")
    filled_quantity: int = Field(..., description="已成交數量")
    remaining_quantity: int = Field(..., description="剩餘數量")
    order_type: str = Field(..., description="訂單類型")
    price: Optional[float] = Field(default=None, description="價格")
    stop_price: Optional[float] = Field(default=None, description="停損價格")
    filled_price: Optional[float] = Field(default=None, description="成交價格")
    time_in_force: str = Field(..., description="有效期限")
    status: str = Field(..., description="訂單狀態")
    portfolio_id: Optional[str] = Field(default=None, description="投資組合 ID")
    created_at: datetime = Field(..., description="創建時間")
    updated_at: Optional[datetime] = Field(default=None, description="更新時間")
    filled_at: Optional[datetime] = Field(default=None, description="成交時間")
    error_message: Optional[str] = Field(default=None, description="錯誤訊息")
    commission: Optional[float] = Field(default=None, description="手續費")
    tax: Optional[float] = Field(default=None, description="交易稅")
    net_amount: Optional[float] = Field(default=None, description="淨金額")
    notes: Optional[str] = Field(default=None, description="備註")


class TradeExecutionResponse(BaseModel):
    """交易執行響應模型

    此模型定義了交易執行的詳細資訊。

    Attributes:
        execution_id: 執行的唯一識別碼
        order_id: 關聯的訂單 ID
        symbol: 股票代碼
        action: 交易動作
        quantity: 執行數量
        price: 執行價格
        amount: 執行金額
        commission: 手續費
        tax: 交易稅
        net_amount: 淨金額
        execution_time: 執行時間
        broker: 券商
        execution_venue: 執行場所
    """

    execution_id: str = Field(..., description="執行 ID")
    order_id: str = Field(..., description="訂單 ID")
    symbol: str = Field(..., description="股票代碼")
    action: str = Field(..., description="交易動作")
    quantity: int = Field(..., description="執行數量")
    price: float = Field(..., description="執行價格")
    amount: float = Field(..., description="執行金額")
    commission: float = Field(..., description="手續費")
    tax: float = Field(..., description="交易稅")
    net_amount: float = Field(..., description="淨金額")
    execution_time: datetime = Field(..., description="執行時間")
    broker: str = Field(..., description="券商")
    execution_venue: str = Field(..., description="執行場所")


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
