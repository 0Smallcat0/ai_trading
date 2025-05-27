"""投資組合工具函數模組

此模組包含投資組合相關的工具函數和常數定義。

主要功能：
- 依賴套件檢查
- 常用工具函數
- 資料驗證函數
"""

import logging
from typing import Dict, Optional
import pandas as pd
import numpy as np

# 設定日誌
logger = logging.getLogger(__name__)

# 可選依賴處理
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None

try:
    import scipy.optimize as sco
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    sco = None

try:
    import seaborn as sns
    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False
    sns = None

try:
    from pypfopt import EfficientFrontier, expected_returns, risk_models
    PYPFOPT_AVAILABLE = True
except ImportError:
    PYPFOPT_AVAILABLE = False
    EfficientFrontier = None
    expected_returns = None
    risk_models = None


def validate_signals(signals: pd.DataFrame) -> bool:
    """驗證交易訊號資料格式

    Args:
        signals: 交易訊號資料

    Returns:
        是否為有效格式

    Raises:
        ValueError: 當資料格式不正確時
    """
    if not isinstance(signals, pd.DataFrame):
        raise ValueError("signals 必須為 pandas.DataFrame")
    
    if signals.index.nlevels < 1:
        raise ValueError("signals 必須有至少一層 index (建議為 MultiIndex: stock_id, date)")
    
    if "buy_signal" not in signals.columns and "signal" not in signals.columns:
        raise ValueError("signals 必須包含 'buy_signal' 或 'signal' 欄位")
    
    return True


def validate_prices(prices: pd.DataFrame) -> bool:
    """驗證價格資料格式

    Args:
        prices: 價格資料

    Returns:
        是否為有效格式

    Raises:
        ValueError: 當資料格式不正確時
    """
    if not isinstance(prices, pd.DataFrame):
        raise ValueError("prices 必須為 pandas.DataFrame")
    
    if "close" not in prices.columns and "收盤價" not in prices.columns:
        raise ValueError("價格資料必須包含 'close' 或 '收盤價' 欄位")
    
    return True


def get_price_column(prices: pd.DataFrame) -> str:
    """獲取價格欄位名稱

    Args:
        prices: 價格資料

    Returns:
        價格欄位名稱
    """
    if "close" in prices.columns:
        return "close"
    elif "收盤價" in prices.columns:
        return "收盤價"
    else:
        raise ValueError("價格資料必須包含 'close' 或 '收盤價' 欄位")


def get_buy_signals(signals: pd.DataFrame) -> pd.DataFrame:
    """獲取買入訊號

    Args:
        signals: 交易訊號資料

    Returns:
        買入訊號資料
    """
    if "buy_signal" in signals.columns:
        return signals[signals["buy_signal"] == 1]
    else:
        return signals[signals["signal"] > 0]


def calculate_equal_weights(stocks: list) -> Dict[str, float]:
    """計算等權重

    Args:
        stocks: 股票列表

    Returns:
        等權重字典
    """
    if len(stocks) == 0:
        return {}
    
    weight = 1.0 / len(stocks)
    return {stock: weight for stock in stocks}


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    """標準化權重，使其總和為1

    Args:
        weights: 權重字典

    Returns:
        標準化後的權重字典
    """
    total_weight = sum(weights.values())
    if total_weight == 0:
        return weights
    
    return {stock: weight / total_weight for stock, weight in weights.items()}


def validate_weights(weights: Dict[str, float], tolerance: float = 1e-6) -> bool:
    """驗證權重是否有效

    Args:
        weights: 權重字典
        tolerance: 容差

    Returns:
        是否為有效權重

    Raises:
        ValueError: 當權重無效時
    """
    if not weights:
        return True
    
    # 檢查權重是否為非負數
    for stock, weight in weights.items():
        if weight < 0:
            raise ValueError(f"權重不能為負數: {stock} = {weight}")
        if weight > 1:
            raise ValueError(f"權重不能超過1: {stock} = {weight}")
    
    # 檢查權重總和是否接近1
    total_weight = sum(weights.values())
    if abs(total_weight - 1.0) > tolerance:
        raise ValueError(f"權重總和必須為1，當前為: {total_weight}")
    
    return True


def calculate_portfolio_returns(
    weights: pd.DataFrame, 
    prices: pd.DataFrame
) -> pd.Series:
    """計算投資組合收益率

    Args:
        weights: 投資組合權重
        prices: 價格資料

    Returns:
        投資組合收益率序列
    """
    # 確定價格欄位
    price_col = get_price_column(prices)
    
    # 計算每日收益率
    daily_returns = prices[price_col].pct_change()
    
    # 計算投資組合收益率
    portfolio_returns = pd.Series(
        0.0, index=daily_returns.index.get_level_values("date").unique()
    )
    
    for date in portfolio_returns.index:
        # 獲取該日期的權重
        date_weights = (
            weights.xs(date, level="date", drop_level=False)
            if date in weights.index.get_level_values("date")
            else pd.DataFrame()
        )
        
        if date_weights.empty:
            continue
        
        # 獲取該日期的收益率
        date_returns = daily_returns.xs(date, level="date", drop_level=False)
        
        # 計算該日期的投資組合收益率
        portfolio_return = 0.0
        for stock_id, stock_weight in date_weights["weight"].items():
            if (stock_id, date) in date_returns.index:
                portfolio_return += (
                    stock_weight * date_returns.loc[(stock_id, date)]
                )
        
        portfolio_returns[date] = portfolio_return
    
    return portfolio_returns


def calculate_performance_metrics(returns: pd.Series) -> Dict[str, float]:
    """計算績效指標

    Args:
        returns: 收益率序列

    Returns:
        績效指標字典
    """
    if returns.empty:
        return {}
    
    # 計算累積收益率
    cumulative_returns = (1 + returns).cumprod()
    
    # 計算年化收益率
    annual_return = returns.mean() * 252
    
    # 計算年化波動率
    annual_volatility = returns.std() * np.sqrt(252)
    
    # 計算夏普比率
    sharpe_ratio = (
        annual_return / annual_volatility if annual_volatility != 0 else 0
    )
    
    # 計算最大回撤
    max_drawdown = (cumulative_returns / cumulative_returns.cummax() - 1).min()
    
    return {
        "cumulative_returns": cumulative_returns.iloc[-1] if not cumulative_returns.empty else 1.0,
        "annual_return": annual_return,
        "annual_volatility": annual_volatility,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
    }


def check_data_sufficiency(
    historical_returns: pd.DataFrame, 
    min_periods: int = 30
) -> bool:
    """檢查歷史資料是否充足

    Args:
        historical_returns: 歷史收益率資料
        min_periods: 最小期數要求

    Returns:
        資料是否充足
    """
    if historical_returns.empty:
        return False
    
    # 檢查每個股票的資料點數
    stock_counts = historical_returns.groupby(level="stock_id").count()
    min_count = stock_counts.min().min() if not stock_counts.empty else 0
    
    return min_count >= min_periods


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """安全除法，避免除零錯誤

    Args:
        numerator: 分子
        denominator: 分母
        default: 當分母為零時的預設值

    Returns:
        除法結果
    """
    if denominator == 0:
        return default
    return numerator / denominator


def log_portfolio_info(portfolio_name: str, weights: Dict[str, float]) -> None:
    """記錄投資組合資訊

    Args:
        portfolio_name: 投資組合名稱
        weights: 權重字典
    """
    logger.info(f"投資組合 {portfolio_name} 權重分配:")
    for stock, weight in weights.items():
        logger.info(f"  {stock}: {weight:.4f}")
    
    total_weight = sum(weights.values())
    logger.info(f"  總權重: {total_weight:.4f}")


def create_fallback_weights(stocks: list, method: str = "equal") -> Dict[str, float]:
    """創建備選權重方案

    Args:
        stocks: 股票列表
        method: 備選方法，目前支援 'equal'

    Returns:
        備選權重字典
    """
    if method == "equal":
        return calculate_equal_weights(stocks)
    else:
        raise ValueError(f"不支援的備選方法: {method}")
