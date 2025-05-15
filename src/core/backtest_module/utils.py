"""
回測工具模組

此模組提供回測過程中使用的工具函數，包括資料處理、績效計算等。
"""

import numpy as np
import pandas as pd

__all__ = [
    "detect_close_col",
    "ensure_multiindex",
    "calculate_sharpe",
    "calculate_max_drawdown",
    "align_timeseries",
]


def detect_close_col(df):
    """
    自動偵測收盤價欄位名稱

    Args:
        df (pd.DataFrame): 價格資料 DataFrame

    Returns:
        str: 收盤價欄位名稱

    Raises:
        ValueError: 如果找不到收盤價欄位
    """
    for col in ["收盤價", "close", "Close"]:
        if col in df.columns:
            return col
    raise ValueError("價格資料必須包含 '收盤價' 或 'close' 欄位")


def ensure_multiindex(df):
    """
    確保 index 為 (stock_id, date) MultiIndex

    Args:
        df (pd.DataFrame): 輸入的 DataFrame

    Returns:
        pd.DataFrame: 設置好 MultiIndex 的 DataFrame

    Raises:
        ValueError: 如果無法設置 MultiIndex
    """
    if isinstance(df.index, pd.MultiIndex):
        return df
    elif "stock_id" in df.columns and "date" in df.columns:
        return df.set_index(["stock_id", "date"])
    else:
        raise ValueError("資料必須有 MultiIndex 或包含 'stock_id' 和 'date' 欄位")


def calculate_sharpe(equity_curve, risk_free_rate=0.0, periods_per_year=252):
    """
    計算夏普比率

    Args:
        equity_curve (pd.Series): 權益曲線
        risk_free_rate (float): 無風險利率
        periods_per_year (int): 每年期數，日頻為 252，週頻為 52，月頻為 12

    Returns:
        float: 夏普比率
    """
    returns = equity_curve.pct_change().dropna()
    annual_return = returns.mean() * periods_per_year
    annual_volatility = returns.std() * np.sqrt(periods_per_year)
    sharpe = (
        (annual_return - risk_free_rate) / annual_volatility
        if annual_volatility != 0
        else 0
    )
    return sharpe


def calculate_max_drawdown(equity_curve):
    """
    計算最大回撤

    Args:
        equity_curve (pd.Series): 權益曲線

    Returns:
        float: 最大回撤
    """
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1
    max_drawdown = drawdown.min()
    return max_drawdown


def align_timeseries(df1, df2):
    """
    對齊兩個時間序列的索引

    Args:
        df1 (pd.DataFrame): 第一個 DataFrame
        df2 (pd.DataFrame): 第二個 DataFrame

    Returns:
        tuple: 對齊後的 (df1, df2)
    """
    common_index = df1.index.intersection(df2.index)
    return df1.loc[common_index], df2.loc[common_index]
