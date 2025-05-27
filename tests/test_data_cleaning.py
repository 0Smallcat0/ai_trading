"""資料清理模組的單元測試

此模組包含對 src/core/data_cleaning.py 中各個類和函數的單元測試。
"""

import os
import sys
import unittest
import pandas as pd
from datetime import datetime, date, timedelta

# 添加專案根目錄到 Python 路徑
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 導入被測試的模組
from src.core.data_cleaning import (
    MissingValueHandler,
    OutlierHandler,
    PriceStandardizer,
    DataCleaningPipeline,
    clean_stock_data,
)


class TestMissingValueHandler(unittest.TestCase):
    """測試缺失值處理器"""def setUp(self):
        """設置測試環境"""# 創建測試資料
        self.df = pd.DataFrame(
            {
                "A": [1, 2, np.nan, 4, 5],
                "B": [np.nan, 2, 3, np.nan, 5],
                "C": [1, 2, 3, 4, 5],
            }
        )

    def test_interpolate(self):
        """測試插值填補"""handler = MissingValueHandler(method="interpolate")
        result = handler.fit_transform(self.df)

        # 檢查缺失值是否大部分被填補（第一個值可能無法插值）
        self.assertLessEqual(result.isna().sum().sum(), 1)

        # 檢查插值結果是否合理
        self.assertAlmostEqual(result.loc[2, "A"], 3.0)  # 1, 2, ?, 4, 5 -> 應該是 3

    def test_mean(self):
        """測試均值填補"""handler = MissingValueHandler(method="mean")
        result = handler.fit_transform(self.df)

        # 檢查是否所有缺失值都被填補
        self.assertEqual(result.isna().sum().sum(), 0)

        # 檢查均值填補結果
        self.assertAlmostEqual(result.loc[2, "A"], self.df["A"].mean())
        self.assertAlmostEqual(result.loc[0, "B"], self.df["B"].mean())

    def test_median(self):
        """測試中位數填補"""handler = MissingValueHandler(method="median")
        result = handler.fit_transform(self.df)

        # 檢查是否所有缺失值都被填補
        self.assertEqual(result.isna().sum().sum(), 0)

        # 檢查中位數填補結果
        self.assertAlmostEqual(result.loc[2, "A"], self.df["A"].median())
        self.assertAlmostEqual(result.loc[0, "B"], self.df["B"].median())

    def test_ffill(self):
        """測試前向填補"""handler = MissingValueHandler(method="ffill")
        result = handler.fit_transform(self.df)

        # 檢查前向填補結果
        self.assertTrue(np.isnan(result.loc[0, "B"]))  # 第一個值無法前向填補
        self.assertAlmostEqual(result.loc[2, "A"], 2.0)  # 應該使用前一個值 2

    def test_bfill(self):
        """測試後向填補"""handler = MissingValueHandler(method="bfill")
        result = handler.fit_transform(self.df)

        # 檢查後向填補結果
        self.assertAlmostEqual(result.loc[0, "B"], 2.0)  # 應該使用後一個值 2
        self.assertAlmostEqual(result.loc[2, "A"], 4.0)  # 應該使用後一個值 4


class TestOutlierHandler(unittest.TestCase):
    """測試異常值處理器"""def setUp(self):
        """設置測試環境"""# 創建測試資料
        np.random.seed(42)
        self.df = pd.DataFrame(
            {
                "A": np.random.normal(0, 1, 100),
                "B": np.random.normal(0, 1, 100),
                "C": np.random.normal(0, 1, 100),
            }
        )

        # 添加異常值
        self.df.loc[10, "A"] = 10.0  # 明顯的異常值
        self.df.loc[20, "B"] = -10.0  # 明顯的異常值

    def test_detect_outliers_zscore(self):
        """測試使用 Z-score 檢測異常值"""handler = OutlierHandler(detection_method="z-score", z_threshold=3.0)
        outliers = handler.detect_outliers(self.df)

        # 檢查是否檢測到已知的異常值
        self.assertTrue(outliers.loc[10, "A"])
        self.assertTrue(outliers.loc[20, "B"])

        # 檢查正常值是否被誤判為異常值
        normal_outliers = outliers.sum().sum() - 2  # 減去已知的 2 個異常值
        self.assertLessEqual(normal_outliers, 5)  # 誤判率應該很低

    def test_detect_outliers_iqr(self):
        """測試使用 IQR 檢測異常值"""handler = OutlierHandler(detection_method="iqr", iqr_multiplier=1.5)
        outliers = handler.detect_outliers(self.df)

        # 檢查是否檢測到已知的異常值
        self.assertTrue(outliers.loc[10, "A"])
        self.assertTrue(outliers.loc[20, "B"])

    def test_treat_outliers_clip(self):
        """測試使用截斷法處理異常值"""handler = OutlierHandler(detection_method="z-score", treatment_method="clip")
        result = handler.treat_outliers(self.df)

        # 檢查異常值是否被截斷
        self.assertLess(abs(result.loc[10, "A"]), 10.0)
        self.assertGreater(abs(result.loc[20, "B"]), -10.0)

    def test_treat_outliers_remove(self):
        """測試使用移除法處理異常值"""handler = OutlierHandler(detection_method="z-score", treatment_method="remove")
        result = handler.treat_outliers(self.df)

        # 檢查異常值是否被設為 NaN
        self.assertTrue(np.isnan(result.loc[10, "A"]))
        self.assertTrue(np.isnan(result.loc[20, "B"]))


class TestPriceStandardizer(unittest.TestCase):
    """測試價格標準化器"""def setUp(self):
        """設置測試環境"""# 創建測試資料
        self.df = pd.DataFrame(
            {
                "open": [100, 101, 102, 103, 104],
                "high": [105, 106, 107, 108, 109],
                "low": [95, 96, 97, 98, 99],
                "close": [102, 103, 104, 105, 106],
                "volume": [1000, 1100, 1200, 1300, 1400],
                "adj_close": [92, 93, 94, 95, 96],  # 假設調整因子為 0.9
            }
        )

    def test_standardize_prices_adj_close(self):
        """測試使用調整後收盤價邏輯標準化價格"""standardizer = PriceStandardizer(adjust_method="adj_close")
        result = standardizer.standardize_prices(self.df)

        # 檢查是否使用了調整後收盤價
        self.assertEqual(result["close"].iloc[0], 92)

        # 檢查其他價格是否按比例調整
        adj_factor = 92 / 102  # 第一個調整因子
        self.assertAlmostEqual(result["open"].iloc[0], 100 * adj_factor)
        self.assertAlmostEqual(result["high"].iloc[0], 105 * adj_factor)
        self.assertAlmostEqual(result["low"].iloc[0], 95 * adj_factor)

        # 檢查是否移除了 adj_close 欄位
        self.assertNotIn("adj_close", result.columns)

    def test_handle_stock_splits(self):
        """測試處理股票分割"""# 創建帶有日期索引的資料
        df = self.df.copy()
        df.index = pd.date_range(start="2023-01-01", periods=5, freq="D")

        # 定義分割事件
        split_events = {date(2023, 1, 3): 2.0}  # 2:1 分割

        standardizer = PriceStandardizer()
        result = standardizer.handle_stock_splits(df, split_events)

        # 檢查分割日期之前的價格是否被調整
        self.assertEqual(result["close"].iloc[0], df["close"].iloc[0] / 2.0)
        self.assertEqual(result["close"].iloc[1], df["close"].iloc[1] / 2.0)

        # 檢查分割日期之後的價格是否保持不變
        self.assertEqual(result["close"].iloc[3], df["close"].iloc[3])
        self.assertEqual(result["close"].iloc[4], df["close"].iloc[4])

        # 檢查成交量是否按相反方向調整
        self.assertEqual(result["volume"].iloc[0], df["volume"].iloc[0] * 2.0)


class TestDataCleaningPipeline(unittest.TestCase):
    """測試資料清理管道"""def setUp(self):
        """設置測試環境"""# 創建測試資料
        np.random.seed(42)
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")

        # 基本價格資料
        close = 100 + np.cumsum(np.random.normal(0, 1, 100))

        self.df = pd.DataFrame(
            {
                "open": close - np.random.uniform(0, 2, 100),
                "high": close + np.random.uniform(0, 2, 100),
                "low": close - np.random.uniform(0, 2, 100),
                "close": close,
                "volume": np.random.uniform(1000, 5000, 100),
                "adj_close": close * 0.9,
            },
            index=dates,
        )

        # 添加缺失值和異常值
        mask = np.random.random(self.df.shape) < 0.1
        self.df.mask(mask, inplace=True)

        # 逐列添加異常值
        for col in self.df.columns:
            # 隨機選擇 5% 的行添加異常值
            mask = np.random.random(len(self.df)) < 0.05
            # 計算異常值的大小
            factor = np.random.uniform(3, 5)
            # 添加異常值
            self.df.loc[mask, col] = (
                self.df.loc[mask, col] + factor * self.df[col].std()
            )

    def test_clean(self):
        """測試完整的清理流程"""pipeline = DataCleaningPipeline()
        result, report = pipeline.clean(self.df)

        # 檢查是否所有缺失值都被填補
        self.assertEqual(result.isna().sum().sum(), 0)

        # 檢查報告是否包含必要的資訊
        self.assertIn("original_shape", report)
        self.assertIn("missing_values_before", report)
        self.assertIn("outliers_detected", report)
        self.assertIn("processing_steps", report)
        self.assertIn("final_shape", report)

        # 檢查處理步驟是否按順序執行
        self.assertEqual(
            report["processing_steps"],
            ["missing_value_handling", "outlier_handling", "price_standardization"],
        )


class TestCleanStockData(unittest.TestCase):
    """測試清理股票資料的便捷函數"""def setUp(self):
        """設置測試環境"""# 創建測試資料
        np.random.seed(42)
        dates = pd.date_range(start="2023-01-01", periods=100, freq="D")

        # 基本價格資料
        close = 100 + np.cumsum(np.random.normal(0, 1, 100))

        self.df = pd.DataFrame(
            {
                "open": close - np.random.uniform(0, 2, 100),
                "high": close + np.random.uniform(0, 2, 100),
                "low": close - np.random.uniform(0, 2, 100),
                "close": close,
                "volume": np.random.uniform(1000, 5000, 100),
                "adj_close": close * 0.9,
            },
            index=dates,
        )

        # 添加缺失值和異常值
        mask = np.random.random(self.df.shape) < 0.1
        self.df.mask(mask, inplace=True)

        # 逐列添加異常值
        for col in self.df.columns:
            # 隨機選擇 5% 的行添加異常值
            mask = np.random.random(len(self.df)) < 0.05
            # 計算異常值的大小
            factor = np.random.uniform(3, 5)
            # 添加異常值
            self.df.loc[mask, col] = (
                self.df.loc[mask, col] + factor * self.df[col].std()
            )

    def test_clean_stock_data(self):
        """測試清理股票資料"""
        result = clean_stock_data(self.df)

        # 檢查是否所有缺失值都被填補
        self.assertEqual(result.isna().sum().sum(), 0)

        # 檢查是否使用了調整後收盤價
        self.assertNotIn("adj_close", result.columns)


if __name__ == "__main__":
    unittest.main()
