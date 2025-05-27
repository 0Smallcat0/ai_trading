# -*- coding: utf-8 -*-
"""
績效指標模組測試

此模組測試績效指標計算功能，包括：
- 風險調整收益指標測試
- 風險指標測試
- 交易統計指標測試
- 向後兼容性測試
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch

from src.models.performance_metrics import (
    calculate_all_metrics,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_calmar_ratio,
    calculate_max_drawdown,
    calculate_volatility,
    calculate_var,
    calculate_win_rate,
    calculate_pnl_ratio,
    calculate_expectancy
)
from src.models.performance_metrics.trading_metrics import (
    calculate_sharpe_ratio as new_calculate_sharpe_ratio,
    calculate_sortino_ratio as new_calculate_sortino_ratio,
    calculate_calmar_ratio as new_calculate_calmar_ratio
)
from src.models.performance_metrics.risk_metrics import (
    calculate_max_drawdown as new_calculate_max_drawdown,
    calculate_volatility as new_calculate_volatility,
    calculate_var as new_calculate_var
)
from src.models.performance_metrics.statistical_metrics import (
    calculate_win_rate as new_calculate_win_rate,
    calculate_pnl_ratio as new_calculate_pnl_ratio,
    calculate_expectancy as new_calculate_expectancy
)
from src.models.performance_metrics.utils import (
    validate_performance_inputs,
    create_performance_report,
    plot_performance_comparison
)


class TestPerformanceInputValidation:
    """測試績效指標輸入驗證"""

    def test_valid_inputs(self):
        """測試有效輸入"""
        returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        # 應該不拋出異常
        validate_performance_inputs(returns)

    def test_none_input(self):
        """測試 None 輸入"""
        with pytest.raises(ValueError, match="輸入資料不能為 None"):
            validate_performance_inputs(None)

    def test_empty_input(self):
        """測試空輸入"""
        empty_series = pd.Series([])
        # 空輸入應該只發出警告，不拋出異常
        validate_performance_inputs(empty_series)

    def test_nan_input(self):
        """測試包含 NaN 的輸入"""
        returns_with_nan = pd.Series([0.01, np.nan, 0.015])
        with pytest.raises(ValueError, match="輸入資料包含 NaN 值"):
            validate_performance_inputs(returns_with_nan)

    def test_inf_input(self):
        """測試包含無窮大的輸入"""
        returns_with_inf = pd.Series([0.01, np.inf, 0.015])
        with pytest.raises(ValueError, match="輸入資料包含無窮大值"):
            validate_performance_inputs(returns_with_inf)

    def test_non_numeric_input(self):
        """測試非數值輸入"""
        non_numeric = pd.Series(['a', 'b', 'c'])
        with pytest.raises(TypeError, match="輸入資料必須是數值類型"):
            validate_performance_inputs(non_numeric)


class TestTradingMetrics:
    """測試交易績效指標"""

    @pytest.fixture
    def sample_returns(self):
        """創建測試收益率資料"""
        np.random.seed(42)
        return pd.Series(np.random.normal(0.001, 0.02, 252))

    def test_sharpe_ratio_calculation(self, sample_returns):
        """測試夏普比率計算"""
        sharpe = calculate_sharpe_ratio(sample_returns, risk_free_rate=0.02)
        new_sharpe = new_calculate_sharpe_ratio(sample_returns, risk_free_rate=0.02)
        
        # 驗證向後兼容性
        assert abs(sharpe - new_sharpe) < 1e-10
        assert isinstance(sharpe, float)

    def test_sharpe_ratio_zero_volatility(self):
        """測試零波動率情況下的夏普比率"""
        constant_returns = pd.Series([0.01] * 10)
        sharpe = calculate_sharpe_ratio(constant_returns)
        assert sharpe == 0.0

    def test_sortino_ratio_calculation(self, sample_returns):
        """測試索提諾比率計算"""
        sortino = calculate_sortino_ratio(sample_returns, target_return=0.005)
        new_sortino = new_calculate_sortino_ratio(sample_returns, target_return=0.005)
        
        # 驗證向後兼容性
        assert abs(sortino - new_sortino) < 1e-10
        assert isinstance(sortino, float)

    def test_calmar_ratio_calculation(self, sample_returns):
        """測試卡爾馬比率計算"""
        calmar = calculate_calmar_ratio(sample_returns)
        new_calmar = new_calculate_calmar_ratio(sample_returns)
        
        # 驗證向後兼容性
        assert abs(calmar - new_calmar) < 1e-10
        assert isinstance(calmar, float)

    def test_empty_returns(self):
        """測試空收益率序列"""
        empty_returns = pd.Series([])
        
        assert calculate_sharpe_ratio(empty_returns) == 0.0
        assert calculate_sortino_ratio(empty_returns) == 0.0
        assert calculate_calmar_ratio(empty_returns) == 0.0


class TestRiskMetrics:
    """測試風險指標"""

    @pytest.fixture
    def sample_returns(self):
        """創建測試收益率資料"""
        return pd.Series([0.02, -0.01, 0.015, -0.025, 0.01, 0.005, -0.015])

    @pytest.fixture
    def sample_prices(self):
        """創建測試價格資料"""
        returns = pd.Series([0.02, -0.01, 0.015, -0.025, 0.01, 0.005, -0.015])
        return (1 + returns).cumprod() * 100

    def test_max_drawdown_calculation(self, sample_returns):
        """測試最大回撤計算"""
        max_dd = calculate_max_drawdown(sample_returns)
        new_max_dd = new_calculate_max_drawdown(sample_returns)
        
        # 驗證向後兼容性
        assert abs(max_dd - new_max_dd) < 1e-10
        assert max_dd <= 0  # 最大回撤應該是負值或零

    def test_max_drawdown_with_prices(self, sample_returns, sample_prices):
        """測試使用價格計算最大回撤"""
        max_dd = calculate_max_drawdown(sample_returns, sample_prices)
        assert max_dd <= 0

    def test_volatility_calculation(self, sample_returns):
        """測試波動率計算"""
        vol = calculate_volatility(sample_returns)
        new_vol = new_calculate_volatility(sample_returns)
        
        # 驗證向後兼容性
        assert abs(vol - new_vol) < 1e-10
        assert vol >= 0  # 波動率應該是非負值

    def test_var_calculation(self, sample_returns):
        """測試 VaR 計算"""
        var_95 = calculate_var(sample_returns, confidence_level=0.95)
        new_var_95 = new_calculate_var(sample_returns, confidence_level=0.95)
        
        # 驗證向後兼容性
        assert abs(var_95 - new_var_95) < 1e-10
        assert isinstance(var_95, float)


class TestStatisticalMetrics:
    """測試統計指標"""

    @pytest.fixture
    def sample_returns(self):
        """創建測試收益率資料"""
        return pd.Series([0.02, -0.01, 0.015, -0.025, 0.01, 0.005, -0.015])

    @pytest.fixture
    def sample_trades(self):
        """創建測試交易資料"""
        return pd.Series([100, -50, 75, -125, 50, 25, -75])

    def test_win_rate_calculation(self, sample_returns):
        """測試勝率計算"""
        win_rate = calculate_win_rate(sample_returns)
        new_win_rate = new_calculate_win_rate(sample_returns)
        
        # 驗證向後兼容性
        assert abs(win_rate - new_win_rate) < 1e-10
        assert 0 <= win_rate <= 1  # 勝率應該在0到1之間

    def test_win_rate_with_trades(self, sample_returns, sample_trades):
        """測試使用交易資料計算勝率"""
        win_rate = calculate_win_rate(sample_returns, sample_trades)
        assert 0 <= win_rate <= 1

    def test_pnl_ratio_calculation(self, sample_returns):
        """測試盈虧比計算"""
        pnl_ratio = calculate_pnl_ratio(sample_returns)
        new_pnl_ratio = new_calculate_pnl_ratio(sample_returns)
        
        # 驗證向後兼容性
        assert abs(pnl_ratio - new_pnl_ratio) < 1e-10
        assert pnl_ratio >= 0  # 盈虧比應該是非負值

    def test_expectancy_calculation(self, sample_returns):
        """測試期望值計算"""
        expectancy = calculate_expectancy(sample_returns)
        new_expectancy = new_calculate_expectancy(sample_returns)
        
        # 驗證向後兼容性
        assert abs(expectancy - new_expectancy) < 1e-10
        assert isinstance(expectancy, float)


class TestComprehensiveMetrics:
    """測試綜合指標計算"""

    @pytest.fixture
    def sample_data(self):
        """創建完整的測試資料"""
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.02, 100))
        prices = (1 + returns).cumprod() * 100
        trades = returns * 10000  # 模擬交易損益
        return returns, prices, trades

    def test_calculate_all_metrics(self, sample_data):
        """測試計算所有指標"""
        returns, prices, trades = sample_data
        
        metrics = calculate_all_metrics(
            returns=returns,
            prices=prices,
            trades=trades,
            risk_free_rate=0.02
        )
        
        # 驗證返回的指標
        expected_metrics = [
            'sharpe_ratio', 'sortino_ratio', 'calmar_ratio',
            'max_drawdown', 'volatility', 'var_95',
            'win_rate', 'pnl_ratio', 'expectancy',
            'total_return', 'annual_return'
        ]
        
        for metric in expected_metrics:
            assert metric in metrics
            assert isinstance(metrics[metric], (int, float))

    def test_calculate_all_metrics_minimal(self):
        """測試最小參數的綜合指標計算"""
        returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        metrics = calculate_all_metrics(returns)
        
        # 驗證基本指標存在
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics
        assert 'win_rate' in metrics

    @patch('src.models.performance_metrics.utils.plt')
    def test_performance_report_generation(self, mock_plt, sample_data):
        """測試績效報告生成"""
        returns, _, _ = sample_data
        metrics = calculate_all_metrics(returns)
        
        report_path = create_performance_report(metrics, "Test Strategy")
        assert report_path.endswith('.html')

    @patch('src.models.performance_metrics.utils.plt')
    def test_performance_comparison_plot(self, mock_plt):
        """測試績效比較圖"""
        strategies_metrics = {
            "Strategy A": {"sharpe_ratio": 1.5, "max_drawdown": -0.1},
            "Strategy B": {"sharpe_ratio": 1.2, "max_drawdown": -0.15}
        }
        
        plot_path = plot_performance_comparison(strategies_metrics)
        assert plot_path.endswith('.png')
