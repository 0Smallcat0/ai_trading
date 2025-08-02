# -*- coding: utf-8 -*-
"""
AI 模型整合組件測試

測試 AI 模型整合的核心功能，包括：
- 模型管理器功能
- 訊號生成器功能
- 推論管道功能
- 錯誤處理機制
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
import tempfile
import os

# 設定測試環境路徑
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from core.model_integration import (
    ModelManager,
    ModelLoadError,
    ModelPredictionError,
    ModelHealthCheckError,
)
from core.signal_generators.ai_model_signals import AIModelSignalGenerator


class TestModelManager(unittest.TestCase):
    """測試模型管理器"""

    def setUp(self):
        """設置測試環境"""
        self.mock_registry = Mock()
        self.manager = ModelManager(
            model_registry=self.mock_registry, cache_size=5, batch_size=10
        )

    def tearDown(self):
        """清理測試環境"""
        if hasattr(self.manager, "shutdown"):
            self.manager.shutdown()

    def test_model_manager_initialization(self):
        """測試模型管理器初始化"""
        self.assertIsNotNone(self.manager.model_registry)
        self.assertEqual(self.manager.cache_size, 5)
        self.assertEqual(self.manager.batch_size, 10)
        self.assertIsInstance(self.manager.model_cache, dict)
        self.assertIsInstance(self.manager.model_health, dict)

    def test_list_models(self):
        """測試獲取模型列表"""
        expected_models = ["model1", "model2", "model3"]
        self.mock_registry.list_models.return_value = expected_models

        result = self.manager.list_models()

        self.assertEqual(result, expected_models)
        self.mock_registry.list_models.assert_called_once()

    def test_get_model_performance(self):
        """測試獲取模型性能指標"""
        model_name = "test_model"
        mock_info = {"performance_metrics": {"accuracy": 0.85, "precision": 0.80}}
        self.mock_registry.get_model_info.return_value = mock_info

        result = self.manager.get_model_performance(model_name)

        self.assertEqual(result["accuracy"], 0.85)
        self.assertEqual(result["precision"], 0.80)
        self.assertIn("recall", result)  # 應該有預設值
        self.assertIn("f1_score", result)

    def test_get_model_performance_error_handling(self):
        """測試模型性能指標獲取錯誤處理"""
        model_name = "nonexistent_model"
        self.mock_registry.get_model_info.side_effect = Exception("Model not found")

        result = self.manager.get_model_performance(model_name)

        # 應該返回預設值
        self.assertEqual(result["accuracy"], 0.5)
        self.assertEqual(result["precision"], 0.5)

    @patch("core.model_integration.InferencePipeline")
    def test_load_model_success(self, mock_pipeline):
        """測試成功載入模型"""
        model_name = "test_model"
        mock_model = Mock()
        mock_model.feature_names = ["feature1", "feature2"]
        self.mock_registry.load_model.return_value = mock_model

        result = self.manager.load_model(model_name)

        self.assertTrue(result)
        self.assertIn(f"{model_name}_latest", self.manager.model_cache)
        self.assertIn(model_name, self.manager.model_health)
        self.assertEqual(self.manager.model_health[model_name]["status"], "healthy")

    def test_load_model_failure(self):
        """測試模型載入失敗"""
        model_name = "failing_model"
        self.mock_registry.load_model.side_effect = Exception("Load failed")

        with self.assertRaises(ModelLoadError):
            self.manager.load_model(model_name)

    def test_predict_single(self):
        """測試單次預測"""
        model_name = "test_model"
        test_data = pd.DataFrame({"feature1": [1.0], "feature2": [2.0]})

        # 模擬預測結果
        with patch.object(self.manager, "predict") as mock_predict:
            mock_predict.return_value = np.array([0.75])

            result = self.manager.predict_single(model_name, test_data)

            self.assertEqual(result, 0.75)
            mock_predict.assert_called_once_with(test_data, model_name)

    def test_predict_single_empty_result(self):
        """測試單次預測空結果"""
        model_name = "test_model"
        test_data = pd.DataFrame({"feature1": [1.0]})

        with patch.object(self.manager, "predict") as mock_predict:
            mock_predict.return_value = np.array([])

            result = self.manager.predict_single(model_name, test_data)

            self.assertEqual(result, 0.0)

    def test_shutdown(self):
        """測試優雅關閉"""
        # 添加一些測試數據
        self.manager.model_cache["test"] = Mock()
        self.manager.model_health["test"] = {"status": "healthy"}

        self.manager.shutdown()

        self.assertEqual(len(self.manager.model_cache), 0)
        self.assertEqual(len(self.manager.model_health), 0)
        self.assertTrue(self.manager._shutdown_flag.is_set())


class TestAIModelSignalGenerator(unittest.TestCase):
    """測試 AI 模型訊號生成器"""

    def setUp(self):
        """設置測試環境"""
        # 創建測試價格數據
        dates = pd.date_range("2023-01-01", periods=50, freq="D")
        self.price_data = pd.DataFrame(
            {
                "close": np.random.randn(50).cumsum() + 100,
                "high": np.random.randn(50).cumsum() + 105,
                "low": np.random.randn(50).cumsum() + 95,
                "volume": np.random.randint(1000, 10000, 50),
            },
            index=dates,
        )

        # 創建模擬的模型管理器
        self.mock_model_manager = Mock()

        # 創建訊號生成器
        self.signal_generator = AIModelSignalGenerator(price_data=self.price_data)
        self.signal_generator.model_manager = self.mock_model_manager

    def test_generate_signals_success(self):
        """測試成功生成訊號"""
        model_name = "test_model"

        # 模擬模型預測結果
        predictions = np.array([0.8, -0.6, 0.3, -0.9, 0.1])
        self.mock_model_manager.predict.return_value = predictions

        with patch.object(self.signal_generator, "_prepare_features") as mock_prepare:
            mock_features = pd.DataFrame(
                {
                    "close": [100, 101, 102, 103, 104],
                    "high": [105, 106, 107, 108, 109],
                    "low": [95, 96, 97, 98, 99],
                },
                index=self.price_data.index[:5],
            )
            mock_prepare.return_value = mock_features

            signals = self.signal_generator.generate_signals(
                model_name=model_name, confidence_threshold=0.5
            )

            self.assertIsInstance(signals, pd.DataFrame)
            self.assertIn("signal", signals.columns)
            self.assertIn("confidence", signals.columns)

            # 檢查訊號邏輯
            # 0.8 > 0.5 且 > 0.1 應該是買入訊號 (1)
            # -0.6 < -0.1 且 abs(-0.6) > 0.5 應該是賣出訊號 (-1)

    def test_generate_signals_no_model_manager(self):
        """測試沒有模型管理器時的處理"""
        signal_generator = AIModelSignalGenerator(price_data=self.price_data)
        signal_generator.model_manager = None

        signals = signal_generator.generate_signals()

        self.assertTrue(signals.empty)

    def test_generate_ensemble_signals(self):
        """測試集成模型訊號生成"""
        model_names = ["model1", "model2", "model3"]

        # 模擬多個模型的預測結果
        predictions1 = np.array([0.8, -0.6, 0.3])
        predictions2 = np.array([0.7, -0.5, 0.4])
        predictions3 = np.array([0.6, -0.7, 0.2])

        def mock_predict(features, model_name):
            if model_name == "model1":
                return predictions1
            elif model_name == "model2":
                return predictions2
            else:
                return predictions3

        self.mock_model_manager.predict.side_effect = mock_predict
        self.mock_model_manager.get_model_performance.return_value = {"accuracy": 0.8}

        with patch.object(self.signal_generator, "_prepare_features") as mock_prepare:
            mock_features = pd.DataFrame(
                {
                    "close": [100, 101, 102],
                    "high": [105, 106, 107],
                    "low": [95, 96, 97],
                },
                index=self.price_data.index[:3],
            )
            mock_prepare.return_value = mock_features

            signals = self.signal_generator.generate_ensemble_signals(
                model_names=model_names, voting_method="weighted"
            )

            self.assertIsInstance(signals, pd.DataFrame)
            self.assertIn("signal", signals.columns)
            self.assertIn("confidence", signals.columns)

    def test_prepare_features(self):
        """測試特徵準備"""
        # 模擬技術指標計算器
        mock_tech_indicators = Mock()
        mock_tech_indicators.calculate_sma.return_value = pd.Series(
            [100.5] * len(self.price_data)
        )
        mock_tech_indicators.calculate_rsi.return_value = pd.Series(
            [50.0] * len(self.price_data)
        )
        mock_tech_indicators.calculate_macd.return_value = (
            pd.Series([0.1] * len(self.price_data)),  # MACD
            pd.Series([0.05] * len(self.price_data)),  # Signal
            pd.Series([0.05] * len(self.price_data)),  # Histogram
        )

        self.signal_generator.tech_indicators = mock_tech_indicators

        features = self.signal_generator._prepare_features()

        self.assertIsInstance(features, pd.DataFrame)
        self.assertIn("close", features.columns)
        self.assertIn("high", features.columns)
        self.assertIn("low", features.columns)
        self.assertIn("sma_20", features.columns)
        self.assertIn("rsi_14", features.columns)
        self.assertIn("macd", features.columns)


if __name__ == "__main__":
    unittest.main()
