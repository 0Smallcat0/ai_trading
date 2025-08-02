"""
進階投資組合管理功能測試

測試風險分析、資產配置、績效歸因、再平衡等核心功能。
"""

import unittest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 添加專案根目錄到 Python 路徑
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ui.utils.portfolio_analytics import (
    PortfolioAnalytics,
    VaRMethod,
    OptimizationObjective,
    PortfolioMetrics,
    RiskDecomposition,
)


class TestPortfolioAnalytics(unittest.TestCase):
    """測試投資組合分析核心功能"""

    def setUp(self):
        """設置測試環境"""
        self.analytics = PortfolioAnalytics(risk_free_rate=0.02)

        # 生成測試數據
        np.random.seed(42)
        self.test_returns = pd.Series(
            np.random.normal(0.001, 0.02, 252),
            index=pd.date_range("2023-01-01", periods=252, freq="D"),
        )

        self.test_weights = np.array([0.4, 0.3, 0.2, 0.1])
        self.test_expected_returns = np.array([0.08, 0.10, 0.06, 0.12])
        self.test_cov_matrix = np.array(
            [
                [0.04, 0.01, 0.005, 0.002],
                [0.01, 0.09, 0.008, 0.003],
                [0.005, 0.008, 0.02, 0.001],
                [0.002, 0.003, 0.001, 0.16],
            ]
        )

    def test_var_calculation_historical(self):
        """測試歷史模擬法 VaR 計算"""
        var = self.analytics.calculate_var(
            self.test_returns, confidence_level=0.95, method=VaRMethod.HISTORICAL
        )

        self.assertIsInstance(var, float)
        self.assertGreater(var, 0)
        self.assertLess(var, 1)  # VaR 應該在合理範圍內

    def test_var_calculation_parametric(self):
        """測試參數法 VaR 計算"""
        var = self.analytics.calculate_var(
            self.test_returns, confidence_level=0.95, method=VaRMethod.PARAMETRIC
        )

        self.assertIsInstance(var, float)
        self.assertGreater(var, 0)

    def test_var_calculation_monte_carlo(self):
        """測試 Monte Carlo 法 VaR 計算"""
        var = self.analytics.calculate_var(
            self.test_returns, confidence_level=0.95, method=VaRMethod.MONTE_CARLO
        )

        self.assertIsInstance(var, float)
        self.assertGreater(var, 0)

    def test_expected_shortfall_calculation(self):
        """測試預期損失計算"""
        es = self.analytics.calculate_expected_shortfall(
            self.test_returns, confidence_level=0.95
        )

        self.assertIsInstance(es, float)
        self.assertGreaterEqual(es, 0)

        # ES 應該大於等於 VaR
        var = self.analytics.calculate_var(self.test_returns, 0.95)
        self.assertGreaterEqual(es, var)

    def test_stress_testing(self):
        """測試壓力測試"""
        returns_matrix = pd.DataFrame(
            {
                "Asset1": np.random.normal(0.001, 0.02, 100),
                "Asset2": np.random.normal(0.0008, 0.025, 100),
                "Asset3": np.random.normal(0.0012, 0.018, 100),
            }
        )

        weights = np.array([0.5, 0.3, 0.2])

        stress_scenarios = {
            "Market Crash": {"Asset1": -0.20, "Asset2": -0.15, "Asset3": -0.25}
        }

        results = self.analytics.stress_test(weights, returns_matrix, stress_scenarios)

        self.assertIsInstance(results, dict)
        self.assertIn("Market Crash", results)
        self.assertIsInstance(results["Market Crash"], float)

    def test_efficient_frontier_calculation(self):
        """測試效率前緣計算"""
        returns, volatility, weights = self.analytics.calculate_efficient_frontier(
            self.test_expected_returns, self.test_cov_matrix, num_points=10
        )

        self.assertEqual(len(returns), 10)
        self.assertEqual(len(volatility), 10)
        self.assertEqual(weights.shape, (10, 4))

        # 檢查權重總和為1
        for w in weights:
            if not np.isnan(w).any():
                self.assertAlmostEqual(np.sum(w), 1.0, places=5)

    def test_portfolio_optimization_max_sharpe(self):
        """測試最大夏普比率優化"""
        result = self.analytics.optimize_portfolio(
            self.test_expected_returns,
            self.test_cov_matrix,
            OptimizationObjective.MAX_SHARPE,
        )

        self.assertTrue(result["success"])
        self.assertIn("weights", result)
        self.assertIn("expected_return", result)
        self.assertIn("volatility", result)
        self.assertIn("sharpe_ratio", result)

        # 檢查權重總和為1
        self.assertAlmostEqual(np.sum(result["weights"]), 1.0, places=5)

    def test_portfolio_optimization_min_volatility(self):
        """測試最小波動率優化"""
        result = self.analytics.optimize_portfolio(
            self.test_expected_returns,
            self.test_cov_matrix,
            OptimizationObjective.MIN_VOLATILITY,
        )

        self.assertTrue(result["success"])
        self.assertAlmostEqual(np.sum(result["weights"]), 1.0, places=5)

    def test_brinson_attribution(self):
        """測試 Brinson 績效歸因"""
        portfolio_weights = np.array([0.3, 0.4, 0.2, 0.1])
        benchmark_weights = np.array([0.25, 0.35, 0.25, 0.15])
        portfolio_returns = np.array([0.08, 0.12, 0.06, 0.10])
        benchmark_returns = np.array([0.07, 0.10, 0.05, 0.09])

        result = self.analytics.brinson_attribution(
            portfolio_weights, benchmark_weights, portfolio_returns, benchmark_returns
        )

        self.assertIn("allocation_effect", result)
        self.assertIn("selection_effect", result)
        self.assertIn("interaction_effect", result)
        self.assertIn("total_excess_return", result)

        # 檢查總超額報酬等於各效應之和
        total_calculated = (
            result["allocation_effect"]
            + result["selection_effect"]
            + result["interaction_effect"]
        )
        self.assertAlmostEqual(
            total_calculated, result["total_excess_return"], places=10
        )

    def test_tracking_error_calculation(self):
        """測試追蹤誤差計算"""
        benchmark_returns = self.test_returns + np.random.normal(
            0, 0.005, len(self.test_returns)
        )

        tracking_error = self.analytics.calculate_tracking_error(
            self.test_returns, benchmark_returns
        )

        self.assertIsInstance(tracking_error, float)
        self.assertGreater(tracking_error, 0)

    def test_information_ratio_calculation(self):
        """測試資訊比率計算"""
        benchmark_returns = self.test_returns + np.random.normal(
            0, 0.005, len(self.test_returns)
        )

        info_ratio = self.analytics.calculate_information_ratio(
            self.test_returns, benchmark_returns
        )

        self.assertIsInstance(info_ratio, float)

    def test_beta_calculation(self):
        """測試 Beta 計算"""
        market_returns = self.test_returns * 0.8 + np.random.normal(
            0, 0.01, len(self.test_returns)
        )

        beta = self.analytics.calculate_beta(self.test_returns, market_returns)

        self.assertIsInstance(beta, float)
        self.assertGreater(beta, 0)  # 假設正相關

    def test_alpha_calculation(self):
        """測試 Alpha 計算"""
        market_returns = self.test_returns * 0.8 + np.random.normal(
            0, 0.01, len(self.test_returns)
        )

        alpha = self.analytics.calculate_alpha(self.test_returns, market_returns)

        self.assertIsInstance(alpha, float)

    def test_rebalancing_suggestion(self):
        """測試再平衡建議"""
        current_weights = np.array([0.35, 0.25, 0.25, 0.15])
        target_weights = np.array([0.30, 0.30, 0.20, 0.20])
        threshold = 0.05

        result = self.analytics.suggest_rebalancing(
            current_weights, target_weights, threshold
        )

        self.assertIn("needs_rebalancing", result)
        self.assertIn("max_deviation", result)
        self.assertIsInstance(result["needs_rebalancing"], bool)
        self.assertIsInstance(result["max_deviation"], float)

        if result["needs_rebalancing"]:
            self.assertIn("trades", result)
            self.assertIn("total_transaction_cost", result)

    def test_portfolio_metrics_calculation(self):
        """測試投資組合指標計算"""
        metrics = self.analytics.calculate_portfolio_metrics(self.test_returns)

        self.assertIsInstance(metrics, PortfolioMetrics)
        self.assertIsInstance(metrics.returns, float)
        self.assertIsInstance(metrics.volatility, float)
        self.assertIsInstance(metrics.sharpe_ratio, float)
        self.assertIsInstance(metrics.max_drawdown, float)
        self.assertIsInstance(metrics.var_95, float)
        self.assertIsInstance(metrics.var_99, float)

        # 檢查邏輯關係
        self.assertLessEqual(
            metrics.var_99, metrics.var_95
        )  # 99% VaR 應該小於等於 95% VaR
        self.assertLessEqual(metrics.max_drawdown, 0)  # 最大回撤應該為負值或零

    def test_risk_decomposition(self):
        """測試風險分解"""
        risk_decomp = self.analytics.decompose_risk(
            self.test_weights, self.test_cov_matrix
        )

        self.assertIsInstance(risk_decomp, RiskDecomposition)
        self.assertGreater(risk_decomp.total_risk, 0)
        self.assertGreater(risk_decomp.diversification_ratio, 0)

        # 檢查風險組成總和
        total_component_risk = (
            risk_decomp.market_risk
            + risk_decomp.credit_risk
            + risk_decomp.liquidity_risk
            + risk_decomp.operational_risk
        )
        self.assertAlmostEqual(total_component_risk, risk_decomp.total_risk, places=5)

    def test_empty_returns_handling(self):
        """測試空報酬率序列的處理"""
        empty_returns = pd.Series([], dtype=float)

        var = self.analytics.calculate_var(empty_returns)
        self.assertEqual(var, 0.0)

        es = self.analytics.calculate_expected_shortfall(empty_returns)
        self.assertEqual(es, 0.0)

    def test_invalid_input_handling(self):
        """測試無效輸入的處理"""
        # 測試不匹配的序列長度
        short_benchmark = pd.Series([0.01, 0.02])

        tracking_error = self.analytics.calculate_tracking_error(
            self.test_returns, short_benchmark
        )
        self.assertEqual(tracking_error, 0.0)

    def test_optimization_with_constraints(self):
        """測試帶約束條件的優化"""
        constraints = {"max_weight": 0.4, "min_weight": {0: 0.1, 1: 0.1}}

        result = self.analytics.optimize_portfolio(
            self.test_expected_returns,
            self.test_cov_matrix,
            OptimizationObjective.MAX_SHARPE,
            constraints,
        )

        if result["success"]:
            # 檢查約束條件
            self.assertLessEqual(np.max(result["weights"]), 0.4 + 1e-6)
            self.assertGreaterEqual(result["weights"][0], 0.1 - 1e-6)
            self.assertGreaterEqual(result["weights"][1], 0.1 - 1e-6)


class TestPortfolioComponents(unittest.TestCase):
    """測試投資組合組件功能"""

    def setUp(self):
        """設置測試環境"""
        self.portfolio_data = {
            "name": "Test Portfolio",
            "total_value": 1000000,
            "annual_return": 0.08,
            "annual_volatility": 0.15,
            "sharpe_ratio": 0.8,
            "max_drawdown": -0.12,
            "beta": 1.1,
            "holdings_count": 25,
            "last_rebalance": datetime.now() - timedelta(days=60),
        }

    @patch("streamlit.session_state")
    def test_risk_analysis_component_initialization(self, mock_session_state):
        """測試風險分析組件初始化"""
        mock_session_state.get.return_value = "light"

        from src.ui.components.portfolio.risk_analysis import RiskAnalysisComponent

        component = RiskAnalysisComponent()
        self.assertIsNotNone(component.analytics)
        self.assertIsNotNone(component.theme)

    @patch("streamlit.session_state")
    def test_asset_allocation_component_initialization(self, mock_session_state):
        """測試資產配置組件初始化"""
        mock_session_state.get.return_value = "light"

        from src.ui.components.portfolio.asset_allocation import (
            AssetAllocationComponent,
        )

        component = AssetAllocationComponent()
        self.assertIsNotNone(component.analytics)
        self.assertIsNotNone(component.theme)

    @patch("streamlit.session_state")
    def test_performance_attribution_component_initialization(self, mock_session_state):
        """測試績效歸因組件初始化"""
        mock_session_state.get.return_value = "light"

        from src.ui.components.portfolio.performance_attribution import (
            PerformanceAttributionComponent,
        )

        component = PerformanceAttributionComponent()
        self.assertIsNotNone(component.analytics)
        self.assertIsNotNone(component.theme)

    @patch("streamlit.session_state")
    def test_rebalancing_component_initialization(self, mock_session_state):
        """測試再平衡組件初始化"""
        mock_session_state.get.return_value = "light"

        from src.ui.components.portfolio.rebalancing import RebalancingComponent

        component = RebalancingComponent()
        self.assertIsNotNone(component.analytics)
        self.assertIsNotNone(component.theme)


class TestPortfolioAdvancedPage(unittest.TestCase):
    """測試進階投資組合管理頁面功能"""

    def test_portfolio_health_check(self):
        """測試投資組合健康檢查"""
        from src.ui.pages.portfolio_management_advanced import (
            perform_portfolio_health_check,
        )

        portfolio_data = {
            "sharpe_ratio": 1.2,
            "max_drawdown": -0.08,
            "last_rebalance": datetime.now() - timedelta(days=45),
            "holdings_count": 25,
        }

        health_check = perform_portfolio_health_check(portfolio_data)

        self.assertIn("good", health_check)
        self.assertIn("warnings", health_check)
        self.assertIn("alerts", health_check)
        self.assertIsInstance(health_check["good"], list)
        self.assertIsInstance(health_check["warnings"], list)
        self.assertIsInstance(health_check["alerts"], list)

    def test_quick_recommendations_generation(self):
        """測試快速建議生成"""
        from src.ui.pages.portfolio_management_advanced import (
            generate_quick_recommendations,
        )

        portfolio_data = {
            "sharpe_ratio": 0.6,
            "annual_volatility": 0.25,
            "last_rebalance": datetime.now() - timedelta(days=150),
        }

        recommendations = generate_quick_recommendations(portfolio_data)

        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)

        for rec in recommendations:
            self.assertIn("title", rec)
            self.assertIn("description", rec)
            self.assertIn("priority", rec)
            self.assertIn("impact", rec)

    def test_portfolio_data_loading(self):
        """測試投資組合數據載入"""
        from src.ui.pages.portfolio_management_advanced import load_portfolio_data

        portfolio_data = load_portfolio_data("Test Portfolio", "6個月")

        self.assertIn("name", portfolio_data)
        self.assertIn("total_value", portfolio_data)
        self.assertIn("annual_return", portfolio_data)
        self.assertIn("annual_volatility", portfolio_data)
        self.assertIsInstance(portfolio_data["total_value"], (int, float))
        self.assertIsInstance(portfolio_data["annual_return"], (int, float))


class TestPerformanceBenchmarks(unittest.TestCase):
    """測試效能基準"""

    def setUp(self):
        """設置效能測試環境"""
        self.analytics = PortfolioAnalytics()

        # 生成大型測試數據集
        np.random.seed(42)
        self.large_returns = pd.Series(
            np.random.normal(0.001, 0.02, 1000),
            index=pd.date_range("2020-01-01", periods=1000, freq="D"),
        )

        # 大型投資組合（100檔股票）
        self.large_portfolio_size = 100
        self.large_expected_returns = np.random.uniform(
            0.05, 0.15, self.large_portfolio_size
        )

        # 生成大型共變異數矩陣
        A = np.random.randn(self.large_portfolio_size, self.large_portfolio_size)
        self.large_cov_matrix = np.dot(A, A.T) * 0.01

    def test_var_calculation_performance(self):
        """測試 VaR 計算效能（目標：<5秒）"""
        import time

        start_time = time.time()

        # 模擬1000檔股票的VaR計算
        for _ in range(10):  # 重複計算以測試效能
            var = self.analytics.calculate_var(
                self.large_returns, confidence_level=0.95, method=VaRMethod.MONTE_CARLO
            )

        end_time = time.time()
        execution_time = end_time - start_time

        self.assertLess(
            execution_time, 5.0, f"VaR計算耗時 {execution_time:.2f}秒，超過5秒基準"
        )

    def test_efficient_frontier_performance(self):
        """測試效率前緣計算效能（目標：<3秒）"""
        import time

        start_time = time.time()

        returns, volatility, weights = self.analytics.calculate_efficient_frontier(
            self.large_expected_returns, self.large_cov_matrix, num_points=100
        )

        end_time = time.time()
        execution_time = end_time - start_time

        self.assertLess(
            execution_time, 3.0, f"效率前緣計算耗時 {execution_time:.2f}秒，超過3秒基準"
        )

    def test_memory_usage(self):
        """測試記憶體使用量"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 執行大量計算
        for _ in range(5):
            self.analytics.calculate_efficient_frontier(
                self.large_expected_returns, self.large_cov_matrix, num_points=50
            )

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        self.assertLess(
            memory_increase, 50, f"記憶體增長 {memory_increase:.1f}MB，超過50MB基準"
        )


if __name__ == "__main__":
    # 運行測試
    unittest.main(verbosity=2)
