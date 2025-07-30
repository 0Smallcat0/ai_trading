# -*- coding: utf-8 -*-
"""
核心數據下載器

此模組提供核心的股票數據下載功能，整合多個數據源並提供統一接口。

主要功能：
- Yahoo Finance 數據下載
- TWSE 台股數據爬取
- 數據格式標準化
- 錯誤處理和重試機制
- 數據品質檢查

Author: AI Trading System
Version: 1.0.0
"""

import logging
import pandas as pd
import yfinance as yf
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
import json
from pathlib import Path
import sqlite3
from sqlalchemy import create_engine

# 設定日誌
logger = logging.getLogger(__name__)


class CoreDataDownloader:
    """核心數據下載器
    
    提供統一的股票數據下載接口，支援多個數據源。
    """
    
    def __init__(self, db_path: str = "data/trading_system.db"):
        """初始化下載器
        
        Args:
            db_path: 數據庫路徑
        """
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 確保數據目錄存在
        Path("data").mkdir(exist_ok=True)
        
        # 初始化數據庫連接
        self.engine = create_engine(f"sqlite:///{db_path}")
        
        logger.info("核心數據下載器初始化完成")
    
    def download_yahoo_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """從 Yahoo Finance 下載股票數據
        
        Args:
            symbol: 股票代碼 (例如: "2330.TW")
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            
        Returns:
            pd.DataFrame: 股票數據
        """
        try:
            logger.info(f"從 Yahoo Finance 下載 {symbol} 數據 ({start_date} 到 {end_date})")
            
            # 下載數據
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date)
            
            if df.empty:
                logger.warning(f"Yahoo Finance 未返回 {symbol} 的數據")
                return pd.DataFrame()
            
            # 標準化數據格式
            df = df.reset_index()
            df = df.rename(columns={
                'Date': 'date',
                'Open': 'open',
                'High': 'high', 
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # 添加元數據
            df['symbol'] = symbol
            df['source'] = 'Yahoo Finance'
            df['download_time'] = datetime.now()
            df['market_type'] = 'TWSE' if symbol.endswith('.TW') else 'OTHER'
            df['data_source'] = 'Yahoo Finance'  # 兼容現有表結構
            df['is_adjusted'] = False

            # 數據類型轉換
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['volume'] = df['volume'].astype(int)

            # 選擇需要的列（包含現有表結構需要的列）
            df = df[['date', 'symbol', 'market_type', 'open', 'high', 'low', 'close', 'volume',
                    'data_source', 'is_adjusted', 'source', 'download_time']]
            
            logger.info(f"✅ 成功下載 {symbol} 數據: {len(df)} 筆記錄")
            return df
            
        except Exception as e:
            logger.error(f"❌ Yahoo Finance 下載 {symbol} 失敗: {e}")
            return pd.DataFrame()
    
    def download_twse_data(self, symbol: str, year: int, month: int) -> pd.DataFrame:
        """從 TWSE 下載台股數據
        
        Args:
            symbol: 股票代碼 (例如: "2330")
            year: 年份
            month: 月份
            
        Returns:
            pd.DataFrame: 股票數據
        """
        try:
            # 移除 .TW 後綴
            stock_code = symbol.replace('.TW', '')
            
            logger.info(f"從 TWSE 下載 {stock_code} 數據 ({year}-{month:02d})")
            
            # 構建 URL
            url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY"
            params = {
                'response': 'json',
                'date': f"{year}{month:02d}01",
                'stockNo': stock_code,
                '_': int(time.time())
            }
            
            # 發送請求
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # 檢查數據
            if data.get('stat') != 'OK' or not data.get('data'):
                logger.warning(f"TWSE 未返回 {stock_code} 的有效數據")
                return pd.DataFrame()
            
            # 解析數據
            records = []
            for row in data['data']:
                try:
                    date_str = row[0].replace('/', '-')
                    # 轉換民國年為西元年
                    date_parts = date_str.split('-')
                    if len(date_parts) == 3:
                        year_tw = int(date_parts[0]) + 1911
                        date_str = f"{year_tw}-{date_parts[1]}-{date_parts[2]}"
                    
                    record = {
                        'date': pd.to_datetime(date_str).date(),
                        'symbol': f"{stock_code}.TW",
                        'market_type': 'TWSE',
                        'open': float(row[3].replace(',', '')),
                        'high': float(row[4].replace(',', '')),
                        'low': float(row[5].replace(',', '')),
                        'close': float(row[6].replace(',', '')),
                        'volume': int(row[1].replace(',', '')),
                        'data_source': 'TWSE',
                        'is_adjusted': False,
                        'source': 'TWSE',
                        'download_time': datetime.now()
                    }
                    records.append(record)
                except (ValueError, IndexError) as e:
                    logger.warning(f"解析 TWSE 數據行失敗: {row}, 錯誤: {e}")
                    continue
            
            if not records:
                logger.warning(f"TWSE 數據解析後為空: {stock_code}")
                return pd.DataFrame()
            
            df = pd.DataFrame(records)
            logger.info(f"✅ 成功下載 {stock_code} TWSE 數據: {len(df)} 筆記錄")
            return df
            
        except Exception as e:
            logger.error(f"❌ TWSE 下載 {symbol} 失敗: {e}")
            return pd.DataFrame()
    
    def download_stock_data(self, symbol: str, start_date: str, end_date: str, 
                          sources: List[str] = None) -> pd.DataFrame:
        """下載股票數據（多數據源策略）
        
        Args:
            symbol: 股票代碼
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            sources: 數據源列表，默認為 ['yahoo', 'twse']
            
        Returns:
            pd.DataFrame: 合併的股票數據
        """
        if sources is None:
            sources = ['yahoo', 'twse']
        
        all_data = []
        
        # 嘗試 Yahoo Finance
        if 'yahoo' in sources:
            yahoo_data = self.download_yahoo_data(symbol, start_date, end_date)
            if not yahoo_data.empty:
                all_data.append(yahoo_data)
        
        # 嘗試 TWSE（按月下載）
        if 'twse' in sources and symbol.endswith('.TW'):
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            current_dt = start_dt
            while current_dt <= end_dt:
                twse_data = self.download_twse_data(symbol, current_dt.year, current_dt.month)
                if not twse_data.empty:
                    # 過濾日期範圍
                    twse_data = twse_data[
                        (pd.to_datetime(twse_data['date']) >= start_dt) &
                        (pd.to_datetime(twse_data['date']) <= end_dt)
                    ]
                    if not twse_data.empty:
                        all_data.append(twse_data)
                
                # 移到下個月
                if current_dt.month == 12:
                    current_dt = current_dt.replace(year=current_dt.year + 1, month=1)
                else:
                    current_dt = current_dt.replace(month=current_dt.month + 1)
                
                time.sleep(1)  # 避免請求過於頻繁
        
        # 合併數據
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            # 去重（優先保留 Yahoo Finance 數據）
            combined_df = combined_df.drop_duplicates(subset=['date', 'symbol'], keep='first')
            combined_df = combined_df.sort_values('date').reset_index(drop=True)
            
            logger.info(f"✅ 成功合併 {symbol} 數據: {len(combined_df)} 筆記錄")
            return combined_df
        else:
            logger.warning(f"⚠️ 無法獲取 {symbol} 的任何數據")
            return pd.DataFrame()
    
    def save_to_database(self, df: pd.DataFrame, table_name: str = "market_daily") -> bool:
        """保存數據到數據庫

        Args:
            df: 要保存的數據
            table_name: 表名

        Returns:
            bool: 是否保存成功
        """
        try:
            if df.empty:
                logger.warning("數據為空，跳過保存")
                return False

            # 檢查重複記錄並過濾
            from sqlalchemy import text
            with self.engine.connect() as conn:
                # 獲取現有記錄
                unique_symbols = df['symbol'].unique()
                placeholders = ','.join([':symbol' + str(i) for i in range(len(unique_symbols))])
                existing_query = text(f"""
                    SELECT symbol, date FROM {table_name}
                    WHERE symbol IN ({placeholders})
                """)

                # 創建參數字典
                params = {f'symbol{i}': symbol for i, symbol in enumerate(unique_symbols)}

                existing_df = pd.read_sql_query(existing_query, conn, params=params)

                if not existing_df.empty:
                    # 創建現有記錄的標識符集合
                    existing_keys = set(
                        zip(existing_df['symbol'], pd.to_datetime(existing_df['date']).dt.date)
                    )

                    # 過濾掉重複記錄
                    df_filtered = df[
                        ~df.apply(lambda row: (row['symbol'], row['date']) in existing_keys, axis=1)
                    ]

                    if len(df_filtered) < len(df):
                        logger.info(f"過濾掉 {len(df) - len(df_filtered)} 筆重複記錄")

                    df = df_filtered

            if df.empty:
                logger.info("所有記錄都已存在，跳過保存")
                return True

            # 保存到數據庫
            df.to_sql(table_name, self.engine, if_exists='append', index=False)
            logger.info(f"✅ 成功保存 {len(df)} 筆新記錄到 {table_name} 表")
            return True

        except Exception as e:
            logger.error(f"❌ 保存數據到數據庫失敗: {e}")
            return False
    
    def get_stock_info(self, symbol: str) -> Dict[str, Any]:
        """獲取股票基本資訊
        
        Args:
            symbol: 股票代碼
            
        Returns:
            Dict[str, Any]: 股票基本資訊
        """
        try:
            logger.info(f"獲取 {symbol} 基本資訊")
            
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info:
                logger.warning(f"無法獲取 {symbol} 的基本資訊")
                return {}
            
            # 提取關鍵資訊
            basic_info = {
                'symbol': symbol,
                'name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0),
                'currency': info.get('currency', ''),
                'exchange': info.get('exchange', ''),
                'updated_time': datetime.now()
            }
            
            logger.info(f"✅ 成功獲取 {symbol} 基本資訊")
            return basic_info
            
        except Exception as e:
            logger.error(f"❌ 獲取 {symbol} 基本資訊失敗: {e}")
            return {}
    
    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """驗證和清理數據
        
        Args:
            df: 原始數據
            
        Returns:
            pd.DataFrame: 清理後的數據
        """
        if df.empty:
            return df
        
        original_count = len(df)
        
        # 移除空值
        df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
        
        # 移除異常值（價格為0或負數）
        df = df[(df['open'] > 0) & (df['high'] > 0) & (df['low'] > 0) & (df['close'] > 0)]
        
        # 移除成交量為負數的記錄
        df = df[df['volume'] >= 0]
        
        # 檢查價格邏輯（最高價 >= 最低價）
        df = df[df['high'] >= df['low']]
        
        cleaned_count = len(df)
        if cleaned_count < original_count:
            logger.info(f"數據清理完成: {original_count} -> {cleaned_count} 筆記錄")
        
        return df
