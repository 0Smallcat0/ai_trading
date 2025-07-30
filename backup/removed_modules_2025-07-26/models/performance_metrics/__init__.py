# -*- coding: utf-8 -*-
"""
績效指標模組

此模組提供完整的金融和交易績效指標計算功能，包括：
- 風險調整收益指標 (Sharpe Ratio, Sortino Ratio, Calmar Ratio)
- 風險指標 (Maximum Drawdown, Volatility, VaR)
- 交易統計指標 (Win Rate, Profit/Loss Ratio, Expectancy)
- 綜合指標計算和分析

Classes:
    PerformanceAnalyzer: 主要的績效分析器
    RiskMetricsCalculator: 風險指標計算器
    TradingMetricsCalculator: 交易指標計算器
    StatisticalMetricsCalculator: 統計指標計算器

Functions:
    calculate_all_metrics: 計算所有績效指標
    create_performance_report: 生成績效報告
    compare_strategies: 比較策略績效

Example:
    >>> from src.models.performance_metrics import calculate_all_metrics
    >>> metrics = calculate_all_metrics(returns, prices=prices, trades=trades)
    >>> print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.4f}")

Note:
    所有指標計算都考慮了金融時間序列的特性
    支援日頻、週頻、月頻等不同頻率的資料
"""

from .trading_metrics import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_calmar_ratio,
    calculate_annual_return,
    calculate_total_return,
)
from .risk_metrics import (
    calculate_max_drawdown,
    calculate_volatility,
    calculate_var,
    calculate_cvar,
    calculate_downside_risk,
)
from .statistical_metrics import (
    calculate_win_rate,
    calculate_pnl_ratio,
    calculate_expectancy,
    calculate_profit_factor,
    calculate_recovery_factor,
)
from .utils import (
    validate_performance_inputs,
    annualize_metric,
    create_performance_report,
    plot_performance_comparison,
)

# 向後兼容的函數導入
from .legacy_interface import calculate_all_metrics

__all__ = [
    # Trading metrics
    "calculate_sharpe_ratio",
    "calculate_sortino_ratio",
    "calculate_calmar_ratio",
    "calculate_annual_return",
    "calculate_total_return",
    # Risk metrics
    "calculate_max_drawdown",
    "calculate_volatility",
    "calculate_var",
    "calculate_cvar",
    "calculate_downside_risk",
    # Statistical metrics
    "calculate_win_rate",
    "calculate_pnl_ratio",
    "calculate_expectancy",
    "calculate_profit_factor",
    "calculate_recovery_factor",
    # Utilities
    "validate_performance_inputs",
    "annualize_metric",
    "create_performance_report",
    "plot_performance_comparison",
    # Legacy interface
    "calculate_all_metrics",
]

# 版本資訊
__version__ = "1.0.0"
__author__ = "AI Trading System Team"
