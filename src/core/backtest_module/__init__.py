"""
回測模組

此模組提供回測功能，用於評估交易策略的表現。
"""

from .backtest import Backtest
from .market_data_simulator import MarketDataSimulator
from .utils import (
    detect_close_col,
    ensure_multiindex,
    calculate_sharpe,
    calculate_max_drawdown,
    align_timeseries,
)

__all__ = [
    "Backtest",
    "MarketDataSimulator",
    "detect_close_col",
    "ensure_multiindex",
    "calculate_sharpe",
    "calculate_max_drawdown",
    "align_timeseries",
]
