"""台灣證券交易所爬蟲模組

此模組提供從台灣證券交易所網站爬取各種資料的功能，包括：
- 股票價格資料 (上市/上櫃)
- 大盤指數資料
- 成交量資料
- 本益比資料
- 月營收資料
- 財務報表資料

Example:
    >>> crawler = TWSECrawler()
    >>> data = crawler.price_twe(datetime.date(2024, 1, 15))
"""

import logging
from datetime import date
from typing import Optional

import pandas as pd

from src.data_sources.twse_base_crawler import TwseBaseCrawler
from src.data_sources.twse_financial_crawler import TwseFinancialCrawler
from src.data_sources.twse_price_crawler import TwsePriceCrawler

logger = logging.getLogger(__name__)


class TwseCrawler(TwseBaseCrawler):
    """台灣證券交易所爬蟲基礎類別

    提供從台灣證券交易所網站爬取各種資料的功能。
    """


class TWSECrawler(TwseCrawler):
    """台灣證券交易所爬蟲類別

    提供從台灣證券交易所網站爬取各種資料的功能。
    使用組合模式整合不同類型的爬蟲。
    """

    def __init__(self, delay: float = 1.0):
        """初始化爬蟲

        Args:
            delay: 請求間隔時間（秒）
        """
        super().__init__(delay)
        self.price_crawler = TwsePriceCrawler(delay)
        self.financial_crawler = TwseFinancialCrawler(delay)

    def crawl_benchmark(self, date_val: date) -> pd.DataFrame:
        """爬取大盤指數資料

        Args:
            date_val: 查詢日期

        Returns:
            pd.DataFrame: 大盤指數資料
        """
        return self.price_crawler.get_benchmark_data(date_val)

    def price_twe(self, date_val: date) -> pd.DataFrame:
        """爬取上市股票價格資料

        Args:
            date_val: 查詢日期

        Returns:
            pd.DataFrame: 上市股票價格資料
        """
        return self.price_crawler.get_twe_prices(date_val)

    def price_otc(self, date_val: date) -> pd.DataFrame:
        """爬取上櫃股票價格資料

        Args:
            date_val: 查詢日期

        Returns:
            pd.DataFrame: 上櫃股票價格資料
        """
        return self.price_crawler.get_otc_prices(date_val)

    def bargin_twe(self, date_val: date) -> pd.DataFrame:
        """爬取上市成交量資料

        Args:
            date_val: 查詢日期

        Returns:
            pd.DataFrame: 上市成交量資料
        """
        return self.price_crawler.get_twe_volume(date_val)

    def bargin_otc(self, date_val: date) -> pd.DataFrame:
        """爬取上櫃成交量資料

        Args:
            date_val: 查詢日期

        Returns:
            pd.DataFrame: 上櫃成交量資料
        """
        return self.price_crawler.get_otc_volume(date_val)

    def pe_twe(self, date_val: date) -> pd.DataFrame:
        """爬取上市本益比資料

        Args:
            date_val: 查詢日期

        Returns:
            pd.DataFrame: 上市本益比資料
        """
        return self.price_crawler.get_twe_pe_ratio(date_val)

    def pe_otc(self, date_val: date) -> pd.DataFrame:
        """爬取上櫃本益比資料

        Args:
            date_val: 查詢日期

        Returns:
            pd.DataFrame: 上櫃本益比資料
        """
        return self.price_crawler.get_otc_pe_ratio(date_val)

    def month_revenue(self, symbol: Optional[str], date_val: date) -> pd.DataFrame:
        """爬取月營收資料

        Args:
            symbol: 股票代號（可選，如果為 None 則爬取所有股票）
            date_val: 查詢日期

        Returns:
            pd.DataFrame: 月營收資料
        """
        return self.financial_crawler.get_monthly_revenue(date_val, symbol)

    def crawl_finance_statement(self, year: int, season: int) -> pd.DataFrame:
        """爬取財務報表資料

        Args:
            year: 年份
            season: 季度 (1-4)

        Returns:
            pd.DataFrame: 財務報表資料
        """
        return self.financial_crawler.get_financial_statement(year, season)

    def crawl_twse_divide_ratio(self) -> pd.DataFrame:
        """爬取上市除權息資料

        Returns:
            pd.DataFrame: 上市除權息資料
        """
        return self.financial_crawler.get_twse_dividend_data()

    def crawl_twse_cap_reduction(self) -> pd.DataFrame:
        """爬取上市減資資料

        Returns:
            pd.DataFrame: 上市減資資料
        """
        return self.financial_crawler.get_twse_capital_reduction_data()

    def crawl_otc_divide_ratio(self) -> pd.DataFrame:
        """爬取上櫃除權息資料

        Returns:
            pd.DataFrame: 上櫃除權息資料
        """
        return self.financial_crawler.get_otc_dividend_data()

    def crawl_otc_cap_reduction(self) -> pd.DataFrame:
        """爬取上櫃減資資料

        Returns:
            pd.DataFrame: 上櫃減資資料
        """
        return self.financial_crawler.get_otc_capital_reduction_data()

    def crawl_capital(self) -> pd.DataFrame:
        """爬取股本資料

        Returns:
            pd.DataFrame: 股本資料
        """
        return self.financial_crawler.get_capital_data()


# 創建全域實例
twse_crawler = TWSECrawler()
