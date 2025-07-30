"""TWSE 爬蟲測試模組

此模組測試 TWSE 爬蟲的各項功能，包括：
- 爬蟲初始化
- 股價資料爬取
- 財務資料爬取
- 錯誤處理

Example:
    >>> pytest tests/test_twse_crawler.py -v
"""

import pytest
from datetime import date
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import requests

from src.data_sources.twse_crawler import TWSECrawler, TwseCrawler
from src.data_sources.twse_base_crawler import TwseBaseCrawler
from src.data_sources.twse_price_crawler import TwsePriceCrawler
from src.data_sources.twse_financial_crawler import TwseFinancialCrawler


class TestTwseBaseCrawler:
    """基礎爬蟲測試類別"""

    def setup_method(self):
        """設定測試環境"""
        self.crawler = TwseBaseCrawler()

    def test_initialization(self):
        """測試初始化"""
        assert self.crawler.delay == 1.0
        assert self.crawler.session is not None

    def test_initialization_with_custom_delay(self):
        """測試使用自定義延遲初始化"""
        crawler = TwseBaseCrawler(delay=2.0)
        assert crawler.delay == 2.0

    @patch('time.sleep')
    @patch('requests.Session.get')
    def test_make_request_success(self, mock_get, mock_sleep):
        """測試成功的 HTTP 請求"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.crawler._make_request("http://test.com")
        
        assert result == mock_response
        mock_sleep.assert_called_once_with(1.0)
        mock_get.assert_called_once()

    @patch('time.sleep')
    @patch('requests.Session.get')
    def test_make_request_failure(self, mock_get, mock_sleep):
        """測試失敗的 HTTP 請求"""
        mock_get.side_effect = requests.RequestException("Network error")
        
        with pytest.raises(requests.RequestException):
            self.crawler._make_request("http://test.com")

    def test_preprocess_dataframe_empty(self):
        """測試預處理空 DataFrame"""
        empty_df = pd.DataFrame()
        test_date = date(2024, 1, 15)
        
        result = self.crawler._preprocess_dataframe(empty_df, test_date)
        
        assert result.empty

    def test_preprocess_dataframe_with_data(self):
        """測試預處理有資料的 DataFrame"""
        df = pd.DataFrame({
            '證券代號': ['2330'],
            '證券名稱': ['台積電'],
            '收盤價': ['500,000']
        })
        test_date = date(2024, 1, 15)
        
        result = self.crawler._preprocess_dataframe(df, test_date)
        
        assert 'date' in result.columns
        assert result['date'].iloc[0] == test_date
        assert result['收盤價'].iloc[0] == 500000.0

    def test_combine_symbol_name(self):
        """測試合併證券代號和名稱"""
        df = pd.DataFrame({
            '證券代號': ['2330'],
            '證券名稱': ['台積電']
        })
        
        result = self.crawler._combine_symbol_name(df)
        
        assert 'symbol' in result.columns
        assert result['symbol'].iloc[0] == '2330 台積電'

    def test_parse_csv_response_empty(self):
        """測試解析空 CSV 響應"""
        mock_response = Mock()
        mock_response.text = ""
        
        result = self.crawler._parse_csv_response(mock_response)
        
        assert result.empty

    def test_parse_json_response_success(self):
        """測試成功解析 JSON 響應"""
        mock_response = Mock()
        mock_response.json.return_value = {'aaData': [['test', 'data']]}
        
        result = self.crawler._parse_json_response(mock_response)
        
        assert 'aaData' in result
        assert result['aaData'] == [['test', 'data']]

    def test_parse_json_response_failure(self):
        """測試失敗解析 JSON 響應"""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        with pytest.raises(ValueError):
            self.crawler._parse_json_response(mock_response)

    def test_get_session_info(self):
        """測試獲取會話資訊"""
        info = self.crawler.get_session_info()
        
        assert 'delay' in info
        assert 'headers' in info
        assert 'cookies' in info
        assert info['delay'] == 1.0

    def test_close_session(self):
        """測試關閉會話"""
        with patch.object(self.crawler.session, 'close') as mock_close:
            self.crawler.close_session()
            mock_close.assert_called_once()


class TestTwsePriceCrawler:
    """股價爬蟲測試類別"""

    def setup_method(self):
        """設定測試環境"""
        self.crawler = TwsePriceCrawler()

    @patch.object(TwsePriceCrawler, '_make_request')
    def test_get_benchmark_data_success(self, mock_request):
        """測試成功獲取大盤指數資料"""
        mock_response = Mock()
        mock_response.text = "發行量加權股價指數,15000,100,0.67"
        mock_request.return_value = mock_response
        
        test_date = date(2024, 1, 15)
        result = self.crawler.get_benchmark_data(test_date)
        
        assert not result.empty
        assert '指數名稱' in result.columns

    @patch.object(TwsePriceCrawler, '_make_request')
    def test_get_benchmark_data_empty(self, mock_request):
        """測試獲取空的大盤指數資料"""
        mock_response = Mock()
        mock_response.text = ""
        mock_request.return_value = mock_response
        
        test_date = date(2024, 1, 15)
        result = self.crawler.get_benchmark_data(test_date)
        
        assert result.empty

    @patch.object(TwsePriceCrawler, '_parse_csv_response')
    @patch.object(TwsePriceCrawler, '_make_request')
    def test_get_twe_prices_success(self, mock_request, mock_parse):
        """測試成功獲取上市股價資料"""
        mock_df = pd.DataFrame({
            '證券代號': ['2330'],
            '證券名稱': ['台積電'],
            '收盤價': [500]
        })
        mock_parse.return_value = mock_df
        
        test_date = date(2024, 1, 15)
        result = self.crawler.get_twe_prices(test_date)
        
        assert not result.empty
        mock_request.assert_called_once()
        mock_parse.assert_called_once()


class TestTwseFinancialCrawler:
    """財務爬蟲測試類別"""

    def setup_method(self):
        """設定測試環境"""
        self.crawler = TwseFinancialCrawler()

    @patch.object(TwseFinancialCrawler, '_parse_html_tables')
    @patch.object(TwseFinancialCrawler, '_make_request')
    def test_get_monthly_revenue_success(self, mock_request, mock_parse):
        """測試成功獲取月營收資料"""
        mock_df = pd.DataFrame({
            '公司代號': ['2330'],
            '公司名稱': ['台積電'],
            '當月營收': [100000]
        })
        mock_parse.return_value = [mock_df]
        
        test_date = date(2024, 1, 15)
        result = self.crawler.get_monthly_revenue(test_date)
        
        assert not result.empty
        mock_request.assert_called_once()

    @patch.object(TwseFinancialCrawler, '_parse_html_tables')
    @patch.object(TwseFinancialCrawler, '_make_request')
    def test_get_financial_statement_success(self, mock_request, mock_parse):
        """測試成功獲取財務報表資料"""
        mock_df = pd.DataFrame({'test': ['data']})
        mock_parse.return_value = [mock_df]
        
        result = self.crawler.get_financial_statement(2024, 1)
        
        assert not result.empty
        mock_request.assert_called_once()


class TestTWSECrawler:
    """TWSE 爬蟲測試類別"""

    def setup_method(self):
        """設定測試環境"""
        self.crawler = TWSECrawler()

    def test_initialization(self):
        """測試初始化"""
        assert self.crawler is not None
        assert hasattr(self.crawler, 'price_crawler')
        assert hasattr(self.crawler, 'financial_crawler')
        assert isinstance(self.crawler.price_crawler, TwsePriceCrawler)
        assert isinstance(self.crawler.financial_crawler, TwseFinancialCrawler)

    def test_initialization_with_custom_delay(self):
        """測試使用自定義延遲初始化"""
        crawler = TWSECrawler(delay=2.0)
        assert crawler.delay == 2.0
        assert crawler.price_crawler.delay == 2.0
        assert crawler.financial_crawler.delay == 2.0

    @patch.object(TwsePriceCrawler, 'get_benchmark_data')
    def test_crawl_benchmark(self, mock_get_benchmark):
        """測試爬取大盤指數"""
        mock_df = pd.DataFrame({'test': ['data']})
        mock_get_benchmark.return_value = mock_df
        
        test_date = date(2024, 1, 15)
        result = self.crawler.crawl_benchmark(test_date)
        
        assert result.equals(mock_df)
        mock_get_benchmark.assert_called_once_with(test_date)

    @patch.object(TwsePriceCrawler, 'get_twe_prices')
    def test_price_twe(self, mock_get_prices):
        """測試爬取上市股價"""
        mock_df = pd.DataFrame({'test': ['data']})
        mock_get_prices.return_value = mock_df
        
        test_date = date(2024, 1, 15)
        result = self.crawler.price_twe(test_date)
        
        assert result.equals(mock_df)
        mock_get_prices.assert_called_once_with(test_date)

    @patch.object(TwseFinancialCrawler, 'get_monthly_revenue')
    def test_month_revenue(self, mock_get_revenue):
        """測試爬取月營收"""
        mock_df = pd.DataFrame({'test': ['data']})
        mock_get_revenue.return_value = mock_df
        
        test_date = date(2024, 1, 15)
        result = self.crawler.month_revenue('2330', test_date)
        
        assert result.equals(mock_df)
        mock_get_revenue.assert_called_once_with(test_date, '2330')

    @patch.object(TwseFinancialCrawler, 'get_financial_statement')
    def test_crawl_finance_statement(self, mock_get_statement):
        """測試爬取財務報表"""
        mock_df = pd.DataFrame({'test': ['data']})
        mock_get_statement.return_value = mock_df
        
        result = self.crawler.crawl_finance_statement(2024, 1)
        
        assert result.equals(mock_df)
        mock_get_statement.assert_called_once_with(2024, 1)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
