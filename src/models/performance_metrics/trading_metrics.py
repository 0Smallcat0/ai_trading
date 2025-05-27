# -*- coding: utf-8 -*-
"""
交易績效指標

此模組實現交易相關的績效指標計算，包括：
- 夏普比率 (Sharpe Ratio)
- 索提諾比率 (Sortino Ratio)
- 卡爾馬比率 (Calmar Ratio)
- 年化收益率計算
- 總收益率計算

Functions:
    calculate_sharpe_ratio: 計算夏普比率
    calculate_sortino_ratio: 計算索提諾比率
    calculate_calmar_ratio: 計算卡爾馬比率
    calculate_annual_return: 計算年化收益率
    calculate_total_return: 計算總收益率
"""

import logging
from typing import Optional, Union

import numpy as np
import pandas as pd

from src.config import LOG_LEVEL
from .utils import validate_performance_inputs

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


def calculate_sharpe_ratio(
    returns: Union[pd.Series, np.ndarray],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    計算夏普比率
    
    夏普比率衡量每單位風險的超額收益，計算公式為：
    Sharpe Ratio = (年化收益率 - 無風險利率) / 年化波動率

    Args:
        returns: 收益率序列，可以是日收益率、週收益率等
        risk_free_rate: 無風險利率，年化形式
        periods_per_year: 每年期數，日頻為252，週頻為52，月頻為12

    Returns:
        夏普比率，數值越高表示風險調整後收益越好
        
    Raises:
        ValueError: 當輸入資料無效時
        
    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        >>> sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        >>> print(f"Sharpe Ratio: {sharpe:.4f}")
        
    Note:
        當波動率為0時，返回0以避免除零錯誤
        建議使用至少一年的資料以獲得穩定的結果
    """
    # 驗證輸入
    validate_performance_inputs(returns)
    
    if len(returns) == 0:
        return 0.0

    try:
        # 計算年化收益率
        annual_return = np.mean(returns) * periods_per_year

        # 計算年化波動率
        annual_volatility = np.std(returns, ddof=1) * np.sqrt(periods_per_year)

        # 避免除以零
        if annual_volatility == 0:
            logger.warning("波動率為0，返回夏普比率0")
            return 0.0

        # 計算夏普比率
        sharpe_ratio = (annual_return - risk_free_rate) / annual_volatility

        return float(sharpe_ratio)
        
    except Exception as e:
        logger.error(f"計算夏普比率時發生錯誤: {e}")
        raise ValueError(f"夏普比率計算失敗: {e}") from e


def calculate_sortino_ratio(
    returns: Union[pd.Series, np.ndarray],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
    target_return: float = 0.0,
) -> float:
    """
    計算索提諾比率
    
    索提諾比率只考慮下行風險，計算公式為：
    Sortino Ratio = (年化收益率 - 無風險利率) / 年化下行風險

    Args:
        returns: 收益率序列
        risk_free_rate: 無風險利率，年化形式
        periods_per_year: 每年期數
        target_return: 目標收益率，用於計算下行風險

    Returns:
        索提諾比率，數值越高表示下行風險調整後收益越好
        
    Raises:
        ValueError: 當輸入資料無效時
        
    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        >>> sortino = calculate_sortino_ratio(returns, target_return=0.005)
        >>> print(f"Sortino Ratio: {sortino:.4f}")
        
    Note:
        索提諾比率相比夏普比率更關注下行風險
        適合評估追求穩定收益的策略
    """
    # 驗證輸入
    validate_performance_inputs(returns)
    
    if len(returns) == 0:
        return 0.0

    try:
        # 計算年化收益率
        annual_return = np.mean(returns) * periods_per_year

        # 計算下行風險
        downside_returns = np.minimum(returns - target_return, 0)
        downside_risk = np.sqrt(np.mean(downside_returns**2)) * np.sqrt(periods_per_year)

        # 避免除以零
        if downside_risk == 0:
            logger.warning("下行風險為0，返回索提諾比率0")
            return 0.0

        # 計算索提諾比率
        sortino_ratio = (annual_return - risk_free_rate) / downside_risk

        return float(sortino_ratio)
        
    except Exception as e:
        logger.error(f"計算索提諾比率時發生錯誤: {e}")
        raise ValueError(f"索提諾比率計算失敗: {e}") from e


def calculate_calmar_ratio(
    returns: Union[pd.Series, np.ndarray],
    prices: Optional[Union[pd.Series, np.ndarray]] = None,
    periods_per_year: int = 252,
) -> float:
    """
    計算卡爾馬比率
    
    卡爾馬比率衡量年化收益率與最大回撤的比值：
    Calmar Ratio = 年化收益率 / |最大回撤|

    Args:
        returns: 收益率序列
        prices: 價格序列，如果提供則使用價格計算最大回撤
        periods_per_year: 每年期數

    Returns:
        卡爾馬比率，數值越高表示回撤風險調整後收益越好
        
    Raises:
        ValueError: 當輸入資料無效時
        
    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        >>> calmar = calculate_calmar_ratio(returns)
        >>> print(f"Calmar Ratio: {calmar:.4f}")
        
    Note:
        當最大回撤為0時，返回0以避免除零錯誤
        適合評估長期投資策略的風險調整收益
    """
    # 驗證輸入
    validate_performance_inputs(returns)
    
    if len(returns) == 0:
        return 0.0

    try:
        # 計算年化收益率
        annual_return = np.mean(returns) * periods_per_year

        # 計算最大回撤
        from .risk_metrics import calculate_max_drawdown
        max_drawdown = calculate_max_drawdown(returns, prices)

        # 避免除以零
        if max_drawdown == 0:
            logger.warning("最大回撤為0，返回卡爾馬比率0")
            return 0.0

        # 計算卡爾馬比率
        calmar_ratio = annual_return / abs(max_drawdown)

        return float(calmar_ratio)
        
    except Exception as e:
        logger.error(f"計算卡爾馬比率時發生錯誤: {e}")
        raise ValueError(f"卡爾馬比率計算失敗: {e}") from e


def calculate_annual_return(
    returns: Union[pd.Series, np.ndarray],
    periods_per_year: int = 252,
    method: str = "arithmetic"
) -> float:
    """
    計算年化收益率
    
    Args:
        returns: 收益率序列
        periods_per_year: 每年期數
        method: 計算方法，"arithmetic"或"geometric"
        
    Returns:
        年化收益率
        
    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        >>> annual_ret = calculate_annual_return(returns, method="geometric")
    """
    validate_performance_inputs(returns)
    
    if len(returns) == 0:
        return 0.0
    
    try:
        if method == "arithmetic":
            return float(np.mean(returns) * periods_per_year)
        elif method == "geometric":
            cumulative_return = (1 + returns).prod()
            periods = len(returns)
            annual_return = (cumulative_return ** (periods_per_year / periods)) - 1
            return float(annual_return)
        else:
            raise ValueError(f"未知的計算方法: {method}")
            
    except Exception as e:
        logger.error(f"計算年化收益率時發生錯誤: {e}")
        raise ValueError(f"年化收益率計算失敗: {e}") from e


def calculate_total_return(
    returns: Union[pd.Series, np.ndarray]
) -> float:
    """
    計算總收益率
    
    Args:
        returns: 收益率序列
        
    Returns:
        總收益率
        
    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        >>> total_ret = calculate_total_return(returns)
    """
    validate_performance_inputs(returns)
    
    if len(returns) == 0:
        return 0.0
    
    try:
        total_return = (1 + returns).prod() - 1
        return float(total_return)
        
    except Exception as e:
        logger.error(f"計算總收益率時發生錯誤: {e}")
        raise ValueError(f"總收益率計算失敗: {e}") from e
