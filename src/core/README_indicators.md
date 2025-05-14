# 交易指標模組使用指南 (Trading Indicators Module Guide)

本文檔提供了 `indicators.py` 模組的詳細說明和使用指南。該模組實現了各種交易指標，包括技術指標、基本面指標和情緒指標，並提供了標準化和比較這些指標的工具。

## 目錄

1. [模組概述](#模組概述)
2. [技術指標](#技術指標)
3. [基本面指標](#基本面指標)
4. [情緒指標](#情緒指標)
5. [指標評估與比較](#指標評估與比較)
6. [使用示例](#使用示例)
7. [常見問題](#常見問題)

## 模組概述

`indicators.py` 模組包含三個主要類別：

- `TechnicalIndicators`：實現各種技術分析指標
- `FundamentalIndicators`：實現各種基本面分析指標
- `SentimentIndicators`：實現各種情緒分析指標

此外，模組還提供了兩個實用函數：

- `evaluate_indicator_efficacy`：評估指標的有效性
- `generate_trading_signals`：根據指標生成交易訊號

## 技術指標

`TechnicalIndicators` 類實現了以下技術指標：

### 移動平均線 (Moving Averages)

- **SMA (Simple Moving Average)**：簡單移動平均線
  ```python
  sma = tech_indicators.calculate_sma(period=20, column='close')
  ```

- **EMA (Exponential Moving Average)**：指數移動平均線
  ```python
  ema = tech_indicators.calculate_ema(period=20, column='close')
  ```

### 動量指標 (Momentum Indicators)

- **MACD (Moving Average Convergence Divergence)**：移動平均收斂散度
  ```python
  macd, signal, hist = tech_indicators.calculate_macd(fast_period=12, slow_period=26, signal_period=9)
  ```

- **RSI (Relative Strength Index)**：相對強弱指標
  ```python
  rsi = tech_indicators.calculate_rsi(period=14, column='close')
  ```

### 波動率指標 (Volatility Indicators)

- **Bollinger Bands**：布林帶
  ```python
  upper, middle, lower = tech_indicators.calculate_bollinger_bands(period=20, std_dev=2.0)
  ```

- **ATR (Average True Range)**：平均真實範圍
  ```python
  atr = tech_indicators.calculate_atr(period=14)
  ```

### 成交量指標 (Volume Indicators)

- **OBV (On-Balance Volume)**：能量潮指標
  ```python
  obv = tech_indicators.calculate_obv()
  ```

### 指標標準化與比較

- **標準化指標**：將指標標準化以便比較
  ```python
  standardized = tech_indicators.standardize_indicators(method='zscore')  # 可選 'zscore', 'minmax', 'robust'
  ```

- **比較指標**：比較不同指標的表現
  ```python
  comparison = tech_indicators.compare_indicators(price_series, periods=[5, 10, 20], indicators=['SMA', 'EMA', 'RSI'])
  ```

## 基本面指標

`FundamentalIndicators` 類實現了以下基本面指標：

- **EPS Growth**：每股盈餘成長率
  ```python
  eps_growth = fund_indicators.calculate_eps_growth(periods=[1, 4, 12])
  ```

- **P/E Ratio**：本益比
  ```python
  pe_ratio = fund_indicators.calculate_pe_ratio(price_data)
  ```

- **P/B Ratio**：股價淨值比
  ```python
  pb_ratio = fund_indicators.calculate_pb_ratio(price_data)
  ```

## 情緒指標

`SentimentIndicators` 類實現了以下情緒指標：

- **News Sentiment**：新聞情緒指標
  ```python
  news_sentiment = sent_indicators.calculate_news_sentiment(window=7)
  ```

- **Social Sentiment**：社交媒體情緒指標
  ```python
  social_sentiment = sent_indicators.calculate_social_sentiment(window=3)
  ```

- **Topic Sentiment**：主題情緒指標
  ```python
  topic_sentiment = sent_indicators.calculate_topic_sentiment(topics=['economy', 'company'], window=7)
  ```

## 指標評估與比較

模組提供了兩個實用函數來評估和使用指標：

- **評估指標有效性**：計算指標與未來價格變化的相關性
  ```python
  efficacy = evaluate_indicator_efficacy(price_data, indicator_data, forward_periods=[1, 5, 10, 20])
  ```

- **生成交易訊號**：根據指標和規則生成交易訊號
  ```python
  signal_rules = {
      'RSI_14': {'type': 'threshold', 'buy_threshold': 30, 'sell_threshold': 70},
      'SMA_20': {'type': 'crossover', 'reference': 'EMA', 'period': 50},
      'MACD': {'type': 'momentum', 'period': 1}
  }
  signals = generate_trading_signals(price_data, indicator_data, signal_rules)
  ```

## 使用示例

以下是一個完整的使用示例：

```python
import pandas as pd
from src.core.indicators import TechnicalIndicators, FundamentalIndicators, SentimentIndicators
from src.core.indicators import evaluate_indicator_efficacy, generate_trading_signals

# 載入價格資料
price_data = pd.read_csv('price_data.csv', index_col='date', parse_dates=True)

# 初始化技術指標類
tech_indicators = TechnicalIndicators(price_data)

# 計算技術指標
sma_20 = tech_indicators.calculate_sma(period=20)
ema_20 = tech_indicators.calculate_ema(period=20)
rsi_14 = tech_indicators.calculate_rsi(period=14)
upper, middle, lower = tech_indicators.calculate_bollinger_bands(period=20, std_dev=2.0)
macd, signal, hist = tech_indicators.calculate_macd()
obv = tech_indicators.calculate_obv()
atr = tech_indicators.calculate_atr()

# 標準化指標
standardized = tech_indicators.standardize_indicators(method='zscore')

# 比較指標
comparison = tech_indicators.compare_indicators(price_data['close'])

# 載入財務資料
financial_data = {
    'income_statement': pd.read_csv('income_statement.csv', index_col='date', parse_dates=True),
    'balance_sheet': pd.read_csv('balance_sheet.csv', index_col='date', parse_dates=True),
    'price': price_data
}

# 初始化基本面指標類
fund_indicators = FundamentalIndicators(financial_data)

# 計算基本面指標
eps_growth = fund_indicators.calculate_eps_growth()
pe_ratio = fund_indicators.calculate_pe_ratio()
pb_ratio = fund_indicators.calculate_pb_ratio()

# 載入情緒資料
sentiment_data = {
    'news': pd.read_csv('news_sentiment.csv', index_col='date', parse_dates=True),
    'social': pd.read_csv('social_sentiment.csv', index_col='date', parse_dates=True)
}

# 初始化情緒指標類
sent_indicators = SentimentIndicators(sentiment_data)

# 計算情緒指標
news_sentiment = sent_indicators.calculate_news_sentiment()
social_sentiment = sent_indicators.calculate_social_sentiment()
topic_sentiment = sent_indicators.calculate_topic_sentiment()

# 合併所有指標
all_indicators = pd.DataFrame({
    'SMA_20': sma_20,
    'EMA_20': ema_20,
    'RSI_14': rsi_14,
    'BBANDS_width': (upper - lower) / middle,
    'MACD': macd,
    'OBV': obv,
    'ATR_14': atr,
    'PE_ratio': pe_ratio,
    'PB_ratio': pb_ratio,
    'News_sentiment': news_sentiment,
    'Social_sentiment': social_sentiment
})

# 評估指標有效性
efficacy = evaluate_indicator_efficacy(price_data, all_indicators)

# 生成交易訊號
signal_rules = {
    'RSI_14': {'type': 'threshold', 'buy_threshold': 30, 'sell_threshold': 70},
    'SMA_20': {'type': 'crossover', 'reference': 'EMA', 'period': 50},
    'MACD': {'type': 'momentum', 'period': 1}
}
signals = generate_trading_signals(price_data, all_indicators, signal_rules)
```

更多示例請參考 `examples/indicators_example.py`。

## 常見問題

### 如何添加新的技術指標？

要添加新的技術指標，請在 `TechnicalIndicators` 類中添加新的方法。例如：

```python
def calculate_new_indicator(self, period: int = 14, column: str = 'close', price_data: pd.DataFrame = None) -> pd.Series:
    """
    計算新指標
    
    Args:
        period (int): 週期長度
        column (str): 使用的價格欄位
        price_data (pd.DataFrame, optional): 價格資料
        
    Returns:
        pd.Series: 新指標值
    """
    if price_data is None:
        price_data = self.price_data
        
    ohlcv_dict = self._prepare_ohlcv_data(price_data)
    
    if column not in ohlcv_dict:
        raise ValueError(f"找不到欄位: {column}")
        
    # 計算新指標的邏輯
    new_indicator = ...
    
    indicator_name = f"NEW_INDICATOR_{period}"
    self.indicators_data[indicator_name] = new_indicator
    
    return new_indicator
```

### 如何處理缺失的 TA-Lib？

如果無法安裝 TA-Lib，模組會自動使用純 Python 實現的替代方法。但是，這些替代方法可能不如 TA-Lib 高效。

要安裝 TA-Lib，請參考 [TA-Lib 安裝指南](https://github.com/mrjbq7/ta-lib#installation)。

### 如何評估指標的有效性？

使用 `evaluate_indicator_efficacy` 函數可以評估指標與未來價格變化的相關性：

```python
efficacy = evaluate_indicator_efficacy(price_data, indicator_data, forward_periods=[1, 5, 10, 20])
```

結果是一個相關性矩陣，顯示每個指標與不同時間範圍未來價格變化的相關性。相關性越高，指標的預測能力越強。
