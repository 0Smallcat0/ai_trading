"""投資組合基礎類別模組

此模組定義了投資組合的基礎抽象類別和相關的異常類別。
所有具體的投資組合策略都應該繼承 Portfolio 基類。

主要功能：
- 定義投資組合基礎介面
- 提供通用的投資組合操作方法
- 定義異常處理類別
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
import logging

import numpy as np
import pandas as pd

# 設定日誌
logger = logging.getLogger(__name__)


class PortfolioOptimizationError(Exception):
    """投資組合最佳化錯誤"""

    pass


class DependencyError(Exception):
    """依賴套件錯誤"""

    pass


class Portfolio(ABC):
    """投資組合基類，所有具體投資組合策略都應該繼承此類"""

    def __init__(
        self,
        name: str = "BasePortfolio",
        initial_capital: float = 1000000,
        transaction_cost: float = 0.001425,
        tax: float = 0.003,
        slippage: float = 0.001,
    ):
        """初始化投資組合

        Args:
            name: 投資組合名稱
            initial_capital: 初始資金
            transaction_cost: 交易成本比例
            tax: 交易稅比例
            slippage: 滑價比例
        """
        self.name = name
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.tax = tax
        self.slippage = slippage

        # 投資組合狀態
        self.cash = initial_capital
        # {stock_id: {'shares': 100, 'cost': 50.0, 'value': 5000.0}}
        self.positions = {}
        self.history = []  # 歷史狀態記錄
        self.transactions = []  # 交易記錄

    @abstractmethod
    def optimize(
        self, signals: pd.DataFrame, price_df: Optional[pd.DataFrame] = None
    ) -> Dict[str, float]:
        """最佳化投資組合

        Args:
            signals: 交易訊號
            price_df: 價格資料

        Returns:
            最佳化後的權重

        Raises:
            NotImplementedError: 子類必須實現此方法
        """
        raise NotImplementedError("子類必須實現 optimize 方法")

    @abstractmethod
    def evaluate(
        self, weights: Dict[str, float], price_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """評估投資組合表現

        Args:
            weights: 投資組合權重
            price_df: 價格資料

        Returns:
            評估結果

        Raises:
            NotImplementedError: 子類必須實現此方法
        """
        raise NotImplementedError("子類必須實現 evaluate 方法")

    @abstractmethod
    def rebalance(
        self, weights: Dict[str, float], price_df: pd.DataFrame, frequency: str = "M"
    ) -> Dict[str, float]:
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
        raise NotImplementedError("子類必須實現 rebalance 方法")

    def simulate(
        self,
        signals: pd.DataFrame,
        price_df: pd.DataFrame,
        start_date=None,
        end_date=None,
        rebalance_freq: str = "M",
    ) -> Dict[str, Any]:
        """模擬投資組合表現

        Args:
            signals: 交易訊號
            price_df: 價格資料
            start_date: 開始日期
            end_date: 結束日期
            rebalance_freq: 再平衡頻率，可選 'D', 'W', 'M', 'Q', 'Y'

        Returns:
            模擬結果，包含 'history', 'transactions', 'performance'
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
                    # 獲取到當前日期為止的價格資料
                    historical_prices = price_df[
                        price_df.index.get_level_values("date") <= day
                    ]
                    weights = self.optimize(day_signals, historical_prices)

                    # 執行再平衡
                    self._execute_rebalance(weights, day_prices, close_col)

        # 計算績效指標
        performance = self._calculate_performance()

        return {
            "history": self.history,
            "transactions": self.transactions,
            "performance": performance,
        }

    def _update_positions_value(self, day_prices: pd.DataFrame, close_col: str):
        """更新持倉價值

        Args:
            day_prices: 當日價格資料
            close_col: 收盤價欄位名稱
        """
        for stock_id, position in list(self.positions.items()):
            date = day_prices.index.get_level_values("date")[0]
            if (date, stock_id) in day_prices.index:
                price = day_prices.loc[(date, stock_id), close_col]
                self.positions[stock_id]["value"] = position["shares"] * price

    def _record_state(self, date):
        """記錄投資組合狀態

        Args:
            date: 日期
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

    def _execute_rebalance(
        self, weights: Dict[str, float], day_prices: pd.DataFrame, close_col: str
    ):
        """執行再平衡

        Args:
            weights: 投資組合權重
            day_prices: 當日價格資料
            close_col: 收盤價欄位名稱
        """
        # 計算總價值
        total_value = self.cash + sum(
            position["value"] for position in self.positions.values()
        )

        # 計算目標持倉
        target_positions = {}
        date = day_prices.index.get_level_values("date")[0]
        for stock_id, weight in weights.items():
            if (date, stock_id) in day_prices.index:
                price = day_prices.loc[(date, stock_id), close_col]
                target_value = total_value * weight
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

    def _buy_stock(
        self, stock_id: str, shares: float, day_prices: pd.DataFrame, close_col: str
    ):
        """買入股票

        Args:
            stock_id: 股票代號
            shares: 股數
            day_prices: 當日價格資料
            close_col: 收盤價欄位名稱
        """
        date = day_prices.index.get_level_values("date")[0]

        if (date, stock_id) in day_prices.index:
            price = day_prices.loc[(date, stock_id), close_col]
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

    def _sell_stock(
        self,
        stock_id: str,
        shares: Optional[float] = None,
        day_prices: Optional[pd.DataFrame] = None,
        close_col: Optional[str] = None,
    ):
        """賣出股票

        Args:
            stock_id: 股票代號
            shares: 股數，如果為 None 則賣出全部
            day_prices: 當日價格資料
            close_col: 收盤價欄位名稱
        """
        if stock_id in self.positions and day_prices is not None:
            date = day_prices.index.get_level_values("date")[0]

            if (date, stock_id) in day_prices.index:
                price = day_prices.loc[(date, stock_id), close_col]
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

    def _calculate_performance(self) -> Dict[str, Any]:
        """計算績效指標

        Returns:
            績效指標
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
        cumulative_returns = (1 + daily_returns).cumprod()

        # 計算年化收益率
        annual_return = daily_returns.mean() * 252

        # 計算年化波動率
        annual_volatility = daily_returns.std() * np.sqrt(252)

        # 計算夏普比率
        sharpe_ratio = annual_return / annual_volatility if annual_volatility else 0

        # 計算最大回撤
        max_drawdown = (equity_curve / equity_curve.cummax() - 1).min()

        # 計算勝率
        win_rate = 0.0
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

        return {
            "total_return": (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1),
            "annual_return": annual_return,
            "annual_volatility": annual_volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "total_trades": len(self.transactions),
            "equity_curve": equity_curve,
            "daily_returns": daily_returns,
            "cumulative_returns": cumulative_returns,
        }
