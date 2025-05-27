"""
測試動量策略模組

此模組測試動量策略的功能，包括訊號生成、參數驗證和邊界條件。
"""

import os
import sys
import unittest
import numpy as np
import pandas as pd
import pytest

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.strategy.momentum import MomentumStrategy
from src.strategy.base import ParameterError, DataValidationError


class TestMomentumStrategy(unittest.TestCase):
    """測試動量策略"""

    def setUp(self):
        """設置測試環境"""
        # 創建測試資料
        self.test_data = pd.DataFrame({
            'Close': [100, 102, 101, 105, 107, 106, 110, 108, 112, 115],
            '收盤價': [100, 102, 101, 105, 107, 106, 110, 108, 112, 115],
            'Volume': [1000, 1100, 950, 1200, 1300, 1150, 1400, 1250, 1500, 1600]
        })

        # 創建上升趨勢資料
        self.uptrend_data = pd.DataFrame({
            'Close': [100, 102, 104, 106, 108, 110, 112, 114, 116, 118]
        })

        # 創建下降趨勢資料
        self.downtrend_data = pd.DataFrame({
            'Close': [118, 116, 114, 112, 110, 108, 106, 104, 102, 100]
        })

        # 創建測試策略
        self.strategy = MomentumStrategy(window=5)

    def test_strategy_initialization(self):
        """測試策略初始化"""
        # 測試預設參數
        strategy = MomentumStrategy()
        self.assertEqual(strategy.name, "Momentum")
        self.assertEqual(strategy.window, 20)
        self.assertEqual(strategy.parameters["window"], 20)

        # 測試自定義參數
        strategy = MomentumStrategy(window=10)
        self.assertEqual(strategy.window, 10)
        self.assertEqual(strategy.parameters["window"], 10)

        # 測試額外參數
        strategy = MomentumStrategy(window=15, extra_param="test")
        self.assertEqual(strategy.window, 15)
        self.assertEqual(strategy.parameters["extra_param"], "test")

    def test_parameter_validation(self):
        """測試參數驗證"""
        # 測試正常參數
        strategy = MomentumStrategy(window=10)
        self.assertEqual(strategy.window, 10)

        # 測試無效參數：零
        with pytest.raises(ParameterError, match="window 必須是正整數"):
            MomentumStrategy(window=0)

        # 測試無效參數：負數
        with pytest.raises(ParameterError, match="window 必須是正整數"):
            MomentumStrategy(window=-5)

        # 測試無效參數：非整數
        with pytest.raises(ParameterError, match="window 必須是正整數"):
            MomentumStrategy(window=10.5)

        # 測試無效參數：字串
        with pytest.raises(ParameterError, match="window 必須是正整數"):
            MomentumStrategy(window="10")

    def test_generate_signals_with_close_column(self):
        """測試使用 Close 欄位生成訊號"""
        signals = self.strategy.generate_signals(self.test_data)

        # 檢查訊號資料框架結構
        self.assertIsInstance(signals, pd.DataFrame)
        expected_columns = ['momentum_ma', 'signal', 'position_change', 'buy_signal', 'sell_signal']
        for col in expected_columns:
            self.assertIn(col, signals.columns)

        # 檢查資料長度
        self.assertEqual(len(signals), len(self.test_data))

        # 檢查移動平均線計算
        self.assertIsNotNone(signals['momentum_ma'].iloc[-1])

        # 檢查訊號值範圍
        self.assertTrue(all(signals['signal'].isin([-1, 0, 1])))
        self.assertTrue(all(signals['buy_signal'].isin([0, 1])))
        self.assertTrue(all(signals['sell_signal'].isin([0, 1])))

    def test_generate_signals_with_chinese_column(self):
        """測試使用中文欄位名稱生成訊號"""
        chinese_data = self.test_data[['收盤價', 'Volume']].copy()
        signals = self.strategy.generate_signals(chinese_data)

        # 檢查基本結構
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertEqual(len(signals), len(chinese_data))

        # 檢查訊號生成
        self.assertIn('signal', signals.columns)
        self.assertIn('momentum_ma', signals.columns)

    def test_generate_signals_uptrend(self):
        """測試上升趨勢中的訊號生成"""
        signals = self.strategy.generate_signals(self.uptrend_data)

        # 在明顯上升趨勢中，應該有買入訊號
        self.assertTrue(signals['buy_signal'].sum() > 0)

        # 檢查最後幾個訊號應該是正的（買入）
        last_signals = signals['signal'].iloc[-3:].dropna()
        if len(last_signals) > 0:
            self.assertTrue(all(last_signals >= 0))

    def test_generate_signals_downtrend(self):
        """測試下降趨勢中的訊號生成"""
        signals = self.strategy.generate_signals(self.downtrend_data)

        # 在明顯下降趨勢中，應該有賣出訊號
        self.assertTrue(signals['sell_signal'].sum() > 0)

        # 檢查最後幾個訊號應該是負的（賣出）
        last_signals = signals['signal'].iloc[-3:].dropna()
        if len(last_signals) > 0:
            self.assertTrue(all(last_signals <= 0))

    def test_data_validation_errors(self):
        """測試資料驗證錯誤"""
        # 測試缺少必要欄位
        invalid_data = pd.DataFrame({'Volume': [1000, 1100, 1200]})
        with pytest.raises(DataValidationError, match="資料必須包含 'Close' 或 '收盤價' 欄位"):
            self.strategy.generate_signals(invalid_data)

        # 測試空資料
        empty_data = pd.DataFrame()
        with pytest.raises(DataValidationError):
            self.strategy.generate_signals(empty_data)

    def test_signal_consistency(self):
        """測試訊號一致性"""
        signals = self.strategy.generate_signals(self.test_data)

        # 買入和賣出訊號不應該同時出現
        simultaneous_signals = (signals['buy_signal'] == 1) & (signals['sell_signal'] == 1)
        self.assertFalse(simultaneous_signals.any())

        # 檢查訊號變化的邏輯
        for i in range(1, len(signals)):
            if signals['buy_signal'].iloc[i] == 1:
                # 買入訊號應該對應正的主訊號
                self.assertEqual(signals['signal'].iloc[i], 1)

            if signals['sell_signal'].iloc[i] == 1:
                # 賣出訊號應該對應負的主訊號
                self.assertEqual(signals['signal'].iloc[i], -1)

    def test_moving_average_calculation(self):
        """測試移動平均線計算"""
        # 使用簡單的測試資料
        simple_data = pd.DataFrame({'Close': [10, 20, 30, 40, 50]})
        strategy = MomentumStrategy(window=3)
        signals = strategy.generate_signals(simple_data)

        # 檢查移動平均線計算（忽略NaN填充的差異）
        expected_ma = simple_data['Close'].rolling(window=3).mean()
        # 只比較非NaN的值
        mask = ~expected_ma.isna()
        pd.testing.assert_series_equal(
            signals['momentum_ma'][mask],
            expected_ma[mask],
            check_names=False
        )

    def test_get_default_param_grid(self):
        """測試獲取預設參數網格"""
        param_grid = self.strategy._get_default_param_grid()

        # 檢查參數網格結構
        self.assertIsInstance(param_grid, dict)
        self.assertIn('window', param_grid)
        self.assertIsInstance(param_grid['window'], list)

        # 檢查參數值
        expected_windows = [10, 15, 20, 25, 30, 50]
        self.assertEqual(param_grid['window'], expected_windows)

    def test_edge_cases(self):
        """測試邊界條件"""
        # 測試窗口大小等於資料長度
        small_data = pd.DataFrame({'Close': [100, 101, 102]})
        strategy = MomentumStrategy(window=3)
        signals = strategy.generate_signals(small_data)

        # 應該能正常生成訊號，即使前面的值是NaN
        self.assertEqual(len(signals), len(small_data))

        # 測試窗口大小大於資料長度
        strategy = MomentumStrategy(window=5)
        signals = strategy.generate_signals(small_data)

        # 由於fillna(0)的處理，移動平均線被填充為0，訊號也應該為0
        self.assertTrue(all(signals['momentum_ma'] == 0))
        self.assertTrue(all(signals['signal'] == 0))

    def test_nan_handling(self):
        """測試NaN值處理"""
        # 創建包含NaN的資料
        nan_data = pd.DataFrame({
            'Close': [100, np.nan, 102, 103, np.nan, 105]
        })

        signals = self.strategy.generate_signals(nan_data)

        # 檢查NaN值被正確處理
        self.assertFalse(signals['signal'].isna().any())
        self.assertFalse(signals['buy_signal'].isna().any())
        self.assertFalse(signals['sell_signal'].isna().any())


if __name__ == '__main__':
    unittest.main()
