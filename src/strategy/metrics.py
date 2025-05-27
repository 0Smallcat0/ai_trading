# -*- coding: utf-8 -*-
"""策略評估指標模組

此模組提供策略評估的各種指標計算功能。

主要功能：
- 收益率計算
- 風險指標計算
- 績效指標計算
"""

import logging
import numpy as np
import pandas as pd

# 設定日誌
logger = logging.getLogger(__name__)


def calculate_returns(signals: pd.DataFrame, price_data: pd.DataFrame) -> pd.Series:
    """計算策略收益率。

    Args:
        signals: 訊號資料
        price_data: 價格資料

    Returns:
        策略收益率序列
    """
    # 計算每日收益率
    daily_returns = price_data["收盤價"].astype(float).pct_change()

    # 根據訊號計算策略收益率
    strategy_returns = signals["signal"].shift(1) * daily_returns

    return strategy_returns.fillna(0)


def calculate_total_return(returns: pd.Series) -> float:
    """計算總收益率。

    Args:
        returns: 收益率序列

    Returns:
        總收益率
    """
    cumulative_returns = (1 + returns).cumprod()
    return float(cumulative_returns.iloc[-1] - 1) if not cumulative_returns.empty else 0.0


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """計算夏普比率。

    Args:
        returns: 收益率序列
        risk_free_rate: 無風險利率

    Returns:
        夏普比率
    """
    if returns.empty or returns.std() == 0:
        return 0.0

    excess_returns = returns.mean() - risk_free_rate / 252
    return float(excess_returns / returns.std() * np.sqrt(252))


def calculate_max_drawdown(returns: pd.Series) -> float:
    """計算最大回撤。

    Args:
        returns: 收益率序列

    Returns:
        最大回撤（負值）
    """
    if returns.empty:
        return 0.0

    cumulative_returns = (1 + returns).cumprod()
    running_max = cumulative_returns.cummax()
    drawdown = cumulative_returns / running_max - 1

    return float(drawdown.min())


def calculate_win_rate(returns: pd.Series) -> float:
    """計算勝率。

    Args:
        returns: 收益率序列

    Returns:
        勝率（0-1之間）
    """
    if returns.empty:
        return 0.0

    winning_trades = (returns > 0).sum()
    total_trades = (returns != 0).sum()

    return float(winning_trades / total_trades) if total_trades > 0 else 0.0


def calculate_volatility(returns: pd.Series) -> float:
    """計算年化波動率。

    Args:
        returns: 收益率序列

    Returns:
        年化波動率
    """
    if returns.empty:
        return 0.0

    return float(returns.std() * np.sqrt(252))


def calculate_all_metrics(
    signals: pd.DataFrame,
    price_data: pd.DataFrame
) -> dict:
    """計算所有策略評估指標。

    Args:
        signals: 訊號資料
        price_data: 價格資料

    Returns:
        包含所有指標的字典
    """
    returns = calculate_returns(signals, price_data)

    return {
        "total_return": calculate_total_return(returns),
        "sharpe_ratio": calculate_sharpe_ratio(returns),
        "max_drawdown": calculate_max_drawdown(returns),
        "win_rate": calculate_win_rate(returns),
        "volatility": calculate_volatility(returns)
    }
