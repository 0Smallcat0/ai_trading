"""
Test script for strategy research module (Section 3.1)
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from src.models.strategy_research import StrategyResearcher
    from src.models.dataset import TimeSeriesSplit, FeatureProcessor, DatasetLoader
    print("Successfully imported strategy research modules")
except ImportError as e:
    print(f"Error importing strategy research modules: {e}")
    sys.exit(1)

def create_test_data():
    """Create test data for strategy research"""
    # Create date range
    dates = pd.date_range(start="2020-01-01", end="2022-12-31", freq="D")
    
    # Create stock symbols
    symbols = ["AAPL", "MSFT"]
    
    # Create multi-index
    index = pd.MultiIndex.from_product([symbols, dates], names=["symbol", "date"])
    
    # Create random price data
    np.random.seed(42)
    n = len(index)
    
    # Generate price data with a trend
    base_price = 100
    trend = np.cumsum(np.random.normal(0.001, 0.01, len(dates)))
    
    # Create price DataFrame
    data = []
    for symbol in symbols:
        symbol_trend = trend + np.random.normal(0, 0.1, len(trend))
        prices = base_price * (1 + symbol_trend)
        
        for i, date in enumerate(dates):
            price = prices[i]
            data.append({
                "symbol": symbol,
                "date": date,
                "open": price * (1 + np.random.normal(0, 0.005)),
                "high": price * (1 + np.random.normal(0.005, 0.005)),
                "low": price * (1 + np.random.normal(-0.005, 0.005)),
                "close": price * (1 + np.random.normal(0, 0.005)),
                "volume": np.random.randint(1000000, 10000000),
                "adj_close": price * (1 + np.random.normal(0, 0.005))
            })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    df.set_index(["symbol", "date"], inplace=True)
    
    return df

def test_time_series_split():
    """Test TimeSeriesSplit functionality"""
    print("\nTesting TimeSeriesSplit...")
    
    # Create test data
    df = create_test_data()
    
    # Create TimeSeriesSplit
    splitter = TimeSeriesSplit()
    
    # Split data
    train, val, test = splitter.split(df)
    
    # Check split sizes
    print(f"Train size: {len(train)}")
    print(f"Validation size: {len(val)}")
    print(f"Test size: {len(test)}")
    
    # Check date ranges
    print(f"Train date range: {train.index.get_level_values('date').min()} to {train.index.get_level_values('date').max()}")
    print(f"Validation date range: {val.index.get_level_values('date').min()} to {val.index.get_level_values('date').max()}")
    print(f"Test date range: {test.index.get_level_values('date').min()} to {test.index.get_level_values('date').max()}")
    
    return train, val, test

def test_feature_processor(train, val, test):
    """Test FeatureProcessor functionality"""
    print("\nTesting FeatureProcessor...")
    
    # Create FeatureProcessor
    processor = FeatureProcessor()
    
    # Fit and transform train data
    train_scaled = processor.fit_transform(train)
    
    # Transform validation and test data
    val_scaled = processor.transform(val)
    test_scaled = processor.transform(test)
    
    # Check scaled data
    print(f"Train scaled shape: {train_scaled.shape}")
    print(f"Validation scaled shape: {val_scaled.shape}")
    print(f"Test scaled shape: {test_scaled.shape}")
    
    # Check column names
    print(f"Columns: {train_scaled.columns[:5]}...")
    
    return train_scaled, val_scaled, test_scaled

def test_dataset_loader():
    """Test DatasetLoader functionality"""
    print("\nTesting DatasetLoader...")
    
    try:
        # Create DatasetLoader
        loader = DatasetLoader()
        
        # Create test data
        df = create_test_data()
        
        # Load data
        loader.load_from_dataframe(df)
        
        # Prepare features
        features = loader.prepare_features(target_type="direction", target_horizon=5)
        
        # Check features
        print(f"Features shape: {features.shape}")
        print(f"Features columns: {features.columns[:5]}...")
        
        # Check if target is created
        if "target" in features.columns:
            print(f"Target values: {features['target'].value_counts()}")
        
        return features
    except Exception as e:
        print(f"Error in DatasetLoader: {e}")
        return None

def test_strategy_researcher():
    """Test StrategyResearcher functionality"""
    print("\nTesting StrategyResearcher...")
    
    try:
        # Create test data
        df = create_test_data()
        
        # Create StrategyResearcher
        researcher = StrategyResearcher()
        
        # Set data
        researcher.set_data(df)
        
        # Evaluate trend following strategies
        trend_results = researcher.evaluate_trend_following_strategies()
        print(f"Trend following results: {trend_results.keys()}")
        
        # Evaluate mean reversion strategies
        reversion_results = researcher.evaluate_mean_reversion_strategies()
        print(f"Mean reversion results: {reversion_results.keys()}")
        
        # Get best strategy
        best_strategy = researcher.get_best_strategy()
        print(f"Best strategy: {best_strategy}")
        
        return researcher
    except Exception as e:
        print(f"Error in StrategyResearcher: {e}")
        return None

if __name__ == "__main__":
    print("Testing Strategy Research Module (Section 3.1)")
    
    # Test TimeSeriesSplit
    train, val, test = test_time_series_split()
    
    # Test FeatureProcessor
    train_scaled, val_scaled, test_scaled = test_feature_processor(train, val, test)
    
    # Test DatasetLoader
    features = test_dataset_loader()
    
    # Test StrategyResearcher
    researcher = test_strategy_researcher()
    
    print("\nAll tests completed!")
