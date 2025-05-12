"""
策略組合與資金配置模組

此模組負責根據交易訊號和風險偏好，決定資金如何分配到不同的股票上，
實現投資組合的最佳化，以達到風險和收益的平衡。

主要功能：
- 投資組合最佳化（如均值方差最佳化、風險平價等）
- 資金配置策略
- 投資組合績效評估
- 投資組合再平衡
"""

import numpy as np
import pandas as pd
import scipy.optimize as sco
from typing import Dict
import matplotlib.pyplot as plt
import seaborn as sns

try:
    from pypfopt import EfficientFrontier, risk_models, expected_returns
except ImportError as e:
    raise ImportError("請先安裝 pypfopt 套件：pip install pypfopt") from e
from .data_ingest import load_data


class Portfolio:
    """投資組合基類，所有具體投資組合策略都應該繼承此類"""

    def __init__(self, name="BasePortfolio"):
        """
        初始化投資組合

        Args:
            name (str): 投資組合名稱
        """
        self.name = name

    def optimize(self, signals, price_df=None):
        """
        最佳化投資組合

        Args:
            signals (pandas.DataFrame): 交易訊號
            price_df (pandas.DataFrame, optional): 價格資料

        Returns:
            pandas.DataFrame: 投資組合權重
        """
        # 基類不實現具體的最佳化邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 optimize 方法")

    def evaluate(self, weights, price_df):
        """
        評估投資組合表現

        Args:
            weights (pandas.DataFrame): 投資組合權重
            price_df (pandas.DataFrame): 價格資料

        Returns:
            dict: 評估結果
        """
        # 基類不實現具體的評估邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 evaluate 方法")

    def rebalance(self, weights, price_df, frequency="M"):
        """
        再平衡投資組合

        Args:
            weights (pandas.DataFrame): 投資組合權重
            price_df (pandas.DataFrame): 價格資料
            frequency (str): 再平衡頻率，可選 'D', 'W', 'M', 'Q', 'Y'

        Returns:
            pandas.DataFrame: 再平衡後的投資組合權重
        """
        # 基類不實現具體的再平衡邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 rebalance 方法")


class EqualWeightPortfolio(Portfolio):
    """等權重投資組合"""

    def __init__(self):
        """初始化等權重投資組合"""
        super().__init__(name="EqualWeight")

    def optimize(self, signals, price_df=None):
        """
        最佳化等權重投資組合

        Args:
            signals (pandas.DataFrame): 交易訊號
            price_df (pandas.DataFrame, optional): 價格資料

        Returns:
            pandas.DataFrame: 投資組合權重
        """
        # 獲取所有有買入訊號的股票
        if "buy_signal" in signals.columns:
            buy_signals = signals[signals["buy_signal"] == 1]
        else:
            buy_signals = signals[signals["signal"] > 0]

        # 按日期分組
        grouped = buy_signals.groupby(level="date")

        # 創建權重資料框架
        weights = pd.DataFrame()

        # 對每個日期，計算等權重
        for date, group in grouped:
            # 獲取該日期的所有股票
            stocks = group.index.get_level_values("stock_id").unique()

            # 計算等權重
            weight = 1.0 / len(stocks) if len(stocks) > 0 else 0.0

            # 創建該日期的權重資料框架
            date_weights = pd.DataFrame(weight, index=stocks, columns=["weight"])
            date_weights["date"] = date
            date_weights.set_index("date", append=True, inplace=True)
            date_weights = date_weights.reorder_levels(["stock_id", "date"])

            # 合併到總權重資料框架
            weights = pd.concat([weights, date_weights])

        return weights

    def evaluate(self, weights, price_df):
        """
        評估等權重投資組合表現

        Args:
            weights (pandas.DataFrame): 投資組合權重
            price_df (pandas.DataFrame): 價格資料

        Returns:
            dict: 評估結果
        """
        # 計算每日收益率
        if "收盤價" not in price_df.columns:
            raise ValueError("價格資料框架必須包含 '收盤價' 欄位")

        daily_returns = price_df["收盤價"].astype(float).pct_change()

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

        # 計算累積收益率
        cumulative_returns = (1 + portfolio_returns).cumprod()

        # 計算年化收益率
        annual_return = portfolio_returns.mean() * 252

        # 計算年化波動率
        annual_volatility = portfolio_returns.std() * np.sqrt(252)

        # 計算夏普比率
        sharpe_ratio = (
            annual_return / annual_volatility if annual_volatility != 0 else 0
        )

        # 計算最大回撤
        max_drawdown = (cumulative_returns / cumulative_returns.cummax() - 1).min()

        return {
            "cumulative_returns": (
                cumulative_returns.iloc[-1] if not cumulative_returns.empty else 1.0
            ),
            "annual_return": annual_return,
            "annual_volatility": annual_volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
        }

    def rebalance(self, weights, price_df, frequency="M"):
        """
        再平衡等權重投資組合

        Args:
            weights (pandas.DataFrame): 投資組合權重
            price_df (pandas.DataFrame): 價格資料
            frequency (str): 再平衡頻率，可選 'D', 'W', 'M', 'Q', 'Y'

        Returns:
            pandas.DataFrame: 再平衡後的投資組合權重
        """
        # 獲取所有日期
        dates = weights.index.get_level_values("date").unique()

        # 按照指定頻率重新採樣日期
        rebalance_dates = pd.date_range(
            start=dates.min(), end=dates.max(), freq=frequency
        )

        # 創建再平衡後的權重資料框架
        rebalanced_weights = pd.DataFrame()

        # 對每個再平衡日期，重新計算等權重
        for rebalance_date in rebalance_dates:
            # 獲取該再平衡日期之前的最後一個交易日
            last_date = (
                dates[dates <= rebalance_date].max()
                if any(dates <= rebalance_date)
                else None
            )

            if last_date is None:
                continue

            # 獲取該日期的權重
            date_weights = weights.xs(last_date, level="date", drop_level=False)

            if date_weights.empty:
                continue

            # 獲取該日期的所有股票
            stocks = date_weights.index.get_level_values("stock_id").unique()

            # 計算等權重
            weight = 1.0 / len(stocks) if len(stocks) > 0 else 0.0

            # 創建該日期的權重資料框架
            rebalance_weights = pd.DataFrame(weight, index=stocks, columns=["weight"])
            rebalance_weights["date"] = rebalance_date
            rebalance_weights.set_index("date", append=True, inplace=True)
            rebalance_weights = rebalance_weights.reorder_levels(["stock_id", "date"])

            # 合併到總權重資料框架
            rebalanced_weights = pd.concat([rebalanced_weights, rebalance_weights])

        return rebalanced_weights


class MeanVariancePortfolio(Portfolio):
    """均值方差最佳化投資組合"""

    def __init__(self, risk_aversion=1.0):
        """
        初始化均值方差最佳化投資組合

        Args:
            risk_aversion (float): 風險厭惡係數
        """
        super().__init__(name="MeanVariance")
        self.risk_aversion = risk_aversion

    def optimize(self, signals, price_df=None):
        """
        最佳化均值方差投資組合

        Args:
            signals (pandas.DataFrame): 交易訊號
            price_df (pandas.DataFrame, optional): 價格資料

        Returns:
            pandas.DataFrame: 投資組合權重
        """
        if price_df is None:
            # 如果沒有提供價格資料，則載入資料
            data_dict = load_data()
            assert isinstance(
                data_dict, dict
            ), "load_data() 應回傳 dict，且需包含 'price' 鍵"
            if "price" not in data_dict:
                raise KeyError(
                    "data_dict 必須包含 'price' 鍵，請檢查 load_data() 回傳內容"
                )
            price_df = data_dict["price"]
            assert isinstance(
                price_df, pd.DataFrame
            ), "data_dict['price'] 應為 pandas.DataFrame"

        # 獲取所有有買入訊號的股票
        if "buy_signal" in signals.columns:
            buy_signals = signals[signals["buy_signal"] == 1]
        else:
            buy_signals = signals[signals["signal"] > 0]

        # 按日期分組
        grouped = buy_signals.groupby(level="date")

        # 創建權重資料框架
        weights = pd.DataFrame()

        # 對每個日期，計算均值方差最佳化權重
        for date, group in grouped:
            # 獲取該日期的所有股票
            stocks = group.index.get_level_values("stock_id").unique()

            if len(stocks) == 0:
                continue

            # 獲取歷史價格資料
            historical_prices = price_df.loc[
                (stocks, slice(None, date)), "收盤價"
            ].astype(float)

            # 計算歷史收益率
            historical_returns = historical_prices.groupby(
                level="stock_id"
            ).pct_change()

            # 刪除缺失值
            historical_returns = historical_returns.dropna()

            # 如果歷史收益率資料不足，則使用等權重
            if len(historical_returns) < len(stocks) * 30:  # 至少需要 30 個交易日的資料
                weight = 1.0 / len(stocks)
                date_weights = pd.DataFrame(weight, index=stocks, columns=["weight"])
            else:
                # 計算預期收益率和協方差矩陣
                expected_returns = historical_returns.groupby(level="stock_id").mean()
                cov_matrix = (
                    historical_returns.groupby(level="stock_id").cov().unstack()
                )

                # 最佳化投資組合權重
                try:
                    weights_opt = self._optimize_weights(expected_returns, cov_matrix)
                    date_weights = pd.DataFrame(
                        weights_opt, index=stocks, columns=["weight"]
                    )
                except BaseException:
                    # 如果最佳化失敗，則使用等權重
                    weight = 1.0 / len(stocks)
                    date_weights = pd.DataFrame(
                        weight, index=stocks, columns=["weight"]
                    )

            # 添加日期索引
            date_weights["date"] = date
            date_weights.set_index("date", append=True, inplace=True)
            date_weights = date_weights.reorder_levels(["stock_id", "date"])

            # 合併到總權重資料框架
            weights = pd.concat([weights, date_weights])

        return weights

    def _optimize_weights(self, expected_returns, cov_matrix):
        """
        最佳化投資組合權重

        Args:
            expected_returns (pandas.Series): 預期收益率
            cov_matrix (pandas.DataFrame): 協方差矩陣

        Returns:
            numpy.ndarray: 最佳化權重
        """
        n = len(expected_returns)

        # 定義目標函數
        def objective(weights):
            portfolio_return = np.sum(expected_returns * weights)
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            return -portfolio_return + self.risk_aversion * portfolio_variance

        # 定義約束條件
        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}  # 權重和為 1
        bounds = tuple((0, 1) for _ in range(n))  # 權重介於 0 和 1 之間

        # 初始猜測
        initial_weights = np.ones(n) / n

        # 最佳化
        result = sco.minimize(
            objective,
            initial_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        return result["x"]

    def evaluate(self, weights, price_df):
        """
        評估均值方差投資組合表現

        Args:
            weights (pandas.DataFrame): 投資組合權重
            price_df (pandas.DataFrame): 價格資料

        Returns:
            dict: 評估結果
        """
        # 計算每日收益率
        if "收盤價" not in price_df.columns:
            raise ValueError("價格資料框架必須包含 '收盤價' 欄位")

        daily_returns = price_df["收盤價"].astype(float).pct_change()

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

        # 計算累積收益率
        cumulative_returns = (1 + portfolio_returns).cumprod()

        # 計算年化收益率
        annual_return = portfolio_returns.mean() * 252

        # 計算年化波動率
        annual_volatility = portfolio_returns.std() * np.sqrt(252)

        # 計算夏普比率
        sharpe_ratio = (
            annual_return / annual_volatility if annual_volatility != 0 else 0
        )

        # 計算最大回撤
        max_drawdown = (cumulative_returns / cumulative_returns.cummax() - 1).min()

        return {
            "cumulative_returns": (
                cumulative_returns.iloc[-1] if not cumulative_returns.empty else 1.0
            ),
            "annual_return": annual_return,
            "annual_volatility": annual_volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
        }


class RiskParityPortfolio(Portfolio):
    """風險平價投資組合"""

    def __init__(self):
        """初始化風險平價投資組合"""
        super().__init__(name="RiskParity")

    def optimize(self, signals, price_df=None):
        """
        最佳化風險平價投資組合

        Args:
            signals (pandas.DataFrame): 交易訊號
            price_df (pandas.DataFrame, optional): 價格資料

        Returns:
            pandas.DataFrame: 投資組合權重
        """
        if price_df is None:
            # 如果沒有提供價格資料，則載入資料
            data_dict = load_data()
            assert isinstance(
                data_dict, dict
            ), "load_data() 應回傳 dict，且需包含 'price' 鍵"
            if "price" not in data_dict:
                raise KeyError(
                    "data_dict 必須包含 'price' 鍵，請檢查 load_data() 回傳內容"
                )
            price_df = data_dict["price"]
            assert isinstance(
                price_df, pd.DataFrame
            ), "data_dict['price'] 應為 pandas.DataFrame"

        # 獲取所有有買入訊號的股票
        if "buy_signal" in signals.columns:
            buy_signals = signals[signals["buy_signal"] == 1]
        else:
            buy_signals = signals[signals["signal"] > 0]

        # 按日期分組
        grouped = buy_signals.groupby(level="date")

        # 創建權重資料框架
        weights = pd.DataFrame()

        # 對每個日期，計算風險平價權重
        for date, group in grouped:
            # 獲取該日期的所有股票
            stocks = group.index.get_level_values("stock_id").unique()

            if len(stocks) == 0:
                continue

            # 獲取歷史價格資料
            historical_prices = price_df.loc[
                (stocks, slice(None, date)), "收盤價"
            ].astype(float)

            # 計算歷史收益率
            historical_returns = historical_prices.groupby(
                level="stock_id"
            ).pct_change()

            # 刪除缺失值
            historical_returns = historical_returns.dropna()

            # 如果歷史收益率資料不足，則使用等權重
            if len(historical_returns) < len(stocks) * 30:  # 至少需要 30 個交易日的資料
                weight = 1.0 / len(stocks)
                date_weights = pd.DataFrame(weight, index=stocks, columns=["weight"])
            else:
                # 計算協方差矩陣
                cov_matrix = (
                    historical_returns.groupby(level="stock_id").cov().unstack()
                )

                # 最佳化風險平價權重
                try:
                    weights_opt = self._optimize_weights(cov_matrix)
                    date_weights = pd.DataFrame(
                        weights_opt, index=stocks, columns=["weight"]
                    )
                except BaseException:
                    # 如果最佳化失敗，則使用等權重
                    weight = 1.0 / len(stocks)
                    date_weights = pd.DataFrame(
                        weight, index=stocks, columns=["weight"]
                    )

            # 添加日期索引
            date_weights["date"] = date
            date_weights.set_index("date", append=True, inplace=True)
            date_weights = date_weights.reorder_levels(["stock_id", "date"])

            # 合併到總權重資料框架
            weights = pd.concat([weights, date_weights])

        return weights

    def _optimize_weights(self, cov_matrix):
        """
        最佳化風險平價權重

        Args:
            cov_matrix (pandas.DataFrame): 協方差矩陣

        Returns:
            numpy.ndarray: 最佳化權重
        """
        n = cov_matrix.shape[0]

        # 定義目標函數
        def objective(weights):
            # 計算每個資產的風險貢獻
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            risk_contribution = (
                weights * np.dot(cov_matrix, weights) / portfolio_variance
            )

            # 計算風險貢獻的標準差
            target_risk = 1.0 / n
            risk_deviation = np.sum((risk_contribution - target_risk) ** 2)

            return risk_deviation

        # 定義約束條件
        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}  # 權重和為 1
        bounds = tuple((0, 1) for _ in range(n))  # 權重介於 0 和 1 之間

        # 初始猜測
        initial_weights = np.ones(n) / n

        # 最佳化
        result = sco.minimize(
            objective,
            initial_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )

        return result["x"]


def optimize(signals, portfolio_type="equal_weight", **portfolio_params):
    """
    最佳化投資組合的主函數

    Args:
        signals (pandas.DataFrame): 交易訊號
        portfolio_type (str): 投資組合類型，可選 'equal_weight', 'mean_variance', 'risk_parity'
        **portfolio_params: 投資組合參數

    Returns:
        pandas.DataFrame: 投資組合權重
    """
    # 載入價格資料
    data_dict = load_data()
    price_df = data_dict["price"]

    # 創建投資組合
    if portfolio_type == "equal_weight":
        portfolio = EqualWeightPortfolio()
    elif portfolio_type == "mean_variance":
        risk_aversion = portfolio_params.get("risk_aversion", 1.0)
        portfolio = MeanVariancePortfolio(risk_aversion=risk_aversion)
    elif portfolio_type == "risk_parity":
        portfolio = RiskParityPortfolio()
    else:
        raise ValueError(f"不支援的投資組合類型: {portfolio_type}")

    # 最佳化投資組合
    weights = portfolio.optimize(signals, price_df)

    return weights


def equal_weight(signals: pd.DataFrame) -> Dict[str, float]:
    """
    等權重資金分配算法

    給所有 signals==1 的標的平均分配權重

    Args:
        signals (pandas.DataFrame): 交易訊號，包含 signal 或 buy_signal 欄位

    Returns:
        Dict[str, float]: 股票代號到權重的映射字典

    Example:
        weights = equal_weight(signals_df)
        # 返回如 {'2330': 0.25, '2317': 0.25, '2454': 0.25, '2412': 0.25}
    """
    # 獲取所有有買入訊號的股票
    if "buy_signal" in signals.columns:
        buy_signals = signals[signals["buy_signal"] == 1]
    else:
        buy_signals = signals[signals["signal"] > 0]

    # 獲取股票代號
    stocks = buy_signals.index.get_level_values("stock_id").unique()

    # 如果沒有股票有買入訊號，返回空字典
    if len(stocks) == 0:
        return {}

    # 計算等權重
    weight = 1.0 / len(stocks)

    # 創建股票代號到權重的映射字典
    weights_dict = {stock: weight for stock in stocks}

    return weights_dict


def kelly_weight(signals: pd.DataFrame, returns: pd.Series) -> Dict[str, float]:
    """
    Kelly 公式資金分配算法

    根據 Kelly 公式計算每檔股票的最優權重

    Args:
        signals (pandas.DataFrame): 交易訊號，包含 signal 或 buy_signal 欄位
        returns (pandas.Series): 歷史報酬率序列，索引為股票代號

    Returns:
        Dict[str, float]: 股票代號到權重的映射字典

    Example:
        weights = kelly_weight(signals_df, returns_series)
        # 返回如 {'2330': 0.35, '2317': 0.20, '2454': 0.30, '2412': 0.15}
    """
    # 獲取所有有買入訊號的股票
    if "buy_signal" in signals.columns:
        buy_signals = signals[signals["buy_signal"] == 1]
    else:
        buy_signals = signals[signals["signal"] > 0]

    # 獲取股票代號
    stocks = buy_signals.index.get_level_values("stock_id").unique()

    # 如果沒有股票有買入訊號，返回空字典
    if len(stocks) == 0:
        return {}

    # 創建股票代號到權重的映射字典
    weights_dict = {}

    # 對每個股票，計算 Kelly 權重
    for stock in stocks:
        if stock in returns.index:
            # 獲取該股票的歷史報酬率
            stock_returns = returns.loc[stock]

            # 計算平均報酬率和標準差
            mean_return = stock_returns.mean()
            var_return = stock_returns.var()

            # 使用 Kelly 公式計算權重
            # f* = μ / σ²，其中 μ 是平均報酬率，σ² 是報酬率方差
            if var_return > 0:
                kelly_weight = mean_return / var_return

                # 限制權重在 0 到 1 之間
                kelly_weight = max(0, min(1, kelly_weight))
            else:
                kelly_weight = 0

            weights_dict[stock] = kelly_weight
        else:
            # 如果沒有該股票的歷史報酬率資料，則給予 0 權重
            weights_dict[stock] = 0

    # 如果所有權重都為 0，則使用等權重
    if sum(weights_dict.values()) == 0:
        weight = 1.0 / len(stocks)
        weights_dict = {stock: weight for stock in stocks}
    else:
        # 標準化權重，使其總和為 1
        total_weight = sum(weights_dict.values())
        weights_dict = {
            stock: weight / total_weight for stock, weight in weights_dict.items()
        }

    return weights_dict


def var_minimize(signals: pd.DataFrame, prices: pd.DataFrame) -> Dict[str, float]:
    """
    最小化風險的資金分配算法

    使用 PyPortfolioOpt 計算最小化風險的投資組合權重

    Args:
        signals (pandas.DataFrame): 交易訊號，包含 signal 或 buy_signal 欄位
        prices (pandas.DataFrame): 價格資料，索引為 (股票代號, 日期)，包含 'close' 或 '收盤價' 欄位

    Returns:
        Dict[str, float]: 股票代號到權重的映射字典

    Example:
        weights = var_minimize(signals_df, prices_df)
        # 返回如 {'2330': 0.15, '2317': 0.25, '2454': 0.35, '2412': 0.25}
    """
    # signals 必須為 DataFrame 且有正確 multi-index
    assert isinstance(signals, pd.DataFrame), "signals 必須為 pandas.DataFrame"
    assert (
        signals.index.nlevels >= 1
    ), "signals 必須有至少一層 index (建議為 MultiIndex: stock_id, date)"
    # 獲取所有有買入訊號的股票
    if "buy_signal" in signals.columns:
        buy_signals = signals[signals["buy_signal"] == 1]
    else:
        if "signal" not in signals.columns:
            raise ValueError("signals 必須包含 'buy_signal' 或 'signal' 欄位")
        buy_signals = signals[signals["signal"] > 0]

    # 獲取股票代號
    if "stock_id" in buy_signals.index.names:
        stocks = buy_signals.index.get_level_values("stock_id").unique()
    else:
        raise ValueError("signals 的 index 必須包含 'stock_id' 層級")

    # 如果沒有股票有買入訊號，返回空字典
    if len(stocks) == 0:
        return {}

    # 確定價格欄位
    if "close" in prices.columns:
        price_col = "close"
    elif "收盤價" in prices.columns:
        price_col = "收盤價"
    else:
        raise ValueError("價格資料必須包含 'close' 或 '收盤價' 欄位")

    # 獲取這些股票的價格資料
    stock_prices = prices.loc[
        prices.index.get_level_values("stock_id").isin(stocks), price_col
    ]

    # 將價格資料轉換為 DataFrame，索引為日期，列為股票代號
    price_df = stock_prices.unstack(level="stock_id")

    # 如果價格資料不足，則使用等權重
    if price_df.shape[0] < 30 or price_df.shape[1] < 2:
        return equal_weight(signals)

    try:
        # 計算預期收益率
        mu = expected_returns.mean_historical_return(price_df)

        # 計算協方差矩陣
        S = risk_models.sample_cov(price_df)

        # 設置有效前沿
        ef = EfficientFrontier(mu, S)

        # 最小化波動率
        ef.min_volatility()

        # 清理權重
        cleaned_weights = ef.clean_weights()

        # 轉換為字典
        weights_dict = {
            stock: weight for stock, weight in cleaned_weights.items() if weight > 0.01
        }

        # 標準化權重，使其總和為 1
        total_weight = sum(weights_dict.values())
        weights_dict = {
            stock: weight / total_weight for stock, weight in weights_dict.items()
        }

        return weights_dict
    except Exception as e:
        print(f"最小化風險優化失敗: {e}")
        return equal_weight(signals)


def backtest_portfolio(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    method: str = "equal",
    show_plot: bool = True,
) -> pd.DataFrame:
    """
    回測投資組合表現

    Args:
        signals (pandas.DataFrame): 交易訊號，包含 signal 或 buy_signal 欄位
        prices (pandas.DataFrame): 價格資料，索引為 (股票代號, 日期)，包含 'close' 或 '收盤價' 欄位
        method (str): 資金分配方法，可選 'equal', 'var_minimize', 'kelly'
        show_plot (bool): 是否繪製圖表，預設 True

    Returns:
        pandas.DataFrame: 投資組合權重，索引為 (股票代號, 日期)，包含 'weight' 欄位

    Example:
        weights_df = backtest_portfolio(signals_df, prices_df, method='var_minimize')
    """
    # 確定價格欄位
    price_col = "close" if "close" in prices.columns else "收盤價"

    # 獲取所有日期
    dates = signals.index.get_level_values("date").unique()

    # 創建權重資料框架
    weights_df = pd.DataFrame(columns=["weight"])

    # 計算歷史報酬率（用於 Kelly 方法）
    returns = prices[price_col].pct_change().groupby(level="stock_id").mean()

    # 對每個日期，計算投資組合權重
    for date in dates:
        # 獲取該日期的訊號
        date_signals = signals.xs(date, level="date", drop_level=False)
        if isinstance(date_signals, pd.Series):
            date_signals = date_signals.to_frame().T
        # 獲取該日期之前的價格資料
        date_prices = prices.loc[prices.index.get_level_values("date") <= date]
        # 根據方法計算權重
        if method == "equal":
            weights_dict = equal_weight(date_signals)
        elif method == "var_minimize":
            weights_dict = var_minimize(date_signals, date_prices)
        elif method == "kelly":
            weights_dict = kelly_weight(date_signals, returns)
        else:
            raise ValueError(f"不支援的資金分配方法: {method}")
        # 創建該日期的權重資料框架
        if weights_dict:
            date_weights = pd.DataFrame.from_dict(
                weights_dict, orient="index", columns=["weight"]
            )
            date_weights["date"] = date
            date_weights = date_weights.reset_index().rename(
                columns={"index": "stock_id"}
            )
            date_weights = date_weights.set_index(["stock_id", "date"])
            # 合併到總權重資料框架
            weights_df = pd.concat([weights_df, date_weights])

    # 計算投資組合表現
    portfolio_performance = evaluate_portfolio(weights_df, prices)

    # 繪製投資組合表現圖
    plot_portfolio_performance(portfolio_performance, show_plot=show_plot)

    return weights_df


def evaluate_portfolio(weights: pd.DataFrame, prices: pd.DataFrame) -> dict:
    """
    評估投資組合表現

    Args:
        weights (pandas.DataFrame): 投資組合權重，索引為 (股票代號, 日期)，包含 'weight' 欄位
        prices (pandas.DataFrame): 價格資料，索引為 (股票代號, 日期)，包含 'close' 或 '收盤價' 欄位

    Returns:
        dict: 評估結果，包含 'returns', 'cumulative_returns', 'annual_return', 'annual_volatility', 'sharpe_ratio', 'max_drawdown'
    """
    # 確定價格欄位
    price_col = "close" if "close" in prices.columns else "收盤價"

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
        # 修正 index bug：正確解包 stock_id
        portfolio_return = 0.0
        for idx, row in date_weights.iterrows():
            if isinstance(idx, tuple) and len(idx) == 2:
                stock_id, _ = idx
            else:
                stock_id = idx
            if (stock_id, date) in date_returns.index:
                portfolio_return += row["weight"] * date_returns.loc[(stock_id, date)]
        portfolio_returns[date] = portfolio_return

    # 計算累積收益率
    cumulative_returns = (1 + portfolio_returns).cumprod()

    # 計算年化收益率
    annual_return = portfolio_returns.mean() * 252

    # 計算年化波動率
    annual_volatility = portfolio_returns.std() * np.sqrt(252)

    # 計算夏普比率
    sharpe_ratio = annual_return / annual_volatility if annual_volatility != 0 else 0

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


def plot_portfolio_performance(performance: dict, show_plot: bool = True):
    """
    繪製投資組合表現圖

    Args:
        performance (dict): 評估結果，包含 'returns', 'cumulative_returns'
        show_plot (bool): 是否呼叫 plt.show()，預設 True
    """
    # 若 returns 為空則直接 return
    if performance["returns"] is None or performance["returns"].empty:
        return
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
    sns.barplot(x=monthly_returns.index, y=monthly_returns.values)
    plt.title("投資組合每月收益率")
    plt.xlabel("月份")
    plt.ylabel("收益率")
    plt.xticks(rotation=90)
    plt.grid(True)

    plt.tight_layout()
    if show_plot:
        try:
            plt.show()
        except Exception as e:
            print(f"無法顯示圖表: {e}")
