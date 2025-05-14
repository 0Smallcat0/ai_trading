"""
回測與模擬交易模組

此模組負責對交易策略進行回測，評估策略的表現，
並提供模擬交易的功能，以便在實際交易前測試策略的有效性。

主要功能：
- 策略執行迴圈（包含資金/部位追蹤）
- 資料模擬器與歷史資料讀取
- 輸出策略績效指標（報酬率、夏普比率、最大回撤）
- 支援多策略切換與比較
- 異常情境模擬（崩盤、流動性不足）
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import warnings
import os
import datetime
import random
import json
from typing import Dict, List, Union, Optional, Tuple, Any, Callable
from pathlib import Path
import backtrader as bt
from src.core.data_ingest import load_data
from src.utils.utils import align_timeseries, clean_data
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


class MarketDataSimulator:
    """
    市場數據模擬器，用於生成模擬數據和異常情境

    主要功能：
    - 生成正常市場數據
    - 模擬市場崩盤情境
    - 模擬流動性不足情境
    - 模擬高波動性情境
    """

    def __init__(self, base_data=None, seed=None):
        """
        初始化市場數據模擬器

        Args:
            base_data (pd.DataFrame, optional): 基礎數據，用於生成模擬數據
            seed (int, optional): 隨機種子，用於重現結果
        """
        self.base_data = base_data
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)

    def generate_normal_market(self, n_stocks=5, n_days=252, start_date=None):
        """
        生成正常市場數據

        Args:
            n_stocks (int): 股票數量
            n_days (int): 天數
            start_date (datetime.date, optional): 開始日期

        Returns:
            pd.DataFrame: 模擬的市場數據，MultiIndex (stock_id, date)
        """
        if start_date is None:
            start_date = datetime.date.today() - datetime.timedelta(days=n_days)

        # 生成日期範圍
        dates = [start_date + datetime.timedelta(days=i) for i in range(n_days)]

        # 生成股票代碼
        stock_ids = [f"SIM{i:04d}" for i in range(n_stocks)]

        # 生成價格數據
        data = []
        for stock_id in stock_ids:
            # 初始價格在 50-200 之間隨機
            price = random.uniform(50, 200)
            for date in dates:
                # 每日價格變動在 -2% 到 2% 之間
                daily_return = random.uniform(-0.02, 0.02)
                price *= (1 + daily_return)

                # 生成開高低收量
                open_price = price * random.uniform(0.99, 1.01)
                high_price = price * random.uniform(1.0, 1.03)
                low_price = price * random.uniform(0.97, 1.0)
                close_price = price
                volume = int(random.uniform(100000, 1000000))

                data.append({
                    'stock_id': stock_id,
                    'date': date,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                })

        # 創建 DataFrame 並設置 MultiIndex
        df = pd.DataFrame(data)
        df = df.set_index(['stock_id', 'date'])

        return df

    def simulate_market_crash(self, data, crash_date, crash_pct=-0.15, recovery_days=30):
        """
        模擬市場崩盤情境

        Args:
            data (pd.DataFrame): 原始市場數據
            crash_date (datetime.date): 崩盤日期
            crash_pct (float): 崩盤幅度，負數表示下跌
            recovery_days (int): 恢復天數

        Returns:
            pd.DataFrame: 模擬崩盤後的市場數據
        """
        # 複製原始數據
        simulated_data = data.copy()

        # 獲取所有日期並排序
        all_dates = sorted(data.index.get_level_values('date').unique())

        # 找到崩盤日期的索引
        try:
            crash_idx = all_dates.index(crash_date)
        except ValueError:
            # 如果找不到確切日期，找最接近的日期
            crash_idx = min(range(len(all_dates)), key=lambda i: abs((all_dates[i] - crash_date).days))
            crash_date = all_dates[crash_idx]

        # 確保有足夠的恢復天數
        recovery_days = min(recovery_days, len(all_dates) - crash_idx - 1)

        # 對每支股票應用崩盤效應
        for stock_id in data.index.get_level_values('stock_id').unique():
            # 崩盤日價格變動
            if (stock_id, crash_date) in simulated_data.index:
                # 崩盤日的價格變動
                crash_factor = 1 + crash_pct * random.uniform(0.8, 1.2)  # 添加一些隨機性

                # 更新崩盤日的價格
                for col in ['open', 'high', 'low', 'close']:
                    if col in simulated_data.columns:
                        simulated_data.loc[(stock_id, crash_date), col] *= crash_factor

                # 崩盤日成交量暴增
                if 'volume' in simulated_data.columns:
                    simulated_data.loc[(stock_id, crash_date), 'volume'] *= random.uniform(3, 5)

                # 恢復期的價格變動
                for i in range(1, recovery_days + 1):
                    if crash_idx + i < len(all_dates):
                        recovery_date = all_dates[crash_idx + i]
                        if (stock_id, recovery_date) in simulated_data.index:
                            # 計算恢復因子，隨著時間推移逐漸恢復
                            recovery_progress = i / recovery_days
                            recovery_factor = 1 + (abs(crash_pct) * 0.7 * recovery_progress * random.uniform(0.8, 1.2))

                            # 更新恢復期的價格
                            for col in ['open', 'high', 'low', 'close']:
                                if col in simulated_data.columns:
                                    simulated_data.loc[(stock_id, recovery_date), col] *= recovery_factor

                            # 恢復期成交量逐漸回落
                            if 'volume' in simulated_data.columns:
                                volume_factor = 3 - 2 * recovery_progress
                                simulated_data.loc[(stock_id, recovery_date), 'volume'] *= volume_factor

        return simulated_data

    def simulate_liquidity_crisis(self, data, start_date, end_date, affected_stocks=None, severity=0.7):
        """
        模擬流動性不足情境

        Args:
            data (pd.DataFrame): 原始市場數據
            start_date (datetime.date): 開始日期
            end_date (datetime.date): 結束日期
            affected_stocks (list, optional): 受影響的股票列表，如果為 None 則隨機選擇
            severity (float): 嚴重程度，0-1 之間

        Returns:
            pd.DataFrame: 模擬流動性危機後的市場數據
        """
        # 複製原始數據
        simulated_data = data.copy()

        # 獲取所有股票
        all_stocks = data.index.get_level_values('stock_id').unique()

        # 如果沒有指定受影響的股票，隨機選擇 30% 的股票
        if affected_stocks is None:
            n_affected = max(1, int(len(all_stocks) * 0.3))
            affected_stocks = random.sample(list(all_stocks), n_affected)

        # 獲取日期範圍
        date_mask = (data.index.get_level_values('date') >= start_date) & (data.index.get_level_values('date') <= end_date)

        # 對受影響的股票應用流動性危機效應
        for stock_id in affected_stocks:
            # 選擇該股票在日期範圍內的數據
            stock_mask = (data.index.get_level_values('stock_id') == stock_id) & date_mask

            if stock_mask.any():
                # 成交量大幅下降
                if 'volume' in simulated_data.columns:
                    simulated_data.loc[stock_mask, 'volume'] *= (1 - severity * random.uniform(0.8, 1.0))

                # 價格波動加大
                for col in ['open', 'high', 'low', 'close']:
                    if col in simulated_data.columns:
                        # 添加更大的價格波動
                        noise = np.random.normal(0, severity * 0.03, size=stock_mask.sum())
                        simulated_data.loc[stock_mask, col] *= (1 + noise)

                # 確保 high >= open >= low 和 high >= close >= low
                if all(col in simulated_data.columns for col in ['open', 'high', 'low', 'close']):
                    for idx in simulated_data[stock_mask].index:
                        row = simulated_data.loc[idx]
                        high = max(row['open'], row['close'], row['high'])
                        low = min(row['open'], row['close'], row['low'])
                        simulated_data.loc[idx, 'high'] = high
                        simulated_data.loc[idx, 'low'] = low

        return simulated_data

    def simulate_high_volatility(self, data, start_date, end_date, volatility_factor=2.5):
        """
        模擬高波動性情境

        Args:
            data (pd.DataFrame): 原始市場數據
            start_date (datetime.date): 開始日期
            end_date (datetime.date): 結束日期
            volatility_factor (float): 波動性放大因子

        Returns:
            pd.DataFrame: 模擬高波動性後的市場數據
        """
        # 複製原始數據
        simulated_data = data.copy()

        # 獲取日期範圍
        date_mask = (data.index.get_level_values('date') >= start_date) & (data.index.get_level_values('date') <= end_date)

        # 對所有股票應用高波動性效應
        for stock_id in data.index.get_level_values('stock_id').unique():
            # 選擇該股票在日期範圍內的數據
            stock_mask = (data.index.get_level_values('stock_id') == stock_id) & date_mask

            if stock_mask.any():
                # 獲取該股票在日期範圍內的收盤價
                if 'close' in simulated_data.columns:
                    # 計算原始波動性
                    close_prices = simulated_data.loc[stock_mask, 'close']
                    returns = close_prices.pct_change().dropna()

                    if len(returns) > 1:
                        # 生成新的高波動性收益率
                        mean_return = returns.mean()
                        std_return = returns.std() * volatility_factor
                        new_returns = np.random.normal(mean_return, std_return, size=len(returns))

                        # 從第一個價格開始重建價格序列
                        first_price = close_prices.iloc[0]
                        new_prices = [first_price]
                        for ret in new_returns:
                            new_prices.append(new_prices[-1] * (1 + ret))

                        # 更新收盤價
                        simulated_data.loc[stock_mask, 'close'] = pd.Series(new_prices, index=close_prices.index)

                        # 更新開高低價
                        if all(col in simulated_data.columns for col in ['open', 'high', 'low']):
                            # 獲取原始的開高低收價差異
                            for i, idx in enumerate(simulated_data[stock_mask].index):
                                if i > 0:  # 跳過第一個數據點
                                    new_close = simulated_data.loc[idx, 'close']

                                    # 根據新的收盤價生成開高低價
                                    simulated_data.loc[idx, 'open'] = new_close * (1 + np.random.normal(0, 0.01))
                                    simulated_data.loc[idx, 'high'] = new_close * (1 + abs(np.random.normal(0, 0.02)))
                                    simulated_data.loc[idx, 'low'] = new_close * (1 - abs(np.random.normal(0, 0.02)))

                                    # 確保 high >= open >= low 和 high >= close >= low
                                    row = simulated_data.loc[idx]
                                    high = max(row['open'], row['close'], row['high'])
                                    low = min(row['open'], row['close'], row['low'])
                                    simulated_data.loc[idx, 'high'] = high
                                    simulated_data.loc[idx, 'low'] = low

        return simulated_data


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
    """
    Backtrader 策略類，用於實現基於訊號的交易策略

    主要功能：
    - 支援多種訊號格式（buy_signal/sell_signal 或 signal）
    - 支援投資組合權重
    - 支援滑價和交易成本
    - 支援止損和止盈
    """

    params = (
        ("signals", None),  # 交易訊號
        ("weights", None),  # 投資組合權重
        ("stop_loss", None),  # 止損比例，如 0.05 表示 5% 止損
        ("take_profit", None),  # 止盈比例，如 0.1 表示 10% 止盈
        ("trailing_stop", None),  # 追蹤止損比例
        ("rebalance_freq", "daily"),  # 再平衡頻率：daily, weekly, monthly
        ("risk_control", True),  # 是否啟用風險控制
        ("max_position_pct", 0.2),  # 單一股票最大持倉比例
    )

    def __init__(self):
        self.signals = self.params.signals
        self.weights = self.params.weights
        self.stop_loss = self.params.stop_loss
        self.take_profit = self.params.take_profit
        self.trailing_stop = self.params.trailing_stop
        self.rebalance_freq = self.params.rebalance_freq
        self.risk_control = self.params.risk_control
        self.max_position_pct = self.params.max_position_pct

        self.order_dict = {}  # stock_id -> order
        self.entry_prices = {}  # stock_id -> entry_price
        self.highest_prices = {}  # stock_id -> highest_price (for trailing stop)

        # 建立 stock_id 與 data feed 的對應
        self.stockid_to_data = {}
        for data in self.datas:
            self.stockid_to_data[data._name] = data

        # 記錄上次再平衡日期
        self.last_rebalance_date = None

        # 交易記錄
        self.trade_history = []

        # 添加績效分析器
        self.add_analyzers()

    def add_analyzers(self):
        """添加內建的績效分析器"""
        # 如果已經添加了分析器，則不重複添加
        if hasattr(self, 'analyzers') and len(self.analyzers) > 0:
            return

        # 添加常用分析器
        self.analyzers.drawdown = bt.analyzers.DrawDown()
        self.analyzers.sharpe = bt.analyzers.SharpeRatio()
        self.analyzers.returns = bt.analyzers.Returns()
        self.analyzers.transactions = bt.analyzers.Transactions()
        self.analyzers.tradeanalyzer = bt.analyzers.TradeAnalyzer()

    def should_rebalance(self, current_date):
        """
        根據再平衡頻率決定是否應該進行再平衡

        Args:
            current_date (datetime.date): 當前日期

        Returns:
            bool: 是否應該再平衡
        """
        if self.last_rebalance_date is None:
            return True

        if self.rebalance_freq == 'daily':
            return True
        elif self.rebalance_freq == 'weekly':
            # 如果是週一或者上次再平衡是上週，則再平衡
            return current_date.weekday() == 0 or (current_date - self.last_rebalance_date).days >= 7
        elif self.rebalance_freq == 'monthly':
            # 如果是新的一個月或者上次再平衡是上個月，則再平衡
            return current_date.day == 1 or current_date.month != self.last_rebalance_date.month
        else:
            return True

    def notify_order(self, order):
        """
        訂單狀態變更通知

        Args:
            order (bt.Order): 訂單對象
        """
        if order.status in [order.Completed]:
            # 記錄成交價格
            if order.isbuy():
                self.entry_prices[order.data._name] = order.executed.price
                self.highest_prices[order.data._name] = order.executed.price

                # 記錄交易
                self.trade_history.append({
                    'date': self.datetime.date(0),
                    'stock_id': order.data._name,
                    'action': 'buy',
                    'price': order.executed.price,
                    'size': order.executed.size,
                    'value': order.executed.value,
                    'commission': order.executed.comm,
                })
            else:
                # 記錄交易
                self.trade_history.append({
                    'date': self.datetime.date(0),
                    'stock_id': order.data._name,
                    'action': 'sell',
                    'price': order.executed.price,
                    'size': order.executed.size,
                    'value': order.executed.value,
                    'commission': order.executed.comm,
                })

                # 如果完全平倉，則清除記錄
                if not self.getposition(order.data).size:
                    if order.data._name in self.entry_prices:
                        del self.entry_prices[order.data._name]
                    if order.data._name in self.highest_prices:
                        del self.highest_prices[order.data._name]

    def check_risk_control(self):
        """
        檢查風險控制條件，執行止損、止盈和追蹤止損
        """
        if not self.risk_control:
            return

        for stock_id, data_feed in self.stockid_to_data.items():
            position = self.getposition(data_feed)

            # 如果沒有持倉，則跳過
            if not position.size:
                continue

            current_price = data_feed.close[0]
            entry_price = self.entry_prices.get(stock_id)

            if entry_price is None:
                continue

            # 更新最高價格（用於追蹤止損）
            if current_price > self.highest_prices.get(stock_id, 0):
                self.highest_prices[stock_id] = current_price

            # 檢查止損
            if self.stop_loss is not None:
                stop_price = entry_price * (1 - self.stop_loss)
                if current_price <= stop_price:
                    self.close(data_feed)
                    self.log(f"止損: {stock_id} @ {current_price:.2f}")
                    continue

            # 檢查止盈
            if self.take_profit is not None:
                take_profit_price = entry_price * (1 + self.take_profit)
                if current_price >= take_profit_price:
                    self.close(data_feed)
                    self.log(f"止盈: {stock_id} @ {current_price:.2f}")
                    continue

            # 檢查追蹤止損
            if self.trailing_stop is not None:
                highest_price = self.highest_prices.get(stock_id, entry_price)
                trail_stop_price = highest_price * (1 - self.trailing_stop)
                if current_price <= trail_stop_price:
                    self.close(data_feed)
                    self.log(f"追蹤止損: {stock_id} @ {current_price:.2f}")
                    continue

    def log(self, txt, dt=None):
        """
        記錄訊息

        Args:
            txt (str): 訊息內容
            dt (datetime.date, optional): 日期
        """
        dt = dt or self.datetime.date(0)
        print(f"{dt.isoformat()}: {txt}")

    def next(self):
        """
        每個交易日執行的策略邏輯
        """
        current_date = self.datetime.date(0)

        # 檢查風險控制
        self.check_risk_control()

        # 檢查是否需要再平衡
        if not self.should_rebalance(current_date):
            return

        # 記錄再平衡日期
        self.last_rebalance_date = current_date

        # signals/weights 需為 MultiIndex (stock_id, date)
        if self.signals is not None:
            try:
                day_signals = self.signals.xs(current_date, level="date")
            except Exception:
                return

            # 處理賣出訊號
            if "sell_signal" in day_signals.columns:
                for stock_id, signal_row in day_signals[
                    day_signals["sell_signal"] == 1
                ].iterrows():
                    if stock_id in self.stockid_to_data:
                        data_feed = self.stockid_to_data[stock_id]
                        position = self.getposition(data_feed)
                        if position.size > 0:
                            self.close(data_feed)
                            self.log(f"賣出訊號: {stock_id} @ {data_feed.close[0]:.2f}")

            # 處理買入訊號
            signal_col = (
                "buy_signal"
                if "buy_signal" in day_signals.columns
                else ("signal" if "signal" in day_signals.columns else None)
            )

            if signal_col:
                # 計算權重
                if self.weights is not None:
                    try:
                        day_weights = self.weights.xs(current_date, level="date")
                    except Exception:
                        # 如果找不到當天的權重，則使用等權重
                        buy_stocks = day_signals[day_signals[signal_col] > 0].index
                        n_stocks = len(buy_stocks)
                        day_weights = pd.Series(
                            1.0 / n_stocks if n_stocks > 0 else 0,
                            index=buy_stocks,
                        )
                else:
                    # 使用等權重
                    buy_stocks = day_signals[day_signals[signal_col] > 0].index
                    n_stocks = len(buy_stocks)
                    day_weights = pd.Series(
                        1.0 / n_stocks if n_stocks > 0 else 0,
                        index=buy_stocks,
                    )

                # 計算投資組合總值
                portfolio_value = self.broker.getvalue()

                # 執行買入訂單
                for stock_id, weight in day_weights.items():
                    if weight > 0 and stock_id in self.stockid_to_data:
                        # 應用單一股票最大持倉限制
                        weight = min(weight, self.max_position_pct)

                        data_feed = self.stockid_to_data[stock_id]
                        price = data_feed.close[0]
                        target_value = portfolio_value * weight
                        target_shares = int(target_value / price)

                        # 檢查現有持倉
                        position = self.getposition(data_feed)

                        if position.size > 0:
                            # 已有持倉，調整至目標持倉
                            if target_shares > position.size:
                                # 增加持倉
                                self.buy(data_feed, size=target_shares - position.size)
                                self.log(f"增加持倉: {stock_id} +{target_shares - position.size} @ {price:.2f}")
                            elif target_shares < position.size:
                                # 減少持倉
                                self.sell(data_feed, size=position.size - target_shares)
                                self.log(f"減少持倉: {stock_id} -{position.size - target_shares} @ {price:.2f}")
                        else:
                            # 新建持倉
                            if target_shares > 0:
                                self.buy(data_feed, size=target_shares)
                                self.log(f"新建持倉: {stock_id} {target_shares} @ {price:.2f}")

    def get_trade_history(self):
        """
        獲取交易歷史

        Returns:
            pd.DataFrame: 交易歷史
        """
        return pd.DataFrame(self.trade_history)


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
        self.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        self.addanalyzer(bt.analyzers.SQN, _name="sqn")

    def run_hybrid(self, strategy_cls, *args, **kwargs):
        """
        執行混合型回測，strategy_cls 必須支援情感因子與 TA-Lib 指標
        """
        self.addstrategy(
            strategy_cls, news_sentiment_df=self.news_sentiment_df, *args, **kwargs
        )
        results = self.run()
        strat = results[0]

        # 獲取分析結果
        sharpe = strat.analyzers.sharpe.get_analysis().get("sharperatio", None)
        max_drawdown = strat.analyzers.drawdown.get_analysis()["max"]["drawdown"] / 100
        annual_return = strat.analyzers.returns.get_analysis().get("rnorm100", None)

        # 獲取交易分析
        trades_analysis = strat.analyzers.trades.get_analysis()

        # 計算更多指標
        win_rate = 0
        avg_win = 0
        avg_loss = 0
        profit_factor = 0

        if hasattr(trades_analysis, 'won') and trades_analysis.won.total > 0:
            win_rate = trades_analysis.won.total / (trades_analysis.won.total + trades_analysis.lost.total)
            avg_win = trades_analysis.won.pnl.average
            avg_loss = abs(trades_analysis.lost.pnl.average) if trades_analysis.lost.total > 0 else 0
            profit_factor = trades_analysis.won.pnl.total / abs(trades_analysis.lost.pnl.total) if trades_analysis.lost.pnl.total != 0 else float('inf')

        # 獲取 SQN 分數
        sqn = strat.analyzers.sqn.get_analysis().get('sqn', 0)

        return {
            "portfolio_value": self.broker.getvalue(),
            "annual_return": annual_return,
            "sharpe": sharpe,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "sqn": sqn,
            "strategy": strat,
        }


class MultiStrategyBacktest:
    """
    多策略回測類，用於比較多個策略的表現

    主要功能：
    - 同時回測多個策略
    - 比較策略表現
    - 生成策略比較報告
    - 支援策略切換
    """

    def __init__(
        self,
        price_data=None,
        start_date=None,
        end_date=None,
        initial_capital=1000000,
        commission_rate=0.001425,
        slippage=0.001,
        tax=0.003,
    ):
        """
        初始化多策略回測

        Args:
            price_data (pd.DataFrame, optional): 價格資料，如果為 None 則載入資料
            start_date (datetime.date, optional): 回測開始日期
            end_date (datetime.date, optional): 回測結束日期
            initial_capital (float): 初始資金
            commission_rate (float): 佣金費率
            slippage (float): 滑價率
            tax (float): 稅率
        """
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.tax = tax

        # 載入資料
        if price_data is None:
            self.price_data = load_data(start_date, end_date)["price"]
        else:
            self.price_data = price_data

        # 避免 look-ahead bias
        self.price_data = align_timeseries(self.price_data, start_date, end_date)

        # 策略結果
        self.strategy_results = {}

    def add_strategy(self, name, signals, weights=None, **kwargs):
        """
        添加策略

        Args:
            name (str): 策略名稱
            signals (pd.DataFrame): 交易訊號
            weights (pd.DataFrame, optional): 投資組合權重
            **kwargs: 其他參數，傳遞給 SignalStrategy
        """
        # 避免 look-ahead bias
        aligned_signals = align_timeseries(signals, self.start_date, self.end_date)

        if weights is not None:
            aligned_weights = align_timeseries(weights, self.start_date, self.end_date)
        else:
            aligned_weights = None

        # 保存策略
        self.strategy_results[name] = {
            "signals": aligned_signals,
            "weights": aligned_weights,
            "params": kwargs,
            "results": None,
        }

    def run_all(self):
        """
        執行所有策略的回測

        Returns:
            dict: 所有策略的回測結果
        """
        for name, strategy in self.strategy_results.items():
            print(f"執行策略: {name}")

            # 創建 Backtrader 引擎
            cerebro = bt.Cerebro()

            # 添加資料
            for stock_id in self.price_data.index.get_level_values("stock_id").unique():
                stock_df = self.price_data.loc[stock_id]
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

            # 設置經紀商參數
            cerebro.broker.setcash(self.initial_capital)
            cerebro.broker.setcommission(commission=self.commission_rate)
            cerebro.broker.set_slippage_perc(self.slippage)

            # 添加策略
            cerebro.addstrategy(
                SignalStrategy,
                signals=strategy["signals"],
                weights=strategy["weights"],
                **strategy["params"],
            )

            # 添加分析器
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
            cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
            cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")

            # 執行回測
            results = cerebro.run()
            strat = results[0]

            # 獲取分析結果
            sharpe = strat.analyzers.sharpe.get_analysis().get("sharperatio", None)
            max_drawdown = strat.analyzers.drawdown.get_analysis()["max"]["drawdown"] / 100
            annual_return = strat.analyzers.returns.get_analysis().get("rnorm100", None)

            # 獲取交易分析
            trades_analysis = strat.analyzers.trades.get_analysis()

            # 計算更多指標
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0

            if hasattr(trades_analysis, 'won') and trades_analysis.won.total > 0:
                win_rate = trades_analysis.won.total / (trades_analysis.won.total + trades_analysis.lost.total)
                avg_win = trades_analysis.won.pnl.average
                avg_loss = abs(trades_analysis.lost.pnl.average) if trades_analysis.lost.total > 0 else 0
                profit_factor = trades_analysis.won.pnl.total / abs(trades_analysis.lost.pnl.total) if trades_analysis.lost.pnl.total != 0 else float('inf')

            # 獲取 SQN 分數
            sqn = strat.analyzers.sqn.get_analysis().get('sqn', 0)

            # 保存結果
            self.strategy_results[name]["results"] = {
                "portfolio_value": cerebro.broker.getvalue(),
                "annual_return": annual_return,
                "sharpe": sharpe,
                "max_drawdown": max_drawdown,
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": profit_factor,
                "sqn": sqn,
                "strategy": strat,
            }

        return self.strategy_results

    def get_comparison_table(self):
        """
        獲取策略比較表

        Returns:
            pd.DataFrame: 策略比較表
        """
        if not self.strategy_results or not any(s["results"] for s in self.strategy_results.values()):
            raise ValueError("必須先執行回測")

        # 創建比較表
        comparison = []
        for name, strategy in self.strategy_results.items():
            if strategy["results"]:
                results = strategy["results"]
                comparison.append({
                    "策略": name,
                    "最終資產": results["portfolio_value"],
                    "年化報酬率": results["annual_return"] if results["annual_return"] else 0,
                    "夏普比率": results["sharpe"] if results["sharpe"] else 0,
                    "最大回撤": results["max_drawdown"] if results["max_drawdown"] else 0,
                    "勝率": results["win_rate"] if "win_rate" in results else 0,
                    "平均獲利": results["avg_win"] if "avg_win" in results else 0,
                    "平均虧損": results["avg_loss"] if "avg_loss" in results else 0,
                    "獲利因子": results["profit_factor"] if "profit_factor" in results else 0,
                    "SQN分數": results["sqn"] if "sqn" in results else 0,
                })

        return pd.DataFrame(comparison)

    def plot_equity_curves(self, figsize=(12, 8)):
        """
        繪製所有策略的權益曲線

        Args:
            figsize (tuple): 圖表大小

        Returns:
            matplotlib.figure.Figure: 圖表對象
        """
        if not self.strategy_results or not any(s["results"] for s in self.strategy_results.values()):
            raise ValueError("必須先執行回測")

        # 創建圖表
        fig, ax = plt.subplots(figsize=figsize)

        # 繪製每個策略的權益曲線
        for name, strategy in self.strategy_results.items():
            if strategy["results"]:
                # 獲取策略對象
                strat = strategy["results"]["strategy"]

                # 獲取權益曲線
                portfolio_value = pd.Series(strat._broker.get_value())

                # 繪製曲線
                ax.plot(portfolio_value.index, portfolio_value.values, label=name)

        # 設置圖表屬性
        ax.set_title("策略權益曲線比較")
        ax.set_xlabel("交易日")
        ax.set_ylabel("資產價值")
        ax.grid(True)
        ax.legend()

        return fig

    def get_best_strategy(self, metric="sharpe"):
        """
        獲取最佳策略

        Args:
            metric (str): 評估指標，可選 "sharpe", "annual_return", "max_drawdown", "win_rate", "profit_factor", "sqn"

        Returns:
            tuple: (策略名稱, 策略結果)
        """
        if not self.strategy_results or not any(s["results"] for s in self.strategy_results.values()):
            raise ValueError("必須先執行回測")

        # 根據指標選擇最佳策略
        if metric == "max_drawdown":
            # 最大回撤越小越好
            best_strategy = min(
                [(name, s["results"]) for name, s in self.strategy_results.items() if s["results"]],
                key=lambda x: x[1]["max_drawdown"] if x[1]["max_drawdown"] is not None else float('inf')
            )
        else:
            # 其他指標越大越好
            best_strategy = max(
                [(name, s["results"]) for name, s in self.strategy_results.items() if s["results"]],
                key=lambda x: x[1][metric] if x[1][metric] is not None else float('-inf')
            )

        return best_strategy

    def generate_report(self, output_dir="results"):
        """
        生成回測報告

        Args:
            output_dir (str): 輸出目錄

        Returns:
            str: 報告文件路徑
        """
        if not self.strategy_results or not any(s["results"] for s in self.strategy_results.values()):
            raise ValueError("必須先執行回測")

        # 創建輸出目錄
        os.makedirs(output_dir, exist_ok=True)

        # 生成報告時間戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(output_dir, f"backtest_report_{timestamp}.html")

        # 創建 HTML 報告
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("<html><head>")
            f.write("<style>")
            f.write("body { font-family: Arial, sans-serif; margin: 20px; }")
            f.write("table { border-collapse: collapse; width: 100%; }")
            f.write("th, td { border: 1px solid #ddd; padding: 8px; text-align: right; }")
            f.write("th { background-color: #f2f2f2; text-align: center; }")
            f.write("tr:nth-child(even) { background-color: #f9f9f9; }")
            f.write("h1, h2, h3 { color: #333; }")
            f.write(".summary { margin-bottom: 20px; }")
            f.write(".best { font-weight: bold; color: green; }")
            f.write(".worst { font-weight: bold; color: red; }")
            f.write("</style>")
            f.write("</head><body>")

            # 報告標題
            f.write(f"<h1>回測報告 - {timestamp}</h1>")

            # 回測參數
            f.write("<div class='summary'>")
            f.write("<h2>回測參數</h2>")
            f.write("<table>")
            f.write("<tr><th>參數</th><th>值</th></tr>")
            f.write(f"<tr><td>開始日期</td><td>{self.start_date}</td></tr>")
            f.write(f"<tr><td>結束日期</td><td>{self.end_date}</td></tr>")
            f.write(f"<tr><td>初始資金</td><td>{self.initial_capital:,.2f}</td></tr>")
            f.write(f"<tr><td>佣金費率</td><td>{self.commission_rate:.6f}</td></tr>")
            f.write(f"<tr><td>滑價率</td><td>{self.slippage:.6f}</td></tr>")
            f.write(f"<tr><td>稅率</td><td>{self.tax:.6f}</td></tr>")
            f.write("</table>")
            f.write("</div>")

            # 策略比較表
            comparison_df = self.get_comparison_table()

            f.write("<div class='summary'>")
            f.write("<h2>策略比較</h2>")
            f.write(comparison_df.to_html(index=False, float_format=lambda x: f"{x:.4f}"))
            f.write("</div>")

            # 最佳策略
            best_sharpe = self.get_best_strategy("sharpe")
            best_return = self.get_best_strategy("annual_return")
            best_drawdown = self.get_best_strategy("max_drawdown")

            f.write("<div class='summary'>")
            f.write("<h2>最佳策略</h2>")
            f.write("<table>")
            f.write("<tr><th>指標</th><th>策略</th><th>值</th></tr>")
            f.write(f"<tr><td>最佳夏普比率</td><td>{best_sharpe[0]}</td><td>{best_sharpe[1]['sharpe']:.4f}</td></tr>")
            f.write(f"<tr><td>最佳年化報酬率</td><td>{best_return[0]}</td><td>{best_return[1]['annual_return']:.4f}</td></tr>")
            f.write(f"<tr><td>最小最大回撤</td><td>{best_drawdown[0]}</td><td>{best_drawdown[1]['max_drawdown']:.4f}</td></tr>")
            f.write("</table>")
            f.write("</div>")

            # 各策略詳細資訊
            f.write("<h2>策略詳細資訊</h2>")

            for name, strategy in self.strategy_results.items():
                if strategy["results"]:
                    results = strategy["results"]
                    f.write(f"<h3>{name}</h3>")

                    # 策略參數
                    f.write("<div class='summary'>")
                    f.write("<h4>策略參數</h4>")
                    f.write("<table>")
                    f.write("<tr><th>參數</th><th>值</th></tr>")
                    for param, value in strategy["params"].items():
                        f.write(f"<tr><td>{param}</td><td>{value}</td></tr>")
                    f.write("</table>")
                    f.write("</div>")

                    # 績效指標
                    f.write("<div class='summary'>")
                    f.write("<h4>績效指標</h4>")
                    f.write("<table>")
                    f.write("<tr><th>指標</th><th>值</th></tr>")
                    f.write(f"<tr><td>最終資產</td><td>{results['portfolio_value']:,.2f}</td></tr>")
                    f.write(f"<tr><td>年化報酬率</td><td>{results['annual_return']:.4f}</td></tr>")
                    f.write(f"<tr><td>夏普比率</td><td>{results['sharpe']:.4f}</td></tr>")
                    f.write(f"<tr><td>最大回撤</td><td>{results['max_drawdown']:.4f}</td></tr>")
                    f.write(f"<tr><td>勝率</td><td>{results['win_rate']:.4f}</td></tr>")
                    f.write(f"<tr><td>平均獲利</td><td>{results['avg_win']:.4f}</td></tr>")
                    f.write(f"<tr><td>平均虧損</td><td>{results['avg_loss']:.4f}</td></tr>")
                    f.write(f"<tr><td>獲利因子</td><td>{results['profit_factor']:.4f}</td></tr>")
                    f.write(f"<tr><td>SQN分數</td><td>{results['sqn']:.4f}</td></tr>")
                    f.write("</table>")
                    f.write("</div>")

            f.write("</body></html>")

        print(f"報告已生成: {report_file}")
        return report_file


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


class StressTest:
    """
    壓力測試類，用於測試策略在極端市場條件下的表現

    主要功能：
    - 模擬市場崩盤情境
    - 模擬流動性危機情境
    - 模擬高波動性情境
    - 比較策略在正常和壓力情境下的表現
    """

    def __init__(
        self,
        strategy,
        price_data=None,
        start_date=None,
        end_date=None,
        initial_capital=1000000,
        commission_rate=0.001425,
        slippage=0.001,
        tax=0.003,
    ):
        """
        初始化壓力測試

        Args:
            strategy: 策略類或策略實例
            price_data (pd.DataFrame, optional): 價格資料，如果為 None 則載入資料
            start_date (datetime.date, optional): 回測開始日期
            end_date (datetime.date, optional): 回測結束日期
            initial_capital (float): 初始資金
            commission_rate (float): 佣金費率
            slippage (float): 滑價率
            tax (float): 稅率
        """
        self.strategy = strategy
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        self.tax = tax

        # 載入資料
        if price_data is None:
            self.price_data = load_data(start_date, end_date)["price"]
        else:
            self.price_data = price_data

        # 避免 look-ahead bias
        self.price_data = align_timeseries(self.price_data, start_date, end_date)

        # 創建資料模擬器
        self.simulator = MarketDataSimulator(self.price_data)

        # 測試結果
        self.test_results = {}

    def run_normal_test(self, signals=None, weights=None, **kwargs):
        """
        執行正常市場條件下的回測

        Args:
            signals (pd.DataFrame, optional): 交易訊號
            weights (pd.DataFrame, optional): 投資組合權重
            **kwargs: 其他參數，傳遞給策略

        Returns:
            dict: 回測結果
        """
        print("執行正常市場條件下的回測...")

        # 使用原始價格資料執行回測
        results = self._run_backtest(
            "normal",
            self.price_data,
            signals,
            weights,
            **kwargs
        )

        return results

    def run_market_crash_test(
        self,
        crash_date=None,
        crash_pct=-0.15,
        recovery_days=30,
        signals=None,
        weights=None,
        **kwargs
    ):
        """
        執行市場崩盤情境下的回測

        Args:
            crash_date (datetime.date, optional): 崩盤日期，如果為 None 則隨機選擇
            crash_pct (float): 崩盤幅度，負數表示下跌
            recovery_days (int): 恢復天數
            signals (pd.DataFrame, optional): 交易訊號
            weights (pd.DataFrame, optional): 投資組合權重
            **kwargs: 其他參數，傳遞給策略

        Returns:
            dict: 回測結果
        """
        print(f"執行市場崩盤情境下的回測 (崩盤幅度: {crash_pct*100:.1f}%)...")

        # 如果未指定崩盤日期，則選擇回測期間的中間日期
        if crash_date is None:
            all_dates = sorted(self.price_data.index.get_level_values("date").unique())
            crash_date = all_dates[len(all_dates) // 3]  # 選擇前 1/3 的位置

        # 模擬市場崩盤
        crash_data = self.simulator.simulate_market_crash(
            self.price_data,
            crash_date,
            crash_pct,
            recovery_days
        )

        # 執行回測
        results = self._run_backtest(
            f"market_crash_{crash_pct}",
            crash_data,
            signals,
            weights,
            **kwargs
        )

        return results

    def run_liquidity_crisis_test(
        self,
        start_date=None,
        end_date=None,
        affected_stocks=None,
        severity=0.7,
        signals=None,
        weights=None,
        **kwargs
    ):
        """
        執行流動性危機情境下的回測

        Args:
            start_date (datetime.date, optional): 危機開始日期，如果為 None 則隨機選擇
            end_date (datetime.date, optional): 危機結束日期，如果為 None 則設為開始日期後 20 天
            affected_stocks (list, optional): 受影響的股票列表，如果為 None 則隨機選擇
            severity (float): 嚴重程度，0-1 之間
            signals (pd.DataFrame, optional): 交易訊號
            weights (pd.DataFrame, optional): 投資組合權重
            **kwargs: 其他參數，傳遞給策略

        Returns:
            dict: 回測結果
        """
        print(f"執行流動性危機情境下的回測 (嚴重程度: {severity:.1f})...")

        # 如果未指定危機日期，則選擇回測期間的中間日期
        all_dates = sorted(self.price_data.index.get_level_values("date").unique())
        if start_date is None:
            start_idx = len(all_dates) // 3
            start_date = all_dates[start_idx]

        if end_date is None:
            end_idx = min(start_idx + 20, len(all_dates) - 1)
            end_date = all_dates[end_idx]

        # 模擬流動性危機
        liquidity_data = self.simulator.simulate_liquidity_crisis(
            self.price_data,
            start_date,
            end_date,
            affected_stocks,
            severity
        )

        # 執行回測
        results = self._run_backtest(
            f"liquidity_crisis_{severity}",
            liquidity_data,
            signals,
            weights,
            **kwargs
        )

        return results

    def run_high_volatility_test(
        self,
        start_date=None,
        end_date=None,
        volatility_factor=2.5,
        signals=None,
        weights=None,
        **kwargs
    ):
        """
        執行高波動性情境下的回測

        Args:
            start_date (datetime.date, optional): 高波動性開始日期，如果為 None 則隨機選擇
            end_date (datetime.date, optional): 高波動性結束日期，如果為 None 則設為開始日期後 30 天
            volatility_factor (float): 波動性放大因子
            signals (pd.DataFrame, optional): 交易訊號
            weights (pd.DataFrame, optional): 投資組合權重
            **kwargs: 其他參數，傳遞給策略

        Returns:
            dict: 回測結果
        """
        print(f"執行高波動性情境下的回測 (波動性因子: {volatility_factor:.1f})...")

        # 如果未指定日期，則選擇回測期間的中間日期
        all_dates = sorted(self.price_data.index.get_level_values("date").unique())
        if start_date is None:
            start_idx = len(all_dates) // 3
            start_date = all_dates[start_idx]

        if end_date is None:
            end_idx = min(start_idx + 30, len(all_dates) - 1)
            end_date = all_dates[end_idx]

        # 模擬高波動性
        volatility_data = self.simulator.simulate_high_volatility(
            self.price_data,
            start_date,
            end_date,
            volatility_factor
        )

        # 執行回測
        results = self._run_backtest(
            f"high_volatility_{volatility_factor}",
            volatility_data,
            signals,
            weights,
            **kwargs
        )

        return results

    def run_all_tests(self, signals=None, weights=None, **kwargs):
        """
        執行所有壓力測試

        Args:
            signals (pd.DataFrame, optional): 交易訊號
            weights (pd.DataFrame, optional): 投資組合權重
            **kwargs: 其他參數，傳遞給策略

        Returns:
            dict: 所有測試的結果
        """
        # 執行正常市場條件下的回測
        self.run_normal_test(signals, weights, **kwargs)

        # 執行市場崩盤情境下的回測
        self.run_market_crash_test(
            crash_pct=-0.15,
            signals=signals,
            weights=weights,
            **kwargs
        )

        # 執行流動性危機情境下的回測
        self.run_liquidity_crisis_test(
            severity=0.7,
            signals=signals,
            weights=weights,
            **kwargs
        )

        # 執行高波動性情境下的回測
        self.run_high_volatility_test(
            volatility_factor=2.5,
            signals=signals,
            weights=weights,
            **kwargs
        )

        return self.test_results

    def _run_backtest(self, scenario_name, price_data, signals=None, weights=None, **kwargs):
        """
        執行回測

        Args:
            scenario_name (str): 情境名稱
            price_data (pd.DataFrame): 價格資料
            signals (pd.DataFrame, optional): 交易訊號
            weights (pd.DataFrame, optional): 投資組合權重
            **kwargs: 其他參數，傳遞給策略

        Returns:
            dict: 回測結果
        """
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

        # 設置經紀商參數
        cerebro.broker.setcash(self.initial_capital)
        cerebro.broker.setcommission(commission=self.commission_rate)
        cerebro.broker.set_slippage_perc(self.slippage)

        # 添加策略
        if signals is not None:
            # 使用 SignalStrategy
            cerebro.addstrategy(
                SignalStrategy,
                signals=signals,
                weights=weights,
                **kwargs
            )
        else:
            # 使用提供的策略
            cerebro.addstrategy(self.strategy, **kwargs)

        # 添加分析器
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")

        # 執行回測
        results = cerebro.run()
        strat = results[0]

        # 獲取分析結果
        sharpe = strat.analyzers.sharpe.get_analysis().get("sharperatio", None)
        max_drawdown = strat.analyzers.drawdown.get_analysis()["max"]["drawdown"] / 100
        annual_return = strat.analyzers.returns.get_analysis().get("rnorm100", None)

        # 獲取交易分析
        trades_analysis = strat.analyzers.trades.get_analysis()

        # 計算更多指標
        win_rate = 0
        avg_win = 0
        avg_loss = 0
        profit_factor = 0

        if hasattr(trades_analysis, 'won') and trades_analysis.won.total > 0:
            win_rate = trades_analysis.won.total / (trades_analysis.won.total + trades_analysis.lost.total)
            avg_win = trades_analysis.won.pnl.average
            avg_loss = abs(trades_analysis.lost.pnl.average) if trades_analysis.lost.total > 0 else 0
            profit_factor = trades_analysis.won.pnl.total / abs(trades_analysis.lost.pnl.total) if trades_analysis.lost.pnl.total != 0 else float('inf')

        # 獲取 SQN 分數
        sqn = strat.analyzers.sqn.get_analysis().get('sqn', 0)

        # 保存結果
        self.test_results[scenario_name] = {
            "portfolio_value": cerebro.broker.getvalue(),
            "annual_return": annual_return,
            "sharpe": sharpe,
            "max_drawdown": max_drawdown,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "sqn": sqn,
            "strategy": strat,
        }

        return self.test_results[scenario_name]

    def get_comparison_table(self):
        """
        獲取情境比較表

        Returns:
            pd.DataFrame: 情境比較表
        """
        if not self.test_results:
            raise ValueError("必須先執行測試")

        # 創建比較表
        comparison = []
        for scenario, results in self.test_results.items():
            comparison.append({
                "情境": scenario,
                "最終資產": results["portfolio_value"],
                "年化報酬率": results["annual_return"] if results["annual_return"] else 0,
                "夏普比率": results["sharpe"] if results["sharpe"] else 0,
                "最大回撤": results["max_drawdown"] if results["max_drawdown"] else 0,
                "勝率": results["win_rate"],
                "平均獲利": results["avg_win"],
                "平均虧損": results["avg_loss"],
                "獲利因子": results["profit_factor"],
                "SQN分數": results["sqn"],
            })

        return pd.DataFrame(comparison)

    def plot_equity_curves(self, figsize=(12, 8)):
        """
        繪製所有情境的權益曲線

        Args:
            figsize (tuple): 圖表大小

        Returns:
            matplotlib.figure.Figure: 圖表對象
        """
        if not self.test_results:
            raise ValueError("必須先執行測試")

        # 創建圖表
        fig, ax = plt.subplots(figsize=figsize)

        # 繪製每個情境的權益曲線
        for scenario, results in self.test_results.items():
            # 獲取策略對象
            strat = results["strategy"]

            # 獲取權益曲線
            portfolio_value = pd.Series(strat._broker.get_value())

            # 繪製曲線
            ax.plot(portfolio_value.index, portfolio_value.values, label=scenario)

        # 設置圖表屬性
        ax.set_title("不同情境下的權益曲線比較")
        ax.set_xlabel("交易日")
        ax.set_ylabel("資產價值")
        ax.grid(True)
        ax.legend()

        return fig

    def generate_report(self, output_dir="results"):
        """
        生成壓力測試報告

        Args:
            output_dir (str): 輸出目錄

        Returns:
            str: 報告文件路徑
        """
        if not self.test_results:
            raise ValueError("必須先執行測試")

        # 創建輸出目錄
        os.makedirs(output_dir, exist_ok=True)

        # 生成報告時間戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(output_dir, f"stress_test_report_{timestamp}.html")

        # 創建 HTML 報告
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("<html><head>")
            f.write("<style>")
            f.write("body { font-family: Arial, sans-serif; margin: 20px; }")
            f.write("table { border-collapse: collapse; width: 100%; }")
            f.write("th, td { border: 1px solid #ddd; padding: 8px; text-align: right; }")
            f.write("th { background-color: #f2f2f2; text-align: center; }")
            f.write("tr:nth-child(even) { background-color: #f9f9f9; }")
            f.write("h1, h2, h3 { color: #333; }")
            f.write(".summary { margin-bottom: 20px; }")
            f.write(".best { font-weight: bold; color: green; }")
            f.write(".worst { font-weight: bold; color: red; }")
            f.write("</style>")
            f.write("</head><body>")

            # 報告標題
            f.write(f"<h1>壓力測試報告 - {timestamp}</h1>")

            # 測試參數
            f.write("<div class='summary'>")
            f.write("<h2>測試參數</h2>")
            f.write("<table>")
            f.write("<tr><th>參數</th><th>值</th></tr>")
            f.write(f"<tr><td>開始日期</td><td>{self.start_date}</td></tr>")
            f.write(f"<tr><td>結束日期</td><td>{self.end_date}</td></tr>")
            f.write(f"<tr><td>初始資金</td><td>{self.initial_capital:,.2f}</td></tr>")
            f.write(f"<tr><td>佣金費率</td><td>{self.commission_rate:.6f}</td></tr>")
            f.write(f"<tr><td>滑價率</td><td>{self.slippage:.6f}</td></tr>")
            f.write(f"<tr><td>稅率</td><td>{self.tax:.6f}</td></tr>")
            f.write("</table>")
            f.write("</div>")

            # 情境比較表
            comparison_df = self.get_comparison_table()

            f.write("<div class='summary'>")
            f.write("<h2>情境比較</h2>")
            f.write(comparison_df.to_html(index=False, float_format=lambda x: f"{x:.4f}"))
            f.write("</div>")

            # 各情境詳細資訊
            f.write("<h2>情境詳細資訊</h2>")

            for scenario, results in self.test_results.items():
                f.write(f"<h3>{scenario}</h3>")

                # 績效指標
                f.write("<div class='summary'>")
                f.write("<h4>績效指標</h4>")
                f.write("<table>")
                f.write("<tr><th>指標</th><th>值</th></tr>")
                f.write(f"<tr><td>最終資產</td><td>{results['portfolio_value']:,.2f}</td></tr>")
                f.write(f"<tr><td>年化報酬率</td><td>{results['annual_return']:.4f}</td></tr>")
                f.write(f"<tr><td>夏普比率</td><td>{results['sharpe']:.4f}</td></tr>")
                f.write(f"<tr><td>最大回撤</td><td>{results['max_drawdown']:.4f}</td></tr>")
                f.write(f"<tr><td>勝率</td><td>{results['win_rate']:.4f}</td></tr>")
                f.write(f"<tr><td>平均獲利</td><td>{results['avg_win']:.4f}</td></tr>")
                f.write(f"<tr><td>平均虧損</td><td>{results['avg_loss']:.4f}</td></tr>")
                f.write(f"<tr><td>獲利因子</td><td>{results['profit_factor']:.4f}</td></tr>")
                f.write(f"<tr><td>SQN分數</td><td>{results['sqn']:.4f}</td></tr>")
                f.write("</table>")
                f.write("</div>")

            f.write("</body></html>")

        print(f"報告已生成: {report_file}")
        return report_file


# region: 修正引用，允許直接執行
if __name__ == "__main__":
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    # 測試代碼
    print("測試回測引擎...")

    # 生成模擬數據
    simulator = MarketDataSimulator(seed=42)
    price_data = simulator.generate_normal_market(n_stocks=5, n_days=252)

    # 生成簡單的交易訊號
    signals = pd.DataFrame(index=price_data.index)
    signals["buy_signal"] = 0
    signals["sell_signal"] = 0

    # 每 20 天買入，持有 10 天後賣出
    dates = sorted(price_data.index.get_level_values("date").unique())
    for i, date in enumerate(dates):
        if i % 20 == 0:  # 每 20 天
            for stock_id in price_data.index.get_level_values("stock_id").unique():
                if (stock_id, date) in signals.index:
                    signals.loc[(stock_id, date), "buy_signal"] = 1
        elif i % 20 == 10:  # 10 天後賣出
            for stock_id in price_data.index.get_level_values("stock_id").unique():
                if (stock_id, date) in signals.index:
                    signals.loc[(stock_id, date), "sell_signal"] = 1

    # 執行回測
    backtest = Backtest(
        start_date=dates[0],
        end_date=dates[-1],
        initial_capital=1000000,
    )
    results = backtest.run(signals)

    # 輸出結果
    print(f"最終資產: {results['final_equity']:.2f}")
    print(f"年化報酬率: {results['annual_return']*100:.2f}%")
    print(f"夏普比率: {results['sharpe_ratio']:.2f}")
    print(f"最大回撤: {results['max_drawdown']*100:.2f}%")

    # 測試多策略比較
    print("\n測試多策略比較...")
    multi_backtest = MultiStrategyBacktest(
        price_data=price_data,
        start_date=dates[0],
        end_date=dates[-1],
        initial_capital=1000000,
    )

    # 添加策略 1: 原始策略
    multi_backtest.add_strategy("原始策略", signals)

    # 添加策略 2: 帶止損的策略
    multi_backtest.add_strategy("止損策略", signals, stop_loss=0.05)

    # 添加策略 3: 帶止盈的策略
    multi_backtest.add_strategy("止盈策略", signals, take_profit=0.1)

    # 執行所有策略
    multi_backtest.run_all()

    # 輸出比較表
    print("\n策略比較表:")
    print(multi_backtest.get_comparison_table())

    # 測試壓力測試
    print("\n測試壓力測試...")
    stress_test = StressTest(
        SignalStrategy,
        price_data=price_data,
        start_date=dates[0],
        end_date=dates[-1],
        initial_capital=1000000,
    )

    # 執行所有測試
    stress_test.run_all_tests(signals=signals)

    # 輸出比較表
    print("\n情境比較表:")
    print(stress_test.get_comparison_table())
