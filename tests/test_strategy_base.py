"""
測試策略基礎模組

此模組測試策略基類和相關功能，確保策略框架的正確性。
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch
import numpy as np
import pandas as pd
import pytest

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.strategy.base import (
    Strategy,
    StrategyError,
    ParameterError,
    ModelNotTrainedError,
    DataValidationError,
)


class ConcreteTestStrategy(Strategy):
    """測試用的具體策略實現"""

    def __init__(self, name: str = "TestStrategy", **parameters):
        """
        初始化測試策略

        Args:
            name (str): 策略名稱
            **parameters: 策略參數
        """
        super().__init__(name, **parameters)

    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成簡單的測試訊號

        Args:
            data (pd.DataFrame): 輸入資料

        Returns:
            pd.DataFrame: 包含訊號的資料框架
        """
        signals = pd.DataFrame(index=data.index)
        signals["signal"] = 1  # 簡單的買入訊號
        signals["buy_signal"] = 1
        signals["sell_signal"] = 0
        return signals

    def _validate_parameters(self):
        """驗證測試策略參數"""
        if "invalid_param" in self.parameters:
            raise ParameterError("不允許使用 invalid_param 參數")


class TestStrategyExceptions(unittest.TestCase):
    """測試策略異常類別"""

    def test_strategy_error(self):
        """測試策略錯誤基類"""
        with pytest.raises(StrategyError):
            raise StrategyError("測試錯誤")

    def test_parameter_error(self):
        """測試參數錯誤"""
        with pytest.raises(ParameterError):
            raise ParameterError("參數錯誤")

        # 測試繼承關係
        self.assertTrue(issubclass(ParameterError, StrategyError))

    def test_model_not_trained_error(self):
        """測試模型未訓練錯誤"""
        with pytest.raises(ModelNotTrainedError):
            raise ModelNotTrainedError("模型未訓練")

        # 測試繼承關係
        self.assertTrue(issubclass(ModelNotTrainedError, StrategyError))

    def test_data_validation_error(self):
        """測試資料驗證錯誤"""
        with pytest.raises(DataValidationError):
            raise DataValidationError("資料驗證失敗")

        # 測試繼承關係
        self.assertTrue(issubclass(DataValidationError, StrategyError))


class TestStrategyBase(unittest.TestCase):
    """測試策略基類"""

    def setUp(self):
        """設置測試環境"""
        # 創建測試資料
        self.test_data = pd.DataFrame(
            {
                "收盤價": [100, 101, 102, 101, 103, 104, 102, 105],
                "開盤價": [99, 100, 101, 102, 102, 103, 104, 101],
                "最高價": [101, 102, 103, 103, 104, 105, 105, 106],
                "最低價": [98, 99, 100, 100, 101, 102, 101, 101],
            }
        )

        # 創建測試策略
        self.strategy = ConcreteTestStrategy(name="測試策略", param1=10, param2=0.5)

    def test_strategy_initialization(self):
        """測試策略初始化"""
        # 測試基本初始化
        strategy = ConcreteTestStrategy()
        self.assertEqual(strategy.name, "TestStrategy")
        self.assertEqual(strategy.parameters, {})

        # 測試帶參數初始化
        strategy = ConcreteTestStrategy(name="自定義策略", param1=20, param2=1.0)
        self.assertEqual(strategy.name, "自定義策略")
        self.assertEqual(strategy.parameters, {"param1": 20, "param2": 1.0})

    def test_parameter_validation(self):
        """測試參數驗證"""
        # 測試正常參數
        strategy = ConcreteTestStrategy(param1=10)
        self.assertEqual(strategy.parameters["param1"], 10)

        # 測試無效參數
        with pytest.raises(ParameterError):
            ConcreteTestStrategy(invalid_param=True)

    def test_generate_signals(self):
        """測試訊號生成"""
        signals = self.strategy.generate_signals(self.test_data)

        # 檢查訊號資料框架結構
        self.assertIsInstance(signals, pd.DataFrame)
        self.assertIn("signal", signals.columns)
        self.assertIn("buy_signal", signals.columns)
        self.assertIn("sell_signal", signals.columns)

        # 檢查訊號值
        self.assertTrue(all(signals["signal"] == 1))
        self.assertTrue(all(signals["buy_signal"] == 1))
        self.assertTrue(all(signals["sell_signal"] == 0))

    def test_price_data_validation(self):
        """測試價格資料驗證"""
        # 測試正常資料
        self.strategy._validate_price_data(self.test_data)

        # 測試缺少必要欄位
        invalid_data = pd.DataFrame({"開盤價": [100, 101, 102]})
        with pytest.raises(DataValidationError, match="價格資料缺少必要欄位"):
            self.strategy._validate_price_data(invalid_data)

        # 測試空資料
        empty_data = pd.DataFrame()
        with pytest.raises(DataValidationError):
            self.strategy._validate_price_data(empty_data)

    def test_signals_data_validation(self):
        """測試訊號資料驗證"""
        # 測試正常訊號資料
        valid_signals = pd.DataFrame({"signal": [1, -1, 0, 1]})
        self.strategy._validate_signals_data(valid_signals)

        # 測試缺少必要欄位
        invalid_signals = pd.DataFrame({"buy_signal": [1, 0, 1, 0]})
        with pytest.raises(DataValidationError, match="訊號資料缺少必要欄位"):
            self.strategy._validate_signals_data(invalid_signals)

    @patch("src.strategy.base.calculate_returns")
    @patch("src.strategy.base.calculate_total_return")
    @patch("src.strategy.base.calculate_sharpe_ratio")
    @patch("src.strategy.base.calculate_max_drawdown")
    @patch("src.strategy.base.calculate_win_rate")
    @patch("src.strategy.base.calculate_volatility")
    def test_evaluate(
        self,
        mock_volatility,
        mock_win_rate,
        mock_drawdown,
        mock_sharpe,
        mock_total_return,
        mock_returns,
    ):
        """測試策略評估"""
        # 設置模擬返回值
        mock_returns.return_value = pd.Series([0.01, -0.005, 0.02, 0.01])
        mock_total_return.return_value = 0.035
        mock_sharpe.return_value = 1.5
        mock_drawdown.return_value = -0.02
        mock_win_rate.return_value = 0.75
        mock_volatility.return_value = 0.15

        # 執行評估
        metrics = self.strategy.evaluate(self.test_data)

        # 檢查返回的指標
        expected_metrics = {
            "total_return": 0.035,
            "sharpe_ratio": 1.5,
            "max_drawdown": -0.02,
            "win_rate": 0.75,
            "volatility": 0.15,
        }

        self.assertEqual(metrics, expected_metrics)

        # 檢查函數調用
        mock_returns.assert_called_once()
        mock_total_return.assert_called_once()
        mock_sharpe.assert_called_once()
        mock_drawdown.assert_called_once()
        mock_win_rate.assert_called_once()
        mock_volatility.assert_called_once()

    def test_evaluate_with_custom_signals(self):
        """測試使用自定義訊號的評估"""
        custom_signals = pd.DataFrame(
            {
                "signal": [1, -1, 0, 1],
                "buy_signal": [1, 0, 0, 1],
                "sell_signal": [0, 1, 0, 0],
            }
        )

        with patch("src.strategy.base.calculate_returns") as mock_returns:
            mock_returns.return_value = pd.Series([0.01, -0.005, 0.02, 0.01])

            # 應該不會調用 generate_signals
            with patch.object(self.strategy, "generate_signals") as mock_generate:
                self.strategy.evaluate(self.test_data, custom_signals)
                mock_generate.assert_not_called()

    def test_optimize_parameters(self):
        """測試參數優化"""
        # 測試預設實現
        result = self.strategy.optimize_parameters(self.test_data)
        self.assertEqual(result, {})

        # 測試帶參數網格
        param_grid = {"param1": [5, 10, 15], "param2": [0.1, 0.5, 1.0]}
        result = self.strategy.optimize_parameters(
            self.test_data, param_grid=param_grid
        )
        self.assertEqual(result, {})

    def test_get_default_param_grid(self):
        """測試獲取預設參數網格"""
        param_grid = self.strategy._get_default_param_grid()
        self.assertEqual(param_grid, {})

    def test_string_representations(self):
        """測試字串表示方法"""
        # 測試 __str__
        str_repr = str(self.strategy)
        self.assertEqual(str_repr, "ConcreteTestStrategy(name='測試策略')")

        # 測試 __repr__
        repr_str = repr(self.strategy)
        expected_repr = (
            "ConcreteTestStrategy(name='測試策略', "
            "parameters={'param1': 10, 'param2': 0.5})"
        )
        self.assertEqual(repr_str, expected_repr)


if __name__ == "__main__":
    unittest.main()
