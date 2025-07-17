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
    LargeBinary,
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
    timestamp = Column(DateTime, nullable=False, comment="日誌時間戳")

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


# 定義風險管理參數表
class RiskParameter(Base):
    """
    風險管理參數表

    記錄風險管理的各種參數設置，包括停損停利、資金控管、VaR等設置。
    """

    __tablename__ = "risk_parameter"

    id = Column(Integer, primary_key=True, autoincrement=True)
    parameter_name = Column(String(50), nullable=False, unique=True, comment="參數名稱")
    parameter_value = Column(String(255), comment="參數值")
    parameter_type = Column(String(20), comment="參數類型 (float/int/bool/string)")
    category = Column(
        String(30), comment="參數分類 (stop_loss/position/var/monitoring)"
    )
    description = Column(Text, comment="參數描述")

    # 參數範圍
    min_value = Column(Float, comment="最小值")
    max_value = Column(Float, comment="最大值")
    default_value = Column(String(255), comment="預設值")

    # 狀態管理
    is_active = Column(Boolean, default=True, comment="是否啟用")
    is_system = Column(Boolean, default=False, comment="是否為系統參數")

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
        Index("ix_risk_parameter_category", "category"),
        Index("ix_risk_parameter_active", "is_active"),
        {"comment": "風險管理參數表，記錄風險管理的各種參數設置"},
    )

    def __repr__(self):
        return (
            f"<RiskParameter(name={self.parameter_name}, value={self.parameter_value})>"
        )


# 定義風險事件表
class RiskEvent(Base):
    """
    風險事件表

    記錄系統產生的風險事件，包括停損觸發、VaR超限、回撤警告等。
    """

    __tablename__ = "risk_event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(50), nullable=False, unique=True, comment="事件唯一ID")
    timestamp = Column(DateTime, nullable=False, comment="事件發生時間")

    # 事件基本資訊
    event_type = Column(String(30), nullable=False, comment="事件類型")
    severity = Column(
        String(10), nullable=False, comment="嚴重程度 (low/medium/high/critical)"
    )
    symbol = Column(String(20), comment="相關股票代碼")
    strategy_name = Column(String(50), comment="相關策略名稱")

    # 事件詳情
    trigger_value = Column(Float, comment="觸發值")
    threshold_value = Column(Float, comment="閾值")
    current_value = Column(Float, comment="當前值")
    message = Column(Text, comment="事件訊息")
    details = Column(JSON, comment="事件詳細資訊")

    # 處理狀態
    status = Column(
        String(20),
        default="pending",
        comment="處理狀態 (pending/processing/resolved/ignored)",
    )
    action_taken = Column(String(100), comment="已採取的動作")
    resolved_at = Column(DateTime, comment="解決時間")
    resolved_by = Column(String(50), comment="解決人員")

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
        Index("ix_risk_event_timestamp", "timestamp"),
        Index("ix_risk_event_type_severity", "event_type", "severity"),
        Index("ix_risk_event_symbol_timestamp", "symbol", "timestamp"),
        Index("ix_risk_event_status", "status"),
        {"comment": "風險事件表，記錄系統產生的風險事件"},
    )

    def __repr__(self):
        return f"<RiskEvent(id={self.event_id}, type={self.event_type}, timestamp={self.timestamp})>"


# 定義風險指標表
class RiskMetric(Base):
    """
    風險指標表

    記錄投資組合的風險指標計算結果，如VaR、最大回撤、夏普比率等。
    """

    __tablename__ = "risk_metric"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, comment="計算日期")
    symbol = Column(String(20), comment="股票代碼，NULL表示投資組合整體")

    # 基本風險指標
    var_95_1day = Column(Float, comment="95% VaR (1日)")
    var_99_1day = Column(Float, comment="99% VaR (1日)")
    cvar_95_1day = Column(Float, comment="95% CVaR (1日)")
    max_drawdown = Column(Float, comment="最大回撤")
    current_drawdown = Column(Float, comment="當前回撤")

    # 績效指標
    volatility = Column(Float, comment="年化波動率")
    sharpe_ratio = Column(Float, comment="夏普比率")
    sortino_ratio = Column(Float, comment="索提諾比率")
    calmar_ratio = Column(Float, comment="卡瑪比率")

    # 相關性指標
    beta = Column(Float, comment="Beta係數")
    correlation_with_market = Column(Float, comment="與市場相關性")
    tracking_error = Column(Float, comment="追蹤誤差")

    # 部位風險指標
    position_concentration = Column(Float, comment="部位集中度")
    sector_concentration = Column(Float, comment="行業集中度")
    avg_correlation = Column(Float, comment="平均相關性")

    # 計算參數
    calculation_method = Column(String(30), comment="計算方法")
    lookback_days = Column(Integer, comment="回顧天數")
    confidence_level = Column(Float, comment="信心水準")

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
        Index("ix_risk_metric_date", "date"),
        Index("ix_risk_metric_symbol_date", "symbol", "date"),
        UniqueConstraint("date", "symbol", name="uq_risk_metric_date_symbol"),
        {"comment": "風險指標表，記錄投資組合的風險指標計算結果"},
    )

    def __repr__(self):
        return f"<RiskMetric(date={self.date}, symbol={self.symbol})>"


# 定義風險控制狀態表
class RiskControlStatus(Base):
    """
    風險控制狀態表

    記錄各種風險控制機制的啟用狀態和配置。
    """

    __tablename__ = "risk_control_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    control_name = Column(
        String(50), nullable=False, unique=True, comment="風控機制名稱"
    )
    control_type = Column(String(30), nullable=False, comment="風控類型")

    # 狀態控制
    is_enabled = Column(Boolean, default=True, comment="是否啟用")
    is_master_enabled = Column(Boolean, default=True, comment="主開關是否啟用")
    emergency_stop = Column(Boolean, default=False, comment="緊急停止狀態")

    # 配置參數
    config_json = Column(JSON, comment="配置參數JSON")
    threshold_values = Column(JSON, comment="閾值設定JSON")

    # 運行狀態
    last_check_time = Column(DateTime, comment="最後檢查時間")
    last_trigger_time = Column(DateTime, comment="最後觸發時間")
    trigger_count = Column(Integer, default=0, comment="觸發次數")

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
        Index("ix_risk_control_type", "control_type"),
        Index("ix_risk_control_enabled", "is_enabled"),
        {"comment": "風險控制狀態表，記錄各種風險控制機制的啟用狀態和配置"},
    )

    def __repr__(self):
        return (
            f"<RiskControlStatus(name={self.control_name}, enabled={self.is_enabled})>"
        )


# 定義交易訂單表
class TradingOrder(Base):
    """
    交易訂單表

    記錄所有交易訂單的詳細資訊，包括委託、成交、取消等狀態。
    """

    __tablename__ = "trading_order"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(50), nullable=False, unique=True, comment="訂單唯一ID")
    exchange_order_id = Column(String(50), comment="交易所訂單ID")

    # 基本訂單資訊
    symbol = Column(String(20), nullable=False, index=True, comment="股票代碼")
    action = Column(String(10), nullable=False, comment="交易方向 (buy/sell)")
    order_type = Column(
        String(20), nullable=False, comment="訂單類型 (market/limit/stop/stop_limit)"
    )
    time_in_force = Column(
        String(10), default="ROD", comment="訂單有效期 (ROD/IOC/FOK)"
    )

    # 數量和價格
    quantity = Column(Integer, nullable=False, comment="委託數量（股）")
    price = Column(Float, comment="委託價格")
    stop_price = Column(Float, comment="停損價格")

    # 成交資訊
    filled_quantity = Column(Integer, default=0, comment="已成交數量")
    filled_price = Column(Float, comment="成交價格")
    filled_amount = Column(Float, comment="成交金額")

    # 費用
    commission = Column(Float, comment="手續費")
    tax = Column(Float, comment="交易稅")
    total_cost = Column(Float, comment="總成本")

    # 訂單狀態
    status = Column(String(20), default="pending", comment="訂單狀態")
    error_message = Column(Text, comment="錯誤訊息")

    # 策略資訊
    strategy_name = Column(String(50), comment="策略名稱")
    signal_id = Column(String(50), comment="信號ID")

    # 交易模式
    is_simulation = Column(Boolean, default=True, comment="是否為模擬交易")
    broker_name = Column(String(30), comment="券商名稱")

    # 風險控制
    risk_check_passed = Column(Boolean, default=False, comment="風險檢查是否通過")
    risk_check_details = Column(JSON, comment="風險檢查詳情")

    # 時間戳
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="訂單創建時間"
    )
    submitted_at = Column(DateTime, comment="訂單提交時間")
    filled_at = Column(DateTime, comment="訂單成交時間")
    cancelled_at = Column(DateTime, comment="訂單取消時間")
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="資料更新時間",
    )

    # 創建索引
    __table_args__ = (
        Index("ix_trading_order_symbol_created", "symbol", "created_at"),
        Index("ix_trading_order_status_created", "status", "created_at"),
        Index("ix_trading_order_simulation", "is_simulation"),
        Index("ix_trading_order_strategy", "strategy_name"),
        {"comment": "交易訂單表，記錄所有交易訂單的詳細資訊"},
    )

    def __repr__(self):
        return f"<TradingOrder(id={self.order_id}, symbol={self.symbol}, action={self.action})>"


# 定義交易成交記錄表
class TradeExecution(Base):
    """
    交易成交記錄表

    記錄訂單的成交明細，一個訂單可能有多筆成交記錄。
    """

    __tablename__ = "trade_execution"

    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String(50), nullable=False, unique=True, comment="成交唯一ID")
    order_id = Column(String(50), nullable=False, index=True, comment="關聯訂單ID")
    exchange_execution_id = Column(String(50), comment="交易所成交ID")

    # 成交資訊
    symbol = Column(String(20), nullable=False, index=True, comment="股票代碼")
    action = Column(String(10), nullable=False, comment="交易方向")
    quantity = Column(Integer, nullable=False, comment="成交數量")
    price = Column(Float, nullable=False, comment="成交價格")
    amount = Column(Float, nullable=False, comment="成交金額")

    # 費用明細
    commission = Column(Float, comment="手續費")
    tax = Column(Float, comment="交易稅")
    other_fees = Column(Float, comment="其他費用")
    net_amount = Column(Float, comment="淨成交金額")

    # 市場資訊
    market_price = Column(Float, comment="市場價格")
    slippage = Column(Float, comment="滑價")

    # 時間戳
    execution_time = Column(DateTime, nullable=False, index=True, comment="成交時間")
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="記錄創建時間"
    )

    # 創建索引
    __table_args__ = (
        Index("ix_trade_execution_symbol_time", "symbol", "execution_time"),
        Index("ix_trade_execution_order_time", "order_id", "execution_time"),
        {"comment": "交易成交記錄表，記錄訂單的成交明細"},
    )

    def __repr__(self):
        return f"<TradeExecution(id={self.execution_id}, symbol={self.symbol}, quantity={self.quantity})>"


# 定義交易執行日誌表
class ExecutionLog(Base):
    """
    交易執行日誌表

    記錄交易執行過程中的各種事件和狀態變化。
    """

    __tablename__ = "execution_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(String(50), nullable=False, unique=True, comment="日誌唯一ID")
    timestamp = Column(DateTime, nullable=False, comment="日誌時間")

    # 關聯資訊
    order_id = Column(String(50), index=True, comment="關聯訂單ID")
    execution_id = Column(String(50), comment="關聯成交ID")

    # 日誌內容
    event_type = Column(String(30), nullable=False, comment="事件類型")
    level = Column(String(10), nullable=False, comment="日誌級別")
    message = Column(Text, nullable=False, comment="日誌訊息")
    details = Column(JSON, comment="詳細資訊")

    # 系統資訊
    module = Column(String(50), comment="模組名稱")
    function = Column(String(50), comment="函數名稱")
    broker_name = Column(String(30), comment="券商名稱")

    # 錯誤資訊
    error_code = Column(String(20), comment="錯誤代碼")
    stack_trace = Column(Text, comment="堆疊追蹤")

    # 創建索引
    __table_args__ = (
        Index("ix_execution_log_timestamp", "timestamp"),
        Index("ix_execution_log_order_timestamp", "order_id", "timestamp"),
        Index("ix_execution_log_event_level", "event_type", "level"),
        {"comment": "交易執行日誌表，記錄交易執行過程中的各種事件"},
    )

    def __repr__(self):
        return f"<ExecutionLog(id={self.log_id}, event={self.event_type}, timestamp={self.timestamp})>"


# 定義券商連線狀態表
class BrokerConnection(Base):
    """
    券商連線狀態表

    記錄各券商API的連線狀態和健康檢查資訊。
    """

    __tablename__ = "broker_connection"

    id = Column(Integer, primary_key=True, autoincrement=True)
    broker_name = Column(String(30), nullable=False, unique=True, comment="券商名稱")

    # 連線狀態
    is_connected = Column(Boolean, default=False, comment="是否已連線")
    connection_time = Column(DateTime, comment="連線時間")
    last_heartbeat = Column(DateTime, comment="最後心跳時間")

    # 連線資訊
    api_version = Column(String(20), comment="API版本")
    server_info = Column(JSON, comment="伺服器資訊")
    account_info = Column(JSON, comment="帳戶資訊")

    # 效能指標
    latency_ms = Column(Float, comment="延遲（毫秒）")
    success_rate = Column(Float, comment="成功率")
    error_count = Column(Integer, default=0, comment="錯誤次數")

    # 限制資訊
    daily_order_limit = Column(Integer, comment="每日下單限制")
    daily_order_count = Column(Integer, default=0, comment="今日下單次數")
    rate_limit_per_second = Column(Integer, comment="每秒請求限制")

    # 狀態資訊
    last_error = Column(Text, comment="最後錯誤訊息")
    status_details = Column(JSON, comment="狀態詳情")

    # 時間戳
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="記錄創建時間"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="資料更新時間",
    )

    # 創建索引
    __table_args__ = (
        Index("ix_broker_connection_status", "is_connected"),
        Index("ix_broker_connection_heartbeat", "last_heartbeat"),
        {"comment": "券商連線狀態表，記錄各券商API的連線狀態"},
    )

    def __repr__(self):
        return f"<BrokerConnection(broker={self.broker_name}, connected={self.is_connected})>"


# 定義交易異常事件表
class TradingException(Base):
    """
    交易異常事件表

    記錄交易過程中發生的各種異常事件和處理結果。
    """

    __tablename__ = "trading_exception"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exception_id = Column(
        String(50), nullable=False, unique=True, comment="異常事件唯一ID"
    )
    timestamp = Column(DateTime, nullable=False, comment="異常發生時間")

    # 關聯資訊
    order_id = Column(String(50), index=True, comment="關聯訂單ID")
    symbol = Column(String(20), comment="相關股票代碼")
    broker_name = Column(String(30), comment="券商名稱")

    # 異常分類
    exception_type = Column(String(30), nullable=False, comment="異常類型")
    severity = Column(String(10), nullable=False, comment="嚴重程度")
    category = Column(String(20), comment="異常分類")

    # 異常詳情
    error_code = Column(String(20), comment="錯誤代碼")
    error_message = Column(Text, comment="錯誤訊息")
    exception_details = Column(JSON, comment="異常詳細資訊")

    # 處理狀態
    status = Column(String(20), default="pending", comment="處理狀態")
    auto_retry_count = Column(Integer, default=0, comment="自動重試次數")
    manual_intervention = Column(Boolean, default=False, comment="是否需要人工介入")

    # 處理結果
    resolution = Column(String(100), comment="解決方案")
    resolved_at = Column(DateTime, comment="解決時間")
    resolved_by = Column(String(50), comment="解決人員")

    # 通知狀態
    notification_sent = Column(Boolean, default=False, comment="是否已發送通知")
    notification_methods = Column(JSON, comment="通知方式")

    # 創建索引
    __table_args__ = (
        Index("ix_trading_exception_timestamp", "timestamp"),
        Index("ix_trading_exception_type_severity", "exception_type", "severity"),
        Index("ix_trading_exception_status", "status"),
        Index("ix_trading_exception_order", "order_id"),
        {"comment": "交易異常事件表，記錄交易過程中的異常事件"},
    )

    def __repr__(self):
        return f"<TradingException(id={self.exception_id}, type={self.exception_type}, timestamp={self.timestamp})>"


# 定義系統指標表
class SystemMetric(Base):
    """
    系統指標表

    記錄系統運行的各種指標，包括CPU、記憶體、磁碟、網路等資源使用情況。
    """

    __tablename__ = "system_metric"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, comment="指標時間戳")
    metric_type = Column(String(30), nullable=False, comment="指標類型")

    # 系統資源指標
    cpu_usage = Column(Float, comment="CPU 使用率 (%)")
    memory_usage = Column(Float, comment="記憶體使用率 (%)")
    memory_total = Column(Float, comment="總記憶體 (GB)")
    memory_available = Column(Float, comment="可用記憶體 (GB)")
    disk_usage = Column(Float, comment="磁碟使用率 (%)")
    disk_total = Column(Float, comment="總磁碟空間 (GB)")
    disk_free = Column(Float, comment="可用磁碟空間 (GB)")

    # 網路指標
    network_bytes_sent = Column(Float, comment="網路發送位元組數")
    network_bytes_recv = Column(Float, comment="網路接收位元組數")
    network_packets_sent = Column(Float, comment="網路發送封包數")
    network_packets_recv = Column(Float, comment="網路接收封包數")

    # 應用程式指標
    process_count = Column(Integer, comment="進程數量")
    thread_count = Column(Integer, comment="執行緒數量")
    file_descriptor_count = Column(Integer, comment="檔案描述符數量")

    # 資料庫指標
    db_connections = Column(Integer, comment="資料庫連線數")
    db_query_time = Column(Float, comment="資料庫查詢時間 (ms)")
    db_pool_size = Column(Integer, comment="連線池大小")

    # 自定義指標
    custom_metrics = Column(JSON, comment="自定義指標JSON")

    # 創建索引
    __table_args__ = (
        Index("ix_system_metric_timestamp", "timestamp"),
        Index("ix_system_metric_type_timestamp", "metric_type", "timestamp"),
        {"comment": "系統指標表，記錄系統運行的各種指標"},
    )

    def __repr__(self):
        return f"<SystemMetric(type={self.metric_type}, timestamp={self.timestamp})>"


# 定義效能日誌表
class PerformanceLog(Base):
    """
    效能日誌表

    記錄系統各模組的效能指標，包括響應時間、吞吐量、錯誤率等。
    """

    __tablename__ = "performance_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, comment="日誌時間戳")

    # 模組資訊
    module_name = Column(String(50), nullable=False, comment="模組名稱")
    function_name = Column(String(50), comment="函數名稱")
    operation_type = Column(String(30), comment="操作類型")

    # 效能指標
    response_time = Column(Float, comment="響應時間 (ms)")
    throughput = Column(Float, comment="吞吐量 (requests/sec)")
    error_rate = Column(Float, comment="錯誤率 (%)")
    success_count = Column(Integer, comment="成功次數")
    error_count = Column(Integer, comment="錯誤次數")

    # 資源使用
    cpu_time = Column(Float, comment="CPU 時間 (ms)")
    memory_usage = Column(Float, comment="記憶體使用 (MB)")
    io_operations = Column(Integer, comment="IO 操作次數")

    # 請求資訊
    request_size = Column(Float, comment="請求大小 (bytes)")
    response_size = Column(Float, comment="回應大小 (bytes)")
    user_agent = Column(String(200), comment="使用者代理")
    ip_address = Column(String(45), comment="IP 地址")

    # 詳細資訊
    details = Column(JSON, comment="詳細資訊JSON")
    error_message = Column(Text, comment="錯誤訊息")
    stack_trace = Column(Text, comment="堆疊追蹤")

    # 創建索引
    __table_args__ = (
        Index("ix_performance_log_timestamp", "timestamp"),
        Index("ix_performance_log_module_timestamp", "module_name", "timestamp"),
        Index("ix_performance_log_operation_timestamp", "operation_type", "timestamp"),
        {"comment": "效能日誌表，記錄系統各模組的效能指標"},
    )

    def __repr__(self):
        return (
            f"<PerformanceLog(module={self.module_name}, timestamp={self.timestamp})>"
        )


# 定義警報規則表
class AlertRule(Base):
    """
    警報規則表

    定義系統監控的警報規則，包括觸發條件、通知方式等。
    """

    __tablename__ = "alert_rule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_name = Column(String(100), nullable=False, unique=True, comment="規則名稱")
    rule_type = Column(String(30), nullable=False, comment="規則類型")

    # 觸發條件
    metric_name = Column(String(50), nullable=False, comment="監控指標名稱")
    operator = Column(
        String(10), nullable=False, comment="比較運算符 (>, <, >=, <=, ==, !=)"
    )
    threshold_value = Column(Float, nullable=False, comment="閾值")
    duration_minutes = Column(Integer, default=5, comment="持續時間 (分鐘)")

    # 警報等級
    severity = Column(
        String(10), nullable=False, comment="嚴重程度 (low/medium/high/critical)"
    )
    priority = Column(Integer, default=3, comment="優先級 (1-5)")

    # 通知設定
    notification_channels = Column(JSON, comment="通知管道JSON")
    notification_template = Column(String(100), comment="通知模板名稱")
    cooldown_minutes = Column(Integer, default=60, comment="冷卻時間 (分鐘)")

    # 規則狀態
    is_enabled = Column(Boolean, default=True, comment="是否啟用")
    last_triggered = Column(DateTime, comment="最後觸發時間")
    trigger_count = Column(Integer, default=0, comment="觸發次數")

    # 描述和標籤
    description = Column(Text, comment="規則描述")
    tags = Column(JSON, comment="標籤JSON")

    # 資料管理欄位
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="建立時間"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新時間",
    )

    # 創建索引
    __table_args__ = (
        Index("ix_alert_rule_enabled", "is_enabled"),
        Index("ix_alert_rule_metric", "metric_name"),
        Index("ix_alert_rule_severity", "severity"),
        {"comment": "警報規則表，定義系統監控的警報規則"},
    )

    def __repr__(self):
        return f"<AlertRule(name={self.rule_name}, metric={self.metric_name})>"


# 定義警報記錄表
class AlertRecord(Base):
    """
    警報記錄表

    記錄系統產生的警報事件和處理狀態。
    """

    __tablename__ = "alert_record"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(String(50), nullable=False, unique=True, comment="警報唯一ID")
    rule_id = Column(Integer, nullable=False, comment="關聯規則ID")

    # 警報資訊
    timestamp = Column(DateTime, nullable=False, comment="警報時間")
    severity = Column(String(10), nullable=False, comment="嚴重程度")
    title = Column(String(200), nullable=False, comment="警報標題")
    message = Column(Text, nullable=False, comment="警報訊息")

    # 觸發資訊
    metric_name = Column(String(50), comment="觸發指標")
    current_value = Column(Float, comment="當前值")
    threshold_value = Column(Float, comment="閾值")

    # 狀態管理
    status = Column(
        String(20),
        default="active",
        comment="警報狀態 (active/acknowledged/resolved/suppressed)",
    )
    acknowledged_at = Column(DateTime, comment="確認時間")
    acknowledged_by = Column(String(50), comment="確認人員")
    resolved_at = Column(DateTime, comment="解決時間")
    resolved_by = Column(String(50), comment="解決人員")

    # 通知狀態
    notification_sent = Column(Boolean, default=False, comment="是否已發送通知")
    notification_channels = Column(JSON, comment="已發送的通知管道")
    notification_attempts = Column(Integer, default=0, comment="通知嘗試次數")

    # 詳細資訊
    details = Column(JSON, comment="詳細資訊JSON")
    tags = Column(JSON, comment="標籤JSON")

    # 創建索引
    __table_args__ = (
        Index("ix_alert_record_timestamp", "timestamp"),
        Index("ix_alert_record_rule_timestamp", "rule_id", "timestamp"),
        Index("ix_alert_record_status", "status"),
        Index("ix_alert_record_severity", "severity"),
        {"comment": "警報記錄表，記錄系統產生的警報事件"},
    )

    def __repr__(self):
        return f"<AlertRecord(id={self.alert_id}, severity={self.severity}, timestamp={self.timestamp})>"


# 定義報表模板表
class ReportTemplate(Base):
    """
    報表模板表

    儲存自定義報表模板的配置資訊，包括版面設計、樣式設定等。
    """

    __tablename__ = "report_template"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(String(50), nullable=False, unique=True, comment="模板唯一ID")
    template_name = Column(String(100), nullable=False, comment="模板名稱")
    template_type = Column(String(30), nullable=False, comment="模板類型")

    # 模板配置
    layout_config = Column(JSON, comment="版面配置JSON")
    style_config = Column(JSON, comment="樣式配置JSON")
    chart_configs = Column(JSON, comment="圖表配置JSON")

    # 模板內容
    title_template = Column(String(200), comment="標題模板")
    header_template = Column(Text, comment="頁首模板")
    footer_template = Column(Text, comment="頁尾模板")
    content_sections = Column(JSON, comment="內容區塊配置")

    # 品牌設定
    company_logo = Column(String(200), comment="公司標誌路徑")
    brand_colors = Column(JSON, comment="品牌色彩配置")
    font_settings = Column(JSON, comment="字體設定")

    # 多語言支援
    language = Column(String(10), default="zh-TW", comment="語言設定")
    localization_config = Column(JSON, comment="本地化配置")

    # 模板狀態
    is_active = Column(Boolean, default=True, comment="是否啟用")
    is_default = Column(Boolean, default=False, comment="是否為預設模板")
    version = Column(String(20), default="1.0", comment="模板版本")

    # 使用統計
    usage_count = Column(Integer, default=0, comment="使用次數")
    last_used = Column(DateTime, comment="最後使用時間")

    # 權限設定
    created_by = Column(String(50), comment="建立者")
    shared_with = Column(JSON, comment="共享對象")
    access_level = Column(String(20), default="private", comment="存取權限")

    # 資料管理欄位
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="建立時間"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新時間",
    )

    # 創建索引
    __table_args__ = (
        Index("ix_report_template_type", "template_type"),
        Index("ix_report_template_active", "is_active"),
        Index("ix_report_template_created_by", "created_by"),
        {"comment": "報表模板表，儲存自定義報表模板配置"},
    )

    def __repr__(self):
        return f"<ReportTemplate(id={self.template_id}, name={self.template_name})>"


# 定義圖表配置表
class ChartConfig(Base):
    """
    圖表配置表

    儲存圖表的詳細配置資訊，包括圖表類型、樣式、數據源等。
    """

    __tablename__ = "chart_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(String(50), nullable=False, unique=True, comment="配置唯一ID")
    config_name = Column(String(100), nullable=False, comment="配置名稱")
    chart_type = Column(String(30), nullable=False, comment="圖表類型")

    # 數據配置
    data_source = Column(String(50), comment="數據源")
    data_query = Column(Text, comment="數據查詢語句")
    data_filters = Column(JSON, comment="數據篩選條件")
    data_aggregation = Column(JSON, comment="數據聚合配置")

    # 圖表配置
    chart_library = Column(
        String(20), default="plotly", comment="圖表庫 (plotly/matplotlib)"
    )
    chart_style = Column(JSON, comment="圖表樣式配置")
    axis_config = Column(JSON, comment="座標軸配置")
    legend_config = Column(JSON, comment="圖例配置")
    color_scheme = Column(JSON, comment="色彩配置")

    # 互動配置
    interactive_features = Column(JSON, comment="互動功能配置")
    zoom_enabled = Column(Boolean, default=True, comment="是否啟用縮放")
    hover_enabled = Column(Boolean, default=True, comment="是否啟用懸停")
    click_events = Column(JSON, comment="點擊事件配置")

    # 尺寸配置
    width = Column(Integer, comment="圖表寬度")
    height = Column(Integer, comment="圖表高度")
    responsive = Column(Boolean, default=True, comment="是否響應式")

    # 效能配置
    cache_enabled = Column(Boolean, default=True, comment="是否啟用快取")
    cache_duration = Column(Integer, default=300, comment="快取持續時間(秒)")
    lazy_loading = Column(Boolean, default=False, comment="是否延遲載入")

    # 匯出配置
    export_formats = Column(JSON, comment="支援的匯出格式")
    export_settings = Column(JSON, comment="匯出設定")

    # 配置狀態
    is_active = Column(Boolean, default=True, comment="是否啟用")
    version = Column(String(20), default="1.0", comment="配置版本")

    # 使用統計
    usage_count = Column(Integer, default=0, comment="使用次數")
    last_used = Column(DateTime, comment="最後使用時間")

    # 權限設定
    created_by = Column(String(50), comment="建立者")
    shared_with = Column(JSON, comment="共享對象")

    # 資料管理欄位
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="建立時間"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新時間",
    )

    # 創建索引
    __table_args__ = (
        Index("ix_chart_config_type", "chart_type"),
        Index("ix_chart_config_active", "is_active"),
        Index("ix_chart_config_created_by", "created_by"),
        {"comment": "圖表配置表，儲存圖表的詳細配置資訊"},
    )

    def __repr__(self):
        return f"<ChartConfig(id={self.config_id}, name={self.config_name}, type={self.chart_type})>"


# 定義匯出日誌表
class ExportLog(Base):
    """
    匯出日誌表

    記錄報表和圖表的匯出操作日誌，包括匯出狀態、檔案資訊等。
    """

    __tablename__ = "export_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    export_id = Column(String(50), nullable=False, unique=True, comment="匯出唯一ID")

    # 匯出資訊
    export_type = Column(
        String(30), nullable=False, comment="匯出類型 (report/chart/data)"
    )
    export_format = Column(String(20), nullable=False, comment="匯出格式")
    export_name = Column(String(200), comment="匯出檔案名稱")

    # 來源資訊
    source_type = Column(String(30), comment="來源類型")
    source_id = Column(String(50), comment="來源ID")
    template_id = Column(String(50), comment="使用的模板ID")
    chart_config_id = Column(String(50), comment="使用的圖表配置ID")

    # 匯出參數
    export_parameters = Column(JSON, comment="匯出參數")
    data_range = Column(JSON, comment="數據範圍")
    filters_applied = Column(JSON, comment="應用的篩選條件")

    # 檔案資訊
    file_path = Column(String(500), comment="檔案路徑")
    file_size = Column(Integer, comment="檔案大小(bytes)")
    file_hash = Column(String(64), comment="檔案雜湊值")

    # 匯出狀態
    status = Column(String(20), default="pending", comment="匯出狀態")
    progress = Column(Float, default=0.0, comment="匯出進度(0-100)")
    error_message = Column(Text, comment="錯誤訊息")

    # 時間資訊
    started_at = Column(DateTime, comment="開始時間")
    completed_at = Column(DateTime, comment="完成時間")
    duration_seconds = Column(Float, comment="耗時(秒)")

    # 使用者資訊
    user_id = Column(String(50), comment="使用者ID")
    user_name = Column(String(50), comment="使用者名稱")
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(String(200), comment="使用者代理")

    # 下載資訊
    download_count = Column(Integer, default=0, comment="下載次數")
    last_downloaded = Column(DateTime, comment="最後下載時間")
    expires_at = Column(DateTime, comment="過期時間")

    # 資料管理欄位
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="建立時間"
    )

    # 創建索引
    __table_args__ = (
        Index("ix_export_log_type", "export_type"),
        Index("ix_export_log_status", "status"),
        Index("ix_export_log_user", "user_id"),
        Index("ix_export_log_created", "created_at"),
        {"comment": "匯出日誌表，記錄報表和圖表的匯出操作"},
    )

    def __repr__(self):
        return f"<ExportLog(id={self.export_id}, type={self.export_type}, status={self.status})>"


# 定義報表快取表
class ReportCache(Base):
    """
    報表快取表

    儲存報表和圖表的快取數據，提升載入速度和使用者體驗。
    """

    __tablename__ = "report_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(100), nullable=False, unique=True, comment="快取鍵值")

    # 快取內容
    cache_type = Column(String(30), nullable=False, comment="快取類型")
    cache_data = Column(LargeBinary, comment="快取數據(壓縮)")
    cache_metadata = Column(JSON, comment="快取元數據")

    # 來源資訊
    source_type = Column(String(30), comment="來源類型")
    source_id = Column(String(50), comment="來源ID")
    data_hash = Column(String(64), comment="數據雜湊值")

    # 快取狀態
    is_valid = Column(Boolean, default=True, comment="是否有效")
    hit_count = Column(Integer, default=0, comment="命中次數")
    last_hit = Column(DateTime, comment="最後命中時間")

    # 時間管理
    expires_at = Column(DateTime, comment="過期時間")
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="建立時間"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新時間",
    )

    # 大小資訊
    original_size = Column(Integer, comment="原始大小(bytes)")
    compressed_size = Column(Integer, comment="壓縮後大小(bytes)")
    compression_ratio = Column(Float, comment="壓縮比率")

    # 創建索引
    __table_args__ = (
        Index("ix_report_cache_type", "cache_type"),
        Index("ix_report_cache_valid", "is_valid"),
        Index("ix_report_cache_expires", "expires_at"),
        {"comment": "報表快取表，儲存報表和圖表的快取數據"},
    )

    def __repr__(self):
        return f"<ReportCache(key={self.cache_key}, type={self.cache_type})>"


# 定義使用者表
class User(Base):
    """
    使用者表

    儲存系統使用者的基本資訊、認證資料和安全設定。
    """

    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, unique=True, comment="使用者唯一ID")
    username = Column(String(50), nullable=False, unique=True, comment="使用者名稱")
    email = Column(String(100), nullable=False, unique=True, comment="電子郵件")

    # 認證資訊
    password_hash = Column(String(255), nullable=False, comment="密碼雜湊值")
    salt = Column(String(32), nullable=False, comment="密碼鹽值")
    password_history = Column(JSON, comment="密碼歷史記錄")

    # 基本資訊
    full_name = Column(String(100), comment="全名")
    phone = Column(String(20), comment="電話號碼")
    department = Column(String(50), comment="部門")
    position = Column(String(50), comment="職位")

    # 帳戶狀態
    is_active = Column(Boolean, default=True, comment="是否啟用")
    is_verified = Column(Boolean, default=False, comment="是否已驗證")
    is_locked = Column(Boolean, default=False, comment="是否被鎖定")

    # 安全設定
    two_factor_enabled = Column(Boolean, default=False, comment="是否啟用兩步驗證")
    two_factor_secret = Column(String(32), comment="兩步驗證密鑰")
    backup_codes = Column(JSON, comment="備用驗證碼")

    # 登入控制
    failed_login_attempts = Column(Integer, default=0, comment="登入失敗次數")
    last_login_at = Column(DateTime, comment="最後登入時間")
    last_login_ip = Column(String(45), comment="最後登入IP")
    last_password_change = Column(DateTime, comment="最後密碼變更時間")

    # 會話管理
    current_session_id = Column(String(128), comment="當前會話ID")
    session_expires_at = Column(DateTime, comment="會話過期時間")
    remember_token = Column(String(128), comment="記住登入令牌")

    # 權限設定
    default_role_id = Column(String(50), comment="預設角色ID")
    permissions_override = Column(JSON, comment="權限覆蓋設定")

    # 安全事件
    locked_at = Column(DateTime, comment="鎖定時間")
    locked_reason = Column(String(200), comment="鎖定原因")
    unlock_token = Column(String(128), comment="解鎖令牌")

    # 資料管理欄位
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="建立時間"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新時間",
    )
    created_by = Column(String(50), comment="建立者")
    updated_by = Column(String(50), comment="更新者")

    # 創建索引
    __table_args__ = (
        Index("ix_user_username", "username"),
        Index("ix_user_email", "email"),
        Index("ix_user_active", "is_active"),
        Index("ix_user_locked", "is_locked"),
        {"comment": "使用者表，儲存系統使用者的基本資訊和認證資料"},
    )

    def __repr__(self):
        return f"<User(id={self.user_id}, username={self.username})>"


# 定義角色表
class Role(Base):
    """
    角色表

    定義系統中的各種角色，包括權限範圍和角色層級。
    """

    __tablename__ = "role"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role_id = Column(String(50), nullable=False, unique=True, comment="角色唯一ID")
    role_name = Column(String(50), nullable=False, comment="角色名稱")
    role_code = Column(String(30), nullable=False, unique=True, comment="角色代碼")

    # 角色描述
    description = Column(Text, comment="角色描述")
    role_level = Column(Integer, default=1, comment="角色層級 (1-10)")
    role_category = Column(String(30), comment="角色分類")

    # 權限設定
    permissions = Column(JSON, comment="角色權限JSON")
    resource_access = Column(JSON, comment="資源存取權限")
    module_access = Column(JSON, comment="模組存取權限")

    # 角色狀態
    is_active = Column(Boolean, default=True, comment="是否啟用")
    is_system_role = Column(Boolean, default=False, comment="是否為系統角色")
    is_default = Column(Boolean, default=False, comment="是否為預設角色")

    # 角色限制
    max_users = Column(Integer, comment="最大使用者數量")
    session_timeout = Column(Integer, comment="會話超時時間(分鐘)")
    ip_restrictions = Column(JSON, comment="IP限制設定")
    time_restrictions = Column(JSON, comment="時間限制設定")

    # 繼承設定
    parent_role_id = Column(String(50), comment="父角色ID")
    inheritance_type = Column(String(20), default="additive", comment="繼承類型")

    # 資料管理欄位
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="建立時間"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新時間",
    )
    created_by = Column(String(50), comment="建立者")
    updated_by = Column(String(50), comment="更新者")

    # 創建索引
    __table_args__ = (
        Index("ix_role_code", "role_code"),
        Index("ix_role_active", "is_active"),
        Index("ix_role_level", "role_level"),
        {"comment": "角色表，定義系統中的各種角色和權限"},
    )

    def __repr__(self):
        return f"<Role(id={self.role_id}, name={self.role_name})>"


# 定義使用者角色關聯表
class UserRole(Base):
    """
    使用者角色關聯表

    管理使用者與角色的多對多關係，支援臨時權限和權限委派。
    """

    __tablename__ = "user_role"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), nullable=False, comment="使用者ID")
    role_id = Column(String(50), nullable=False, comment="角色ID")

    # 分配資訊
    assignment_type = Column(String(20), default="permanent", comment="分配類型")
    assigned_by = Column(String(50), comment="分配者")
    assignment_reason = Column(String(200), comment="分配原因")

    # 時效設定
    effective_from = Column(DateTime, comment="生效開始時間")
    effective_until = Column(DateTime, comment="生效結束時間")
    is_temporary = Column(Boolean, default=False, comment="是否為臨時權限")

    # 狀態管理
    is_active = Column(Boolean, default=True, comment="是否啟用")
    is_delegated = Column(Boolean, default=False, comment="是否為委派權限")
    delegated_from = Column(String(50), comment="委派來源使用者ID")

    # 審核資訊
    approval_status = Column(String(20), default="approved", comment="審核狀態")
    approved_by = Column(String(50), comment="審核者")
    approved_at = Column(DateTime, comment="審核時間")
    approval_comments = Column(Text, comment="審核備註")

    # 資料管理欄位
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="建立時間"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新時間",
    )

    # 創建索引和約束
    __table_args__ = (
        Index("ix_user_role_user", "user_id"),
        Index("ix_user_role_role", "role_id"),
        Index("ix_user_role_active", "is_active"),
        Index("ix_user_role_effective", "effective_from", "effective_until"),
        UniqueConstraint("user_id", "role_id", name="uq_user_role"),
        {"comment": "使用者角色關聯表，管理使用者與角色的關係"},
    )

    def __repr__(self):
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"


# 定義權限表
class Permission(Base):
    """
    權限表

    定義系統中的各種權限，包括功能權限、資源權限和操作權限。
    """

    __tablename__ = "permission"

    id = Column(Integer, primary_key=True, autoincrement=True)
    permission_id = Column(
        String(50), nullable=False, unique=True, comment="權限唯一ID"
    )
    permission_name = Column(String(100), nullable=False, comment="權限名稱")
    permission_code = Column(
        String(50), nullable=False, unique=True, comment="權限代碼"
    )

    # 權限分類
    permission_type = Column(String(30), nullable=False, comment="權限類型")
    permission_category = Column(String(30), comment="權限分類")
    module_name = Column(String(50), comment="所屬模組")

    # 權限描述
    description = Column(Text, comment="權限描述")
    risk_level = Column(String(20), default="low", comment="風險等級")

    # 權限範圍
    resource_type = Column(String(30), comment="資源類型")
    resource_pattern = Column(String(200), comment="資源模式")
    action_type = Column(String(30), comment="操作類型")

    # 權限限制
    requires_approval = Column(Boolean, default=False, comment="是否需要審核")
    requires_2fa = Column(Boolean, default=False, comment="是否需要兩步驗證")
    ip_restrictions = Column(JSON, comment="IP限制")
    time_restrictions = Column(JSON, comment="時間限制")

    # 權限狀態
    is_active = Column(Boolean, default=True, comment="是否啟用")
    is_system_permission = Column(Boolean, default=False, comment="是否為系統權限")

    # 依賴關係
    depends_on = Column(JSON, comment="依賴的權限")
    conflicts_with = Column(JSON, comment="衝突的權限")

    # 資料管理欄位
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="建立時間"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新時間",
    )
    created_by = Column(String(50), comment="建立者")
    updated_by = Column(String(50), comment="更新者")

    # 創建索引
    __table_args__ = (
        Index("ix_permission_code", "permission_code"),
        Index("ix_permission_type", "permission_type"),
        Index("ix_permission_module", "module_name"),
        Index("ix_permission_active", "is_active"),
        {"comment": "權限表，定義系統中的各種權限"},
    )

    def __repr__(self):
        return f"<Permission(id={self.permission_id}, code={self.permission_code})>"


# 定義安全事件表
class SecurityEvent(Base):
    """
    安全事件表

    記錄系統中發生的各種安全事件，包括登入失敗、異常操作等。
    """

    __tablename__ = "security_event"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(50), nullable=False, unique=True, comment="事件唯一ID")

    # 事件基本資訊
    event_type = Column(String(30), nullable=False, comment="事件類型")
    event_category = Column(String(30), comment="事件分類")
    event_level = Column(String(20), default="info", comment="事件等級")
    event_source = Column(String(50), comment="事件來源")

    # 使用者資訊
    user_id = Column(String(50), comment="使用者ID")
    username = Column(String(50), comment="使用者名稱")
    session_id = Column(String(128), comment="會話ID")

    # 網路資訊
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(String(500), comment="使用者代理")
    geo_location = Column(JSON, comment="地理位置資訊")

    # 事件詳情
    event_description = Column(Text, comment="事件描述")
    event_data = Column(JSON, comment="事件數據")
    affected_resources = Column(JSON, comment="受影響的資源")

    # 風險評估
    risk_score = Column(Float, comment="風險分數")
    threat_level = Column(String(20), comment="威脅等級")
    is_suspicious = Column(Boolean, default=False, comment="是否可疑")

    # 處理狀態
    status = Column(String(20), default="new", comment="處理狀態")
    assigned_to = Column(String(50), comment="分配給")
    resolution = Column(Text, comment="解決方案")
    resolved_at = Column(DateTime, comment="解決時間")

    # 關聯事件
    parent_event_id = Column(String(50), comment="父事件ID")
    correlation_id = Column(String(50), comment="關聯ID")

    # 資料管理欄位
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="建立時間"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新時間",
    )

    # 創建索引
    __table_args__ = (
        Index("ix_security_event_type", "event_type"),
        Index("ix_security_event_user", "user_id"),
        Index("ix_security_event_ip", "ip_address"),
        Index("ix_security_event_level", "event_level"),
        Index("ix_security_event_created", "created_at"),
        {"comment": "安全事件表，記錄系統中的安全事件"},
    )

    def __repr__(self):
        return f"<SecurityEvent(id={self.event_id}, type={self.event_type})>"


# 定義操作審計表
class AuditLog(Base):
    """
    操作審計表

    記錄系統中所有重要操作的審計日誌，用於合規性和安全審計。
    """

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_id = Column(String(50), nullable=False, unique=True, comment="審計唯一ID")

    # 操作基本資訊
    operation_type = Column(String(30), nullable=False, comment="操作類型")
    operation_name = Column(String(100), comment="操作名稱")
    module_name = Column(String(50), comment="模組名稱")
    function_name = Column(String(100), comment="函數名稱")

    # 使用者資訊
    user_id = Column(String(50), comment="使用者ID")
    username = Column(String(50), comment="使用者名稱")
    user_role = Column(String(50), comment="使用者角色")
    session_id = Column(String(128), comment="會話ID")

    # 網路資訊
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(String(500), comment="使用者代理")
    request_id = Column(String(50), comment="請求ID")

    # 操作詳情
    operation_description = Column(Text, comment="操作描述")
    input_parameters = Column(JSON, comment="輸入參數")
    output_result = Column(JSON, comment="輸出結果")

    # 資源資訊
    resource_type = Column(String(30), comment="資源類型")
    resource_id = Column(String(50), comment="資源ID")
    resource_name = Column(String(100), comment="資源名稱")
    affected_data = Column(JSON, comment="受影響的數據")

    # 操作結果
    operation_status = Column(String(20), comment="操作狀態")
    error_message = Column(Text, comment="錯誤訊息")
    execution_time = Column(Float, comment="執行時間(秒)")

    # 風險評估
    risk_level = Column(String(20), default="low", comment="風險等級")
    requires_approval = Column(Boolean, default=False, comment="是否需要審核")
    approval_status = Column(String(20), comment="審核狀態")
    approved_by = Column(String(50), comment="審核者")

    # 合規性標記
    compliance_tags = Column(JSON, comment="合規性標籤")
    retention_period = Column(Integer, comment="保留期限(天)")
    is_sensitive = Column(Boolean, default=False, comment="是否敏感操作")

    # 資料管理欄位
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="建立時間"
    )

    # 創建索引
    __table_args__ = (
        Index("ix_audit_log_operation", "operation_type"),
        Index("ix_audit_log_user", "user_id"),
        Index("ix_audit_log_module", "module_name"),
        Index("ix_audit_log_resource", "resource_type", "resource_id"),
        Index("ix_audit_log_created", "created_at"),
        Index("ix_audit_log_risk", "risk_level"),
        {"comment": "操作審計表，記錄系統中的重要操作"},
    )

    def __repr__(self):
        return f"<AuditLog(id={self.audit_id}, operation={self.operation_type})>"


# 定義使用者會話表
class UserSession(Base):
    """
    使用者會話表

    管理使用者的登入會話，包括會話狀態、安全資訊等。
    """

    __tablename__ = "user_session"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(128), nullable=False, unique=True, comment="會話唯一ID")

    # 使用者資訊
    user_id = Column(String(50), nullable=False, comment="使用者ID")
    username = Column(String(50), comment="使用者名稱")

    # 會話狀態
    session_status = Column(String(20), default="active", comment="會話狀態")
    login_method = Column(String(30), comment="登入方式")
    is_remember_me = Column(Boolean, default=False, comment="是否記住登入")

    # 時間管理
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="建立時間"
    )
    last_activity = Column(DateTime, comment="最後活動時間")
    expires_at = Column(DateTime, comment="過期時間")
    logout_at = Column(DateTime, comment="登出時間")

    # 網路資訊
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(String(500), comment="使用者代理")
    device_fingerprint = Column(String(128), comment="設備指紋")
    geo_location = Column(JSON, comment="地理位置")

    # 安全資訊
    is_secure = Column(Boolean, default=True, comment="是否安全連線")
    two_factor_verified = Column(Boolean, default=False, comment="是否通過兩步驗證")
    login_attempts = Column(Integer, default=1, comment="登入嘗試次數")

    # 會話數據
    session_data = Column(JSON, comment="會話數據")
    permissions_cache = Column(JSON, comment="權限快取")

    # 終止原因
    logout_reason = Column(String(50), comment="登出原因")
    is_forced_logout = Column(Boolean, default=False, comment="是否強制登出")

    # 創建索引
    __table_args__ = (
        Index("ix_user_session_user", "user_id"),
        Index("ix_user_session_status", "session_status"),
        Index("ix_user_session_ip", "ip_address"),
        Index("ix_user_session_created", "created_at"),
        Index("ix_user_session_expires", "expires_at"),
        {"comment": "使用者會話表，管理使用者的登入會話"},
    )

    def __repr__(self):
        return f"<UserSession(id={self.session_id}, user={self.username})>"


class APIKey(Base):
    """API 金鑰表"""

    __tablename__ = "api_keys"

    # 主鍵
    key_id = Column(String(50), primary_key=True, comment="金鑰ID")

    # 使用者資訊
    user_id = Column(String(50), nullable=False, comment="使用者ID")

    # 券商資訊
    broker_name = Column(String(50), nullable=False, comment="券商名稱")
    broker_account_id = Column(String(100), comment="券商帳戶ID")

    # 加密的金鑰資料
    encrypted_api_key = Column(Text, nullable=False, comment="加密的API金鑰")
    encrypted_api_secret = Column(Text, nullable=False, comment="加密的API密鑰")
    key_hash = Column(String(128), comment="金鑰雜湊值（用於驗證）")

    # 權限和狀態
    permissions = Column(JSON, comment="權限列表")
    status = Column(String(20), default="active", comment="狀態")
    description = Column(String(200), comment="描述")

    # 時間資訊
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="建立時間"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新時間",
    )
    expires_at = Column(DateTime, comment="過期時間")
    last_used_at = Column(DateTime, comment="最後使用時間")
    last_rotated_at = Column(DateTime, comment="最後輪換時間")

    # 使用統計
    usage_count = Column(Integer, default=0, comment="使用次數")
    rotation_count = Column(Integer, default=0, comment="輪換次數")

    # 安全資訊
    created_ip = Column(String(45), comment="建立時的IP地址")
    last_used_ip = Column(String(45), comment="最後使用的IP地址")

    # 創建索引
    __table_args__ = (
        Index("ix_api_key_user", "user_id"),
        Index("ix_api_key_broker", "broker_name"),
        Index("ix_api_key_status", "status"),
        Index("ix_api_key_expires", "expires_at"),
        Index("ix_api_key_created", "created_at"),
        {"comment": "API金鑰表，存儲加密的券商API金鑰"},
    )

    def __repr__(self):
        return f"<APIKey(id={self.key_id}, user={self.user_id}, broker={self.broker_name})>"


class APIKeyBackup(Base):
    """API 金鑰備份表"""

    __tablename__ = "api_key_backups"

    # 主鍵
    backup_id = Column(String(50), primary_key=True, comment="備份ID")

    # 關聯的金鑰
    key_id = Column(String(50), nullable=False, comment="原金鑰ID")

    # 備份的加密資料
    encrypted_api_key = Column(Text, nullable=False, comment="備份的加密API金鑰")
    encrypted_api_secret = Column(Text, nullable=False, comment="備份的加密API密鑰")

    # 備份資訊
    backup_reason = Column(String(100), comment="備份原因")
    rotated_at = Column(DateTime, comment="輪換時間")

    # 時間資訊
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="建立時間"
    )

    # 創建索引
    __table_args__ = (
        Index("ix_api_key_backup_key", "key_id"),
        Index("ix_api_key_backup_created", "created_at"),
        {"comment": "API金鑰備份表，用於金鑰輪換時的備份"},
    )

    def __repr__(self):
        return f"<APIKeyBackup(id={self.backup_id}, key={self.key_id})>"


class APIKeyUsageLog(Base):
    """API 金鑰使用日誌表"""

    __tablename__ = "api_key_usage_logs"

    # 主鍵
    log_id = Column(String(50), primary_key=True, comment="日誌ID")

    # 金鑰資訊
    key_id = Column(String(50), nullable=False, comment="金鑰ID")
    user_id = Column(String(50), nullable=False, comment="使用者ID")

    # 使用資訊
    operation = Column(String(50), comment="操作類型")
    endpoint = Column(String(200), comment="API端點")
    request_method = Column(String(10), comment="請求方法")

    # 結果資訊
    status_code = Column(Integer, comment="回應狀態碼")
    response_time = Column(Float, comment="回應時間（毫秒）")
    success = Column(Boolean, comment="是否成功")
    error_message = Column(Text, comment="錯誤訊息")

    # 網路資訊
    ip_address = Column(String(45), comment="IP地址")
    user_agent = Column(String(500), comment="使用者代理")

    # 時間資訊
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="建立時間"
    )

    # 創建索引
    __table_args__ = (
        Index("ix_api_usage_key", "key_id"),
        Index("ix_api_usage_user", "user_id"),
        Index("ix_api_usage_created", "created_at"),
        Index("ix_api_usage_operation", "operation"),
        Index("ix_api_usage_success", "success"),
        {"comment": "API金鑰使用日誌表，記錄所有API使用情況"},
    )

    def __repr__(self):
        return f"<APIKeyUsageLog(id={self.log_id}, key={self.key_id}, operation={self.operation})>"


class APIKeyPermission(Base):
    """API 金鑰權限表"""

    __tablename__ = "api_key_permissions"

    # 主鍵
    permission_id = Column(String(50), primary_key=True, comment="權限ID")

    # 權限資訊
    permission_code = Column(String(50), nullable=False, comment="權限代碼")
    permission_name = Column(String(100), nullable=False, comment="權限名稱")
    description = Column(String(200), comment="權限描述")

    # 權限分類
    category = Column(String(50), comment="權限分類")
    level = Column(Integer, comment="權限等級")

    # 是否啟用
    is_active = Column(Boolean, default=True, comment="是否啟用")

    # 時間資訊
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), comment="建立時間"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        comment="更新時間",
    )

    # 創建索引
    __table_args__ = (
        Index("ix_api_permission_code", "permission_code"),
        Index("ix_api_permission_category", "category"),
        Index("ix_api_permission_level", "level"),
        {"comment": "API金鑰權限表，定義可用的權限"},
    )

    def __repr__(self):
        return f"<APIKeyPermission(id={self.permission_id}, code={self.permission_code})>"


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
    file_format = Column(
        String(50), default="parquet", comment="檔案格式 (parquet/arrow/csv)"
    )
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
    """在插入或更新 MarketDaily 記錄前計算校驗碼

    Args:
        mapper: SQLAlchemy mapper (未使用但為必要參數)
        connection: 資料庫連線 (未使用但為必要參數)
        target: 目標記錄物件
    """
    # 忽略未使用的參數警告
    _ = mapper, connection
    target.checksum = target.calculate_checksum()


@event.listens_for(MarketMinute, "before_insert")
@event.listens_for(MarketMinute, "before_update")
def calculate_market_minute_checksum(mapper, connection, target):
    """在插入或更新 MarketMinute 記錄前計算校驗碼

    Args:
        mapper: SQLAlchemy mapper (未使用但為必要參數)
        connection: 資料庫連線 (未使用但為必要參數)
        target: 目標記錄物件
    """
    # 忽略未使用的參數警告
    _ = mapper, connection
    target.checksum = target.calculate_checksum()


@event.listens_for(MarketTick, "before_insert")
@event.listens_for(MarketTick, "before_update")
def calculate_market_tick_checksum(mapper, connection, target):
    """在插入或更新 MarketTick 記錄前計算校驗碼

    Args:
        mapper: SQLAlchemy mapper (未使用但為必要參數)
        connection: 資料庫連線 (未使用但為必要參數)
        target: 目標記錄物件
    """
    # 忽略未使用的參數警告
    _ = mapper, connection
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
