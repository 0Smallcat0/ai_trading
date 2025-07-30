# -*- coding: utf-8 -*-
"""
統計績效指標

此模組實現交易統計相關的指標計算，包括：
- 勝率 (Win Rate)
- 盈虧比 (Profit/Loss Ratio)
- 期望值 (Expectancy)
- 獲利因子 (Profit Factor)
- 恢復因子 (Recovery Factor)

Functions:
    calculate_win_rate: 計算勝率
    calculate_pnl_ratio: 計算盈虧比
    calculate_expectancy: 計算期望值
    calculate_profit_factor: 計算獲利因子
    calculate_recovery_factor: 計算恢復因子
"""

import logging
from typing import Union

import numpy as np
import pandas as pd

from src.config import LOG_LEVEL
from .utils import validate_performance_inputs

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


def calculate_win_rate(returns: Union[pd.Series, np.ndarray]) -> float:
    """
    計算勝率

    勝率是獲利交易次數佔總交易次數的比例：
    Win Rate = 獲利交易次數 / 總交易次數

    Args:
        returns: 收益率序列或交易損益序列

    Returns:
        勝率，範圍在0到1之間

    Raises:
        ValueError: 當輸入資料無效時

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        >>> win_rate = calculate_win_rate(returns)
        >>> print(f"Win Rate: {win_rate:.2%}")

    Note:
        勝率高不一定代表策略好，還需要考慮盈虧比
        建議與其他指標結合使用
    """
    # 驗證輸入
    validate_performance_inputs(returns)

    if len(returns) == 0:
        return 0.0

    try:
        # 計算獲利交易次數
        winning_trades = np.sum(returns > 0)
        total_trades = len(returns)

        # 計算勝率
        win_rate = winning_trades / total_trades

        return float(win_rate)

    except Exception as e:
        logger.error(f"計算勝率時發生錯誤: {e}")
        raise ValueError(f"勝率計算失敗: {e}") from e


def calculate_pnl_ratio(returns: Union[pd.Series, np.ndarray]) -> float:
    """
    計算盈虧比

    盈虧比是平均獲利與平均虧損的比值：
    P/L Ratio = 平均獲利 / |平均虧損|

    Args:
        returns: 收益率序列或交易損益序列

    Returns:
        盈虧比，數值越高表示獲利能力越強

    Raises:
        ValueError: 當輸入資料無效時

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        >>> pnl_ratio = calculate_pnl_ratio(returns)
        >>> print(f"P/L Ratio: {pnl_ratio:.2f}")

    Note:
        當沒有虧損交易時，返回無窮大
        當沒有獲利交易時，返回0
    """
    # 驗證輸入
    validate_performance_inputs(returns)

    if len(returns) == 0:
        return 0.0

    try:
        # 分離獲利和虧損交易
        winning_trades = returns[returns > 0]
        losing_trades = returns[returns < 0]

        # 計算平均獲利和平均虧損
        if len(winning_trades) == 0:
            return 0.0

        avg_win = np.mean(winning_trades)

        if len(losing_trades) == 0:
            return float("inf")

        avg_loss = np.mean(losing_trades)

        # 計算盈虧比
        pnl_ratio = avg_win / abs(avg_loss)

        return float(pnl_ratio)

    except Exception as e:
        logger.error(f"計算盈虧比時發生錯誤: {e}")
        raise ValueError(f"盈虧比計算失敗: {e}") from e


def calculate_expectancy(returns: Union[pd.Series, np.ndarray]) -> float:
    """
    計算期望值

    期望值是每筆交易的平均收益：
    Expectancy = (勝率 × 平均獲利) - (敗率 × |平均虧損|)

    Args:
        returns: 收益率序列或交易損益序列

    Returns:
        期望值，正值表示策略有正期望

    Raises:
        ValueError: 當輸入資料無效時

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        >>> expectancy = calculate_expectancy(returns)
        >>> print(f"Expectancy: {expectancy:.4f}")

    Note:
        期望值是評估交易策略長期表現的重要指標
        正期望值表示策略在長期內可能獲利
    """
    # 驗證輸入
    validate_performance_inputs(returns)

    if len(returns) == 0:
        return 0.0

    try:
        # 分離獲利和虧損交易
        winning_trades = returns[returns > 0]
        losing_trades = returns[returns < 0]

        # 計算勝率和敗率
        win_rate = len(winning_trades) / len(returns)
        loss_rate = len(losing_trades) / len(returns)

        # 計算平均獲利和平均虧損
        avg_win = np.mean(winning_trades) if len(winning_trades) > 0 else 0
        avg_loss = np.mean(losing_trades) if len(losing_trades) > 0 else 0

        # 計算期望值
        expectancy = (win_rate * avg_win) - (loss_rate * abs(avg_loss))

        return float(expectancy)

    except Exception as e:
        logger.error(f"計算期望值時發生錯誤: {e}")
        raise ValueError(f"期望值計算失敗: {e}") from e


def calculate_profit_factor(returns: Union[pd.Series, np.ndarray]) -> float:
    """
    計算獲利因子

    獲利因子是總獲利與總虧損的比值：
    Profit Factor = 總獲利 / |總虧損|

    Args:
        returns: 收益率序列或交易損益序列

    Returns:
        獲利因子，大於1表示總獲利大於總虧損

    Raises:
        ValueError: 當輸入資料無效時

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        >>> profit_factor = calculate_profit_factor(returns)
        >>> print(f"Profit Factor: {profit_factor:.2f}")

    Note:
        獲利因子大於1表示策略整體獲利
        數值越高表示獲利能力越強
    """
    # 驗證輸入
    validate_performance_inputs(returns)

    if len(returns) == 0:
        return 0.0

    try:
        # 計算總獲利和總虧損
        total_profit = np.sum(returns[returns > 0])
        total_loss = np.sum(returns[returns < 0])

        # 避免除以零
        if total_loss == 0:
            return float("inf") if total_profit > 0 else 0.0

        # 計算獲利因子
        profit_factor = total_profit / abs(total_loss)

        return float(profit_factor)

    except Exception as e:
        logger.error(f"計算獲利因子時發生錯誤: {e}")
        raise ValueError(f"獲利因子計算失敗: {e}") from e


def calculate_recovery_factor(returns: Union[pd.Series, np.ndarray]) -> float:
    """
    計算恢復因子

    恢復因子是總收益與最大回撤的比值：
    Recovery Factor = 總收益 / |最大回撤|

    Args:
        returns: 收益率序列

    Returns:
        恢復因子，數值越高表示回撤風險調整後收益越好

    Raises:
        ValueError: 當輸入資料無效時

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        >>> recovery_factor = calculate_recovery_factor(returns)
        >>> print(f"Recovery Factor: {recovery_factor:.2f}")

    Note:
        恢復因子類似於卡爾馬比率，但使用總收益而非年化收益
        適合評估策略的風險調整收益能力
    """
    # 驗證輸入
    validate_performance_inputs(returns)

    if len(returns) == 0:
        return 0.0

    try:
        # 計算總收益
        total_return = (1 + returns).prod() - 1

        # 計算最大回撤
        from .risk_metrics import calculate_max_drawdown

        max_drawdown = calculate_max_drawdown(returns)

        # 避免除以零
        if max_drawdown == 0:
            return float("inf") if total_return > 0 else 0.0

        # 計算恢復因子
        recovery_factor = total_return / abs(max_drawdown)

        return float(recovery_factor)

    except Exception as e:
        logger.error(f"計算恢復因子時發生錯誤: {e}")
        raise ValueError(f"恢復因子計算失敗: {e}") from e
