"""
Test script for rule-based models (Section 3.3)
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from src.models.rule_based_models import RuleBasedModel, moving_average_crossover, rsi_strategy, bollinger_bands_strategy
    print("Successfully imported rule-based models")
except ImportError as e:
    print(f"Error importing rule-based models: {e}")
    sys.exit(1)

def create_test_data():
    """Create test data for rule-based models"""
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
    
    # Ensure high >= open >= close >= low
    for i in range(n):
        high = max(df.iloc[i]["open"], df.iloc[i]["close"]) + abs(np.random.normal(5, 1))
        low = min(df.iloc[i]["open"], df.iloc[i]["close"]) - abs(np.random.normal(5, 1))
        df.iloc[i, df.columns.get_loc("high")] = high
        df.iloc[i, df.columns.get_loc("low")] = low
    
    return df

def test_moving_average_crossover():
    """Test moving_average_crossover function"""
    print("\nTesting moving_average_crossover...")
    
    # Create test data
    df = create_test_data()
    
    # Test with different parameters
    params = {"short_window": 5, "long_window": 20}
    signals = moving_average_crossover(df, **params)
    
    # Check signals
    print(f"Generated {len(signals)} signals")
    print(f"Signal values: {np.unique(signals)}")
    print(f"Signal counts: {pd.Series(signals).value_counts()}")
    
    return signals

def test_rsi_strategy():
    """Test rsi_strategy function"""
    print("\nTesting rsi_strategy...")
    
    # Create test data
    df = create_test_data()
    
    # Test with different parameters
    params = {"window": 14, "overbought": 70, "oversold": 30}
    signals = rsi_strategy(df, **params)
    
    # Check signals
    print(f"Generated {len(signals)} signals")
    print(f"Signal values: {np.unique(signals)}")
    print(f"Signal counts: {pd.Series(signals).value_counts()}")
    
    return signals

def test_bollinger_bands_strategy():
    """Test bollinger_bands_strategy function"""
    print("\nTesting bollinger_bands_strategy...")
    
    # Create test data
    df = create_test_data()
    
    # Test with different parameters
    params = {"window": 20, "num_std": 2.0}
    signals = bollinger_bands_strategy(df, **params)
    
    # Check signals
    print(f"Generated {len(signals)} signals")
    print(f"Signal values: {np.unique(signals)}")
    print(f"Signal counts: {pd.Series(signals).value_counts()}")
    
    return signals

def test_rule_based_model():
    """Test RuleBasedModel class"""
    print("\nTesting RuleBasedModel...")
    
    # Create test data
    df = create_test_data()
    
    # Test with moving_average_crossover
    print("Testing with moving_average_crossover...")
    model = RuleBasedModel(
        name="ma_cross",
        rule_func=moving_average_crossover,
        rule_params={"short_window": 5, "long_window": 20}
    )
    
    # Generate signals
    signals = model.predict(df)
    
    # Check signals
    print(f"Generated {len(signals)} signals")
    print(f"Signal values: {np.unique(signals)}")
    print(f"Signal counts: {pd.Series(signals).value_counts()}")
    
    # Test with rsi_strategy
    print("\nTesting with rsi_strategy...")
    model = RuleBasedModel(
        name="rsi",
        rule_func=rsi_strategy,
        rule_params={"window": 14, "overbought": 70, "oversold": 30}
    )
    
    # Generate signals
    signals = model.predict(df)
    
    # Check signals
    print(f"Generated {len(signals)} signals")
    print(f"Signal values: {np.unique(signals)}")
    print(f"Signal counts: {pd.Series(signals).value_counts()}")
    
    # Test with bollinger_bands_strategy
    print("\nTesting with bollinger_bands_strategy...")
    model = RuleBasedModel(
        name="bollinger",
        rule_func=bollinger_bands_strategy,
        rule_params={"window": 20, "num_std": 2.0}
    )
    
    # Generate signals
    signals = model.predict(df)
    
    # Check signals
    print(f"Generated {len(signals)} signals")
    print(f"Signal values: {np.unique(signals)}")
    print(f"Signal counts: {pd.Series(signals).value_counts()}")
    
    return model

if __name__ == "__main__":
    print("Testing Rule-Based Models (Section 3.3)")
    
    # Test moving_average_crossover
    ma_signals = test_moving_average_crossover()
    
    # Test rsi_strategy
    rsi_signals = test_rsi_strategy()
    
    # Test bollinger_bands_strategy
    bb_signals = test_bollinger_bands_strategy()
    
    # Test RuleBasedModel
    model = test_rule_based_model()
    
    print("\nAll tests completed!")
