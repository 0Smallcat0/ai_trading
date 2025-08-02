"""
Test script for integration between components (Sections 3.1-3.4)
"""

import os
import sys
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def create_test_data():
    """Create test data for integration testing"""
    # Create date range
    dates = pd.date_range(start="2020-01-01", end="2022-12-31", freq="D")

    # Create stock symbols
    symbols = ["AAPL", "MSFT"]

    # Create multi-index
    index = pd.MultiIndex.from_product([symbols, dates], names=["symbol", "date"])

    # Create random price data
    np.random.seed(42)

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
            data.append(
                {
                    "symbol": symbol,
                    "date": date,
                    "open": price * (1 + np.random.normal(0, 0.005)),
                    "high": price * (1 + np.random.normal(0.005, 0.005)),
                    "low": price * (1 + np.random.normal(-0.005, 0.005)),
                    "close": price * (1 + np.random.normal(0, 0.005)),
                    "volume": np.random.randint(1000000, 10000000),
                }
            )

    # Create DataFrame
    df = pd.DataFrame(data)
    df.set_index(["symbol", "date"], inplace=True)

    return df


def test_feature_engineering():
    """Test feature engineering functionality"""
    print("\nTesting feature engineering...")

    try:
        from src.core.features import RollingWindowFeatureGenerator, DataCleaner

        # Create test data
        df = create_test_data()

        # Create RollingWindowFeatureGenerator
        feature_generator = RollingWindowFeatureGenerator(window_sizes=[5, 10, 20])

        # Generate features
        features = feature_generator.generate(df)

        # Create DataCleaner
        data_cleaner = DataCleaner()

        # Clean data
        cleaned_data, outliers = data_cleaner.clean_data(df)

        # Print results
        print(f"Generated {len(features.columns)} features")
        print(f"Feature columns: {list(features.columns)[:5]}...")
        print(f"Cleaned data shape: {cleaned_data.shape}")
        print(f"Detected {outliers.sum().sum()} outliers")

        return features, cleaned_data
    except ImportError as e:
        print(f"Error importing feature engineering modules: {e}")
        return None, None


def test_rule_based_models():
    """Test rule-based models"""
    print("\nTesting rule-based models...")

    try:
        from src.models.rule_based_models import (
            RuleBasedModel,
            moving_average_crossover,
        )

        # Create test data
        df = create_test_data()

        # Create RuleBasedModel
        model = RuleBasedModel(
            name="ma_cross",
            rule_func=moving_average_crossover,
            rule_params={"short_window": 5, "long_window": 20},
        )

        # Generate signals
        signals = model.predict(df)

        # Print results
        print(f"Generated {len(signals)} signals")
        print(f"Signal values: {np.unique(signals)}")
        print(f"Signal counts: {pd.Series(signals).value_counts()}")

        return model, signals
    except ImportError as e:
        print(f"Error importing rule-based models: {e}")
        return None, None


def test_backtest_integration():
    """Test backtest integration"""
    print("\nTesting backtest integration...")

    try:
        from src.backtest.backtrader_integration import (
            BacktestEngine,
            ModelSignalStrategy,
        )
        from src.models.rule_based_models import (
            RuleBasedModel,
            moving_average_crossover,
        )

        # Create test data
        df = create_test_data()

        # Create RuleBasedModel
        model = RuleBasedModel(
            name="ma_cross",
            rule_func=moving_average_crossover,
            rule_params={"short_window": 5, "long_window": 20},
        )

        # Create BacktestEngine
        engine = BacktestEngine(cash=100000.0, commission=0.001, slippage=0.001)

        # Add data
        for symbol in df.index.get_level_values(0).unique():
            symbol_data = df.loc[symbol].copy()
            symbol_data.reset_index(inplace=True)
            engine.add_data(data=symbol_data, name=symbol)

        # Add strategy
        engine.add_strategy(ModelSignalStrategy, model=model, verbose=True)

        # Run backtest
        results = engine.run()

        # Print results
        print(f"Initial cash: ${results['initial_cash']:.2f}")
        print(f"Final value: ${results['final_value']:.2f}")
        print(f"Total return: {results['total_return']:.2%}")
        print(f"Sharpe ratio: {results['sharpe_ratio']:.2f}")
        print(f"Max drawdown: {results['max_drawdown']:.2%}")
        print(f"Number of trades: {results['trades']['total']}")
        print(f"Win rate: {results['trades']['win_rate']:.2%}")

        return engine, results
    except ImportError as e:
        print(f"Error importing backtest integration modules: {e}")
        return None, None


def test_signal_generation():
    """Test signal generation"""
    print("\nTesting signal generation...")

    try:
        from src.core.signal_gen import SignalGenerator

        # Create test data
        df = create_test_data()

        # Create SignalGenerator
        signal_generator = SignalGenerator(price_data=df)

        # Generate momentum signals
        momentum_signals = signal_generator.generate_momentum()

        # Generate mean reversion signals
        reversion_signals = signal_generator.generate_reversion()

        # Combine signals
        combined_signals = signal_generator.combine_signals(
            weights={"momentum": 0.6, "reversion": 0.4}
        )

        # Print results
        print(f"Generated {len(momentum_signals)} momentum signals")
        print(f"Generated {len(reversion_signals)} mean reversion signals")
        print(f"Generated {len(combined_signals)} combined signals")

        return signal_generator, combined_signals
    except ImportError as e:
        print(f"Error importing signal generation modules: {e}")
        return None, None


if __name__ == "__main__":
    print("Testing Integration Between Components (Sections 3.1-3.4)")

    # Test feature engineering
    features, cleaned_data = test_feature_engineering()

    # Test rule-based models
    model, signals = test_rule_based_models()

    # Test backtest integration
    engine, results = test_backtest_integration()

    # Test signal generation
    signal_generator, combined_signals = test_signal_generation()

    print("\nAll tests completed!")
