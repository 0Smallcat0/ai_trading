"""台灣證券交易所財務資料爬蟲模組

此模組提供財務相關資料的爬取功能，包括：
- 月營收資料
- 財務報表資料
- 除權息資料
- 減資資料
- 股本資料

Example:
    >>> from src.data_sources.twse_financial_crawler import TwseFinancialCrawler
    >>> crawler = TwseFinancialCrawler()
    >>> data = crawler.get_monthly_revenue(datetime.date(2024, 1, 1))
"""

import logging
from datetime import date
from typing import Optional

import pandas as pd

from src.data_sources.twse_base_crawler import TwseBaseCrawler

logger = logging.getLogger(__name__)


class TwseFinancialCrawler(TwseBaseCrawler):
    """台灣證券交易所財務資料爬蟲類別

    專門負責爬取財務相關資料。
    """

    def get_monthly_revenue(self, date_val: date, 
                           symbol: Optional[str] = None) -> pd.DataFrame:
        """爬取月營收資料

        Args:
            date_val: 查詢日期
            symbol: 股票代號（可選，如果為 None 則爬取所有股票）

        Returns:
            pd.DataFrame: 月營收資料
        """
        try:
            year = date_val.year - 1911  # 轉換為民國年
            month = date_val.month

            url = (f"https://mops.twse.com.tw/nas/t21/sii/"
                   f"t21sc03_{year}_{month}_0.html")

            response = self._make_request(url)
            dfs = self._parse_html_tables(response, encoding='big5')

            if not dfs:
                logger.warning("月營收資料為空: %s", date_val)
                return pd.DataFrame()

            # 合併所有表格
            df = pd.concat([df for df in dfs if df.shape[1] > 10])
            df = df.iloc[:, :10]  # 只取前10欄
            df.columns = df.columns.droplevel(0)
            df.columns = [
                '公司代號', '公司名稱', '當月營收', '上月營收', '去年當月營收',
                '上月比較增減(%)', '去年同月增減(%)', '當月累計營收',
                '去年累計營收', '前期比較增減(%)'
            ]

            # 如果指定了股票代號，則過濾資料
            if symbol:
                df = df[df['公司代號'] == symbol]

            # 合併公司代號和名稱
            df = self._combine_symbol_name(df)
            return self._preprocess_dataframe(df, date_val)

        except Exception as e:
            logger.error("爬取月營收資料時發生錯誤: %s", e)
            return pd.DataFrame()

    def get_financial_statement(self, year: int, season: int) -> pd.DataFrame:
        """爬取財務報表資料

        Args:
            year: 年份
            season: 季度 (1-4)

        Returns:
            pd.DataFrame: 財務報表資料
        """
        try:
            # 轉換為民國年
            roc_year = year - 1911

            url = (f"https://mops.twse.com.tw/mops/web/t163sb04?"
                   f"encodeURIComponent=1&step=1&firstin=1&off=1&"
                   f"keyword4=&code1=&TYPEK2=&checkbtn=&queryName=co_id&"
                   f"inpuType=co_id&TYPEK=all&isnew=false&co_id=&"
                   f"year={roc_year}&season={season}")

            response = self._make_request(url)
            dfs = self._parse_html_tables(response, encoding='big5')

            if not dfs:
                logger.warning("財務報表資料為空: %s Q%s", year, season)
                return pd.DataFrame()

            # 取得主要財務報表
            df = dfs[0] if dfs else pd.DataFrame()
            return self._preprocess_dataframe(df, date(year, season * 3, 1))

        except Exception as e:
            logger.error("爬取財務報表資料時發生錯誤: %s", e)
            return pd.DataFrame()

    def get_twse_dividend_data(self) -> pd.DataFrame:
        """爬取上市除權息資料

        Returns:
            pd.DataFrame: 上市除權息資料
        """
        try:
            url = ("https://www.twse.com.tw/exchangeReport/TWT49U?"
                   "response=csv&strDate=")

            response = self._make_request(url)
            df = self._parse_csv_response(response)

            if df.empty:
                logger.warning("上市除權息資料為空")
                return df

            return df

        except Exception as e:
            logger.error("爬取上市除權息資料時發生錯誤: %s", e)
            return pd.DataFrame()

    def get_twse_capital_reduction_data(self) -> pd.DataFrame:
        """爬取上市減資資料

        Returns:
            pd.DataFrame: 上市減資資料
        """
        try:
            url = ("https://www.twse.com.tw/exchangeReport/TWT48U?"
                   "response=csv")

            response = self._make_request(url)
            df = self._parse_csv_response(response)

            if df.empty:
                logger.warning("上市減資資料為空")
                return df

            return df

        except Exception as e:
            logger.error("爬取上市減資資料時發生錯誤: %s", e)
            return pd.DataFrame()

    def get_otc_dividend_data(self) -> pd.DataFrame:
        """爬取上櫃除權息資料

        Returns:
            pd.DataFrame: 上櫃除權息資料
        """
        try:
            url = ("https://www.tpex.org.tw/web/stock/exright/dailyquo/"
                   "exDailyQ_result.php?l=zh-tw")

            response = self._make_request(url)
            data = self._parse_json_response(response)

            if not data:
                logger.warning("上櫃除權息資料為空")
                return pd.DataFrame()

            columns = ['證券代號', '證券名稱', '除權息日期', '除權息類型']
            df = pd.DataFrame(data['aaData'], columns=columns)

            # 合併證券代號和名稱
            df = self._combine_symbol_name(df)
            return df

        except Exception as e:
            logger.error("爬取上櫃除權息資料時發生錯誤: %s", e)
            return pd.DataFrame()

    def get_otc_capital_reduction_data(self) -> pd.DataFrame:
        """爬取上櫃減資資料

        Returns:
            pd.DataFrame: 上櫃減資資料
        """
        try:
            url = ("https://www.tpex.org.tw/web/stock/exright/revivt/"
                   "revivt_result.php?l=zh-tw")

            response = self._make_request(url)
            data = self._parse_json_response(response)

            if not data:
                logger.warning("上櫃減資資料為空")
                return pd.DataFrame()

            columns = ['證券代號', '證券名稱', '減資日期', '減資比例']
            df = pd.DataFrame(data['aaData'], columns=columns)

            # 合併證券代號和名稱
            df = self._combine_symbol_name(df)
            return df

        except Exception as e:
            logger.error("爬取上櫃減資資料時發生錯誤: %s", e)
            return pd.DataFrame()

    def get_capital_data(self) -> pd.DataFrame:
        """爬取股本資料

        Returns:
            pd.DataFrame: 股本資料
        """
        try:
            url = ("https://mops.twse.com.tw/mops/web/t05st03?"
                   "encodeURIComponent=1&step=1&firstin=1&off=1")

            response = self._make_request(url)
            dfs = self._parse_html_tables(response, encoding='big5')

            if not dfs:
                logger.warning("股本資料為空")
                return pd.DataFrame()

            df = dfs[0] if dfs else pd.DataFrame()
            return df

        except Exception as e:
            logger.error("爬取股本資料時發生錯誤: %s", e)
            return pd.DataFrame()

    def get_comprehensive_financial_data(self, date_val: date) -> dict:
        """獲取綜合財務資料

        Args:
            date_val: 查詢日期

        Returns:
            dict: 包含各種財務資料的字典
        """
        result = {}

        # 月營收資料
        try:
            monthly_revenue = self.get_monthly_revenue(date_val)
            if not monthly_revenue.empty:
                result['monthly_revenue'] = monthly_revenue
        except Exception as e:
            logger.error("獲取月營收資料時發生錯誤: %s", e)

        # 除權息資料
        try:
            twse_dividend = self.get_twse_dividend_data()
            if not twse_dividend.empty:
                result['twse_dividend'] = twse_dividend

            otc_dividend = self.get_otc_dividend_data()
            if not otc_dividend.empty:
                result['otc_dividend'] = otc_dividend
        except Exception as e:
            logger.error("獲取除權息資料時發生錯誤: %s", e)

        # 股本資料
        try:
            capital_data = self.get_capital_data()
            if not capital_data.empty:
                result['capital_data'] = capital_data
        except Exception as e:
            logger.error("獲取股本資料時發生錯誤: %s", e)

        return result
