"""市場資料模型模組

此模組定義了市場資料相關的資料模型。

Classes:
    MarketDaily: 日線資料模型
    MarketMinute: 分鐘資料模型
    MarketTick: Tick 資料模型
    Fundamental: 基本面資料模型

Example:
    >>> from src.database.models.market_data_models import MarketDaily
    >>> daily_data = MarketDaily(
    ...     symbol="2330.TW",
    ...     date=date(2023, 1, 1),
    ...     open=500.0,
    ...     close=505.0
    ... )
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column, Date, DateTime, Float, Index, Integer, String,
    UniqueConstraint
)
from sqlalchemy.event import listen

from .base_models import (
    Base, MarketDataMixin, TimeGranularity,
    calculate_checksum_before_insert, calculate_checksum_before_update
)


class MarketDaily(Base, MarketDataMixin):
    """市場日線資料模型

    記錄日線級別的 K 線資料，包括開高低收、成交量、技術指標等。

    Attributes:
        date: 交易日期
        adj_factor: 調整因子
        turnover: 成交額
        ma5: 5日均線
        ma10: 10日均線
        ma20: 20日均線
        ma60: 60日均線

    Example:
        >>> daily_data = MarketDaily(
        ...     symbol="2330.TW",
        ...     market_type=MarketType.STOCK,
        ...     date=date(2023, 1, 1),
        ...     open=500.0,
        ...     close=505.0
        ... )
    """

    __tablename__ = "market_daily"

    date = Column(Date, nullable=False, comment="交易日期")
    adj_factor = Column(Float, comment="調整因子")
    turnover = Column(Float, comment="成交額")

    # 常用技術指標
    ma5 = Column(Float, comment="5日均線")
    ma10 = Column(Float, comment="10日均線")
    ma20 = Column(Float, comment="20日均線")
    ma60 = Column(Float, comment="60日均線")

    # 創建複合索引 (symbol + date)
    __table_args__ = (
        Index("ix_market_daily_symbol_date", "symbol", "date"),
        UniqueConstraint("symbol", "date", name="uq_market_daily_symbol_date"),
        {"comment": "市場日線資料表，記錄日線級別的 K 線資料"},
    )


class MarketMinute(Base, MarketDataMixin):
    """市場分鐘資料模型

    記錄分鐘級別的 K 線資料。

    Attributes:
        timestamp: 時間戳
        granularity: 時間粒度

    Example:
        >>> minute_data = MarketMinute(
        ...     symbol="2330.TW",
        ...     market_type=MarketType.STOCK,
        ...     timestamp=datetime.now(),
        ...     granularity=TimeGranularity.MIN_1
        ... )
    """

    __tablename__ = "market_minute"

    timestamp = Column(DateTime, nullable=False, comment="時間戳")
    granularity = Column(
        String(10),
        nullable=False,
        default="1min",
        comment="時間粒度"
    )

    # 創建複合索引 (symbol + timestamp)
    __table_args__ = (
        Index("ix_market_minute_symbol_timestamp", "symbol", "timestamp"),
        UniqueConstraint(
            "symbol", "timestamp", "granularity",
            name="uq_market_minute_symbol_timestamp_granularity"
        ),
        {"comment": "市場分鐘資料表，記錄分鐘級別的 K 線資料"},
    )


class MarketTick(Base, MarketDataMixin):
    """市場 Tick 資料模型

    記錄每筆交易的詳細資訊，包括價格、成交量、買賣方向等。

    Attributes:
        timestamp: 交易時間戳
        bid_price: 買方出價
        ask_price: 賣方出價
        bid_volume: 買方量
        ask_volume: 賣方量
        direction: 交易方向
        trade_id: 交易ID

    Example:
        >>> tick_data = MarketTick(
        ...     symbol="2330.TW",
        ...     timestamp=datetime.now(),
        ...     bid_price=499.5,
        ...     ask_price=500.5
        ... )
    """

    __tablename__ = "market_tick"

    timestamp = Column(DateTime, nullable=False, comment="交易時間戳")
    bid_price = Column(Float, comment="買方出價")
    ask_price = Column(Float, comment="賣方出價")
    bid_volume = Column(Float, comment="買方量")
    ask_volume = Column(Float, comment="賣方量")
    direction = Column(String(10), comment="交易方向 (buy/sell)")
    trade_id = Column(String(50), comment="交易 ID")

    # 創建複合索引 (symbol + timestamp)
    __table_args__ = (
        Index("ix_market_tick_symbol_timestamp", "symbol", "timestamp"),
        {"comment": "市場 Tick 資料表，記錄每筆交易的詳細資訊"},
    )


class Fundamental(Base):
    """基本面資料模型

    記錄公司的基本面資料，如財務報表、股本結構、股利政策等。

    Attributes:
        symbol: 股票代碼
        date: 資料日期
        pe_ratio: 本益比
        pb_ratio: 股價淨值比
        ps_ratio: 股價營收比
        dividend_yield: 股息殖利率
        roe: 股東權益報酬率
        roa: 資產報酬率
        revenue: 營收
        net_income: 淨利
        eps: 每股盈餘
        book_value: 每股淨值
        market_cap: 市值
        outstanding_shares: 流通股數
        industry: 產業類別

    Example:
        >>> fundamental = Fundamental(
        ...     symbol="2330.TW",
        ...     date=date.today(),
        ...     pe_ratio=15.5,
        ...     market_cap=10000000000
        ... )
    """

    __tablename__ = "fundamental"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment="股票代碼")
    date = Column(Date, nullable=False, comment="資料日期")

    # 財務比率
    pe_ratio = Column(Float, comment="本益比")
    pb_ratio = Column(Float, comment="股價淨值比")
    ps_ratio = Column(Float, comment="股價營收比")
    dividend_yield = Column(Float, comment="股息殖利率")
    roe = Column(Float, comment="股東權益報酬率")
    roa = Column(Float, comment="資產報酬率")

    # 財務數據
    revenue = Column(Float, comment="營收")
    net_income = Column(Float, comment="淨利")
    eps = Column(Float, comment="每股盈餘")
    book_value = Column(Float, comment="每股淨值")

    # 其他資訊
    market_cap = Column(Float, comment="市值")
    outstanding_shares = Column(Float, comment="流通股數")
    industry = Column(String(50), comment="產業類別")

    # 資料管理欄位
    data_source = Column(String(50), comment="資料來源")
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

    # 創建複合索引 (symbol + date)
    __table_args__ = (
        Index("ix_fundamental_symbol_date", "symbol", "date"),
        UniqueConstraint("symbol", "date", name="uq_fundamental_symbol_date"),
        {"comment": "基本面資料表，記錄公司的基本面資料"},
    )

    def __repr__(self) -> str:
        """字串表示

        Returns:
            str: 基本面資料的字串表示
        """
        return f"<Fundamental(symbol={self.symbol}, date={self.date})>"


class TechnicalIndicator(Base):
    """技術指標資料模型

    記錄各種技術指標的計算結果，如 MACD、RSI、布林帶等。

    Attributes:
        symbol: 股票代碼
        date: 資料日期
        macd: MACD 值
        macd_signal: MACD 信號線
        macd_histogram: MACD 柱狀圖
        rsi_6: 6 日 RSI
        rsi_14: 14 日 RSI
        bollinger_upper: 布林帶上軌
        bollinger_middle: 布林帶中軌
        bollinger_lower: 布林帶下軌
        atr: 真實波動幅度均值

    Example:
        >>> indicator = TechnicalIndicator(
        ...     symbol="2330.TW",
        ...     date=date.today(),
        ...     rsi_14=65.5,
        ...     macd=1.2
        ... )
    """

    __tablename__ = "technical_indicator"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment="股票代碼")
    date = Column(Date, nullable=False, comment="資料日期")

    # 趨勢指標
    macd = Column(Float, comment="MACD 值")
    macd_signal = Column(Float, comment="MACD 信號線")
    macd_histogram = Column(Float, comment="MACD 柱狀圖")

    # 動量指標
    rsi_6 = Column(Float, comment="6 日 RSI")
    rsi_14 = Column(Float, comment="14 日 RSI")

    # 波動指標
    bollinger_upper = Column(Float, comment="布林帶上軌")
    bollinger_middle = Column(Float, comment="布林帶中軌")
    bollinger_lower = Column(Float, comment="布林帶下軌")
    atr = Column(Float, comment="真實波動幅度均值")

    # 資料管理欄位
    data_source = Column(String(50), comment="資料來源")
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

    # 創建複合索引 (symbol + date)
    __table_args__ = (
        Index("ix_technical_indicator_symbol_date", "symbol", "date"),
        UniqueConstraint("symbol", "date", name="uq_technical_indicator_symbol_date"),
        {"comment": "技術指標資料表，記錄各種技術指標的計算結果"},
    )

    def __repr__(self) -> str:
        """字串表示

        Returns:
            str: 技術指標資料的字串表示
        """
        return f"<TechnicalIndicator(symbol={self.symbol}, date={self.date})>"


# 註冊事件監聽器
listen(MarketDaily, 'before_insert', calculate_checksum_before_insert)
listen(MarketDaily, 'before_update', calculate_checksum_before_update)
listen(MarketMinute, 'before_insert', calculate_checksum_before_insert)
listen(MarketMinute, 'before_update', calculate_checksum_before_update)
listen(MarketTick, 'before_insert', calculate_checksum_before_insert)
listen(MarketTick, 'before_update', calculate_checksum_before_update)
