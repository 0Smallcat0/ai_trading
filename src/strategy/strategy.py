# -*- coding: utf-8 -*-
"""
策略模組向後相容性橋樑

此檔案提供向後相容性，將舊的API重新導向到新的模組結構。

注意：此檔案主要用於向後相容性，新的開發應該直接使用新的模組結構：
- src.strategy.base: 基礎策略類別
- src.strategy.technical: 技術分析策略
- src.strategy.ml: 機器學習策略
- src.strategy.utils: 工具函數

已棄用的功能將在未來版本中移除。
"""

import warnings
import logging

# 從新模組導入所有功能
from .base import (
    Strategy as NewStrategy,
    StrategyError,
    ParameterError,
    ModelNotTrainedError,
    DataValidationError,
)

from .technical import (
    MovingAverageCrossStrategy as NewMovingAverageCrossStrategy,
    RSIStrategy as NewRSIStrategy,
)

from .ml import MachineLearningStrategy as NewMachineLearningStrategy

from .utils import (
    trade_point_decision,
    continuous_trading_signal,
    triple_barrier,
    fixed_time_horizon,
    generate_signals,
    numba_moving_average,
)

# 設定日誌
logger = logging.getLogger(__name__)

# 多語系訊息（保持向後相容性）
LOG_MSGS = {
    "zh_tw": {
        "no_close": "價格資料框架必須包含 '收盤價' 欄位",
        "no_rsi": "特徵資料框架必須包含 RSI 特徵",
        "no_model": "必須先訓練模型",
        "unknown_model": "不支援的模型類型: {model_type}",
        "unknown_strategy": "不支援的策略名稱: {strategy_name}",
        "index_structure_error": "價格資料 index 結構需包含 'stock_id' 層級，請確認資料格式。",
        "target_type_error": "target_df 必須為 pandas.Series 型別，請確認資料格式。",
    },
}
LOG_LANG = "zh_tw"


# 向後相容性類別定義
class Strategy(NewStrategy):
    """
    策略基類（向後相容性）

    注意：此類別已棄用，請使用 src.strategy.base.Strategy
    """

    def __init__(self, name="BaseStrategy"):
        """
        初始化策略（向後相容性）

        Args:
            name (str): 策略名稱
        """
        warnings.warn(
            "此 Strategy 類別已棄用，請使用 src.strategy.base.Strategy",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(name=name)


class MovingAverageCrossStrategy(NewMovingAverageCrossStrategy):
    """
    移動平均線交叉策略（向後相容性）

    注意：此類別已棄用，請使用 src.strategy.technical.MovingAverageCrossStrategy
    """

    def __init__(self, short_window=5, long_window=20):
        """
        初始化移動平均線交叉策略（向後相容性）

        Args:
            short_window (int): 短期窗口大小
            long_window (int): 長期窗口大小
        """
        warnings.warn(
            "此 MovingAverageCrossStrategy 類別已棄用，請使用 src.strategy.technical.MovingAverageCrossStrategy",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(short_window=short_window, long_window=long_window)


class RSIStrategy(NewRSIStrategy):
    """
    RSI策略（向後相容性）

    注意：此類別已棄用，請使用 src.strategy.technical.RSIStrategy
    """

    def __init__(self, rsi_window=14, overbought=70, oversold=30):
        """
        初始化RSI策略（向後相容性）

        Args:
            rsi_window (int): RSI 窗口大小
            overbought (int): 超買閾值
            oversold (int): 超賣閾值
        """
        warnings.warn(
            "此 RSIStrategy 類別已棄用，請使用 src.strategy.technical.RSIStrategy",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            rsi_window=rsi_window, overbought=overbought, oversold=oversold
        )


class MachineLearningStrategy(NewMachineLearningStrategy):
    """
    機器學習策略（向後相容性）

    注意：此類別已棄用，請使用 src.strategy.ml.MachineLearningStrategy
    """

    def __init__(self, model_type="random_forest", **model_params):
        """
        初始化機器學習策略（向後相容性）

        Args:
            model_type (str): 模型類型
            **model_params: 模型參數
        """
        warnings.warn(
            "此 MachineLearningStrategy 類別已棄用，請使用 src.strategy.ml.MachineLearningStrategy",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(model_type=model_type, **model_params)


# 向後相容性函數定義
def generate_signals_legacy(
    features, strategy_name="moving_average_cross", **strategy_params
):
    """
    生成交易訊號的統一介面函數（向後相容性）

    注意：此函數已棄用，請使用 src.strategy.utils.generate_signals

    Args:
        features: 特徵資料框架
        strategy_name: 策略名稱
        **strategy_params: 策略參數

    Returns:
        包含交易訊號的資料框架
    """
    warnings.warn(
        "此 generate_signals_legacy 函數已棄用，請使用 src.strategy.utils.generate_signals",
        DeprecationWarning,
        stacklevel=2,
    )
    return generate_signals(features, strategy_name, **strategy_params)


# 重新導出所有新模組的功能以保持向後相容性
__all__ = [
    # 基礎類別（向後相容性）
    "Strategy",
    "MovingAverageCrossStrategy",
    "RSIStrategy",
    "MachineLearningStrategy",
    # 工具函數
    "trade_point_decision",
    "continuous_trading_signal",
    "triple_barrier",
    "fixed_time_horizon",
    "generate_signals",
    "generate_signals_legacy",
    "numba_moving_average",
    # 異常類別
    "StrategyError",
    "ParameterError",
    "ModelNotTrainedError",
    "DataValidationError",
    # 常數
    "LOG_MSGS",
    "LOG_LANG",
]
