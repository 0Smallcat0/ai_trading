"""投資組合績效評估模組

此模組提供投資組合績效評估的各種指標和函數，包括：
- 基本績效指標（收益率、波動率、夏普比率等）
- 風險指標（VaR、最大回撤、下行風險等）
- 歸因分析
- 績效比較和排名

這些函數可以用於評估單個投資組合或比較多個投資組合的表現。
"""

from typing import Dict, Optional, Any
import logging

import numpy as np
import pandas as pd

# 設定日誌
logger = logging.getLogger(__name__)

# 可選依賴處理
try:
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    logger.warning("matplotlib 不可用，無法繪製圖表")

try:
    import seaborn as sns

    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False
    sns = None


def calculate_portfolio_returns(
    weights: Dict[str, float], prices: pd.DataFrame
) -> Dict[str, Any]:
    """計算投資組合收益率

    Args:
        weights: 投資組合權重
        prices: 價格資料，索引為 (股票代號, 日期)

    Returns:
        評估結果，包含 'returns', 'cumulative_returns', 'annual_return',
        'annual_volatility', 'sharpe_ratio', 'max_drawdown'
    """
    if not weights:
        return {}

    # 確定價格欄位
    price_col = "close" if "close" in prices.columns else "收盤價"

    # 計算每日收益率
    daily_returns = prices[price_col].pct_change()

    # 計算投資組合收益率
    portfolio_returns = pd.Series(
        0.0, index=daily_returns.index.get_level_values("date").unique()
    )

    for date in portfolio_returns.index:
        # 獲取該日期的收益率
        date_returns = daily_returns.xs(date, level="date", drop_level=False)
        portfolio_return = 0.0
        for stock_id, weight in weights.items():
            if (stock_id, date) in date_returns.index:
                portfolio_return += weight * date_returns.loc[(stock_id, date)]
        portfolio_returns[date] = portfolio_return

    # 計算累積收益率
    cumulative_returns = (1 + portfolio_returns).cumprod()

    # 計算年化收益率
    annual_return = portfolio_returns.mean() * 252

    # 計算年化波動率
    annual_volatility = portfolio_returns.std() * np.sqrt(252)

    # 計算夏普比率
    sharpe_ratio = annual_return / annual_volatility if annual_volatility else 0

    # 計算最大回撤
    max_drawdown = (cumulative_returns / cumulative_returns.cummax() - 1).min()

    return {
        "returns": portfolio_returns,
        "cumulative_returns": cumulative_returns,
        "annual_return": annual_return,
        "annual_volatility": annual_volatility,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
    }


def calculate_var(returns: pd.Series, confidence_level: float = 0.05) -> float:
    """計算風險值 (Value at Risk)

    Args:
        returns: 收益率序列
        confidence_level: 信心水準（預設 5%）

    Returns:
        VaR 值
    """
    if returns.empty:
        return 0.0

    try:
        return np.percentile(returns.dropna(), confidence_level * 100)
    except Exception as e:
        logger.error(f"VaR 計算錯誤: {e}")
        return 0.0


def calculate_cvar(returns: pd.Series, confidence_level: float = 0.05) -> float:
    """計算條件風險值 (Conditional Value at Risk)

    Args:
        returns: 收益率序列
        confidence_level: 信心水準（預設 5%）

    Returns:
        CVaR 值
    """
    if returns.empty:
        return 0.0

    try:
        var = calculate_var(returns, confidence_level)
        return returns[returns <= var].mean()
    except Exception as e:
        logger.error(f"CVaR 計算錯誤: {e}")
        return 0.0


def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """計算 Sortino 比率

    Args:
        returns: 收益率序列
        risk_free_rate: 無風險利率

    Returns:
        Sortino 比率
    """
    if returns.empty:
        return 0.0

    try:
        excess_returns = returns - risk_free_rate / 252
        downside_returns = excess_returns[excess_returns < 0]

        if len(downside_returns) == 0:
            return np.inf

        downside_deviation = np.sqrt(np.mean(downside_returns**2)) * np.sqrt(252)

        if downside_deviation == 0:
            return np.inf

        return (returns.mean() * 252 - risk_free_rate) / downside_deviation
    except Exception as e:
        logger.error(f"Sortino 比率計算錯誤: {e}")
        return 0.0


def calculate_calmar_ratio(returns: pd.Series) -> float:
    """計算 Calmar 比率

    Args:
        returns: 收益率序列

    Returns:
        Calmar 比率
    """
    if returns.empty:
        return 0.0

    try:
        cumulative_returns = (1 + returns).cumprod()
        max_drawdown = (cumulative_returns / cumulative_returns.cummax() - 1).min()
        annual_return = returns.mean() * 252

        if max_drawdown == 0:
            return np.inf

        return annual_return / abs(max_drawdown)
    except Exception as e:
        logger.error(f"Calmar 比率計算錯誤: {e}")
        return 0.0


def calculate_information_ratio(
    portfolio_returns: pd.Series, benchmark_returns: pd.Series
) -> float:
    """計算資訊比率

    Args:
        portfolio_returns: 投資組合收益率
        benchmark_returns: 基準收益率

    Returns:
        資訊比率
    """
    if portfolio_returns.empty or benchmark_returns.empty:
        return 0.0

    try:
        # 對齊時間序列
        aligned_data = pd.DataFrame(
            {"portfolio": portfolio_returns, "benchmark": benchmark_returns}
        ).dropna()

        if aligned_data.empty:
            return 0.0

        excess_returns = aligned_data["portfolio"] - aligned_data["benchmark"]
        tracking_error = excess_returns.std() * np.sqrt(252)

        if tracking_error == 0:
            return np.inf

        return (excess_returns.mean() * 252) / tracking_error
    except Exception as e:
        logger.error(f"資訊比率計算錯誤: {e}")
        return 0.0


def calculate_beta(portfolio_returns: pd.Series, market_returns: pd.Series) -> float:
    """計算 Beta 值

    Args:
        portfolio_returns: 投資組合收益率
        market_returns: 市場收益率

    Returns:
        Beta 值
    """
    if portfolio_returns.empty or market_returns.empty:
        return 1.0

    try:
        # 對齊時間序列
        aligned_data = pd.DataFrame(
            {"portfolio": portfolio_returns, "market": market_returns}
        ).dropna()

        if len(aligned_data) < 2:
            return 1.0

        covariance = aligned_data["portfolio"].cov(aligned_data["market"])
        market_variance = aligned_data["market"].var()

        if market_variance == 0:
            return 1.0

        return covariance / market_variance
    except Exception as e:
        logger.error(f"Beta 計算錯誤: {e}")
        return 1.0


def calculate_alpha(
    portfolio_returns: pd.Series,
    market_returns: pd.Series,
    risk_free_rate: float = 0.02,
) -> float:
    """計算 Alpha 值

    Args:
        portfolio_returns: 投資組合收益率
        market_returns: 市場收益率
        risk_free_rate: 無風險利率

    Returns:
        Alpha 值
    """
    if portfolio_returns.empty or market_returns.empty:
        return 0.0

    try:
        beta = calculate_beta(portfolio_returns, market_returns)
        portfolio_annual_return = portfolio_returns.mean() * 252
        market_annual_return = market_returns.mean() * 252

        return portfolio_annual_return - (
            risk_free_rate + beta * (market_annual_return - risk_free_rate)
        )
    except Exception as e:
        logger.error(f"Alpha 計算錯誤: {e}")
        return 0.0


def calculate_comprehensive_metrics(
    portfolio_returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None,
    risk_free_rate: float = 0.02,
) -> Dict[str, float]:
    """計算綜合績效指標

    Args:
        portfolio_returns: 投資組合收益率
        benchmark_returns: 基準收益率（可選）
        risk_free_rate: 無風險利率

    Returns:
        綜合績效指標字典
    """
    if portfolio_returns.empty:
        return {}

    metrics = {}

    try:
        # 基本指標
        cumulative_returns = (1 + portfolio_returns).cumprod()
        metrics["total_return"] = cumulative_returns.iloc[-1] - 1
        metrics["annual_return"] = portfolio_returns.mean() * 252
        metrics["annual_volatility"] = portfolio_returns.std() * np.sqrt(252)
        metrics["sharpe_ratio"] = (
            (metrics["annual_return"] - risk_free_rate) / metrics["annual_volatility"]
            if metrics["annual_volatility"] > 0
            else 0
        )

        # 風險指標
        metrics["max_drawdown"] = (
            cumulative_returns / cumulative_returns.cummax() - 1
        ).min()
        metrics["var_5"] = calculate_var(portfolio_returns, 0.05)
        metrics["cvar_5"] = calculate_cvar(portfolio_returns, 0.05)
        metrics["sortino_ratio"] = calculate_sortino_ratio(
            portfolio_returns, risk_free_rate
        )
        metrics["calmar_ratio"] = calculate_calmar_ratio(portfolio_returns)

        # 如果有基準，計算相對指標
        if benchmark_returns is not None and not benchmark_returns.empty:
            metrics["beta"] = calculate_beta(portfolio_returns, benchmark_returns)
            metrics["alpha"] = calculate_alpha(
                portfolio_returns, benchmark_returns, risk_free_rate
            )
            metrics["information_ratio"] = calculate_information_ratio(
                portfolio_returns, benchmark_returns
            )

            # 相對表現
            aligned_data = pd.DataFrame(
                {"portfolio": portfolio_returns, "benchmark": benchmark_returns}
            ).dropna()

            if not aligned_data.empty:
                excess_returns = aligned_data["portfolio"] - aligned_data["benchmark"]
                metrics["excess_return"] = excess_returns.mean() * 252
                metrics["tracking_error"] = excess_returns.std() * np.sqrt(252)

    except Exception as e:
        logger.error(f"綜合指標計算錯誤: {e}")

    return metrics


def plot_portfolio_performance(
    performance: Dict[str, Any], show_plot: bool = True
) -> None:
    """繪製投資組合表現圖

    Args:
        performance: 評估結果，包含 'returns', 'cumulative_returns'
        show_plot: 是否呼叫 plt.show()，預設 True
    """
    if not MATPLOTLIB_AVAILABLE:
        logger.warning("Matplotlib 不可用，無法繪製圖表")
        return

    # 若 returns 為空則直接 return
    if (
        not performance
        or performance.get("returns") is None
        or performance["returns"].empty
    ):
        logger.warning("沒有可繪製的績效資料")
        return

    try:
        plt.figure(figsize=(12, 8))

        # 繪製累積收益率
        plt.subplot(2, 1, 1)
        performance["cumulative_returns"].plot()
        plt.title("投資組合累積收益率")
        plt.xlabel("日期")
        plt.ylabel("累積收益率")
        plt.grid(True)

        # 繪製每月收益率
        plt.subplot(2, 1, 2)
        monthly_returns = (
            performance["returns"].resample("M").apply(lambda x: (1 + x).prod() - 1)
        )
        monthly_returns.index = monthly_returns.index.strftime("%Y-%m")

        if SEABORN_AVAILABLE:
            sns.barplot(x=monthly_returns.index, y=monthly_returns.values)
        else:
            plt.bar(range(len(monthly_returns)), monthly_returns.values)
            plt.xticks(range(len(monthly_returns)), monthly_returns.index, rotation=90)

        plt.title("投資組合每月收益率")
        plt.xlabel("月份")
        plt.ylabel("收益率")
        plt.xticks(rotation=90)
        plt.grid(True)

        plt.tight_layout()

        if show_plot:
            plt.show()

    except Exception as e:
        logger.error(f"無法繪製圖表: {e}")
