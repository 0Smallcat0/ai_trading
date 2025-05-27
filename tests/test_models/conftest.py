# -*- coding: utf-8 -*-
"""
Test configuration and fixtures for models tests
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


@pytest.fixture(scope="session")
def sample_stock_data():
    """Create sample stock data for testing"""
    # Create date range
    dates = pd.date_range(start="2020-01-01", end="2020-12-31", freq="D")
    
    # Create random price data
    np.random.seed(42)
    n_days = len(dates)
    
    # Generate realistic stock price data
    initial_price = 100.0
    returns = np.random.normal(0.001, 0.02, n_days)  # Daily returns
    prices = [initial_price]
    
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))
    
    # Create OHLCV data
    df = pd.DataFrame({
        "date": dates,
        "open": prices,
        "high": [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        "low": [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        "close": prices,
        "volume": np.random.randint(1000000, 10000000, n_days),
        "adj_close": prices
    })
    
    # Set date as index
    df.set_index("date", inplace=True)
    
    # Add technical indicators
    df["returns"] = df["close"].pct_change()
    df["sma_5"] = df["close"].rolling(window=5).mean()
    df["sma_20"] = df["close"].rolling(window=20).mean()
    
    return df


@pytest.fixture(scope="session") 
def multi_symbol_data():
    """Create multi-symbol stock data for testing"""
    # Create date range
    dates = pd.date_range(start="2020-01-01", end="2022-12-31", freq="D")
    symbols = ["AAPL", "MSFT"]
    
    # Create multi-index
    index = pd.MultiIndex.from_product([symbols, dates], names=["symbol", "date"])
    
    # Create random price data
    np.random.seed(42)
    n_rows = len(index)
    
    # Generate realistic stock price data
    initial_prices = {"AAPL": 100.0, "MSFT": 150.0}
    
    data = []
    for symbol in symbols:
        symbol_dates = dates
        n_days = len(symbol_dates)
        
        # Generate returns for this symbol
        returns = np.random.normal(0.001, 0.02, n_days)
        prices = [initial_prices[symbol]]
        
        for ret in returns[1:]:
            prices.append(prices[-1] * (1 + ret))
        
        # Create OHLCV data for this symbol
        for i, date in enumerate(symbol_dates):
            price = prices[i]
            data.append({
                "symbol": symbol,
                "date": date,
                "open": price * (1 + np.random.normal(0, 0.005)),
                "high": price * (1 + abs(np.random.normal(0, 0.01))),
                "low": price * (1 - abs(np.random.normal(0, 0.01))),
                "close": price,
                "volume": np.random.randint(1000000, 10000000),
                "adj_close": price
            })
    
    df = pd.DataFrame(data)
    df.set_index(["symbol", "date"], inplace=True)
    
    return df


@pytest.fixture
def df(sample_stock_data):
    """Alias for sample_stock_data for backward compatibility"""
    return sample_stock_data


@pytest.fixture
def train_val_test_split(multi_symbol_data):
    """Create train/validation/test split"""
    # Sort by date
    df = multi_symbol_data.sort_index(level="date")
    
    # Get unique dates
    dates = df.index.get_level_values("date").unique().sort_values()
    
    # Split dates
    n_dates = len(dates)
    train_end_idx = int(n_dates * 0.6)
    val_end_idx = int(n_dates * 0.8)
    
    train_dates = dates[:train_end_idx]
    val_dates = dates[train_end_idx:val_end_idx]
    test_dates = dates[val_end_idx:]
    
    # Filter data by date ranges
    train = df[df.index.get_level_values("date").isin(train_dates)]
    val = df[df.index.get_level_values("date").isin(val_dates)]
    test = df[df.index.get_level_values("date").isin(test_dates)]
    
    return train, val, test


@pytest.fixture
def train(train_val_test_split):
    """Training data fixture"""
    train_data, _, _ = train_val_test_split
    return train_data


@pytest.fixture
def val(train_val_test_split):
    """Validation data fixture"""
    _, val_data, _ = train_val_test_split
    return val_data


@pytest.fixture
def test(train_val_test_split):
    """Test data fixture"""
    _, _, test_data = train_val_test_split
    return test_data


@pytest.fixture
def mock_model():
    """Create a mock model for testing"""
    from unittest.mock import Mock
    
    model = Mock()
    model.name = "test_model"
    model.trained = True
    model.feature_names = ["feature_1", "feature_2", "feature_3"]
    model.target_name = "target"
    model.predict.return_value = np.random.random(100)
    model.feature_importance.return_value = pd.DataFrame({
        "feature": ["feature_1", "feature_2", "feature_3"],
        "importance": [0.5, 0.3, 0.2]
    })
    
    return model


@pytest.fixture
def sample_features():
    """Create sample feature data"""
    np.random.seed(42)
    n_samples = 1000
    
    features = pd.DataFrame({
        "feature_1": np.random.normal(0, 1, n_samples),
        "feature_2": np.random.normal(0, 1, n_samples),
        "feature_3": np.random.normal(0, 1, n_samples),
        "feature_4": np.random.normal(0, 1, n_samples),
        "feature_5": np.random.normal(0, 1, n_samples),
    })
    
    # Create target variable
    target = (features["feature_1"] * 0.5 + 
              features["feature_2"] * 0.3 + 
              np.random.normal(0, 0.1, n_samples))
    
    return features, target


@pytest.fixture
def sample_returns():
    """Create sample return data for testing"""
    np.random.seed(42)
    n_samples = 252  # One year of daily returns
    
    returns = pd.Series(
        np.random.normal(0.001, 0.02, n_samples),
        index=pd.date_range(start="2020-01-01", periods=n_samples, freq="D"),
        name="returns"
    )
    
    return returns


@pytest.fixture(scope="session")
def test_config():
    """Test configuration"""
    return {
        "random_seed": 42,
        "test_size": 0.2,
        "validation_size": 0.2,
        "n_samples": 1000,
        "n_features": 5,
        "noise_level": 0.1
    }


# Configure pytest to ignore warnings
def pytest_configure(config):
    """Configure pytest settings"""
    config.addinivalue_line(
        "filterwarnings", "ignore::DeprecationWarning"
    )
    config.addinivalue_line(
        "filterwarnings", "ignore::FutureWarning"
    )
    config.addinivalue_line(
        "filterwarnings", "ignore::UserWarning"
    )


# Pytest collection configuration
def pytest_collection_modifyitems(config, items):
    """Modify test collection"""
    # Add markers for slow tests
    for item in items:
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.slow)
        if "tensorflow" in item.nodeid or "keras" in item.nodeid:
            item.add_marker(pytest.mark.tensorflow)
