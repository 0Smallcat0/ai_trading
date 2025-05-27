"""
回測指標計算模組

此模組包含各種回測績效指標的計算功能。
"""

import logging
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def calculate_performance_metrics(
    equity_curve: pd.Series,
    trades: List[Dict[str, Any]],
    benchmark_returns: Optional[pd.Series] = None
) -> Dict[str, float]:
    """
    計算回測績效指標

    Args:
        equity_curve: 權益曲線
        trades: 交易記錄
        benchmark_returns: 基準收益率序列

    Returns:
        Dict[str, float]: 績效指標字典
    """
    try:
        if equity_curve.empty:
            logger.warning("權益曲線為空，返回默認指標")
            return _get_default_metrics()

        # 計算基本指標
        total_return = _calculate_total_return(equity_curve)
        annual_return = _calculate_annual_return(equity_curve)
        volatility = _calculate_volatility(equity_curve)
        sharpe_ratio = _calculate_sharpe_ratio(equity_curve)
        max_drawdown = _calculate_max_drawdown(equity_curve)

        # 計算交易相關指標
        win_rate = _calculate_win_rate(trades)
        profit_factor = _calculate_profit_factor(trades)
        avg_trade_return = _calculate_avg_trade_return(trades)

        # 計算風險指標
        sortino_ratio = _calculate_sortino_ratio(equity_curve)
        calmar_ratio = _calculate_calmar_ratio(annual_return, max_drawdown)

        metrics = {
            "total_return": total_return,
            "annual_return": annual_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "calmar_ratio": calmar_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "avg_trade_return": avg_trade_return,
            "total_trades": len(trades),
        }

        # 如果有基準數據，計算相對指標
        if benchmark_returns is not None and not benchmark_returns.empty:
            alpha, beta = _calculate_alpha_beta(equity_curve, benchmark_returns)
            information_ratio = _calculate_information_ratio(
                equity_curve, benchmark_returns
            )
            metrics.update({
                "alpha": alpha,
                "beta": beta,
                "information_ratio": information_ratio,
            })

        return metrics

    except Exception as e:
        logger.error("計算績效指標時發生錯誤: %s", e)
        return _get_default_metrics()


def _calculate_total_return(equity_curve: pd.Series) -> float:
    """計算總收益率"""
    if len(equity_curve) < 2:
        return 0.0
    return (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) * 100


def _calculate_annual_return(equity_curve: pd.Series) -> float:
    """計算年化收益率"""
    if len(equity_curve) < 2:
        return 0.0

    total_return = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1
    days = len(equity_curve)
    years = days / 252  # 假設一年252個交易日

    if years <= 0:
        return 0.0

    return (pow(1 + total_return, 1 / years) - 1) * 100


def _calculate_volatility(equity_curve: pd.Series) -> float:
    """計算波動率"""
    if len(equity_curve) < 2:
        return 0.0

    returns = equity_curve.pct_change().dropna()
    if returns.empty:
        return 0.0

    return returns.std() * np.sqrt(252) * 100


def _calculate_sharpe_ratio(equity_curve: pd.Series, risk_free_rate: float = 0.02) -> float:
    """計算夏普比率"""
    if len(equity_curve) < 2:
        return 0.0

    returns = equity_curve.pct_change().dropna()
    if returns.empty:
        return 0.0

    excess_returns = returns - risk_free_rate / 252

    if excess_returns.std() == 0:
        return 0.0

    return excess_returns.mean() / excess_returns.std() * np.sqrt(252)


def _calculate_sortino_ratio(equity_curve: pd.Series, risk_free_rate: float = 0.02) -> float:
    """計算索提諾比率"""
    if len(equity_curve) < 2:
        return 0.0

    returns = equity_curve.pct_change().dropna()
    if returns.empty:
        return 0.0

    excess_returns = returns - risk_free_rate / 252
    downside_returns = excess_returns[excess_returns < 0]

    if len(downside_returns) == 0 or downside_returns.std() == 0:
        return 0.0

    return excess_returns.mean() / downside_returns.std() * np.sqrt(252)


def _calculate_max_drawdown(equity_curve: pd.Series) -> float:
    """計算最大回撤"""
    if len(equity_curve) < 2:
        return 0.0

    peak = equity_curve.iloc[0]
    max_drawdown = 0.0

    for value in equity_curve:
        peak = max(peak, value)
        drawdown = (peak - value) / peak * 100
        max_drawdown = max(max_drawdown, drawdown)

    return max_drawdown


def _calculate_calmar_ratio(annual_return: float, max_drawdown: float) -> float:
    """計算卡瑪比率"""
    if max_drawdown == 0:
        return 0.0
    return annual_return / max_drawdown


def _calculate_win_rate(trades: List[Dict[str, Any]]) -> float:
    """計算勝率"""
    if not trades:
        return 0.0

    winning_trades = sum(1 for trade in trades if trade.get("pnl", 0) > 0)
    return (winning_trades / len(trades)) * 100


def _calculate_profit_factor(trades: List[Dict[str, Any]]) -> float:
    """計算獲利因子"""
    if not trades:
        return 0.0

    gross_profit = sum(trade.get("pnl", 0) for trade in trades if trade.get("pnl", 0) > 0)
    gross_loss = abs(sum(trade.get("pnl", 0) for trade in trades if trade.get("pnl", 0) < 0))

    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0

    return gross_profit / gross_loss


def _calculate_avg_trade_return(trades: List[Dict[str, Any]]) -> float:
    """計算平均交易收益"""
    if not trades:
        return 0.0

    total_pnl = sum(trade.get("pnl", 0) for trade in trades)
    return total_pnl / len(trades)


def _calculate_alpha_beta(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series
) -> tuple[float, float]:
    """計算阿爾法和貝塔值"""
    try:
        # 對齊時間序列
        aligned_data = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
        if len(aligned_data) < 2:
            return 0.0, 1.0

        portfolio_rets = aligned_data.iloc[:, 0].pct_change().dropna()
        benchmark_rets = aligned_data.iloc[:, 1].pct_change().dropna()

        if len(portfolio_rets) < 2 or len(benchmark_rets) < 2:
            return 0.0, 1.0

        # 計算貝塔值
        covariance = np.cov(portfolio_rets, benchmark_rets)[0, 1]
        benchmark_variance = np.var(benchmark_rets)

        if benchmark_variance == 0:
            beta = 1.0
        else:
            beta = covariance / benchmark_variance

        # 計算阿爾法值
        alpha = portfolio_rets.mean() - beta * benchmark_rets.mean()

        return alpha * 252, beta  # 年化阿爾法

    except Exception as e:
        logger.error("計算阿爾法和貝塔值時發生錯誤: %s", e)
        return 0.0, 1.0


def _calculate_information_ratio(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series
) -> float:
    """計算信息比率"""
    try:
        # 對齊時間序列
        aligned_data = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
        if len(aligned_data) < 2:
            return 0.0

        portfolio_rets = aligned_data.iloc[:, 0].pct_change().dropna()
        benchmark_rets = aligned_data.iloc[:, 1].pct_change().dropna()

        if len(portfolio_rets) < 2 or len(benchmark_rets) < 2:
            return 0.0

        excess_returns = portfolio_rets - benchmark_rets

        if excess_returns.std() == 0:
            return 0.0

        return excess_returns.mean() / excess_returns.std() * np.sqrt(252)

    except Exception as e:
        logger.error("計算信息比率時發生錯誤: %s", e)
        return 0.0


def _get_default_metrics() -> Dict[str, float]:
    """獲取默認指標值"""
    return {
        "total_return": 0.0,
        "annual_return": 0.0,
        "volatility": 0.0,
        "sharpe_ratio": 0.0,
        "sortino_ratio": 0.0,
        "calmar_ratio": 0.0,
        "max_drawdown": 0.0,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "avg_trade_return": 0.0,
        "total_trades": 0,
    }
