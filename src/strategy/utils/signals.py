# -*- coding: utf-8 -*-
"""
訊號生成工具模組（向後相容性）

此模組提供向後相容性，重新導出新模組結構中的功能。

注意：此檔案主要用於向後相容性，新的開發應該直接使用：
- src.strategy.utils.signal_generators: 基礎訊號生成器
- src.strategy.utils.signal_interface: 統一訊號生成介面
"""

# 從新模組導入所有功能
from .signal_generators import (
    trade_point_decision,
    continuous_trading_signal,
    triple_barrier,
    fixed_time_horizon,
    numba_moving_average
)

from .signal_interface import generate_signals

# 重新導出所有功能以保持向後相容性
__all__ = [
    "trade_point_decision",
    "continuous_trading_signal",
    "triple_barrier",
    "fixed_time_horizon",
    "numba_moving_average",
    "generate_signals"
]
