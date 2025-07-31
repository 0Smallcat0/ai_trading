"""
回測模組

此模組已被重構為 backtest_module 目錄下的多個模組。
此檔案僅作為向後兼容的橋接，請直接使用 backtest_module 中的類別和函數。
"""

# 忽略 FutureWarning
import warnings

from .backtest_module import (
    Backtest,
    MarketDataSimulator,
    detect_close_col,
    ensure_multiindex,
    calculate_sharpe,
    calculate_max_drawdown,
    align_timeseries,
)

warnings.simplefilter(action="ignore", category=FutureWarning)

__all__ = [
    "Backtest",
    "MarketDataSimulator",
    "detect_close_col",
    "ensure_multiindex",
    "calculate_sharpe",
    "calculate_max_drawdown",
    "align_timeseries",
]
