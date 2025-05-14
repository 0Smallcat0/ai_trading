"""
訊號產生模組測試

此模組測試訊號產生相關功能，包括：
- 基本面策略訊號生成
- 動量策略訊號生成
- 均值回歸策略訊號生成
- 新聞情緒策略訊號生成
- 突破策略訊號生成
- 交叉策略訊號生成
- 背離策略訊號生成
- 多策略訊號合併
"""

import os
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock

from src.core.signal_gen import SignalGenerator


class TestSignalGenerator(unittest.TestCase):
    """測試訊號產生器"""

    def setUp(self):
        """設置測試環境"""
        # 創建測試用的價格資料
        dates = pd.date_range(start="2023-01-01", end="2023-01-31")
        stock_ids = ["2330.TW", "2317.TW"]
        
        # 創建多層索引
        index = pd.MultiIndex.from_product(
            [stock_ids, dates], names=["stock_id", "date"]
        )
        
        # 創建價格資料
        np.random.seed(42)  # 設置隨機種子，確保結果可重現
        
        # 生成隨機價格
        n = len(index)
        price_data = pd.DataFrame(
            {
                "open": np.random.normal(500, 10, n),
                "high": np.random.normal(510, 10, n),
                "low": np.random.normal(490, 10, n),
                "close": np.random.normal(500, 10, n),
                "volume": np.random.normal(1000000, 100000, n),
            },
            index=index,
        )
        
        # 確保 high >= open >= close >= low
        for i in range(n):
            values = price_data.iloc[i]
            high = max(values["open"], values["close"]) + abs(np.random.normal(5, 1))
            low = min(values["open"], values["close"]) - abs(np.random.normal(5, 1))
            price_data.iloc[i, price_data.columns.get_loc("high")] = high
            price_data.iloc[i, price_data.columns.get_loc("low")] = low
        
        # 創建財務資料
        financial_data = pd.DataFrame(
            {
                "pe_ratio": np.random.normal(15, 5, n),
                "pb_ratio": np.random.normal(1.5, 0.5, n),
                "dividend_yield": np.random.normal(3.0, 1.0, n),
            },
            index=index,
        )
        
        # 創建新聞情緒資料
        news_data = pd.DataFrame(
            {
                "sentiment": np.random.normal(0, 1, n),
                "title": ["測試新聞" + str(i) for i in range(n)],
                "content": ["測試內容" + str(i) for i in range(n)],
            },
            index=index,
        )
        
        # 設置測試資料
        self.price_data = price_data
        self.financial_data = financial_data
        self.news_data = news_data
        
        # 創建訊號產生器
        self.signal_gen = SignalGenerator(
            price_data=price_data,
            financial_data=financial_data,
            news_data=news_data
        )

    def test_generate_basic(self):
        """測試生成基本面策略訊號"""
        signals = self.signal_gen.generate_basic()
        
        # 檢查結果
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertIn("signal", signals.columns)
        self.assertEqual(len(signals), len(self.financial_data))
        
        # 檢查訊號值是否合法
        self.assertTrue(all(signals["signal"].isin([-1, 0, 1])))
        
        # 檢查是否已儲存訊號
        self.assertIn("basic", self.signal_gen.signals)

    def test_generate_momentum(self):
        """測試生成動量策略訊號"""
        signals = self.signal_gen.generate_momentum()
        
        # 檢查結果
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertIn("signal", signals.columns)
        self.assertEqual(len(signals), len(self.price_data))
        
        # 檢查訊號值是否合法
        self.assertTrue(all(signals["signal"].isin([-1, 0, 1])))
        
        # 檢查是否已儲存訊號
        self.assertIn("momentum", self.signal_gen.signals)

    def test_generate_reversion(self):
        """測試生成均值回歸策略訊號"""
        signals = self.signal_gen.generate_reversion()
        
        # 檢查結果
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertIn("signal", signals.columns)
        self.assertEqual(len(signals), len(self.price_data))
        
        # 檢查訊號值是否合法
        self.assertTrue(all(signals["signal"].isin([-1, 0, 1])))
        
        # 檢查是否已儲存訊號
        self.assertIn("reversion", self.signal_gen.signals)

    def test_generate_sentiment(self):
        """測試生成新聞情緒策略訊號"""
        signals = self.signal_gen.generate_sentiment()
        
        # 檢查結果
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertIn("signal", signals.columns)
        self.assertEqual(len(signals), len(self.news_data))
        
        # 檢查訊號值是否合法
        self.assertTrue(all(signals["signal"].isin([-1, 0, 1])))
        
        # 檢查是否已儲存訊號
        self.assertIn("sentiment", self.signal_gen.signals)

    def test_generate_breakout_signals(self):
        """測試生成突破策略訊號"""
        signals = self.signal_gen.generate_breakout_signals()
        
        # 檢查結果
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertIn("signal", signals.columns)
        self.assertEqual(len(signals), len(self.price_data))
        
        # 檢查訊號值是否合法
        self.assertTrue(all(signals["signal"].isin([-1, 0, 1])))
        
        # 檢查是否已儲存訊號
        self.assertIn("breakout", self.signal_gen.signals)

    def test_generate_crossover_signals(self):
        """測試生成交叉策略訊號"""
        signals = self.signal_gen.generate_crossover_signals()
        
        # 檢查結果
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertIn("signal", signals.columns)
        self.assertEqual(len(signals), len(self.price_data))
        
        # 檢查訊號值是否合法
        self.assertTrue(all(signals["signal"].isin([-1, 0, 1])))
        
        # 檢查是否已儲存訊號
        self.assertIn("crossover", self.signal_gen.signals)

    def test_generate_divergence_signals(self):
        """測試生成背離策略訊號"""
        signals = self.signal_gen.generate_divergence_signals()
        
        # 檢查結果
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertIn("signal", signals.columns)
        self.assertEqual(len(signals), len(self.price_data))
        
        # 檢查訊號值是否合法
        self.assertTrue(all(signals["signal"].isin([-1, 0, 1])))
        
        # 檢查是否已儲存訊號
        self.assertIn("divergence", self.signal_gen.signals)

    def test_combine_signals(self):
        """測試合併多策略訊號"""
        # 先生成各種訊號
        self.signal_gen.generate_all_signals()
        
        # 合併訊號
        signals = self.signal_gen.combine_signals()
        
        # 檢查結果
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertIn("signal", signals.columns)
        
        # 檢查訊號值是否合法
        self.assertTrue(all(signals["signal"].isin([-1, 0, 1])))

    def test_export_signals_for_backtest(self):
        """測試匯出訊號以供回測使用"""
        # 先生成各種訊號
        self.signal_gen.generate_all_signals()
        
        # 匯出訊號
        backtest_signals = self.signal_gen.export_signals_for_backtest()
        
        # 檢查結果
        self.assertIsInstance(backtest_signals, pd.DataFrame)
        self.assertIn("buy_signal", backtest_signals.columns)
        self.assertIn("sell_signal", backtest_signals.columns)
        
        # 檢查訊號值是否合法
        self.assertTrue(all(backtest_signals["buy_signal"].isin([0, 1])))
        self.assertTrue(all(backtest_signals["sell_signal"].isin([0, 1])))


if __name__ == "__main__":
    unittest.main()
