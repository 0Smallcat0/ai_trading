# AI 模型整合指南

本文檔提供了將 AI 模型整合到交易流程中的詳細指南。

## 1. 模型整合概述

AI 模型整合系統提供了以下功能：

- 模型載入與管理
- 模型推論與訊號生成
- 模型健康檢查與備援機制
- 混合訊號生成（AI + 規則型）
- 訊號優化與調整

## 2. 模型管理

### 2.1 初始化模型管理器

首先，需要初始化 `ModelManager` 類來管理 AI 模型：

```python
from src.core.model_integration import ModelManager
from src.models.model_governance import ModelRegistry

# 創建模型註冊表
registry = ModelRegistry()

# 創建模型管理器
model_manager = ModelManager(
    model_registry=registry,
    cache_size=10,  # 快取大小
    batch_size=32,  # 批次推論大小
    use_onnx=False,  # 是否使用 ONNX 優化
    fallback_strategy="latest",  # 備援策略
    model_check_interval=3600  # 健康檢查間隔（秒）
)
```

### 2.2 載入模型

載入模型到管理器中：

```python
# 載入模型
model_manager.load_model(
    model_name="price_direction",  # 模型名稱
    version="20230101",  # 版本，如果為 None，則使用最新部署版本
    environment="production"  # 環境
)

# 載入多個模型
for model_name in ["price_direction", "volatility", "return_prediction"]:
    model_manager.load_model(model_name)
```

### 2.3 模型健康檢查

檢查模型健康狀態：

```python
# 檢查特定模型的健康狀態
is_healthy = model_manager.check_model_health("price_direction")

# 獲取所有模型的健康狀態
health_status = model_manager.get_health_status()

# 獲取模型資訊
model_info = model_manager.get_model_info("price_direction")
```

## 3. 訊號生成

### 3.1 使用 AI 模型生成訊號

使用 `SignalGenerator` 類生成 AI 模型訊號：

```python
from src.core.signal_gen import SignalGenerator

# 創建訊號產生器
signal_generator = SignalGenerator(
    price_data=price_data,
    volume_data=volume_data,
    financial_data=financial_data,
    news_data=news_data,
    model_manager=model_manager
)

# 生成 AI 模型訊號
ai_signals = signal_generator.generate_ai_model_signals(
    model_name="price_direction",
    version=None,  # 使用最新版本
    signal_threshold=0.5  # 訊號閾值
)

# 生成所有訊號（包括 AI 模型訊號）
all_signals = signal_generator.generate_all_signals(
    include_advanced=True,
    include_ai=True,
    ai_models=["price_direction", "volatility"]
)
```

### 3.2 使用混合訊號產生器

使用 `HybridSignalGenerator` 類生成混合訊號：

```python
from src.core.hybrid_signal_gen import HybridSignalGenerator

# 創建混合訊號產生器
hybrid_generator = HybridSignalGenerator(
    price_data=price_data,
    volume_data=volume_data,
    financial_data=financial_data,
    news_data=news_data,
    model_manager=model_manager,
    ai_weight=0.6,  # AI 模型訊號權重
    rule_weight=0.4,  # 規則型策略訊號權重
    conflict_resolution="ai_priority"  # 衝突解決方式
)

# 生成混合訊號
hybrid_signals = hybrid_generator.generate_hybrid_signals(
    model_name="price_direction",
    rule_strategies=["momentum", "reversion"],
    version=None,
    signal_threshold=0.5
)

# 優化訊號時機
optimized_signals = hybrid_generator.optimize_signal_timing(
    signals=hybrid_signals,
    lookback_window=5,
    confirmation_threshold=3
)

# 調整訊號強度
adjusted_signals = hybrid_generator.adjust_signal_strength(
    signals=optimized_signals,
    strength_factors={
        "price_trend": 0.4,
        "volume": 0.3,
        "volatility": 0.3
    }
)

# 生成所有混合訊號
all_hybrid_signals = hybrid_generator.generate_all_hybrid_signals(
    ai_models=["price_direction", "volatility"],
    rule_strategies=["momentum", "reversion", "sentiment"],
    optimize_timing=True,
    adjust_strength=True
)
```

## 4. 訊號優化

### 4.1 使用訊號優化器

使用 `ModelSignalOptimizer` 類優化 AI 模型訊號：

```python
from src.core.model_signal_optimizer import ModelSignalOptimizer

# 創建訊號優化器
optimizer = ModelSignalOptimizer(
    signals=ai_signals,
    price_data=price_data,
    volume_data=volume_data
)

# 平滑訊號
smoothed_signals = optimizer.smooth_signals(
    method="moving_average",
    window=3
)

# 過濾噪聲
filtered_signals = optimizer.filter_noise(
    threshold=0.5,
    min_consecutive=2
)

# 修正延遲
corrected_signals = optimizer.correct_delay(
    delay=1
)

# 解決衝突
resolved_signals = optimizer.resolve_conflicts(
    signals_dict={
        "model1": model1_signals,
        "model2": model2_signals,
        "model3": model3_signals
    },
    method="weighted_average",
    weights={
        "model1": 0.5,
        "model2": 0.3,
        "model3": 0.2
    }
)

# 優化組合
optimized_signals, best_weights = optimizer.optimize_combination(
    signals_dict={
        "model1": model1_signals,
        "model2": model2_signals,
        "model3": model3_signals
    },
    optimization_metric="sharpe_ratio",
    lookback_period=252
)
```

## 5. 模型推論效能優化

### 5.1 批次推論

使用批次推論提高效能：

```python
# 使用批次推論
predictions = model_manager.predict(
    data=features,
    model_name="price_direction",
    version=None,
    use_pipeline=True  # 使用推論管道
)
```

### 5.2 使用 ONNX 優化

使用 ONNX 優化推論效能：

```python
# 創建使用 ONNX 的模型管理器
onnx_model_manager = ModelManager(
    model_registry=registry,
    use_onnx=True  # 啟用 ONNX 優化
)

# 使用 ONNX 進行推論
predictions = onnx_model_manager.predict(
    data=features,
    model_name="price_direction"
)
```

## 6. 備援機制

### 6.1 設定備援策略

設定模型備援策略：

```python
# 創建具有備援策略的模型管理器
model_manager = ModelManager(
    model_registry=registry,
    fallback_strategy="rule_based"  # 使用規則型策略作為備援
)
```

### 6.2 使用規則型備援

當 AI 模型不可用時，自動使用規則型策略作為備援：

```python
# 生成訊號（如果 AI 模型不可用，將使用規則型策略）
signals = signal_generator.generate_ai_model_signals("price_direction")
```

## 7. 整合到交易流程

### 7.1 在回測中使用 AI 模型

在回測中使用 AI 模型：

```python
from src.backtest import BacktestEngine, MLStrategy

# 創建回測引擎
engine = BacktestEngine(
    cash=100000.0,
    commission=0.001425,
    slippage=0.001,
    tax=0.003
)

# 添加資料
engine.add_data(data=price_data)

# 添加 AI 模型策略
engine.add_strategy(
    MLStrategy,
    model=model_manager.model_cache["price_direction_latest"],
    prediction_window=5,
    confidence_threshold=0.6,
    feature_window=10,
    retrain_freq=20
)

# 執行回測
results = engine.run()
```

### 7.2 在實時交易中使用 AI 模型

在實時交易中使用 AI 模型：

```python
from src.trading import TradingSystem
from src.core.hybrid_signal_gen import HybridSignalGenerator

# 創建混合訊號產生器
hybrid_generator = HybridSignalGenerator(
    price_data=price_data,
    model_manager=model_manager,
    ai_weight=0.7,
    rule_weight=0.3
)

# 創建交易系統
trading_system = TradingSystem(
    signal_generator=hybrid_generator,
    broker=broker,
    risk_manager=risk_manager
)

# 更新資料
trading_system.update_data(new_price_data)

# 生成訊號
signals = trading_system.generate_signals()

# 執行交易
trading_system.execute_trades(signals)
```

## 8. 最佳實踐

### 8.1 模型版本管理

使用模型版本管理確保穩定性：

```python
# 註冊新模型版本
version = registry.register_model(
    model=model,
    description="價格方向預測模型 v2.0",
    metrics=metrics
)

# 部署模型到生產環境
registry.deploy_model(
    model_name="price_direction",
    version=version,
    environment="production"
)

# 如果需要，回滾到之前的版本
registry.rollback_model(
    model_name="price_direction",
    environment="production",
    to_version="20230101"
)
```

### 8.2 模型監控

監控模型性能：

```python
# 獲取模型監控資訊
monitor = model_manager.inference_pipelines["price_direction"].monitor

# 計算監控指標
metrics = monitor.calculate_metrics()

# 記錄預測結果
monitor.log_prediction(
    features=features,
    prediction=prediction,
    actual=actual
)
```

### 8.3 混合策略調整

根據市場條件調整混合策略：

```python
# 在不同市場條件下調整權重
if market_volatility > high_volatility_threshold:
    # 高波動市場，增加規則型策略權重
    hybrid_generator.ai_weight = 0.4
    hybrid_generator.rule_weight = 0.6
elif market_volatility < low_volatility_threshold:
    # 低波動市場，增加 AI 模型權重
    hybrid_generator.ai_weight = 0.8
    hybrid_generator.rule_weight = 0.2
else:
    # 正常市場，使用平衡權重
    hybrid_generator.ai_weight = 0.6
    hybrid_generator.rule_weight = 0.4
```
