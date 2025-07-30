#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
綜合數據爬蟲系統
==============

實現所有33個台股免費數據源的爬蟲模組，確保每個功能都有可用的實現。
按照技術面、基本面、籌碼面、事件面、總經面分類組織。
"""

import requests
import pandas as pd
import yfinance as yf
import time
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin
import warnings
warnings.filterwarnings('ignore')

try:
    from .enhanced_html_parser import EnhancedHTMLParser
except ImportError:
    # 如果導入失敗，使用空類作為備用
    class EnhancedHTMLParser:
        def parse_twse_page(self, url, data_type, **kwargs):
            return pd.DataFrame()

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensiveCrawler:
    """綜合數據爬蟲系統"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.request_delay = 2.0  # 請求間隔

        # 初始化增強HTML解析器
        try:
            self.html_parser = EnhancedHTMLParser()
            logger.info("✅ 增強HTML解析器初始化成功")
        except Exception as e:
            logger.warning(f"增強HTML解析器初始化失敗: {e}")
            self.html_parser = None
        
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
    # 技術面數據爬蟲 (10個數據源)
    # ========================================================================
    
    def crawl_twse_zero_share(self, date_str: str = None) -> pd.DataFrame:
        """1. 上市櫃盤後零股成交資訊 - TWSE CSV"""
        if not date_str:
            date_str = datetime.now().strftime('%Y%m%d')
            
        url = "https://www.twse.com.tw/exchangeReport/TWTASU"
        params = {
            'response': 'csv',
            'date': date_str
        }
        
        response = self._safe_request(url, params)
        if not response:
            return pd.DataFrame()
            
        try:
            # 解析CSV數據
            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                return pd.DataFrame()

            # 找到數據開始行
            data_lines = []
            for line in lines:
                if '證券代號' in line or line.startswith('"'):
                    data_lines.append(line)

            if data_lines:
                from io import StringIO
                df = pd.read_csv(StringIO('\n'.join(data_lines)))
                df['data_source'] = 'TWSE_零股'
                df['crawl_time'] = datetime.now()
                logger.info(f"✅ 零股成交資訊獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"零股成交資訊解析失敗: {e}")
            return pd.DataFrame()
    
    def crawl_twse_backtest_index(self) -> pd.DataFrame:
        """2. 回測基準指數 - TWSE OpenAPI JSON"""
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
    
    def crawl_tpex_cb_trading(self) -> pd.DataFrame:
        """3. 可轉換公司債成交資訊 - TPEX HTML"""
        url = "https://www.tpex.org.tw/web/regular_emerging/corporateInfo/regular_bond_trading.php"
        
        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()
            
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
            
            if tables:
                # 找到包含債券數據的表格
                for table in tables:
                    if table.find('th') and '債券' in table.get_text():
                        df = pd.read_html(str(table))[0]
                        df['data_source'] = 'TPEX_可轉債'
                        df['crawl_time'] = datetime.now()
                        logger.info(f"✅ 可轉換公司債資訊獲取成功: {len(df)} 筆記錄")
                        return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"可轉換公司債資訊解析失敗: {e}")
            return pd.DataFrame()
    
    def crawl_twse_trading_change(self) -> pd.DataFrame:
        """4. 上市櫃變更交易 - TWSE HTML"""
        url = "https://www.twse.com.tw/zh/page/trading/exchange/TWTAUU.html"
        
        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()
            
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
            
            if tables:
                # 找到變更交易的表格
                for table in tables:
                    if table.find('th') and ('變更' in table.get_text() or '交易' in table.get_text()):
                        df = pd.read_html(str(table))[0]
                        df['data_source'] = 'TWSE_變更交易'
                        df['crawl_time'] = datetime.now()
                        logger.info(f"✅ 變更交易資訊獲取成功: {len(df)} 筆記錄")
                        return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"變更交易資訊解析失敗: {e}")
            return pd.DataFrame()
    
    def crawl_yahoo_adjusted_price(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """5. 還原權值股價 - Yahoo Finance API"""
        try:
            # 轉換日期格式
            start = pd.to_datetime(start_date).strftime('%Y-%m-%d')
            end = pd.to_datetime(end_date).strftime('%Y-%m-%d')
            
            # 使用yfinance獲取調整後股價
            df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)
            
            if not df.empty:
                # 修復多層欄位結構問題
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]
                
                df.reset_index(inplace=True)
                df['symbol'] = symbol
                df['data_source'] = 'Yahoo_還原股價'
                df['crawl_time'] = datetime.now()
                
                logger.info(f"✅ {symbol} 還原股價獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"還原股價獲取失敗: {e}")
            return pd.DataFrame()
    
    def crawl_tpex_disposal_stocks(self) -> pd.DataFrame:
        """6. 排除處置股 - TPEX HTML"""
        url = "https://www.tpex.org.tw/web/stock/aftertrading/daily_trading_info/st43.php"
        
        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()
            
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
            
            if tables:
                # 找到處置股的表格
                for table in tables:
                    if table.find('th') and ('處置' in table.get_text() or '股票' in table.get_text()):
                        df = pd.read_html(str(table))[0]
                        df['data_source'] = 'TPEX_處置股'
                        df['crawl_time'] = datetime.now()
                        logger.info(f"✅ 處置股資訊獲取成功: {len(df)} 筆記錄")
                        return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"處置股資訊解析失敗: {e}")
            return pd.DataFrame()
    
    def crawl_twse_market_indicators(self) -> pd.DataFrame:
        """7. 大盤市況指標 - TWSE OpenAPI JSON ✅"""
        url = "https://openapi.twse.com.tw/v1/indicesReport/MI_INDEX"
        
        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()
            
        try:
            data = response.json()
            if data:
                df = pd.DataFrame(data)
                df['data_source'] = 'TWSE_大盤指標'
                df['crawl_time'] = datetime.now()
                logger.info(f"✅ 大盤市況指標獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"大盤市況指標解析失敗: {e}")
            return pd.DataFrame()
    
    def crawl_twse_attention_stocks(self) -> pd.DataFrame:
        """8. 排除注意股 - TWSE HTML"""
        url = "https://www.twse.com.tw/zh/page/trading/exchange/TWTB4U.html"
        
        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()
            
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
            
            if tables:
                # 找到注意股的表格
                for table in tables:
                    if table.find('th') and ('注意' in table.get_text() or '股票' in table.get_text()):
                        df = pd.read_html(str(table))[0]
                        df['data_source'] = 'TWSE_注意股'
                        df['crawl_time'] = datetime.now()
                        logger.info(f"✅ 注意股資訊獲取成功: {len(df)} 筆記錄")
                        return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"注意股資訊解析失敗: {e}")
            return pd.DataFrame()
    
    def crawl_taifex_futures_daily(self, date_str: str = None) -> pd.DataFrame:
        """9. 期貨日成交資訊 - TAIFEX CSV"""
        if not date_str:
            date_str = datetime.now().strftime('%Y%m%d')
            
        url = "https://www.taifex.com.tw/cht/3/dailyFXRate"
        params = {
            'queryDate': date_str
        }
        
        response = self._safe_request(url, params)
        if not response:
            return pd.DataFrame()
            
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
            
            if tables:
                # 找到期貨數據的表格
                for table in tables:
                    if table.find('th') and ('期貨' in table.get_text() or '成交' in table.get_text()):
                        df = pd.read_html(str(table))[0]
                        df['data_source'] = 'TAIFEX_期貨'
                        df['crawl_time'] = datetime.now()
                        logger.info(f"✅ 期貨日成交資訊獲取成功: {len(df)} 筆記錄")
                        return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"期貨日成交資訊解析失敗: {e}")
            return pd.DataFrame()
    
    def crawl_twse_intraday_zero_share(self) -> pd.DataFrame:
        """10. 上市櫃盤中零股成交資訊 - TWSE HTML"""
        url = "https://www.twse.com.tw/zh/page/trading/exchange/TWTASU.html"
        
        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()
            
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
            
            if tables:
                # 找到盤中零股的表格
                for table in tables:
                    if table.find('th') and ('零股' in table.get_text() or '盤中' in table.get_text()):
                        df = pd.read_html(str(table))[0]
                        df['data_source'] = 'TWSE_盤中零股'
                        df['crawl_time'] = datetime.now()
                        logger.info(f"✅ 盤中零股成交資訊獲取成功: {len(df)} 筆記錄")
                        return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"盤中零股成交資訊解析失敗: {e}")
            return pd.DataFrame()
    
    # ========================================================================
    # 基本面數據爬蟲 (7個數據源)
    # ========================================================================
    
    def crawl_twse_dividend_announcement(self) -> pd.DataFrame:
        """1. 董事會決擬議分配股利公告 - TWSE HTML (增強解析)"""
        url = "https://www.twse.com.tw/zh/page/trading/exchange/TWTB7U.html"

        # 優先使用增強HTML解析器
        if self.html_parser:
            try:
                df = self.html_parser.parse_twse_page(url, '股利公告')
                if not df.empty:
                    logger.info(f"✅ 股利公告獲取成功 (增強解析): {len(df)} 筆記錄")
                    return df
            except Exception as e:
                logger.warning(f"增強解析失敗，使用備用方法: {e}")

        # 備用解析方法
        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()

        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')

            if tables:
                # 找到股利公告的表格
                for table in tables:
                    if table.find('th') and ('股利' in table.get_text() or '分配' in table.get_text()):
                        df = pd.read_html(str(table))[0]
                        df['data_source'] = 'TWSE_股利公告'
                        df['crawl_time'] = datetime.now()
                        logger.info(f"✅ 股利公告獲取成功: {len(df)} 筆記錄")
                        return df

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"股利公告解析失敗: {e}")
            return pd.DataFrame()
    
    def crawl_tpex_capital_reduction(self) -> pd.DataFrame:
        """2. 上櫃減資 - TPEX HTML"""
        url = "https://www.tpex.org.tw/web/regular_emerging/corporateInfo/capital_reduction.php"
        
        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()
            
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
            
            if tables:
                # 找到減資的表格
                for table in tables:
                    if table.find('th') and '減資' in table.get_text():
                        df = pd.read_html(str(table))[0]
                        df['data_source'] = 'TPEX_減資'
                        df['crawl_time'] = datetime.now()
                        logger.info(f"✅ 上櫃減資資訊獲取成功: {len(df)} 筆記錄")
                        return df
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"上櫃減資資訊解析失敗: {e}")
            return pd.DataFrame()

    def crawl_twse_capital_reduction(self) -> pd.DataFrame:
        """3. 上市減資 - TWSE HTML"""
        url = "https://www.twse.com.tw/zh/page/trading/exchange/TWTB8U.html"

        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()

        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')

            if tables:
                # 找到減資的表格
                for table in tables:
                    if table.find('th') and '減資' in table.get_text():
                        df = pd.read_html(str(table))[0]
                        df['data_source'] = 'TWSE_減資'
                        df['crawl_time'] = datetime.now()
                        logger.info(f"✅ 上市減資資訊獲取成功: {len(df)} 筆記錄")
                        return df

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"上市減資資訊解析失敗: {e}")
            return pd.DataFrame()

    def crawl_gov_company_info(self, api_key: str = None) -> pd.DataFrame:
        """4. 企業基本資訊 - 政府開放平台 JSON ✅"""
        if not api_key:
            logger.warning("政府開放平台需要API金鑰，返回模擬數據")
            # 返回模擬數據結構
            return pd.DataFrame({
                'company_id': ['12345678'],
                'company_name': ['測試公司 [模擬數據]'],
                'industry': ['電子業 [模擬數據]'],
                'data_source': ['政府開放平台_企業資訊_模擬數據'],
                'crawl_time': [datetime.now()],
                'data_type': ['MOCK_DATA']
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

    def crawl_twse_business_info(self) -> pd.DataFrame:
        """5. 企業主要經營業務 - TWSE HTML"""
        url = "https://www.twse.com.tw/zh/page/trading/exchange/TWTB9U.html"

        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()

        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')

            if tables:
                # 找到經營業務的表格
                for table in tables:
                    if table.find('th') and ('業務' in table.get_text() or '經營' in table.get_text()):
                        df = pd.read_html(str(table))[0]
                        df['data_source'] = 'TWSE_經營業務'
                        df['crawl_time'] = datetime.now()
                        logger.info(f"✅ 企業經營業務獲取成功: {len(df)} 筆記錄")
                        return df

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"企業經營業務解析失敗: {e}")
            return pd.DataFrame()

    def crawl_twse_monthly_revenue(self, year: int = None, month: int = None) -> pd.DataFrame:
        """6. 上市櫃月營收 - TWSE HTML (增強解析)"""
        if not year:
            year = datetime.now().year
        if not month:
            month = datetime.now().month

        # 優先使用增強HTML解析器
        if self.html_parser:
            try:
                url_html = "https://www.twse.com.tw/zh/page/trading/exchange/TWTB4U.html"
                df = self.html_parser.parse_twse_page(url_html, '月營收', year=year, month=month)
                if not df.empty:
                    logger.info(f"✅ 月營收資訊獲取成功 (增強解析): {len(df)} 筆記錄")
                    return df
            except Exception as e:
                logger.warning(f"增強解析失敗，使用備用方法: {e}")

        # 備用JSON API方法
        url = "https://www.twse.com.tw/exchangeReport/TWTB4U"
        params = {
            'response': 'json',
            'date': f"{year}{month:02d}01"
        }

        response = self._safe_request(url, params)
        if not response:
            return pd.DataFrame()

        try:
            data = response.json()
            if 'data' in data and data['data']:
                df = pd.DataFrame(data['data'])
                df['data_source'] = 'TWSE_月營收'
                df['crawl_time'] = datetime.now()
                logger.info(f"✅ 月營收資訊獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"月營收資訊解析失敗: {e}")
            return pd.DataFrame()

    def crawl_finmind_financial_data(self, symbol: str = "2330") -> pd.DataFrame:
        """7. 財務指標 - FinMind API JSON"""
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
    # 籌碼面數據爬蟲 (6個數據源)
    # ========================================================================

    def crawl_twse_broker_mapping(self) -> pd.DataFrame:
        """1. 券商分點名稱對照表 - TWSE HTML"""
        url = "https://www.twse.com.tw/zh/page/trading/exchange/TWTB5U.html"

        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()

        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')

            if tables:
                # 找到券商對照表
                for table in tables:
                    if table.find('th') and ('券商' in table.get_text() or '分點' in table.get_text()):
                        df = pd.read_html(str(table))[0]
                        df['data_source'] = 'TWSE_券商對照'
                        df['crawl_time'] = datetime.now()
                        logger.info(f"✅ 券商分點對照表獲取成功: {len(df)} 筆記錄")
                        return df

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"券商分點對照表解析失敗: {e}")
            return pd.DataFrame()

    def crawl_twse_broker_trading(self, symbol: str = "2330") -> pd.DataFrame:
        """2. 券商分點買賣超前15大券商明細 - TWSE HTML"""
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
        """3. 外資持股比率 - TWSE HTML"""
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

    def crawl_taifex_institutional_trading(self) -> pd.DataFrame:
        """4. 期貨三大法人盤後資訊 - TAIFEX CSV"""
        url = "https://www.taifex.com.tw/cht/3/largeTraderFutQry"
        params = {
            'queryDate': datetime.now().strftime('%Y/%m/%d')
        }

        response = self._safe_request(url, params)
        if not response:
            return pd.DataFrame()

        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')

            if tables:
                # 找到三大法人的表格
                for table in tables:
                    if table.find('th') and ('法人' in table.get_text() or '期貨' in table.get_text()):
                        df = pd.read_html(str(table))[0]
                        df['data_source'] = 'TAIFEX_三大法人'
                        df['crawl_time'] = datetime.now()
                        logger.info(f"✅ 期貨三大法人資訊獲取成功: {len(df)} 筆記錄")
                        return df

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"期貨三大法人資訊解析失敗: {e}")
            return pd.DataFrame()

    def crawl_twse_margin_trading(self) -> pd.DataFrame:
        """5. 融資融券 - TWSE HTML"""
        url = "https://www.twse.com.tw/exchangeReport/MI_MARGN"
        params = {
            'response': 'json',
            'date': datetime.now().strftime('%Y%m%d'),
            'selectType': 'ALL'
        }

        response = self._safe_request(url, params)
        if not response:
            return pd.DataFrame()

        try:
            data = response.json()
            if 'data' in data and data['data']:
                df = pd.DataFrame(data['data'])
                df['data_source'] = 'TWSE_融資融券'
                df['crawl_time'] = datetime.now()
                logger.info(f"✅ 融資融券資訊獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"融資融券資訊解析失敗: {e}")
            return pd.DataFrame()

    def crawl_twse_securities_lending(self) -> pd.DataFrame:
        """6. 借券 - TWSE HTML"""
        url = "https://www.twse.com.tw/exchangeReport/TWT38U"
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
                df['data_source'] = 'TWSE_借券'
                df['crawl_time'] = datetime.now()
                logger.info(f"✅ 借券資訊獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"借券資訊解析失敗: {e}")
            return pd.DataFrame()

    # ========================================================================
    # 事件面數據爬蟲 (5個數據源)
    # ========================================================================

    def crawl_twse_announcements(self) -> pd.DataFrame:
        """1. 重訊公告 - TWSE HTML (增強解析)"""
        url = "https://www.twse.com.tw/zh/page/trading/exchange/TWTB6U.html"

        # 優先使用增強HTML解析器
        if self.html_parser:
            try:
                df = self.html_parser.parse_twse_page(url, '重訊公告')
                if not df.empty:
                    logger.info(f"✅ 重訊公告獲取成功 (增強解析): {len(df)} 筆記錄")
                    return df
            except Exception as e:
                logger.warning(f"增強解析失敗，使用備用方法: {e}")

        # 備用解析方法
        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()

        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')

            if tables:
                # 找到重訊公告的表格
                for table in tables:
                    if table.find('th') and ('公告' in table.get_text() or '重訊' in table.get_text()):
                        df = pd.read_html(str(table))[0]
                        df['data_source'] = 'TWSE_重訊公告'
                        df['crawl_time'] = datetime.now()
                        logger.info(f"✅ 重訊公告獲取成功: {len(df)} 筆記錄")
                        return df

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"重訊公告解析失敗: {e}")
            return pd.DataFrame()

    def crawl_twse_investor_conference(self) -> pd.DataFrame:
        """2. 法說會期程 - TWSE HTML"""
        url = "https://www.twse.com.tw/zh/page/trading/exchange/TWTB1U.html"

        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()

        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')

            if tables:
                # 找到法說會的表格
                for table in tables:
                    if table.find('th') and ('法說會' in table.get_text() or '期程' in table.get_text()):
                        df = pd.read_html(str(table))[0]
                        df['data_source'] = 'TWSE_法說會'
                        df['crawl_time'] = datetime.now()
                        logger.info(f"✅ 法說會期程獲取成功: {len(df)} 筆記錄")
                        return df

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"法說會期程解析失敗: {e}")
            return pd.DataFrame()

    def crawl_twse_shareholder_meeting(self) -> pd.DataFrame:
        """3. 股東會期程 - TWSE HTML"""
        url = "https://www.twse.com.tw/zh/page/trading/exchange/TWTB2U.html"

        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()

        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')

            if tables:
                # 找到股東會的表格
                for table in tables:
                    if table.find('th') and ('股東會' in table.get_text() or '期程' in table.get_text()):
                        df = pd.read_html(str(table))[0]
                        df['data_source'] = 'TWSE_股東會'
                        df['crawl_time'] = datetime.now()
                        logger.info(f"✅ 股東會期程獲取成功: {len(df)} 筆記錄")
                        return df

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"股東會期程解析失敗: {e}")
            return pd.DataFrame()

    def crawl_twse_treasury_stock(self) -> pd.DataFrame:
        """4. 庫藏股 - TWSE HTML"""
        url = "https://www.twse.com.tw/zh/page/trading/exchange/TWTB3U.html"

        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()

        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')

            if tables:
                # 找到庫藏股的表格
                for table in tables:
                    if table.find('th') and '庫藏股' in table.get_text():
                        df = pd.read_html(str(table))[0]
                        df['data_source'] = 'TWSE_庫藏股'
                        df['crawl_time'] = datetime.now()
                        logger.info(f"✅ 庫藏股資訊獲取成功: {len(df)} 筆記錄")
                        return df

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"庫藏股資訊解析失敗: {e}")
            return pd.DataFrame()

    def crawl_cnyes_news(self) -> pd.DataFrame:
        """5. 台股新聞 - cnyes RSS"""
        url = "https://news.cnyes.com/api/v3/news/category/tw_stock"

        response = self._safe_request(url)
        if not response:
            return pd.DataFrame()

        try:
            data = response.json()
            if 'items' in data and 'data' in data['items']:
                news_data = []
                for item in data['items']['data']:
                    news_data.append({
                        'title': item.get('title', ''),
                        'summary': item.get('summary', ''),
                        'publish_at': item.get('publishAt', ''),
                        'url': item.get('url', ''),
                        'data_source': 'cnyes_新聞',
                        'crawl_time': datetime.now()
                    })

                df = pd.DataFrame(news_data)
                logger.info(f"✅ 台股新聞獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"台股新聞解析失敗: {e}")
            return pd.DataFrame()

    # ========================================================================
    # 總經面數據爬蟲 (5個數據源)
    # ========================================================================

    def crawl_gov_economic_indicators(self, api_key: str = None) -> pd.DataFrame:
        """1. 台灣景氣指標 - 政府開放平台 JSON ✅"""
        if not api_key:
            logger.warning("政府開放平台需要API金鑰，返回模擬數據")
            # 返回模擬數據結構
            return pd.DataFrame({
                'indicator_name': ['景氣對策信號 [模擬數據]'],
                'value': [25],
                'period': ['2025-01'],
                'data_source': ['政府開放平台_景氣指標_模擬數據'],
                'crawl_time': [datetime.now()],
                'data_type': ['MOCK_DATA']
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

    def crawl_gov_manufacturing_pmi(self, api_key: str = None) -> pd.DataFrame:
        """2. 台灣製造業採購經理人指數 - 政府開放平台 JSON"""
        if not api_key:
            logger.warning("政府開放平台需要API金鑰，返回模擬數據")
            return pd.DataFrame({
                'pmi_value': [52.5],
                'period': ['2025-01 [模擬數據]'],
                'data_source': ['政府開放平台_製造業PMI_模擬數據'],
                'crawl_time': [datetime.now()],
                'data_type': ['MOCK_DATA']
            })

        url = "https://data.gov.tw/api/v1/rest/datastore/382000000A-000152-001"
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
                df['data_source'] = '政府開放平台_製造業PMI'
                df['crawl_time'] = datetime.now()
                logger.info(f"✅ 製造業PMI獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"製造業PMI解析失敗: {e}")
            return pd.DataFrame()

    def crawl_gov_service_pmi(self, api_key: str = None) -> pd.DataFrame:
        """3. 台灣非製造業採購經理人指數 - 政府開放平台 JSON"""
        if not api_key:
            logger.warning("政府開放平台需要API金鑰，返回模擬數據")
            return pd.DataFrame({
                'pmi_value': [48.5],
                'period': ['2025-01 [模擬數據]'],
                'data_source': ['政府開放平台_服務業PMI_模擬數據'],
                'crawl_time': [datetime.now()],
                'data_type': ['MOCK_DATA']
            })

        url = "https://data.gov.tw/api/v1/rest/datastore/382000000A-000153-001"
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
                df['data_source'] = '政府開放平台_服務業PMI'
                df['crawl_time'] = datetime.now()
                logger.info(f"✅ 服務業PMI獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"服務業PMI解析失敗: {e}")
            return pd.DataFrame()

    def crawl_gov_money_supply(self, api_key: str = None) -> pd.DataFrame:
        """4. 貨幣總計數年增率 - 政府開放平台 JSON"""
        if not api_key:
            logger.warning("政府開放平台需要API金鑰，返回模擬數據")
            return pd.DataFrame({
                'money_supply_growth': [3.2],
                'period': ['2025-01 [模擬數據]'],
                'data_source': ['政府開放平台_貨幣供給_模擬數據'],
                'crawl_time': [datetime.now()],
                'data_type': ['MOCK_DATA']
            })

        url = "https://data.gov.tw/api/v1/rest/datastore/382000000A-000154-001"
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
                df['data_source'] = '政府開放平台_貨幣供給'
                df['crawl_time'] = datetime.now()
                logger.info(f"✅ 貨幣供給數據獲取成功: {len(df)} 筆記錄")
                return df
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"貨幣供給數據解析失敗: {e}")
            return pd.DataFrame()

    def crawl_yahoo_world_indices(self) -> pd.DataFrame:
        """5. 世界指數 - Yahoo Finance API"""
        try:
            # 主要世界指數代碼
            indices = {
                '^GSPC': 'S&P 500',
                '^DJI': 'Dow Jones',
                '^IXIC': 'NASDAQ',
                '^N225': 'Nikkei 225',
                '^HSI': 'Hang Seng',
                '000001.SS': 'Shanghai Composite'
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
    # 統一接口方法
    # ========================================================================

    def get_all_data_sources(self) -> Dict[str, List[str]]:
        """獲取所有數據源的分類清單"""
        return {
            'technical': [
                'crawl_twse_zero_share',
                'crawl_twse_backtest_index',
                'crawl_tpex_cb_trading',
                'crawl_twse_trading_change',
                'crawl_yahoo_adjusted_price',
                'crawl_tpex_disposal_stocks',
                'crawl_twse_market_indicators',
                'crawl_twse_attention_stocks',
                'crawl_taifex_futures_daily',
                'crawl_twse_intraday_zero_share'
            ],
            'fundamental': [
                'crawl_twse_dividend_announcement',
                'crawl_tpex_capital_reduction',
                'crawl_twse_capital_reduction',
                'crawl_gov_company_info',
                'crawl_twse_business_info',
                'crawl_twse_monthly_revenue',
                'crawl_finmind_financial_data'
            ],
            'chip': [
                'crawl_twse_broker_mapping',
                'crawl_twse_broker_trading',
                'crawl_twse_foreign_holding',
                'crawl_taifex_institutional_trading',
                'crawl_twse_margin_trading',
                'crawl_twse_securities_lending'
            ],
            'event': [
                'crawl_twse_announcements',
                'crawl_twse_investor_conference',
                'crawl_twse_shareholder_meeting',
                'crawl_twse_treasury_stock',
                'crawl_cnyes_news'
            ],
            'macro': [
                'crawl_gov_economic_indicators',
                'crawl_gov_manufacturing_pmi',
                'crawl_gov_service_pmi',
                'crawl_gov_money_supply',
                'crawl_yahoo_world_indices'
            ]
        }

    def crawl_by_category(self, category: str, **kwargs) -> Dict[str, pd.DataFrame]:
        """按分類爬取數據"""
        all_sources = self.get_all_data_sources()

        if category not in all_sources:
            logger.error(f"未知的數據分類: {category}")
            return {}

        results = {}
        methods = all_sources[category]

        for method_name in methods:
            try:
                method = getattr(self, method_name)
                logger.info(f"正在執行: {method_name}")

                # 根據方法需要的參數調用
                if method_name in ['crawl_yahoo_adjusted_price']:
                    if 'symbol' in kwargs and 'start_date' in kwargs and 'end_date' in kwargs:
                        df = method(kwargs['symbol'], kwargs['start_date'], kwargs['end_date'])
                    else:
                        logger.warning(f"{method_name} 需要 symbol, start_date, end_date 參數")
                        continue
                elif method_name in ['crawl_gov_company_info', 'crawl_gov_economic_indicators',
                                   'crawl_gov_manufacturing_pmi', 'crawl_gov_service_pmi',
                                   'crawl_gov_money_supply']:
                    df = method(kwargs.get('api_key'))
                else:
                    df = method()

                if not df.empty:
                    results[method_name] = df
                    logger.info(f"✅ {method_name} 成功: {len(df)} 筆記錄")
                else:
                    logger.warning(f"⚠️ {method_name} 無數據")

            except Exception as e:
                logger.error(f"❌ {method_name} 執行失敗: {e}")
                continue

        return results

    def crawl_all_data(self, **kwargs) -> Dict[str, Dict[str, pd.DataFrame]]:
        """爬取所有分類的數據"""
        all_results = {}
        categories = ['technical', 'fundamental', 'chip', 'event', 'macro']

        for category in categories:
            logger.info(f"🔄 開始爬取 {category} 數據...")
            category_results = self.crawl_by_category(category, **kwargs)
            all_results[category] = category_results

            success_count = len(category_results)
            total_count = len(self.get_all_data_sources()[category])
            logger.info(f"📊 {category} 完成: {success_count}/{total_count} 成功")

        return all_results
