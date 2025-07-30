#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
已驗證數據爬蟲系統
================

專注於已驗證可用的台股免費數據源，確保每個功能都穩定可用。
基於測試結果，優先實現成功率高的數據源。
"""

import requests
import pandas as pd
import yfinance as yf
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from io import StringIO
import warnings
warnings.filterwarnings('ignore')

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VerifiedCrawler:
    """已驗證數據爬蟲系統"""

    def __init__(self, db_url: str = "sqlite:///unified_stock_database.db",
                 auto_save: bool = True):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.request_delay = 2.0
        self.auto_save = auto_save

        # 初始化統一存儲
        if auto_save:
            try:
                from ..database.unified_storage import UnifiedStorage
                self.storage = UnifiedStorage(db_url)
                logger.info("✅ 統一存儲系統已啟用")
            except Exception as e:
                logger.warning(f"⚠️ 統一存儲系統初始化失敗: {e}")
                self.storage = None
        else:
            self.storage = None

    def _save_data_if_enabled(self, df: pd.DataFrame, table_name: str,
                              data_source: str, data_type: str = 'REAL_DATA') -> Dict:
        """如果啟用自動存儲，則保存數據到資料庫"""
        if not self.auto_save or not self.storage or df.empty:
            return {'success': False, 'reason': 'Auto save disabled or no data'}

        try:
            result = self.storage.save_to_database(df, table_name, data_source, data_type)
            return result
        except Exception as e:
            logger.error(f"自動存儲失敗: {e}")
            return {'success': False, 'error': str(e)}
    def _safe_request(self, url: str, params: Dict = None, timeout: int = 30) -> Optional[requests.Response]:
        """安全的HTTP請求"""
        try:
            time.sleep(self.request_delay)
            response = self.session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as e:
            logger.error(f"請求失敗 {url}: {e}")
            return None
    
    # ========================================================================
    # 已驗證可用的技術面數據源
    # ========================================================================
    
    def crawl_twse_backtest_index(self) -> pd.DataFrame:
        """回測基準指數 - TWSE OpenAPI JSON ✅"""
        url = "https://openapi.twse.com.tw/v1/indicesReport/MI_5MINS_HIST"
        
        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()
            
        try:
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                df['data_source'] = 'TWSE_回測指數'
                df['crawl_time'] = datetime.now()
                logger.info(f"✅ 回測基準指數獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"回測基準指數解析失敗: {e}")
            return pd.DataFrame()
    
    def crawl_yahoo_adjusted_price(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """還原權值股價 - Yahoo Finance API ✅"""
        try:
            start = pd.to_datetime(start_date).strftime('%Y-%m-%d')
            end = pd.to_datetime(end_date).strftime('%Y-%m-%d')

            df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)

            if not df.empty:
                # 修復多層欄位結構問題
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

                df.reset_index(inplace=True)
                df['symbol'] = symbol

                # 標準化欄位名稱以符合資料庫結構
                df = df.rename(columns={
                    'Date': 'date',
                    'Open': 'open_price',
                    'High': 'high_price',
                    'Low': 'low_price',
                    'Close': 'close_price',
                    'Volume': 'volume'
                })

                # 如果有調整後收盤價，添加到adjusted_close欄位
                if 'close_price' in df.columns:
                    df['adjusted_close'] = df['close_price']

                logger.info(f"✅ {symbol} 還原股價獲取成功: {len(df)} 筆記錄")

                # 自動存儲到資料庫
                storage_result = self._save_data_if_enabled(
                    df, 'stock_daily_prices', 'Yahoo_Finance', 'REAL_DATA'
                )
                if storage_result.get('success'):
                    logger.info(f"✅ {symbol} 股價數據已存儲到資料庫")

                return df
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"還原股價獲取失敗: {e}")
            return pd.DataFrame()
    
    def crawl_twse_market_indicators(self) -> pd.DataFrame:
        """大盤市況指標 - TWSE OpenAPI JSON ✅"""
        url = "https://openapi.twse.com.tw/v1/indicesReport/MI_INDEX"
        
        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()
            
        try:
            data = response.json()
            if data:
                df = pd.DataFrame(data)

                # 標準化欄位名稱
                df = df.rename(columns={
                    '日期': 'date',
                    '指數': 'index_name',
                    '收盤指數': 'index_value',
                    '漲跌點數': 'change_points',
                    '漲跌百分比': 'change_percent',
                    '特殊處理註記': 'special_note'
                })

                # 處理日期格式
                if 'date' in df.columns:
                    try:
                        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d', errors='coerce')
                    except Exception:
                        df['date'] = datetime.now().date()
                else:
                    df['date'] = datetime.now().date()

                # 處理數值欄位
                for col in ['index_value', 'change_points', 'change_percent']:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')

                logger.info(f"✅ 大盤市況指標獲取成功: {len(df)} 筆記錄")

                # 自動存儲到資料庫
                storage_result = self._save_data_if_enabled(
                    df, 'market_indicators', 'TWSE_OpenAPI', 'REAL_DATA'
                )
                if storage_result.get('success'):
                    logger.info(f"✅ 大盤指標數據已存儲到資料庫")

                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"大盤市況指標解析失敗: {e}")
            return pd.DataFrame()
    
    def crawl_tpex_mainboard_quotes(self) -> pd.DataFrame:
        """TPEX上櫃股票即時報價 ✅"""
        url = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
        
        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()
            
        try:
            data = response.json()
            if isinstance(data, list) and data:
                df = pd.DataFrame(data)
                df['data_source'] = 'TPEX_上櫃股票'
                df['crawl_time'] = datetime.now()
                logger.info(f"✅ TPEX上櫃股票獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"TPEX上櫃股票解析失敗: {e}")
            return pd.DataFrame()
    
    # ========================================================================
    # 已驗證可用的基本面數據源
    # ========================================================================
    
    def crawl_gov_company_info(self, api_key: str = None) -> pd.DataFrame:
        """企業基本資訊 - 政府開放平台 JSON ✅"""
        if not api_key:
            logger.info("政府開放平台需要API金鑰，返回模擬數據")
            return pd.DataFrame({
                'company_id': ['12345678', '87654321'],
                'company_name': ['台積電 [模擬數據]', '鴻海精密 [模擬數據]'],
                'industry': ['半導體業 [模擬數據]', '電子製造業 [模擬數據]'],
                'capital': [259303956330, 138460264120],
                'data_source': ['政府開放平台_企業資訊_模擬數據', '政府開放平台_企業資訊_模擬數據'],
                'crawl_time': [datetime.now(), datetime.now()],
                'data_type': ['MOCK_DATA', 'MOCK_DATA']
            })
        
        url = "https://data.gov.tw/api/v1/rest/datastore/382000000A-000157-053"
        params = {
            'Authorization': api_key,
            'limit': 1000
        }
        
        response = self._safe_request(url, params)
        if not response:
            return pd.DataFrame()
            
        try:
            data = response.json()
            if 'result' in data and 'records' in data['result']:
                df = pd.DataFrame(data['result']['records'])
                df['data_source'] = '政府開放平台_企業資訊'
                df['crawl_time'] = datetime.now()
                logger.info(f"✅ 企業基本資訊獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"企業基本資訊解析失敗: {e}")
            return pd.DataFrame()
    
    def crawl_finmind_financial_data(self, symbol: str = "2330") -> pd.DataFrame:
        """財務指標 - FinMind API JSON ✅"""
        url = "https://api.finmindtrade.com/api/v4/data"
        params = {
            'dataset': 'TaiwanStockFinancialStatements',
            'data_id': symbol,
            'start_date': '2024-01-01'
        }
        
        response = self._safe_request(url, params)
        if not response:
            return pd.DataFrame()
            
        try:
            data = response.json()
            if 'data' in data and data['data']:
                df = pd.DataFrame(data['data'])
                df['data_source'] = 'FinMind_財務指標'
                df['crawl_time'] = datetime.now()
                logger.info(f"✅ 財務指標獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"財務指標解析失敗: {e}")
            return pd.DataFrame()
    
    # ========================================================================
    # 已驗證可用的籌碼面數據源
    # ========================================================================
    
    def crawl_twse_broker_trading(self) -> pd.DataFrame:
        """券商分點買賣超前15大券商明細 - TWSE JSON ✅"""
        url = "https://www.twse.com.tw/fund/T86"
        params = {
            'response': 'json',
            'date': datetime.now().strftime('%Y%m%d'),
            'selectType': 'ALLBUT0999'
        }
        
        response = self._safe_request(url, params)
        if not response:
            return pd.DataFrame()
            
        try:
            data = response.json()
            if 'data' in data and data['data']:
                df = pd.DataFrame(data['data'])
                df['data_source'] = 'TWSE_券商買賣超'
                df['crawl_time'] = datetime.now()
                logger.info(f"✅ 券商買賣超明細獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"券商買賣超明細解析失敗: {e}")
            return pd.DataFrame()
    
    def crawl_twse_foreign_holding(self) -> pd.DataFrame:
        """外資持股比率 - TWSE JSON ✅"""
        url = "https://www.twse.com.tw/fund/MI_QFIIS"
        params = {
            'response': 'json',
            'date': datetime.now().strftime('%Y%m%d')
        }
        
        response = self._safe_request(url, params)
        if not response:
            return pd.DataFrame()
            
        try:
            data = response.json()
            if 'data' in data and data['data']:
                df = pd.DataFrame(data['data'])
                df['data_source'] = 'TWSE_外資持股'
                df['crawl_time'] = datetime.now()
                logger.info(f"✅ 外資持股比率獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"外資持股比率解析失敗: {e}")
            return pd.DataFrame()
    
    # ========================================================================
    # 已驗證可用的總經面數據源
    # ========================================================================
    
    def crawl_gov_economic_indicators(self, api_key: str = None) -> pd.DataFrame:
        """台灣景氣指標 - 政府開放平台 JSON ✅"""
        if not api_key:
            logger.info("政府開放平台需要API金鑰，返回模擬數據")
            return pd.DataFrame({
                'indicator_name': ['景氣對策信號 [模擬數據]', '景氣領先指標 [模擬數據]', '景氣同時指標 [模擬數據]'],
                'value': [25, 102.5, 98.7],
                'period': ['2025-01', '2025-01', '2025-01'],
                'data_source': ['政府開放平台_景氣指標_模擬數據', '政府開放平台_景氣指標_模擬數據', '政府開放平台_景氣指標_模擬數據'],
                'crawl_time': [datetime.now(), datetime.now(), datetime.now()],
                'data_type': ['MOCK_DATA', 'MOCK_DATA', 'MOCK_DATA']
            })
        
        url = "https://data.gov.tw/api/v1/rest/datastore/382000000A-000151-001"
        params = {
            'Authorization': api_key,
            'limit': 100
        }
        
        response = self._safe_request(url, params)
        if not response:
            return pd.DataFrame()
            
        try:
            data = response.json()
            if 'result' in data and 'records' in data['result']:
                df = pd.DataFrame(data['result']['records'])
                df['data_source'] = '政府開放平台_景氣指標'
                df['crawl_time'] = datetime.now()
                logger.info(f"✅ 景氣指標獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"景氣指標解析失敗: {e}")
            return pd.DataFrame()
    
    def crawl_yahoo_world_indices(self) -> pd.DataFrame:
        """世界指數 - Yahoo Finance API ✅"""
        try:
            indices = {
                '^GSPC': 'S&P 500',
                '^DJI': 'Dow Jones',
                '^IXIC': 'NASDAQ',
                '^N225': 'Nikkei 225',
                '^HSI': 'Hang Seng'
            }
            
            world_data = []
            for symbol, name in indices.items():
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    
                    world_data.append({
                        'symbol': symbol,
                        'name': name,
                        'current_price': info.get('regularMarketPrice', 0),
                        'previous_close': info.get('previousClose', 0),
                        'change': info.get('regularMarketChange', 0),
                        'change_percent': info.get('regularMarketChangePercent', 0),
                        'data_source': 'Yahoo_世界指數',
                        'crawl_time': datetime.now()
                    })
                    
                except Exception as e:
                    logger.warning(f"獲取 {name} 數據失敗: {e}")
                    continue
            
            if world_data:
                df = pd.DataFrame(world_data)
                logger.info(f"✅ 世界指數獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"世界指數解析失敗: {e}")
            return pd.DataFrame()
    
    # ========================================================================
    # 統一接口
    # ========================================================================
    
    def get_verified_sources(self) -> Dict[str, List[str]]:
        """獲取已驗證可用的數據源清單"""
        return {
            'technical': [
                'crawl_twse_backtest_index',
                'crawl_yahoo_adjusted_price', 
                'crawl_twse_market_indicators',
                'crawl_tpex_mainboard_quotes'
            ],
            'fundamental': [
                'crawl_gov_company_info',
                'crawl_finmind_financial_data'
            ],
            'chip': [
                'crawl_twse_broker_trading',
                'crawl_twse_foreign_holding'
            ],
            'macro': [
                'crawl_gov_economic_indicators',
                'crawl_yahoo_world_indices'
            ]
        }
    
    def crawl_all_verified_data(self, **kwargs) -> Dict[str, Dict[str, pd.DataFrame]]:
        """爬取所有已驗證的數據源"""
        verified_sources = self.get_verified_sources()
        all_results = {}
        
        for category, methods in verified_sources.items():
            logger.info(f"🔄 開始爬取 {category} 已驗證數據...")
            category_results = {}
            
            for method_name in methods:
                try:
                    method = getattr(self, method_name)
                    
                    # 根據方法需要的參數調用
                    if method_name == 'crawl_yahoo_adjusted_price':
                        if 'symbol' in kwargs and 'start_date' in kwargs and 'end_date' in kwargs:
                            df = method(kwargs['symbol'], kwargs['start_date'], kwargs['end_date'])
                        else:
                            df = method('2330.TW', '2025-07-20', '2025-07-25')  # 默認參數
                    elif method_name in ['crawl_gov_company_info', 'crawl_gov_economic_indicators']:
                        df = method(kwargs.get('api_key'))
                    elif method_name == 'crawl_finmind_financial_data':
                        df = method(kwargs.get('symbol', '2330'))
                    else:
                        df = method()
                    
                    if not df.empty:
                        category_results[method_name] = df
                        logger.info(f"✅ {method_name} 成功: {len(df)} 筆記錄")
                    else:
                        logger.warning(f"⚠️ {method_name} 無數據")
                        
                except Exception as e:
                    logger.error(f"❌ {method_name} 執行失敗: {e}")
                    continue
            
            all_results[category] = category_results
            success_count = len(category_results)
            total_count = len(methods)
            logger.info(f"📊 {category} 完成: {success_count}/{total_count} 成功")
        
        return all_results
