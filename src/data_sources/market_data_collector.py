"""
市場資料收集器模組

此模組提供收集市場資料的功能，包括：
- 日線/分鐘線資料收集
- 多來源資料整合
- 資料驗證與儲存

支援從 Yahoo Finance、券商 API 等多個來源收集資料。
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import CACHE_DIR, DATA_DIR, DB_PATH
from src.data_sources.data_collector import DataCollector, RetryStrategy
from src.data_sources.twse_crawler import TwseCrawler
from src.data_sources.yahoo_adapter import YahooFinanceAdapter
from src.database.schema import MarketDaily, MarketMinute, MarketType, TimeGranularity

# 設定日誌
logger = logging.getLogger(__name__)


class MarketDataCollector(DataCollector):
    """
    市場資料收集器

    負責收集日線/分鐘線資料，支援多來源資料整合。
    """

    def __init__(
        self,
        source: str = "yahoo",
        use_cache: bool = True,
        cache_expiry_days: int = 1,
        retry_strategy: Optional[RetryStrategy] = None,
    ):
        """
        初始化市場資料收集器

        Args:
            source: 資料來源，預設為 'yahoo'
            use_cache: 是否使用快取
            cache_expiry_days: 快取過期天數
            retry_strategy: 重試策略
        """
        super().__init__(
            name=f"MarketDataCollector_{source}",
            source=source,
            use_cache=use_cache,
            cache_expiry_days=cache_expiry_days,
            retry_strategy=retry_strategy,
        )

        # 初始化資料適配器
        if source == "yahoo":
            self.adapter = YahooFinanceAdapter(
                use_cache=use_cache, cache_expiry_days=cache_expiry_days
            )
        elif source == "twse":
            self.adapter = TwseCrawler()
        else:
            raise ValueError(f"不支援的資料來源: {source}")

        # 初始化資料庫連接
        self.engine = create_engine(f"sqlite:///{DB_PATH}")
        self.Session = sessionmaker(bind=self.engine)

    def collect_daily_data(
        self,
        symbols: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        save_to_db: bool = True,
        max_workers: int = 5,
    ) -> Dict[str, pd.DataFrame]:
        """
        收集日線資料

        Args:
            symbols: 股票代碼列表
            start_date: 開始日期，格式為 'YYYY-MM-DD'，如果為 None 則使用一年前的日期
            end_date: 結束日期，格式為 'YYYY-MM-DD'，如果為 None 則使用今天的日期
            save_to_db: 是否儲存到資料庫
            max_workers: 最大工作執行緒數

        Returns:
            Dict[str, pd.DataFrame]: 股票代碼到日線資料的映射
        """
        logger.info(f"開始收集 {len(symbols)} 檔股票的日線資料")

        # 設定日期
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        results = {}

        # 使用執行緒池並行獲取資料
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任務
            future_to_symbol = {
                executor.submit(
                    self.with_retry,
                    self.adapter.get_historical_data,
                    symbol,
                    start_date,
                    end_date,
                    "1d",
                    self.use_cache,
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
                        logger.info(f"成功收集 {symbol} 的日線資料，共 {len(data)} 筆")

                        # 儲存到資料庫
                        if save_to_db:
                            self._save_daily_data_to_db(data)
                    else:
                        logger.warning(f"收集 {symbol} 的日線資料為空")
                except Exception as e:
                    logger.error(f"收集 {symbol} 的日線資料時發生錯誤: {e}")

        logger.info(f"完成收集日線資料，成功收集 {len(results)} 檔股票")
        return results

    def collect_minute_data(
        self,
        symbols: List[str],
        interval: str = "1m",
        days: int = 7,
        save_to_db: bool = True,
        max_workers: int = 5,
    ) -> Dict[str, pd.DataFrame]:
        """
        收集分鐘線資料

        Args:
            symbols: 股票代碼列表
            interval: 時間間隔，可選 '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h'
            days: 收集的天數，Yahoo Finance 對分鐘資料有限制，通常只能獲取最近 7 天的資料
            save_to_db: 是否儲存到資料庫
            max_workers: 最大工作執行緒數

        Returns:
            Dict[str, pd.DataFrame]: 股票代碼到分鐘線資料的映射
        """
        logger.info(f"開始收集 {len(symbols)} 檔股票的 {interval} 分鐘線資料")

        # 設定日期
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        results = {}

        # 使用執行緒池並行獲取資料
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任務
            future_to_symbol = {
                executor.submit(
                    self.with_retry,
                    self.adapter.get_historical_data,
                    symbol,
                    start_date,
                    end_date,
                    interval,
                    self.use_cache,
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
                        logger.info(
                            f"成功收集 {symbol} 的 {interval} 分鐘線資料，共 {len(data)} 筆"
                        )

                        # 儲存到資料庫
                        if save_to_db:
                            self._save_minute_data_to_db(data)
                    else:
                        logger.warning(f"收集 {symbol} 的 {interval} 分鐘線資料為空")
                except Exception as e:
                    logger.error(
                        f"收集 {symbol} 的 {interval} 分鐘線資料時發生錯誤: {e}"
                    )

        logger.info(f"完成收集 {interval} 分鐘線資料，成功收集 {len(results)} 檔股票")
        return results

    def _save_daily_data_to_db(self, data: pd.DataFrame) -> None:
        """
        將日線資料儲存到資料庫

        Args:
            data: 日線資料
        """
        session = self.Session()
        try:
            for _, row in data.iterrows():
                # 檢查是否已存在相同的記錄
                existing = (
                    session.query(MarketDaily)
                    .filter(
                        MarketDaily.symbol == row["symbol"],
                        MarketDaily.date == row["date"],
                    )
                    .first()
                )

                if existing:
                    # 更新現有記錄
                    existing.open = row["open"]
                    existing.high = row["high"]
                    existing.low = row["low"]
                    existing.close = row["close"]
                    existing.volume = row["volume"]
                    existing.data_source = row["data_source"]
                    existing.is_adjusted = row["is_adjusted"]
                    existing.updated_at = datetime.now()
                else:
                    # 創建新記錄
                    market_data = MarketDaily(
                        symbol=row["symbol"],
                        date=row["date"],
                        open=row["open"],
                        high=row["high"],
                        low=row["low"],
                        close=row["close"],
                        volume=row["volume"],
                        market_type=row["market_type"],
                        data_source=row["data_source"],
                        is_adjusted=row["is_adjusted"],
                    )
                    session.add(market_data)

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"儲存日線資料到資料庫時發生錯誤: {e}")
        finally:
            session.close()

    def _save_minute_data_to_db(self, data: pd.DataFrame) -> None:
        """
        將分鐘線資料儲存到資料庫

        Args:
            data: 分鐘線資料
        """
        session = self.Session()
        try:
            for _, row in data.iterrows():
                # 檢查是否已存在相同的記錄
                existing = (
                    session.query(MarketMinute)
                    .filter(
                        MarketMinute.symbol == row["symbol"],
                        MarketMinute.timestamp == row["timestamp"],
                        MarketMinute.granularity == row["granularity"],
                    )
                    .first()
                )

                if existing:
                    # 更新現有記錄
                    existing.open = row["open"]
                    existing.high = row["high"]
                    existing.low = row["low"]
                    existing.close = row["close"]
                    existing.volume = row["volume"]
                    existing.data_source = row["data_source"]
                    existing.is_adjusted = row["is_adjusted"]
                    existing.updated_at = datetime.now()
                else:
                    # 創建新記錄
                    market_data = MarketMinute(
                        symbol=row["symbol"],
                        timestamp=row["timestamp"],
                        granularity=row["granularity"],
                        open=row["open"],
                        high=row["high"],
                        low=row["low"],
                        close=row["close"],
                        volume=row["volume"],
                        market_type=row["market_type"],
                        data_source=row["data_source"],
                        is_adjusted=row["is_adjusted"],
                    )
                    session.add(market_data)

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"儲存分鐘線資料到資料庫時發生錯誤: {e}")
        finally:
            session.close()

    def collect(
        self, symbols: List[str], data_type: str = "daily", **kwargs
    ) -> Dict[str, pd.DataFrame]:
        """
        收集資料的實現方法

        Args:
            symbols: 股票代碼列表
            data_type: 資料類型，可選 'daily' 或 'minute'
            **kwargs: 其他參數，將傳遞給對應的收集方法

        Returns:
            Dict[str, pd.DataFrame]: 收集的資料
        """
        if data_type == "daily":
            return self.collect_daily_data(symbols, **kwargs)
        elif data_type == "minute":
            return self.collect_minute_data(symbols, **kwargs)
        else:
            raise ValueError(f"不支援的資料類型: {data_type}")
