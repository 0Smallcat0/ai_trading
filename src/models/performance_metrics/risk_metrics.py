# -*- coding: utf-8 -*-
"""
風險指標

此模組實現風險相關的指標計算，包括：
- 最大回撤 (Maximum Drawdown)
- 波動率 (Volatility)
- 風險值 (Value at Risk, VaR)
- 條件風險值 (Conditional VaR, CVaR)
- 下行風險 (Downside Risk)

Functions:
    calculate_max_drawdown: 計算最大回撤
    calculate_volatility: 計算波動率
    calculate_var: 計算風險值
    calculate_cvar: 計算條件風險值
    calculate_downside_risk: 計算下行風險
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


def calculate_max_drawdown(
    returns: Union[pd.Series, np.ndarray],
    prices: Optional[Union[pd.Series, np.ndarray]] = None,
) -> float:
    """
    計算最大回撤
    
    最大回撤是投資組合從峰值到谷值的最大跌幅：
    Max Drawdown = (最低點價格 - 最高點價格) / 最高點價格

    Args:
        returns: 收益率序列
        prices: 價格序列，如果提供則使用價格計算最大回撤

    Returns:
        最大回撤，負值表示損失程度
        
    Raises:
        ValueError: 當輸入資料無效時
        
    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        >>> max_dd = calculate_max_drawdown(returns)
        >>> print(f"Max Drawdown: {max_dd:.4f}")
        
    Note:
        最大回撤是衡量投資風險的重要指標
        數值越接近0表示風險越小
    """
    # 驗證輸入
    validate_performance_inputs(returns)
    
    if len(returns) == 0:
        return 0.0

    try:
        if prices is not None:
            # 使用價格計算最大回撤
            validate_performance_inputs(prices)
            if len(prices) != len(returns):
                raise ValueError("價格序列和收益率序列長度必須相同")
                
            cumulative_max = np.maximum.accumulate(prices)
            drawdown = (prices - cumulative_max) / cumulative_max
            max_drawdown = np.min(drawdown)
        else:
            # 使用收益率計算最大回撤
            cumulative_returns = (1 + returns).cumprod()
            cumulative_max = np.maximum.accumulate(cumulative_returns)
            drawdown = (cumulative_returns - cumulative_max) / cumulative_max
            max_drawdown = np.min(drawdown)

        return float(max_drawdown)
        
    except Exception as e:
        logger.error(f"計算最大回撤時發生錯誤: {e}")
        raise ValueError(f"最大回撤計算失敗: {e}") from e


def calculate_volatility(
    returns: Union[pd.Series, np.ndarray], 
    periods_per_year: int = 252
) -> float:
    """
    計算年化波動率
    
    波動率衡量收益率的變動程度：
    Volatility = 收益率標準差 * sqrt(每年期數)

    Args:
        returns: 收益率序列
        periods_per_year: 每年期數，日頻為252，週頻為52，月頻為12

    Returns:
        年化波動率，數值越高表示風險越大
        
    Raises:
        ValueError: 當輸入資料無效時
        
    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        >>> vol = calculate_volatility(returns)
        >>> print(f"Volatility: {vol:.4f}")
        
    Note:
        使用樣本標準差（ddof=1）進行計算
        建議使用至少30個觀測值以獲得穩定結果
    """
    # 驗證輸入
    validate_performance_inputs(returns)
    
    if len(returns) == 0:
        return 0.0

    try:
        # 計算年化波動率
        annual_volatility = np.std(returns, ddof=1) * np.sqrt(periods_per_year)
        return float(annual_volatility)
        
    except Exception as e:
        logger.error(f"計算波動率時發生錯誤: {e}")
        raise ValueError(f"波動率計算失敗: {e}") from e


def calculate_var(
    returns: Union[pd.Series, np.ndarray], 
    confidence_level: float = 0.95
) -> float:
    """
    計算風險值 (Value at Risk)
    
    VaR表示在給定置信水平下，投資組合在特定時間內的最大可能損失。

    Args:
        returns: 收益率序列
        confidence_level: 置信水平，通常為0.95或0.99

    Returns:
        風險值，負值表示潛在損失
        
    Raises:
        ValueError: 當輸入資料無效時
        
    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        >>> var_95 = calculate_var(returns, confidence_level=0.95)
        >>> print(f"VaR (95%): {var_95:.4f}")
        
    Note:
        使用歷史模擬法計算VaR
        置信水平越高，VaR的絕對值越大
    """
    # 驗證輸入
    validate_performance_inputs(returns)
    
    if len(returns) == 0:
        return 0.0
        
    if not 0 < confidence_level < 1:
        raise ValueError("置信水平必須在0和1之間")

    try:
        # 計算風險值
        var = np.percentile(returns, 100 * (1 - confidence_level))
        return float(var)
        
    except Exception as e:
        logger.error(f"計算VaR時發生錯誤: {e}")
        raise ValueError(f"VaR計算失敗: {e}") from e


def calculate_cvar(
    returns: Union[pd.Series, np.ndarray], 
    confidence_level: float = 0.95
) -> float:
    """
    計算條件風險值 (Conditional VaR / Expected Shortfall)
    
    CVaR是超過VaR的損失的期望值，提供了尾部風險的更完整描述。

    Args:
        returns: 收益率序列
        confidence_level: 置信水平

    Returns:
        條件風險值，負值表示潛在損失
        
    Raises:
        ValueError: 當輸入資料無效時
        
    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        >>> cvar_95 = calculate_cvar(returns, confidence_level=0.95)
        >>> print(f"CVaR (95%): {cvar_95:.4f}")
        
    Note:
        CVaR總是小於等於VaR（絕對值更大）
        CVaR是一致性風險度量，具有更好的數學性質
    """
    # 驗證輸入
    validate_performance_inputs(returns)
    
    if len(returns) == 0:
        return 0.0
        
    if not 0 < confidence_level < 1:
        raise ValueError("置信水平必須在0和1之間")

    try:
        # 計算VaR
        var = calculate_var(returns, confidence_level)
        
        # 計算CVaR（超過VaR的損失的期望值）
        tail_losses = returns[returns <= var]
        
        if len(tail_losses) == 0:
            return var
            
        cvar = np.mean(tail_losses)
        return float(cvar)
        
    except Exception as e:
        logger.error(f"計算CVaR時發生錯誤: {e}")
        raise ValueError(f"CVaR計算失敗: {e}") from e


def calculate_downside_risk(
    returns: Union[pd.Series, np.ndarray],
    target_return: float = 0.0,
    periods_per_year: int = 252
) -> float:
    """
    計算下行風險
    
    下行風險只考慮低於目標收益率的波動性：
    Downside Risk = sqrt(E[(min(R - T, 0))^2]) * sqrt(periods_per_year)

    Args:
        returns: 收益率序列
        target_return: 目標收益率
        periods_per_year: 每年期數

    Returns:
        年化下行風險
        
    Raises:
        ValueError: 當輸入資料無效時
        
    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        >>> downside_risk = calculate_downside_risk(returns, target_return=0.005)
        >>> print(f"Downside Risk: {downside_risk:.4f}")
        
    Note:
        下行風險用於計算索提諾比率
        只關注負面波動，忽略正面波動
    """
    # 驗證輸入
    validate_performance_inputs(returns)
    
    if len(returns) == 0:
        return 0.0

    try:
        # 計算下行偏差
        downside_returns = np.minimum(returns - target_return, 0)
        
        # 計算下行風險
        downside_variance = np.mean(downside_returns**2)
        downside_risk = np.sqrt(downside_variance) * np.sqrt(periods_per_year)
        
        return float(downside_risk)
        
    except Exception as e:
        logger.error(f"計算下行風險時發生錯誤: {e}")
        raise ValueError(f"下行風險計算失敗: {e}") from e
