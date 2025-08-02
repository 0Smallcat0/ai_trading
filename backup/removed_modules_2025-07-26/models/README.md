# AI 模型模組 (AI Models Module)

此目錄包含 AI 股票自動交易系統的模型相關模組，負責模型的訓練、評估、部署和管理。

## 模組概述

### model_base.py

模型基類，定義了所有模型的共同介面和功能。

**主要類別**：
- `ModelBase`: 模型基類，所有具體模型都應該繼承此類

**主要方法**：
- `train(X, y)`: 訓練模型
- `predict(X)`: 使用模型進行預測
- `evaluate(X, y)`: 評估模型表現
- `save(path)`: 保存模型
- `load(path)`: 載入模型
- `feature_importance()`: 獲取特徵重要性
- `get_params()`: 獲取模型參數
- `set_params(**params)`: 設定模型參數

### model_factory.py

模型工廠，提供創建各種模型的工廠函數。

**主要函數**：
- `create_model(model_type, name, **kwargs)`: 創建模型
- `register_model(model_type, model_class)`: 註冊自定義模型
- `get_available_models()`: 獲取所有可用的模型類型

### ml_models.py

機器學習模型，實現了各種機器學習模型。

**主要類別**：
- `RandomForestModel`: 隨機森林模型
- `XGBoostModel`: XGBoost 模型
- `LightGBMModel`: LightGBM 模型
- `SVMModel`: SVM 模型

### dl_models.py

深度學習模型，實現了各種深度學習模型。

**主要類別**：
- `LSTMModel`: LSTM 模型
- `GRUModel`: GRU 模型
- `TransformerModel`: Transformer 模型

### rule_based_models.py

規則型模型，實現了各種規則型模型。

**主要類別**：
- `RuleBasedModel`: 規則型模型

**主要函數**：
- `moving_average_crossover()`: 移動平均線交叉規則
- `rsi_strategy()`: RSI 策略規則
- `bollinger_bands_strategy()`: 布林通道策略規則

### dataset.py

資料集處理，提供資料集的處理功能。

**主要類別**：
- `TimeSeriesSplit`: 時間序列資料分割
- `FeatureProcessor`: 特徵處理器
- `DatasetLoader`: 資料集載入器

### strategy_research.py

策略研究，用於研究和分析不同的交易策略。

**主要類別**：
- `StrategyResearcher`: 策略研究器

**主要方法**：
- `evaluate_trend_following_strategies()`: 評估趨勢跟蹤策略
- `evaluate_mean_reversion_strategies()`: 評估均值回歸策略
- `evaluate_oscillator_strategies()`: 評估震盪指標策略
- `compare_strategies()`: 比較不同策略的表現
- `plot_strategy_comparison()`: 繪製策略比較圖
- `get_best_strategy()`: 獲取最佳策略

## 模型類型

系統支援多種模型類型，包括：

### 機器學習模型

- **隨機森林 (Random Forest)**：基於決策樹的集成學習方法，適用於分類和回歸問題
- **XGBoost**：高效的梯度提升樹實現，具有優秀的性能和可擴展性
- **LightGBM**：微軟開發的梯度提升框架，專注於效率和低記憶體使用
- **SVM**：支持向量機，適用於分類和回歸問題

### 深度學習模型

- **LSTM**：長短期記憶網絡，適用於時間序列預測
- **GRU**：門控循環單元，LSTM 的變體，計算效率更高
- **Transformer**：基於自注意力機制的模型，適用於序列資料

### 規則型模型

- **移動平均線交叉**：基於短期和長期移動平均線交叉的策略
- **RSI 策略**：基於相對強弱指標的策略
- **布林通道策略**：基於價格與布林通道的關係的策略

## 策略類型

系統研究了多種交易策略類型，包括：

### 趨勢跟蹤策略 (Trend Following)

跟隨市場趨勢的策略，當市場呈現上升趨勢時買入，下降趨勢時賣出。

**代表策略**：
- 移動平均線交叉
- MACD
- 拋物線轉向 (SAR)

### 均值回歸策略 (Mean Reversion)

基於價格會回歸均值的假設，當價格偏離均值過遠時進行交易。

**代表策略**：
- 布林通道
- 統計套利
- 對數回歸

### 震盪指標策略 (Oscillator)

基於市場超買超賣狀態的策略，當市場超買時賣出，超賣時買入。

**代表策略**：
- RSI
- 隨機指標 (Stochastic)
- 威廉指標 (Williams %R)

### 事件驅動策略 (Event-Driven)

基於特定事件或新聞的策略，當發生特定事件時進行交易。

**代表策略**：
- 財報公布
- 併購事件
- 政策變化

## 模型評估指標

系統使用多種指標評估模型和策略的表現，包括：

### 收益率指標

- **累積收益率**：策略的總收益率
- **年化收益率**：策略的年化收益率
- **每筆交易平均收益**：每筆交易的平均收益率

### 風險指標

- **最大回撤**：策略的最大回撤幅度
- **波動率**：策略收益率的標準差
- **下行風險**：只考慮負收益的風險指標

### 風險調整收益指標

- **夏普比率**：超額收益與波動率的比值
- **索提諾比率**：超額收益與下行風險的比值
- **卡爾馬比率**：年化收益率與最大回撤的比值

### 交易統計指標

- **勝率**：盈利交易的比例
- **盈虧比**：平均盈利與平均虧損的比值
- **交易次數**：策略的交易次數
- **持倉時間**：平均持倉時間

## 使用示例

```python
from src.models.model_factory import create_model
from src.models.dataset import TimeSeriesSplit, FeatureProcessor, DatasetLoader
from src.models.strategy_research import StrategyResearcher

# 載入資料
loader = DatasetLoader()
loader.load_from_database(symbols=["AAPL", "MSFT"], start_date="2020-01-01", end_date="2021-12-31")
features = loader.prepare_features(target_type="direction", target_horizon=5)

# 分割資料
splitter = TimeSeriesSplit()
train, val, test = splitter.split(features)

# 處理特徵
processor = FeatureProcessor()
train_scaled = processor.fit_transform(train)
val_scaled = processor.transform(val)
test_scaled = processor.transform(test)

# 創建模型
model = create_model("random_forest", is_classifier=True, n_estimators=100, max_depth=10)

# 訓練模型
X_train = train_scaled.drop(["target", "date", "symbol"], axis=1)
y_train = train_scaled["target"]
model.train(X_train, y_train)

# 評估模型
X_val = val_scaled.drop(["target", "date", "symbol"], axis=1)
y_val = val_scaled["target"]
metrics = model.evaluate(X_val, y_val)
print(metrics)

# 研究策略
researcher = StrategyResearcher(price_data=loader.price_data)
researcher.evaluate_trend_following_strategies()
researcher.evaluate_mean_reversion_strategies()
researcher.evaluate_oscillator_strategies()
best_strategy = researcher.get_best_strategy()
print(best_strategy)
```
