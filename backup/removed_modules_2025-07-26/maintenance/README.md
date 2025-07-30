# 持續優化與維護模組 (Continuous Optimization and Maintenance Module)

此目錄包含 AI 股票自動交易系統的持續優化與維護相關模組，負責系統的長期健康和性能。

## 模組概述

### continuous_optimization.py

持續優化模組，協調和執行系統的持續優化任務。

**主要類別**：
- `ContinuousOptimization`: 持續優化類，負責排程和執行優化任務

**主要方法**：
- `start()`: 啟動持續優化
- `stop()`: 停止持續優化
- `check_and_retrain_models()`: 檢查並重訓練模型
- `check_and_refine_strategies()`: 檢查並優化策略
- `optimize_performance()`: 優化系統性能
- `check_api_compatibility()`: 檢查 API 兼容性
- `get_status()`: 獲取持續優化狀態

### model_retrainer.py

模型重訓練模組，負責檢查模型性能並在需要時重訓練模型。

**主要類別**：
- `ModelRetrainer`: 模型重訓練類

**主要方法**：
- `check_model_performance()`: 檢查模型性能
- `retrain_models()`: 重訓練模型
- `_evaluate_model()`: 評估模型性能
- `_prepare_training_data()`: 準備訓練資料
- `_prepare_test_data()`: 準備測試資料

### strategy_refiner.py

策略優化模組，負責評估和優化交易策略。

**主要類別**：
- `StrategyRefiner`: 策略優化類

**主要方法**：
- `check_strategy_performance()`: 檢查策略性能
- `refine_strategies()`: 優化策略
- `_evaluate_strategy()`: 評估策略性能
- `_optimize_parameters()`: 優化策略參數
- `_analyze_market_conditions()`: 分析不同市場條件下的表現

### performance_optimizer.py

性能優化模組，負責識別和優化系統性能瓶頸。

**主要類別**：
- `PerformanceOptimizer`: 性能優化類

**主要方法**：
- `identify_bottlenecks()`: 識別性能瓶頸
- `optimize()`: 優化性能瓶頸
- `_check_system_resources()`: 檢查系統資源使用情況
- `_check_api_latency()`: 檢查 API 延遲
- `_check_db_query_time()`: 檢查資料庫查詢時間
- `_check_model_inference_time()`: 檢查模型推論時間

### api_compatibility.py

API 兼容性檢查模組，負責檢查和維護 API 兼容性。

**主要類別**：
- `APICompatibilityChecker`: API 兼容性檢查類

**主要方法**：
- `check_compatibility()`: 檢查 API 兼容性
- `resolve_compatibility_issues()`: 解決兼容性問題
- `_get_api_version()`: 獲取 API 版本
- `_test_api_endpoints()`: 測試 API 端點
- `_implement_solution()`: 實施解決方案

## 使用範例

### 啟動持續優化

```python
from src.maintenance.continuous_optimization import ContinuousOptimization

# 創建持續優化實例
optimizer = ContinuousOptimization()

# 啟動持續優化
optimizer.start()
```

### 手動檢查模型性能

```python
from src.maintenance.model_retrainer import ModelRetrainer

# 創建模型重訓練器
retrainer = ModelRetrainer()

# 檢查模型性能
models_to_retrain = retrainer.check_model_performance()

# 重訓練模型
if models_to_retrain:
    results = retrainer.retrain_models(models_to_retrain)
    print(f"重訓練結果: {results}")
else:
    print("所有模型性能良好，無需重訓練")
```

### 手動優化策略

```python
from src.maintenance.strategy_refiner import StrategyRefiner

# 創建策略優化器
refiner = StrategyRefiner()

# 檢查策略性能
strategies_to_refine = refiner.check_strategy_performance()

# 優化策略
if strategies_to_refine:
    results = refiner.refine_strategies(strategies_to_refine)
    print(f"優化結果: {results}")
else:
    print("所有策略性能良好，無需優化")
```

### 手動識別性能瓶頸

```python
from src.maintenance.performance_optimizer import PerformanceOptimizer

# 創建性能優化器
optimizer = PerformanceOptimizer()

# 識別性能瓶頸
bottlenecks = optimizer.identify_bottlenecks()

# 優化性能瓶頸
if bottlenecks:
    results = optimizer.optimize(bottlenecks)
    print(f"優化結果: {results}")
else:
    print("系統性能良好，無需優化")
```

### 手動檢查 API 兼容性

```python
from src.maintenance.api_compatibility import APICompatibilityChecker

# 創建 API 兼容性檢查器
checker = APICompatibilityChecker()

# 檢查 API 兼容性
apis = {
    "n8n": "https://api.n8n.io/version",
    "broker": "https://api.broker.com/version",
}
compatibility_issues = checker.check_compatibility(apis)

# 解決兼容性問題
if compatibility_issues:
    results = checker.resolve_compatibility_issues(compatibility_issues)
    print(f"解決結果: {results}")
else:
    print("所有 API 兼容性良好")
```

## 排程任務

系統使用 n8n 工作流自動執行持續優化任務：

- **星期一**：執行性能優化
- **星期二**：執行 API 兼容性檢查
- **星期三**：檢查模型性能
- **星期四**：檢查策略性能
- **星期五**：生成週報

工作流配置文件位於 `src/integration/workflows/continuous_optimization_workflow.json`。

## 配置

持續優化模組的配置可以通過 JSON 文件提供，包括：

- 模型重訓練頻率和閾值
- 策略優化頻率和閾值
- 性能優化閾值
- API 兼容性檢查頻率和端點

預設配置包括：

```json
{
  "model_retraining": {
    "schedule": {
      "ml_models": "monthly",
      "dl_models": "quarterly"
    },
    "thresholds": {
      "accuracy_drop": 0.05,
      "sharpe_drop": 0.2
    }
  },
  "strategy_refinement": {
    "schedule": {
      "trend_following": "quarterly",
      "mean_reversion": "monthly",
      "ml_based": "monthly"
    },
    "thresholds": {
      "sharpe_ratio": 0.8,
      "max_drawdown": 0.2,
      "win_rate": 0.45
    }
  },
  "performance_optimization": {
    "schedule": "weekly",
    "thresholds": {
      "cpu_usage": 80,
      "memory_usage": 80,
      "api_latency": 0.5,
      "db_query_time": 1.0
    }
  },
  "api_compatibility": {
    "schedule": "weekly",
    "apis": {
      "n8n": "https://api.n8n.io/version",
      "broker": "https://api.broker.com/version"
    }
  }
}
```
