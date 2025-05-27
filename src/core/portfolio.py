"""策略組合與資金配置模組

此模組負責根據交易訊號和風險偏好，決定資金如何分配到不同的股票上，
實現投資組合的最佳化，以達到風險和收益的平衡。

主要功能：
- 投資組合最佳化（如均值方差最佳化、風險平價等）
- 資金配置策略
- 投資組合績效評估
- 投資組合再平衡
"""

from typing import Dict, Optional, Any
import logging

import numpy as np
import pandas as pd

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

from .data_ingest import load_data

# 設定日誌
logger = logging.getLogger(__name__)


class PortfolioOptimizationError(Exception):
    """投資組合最佳化錯誤"""
    pass


class DependencyError(Exception):
    """依賴套件錯誤"""
    pass


class Portfolio:
    """投資組合基類，所有具體投資組合策略都應該繼承此類"""

    def __init__(
        self,
        name="BasePortfolio",
        initial_capital=1000000,
        transaction_cost=0.001425,
        tax=0.003,
        slippage=0.001,
    ):
        """
        初始化投資組合

        Args:
            name (str): 投資組合名稱
            initial_capital (float): 初始資金
            transaction_cost (float): 交易成本比例
            tax (float): 交易稅比例
            slippage (float): 滑價比例
        """
        self.name = name
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.tax = tax
        self.slippage = slippage

        # 投資組合狀態
        self.cash = initial_capital
        self.positions = (
            {}
        )  # {stock_id: {'shares': 100, 'cost': 50.0, 'value': 5000.0}}
        self.history = []  # 歷史狀態記錄
        self.transactions = []  # 交易記錄

    def optimize(self, signals: pd.DataFrame, price_df: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """最佳化投資組合

        Args:
            signals: 交易訊號
            price_df: 價格資料

        Returns:
            最佳化後的權重

        Raises:
            NotImplementedError: 子類必須實現此方法
        """
        # 基類不實現具體的最佳化邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 optimize 方法")

    def evaluate(self, weights: Dict[str, float], price_df: pd.DataFrame) -> Dict[str, Any]:
        """評估投資組合表現

        Args:
            weights: 投資組合權重
            price_df: 價格資料

        Returns:
            評估結果

        Raises:
            NotImplementedError: 子類必須實現此方法
        """
        # 基類不實現具體的評估邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 evaluate 方法")

    def rebalance(self, weights: Dict[str, float], price_df: pd.DataFrame, frequency: str = "M") -> Dict[str, float]:
        """再平衡投資組合

        Args:
            weights: 投資組合權重
            price_df: 價格資料
            frequency: 再平衡頻率，可選 'D', 'W', 'M', 'Q', 'Y'

        Returns:
            再平衡後的投資組合權重

        Raises:
            NotImplementedError: 子類必須實現此方法
        """
        # 基類不實現具體的再平衡邏輯
        # 子類應該覆寫此方法
        raise NotImplementedError("子類必須實現 rebalance 方法")

    def simulate(
        self, signals, price_df, start_date=None, end_date=None, rebalance_freq="M"
    ):
        """
        模擬投資組合表現

        Args:
            signals (pandas.DataFrame): 交易訊號
            price_df (pandas.DataFrame): 價格資料
            start_date (datetime.date, optional): 開始日期
            end_date (datetime.date, optional): 結束日期
            rebalance_freq (str): 再平衡頻率，可選 'D', 'W', 'M', 'Q', 'Y'

        Returns:
            dict: 模擬結果，包含 'history', 'transactions', 'performance'
        """
        # 確保價格資料有收盤價欄位
        if "收盤價" not in price_df.columns and "close" not in price_df.columns:
            raise ValueError("價格資料必須包含 '收盤價' 或 'close' 欄位")

        # 確定收盤價欄位名稱
        close_col = "收盤價" if "收盤價" in price_df.columns else "close"

        # 篩選日期範圍
        if start_date is not None:
            price_df = price_df[price_df.index.get_level_values("date") >= start_date]
            signals = signals[signals.index.get_level_values("date") >= start_date]
        if end_date is not None:
            price_df = price_df[price_df.index.get_level_values("date") <= end_date]
            signals = signals[signals.index.get_level_values("date") <= end_date]

        # 獲取所有交易日
        trading_days = sorted(price_df.index.get_level_values("date").unique())

        # 初始化投資組合狀態
        self.cash = self.initial_capital
        self.positions = {}
        self.history = []
        self.transactions = []

        # 計算再平衡日期
        rebalance_dates = pd.date_range(
            start=trading_days[0], end=trading_days[-1], freq=rebalance_freq
        )

        # 模擬每個交易日
        for day in trading_days:
            # 獲取當日價格
            day_prices = price_df.xs(day, level="date", drop_level=False)

            # 更新持倉價值
            self._update_positions_value(day_prices, close_col)

            # 記錄當日狀態
            self._record_state(day)

            # 檢查是否為再平衡日
            if day in rebalance_dates:
                # 獲取當日訊號
                day_signals = (
                    signals.xs(day, level="date", drop_level=False)
                    if day in signals.index.get_level_values("date")
                    else pd.DataFrame()
                )

                if not day_signals.empty:
                    # 最佳化投資組合權重
                    weights = self.optimize(day_signals, price_df.loc[:day])

                    # 執行再平衡
                    self._execute_rebalance(weights, day_prices, close_col)

        # 計算績效指標
        performance = self._calculate_performance()

        return {
            "history": self.history,
            "transactions": self.transactions,
            "performance": performance,
        }

    def _update_positions_value(self, day_prices, close_col):
        """
        更新持倉價值

        Args:
            day_prices (pandas.DataFrame): 當日價格資料
            close_col (str): 收盤價欄位名稱
        """
        for stock_id, position in list(self.positions.items()):
            if (
                stock_id,
                day_prices.index.get_level_values("date")[0],
            ) in day_prices.index:
                price = day_prices.loc[
                    (stock_id, day_prices.index.get_level_values("date")[0]), close_col
                ]
                self.positions[stock_id]["value"] = position["shares"] * price

    def _record_state(self, date):
        """
        記錄投資組合狀態

        Args:
            date (datetime.date): 日期
        """
        # 計算總價值
        total_value = self.cash + sum(
            position["value"] for position in self.positions.values()
        )

        # 記錄狀態
        self.history.append(
            {
                "date": date,
                "cash": self.cash,
                "positions": {
                    stock_id: position.copy()
                    for stock_id, position in self.positions.items()
                },
                "total_value": total_value,
            }
        )

    def _execute_rebalance(self, weights, day_prices, close_col):
        """
        執行再平衡

        Args:
            weights (pandas.DataFrame): 投資組合權重
            day_prices (pandas.DataFrame): 當日價格資料
            close_col (str): 收盤價欄位名稱
        """
        # 計算總價值
        total_value = self.cash + sum(
            position["value"] for position in self.positions.values()
        )

        # 計算目標持倉
        target_positions = {}
        for (stock_id, _), row in weights.iterrows():
            if (
                stock_id,
                day_prices.index.get_level_values("date")[0],
            ) in day_prices.index:
                price = day_prices.loc[
                    (stock_id, day_prices.index.get_level_values("date")[0]), close_col
                ]
                target_value = total_value * row["weight"]
                target_shares = target_value / price
                target_positions[stock_id] = {
                    "shares": target_shares,
                    "value": target_value,
                }

        # 賣出不在目標持倉中的股票
        for stock_id in list(self.positions.keys()):
            if stock_id not in target_positions:
                self._sell_stock(stock_id, day_prices, close_col)

        # 調整持倉
        for stock_id, target in target_positions.items():
            if stock_id in self.positions:
                # 調整現有持倉
                current_shares = self.positions[stock_id]["shares"]
                target_shares = target["shares"]

                if target_shares > current_shares:
                    # 買入股票
                    self._buy_stock(
                        stock_id, target_shares - current_shares, day_prices, close_col
                    )
                elif target_shares < current_shares:
                    # 賣出股票
                    self._sell_stock(
                        stock_id, current_shares - target_shares, day_prices, close_col
                    )
            else:
                # 買入新股票
                self._buy_stock(stock_id, target["shares"], day_prices, close_col)

    def _buy_stock(self, stock_id, shares, day_prices, close_col):
        """
        買入股票

        Args:
            stock_id (str): 股票代號
            shares (float): 股數
            day_prices (pandas.DataFrame): 當日價格資料
            close_col (str): 收盤價欄位名稱
        """
        date = day_prices.index.get_level_values("date")[0]

        if (stock_id, date) in day_prices.index:
            price = day_prices.loc[(stock_id, date), close_col]
            buy_price = price * (1 + self.slippage)
            amount = shares * buy_price
            transaction_cost = amount * self.transaction_cost

            # 檢查資金是否足夠
            if self.cash >= amount + transaction_cost:
                # 更新持倉
                if stock_id in self.positions:
                    # 更新現有持倉
                    current_shares = self.positions[stock_id]["shares"]
                    current_cost = self.positions[stock_id]["cost"]

                    # 計算新的平均成本
                    total_shares = current_shares + shares
                    total_cost = current_shares * current_cost + shares * buy_price
                    avg_cost = total_cost / total_shares

                    self.positions[stock_id]["shares"] = total_shares
                    self.positions[stock_id]["cost"] = avg_cost
                    self.positions[stock_id]["value"] = total_shares * price
                else:
                    # 新增持倉
                    self.positions[stock_id] = {
                        "shares": shares,
                        "cost": buy_price,
                        "value": shares * price,
                    }

                # 更新現金
                self.cash -= amount + transaction_cost

                # 記錄交易
                self.transactions.append(
                    {
                        "date": date,
                        "stock_id": stock_id,
                        "action": "buy",
                        "shares": shares,
                        "price": buy_price,
                        "amount": amount,
                        "transaction_cost": transaction_cost,
                        "tax": 0.0,  # 買入不課稅
                    }
                )

    def _sell_stock(self, stock_id, shares=None, day_prices=None, close_col=None):
        """
        賣出股票

        Args:
            stock_id (str): 股票代號
            shares (float, optional): 股數，如果為 None 則賣出全部
            day_prices (pandas.DataFrame): 當日價格資料
            close_col (str): 收盤價欄位名稱
        """
        if stock_id in self.positions:
            date = day_prices.index.get_level_values("date")[0]

            if (stock_id, date) in day_prices.index:
                price = day_prices.loc[(stock_id, date), close_col]
                sell_price = price * (1 - self.slippage)

                # 確定賣出股數
                if shares is None or shares >= self.positions[stock_id]["shares"]:
                    # 賣出全部
                    shares = self.positions[stock_id]["shares"]
                    full_sell = True
                else:
                    # 部分賣出
                    full_sell = False

                amount = shares * sell_price
                transaction_cost = amount * self.transaction_cost
                tax = amount * self.tax

                # 更新持倉
                if full_sell:
                    # 刪除持倉
                    del self.positions[stock_id]
                else:
                    # 更新持倉
                    self.positions[stock_id]["shares"] -= shares
                    self.positions[stock_id]["value"] = (
                        self.positions[stock_id]["shares"] * price
                    )

                # 更新現金
                self.cash += amount - transaction_cost - tax

                # 記錄交易
                self.transactions.append(
                    {
                        "date": date,
                        "stock_id": stock_id,
                        "action": "sell",
                        "shares": shares,
                        "price": sell_price,
                        "amount": amount,
                        "transaction_cost": transaction_cost,
                        "tax": tax,
                    }
                )

    def _calculate_performance(self):
        """
        計算績效指標

        Returns:
            dict: 績效指標
        """
        if not self.history:
            return {}

        # 提取權益曲線
        equity_curve = pd.Series(
            [state["total_value"] for state in self.history],
            index=[state["date"] for state in self.history],
        )

        # 計算每日收益率
        daily_returns = equity_curve.pct_change().dropna()

        # 計算累積收益率
        (1 + daily_returns).cumprod()

        # 計算年化收益率
        annual_return = daily_returns.mean() * 252

        # 計算年化波動率
        annual_volatility = daily_returns.std() * np.sqrt(252)

        # 計算夏普比率
        sharpe_ratio = (
            annual_return / annual_volatility if annual_volatility != 0 else 0
        )

        # 計算最大回撤
        max_drawdown = (equity_curve / equity_curve.cummax() - 1).min()

        # 計算勝率
        if self.transactions:
            trades = pd.DataFrame(self.transactions)
            buy_trades = trades[trades["action"] == "buy"].set_index("stock_id")
            sell_trades = trades[trades["action"] == "sell"].set_index("stock_id")

            # 計算每筆交易的盈虧
            profits = []
            for stock_id in sell_trades.index.unique():
                if stock_id in buy_trades.index:
                    buy_price = (
                        buy_trades.loc[stock_id, "price"].mean()
                        if isinstance(buy_trades.loc[stock_id, "price"], pd.Series)
                        else buy_trades.loc[stock_id, "price"]
                    )
                    sell_price = (
                        sell_trades.loc[stock_id, "price"].mean()
                        if isinstance(sell_trades.loc[stock_id, "price"], pd.Series)
                        else sell_trades.loc[stock_id, "price"]
                    )
                    profit = (sell_price - buy_price) / buy_price
                    profits.append(profit)

            if profits:
                win_rate = sum(1 for p in profits if p > 0) / len(profits)
            else:
                win_rate = 0
        else:
            win_rate = 0

        return {
            "initial_capital": self.initial_capital,
            "final_value": equity_curve.iloc[-1],
            "total_return": (equity_curve.iloc[-1] / self.initial_capital - 1) * 100,
            "annual_return": annual_return * 100,
            "annual_volatility": annual_volatility * 100,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown * 100,
            "win_rate": win_rate * 100,
        }


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
        """最佳化投資組合權重

        Args:
            expected_returns: 預期收益率
            cov_matrix: 協方差矩陣

        Returns:
            最佳化權重

        Raises:
            DependencyError: 當scipy不可用時
        """
        if not SCIPY_AVAILABLE:
            raise DependencyError("scipy套件不可用，無法進行投資組合最佳化")

        n = len(expected_returns)

        # 定義目標函數
        def objective(weights):
            """計算目標函數值

            Args:
                weights: 投資組合權重
            """
            portfolio_return = np.sum(expected_returns * weights)
            portfolio_variance = np.dot(weights.T, np.dot(cov_matrix, weights))
            return -portfolio_return + self.risk_aversion * portfolio_variance

        # 定義約束條件
        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}  # 權重和為 1
        bounds = tuple((0, 1) for _ in range(n))  # 權重介於 0 和 1 之間

        # 初始猜測
        initial_weights = np.ones(n) / n

        try:
            # 最佳化
            result = sco.minimize(
                objective,
                initial_weights,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
            )

            if not result.success:
                logger.warning(f"最佳化未收斂: {result.message}")
                # 返回等權重作為備選方案
                return np.ones(n) / n

            return result["x"]
        except Exception as e:
            logger.error(f"最佳化過程中發生錯誤: {e}")
            # 返回等權重作為備選方案
            return np.ones(n) / n

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

    def rebalance(self, weights: Dict[str, float], price_df: pd.DataFrame, frequency: str = "M") -> Dict[str, float]:
        """再平衡均值方差投資組合

        Args:
            weights: 當前投資組合權重
            price_df: 價格資料
            frequency: 再平衡頻率

        Returns:
            再平衡後的投資組合權重
        """
        # 對於均值方差投資組合，重新計算最佳權重
        try:
            # 獲取股票列表
            symbols = list(weights.keys())

            # 計算歷史收益率
            historical_returns = price_df.loc[symbols, "收盤價"].pct_change().dropna()

            if len(historical_returns) < 30:  # 資料不足
                logger.warning("歷史資料不足，使用等權重")
                equal_weight = 1.0 / len(symbols)
                return {symbol: equal_weight for symbol in symbols}

            # 計算預期收益率和協方差矩陣
            expected_returns = historical_returns.mean() * 252  # 年化
            cov_matrix = historical_returns.cov() * 252  # 年化

            # 重新最佳化
            optimized_weights = self._optimize_weights(expected_returns, cov_matrix)

            # 轉換為字典格式
            return dict(zip(symbols, optimized_weights))

        except Exception as e:
            logger.error(f"再平衡失敗: {e}")
            # 返回等權重作為備選方案
            equal_weight = 1.0 / len(weights)
            return {symbol: equal_weight for symbol in weights.keys()}


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
            """
            計算每個資產的風險貢獻

            Args:
                weights: 投資組合權重
            """
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

    def evaluate(self, weights: Dict[str, float], price_df: pd.DataFrame) -> Dict[str, Any]:
        """評估風險平價投資組合表現

        Args:
            weights: 投資組合權重
            price_df: 價格資料

        Returns:
            評估結果字典，包含風險貢獻分析和績效指標
        """
        try:
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
                    if hasattr(weights, 'xs') and date in weights.index.get_level_values("date")
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

            # 計算風險貢獻分析
            risk_contribution = self._calculate_risk_contribution(weights, daily_returns)

            return {
                "cumulative_returns": (
                    cumulative_returns.iloc[-1] if not cumulative_returns.empty else 1.0
                ),
                "annual_return": annual_return,
                "annual_volatility": annual_volatility,
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": max_drawdown,
                "risk_contribution": risk_contribution,
            }

        except Exception as e:
            logger.error("風險平價投資組合評估失敗: %s", str(e))
            return {
                "cumulative_returns": 1.0,
                "annual_return": 0.0,
                "annual_volatility": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "risk_contribution": {},
            }

    def _calculate_risk_contribution(self, weights: Dict[str, float], returns: pd.Series) -> Dict[str, float]:
        """計算風險貢獻

        Args:
            weights: 投資組合權重
            returns: 收益率資料

        Returns:
            各資產的風險貢獻
        """
        try:
            if isinstance(weights, dict):
                # 如果weights是字典，轉換為Series
                weight_series = pd.Series(weights)
            else:
                # 假設weights是DataFrame，取最新的權重
                weight_series = weights.groupby(level="stock_id")["weight"].last()

            # 計算協方差矩陣
            symbols = list(weight_series.index)
            symbol_returns = returns.unstack(level="stock_id")[symbols].dropna()

            if symbol_returns.empty:
                return {symbol: 0.0 for symbol in symbols}

            cov_matrix = symbol_returns.cov()

            # 計算投資組合方差
            portfolio_variance = np.dot(weight_series.values, np.dot(cov_matrix.values, weight_series.values))

            # 計算風險貢獻
            risk_contributions = {}
            for symbol in symbols:
                if symbol in weight_series.index and symbol in cov_matrix.index:
                    marginal_contrib = np.dot(cov_matrix.loc[symbol].values, weight_series.values)
                    risk_contrib = weight_series[symbol] * marginal_contrib / portfolio_variance
                    risk_contributions[symbol] = risk_contrib
                else:
                    risk_contributions[symbol] = 0.0

            return risk_contributions

        except Exception as e:
            logger.error("風險貢獻計算失敗: %s", str(e))
            if isinstance(weights, dict):
                return {symbol: 0.0 for symbol in weights.keys()}
            else:
                return {}

    def rebalance(self, weights: Dict[str, float], price_df: pd.DataFrame, frequency: str = "M") -> Dict[str, float]:
        """再平衡風險平價投資組合

        Args:
            weights: 當前投資組合權重
            price_df: 價格資料
            frequency: 再平衡頻率

        Returns:
            再平衡後的投資組合權重
        """
        try:
            # 獲取股票列表
            symbols = list(weights.keys())

            # 計算歷史收益率
            historical_returns = price_df.loc[symbols, "收盤價"].pct_change().dropna()

            if len(historical_returns) < 30:  # 資料不足
                logger.warning("歷史資料不足，使用等權重")
                equal_weight = 1.0 / len(symbols)
                return {symbol: equal_weight for symbol in symbols}

            # 計算協方差矩陣
            cov_matrix = historical_returns.cov() * 252  # 年化

            # 重新最佳化風險平價權重
            optimized_weights = self._optimize_weights(cov_matrix)

            # 轉換為字典格式
            return dict(zip(symbols, optimized_weights))

        except Exception as e:
            logger.error("風險平價再平衡失敗: %s", str(e))
            # 返回等權重作為備選方案
            equal_weight = 1.0 / len(weights)
            return {symbol: equal_weight for symbol in weights.keys()}


class MaxSharpePortfolio(Portfolio):
    """最大夏普比率投資組合"""

    def __init__(self, risk_free_rate=0.0):
        """
        初始化最大夏普比率投資組合

        Args:
            risk_free_rate (float): 無風險利率，預設為 0
        """
        super().__init__(name="MaxSharpe")
        self.risk_free_rate = risk_free_rate

    def optimize(self, signals, price_df=None):
        """
        最佳化最大夏普比率投資組合

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

        # 對每個日期，計算最大夏普比率權重
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
                expected_returns = (
                    historical_returns.groupby(level="stock_id").mean() * 252
                )  # 年化
                cov_matrix = (
                    historical_returns.groupby(level="stock_id").cov() * 252  # 年化
                ).unstack()

                # 最佳化最大夏普比率權重
                try:
                    weights_opt = self._optimize_weights(expected_returns, cov_matrix)
                    date_weights = pd.DataFrame(
                        weights_opt, index=stocks, columns=["weight"]
                    )
                except BaseException as e:
                    print(f"最大夏普比率最佳化失敗: {e}")
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
        最佳化最大夏普比率權重

        Args:
            expected_returns (pandas.Series): 預期收益率
            cov_matrix (pandas.DataFrame): 協方差矩陣

        Returns:
            numpy.ndarray: 最佳化權重
        """
        n = len(expected_returns)

        # 定義目標函數 (負的夏普比率，因為我們要最大化)
        def objective(weights):
            """
            計算負的夏普比率

            Args:
                weights: 投資組合權重
            """
            portfolio_return = np.sum(expected_returns * weights)
            portfolio_volatility = np.sqrt(
                np.dot(weights.T, np.dot(cov_matrix, weights))
            )

            # 避免除以零
            if portfolio_volatility == 0:
                return -999999  # 一個非常小的數，表示這不是一個好的解

            sharpe_ratio = (
                portfolio_return - self.risk_free_rate
            ) / portfolio_volatility
            return -sharpe_ratio  # 負號是因為我們要最大化夏普比率

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
        評估最大夏普比率投資組合表現

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
            (annual_return - self.risk_free_rate) / annual_volatility
            if annual_volatility != 0
            else 0
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

    def rebalance(self, weights: Dict[str, float], price_df: pd.DataFrame, frequency: str = "M") -> Dict[str, float]:
        """再平衡最大夏普比率投資組合

        Args:
            weights: 當前投資組合權重
            price_df: 價格資料
            frequency: 再平衡頻率

        Returns:
            再平衡後的投資組合權重
        """
        try:
            # 獲取股票列表
            symbols = list(weights.keys())

            # 計算歷史收益率
            historical_returns = price_df.loc[symbols, "收盤價"].pct_change().dropna()

            if len(historical_returns) < 30:  # 資料不足
                logger.warning("歷史資料不足，使用等權重")
                equal_weight = 1.0 / len(symbols)
                return {symbol: equal_weight for symbol in symbols}

            # 計算預期收益率和協方差矩陣
            expected_returns = historical_returns.mean() * 252  # 年化
            cov_matrix = historical_returns.cov() * 252  # 年化

            # 重新最佳化最大夏普比率權重
            optimized_weights = self._optimize_weights(expected_returns, cov_matrix)

            # 轉換為字典格式
            return dict(zip(symbols, optimized_weights))

        except Exception as e:
            logger.error("最大夏普比率再平衡失敗: %s", str(e))
            # 返回等權重作為備選方案
            equal_weight = 1.0 / len(weights)
            return {symbol: equal_weight for symbol in weights.keys()}


class MinVariancePortfolio(Portfolio):
    """最小方差投資組合"""

    def __init__(self):
        """初始化最小方差投資組合"""
        super().__init__(name="MinVariance")

    def optimize(self, signals, price_df=None):
        """
        最佳化最小方差投資組合

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

        # 對每個日期，計算最小方差權重
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
                    historical_returns.groupby(level="stock_id").cov() * 252  # 年化
                ).unstack()

                # 最佳化最小方差權重
                try:
                    weights_opt = self._optimize_weights(cov_matrix)
                    date_weights = pd.DataFrame(
                        weights_opt, index=stocks, columns=["weight"]
                    )
                except BaseException as e:
                    print(f"最小方差最佳化失敗: {e}")
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
        最佳化最小方差權重

        Args:
            cov_matrix (pandas.DataFrame): 協方差矩陣

        Returns:
            numpy.ndarray: 最佳化權重
        """
        n = cov_matrix.shape[0]

        # 定義目標函數 (投資組合方差)
        def objective(weights):
            """
            計算投資組合方差

            Args:
                weights: 投資組合權重
            """
            return np.dot(weights.T, np.dot(cov_matrix, weights))

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
        評估最小方差投資組合表現

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

    def rebalance(self, weights: Dict[str, float], price_df: pd.DataFrame, frequency: str = "M") -> Dict[str, float]:
        """再平衡最小方差投資組合

        Args:
            weights: 當前投資組合權重
            price_df: 價格資料
            frequency: 再平衡頻率

        Returns:
            再平衡後的投資組合權重
        """
        try:
            # 獲取股票列表
            symbols = list(weights.keys())

            # 計算歷史收益率
            historical_returns = price_df.loc[symbols, "收盤價"].pct_change().dropna()

            if len(historical_returns) < 30:  # 資料不足
                logger.warning("歷史資料不足，使用等權重")
                equal_weight = 1.0 / len(symbols)
                return {symbol: equal_weight for symbol in symbols}

            # 計算協方差矩陣
            cov_matrix = historical_returns.cov() * 252  # 年化

            # 重新最佳化最小方差權重
            optimized_weights = self._optimize_weights(cov_matrix)

            # 轉換為字典格式
            return dict(zip(symbols, optimized_weights))

        except Exception as e:
            logger.error("最小方差再平衡失敗: %s", str(e))
            # 返回等權重作為備選方案
            equal_weight = 1.0 / len(weights)
            return {symbol: equal_weight for symbol in weights.keys()}


def optimize(signals, portfolio_type="equal_weight", **portfolio_params):
    """
    最佳化投資組合的主函數

    Args:
        signals (pandas.DataFrame): 交易訊號
        portfolio_type (str): 投資組合類型，可選 'equal_weight', 'mean_variance', 'risk_parity', 'max_sharpe', 'min_variance'
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
    elif portfolio_type == "max_sharpe":
        risk_free_rate = portfolio_params.get("risk_free_rate", 0.0)
        portfolio = MaxSharpePortfolio(risk_free_rate=risk_free_rate)
    elif portfolio_type == "min_variance":
        portfolio = MinVariancePortfolio()
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


def simulate_portfolios(
    signals: pd.DataFrame,
    prices: pd.DataFrame,
    portfolio_types: list = [
        "equal_weight",
        "mean_variance",
        "risk_parity",
        "max_sharpe",
        "min_variance",
    ],
    initial_capital: float = 1000000,
    start_date=None,
    end_date=None,
    rebalance_freq: str = "M",
    show_plot: bool = True,
) -> dict:
    """
    模擬並比較不同投資組合策略的表現

    Args:
        signals (pandas.DataFrame): 交易訊號，包含 signal 或 buy_signal 欄位
        prices (pandas.DataFrame): 價格資料，索引為 (股票代號, 日期)，包含 'close' 或 '收盤價' 欄位
        portfolio_types (list): 要比較的投資組合類型列表
        initial_capital (float): 初始資金
        start_date: 開始日期
        end_date: 結束日期
        rebalance_freq (str): 再平衡頻率，可選 'D', 'W', 'M', 'Q', 'Y'
        show_plot (bool): 是否繪製比較圖表

    Returns:
        dict: 各投資組合的模擬結果
    """
    # 篩選日期範圍
    if start_date is not None:
        prices = prices[prices.index.get_level_values("date") >= start_date]
        signals = signals[signals.index.get_level_values("date") >= start_date]
    if end_date is not None:
        prices = prices[prices.index.get_level_values("date") <= end_date]
        signals = signals[signals.index.get_level_values("date") <= end_date]

    # 模擬各投資組合
    results = {}
    for portfolio_type in portfolio_types:
        # 創建投資組合
        if portfolio_type == "equal_weight":
            portfolio = EqualWeightPortfolio(initial_capital=initial_capital)
        elif portfolio_type == "mean_variance":
            portfolio = MeanVariancePortfolio(initial_capital=initial_capital)
        elif portfolio_type == "risk_parity":
            portfolio = RiskParityPortfolio(initial_capital=initial_capital)
        elif portfolio_type == "max_sharpe":
            portfolio = MaxSharpePortfolio(initial_capital=initial_capital)
        elif portfolio_type == "min_variance":
            portfolio = MinVariancePortfolio(initial_capital=initial_capital)
        else:
            raise ValueError(f"不支援的投資組合類型: {portfolio_type}")

        # 模擬投資組合
        result = portfolio.simulate(
            signals, prices, start_date, end_date, rebalance_freq
        )
        results[portfolio_type] = result

    # 比較各投資組合的表現
    if show_plot:
        compare_portfolio_performance(results)

    return results


def compare_portfolio_performance(results: dict):
    """
    比較不同投資組合的表現

    Args:
        results (dict): 各投資組合的模擬結果
    """
    # 提取各投資組合的權益曲線
    equity_curves = {}
    for portfolio_type, result in results.items():
        equity_curve = pd.Series(
            [state["total_value"] for state in result["history"]],
            index=[state["date"] for state in result["history"]],
        )
        equity_curves[portfolio_type] = equity_curve

    # 繪製權益曲線比較圖
    plt.figure(figsize=(12, 8))

    # 繪製累積收益率
    plt.subplot(2, 1, 1)
    for portfolio_type, equity_curve in equity_curves.items():
        normalized_curve = equity_curve / equity_curve.iloc[0]
        plt.plot(normalized_curve.index, normalized_curve, label=portfolio_type)

    plt.title("投資組合累積收益率比較")
    plt.xlabel("日期")
    plt.ylabel("累積收益率")
    plt.legend()
    plt.grid(True)

    # 繪製績效指標比較
    plt.subplot(2, 1, 2)

    # 提取各投資組合的績效指標
    performance_data = {
        "年化收益率 (%)": [
            result["performance"]["annual_return"] for result in results.values()
        ],
        "年化波動率 (%)": [
            result["performance"]["annual_volatility"] for result in results.values()
        ],
        "夏普比率": [
            result["performance"]["sharpe_ratio"] for result in results.values()
        ],
        "最大回撤 (%)": [
            result["performance"]["max_drawdown"] for result in results.values()
        ],
        "勝率 (%)": [result["performance"]["win_rate"] for result in results.values()],
    }

    # 創建績效指標比較表
    performance_df = pd.DataFrame(performance_data, index=results.keys())

    # 繪製柱狀圖
    ax = plt.gca()
    performance_df.plot(kind="bar", ax=ax)

    plt.title("投資組合績效指標比較")
    plt.xlabel("投資組合類型")
    plt.ylabel("績效指標值")
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()


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
