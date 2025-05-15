# 模型訓練與調優指南

本文檔提供了使用 AI 股票自動交易系統進行模型訓練和調優的詳細指南。

## 1. 模型訓練流程

### 1.1 準備資料

首先，需要準備訓練資料，包括特徵資料和目標資料。可以使用 `DatasetLoader` 類載入資料：

```python
from src.models.dataset import DatasetLoader, TimeSeriesSplit, FeatureProcessor

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

# 準備訓練資料
X_train = train_scaled.drop(["target", "date", "symbol"], axis=1)
y_train = train_scaled["target"]
X_val = val_scaled.drop(["target", "date", "symbol"], axis=1)
y_val = val_scaled["target"]
```

### 1.2 創建模型

使用 `model_factory` 模組創建模型：

```python
from src.models.model_factory import create_model

# 創建模型
model = create_model(
    "random_forest",  # 模型類型
    name="rf_direction_5d",  # 模型名稱
    is_classifier=True,  # 是否為分類模型
    n_estimators=100,  # 樹的數量
    max_depth=10,  # 最大深度
    random_state=42  # 隨機種子
)
```

### 1.3 訓練模型

使用 `ModelTrainer` 類訓練模型：

```python
from src.models.training_pipeline import ModelTrainer

# 創建訓練器
trainer = ModelTrainer(
    model=model,
    experiment_name="stock_direction_prediction",
    metrics_threshold={"accuracy": 0.6, "f1": 0.6}
)

# 訓練模型
result = trainer.train(
    X_train=X_train,
    y_train=y_train,
    X_val=X_val,
    y_val=y_val,
    log_to_mlflow=True
)

# 查看訓練結果
print(f"訓練指標: {result['train_metrics']}")
print(f"驗證指標: {result['val_metrics']}")
print(f"模型路徑: {result['model_path']}")
print(f"是否達到接受標準: {result['accepted']}")
```

### 1.4 交叉驗證

使用交叉驗證評估模型：

```python
# 執行交叉驗證
cv_result = trainer.cross_validate(
    X=X_train,
    y=y_train,
    cv=5,
    time_series=True,
    log_to_mlflow=True
)

# 查看交叉驗證結果
print(f"平均訓練指標: {cv_result['avg_train_metrics']}")
print(f"平均驗證指標: {cv_result['avg_val_metrics']}")
```

### 1.5 評估模型

在測試集上評估模型：

```python
# 準備測試資料
X_test = test_scaled.drop(["target", "date", "symbol"], axis=1)
y_test = test_scaled["target"]

# 評估模型
test_metrics = trainer.evaluate_on_test(
    X_test=X_test,
    y_test=y_test,
    log_to_mlflow=True
)

# 查看測試指標
print(f"測試指標: {test_metrics}")
```

## 2. 超參數調優

### 2.1 網格搜索

使用網格搜索調優超參數：

```python
from src.models.hyperparameter_tuning import HyperparameterTuner

# 定義參數網格
param_grid = {
    "n_estimators": [50, 100, 200],
    "max_depth": [None, 5, 10, 20],
    "min_samples_split": [2, 5, 10]
}

# 創建調優器
tuner = HyperparameterTuner(
    model_type="random_forest",
    param_grid=param_grid,
    experiment_name="rf_hyperparameter_tuning",
    scoring="f1",
    cv=5
)

# 執行網格搜索
grid_result = tuner.grid_search(
    X=X_train,
    y=y_train,
    log_to_mlflow=True
)

# 查看調優結果
print(f"最佳參數: {grid_result['best_params']}")
print(f"最佳分數: {grid_result['best_score']}")
```

### 2.2 隨機搜索

使用隨機搜索調優超參數：

```python
# 執行隨機搜索
random_result = tuner.random_search(
    X=X_train,
    y=y_train,
    n_iter=20,
    log_to_mlflow=True
)

# 查看調優結果
print(f"最佳參數: {random_result['best_params']}")
print(f"最佳分數: {random_result['best_score']}")
```

### 2.3 貝葉斯優化

使用貝葉斯優化調優超參數：

```python
# 執行貝葉斯優化
bayesian_result = tuner.bayesian_optimization(
    X=X_train,
    y=y_train,
    n_trials=50,
    log_to_mlflow=True
)

# 查看調優結果
print(f"最佳參數: {bayesian_result['best_params']}")
print(f"最佳分數: {bayesian_result['best_score']}")
```

## 3. 模型解釋性

### 3.1 SHAP 解釋

使用 SHAP 解釋模型：

```python
from src.models.model_interpretability import ModelInterpreter

# 創建解釋器
interpreter = ModelInterpreter(
    model=model,
    feature_names=X_train.columns.tolist(),
    output_dir="results/model_interpretation/rf_direction_5d"
)

# 使用 SHAP 解釋模型
shap_result = interpreter.explain_with_shap(
    X=X_val.sample(100),
    plot_type="summary",
    log_to_mlflow=True
)

# 查看特徵重要性
print(shap_result["importance"].head())
```

### 3.2 LIME 解釋

使用 LIME 解釋模型：

```python
# 使用 LIME 解釋模型
lime_result = interpreter.explain_with_lime(
    X=X_val.sample(5),
    y=y_val.sample(5),
    num_features=10,
    log_to_mlflow=True
)

# 查看解釋結果
for i, exp in enumerate(lime_result["explanations"]):
    print(f"樣本 {i+1} 的解釋:")
    print(exp["importance"])
```

### 3.3 特徵重要性

計算特徵重要性：

```python
# 計算特徵重要性
importance_df = interpreter.feature_importance(
    X=X_train,
    y=y_train,
    method="permutation",
    n_repeats=10,
    log_to_mlflow=True
)

# 查看特徵重要性
print(importance_df.head())
```

## 4. 模型治理

### 4.1 註冊模型

使用 `ModelRegistry` 註冊模型：

```python
from src.models.model_governance import ModelRegistry

# 創建註冊表
registry = ModelRegistry()

# 註冊模型
version = registry.register_model(
    model=model,
    description="隨機森林模型，預測 5 天後的價格方向",
    metrics=test_metrics,
    run_id=result["run_id"]
)

# 查看模型資訊
model_info = registry.get_model_info(model.name, version)
print(f"模型資訊: {model_info}")
```

### 4.2 部署模型

部署模型到生產環境：

```python
# 部署模型
deployment = registry.deploy_model(
    model_name=model.name,
    version=version,
    environment="production",
    description="用於生產環境的方向預測模型"
)

# 查看部署資訊
print(f"部署資訊: {deployment}")
```

### 4.3 回滾模型

如果需要，可以回滾模型到之前的版本：

```python
# 回滾模型
rollback = registry.rollback_model(
    model_name=model.name,
    environment="production",
    to_version="20220101120000",  # 回滾到的版本
    description="由於性能下降，回滾到之前的版本"
)

# 查看回滾後的部署資訊
print(f"回滾後的部署資訊: {rollback}")
```

## 5. 推論管道

### 5.1 創建推論管道

使用 `InferencePipeline` 創建推論管道：

```python
from src.models.inference_pipeline import InferencePipeline

# 創建推論管道
pipeline = InferencePipeline(
    model_name=model.name,
    environment="production",
    feature_processor=processor,
    monitor=True
)

# 進行預測
predictions = pipeline.predict(
    data=X_test.iloc[:10],
    preprocess=True,
    postprocess=True,
    log_prediction=True
)

# 查看預測結果
print(f"預測結果: {predictions}")
```

### 5.2 批次預測

進行批次預測：

```python
# 進行批次預測
batch_predictions = pipeline.batch_predict(
    data=X_test,
    batch_size=100,
    preprocess=True,
    postprocess=True,
    log_prediction=True,
    actual=y_test
)

# 保存預測結果
output_path = pipeline.save_results(format="csv")
print(f"預測結果已保存至: {output_path}")

# 計算指標
metrics = pipeline.calculate_metrics()
print(f"預測指標: {metrics}")
```

## 6. 最佳實踐

### 6.1 模型選擇

根據不同的預測任務選擇合適的模型：

- **分類任務**（如價格方向預測）：隨機森林、XGBoost、LightGBM
- **回歸任務**（如價格預測）：LSTM、GRU、XGBoost
- **時間序列任務**：LSTM、GRU、Transformer

### 6.2 特徵選擇

選擇有預測能力的特徵：

- 使用特徵重要性分析選擇特徵
- 使用 SHAP 值分析特徵對預測的貢獻
- 考慮特徵之間的相關性，避免多重共線性

### 6.3 避免過擬合

防止模型過擬合：

- 使用交叉驗證評估模型
- 適當調整模型複雜度（如樹的深度、正則化參數）
- 使用足夠的訓練資料
- 監控訓練集和驗證集的性能差距

### 6.4 模型監控

持續監控模型性能：

- 記錄預測結果和實際值
- 定期計算模型指標
- 監控特徵分佈的變化
- 當性能下降時及時回滾或重新訓練模型
