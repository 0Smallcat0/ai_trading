"""
Test script for rule-based models and backtest integration without TensorFlow
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import backtrader as bt

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def create_test_data():
    """Create test data for testing"""
    # Create date range
    dates = pd.date_range(start="2020-01-01", end="2020-12-31", freq="D")

    # Create random price data
    np.random.seed(42)
    n = len(dates)

    # Generate price data with a trend
    base_price = 100
    trend = np.cumsum(np.random.normal(0.001, 0.01, n))
    prices = base_price * (1 + trend)

    # Create price DataFrame
    df = pd.DataFrame(
        {
            "open": prices * (1 + np.random.normal(0, 0.005, n)),
            "high": prices * (1 + np.random.normal(0.005, 0.005, n)),
            "low": prices * (1 + np.random.normal(-0.005, 0.005, n)),
            "close": prices * (1 + np.random.normal(0, 0.005, n)),
            "volume": np.random.randint(1000000, 10000000, n),
        },
        index=dates,
    )

    return df


class MovingAverageCrossStrategy(bt.Strategy):
    """Moving Average Crossover Strategy"""

    params = (
        ("fast", 5),
        ("slow", 20),
    )

    def __init__(self):
        """Initialize strategy"""
        self.fast_ma = bt.indicators.SMA(self.data.close, period=self.params.fast)
        self.slow_ma = bt.indicators.SMA(self.data.close, period=self.params.slow)
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)

        # Keep track of pending orders
        self.order = None

        # Keep track of trades
        self.trades = 0

    def next(self):
        """Execute strategy"""
        # Check if an order is pending
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            # Buy if fast MA crosses above slow MA
            if self.crossover > 0:
                self.order = self.buy()
                self.trades += 1
        else:
            # Sell if fast MA crosses below slow MA
            if self.crossover < 0:
                self.order = self.sell()
                self.trades += 1

    def stop(self):
        """Print results at the end of the backtest"""
        print(f"Ending value: {self.broker.getvalue():.2f}")
        print(f"Number of trades: {self.trades}")


def test_moving_average_crossover():
    """Test moving average crossover strategy"""
    print("\nTesting moving average crossover strategy...")

    # Create test data
    df = create_test_data()

    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(MovingAverageCrossStrategy)

    # Create a data feed
    data = bt.feeds.PandasData(
        dataname=df,
        datetime=None,  # Use index as datetime
        open="open",
        high="high",
        low="low",
        close="close",
        volume="volume",
        openinterest=None,
    )

    # Add the data feed to cerebro
    cerebro.adddata(data)

    # Set initial cash
    cerebro.broker.setcash(100000.0)

    # Set commission
    cerebro.broker.setcommission(commission=0.001)

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    # Print starting cash
    print(f"Starting value: {cerebro.broker.getvalue():.2f}")

    # Run backtest
    results = cerebro.run()
    strat = results[0]

    # Get analysis results
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    returns = strat.analyzers.returns.get_analysis()
    trades = strat.analyzers.trades.get_analysis()

    # Print results
    sharpe_ratio = sharpe.get("sharperatio", 0.0) if sharpe else 0.0
    max_dd = drawdown.get("max", {}).get("drawdown", 0.0) if drawdown else 0.0
    total_ret = returns.get("rtot", 0.0) if returns else 0.0
    total_trades = trades.get("total", 0) if trades else 0
    win_rate = (
        trades.get("won", 0) / trades.get("total", 1)
        if trades and trades.get("total", 0) > 0
        else 0.0
    )

    print(f"Sharpe ratio: {sharpe_ratio:.2f}")
    print(f"Max drawdown: {max_dd:.2%}")
    print(f"Total return: {total_ret:.2%}")
    print(f"Number of trades: {total_trades}")
    print(f"Win rate: {win_rate:.2%}")

    return cerebro, results


class RSIStrategy(bt.Strategy):
    """RSI Strategy"""

    params = (
        ("period", 14),
        ("overbought", 70),
        ("oversold", 30),
    )

    def __init__(self):
        """Initialize strategy"""
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.period)

        # Keep track of pending orders
        self.order = None

        # Keep track of trades
        self.trades = 0

    def next(self):
        """Execute strategy"""
        # Check if an order is pending
        if self.order:
            return

        # Check if we are in the market
        if not self.position:
            # Buy if RSI is below oversold threshold
            if self.rsi < self.params.oversold:
                self.order = self.buy()
                self.trades += 1
        else:
            # Sell if RSI is above overbought threshold
            if self.rsi > self.params.overbought:
                self.order = self.sell()
                self.trades += 1

    def stop(self):
        """Print results at the end of the backtest"""
        print(f"Ending value: {self.broker.getvalue():.2f}")
        print(f"Number of trades: {self.trades}")


def test_rsi_strategy():
    """Test RSI strategy"""
    print("\nTesting RSI strategy...")

    # Create test data
    df = create_test_data()

    # Create a cerebro entity
    cerebro = bt.Cerebro()

    # Add a strategy
    cerebro.addstrategy(RSIStrategy)

    # Create a data feed
    data = bt.feeds.PandasData(
        dataname=df,
        datetime=None,  # Use index as datetime
        open="open",
        high="high",
        low="low",
        close="close",
        volume="volume",
        openinterest=None,
    )

    # Add the data feed to cerebro
    cerebro.adddata(data)

    # Set initial cash
    cerebro.broker.setcash(100000.0)

    # Set commission
    cerebro.broker.setcommission(commission=0.001)

    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
    cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

    # Print starting cash
    print(f"Starting value: {cerebro.broker.getvalue():.2f}")

    # Run backtest
    results = cerebro.run()
    strat = results[0]

    # Get analysis results
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    returns = strat.analyzers.returns.get_analysis()
    trades = strat.analyzers.trades.get_analysis()

    # Print results
    sharpe_ratio = sharpe.get("sharperatio", 0.0) if sharpe else 0.0
    max_dd = drawdown.get("max", {}).get("drawdown", 0.0) if drawdown else 0.0
    total_ret = returns.get("rtot", 0.0) if returns else 0.0
    total_trades = trades.get("total", 0) if trades else 0
    win_rate = (
        trades.get("won", 0) / trades.get("total", 1)
        if trades and trades.get("total", 0) > 0
        else 0.0
    )

    print(f"Sharpe ratio: {sharpe_ratio:.2f}")
    print(f"Max drawdown: {max_dd:.2%}")
    print(f"Total return: {total_ret:.2%}")
    print(f"Number of trades: {total_trades}")
    print(f"Win rate: {win_rate:.2%}")

    return cerebro, results


if __name__ == "__main__":
    print("Testing Rule-Based Models and Backtest Integration Without TensorFlow")

    # Test moving average crossover strategy
    ma_cerebro, ma_results = test_moving_average_crossover()

    # Test RSI strategy
    rsi_cerebro, rsi_results = test_rsi_strategy()

    print("\nAll tests completed!")
