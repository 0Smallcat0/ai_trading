#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
真實數據爬取器 - 基於官方交易所渠道
=====================================

使用TWSE官方API和櫃買中心獲取準確的股票數據，
替代之前不準確的模擬數據。

數據來源優先級：
1. TWSE官方API (最高準確性)
2. 櫃買中心 (上櫃股票)
3. Yahoo Finance (備援)

Author: AI Trading System
Date: 2025-01-28
Version: 1.0
"""

import requests
import pandas as pd
import yfinance as yf
from sqlalchemy import create_engine, text
from datetime import datetime, date, timedelta
import time
import logging
from typing import Dict, List, Optional, Tuple
import json

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealDataCrawler:
    """真實數據爬取器 - 基於官方交易所渠道"""
    
    def __init__(self, db_path: str = 'sqlite:///data/real_stock_database.db'):
        """
        初始化真實數據爬取器
        
        Args:
            db_path: 資料庫連接路徑
        """
        self.db_path = db_path
        self.engine = create_engine(db_path)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 統計信息
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'twse_requests': 0,
            'tpex_requests': 0,
            'yahoo_requests': 0,
            'total_records': 0
        }

        # 智能爬取統計
        self.scan_stats = {
            'total_symbols': 0,
            'existing_symbols': 0,
            'missing_symbols': 0,
            'partial_symbols': 0,
            'skipped_records': 0,
            'new_records_needed': 0
        }
        
        # 創建資料庫表
        self._create_tables()
        
        logger.info("RealDataCrawler 初始化完成")

    def scan_existing_data(self, symbols: List[str], start_date: date, end_date: date) -> Dict:
        """
        掃描數據庫中已存在的數據，識別需要爬取的缺失數據

        Args:
            symbols: 股票代碼列表
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            掃描結果統計
        """
        scan_result = {
            'existing_symbols': [],
            'missing_symbols': [],
            'partial_symbols': [],
            'complete_symbols': [],
            'total_existing_records': 0,
            'total_missing_records': 0,
            'scan_summary': {}
        }

        logger.info(f"開始掃描數據庫，目標期間: {start_date} 到 {end_date}")

        # 計算期間內的交易日數量（簡化估算）
        total_days = (end_date - start_date).days + 1
        expected_records_per_symbol = int(total_days * 0.7)  # 假設70%為交易日

        with self.engine.connect() as conn:
            for symbol in symbols:
                try:
                    # 查詢該股票在指定期間的數據
                    query = text("""
                        SELECT COUNT(*) as count, MIN(date) as min_date, MAX(date) as max_date
                        FROM real_stock_data
                        WHERE symbol = :symbol
                        AND date >= :start_date
                        AND date <= :end_date
                    """)

                    result = conn.execute(query, {
                        'symbol': symbol,
                        'start_date': start_date.strftime('%Y-%m-%d'),
                        'end_date': end_date.strftime('%Y-%m-%d')
                    }).fetchone()

                    record_count = result[0] if result else 0

                    if record_count == 0:
                        # 完全沒有數據
                        scan_result['missing_symbols'].append(symbol)
                        scan_result['total_missing_records'] += expected_records_per_symbol
                    elif record_count < expected_records_per_symbol * 0.8:  # 少於80%認為是部分數據
                        # 部分數據
                        scan_result['partial_symbols'].append(symbol)
                        missing_records = expected_records_per_symbol - record_count
                        scan_result['total_missing_records'] += missing_records
                        scan_result['total_existing_records'] += record_count
                    else:
                        # 數據完整
                        scan_result['complete_symbols'].append(symbol)
                        scan_result['total_existing_records'] += record_count

                    # 記錄詳細信息
                    scan_result['scan_summary'][symbol] = {
                        'existing_records': record_count,
                        'expected_records': expected_records_per_symbol,
                        'completeness': record_count / expected_records_per_symbol if expected_records_per_symbol > 0 else 0,
                        'min_date': result[1] if result and result[1] else None,
                        'max_date': result[2] if result and result[2] else None
                    }

                except Exception as e:
                    logger.error(f"掃描 {symbol} 數據時發生錯誤: {e}")
                    scan_result['missing_symbols'].append(symbol)

        # 更新統計
        self.scan_stats.update({
            'total_symbols': len(symbols),
            'existing_symbols': len(scan_result['complete_symbols']),
            'missing_symbols': len(scan_result['missing_symbols']),
            'partial_symbols': len(scan_result['partial_symbols']),
            'skipped_records': scan_result['total_existing_records'],
            'new_records_needed': scan_result['total_missing_records']
        })

        logger.info(f"數據庫掃描完成: 完整 {len(scan_result['complete_symbols'])} 檔, "
                   f"部分 {len(scan_result['partial_symbols'])} 檔, "
                   f"缺失 {len(scan_result['missing_symbols'])} 檔")

        return scan_result

    def crawl_missing_data_only(self, symbols: List[str], start_date: date, end_date: date) -> Dict:
        """
        智能爬取：只爬取數據庫中缺失的數據

        Args:
            symbols: 股票代碼列表
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            爬取結果統計
        """
        # 先掃描現有數據
        scan_result = self.scan_existing_data(symbols, start_date, end_date)

        # 確定需要爬取的股票
        symbols_to_crawl = scan_result['missing_symbols'] + scan_result['partial_symbols']

        if not symbols_to_crawl:
            logger.info("所有股票數據已存在，無需爬取")
            return {
                'success': True,
                'skipped_symbols': len(scan_result['complete_symbols']),
                'crawled_symbols': 0,
                'total_new_records': 0,
                'failed_symbols': [],
                'scan_result': scan_result
            }

        logger.info(f"發現 {len(scan_result['complete_symbols'])} 檔股票已有完整數據，"
                   f"將爬取 {len(symbols_to_crawl)} 檔新股票")

        # 爬取缺失的數據
        crawl_result = {
            'success': True,
            'skipped_symbols': len(scan_result['complete_symbols']),
            'crawled_symbols': 0,
            'total_new_records': 0,
            'failed_symbols': [],
            'scan_result': scan_result
        }

        for symbol in symbols_to_crawl:
            try:
                logger.info(f"爬取缺失數據: {symbol}")

                # 對於部分數據的股票，可以進一步優化只爬取缺失的日期範圍
                if symbol in scan_result['partial_symbols']:
                    # 這裡可以實現更精細的日期範圍爬取
                    # 暫時使用完整範圍爬取，依賴數據庫的UNIQUE約束避免重複
                    pass

                # 爬取數據
                df = self.crawl_stock_data_range(symbol, start_date, end_date)

                if not df.empty:
                    # 保存到數據庫（會自動跳過重複記錄）
                    self.save_to_database(df)
                    crawl_result['crawled_symbols'] += 1
                    crawl_result['total_new_records'] += len(df)
                    logger.info(f"✅ {symbol}: 爬取 {len(df)} 筆記錄")
                else:
                    crawl_result['failed_symbols'].append(symbol)
                    logger.warning(f"⚠️ {symbol}: 爬取失敗或無數據")

            except Exception as e:
                crawl_result['failed_symbols'].append(symbol)
                logger.error(f"❌ {symbol}: 爬取錯誤 - {e}")

        logger.info(f"智能爬取完成: 跳過 {crawl_result['skipped_symbols']} 檔, "
                   f"爬取 {crawl_result['crawled_symbols']} 檔, "
                   f"新增 {crawl_result['total_new_records']} 筆記錄")

        return crawl_result

    def _create_tables(self):
        """創建資料庫表"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS real_stock_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date DATE NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume INTEGER NOT NULL,
            source TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date)
        )
        """
        
        with self.engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
    
    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        驗證股價數據準確性
        
        Args:
            df: 原始數據DataFrame
            
        Returns:
            驗證後的有效數據
        """
        if df.empty:
            return df
        
        # 檢查價格 > 0 和 OHLC 邏輯
        valid_mask = (
            (df['open'] > 0) & 
            (df['high'] >= df['open']) & 
            (df['high'] >= df['close']) & 
            (df['low'] <= df['open']) & 
            (df['low'] <= df['close']) & 
            (df['volume'] >= 0) &
            (df['high'] >= df['low'])  # 最高價 >= 最低價
        )
        
        valid_df = df[valid_mask].copy()
        
        if len(valid_df) < len(df):
            logger.warning(f"數據驗證：移除了 {len(df) - len(valid_df)} 筆無效記錄")
        
        return valid_df
    
    def crawl_twse_data(self, symbol: str, year: int, month: int) -> pd.DataFrame:
        """
        從TWSE爬取單月股價數據
        
        Args:
            symbol: 股票代碼 (如 '2330.TW')
            year: 年份
            month: 月份
            
        Returns:
            股價數據DataFrame
        """
        stock_code = symbol.split('.')[0]  # 移除.TW後綴
        url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&date={year}{month:02d}01&stockNo={stock_code}&_={int(time.time())}"
        
        try:
            logger.info(f"正在從TWSE爬取 {symbol} {year}-{month:02d} 數據...")
            
            self.stats['total_requests'] += 1
            self.stats['twse_requests'] += 1
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' in data and data['data']:
                columns = data['fields']
                df = pd.DataFrame(data['data'], columns=columns)
                
                # 轉換民國日期為西元日期
                df['date'] = pd.to_datetime(df['日期'].apply(
                    lambda x: f"{int(x.split('/')[0]) + 1911}-{x.split('/')[1]}-{x.split('/')[2]}"
                ))
                
                # 選取OHLCV欄位
                df = df[['date', '開盤價', '最高價', '最低價', '收盤價', '成交股數']].copy()
                df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                
                # 轉換數據類型，處理逗號分隔的數字和特殊值
                for col in ['open', 'high', 'low', 'close']:
                    # 處理 "--" 和其他無效值
                    df[col] = df[col].str.replace(',', '').replace('--', '0').replace('', '0')
                    # 轉換為數值，無效值設為NaN
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    # 將NaN和0值的行移除
                    df = df[df[col].notna() & (df[col] > 0)]

                # 處理成交量
                df['volume'] = df['volume'].str.replace(',', '').replace('--', '0').replace('', '0')
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0).astype(int)
                df['symbol'] = symbol
                df['source'] = 'TWSE'
                
                # 驗證數據
                df = self.validate_data(df)
                
                self.stats['successful_requests'] += 1
                self.stats['total_records'] += len(df)
                
                logger.info(f"✅ TWSE成功爬取 {symbol} 數據: {len(df)} 筆記錄")
                return df
            else:
                raise ValueError("TWSE API返回空數據")
                
        except Exception as e:
            self.stats['failed_requests'] += 1
            logger.error(f"❌ TWSE爬取 {symbol} 失敗: {e}")
            return pd.DataFrame()
    
    def crawl_tpex_data(self, symbol: str, year: int, month: int) -> pd.DataFrame:
        """
        從櫃買中心爬取上櫃股票數據
        
        Args:
            symbol: 股票代碼
            year: 年份
            month: 月份
            
        Returns:
            股價數據DataFrame
        """
        stock_code = symbol.split('.')[0]
        url = f"https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43_result.php?l=zh-tw&d={year}/{month:02d}&stkno={stock_code}&_={int(time.time())}"
        
        try:
            logger.info(f"正在從TPEX爬取 {symbol} {year}-{month:02d} 數據...")
            
            self.stats['total_requests'] += 1
            self.stats['tpex_requests'] += 1
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            # 檢查響應內容是否為有效JSON
            response_text = response.text.strip()
            if not response_text or response_text.startswith('<'):
                raise ValueError("TPEX返回無效響應（可能是HTML錯誤頁面）")

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise ValueError(f"TPEX響應JSON解析失敗: {e}")
            
            if 'aaData' in data and data['aaData']:
                df_data = []
                for row in data['aaData']:
                    # TPEX數據格式處理，跳過包含 "--" 的行
                    try:
                        # 檢查關鍵價格欄位是否有效
                        if any(val in ['--', '', None] for val in [row[2], row[4], row[5], row[6]]):
                            continue

                        date_parts = row[0].split('/')
                        date_str = f"{int(date_parts[0]) + 1911}-{date_parts[1]}-{date_parts[2]}"

                        df_data.append({
                            'date': pd.to_datetime(date_str),
                            'open': float(row[4].replace(',', '')),
                            'high': float(row[5].replace(',', '')),
                            'low': float(row[6].replace(',', '')),
                            'close': float(row[2].replace(',', '')),
                            'volume': int(row[8].replace(',', '') if row[8] not in ['--', ''] else '0'),
                            'symbol': symbol,
                            'source': 'TPEX'
                        })
                    except (ValueError, IndexError) as e:
                        logger.warning(f"跳過無效的TPEX數據行: {row}, 錯誤: {e}")
                        continue
                
                df = pd.DataFrame(df_data)
                df = self.validate_data(df)
                
                self.stats['successful_requests'] += 1
                self.stats['total_records'] += len(df)
                
                logger.info(f"✅ TPEX成功爬取 {symbol} 數據: {len(df)} 筆記錄")
                return df
            else:
                raise ValueError("TPEX API返回空數據")
                
        except Exception as e:
            self.stats['failed_requests'] += 1
            logger.error(f"❌ TPEX爬取 {symbol} 失敗: {e}")
            return pd.DataFrame()
    
    def crawl_yahoo_finance_backup(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Yahoo Finance備援數據源
        
        Args:
            symbol: 股票代碼
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            
        Returns:
            股價數據DataFrame
        """
        try:
            logger.info(f"正在從Yahoo Finance爬取 {symbol} 備援數據...")
            
            self.stats['total_requests'] += 1
            self.stats['yahoo_requests'] += 1
            
            # 轉換股票代碼格式 - 保持.TW格式，不轉換為.TWO
            yahoo_symbol = symbol if symbol.endswith('.TW') else f"{symbol}.TW"
            
            df = yf.download(yahoo_symbol, start=start_date, end=end_date, progress=False)
            
            if not df.empty:
                df.reset_index(inplace=True)
                df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].copy()
                df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
                df['symbol'] = symbol
                df['source'] = 'Yahoo Finance'
                
                # 轉換數據類型
                df['volume'] = df['volume'].astype(int)
                
                df = self.validate_data(df)
                
                self.stats['successful_requests'] += 1
                self.stats['total_records'] += len(df)
                
                logger.info(f"✅ Yahoo Finance成功爬取 {symbol} 數據: {len(df)} 筆記錄")
                return df
            else:
                raise ValueError("Yahoo Finance返回空數據")
                
        except Exception as e:
            self.stats['failed_requests'] += 1
            logger.error(f"❌ Yahoo Finance爬取 {symbol} 失敗: {e}")
            return pd.DataFrame()
    
    def crawl_stock_data(self, symbol: str, year: int, month: int) -> pd.DataFrame:
        """
        爬取股票數據 - 多數據源策略
        
        Args:
            symbol: 股票代碼
            year: 年份
            month: 月份
            
        Returns:
            股價數據DataFrame
        """
        # 首先嘗試TWSE
        df = self.crawl_twse_data(symbol, year, month)
        
        if not df.empty:
            return df
        
        # 如果TWSE失敗，嘗試TPEX (適用於上櫃股票)
        logger.info(f"TWSE失敗，嘗試TPEX...")
        time.sleep(2)  # 請求間隔
        df = self.crawl_tpex_data(symbol, year, month)
        
        if not df.empty:
            return df
        
        # 最後使用Yahoo Finance備援
        logger.info(f"TPEX失敗，使用Yahoo Finance備援...")
        time.sleep(2)  # 請求間隔
        
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
        
        df = self.crawl_yahoo_finance_backup(symbol, start_date, end_date)
        
        return df

    def crawl_stock_data_range(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        爬取指定日期範圍的股票數據

        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            股價數據DataFrame
        """
        logger.info(f"開始爬取 {symbol} 日期範圍 {start_date} 至 {end_date} 的數據")

        # 生成需要爬取的月份列表
        months_to_crawl = self._generate_month_list(start_date, end_date)

        all_data = []
        total_records = 0

        for year, month in months_to_crawl:
            try:
                logger.info(f"正在爬取 {symbol} {year}-{month:02d} 數據...")

                # 爬取單月數據
                df_month = self.crawl_stock_data(symbol, year, month)

                if not df_month.empty:
                    # 過濾日期範圍
                    df_month['date'] = pd.to_datetime(df_month['date'])
                    df_filtered = df_month[
                        (df_month['date'].dt.date >= start_date) &
                        (df_month['date'].dt.date <= end_date)
                    ]

                    if not df_filtered.empty:
                        all_data.append(df_filtered)
                        total_records += len(df_filtered)
                        logger.info(f"✅ {symbol} {year}-{month:02d}: {len(df_filtered)} 筆記錄")
                    else:
                        logger.info(f"⚠️ {symbol} {year}-{month:02d}: 無符合日期範圍的記錄")
                else:
                    logger.warning(f"❌ {symbol} {year}-{month:02d}: 爬取失敗")

                # 請求間隔，避免被封鎖
                time.sleep(1)

            except Exception as e:
                logger.error(f"❌ 爬取 {symbol} {year}-{month:02d} 時發生錯誤: {e}")
                continue

        # 合併所有數據
        if all_data:
            result_df = pd.concat(all_data, ignore_index=True)
            result_df = result_df.sort_values('date').reset_index(drop=True)

            logger.info(f"✅ {symbol} 日期範圍爬取完成: 總共 {total_records} 筆記錄")
            return result_df
        else:
            logger.warning(f"⚠️ {symbol} 在指定日期範圍內無可用數據")
            return pd.DataFrame()

    def _generate_month_list(self, start_date: date, end_date: date) -> List[Tuple[int, int]]:
        """
        生成需要爬取的月份列表

        Args:
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            (年份, 月份) 的列表
        """
        months = []
        current_date = start_date.replace(day=1)  # 從月初開始

        while current_date <= end_date:
            months.append((current_date.year, current_date.month))

            # 移動到下個月
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        return months

    def save_to_database(self, df: pd.DataFrame):
        """
        存入資料庫 - 使用UPSERT邏輯
        
        Args:
            df: 要存儲的數據DataFrame
        """
        if df.empty:
            logger.warning("沒有數據可存儲")
            return
        
        try:
            # 準備數據
            df_to_save = df[['symbol', 'date', 'open', 'high', 'low', 'close', 'volume', 'source']].copy()
            
            records_inserted = 0
            records_updated = 0
            
            with self.engine.connect() as conn:
                for _, row in df_to_save.iterrows():
                    # 檢查記錄是否已存在
                    check_sql = text("""
                        SELECT COUNT(*) as count FROM real_stock_data 
                        WHERE symbol = :symbol AND date = :date
                    """)
                    
                    result = conn.execute(check_sql, {
                        'symbol': row['symbol'],
                        'date': row['date'].strftime('%Y-%m-%d')
                    }).fetchone()
                    
                    if result[0] == 0:
                        # 插入新記錄
                        insert_sql = text("""
                            INSERT INTO real_stock_data (symbol, date, open, high, low, close, volume, source)
                            VALUES (:symbol, :date, :open, :high, :low, :close, :volume, :source)
                        """)
                        
                        row_dict = row.to_dict()
                        row_dict['date'] = row['date'].strftime('%Y-%m-%d')
                        conn.execute(insert_sql, row_dict)
                        records_inserted += 1
                    else:
                        # 更新現有記錄
                        update_sql = text("""
                            UPDATE real_stock_data
                            SET open = :open, high = :high, low = :low, close = :close,
                                volume = :volume, source = :source
                            WHERE symbol = :symbol AND date = :date
                        """)

                        row_dict = row.to_dict()
                        row_dict['date'] = row['date'].strftime('%Y-%m-%d')
                        conn.execute(update_sql, row_dict)
                        records_updated += 1
                
                conn.commit()
            
            logger.info(f"✅ 數據存儲完成: 新增 {records_inserted} 筆, 更新 {records_updated} 筆")
            
        except Exception as e:
            logger.error(f"❌ 數據存儲失敗: {e}")
    
    def get_stats(self) -> Dict:
        """獲取統計信息"""
        return self.stats.copy()
    
    def print_stats(self):
        """打印統計信息"""
        print("\n📊 爬取統計信息:")
        print("=" * 50)
        print(f"總請求數: {self.stats['total_requests']}")
        print(f"成功請求數: {self.stats['successful_requests']}")
        print(f"失敗請求數: {self.stats['failed_requests']}")
        print(f"TWSE請求數: {self.stats['twse_requests']}")
        print(f"TPEX請求數: {self.stats['tpex_requests']}")
        print(f"Yahoo請求數: {self.stats['yahoo_requests']}")
        print(f"總記錄數: {self.stats['total_records']}")
        
        if self.stats['total_requests'] > 0:
            success_rate = (self.stats['successful_requests'] / self.stats['total_requests']) * 100
            print(f"成功率: {success_rate:.1f}%")

if __name__ == "__main__":
    # 測試範例
    crawler = RealDataCrawler()
    
    # 測試爬取2330.TW (台積電) 2025年7月數據
    symbol = '2330.TW'
    year = 2025
    month = 7
    
    df = crawler.crawl_stock_data(symbol, year, month)
    
    if not df.empty:
        print(f"\n✅ 成功爬取 {symbol} {year}-{month} 數據:")
        print(f"記錄數: {len(df)}")
        print(f"數據來源: {df['source'].iloc[0]}")
        print(f"價格範圍: {df['low'].min():.2f} - {df['high'].max():.2f}")
        print(f"平均收盤價: {df['close'].mean():.2f}")
        
        # 存入資料庫
        crawler.save_to_database(df)
        
        # 顯示前5筆數據
        print("\n📋 前5筆數據:")
        print(df[['date', 'open', 'high', 'low', 'close', 'volume']].head().to_string(index=False))
    else:
        print(f"❌ 無法獲取 {symbol} 數據")
    
    # 打印統計信息
    crawler.print_stats()
