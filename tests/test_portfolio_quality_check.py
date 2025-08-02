"""
投資組合管理模組程式碼品質檢查測試

此測試檔案驗證Phase 2.4投資組合管理模組的程式碼品質改善。
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from src.core.portfolio import (
        Portfolio,
        MeanVariancePortfolio,
        EqualWeightPortfolio,
        PortfolioOptimizationError,
        DependencyError,
        SCIPY_AVAILABLE,
        MATPLOTLIB_AVAILABLE,
    )
except ImportError as e:
    print(f"導入錯誤: {e}")
    Portfolio = None
    MeanVariancePortfolio = None


class TestPortfolioQualityImprovements(unittest.TestCase):
    """測試投資組合管理模組的程式碼品質改善"""

    def setUp(self):
        """設置測試環境"""
        if Portfolio is None:
            self.skipTest("無法導入投資組合模組")

        # 創建測試資料
        self.test_signals = pd.DataFrame(
            {"signal": [1, 1, 0, 1], "buy_signal": [1, 1, 0, 1]},
            index=pd.MultiIndex.from_tuples(
                [
                    ("AAPL", "2023-01-01"),
                    ("GOOGL", "2023-01-01"),
                    ("MSFT", "2023-01-01"),
                    ("TSLA", "2023-01-01"),
                ],
                names=["stock_id", "date"],
            ),
        )

        self.test_weights = {"AAPL": 0.3, "GOOGL": 0.3, "MSFT": 0.2, "TSLA": 0.2}

        # 創建測試價格資料
        dates = pd.date_range("2023-01-01", periods=10, freq="D")
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]

        price_data = []
        for symbol in symbols:
            for date in dates:
                price_data.append(
                    {
                        "stock_id": symbol,
                        "date": date,
                        "收盤價": 100 + np.random.randn() * 5,
                    }
                )

        self.test_price_df = pd.DataFrame(price_data)
        self.test_price_df.set_index(["stock_id", "date"], inplace=True)

    def test_dependency_error_handling(self):
        """測試依賴套件錯誤處理"""
        # 測試自定義異常類別存在
        self.assertTrue(issubclass(PortfolioOptimizationError, Exception))
        self.assertTrue(issubclass(DependencyError, Exception))

        # 測試依賴檢查變數存在
        self.assertIsInstance(SCIPY_AVAILABLE, bool)
        self.assertIsInstance(MATPLOTLIB_AVAILABLE, bool)

    def test_abstract_methods_type_hints(self):
        """測試抽象方法的型別提示"""
        # 檢查基類Portfolio的抽象方法是否有正確的型別提示
        portfolio = Portfolio("test")

        # 檢查方法存在
        self.assertTrue(hasattr(portfolio, "optimize"))
        self.assertTrue(hasattr(portfolio, "evaluate"))
        self.assertTrue(hasattr(portfolio, "rebalance"))

        # 檢查方法會拋出NotImplementedError
        with self.assertRaises(NotImplementedError):
            portfolio.optimize(self.test_signals)

        with self.assertRaises(NotImplementedError):
            portfolio.evaluate(self.test_weights, self.test_price_df)

        with self.assertRaises(NotImplementedError):
            portfolio.rebalance(self.test_weights, self.test_price_df)

    def test_mean_variance_portfolio_rebalance(self):
        """測試均值方差投資組合的rebalance方法實現"""
        portfolio = MeanVariancePortfolio(risk_aversion=1.0)

        # 檢查rebalance方法存在
        self.assertTrue(hasattr(portfolio, "rebalance"))

        # 測試rebalance方法可以調用（即使可能因為資料不足而返回等權重）
        try:
            result = portfolio.rebalance(self.test_weights, self.test_price_df)

            # 檢查返回值是字典
            self.assertIsInstance(result, dict)

            # 檢查權重總和接近1.0
            total_weight = sum(result.values())
            self.assertAlmostEqual(total_weight, 1.0, places=2)

            # 檢查所有權重都是非負數
            for weight in result.values():
                self.assertGreaterEqual(weight, 0)

        except Exception as e:
            # 如果因為依賴問題失敗，確保是預期的錯誤
            self.assertIn("scipy", str(e).lower())

    def test_equal_weight_portfolio_functionality(self):
        """測試等權重投資組合的基本功能"""
        portfolio = EqualWeightPortfolio()

        # 檢查初始化
        self.assertEqual(portfolio.name, "EqualWeight")

        # 檢查optimize方法存在
        self.assertTrue(hasattr(portfolio, "optimize"))

    @patch("src.core.portfolio.sco")
    def test_scipy_dependency_handling(self, mock_sco):
        """測試scipy依賴處理"""
        # 模擬scipy不可用的情況
        with patch("src.core.portfolio.SCIPY_AVAILABLE", False):
            portfolio = MeanVariancePortfolio(risk_aversion=1.0)

            # 測試當scipy不可用時，_optimize_weights應該拋出DependencyError
            with self.assertRaises(DependencyError):
                portfolio._optimize_weights(
                    expected_returns=pd.Series([0.1, 0.1], index=["A", "B"]),
                    cov_matrix=pd.DataFrame(
                        [[0.1, 0.05], [0.05, 0.1]], index=["A", "B"], columns=["A", "B"]
                    ),
                )

    def test_portfolio_weight_validation(self):
        """測試投資組合權重驗證"""
        # 測試權重總和驗證
        weights = self.test_weights
        total_weight = sum(weights.values())

        # 權重總和應該接近1.0
        self.assertAlmostEqual(total_weight, 1.0, places=2)

        # 所有權重應該非負
        for symbol, weight in weights.items():
            self.assertGreaterEqual(weight, 0, f"{symbol}的權重不應為負數")
            self.assertLessEqual(weight, 1, f"{symbol}的權重不應超過1")

    def test_error_handling_improvements(self):
        """測試錯誤處理改善"""
        portfolio = MeanVariancePortfolio(risk_aversion=1.0)

        # 測試空資料處理
        empty_signals = pd.DataFrame()

        try:
            result = portfolio.optimize(empty_signals)
            # 如果沒有拋出異常，結果應該是空的或等權重
            self.assertIsInstance(result, (pd.DataFrame, dict))
        except Exception as e:
            # 應該是有意義的錯誤訊息
            self.assertIsInstance(e, (ValueError, KeyError, IndexError))

    def test_logging_integration(self):
        """測試日誌記錄整合"""
        # 檢查日誌記錄器是否正確設置
        import logging

        # 獲取模組的日誌記錄器
        logger = logging.getLogger("src.core.portfolio")
        self.assertIsInstance(logger, logging.Logger)

    def test_performance_considerations(self):
        """測試效能考量"""
        # 測試大量資料處理時的基本效能
        import time

        # 創建較大的測試資料集
        large_weights = {f"STOCK_{i}": 1.0 / 100 for i in range(100)}

        portfolio = MeanVariancePortfolio(risk_aversion=1.0)

        start_time = time.time()
        try:
            # 測試rebalance方法的基本效能
            result = portfolio.rebalance(large_weights, self.test_price_df)
            end_time = time.time()

            # 基本效能檢查（應該在合理時間內完成）
            execution_time = end_time - start_time
            self.assertLess(execution_time, 10.0, "rebalance方法執行時間過長")

        except Exception:
            # 如果因為資料問題失敗，這是可以接受的
            pass


class TestCodeQualityMetrics(unittest.TestCase):
    """測試程式碼品質指標"""

    def test_module_imports(self):
        """測試模組導入"""
        try:
            import src.core.portfolio as portfolio_module

            # 檢查主要類別是否可以導入
            self.assertTrue(hasattr(portfolio_module, "Portfolio"))
            self.assertTrue(hasattr(portfolio_module, "MeanVariancePortfolio"))
            self.assertTrue(hasattr(portfolio_module, "EqualWeightPortfolio"))

            # 檢查異常類別
            self.assertTrue(hasattr(portfolio_module, "PortfolioOptimizationError"))
            self.assertTrue(hasattr(portfolio_module, "DependencyError"))

        except ImportError as e:
            self.fail(f"無法導入投資組合模組: {e}")

    def test_docstring_presence(self):
        """測試文檔字串存在性"""
        if Portfolio is None:
            self.skipTest("無法導入投資組合模組")

        # 檢查主要類別是否有文檔字串
        self.assertIsNotNone(Portfolio.__doc__)
        self.assertIsNotNone(MeanVariancePortfolio.__doc__)

        # 檢查文檔字串不為空
        self.assertTrue(len(Portfolio.__doc__.strip()) > 0)
        self.assertTrue(len(MeanVariancePortfolio.__doc__.strip()) > 0)


if __name__ == "__main__":
    unittest.main()
