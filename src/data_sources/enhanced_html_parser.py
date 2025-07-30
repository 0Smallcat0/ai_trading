# -*- coding: utf-8 -*-
"""
增強HTML解析器模組

此模組提供強化的HTML解析功能，解決數據源驗證報告中HTML解析失敗率高的問題。
整合BeautifulSoup和Selenium動態加載，支援自動更新選擇器機制。

主要功能：
- 智能HTML解析（BeautifulSoup + Selenium）
- 動態選擇器更新機制
- 多重解析策略
- 錯誤恢復和重試機制
- 數據品質驗證

Example:
    基本使用：
    ```python
    from src.data_sources.enhanced_html_parser import EnhancedHTMLParser
    
    parser = EnhancedHTMLParser()
    data = parser.parse_twse_page("https://example.com", "股利公告")
    ```

Note:
    此模組專門解決數據源驗證報告中提到的HTML解析問題，
    特別針對董事會決議分配股利公告、上市櫃月營收、重訊公告等失效數據源。
"""

import logging
import time
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup, Tag
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

# 設定日誌
logger = logging.getLogger(__name__)


class EnhancedHTMLParser:
    """
    增強HTML解析器
    
    提供多重解析策略和智能錯誤恢復機制，專門解決TWSE/TPEX網站的HTML解析問題。
    """
    
    def __init__(self, request_delay: float = 2.0, timeout: int = 30):
        """
        初始化增強HTML解析器
        
        Args:
            request_delay: 請求間隔時間（秒）
            timeout: 請求超時時間（秒）
        """
        self.request_delay = request_delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                         '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 選擇器映射表（可動態更新）
        self.selector_mapping = {
            '股利公告': {
                'table_keywords': ['股利', '分配', '董事會'],
                'selectors': ['table.hasBorder', 'table[class*="table"]', 'table'],
                'fallback_url_patterns': ['/TWTB7U', '/dividend']
            },
            '月營收': {
                'table_keywords': ['營收', '收入', '月報'],
                'selectors': ['table.hasBorder', 'table[id*="revenue"]', 'table'],
                'fallback_url_patterns': ['/TWTB4U', '/revenue']
            },
            '重訊公告': {
                'table_keywords': ['公告', '重訊', '重大訊息'],
                'selectors': ['table.hasBorder', 'table[class*="announce"]', 'table'],
                'fallback_url_patterns': ['/TWTB6U', '/announcement']
            },
            '券商分點': {
                'table_keywords': ['券商', '分點', '對照'],
                'selectors': ['table.hasBorder', 'table[class*="broker"]', 'table'],
                'fallback_url_patterns': ['/broker', '/branch']
            },
            '融資融券': {
                'table_keywords': ['融資', '融券', '信用交易'],
                'selectors': ['table.hasBorder', 'table[class*="margin"]', 'table'],
                'fallback_url_patterns': ['/margin', '/credit']
            }
        }
        
        # Chrome選項設定
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--window-size=1920,1080')
        
    def parse_twse_page(self, url: str, data_type: str, **kwargs) -> pd.DataFrame:
        """
        解析TWSE頁面數據
        
        Args:
            url: 目標URL
            data_type: 數據類型（如'股利公告'、'月營收'等）
            **kwargs: 額外參數
            
        Returns:
            pd.DataFrame: 解析後的數據
        """
        logger.info(f"開始解析 {data_type} 數據: {url}")
        
        # 策略1: 標準HTTP請求 + BeautifulSoup
        result = self._parse_with_requests(url, data_type, **kwargs)
        if not result.empty:
            logger.info(f"✅ 策略1成功解析 {data_type}: {len(result)} 筆記錄")
            return result
            
        # 策略2: Selenium動態加載
        result = self._parse_with_selenium(url, data_type, **kwargs)
        if not result.empty:
            logger.info(f"✅ 策略2成功解析 {data_type}: {len(result)} 筆記錄")
            return result
            
        # 策略3: 備用URL嘗試
        result = self._parse_with_fallback_urls(url, data_type, **kwargs)
        if not result.empty:
            logger.info(f"✅ 策略3成功解析 {data_type}: {len(result)} 筆記錄")
            return result
            
        logger.warning(f"⚠️ 所有解析策略均失敗: {data_type}")
        return pd.DataFrame()
        
    def _parse_with_requests(self, url: str, data_type: str, **kwargs) -> pd.DataFrame:
        """
        使用requests + BeautifulSoup解析
        
        Args:
            url: 目標URL
            data_type: 數據類型
            **kwargs: 額外參數
            
        Returns:
            pd.DataFrame: 解析結果
        """
        try:
            time.sleep(self.request_delay)
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            return self._extract_table_data(soup, data_type, **kwargs)
            
        except Exception as e:
            logger.error(f"requests解析失敗 {url}: {e}")
            return pd.DataFrame()
            
    def _parse_with_selenium(self, url: str, data_type: str, **kwargs) -> pd.DataFrame:
        """
        使用Selenium動態加載解析
        
        Args:
            url: 目標URL
            data_type: 數據類型
            **kwargs: 額外參數
            
        Returns:
            pd.DataFrame: 解析結果
        """
        driver = None
        try:
            driver = webdriver.Chrome(options=self.chrome_options)
            driver.get(url)
            
            # 等待頁面加載完成
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            # 額外等待JavaScript執行
            time.sleep(3)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            return self._extract_table_data(soup, data_type, **kwargs)
            
        except Exception as e:
            logger.error(f"Selenium解析失敗 {url}: {e}")
            return pd.DataFrame()
        finally:
            if driver:
                driver.quit()
                
    def _parse_with_fallback_urls(self, original_url: str, data_type: str, **kwargs) -> pd.DataFrame:
        """
        使用備用URL解析
        
        Args:
            original_url: 原始URL
            data_type: 數據類型
            **kwargs: 額外參數
            
        Returns:
            pd.DataFrame: 解析結果
        """
        if data_type not in self.selector_mapping:
            return pd.DataFrame()
            
        base_url = f"{urlparse(original_url).scheme}://{urlparse(original_url).netloc}"
        fallback_patterns = self.selector_mapping[data_type]['fallback_url_patterns']
        
        for pattern in fallback_patterns:
            fallback_url = urljoin(base_url, pattern)
            if fallback_url != original_url:
                logger.info(f"嘗試備用URL: {fallback_url}")
                result = self._parse_with_requests(fallback_url, data_type, **kwargs)
                if not result.empty:
                    return result
                    
        return pd.DataFrame()
        
    def _extract_table_data(self, soup: BeautifulSoup, data_type: str, **kwargs) -> pd.DataFrame:
        """
        從BeautifulSoup對象中提取表格數據
        
        Args:
            soup: BeautifulSoup對象
            data_type: 數據類型
            **kwargs: 額外參數
            
        Returns:
            pd.DataFrame: 提取的數據
        """
        if data_type not in self.selector_mapping:
            logger.warning(f"未知數據類型: {data_type}")
            return pd.DataFrame()
            
        config = self.selector_mapping[data_type]
        keywords = config['table_keywords']
        selectors = config['selectors']
        
        # 嘗試不同的選擇器
        for selector in selectors:
            tables = soup.select(selector)
            
            for table in tables:
                # 檢查表格是否包含相關關鍵字
                table_text = table.get_text()
                if any(keyword in table_text for keyword in keywords):
                    try:
                        df = pd.read_html(str(table))[0]
                        if not df.empty and len(df.columns) > 1:
                            # 添加元數據
                            df['data_source'] = f'TWSE_{data_type}'
                            df['crawl_time'] = datetime.now()
                            df['parse_method'] = 'enhanced_html_parser'
                            
                            logger.info(f"成功提取 {data_type} 表格數據: {len(df)} 筆記錄")
                            return self._validate_and_clean_data(df, data_type)
                    except Exception as e:
                        logger.warning(f"表格解析失敗: {e}")
                        continue
                        
        logger.warning(f"未找到有效的 {data_type} 表格")
        return pd.DataFrame()
        
    def _validate_and_clean_data(self, df: pd.DataFrame, data_type: str) -> pd.DataFrame:
        """
        驗證和清理數據
        
        Args:
            df: 原始數據
            data_type: 數據類型
            
        Returns:
            pd.DataFrame: 清理後的數據
        """
        try:
            # 移除空行
            df = df.dropna(how='all')
            
            # 移除重複行
            df = df.drop_duplicates()
            
            # 數據類型特定的清理
            if data_type == '股利公告':
                df = self._clean_dividend_data(df)
            elif data_type == '月營收':
                df = self._clean_revenue_data(df)
            elif data_type == '重訊公告':
                df = self._clean_announcement_data(df)
                
            logger.info(f"數據清理完成: {len(df)} 筆有效記錄")
            return df
            
        except Exception as e:
            logger.error(f"數據清理失敗: {e}")
            return df
            
    def _clean_dividend_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理股利公告數據"""
        # 實施股利數據特定的清理邏輯
        return df
        
    def _clean_revenue_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理月營收數據"""
        # 實施營收數據特定的清理邏輯
        return df
        
    def _clean_announcement_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理重訊公告數據"""
        # 實施公告數據特定的清理邏輯
        return df
        
    def update_selector_mapping(self, data_type: str, new_config: Dict[str, Any]) -> None:
        """
        動態更新選擇器映射
        
        Args:
            data_type: 數據類型
            new_config: 新的配置
        """
        self.selector_mapping[data_type] = new_config
        logger.info(f"已更新 {data_type} 的選擇器配置")
        
    def get_health_status(self) -> Dict[str, Any]:
        """
        獲取解析器健康狀態
        
        Returns:
            Dict[str, Any]: 健康狀態信息
        """
        return {
            'parser_name': 'EnhancedHTMLParser',
            'supported_data_types': list(self.selector_mapping.keys()),
            'request_delay': self.request_delay,
            'timeout': self.timeout,
            'last_update': datetime.now().isoformat()
        }
