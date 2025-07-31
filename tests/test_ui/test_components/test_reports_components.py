"""報表組件單元測試

此模組測試報表組件的各種功能，包括報表生成、數據處理和錯誤處理。
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timedelta

from src.ui.components.reports_components import (
    ReportGenerator,
    PerformanceAnalyzer,
    RiskAnalyzer,
)


@pytest.fixture
def sample_trading_data():
    """提供測試用的交易數據"""
    dates = pd.date_range("2023-01-01", periods=30, freq="D")
    return pd.DataFrame(
        {
            "date": dates,
            "symbol": ["AAPL"] * 30,
            "price": np.random.uniform(100, 200, 30),
            "volume": np.random.randint(1000, 10000, 30),
            "returns": np.random.normal(0.001, 0.02, 30),
        }
    )


@pytest.fixture
def sample_portfolio_data():
    """提供測試用的投資組合數據"""
    return pd.DataFrame(
        {
            "symbol": ["AAPL", "GOOGL", "MSFT", "TSLA"],
            "weight": [0.3, 0.25, 0.25, 0.2],
            "value": [30000, 25000, 25000, 20000],
            "returns": [0.05, 0.03, 0.04, 0.08],
        }
    )


@pytest.fixture
def mock_streamlit():
    """模擬 Streamlit 功能"""
    with patch("src.ui.components.reports_components.st") as mock_st:
        mock_st.columns.return_value = [Mock(), Mock(), Mock()]
        mock_st.metric = Mock()
        mock_st.plotly_chart = Mock()
        mock_st.dataframe = Mock()
        mock_st.success = Mock()
        mock_st.error = Mock()
        mock_st.warning = Mock()
        yield mock_st


class TestReportGenerator:
    """測試報表生成器"""

    def test_init(self):
        """測試初始化"""
        generator = ReportGenerator()
        assert generator is not None

    @patch("src.ui.components.reports_components.st")
    def test_generate_trading_summary(self, mock_st, sample_trading_data):
        """測試交易摘要生成"""
        mock_st.columns.return_value = [Mock(), Mock(), Mock()]
        mock_st.metric = Mock()

        generator = ReportGenerator()

        # 模擬方法調用
        with patch.object(generator, "_calculate_trading_metrics") as mock_calc:
            mock_calc.return_value = {
                "total_trades": 100,
                "win_rate": 65.5,
                "total_pnl": 15000,
            }

            generator.generate_trading_summary(sample_trading_data)

            mock_calc.assert_called_once_with(sample_trading_data)
            mock_st.metric.assert_called()

    @patch("src.ui.components.reports_components.st")
    def test_generate_portfolio_report(self, mock_st, sample_portfolio_data):
        """測試投資組合報表生成"""
        mock_st.plotly_chart = Mock()
        mock_st.dataframe = Mock()

        generator = ReportGenerator()
        generator.generate_portfolio_report(sample_portfolio_data)

        mock_st.plotly_chart.assert_called()
        mock_st.dataframe.assert_called()

    def test_calculate_trading_metrics(self, sample_trading_data):
        """測試交易指標計算"""
        generator = ReportGenerator()

        # 添加必要的欄位
        sample_trading_data["pnl"] = np.random.normal(
            100, 500, len(sample_trading_data)
        )
        sample_trading_data["trades"] = np.random.randint(
            1, 10, len(sample_trading_data)
        )

        metrics = generator._calculate_trading_metrics(sample_trading_data)

        assert isinstance(metrics, dict)
        assert "total_trades" in metrics
        assert "total_pnl" in metrics
        assert "win_rate" in metrics
        assert isinstance(metrics["total_trades"], (int, float))
        assert isinstance(metrics["total_pnl"], (int, float))
        assert isinstance(metrics["win_rate"], (int, float))

    def test_calculate_trading_metrics_empty_data(self):
        """測試空數據的交易指標計算"""
        generator = ReportGenerator()
        empty_data = pd.DataFrame()

        with pytest.raises(ValueError, match="數據不能為空"):
            generator._calculate_trading_metrics(empty_data)

    @patch("src.ui.components.reports_components.st")
    def test_error_handling_in_trading_summary(self, mock_st):
        """測試交易摘要中的錯誤處理"""
        mock_st.error = Mock()

        generator = ReportGenerator()

        # 傳入無效數據
        invalid_data = "not a dataframe"

        with pytest.raises(Exception):
            generator.generate_trading_summary(invalid_data)


class TestPerformanceAnalyzer:
    """測試績效分析器"""

    def test_init(self):
        """測試初始化"""
        analyzer = PerformanceAnalyzer()
        assert analyzer is not None

    @patch("src.ui.components.reports_components.st")
    def test_analyze_returns(self, mock_st, sample_trading_data):
        """測試收益分析"""
        mock_st.plotly_chart = Mock()
        mock_st.metric = Mock()

        analyzer = PerformanceAnalyzer()
        analyzer.analyze_returns(sample_trading_data)

        mock_st.plotly_chart.assert_called()
        mock_st.metric.assert_called()

    @patch("src.ui.components.reports_components.st")
    def test_analyze_drawdown(self, mock_st, sample_trading_data):
        """測試回撤分析"""
        mock_st.plotly_chart = Mock()
        mock_st.metric = Mock()

        analyzer = PerformanceAnalyzer()
        analyzer.analyze_drawdown(sample_trading_data)

        mock_st.plotly_chart.assert_called()
        mock_st.metric.assert_called()

    def test_calculate_sharpe_ratio(self, sample_trading_data):
        """測試夏普比率計算"""
        analyzer = PerformanceAnalyzer()

        sharpe = analyzer._calculate_sharpe_ratio(sample_trading_data["returns"])

        assert isinstance(sharpe, (int, float))
        assert not np.isnan(sharpe)

    def test_calculate_max_drawdown(self, sample_trading_data):
        """測試最大回撤計算"""
        analyzer = PerformanceAnalyzer()

        # 創建累積收益
        cumulative_returns = (1 + sample_trading_data["returns"]).cumprod()
        max_dd = analyzer._calculate_max_drawdown(cumulative_returns)

        assert isinstance(max_dd, (int, float))
        assert max_dd <= 0  # 回撤應該是負值或零

    def test_calculate_sharpe_ratio_zero_std(self):
        """測試標準差為零時的夏普比率計算"""
        analyzer = PerformanceAnalyzer()

        # 創建標準差為零的收益序列
        zero_std_returns = pd.Series([0.01] * 10)
        sharpe = analyzer._calculate_sharpe_ratio(zero_std_returns)

        assert sharpe == 0  # 標準差為零時應返回0

    def test_empty_data_handling(self):
        """測試空數據處理"""
        analyzer = PerformanceAnalyzer()
        empty_data = pd.DataFrame()

        with pytest.raises(ValueError, match="數據不能為空"):
            analyzer.analyze_returns(empty_data)


class TestRiskAnalyzer:
    """測試風險分析器"""

    def test_init(self):
        """測試初始化"""
        analyzer = RiskAnalyzer()
        assert analyzer is not None

    @patch("src.ui.components.reports_components.st")
    def test_analyze_var(self, mock_st, sample_trading_data):
        """測試VaR分析"""
        mock_st.plotly_chart = Mock()
        mock_st.metric = Mock()

        analyzer = RiskAnalyzer()
        analyzer.analyze_var(sample_trading_data)

        mock_st.plotly_chart.assert_called()
        mock_st.metric.assert_called()

    @patch("src.ui.components.reports_components.st")
    def test_analyze_correlation(self, mock_st, sample_portfolio_data):
        """測試相關性分析"""
        mock_st.plotly_chart = Mock()

        analyzer = RiskAnalyzer()

        # 創建多資產收益數據
        multi_asset_data = pd.DataFrame(
            {
                "AAPL": np.random.normal(0.001, 0.02, 30),
                "GOOGL": np.random.normal(0.001, 0.02, 30),
                "MSFT": np.random.normal(0.001, 0.02, 30),
            }
        )

        analyzer.analyze_correlation(multi_asset_data)
        mock_st.plotly_chart.assert_called()

    def test_calculate_var(self, sample_trading_data):
        """測試VaR計算"""
        analyzer = RiskAnalyzer()

        var_95 = analyzer._calculate_var(
            sample_trading_data["returns"], confidence=0.95
        )
        var_99 = analyzer._calculate_var(
            sample_trading_data["returns"], confidence=0.99
        )

        assert isinstance(var_95, (int, float))
        assert isinstance(var_99, (int, float))
        assert var_99 <= var_95  # 99% VaR應該小於等於95% VaR

    def test_calculate_var_invalid_confidence(self, sample_trading_data):
        """測試無效信心水準的VaR計算"""
        analyzer = RiskAnalyzer()

        with pytest.raises(ValueError, match="信心水準必須在0和1之間"):
            analyzer._calculate_var(sample_trading_data["returns"], confidence=1.5)

    def test_calculate_correlation_matrix(self):
        """測試相關性矩陣計算"""
        analyzer = RiskAnalyzer()

        # 創建測試數據
        data = pd.DataFrame(
            {
                "A": np.random.randn(100),
                "B": np.random.randn(100),
                "C": np.random.randn(100),
            }
        )

        corr_matrix = analyzer._calculate_correlation_matrix(data)

        assert isinstance(corr_matrix, pd.DataFrame)
        assert corr_matrix.shape == (3, 3)
        assert np.allclose(np.diag(corr_matrix), 1.0)  # 對角線應該是1

    def test_empty_data_handling(self):
        """測試空數據處理"""
        analyzer = RiskAnalyzer()
        empty_data = pd.DataFrame()

        with pytest.raises(ValueError, match="數據不能為空"):
            analyzer.analyze_var(empty_data)


class TestErrorHandling:
    """測試錯誤處理機制"""

    def test_exception_chaining_in_report_generator(self, sample_trading_data):
        """測試報表生成器中的異常鏈接"""
        generator = ReportGenerator()

        # 模擬內部方法拋出異常
        with patch.object(generator, "_calculate_trading_metrics") as mock_calc:
            mock_calc.side_effect = Exception("計算錯誤")

            with pytest.raises(Exception) as exc_info:
                generator.generate_trading_summary(sample_trading_data)

            # 驗證異常鏈接
            assert exc_info.value.__cause__ is not None or "計算錯誤" in str(
                exc_info.value
            )

    def test_exception_chaining_in_performance_analyzer(self, sample_trading_data):
        """測試績效分析器中的異常鏈接"""
        analyzer = PerformanceAnalyzer()

        # 模擬計算方法拋出異常
        with patch.object(analyzer, "_calculate_sharpe_ratio") as mock_calc:
            mock_calc.side_effect = Exception("計算錯誤")

            with pytest.raises(Exception):
                analyzer.analyze_returns(sample_trading_data)

    def test_exception_chaining_in_risk_analyzer(self, sample_trading_data):
        """測試風險分析器中的異常鏈接"""
        analyzer = RiskAnalyzer()

        # 模擬計算方法拋出異常
        with patch.object(analyzer, "_calculate_var") as mock_calc:
            mock_calc.side_effect = Exception("計算錯誤")

            with pytest.raises(Exception):
                analyzer.analyze_var(sample_trading_data)


class TestIntegration:
    """測試整合功能"""

    @patch("src.ui.components.reports_components.st")
    def test_full_report_generation_workflow(
        self, mock_st, sample_trading_data, sample_portfolio_data
    ):
        """測試完整的報表生成工作流程"""
        mock_st.columns.return_value = [Mock(), Mock(), Mock()]
        mock_st.metric = Mock()
        mock_st.plotly_chart = Mock()
        mock_st.dataframe = Mock()

        # 初始化所有組件
        generator = ReportGenerator()
        perf_analyzer = PerformanceAnalyzer()
        risk_analyzer = RiskAnalyzer()

        # 執行完整工作流程
        generator.generate_trading_summary(sample_trading_data)
        perf_analyzer.analyze_returns(sample_trading_data)
        risk_analyzer.analyze_var(sample_trading_data)
        generator.generate_portfolio_report(sample_portfolio_data)

        # 驗證所有組件都被調用
        assert mock_st.metric.call_count > 0
        assert mock_st.plotly_chart.call_count > 0
        assert mock_st.dataframe.call_count > 0

    def test_data_consistency_across_components(self, sample_trading_data):
        """測試組件間數據一致性"""
        generator = ReportGenerator()
        perf_analyzer = PerformanceAnalyzer()
        risk_analyzer = RiskAnalyzer()

        # 添加必要欄位
        sample_trading_data["pnl"] = np.random.normal(
            100, 500, len(sample_trading_data)
        )
        sample_trading_data["trades"] = np.random.randint(
            1, 10, len(sample_trading_data)
        )

        # 計算指標
        trading_metrics = generator._calculate_trading_metrics(sample_trading_data)
        sharpe_ratio = perf_analyzer._calculate_sharpe_ratio(
            sample_trading_data["returns"]
        )
        var_95 = risk_analyzer._calculate_var(sample_trading_data["returns"])

        # 驗證數據類型一致性
        assert isinstance(trading_metrics["total_pnl"], (int, float))
        assert isinstance(sharpe_ratio, (int, float))
        assert isinstance(var_95, (int, float))
