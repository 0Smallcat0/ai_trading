# -*- coding: utf-8 -*-
"""
簡化性能指標模組 - MVP版本

提供回測分析所需的基本性能指標計算功能。
此為簡化版本，移除了複雜的機器學習相關功能。

Functions:
    calculate_all_metrics: 計算所有基本性能指標
    calculate_sharpe_ratio: 計算夏普比率
    calculate_max_drawdown: 計算最大回撤
    calculate_volatility: 計算波動率

Example:
    >>> from src.models.performance_metrics import calculate_all_metrics
    >>> metrics = calculate_all_metrics(returns, risk_free_rate=0.02)
    >>> print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.4f}")
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Union

def calculate_sharpe_ratio(returns: Union[pd.Series, np.ndarray],
                          risk_free_rate: float = 0.0) -> float:
    """
    計算夏普比率

    Args:
        returns: 收益率序列
        risk_free_rate: 無風險利率

    Returns:
        float: 夏普比率
    """
    if isinstance(returns, pd.Series):
        returns = returns.values

    if len(returns) == 0:
        return 0.0

    excess_returns = returns - risk_free_rate
    if np.std(excess_returns) == 0:
        return 0.0

    return np.mean(excess_returns) / np.std(excess_returns)


def calculate_max_drawdown(returns: Union[pd.Series, np.ndarray]) -> float:
    """
    計算最大回撤

    Args:
        returns: 收益率序列

    Returns:
        float: 最大回撤
    """
    if isinstance(returns, pd.Series):
        returns = returns.values

    if len(returns) == 0:
        return 0.0

    cumulative = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max

    return abs(np.min(drawdown))


def calculate_volatility(returns: Union[pd.Series, np.ndarray]) -> float:
    """
    計算波動率

    Args:
        returns: 收益率序列

    Returns:
        float: 波動率
    """
    if isinstance(returns, pd.Series):
        returns = returns.values

    if len(returns) == 0:
        return 0.0

    return np.std(returns)


def calculate_total_return(returns: Union[pd.Series, np.ndarray]) -> float:
    """
    計算總收益率

    Args:
        returns: 收益率序列

    Returns:
        float: 總收益率
    """
    if isinstance(returns, pd.Series):
        returns = returns.values

    if len(returns) == 0:
        return 0.0

    return np.prod(1 + returns) - 1


def calculate_all_metrics(returns: Union[pd.Series, np.ndarray],
                         risk_free_rate: float = 0.0) -> Dict[str, float]:
    """
    計算所有基本性能指標

    Args:
        returns: 收益率序列
        risk_free_rate: 無風險利率

    Returns:
        Dict[str, float]: 包含所有指標的字典
    """
    if isinstance(returns, pd.Series):
        returns = returns.values

    if len(returns) == 0:
        return {
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'volatility': 0.0,
            'win_rate': 0.0,
            'num_trades': 0
        }

    # 計算基本指標
    total_return = calculate_total_return(returns)
    sharpe_ratio = calculate_sharpe_ratio(returns, risk_free_rate)
    max_drawdown = calculate_max_drawdown(returns)
    volatility = calculate_volatility(returns)

    # 計算勝率
    positive_returns = returns[returns > 0]
    win_rate = len(positive_returns) / len(returns) if len(returns) > 0 else 0.0

    return {
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'volatility': volatility,
        'win_rate': win_rate,
        'num_trades': len(returns)
    }


# 向後兼容性別名
def calculate_performance_metrics(returns: Union[pd.Series, np.ndarray],
                                 risk_free_rate: float = 0.0) -> Dict[str, float]:
    """向後兼容性別名"""
    return calculate_all_metrics(returns, risk_free_rate)
