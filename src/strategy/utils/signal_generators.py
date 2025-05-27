# -*- coding: utf-8 -*-
"""
基礎訊號生成器模組

此模組提供各種基礎的交易訊號生成函數。

主要功能：
- 交易點決策
- 連續交易訊號
- 三重障礙法
- 固定時間範圍訊號
"""

import logging
import math
import pandas as pd
import numpy as np

# 可選導入 numba
try:
    from numba import njit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    # 如果沒有 numba，創建一個空的裝飾器
    def njit(*args, **kwargs):  # pylint: disable=unused-argument
        def decorator(func):
            return func
        return decorator

# 設定日誌
logger = logging.getLogger(__name__)


def trade_point_decision(price_series: pd.Series, threshold: float = 200.0) -> pd.Series:
    """
    交易點決策函數。

    根據價格變化幅度決定交易點，當價格變化超過閾值時產生訊號。

    Args:
        price_series: 價格序列
        threshold: 價格變化閾值

    Returns:
        交易決策訊號序列 (1=買入, -1=賣出, 0=觀望)

    Example:
        >>> prices = pd.Series([100, 105, 110, 95, 90])
        >>> signals = trade_point_decision(prices, threshold=5.0)
    """
    if price_series.empty:
        return pd.Series(dtype=float, name="trade_point_decision")

    # 計算價格變化
    price_change = price_series.diff()

    # 生成訊號
    signals = pd.Series(0, index=price_series.index, name="trade_point_decision")

    # 當價格上漲超過閾值時買入
    signals[price_change > threshold] = 1

    # 當價格下跌超過閾值時賣出
    signals[price_change < -threshold] = -1

    return signals


def continuous_trading_signal(price_series: pd.Series, window: int = 20) -> pd.Series:
    """
    連續交易訊號生成函數。

    基於滾動窗口內的價格動量生成連續的交易訊號。

    Args:
        price_series: 價格序列
        window: 滾動窗口大小

    Returns:
        連續交易訊號序列 (0-1之間的連續值)

    Example:
        >>> prices = pd.Series([100, 102, 104, 103, 105])
        >>> signals = continuous_trading_signal(prices, window=3)
    """
    if price_series.empty or window <= 0:
        return pd.Series(dtype=float, name="continuous_trading_signal")

    def generate_signal(s: np.ndarray) -> float:
        """
        生成單個窗口的訊號。

        Args:
            s: 價格窗口數組

        Returns:
            訊號強度 (0-1)
        """
        if len(s) == 0:
            return 0.0

        if s[0] < s[-1]:  # 上升趨勢
            smin = s.min()
            smax = s.max()
            if smax == smin:
                return 0.5
            return (s[-1] - smin) / (smax - smin) / 2 + 0.5
        else:  # 下降趨勢
            smin = s.min()
            smax = s.max()
            if smax == smin:
                return 0.0
            return (s[-1] - smin) / (smax - smin) / 2

    ret = price_series.rolling(window).apply(generate_signal, raw=True)
    ret.name = "continuous_trading_signal"
    return ret


def triple_barrier(
    price_series: pd.Series,
    upper_barrier: float = 1.1,
    lower_barrier: float = 0.9,
    max_period: int = 20
) -> pd.DataFrame:
    """
    三重障礙法訊號生成。

    基於上下障礙和時間障礙的三重條件生成交易訊號。

    Args:
        price_series: 價格序列
        upper_barrier: 上障礙比例 (相對於起始價格)
        lower_barrier: 下障礙比例 (相對於起始價格)
        max_period: 最大持有期間

    Returns:
        包含三重障礙結果的DataFrame，包含：
        - triple_barrier_profit: 利潤比例
        - triple_barrier_sell_time: 賣出時間
        - triple_barrier_signal: 訊號 (1=盈利, -1=虧損, 0=持平)

    Example:
        >>> prices = pd.Series([100, 105, 110, 95, 90])
        >>> result = triple_barrier(prices, upper_barrier=1.1, lower_barrier=0.9)
    """
    if price_series.empty or max_period <= 0:
        return pd.DataFrame(columns=[
            "triple_barrier_profit",
            "triple_barrier_sell_time",
            "triple_barrier_signal"
        ])

    def end_price(s: np.ndarray) -> float:
        """
        計算結束價格比例。

        Args:
            s: 價格窗口數組

        Returns:
            結束價格相對於起始價格的比例
        """
        if len(s) == 0 or s[0] == 0:
            return 1.0

        # 找到第一個觸及障礙的價格，如果沒有則使用最後一個價格
        barrier_hits = (s / s[0] > upper_barrier) | (s / s[0] < lower_barrier)
        if np.any(barrier_hits):
            hit_indices = np.where(barrier_hits)[0]
            return s[hit_indices[0]] / s[0]
        else:
            return s[-1] / s[0]

    def end_time(s: np.ndarray) -> int:
        """
        計算結束時間索引。

        Args:
            s: 價格窗口數組

        Returns:
            結束時間的索引
        """
        if len(s) == 0 or s[0] == 0:
            return max_period - 1

        # 找到第一個觸及障礙的時間，如果沒有則使用最大期間
        barrier_hits = (s / s[0] > upper_barrier) | (s / s[0] < lower_barrier)
        if np.any(barrier_hits):
            hit_indices = np.where(barrier_hits)[0]
            return hit_indices[0]
        else:
            return max_period - 1

    # 計算利潤比例
    p = (
        price_series.rolling(max_period)
        .apply(end_price, raw=True)
        .shift(-max_period + 1)
    )

    # 計算結束時間
    t = (
        price_series.rolling(max_period)
        .apply(end_time, raw=True)
        .shift(-max_period + 1)
    )

    # 將時間索引轉換為實際時間
    t = pd.Series([
        t.index[int(k + i)] if not math.isnan(k + i) and int(k + i) < len(t.index)
        else np.datetime64("NaT")
        for i, k in enumerate(t)
    ], index=t.index).dropna()

    # 創建結果DataFrame
    ret = pd.DataFrame({
        "triple_barrier_profit": p,
        "triple_barrier_sell_time": t,
        "triple_barrier_signal": 0,
    })

    # 生成訊號
    ret.loc[ret["triple_barrier_profit"] > upper_barrier, "triple_barrier_signal"] = 1
    ret.loc[ret["triple_barrier_profit"] < lower_barrier, "triple_barrier_signal"] = -1

    return ret


def fixed_time_horizon(price_series: pd.Series, window: int = 20) -> pd.Series:
    """
    固定時間範圍的交易訊號。

    基於統計學的均值回歸原理，在固定時間範圍內生成交易訊號。

    Args:
        price_series: 價格序列
        window: 時間窗口大小

    Returns:
        固定時間範圍的交易訊號 (1=買入, -1=賣出, 0=觀望)

    Example:
        >>> prices = pd.Series([100, 105, 110, 95, 90])
        >>> signals = fixed_time_horizon(prices, window=3)
    """
    if price_series.empty or window <= 0:
        return pd.Series(dtype=int, name=f"fixed_time_horizon_{window}")

    # 計算統計指標
    std = price_series.rolling(window * 4).std()
    mean = price_series.rolling(window * 4).mean()

    # 計算上下障礙
    upper_barrier = mean + 1.5 * std
    lower_barrier = mean - 1.5 * std

    # 生成訊號
    ret = pd.Series(0, index=price_series.index)

    # 當價格高於上障礙時賣出（均值回歸）
    ret[price_series > upper_barrier.shift(-window)] = -1

    # 當價格低於下障礙時買入（均值回歸）
    ret[price_series < lower_barrier.shift(-window)] = 1

    ret.name = f"fixed_time_horizon_{window}"
    return ret

@njit(fastmath=True, cache=True)
def numba_moving_average(arr: np.ndarray, window: int) -> np.ndarray:
    """
    使用Numba加速的移動平均計算。

    Args:
        arr: 價格數組
        window: 窗口大小

    Returns:
        移動平均數組

    Note:
        如果numba不可用，此函數將退化為普通Python函數
    """
    n = arr.shape[0]
    result = np.zeros(n, dtype=np.float64)
    s = 0.0

    for i in range(n):
        if i < window:
            s += arr[i]
            result[i] = s / (i + 1)
        else:
            s += arr[i] - arr[i - window]
            result[i] = s / window

    return result
