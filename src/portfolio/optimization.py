"""投資組合最佳化演算法模組

此模組提供各種投資組合最佳化演算法的實現，包括：
- 均值變異數最佳化
- 風險平價最佳化
- 最大夏普比率最佳化
- 最小變異數最佳化
- Kelly 公式權重計算
- 有效前緣計算

這些函數可以被投資組合策略類別使用，也可以獨立調用。
"""

from typing import Dict, List
import logging

import numpy as np
import pandas as pd

# 可選依賴處理
try:
    import scipy.optimize as sco

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    sco = None

try:
    from pypfopt import EfficientFrontier, expected_returns, risk_models

    PYPFOPT_AVAILABLE = True
except ImportError:
    PYPFOPT_AVAILABLE = False
    EfficientFrontier = None
    expected_returns = None
    risk_models = None

# 設定日誌
logger = logging.getLogger(__name__)


def equal_weight(stocks: List[str]) -> Dict[str, float]:
    """等權重配置

    Args:
        stocks: 股票代碼列表

    Returns:
        等權重配置字典
    """
    if not stocks:
        return {}

    weight = 1.0 / len(stocks)
    return {stock: weight for stock in stocks}


def kelly_weight(
    stocks: List[str],
    expected_returns: pd.Series,
    win_rates: pd.Series,
    loss_rates: pd.Series,
) -> Dict[str, float]:
    """Kelly 公式權重計算

    Args:
        stocks: 股票代碼列表
        expected_returns: 期望收益率
        win_rates: 勝率
        loss_rates: 敗率

    Returns:
        Kelly 權重配置
    """
    if not stocks:
        return {}

    weights_dict = {}
    total_weight = 0

    for stock in stocks:
        if stock in expected_returns.index and stock in win_rates.index:
            p = win_rates[stock]  # 勝率
            q = loss_rates.get(stock, 1 - p)  # 敗率
            b = abs(expected_returns[stock])  # 期望收益率的絕對值

            if q > 0 and b > 0:
                # Kelly 公式: f = (bp - q) / b
                kelly_weight_val = (b * p - q) / b
                # 限制權重在合理範圍內
                kelly_weight_val = max(0, min(kelly_weight_val, 0.25))
                weights_dict[stock] = kelly_weight_val
                total_weight += kelly_weight_val

    # 正規化權重
    if total_weight > 0:
        weights_dict = {k: v / total_weight for k, v in weights_dict.items()}
    else:
        # 如果所有權重都是0，回退到等權重
        return equal_weight(stocks)

    return weights_dict


def momentum_weight(
    stocks: List[str], returns_data: pd.DataFrame, lookback_period: int = 252
) -> Dict[str, float]:
    """動量權重配置

    Args:
        stocks: 股票代碼列表
        returns_data: 收益率資料
        lookback_period: 回望期間（天數）

    Returns:
        動量權重配置
    """
    if not stocks or returns_data.empty:
        return equal_weight(stocks)

    try:
        # 計算動量分數（過去一年的累積收益率）
        momentum_scores = {}

        for stock in stocks:
            if stock in returns_data.columns:
                stock_returns = returns_data[stock].tail(lookback_period)
                if len(stock_returns) > 0:
                    # 累積收益率作為動量分數
                    momentum_score = (1 + stock_returns).prod() - 1
                    momentum_scores[stock] = max(0, momentum_score)  # 只考慮正動量

        if not momentum_scores:
            return equal_weight(stocks)

        # 正規化權重
        total_score = sum(momentum_scores.values())
        if total_score > 0:
            return {
                stock: score / total_score for stock, score in momentum_scores.items()
            }
        else:
            return equal_weight(stocks)

    except Exception as e:
        logger.error(f"動量權重計算錯誤: {e}")
        return equal_weight(stocks)


def mean_variance_optimization(
    stocks: List[str],
    returns_data: pd.DataFrame,
    target_return: float = 0.1,
    risk_free_rate: float = 0.02,
) -> Dict[str, float]:
    """均值變異數最佳化

    Args:
        stocks: 股票代碼列表
        returns_data: 收益率資料
        target_return: 目標年化收益率
        risk_free_rate: 無風險利率

    Returns:
        最佳化權重配置
    """
    if not stocks or returns_data.empty:
        return equal_weight(stocks)

    try:
        # 篩選可用股票
        available_stocks = [s for s in stocks if s in returns_data.columns]
        if not available_stocks:
            return {}

        returns_subset = returns_data[available_stocks].dropna()
        if returns_subset.empty:
            return equal_weight(available_stocks)

        # 計算期望收益率和協方差矩陣
        expected_returns_vec = returns_subset.mean() * 252  # 年化
        cov_matrix = returns_subset.cov() * 252  # 年化

        if not SCIPY_AVAILABLE:
            logger.warning("SciPy 不可用，使用等權重分配")
            return equal_weight(available_stocks)

        # 目標函數：最小化變異數
        def objective(weights):
            return np.dot(weights, np.dot(cov_matrix.values, weights))

        # 約束條件
        constraints = [
            {"type": "eq", "fun": lambda x: np.sum(x) - 1},  # 權重和為1
            {
                "type": "eq",
                "fun": lambda x: np.dot(x, expected_returns_vec.values) - target_return,
            },  # 目標收益率
        ]
        bounds = tuple((0.01, 0.5) for _ in range(len(available_stocks)))

        # 初始權重
        x0 = np.array([1.0 / len(available_stocks)] * len(available_stocks))

        # 最佳化
        result = sco.minimize(
            objective, x0, method="SLSQP", bounds=bounds, constraints=constraints
        )

        if result.success:
            return dict(zip(available_stocks, result.x))
        else:
            logger.warning(f"均值變異數最佳化失敗: {result.message}")
            return equal_weight(available_stocks)

    except Exception as e:
        logger.error(f"均值變異數最佳化錯誤: {e}")
        return equal_weight(stocks)


def minimum_variance_optimization(
    stocks: List[str], returns_data: pd.DataFrame
) -> Dict[str, float]:
    """最小變異數最佳化

    Args:
        stocks: 股票代碼列表
        returns_data: 收益率資料

    Returns:
        最小變異數權重配置
    """
    if not stocks or returns_data.empty:
        return equal_weight(stocks)

    try:
        # 篩選可用股票
        available_stocks = [s for s in stocks if s in returns_data.columns]
        if not available_stocks:
            return {}

        returns_subset = returns_data[available_stocks].dropna()
        if returns_subset.empty:
            return equal_weight(available_stocks)

        # 計算協方差矩陣
        cov_matrix = returns_subset.cov() * 252  # 年化

        if not SCIPY_AVAILABLE:
            logger.warning("SciPy 不可用，使用等權重分配")
            return equal_weight(available_stocks)

        # 目標函數：最小化變異數
        def objective(weights):
            return np.dot(weights, np.dot(cov_matrix.values, weights))

        # 約束條件
        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
        bounds = tuple((0.01, 0.5) for _ in range(len(available_stocks)))

        # 初始權重
        x0 = np.array([1.0 / len(available_stocks)] * len(available_stocks))

        # 最佳化
        result = sco.minimize(
            objective, x0, method="SLSQP", bounds=bounds, constraints=constraints
        )

        if result.success:
            return dict(zip(available_stocks, result.x))
        else:
            logger.warning(f"最小變異數最佳化失敗: {result.message}")
            return equal_weight(available_stocks)

    except Exception as e:
        logger.error(f"最小變異數最佳化錯誤: {e}")
        return equal_weight(stocks)


def maximum_sharpe_optimization(
    stocks: List[str], returns_data: pd.DataFrame, risk_free_rate: float = 0.02
) -> Dict[str, float]:
    """最大夏普比率最佳化

    Args:
        stocks: 股票代碼列表
        returns_data: 收益率資料
        risk_free_rate: 無風險利率

    Returns:
        最大夏普比率權重配置
    """
    if not stocks or returns_data.empty:
        return equal_weight(stocks)

    try:
        # 篩選可用股票
        available_stocks = [s for s in stocks if s in returns_data.columns]
        if not available_stocks:
            return {}

        returns_subset = returns_data[available_stocks].dropna()
        if returns_subset.empty:
            return equal_weight(available_stocks)

        # 計算期望收益率和協方差矩陣
        expected_returns_vec = returns_subset.mean() * 252  # 年化
        cov_matrix = returns_subset.cov() * 252  # 年化

        if not SCIPY_AVAILABLE:
            logger.warning("SciPy 不可用，使用等權重分配")
            return equal_weight(available_stocks)

        # 負夏普比率目標函數（最小化負值等於最大化正值）
        def negative_sharpe(weights):
            portfolio_return = np.dot(weights, expected_returns_vec.values)
            portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix.values, weights)))
            if portfolio_vol == 0:
                return -np.inf
            return -(portfolio_return - risk_free_rate) / portfolio_vol

        # 約束條件
        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
        bounds = tuple((0.01, 0.5) for _ in range(len(available_stocks)))

        # 初始權重
        x0 = np.array([1.0 / len(available_stocks)] * len(available_stocks))

        # 最佳化
        result = sco.minimize(
            negative_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints
        )

        if result.success:
            return dict(zip(available_stocks, result.x))
        else:
            logger.warning(f"最大夏普比率最佳化失敗: {result.message}")
            return equal_weight(available_stocks)

    except Exception as e:
        logger.error(f"最大夏普比率最佳化錯誤: {e}")
        return equal_weight(stocks)


def risk_parity_optimization(
    stocks: List[str], returns_data: pd.DataFrame
) -> Dict[str, float]:
    """風險平價最佳化

    Args:
        stocks: 股票代碼列表
        returns_data: 收益率資料

    Returns:
        風險平價權重配置
    """
    if not stocks or returns_data.empty:
        return equal_weight(stocks)

    try:
        # 篩選可用股票
        available_stocks = [s for s in stocks if s in returns_data.columns]
        if not available_stocks:
            return {}

        returns_subset = returns_data[available_stocks].dropna()
        if returns_subset.empty:
            return equal_weight(available_stocks)

        # 計算協方差矩陣
        cov_matrix = returns_subset.cov() * 252  # 年化

        if not SCIPY_AVAILABLE:
            logger.warning("SciPy 不可用，使用等權重分配")
            return equal_weight(available_stocks)

        # 風險平價目標函數
        def risk_parity_objective(weights):
            portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix.values, weights)))
            if portfolio_vol == 0:
                return np.inf
            marginal_contrib = np.dot(cov_matrix.values, weights) / portfolio_vol
            contrib = weights * marginal_contrib
            target_contrib = portfolio_vol / len(weights)
            return np.sum((contrib - target_contrib) ** 2)

        # 約束條件
        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
        bounds = tuple((0.01, 0.5) for _ in range(len(available_stocks)))

        # 初始權重
        x0 = np.array([1.0 / len(available_stocks)] * len(available_stocks))

        # 最佳化
        result = sco.minimize(
            risk_parity_objective,
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        if result.success:
            return dict(zip(available_stocks, result.x))
        else:
            logger.warning(f"風險平價最佳化失敗: {result.message}")
            return equal_weight(available_stocks)

    except Exception as e:
        logger.error(f"風險平價最佳化錯誤: {e}")
        return equal_weight(stocks)
