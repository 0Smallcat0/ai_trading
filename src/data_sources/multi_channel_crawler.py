#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多渠道股票數據爬蟲系統
====================

整合TWSE、TPEX、Yahoo Finance等多個數據源，提供高可靠性的股票數據獲取服務。
支援自動備援切換、並行處理、數據品質驗證和自學優化功能。

功能特點：
- 多渠道數據源整合 (TWSE + TPEX + Yahoo Finance)
- 自動備援切換機制
- 並行處理提升效率
- 智能數據品質驗證
- 自學能力和準確性報告
- UPSERT資料庫操作
- 支援PostgreSQL和SQLite

Author: AI Trading System
Date: 2025-01-28
Version: 1.0
"""

import requests
import pandas as pd
import yfinance as yf
import time
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
import numpy as np

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_with_retry(max_retries: int = 3, delay: float = 2.0):
    """錯誤處理裝飾器，支援重試機制"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"函數 {func.__name__} 執行失敗，已重試 {max_retries} 次: {e}")
                        raise e
                    else:
                        logger.warning(f"函數 {func.__name__} 第 {attempt + 1} 次嘗試失敗: {e}，{delay}秒後重試")
                        time.sleep(delay)
            return None
        return wrapper
    return decorator

class DataValidator:
    """數據驗證器"""
    
    @staticmethod
    def validate_ohlcv_data(df: pd.DataFrame) -> pd.DataFrame:
        """驗證OHLCV數據的邏輯正確性"""
        if df.empty:
            return df
        
        # 基本數值檢查
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # OHLC邏輯檢查
        valid_mask = (
            (df['open'] > 0) & 
            (df['high'] >= df['open']) & 
            (df['high'] >= df['close']) & 
            (df['low'] <= df['open']) & 
            (df['low'] <= df['close']) & 
            (df['high'] >= df['low']) &
            (df['volume'] >= 0)
        )
        
        invalid_count = (~valid_mask).sum()
        if invalid_count > 0:
            logger.warning(f"發現 {invalid_count} 筆無效數據，已自動過濾")
        
        return df[valid_mask].copy()
    
    @staticmethod
    def check_data_completeness(df: pd.DataFrame, expected_days: int = 20) -> Dict[str, Any]:
        """檢查數據完整性"""
        actual_days = len(df)
        completeness_ratio = actual_days / expected_days if expected_days > 0 else 0
        
        return {
            'actual_records': actual_days,
            'expected_records': expected_days,
            'completeness_ratio': completeness_ratio,
            'is_complete': completeness_ratio >= 0.8,  # 80%以上視為完整
            'missing_days': max(0, expected_days - actual_days)
        }

class TPEXCrawler:
    """櫃買中心(TPEX)數據爬蟲 - 使用OpenAPI"""

    def __init__(self):
        self.openapi_url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # 緩存當日數據以提升效率
        self._daily_cache = {}
        self._cache_date = None

    @handle_with_retry(max_retries=3, delay=2.0)
    def crawl_monthly_data(self, symbol: str, year: int, month: int) -> pd.DataFrame:
        """爬取TPEX股票數據 - 使用OpenAPI獲取當日數據"""
        try:
            # 移除.TW後綴
            stock_code = symbol.replace('.TW', '')

            logger.info(f"正在從TPEX OpenAPI爬取 {symbol} 數據...")

            # 獲取當日所有上櫃股票數據
            all_data = self._get_daily_data()

            if not all_data:
                logger.warning(f"TPEX OpenAPI未返回數據")
                return pd.DataFrame()

            # 尋找目標股票
            target_stock = None
            for stock in all_data:
                if isinstance(stock, dict) and stock.get('SecuritiesCompanyCode') == stock_code:
                    target_stock = stock
                    break

            if not target_stock:
                logger.warning(f"TPEX未找到股票 {symbol} ({stock_code}) 的數據")
                return pd.DataFrame()

            # 轉換為DataFrame格式
            date_str = target_stock.get('Date', '')
            # 修復日期解析問題
            try:
                if date_str:
                    # TPEX日期格式: 1140728 (民國年月日)
                    if len(date_str) == 7:  # 1140728
                        year = int(date_str[:3]) + 1911  # 114 + 1911 = 2025
                        month = int(date_str[3:5])       # 07
                        day = int(date_str[5:7])         # 28
                        parsed_date = pd.to_datetime(f"{year}-{month:02d}-{day:02d}")
                    else:
                        parsed_date = pd.to_datetime(date_str)
                else:
                    parsed_date = pd.to_datetime('today')
            except Exception as e:
                logger.warning(f"日期解析失敗 {date_str}: {e}，使用今日日期")
                parsed_date = pd.to_datetime('today')

            df_data = {
                'date': [parsed_date],
                'open': [self._safe_float(target_stock.get('Open', 0))],
                'high': [self._safe_float(target_stock.get('High', 0))],
                'low': [self._safe_float(target_stock.get('Low', 0))],
                'close': [self._safe_float(target_stock.get('Close', 0))],
                'volume': [self._safe_int(target_stock.get('TradingShares', 0))],
                'symbol': [symbol],
                'source': ['TPEX']
                # 移除company_name以保持與標準格式一致
            }

            df = pd.DataFrame(df_data)

            # 數據驗證
            df = DataValidator.validate_ohlcv_data(df)

            if not df.empty:
                logger.info(f"✅ TPEX成功爬取 {symbol} 數據: {len(df)} 筆記錄")
                logger.info(f"   公司名稱: {target_stock.get('CompanyName', 'Unknown')}")
                logger.info(f"   收盤價: {target_stock.get('Close', 'Unknown')}")
            else:
                logger.warning(f"⚠️ TPEX數據驗證失敗: {symbol}")

            return df

        except Exception as e:
            logger.error(f"❌ TPEX爬取 {symbol} 失敗: {e}")
            return pd.DataFrame()

    def _get_daily_data(self) -> List[Dict]:
        """獲取當日所有上櫃股票數據，使用緩存提升效率"""
        try:
            from datetime import date
            today = date.today()

            # 檢查緩存
            if self._cache_date == today and self._daily_cache:
                logger.debug("使用TPEX數據緩存")
                return self._daily_cache

            # 獲取新數據
            response = self.session.get(self.openapi_url, timeout=30)
            response.raise_for_status()

            data = response.json()

            if isinstance(data, list):
                # 更新緩存
                self._daily_cache = data
                self._cache_date = today
                logger.info(f"✅ TPEX OpenAPI獲取 {len(data)} 筆股票數據")
                return data
            else:
                logger.warning(f"TPEX OpenAPI數據格式異常: {type(data)}")
                return []

        except Exception as e:
            logger.error(f"❌ TPEX OpenAPI請求失敗: {e}")
            return []

    def _safe_float(self, value) -> float:
        """安全轉換為浮點數"""
        try:
            if isinstance(value, str):
                # 移除逗號和其他非數字字符
                cleaned = value.replace(',', '').replace(' ', '')
                return float(cleaned) if cleaned else 0.0
            return float(value) if value is not None else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _safe_int(self, value) -> int:
        """安全轉換為整數"""
        try:
            if isinstance(value, str):
                # 移除逗號和其他非數字字符
                cleaned = value.replace(',', '').replace(' ', '')
                return int(float(cleaned)) if cleaned else 0
            return int(float(value)) if value is not None else 0
        except (ValueError, TypeError):
            return 0

    def get_available_symbols(self) -> List[str]:
        """獲取所有可用的上櫃股票代碼"""
        try:
            all_data = self._get_daily_data()
            symbols = []

            for stock in all_data:
                if isinstance(stock, dict):
                    code = stock.get('SecuritiesCompanyCode', '')
                    if code and code.isdigit():  # 只取數字代碼
                        symbols.append(f"{code}.TW")

            return sorted(symbols)

        except Exception as e:
            logger.error(f"❌ 獲取TPEX股票列表失敗: {e}")
            return []

class YahooFinanceCrawler:
    """Yahoo Finance數據爬蟲"""
    
    @handle_with_retry(max_retries=3, delay=1.0)
    def crawl_historical_data(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """爬取Yahoo Finance歷史數據"""
        try:
            logger.info(f"正在從Yahoo Finance爬取 {symbol} {start_date} 至 {end_date} 數據...")
            
            # 使用yfinance獲取數據
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, auto_adjust=False)
            
            if df.empty:
                logger.warning(f"Yahoo Finance未返回 {symbol} 的數據")
                return pd.DataFrame()
            
            # 重置索引並重命名欄位
            df.reset_index(inplace=True)
            df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
            df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            
            # 添加元數據
            df['symbol'] = symbol
            df['source'] = 'Yahoo Finance'
            
            # 數據驗證
            df = DataValidator.validate_ohlcv_data(df)
            
            logger.info(f"✅ Yahoo Finance成功爬取 {symbol} 數據: {len(df)} 筆記錄")
            return df
            
        except Exception as e:
            logger.error(f"❌ Yahoo Finance爬取 {symbol} 失敗: {e}")
            return pd.DataFrame()

class AutoDataManager:
    """自動數據管理器 - 支援自學能力"""
    
    def __init__(self, db_url: str = "sqlite:///stock_data.db"):
        self.db_url = db_url
        self.engine = create_engine(db_url)
        self.tpex_crawler = TPEXCrawler()
        self.yahoo_crawler = YahooFinanceCrawler()
        
    def crawl_multi_channel_data(self, symbols: List[str], start_date: date, end_date: date, 
                                max_workers: int = 2) -> Dict[str, pd.DataFrame]:
        """多渠道並行爬取數據"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任務
            future_to_symbol = {}
            
            for symbol in symbols:
                # Yahoo Finance任務
                future_yahoo = executor.submit(
                    self.yahoo_crawler.crawl_historical_data, 
                    symbol, start_date, end_date
                )
                future_to_symbol[future_yahoo] = (symbol, 'yahoo')
                
                # TPEX任務 (按月份拆分)
                current_date = start_date
                while current_date <= end_date:
                    future_tpex = executor.submit(
                        self.tpex_crawler.crawl_monthly_data,
                        symbol, current_date.year, current_date.month
                    )
                    future_to_symbol[future_tpex] = (symbol, f'tpex_{current_date.year}_{current_date.month}')
                    
                    # 移動到下個月
                    if current_date.month == 12:
                        current_date = current_date.replace(year=current_date.year + 1, month=1)
                    else:
                        current_date = current_date.replace(month=current_date.month + 1)
            
            # 收集結果
            for future in as_completed(future_to_symbol):
                symbol, source_key = future_to_symbol[future]
                try:
                    df = future.result()
                    if not df.empty:
                        if symbol not in results:
                            results[symbol] = []
                        results[symbol].append(df)
                except Exception as e:
                    logger.error(f"任務執行失敗 {symbol} ({source_key}): {e}")
        
        # 合併同一股票的多個數據源
        final_results = {}
        for symbol, dfs in results.items():
            if dfs:
                combined_df = pd.concat(dfs, ignore_index=True)
                # 去重並排序
                combined_df = combined_df.drop_duplicates(subset=['date', 'symbol']).sort_values('date')
                final_results[symbol] = combined_df
        
        return final_results

    def generate_accuracy_report(self, symbol_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """生成數據準確性報告"""
        report = {
            'timestamp': datetime.now(),
            'symbols_processed': len(symbol_data),
            'symbol_reports': {},
            'overall_quality': 0.0
        }

        total_quality_score = 0

        for symbol, df in symbol_data.items():
            if df.empty:
                continue

            # 計算數據品質指標
            completeness = DataValidator.check_data_completeness(df)

            # 檢查數據源多樣性
            sources = df['source'].unique() if 'source' in df.columns else ['Unknown']

            # 計算價格變動合理性
            df_sorted = df.sort_values('date')
            price_changes = df_sorted['close'].pct_change().abs()
            extreme_changes = (price_changes > 0.1).sum()  # 超過10%變動的天數

            # 計算品質分數
            quality_score = (
                completeness['completeness_ratio'] * 0.4 +  # 完整性40%
                (len(sources) / 3) * 0.3 +  # 數據源多樣性30%
                max(0, 1 - extreme_changes / len(df)) * 0.3  # 價格合理性30%
            )

            symbol_report = {
                'symbol': symbol,
                'total_records': len(df),
                'date_range': {
                    'start': df['date'].min().strftime('%Y-%m-%d') if not df.empty else None,
                    'end': df['date'].max().strftime('%Y-%m-%d') if not df.empty else None
                },
                'completeness': completeness,
                'data_sources': sources.tolist(),
                'extreme_price_changes': int(extreme_changes),
                'quality_score': round(quality_score, 3),
                'recommendations': []
            }

            # 生成建議
            if completeness['completeness_ratio'] < 0.8:
                symbol_report['recommendations'].append("數據完整性不足，建議增加備援數據源")

            if len(sources) == 1:
                symbol_report['recommendations'].append("僅有單一數據源，建議啟用多渠道備援")

            if extreme_changes > len(df) * 0.1:
                symbol_report['recommendations'].append("發現異常價格變動，建議進行數據驗證")

            report['symbol_reports'][symbol] = symbol_report
            total_quality_score += quality_score

        # 計算整體品質分數
        if symbol_data:
            report['overall_quality'] = round(total_quality_score / len(symbol_data), 3)

        return report

    def save_to_database_with_upsert(self, df: pd.DataFrame, table_name: str = 'stock_data') -> bool:
        """使用UPSERT邏輯保存數據到資料庫"""
        if df.empty:
            return False

        try:
            # 檢查資料庫類型
            if 'postgresql' in self.db_url:
                return self._upsert_postgresql(df, table_name)
            else:
                return self._upsert_sqlite(df, table_name)

        except Exception as e:
            logger.error(f"數據庫保存失敗: {e}")
            return False

    def _upsert_postgresql(self, df: pd.DataFrame, table_name: str) -> bool:
        """PostgreSQL UPSERT操作"""
        try:
            # 創建表格（如果不存在）
            df.head(0).to_sql(table_name, self.engine, if_exists='append', index=False)

            # 執行UPSERT
            with self.engine.begin() as conn:
                for _, row in df.iterrows():
                    stmt = pg_insert(table_name).values(**row.to_dict())
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['symbol', 'date'],
                        set_={col: stmt.excluded[col] for col in df.columns if col not in ['symbol', 'date']}
                    )
                    conn.execute(stmt)

            logger.info(f"✅ PostgreSQL UPSERT完成: {len(df)} 筆記錄")
            return True

        except Exception as e:
            logger.error(f"PostgreSQL UPSERT失敗: {e}")
            return False

    def _upsert_sqlite(self, df: pd.DataFrame, table_name: str) -> bool:
        """SQLite UPSERT操作 - 修復版"""
        try:
            if df.empty:
                logger.warning("DataFrame為空，跳過UPSERT操作")
                return True

            # 創建帶有主鍵約束的表格
            self._create_table_with_constraints(df, table_name)

            # 使用真正的UPSERT操作
            with self.engine.begin() as conn:
                # 為每一行數據執行UPSERT
                for _, row in df.iterrows():
                    # 構建參數字典
                    row_dict = row.to_dict()

                    # 處理NaN值和特殊類型
                    for key, value in row_dict.items():
                        if pd.isna(value):
                            row_dict[key] = None
                        elif isinstance(value, pd.Timestamp):
                            # 修復時區問題：轉換為不帶時區的日期字符串
                            row_dict[key] = value.strftime('%Y-%m-%d')
                        elif hasattr(value, 'item'):  # numpy類型
                            row_dict[key] = value.item()

                    # 首先嘗試更新
                    if 'symbol' in row_dict and 'date' in row_dict:
                        # 檢查記錄是否存在
                        check_sql = f"""
                        SELECT COUNT(*) FROM {table_name}
                        WHERE symbol = :symbol AND date = :date
                        """

                        result = conn.execute(text(check_sql), {
                            'symbol': row_dict['symbol'],
                            'date': row_dict['date']
                        })

                        exists = result.fetchone()[0] > 0

                        if exists:
                            # 更新現有記錄
                            update_columns = [f"{col} = :{col}" for col in row_dict.keys()
                                            if col not in ['symbol', 'date']]
                            if update_columns:
                                update_sql = f"""
                                UPDATE {table_name}
                                SET {', '.join(update_columns)}
                                WHERE symbol = :symbol AND date = :date
                                """
                                conn.execute(text(update_sql), row_dict)
                        else:
                            # 插入新記錄
                            columns = list(row_dict.keys())
                            placeholders = ', '.join([f':{col}' for col in columns])
                            columns_str = ', '.join(columns)

                            insert_sql = f"""
                            INSERT INTO {table_name} ({columns_str})
                            VALUES ({placeholders})
                            """
                            conn.execute(text(insert_sql), row_dict)
                    else:
                        # 如果沒有symbol和date，直接插入
                        columns = list(row_dict.keys())
                        placeholders = ', '.join([f':{col}' for col in columns])
                        columns_str = ', '.join(columns)

                        insert_sql = f"""
                        INSERT INTO {table_name} ({columns_str})
                        VALUES ({placeholders})
                        """
                        conn.execute(text(insert_sql), row_dict)

            logger.info(f"✅ SQLite UPSERT完成: {len(df)} 筆記錄")
            return True

        except Exception as e:
            logger.error(f"SQLite UPSERT失敗: {e}")
            logger.error(f"DataFrame info: shape={df.shape}, columns={list(df.columns)}")
            return False

    def _create_table_with_constraints(self, df: pd.DataFrame, table_name: str):
        """創建帶有約束的表格"""
        try:
            with self.engine.begin() as conn:
                # 檢查表格是否已存在
                check_table_sql = f"""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='{table_name}'
                """

                result = conn.execute(text(check_table_sql))
                table_exists = result.fetchone() is not None

                if not table_exists:
                    # 創建表格結構
                    columns_def = []
                    for col in df.columns:
                        if col in ['symbol', 'date']:
                            columns_def.append(f"{col} TEXT NOT NULL")
                        elif col in ['open', 'high', 'low', 'close', 'volume']:
                            columns_def.append(f"{col} REAL")
                        else:
                            columns_def.append(f"{col} TEXT")

                    # 添加主鍵約束
                    if 'symbol' in df.columns and 'date' in df.columns:
                        columns_def.append("PRIMARY KEY (symbol, date)")

                    create_table_sql = f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        {', '.join(columns_def)}
                    )
                    """

                    conn.execute(text(create_table_sql))
                    logger.debug(f"創建表格 {table_name} 成功")

        except Exception as e:
            logger.warning(f"創建表格約束失敗，使用默認方式: {e}")
            # 回退到pandas默認創建方式
            df.head(0).to_sql(table_name, self.engine, if_exists='append', index=False)

    def auto_detect_and_retry(self, symbols: List[str], start_date: date, end_date: date) -> Dict[str, Any]:
        """自動偵測數據缺失並重試"""
        logger.info("🤖 啟動自學數據管理模式")

        # 第一次爬取
        data_results = self.crawl_multi_channel_data(symbols, start_date, end_date)

        # 生成初始報告
        initial_report = self.generate_accuracy_report(data_results)

        # 識別需要重試的股票
        retry_symbols = []
        for symbol, report in initial_report['symbol_reports'].items():
            if (report['completeness']['completeness_ratio'] < 0.8 or
                report['quality_score'] < 0.7):
                retry_symbols.append(symbol)

        # 執行重試
        if retry_symbols:
            logger.info(f"🔄 檢測到 {len(retry_symbols)} 個股票需要重試: {retry_symbols}")

            # 延遲後重試
            time.sleep(5)
            retry_results = self.crawl_multi_channel_data(retry_symbols, start_date, end_date)

            # 智能合併結果
            for symbol, retry_df in retry_results.items():
                if not retry_df.empty:
                    original_df = data_results.get(symbol, pd.DataFrame())

                    if original_df.empty:
                        # 如果原始數據為空，直接使用重試數據
                        data_results[symbol] = retry_df
                        logger.info(f"✅ {symbol} 重試獲得新數據: {len(retry_df)} 筆記錄")
                    else:
                        # 合併數據並去重
                        combined_df = pd.concat([original_df, retry_df], ignore_index=True)

                        # 根據日期和股票代碼去重，保留最新數據
                        if 'date' in combined_df.columns and 'symbol' in combined_df.columns:
                            combined_df = combined_df.drop_duplicates(
                                subset=['date', 'symbol'],
                                keep='last'
                            ).sort_values('date')

                        # 只有在合併後數據更好時才替換
                        if len(combined_df) > len(original_df):
                            data_results[symbol] = combined_df
                            logger.info(f"✅ {symbol} 重試改善數據: {len(original_df)} → {len(combined_df)} 筆記錄")
                        else:
                            logger.info(f"⚠️ {symbol} 重試未改善數據品質，保持原始數據")

        # 生成最終報告
        final_report = self.generate_accuracy_report(data_results)

        # 保存到資料庫
        saved_count = 0
        for symbol, df in data_results.items():
            if self.save_to_database_with_upsert(df):
                saved_count += 1

        return {
            'data_results': data_results,
            'initial_report': initial_report,
            'final_report': final_report,
            'retry_symbols': retry_symbols,
            'saved_to_db': saved_count,
            'total_symbols': len(symbols)
        }
