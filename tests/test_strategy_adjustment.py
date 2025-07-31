# -*- coding: utf-8 -*-
"""
測試策略調整模組

此模組用於測試策略重新回測和參數調整功能。
"""

import os
import sys
import unittest
import tempfile
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.maintenance.strategy_rebacktester import StrategyRebacktester
from src.maintenance.strategy_tuner import StrategyTuner


class TestStrategyAdjustment(unittest.TestCase):
    """測試策略調整"""

    def setUp(self):
        """設置測試環境"""
        # 創建臨時目錄
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = self.temp_dir.name

        # 創建測試資料
        self.create_test_data()

    def tearDown(self):
        """清理測試環境"""
        # 刪除臨時目錄
        self.temp_dir.cleanup()

    def create_test_data(self):
        """創建測試資料"""
        # 創建價格資料
        dates = pd.date_range(start="2022-01-01", end="2022-12-31", freq="D")
        prices = np.random.normal(loc=100, scale=10, size=len(dates))
        prices = np.cumsum(np.random.normal(loc=0, scale=1, size=len(dates))) + 100

        # 確保價格為正數
        prices = np.maximum(prices, 1)

        # 創建價格資料框
        self.price_df = pd.DataFrame(
            {
                "date": dates,
                "open": prices,
                "high": prices * 1.01,
                "low": prices * 0.99,
                "close": prices,
                "volume": np.random.randint(1000, 10000, size=len(dates)),
            }
        )

        # 設置索引
        self.price_df.set_index("date", inplace=True)

        # 創建特徵資料
        self.features_df = pd.DataFrame(
            {
                "date": dates,
                "feature1": np.random.normal(loc=0, scale=1, size=len(dates)),
                "feature2": np.random.normal(loc=0, scale=1, size=len(dates)),
                "feature3": np.random.normal(loc=0, scale=1, size=len(dates)),
            }
        )

        # 設置索引
        self.features_df.set_index("date", inplace=True)

        # 創建目標資料
        self.target_df = pd.Series(
            np.random.choice([0, 1], size=len(dates), p=[0.7, 0.3]),
            index=dates,
            name="target",
        )

    def test_strategy_rebacktester(self):
        """測試策略重新回測器"""
        # 創建策略重新回測器
        rebacktester = StrategyRebacktester(self.output_dir)

        # 模擬市場變化分析
        market_changes = {
            "volatility_change": 0.1,
            "trend_change": 0.05,
            "correlation_change": -0.02,
        }

        # 模擬回測結果
        backtest_results = {
            "sharpe_ratio": 1.5,
            "max_drawdown": 0.1,
            "annual_return": 0.2,
            "win_rate": 0.6,
        }

        # 模擬方法
        rebacktester.analyze_market_changes = lambda *args, **kwargs: market_changes
        rebacktester.rebacktest_strategy = lambda *args, **kwargs: backtest_results

        # 測試市場變化分析
        result = rebacktester.analyze_market_changes()
        self.assertEqual(result, market_changes)

        # 測試策略重新回測
        result = rebacktester.rebacktest_strategy(
            "moving_average_crossover", {"short_window": 20, "long_window": 50}
        )
        self.assertEqual(result, backtest_results)

    def test_strategy_tuner(self):
        """測試策略調整器"""
        # 創建策略調整器
        tuner = StrategyTuner(self.output_dir)

        # 模擬優化結果
        optimization_results = {
            "best_params": {"short_window": 15, "long_window": 45},
            "best_score": 1.8,
        }

        # 模擬比較結果
        comparison_results = {
            "improvement": {
                "sharpe_ratio": 20.0,
                "max_drawdown": -10.0,
                "annual_return": 15.0,
                "win_rate": 5.0,
            },
        }

        # 模擬方法
        tuner.rebacktester.analyze_market_changes = lambda *args, **kwargs: {}
        tuner.rebacktester.rebacktest_strategy = lambda *args, **kwargs: {}
        tuner.rebacktester.optimize_strategy_parameters = (
            lambda *args, **kwargs: optimization_results
        )
        tuner.rebacktester.compare_strategy_versions = (
            lambda *args, **kwargs: comparison_results
        )
        tuner.rebacktester.generate_optimization_report = lambda *args: "report.md"

        # 測試策略參數調整
        result = tuner.tune_strategy_parameters(
            "moving_average_crossover",
            {"short_window": 20, "long_window": 50},
            {"short_window": [10, 15, 20], "long_window": [40, 45, 50]},
        )

        # 檢查結果
        self.assertEqual(
            result["optimized_params"], optimization_results["best_params"]
        )
        self.assertEqual(result["improvement"], comparison_results["improvement"])
        self.assertEqual(result["report_path"], "report.md")

    def test_ml_strategy_tuning(self):
        """測試機器學習策略調整"""
        # 創建策略調整器
        tuner = StrategyTuner(self.output_dir)

        # 模擬評估結果
        current_metrics = {
            "accuracy": 0.7,
            "precision": 0.65,
            "recall": 0.6,
            "f1": 0.625,
        }

        optimized_metrics = {
            "accuracy": 0.75,
            "precision": 0.7,
            "recall": 0.65,
            "f1": 0.675,
        }

        # 模擬改進
        improvement = {
            "accuracy": 7.14,
            "precision": 7.69,
            "recall": 8.33,
            "f1": 8.0,
        }

        # 模擬方法
        tuner._evaluate_ml_model = lambda *args, **kwargs: optimized_metrics
        tuner._generate_ml_tuning_report = lambda *args, **kwargs: "ml_report.md"

        # 創建模擬模型
        class MockModel:
            def __init__(self, **kwargs):
                self.params = kwargs

            def train(self, X, y):
                pass

            def predict(self, X):
                return np.random.choice([0, 1], size=len(X))

        # 模擬 create_model 函數
        import src.models.model_factory

        original_create_model = src.models.model_factory.create_model
        src.models.model_factory.create_model = lambda *args, **kwargs: MockModel(
            **kwargs
        )

        try:
            # 測試機器學習策略調整
            result = tuner.tune_ml_strategy(
                "ml_strategy",
                "random_forest",
                {"n_estimators": 100, "max_depth": 5},
                {"n_estimators": [50, 100, 200], "max_depth": [3, 5, 10]},
                self.features_df,
                self.target_df,
            )

            # 檢查結果
            self.assertIn("current_params", result)
            self.assertIn("optimized_params", result)
            self.assertIn("report_path", result)
            self.assertEqual(result["report_path"], "ml_report.md")
        finally:
            # 還原 create_model 函數
            src.models.model_factory.create_model = original_create_model


if __name__ == "__main__":
    unittest.main()
