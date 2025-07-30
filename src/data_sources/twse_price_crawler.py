"""台灣證券交易所股價爬蟲模組

此模組提供股價相關資料的爬取功能，包括：
- 上市股票價格資料
- 上櫃股票價格資料
- 大盤指數資料
- 成交量資料

Example:
    >>> from src.data_sources.twse_price_crawler import TwsePriceCrawler
    >>> crawler = TwsePriceCrawler()
    >>> data = crawler.get_twe_prices(datetime.date(2024, 1, 15))
"""

import logging
from datetime import date
from io import StringIO

import pandas as pd

from src.data_sources.twse_base_crawler import TwseBaseCrawler

logger = logging.getLogger(__name__)


class TwsePriceCrawler(TwseBaseCrawler):
    """台灣證券交易所股價爬蟲類別

    專門負責爬取股價相關資料。
    """

    def get_benchmark_data(self, date_val: date) -> pd.DataFrame:
        """爬取大盤指數資料

        Args:
            date_val: 查詢日期

        Returns:
            pd.DataFrame: 大盤指數資料
        """
        try:
            date_str = date_val.strftime("%Y%m%d")
            url = (f"https://www.twse.com.tw/exchangeReport/FMTQIK?"
                   f"response=csv&date={date_str}")

            response = self._make_request(url)
            if not response.text.strip():
                logger.warning("大盤指數資料為空: %s", date_val)
                return pd.DataFrame()

            # 解析 CSV 資料
            lines = response.text.strip().split('\n')
            data_lines = [line for line in lines if '發行量加權股價指數' in line]

            if not data_lines:
                logger.warning("未找到大盤指數資料: %s", date_val)
                return pd.DataFrame()

            # 建立 DataFrame
            df = pd.DataFrame([line.split(',') for line in data_lines])
            df.columns = ['指數名稱', '收盤指數', '漲跌', '漲跌幅']

            return self._preprocess_dataframe(df, date_val)

        except Exception as e:
            logger.error("爬取大盤指數資料時發生錯誤: %s", e)
            return pd.DataFrame()

    def get_twe_prices(self, date_val: date) -> pd.DataFrame:
        """爬取上市股票價格資料

        Args:
            date_val: 查詢日期

        Returns:
            pd.DataFrame: 上市股票價格資料
        """
        try:
            date_str = date_val.strftime("%Y%m%d")
            url = (f"https://www.twse.com.tw/exchangeReport/MI_INDEX?"
                   f"response=csv&date={date_str}&type=ALLBUT0999")

            response = self._make_request(url)
            df = self._parse_csv_response(response, '證券代號')

            if df.empty:
                logger.warning("上市股票資料為空: %s", date_val)
                return df

            # 合併證券代號和名稱
            df = self._combine_symbol_name(df)
            return self._preprocess_dataframe(df, date_val)

        except Exception as e:
            logger.error("爬取上市股票資料時發生錯誤: %s", e)
            return pd.DataFrame()

    def get_otc_prices(self, date_val: date) -> pd.DataFrame:
        """爬取上櫃股票價格資料

        Args:
            date_val: 查詢日期

        Returns:
            pd.DataFrame: 上櫃股票價格資料
        """
        try:
            date_str = date_val.strftime("%Y/%m/%d")
            url = (f"https://www.tpex.org.tw/web/stock/aftertrading/"
                   f"otc_quotes_no1430/stk_wn1430_result.php?"
                   f"l=zh-tw&d={date_str}&se=AL")

            response = self._make_request(url)
            data = self._parse_json_response(response)

            if not data:
                logger.warning("上櫃股票資料為空: %s", date_val)
                return pd.DataFrame()

            # 建立 DataFrame
            columns = ['證券代號', '證券名稱', '收盤價', '漲跌', '開盤價',
                      '最高價', '最低價', '成交股數', '成交筆數', '成交金額']
            df = pd.DataFrame(data['aaData'], columns=columns)

            # 合併證券代號和名稱
            df = self._combine_symbol_name(df)
            return self._preprocess_dataframe(df, date_val)

        except Exception as e:
            logger.error("爬取上櫃股票資料時發生錯誤: %s", e)
            return pd.DataFrame()

    def get_twe_volume(self, date_val: date) -> pd.DataFrame:
        """爬取上市成交量資料

        Args:
            date_val: 查詢日期

        Returns:
            pd.DataFrame: 上市成交量資料
        """
        try:
            date_str = date_val.strftime("%Y%m%d")
            url = (f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?"
                   f"response=csv&date={date_str}")

            response = self._make_request(url)
            df = self._parse_csv_response(response)

            if df.empty:
                logger.warning("上市成交量資料為空: %s", date_val)
                return df

            return self._preprocess_dataframe(df, date_val)

        except Exception as e:
            logger.error("爬取上市成交量資料時發生錯誤: %s", e)
            return pd.DataFrame()

    def get_otc_volume(self, date_val: date) -> pd.DataFrame:
        """爬取上櫃成交量資料

        Args:
            date_val: 查詢日期

        Returns:
            pd.DataFrame: 上櫃成交量資料
        """
        try:
            date_str = date_val.strftime("%Y/%m/%d")
            url = (f"https://www.tpex.org.tw/web/stock/aftertrading/"
                   f"daily_trading_info/st43_result.php?"
                   f"l=zh-tw&d={date_str}")

            response = self._make_request(url)
            data = self._parse_json_response(response)

            if not data:
                logger.warning("上櫃成交量資料為空: %s", date_val)
                return pd.DataFrame()

            # 建立 DataFrame
            columns = ['證券代號', '證券名稱', '成交股數', '成交筆數', '成交金額']
            df = pd.DataFrame(data['aaData'], columns=columns)

            # 合併證券代號和名稱
            df = self._combine_symbol_name(df)
            return self._preprocess_dataframe(df, date_val)

        except Exception as e:
            logger.error("爬取上櫃成交量資料時發生錯誤: %s", e)
            return pd.DataFrame()

    def get_twe_pe_ratio(self, date_val: date) -> pd.DataFrame:
        """爬取上市本益比資料

        Args:
            date_val: 查詢日期

        Returns:
            pd.DataFrame: 上市本益比資料
        """
        try:
            date_str = date_val.strftime("%Y%m%d")
            url = (f"https://www.twse.com.tw/exchangeReport/BWIBBU_d?"
                   f"response=csv&date={date_str}&selectType=ALL")

            response = self._make_request(url)
            df = self._parse_csv_response(response)

            if df.empty:
                logger.warning("上市本益比資料為空: %s", date_val)
                return df

            return self._preprocess_dataframe(df, date_val)

        except Exception as e:
            logger.error("爬取上市本益比資料時發生錯誤: %s", e)
            return pd.DataFrame()

    def get_otc_pe_ratio(self, date_val: date) -> pd.DataFrame:
        """爬取上櫃本益比資料

        Args:
            date_val: 查詢日期

        Returns:
            pd.DataFrame: 上櫃本益比資料
        """
        try:
            date_str = date_val.strftime("%Y/%m/%d")
            url = (f"https://www.tpex.org.tw/web/stock/aftertrading/"
                   f"peratio_analysis/pera_result.php?"
                   f"l=zh-tw&d={date_str}")

            response = self._make_request(url)
            data = self._parse_json_response(response)

            if not data:
                logger.warning("上櫃本益比資料為空: %s", date_val)
                return pd.DataFrame()

            # 建立 DataFrame
            columns = ['證券代號', '證券名稱', '本益比', '股利殖利率', '股價淨值比']
            df = pd.DataFrame(data['aaData'], columns=columns)

            # 合併證券代號和名稱
            df = self._combine_symbol_name(df)
            return self._preprocess_dataframe(df, date_val)

        except Exception as e:
            logger.error("爬取上櫃本益比資料時發生錯誤: %s", e)
            return pd.DataFrame()
