# -*- coding: utf-8 -*-
"""
策略工具模組

此模組包含策略開發和分析的工具函數。

可用工具：
- signals: 訊號生成和處理工具
"""

from .signals import (
    trade_point_decision,
    continuous_trading_signal,
    triple_barrier,
    fixed_time_horizon,
    generate_signals,
    numba_moving_average
)

__all__ = [
    "trade_point_decision",
    "continuous_trading_signal",
    "triple_barrier",
    "fixed_time_horizon",
    "generate_signals",
    "numba_moving_average"
]
