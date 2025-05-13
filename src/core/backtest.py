"""
回測與模擬交易模組

此模組負責對交易策略進行回測，評估策略的表現，
並提供模擬交易的功能，以便在實際交易前測試策略的有效性。
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import warnings
import os
import backtrader as bt
from src.core.data_ingest import load_data
from src.utils.utils import align_timeseries
from src.data_sources.twse_crawler import twse_crawler


def _detect_close_col(df):
    """自動偵測收盤價欄位名稱"""
    for col in ["收盤價", "close", "Close"]:
        if col in df.columns:
            return col
    raise ValueError("價格資料必須包含 '收盤價' 或 'close' 欄位")


def _ensure_multiindex(df):
    """確保 index 為 (stock_id, date) MultiIndex"""
    if isinstance(df.index, pd.MultiIndex):
        return df
    elif "stock_id" in df.columns and "date" in df.columns:
        return df.set_index(["stock_id", "date"])
    else:
        raise ValueError("資料必須有 MultiIndex 或包含 'stock_id' 和 'date' 欄位")


def calculate_sharpe(equity_curve, risk_free_rate=0.0, periods_per_year=252):
    returns = equity_curve.pct_change().dropna()
    annual_return = returns.mean() * periods_per_year
    annual_volatility = returns.std() * np.sqrt(periods_per_year)
    sharpe = (
        (annual_return - risk_free_rate) / annual_volatility
        if annual_volatility != 0
        else 0
    )
    return sharpe


def calculate_max_drawdown(equity_curve):
    running_max = equity_curve.cummax()
    drawdown = equity_curve / running_max - 1
    max_drawdown = drawdown.min()
    return max_drawdown


warnings.simplefilter(action="ignore", category=FutureWarning)


class Backtest:
    """回測類，用於回測交易策略"""

    def __init__(
        self,
        start_date=None,
        end_date=None,
        initial_capital=1000000,
        transaction_cost=0.001425,
        slippage=0.001,
        tax=0.003,
    ):
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
        self.price_df = _ensure_multiindex(self.data_dict["price"])
        self.close_col = _detect_close_col(self.price_df)

        self.results = None
        self.transactions = None

    def run(self, signals, weights=None):
        price_df = self.price_df
        close_col = self.close_col

        signals = _ensure_multiindex(signals)
        if weights is not None:
            weights = _ensure_multiindex(weights)

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

        for day in trading_days:
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

            # 更新持倉價值
            for stock_id, position in list(portfolio["positions"].items()):
                if (stock_id, day) in day_prices.index:
                    price = day_prices.loc[(stock_id, day), close_col]
                    portfolio["positions"][stock_id]["value"] = (
                        position["shares"] * price
                    )

            portfolio["total_value"] = portfolio["cash"] + sum(
                position["value"] for position in portfolio["positions"].values()
            )
            portfolio["history"].append(
                {
                    "date": day,
                    "cash": portfolio["cash"],
                    "positions": {
                        stock_id: position.copy()
                        for stock_id, position in portfolio["positions"].items()
                    },
                    "total_value": portfolio["total_value"],
                }
            )

            # 處理賣出訊號
            if not day_signals.empty and "sell_signal" in day_signals.columns:
                sell_signals = day_signals[day_signals["sell_signal"] == 1]
                for (stock_id, _), _ in sell_signals.iterrows():
                    if stock_id in portfolio["positions"]:
                        if (stock_id, day) in day_prices.index:
                            price = day_prices.loc[(stock_id, day), close_col]
                            sell_price = price * (1 - self.slippage)
                            shares = portfolio["positions"][stock_id]["shares"]
                            sell_amount = shares * sell_price
                            transaction_cost = sell_amount * self.transaction_cost
                            tax = sell_amount * self.tax
                            portfolio["cash"] += sell_amount - transaction_cost - tax
                            transactions.append(
                                {
                                    "date": day,
                                    "stock_id": stock_id,
                                    "action": "sell",
                                    "shares": shares,
                                    "price": sell_price,
                                    "amount": sell_amount,
                                    "transaction_cost": transaction_cost,
                                    "tax": tax,
                                }
                            )
                            del portfolio["positions"][stock_id]

            # 處理買入訊號
            if not day_weights.empty:
                portfolio_value = portfolio["cash"] + sum(
                    position["value"] for position in portfolio["positions"].values()
                )
                for (stock_id, _), row in day_weights.iterrows():
                    if (stock_id, day) in day_prices.index:
                        price = day_prices.loc[(stock_id, day), close_col]
                        buy_price = price * (1 + self.slippage)
                        weight = row["weight"]
                        allocated_amount = portfolio_value * weight
                        if stock_id in portfolio["positions"]:
                            current_value = portfolio["positions"][stock_id]["value"]
                            adjust_amount = allocated_amount - current_value
                            if adjust_amount > 0:
                                if portfolio["cash"] >= adjust_amount:
                                    additional_shares = adjust_amount / buy_price
                                    transaction_cost = (
                                        adjust_amount * self.transaction_cost
                                    )
                                    portfolio["positions"][stock_id][
                                        "shares"
                                    ] += additional_shares
                                    portfolio["positions"][stock_id][
                                        "value"
                                    ] += adjust_amount
                                    portfolio["cash"] -= (
                                        adjust_amount + transaction_cost
                                    )
                                    transactions.append(
                                        {
                                            "date": day,
                                            "stock_id": stock_id,
                                            "action": "buy",
                                            "shares": additional_shares,
                                            "price": buy_price,
                                            "amount": adjust_amount,
                                            "transaction_cost": transaction_cost,
                                            "tax": 0,
                                        }
                                    )
                            elif adjust_amount < 0:
                                reduce_amount = -adjust_amount
                                reduce_shares = reduce_amount / price
                                transaction_cost = reduce_amount * self.transaction_cost
                                tax = reduce_amount * self.tax
                                portfolio["positions"][stock_id][
                                    "shares"
                                ] -= reduce_shares
                                portfolio["positions"][stock_id][
                                    "value"
                                ] -= reduce_amount
                                portfolio["cash"] += (
                                    reduce_amount - transaction_cost - tax
                                )
                                transactions.append(
                                    {
                                        "date": day,
                                        "stock_id": stock_id,
                                        "action": "sell",
                                        "shares": reduce_shares,
                                        "price": price,
                                        "amount": reduce_amount,
                                        "transaction_cost": transaction_cost,
                                        "tax": tax,
                                    }
                                )
                        else:
                            if portfolio["cash"] >= allocated_amount:
                                shares = allocated_amount / buy_price
                                transaction_cost = (
                                    allocated_amount * self.transaction_cost
                                )
                                portfolio["positions"][stock_id] = {
                                    "shares": shares,
                                    "value": allocated_amount,
                                }
                                portfolio["cash"] -= allocated_amount + transaction_cost
                                transactions.append(
                                    {
                                        "date": day,
                                        "stock_id": stock_id,
                                        "action": "buy",
                                        "shares": shares,
                                        "price": buy_price,
                                        "amount": allocated_amount,
                                        "transaction_cost": transaction_cost,
                                        "tax": 0,
                                    }
                                )

        self.results = self._calculate_results(portfolio)
        self.transactions = pd.DataFrame(transactions)
        return self.results

    def _calculate_results(self, portfolio):
        daily_values = pd.Series(
            {
                history["date"]: history["total_value"]
                for history in portfolio["history"]
            }
        )
        daily_returns = daily_values.pct_change().fillna(0)
        cumulative_returns = (1 + daily_returns).cumprod()
        annual_return = daily_returns.mean() * 252
        annual_volatility = daily_returns.std() * np.sqrt(252)
        risk_free_rate = 0.0
        sharpe_ratio = (
            (annual_return - risk_free_rate) / annual_volatility
            if annual_volatility != 0
            else 0
        )
        max_drawdown = (daily_values / daily_values.cummax() - 1).min()
        win_rate = (daily_returns > 0).sum() / len(daily_returns)
        profit_loss_ratio = (
            daily_returns[daily_returns > 0].mean()
            / abs(daily_returns[daily_returns < 0].mean())
            if len(daily_returns[daily_returns < 0]) > 0
            else float("inf")
        )
        final_equity = daily_values.iloc[-1]
        total_return = (final_equity / self.initial_capital - 1) * 100
        return {
            "daily_values": daily_values,
            "daily_returns": daily_returns,
            "cumulative_returns": cumulative_returns,
            "annual_return": annual_return,
            "annual_volatility": annual_volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "profit_loss_ratio": profit_loss_ratio,
            "final_equity": final_equity,
            "total_return": total_return,
        }

    def plot_results(self):
        if self.results is None:
            raise ValueError("必須先執行回測")
        fig, axes = plt.subplots(3, 1, figsize=(12, 15))
        axes[0].plot(
            self.results["daily_values"].index, self.results["daily_values"].values
        )
        axes[0].set_title("投資組合價值")
        axes[0].set_xlabel("日期")
        axes[0].set_ylabel("價值")
        axes[0].grid(True)
        axes[1].plot(
            self.results["cumulative_returns"].index,
            self.results["cumulative_returns"].values,
        )
        axes[1].set_title("累積收益率")
        axes[1].set_xlabel("日期")
        axes[1].set_ylabel("累積收益率")
        axes[1].grid(True)
        drawdown = (
            self.results["daily_values"] / self.results["daily_values"].cummax() - 1
        ) * 100
        axes[2].fill_between(drawdown.index, drawdown.values, 0, color="red", alpha=0.3)
        axes[2].set_title("回撤 (%)")
        axes[2].set_xlabel("日期")
        axes[2].set_ylabel("回撤 (%)")
        axes[2].grid(True)
        plt.tight_layout()
        return fig

    def get_transactions(self):
        if self.transactions is None:
            raise ValueError("必須先執行回測")
        return self.transactions

    def get_performance_metrics(self):
        if self.results is None:
            raise ValueError("必須先執行回測")
        return {
            "annual_return": self.results["annual_return"],
            "annual_volatility": self.results["annual_volatility"],
            "sharpe_ratio": self.results["sharpe_ratio"],
            "max_drawdown": self.results["max_drawdown"],
            "win_rate": self.results["win_rate"],
            "profit_loss_ratio": self.results["profit_loss_ratio"],
            "final_equity": self.results["final_equity"],
            "total_return": self.results["total_return"],
        }


def backtest_strategy(
    signals,
    weights=None,
    start_date=None,
    end_date=None,
    initial_capital=1000000,
    transaction_cost=0.001425,
    slippage=0.001,
    tax=0.003,
):
    backtest = Backtest(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        transaction_cost=transaction_cost,
        slippage=slippage,
        tax=tax,
    )
    backtest.run(signals, weights)
    return backtest


def run_backtest(
    signals,
    weights=None,
    start_date=None,
    end_date=None,
    initial_capital=1000000,
    transaction_cost=0.001425,
    slippage=0.001,
    tax=0.003,
    commission_rate=None,
):
    if commission_rate is not None:
        transaction_cost = commission_rate
    data_dict = load_data(start_date, end_date)
    if "price" not in data_dict:
        raise ValueError("缺少價格資料，請先執行 data_ingest.update_data() 下載資料。")
    price_df = _ensure_multiindex(data_dict["price"])
    _detect_close_col(price_df)
    if signals is not None and not signals.empty:
        signals = align_timeseries(signals, start_date, end_date)
    if weights is not None and not weights.empty:
        weights = align_timeseries(weights, start_date, end_date)
    price_df = align_timeseries(price_df, start_date, end_date)
    backtest = Backtest(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        transaction_cost=transaction_cost,
        slippage=slippage,
        tax=tax,
    )
    results = backtest.run(signals, weights)
    daily_values = results["daily_values"]
    daily_returns = daily_values.pct_change().fillna(0)
    cumulative_returns = (1 + daily_returns).cumprod() - 1
    annual_return = daily_returns.mean() * 252
    sharpe = calculate_sharpe(daily_values)
    max_drawdown = calculate_max_drawdown(daily_values)
    results["equity_curve"] = daily_values
    results["daily_pnl"] = daily_returns * daily_values.shift(1)
    results["cumulative_returns"] = cumulative_returns
    results["annual_return"] = annual_return
    results["sharpe"] = sharpe
    results["max_drawdown"] = max_drawdown
    return results


class SignalStrategy(bt.Strategy):
    """Backtrader 策略類，用於實現基於訊號的交易策略"""

    params = (
        ("signals", None),  # 交易訊號
        ("weights", None),  # 投資組合權重
    )

    def __init__(self):
        self.signals = self.params.signals
        self.weights = self.params.weights
        self.order_dict = {}  # stock_id -> data feed
        # 建立 stock_id 與 data feed 的對應
        self.stockid_to_data = {}
        for data in self.datas:
            self.stockid_to_data[data._name] = data

    def next(self):
        current_date = self.datetime.date(0)
        # signals/weights 需為 MultiIndex (stock_id, date)
        if self.signals is not None:
            try:
                day_signals = self.signals.xs(current_date, level="date")
            except Exception:
                return
            # 處理賣出訊號
            if "sell_signal" in day_signals.columns:
                for stock_id, row in day_signals[
                    day_signals["sell_signal"] == 1
                ].iterrows():
                    if stock_id in self.stockid_to_data:
                        data_feed = self.stockid_to_data[stock_id]
                        position = self.getposition(data_feed)
                        if position.size > 0:
                            self.close(data_feed)
            # 處理買入訊號
            signal_col = (
                "buy_signal"
                if "buy_signal" in day_signals.columns
                else ("signal" if "signal" in day_signals.columns else None)
            )
            if signal_col:
                # 權重
                if self.weights is not None:
                    try:
                        day_weights = self.weights.xs(current_date, level="date")
                    except Exception:
                        day_weights = pd.Series(
                            (
                                1.0 / len(day_signals[day_signals[signal_col] > 0])
                                if len(day_signals[day_signals[signal_col] > 0]) > 0
                                else 0
                            ),
                            index=day_signals[day_signals[signal_col] > 0].index,
                        )
                else:
                    buy_stocks = day_signals[day_signals[signal_col] > 0].index
                    day_weights = pd.Series(
                        1.0 / len(buy_stocks) if len(buy_stocks) > 0 else 0,
                        index=buy_stocks,
                    )
                portfolio_value = self.broker.getvalue()
                for stock_id, weight in day_weights.items():
                    if weight > 0 and stock_id in self.stockid_to_data:
                        data_feed = self.stockid_to_data[stock_id]
                        price = data_feed.close[0]
                        shares = int(portfolio_value * weight / price)
                        position = self.getposition(data_feed)
                        if position.size > 0:
                            target_shares = shares
                            if target_shares > position.size:
                                self.buy(data_feed, size=target_shares - position.size)
                            elif target_shares < position.size:
                                self.sell(data_feed, size=position.size - target_shares)
                        else:
                            self.buy(data_feed, size=shares)


def run_with_backtrader(
    signals,
    weights=None,
    price_data=None,
    start_date=None,
    end_date=None,
    initial_capital=1000000,
    commission_rate=0.001,
    slippage=0.0005,
):
    """
    使用 Backtrader 框架執行回測

    Args:
        signals (pandas.DataFrame): 交易訊號，索引為日期，包含 'buy_signal' 或 'signal' 欄位
        weights (pandas.DataFrame, optional): 投資組合權重，索引為日期
        price_data (pandas.DataFrame, optional): 價格資料，如果為 None 則載入資料
        start_date (datetime.date, optional): 回測開始日期
        end_date (datetime.date, optional): 回測結束日期
        initial_capital (float): 初始資金
        commission_rate (float): 佣金費率
        slippage (float): 滑價率

    Returns:
        dict: 回測結果，包含年化報酬、夏普比率和最大回撤
    """
    # 載入資料
    if price_data is None:
        from .data_ingest import load_data

        price_data = load_data(start_date, end_date)["price"]

    # 避免 look-ahead bias，統一用 align_timeseries() 前處理
    if signals is not None and not signals.empty:
        from .utils import align_timeseries

        signals = align_timeseries(signals, start_date, end_date)
    if weights is not None and not weights.empty:
        from .utils import align_timeseries

        weights = align_timeseries(weights, start_date, end_date)
    from .utils import align_timeseries

    price_data = align_timeseries(price_data, start_date, end_date)

    # 創建 Backtrader 引擎
    cerebro = bt.Cerebro()
    # 添加資料
    for stock_id in price_data.index.get_level_values("stock_id").unique():
        stock_df = price_data.loc[stock_id]
        data = bt.feeds.PandasData(
            dataname=stock_df,
            datetime="date",
            open="open",
            high="high",
            low="low",
            close="close",
            volume="volume",
            openinterest=None,
        )
        cerebro.adddata(data, name=stock_id)
    cerebro.broker.setcash(initial_capital)
    cerebro.broker.setcommission(commission=commission_rate)
    cerebro.broker.set_slippage_perc(slippage)
    cerebro.addstrategy(SignalStrategy, signals=signals, weights=weights)
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
    results = cerebro.run()
    strategy = results[0]
    sharpe = strategy.analyzers.sharpe.get_analysis().get("sharperatio", None)
    max_drawdown = strategy.analyzers.drawdown.get_analysis()["max"]["drawdown"] / 100
    annual_return = strategy.analyzers.returns.get_analysis()["rnorm100"]
    portfolio_value = cerebro.broker.getvalue()
    return {
        "portfolio_value": portfolio_value,
        "annual_return": annual_return,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "strategy": strategy,
    }


class HybridBacktest(bt.Cerebro):
    """
    混合型回測引擎，繼承 Backtrader Cerebro，支援：
    - 新聞情感因子注入
    - 內建夏普率與最大回撤分析
    - 整合 TA-Lib 技術指標
    """

    def __init__(self, news_sentiment_df=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.news_sentiment_df = news_sentiment_df
        # 預設加上夏普率與最大回撤分析
        self.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
        self.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        self.addanalyzer(bt.analyzers.Returns, _name="returns")

    def run_hybrid(self, strategy_cls, *args, **kwargs):
        """
        執行混合型回測，strategy_cls 必須支援情感因子與 TA-Lib 指標
        """
        self.addstrategy(
            strategy_cls, news_sentiment_df=self.news_sentiment_df, *args, **kwargs
        )
        results = self.run()
        strat = results[0]
        sharpe = strat.analyzers.sharpe.get_analysis().get("sharperatio", None)
        max_drawdown = strat.analyzers.drawdown.get_analysis()["max"]["drawdown"] / 100
        annual_return = strat.analyzers.returns.get_analysis().get("rnorm100", None)
        return {
            "portfolio_value": self.broker.getvalue(),
            "annual_return": annual_return,
            "sharpe": sharpe,
            "max_drawdown": max_drawdown,
            "strategy": strat,
        }


class HybridStrategy(bt.Strategy):
    """
    範例混合策略模板：
    - 支援新聞情感因子注入
    - 內建 TA-Lib 技術指標
    - 可擴充自訂邏輯
    params:
        news_sentiment_df: pd.DataFrame, 索引為 (stock_id, date)，欄位含 'sentiment'
    """

    params = (("news_sentiment_df", None),)

    def __init__(self):
        self.news_sentiment_df = self.params.news_sentiment_df
        self.stockid_to_data = {data._name: data for data in self.datas}
        # 範例：為每檔股票加一個 RSI 指標
        import backtrader.talib as bttalib

        self.rsi_dict = {}
        for data in self.datas:
            self.rsi_dict[data._name] = bttalib.RSI(data, timeperiod=14)

    def next(self):
        current_date = self.datetime.date(0)
        for stock_id, data in self.stockid_to_data.items():
            # 取得 RSI 值
            rsi = self.rsi_dict[stock_id][0]
            # 取得新聞情感分數
            sentiment = 0
            if self.news_sentiment_df is not None:
                try:
                    sentiment = self.news_sentiment_df.loc[
                        (stock_id, current_date), "sentiment"
                    ]
                except Exception:
                    sentiment = 0
            # 範例邏輯：RSI < 30 且情感分數 > 0.2 則買進，RSI > 70 或情感 < -0.2 則賣出
            position = self.getposition(data)
            if rsi < 30 and sentiment > 0.2 and position.size == 0:
                self.buy(data=data)
            elif (rsi > 70 or sentiment < -0.2) and position.size > 0:
                self.close(data=data)


# region: 修正引用，允許直接執行
if __name__ == "__main__":
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
