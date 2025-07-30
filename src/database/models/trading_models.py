"""交易相關模型模組

此模組定義了交易系統相關的資料模型。

Classes:
    TradeSide: 交易方向枚舉
    OrderType: 訂單類型枚舉
    TradeRecord: 交易記錄模型

Example:
    >>> from src.database.models.trading_models import TradeRecord, TradeSide
    >>> trade = TradeRecord(
    ...     transaction_id="TXN001",
    ...     symbol="2330.TW",
    ...     side=TradeSide.BUY.value,
    ...     quantity=1000,
    ...     price=500.0
    ... )
"""

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    Column, DateTime, Float, Index, Integer, String, Text
)
from sqlalchemy.orm import validates

from .base_models import Base


class TradeSide(Enum):
    """交易方向枚舉

    定義交易的買賣方向。

    Attributes:
        BUY: 買入
        SELL: 賣出

    Example:
        >>> side = TradeSide.BUY
        >>> print(side.value)
        'BUY'
    """
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """訂單類型枚舉

    定義不同的訂單類型。

    Attributes:
        MARKET: 市價單
        LIMIT: 限價單
        STOP: 停損單
        STOP_LIMIT: 停損限價單
        TRAILING_STOP: 追蹤停損單

    Example:
        >>> order_type = OrderType.LIMIT
        >>> print(order_type.value)
        'LIMIT'
    """
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"
    TRAILING_STOP = "TRAILING_STOP"


class TradeRecord(Base):
    """交易記錄模型

    記錄系統執行的所有交易，包括買入、賣出、持倉等資訊。

    Attributes:
        id: 主鍵
        transaction_id: 交易唯一識別碼
        symbol: 股票代碼
        timestamp: 交易時間戳
        side: 交易方向 (BUY/SELL)
        action: 交易動作 (buy/sell) - 保留向後相容性
        quantity: 交易數量
        price: 交易價格
        total_amount: 總金額
        commission: 手續費
        tax: 交易稅
        slippage: 滑價
        order_type: 訂單類型
        strategy_id: 策略ID
        strategy_name: 策略名稱
        portfolio_id: 投資組合ID
        signal_id: 信號ID
        profit_loss: 損益
        profit_loss_pct: 損益百分比
        notes: 備註
        created_at: 資料建立時間

    Methods:
        __repr__: 字串表示
        calculate_total_amount: 計算總金額
        calculate_net_amount: 計算淨金額

    Example:
        >>> trade = TradeRecord(
        ...     transaction_id="TXN001",
        ...     symbol="2330.TW",
        ...     side=TradeSide.BUY.value,
        ...     quantity=1000,
        ...     price=500.0
        ... )
        >>> trade.calculate_total_amount()
        500000.0
    """

    __tablename__ = "trade_record"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 交易識別資訊
    transaction_id = Column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="交易唯一識別碼"
    )
    symbol = Column(String(20), nullable=False, index=True, comment="股票代碼")
    timestamp = Column(DateTime, nullable=False, comment="交易時間戳")

    # 交易資訊
    side = Column(String(10), nullable=False, comment="交易方向 (BUY/SELL)")
    action = Column(String(10), comment="交易動作 (buy/sell) - 向後相容性")
    quantity = Column(Float, nullable=False, comment="交易數量")
    price = Column(Float, nullable=False, comment="交易價格")
    total_amount = Column(Float, comment="總金額")

    # 交易成本
    commission = Column(Float, comment="手續費")
    tax = Column(Float, comment="交易稅")
    slippage = Column(Float, comment="滑價")

    # 訂單資訊
    order_type = Column(String(20), comment="訂單類型")

    # 策略資訊
    strategy_id = Column(String(50), comment="策略ID")
    strategy_name = Column(String(50), comment="策略名稱")
    portfolio_id = Column(String(50), comment="投資組合ID")
    signal_id = Column(String(50), comment="信號ID")

    # 交易結果
    profit_loss = Column(Float, comment="損益")
    profit_loss_pct = Column(Float, comment="損益百分比")

    # 其他資訊
    notes = Column(Text, comment="備註")

    # 資料管理欄位
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="資料建立時間"
    )

    # 創建索引
    __table_args__ = (
        Index("ix_trade_record_timestamp", "timestamp"),
        Index("ix_trade_record_symbol_timestamp", "symbol", "timestamp"),
        Index("ix_trade_record_strategy", "strategy_id"),
        Index("ix_trade_record_portfolio", "portfolio_id"),
        {"comment": "交易記錄表，記錄系統執行的所有交易"},
    )

    def __init__(self, **kwargs):
        """初始化交易記錄

        Args:
            **kwargs: 關鍵字參數
        """
        # 如果沒有提供 transaction_id，自動生成
        if 'transaction_id' not in kwargs:
            kwargs['transaction_id'] = self.generate_transaction_id()

        # 向後相容性：如果提供了 action 但沒有 side，則轉換
        if 'action' in kwargs and 'side' not in kwargs:
            action = kwargs['action'].upper()
            if action == 'BUY':
                kwargs['side'] = TradeSide.BUY.value
            elif action == 'SELL':
                kwargs['side'] = TradeSide.SELL.value

        super().__init__(**kwargs)

    @staticmethod
    def generate_transaction_id() -> str:
        """生成交易ID

        Returns:
            str: 唯一的交易ID

        Example:
            >>> txn_id = TradeRecord.generate_transaction_id()
            >>> len(txn_id)
            36
        """
        return str(uuid.uuid4())

    @validates('side')
    def validate_side(self, _key: str, value: str) -> str:
        """驗證交易方向

        Args:
            key: 欄位名稱
            value: 交易方向值

        Returns:
            str: 驗證後的交易方向

        Raises:
            ValueError: 當交易方向不正確時
        """
        valid_sides = [side.value for side in TradeSide]
        if value not in valid_sides:
            raise ValueError(f"無效的交易方向: {value}，允許的值: {valid_sides}")

        return value

    @validates('order_type')
    def validate_order_type(self, _key: str, value: str) -> str:
        """驗證訂單類型

        Args:
            key: 欄位名稱
            value: 訂單類型值

        Returns:
            str: 驗證後的訂單類型

        Raises:
            ValueError: 當訂單類型不正確時
        """
        if value is None:
            return value

        valid_types = [order_type.value for order_type in OrderType]
        if value not in valid_types:
            raise ValueError(f"無效的訂單類型: {value}，允許的值: {valid_types}")

        return value

    def __repr__(self) -> str:
        """字串表示

        Returns:
            str: 交易記錄的字串表示
        """
        return (f"<TradeRecord(txn_id={self.transaction_id}, "
                f"symbol={self.symbol}, side={self.side}, "
                f"quantity={self.quantity}, price={self.price})>")

    def calculate_total_amount(self) -> float:
        """計算總金額

        Returns:
            float: 總金額（數量 × 價格）

        Example:
            >>> trade = TradeRecord(quantity=1000, price=500.0)
            >>> trade.calculate_total_amount()
            500000.0
        """
        if self.quantity is None or self.price is None:
            return 0.0
        return self.quantity * self.price

    def calculate_net_amount(self) -> float:
        """計算淨金額（扣除手續費和稅費）

        Returns:
            float: 淨金額

        Example:
            >>> trade = TradeRecord(quantity=1000, price=500.0, commission=100, tax=50)
            >>> trade.calculate_net_amount()
            499850.0
        """
        total = self.calculate_total_amount()
        commission = self.commission or 0.0
        tax = self.tax or 0.0
        slippage = self.slippage or 0.0

        return total - commission - tax - slippage

    def to_dict(self) -> dict:
        """轉換為字典格式

        Returns:
            dict: 包含交易記錄的字典
        """
        return {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'symbol': self.symbol,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'side': self.side,
            'action': self.action,
            'quantity': self.quantity,
            'price': self.price,
            'total_amount': self.total_amount,
            'commission': self.commission,
            'tax': self.tax,
            'slippage': self.slippage,
            'order_type': self.order_type,
            'strategy_id': self.strategy_id,
            'strategy_name': self.strategy_name,
            'portfolio_id': self.portfolio_id,
            'signal_id': self.signal_id,
            'profit_loss': self.profit_loss,
            'profit_loss_pct': self.profit_loss_pct,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
