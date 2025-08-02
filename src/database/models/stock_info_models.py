"""股票基本資訊模型模組

此模組定義了股票基本資訊相關的資料模型。

Classes:
    StockStatus: 股票狀態枚舉
    StockInfo: 股票基本資訊模型

Example:
    >>> from src.database.models.stock_info_models import StockInfo, StockStatus
    >>> stock = StockInfo(
    ...     stock_code="2330.TW",
    ...     stock_name="台積電",
    ...     market="TWSE",
    ...     sector="半導體"
    ... )
"""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import (
    Column, Date, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
)
from sqlalchemy.orm import validates

from .base_models import Base


class StockStatus(Enum):
    """股票狀態枚舉

    定義股票的交易狀態。

    Attributes:
        ACTIVE: 正常交易
        SUSPENDED: 暫停交易
        DELISTED: 下市
        HALT: 停牌
        WARNING: 警示股
        DISPOSAL: 處置股

    Example:
        >>> status = StockStatus.ACTIVE
        >>> print(status.value)
        'active'
    """
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELISTED = "delisted"
    HALT = "halt"
    WARNING = "warning"
    DISPOSAL = "disposal"


class StockInfo(Base):
    """股票基本資訊模型

    儲存股票的基本資訊，包括股票代碼、名稱、市場別、產業別等。

    Attributes:
        id: 主鍵
        stock_code: 股票代碼（如 "2330.TW"）
        stock_name: 股票名稱（如 "台積電"）
        english_name: 英文名稱
        market: 市場別（如 "TWSE", "OTC"）
        sector: 產業別（如 "半導體"）
        industry: 細分行業
        listing_date: 上市日期
        status: 股票狀態
        currency: 交易幣別
        lot_size: 交易單位
        tick_size: 最小跳動單位
        description: 公司描述
        website: 公司網站
        created_at: 資料建立時間
        updated_at: 資料更新時間

    Methods:
        __repr__: 字串表示
        is_active: 檢查是否為正常交易狀態
        get_display_name: 取得顯示名稱

    Example:
        >>> stock = StockInfo(
        ...     stock_code="2330.TW",
        ...     stock_name="台積電",
        ...     market="TWSE",
        ...     sector="半導體"
        ... )
        >>> print(stock.get_display_name())
        '2330.TW 台積電'
    """

    __tablename__ = "stock_info"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 基本識別資訊
    stock_code = Column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
        comment="股票代碼"
    )
    stock_name = Column(String(100), nullable=False, comment="股票名稱")
    english_name = Column(String(200), comment="英文名稱")

    # 市場資訊
    market = Column(String(20), nullable=False, index=True, comment="市場別")
    sector = Column(String(50), index=True, comment="產業別")
    industry = Column(String(100), comment="細分行業")

    # 上市資訊
    listing_date = Column(Date, comment="上市日期")
    status = Column(
        String(20),
        default=StockStatus.ACTIVE.value,
        index=True,
        comment="股票狀態"
    )

    # 交易資訊
    currency = Column(String(10), default="TWD", comment="交易幣別")
    lot_size = Column(Integer, default=1000, comment="交易單位")
    tick_size = Column(Float, default=0.01, comment="最小跳動單位")

    # 其他資訊
    description = Column(Text, comment="公司描述")
    website = Column(String(200), comment="公司網站")

    # 資料管理欄位
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        comment="資料建立時間"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="資料更新時間",
    )

    # 創建索引和約束
    __table_args__ = (
        Index("ix_stock_info_market_sector", "market", "sector"),
        UniqueConstraint("stock_code", name="uq_stock_info_code"),
        {"comment": "股票基本資訊表，記錄股票的基本資料"},
    )

    @validates('stock_code')
    def validate_stock_code(self, _key: str, value: str) -> str:
        """驗證股票代碼格式

        Args:
            _key: 欄位名稱
            value: 股票代碼值

        Returns:
            str: 驗證後的股票代碼

        Raises:
            ValueError: 當股票代碼格式不正確時

        Example:
            >>> stock = StockInfo()
            >>> stock.stock_code = "2330.TW"  # 正確格式
            >>> stock.stock_code = "invalid"  # 會拋出 ValueError
        """
        if not value:
            raise ValueError("股票代碼不能為空")

        # 基本格式檢查
        if len(value) < 3:
            raise ValueError("股票代碼長度不能少於 3 個字元")

        return value.upper()

    @validates('status')
    def validate_status(self, _key: str, value: str) -> str:
        """驗證股票狀態

        Args:
            _key: 欄位名稱
            value: 狀態值

        Returns:
            str: 驗證後的狀態值

        Raises:
            ValueError: 當狀態值不在允許範圍內時
        """
        valid_statuses = [status.value for status in StockStatus]
        if value not in valid_statuses:
            raise ValueError(
                f"無效的股票狀態: {value}，允許的值: {valid_statuses}"
            )

        return value

    def __repr__(self) -> str:
        """字串表示

        Returns:
            str: 股票資訊的字串表示

        Example:
            >>> stock = StockInfo(stock_code="2330.TW", stock_name="台積電")
            >>> print(repr(stock))
            <StockInfo(code=2330.TW, name=台積電, market=None)>
        """
        return (f"<StockInfo(code={self.stock_code}, "
                f"name={self.stock_name}, market={self.market})>")

    def is_active(self) -> bool:
        """檢查是否為正常交易狀態

        Returns:
            bool: True 如果股票處於正常交易狀態，否則 False

        Example:
            >>> stock = StockInfo(status=StockStatus.ACTIVE.value)
            >>> stock.is_active()
            True
        """
        return self.status == StockStatus.ACTIVE.value

    def get_display_name(self) -> str:
        """取得顯示名稱

        Returns:
            str: 格式化的顯示名稱（代碼 + 名稱）

        Example:
            >>> stock = StockInfo(stock_code="2330.TW", stock_name="台積電")
            >>> stock.get_display_name()
            '2330.TW 台積電'
        """
        return f"{self.stock_code} {self.stock_name}"

    def to_dict(self) -> dict:
        """轉換為字典格式

        Returns:
            dict: 包含股票資訊的字典

        Example:
            >>> stock = StockInfo(stock_code="2330.TW", stock_name="台積電")
            >>> data = stock.to_dict()
            >>> data['stock_code']
            '2330.TW'
        """
        return {
            'id': self.id,
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'english_name': self.english_name,
            'market': self.market,
            'sector': self.sector,
            'industry': self.industry,
            'listing_date': (self.listing_date.isoformat()
                             if self.listing_date else None),
            'status': self.status,
            'currency': self.currency,
            'lot_size': self.lot_size,
            'tick_size': self.tick_size,
            'description': self.description,
            'website': self.website,
            'created_at': (self.created_at.isoformat()
                           if self.created_at else None),
            'updated_at': (self.updated_at.isoformat()
                           if self.updated_at else None),
        }
