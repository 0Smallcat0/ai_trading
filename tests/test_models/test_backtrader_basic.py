"""
Basic test script for backtrader
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import backtrader as bt

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
    df = pd.DataFrame({
        "open": prices * (1 + np.random.normal(0, 0.005, n)),
        "high": prices * (1 + np.random.normal(0.005, 0.005, n)),
        "low": prices * (1 + np.random.normal(-0.005, 0.005, n)),
        "close": prices * (1 + np.random.normal(0, 0.005, n)),
        "volume": np.random.randint(1000000, 10000000, n)
    }, index=dates)
    
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

def test_backtrader():
    """Test backtrader"""
    print("\nTesting backtrader...")
    
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
    
    # Print final value
    print(f"Final value: {cerebro.broker.getvalue():.2f}")
    
    return cerebro

if __name__ == "__main__":
    print("Testing Backtrader Basic Functionality")
    
    # Test backtrader
    cerebro = test_backtrader()
    
    print("\nAll tests completed!")
