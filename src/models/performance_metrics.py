# -*- coding: utf-8 -*-
"""
績效指標模組 (向後兼容)

此模組提供績效指標計算功能的向後兼容介面。
新的模組化實現位於 performance_metrics 子模組中。

Functions:
    calculate_all_metrics: 計算所有績效指標（向後兼容）
    calculate_sharpe_ratio: 計算夏普比率（向後兼容）
    calculate_sortino_ratio: 計算索提諾比率（向後兼容）
    calculate_calmar_ratio: 計算卡爾馬比率（向後兼容）
    calculate_max_drawdown: 計算最大回撤（向後兼容）
    calculate_volatility: 計算波動率（向後兼容）
    calculate_var: 計算風險值（向後兼容）
    calculate_win_rate: 計算勝率（向後兼容）
    calculate_pnl_ratio: 計算盈虧比（向後兼容）
    calculate_expectancy: 計算期望值（向後兼容）

Example:
    >>> from src.models.performance_metrics import calculate_all_metrics
    >>> metrics = calculate_all_metrics(returns, risk_free_rate=0.02)
    >>> print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.4f}")

Note:
    建議使用新的模組化介面：
    from src.models.performance_metrics import calculate_sharpe_ratio
"""

import warnings
from typing import Dict, Optional, Union

import numpy as np
import pandas as pd

# 導入新的模組化實現
from .performance_metrics.legacy_interface import calculate_all_metrics as _calculate_all_metrics
from .performance_metrics.trading_metrics import (
    calculate_sharpe_ratio as _calculate_sharpe_ratio,
    calculate_sortino_ratio as _calculate_sortino_ratio,
    calculate_calmar_ratio as _calculate_calmar_ratio
)
from .performance_metrics.risk_metrics import (
    calculate_max_drawdown as _calculate_max_drawdown,
    calculate_volatility as _calculate_volatility,
    calculate_var as _calculate_var
)
from .performance_metrics.statistical_metrics import (
    calculate_win_rate as _calculate_win_rate,
    calculate_pnl_ratio as _calculate_pnl_ratio,
    calculate_expectancy as _calculate_expectancy
)

# 向後兼容的函數介面


def calculate_sharpe_ratio(
    returns: Union[pd.Series, np.ndarray],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    計算夏普比率 (向後兼容函數)

    夏普比率 = (年化收益率 - 無風險利率) / 年化波動率

    Args:
        returns: 收益率序列
        risk_free_rate: 無風險利率
        periods_per_year: 每年期數，日頻為 252，週頻為 52，月頻為 12

    Returns:
        夏普比率

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015])
        >>> sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
    """
    return _calculate_sharpe_ratio(returns, risk_free_rate, periods_per_year)


def calculate_sortino_ratio(
    returns: Union[pd.Series, np.ndarray],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
    target_return: float = 0.0,
) -> float:
    """
    計算索提諾比率 (向後兼容函數)

    索提諾比率 = (年化收益率 - 無風險利率) / 年化下行風險

    Args:
        returns: 收益率序列
        risk_free_rate: 無風險利率
        periods_per_year: 每年期數
        target_return: 目標收益率

    Returns:
        索提諾比率

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015])
        >>> sortino = calculate_sortino_ratio(returns, target_return=0.005)
    """
    return _calculate_sortino_ratio(returns, risk_free_rate, periods_per_year, target_return)


def calculate_calmar_ratio(
    returns: Union[pd.Series, np.ndarray],
    prices: Optional[Union[pd.Series, np.ndarray]] = None,
    periods_per_year: int = 252,
) -> float:
    """
    計算卡爾馬比率 (向後兼容函數)

    卡爾馬比率 = 年化收益率 / 最大回撤

    Args:
        returns: 收益率序列
        prices: 價格序列
        periods_per_year: 每年期數

    Returns:
        卡爾馬比率

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015])
        >>> calmar = calculate_calmar_ratio(returns)
    """
    return _calculate_calmar_ratio(returns, prices, periods_per_year)


def calculate_max_drawdown(
    returns: Union[pd.Series, np.ndarray],
    prices: Optional[Union[pd.Series, np.ndarray]] = None,
) -> float:
    """
    計算最大回撤 (向後兼容函數)

    最大回撤 = (最低點價格 - 最高點價格) / 最高點價格

    Args:
        returns: 收益率序列
        prices: 價格序列

    Returns:
        最大回撤

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015])
        >>> max_dd = calculate_max_drawdown(returns)
    """
    return _calculate_max_drawdown(returns, prices)


def calculate_volatility(
    returns: Union[pd.Series, np.ndarray],
    periods_per_year: int = 252
) -> float:
    """
    計算波動率 (向後兼容函數)

    波動率 = 收益率標準差 * sqrt(每年期數)

    Args:
        returns: 收益率序列
        periods_per_year: 每年期數

    Returns:
        年化波動率

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015])
        >>> vol = calculate_volatility(returns)
    """
    return _calculate_volatility(returns, periods_per_year)


def calculate_var(
    returns: Union[pd.Series, np.ndarray],
    confidence_level: float = 0.95
) -> float:
    """
    計算風險值 (向後兼容函數)

    Args:
        returns: 收益率序列
        confidence_level: 置信水平

    Returns:
        風險值

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015])
        >>> var_95 = calculate_var(returns, confidence_level=0.95)
    """
    return _calculate_var(returns, confidence_level)


def calculate_win_rate(
    returns: Union[pd.Series, np.ndarray],
    trades: Optional[Union[pd.Series, np.ndarray]] = None,
) -> float:
    """
    計算勝率 (向後兼容函數)

    勝率 = 盈利交易次數 / 總交易次數

    Args:
        returns: 收益率序列
        trades: 交易序列（可選）

    Returns:
        勝率

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015])
        >>> win_rate = calculate_win_rate(returns)
    """
    # 使用交易序列或收益率序列
    analysis_data = trades if trades is not None else returns
    return _calculate_win_rate(analysis_data)


def calculate_pnl_ratio(
    returns: Union[pd.Series, np.ndarray],
    trades: Optional[Union[pd.Series, np.ndarray]] = None,
) -> float:
    """
    計算盈虧比 (向後兼容函數)

    盈虧比 = 平均盈利 / 平均虧損

    Args:
        returns: 收益率序列
        trades: 交易序列（可選）

    Returns:
        盈虧比

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015])
        >>> pnl_ratio = calculate_pnl_ratio(returns)
    """
    # 使用交易序列或收益率序列
    analysis_data = trades if trades is not None else returns
    return _calculate_pnl_ratio(analysis_data)


def calculate_expectancy(
    returns: Union[pd.Series, np.ndarray],
    trades: Optional[Union[pd.Series, np.ndarray]] = None,
) -> float:
    """
    計算期望值 (向後兼容函數)

    期望值 = 勝率 * 平均盈利 - (1 - 勝率) * 平均虧損

    Args:
        returns: 收益率序列
        trades: 交易序列（可選）

    Returns:
        期望值

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015])
        >>> expectancy = calculate_expectancy(returns)
    """
    # 使用交易序列或收益率序列
    analysis_data = trades if trades is not None else returns
    return _calculate_expectancy(analysis_data)


def calculate_all_metrics(
    returns: Union[pd.Series, np.ndarray],
    prices: Optional[Union[pd.Series, np.ndarray]] = None,
    trades: Optional[Union[pd.Series, np.ndarray]] = None,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
    **kwargs
) -> Dict[str, float]:
    """
    計算所有績效指標 (向後兼容函數)

    Args:
        returns: 收益率序列
        prices: 價格序列（可選）
        trades: 交易序列（可選）
        risk_free_rate: 無風險利率
        periods_per_year: 每年期數
        **kwargs: 其他參數

    Returns:
        所有績效指標的字典

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015])
        >>> metrics = calculate_all_metrics(returns, risk_free_rate=0.02)
        >>> print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.4f}")
    """
    return _calculate_all_metrics(
        returns=returns,
        prices=prices,
        trades=trades,
        risk_free_rate=risk_free_rate,
        periods_per_year=periods_per_year,
        **kwargs
    )
