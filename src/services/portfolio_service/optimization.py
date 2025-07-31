"""投資組合最佳化服務模組

此模組提供投資組合最佳化相關的服務功能，包括：
- 各種最佳化演算法的封裝
- 最佳化參數配置
- 最佳化結果處理
- 再平衡邏輯實現

這個模組將複雜的 rebalance_portfolio 函數拆分為更小的、職責單一的函數。
"""

from datetime import datetime
from typing import Dict, List, Tuple, Any
import logging

import pandas as pd
import numpy as np

# 可選依賴
try:
    from scipy.optimize import minimize

    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

from .core import PortfolioServiceCore

# 設定日誌
logger = logging.getLogger(__name__)


class PortfolioOptimizationService:
    """投資組合最佳化服務"""

    def __init__(self, core_service: PortfolioServiceCore):
        """初始化最佳化服務

        Args:
            core_service: 核心服務實例
        """
        self.core = core_service

    def _validate_rebalance_config(
        self,
        portfolio_id: str,
        target_weights: Dict[str, float],
        constraints: Dict[str, Any] = None,
    ) -> Tuple[bool, str]:
        """驗證再平衡配置

        Args:
            portfolio_id: 投資組合ID
            target_weights: 目標權重
            constraints: 約束條件

        Returns:
            (是否有效, 錯誤訊息)
        """
        try:
            # 檢查投資組合是否存在
            portfolio = self.core.get_portfolio(portfolio_id)
            if not portfolio:
                return False, f"投資組合不存在: {portfolio_id}"

            # 檢查權重是否有效
            if not target_weights:
                return False, "目標權重不能為空"

            # 檢查權重總和
            total_weight = sum(target_weights.values())
            if abs(total_weight - 1.0) > 0.01:
                return False, f"權重總和必須為1，當前為: {total_weight:.4f}"

            # 檢查權重是否為非負數
            for symbol, weight in target_weights.items():
                if weight < 0:
                    return False, f"權重不能為負數: {symbol} = {weight}"

            # 檢查約束條件
            if constraints:
                max_weight = constraints.get("max_weight", 1.0)
                min_weight = constraints.get("min_weight", 0.0)

                for symbol, weight in target_weights.items():
                    if weight > max_weight:
                        return (
                            False,
                            f"權重超過最大限制: {symbol} = {weight} > {max_weight}",
                        )
                    if weight < min_weight:
                        return (
                            False,
                            f"權重低於最小限制: {symbol} = {weight} < {min_weight}",
                        )

            return True, ""

        except Exception as e:
            logger.error(f"驗證再平衡配置錯誤: {e}")
            return False, f"驗證錯誤: {e}"

    def _calculate_target_weights(
        self,
        symbols: List[str],
        optimization_method: str = "equal_weight",
        returns_data: pd.DataFrame = None,
        **kwargs,
    ) -> Dict[str, float]:
        """計算目標權重

        Args:
            symbols: 股票代碼列表
            optimization_method: 最佳化方法
            returns_data: 收益率資料
            **kwargs: 其他參數

        Returns:
            目標權重字典
        """
        try:
            if optimization_method == "equal_weight":
                return self._equal_weight_optimization(symbols)
            elif optimization_method == "minimum_variance":
                return self._minimum_variance_optimization(symbols, returns_data)
            elif optimization_method == "risk_parity":
                return self._risk_parity_optimization(symbols, returns_data)
            elif optimization_method == "mean_variance":
                target_return = kwargs.get("target_return", 0.1)
                return self._mean_variance_optimization(
                    symbols, returns_data, target_return
                )
            elif optimization_method == "maximum_sharpe":
                risk_free_rate = kwargs.get("risk_free_rate", 0.02)
                return self._maximum_sharpe_optimization(
                    symbols, returns_data, risk_free_rate
                )
            else:
                logger.warning(f"未知的最佳化方法: {optimization_method}，使用等權重")
                return self._equal_weight_optimization(symbols)

        except Exception as e:
            logger.error(f"計算目標權重錯誤: {e}")
            return self._equal_weight_optimization(symbols)

    def _equal_weight_optimization(self, symbols: List[str]) -> Dict[str, float]:
        """等權重最佳化"""
        if not symbols:
            return {}
        weight = 1.0 / len(symbols)
        return {symbol: weight for symbol in symbols}

    def _minimum_variance_optimization(
        self, symbols: List[str], returns_data: pd.DataFrame = None
    ) -> Dict[str, float]:
        """最小變異數最佳化"""
        if returns_data is None:
            returns_data = self._generate_mock_returns(symbols)

        # 計算協方差矩陣
        cov_matrix = returns_data.cov().values * 252  # 年化

        # 目標函數：最小化變異數
        def objective(weights):
            return np.dot(weights, np.dot(cov_matrix, weights))

        # 約束條件
        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
        bounds = tuple((0.01, 0.5) for _ in range(len(symbols)))

        # 初始權重
        x0 = np.array([1.0 / len(symbols)] * len(symbols))

        # 最佳化
        if not SCIPY_AVAILABLE:
            logger.warning("SciPy 不可用，使用等權重分配")
            return self._equal_weight_optimization(symbols)

        try:
            result = minimize(
                objective, x0, method="SLSQP", bounds=bounds, constraints=constraints
            )

            if result.success:
                weights = dict(zip(symbols, result.x))
                return weights
            else:
                logger.warning(f"最小變異數最佳化失敗: {result.message}")
                return self._equal_weight_optimization(symbols)

        except Exception as e:
            logger.error(f"最小變異數最佳化錯誤: {e}")
            return self._equal_weight_optimization(symbols)

    def _risk_parity_optimization(
        self, symbols: List[str], returns_data: pd.DataFrame = None
    ) -> Dict[str, float]:
        """風險平價最佳化"""
        if returns_data is None:
            returns_data = self._generate_mock_returns(symbols)

        # 計算協方差矩陣
        cov_matrix = returns_data.cov().values * 252  # 年化

        # 風險平價目標函數
        def risk_parity_objective(weights):
            portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
            if portfolio_vol == 0:
                return np.inf
            marginal_contrib = np.dot(cov_matrix, weights) / portfolio_vol
            contrib = weights * marginal_contrib
            target_contrib = portfolio_vol / len(weights)
            return np.sum((contrib - target_contrib) ** 2)

        # 約束條件
        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
        bounds = tuple((0.01, 0.5) for _ in range(len(symbols)))

        # 初始權重
        x0 = np.array([1.0 / len(symbols)] * len(symbols))

        if not SCIPY_AVAILABLE:
            logger.warning("SciPy 不可用，使用等權重分配")
            return self._equal_weight_optimization(symbols)

        try:
            result = minimize(
                risk_parity_objective,
                x0,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
            )

            if result.success:
                return dict(zip(symbols, result.x))
            else:
                logger.warning(f"風險平價最佳化失敗: {result.message}")
                return self._equal_weight_optimization(symbols)

        except Exception as e:
            logger.error(f"風險平價最佳化錯誤: {e}")
            return self._equal_weight_optimization(symbols)

    def _mean_variance_optimization(
        self,
        symbols: List[str],
        returns_data: pd.DataFrame = None,
        target_return: float = 0.1,
    ) -> Dict[str, float]:
        """均值變異數最佳化"""
        if returns_data is None:
            returns_data = self._generate_mock_returns(symbols)

        # 計算期望報酬率和協方差矩陣
        expected_returns = returns_data.mean().values * 252  # 年化
        cov_matrix = returns_data.cov().values * 252  # 年化

        # 目標函數：最小化變異數
        def objective(weights):
            return np.dot(weights, np.dot(cov_matrix, weights))

        # 約束條件
        constraints = [
            {"type": "eq", "fun": lambda x: np.sum(x) - 1},  # 權重和為1
            {
                "type": "eq",
                "fun": lambda x: np.dot(x, expected_returns) - target_return,
            },  # 目標報酬率
        ]
        bounds = tuple((0.01, 0.5) for _ in range(len(symbols)))

        # 初始權重
        x0 = np.array([1.0 / len(symbols)] * len(symbols))

        if not SCIPY_AVAILABLE:
            logger.warning("SciPy 不可用，使用等權重分配")
            return self._equal_weight_optimization(symbols)

        try:
            result = minimize(
                objective, x0, method="SLSQP", bounds=bounds, constraints=constraints
            )

            if result.success:
                return dict(zip(symbols, result.x))
            else:
                logger.warning(f"均值變異數最佳化失敗: {result.message}")
                return self._equal_weight_optimization(symbols)

        except Exception as e:
            logger.error(f"均值變異數最佳化錯誤: {e}")
            return self._equal_weight_optimization(symbols)

    def _maximum_sharpe_optimization(
        self,
        symbols: List[str],
        returns_data: pd.DataFrame = None,
        risk_free_rate: float = 0.02,
    ) -> Dict[str, float]:
        """最大夏普比率最佳化"""
        if returns_data is None:
            returns_data = self._generate_mock_returns(symbols)

        # 計算期望報酬率和協方差矩陣
        expected_returns = returns_data.mean().values * 252  # 年化
        cov_matrix = returns_data.cov().values * 252  # 年化

        # 負夏普比率目標函數（最小化負值等於最大化正值）
        def negative_sharpe(weights):
            portfolio_return = np.dot(weights, expected_returns)
            portfolio_vol = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
            if portfolio_vol == 0:
                return -np.inf
            return -(portfolio_return - risk_free_rate) / portfolio_vol

        # 約束條件
        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
        bounds = tuple((0.01, 0.5) for _ in range(len(symbols)))

        # 初始權重
        x0 = np.array([1.0 / len(symbols)] * len(symbols))

        if not SCIPY_AVAILABLE:
            logger.warning("SciPy 不可用，使用等權重分配")
            return self._equal_weight_optimization(symbols)

        try:
            result = minimize(
                negative_sharpe,
                x0,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
            )

            if result.success:
                return dict(zip(symbols, result.x))
            else:
                logger.warning(f"最大夏普比率最佳化失敗: {result.message}")
                return self._equal_weight_optimization(symbols)

        except Exception as e:
            logger.error(f"最大夏普比率最佳化錯誤: {e}")
            return self._equal_weight_optimization(symbols)

    def _generate_mock_returns(self, symbols: List[str]) -> pd.DataFrame:
        """生成模擬收益率資料"""
        # 生成252天的模擬資料
        n_days = 252
        returns_data = {}

        for symbol in symbols:
            # 使用隨機數生成模擬收益率
            np.random.seed(hash(symbol) % 2**32)  # 確保每個股票的資料一致
            daily_returns = np.random.normal(
                0.0008, 0.02, n_days
            )  # 年化8%收益，20%波動
            returns_data[symbol] = daily_returns

        return pd.DataFrame(returns_data)

    def _execute_trades(
        self,
        portfolio_id: str,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        total_value: float,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """執行交易

        Args:
            portfolio_id: 投資組合ID
            current_weights: 當前權重
            target_weights: 目標權重
            total_value: 總價值

        Returns:
            (是否成功, 錯誤訊息, 交易詳情)
        """
        try:
            trades = []

            # 計算需要調整的股票
            all_symbols = set(current_weights.keys()) | set(target_weights.keys())

            for symbol in all_symbols:
                current_weight = current_weights.get(symbol, 0.0)
                target_weight = target_weights.get(symbol, 0.0)

                weight_diff = target_weight - current_weight

                if abs(weight_diff) > 0.001:  # 只有差異大於0.1%才執行交易
                    trade_value = weight_diff * total_value

                    trade = {
                        "symbol": symbol,
                        "action": "buy" if weight_diff > 0 else "sell",
                        "current_weight": current_weight,
                        "target_weight": target_weight,
                        "weight_change": weight_diff,
                        "trade_value": abs(trade_value),
                        "timestamp": datetime.now().isoformat(),
                    }
                    trades.append(trade)

            # 記錄交易到資料庫（這裡簡化處理）
            trade_summary = {
                "total_trades": len(trades),
                "total_trade_value": sum(trade["trade_value"] for trade in trades),
                "trades": trades,
            }

            logger.info(
                f"執行 {len(trades)} 筆交易，總交易金額: {trade_summary['total_trade_value']:,.0f}"
            )

            return True, "", trade_summary

        except Exception as e:
            logger.error(f"執行交易錯誤: {e}")
            return False, f"交易執行失敗: {e}", {}
