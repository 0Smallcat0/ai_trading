# Data Ingestion Module Documentation

## Overview

The Data Ingestion Module is responsible for fetching market data from various sources, standardizing the output format, and providing a unified interface for the rest of the system. It supports multiple data sources, real-time streaming, and implements fault tolerance mechanisms.

## Key Components

### 1. Data Source Adapters

The module includes adapters for different data sources:

- **YahooFinanceAdapter**: Fetches historical price data and company information from Yahoo Finance.
- **SimulatedBrokerAdapter**: Simulates a broker API for testing and development.
- **MarketDataAdapter**: Base class for all market data adapters, providing a standardized interface.

### 2. Data Ingestion Manager

The `DataIngestionManager` class coordinates data fetching from multiple sources and implements fault tolerance mechanisms:

- **Multi-source integration**: Automatically selects the best data source based on availability and priority.
- **Automatic failover**: If a data source fails, the system automatically switches to an alternative source.
- **Rate limiting**: Prevents exceeding API rate limits and implements backoff strategies.
- **WebSocket support**: Manages WebSocket connections for real-time data with auto-reconnection.
- **Backpressure control**: Prevents memory overflow when processing high-volume data streams.

### 3. MCP Data Ingestor

The `MCPDataIngestor` class is specialized for fetching news and market information from Market Content Providers:

- **News fetching**: Retrieves market news based on keywords and time range.
- **Sentiment analysis**: Analyzes market sentiment from news content.
- **WebSocket streaming**: Supports real-time news updates via WebSocket.

### 4. Rate Limiter

The rate limiter components prevent exceeding API rate limits:

- **RateLimiter**: Basic rate limiter with fixed window or sliding window strategies.
- **AdaptiveRateLimiter**: Dynamically adjusts rate limits based on API responses.

### 5. WebSocket Client

The WebSocket client provides real-time data streaming capabilities:

- **Auto-reconnection**: Automatically reconnects if the connection is lost.
- **Backpressure control**: Manages message queue to prevent memory overflow.
- **Error handling**: Robust error handling and logging.

## Usage Examples

### Fetching Historical Data

```python
from src.core.data_ingest import DataIngestionManager

# Initialize the data ingestion manager
manager = DataIngestionManager(use_cache=True)

# Fetch historical data for a single stock
data = manager.get_historical_data(
    symbols="2330.TW",
    start_date="2023-01-01",
    end_date="2023-01-31",
    interval="1d",
)

# Fetch historical data for multiple stocks
data = manager.get_historical_data(
    symbols=["2330.TW", "2317.TW"],
    start_date="2023-01-01",
    end_date="2023-01-31",
    interval="1d",
)
```

### Getting Real-time Quotes

```python
from src.core.data_ingest import DataIngestionManager

# Initialize the data ingestion manager
manager = DataIngestionManager()

# Get real-time quotes for a single stock
quote = manager.get_quote("2330.TW")

# Get real-time quotes for multiple stocks
quotes = manager.get_quote(["2330.TW", "2317.TW"])
```

### Connecting to WebSocket for Real-time Updates

```python
from src.core.data_ingest import DataIngestionManager

# Initialize the data ingestion manager
manager = DataIngestionManager()

# Define a callback function for WebSocket messages
def on_message(message):
    print(f"Received message: {message}")

# Connect to WebSocket for real-time updates
manager.connect_websocket(
    symbols=["2330.TW", "2317.TW"],
    on_message=on_message,
)

# Disconnect from WebSocket
manager.disconnect_websocket(symbols=["2330.TW", "2317.TW"])
```

### Fetching Market News

```python
from src.core.mcp_data_ingest import MCPDataIngestor

# Initialize the MCP data ingestor
ingestor = MCPDataIngestor(use_cache=True)

# Fetch market news
news = ingestor.fetch_market_news(
    query="台積電",
    days=7,
    fulltext=True,
)

# Analyze market sentiment
from src.core.mcp_data_ingest import analyze_market_sentiment

sentiment = analyze_market_sentiment(news)
print(f"Sentiment: {sentiment['sentiment']}, Score: {sentiment['score']}")
```

## Architecture

The Data Ingestion Module follows a layered architecture:

1. **Adapter Layer**: Interfaces with external data sources.
2. **Manager Layer**: Coordinates data fetching and implements fault tolerance.
3. **Utility Layer**: Provides supporting functionality like rate limiting and WebSocket management.

### Data Flow

1. The application requests data through the `DataIngestionManager` or `MCPDataIngestor`.
2. The manager selects the appropriate adapter based on availability and priority.
3. The adapter fetches data from the external source.
4. The data is standardized and returned to the application.

### Fault Tolerance

The module implements several fault tolerance mechanisms:

- **Automatic failover**: If a data source fails, the system automatically switches to an alternative source.
- **Rate limiting**: Prevents exceeding API rate limits and implements backoff strategies.
- **Auto-reconnection**: WebSocket connections automatically reconnect if lost.
- **Error handling**: Comprehensive error handling and logging.

## Configuration

The module can be configured through the following parameters:

- **use_cache**: Whether to use cache for data fetching.
- **cache_expiry_days**: Number of days before cache expires.
- **max_workers**: Maximum number of worker threads for parallel data fetching.
- **rate_limit_max_calls**: Maximum number of API calls allowed in the rate limit period.
- **rate_limit_period**: Rate limit period in seconds.

## Testing

The module includes comprehensive tests:

- **Unit tests**: Test individual components in isolation.
- **Integration tests**: Test the interaction between components.
- **Mock tests**: Test with mock data sources to avoid hitting real APIs.

Run the tests with:

```bash
poetry run pytest tests/test_data_ingest.py
```

## Future Improvements

- Add support for more data sources (e.g., Alpha Vantage, Finnhub).
- Implement data compression for large datasets.
- Add support for more complex WebSocket protocols.
- Enhance the adaptive rate limiter with machine learning.
- Implement distributed data fetching for very large datasets.
