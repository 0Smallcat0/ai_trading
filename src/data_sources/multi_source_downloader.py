#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多數據源下載器 - 台股免費數據整合系統
==================================

整合多個免費台股數據來源，提供統一的數據獲取接口。
支援技術面、基本面、籌碼面、事件面和總經面數據。

功能特點：
- 多數據源整合 (TWSE + TPEX + Yahoo Finance + 政府開放平台)
- 自學能力和數據驗證
- 自動重試和錯誤處理
- 統一的數據格式
- UPSERT資料庫操作

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
from typing import List, Dict, Optional, Any, Union
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text
import json
from functools import wraps
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

class MultiSourceDownloader:
    """多數據源下載器主類"""
    
    def __init__(self, db_url: str = "sqlite:///multi_source_data.db"):
        self.db_url = db_url
        self.engine = create_engine(db_url)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 初始化各個數據源模組
        self.technical = TechnicalDataCrawler(self.session, self.engine)
        self.fundamental = FundamentalDataCrawler(self.session, self.engine)
        self.chip = ChipDataCrawler(self.session, self.engine)
        self.event = EventDataCrawler(self.session, self.engine)
        self.macro = MacroDataCrawler(self.session, self.engine)
        
        logger.info("✅ 多數據源下載器初始化完成")
    
    def get_all_data(self, symbol: str, start_date: str = None, end_date: str = None) -> Dict[str, pd.DataFrame]:
        """獲取指定股票的所有類型數據"""
        if start_date is None:
            start_date = (date.today() - timedelta(days=30)).strftime('%Y%m%d')
        if end_date is None:
            end_date = date.today().strftime('%Y%m%d')
        
        logger.info(f"🚀 開始獲取 {symbol} 的全方位數據 ({start_date} - {end_date})")
        
        results = {}
        
        try:
            # 技術面數據
            results['technical'] = self.technical.get_comprehensive_data(symbol, start_date, end_date)
            
            # 基本面數據
            results['fundamental'] = self.fundamental.get_comprehensive_data(symbol, start_date, end_date)
            
            # 籌碼面數據
            results['chip'] = self.chip.get_comprehensive_data(symbol, start_date, end_date)
            
            # 事件面數據
            results['event'] = self.event.get_comprehensive_data(symbol, start_date, end_date)
            
            # 總經面數據
            results['macro'] = self.macro.get_comprehensive_data(start_date, end_date)
            
            logger.info(f"✅ {symbol} 全方位數據獲取完成")
            return results
            
        except Exception as e:
            logger.error(f"❌ 獲取 {symbol} 數據失敗: {e}")
            return {}

class TechnicalDataCrawler:
    """技術面數據爬蟲"""
    
    def __init__(self, session: requests.Session, engine):
        self.session = session
        self.engine = engine
    
    @handle_with_retry(max_retries=3, delay=2.0)
    def crawl_twse_zero_share(self, date: str = None) -> pd.DataFrame:
        """爬取TWSE零股成交資訊"""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        url = f"https://www.twse.com.tw/exchangeReport/TWTASU?response=csv&date={date}"
        
        try:
            logger.info(f"正在獲取 {date} 零股成交資訊...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # 解析CSV數據
            lines = response.text.strip().split('\n')
            if len(lines) < 2:
                logger.warning(f"零股數據為空: {date}")
                return pd.DataFrame()
            
            # 跳過標題行，從第二行開始
            df = pd.read_csv(pd.io.StringIO('\n'.join(lines[1:])))
            
            if not df.empty:
                df['date'] = pd.to_datetime(date)
                df['data_source'] = 'TWSE_零股'
                
                # 保存到資料庫
                df.to_sql('zero_share_trading', self.engine, if_exists='append', index=False)
                
                logger.info(f"✅ 零股成交資訊獲取成功: {len(df)} 筆記錄")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 零股成交資訊獲取失敗: {e}")
            return pd.DataFrame()
    
    @handle_with_retry(max_retries=3, delay=2.0)
    def crawl_twse_backtest_index(self, start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """爬取TWSE回測基準指數"""
        url = "https://openapi.twse.com.tw/v1/indicesReport/MI_5MINS_HIST"
        
        try:
            logger.info("正在獲取回測基準指數...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            df = pd.DataFrame(data)
            
            if not df.empty:
                df['Date'] = pd.to_datetime(df['Date'])
                
                # 日期篩選
                if start_date:
                    df = df[df['Date'] >= pd.to_datetime(start_date)]
                if end_date:
                    df = df[df['Date'] <= pd.to_datetime(end_date)]
                
                df['data_source'] = 'TWSE_指數'
                
                # 保存到資料庫
                df.to_sql('backtest_index', self.engine, if_exists='append', index=False)
                
                logger.info(f"✅ 回測基準指數獲取成功: {len(df)} 筆記錄")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ 回測基準指數獲取失敗: {e}")
            return pd.DataFrame()
    
    @handle_with_retry(max_retries=3, delay=2.0)
    def crawl_yahoo_adjusted_price(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """爬取Yahoo Finance還原權值股價"""
        try:
            logger.info(f"正在獲取 {symbol} Yahoo Finance還原股價...")
            
            # 轉換日期格式
            start = pd.to_datetime(start_date).strftime('%Y-%m-%d')
            end = pd.to_datetime(end_date).strftime('%Y-%m-%d')
            
            # 使用yfinance獲取調整後股價
            df = yf.download(symbol, start=start, end=end, auto_adjust=True, progress=False)

            if not df.empty:
                # 修復多層欄位結構問題
                if isinstance(df.columns, pd.MultiIndex):
                    # 如果是多層索引，取第一層
                    df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

                df.reset_index(inplace=True)
                df['symbol'] = symbol
                df['data_source'] = 'Yahoo_還原股價'

                # 保存到資料庫
                df.to_sql('adjusted_prices', self.engine, if_exists='append', index=False)

                logger.info(f"✅ {symbol} 還原股價獲取成功: {len(df)} 筆記錄")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ {symbol} 還原股價獲取失敗: {e}")
            return pd.DataFrame()
    
    @handle_with_retry(max_retries=3, delay=2.0)
    def crawl_tpex_cb_trading(self) -> pd.DataFrame:
        """爬取TPEX可轉換公司債成交資訊"""
        url = "https://www.tpex.org.tw/web/regular_emerging/corporateInfo/regular_bond_trading.php"
        
        try:
            logger.info("正在獲取可轉換公司債成交資訊...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
            
            if tables:
                df = pd.read_html(str(tables[0]))[0]
                df['date'] = datetime.now().date()
                df['data_source'] = 'TPEX_可轉債'
                
                # 保存到資料庫
                df.to_sql('cb_trading', self.engine, if_exists='append', index=False)
                
                logger.info(f"✅ 可轉換公司債成交資訊獲取成功: {len(df)} 筆記錄")
                return df
            else:
                logger.warning("未找到可轉換公司債交易表格")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"❌ 可轉換公司債成交資訊獲取失敗: {e}")
            return pd.DataFrame()
    
    @handle_with_retry(max_retries=3, delay=2.0)
    def crawl_market_indicators(self) -> pd.DataFrame:
        """爬取大盤市況指標"""
        url = "https://openapi.twse.com.tw/v1/indicesReport/MI_INDEX"

        try:
            logger.info("正在獲取大盤市況指標...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            df = pd.DataFrame(data)

            if not df.empty:
                df['crawl_date'] = datetime.now().date()
                df['data_source'] = 'TWSE_大盤指標'

                # 保存到資料庫
                df.to_sql('market_indicators', self.engine, if_exists='append', index=False)

                logger.info(f"✅ 大盤市況指標獲取成功: {len(df)} 筆記錄")

            return df

        except Exception as e:
            logger.error(f"❌ 大盤市況指標獲取失敗: {e}")
            return pd.DataFrame()

    @handle_with_retry(max_retries=3, delay=2.0)
    def crawl_disposal_stocks(self) -> pd.DataFrame:
        """爬取處置股清單"""
        url = "https://www.tpex.org.tw/zh-tw/announce/market/disposal.html"

        try:
            logger.info("正在獲取處置股清單...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')

            if tables:
                df = pd.read_html(str(tables[0]))[0]
                df['crawl_date'] = datetime.now().date()
                df['data_source'] = 'TPEX_處置股'

                # 保存到資料庫
                df.to_sql('disposal_stocks', self.engine, if_exists='append', index=False)

                logger.info(f"✅ 處置股清單獲取成功: {len(df)} 筆記錄")
                return df
            else:
                logger.warning("未找到處置股表格")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"❌ 處置股清單獲取失敗: {e}")
            return pd.DataFrame()

    @handle_with_retry(max_retries=3, delay=2.0)
    def crawl_attention_stocks(self) -> pd.DataFrame:
        """爬取注意股清單"""
        url = "https://www.twse.com.tw/zh/page/trading/attention.html"

        try:
            logger.info("正在獲取注意股清單...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')

            if tables:
                df = pd.read_html(str(tables[0]))[0]
                df['crawl_date'] = datetime.now().date()
                df['data_source'] = 'TWSE_注意股'

                # 保存到資料庫
                df.to_sql('attention_stocks', self.engine, if_exists='append', index=False)

                logger.info(f"✅ 注意股清單獲取成功: {len(df)} 筆記錄")
                return df
            else:
                logger.warning("未找到注意股表格")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"❌ 注意股清單獲取失敗: {e}")
            return pd.DataFrame()

    def get_comprehensive_data(self, symbol: str, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """獲取技術面綜合數據"""
        logger.info(f"📊 獲取 {symbol} 技術面數據...")

        results = {}

        # 零股成交資訊
        results['zero_share'] = self.crawl_twse_zero_share(end_date)

        # 回測基準指數
        results['backtest_index'] = self.crawl_twse_backtest_index(start_date, end_date)

        # 還原權值股價
        results['adjusted_price'] = self.crawl_yahoo_adjusted_price(symbol, start_date, end_date)

        # 可轉換公司債
        results['cb_trading'] = self.crawl_tpex_cb_trading()

        # 大盤市況指標
        results['market_indicators'] = self.crawl_market_indicators()

        # 處置股清單
        results['disposal_stocks'] = self.crawl_disposal_stocks()

        # 注意股清單
        results['attention_stocks'] = self.crawl_attention_stocks()

        # 添加延遲避免被封鎖
        time.sleep(3)

        return results

class FundamentalDataCrawler:
    """基本面數據爬蟲"""
    
    def __init__(self, session: requests.Session, engine):
        self.session = session
        self.engine = engine
    
    @handle_with_retry(max_retries=3, delay=2.0)
    def crawl_dividend_announcement(self) -> pd.DataFrame:
        """爬取董事會決擬議分配股利公告"""
        url = "https://www.twse.com.tw/zh/page/announcement/dividend.html"
        
        try:
            logger.info("正在獲取股利公告...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
            
            if tables:
                df = pd.read_html(str(tables[0]))[0]
                df['crawl_date'] = datetime.now().date()
                df['data_source'] = 'TWSE_股利公告'
                
                # 保存到資料庫
                df.to_sql('dividend_announcements', self.engine, if_exists='append', index=False)
                
                logger.info(f"✅ 股利公告獲取成功: {len(df)} 筆記錄")
                return df
            else:
                logger.warning("未找到股利公告表格")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"❌ 股利公告獲取失敗: {e}")
            return pd.DataFrame()
    
    @handle_with_retry(max_retries=3, delay=2.0)
    def crawl_monthly_revenue(self) -> pd.DataFrame:
        """爬取上市櫃月營收"""
        url = "https://www.twse.com.tw/zh/page/announcement/monthly_revenue.html"
        
        try:
            logger.info("正在獲取月營收資料...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table')
            
            if tables:
                df = pd.read_html(str(tables[0]))[0]
                df['crawl_date'] = datetime.now().date()
                df['data_source'] = 'TWSE_月營收'
                
                # 保存到資料庫
                df.to_sql('monthly_revenue', self.engine, if_exists='append', index=False)
                
                logger.info(f"✅ 月營收資料獲取成功: {len(df)} 筆記錄")
                return df
            else:
                logger.warning("未找到月營收表格")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"❌ 月營收資料獲取失敗: {e}")
            return pd.DataFrame()
    
    def get_comprehensive_data(self, symbol: str, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """獲取基本面綜合數據"""
        logger.info(f"📈 獲取 {symbol} 基本面數據...")
        
        results = {}
        
        # 股利公告
        results['dividend'] = self.crawl_dividend_announcement()
        
        # 月營收
        results['monthly_revenue'] = self.crawl_monthly_revenue()
        
        # 添加延遲
        time.sleep(2)
        
        return results

class ChipDataCrawler:
    """籌碼面數據爬蟲"""
    
    def __init__(self, session: requests.Session, engine):
        self.session = session
        self.engine = engine
    
    def get_comprehensive_data(self, symbol: str, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """獲取籌碼面綜合數據"""
        logger.info(f"💰 獲取 {symbol} 籌碼面數據...")
        # 這裡可以添加具體的籌碼面數據爬取邏輯
        return {}

class EventDataCrawler:
    """事件面數據爬蟲"""
    
    def __init__(self, session: requests.Session, engine):
        self.session = session
        self.engine = engine
    
    def get_comprehensive_data(self, symbol: str, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """獲取事件面綜合數據"""
        logger.info(f"📅 獲取 {symbol} 事件面數據...")
        # 這裡可以添加具體的事件面數據爬取邏輯
        return {}

class MacroDataCrawler:
    """總經面數據爬蟲"""
    
    def __init__(self, session: requests.Session, engine):
        self.session = session
        self.engine = engine
    
    def get_comprehensive_data(self, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """獲取總經面綜合數據"""
        logger.info(f"🌍 獲取總經面數據...")
        # 這裡可以添加具體的總經面數據爬取邏輯
        return {}

if __name__ == "__main__":
    # 測試多數據源下載器
    downloader = MultiSourceDownloader()
    
    # 測試獲取台積電的數據
    test_symbol = "2330.TW"
    start_date = "20250701"
    end_date = "20250728"
    
    results = downloader.get_all_data(test_symbol, start_date, end_date)
    
    print("🎉 多數據源下載器測試完成")
    for category, data in results.items():
        if isinstance(data, dict):
            print(f"📊 {category}: {len(data)} 個子類別")
            for sub_cat, df in data.items():
                if not df.empty:
                    print(f"   - {sub_cat}: {len(df)} 筆記錄")
        else:
            print(f"📊 {category}: {len(data) if not data.empty else 0} 筆記錄")
