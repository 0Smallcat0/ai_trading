"""
Yahoo Finance 資料適配器

此模組提供從 Yahoo Finance API 獲取股票資料的功能，
並將資料轉換為系統標準格式。

主要功能：
- 獲取歷史價格資料
- 獲取公司基本資料
- 獲取財務報表資料
- 獲取即時報價
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import yfinance as yf

from src.config import CACHE_DIR
from src.core.rate_limiter import RateLimiter
from src.database.schema import MarketType, TimeGranularity

# 設定日誌
logger = logging.getLogger(__name__)

# 建立快取目錄
YAHOO_CACHE_DIR = os.path.join(CACHE_DIR, "yahoo")
os.makedirs(YAHOO_CACHE_DIR, exist_ok=True)

# 建立速率限制器 (每分鐘最多 60 次請求)
rate_limiter = RateLimiter(max_calls=60, period=60)


class YahooFinanceAdapter:
    """Yahoo Finance 資料適配器"""

    def __init__(self, use_cache: bool = True, cache_expiry_days: int = 1):
        """
        初始化 Yahoo Finance 適配器

        Args:
            use_cache: 是否使用快取
            cache_expiry_days: 快取過期天數
        """
        self.use_cache = use_cache
        self.cache_expiry_days = cache_expiry_days
        self.session = None

    def _get_cache_path(
        self, symbol: str, data_type: str, start_date: str, end_date: str
    ) -> str:
        """
        獲取快取檔案路徑

        Args:
            symbol: 股票代碼
            data_type: 資料類型
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            str: 快取檔案路徑
        """
        symbol_dir = os.path.join(YAHOO_CACHE_DIR, symbol.replace(".", "_"))
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

    def _format_symbol(self, symbol: str) -> str:
        """
        格式化股票代碼

        Args:
            symbol: 原始股票代碼

        Returns:
            str: 格式化後的股票代碼
        """
        # 台股自動添加 .TW 後綴
        if symbol.isdigit() and len(symbol) == 4:
            return f"{symbol}.TW"
        return symbol

    def get_historical_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d",
        use_cache: Optional[bool] = None,
    ) -> pd.DataFrame:
        """
        獲取歷史價格資料

        Args:
            symbol: 股票代碼
            start_date: 開始日期，格式為 'YYYY-MM-DD'
            end_date: 結束日期，格式為 'YYYY-MM-DD'
            interval: 時間間隔，可選 '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo'
            use_cache: 是否使用快取，如果為 None 則使用類別設定

        Returns:
            pd.DataFrame: 歷史價格資料
        """
        # 使用速率限制器
        with rate_limiter:
            # 格式化股票代碼
            symbol = self._format_symbol(symbol)

            # 設定日期
            if end_date is None:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if start_date is None:
                # 根據間隔設定預設的開始日期
                if interval in ["1d", "5d", "1wk", "1mo", "3mo"]:
                    start_date = (datetime.now() - timedelta(days=365)).strftime(
                        "%Y-%m-%d"
                    )
                else:
                    start_date = (datetime.now() - timedelta(days=7)).strftime(
                        "%Y-%m-%d"
                    )

            # 檢查是否使用快取
            use_cache = self.use_cache if use_cache is None else use_cache
            cache_path = self._get_cache_path(
                symbol, f"hist_{interval}", start_date, end_date
            )

            if use_cache and self._is_cache_valid(cache_path):
                logger.info(f"從快取讀取 {symbol} 的歷史資料")
                return pd.read_csv(cache_path, index_col=0, parse_dates=True)

            try:
                # 獲取股票資料
                logger.info(f"從 Yahoo Finance 獲取 {symbol} 的歷史資料")
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=start_date, end=end_date, interval=interval)

                # 如果資料為空，返回空 DataFrame
                if df.empty:
                    logger.warning(f"無法獲取 {symbol} 的歷史資料")
                    return pd.DataFrame()

                # 標準化欄位名稱
                df.columns = [col.lower() for col in df.columns]

                # 添加股票代碼欄位
                df["symbol"] = symbol

                # 添加市場類型欄位
                if ".TW" in symbol:
                    df["market_type"] = MarketType.STOCK.value
                elif symbol.startswith("^"):
                    df["market_type"] = MarketType.INDEX.value
                else:
                    df["market_type"] = MarketType.STOCK.value

                # 添加時間粒度欄位
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
                df["data_source"] = "yahoo"

                # 添加是否調整欄位
                df["is_adjusted"] = True

                # 重設索引，將日期轉為欄位
                df = df.reset_index()
                df.rename(
                    columns={
                        "index": (
                            "date"
                            if interval in ["1d", "5d", "1wk", "1mo", "3mo"]
                            else "timestamp"
                        )
                    },
                    inplace=True,
                )

                # 儲存到快取
                if use_cache:
                    df.to_csv(cache_path)

                return df

            except Exception as e:
                logger.error(f"獲取 {symbol} 的歷史資料時發生錯誤: {e}")
                return pd.DataFrame()

    def get_company_info(
        self, symbol: str, use_cache: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        獲取公司基本資料

        Args:
            symbol: 股票代碼
            use_cache: 是否使用快取，如果為 None 則使用類別設定

        Returns:
            Dict[str, Any]: 公司基本資料
        """
        # 使用速率限制器
        with rate_limiter:
            # 格式化股票代碼
            symbol = self._format_symbol(symbol)

            # 檢查是否使用快取
            use_cache = self.use_cache if use_cache is None else use_cache
            cache_path = self._get_cache_path(symbol, "info", "", "")

            if use_cache and self._is_cache_valid(cache_path):
                logger.info(f"從快取讀取 {symbol} 的公司資料")
                return pd.read_csv(cache_path, index_col=0).to_dict("records")[0]

            try:
                # 獲取股票資料
                logger.info(f"從 Yahoo Finance 獲取 {symbol} 的公司資料")
                ticker = yf.Ticker(symbol)
                info = ticker.info

                # 如果資料為空，返回空字典
                if not info:
                    logger.warning(f"無法獲取 {symbol} 的公司資料")
                    return {}

                # 儲存到快取
                if use_cache:
                    pd.DataFrame([info]).to_csv(cache_path)

                return info

            except Exception as e:
                logger.error(f"獲取 {symbol} 的公司資料時發生錯誤: {e}")
                return {}

    def get_multiple_historical_data(
        self,
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d",
        use_cache: Optional[bool] = None,
        max_workers: int = 5,
    ) -> Dict[str, pd.DataFrame]:
        """
        獲取多個股票的歷史價格資料

        Args:
            symbols: 股票代碼列表
            start_date: 開始日期，格式為 'YYYY-MM-DD'
            end_date: 結束日期，格式為 'YYYY-MM-DD'
            interval: 時間間隔，可選 '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo'
            use_cache: 是否使用快取，如果為 None 則使用類別設定
            max_workers: 最大工作執行緒數

        Returns:
            Dict[str, pd.DataFrame]: 股票代碼到歷史價格資料的映射
        """
        results = {}

        # 使用執行緒池並行獲取資料
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任務
            future_to_symbol = {
                executor.submit(
                    self.get_historical_data,
                    symbol,
                    start_date,
                    end_date,
                    interval,
                    use_cache,
                ): symbol
                for symbol in symbols
            }

            # 獲取結果
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    data = future.result()
                    if not data.empty:
                        results[symbol] = data
                except Exception as e:
                    logger.error(f"獲取 {symbol} 的歷史資料時發生錯誤: {e}")

        return results
