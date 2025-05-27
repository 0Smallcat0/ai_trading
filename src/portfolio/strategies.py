"""投資組合策略實現模組

此模組實現各種具體的投資組合策略，包括：
- 等權重投資組合
- 均值變異數投資組合
- 風險平價投資組合
- 最大夏普比率投資組合
- 最小變異數投資組合

所有策略都繼承自 Portfolio 基類。
"""

from typing import Dict, Optional, Any
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

from .base import Portfolio

# 設定日誌
logger = logging.getLogger(__name__)


class EqualWeightPortfolio(Portfolio):
    """等權重投資組合"""

    def __init__(self, **kwargs):
        """初始化等權重投資組合"""
        super().__init__(name="EqualWeight", **kwargs)

    def optimize(
        self, signals: pd.DataFrame, price_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """等權重最佳化

        Args:
            signals: 交易訊號
            price_df: 價格資料（此策略不使用）

        Returns:
            等權重配置
        """
        # 獲取有買入訊號的股票
        buy_signals = signals[signals.get("signal", signals.get("buy_signal", 0)) > 0]

        if buy_signals.empty:
            return {}

        # 獲取股票列表
        if isinstance(buy_signals.index, pd.MultiIndex):
            stocks = buy_signals.index.get_level_values(0).unique().tolist()
        else:
            stocks = buy_signals.index.tolist()

        if not stocks:
            return {}

        # 等權重分配
        weight = 1.0 / len(stocks)
        return {stock: weight for stock in stocks}

    def evaluate(
        self, weights: Dict[str, float], price_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """評估等權重投資組合表現

        Args:
            weights: 投資組合權重
            price_df: 價格資料

        Returns:
            評估結果
        """
        if not weights:
            return {}

        # 確定價格欄位
        price_col = "close" if "close" in price_df.columns else "收盤價"

        # 計算每日收益率
        daily_returns = price_df[price_col].pct_change()

        # 計算投資組合收益率
        portfolio_returns = pd.Series(
            0.0, index=daily_returns.index.get_level_values("date").unique()
        )

        for date in portfolio_returns.index:
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

    def rebalance(
        self,
        weights: Dict[str, float],
        price_df: pd.DataFrame,
        frequency: str = "M"
    ) -> Dict[str, float]:
        """等權重再平衡

        Args:
            weights: 當前權重
            price_df: 價格資料
            frequency: 再平衡頻率

        Returns:
            再平衡後的權重（等權重策略保持不變）
        """
        # 等權重策略不需要調整權重
        return weights


class MeanVariancePortfolio(Portfolio):
    """均值變異數投資組合（馬可維茲投資組合）"""

    def __init__(self, target_return: float = 0.1, **kwargs):
        """初始化均值變異數投資組合

        Args:
            target_return: 目標年化收益率
        """
        super().__init__(name="MeanVariance", **kwargs)
        self.target_return = target_return

    def optimize(
        self, signals: pd.DataFrame, price_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """均值變異數最佳化

        Args:
            signals: 交易訊號
            price_df: 價格資料

        Returns:
            最佳化後的權重
        """
        # 獲取有買入訊號的股票
        buy_signals = signals[signals.get("signal", signals.get("buy_signal", 0)) > 0]

        if buy_signals.empty or price_df is None:
            return {}

        # 獲取股票列表
        if isinstance(buy_signals.index, pd.MultiIndex):
            stocks = buy_signals.index.get_level_values(0).unique().tolist()
        else:
            stocks = buy_signals.index.tolist()

        if not stocks:
            return {}

        try:
            # 計算期望收益率和協方差矩陣
            price_col = "close" if "close" in price_df.columns else "收盤價"
            returns_data = price_df[price_col].unstack(level=0).pct_change().dropna()

            # 只保留有訊號的股票
            available_stocks = [s for s in stocks if s in returns_data.columns]
            if not available_stocks:
                logger.warning("沒有可用的股票資料進行最佳化")
                return {}

            returns_data = returns_data[available_stocks]

            expected_returns_vec = returns_data.mean() * 252  # 年化
            cov_matrix = returns_data.cov() * 252  # 年化

            if not SCIPY_AVAILABLE:
                logger.warning("SciPy 不可用，使用等權重分配")
                weight = 1.0 / len(available_stocks)
                return {stock: weight for stock in available_stocks}

            # 目標函數：最小化變異數
            def objective(weights):
                return np.dot(weights, np.dot(cov_matrix.values, weights))

            # 約束條件
            constraints = [
                {"type": "eq", "fun": lambda x: np.sum(x) - 1},  # 權重和為1
                {
                    "type": "eq",
                    "fun": lambda x: np.dot(x, expected_returns_vec.values) - self.target_return,
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
                weights_dict = dict(zip(available_stocks, result.x))
                return weights_dict
            else:
                logger.warning(f"最佳化失敗: {result.message}")
                weight = 1.0 / len(available_stocks)
                return {stock: weight for stock in available_stocks}

        except Exception as e:
            logger.error(f"均值變異數最佳化錯誤: {e}")
            # 回退到等權重
            weight = 1.0 / len(stocks)
            return {stock: weight for stock in stocks}

    def evaluate(
        self, weights: Dict[str, float], price_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """評估均值變異數投資組合表現"""
        # 使用基類的評估邏輯
        equal_weight = EqualWeightPortfolio()
        return equal_weight.evaluate(weights, price_df)

    def rebalance(
        self,
        weights: Dict[str, float],
        price_df: pd.DataFrame,
        frequency: str = "M"
    ) -> Dict[str, float]:
        """均值變異數再平衡

        Args:
            weights: 當前權重
            price_df: 價格資料
            frequency: 再平衡頻率

        Returns:
            再平衡後的權重
        """
        # 重新計算最佳權重
        # 這裡簡化處理，實際應該根據最新的市場資料重新最佳化
        stocks = list(weights.keys())
        if not stocks:
            return weights

        try:
            # 使用最新的價格資料重新計算
            price_col = "close" if "close" in price_df.columns else "收盤價"
            recent_data = price_df[price_col].tail(252)  # 使用最近一年的資料
            returns_data = recent_data.unstack(level=0).pct_change().dropna()

            available_stocks = [s for s in stocks if s in returns_data.columns]
            if not available_stocks:
                return weights

            returns_data = returns_data[available_stocks]

            expected_returns_vec = returns_data.mean() * 252
            cov_matrix = returns_data.cov() * 252

            if not SCIPY_AVAILABLE:
                weight = 1.0 / len(available_stocks)
                return {stock: weight for stock in available_stocks}

            # 重新最佳化
            def objective(w):
                return np.dot(w, np.dot(cov_matrix.values, w))

            constraints = [
                {"type": "eq", "fun": lambda x: np.sum(x) - 1},
                {
                    "type": "eq",
                    "fun": lambda x: np.dot(x, expected_returns_vec.values) - self.target_return,
                },
            ]
            bounds = tuple((0.01, 0.5) for _ in range(len(available_stocks)))
            x0 = np.array([1.0 / len(available_stocks)] * len(available_stocks))

            result = sco.minimize(
                objective, x0, method="SLSQP", bounds=bounds, constraints=constraints
            )

            if result.success:
                return dict(zip(available_stocks, result.x))
            else:
                return weights

        except Exception as e:
            logger.error(f"再平衡錯誤: {e}")
            return weights


class RiskParityPortfolio(Portfolio):
    """風險平價投資組合"""

    def __init__(self, **kwargs):
        """初始化風險平價投資組合"""
        super().__init__(name="RiskParity", **kwargs)

    def optimize(
        self, signals: pd.DataFrame, price_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """風險平價最佳化

        Args:
            signals: 交易訊號
            price_df: 價格資料

        Returns:
            風險平價權重
        """
        # 獲取有買入訊號的股票
        buy_signals = signals[signals.get("signal", signals.get("buy_signal", 0)) > 0]

        if buy_signals.empty or price_df is None:
            return {}

        # 獲取股票列表
        if isinstance(buy_signals.index, pd.MultiIndex):
            stocks = buy_signals.index.get_level_values(0).unique().tolist()
        else:
            stocks = buy_signals.index.tolist()

        if not stocks:
            return {}

        try:
            # 計算協方差矩陣
            price_col = "close" if "close" in price_df.columns else "收盤價"
            returns_data = price_df[price_col].unstack(level=0).pct_change().dropna()

            available_stocks = [s for s in stocks if s in returns_data.columns]
            if not available_stocks:
                logger.warning("沒有可用的股票資料進行風險平價最佳化")
                return {}

            returns_data = returns_data[available_stocks]
            cov_matrix = returns_data.cov() * 252  # 年化

            if not SCIPY_AVAILABLE:
                logger.warning("SciPy 不可用，使用等權重分配")
                weight = 1.0 / len(available_stocks)
                return {stock: weight for stock in available_stocks}

            # 風險平價目標函數
            def risk_parity_objective(weights):
                portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix.values, weights)))
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
                constraints=constraints
            )

            if result.success:
                return dict(zip(available_stocks, result.x))
            else:
                logger.warning(f"風險平價最佳化失敗: {result.message}")
                weight = 1.0 / len(available_stocks)
                return {stock: weight for stock in available_stocks}

        except Exception as e:
            logger.error(f"風險平價最佳化錯誤: {e}")
            weight = 1.0 / len(stocks)
            return {stock: weight for stock in stocks}

    def evaluate(
        self, weights: Dict[str, float], price_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """評估風險平價投資組合表現"""
        equal_weight = EqualWeightPortfolio()
        return equal_weight.evaluate(weights, price_df)

    def rebalance(
        self,
        weights: Dict[str, float],
        price_df: pd.DataFrame,
        frequency: str = "M"
    ) -> Dict[str, float]:
        """風險平價再平衡"""
        # 重新計算風險平價權重
        stocks = list(weights.keys())
        if not stocks:
            return weights

        try:
            price_col = "close" if "close" in price_df.columns else "收盤價"
            recent_data = price_df[price_col].tail(252)
            returns_data = recent_data.unstack(level=0).pct_change().dropna()

            available_stocks = [s for s in stocks if s in returns_data.columns]
            if not available_stocks:
                return weights

            returns_data = returns_data[available_stocks]
            cov_matrix = returns_data.cov() * 252

            if not SCIPY_AVAILABLE:
                weight = 1.0 / len(available_stocks)
                return {stock: weight for stock in available_stocks}

            def risk_parity_objective(w):
                portfolio_vol = np.sqrt(np.dot(w, np.dot(cov_matrix.values, w)))
                marginal_contrib = np.dot(cov_matrix.values, w) / portfolio_vol
                contrib = w * marginal_contrib
                target_contrib = portfolio_vol / len(w)
                return np.sum((contrib - target_contrib) ** 2)

            constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
            bounds = tuple((0.01, 0.5) for _ in range(len(available_stocks)))
            x0 = np.array([1.0 / len(available_stocks)] * len(available_stocks))

            result = sco.minimize(
                risk_parity_objective, x0, method="SLSQP", bounds=bounds, constraints=constraints
            )

            if result.success:
                return dict(zip(available_stocks, result.x))
            else:
                return weights

        except Exception as e:
            logger.error(f"風險平價再平衡錯誤: {e}")
            return weights


class MaxSharpePortfolio(Portfolio):
    """最大夏普比率投資組合"""

    def __init__(self, risk_free_rate: float = 0.02, **kwargs):
        """初始化最大夏普比率投資組合

        Args:
            risk_free_rate: 無風險利率
        """
        super().__init__(name="MaxSharpe", **kwargs)
        self.risk_free_rate = risk_free_rate

    def optimize(
        self, signals: pd.DataFrame, price_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """最大夏普比率最佳化

        Args:
            signals: 交易訊號
            price_df: 價格資料

        Returns:
            最大夏普比率權重
        """
        # 獲取有買入訊號的股票
        buy_signals = signals[signals.get("signal", signals.get("buy_signal", 0)) > 0]

        if buy_signals.empty or price_df is None:
            return {}

        # 獲取股票列表
        if isinstance(buy_signals.index, pd.MultiIndex):
            stocks = buy_signals.index.get_level_values(0).unique().tolist()
        else:
            stocks = buy_signals.index.tolist()

        if not stocks:
            return {}

        try:
            # 計算期望收益率和協方差矩陣
            price_col = "close" if "close" in price_df.columns else "收盤價"
            returns_data = price_df[price_col].unstack(level=0).pct_change().dropna()

            available_stocks = [s for s in stocks if s in returns_data.columns]
            if not available_stocks:
                logger.warning("沒有可用的股票資料進行最大夏普比率最佳化")
                return {}

            returns_data = returns_data[available_stocks]
            expected_returns_vec = returns_data.mean() * 252  # 年化
            cov_matrix = returns_data.cov() * 252  # 年化

            if not SCIPY_AVAILABLE:
                logger.warning("SciPy 不可用，使用等權重分配")
                weight = 1.0 / len(available_stocks)
                return {stock: weight for stock in available_stocks}

            # 負夏普比率目標函數（最小化負值等於最大化正值）
            def negative_sharpe(weights):
                portfolio_return = np.dot(weights, expected_returns_vec.values)
                portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix.values, weights)))
                if portfolio_vol == 0:
                    return -np.inf
                return -(portfolio_return - self.risk_free_rate) / portfolio_vol

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
                weight = 1.0 / len(available_stocks)
                return {stock: weight for stock in available_stocks}

        except Exception as e:
            logger.error(f"最大夏普比率最佳化錯誤: {e}")
            weight = 1.0 / len(stocks)
            return {stock: weight for stock in stocks}

    def evaluate(
        self, weights: Dict[str, float], price_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """評估最大夏普比率投資組合表現"""
        equal_weight = EqualWeightPortfolio()
        return equal_weight.evaluate(weights, price_df)

    def rebalance(
        self,
        weights: Dict[str, float],
        price_df: pd.DataFrame,
        frequency: str = "M"
    ) -> Dict[str, float]:
        """最大夏普比率再平衡"""
        # 重新計算最大夏普比率權重
        stocks = list(weights.keys())
        if not stocks:
            return weights

        try:
            price_col = "close" if "close" in price_df.columns else "收盤價"
            recent_data = price_df[price_col].tail(252)
            returns_data = recent_data.unstack(level=0).pct_change().dropna()

            available_stocks = [s for s in stocks if s in returns_data.columns]
            if not available_stocks:
                return weights

            returns_data = returns_data[available_stocks]
            expected_returns_vec = returns_data.mean() * 252
            cov_matrix = returns_data.cov() * 252

            if not SCIPY_AVAILABLE:
                weight = 1.0 / len(available_stocks)
                return {stock: weight for stock in available_stocks}

            def negative_sharpe(w):
                portfolio_return = np.dot(w, expected_returns_vec.values)
                portfolio_vol = np.sqrt(np.dot(w, np.dot(cov_matrix.values, w)))
                if portfolio_vol == 0:
                    return -np.inf
                return -(portfolio_return - self.risk_free_rate) / portfolio_vol

            constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
            bounds = tuple((0.01, 0.5) for _ in range(len(available_stocks)))
            x0 = np.array([1.0 / len(available_stocks)] * len(available_stocks))

            result = sco.minimize(
                negative_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints
            )

            if result.success:
                return dict(zip(available_stocks, result.x))
            else:
                return weights

        except Exception as e:
            logger.error(f"最大夏普比率再平衡錯誤: {e}")
            return weights


class MinVariancePortfolio(Portfolio):
    """最小變異數投資組合"""

    def __init__(self, **kwargs):
        """初始化最小變異數投資組合"""
        super().__init__(name="MinVariance", **kwargs)

    def optimize(
        self, signals: pd.DataFrame, price_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """最小變異數最佳化

        Args:
            signals: 交易訊號
            price_df: 價格資料

        Returns:
            最小變異數權重
        """
        # 獲取有買入訊號的股票
        buy_signals = signals[signals.get("signal", signals.get("buy_signal", 0)) > 0]

        if buy_signals.empty or price_df is None:
            return {}

        # 獲取股票列表
        if isinstance(buy_signals.index, pd.MultiIndex):
            stocks = buy_signals.index.get_level_values(0).unique().tolist()
        else:
            stocks = buy_signals.index.tolist()

        if not stocks:
            return {}

        try:
            # 計算協方差矩陣
            price_col = "close" if "close" in price_df.columns else "收盤價"
            returns_data = price_df[price_col].unstack(level=0).pct_change().dropna()

            available_stocks = [s for s in stocks if s in returns_data.columns]
            if not available_stocks:
                logger.warning("沒有可用的股票資料進行最小變異數最佳化")
                return {}

            returns_data = returns_data[available_stocks]
            cov_matrix = returns_data.cov() * 252  # 年化

            if not SCIPY_AVAILABLE:
                logger.warning("SciPy 不可用，使用等權重分配")
                weight = 1.0 / len(available_stocks)
                return {stock: weight for stock in available_stocks}

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
                weight = 1.0 / len(available_stocks)
                return {stock: weight for stock in available_stocks}

        except Exception as e:
            logger.error(f"最小變異數最佳化錯誤: {e}")
            weight = 1.0 / len(stocks)
            return {stock: weight for stock in stocks}

    def evaluate(
        self, weights: Dict[str, float], price_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """評估最小變異數投資組合表現"""
        equal_weight = EqualWeightPortfolio()
        return equal_weight.evaluate(weights, price_df)

    def rebalance(
        self,
        weights: Dict[str, float],
        price_df: pd.DataFrame,
        frequency: str = "M"
    ) -> Dict[str, float]:
        """最小變異數再平衡

        Args:
            weights: 當前權重
            price_df: 價格資料
            frequency: 再平衡頻率（此參數保留以符合介面）

        Returns:
            再平衡後的權重
        """
        # 重新計算最小變異數權重
        stocks = list(weights.keys())
        if not stocks:
            return weights

        try:
            price_col = "close" if "close" in price_df.columns else "收盤價"
            recent_data = price_df[price_col].tail(252)
            returns_data = recent_data.unstack(level=0).pct_change().dropna()

            available_stocks = [s for s in stocks if s in returns_data.columns]
            if not available_stocks:
                return weights

            returns_data = returns_data[available_stocks]
            cov_matrix = returns_data.cov() * 252

            if not SCIPY_AVAILABLE:
                weight = 1.0 / len(available_stocks)
                return {stock: weight for stock in available_stocks}

            def objective(w):
                return np.dot(w, np.dot(cov_matrix.values, w))

            constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
            bounds = tuple((0.01, 0.5) for _ in range(len(available_stocks)))
            x0 = np.array([1.0 / len(available_stocks)] * len(available_stocks))

            result = sco.minimize(
                objective, x0, method="SLSQP", bounds=bounds, constraints=constraints
            )

            if result.success:
                return dict(zip(available_stocks, result.x))
            else:
                return weights

        except Exception as e:
            logger.error(f"最小變異數再平衡錯誤: {e}")
            return weights
