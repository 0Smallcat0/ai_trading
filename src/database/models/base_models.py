"""資料庫基礎模型模組

此模組定義了資料庫的基礎模型、Mixin 類別和枚舉類型。

Classes:
    MarketType: 市場類型枚舉
    TimeGranularity: 時間粒度枚舉
    MarketDataMixin: 市場資料基礎欄位 Mixin

Functions:
    calculate_checksum_before_insert: 插入前計算校驗碼
    calculate_checksum_before_update: 更新前計算校驗碼
    calculate_checksum_before_delete: 刪除前計算校驗碼

Example:
    >>> from src.database.models.base_models import MarketType, MarketDataMixin
    >>> market_type = MarketType.STOCK
    >>> print(market_type.value)
    'stock'
"""

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import (
    Boolean, Column, DateTime, Enum as SQLEnum, Float, Integer, String
)
from sqlalchemy.ext.declarative import declarative_base, declared_attr

# 創建基礎模型類
Base = declarative_base()


class MarketType(Enum):
    """市場類型枚舉

    定義不同的市場類型，用於區分股票、期貨、選擇權等不同金融商品。

    Attributes:
        STOCK: 股票市場
        FUTURES: 期貨市場
        FOREX: 外匯市場
        CRYPTO: 加密貨幣市場
        BOND: 債券市場
        COMMODITY: 商品市場
        INDEX: 指數市場
        OPTION: 選擇權市場

    Example:
        >>> market_type = MarketType.STOCK
        >>> print(market_type.value)
        'stock'
    """
    STOCK = "stock"
    FUTURES = "futures"
    FOREX = "forex"
    CRYPTO = "crypto"
    BOND = "bond"
    COMMODITY = "commodity"
    INDEX = "index"
    OPTION = "option"


class TimeGranularity(Enum):
    """時間粒度枚舉

    定義不同的時間粒度，用於市場資料的時間間隔設定。

    Attributes:
        TICK: Tick 級別（即時）
        SEC_1: 1 秒
        SEC_5: 5 秒
        SEC_15: 15 秒
        SEC_30: 30 秒
        MIN_1: 1 分鐘
        MIN_5: 5 分鐘
        MIN_15: 15 分鐘
        MIN_30: 30 分鐘
        HOUR_1: 1 小時
        HOUR_4: 4 小時
        DAY_1: 1 天
        WEEK_1: 1 週
        MONTH_1: 1 個月

    Example:
        >>> granularity = TimeGranularity.MIN_1
        >>> print(granularity.value)
        '1min'
    """
    TICK = "tick"
    SEC_1 = "1sec"
    SEC_5 = "5sec"
    SEC_15 = "15sec"
    SEC_30 = "30sec"
    MIN_1 = "1min"
    MIN_5 = "5min"
    MIN_15 = "15min"
    MIN_30 = "30min"
    HOUR_1 = "1hour"
    HOUR_4 = "4hour"
    DAY_1 = "1day"
    WEEK_1 = "1week"
    MONTH_1 = "1month"


class MarketDataMixin:
    """市場資料基礎欄位 Mixin

    提供市場資料表的基礎欄位定義，包括 OHLCV 資料、資料完整性欄位等。

    Attributes:
        id: 主鍵
        symbol: 交易標的代碼
        market_type: 市場類型
        open: 開盤價
        high: 最高價
        low: 最低價
        close: 收盤價
        volume: 成交量
        data_source: 資料來源
        is_adjusted: 是否為調整後價格
        checksum: 資料校驗碼
        created_at: 資料建立時間
        updated_at: 資料更新時間

    Methods:
        calculate_checksum: 計算資料校驗碼

    Example:
        >>> class MyMarketData(Base, MarketDataMixin):
        ...     __tablename__ = 'my_market_data'
        ...     date = Column(Date, nullable=False)
    """

    @declared_attr
    def __tablename__(cls) -> str:  # pylint: disable=no-self-argument
        """動態生成表名

        Args:
            cls: 類別物件

        Returns:
            str: 表名（類別名稱的小寫形式）
        """
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment="交易標的代碼")
    market_type = Column(
        SQLEnum(MarketType), nullable=False, index=True, comment="市場類型"
    )

    # OHLCV 基本欄位
    open = Column(Float, comment="開盤價")
    high = Column(Float, comment="最高價")
    low = Column(Float, comment="最低價")
    close = Column(Float, comment="收盤價")
    volume = Column(Float, comment="成交量")

    # 資料完整性欄位
    data_source = Column(String(50), comment="資料來源")
    is_adjusted = Column(Boolean, default=False, comment="是否為調整後價格")
    checksum = Column(String(64), comment="資料校驗碼")

    # 資料管理欄位
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="資料建立時間"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="資料更新時間",
    )

    def calculate_checksum(self) -> str:
        """計算資料校驗碼

        使用 SHA-256 演算法計算資料的校驗碼，用於資料完整性驗證。

        Returns:
            str: 64 位元的十六進制校驗碼

        Example:
            >>> data = MyMarketData(symbol="2330.TW", open=500.0, close=505.0)
            >>> checksum = data.calculate_checksum()
            >>> len(checksum)
            64
        """
        data = {
            "symbol": self.symbol,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }

        # 將資料序列化為 JSON 字串並計算 SHA-256
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()


# SQLAlchemy 事件處理函數
def calculate_checksum_before_insert(
    _mapper: Any, _connection: Any, target: Any
) -> None:
    """插入前計算校驗碼

    在資料插入資料庫前自動計算校驗碼。

    Args:
        _mapper: SQLAlchemy mapper 物件
        _connection: 資料庫連接物件
        target: 目標資料物件

    Note:
        此函數會在 SQLAlchemy 的 before_insert 事件中被調用。
    """
    if hasattr(target, 'calculate_checksum'):
        target.checksum = target.calculate_checksum()


def calculate_checksum_before_update(
    _mapper: Any, _connection: Any, target: Any
) -> None:
    """更新前計算校驗碼

    在資料更新前自動重新計算校驗碼。

    Args:
        _mapper: SQLAlchemy mapper 物件
        _connection: 資料庫連接物件
        target: 目標資料物件

    Note:
        此函數會在 SQLAlchemy 的 before_update 事件中被調用。
    """
    if hasattr(target, 'calculate_checksum'):
        target.checksum = target.calculate_checksum()


def calculate_checksum_before_delete(
    _mapper: Any, _connection: Any, _target: Any
) -> None:
    """刪除前記錄校驗碼

    在資料刪除前記錄最後的校驗碼，用於審計追蹤。

    Args:
        _mapper: SQLAlchemy mapper 物件
        _connection: 資料庫連接物件
        _target: 目標資料物件

    Note:
        此函數會在 SQLAlchemy 的 before_delete 事件中被調用。
    """
    # 這裡可以添加刪除前的校驗碼記錄邏輯
