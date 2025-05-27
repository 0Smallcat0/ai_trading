"""
財務報表收集器模組

此模組提供收集公司財務報表資料的功能，包括：
- 季度/年度財務報表收集
- 財務比率計算
- 資料驗證與儲存

支援從 Yahoo Finance、公開資訊觀測站等多個來源收集資料。
"""

import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import CACHE_DIR, DATA_DIR, DB_PATH
from src.data_sources.data_collector import DataCollector, RetryStrategy
from src.data_sources.yahoo_adapter import YahooFinanceAdapter
from src.database.schema import Fundamental

# 設定日誌
logger = logging.getLogger(__name__)


class FinancialStatementCollector(DataCollector):
    """
    財務報表收集器

    負責收集公司財務報表資料，支援多來源資料整合。
    """

    def __init__(
        self,
        source: str = "yahoo",
        use_cache: bool = True,
        cache_expiry_days: int = 30,  # 財務資料變化較慢，可以使用較長的快取時間
        retry_strategy: Optional[RetryStrategy] = None,
    ):
        """
        初始化財務報表收集器

        Args:
            source: 資料來源，預設為 'yahoo'
            use_cache: 是否使用快取
            cache_expiry_days: 快取過期天數
            retry_strategy: 重試策略
        """
        super().__init__(
            name=f"FinancialStatementCollector_{source}",
            source=source,
            use_cache=use_cache,
            cache_expiry_days=cache_expiry_days,
            retry_strategy=retry_strategy,
        )

        # 初始化資料適配器
        if source == "yahoo":
            self.adapter = YahooFinanceAdapter(use_cache=use_cache, cache_expiry_days=cache_expiry_days)
        else:
            raise ValueError(f"不支援的資料來源: {source}")

        # 初始化資料庫連接
        self.engine = create_engine(f"sqlite:///{DB_PATH}")
        self.Session = sessionmaker(bind=self.engine)

    def collect_company_info(
        self,
        symbols: List[str],
        save_to_db: bool = True,
        max_workers: int = 5,
    ) -> Dict[str, Dict[str, Any]]:
        """
        收集公司基本資料

        Args:
            symbols: 股票代碼列表
            save_to_db: 是否儲存到資料庫
            max_workers: 最大工作執行緒數

        Returns:
            Dict[str, Dict[str, Any]]: 股票代碼到公司基本資料的映射
        """
        logger.info(f"開始收集 {len(symbols)} 檔股票的公司基本資料")

        results = {}

        # 使用執行緒池並行獲取資料
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任務
            future_to_symbol = {
                executor.submit(
                    self.with_retry,
                    self.adapter.get_company_info,
                    symbol,
                    self.use_cache,
                ): symbol
                for symbol in symbols
            }

            # 獲取結果
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    data = future.result()
                    if data:
                        results[symbol] = data
                        logger.info(f"成功收集 {symbol} 的公司基本資料")

                        # 儲存到資料庫
                        if save_to_db:
                            self._save_company_info_to_db(symbol, data)
                    else:
                        logger.warning(f"收集 {symbol} 的公司基本資料為空")
                except Exception as e:
                    logger.error(f"收集 {symbol} 的公司基本資料時發生錯誤: {e}")

        logger.info(f"完成收集公司基本資料，成功收集 {len(results)} 檔股票")
        return results

    def collect_financial_ratios(
        self,
        symbols: List[str],
        save_to_db: bool = True,
        max_workers: int = 5,
    ) -> Dict[str, pd.DataFrame]:
        """
        收集財務比率資料

        Args:
            symbols: 股票代碼列表
            save_to_db: 是否儲存到資料庫
            max_workers: 最大工作執行緒數

        Returns:
            Dict[str, pd.DataFrame]: 股票代碼到財務比率資料的映射
        """
        logger.info(f"開始收集 {len(symbols)} 檔股票的財務比率資料")

        results = {}

        # 使用執行緒池並行獲取資料
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任務
            future_to_symbol = {
                executor.submit(
                    self._collect_financial_ratios_for_symbol,
                    symbol,
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
                        logger.info(f"成功收集 {symbol} 的財務比率資料")

                        # 儲存到資料庫
                        if save_to_db:
                            self._save_financial_ratios_to_db(symbol, data)
                    else:
                        logger.warning(f"收集 {symbol} 的財務比率資料為空")
                except Exception as e:
                    logger.error(f"收集 {symbol} 的財務比率資料時發生錯誤: {e}")

        logger.info(f"完成收集財務比率資料，成功收集 {len(results)} 檔股票")
        return results

    def _collect_financial_ratios_for_symbol(self, symbol: str) -> pd.DataFrame:
        """
        收集單一股票的財務比率資料

        Args:
            symbol: 股票代碼

        Returns:
            pd.DataFrame: 財務比率資料
        """
        # 檢查快取
        cache_path = self._get_cache_path("financial_ratios", symbol, "", "")
        if self.use_cache and self._is_cache_valid(cache_path):
            logger.info(f"從快取讀取 {symbol} 的財務比率資料")
            return pd.read_csv(cache_path)

        # 從 Yahoo Finance 獲取資料
        if self.source == "yahoo":
            try:
                # 獲取公司基本資料
                info = self.adapter.get_company_info(symbol)
                if not info:
                    return pd.DataFrame()

                # 提取財務比率
                today = datetime.now().date()
                data = {
                    "symbol": symbol,
                    "date": today,
                    "pe_ratio": info.get("trailingPE"),
                    "pb_ratio": info.get("priceToBook"),
                    "ps_ratio": info.get("priceToSalesTrailing12Months"),
                    "dividend_yield": info.get("dividendYield"),
                    "roe": info.get("returnOnEquity"),
                    "roa": info.get("returnOnAssets"),
                    "market_cap": info.get("marketCap"),
                    "outstanding_shares": info.get("sharesOutstanding"),
                    "industry": info.get("industry"),
                }

                # 創建 DataFrame
                df = pd.DataFrame([data])

                # 儲存到快取
                if self.use_cache:
                    df.to_csv(cache_path, index=False)

                return df
            except Exception as e:
                logger.error(f"從 Yahoo Finance 獲取 {symbol} 的財務比率資料時發生錯誤: {e}")
                return pd.DataFrame()
        else:
            raise ValueError(f"不支援的資料來源: {self.source}")

    def _save_company_info_to_db(self, symbol: str, data: Dict[str, Any]) -> None:
        """
        將公司基本資料儲存到資料庫

        Args:
            symbol: 股票代碼
            data: 公司基本資料
        """
        session = self.Session()
        try:
            # 提取需要的資料
            today = datetime.now().date()

            # 檢查是否已存在相同的記錄
            existing = session.query(Fundamental).filter(
                Fundamental.symbol == symbol,
                Fundamental.date == today,
            ).first()

            if existing:
                # 更新現有記錄
                existing.pe_ratio = data.get("trailingPE")
                existing.pb_ratio = data.get("priceToBook")
                existing.ps_ratio = data.get("priceToSalesTrailing12Months")
                existing.dividend_yield = data.get("dividendYield")
                existing.roe = data.get("returnOnEquity")
                existing.roa = data.get("returnOnAssets")
                existing.market_cap = data.get("marketCap")
                existing.outstanding_shares = data.get("sharesOutstanding")
                existing.industry = data.get("industry")
                existing.updated_at = datetime.now()
            else:
                # 創建新記錄
                fundamental = Fundamental(
                    symbol=symbol,
                    date=today,
                    pe_ratio=data.get("trailingPE"),
                    pb_ratio=data.get("priceToBook"),
                    ps_ratio=data.get("priceToSalesTrailing12Months"),
                    dividend_yield=data.get("dividendYield"),
                    roe=data.get("returnOnEquity"),
                    roa=data.get("returnOnAssets"),
                    market_cap=data.get("marketCap"),
                    outstanding_shares=data.get("sharesOutstanding"),
                    industry=data.get("industry"),
                    data_source=self.source,
                )
                session.add(fundamental)

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"儲存 {symbol} 的公司基本資料到資料庫時發生錯誤: {e}")
        finally:
            session.close()

    def _save_financial_ratios_to_db(self, symbol: str, data: pd.DataFrame) -> None:
        """
        將財務比率資料儲存到資料庫

        Args:
            symbol: 股票代碼
            data: 財務比率資料
        """
        session = self.Session()
        try:
            for _, row in data.iterrows():
                # 檢查是否已存在相同的記錄
                existing = session.query(Fundamental).filter(
                    Fundamental.symbol == row["symbol"],
                    Fundamental.date == row["date"],
                ).first()

                if existing:
                    # 更新現有記錄
                    existing.pe_ratio = row.get("pe_ratio")
                    existing.pb_ratio = row.get("pb_ratio")
                    existing.ps_ratio = row.get("ps_ratio")
                    existing.dividend_yield = row.get("dividend_yield")
                    existing.roe = row.get("roe")
                    existing.roa = row.get("roa")
                    existing.market_cap = row.get("market_cap")
                    existing.outstanding_shares = row.get("outstanding_shares")
                    existing.industry = row.get("industry")
                    existing.updated_at = datetime.now()
                else:
                    # 創建新記錄
                    fundamental = Fundamental(
                        symbol=row["symbol"],
                        date=row["date"],
                        pe_ratio=row.get("pe_ratio"),
                        pb_ratio=row.get("pb_ratio"),
                        ps_ratio=row.get("ps_ratio"),
                        dividend_yield=row.get("dividend_yield"),
                        roe=row.get("roe"),
                        roa=row.get("roa"),
                        market_cap=row.get("market_cap"),
                        outstanding_shares=row.get("outstanding_shares"),
                        industry=row.get("industry"),
                        data_source=self.source,
                    )
                    session.add(fundamental)

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"儲存 {symbol} 的財務比率資料到資料庫時發生錯誤: {e}")
        finally:
            session.close()

    def collect(
        self,
        symbols: List[str],
        data_type: str = "company_info",
        **kwargs
    ) -> Union[Dict[str, Dict[str, Any]], Dict[str, pd.DataFrame]]:
        """
        收集資料的實現方法

        Args:
            symbols: 股票代碼列表
            data_type: 資料類型，可選 'company_info' 或 'financial_ratios'
            **kwargs: 其他參數，將傳遞給對應的收集方法

        Returns:
            Union[Dict[str, Dict[str, Any]], Dict[str, pd.DataFrame]]: 收集的資料
        """
        if data_type == "company_info":
            return self.collect_company_info(symbols, **kwargs)
        elif data_type == "financial_ratios":
            return self.collect_financial_ratios(symbols, **kwargs)
        else:
            raise ValueError(f"不支援的資料類型: {data_type}")
"""
