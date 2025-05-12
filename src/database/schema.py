# type: ignore
# -*- coding: utf-8 -*-
"""
資料庫schema定義
"""

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Date,
)
from sqlalchemy.orm import declarative_base

# type: ignore[misc, valid-type]
Base = declarative_base()


class MarketDaily(Base):
    """
    市場日線資料表
    """

    __tablename__ = "market_daily"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String, index=True, nullable=False)  # 股票代碼
    date = Column(Date, index=True, nullable=False)  # 交易日期
    open = Column(Float)  # 開盤價
    high = Column(Float)  # 最高價
    low = Column(Float)  # 最低價
    close = Column(Float)  # 收盤價
    volume = Column(Float)  # 成交量
    ma5 = Column(Float)  # 5日均線
    ma20 = Column(Float)  # 20日均線
