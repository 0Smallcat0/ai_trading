# -*- coding: utf-8 -*-
"""
交易策略庫模組

此模組提供完整的交易策略框架，包括：

基礎模組：
- Strategy: 策略基類
- StrategyError, ParameterError, ModelNotTrainedError: 異常類別

技術分析策略：
- MovingAverageCrossStrategy: 移動平均線交叉策略
- RSIStrategy: RSI策略
- MomentumStrategy: 動量策略
- MeanReversionStrategy: 均值回歸策略

機器學習策略：
- MachineLearningStrategy: 機器學習策略基類

工具函數：
- 各種訊號生成工具函數
"""

# 基礎模組
from .base import (
    Strategy,
    StrategyError,
    ParameterError,
    ModelNotTrainedError,
    DataValidationError,
)

# 技術分析策略
from .technical import MovingAverageCrossStrategy, RSIStrategy

# 機器學習策略
from .ml import MachineLearningStrategy

# 工具函數
from .utils import (
    trade_point_decision,
    continuous_trading_signal,
    triple_barrier,
    fixed_time_horizon,
    generate_signals,
)

# 保持向後相容性
from .momentum import MomentumStrategy
from .mean_reversion import MeanReversionStrategy

__all__ = [
    # 基礎類別
    "Strategy",
    "StrategyError",
    "ParameterError",
    "ModelNotTrainedError",
    "DataValidationError",
    # 技術分析策略
    "MovingAverageCrossStrategy",
    "RSIStrategy",
    "MomentumStrategy",
    "MeanReversionStrategy",
    # 機器學習策略
    "MachineLearningStrategy",
    # 工具函數
    "trade_point_decision",
    "continuous_trading_signal",
    "triple_barrier",
    "fixed_time_horizon",
    "generate_signals",
]
