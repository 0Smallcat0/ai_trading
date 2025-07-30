"""台灣證券交易所基礎爬蟲模組

此模組提供 TWSE 爬蟲的基礎功能，包括：
- HTTP 請求處理
- 資料預處理
- 錯誤處理

Example:
    >>> from src.data_sources.twse_base_crawler import TwseBaseCrawler
    >>> crawler = TwseBaseCrawler()
"""

import logging
import time
from datetime import date
from typing import Any, Dict

import pandas as pd
import requests

logger = logging.getLogger(__name__)


class TwseBaseCrawler:
    """台灣證券交易所基礎爬蟲類別

    提供爬蟲的基礎功能，包括 HTTP 請求和資料預處理。
    """

    def __init__(self, delay: float = 1.0):
        """初始化爬蟲

        Args:
            delay: 請求間隔時間（秒），避免過於頻繁的請求
        """
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                         'AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/91.0.4472.124 Safari/537.36'
        })

    def _make_request(self, url: str, **kwargs) -> requests.Response:
        """發送 HTTP 請求

        Args:
            url: 請求 URL
            **kwargs: 其他請求參數

        Returns:
            requests.Response: 響應物件

        Raises:
            requests.RequestException: 請求失敗時拋出
        """
        try:
            time.sleep(self.delay)  # 避免過於頻繁的請求
            response = self.session.get(url, timeout=30, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error("請求失敗: %s, URL: %s", e, url)
            raise

    def _preprocess_dataframe(self, df: pd.DataFrame, date_val: date) -> pd.DataFrame:
        """預處理 DataFrame

        Args:
            df: 原始 DataFrame
            date_val: 日期

        Returns:
            pd.DataFrame: 處理後的 DataFrame
        """
        if df.empty:
            return df

        # 添加日期欄位
        df['date'] = date_val

        # 清理數值欄位
        numeric_columns = df.select_dtypes(include=[object]).columns
        for col in numeric_columns:
            if col not in ['證券代號', '證券名稱', 'date']:
                df[col] = pd.to_numeric(
                    df[col].astype(str).str.replace(',', ''),
                    errors='coerce'
                )

        return df

    def _combine_symbol_name(self, df: pd.DataFrame) -> pd.DataFrame:
        """合併證券代號和名稱

        Args:
            df: 包含證券代號和名稱的 DataFrame

        Returns:
            pd.DataFrame: 處理後的 DataFrame
        """
        if '證券代號' in df.columns and '證券名稱' in df.columns:
            df['symbol'] = df['證券代號'] + ' ' + df['證券名稱']
        elif '公司代號' in df.columns and '公司名稱' in df.columns:
            df['symbol'] = df['公司代號'] + ' ' + df['公司名稱']

        return df

    def _parse_csv_response(self, response: requests.Response, 
                           header_keyword: str = '證券代號') -> pd.DataFrame:
        """解析 CSV 響應

        Args:
            response: HTTP 響應物件
            header_keyword: 用於識別標頭行的關鍵字

        Returns:
            pd.DataFrame: 解析後的 DataFrame
        """
        if not response.text.strip():
            return pd.DataFrame()

        # 找到資料開始的行
        lines = response.text.split('\n')
        header_line = None
        for i, line in enumerate(lines):
            if header_keyword in line:
                header_line = i
                break

        if header_line is None:
            logger.warning("未找到資料標頭，關鍵字: %s", header_keyword)
            return pd.DataFrame()

        # 解析 CSV 資料
        from io import StringIO
        csv_data = '\n'.join(lines[header_line:])
        df = pd.read_csv(StringIO(csv_data.replace('=', '')))
        df.columns = df.columns.str.replace(' ', '')

        return df

    def _parse_json_response(self, response: requests.Response, 
                            data_key: str = 'aaData') -> Dict[str, Any]:
        """解析 JSON 響應

        Args:
            response: HTTP 響應物件
            data_key: 資料鍵名

        Returns:
            Dict[str, Any]: 解析後的資料

        Raises:
            ValueError: JSON 解析失敗時拋出
        """
        try:
            data = response.json()
            if data_key not in data or not data[data_key]:
                logger.warning("JSON 響應中沒有資料，鍵: %s", data_key)
                return {}
            return data
        except ValueError as e:
            logger.error("JSON 解析失敗: %s", e)
            raise

    def _parse_html_tables(self, response: requests.Response, 
                          encoding: str = 'utf-8') -> list:
        """解析 HTML 表格

        Args:
            response: HTTP 響應物件
            encoding: 編碼格式

        Returns:
            list: 解析後的 DataFrame 列表
        """
        try:
            response.encoding = encoding
            from io import StringIO
            dfs = pd.read_html(StringIO(response.text))
            return dfs if dfs else []
        except Exception as e:
            logger.error("HTML 表格解析失敗: %s", e)
            return []

    def get_session_info(self) -> Dict[str, Any]:
        """獲取會話資訊

        Returns:
            Dict[str, Any]: 會話資訊
        """
        return {
            'delay': self.delay,
            'headers': dict(self.session.headers),
            'cookies': dict(self.session.cookies)
        }

    def close_session(self) -> None:
        """關閉會話"""
        if self.session:
            self.session.close()
            logger.info("已關閉 HTTP 會話")
