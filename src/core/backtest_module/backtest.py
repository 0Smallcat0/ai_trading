"""回測模組

此模組提供回測功能，用於評估交易策略的表現。
"""

import warnings

import matplotlib.pyplot as plt
import pandas as pd

from src.core.data_ingest import load_data
from .utils import detect_close_col, ensure_multiindex

__all__ = ["Backtest"]

# 忽略 FutureWarning
warnings.simplefilter(action="ignore", category=FutureWarning)


class Backtest:
    """回測類，用於回測交易策略

    主要功能：
    - 策略執行迴圈（包含資金/部位追蹤）
    - 輸出策略績效指標（報酬率、夏普比率、最大回撤）
    - 支援多策略切換與比較
    """

    def __init__(
        self,
        start_date=None,
        end_date=None,
        initial_capital=1000000,
        transaction_cost=0.001425,
        slippage=0.001,
        tax=0.003,
    ):
        """初始化回測環境

        Args:
            start_date (datetime.date, optional): 回測開始日期
            end_date (datetime.date, optional): 回測結束日期
            initial_capital (float): 初始資金
            transaction_cost (float): 交易成本，預設為 0.001425 (0.1425%)
            slippage (float): 滑價，預設為 0.001 (0.1%)
            tax (float): 交易稅，預設為 0.003 (0.3%)
        """
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.transaction_cost = transaction_cost
        self.slippage = slippage
        self.tax = tax

        # 載入資料
        self.data_dict = load_data(start_date, end_date)
        if "price" not in self.data_dict:
            raise ValueError(
                "缺少價格資料，請先執行 data_ingest.update_data() 下載資料。"
            )
        self.price_df = ensure_multiindex(self.data_dict["price"])
        self.close_col = detect_close_col(self.price_df)

        self.results = None
        self.transactions = None

    def run(self, signals, weights=None):
        """執行回測

        Args:
            signals (pd.DataFrame): 交易信號，MultiIndex (stock_id, date)
                                   包含 'signal' 或 'buy_signal'/'sell_signal' 欄位
            weights (pd.DataFrame, optional): 權重，MultiIndex (stock_id, date)
                                            包含 'weight' 欄位

        Returns:
            dict: 回測結果，包含以下鍵值：
                - 'equity_curve': 權益曲線
                - 'returns': 每日收益率
                - 'positions': 最終持倉
                - 'transactions': 交易記錄
                - 'metrics': 績效指標
        """
        price_df = self.price_df

        signals = ensure_multiindex(signals)
        if weights is not None:
            weights = ensure_multiindex(weights)

        # 如果沒有提供權重，則使用等權重
        if weights is None:
            if "buy_signal" in signals.columns:
                buy_signals = signals[signals["buy_signal"] == 1]
            else:
                buy_signals = signals[signals["signal"] > 0]
            grouped = buy_signals.groupby(level="date")
            weights = pd.DataFrame()
            for date, group in grouped:
                stocks = group.index.get_level_values("stock_id").unique()
                weight = 1.0 / len(stocks) if len(stocks) > 0 else 0.0
                date_weights = pd.DataFrame(weight, index=stocks, columns=["weight"])
                date_weights["date"] = date
                date_weights.set_index("date", append=True, inplace=True)
                date_weights = date_weights.reorder_levels(["stock_id", "date"])
                weights = pd.concat([weights, date_weights])

        # 初始化投資組合
        portfolio = {
            "cash": self.initial_capital,
            "positions": {},
            "total_value": self.initial_capital,
            "history": [],
        }
        transactions = []
        trading_days = sorted(price_df.index.get_level_values("date").unique())

        # 執行回測迴圈
        for day in trading_days:
            # 獲取當日價格、信號和權重
            day_prices = price_df.xs(day, level="date", drop_level=False)
            day_signals = (
                signals.xs(day, level="date", drop_level=False)
                if day in signals.index.get_level_values("date")
                else pd.DataFrame()
            )
            day_weights = (
                weights.xs(day, level="date", drop_level=False)
                if day in weights.index.get_level_values("date")
                else pd.DataFrame()
            )

            # 處理當日交易
            self._process_day_trading(
                day, day_prices, day_signals, day_weights, portfolio, transactions
            )

            # 更新投資組合價值
            self._update_portfolio_value(day, day_prices, portfolio)

        # 計算績效指標
        self.results = self._calculate_performance_metrics(portfolio)
        self.transactions = transactions

        return self.results

    def _process_day_trading(
        self, day, day_prices, day_signals, day_weights, portfolio, transactions
    ):
        """
        處理當日交易

        Args:
            day (datetime.date): 交易日期
            day_prices (pd.DataFrame): 當日價格
            day_signals (pd.DataFrame): 當日信號
            day_weights (pd.DataFrame): 當日權重
            portfolio (dict): 投資組合
            transactions (list): 交易記錄
        """
        # 處理賣出信號
        self._process_sell_signals(
            day, day_prices, day_signals, portfolio, transactions
        )

        # 處理買入信號
        self._process_buy_signals(
            day, day_prices, day_signals, day_weights, portfolio, transactions
        )

    def _process_sell_signals(
        self, day, day_prices, day_signals, portfolio, transactions
    ):
        """
        處理賣出信號

        Args:
            day (datetime.date): 交易日期
            day_prices (pd.DataFrame): 當日價格
            day_signals (pd.DataFrame): 當日信號
            portfolio (dict): 投資組合
            transactions (list): 交易記錄
        """
        close_col = self.close_col

        # 處理賣出信號
        stocks_to_sell = []

        # 如果有 sell_signal 欄位，使用它
        if "sell_signal" in day_signals.columns:
            sell_signals = day_signals[day_signals["sell_signal"] == 1]
            stocks_to_sell.extend(
                sell_signals.index.get_level_values("stock_id").tolist()
            )

        # 如果有 signal 欄位，使用它（負值表示賣出）
        if "signal" in day_signals.columns:
            sell_signals = day_signals[day_signals["signal"] < 0]
            stocks_to_sell.extend(
                sell_signals.index.get_level_values("stock_id").tolist()
            )

        # 賣出持倉中的股票
        for stock_id in list(portfolio["positions"].keys()):
            if (stock_id in stocks_to_sell
                    or stock_id not in day_prices.index.get_level_values("stock_id")):
                if stock_id in day_prices.index.get_level_values("stock_id"):
                    # 獲取當日收盤價
                    price = day_prices.loc[(stock_id, day), close_col]

                    # 考慮滑價
                    sell_price = price * (1 - self.slippage)

                    # 計算賣出金額和手續費
                    position = portfolio["positions"][stock_id]
                    sell_amount = position["shares"] * sell_price
                    fee = sell_amount * self.transaction_cost
                    tax = sell_amount * self.tax

                    # 更新現金
                    portfolio["cash"] += sell_amount - fee - tax

                    # 記錄交易
                    transactions.append(
                        {
                            "date": day,
                            "stock_id": stock_id,
                            "action": "sell",
                            "price": sell_price,
                            "shares": position["shares"],
                            "amount": sell_amount,
                            "fee": fee,
                            "tax": tax,
                            "cash_after": portfolio["cash"],
                        }
                    )

                # 移除持倉
                del portfolio["positions"][stock_id]

    def _process_buy_signals(
        self, day, day_prices, day_signals, day_weights, portfolio, transactions
    ):
        """
        處理買入信號

        Args:
            day (datetime.date): 交易日期
            day_prices (pd.DataFrame): 當日價格
            day_signals (pd.DataFrame): 當日信號
            day_weights (pd.DataFrame): 當日權重
            portfolio (dict): 投資組合
            transactions (list): 交易記錄
        """
        close_col = self.close_col

        # 處理買入信號
        stocks_to_buy = []

        # 如果有 buy_signal 欄位，使用它
        if "buy_signal" in day_signals.columns:
            buy_signals = day_signals[day_signals["buy_signal"] == 1]
            stocks_to_buy.extend(
                buy_signals.index.get_level_values("stock_id").tolist()
            )

        # 如果有 signal 欄位，使用它（正值表示買入）
        if "signal" in day_signals.columns:
            buy_signals = day_signals[day_signals["signal"] > 0]
            stocks_to_buy.extend(
                buy_signals.index.get_level_values("stock_id").tolist()
            )

        # 如果沒有買入信號，直接返回
        if not stocks_to_buy:
            return

        # 獲取當日權重
        stock_weights = {}
        for stock_id in stocks_to_buy:
            if stock_id in day_weights.index.get_level_values("stock_id"):
                stock_weights[stock_id] = day_weights.loc[(stock_id, day), "weight"]
            else:
                stock_weights[stock_id] = 1.0 / len(stocks_to_buy)

        # 正規化權重
        total_weight = sum(stock_weights.values())
        if total_weight > 0:
            for stock_id in stock_weights:
                stock_weights[stock_id] /= total_weight

        # 計算可用資金
        available_cash = portfolio["cash"]

        # 買入股票
        for stock_id in stocks_to_buy:
            if stock_id in day_prices.index.get_level_values("stock_id"):
                # 獲取當日收盤價
                price = day_prices.loc[(stock_id, day), close_col]

                # 考慮滑價
                buy_price = price * (1 + self.slippage)

                # 計算買入金額
                weight = stock_weights.get(stock_id, 0)
                buy_amount = available_cash * weight

                # 計算可買入股數
                fee = buy_amount * self.transaction_cost
                shares = int((buy_amount - fee) / buy_price)

                # 如果可買入股數大於 0，執行買入
                if shares > 0:
                    actual_buy_amount = shares * buy_price
                    actual_fee = actual_buy_amount * self.transaction_cost

                    # 更新現金
                    portfolio["cash"] -= actual_buy_amount + actual_fee

                    # 更新持倉
                    portfolio["positions"][stock_id] = {
                        "shares": shares,
                        "cost": buy_price,
                        "date": day,
                    }

                    # 記錄交易
                    transactions.append(
                        {
                            "date": day,
                            "stock_id": stock_id,
                            "action": "buy",
                            "price": buy_price,
                            "shares": shares,
                            "amount": actual_buy_amount,
                            "fee": actual_fee,
                            "tax": 0,
                            "cash_after": portfolio["cash"],
                        }
                    )

    def _update_portfolio_value(self, day, day_prices, portfolio):
        """
        更新投資組合價值

        Args:
            day (datetime.date): 交易日期
            day_prices (pd.DataFrame): 當日價格
            portfolio (dict): 投資組合
        """
        close_col = self.close_col

        # 計算持倉價值
        positions_value = 0
        for stock_id, position in portfolio["positions"].items():
            if stock_id in day_prices.index.get_level_values("stock_id"):
                price = day_prices.loc[(stock_id, day), close_col]
                position_value = position["shares"] * price
                positions_value += position_value

        # 更新投資組合總價值
        portfolio["total_value"] = portfolio["cash"] + positions_value

        # 記錄歷史
        portfolio["history"].append(
            {
                "date": day,
                "cash": portfolio["cash"],
                "positions_value": positions_value,
                "total_value": portfolio["total_value"],
            }
        )

    def _calculate_performance_metrics(self, portfolio):
        """
        計算績效指標

        Args:
            portfolio (dict): 投資組合

        Returns:
            dict: 績效指標
        """
        from .utils import calculate_sharpe, calculate_max_drawdown

        # 建立權益曲線
        history_df = pd.DataFrame(portfolio["history"])
        history_df.set_index("date", inplace=True)
        equity_curve = history_df["total_value"]

        # 計算收益率
        returns = equity_curve.pct_change().dropna()

        # 計算年化收益率
        if len(returns) > 0:
            annual_return = returns.mean() * 252
        else:
            annual_return = 0

        # 計算夏普比率
        sharpe = calculate_sharpe(equity_curve)

        # 計算最大回撤
        max_drawdown = calculate_max_drawdown(equity_curve)

        # 計算勝率
        if self.transactions:
            transactions_df = pd.DataFrame(self.transactions)
            buy_transactions = transactions_df[transactions_df["action"] == "buy"]
            sell_transactions = transactions_df[transactions_df["action"] == "sell"]

            # 計算每筆交易的盈虧
            trades = []
            for buy in buy_transactions.itertuples():
                sell_records = sell_transactions[
                    sell_transactions["stock_id"] == buy.stock_id
                ]
                if not sell_records.empty:
                    sell = sell_records.iloc[0]
                    profit = ((sell["price"] - buy.price) * buy.shares
                              - buy.fee - sell["fee"] - sell["tax"])
                    trades.append(
                        {
                            "stock_id": buy.stock_id,
                            "buy_date": buy.date,
                            "sell_date": sell["date"],
                            "buy_price": buy.price,
                            "sell_price": sell["price"],
                            "shares": buy.shares,
                            "profit": profit,
                            "return": profit / (buy.price * buy.shares),
                        }
                    )

            trades_df = pd.DataFrame(trades)
            if not trades_df.empty:
                win_rate = (trades_df["profit"] > 0).mean()
                profit_loss_ratio = (abs(trades_df[trades_df["profit"] > 0]["profit"].mean())
                                      / abs(trades_df[trades_df["profit"] < 0]["profit"].mean())
                                      if (trades_df["profit"] < 0).any()
                                      else float("inf"))
            else:
                win_rate = 0
                profit_loss_ratio = 0
        else:
            win_rate = 0
            profit_loss_ratio = 0
            trades_df = pd.DataFrame()

        # 返回結果
        return {
            "equity_curve": equity_curve,
            "returns": returns,
            "positions": portfolio["positions"],
            "transactions": self.transactions,
            "metrics": {
                "initial_capital": self.initial_capital,
                "final_value": portfolio["total_value"],
                "total_return": (portfolio["total_value"] / self.initial_capital) - 1,
                "annual_return": annual_return,
                "sharpe_ratio": sharpe,
                "max_drawdown": max_drawdown,
                "win_rate": win_rate,
                "profit_loss_ratio": profit_loss_ratio,
            },
            "trades": trades_df,
        }

    def plot_equity_curve(self):
        """
        繪製權益曲線

        Returns:
            matplotlib.figure.Figure: 圖表
        """
        if self.results is None:
            raise ValueError("請先執行回測")

        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(self.results["equity_curve"])
        ax.set_title("權益曲線")
        ax.set_xlabel("日期")
        ax.set_ylabel("價值")
        ax.grid(True)

        return fig

    def plot_returns_distribution(self):
        """
        繪製收益率分佈

        Returns:
            matplotlib.figure.Figure: 圖表
        """
        if self.results is None:
            raise ValueError("請先執行回測")

        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(12, 6))
        self.results["returns"].hist(ax=ax, bins=50)
        ax.set_title("收益率分佈")
        ax.set_xlabel("收益率")
        ax.set_ylabel("頻率")
        ax.grid(True)

        return fig

    def plot_drawdown(self):
        """
        繪製回撤圖

        Returns:
            matplotlib.figure.Figure: 圖表
        """
        if self.results is None:
            raise ValueError("請先執行回測")

        equity_curve = self.results["equity_curve"]
        running_max = equity_curve.cummax()
        drawdown = equity_curve / running_max - 1

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.fill_between(drawdown.index, drawdown.values, 0, color="red", alpha=0.3)
        ax.plot(drawdown, color="red", alpha=0.5)
        ax.set_title("回撤")
        ax.set_xlabel("日期")
        ax.set_ylabel("回撤")
        ax.grid(True)

        return fig
