# type: ignore
# -*- coding: utf-8 -*-
"""
資料庫schema定義

此模組定義了交易系統所需的資料庫結構，包括：
- 不同時間粒度的市場資料表（Tick、分鐘、日線）
- 基本面資料表
- 技術指標資料表
- 新聞情緒資料表
- 交易記錄表
- 系統日誌表

支持多種時間粒度的時間序列資料，並使用複合索引優化查詢效能。
同時實現了資料分片策略和資料完整性機制。
"""

import enum
import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import declarative_base

# type: ignore[misc, valid-type]
Base = declarative_base()


# 定義時間粒度枚舉
class TimeGranularity(enum.Enum):
    """時間粒度枚舉"""

    TICK = "tick"
    MIN_1 = "1min"
    MIN_5 = "5min"
    MIN_15 = "15min"
    MIN_30 = "30min"
    HOUR_1 = "1hour"
    HOUR_4 = "4hour"
    DAY_1 = "1day"
    WEEK_1 = "1week"
    MONTH_1 = "1month"


# 定義市場類型枚舉
class MarketType(enum.Enum):
    """市場類型枚舉"""

    STOCK = "stock"
    FUTURES = "futures"
    FOREX = "forex"
    CRYPTO = "crypto"
    INDEX = "index"
    OPTION = "option"


# 定義基礎市場資料模型 Mixin
class MarketDataMixin:
    """市場資料基礎欄位 Mixin"""

    @declared_attr
    def __tablename__(cls):
    """
    __tablename__
    
    Args:
        cls: 
    """
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment="交易標的代碼")
    market_type = Column(
        Enum(MarketType), nullable=False, index=True, comment="市場類型"
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
        """計算資料校驗碼"""
        data = {
            "symbol": self.symbol,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def __repr__(self):
    """
    __repr__
    
    """
        return f"<{self.__class__.__name__}(symbol={self.symbol}, timestamp={getattr(self, 'timestamp', None) or getattr(self, 'date', None)})>"


# 定義 Tick 資料表
class MarketTick(Base, MarketDataMixin):
    """
    市場 Tick 資料表

    記錄每筆交易的詳細資訊，包括價格、成交量、買賣方向等。
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


# 定義分鐘資料表
class MarketMinute(Base, MarketDataMixin):
    """
    市場分鐘資料表

    記錄分鐘級別的 K 線資料，支援 1 分鐘、5 分鐘、15 分鐘等多種時間粒度。
    """

    __tablename__ = "market_minute"

    timestamp = Column(DateTime, nullable=False, comment="K線時間戳")
    granularity = Column(Enum(TimeGranularity), nullable=False, comment="時間粒度")
    vwap = Column(Float, comment="成交量加權平均價")
    turnover = Column(Float, comment="成交額")
    open_interest = Column(Float, comment="未平倉量 (期貨/選擇權)")

    # 創建複合索引 (symbol + timestamp + granularity)
    __table_args__ = (
        Index("ix_market_minute_symbol_timestamp", "symbol", "timestamp"),
        Index(
            "ix_market_minute_symbol_granularity_timestamp",
            "symbol",
            "granularity",
            "timestamp",
        ),
        {"comment": "市場分鐘資料表，記錄分鐘級別的 K 線資料"},
    )


# 定義日線資料表
class MarketDaily(Base, MarketDataMixin):
    """
    市場日線資料表

    記錄日線級別的 K 線資料，包括開高低收、成交量、技術指標等。
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


# 定義基本面資料表
class Fundamental(Base):
    """
    基本面資料表

    記錄公司的基本面資料，如財務報表、股本結構、股利政策等。
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
        DateTime, default=lambda: datetime.now(timezone.utc), comment="資料建立時間"
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

    def __repr__(self):
    """
    __repr__
    
    """
        return f"<Fundamental(symbol={self.symbol}, date={self.date})>"


# 定義技術指標資料表
class TechnicalIndicator(Base):
    """
    技術指標資料表

    記錄各種技術指標的計算結果，如 MACD、RSI、布林帶等。
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

    # 成交量指標
    obv = Column(Float, comment="能量潮指標")

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

    # 創建複合索引 (symbol + date)
    __table_args__ = (
        Index("ix_technical_indicator_symbol_date", "symbol", "date"),
        UniqueConstraint("symbol", "date", name="uq_technical_indicator_symbol_date"),
        {"comment": "技術指標資料表，記錄各種技術指標的計算結果"},
    )

    def __repr__(self):
    """
    __repr__
    
    """
        return f"<TechnicalIndicator(symbol={self.symbol}, date={self.date})>"


# 定義新聞情緒資料表
class NewsSentiment(Base):
    """
    新聞情緒資料表

    記錄與特定股票相關的新聞情緒分析結果。
    """

    __tablename__ = "news_sentiment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment="股票代碼")
    date = Column(Date, nullable=False, comment="資料日期")

    # 情緒分析
    sentiment_score = Column(Float, comment="情緒分數 (-1 到 1)")
    positive_count = Column(Integer, comment="正面新聞數量")
    negative_count = Column(Integer, comment="負面新聞數量")
    neutral_count = Column(Integer, comment="中性新聞數量")

    # 新聞摘要
    news_summary = Column(Text, comment="新聞摘要")
    news_sources = Column(JSON, comment="新聞來源列表")

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

    # 創建複合索引 (symbol + date)
    __table_args__ = (
        Index("ix_news_sentiment_symbol_date", "symbol", "date"),
        {"comment": "新聞情緒資料表，記錄與特定股票相關的新聞情緒分析結果"},
    )

    def __repr__(self):
    """
    __repr__
    
    """
        return f"<NewsSentiment(symbol={self.symbol}, date={self.date}, score={self.sentiment_score})>"


# 定義交易記錄表
class TradeRecord(Base):
    """
    交易記錄表

    記錄系統執行的所有交易，包括買入、賣出、持倉等資訊。
    """

    __tablename__ = "trade_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True, comment="股票代碼")
    timestamp = Column(DateTime, nullable=False, comment="交易時間戳")

    # 交易資訊
    action = Column(String(10), nullable=False, comment="交易動作 (buy/sell)")
    price = Column(Float, nullable=False, comment="交易價格")
    quantity = Column(Float, nullable=False, comment="交易數量")
    amount = Column(Float, comment="交易金額")

    # 交易成本
    commission = Column(Float, comment="手續費")
    tax = Column(Float, comment="交易稅")
    slippage = Column(Float, comment="滑價")

    # 策略資訊
    strategy_name = Column(String(50), comment="策略名稱")
    signal_id = Column(String(50), comment="信號 ID")

    # 交易結果
    profit_loss = Column(Float, comment="損益")
    profit_loss_pct = Column(Float, comment="損益百分比")

    # 資料管理欄位
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="資料建立時間"
    )

    # 創建索引
    __table_args__ = (
        Index("ix_trade_record_timestamp", "timestamp"),
        Index("ix_trade_record_symbol_timestamp", "symbol", "timestamp"),
        {"comment": "交易記錄表，記錄系統執行的所有交易"},
    )

    def __repr__(self):
    """
    __repr__
    
    """
        return f"<TradeRecord(symbol={self.symbol}, action={self.action}, timestamp={self.timestamp})>"


# 定義系統日誌表
class SystemLog(Base):
    """
    系統日誌表

    記錄系統運行過程中的各種日誌，包括錯誤、警告、資訊等。
    """

    __tablename__ = "system_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True, comment="日誌時間戳")

    # 日誌資訊
    level = Column(
        String(10), nullable=False, comment="日誌級別 (INFO/WARNING/ERROR/CRITICAL)"
    )
    module = Column(String(50), comment="模組名稱")
    message = Column(Text, nullable=False, comment="日誌訊息")

    # 詳細資訊
    details = Column(JSON, comment="詳細資訊")
    stack_trace = Column(Text, comment="堆疊追蹤")

    # 創建索引
    __table_args__ = (
        Index("ix_system_log_level_timestamp", "level", "timestamp"),
        {"comment": "系統日誌表，記錄系統運行過程中的各種日誌"},
    )

    def __repr__(self):
    """
    __repr__
    
    """
        return f"<SystemLog(level={self.level}, timestamp={self.timestamp})>"


# 定義資料分片表
class DataShard(Base):
    """
    資料分片表

    記錄資料分片的相關資訊，用於管理大型資料集的分片策略。
    """

    __tablename__ = "data_shard"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50), nullable=False, comment="資料表名稱")
    shard_key = Column(String(50), nullable=False, comment="分片鍵")
    shard_id = Column(String(50), nullable=False, comment="分片 ID")

    # 分片範圍
    start_date = Column(Date, comment="開始日期")
    end_date = Column(Date, comment="結束日期")

    # 分片資訊
    row_count = Column(Integer, comment="資料列數")
    file_path = Column(String(255), comment="檔案路徑")
    file_format = Column(String(20), comment="檔案格式 (parquet/arrow/csv)")
    file_size_bytes = Column(Integer, comment="檔案大小 (位元組)")

    # 壓縮資訊
    compression = Column(String(20), comment="壓縮方式 (snappy/gzip/none)")
    is_compressed = Column(Boolean, default=False, comment="是否已壓縮")

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

    # 創建索引
    __table_args__ = (
        Index("ix_data_shard_table_shard", "table_name", "shard_id"),
        {"comment": "資料分片表，記錄資料分片的相關資訊"},
    )

    def __repr__(self):
    """
    __repr__
    
    """
        return f"<DataShard(table={self.table_name}, shard_id={self.shard_id})>"


# 定義資料校驗表
class DataChecksum(Base):
    """
    資料校驗表

    記錄資料的校驗碼，用於驗證資料的完整性和一致性。
    """

    __tablename__ = "data_checksum"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(50), nullable=False, comment="資料表名稱")
    record_id = Column(Integer, nullable=False, comment="記錄 ID")

    # 校驗資訊
    checksum = Column(String(64), nullable=False, comment="校驗碼 (SHA-256)")
    checksum_fields = Column(JSON, comment="參與校驗的欄位")

    # 資料管理欄位
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="資料建立時間"
    )
    verified_at = Column(DateTime, comment="最後驗證時間")
    is_valid = Column(Boolean, comment="是否有效")

    # 創建索引
    __table_args__ = (
        Index("ix_data_checksum_table_record", "table_name", "record_id"),
        {"comment": "資料校驗表，記錄資料的校驗碼"},
    )

    def __repr__(self):
    """
    __repr__
    
    """
        return f"<DataChecksum(table={self.table_name}, record_id={self.record_id})>"


# 定義資料庫版本表
class DatabaseVersion(Base):
    """
    資料庫版本表

    記錄資料庫結構的版本資訊，用於管理資料庫結構的變更。
    """

    __tablename__ = "database_version"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(20), nullable=False, comment="版本號")

    # 版本資訊
    description = Column(Text, comment="版本描述")
    applied_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="應用時間"
    )

    # 變更資訊
    changes = Column(JSON, comment="變更內容")
    applied_by = Column(String(50), comment="應用者")

    def __repr__(self):
    """
    __repr__
    
    """
        return (
            f"<DatabaseVersion(version={self.version}, applied_at={self.applied_at})>"
        )


# 添加資料庫事件監聽器，用於自動計算校驗碼
@event.listens_for(MarketDaily, "before_insert")
@event.listens_for(MarketDaily, "before_update")
def calculate_market_daily_checksum(mapper, connection, target):
    """在插入或更新 MarketDaily 記錄前計算校驗碼"""
    target.checksum = target.calculate_checksum()


@event.listens_for(MarketMinute, "before_insert")
@event.listens_for(MarketMinute, "before_update")
def calculate_market_minute_checksum(mapper, connection, target):
    """在插入或更新 MarketMinute 記錄前計算校驗碼"""
    target.checksum = target.calculate_checksum()


@event.listens_for(MarketTick, "before_insert")
@event.listens_for(MarketTick, "before_update")
def calculate_market_tick_checksum(mapper, connection, target):
    """在插入或更新 MarketTick 記錄前計算校驗碼"""
    target.checksum = target.calculate_checksum()


# 創建資料庫初始化函數
def init_db(engine):
    """
    初始化資料庫

    創建所有資料表並設置初始資料。

    Args:
        engine: SQLAlchemy 引擎
    """
    # 創建所有資料表
    Base.metadata.create_all(engine)

    # 初始化資料庫版本
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        # 檢查是否已有版本記錄
        version_exists = session.query(DatabaseVersion).first() is not None
        if not version_exists:
            # 添加初始版本記錄
            initial_version = DatabaseVersion(
                version="1.0.0",
                description="初始資料庫結構",
                changes={
                    "tables_created": [
                        table.name for table in Base.metadata.sorted_tables
                    ]
                },
                applied_by="system",
            )
            session.add(initial_version)
            session.commit()


# 創建資料分片函數
def create_data_shard(session, table_name, start_date, end_date, shard_key="date"):
    """
    創建資料分片

    根據日期範圍創建資料分片記錄。

    Args:
        session: SQLAlchemy 會話
        table_name: 資料表名稱
        start_date: 開始日期
        end_date: 結束日期
        shard_key: 分片鍵，預設為 'date'

    Returns:
        DataShard: 創建的資料分片記錄
    """
    # 生成分片 ID
    shard_id = (
        f"{table_name}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
    )

    # 創建分片記錄
    shard = DataShard(
        table_name=table_name,
        shard_key=shard_key,
        shard_id=shard_id,
        start_date=start_date,
        end_date=end_date,
        file_format="parquet",
        compression="snappy",
    )

    session.add(shard)
    return shard
