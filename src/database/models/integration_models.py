# -*- coding: utf-8 -*-
"""資料整合系統資料庫模型

此模組定義了資料整合系統所需的新資料表模型，擴展現有的資料庫架構，
支援多元化的台股資料類型。

主要資料表：
- DividendInfo: 股利資訊
- ImportantNews: 重要公告
- ChipData: 籌碼面資料
- FundamentalData: 基本面資料
- DataSourceStatus: 資料來源狀態
- DataQualityLog: 資料品質日誌

Example:
    使用資料模型：
    ```python
    from src.database.models.integration_models import DividendInfo
    
    # 創建股利資訊記錄
    dividend = DividendInfo(
        symbol="2330.TW",
        ex_date=date(2024, 6, 15),
        dividend_cash=18.0,
        dividend_stock=0.0
    )
    ```

Note:
    所有模型都繼承自現有的 Base 類別，確保與現有資料庫架構的一致性。
    使用 SQLAlchemy 2.0 的新語法和類型註解。
"""

from datetime import date, datetime
from typing import Optional
from sqlalchemy import (
    String, Float, Integer, BigInteger, Date, DateTime, Text, Boolean,
    UniqueConstraint, Index, CheckConstraint, ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 導入現有的基礎模型
from src.database.models.base_models import Base


class DividendInfo(Base):
    """股利資訊資料表
    
    儲存上市櫃公司的股利發放資訊，包括現金股利和股票股利。
    
    Attributes:
        id: 主鍵
        symbol: 股票代碼
        ex_date: 除權息日期
        dividend_cash: 現金股利（元）
        dividend_stock: 股票股利（股）
        record_date: 停止過戶日
        payment_date: 發放日
        announcement_date: 公告日期
        dividend_type: 股利類型（現金/股票/混合）
        source: 資料來源
        created_at: 建立時間
        updated_at: 更新時間
    """
    __tablename__ = 'dividend_info'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, comment='股票代碼')
    ex_date: Mapped[date] = mapped_column(Date, nullable=False, comment='除權息日期')
    dividend_cash: Mapped[Optional[float]] = mapped_column(Float, comment='現金股利（元）')
    dividend_stock: Mapped[Optional[float]] = mapped_column(Float, comment='股票股利（股）')
    record_date: Mapped[Optional[date]] = mapped_column(Date, comment='停止過戶日')
    payment_date: Mapped[Optional[date]] = mapped_column(Date, comment='發放日')
    announcement_date: Mapped[Optional[date]] = mapped_column(Date, comment='公告日期')
    dividend_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default='cash', comment='股利類型'
    )
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default='TWSE', comment='資料來源'
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment='建立時間'
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment='更新時間')
    
    __table_args__ = (
        UniqueConstraint('symbol', 'ex_date', name='uq_dividend_symbol_date'),
        Index('idx_dividend_symbol', 'symbol'),
        Index('idx_dividend_date', 'ex_date'),
        Index('idx_dividend_announcement', 'announcement_date'),
        CheckConstraint(
            'dividend_cash IS NOT NULL OR dividend_stock IS NOT NULL',
            name='ck_dividend_not_null'
        ),
        CheckConstraint(
            "dividend_type IN ('cash', 'stock', 'mixed')",
            name='ck_dividend_type'
        ),
        {'comment': '股利資訊資料表'}
    )


class ImportantNews(Base):
    """重要公告資料表
    
    儲存上市櫃公司的重要公告和新聞資訊。
    
    Attributes:
        id: 主鍵
        symbol: 股票代碼
        announce_date: 公告日期時間
        title: 公告標題
        content: 公告內容
        category: 公告分類
        subcategory: 公告子分類
        source: 資料來源
        source_url: 原始連結
        importance_level: 重要性等級（1-5）
        is_processed: 是否已處理
        created_at: 建立時間
    """
    __tablename__ = 'important_news'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[Optional[str]] = mapped_column(
        String(20), comment='股票代碼（可為空，用於全市場新聞）'
    )
    announce_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment='公告日期時間'
    )
    title: Mapped[str] = mapped_column(Text, nullable=False, comment='公告標題')
    content: Mapped[Optional[str]] = mapped_column(Text, comment='公告內容')
    category: Mapped[str] = mapped_column(String(50), nullable=False, comment='公告分類')
    subcategory: Mapped[Optional[str]] = mapped_column(String(50), comment='公告子分類')
    source: Mapped[str] = mapped_column(
        String(100), nullable=False, comment='資料來源'
    )
    source_url: Mapped[Optional[str]] = mapped_column(String(500), comment='原始連結')
    importance_level: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, comment='重要性等級（1-5）'
    )
    is_processed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment='是否已處理'
    )
    # 新增事件面資料欄位
    event_type: Mapped[Optional[str]] = mapped_column(
        String(50), comment='事件類型（material_news, investor_conference, '
                            'stock_news, dividend_events）'
    )
    publish_date: Mapped[Optional[date]] = mapped_column(
        Date, comment='發布日期'
    )
    publish_time: Mapped[Optional[str]] = mapped_column(
        String(10), comment='發布時間（HH:MM）'
    )
    location: Mapped[Optional[str]] = mapped_column(
        String(200), comment='地點（法說會等）'
    )
    stock_symbols: Mapped[Optional[str]] = mapped_column(
        Text, comment='相關股票代碼（逗號分隔）'
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text, comment='摘要'
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment='建立時間'
    )
    
    __table_args__ = (
        Index('idx_news_symbol', 'symbol'),
        Index('idx_news_date', 'announce_date'),
        Index('idx_news_category', 'category'),
        Index('idx_news_importance', 'importance_level'),
        Index('idx_news_processed', 'is_processed'),
        Index('idx_news_event_type', 'event_type'),
        Index('idx_news_publish_date', 'publish_date'),
        Index('idx_news_source', 'source'),
        Index('idx_news_symbol_date', 'symbol', 'announce_date'),
        Index('idx_news_category_importance', 'category', 'importance_level'),
        Index('idx_news_event_type_date', 'event_type', 'publish_date'),
        CheckConstraint(
            'importance_level >= 1 AND importance_level <= 5',
            name='ck_news_importance_level'
        ),
        {'comment': '重要公告資料表'}
    )


class ChipData(Base):
    """籌碼面資料表
    
    儲存三大法人買賣超、融資融券等籌碼面資料。
    
    Attributes:
        id: 主鍵
        symbol: 股票代碼
        date: 資料日期
        foreign_buy: 外資買進金額（千元）
        foreign_sell: 外資賣出金額（千元）
        investment_trust_buy: 投信買進金額（千元）
        investment_trust_sell: 投信賣出金額（千元）
        dealer_buy: 自營商買進金額（千元）
        dealer_sell: 自營商賣出金額（千元）
        margin_balance: 融資餘額（千股）
        short_balance: 融券餘額（千股）
        margin_quota: 融資限額（千股）
        short_quota: 融券限額（千股）
        source: 資料來源
        created_at: 建立時間
    """
    __tablename__ = 'chip_data'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, comment='股票代碼')
    date: Mapped[date] = mapped_column(Date, nullable=False, comment='資料日期')
    foreign_buy: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='外資買進金額（千元）'
    )
    foreign_sell: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='外資賣出金額（千元）'
    )
    investment_trust_buy: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='投信買進金額（千元）'
    )
    investment_trust_sell: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='投信賣出金額（千元）'
    )
    dealer_buy: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='自營商買進金額（千元）'
    )
    dealer_sell: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='自營商賣出金額（千元）'
    )
    margin_balance: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='融資餘額（千股）'
    )
    short_balance: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='融券餘額（千股）'
    )
    margin_quota: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='融資限額（千股）'
    )
    short_quota: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='融券限額（千股）'
    )
    # 新增融資融券交易欄位
    margin_buy: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='融資買進金額（千元）'
    )
    margin_sell: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='融資賣出金額（千元）'
    )
    short_sell: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='融券賣出股數（千股）'
    )
    short_cover: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='融券回補股數（千股）'
    )
    # 新增外資持股欄位
    foreign_holding_ratio: Mapped[Optional[float]] = mapped_column(
        Float, comment='外資持股比例（%）'
    )
    foreign_holding_shares: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='外資持股股數（千股）'
    )
    # 新增券商分點欄位
    broker_id: Mapped[Optional[str]] = mapped_column(
        String(10), comment='券商代號'
    )
    broker_name: Mapped[Optional[str]] = mapped_column(
        String(100), comment='券商名稱'
    )
    buy_amount: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='買進金額（千元）'
    )
    sell_amount: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='賣出金額（千元）'
    )
    net_amount: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='買賣超金額（千元）'
    )
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default='TWSE', comment='資料來源'
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment='建立時間'
    )
    
    __table_args__ = (
        UniqueConstraint('symbol', 'date', 'broker_id', name='uq_chip_symbol_date_broker'),
        Index('idx_chip_symbol', 'symbol'),
        Index('idx_chip_date', 'date'),
        Index('idx_chip_symbol_date', 'symbol', 'date'),
        Index('idx_chip_foreign', 'foreign_buy', 'foreign_sell'),
        Index('idx_chip_margin', 'margin_buy', 'margin_sell'),
        Index('idx_chip_short', 'short_sell', 'short_cover'),
        Index('idx_chip_broker', 'broker_id'),
        Index('idx_chip_source', 'source'),
        Index('idx_chip_foreign_holding', 'foreign_holding_ratio'),
        {'comment': '籌碼面資料表'}
    )


class FundamentalData(Base):
    """基本面資料表
    
    儲存公司基本面財務資料，包括營收、獲利能力等指標。
    
    Attributes:
        id: 主鍵
        symbol: 股票代碼
        period_date: 資料期間日期
        revenue: 營收（千元）
        gross_profit: 毛利（千元）
        operating_income: 營業利益（千元）
        net_income: 淨利（千元）
        eps: 每股盈餘（元）
        roe: 股東權益報酬率（%）
        roa: 資產報酬率（%）
        debt_ratio: 負債比率（%）
        current_ratio: 流動比率（%）
        data_type: 資料類型（月營收/季報/年報）
        source: 資料來源
        created_at: 建立時間
    """
    __tablename__ = 'fundamental_data'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, comment='股票代碼')
    period_date: Mapped[date] = mapped_column(Date, nullable=False, comment='資料期間日期')
    revenue: Mapped[Optional[BigInteger]] = mapped_column(BigInteger, comment='營收（千元）')
    gross_profit: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='毛利（千元）'
    )
    operating_income: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='營業利益（千元）'
    )
    net_income: Mapped[Optional[BigInteger]] = mapped_column(
        BigInteger, comment='淨利（千元）'
    )
    eps: Mapped[Optional[float]] = mapped_column(Float, comment='每股盈餘（元）')
    roe: Mapped[Optional[float]] = mapped_column(Float, comment='股東權益報酬率（%）')
    roa: Mapped[Optional[float]] = mapped_column(Float, comment='資產報酬率（%）')
    debt_ratio: Mapped[Optional[float]] = mapped_column(Float, comment='負債比率（%）')
    current_ratio: Mapped[Optional[float]] = mapped_column(Float, comment='流動比率（%）')
    data_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment='資料類型'
    )
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default='TWSE', comment='資料來源'
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment='建立時間'
    )
    
    __table_args__ = (
        UniqueConstraint('symbol', 'period_date', 'data_type', name='uq_fundamental_symbol_period'),
        Index('idx_fundamental_symbol', 'symbol'),
        Index('idx_fundamental_date', 'period_date'),
        Index('idx_fundamental_type', 'data_type'),
        CheckConstraint(
            "data_type IN ('monthly_revenue', 'quarterly_report', 'annual_report')",
            name='ck_fundamental_data_type'
        ),
        {'comment': '基本面資料表'}
    )


class DataSourceStatus(Base):
    """資料來源狀態表
    
    監控各個資料來源的可用性和健康狀態。
    
    Attributes:
        id: 主鍵
        source_name: 資料來源名稱
        source_url: 資料來源網址
        last_check_time: 最後檢查時間
        is_available: 是否可用
        response_time: 回應時間（毫秒）
        error_count: 錯誤次數
        last_error_message: 最後錯誤訊息
        success_rate: 成功率（%）
        created_at: 建立時間
        updated_at: 更新時間
    """
    __tablename__ = 'data_source_status'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, comment='資料來源名稱'
    )
    source_url: Mapped[str] = mapped_column(String(500), nullable=False, comment='資料來源網址')
    last_check_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, comment='最後檢查時間'
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment='是否可用'
    )
    response_time: Mapped[Optional[int]] = mapped_column(Integer, comment='回應時間（毫秒）')
    error_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment='錯誤次數'
    )
    last_error_message: Mapped[Optional[str]] = mapped_column(
        Text, comment='最後錯誤訊息'
    )
    success_rate: Mapped[Optional[float]] = mapped_column(Float, comment='成功率（%）')
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment='建立時間'
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, comment='更新時間')
    
    __table_args__ = (
        Index('idx_source_name', 'source_name'),
        Index('idx_source_available', 'is_available'),
        Index('idx_source_check_time', 'last_check_time'),
        {'comment': '資料來源狀態表'}
    )


class DataQualityLog(Base):
    """資料品質日誌表
    
    記錄資料品質檢查的結果和異常情況。
    
    Attributes:
        id: 主鍵
        table_name: 資料表名稱
        symbol: 股票代碼（可選）
        check_date: 檢查日期
        quality_score: 品質分數（0-100）
        total_records: 總記錄數
        valid_records: 有效記錄數
        invalid_records: 無效記錄數
        missing_records: 缺失記錄數
        anomaly_count: 異常數量
        check_details: 檢查詳情（JSON格式）
        created_at: 建立時間
    """
    __tablename__ = 'data_quality_log'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False, comment='資料表名稱')
    symbol: Mapped[Optional[str]] = mapped_column(String(20), comment='股票代碼')
    check_date: Mapped[date] = mapped_column(Date, nullable=False, comment='檢查日期')
    quality_score: Mapped[float] = mapped_column(
        Float, nullable=False, comment='品質分數（0-100）'
    )
    total_records: Mapped[int] = mapped_column(Integer, nullable=False, comment='總記錄數')
    valid_records: Mapped[int] = mapped_column(Integer, nullable=False, comment='有效記錄數')
    invalid_records: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment='無效記錄數'
    )
    missing_records: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment='缺失記錄數'
    )
    anomaly_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment='異常數量'
    )
    check_details: Mapped[Optional[str]] = mapped_column(
        Text, comment='檢查詳情（JSON格式）'
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, comment='建立時間'
    )
    
    __table_args__ = (
        Index('idx_quality_table', 'table_name'),
        Index('idx_quality_symbol', 'symbol'),
        Index('idx_quality_date', 'check_date'),
        Index('idx_quality_score', 'quality_score'),
        CheckConstraint(
            'quality_score >= 0 AND quality_score <= 100',
            name='ck_quality_score_range'
        ),
        {'comment': '資料品質日誌表'}
    )
