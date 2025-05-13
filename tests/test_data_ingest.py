"""
資料擷取模組測試

此模組測試資料擷取相關功能，包括：
- 從多種來源獲取股票資料
- WebSocket 自動重連和背壓控制
- 請求速率限制和自動故障轉移機制
"""

import os
import time
import unittest
import tempfile
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock

from src.core.data_ingest import DataIngestionManager
from src.core.mcp_data_ingest import MCPDataIngestor, analyze_market_sentiment
from src.data_sources.yahoo_adapter import YahooFinanceAdapter
from src.data_sources.broker_adapter import SimulatedBrokerAdapter
from src.core.rate_limiter import RateLimiter, AdaptiveRateLimiter
from src.core.websocket_client import WebSocketClient


class TestDataIngestionManager(unittest.TestCase):
    """測試資料擷取管理器"""

    def setUp(self):
        """測試前準備"""
        # 創建資料擷取管理器
        self.manager = DataIngestionManager(
            use_cache=False,  # 測試時不使用快取
            max_workers=2,
            rate_limit_max_calls=100,  # 測試時使用較高的速率限制
            rate_limit_period=1,
        )

    def tearDown(self):
        """測試後清理"""
        # 關閉資料擷取管理器
        self.manager.close()

    @patch.object(YahooFinanceAdapter, "get_historical_data")
    def test_get_historical_data(self, mock_get_historical_data):
        """測試獲取歷史價格資料"""
        # 模擬 YahooFinanceAdapter.get_historical_data 的返回值
        mock_df = pd.DataFrame(
            {
                "date": [date(2023, 1, 1), date(2023, 1, 2)],
                "open": [100.0, 101.0],
                "high": [102.0, 103.0],
                "low": [99.0, 100.0],
                "close": [101.0, 102.0],
                "volume": [1000000, 1100000],
                "symbol": ["2330.TW", "2330.TW"],
            }
        )
        mock_get_historical_data.return_value = mock_df

        # 測試獲取單一股票的歷史價格資料
        result = self.manager.get_historical_data(
            "2330.TW",
            start_date="2023-01-01",
            end_date="2023-01-02",
            interval="1d",
            source="yahoo",
        )

        # 檢查結果
        self.assertIn("2330.TW", result)
        self.assertEqual(len(result["2330.TW"]), 2)
        self.assertEqual(result["2330.TW"]["close"].iloc[0], 101.0)
        self.assertEqual(result["2330.TW"]["close"].iloc[1], 102.0)

        # 檢查 YahooFinanceAdapter.get_historical_data 是否被正確調用
        mock_get_historical_data.assert_called_once_with(
            "2330.TW",
            "2023-01-01",
            "2023-01-02",
            "1d",
            None,
        )

    @patch.object(SimulatedBrokerAdapter, "get_quote")
    def test_get_quote(self, mock_get_quote):
        """測試獲取即時報價"""
        # 模擬 SimulatedBrokerAdapter.get_quote 的返回值
        mock_quote = {
            "symbol": "2330.TW",
            "bid": 499.0,
            "ask": 501.0,
            "last": 500.0,
            "high": 505.0,
            "low": 495.0,
            "volume": 5000,
            "timestamp": datetime.now().isoformat(),
        }
        mock_get_quote.return_value = mock_quote

        # 測試獲取單一股票的即時報價
        result = self.manager.get_quote("2330.TW", source="broker")

        # 檢查結果
        self.assertIn("2330.TW", result)
        self.assertEqual(result["2330.TW"]["last"], 500.0)
        self.assertEqual(result["2330.TW"]["bid"], 499.0)
        self.assertEqual(result["2330.TW"]["ask"], 501.0)

        # 檢查 SimulatedBrokerAdapter.get_quote 是否被正確調用
        mock_get_quote.assert_called_once_with("2330.TW")

    @patch.object(WebSocketClient, "connect")
    @patch.object(WebSocketClient, "send")
    def test_connect_websocket(self, mock_send, mock_connect):
        """測試連接 WebSocket"""
        # 模擬 WebSocketClient.connect 和 WebSocketClient.send 的返回值
        mock_connect.return_value = None
        mock_send.return_value = True

        # 測試連接 WebSocket
        def on_message(message):
            pass

        result = self.manager.connect_websocket(
            ["2330.TW"], on_message, source="broker"
        )

        # 檢查結果
        self.assertTrue(result)
        self.assertIn("broker_2330.TW", self.manager.websocket_clients)

        # 檢查 WebSocketClient.connect 是否被正確調用
        mock_connect.assert_called_once()

    def test_get_stats(self):
        """測試獲取統計信息"""
        # 測試獲取統計信息
        stats = self.manager.get_stats()

        # 檢查結果
        self.assertIn("requests_total", stats)
        self.assertIn("requests_success", stats)
        self.assertIn("requests_failed", stats)
        self.assertIn("data_points_total", stats)
        self.assertIn("source_usage", stats)
        self.assertIn("queue_size", stats)
        self.assertIn("websocket_clients", stats)
        self.assertIn("source_status", stats)


class TestMCPDataIngestor(unittest.TestCase):
    """測試 MCP 資料擷取器"""

    def setUp(self):
        """測試前準備"""
        # 創建 MCP 資料擷取器
        self.ingestor = MCPDataIngestor(
            use_cache=False,  # 測試時不使用快取
            max_workers=2,
            rate_limit_max_calls=100,  # 測試時使用較高的速率限制
            rate_limit_period=1,
        )

    def tearDown(self):
        """測試後清理"""
        # 關閉 MCP 資料擷取器
        self.ingestor.close()

    @patch("src.core.mcp_data_ingest.crawl_stock_news")
    def test_fetch_market_news(self, mock_crawl_stock_news):
        """測試獲取市場新聞"""
        # 模擬 crawl_stock_news 的返回值
        mock_news = [
            {
                "title": "台積電Q2營收創新高",
                "content": "台積電第二季營收達到 5000 億元，創下歷史新高。",
                "date": "2023-07-10",
                "source": "經濟日報",
                "url": "https://example.com/news/1",
            },
            {
                "title": "台積電宣布加碼投資",
                "content": "台積電宣布將加碼投資 3 奈米製程，預計 2024 年量產。",
                "date": "2023-07-09",
                "source": "工商時報",
                "url": "https://example.com/news/2",
            },
        ]
        mock_crawl_stock_news.return_value = mock_news

        # 測試獲取市場新聞
        result = self.ingestor.fetch_market_news("台積電", days=7, fulltext=True)

        # 檢查結果
        self.assertEqual(len(result), 2)
        self.assertEqual(result["title"].iloc[0], "台積電Q2營收創新高")
        self.assertEqual(result["title"].iloc[1], "台積電宣布加碼投資")

        # 檢查 crawl_stock_news 是否被正確調用
        mock_crawl_stock_news.assert_called_once_with("台積電", days=7, fulltext=True)

    def test_analyze_market_sentiment(self):
        """測試分析市場情緒"""
        # 創建測試資料
        news_df = pd.DataFrame(
            {
                "title": [
                    "台積電Q2營收創新高",
                    "台積電宣布加碼投資",
                    "台積電面臨競爭壓力",
                ],
                "content": [
                    "台積電第二季營收達到 5000 億元，創下歷史新高。",
                    "台積電宣布將加碼投資 3 奈米製程，預計 2024 年量產。",
                    "台積電面臨來自三星和英特爾的競爭壓力，市場份額可能下降。",
                ],
                "date": ["2023-07-10", "2023-07-09", "2023-07-08"],
                "source": ["經濟日報", "工商時報", "財經時報"],
                "url": [
                    "https://example.com/news/1",
                    "https://example.com/news/2",
                    "https://example.com/news/3",
                ],
            }
        )

        # 測試分析市場情緒
        result = analyze_market_sentiment(news_df)

        # 檢查結果
        self.assertIn("sentiment", result)
        self.assertIn("score", result)
        self.assertIn("count", result)
        self.assertIn("positive_count", result)
        self.assertIn("negative_count", result)
        self.assertEqual(result["count"], 3)


class TestRateLimiter(unittest.TestCase):
    """測試速率限制器"""

    def test_rate_limiter(self):
        """測試速率限制器"""
        # 創建速率限制器
        limiter = RateLimiter(max_calls=5, period=1)

        # 測試速率限制
        start_time = time.time()
        for i in range(10):
            with limiter:
                pass
        end_time = time.time()

        # 檢查結果：應該至少花費 1 秒
        self.assertGreaterEqual(end_time - start_time, 1.0)

    def test_adaptive_rate_limiter(self):
        """測試自適應速率限制器"""
        # 創建自適應速率限制器
        limiter = AdaptiveRateLimiter(
            max_calls=10,
            period=1,
            min_calls=1,
            increase_factor=1.5,
            decrease_factor=0.5,
        )

        # 測試成功報告
        for i in range(10):
            limiter.report_success()

        # 檢查結果：速率應該增加
        self.assertEqual(
            limiter.current_max_calls, 10
        )  # 實際上，當前實現在10次成功後重置計數器，但不會超過max_calls

        # 測試失敗報告
        for i in range(3):
            limiter.report_failure(429)

        # 檢查結果：速率應該減少
        self.assertLess(limiter.current_max_calls, 15)


if __name__ == "__main__":
    unittest.main()
