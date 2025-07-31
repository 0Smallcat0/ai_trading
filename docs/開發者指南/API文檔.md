# 服務層 API 文檔

**版本**: v1.0  
**更新日期**: 2025-01-15  
**適用範圍**: 開發者和系統集成商

## 📋 概述

本文檔描述了 AI 股票自動交易系統服務層的 API 接口，包括服務管理、回測系統、交易執行等核心功能。這些 API 可用於系統集成、擴展開發和自定義應用。

## 🔧 服務管理 API

服務管理 API 提供了統一的服務註冊、發現和生命週期管理功能。

### ServiceManager

服務管理器是系統的核心組件，負責管理所有服務的生命週期。

#### 獲取服務管理器

```python
from src.core.services import get_service_manager

# 獲取全局服務管理器實例
manager = get_service_manager()
```

#### 註冊服務

```python
# 註冊現有服務實例
service = MyCustomService("custom_service", "1.0.0")
success = manager.register_service(service)

# 註冊服務類型（自動實例化）
service = manager.register_service_type(MyCustomService, "custom_service", version="1.0.0")
```

#### 獲取服務

```python
# 獲取服務實例
service = manager.get_service("service_name")

# 列出所有服務
services = manager.list_services()
```

#### 服務控制

```python
# 啟動服務
success = manager.start_service("service_name")

# 停止服務
success = manager.stop_service("service_name")

# 重啟服務
success = manager.restart_service("service_name")
```

### UIServiceClient

UI 服務客戶端提供了簡化的服務訪問接口，專為 UI 層設計。

```python
from src.core.services import get_ui_client

# 獲取全局 UI 客戶端實例
client = get_ui_client()

# 檢查服務是否可用
is_available = client.is_service_available("BacktestService")

# 獲取所有可用功能
features = client.get_available_features()
```

## 🔄 回測系統 API

回測系統 API 提供了策略回測和績效分析功能。

### BacktestService

```python
from src.core.backtest import BacktestService, BacktestConfig

# 創建回測服務
backtest_service = BacktestService()

# 創建回測配置
config = BacktestConfig(
    strategy_name="double_ma",
    symbols=["AAPL", "GOOGL"],
    start_date="2023-01-01",
    end_date="2023-12-31",
    initial_capital=100000.0
)

# 啟動回測
backtest_id = backtest_service.start_backtest(config)

# 獲取回測狀態
status = backtest_service.get_backtest_status(backtest_id)

# 獲取回測結果
results = backtest_service.get_backtest_results(backtest_id)
```

### BacktestEngine

```python
from src.core.backtest import BacktestEngine

# 創建回測引擎
engine = BacktestEngine()

# 執行回測
results = engine.run_backtest(
    signals=signals_df,
    market_data=market_data_df,
    initial_capital=100000.0,
    commission=0.001,
    slippage=0.001
)
```

### 績效指標計算

```python
from src.core.backtest import calculate_performance_metrics

# 計算績效指標
metrics = calculate_performance_metrics(results, config)

# 獲取關鍵指標
total_return = metrics.total_return
sharpe_ratio = metrics.sharpe_ratio
max_drawdown = metrics.max_drawdown
```

## 🔐 認證服務 API

```python
# 通過服務管理器獲取
auth_service = manager.get_service("AuthenticationService")

# 用戶認證
success = auth_service.authenticate(username, password)

# 檢查認證狀態
is_authenticated = auth_service.is_authenticated(username)
```

## 📊 數據服務 API

```python
# 通過服務管理器獲取
data_service = manager.get_service("DataService")

# 獲取市場數據
market_data = data_service.get_market_data(
    symbols=["AAPL", "GOOGL"],
    start_date="2023-01-01",
    end_date="2023-12-31"
)
```

## 💹 交易服務 API

```python
# 通過服務管理器獲取
trading_service = manager.get_service("TradingService")

# 下單
order_id = trading_service.place_order({
    "symbol": "AAPL",
    "order_type": "LIMIT",
    "side": "BUY",
    "quantity": 100,
    "price": 150.0
})

# 獲取訂單狀態
order_status = trading_service.get_order_status(order_id)
```

## ⚠️ 風險管理服務 API

```python
# 通過服務管理器獲取
risk_service = manager.get_service("RiskManagementService")

# 獲取風險指標
risk_metrics = risk_service.get_risk_metrics()

# 檢查倉位風險
is_safe = risk_service.check_position_risk({
    "symbol": "AAPL",
    "quantity": 1000,
    "price": 150.0
})
```

## 🔧 自定義服務開發

### 創建自定義服務

```python
from src.core.services import BaseService

class MyCustomService(BaseService):
    def __init__(self, name="MyCustomService", version="1.0.0"):
        super().__init__(name, version)
    
    def _initialize(self):
        # 初始化邏輯
        self.logger.info("初始化自定義服務")
    
    def _health_check(self):
        # 健康檢查邏輯
        return {"status": "healthy"}
    
    # 自定義方法
    def my_custom_method(self, param):
        return f"處理參數: {param}"
```

### 註冊自定義服務

```python
# 創建服務實例
my_service = MyCustomService()

# 註冊到服務管理器
manager = get_service_manager()
manager.register_service(my_service)

# 使用服務
service = manager.get_service("MyCustomService")
result = service.my_custom_method("test")
```

## 🔄 服務依賴管理

```python
# 添加依賴關係
manager.add_dependency("ServiceA", "ServiceB")  # ServiceA 依賴 ServiceB

# 獲取服務依賴
deps = manager.registry.get_dependencies("ServiceA")

# 按依賴順序啟動所有服務
results = manager.start_all_services()
```

## 📝 最佳實踐

### 1. 服務設計原則
- 單一職責：每個服務只負責一個業務領域
- 無狀態：服務應該是無狀態的，狀態存儲在數據層
- 冪等性：API 操作應該是冪等的
- 錯誤處理：提供清晰的錯誤信息和狀態碼

### 2. API 使用建議
- 使用服務管理器統一管理服務生命週期
- 通過 UI 客戶端簡化 UI 層的服務訪問
- 實現適當的錯誤處理和重試機制
- 使用健康檢查監控服務狀態

### 3. 性能優化
- 使用快取減少重複計算
- 實現異步處理提升響應速度
- 合理設置超時和重試策略
- 監控 API 性能指標
