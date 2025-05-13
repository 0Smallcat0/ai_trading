"""
券商 API 適配器

此模組提供與各種券商 API 連接的功能，
並將資料轉換為系統標準格式。

主要功能：
- 獲取帳戶資訊
- 獲取持倉資訊
- 獲取歷史交易記錄
- 獲取即時報價
- 下單和撤單
"""

import os
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from abc import ABC, abstractmethod

from src.config import DATA_DIR, CACHE_DIR
from src.database.schema import MarketType, TimeGranularity
from src.core.rate_limiter import RateLimiter

# 設定日誌
logger = logging.getLogger(__name__)

# 建立快取目錄
BROKER_CACHE_DIR = os.path.join(CACHE_DIR, "broker")
os.makedirs(BROKER_CACHE_DIR, exist_ok=True)


class BrokerAdapter(ABC):
    """券商 API 適配器基類"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        account_id: Optional[str] = None,
        use_cache: bool = True,
        cache_expiry_days: int = 1,
    ):
        """
        初始化券商 API 適配器

        Args:
            api_key: API 金鑰
            api_secret: API 密鑰
            account_id: 帳戶 ID
            use_cache: 是否使用快取
            cache_expiry_days: 快取過期天數
        """
        self.api_key = api_key or os.getenv("BROKER_API_KEY", "")
        self.api_secret = api_secret or os.getenv("BROKER_API_SECRET", "")
        self.account_id = account_id or os.getenv("BROKER_ACCOUNT_ID", "")
        self.use_cache = use_cache
        self.cache_expiry_days = cache_expiry_days
        self.connected = False
        self.rate_limiter = RateLimiter(
            max_calls=60, period=60
        )  # 預設每分鐘最多 60 次請求

    @abstractmethod
    def connect(self) -> bool:
        """
        連接券商 API

        Returns:
            bool: 是否連接成功
        """
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """
        斷開券商 API 連接

        Returns:
            bool: 是否斷開成功
        """
        pass

    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """
        獲取帳戶資訊

        Returns:
            Dict[str, Any]: 帳戶資訊
        """
        pass

    @abstractmethod
    def get_positions(self) -> pd.DataFrame:
        """
        獲取持倉資訊

        Returns:
            pd.DataFrame: 持倉資訊
        """
        pass

    @abstractmethod
    def get_historical_trades(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        獲取歷史交易記錄

        Args:
            start_date: 開始日期，格式為 'YYYY-MM-DD'
            end_date: 結束日期，格式為 'YYYY-MM-DD'

        Returns:
            pd.DataFrame: 歷史交易記錄
        """
        pass

    @abstractmethod
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        獲取即時報價

        Args:
            symbol: 股票代碼

        Returns:
            Dict[str, Any]: 即時報價
        """
        pass

    def _get_cache_path(self, data_type: str, params: Dict[str, Any] = None) -> str:
        """
        獲取快取檔案路徑

        Args:
            data_type: 資料類型
            params: 參數字典

        Returns:
            str: 快取檔案路徑
        """
        broker_name = self.__class__.__name__.lower().replace("brokeradapter", "")
        broker_dir = os.path.join(BROKER_CACHE_DIR, broker_name)
        os.makedirs(broker_dir, exist_ok=True)

        if params:
            param_str = "_".join(f"{k}_{v}" for k, v in params.items())
            return os.path.join(broker_dir, f"{data_type}_{param_str}.csv")
        else:
            return os.path.join(broker_dir, f"{data_type}.csv")

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


class SimulatedBrokerAdapter(BrokerAdapter):
    """模擬券商 API 適配器，用於測試和開發"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        account_id: Optional[str] = None,
        use_cache: bool = True,
        cache_expiry_days: int = 1,
        initial_balance: float = 1000000.0,
    ):
        """
        初始化模擬券商 API 適配器

        Args:
            api_key: API 金鑰
            api_secret: API 密鑰
            account_id: 帳戶 ID
            use_cache: 是否使用快取
            cache_expiry_days: 快取過期天數
            initial_balance: 初始資金
        """
        super().__init__(api_key, api_secret, account_id, use_cache, cache_expiry_days)
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions = pd.DataFrame(
            columns=["symbol", "quantity", "avg_price", "market_value"]
        )
        self.trades = pd.DataFrame(
            columns=[
                "trade_id",
                "symbol",
                "action",
                "quantity",
                "price",
                "timestamp",
                "status",
                "commission",
            ]
        )
        self.connected = True

    def connect(self) -> bool:
        """
        連接模擬券商 API

        Returns:
            bool: 是否連接成功
        """
        self.connected = True
        logger.info("已連接模擬券商 API")
        return True

    def disconnect(self) -> bool:
        """
        斷開模擬券商 API 連接

        Returns:
            bool: 是否斷開成功
        """
        self.connected = False
        logger.info("已斷開模擬券商 API 連接")
        return True

    def get_account_info(self) -> Dict[str, Any]:
        """
        獲取帳戶資訊

        Returns:
            Dict[str, Any]: 帳戶資訊
        """
        # 使用速率限制器
        with self.rate_limiter:
            return {
                "account_id": self.account_id or "simulated_account",
                "balance": self.balance,
                "equity": self.balance + self.positions["market_value"].sum(),
                "margin": 0.0,
                "free_margin": self.balance,
                "margin_level": 100.0,
                "currency": "TWD",
            }

    def get_positions(self) -> pd.DataFrame:
        """
        獲取持倉資訊

        Returns:
            pd.DataFrame: 持倉資訊
        """
        # 使用速率限制器
        with self.rate_limiter:
            return self.positions.copy()

    def get_historical_trades(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        獲取歷史交易記錄

        Args:
            start_date: 開始日期，格式為 'YYYY-MM-DD'
            end_date: 結束日期，格式為 'YYYY-MM-DD'

        Returns:
            pd.DataFrame: 歷史交易記錄
        """
        # 使用速率限制器
        with self.rate_limiter:
            if start_date is None and end_date is None:
                return self.trades.copy()

            # 轉換日期
            if start_date:
                start_dt = pd.to_datetime(start_date)
            else:
                start_dt = pd.Timestamp.min

            if end_date:
                end_dt = pd.to_datetime(end_date)
            else:
                end_dt = pd.Timestamp.max

            # 過濾交易記錄
            mask = (pd.to_datetime(self.trades["timestamp"]) >= start_dt) & (
                pd.to_datetime(self.trades["timestamp"]) <= end_dt
            )
            return self.trades[mask].copy()

    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        獲取即時報價

        Args:
            symbol: 股票代碼

        Returns:
            Dict[str, Any]: 即時報價
        """
        # 使用速率限制器
        with self.rate_limiter:
            # 模擬報價，使用隨機數據
            import random

            base_price = 100.0
            if symbol in self.positions["symbol"].values:
                # 如果有持倉，使用平均價格作為基準
                position = self.positions[self.positions["symbol"] == symbol]
                base_price = position["avg_price"].values[0]

            price = base_price * (1 + random.uniform(-0.05, 0.05))
            return {
                "symbol": symbol,
                "bid": price * 0.995,
                "ask": price * 1.005,
                "last": price,
                "high": price * 1.01,
                "low": price * 0.99,
                "volume": random.randint(1000, 10000),
                "timestamp": datetime.now().isoformat(),
            }
