# -*- coding: utf-8 -*-
"""
數據查詢服務

此模組提供統一的數據查詢接口，支援多種查詢條件和數據匯出功能。

主要功能：
- 按股票代碼查詢
- 按日期範圍篩選
- 數據匯出（CSV、JSON）
- 數據品質檢查
- 查詢結果緩存

Author: AI Trading System
Version: 1.0.0
"""

import logging
import pandas as pd
import sqlite3
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Union
import json
from pathlib import Path
from sqlalchemy import create_engine, text
import io

# 設定日誌
logger = logging.getLogger(__name__)


class DataQueryService:
    """數據查詢服務
    
    提供統一的數據查詢和匯出功能。
    """
    
    def __init__(self, db_path: str = "data/trading_system.db"):
        """初始化查詢服務
        
        Args:
            db_path: 數據庫路徑
        """
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        
        # 確保數據目錄存在
        Path("data").mkdir(exist_ok=True)
        
        logger.info("數據查詢服務初始化完成")
    
    def query_stock_data(self, 
                        symbol: str = None,
                        start_date: str = None,
                        end_date: str = None,
                        limit: int = 1000) -> pd.DataFrame:
        """查詢股票數據
        
        Args:
            symbol: 股票代碼，None 表示查詢所有股票
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            limit: 最大返回記錄數
            
        Returns:
            pd.DataFrame: 查詢結果
        """
        try:
            logger.info(f"查詢股票數據: symbol={symbol}, start_date={start_date}, end_date={end_date}")
            
            # 構建查詢條件
            conditions = []
            params = {}
            
            if symbol:
                conditions.append("symbol = :symbol")
                params['symbol'] = symbol
            
            if start_date:
                conditions.append("date >= :start_date")
                params['start_date'] = start_date
            
            if end_date:
                conditions.append("date <= :end_date")
                params['end_date'] = end_date
            
            # 構建 SQL 查詢
            base_query = """
                SELECT date, symbol, open, high, low, close, volume, source, download_time
                FROM market_daily
            """
            
            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)
            
            base_query += " ORDER BY date DESC, symbol"
            
            if limit:
                base_query += f" LIMIT {limit}"
            
            # 執行查詢
            with self.engine.connect() as conn:
                df = pd.read_sql_query(text(base_query), conn, params=params)
            
            if df.empty:
                logger.info("查詢結果為空")
                return pd.DataFrame()
            
            # 數據類型轉換
            df['date'] = pd.to_datetime(df['date']).dt.date
            df['download_time'] = pd.to_datetime(df['download_time'])
            
            logger.info(f"✅ 查詢完成: {len(df)} 筆記錄")
            return df
            
        except Exception as e:
            logger.error(f"❌ 查詢股票數據失敗: {e}")
            return pd.DataFrame()
    
    def get_available_symbols(self) -> List[str]:
        """獲取可用的股票代碼列表
        
        Returns:
            List[str]: 股票代碼列表
        """
        try:
            query = "SELECT DISTINCT symbol FROM market_daily ORDER BY symbol"
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                symbols = [row[0] for row in result.fetchall()]
            
            logger.info(f"✅ 獲取到 {len(symbols)} 個股票代碼")
            return symbols
            
        except Exception as e:
            logger.error(f"❌ 獲取股票代碼列表失敗: {e}")
            return []
    
    def get_date_range(self, symbol: str = None) -> Dict[str, Any]:
        """獲取數據的日期範圍
        
        Args:
            symbol: 股票代碼，None 表示查詢所有股票
            
        Returns:
            Dict[str, Any]: 包含最早和最晚日期的字典
        """
        try:
            base_query = "SELECT MIN(date) as min_date, MAX(date) as max_date FROM market_daily"
            params = {}
            
            if symbol:
                base_query += " WHERE symbol = :symbol"
                params['symbol'] = symbol
            
            with self.engine.connect() as conn:
                result = conn.execute(text(base_query), params).fetchone()
            
            if result and result[0] and result[1]:
                date_range = {
                    'min_date': result[0],
                    'max_date': result[1],
                    'symbol': symbol or 'all'
                }
                logger.info(f"✅ 獲取日期範圍: {date_range}")
                return date_range
            else:
                logger.info("未找到數據或日期範圍為空")
                return {}
                
        except Exception as e:
            logger.error(f"❌ 獲取日期範圍失敗: {e}")
            return {}
    
    def get_data_summary(self) -> Dict[str, Any]:
        """獲取數據摘要統計
        
        Returns:
            Dict[str, Any]: 數據摘要
        """
        try:
            summary_queries = {
                'total_records': "SELECT COUNT(*) FROM market_daily",
                'unique_symbols': "SELECT COUNT(DISTINCT symbol) FROM market_daily",
                'data_sources': "SELECT source, COUNT(*) as count FROM market_daily GROUP BY source",
                'latest_update': "SELECT MAX(download_time) FROM market_daily"
            }
            
            summary = {}
            
            with self.engine.connect() as conn:
                # 總記錄數
                result = conn.execute(text(summary_queries['total_records'])).fetchone()
                summary['total_records'] = result[0] if result else 0
                
                # 唯一股票數
                result = conn.execute(text(summary_queries['unique_symbols'])).fetchone()
                summary['unique_symbols'] = result[0] if result else 0
                
                # 數據源統計
                result = conn.execute(text(summary_queries['data_sources'])).fetchall()
                summary['data_sources'] = {row[0]: row[1] for row in result}
                
                # 最新更新時間
                result = conn.execute(text(summary_queries['latest_update'])).fetchone()
                summary['latest_update'] = result[0] if result and result[0] else None
            
            logger.info(f"✅ 獲取數據摘要: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"❌ 獲取數據摘要失敗: {e}")
            return {}
    
    def export_to_csv(self, df: pd.DataFrame, filename: str = None) -> str:
        """匯出數據為 CSV 格式
        
        Args:
            df: 要匯出的數據
            filename: 檔案名稱，None 則自動生成
            
        Returns:
            str: 檔案路徑或 CSV 內容
        """
        try:
            if df.empty:
                logger.warning("數據為空，無法匯出")
                return ""
            
            if filename:
                # 保存到檔案
                filepath = Path("data") / filename
                df.to_csv(filepath, index=False, encoding='utf-8-sig')
                logger.info(f"✅ 數據已匯出到 {filepath}")
                return str(filepath)
            else:
                # 返回 CSV 內容
                csv_buffer = io.StringIO()
                df.to_csv(csv_buffer, index=False, encoding='utf-8')
                csv_content = csv_buffer.getvalue()
                logger.info(f"✅ 生成 CSV 內容: {len(df)} 筆記錄")
                return csv_content
                
        except Exception as e:
            logger.error(f"❌ 匯出 CSV 失敗: {e}")
            return ""
    
    def export_to_json(self, df: pd.DataFrame, filename: str = None) -> str:
        """匯出數據為 JSON 格式
        
        Args:
            df: 要匯出的數據
            filename: 檔案名稱，None 則返回 JSON 字串
            
        Returns:
            str: 檔案路徑或 JSON 內容
        """
        try:
            if df.empty:
                logger.warning("數據為空，無法匯出")
                return ""
            
            # 轉換日期格式以便 JSON 序列化
            df_copy = df.copy()
            for col in df_copy.columns:
                if df_copy[col].dtype == 'object':
                    # 嘗試轉換日期列
                    try:
                        if 'date' in col.lower() or 'time' in col.lower():
                            df_copy[col] = df_copy[col].astype(str)
                    except:
                        pass
            
            if filename:
                # 保存到檔案
                filepath = Path("data") / filename
                df_copy.to_json(filepath, orient='records', date_format='iso', indent=2)
                logger.info(f"✅ 數據已匯出到 {filepath}")
                return str(filepath)
            else:
                # 返回 JSON 內容
                json_content = df_copy.to_json(orient='records', date_format='iso', indent=2)
                logger.info(f"✅ 生成 JSON 內容: {len(df)} 筆記錄")
                return json_content
                
        except Exception as e:
            logger.error(f"❌ 匯出 JSON 失敗: {e}")
            return ""
    
    def search_stocks(self, keyword: str) -> List[Dict[str, Any]]:
        """搜尋股票
        
        Args:
            keyword: 搜尋關鍵字（股票代碼或名稱）
            
        Returns:
            List[Dict[str, Any]]: 搜尋結果
        """
        try:
            # 簡單的股票代碼搜尋
            symbols = self.get_available_symbols()
            
            # 過濾包含關鍵字的股票代碼
            matching_symbols = [
                symbol for symbol in symbols 
                if keyword.upper() in symbol.upper()
            ]
            
            results = []
            for symbol in matching_symbols[:20]:  # 限制結果數量
                # 獲取最新數據
                latest_data = self.query_stock_data(symbol=symbol, limit=1)
                if not latest_data.empty:
                    row = latest_data.iloc[0]
                    results.append({
                        'symbol': symbol,
                        'latest_date': str(row['date']),
                        'latest_close': float(row['close']),
                        'source': row['source']
                    })
            
            logger.info(f"✅ 搜尋 '{keyword}' 找到 {len(results)} 個結果")
            return results
            
        except Exception as e:
            logger.error(f"❌ 搜尋股票失敗: {e}")
            return []
    
    def validate_query_params(self, symbol: str = None, start_date: str = None, 
                            end_date: str = None) -> Dict[str, Any]:
        """驗證查詢參數
        
        Args:
            symbol: 股票代碼
            start_date: 開始日期
            end_date: 結束日期
            
        Returns:
            Dict[str, Any]: 驗證結果
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # 驗證股票代碼
            if symbol:
                available_symbols = self.get_available_symbols()
                if symbol not in available_symbols:
                    validation_result['warnings'].append(f"股票代碼 {symbol} 在數據庫中不存在")
            
            # 驗證日期格式
            if start_date:
                try:
                    pd.to_datetime(start_date)
                except:
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"開始日期格式錯誤: {start_date}")
            
            if end_date:
                try:
                    pd.to_datetime(end_date)
                except:
                    validation_result['valid'] = False
                    validation_result['errors'].append(f"結束日期格式錯誤: {end_date}")
            
            # 驗證日期邏輯
            if start_date and end_date:
                try:
                    start_dt = pd.to_datetime(start_date)
                    end_dt = pd.to_datetime(end_date)
                    if start_dt > end_dt:
                        validation_result['valid'] = False
                        validation_result['errors'].append("開始日期不能晚於結束日期")
                except:
                    pass  # 日期格式錯誤已在上面檢查
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ 驗證查詢參數失敗: {e}")
            return {
                'valid': False,
                'errors': [f"參數驗證失敗: {e}"],
                'warnings': []
            }
