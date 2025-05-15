# -*- coding: utf-8 -*-
"""
績效指標模組

此模組提供各種金融和交易績效指標的計算功能，包括：
- 夏普比率 (Sharpe Ratio)
- 索提諾比率 (Sortino Ratio)
- 卡爾馬比率 (Calmar Ratio)
- 最大回撤 (Maximum Drawdown)
- 勝率 (Win Rate)
- 盈虧比 (Profit/Loss Ratio)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# 風險調整收益指標


def calculate_sharpe_ratio(
    returns: Union[pd.Series, np.ndarray],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    計算夏普比率

    夏普比率 = (年化收益率 - 無風險利率) / 年化波動率

    Args:
        returns (Union[pd.Series, np.ndarray]): 收益率序列
        risk_free_rate (float): 無風險利率
        periods_per_year (int): 每年期數，日頻為 252，週頻為 52，月頻為 12

    Returns:
        float: 夏普比率
    """
    if len(returns) == 0:
        return 0.0

    # 計算年化收益率
    annual_return = np.mean(returns) * periods_per_year

    # 計算年化波動率
    annual_volatility = np.std(returns) * np.sqrt(periods_per_year)

    # 避免除以零
    if annual_volatility == 0:
        return 0.0

    # 計算夏普比率
    sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility

    return sharpe_ratio


def calculate_sortino_ratio(
    returns: Union[pd.Series, np.ndarray],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
    target_return: float = 0.0,
) -> float:
    """
    計算索提諾比率

    索提諾比率 = (年化收益率 - 無風險利率) / 年化下行風險

    Args:
        returns (Union[pd.Series, np.ndarray]): 收益率序列
        risk_free_rate (float): 無風險利率
        periods_per_year (int): 每年期數，日頻為 252，週頻為 52，月頻為 12
        target_return (float): 目標收益率

    Returns:
        float: 索提諾比率
    """
    if len(returns) == 0:
        return 0.0

    # 計算年化收益率
    annual_return = np.mean(returns) * periods_per_year

    # 計算下行風險
    downside_returns = np.minimum(returns - target_return, 0)
    downside_risk = np.sqrt(np.mean(downside_returns**2)) * np.sqrt(periods_per_year)

    # 避免除以零
    if downside_risk == 0:
        return 0.0

    # 計算索提諾比率
    sortino_ratio = (annual_return - risk_free_rate) / downside_risk

    return sortino_ratio


def calculate_calmar_ratio(
    returns: Union[pd.Series, np.ndarray],
    prices: Optional[Union[pd.Series, np.ndarray]] = None,
    periods_per_year: int = 252,
) -> float:
    """
    計算卡爾馬比率

    卡爾馬比率 = 年化收益率 / 最大回撤

    Args:
        returns (Union[pd.Series, np.ndarray]): 收益率序列
        prices (Optional[Union[pd.Series, np.ndarray]]): 價格序列，如果提供則使用價格計算最大回撤
        periods_per_year (int): 每年期數，日頻為 252，週頻為 52，月頻為 12

    Returns:
        float: 卡爾馬比率
    """
    if len(returns) == 0:
        return 0.0

    # 計算年化收益率
    annual_return = np.mean(returns) * periods_per_year

    # 計算最大回撤
    max_drawdown = calculate_max_drawdown(returns, prices)

    # 避免除以零
    if max_drawdown == 0:
        return 0.0

    # 計算卡爾馬比率
    calmar_ratio = annual_return / abs(max_drawdown)

    return calmar_ratio


# 風險指標


def calculate_max_drawdown(
    returns: Union[pd.Series, np.ndarray],
    prices: Optional[Union[pd.Series, np.ndarray]] = None,
) -> float:
    """
    計算最大回撤

    最大回撤 = (最低點價格 - 最高點價格) / 最高點價格

    Args:
        returns (Union[pd.Series, np.ndarray]): 收益率序列
        prices (Optional[Union[pd.Series, np.ndarray]]): 價格序列，如果提供則使用價格計算最大回撤

    Returns:
        float: 最大回撤
    """
    if prices is not None:
        # 使用價格計算最大回撤
        cumulative_max = np.maximum.accumulate(prices)
        drawdown = (prices - cumulative_max) / cumulative_max
        max_drawdown = np.min(drawdown)
    else:
        # 使用收益率計算最大回撤
        cumulative_returns = (1 + returns).cumprod()
        cumulative_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - cumulative_max) / cumulative_max
        max_drawdown = np.min(drawdown)

    return max_drawdown


def calculate_volatility(
    returns: Union[pd.Series, np.ndarray], periods_per_year: int = 252
) -> float:
    """
    計算波動率

    波動率 = 收益率標準差 * sqrt(每年期數)

    Args:
        returns (Union[pd.Series, np.ndarray]): 收益率序列
        periods_per_year (int): 每年期數，日頻為 252，週頻為 52，月頻為 12

    Returns:
        float: 年化波動率
    """
    if len(returns) == 0:
        return 0.0

    # 計算年化波動率
    annual_volatility = np.std(returns) * np.sqrt(periods_per_year)

    return annual_volatility


def calculate_var(
    returns: Union[pd.Series, np.ndarray], confidence_level: float = 0.95
) -> float:
    """
    計算風險值 (Value at Risk)

    Args:
        returns (Union[pd.Series, np.ndarray]): 收益率序列
        confidence_level (float): 置信水平

    Returns:
        float: 風險值
    """
    if len(returns) == 0:
        return 0.0

    # 計算風險值
    var = np.percentile(returns, 100 * (1 - confidence_level))

    return var


# 交易統計指標


def calculate_win_rate(
    returns: Union[pd.Series, np.ndarray],
    trades: Optional[Union[pd.Series, np.ndarray]] = None,
) -> float:
    """
    計算勝率

    勝率 = 盈利交易次數 / 總交易次數

    Args:
        returns (Union[pd.Series, np.ndarray]): 收益率序列
        trades (Optional[Union[pd.Series, np.ndarray]]): 交易序列，如果提供則使用交易計算勝率

    Returns:
        float: 勝率
    """
    if trades is not None:
        # 使用交易計算勝率
        if len(trades) == 0:
            return 0.0

        win_trades = np.sum(trades > 0)
        total_trades = len(trades)
    else:
        # 使用收益率計算勝率
        if len(returns) == 0:
            return 0.0

        win_trades = np.sum(returns > 0)
        total_trades = len(returns)

    # 避免除以零
    if total_trades == 0:
        return 0.0

    # 計算勝率
    win_rate = win_trades / total_trades

    return win_rate


def calculate_pnl_ratio(
    returns: Union[pd.Series, np.ndarray],
    trades: Optional[Union[pd.Series, np.ndarray]] = None,
) -> float:
    """
    計算盈虧比

    盈虧比 = 平均盈利 / 平均虧損

    Args:
        returns (Union[pd.Series, np.ndarray]): 收益率序列
        trades (Optional[Union[pd.Series, np.ndarray]]): 交易序列，如果提供則使用交易計算盈虧比

    Returns:
        float: 盈虧比
    """
    if trades is not None:
        # 使用交易計算盈虧比
        if len(trades) == 0:
            return 0.0

        win_trades = trades[trades > 0]
        loss_trades = trades[trades < 0]
    else:
        # 使用收益率計算盈虧比
        if len(returns) == 0:
            return 0.0

        win_trades = returns[returns > 0]
        loss_trades = returns[returns < 0]

    # 計算平均盈利和平均虧損
    avg_win = np.mean(win_trades) if len(win_trades) > 0 else 0
    avg_loss = np.mean(loss_trades) if len(loss_trades) > 0 else 0

    # 避免除以零
    if avg_loss == 0:
        return 0.0

    # 計算盈虧比
    pnl_ratio = abs(avg_win / avg_loss)

    return pnl_ratio


def calculate_expectancy(
    returns: Union[pd.Series, np.ndarray],
    trades: Optional[Union[pd.Series, np.ndarray]] = None,
) -> float:
    """
    計算期望值

    期望值 = 勝率 * 平均盈利 - (1 - 勝率) * 平均虧損

    Args:
        returns (Union[pd.Series, np.ndarray]): 收益率序列
        trades (Optional[Union[pd.Series, np.ndarray]]): 交易序列，如果提供則使用交易計算期望值

    Returns:
        float: 期望值
    """
    if trades is not None:
        # 使用交易計算期望值
        if len(trades) == 0:
            return 0.0

        win_trades = trades[trades > 0]
        loss_trades = trades[trades < 0]

        win_rate = len(win_trades) / len(trades) if len(trades) > 0 else 0
    else:
        # 使用收益率計算期望值
        if len(returns) == 0:
            return 0.0

        win_trades = returns[returns > 0]
        loss_trades = returns[returns < 0]

        win_rate = len(win_trades) / len(returns) if len(returns) > 0 else 0

    # 計算平均盈利和平均虧損
    avg_win = np.mean(win_trades) if len(win_trades) > 0 else 0
    avg_loss = np.mean(loss_trades) if len(loss_trades) > 0 else 0

    # 計算期望值
    expectancy = win_rate * avg_win - (1 - win_rate) * abs(avg_loss)

    return expectancy


# 綜合指標


def calculate_all_metrics(
    returns: Union[pd.Series, np.ndarray],
    prices: Optional[Union[pd.Series, np.ndarray]] = None,
    trades: Optional[Union[pd.Series, np.ndarray]] = None,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> Dict[str, float]:
    """
    計算所有績效指標

    Args:
        returns (Union[pd.Series, np.ndarray]): 收益率序列
        prices (Optional[Union[pd.Series, np.ndarray]]): 價格序列
        trades (Optional[Union[pd.Series, np.ndarray]]): 交易序列
        risk_free_rate (float): 無風險利率
        periods_per_year (int): 每年期數，日頻為 252，週頻為 52，月頻為 12

    Returns:
        Dict[str, float]: 所有績效指標
    """
    metrics = {}

    # 風險調整收益指標
    metrics["sharpe_ratio"] = calculate_sharpe_ratio(
        returns, risk_free_rate, periods_per_year
    )
    metrics["sortino_ratio"] = calculate_sortino_ratio(
        returns, risk_free_rate, periods_per_year
    )
    metrics["calmar_ratio"] = calculate_calmar_ratio(returns, prices, periods_per_year)

    # 風險指標
    metrics["max_drawdown"] = calculate_max_drawdown(returns, prices)
    metrics["volatility"] = calculate_volatility(returns, periods_per_year)
    metrics["var_95"] = calculate_var(returns, 0.95)

    # 交易統計指標
    metrics["win_rate"] = calculate_win_rate(returns, trades)
    metrics["pnl_ratio"] = calculate_pnl_ratio(returns, trades)
    metrics["expectancy"] = calculate_expectancy(returns, trades)

    # 收益指標
    metrics["total_return"] = (1 + returns).prod() - 1 if len(returns) > 0 else 0.0
    metrics["annual_return"] = (
        np.mean(returns) * periods_per_year if len(returns) > 0 else 0.0
    )
    metrics["avg_return"] = np.mean(returns) if len(returns) > 0 else 0.0

    return metrics
