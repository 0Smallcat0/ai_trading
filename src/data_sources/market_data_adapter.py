# -*- coding: utf-8 -*-
"""
市場數據適配器模組

此模組提供統一的市場數據存取介面，
支援多種數據來源，並將數據轉換為標準格式。

主要功能：
- 連接不同的數據來源
- 獲取歷史價格數據
- 獲取即時報價
- 獲取基本面數據
- 獲取技術指標
"""

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from src.config import CACHE_DIR
from src.core.rate_limiter import RateLimiter
from src.database.schema import MarketType, TimeGranularity

# 設定日誌
logger = logging.getLogger(__name__)


class MarketDataAdapter(ABC):
    """
    市場數據適配器基礎類別，負責連接數據源並取得市場資料。
    所有具體的數據來源適配器都應該繼承此類。
    """

    def __init__(
        self,
        source: str,
        use_cache: bool = True,
        cache_expiry_days: int = 1,
        rate_limit_max_calls: int = 60,
        rate_limit_period: int = 60,
    ):
        """
        初始化市場數據適配器

        Args:
            source: 數據來源名稱（如 'yahoo', 'twse' 等）
            use_cache: 是否使用快取
            cache_expiry_days: 快取過期天數
            rate_limit_max_calls: 速率限制最大請求數
            rate_limit_period: 速率限制時間段（秒）
        """
        self.source = source
        self.use_cache = use_cache
        self.cache_expiry_days = cache_expiry_days
        self.connection = None
        self.connected = False

        # 建立快取目錄
        self.cache_dir = os.path.join(CACHE_DIR, source)
        os.makedirs(self.cache_dir, exist_ok=True)

        # 建立速率限制器
        self.rate_limiter = RateLimiter(
            max_calls=rate_limit_max_calls,
            period=rate_limit_period,
        )

    @abstractmethod
    def connect(self) -> bool:
        """
        連接到指定的數據來源

        Returns:
            bool: 是否連接成功
        """

    @abstractmethod
    def disconnect(self) -> bool:
        """
        斷開與數據來源的連接

        Returns:
            bool: 是否斷開成功
        """

    @abstractmethod
    def get_historical_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d",
        use_cache: Optional[bool] = None,
    ) -> pd.DataFrame:
        """
        獲取歷史價格數據

        Args:
            symbol: 股票代碼
            start_date: 開始日期，格式為 'YYYY-MM-DD'
            end_date: 結束日期，格式為 'YYYY-MM-DD'
            interval: 時間間隔，如 '1d', '1h', '5m' 等
            use_cache: 是否使用快取，如果為 None 則使用類別設定

        Returns:
            pd.DataFrame: 歷史價格數據
        """

    @abstractmethod
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        獲取即時報價

        Args:
            symbol: 股票代碼

        Returns:
            Dict[str, Any]: 即時報價
        """

    def _get_cache_path(
        self, symbol: str, data_type: str, start_date: str, end_date: str
    ) -> str:
        """
        獲取快取檔案路徑

        Args:
            symbol: 股票代碼
            data_type: 數據類型
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            str: 快取檔案路徑
        """
        symbol_dir = os.path.join(self.cache_dir, symbol.replace(".", "_"))
        os.makedirs(symbol_dir, exist_ok=True)
        return os.path.join(symbol_dir, f"{data_type}_{start_date}_{end_date}.csv")

    def _is_cache_valid(self, cache_path: str) -> bool:
        """
        檢查快取是否有效

        Args:
            cache_path: 快取檔案路徑

        Returns:
            bool: 快取是否有效
        """
        if not os.path.exists(cache_path):
            return False

        # 檢查檔案修改時間
        file_time = os.path.getmtime(cache_path)
        file_date = datetime.fromtimestamp(file_time)
        now = datetime.now()
        return (now - file_date).days < self.cache_expiry_days

    def standardize_dataframe(
        self, df: pd.DataFrame, symbol: str, interval: str
    ) -> pd.DataFrame:
        """
        標準化數據框架

        將不同來源的數據轉換為統一的格式，包括欄位名稱、數據類型等。

        Args:
            df: 原始數據框架
            symbol: 股票代碼
            interval: 時間間隔

        Returns:
            pd.DataFrame: 標準化後的數據框架
        """
        if df.empty:
            return df

        # 複製數據框架，避免修改原始數據
        df = df.copy()

        # 標準化欄位名稱
        column_mapping = {
            "date": "date",
            "timestamp": "timestamp",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
            "adj close": "adj_close",
            "adjusted_close": "adj_close",
        }

        # 將欄位名稱轉為小寫
        df.columns = [col.lower() for col in df.columns]

        # 重命名欄位
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns and old_col != new_col:
                df.rename(columns={old_col: new_col}, inplace=True)

        # 添加股票代碼欄位
        if "symbol" not in df.columns:
            df["symbol"] = symbol

        # 添加市場類型欄位
        if "market_type" not in df.columns:
            if ".TW" in symbol:
                df["market_type"] = MarketType.STOCK.value
            elif symbol.startswith("^"):
                df["market_type"] = MarketType.INDEX.value
            else:
                df["market_type"] = MarketType.STOCK.value

        # 添加時間粒度欄位
        if "granularity" not in df.columns:
            if interval == "1d":
                df["granularity"] = TimeGranularity.DAY_1.value
            elif interval == "1wk":
                df["granularity"] = TimeGranularity.WEEK_1.value
            elif interval == "1mo":
                df["granularity"] = TimeGranularity.MONTH_1.value
            elif interval == "1m":
                df["granularity"] = TimeGranularity.MIN_1.value
            elif interval == "5m":
                df["granularity"] = TimeGranularity.MIN_5.value
            elif interval == "15m":
                df["granularity"] = TimeGranularity.MIN_15.value
            elif interval == "30m":
                df["granularity"] = TimeGranularity.MIN_30.value
            elif interval == "60m" or interval == "1h":
                df["granularity"] = TimeGranularity.HOUR_1.value
            else:
                df["granularity"] = interval

        # 添加資料來源欄位
        if "data_source" not in df.columns:
            df["data_source"] = self.source

        # 添加是否調整欄位
        if "is_adjusted" not in df.columns:
            df["is_adjusted"] = "adj_close" in df.columns

        # 處理日期欄位
        date_columns = [col for col in df.columns if col in ["date", "timestamp"]]
        for col in date_columns:
            if df[col].dtype == "object":
                df[col] = pd.to_datetime(df[col])

        return df
