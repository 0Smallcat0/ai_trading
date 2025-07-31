# -*- coding: utf-8 -*-
"""
績效指標向後兼容介面

此模組提供與原始 performance_metrics.py 相容的介面，
確保現有代碼可以無縫遷移到新的模組化實現。

Functions:
    calculate_all_metrics: 計算所有績效指標（向後兼容）
"""

import logging
from typing import Any, Dict, Optional, Union

import numpy as np
import pandas as pd

from src.config import LOG_LEVEL
from .trading_metrics import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_calmar_ratio,
    calculate_annual_return,
    calculate_total_return,
)
from .risk_metrics import (
    calculate_max_drawdown,
    calculate_volatility,
    calculate_var,
    calculate_cvar,
    calculate_downside_risk,
)
from .statistical_metrics import (
    calculate_win_rate,
    calculate_pnl_ratio,
    calculate_expectancy,
    calculate_profit_factor,
    calculate_recovery_factor,
)

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


def calculate_all_metrics(
    returns: Union[pd.Series, np.ndarray],
    prices: Optional[Union[pd.Series, np.ndarray]] = None,
    trades: Optional[Union[pd.Series, np.ndarray]] = None,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
    confidence_levels: list = None,
    **kwargs: Any,
) -> Dict[str, float]:
    """
    計算所有績效指標 (向後兼容函數)

    此函數提供與原始實現相同的介面，計算完整的績效指標集合。

    Args:
        returns: 收益率序列
        prices: 價格序列（可選）
        trades: 交易損益序列（可選）
        risk_free_rate: 無風險利率
        periods_per_year: 每年期數
        confidence_levels: VaR 置信水平列表
        **kwargs: 其他參數

    Returns:
        包含所有績效指標的字典

    Raises:
        ValueError: 當輸入資料無效時

    Example:
        >>> returns = pd.Series([0.01, -0.02, 0.015, 0.008, -0.005])
        >>> metrics = calculate_all_metrics(returns, risk_free_rate=0.02)
        >>> print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.4f}")

    Note:
        此函數保持與原始 API 的完全兼容性
        建議新代碼使用模組化的單獨函數
    """
    if confidence_levels is None:
        confidence_levels = [0.95, 0.99]

    try:
        logger.info("開始計算所有績效指標")

        # 初始化結果字典
        metrics = {}

        # 使用交易損益序列（如果提供）
        analysis_data = trades if trades is not None else returns

        # === 風險調整收益指標 ===
        try:
            metrics["sharpe_ratio"] = calculate_sharpe_ratio(
                returns, risk_free_rate, periods_per_year
            )
        except Exception as e:
            logger.warning(f"計算夏普比率失敗: {e}")
            metrics["sharpe_ratio"] = 0.0

        try:
            metrics["sortino_ratio"] = calculate_sortino_ratio(
                returns, risk_free_rate, periods_per_year
            )
        except Exception as e:
            logger.warning(f"計算索提諾比率失敗: {e}")
            metrics["sortino_ratio"] = 0.0

        try:
            metrics["calmar_ratio"] = calculate_calmar_ratio(
                returns, prices, periods_per_year
            )
        except Exception as e:
            logger.warning(f"計算卡爾馬比率失敗: {e}")
            metrics["calmar_ratio"] = 0.0

        # === 收益指標 ===
        try:
            metrics["annual_return"] = calculate_annual_return(
                returns, periods_per_year, method="arithmetic"
            )
        except Exception as e:
            logger.warning(f"計算年化收益率失敗: {e}")
            metrics["annual_return"] = 0.0

        try:
            metrics["total_return"] = calculate_total_return(returns)
        except Exception as e:
            logger.warning(f"計算總收益率失敗: {e}")
            metrics["total_return"] = 0.0

        # === 風險指標 ===
        try:
            metrics["max_drawdown"] = calculate_max_drawdown(returns, prices)
        except Exception as e:
            logger.warning(f"計算最大回撤失敗: {e}")
            metrics["max_drawdown"] = 0.0

        try:
            metrics["volatility"] = calculate_volatility(returns, periods_per_year)
        except Exception as e:
            logger.warning(f"計算波動率失敗: {e}")
            metrics["volatility"] = 0.0

        try:
            metrics["downside_risk"] = calculate_downside_risk(
                returns, target_return=0.0, periods_per_year=periods_per_year
            )
        except Exception as e:
            logger.warning(f"計算下行風險失敗: {e}")
            metrics["downside_risk"] = 0.0

        # === VaR 指標 ===
        for confidence_level in confidence_levels:
            try:
                var_key = f"var_{int(confidence_level * 100)}"
                metrics[var_key] = calculate_var(returns, confidence_level)
            except Exception as e:
                logger.warning(f"計算VaR({confidence_level})失敗: {e}")
                metrics[var_key] = 0.0

            try:
                cvar_key = f"cvar_{int(confidence_level * 100)}"
                metrics[cvar_key] = calculate_cvar(returns, confidence_level)
            except Exception as e:
                logger.warning(f"計算CVaR({confidence_level})失敗: {e}")
                metrics[cvar_key] = 0.0

        # === 交易統計指標 ===
        try:
            metrics["win_rate"] = calculate_win_rate(analysis_data)
        except Exception as e:
            logger.warning(f"計算勝率失敗: {e}")
            metrics["win_rate"] = 0.0

        try:
            metrics["pnl_ratio"] = calculate_pnl_ratio(analysis_data)
        except Exception as e:
            logger.warning(f"計算盈虧比失敗: {e}")
            metrics["pnl_ratio"] = 0.0

        try:
            metrics["expectancy"] = calculate_expectancy(analysis_data)
        except Exception as e:
            logger.warning(f"計算期望值失敗: {e}")
            metrics["expectancy"] = 0.0

        try:
            metrics["profit_factor"] = calculate_profit_factor(analysis_data)
        except Exception as e:
            logger.warning(f"計算獲利因子失敗: {e}")
            metrics["profit_factor"] = 0.0

        try:
            metrics["recovery_factor"] = calculate_recovery_factor(returns)
        except Exception as e:
            logger.warning(f"計算恢復因子失敗: {e}")
            metrics["recovery_factor"] = 0.0

        # === 額外統計指標 ===
        try:
            # 計算一些額外的統計指標
            metrics["skewness"] = float(pd.Series(returns).skew())
            metrics["kurtosis"] = float(pd.Series(returns).kurtosis())
            metrics["best_return"] = float(np.max(returns))
            metrics["worst_return"] = float(np.min(returns))
            metrics["avg_return"] = float(np.mean(returns))
            metrics["std_return"] = float(np.std(returns, ddof=1))

            # 交易次數統計
            if trades is not None:
                metrics["total_trades"] = len(trades)
                metrics["winning_trades"] = int(np.sum(trades > 0))
                metrics["losing_trades"] = int(np.sum(trades < 0))
            else:
                metrics["total_trades"] = len(returns)
                metrics["winning_trades"] = int(np.sum(returns > 0))
                metrics["losing_trades"] = int(np.sum(returns < 0))

        except Exception as e:
            logger.warning(f"計算額外統計指標失敗: {e}")

        logger.info(f"績效指標計算完成，共計算 {len(metrics)} 個指標")

        return metrics

    except Exception as e:
        logger.error(f"計算績效指標時發生嚴重錯誤: {e}")
        raise RuntimeError(f"績效指標計算失敗: {e}") from e
