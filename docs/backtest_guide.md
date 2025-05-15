# 回測系統使用指南

本文檔提供了使用 AI 股票自動交易系統的回測功能的詳細指南。

## 1. 回測系統概述

回測系統基於 Backtrader 框架，提供了以下功能：

- 模型驅動的交易策略
- 多種交易成本模型
- 詳細的回測分析
- 壓力測試和異常情境模擬
- 敏感性和穩健性分析

## 2. 基本回測流程

### 2.1 準備資料

首先，需要準備回測資料，通常是 OHLCV（開盤價、最高價、最低價、收盤價、成交量）格式的價格資料：

```python
import pandas as pd
from src.backtest import BacktestEngine

# 載入資料
data = pd.read_csv("data/stock_prices.csv")

# 確保日期欄位為 datetime 類型
data["date"] = pd.to_datetime(data["date"])

# 排序資料
data = data.sort_values("date")
```

### 2.2 創建回測引擎

使用 `BacktestEngine` 類創建回測引擎：

```python
# 創建回測引擎
engine = BacktestEngine(
    cash=100000.0,  # 初始資金
    commission=0.001425,  # 手續費率
    slippage=0.001,  # 滑價率
    tax=0.003,  # 稅率
    output_dir="results/backtest/my_strategy"  # 輸出目錄
)

# 添加資料
engine.add_data(
    data=data,
    name="AAPL",
    fromdate=pd.to_datetime("2020-01-01"),
    todate=pd.to_datetime("2021-12-31")
)
```

### 2.3 添加策略

添加交易策略：

```python
from src.backtest import ModelSignalStrategy
from src.models.model_factory import create_model
from src.models.inference_pipeline import InferencePipeline

# 創建模型
model = create_model("random_forest", name="stock_direction")

# 載入模型
model.load("models/stock_direction/model.joblib")

# 創建推論管道
pipeline = InferencePipeline(model=model)

# 添加策略
engine.add_strategy(
    ModelSignalStrategy,
    inference_pipeline=pipeline,
    signal_threshold=0.6,
    position_size=0.1,
    stop_loss=0.05,
    take_profit=0.1,
    trailing_stop=True,
    trailing_stop_distance=0.02,
    max_positions=5,
    verbose=True
)
```

### 2.4 執行回測

執行回測並獲取結果：

```python
# 執行回測
results = engine.run()

# 繪製回測結果
engine.plot(filename="results/backtest/my_strategy/backtest_plot.png")

# 獲取權益曲線
equity_curve = engine.get_equity_curve()
```

### 2.5 分析回測結果

使用 `BacktestAnalyzer` 分析回測結果：

```python
from src.backtest import BacktestAnalyzer

# 創建分析器
analyzer = BacktestAnalyzer(
    results=results,
    equity_curve=equity_curve,
    output_dir="results/backtest/my_strategy/analysis"
)

# 生成報告
report_path = analyzer.generate_report()

# 繪製權益曲線
equity_curve_path = analyzer.plot_equity_curve()

# 繪製回撤圖
drawdown_path = analyzer.plot_drawdown()

# 繪製月度收益熱圖
monthly_returns_path = analyzer.plot_monthly_returns()
```

## 3. 使用自定義策略

### 3.1 機器學習策略

使用 `MLStrategy` 實現基於機器學習模型的交易策略：

```python
from src.backtest import MLStrategy

# 添加機器學習策略
engine.add_strategy(
    MLStrategy,
    model=model,
    prediction_window=5,
    confidence_threshold=0.6,
    feature_window=10,
    retrain_freq=20,
    retrain_window=252
)
```

### 3.2 集成策略

使用 `EnsembleStrategy` 結合多個模型的交易策略：

```python
from src.backtest import EnsembleStrategy

# 創建多個模型
model1 = create_model("random_forest", name="model1")
model2 = create_model("xgboost", name="model2")
model3 = create_model("lightgbm", name="model3")

# 載入模型
model1.load("models/model1/model.joblib")
model2.load("models/model2/model.joblib")
model3.load("models/model3/model.joblib")

# 添加集成策略
engine.add_strategy(
    EnsembleStrategy,
    models=[model1, model2, model3],
    weights=[0.4, 0.3, 0.3],
    voting_method="weighted"
)
```

### 3.3 技術指標策略

使用 `TechnicalStrategy` 實現基於技術指標的交易策略：

```python
from src.backtest import TechnicalStrategy

# 添加技術指標策略
engine.add_strategy(
    TechnicalStrategy,
    sma_short=10,
    sma_long=50,
    rsi_period=14,
    rsi_overbought=70,
    rsi_oversold=30,
    macd_fast=12,
    macd_slow=26,
    macd_signal=9,
    bb_period=20,
    bb_dev=2.0,
    stop_loss=0.05,
    take_profit=0.1
)
```

## 4. 交易成本模擬

### 4.1 使用預定義的成本模型

使用 `get_cost_scheme` 函數獲取預定義的成本模型：

```python
from src.backtest.transaction_costs import get_cost_scheme

# 獲取台股成本模型
tw_cost = get_cost_scheme(
    market="TW",
    commission_rate=0.001425,
    min_commission=20.0,
    tax_rate=0.003,
    slippage_perc=0.001
)

# 獲取美股成本模型
us_cost = get_cost_scheme(
    market="US",
    commission_rate=0.0,
    slippage_perc=0.0005
)

# 設定成本模型
engine.cerebro.broker.addcommissioninfo(tw_cost)
```

### 4.2 自定義成本模型

使用自定義成本模型：

```python
from src.backtest.transaction_costs import TieredCommissionScheme

# 創建階梯式手續費模型
tiered_cost = TieredCommissionScheme(
    tiers={
        0: 0.002,      # 0 元以上，0.2%
        100000: 0.0015,  # 10 萬元以上，0.15%
        1000000: 0.001   # 100 萬元以上，0.1%
    },
    tier_type="amount",
    min_commission=20.0
)

# 設定成本模型
engine.cerebro.broker.addcommissioninfo(tiered_cost)
```

## 5. 壓力測試

使用 `StressTester` 進行壓力測試：

```python
from src.backtest import StressTester

# 定義回測函數
def run_backtest(test_data):
    # 創建回測引擎
    engine = BacktestEngine(cash=100000.0)
    
    # 添加資料
    engine.add_data(data=test_data)
    
    # 添加策略
    engine.add_strategy(ModelSignalStrategy, model=model)
    
    # 執行回測
    return engine.run()

# 創建壓力測試器
stress_tester = StressTester(
    data=data,
    backtest_func=run_backtest,
    output_dir="results/stress_test"
)

# 執行基準回測
baseline_result = stress_tester.run_baseline()

# 模擬市場崩盤
crash_result = stress_tester.simulate_market_crash(
    crash_period=("2021-03-01", "2021-03-31"),
    crash_percentage=-0.3,
    recovery_period=("2021-04-01", "2021-06-30"),
    recovery_percentage=0.2
)

# 模擬流動性危機
liquidity_result = stress_tester.simulate_liquidity_crisis(
    crisis_period=("2021-05-01", "2021-05-31"),
    volume_reduction=0.8,
    slippage_increase=5.0,
    spread_increase=3.0
)

# 模擬波動率衝擊
volatility_result = stress_tester.simulate_volatility_shock(
    shock_period=("2021-07-01", "2021-07-31"),
    volatility_multiplier=3.0
)
```

## 6. 敏感性和穩健性分析

使用 `BacktestAnalyzer` 進行敏感性和穩健性分析：

```python
# 敏感性分析
def param_backtest(stop_loss):
    # 創建回測引擎
    engine = BacktestEngine(cash=100000.0)
    
    # 添加資料
    engine.add_data(data=data)
    
    # 添加策略
    engine.add_strategy(ModelSignalStrategy, model=model, stop_loss=stop_loss)
    
    # 執行回測
    return engine.run()

# 執行敏感性分析
sensitivity_df, sensitivity_plot = analyzer.perform_sensitivity_analysis(
    parameter_name="stop_loss",
    parameter_values=[0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08],
    backtest_func=param_backtest,
    metric_name="sharpe_ratio"
)

# 穩健性分析
def random_backtest():
    # 創建回測引擎
    engine = BacktestEngine(cash=100000.0)
    
    # 添加資料（隨機選擇時間段）
    start_idx = np.random.randint(0, len(data) - 252)
    end_idx = start_idx + 252
    test_data = data.iloc[start_idx:end_idx]
    
    engine.add_data(data=test_data)
    
    # 添加策略
    engine.add_strategy(ModelSignalStrategy, model=model)
    
    # 執行回測
    return engine.run()

# 執行穩健性分析
robustness_df, robustness_plot = analyzer.perform_robustness_analysis(
    backtest_func=random_backtest,
    num_simulations=100,
    metric_name="sharpe_ratio"
)
```

## 7. 最佳實踐

### 7.1 防止前瞻偏差

在回測中嚴格防止前瞻偏差：

- 確保模型只使用當前時間點之前的資料進行訓練和預測
- 使用時間序列交叉驗證進行模型評估
- 在特徵工程中避免使用未來資訊
- 使用 `TimeSeriesSplit` 進行資料分割

### 7.2 樣本內/樣本外測試

進行樣本內和樣本外測試：

```python
# 樣本內測試
in_sample_data = data[data["date"] < "2020-01-01"]
in_sample_result = run_backtest(in_sample_data)

# 樣本外測試
out_sample_data = data[data["date"] >= "2020-01-01"]
out_sample_result = run_backtest(out_sample_data)
```

### 7.3 避免過度擬合

避免回測過度擬合：

- 限制策略參數的數量
- 使用穩健性分析評估策略在不同市場條件下的表現
- 避免過度優化參數
- 使用樣本外測試驗證策略表現

### 7.4 考慮交易成本

在回測中考慮所有交易成本：

- 手續費
- 滑價
- 稅費
- 價差
- 市場衝擊

### 7.5 評估策略風險

全面評估策略風險：

- 最大回撤
- 波動率
- 風險調整收益（夏普比率、索提諾比率、卡爾馬比率）
- 壓力測試結果
- 下行風險
