"""
測試風險值 (VaR) 計算模組

此模組測試 VaR 和 CVaR 計算功能，包括歷史模擬法、參數法和蒙特卡洛模擬法。
"""

import os
import sys
import unittest
from unittest.mock import patch
import numpy as np
import pandas as pd

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.risk_management.var_calculator import ValueAtRisk, ConditionalValueAtRisk


class TestValueAtRisk(unittest.TestCase):
    """測試風險值計算器"""

    def setUp(self):
        """設置測試環境"""
        # 創建測試收益率資料
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        # 創建三個資產的收益率資料
        self.returns = pd.DataFrame({
            'AAPL': np.random.normal(0.001, 0.02, 100),  # 平均收益率 0.1%, 波動率 2%
            'GOOGL': np.random.normal(0.0005, 0.025, 100),  # 平均收益率 0.05%, 波動率 2.5%
            'MSFT': np.random.normal(0.0008, 0.018, 100)   # 平均收益率 0.08%, 波動率 1.8%
        }, index=dates)

        # 創建權重
        self.weights = {'AAPL': 0.4, 'GOOGL': 0.35, 'MSFT': 0.25}

        # 創建 VaR 計算器
        self.var_calculator = ValueAtRisk(self.returns, self.weights)

    def test_initialization_with_weights(self):
        """測試帶權重的初始化"""
        calculator = ValueAtRisk(self.returns, self.weights)

        # 檢查權重是否正確設置
        self.assertEqual(calculator.weights, self.weights)

        # 檢查收益率資料
        pd.testing.assert_frame_equal(calculator.returns, self.returns)

    def test_initialization_without_weights(self):
        """測試不帶權重的初始化（等權重）"""
        calculator = ValueAtRisk(self.returns)

        # 檢查是否使用等權重
        expected_weight = 1.0 / len(self.returns.columns)
        for asset in self.returns.columns:
            self.assertAlmostEqual(calculator.weights[asset], expected_weight, places=6)

    def test_weight_normalization(self):
        """測試權重正規化"""
        # 創建權重和不為1的權重
        unnormalized_weights = {'AAPL': 0.8, 'GOOGL': 0.7, 'MSFT': 0.5}
        calculator = ValueAtRisk(self.returns, unnormalized_weights)

        # 檢查權重是否被正規化
        total_weight = sum(calculator.weights.values())
        self.assertAlmostEqual(total_weight, 1.0, places=6)

        # 檢查權重比例是否保持
        original_total = sum(unnormalized_weights.values())
        for asset in unnormalized_weights:
            expected_weight = unnormalized_weights[asset] / original_total
            self.assertAlmostEqual(calculator.weights[asset], expected_weight, places=6)

    def test_calculate_portfolio_returns(self):
        """測試投資組合收益率計算"""
        portfolio_returns = self.var_calculator._calculate_portfolio_returns()

        # 檢查返回類型
        self.assertIsInstance(portfolio_returns, pd.Series)

        # 檢查長度
        self.assertEqual(len(portfolio_returns), len(self.returns))

        # 檢查索引
        pd.testing.assert_index_equal(portfolio_returns.index, self.returns.index)

        # 手動計算第一個值進行驗證
        expected_first_return = (
            self.returns.iloc[0]['AAPL'] * self.weights['AAPL'] +
            self.returns.iloc[0]['GOOGL'] * self.weights['GOOGL'] +
            self.returns.iloc[0]['MSFT'] * self.weights['MSFT']
        )
        self.assertAlmostEqual(portfolio_returns.iloc[0], expected_first_return, places=6)

    def test_calculate_var_historical(self):
        """測試歷史模擬法 VaR 計算"""
        # 測試不同置信水平
        confidence_levels = [0.90, 0.95, 0.99]

        for confidence in confidence_levels:
            var = self.var_calculator.calculate_var_historical(confidence)

            # 檢查返回值類型
            self.assertIsInstance(var, float)

            # 檢查 VaR 為正值
            self.assertGreater(var, 0)

            # 檢查置信水平越高，VaR 越大
            if confidence > 0.90:
                var_90 = self.var_calculator.calculate_var_historical(0.90)
                self.assertGreaterEqual(var, var_90)

    def test_calculate_var_parametric(self):
        """測試參數法 VaR 計算"""
        var = self.var_calculator.calculate_var_parametric(0.95)

        # 檢查返回值類型
        self.assertIsInstance(var, float)

        # 檢查 VaR 為正值
        self.assertGreater(var, 0)

        # 檢查不同置信水平的結果
        var_90 = self.var_calculator.calculate_var_parametric(0.90)
        var_99 = self.var_calculator.calculate_var_parametric(0.99)

        # 置信水平越高，VaR 應該越大
        self.assertLess(var_90, var)
        self.assertLess(var, var_99)

    @patch('numpy.random.normal')
    def test_calculate_var_monte_carlo(self, mock_random):
        """測試蒙特卡洛模擬法 VaR 計算"""
        # 設置模擬的隨機數
        mock_random.return_value = np.array([-0.05, -0.03, -0.01, 0.01, 0.03] * 2000)

        var = self.var_calculator.calculate_var_monte_carlo(0.95, 10000)

        # 檢查返回值類型
        self.assertIsInstance(var, float)

        # 檢查 VaR 為正值
        self.assertGreater(var, 0)

        # 檢查是否調用了隨機數生成
        self.assertTrue(mock_random.called)

    def test_var_methods_consistency(self):
        """測試不同 VaR 計算方法的一致性"""
        confidence = 0.95

        var_hist = self.var_calculator.calculate_var_historical(confidence)
        var_param = self.var_calculator.calculate_var_parametric(confidence)
        var_mc = self.var_calculator.calculate_var_monte_carlo(confidence, 10000)

        # 所有方法都應該返回正值
        self.assertGreater(var_hist, 0)
        self.assertGreater(var_param, 0)
        self.assertGreater(var_mc, 0)

        # 結果應該在合理範圍內（不應該相差太大）
        methods = [var_hist, var_param, var_mc]
        max_var = max(methods)
        min_var = min(methods)

        # 最大值不應該超過最小值的5倍（合理性檢查）
        self.assertLess(max_var / min_var, 5.0)


class TestConditionalValueAtRisk(unittest.TestCase):
    """測試條件風險值計算器"""

    def setUp(self):
        """設置測試環境"""
        # 創建測試收益率資料
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')

        self.returns = pd.DataFrame({
            'AAPL': np.random.normal(0.001, 0.02, 100),
            'GOOGL': np.random.normal(0.0005, 0.025, 100),
            'MSFT': np.random.normal(0.0008, 0.018, 100)
        }, index=dates)

        self.weights = {'AAPL': 0.4, 'GOOGL': 0.35, 'MSFT': 0.25}

        # 創建 CVaR 計算器
        self.cvar_calculator = ConditionalValueAtRisk(self.returns, self.weights)

    def test_initialization(self):
        """測試初始化"""
        calculator = ConditionalValueAtRisk(self.returns, self.weights)

        # 檢查權重設置
        self.assertEqual(calculator.weights, self.weights)

        # 檢查是否創建了 VaR 計算器
        self.assertIsInstance(calculator.var_calculator, ValueAtRisk)

    def test_calculate_cvar_historical(self):
        """測試歷史模擬法 CVaR 計算"""
        cvar = self.cvar_calculator.calculate_cvar_historical(0.95)

        # 檢查返回值類型
        self.assertIsInstance(cvar, float)

        # 檢查 CVaR 為正值
        self.assertGreater(cvar, 0)

        # CVaR 應該大於或等於 VaR
        var = self.cvar_calculator.var_calculator.calculate_var_historical(0.95)
        self.assertGreaterEqual(cvar, var)

    def test_calculate_cvar_parametric(self):
        """測試參數法 CVaR 計算"""
        cvar = self.cvar_calculator.calculate_cvar_parametric(0.95)

        # 檢查返回值類型
        self.assertIsInstance(cvar, float)

        # 檢查 CVaR 為正值
        self.assertGreater(cvar, 0)

    def test_cvar_confidence_levels(self):
        """測試不同置信水平的 CVaR"""
        confidence_levels = [0.90, 0.95, 0.99]
        cvars = []

        for confidence in confidence_levels:
            cvar = self.cvar_calculator.calculate_cvar_historical(confidence)
            cvars.append(cvar)

            # 檢查 CVaR 為正值
            self.assertGreater(cvar, 0)

        # 置信水平越高，CVaR 應該越大
        for i in range(1, len(cvars)):
            self.assertGreaterEqual(cvars[i], cvars[i-1])

    def test_portfolio_returns_calculation(self):
        """測試投資組合收益率計算"""
        portfolio_returns = self.cvar_calculator._calculate_portfolio_returns()

        # 檢查返回類型
        self.assertIsInstance(portfolio_returns, pd.Series)

        # 檢查長度
        self.assertEqual(len(portfolio_returns), len(self.returns))


class TestEdgeCases(unittest.TestCase):
    """測試邊界條件"""

    def test_single_asset(self):
        """測試單一資產的情況"""
        # 創建單一資產的收益率資料
        returns = pd.DataFrame({
            'AAPL': np.random.normal(0.001, 0.02, 50)
        })

        calculator = ValueAtRisk(returns)
        var = calculator.calculate_var_historical(0.95)

        # 應該能正常計算
        self.assertIsInstance(var, float)
        self.assertGreater(var, 0)

    def test_zero_weights(self):
        """測試零權重的情況"""
        returns = pd.DataFrame({
            'AAPL': np.random.normal(0.001, 0.02, 50),
            'GOOGL': np.random.normal(0.0005, 0.025, 50)
        })

        # 權重和為0的情況
        weights = {'AAPL': 0.0, 'GOOGL': 0.0}
        calculator = ValueAtRisk(returns, weights)

        # 應該使用原始權重（不進行正規化）
        self.assertEqual(calculator.weights, weights)

    def test_missing_assets_in_weights(self):
        """測試權重中包含不存在的資產"""
        returns = pd.DataFrame({
            'AAPL': np.random.normal(0.001, 0.02, 50),
            'GOOGL': np.random.normal(0.0005, 0.025, 50)
        })

        # 權重包含不存在的資產
        weights = {'AAPL': 0.5, 'GOOGL': 0.3, 'TSLA': 0.2}
        calculator = ValueAtRisk(returns, weights)

        # 計算投資組合收益率時應該忽略不存在的資產
        portfolio_returns = calculator._calculate_portfolio_returns()
        self.assertIsInstance(portfolio_returns, pd.Series)


if __name__ == '__main__':
    unittest.main()
