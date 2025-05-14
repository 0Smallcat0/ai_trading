# Core Modules Documentation

This document provides detailed information about the core modules of the AI trading system, focusing on the modules implemented in items 2.1-2.10 of the Todo list.

## 1. Signal Generation Module (`src/core/signal_gen.py`)

The signal generation module is responsible for generating trading signals based on various strategies and indicators.

### Key Features

- **Multiple Strategy Support**: Implements fundamental, momentum, mean reversion, and news sentiment strategies
- **Signal Combination**: Combines signals from multiple strategies with customizable weights
- **Technical Indicator Integration**: Integrates with technical indicators from the features module
- **Signal Statistics**: Provides statistics and visualization of generated signals
- **Signal Filtering**: Filters signals based on various criteria to reduce noise
- **Time Series Analysis**: Analyzes signal patterns over time to identify trends

### Usage Example

```python
from src.core.signal_gen import generate_signals, combine_signals

# Generate signals from different strategies
momentum_signals = generate_signals(data, strategy='momentum')
mean_reversion_signals = generate_signals(data, strategy='mean_reversion')
fundamental_signals = generate_signals(data, strategy='fundamental')

# Combine signals with custom weights
combined_signals = combine_signals({
    'momentum': momentum_signals,
    'mean_reversion': mean_reversion_signals,
    'fundamental': fundamental_signals
}, weights={'momentum': 0.4, 'mean_reversion': 0.3, 'fundamental': 0.3})
```

## 2. Backtesting Module (`src/core/backtest.py`)

The backtesting module simulates trading strategies on historical data to evaluate their performance.

### Key Features

- **Strategy Execution Loop**: Tracks portfolio value, positions, and cash throughout the simulation
- **Market Data Simulation**: Simulates various market scenarios including crashes, liquidity crises, and high volatility
- **Performance Metrics**: Calculates key metrics such as returns, Sharpe ratio, drawdown, win rate, and profit/loss ratio
- **Multi-Strategy Comparison**: Supports comparing multiple strategies side by side
- **Backtrader Integration**: Integrates with the Backtrader framework for advanced backtesting capabilities
- **Hybrid Backtesting**: Supports news sentiment factor injection and other hybrid approaches
- **Visualization**: Provides visualization of backtest results including equity curves and drawdowns

### Usage Example

```python
from src.core.backtest import Backtest, run_backtest

# Create a backtest instance
backtest = Backtest(
    start_date='2022-01-01',
    end_date='2022-12-31',
    initial_capital=1000000,
    transaction_cost=0.001425,
    slippage=0.001,
    tax=0.003
)

# Run the backtest with signals
results = backtest.run(signals)

# Get performance metrics
metrics = backtest.get_performance_metrics()
print(f"Annual Return: {metrics['annual_return']:.2%}")
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")

# Plot results
fig = backtest.plot_results()
```

## 3. Portfolio Management Module (`src/core/portfolio.py`)

The portfolio management module handles asset allocation and position management based on trading signals and risk preferences.

### Key Features

- **Asset Allocation**: Implements various allocation methods including equal weight, mean-variance, risk parity, max Sharpe, and min variance
- **Position Management**: Tracks and manages positions over time
- **Portfolio Optimization**: Optimizes portfolios based on different objectives and constraints
- **Performance Evaluation**: Evaluates portfolio performance using various metrics
- **Rebalancing**: Handles portfolio rebalancing at different frequencies
- **Multi-Strategy Integration**: Integrates multiple strategies into a single portfolio

### Usage Example

```python
from src.core.portfolio import Portfolio, optimize_portfolio

# Create a portfolio instance
portfolio = Portfolio(
    initial_capital=1000000,
    allocation_method='risk_parity',
    rebalance_frequency='monthly'
)

# Update portfolio with signals
portfolio.update(signals, prices)

# Get portfolio state
state = portfolio.get_state()
print(f"Portfolio Value: {state['total_value']}")
print(f"Cash: {state['cash']}")
print(f"Positions: {state['positions']}")

# Optimize portfolio
optimized_weights = optimize_portfolio(
    returns, 
    method='max_sharpe', 
    risk_free_rate=0.02
)
```

## 4. Risk Control Module (`src/core/risk_control.py`)

The risk control module manages trading risk using various risk control strategies and metrics.

### Key Features

- **Stop-Loss and Take-Profit**: Implements various stop-loss and take-profit strategies
- **Position Sizing**: Determines position sizes based on risk parameters
- **Risk Metrics**: Calculates risk metrics such as Value at Risk (VaR), Conditional Value at Risk (CVaR), and volatility
- **Drawdown Monitoring**: Monitors drawdowns and implements circuit breakers
- **Risk Diversification**: Ensures proper diversification across assets
- **Signal Filtering**: Filters trading signals based on risk parameters
- **Dynamic Risk Adjustment**: Adjusts risk parameters based on market conditions
- **Extreme Scenario Testing**: Tests strategies under extreme market conditions

### Usage Example

```python
from src.core.risk_control import RiskController, calculate_var

# Create a risk controller instance
risk_controller = RiskController(
    max_position_size=0.05,
    max_portfolio_var=0.02,
    stop_loss_pct=0.05,
    take_profit_pct=0.1
)

# Apply risk control to signals
filtered_signals = risk_controller.filter_signals(signals, portfolio)

# Calculate Value at Risk
var = calculate_var(returns, confidence_level=0.95, method='historical')
print(f"95% VaR: {var:.2%}")

# Check if a trade is within risk limits
is_allowed = risk_controller.check_trade(
    stock_id='2330',
    quantity=1000,
    price=500,
    portfolio=portfolio
)
```

## 5. Data Collection Module (`src/core/data_ingest.py`)

The data collection module is responsible for gathering stock data from various sources and preprocessing it for use in the trading system.

### Key Features

- **Multi-Source Integration**: Collects data from Yahoo Finance, Alpha Vantage, FinMind, and broker APIs
- **Data Type Support**: Handles price, volume, financial statements, and technical indicators
- **WebSocket Support**: Implements WebSocket auto-reconnection and backpressure control
- **Rate Limiting**: Provides request rate limiting to avoid API throttling
- **Failover Mechanism**: Automatically switches to backup data sources when primary sources fail
- **Data Standardization**: Standardizes data formats across different sources
- **Scheduled Updates**: Supports scheduled data updates
- **Data Validation**: Validates data for completeness and accuracy

### Usage Example

```python
from src.core.data_ingest import DataIngestionManager, load_data, update_data

# Create a data ingestion manager
manager = DataIngestionManager(
    use_cache=True,
    cache_expiry_days=1,
    max_workers=5
)

# Get historical data
historical_data = manager.get_historical_data(
    symbols=['2330', '2317'],
    start_date='2022-01-01',
    end_date='2022-12-31',
    interval='1d'
)

# Get real-time quotes
quotes = manager.get_quote(['2330', '2317'])

# Load data from cache
data_dict = load_data(
    start_date='2022-01-01',
    end_date='2022-12-31',
    data_types=['price', 'bargin', 'pe']
)

# Update data
updated_data = update_data(
    start_date='2023-01-01',
    end_date='2023-01-31',
    data_types=['price', 'bargin']
)
```

## 6. Feature Engineering Module (`src/core/features.py`)

The feature engineering module calculates technical and fundamental indicators and performs data preprocessing for the trading system.

### Key Features

- **Technical Indicators**: Calculates various technical indicators such as RSI, MACD, Bollinger Bands, etc.
- **Fundamental Indicators**: Calculates fundamental indicators such as ROE, ROA, EPS, etc.
- **Data Cleaning**: Handles missing values, outliers, and data normalization
- **Feature Selection**: Selects the most relevant features for trading strategies
- **Dimensionality Reduction**: Reduces feature dimensionality using PCA and other methods
- **Distributed Processing**: Supports distributed processing using Dask and Ray
- **Feature Importance**: Calculates and visualizes feature importance
- **Feature Store**: Stores and versions features for reproducibility

### Usage Example

```python
from src.core.features import FeatureCalculator, compute_features

# Create a feature calculator
calculator = FeatureCalculator(data_dict)

# Calculate technical indicators
tech_indicators = calculator.calculate_technical_indicators(
    stock_id='2330',
    indicators=['RSI', 'MACD', 'BBANDS'],
    multipliers=[0.5, 1, 2]
)

# Calculate fundamental indicators
fund_indicators = calculator.calculate_fundamental_indicators()

# Calculate custom features
custom_features = calculator.calculate_custom_features()

# Combine all features
all_features = calculator.combine_features()

# Normalize features
scaler, normalized_features = calculator.normalize_features(
    all_features,
    method='standard'
)

# Select features
selected_features, selector = calculator.select_features(
    normalized_features,
    method='f_regression',
    k=10
)

# Calculate feature importance
importance = calculator.calculate_feature_importance(
    selected_features,
    method='random_forest'
)

# Plot feature importance
fig = calculator.plot_feature_importance(importance, top_n=10)

# Compute features with all options
features = compute_features(
    start_date='2022-01-01',
    end_date='2022-12-31',
    normalize=True,
    remove_extremes=True,
    clean_data=True,
    use_distributed=True,
    feature_selection=True,
    dimensionality_reduction=True
)
```

## Integration Between Modules

The core modules are designed to work together seamlessly:

1. **Data Flow**: 
   - `data_ingest.py` collects and preprocesses data
   - `features.py` calculates features from the data
   - `signal_gen.py` generates signals based on the features
   - `backtest.py` simulates trading based on the signals
   - `portfolio.py` manages the portfolio based on the backtest results
   - `risk_control.py` applies risk management to the portfolio

2. **Common Data Structures**:
   - All modules use pandas DataFrames with consistent index structures
   - Time series data uses MultiIndex with (stock_id, date) for easy cross-sectional and temporal analysis

3. **Configuration Sharing**:
   - Modules share configuration through the `config.py` file
   - Environment-specific settings are loaded from `.env` files

## Best Practices

When working with these modules, follow these best practices:

1. **Data Handling**:
   - Always check for missing values and outliers
   - Use the provided data cleaning functions
   - Be mindful of look-ahead bias in backtesting

2. **Performance Optimization**:
   - Use distributed processing for large datasets
   - Cache intermediate results when appropriate
   - Monitor memory usage when working with large datasets

3. **Risk Management**:
   - Always apply risk controls to trading signals
   - Test strategies under various market conditions
   - Monitor drawdowns and other risk metrics

4. **Code Organization**:
   - Follow the modular structure of the codebase
   - Write unit tests for new functionality
   - Document code with docstrings and comments
