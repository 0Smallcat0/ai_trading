"""
Basic test script to verify functionality without importing project modules
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import talib
import backtrader as bt
from datetime import datetime, timedelta

def test_pandas():
    """Test pandas functionality"""
    print("\nTesting pandas...")
    
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
    df = pd.DataFrame({
        "open": prices * (1 + np.random.normal(0, 0.005, n)),
        "high": prices * (1 + np.random.normal(0.005, 0.005, n)),
        "low": prices * (1 + np.random.normal(-0.005, 0.005, n)),
        "close": prices * (1 + np.random.normal(0, 0.005, n)),
        "volume": np.random.randint(1000000, 10000000, n)
    }, index=dates)
    
    # Print DataFrame info
    print(f"DataFrame shape: {df.shape}")
    print(f"DataFrame columns: {df.columns.tolist()}")
    print(f"DataFrame index: {df.index[0]} to {df.index[-1]}")
    
    # Calculate returns
    df["returns"] = df["close"].pct_change()
    
    # Calculate moving averages
    df["sma_5"] = df["close"].rolling(window=5).mean()
    df["sma_20"] = df["close"].rolling(window=20).mean()
    
    # Print statistics
    print(f"Mean return: {df['returns'].mean():.4f}")
    print(f"Std return: {df['returns'].std():.4f}")
    
    return df

def test_talib(df):
    """Test TA-Lib functionality"""
    print("\nTesting TA-Lib...")
    
    # Calculate RSI
    df["rsi"] = talib.RSI(df["close"].values, timeperiod=14)
    
    # Calculate MACD
    macd, macd_signal, macd_hist = talib.MACD(
        df["close"].values, 
        fastperiod=12, 
        slowperiod=26, 
        signalperiod=9
    )
    df["macd"] = macd
    df["macd_signal"] = macd_signal
    df["macd_hist"] = macd_hist
    
    # Calculate Bollinger Bands
    upper, middle, lower = talib.BBANDS(
        df["close"].values,
        timeperiod=20,
        nbdevup=2,
        nbdevdn=2,
        matype=0
    )
    df["bb_upper"] = upper
    df["bb_middle"] = middle
    df["bb_lower"] = lower
    
    # Print statistics
    print(f"RSI mean: {df['rsi'].mean():.2f}")
    print(f"MACD mean: {df['macd'].mean():.4f}")
    print(f"BB width mean: {(df['bb_upper'] - df['bb_lower']).mean():.4f}")
    
    return df

class MAStrategy(bt.Strategy):
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

def test_backtrader(df):
    """Test backtrader functionality"""
    print("\nTesting backtrader...")
    
    # Create a cerebro entity
    cerebro = bt.Cerebro()
    
    # Add a strategy
    cerebro.addstrategy(MAStrategy)
    
    # Create a data feed
    data = bt.feeds.PandasData(
        dataname=df,
        datetime=None,  # Use index as datetime
        open="open",
        high="high",
        low="low",
        close="close",
        volume="volume",
        openinterest=None
    )
    
    # Add the data feed to cerebro
    cerebro.adddata(data)
    
    # Set initial cash
    cerebro.broker.setcash(100000.0)
    
    # Set commission
    cerebro.broker.setcommission(commission=0.001)
    
    # Print starting cash
    print(f"Starting value: {cerebro.broker.getvalue():.2f}")
    
    # Run backtest
    cerebro.run()
    
    return cerebro

if __name__ == "__main__":
    print("Testing Basic Functionality")
    
    # Test pandas
    df = test_pandas()
    
    # Test TA-Lib
    df = test_talib(df)
    
    # Test backtrader
    cerebro = test_backtrader(df)
    
    print("\nAll tests completed!")
