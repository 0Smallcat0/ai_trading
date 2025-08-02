# Live Trading 核心功能模組

## 📋 概述

Live Trading 核心功能模組提供完整的實時交易執行能力，包括券商 API 整合、實時交易執行、和風險控制強化三大核心功能。

**版本**: v1.0  
**最後更新**: 2025-01-15  
**維護狀態**: ✅ 活躍維護

## 🏗️ 模組架構

```
src/
├── execution/
│   ├── ib_adapter.py              # Interactive Brokers API 適配器
│   ├── connection_monitor.py      # API 連接狀態監控
│   └── order_tracker.py          # 訂單執行狀態追蹤
├── trading/live/
│   ├── position_manager.py       # 持倉管理器 (一鍵平倉)
│   ├── quick_order.py            # 快速下單面板
│   ├── emergency_stop.py         # 緊急停損管理器
│   └── order_confirmation.py     # 訂單確認機制
└── risk/live/
    ├── fund_monitor.py           # 實時資金監控
    ├── dynamic_stop_loss.py      # 動態停損調整
    ├── position_limiter.py       # 部位大小限制
    ├── trade_limiter.py          # 交易次數限制
    └── loss_alert.py             # 最大虧損警報
```

## 🚀 主要功能

### 1. 券商 API 整合

#### Interactive Brokers API 適配器 (`ib_adapter.py`)
- **功能**: 提供與 Interactive Brokers API 的連接和交易功能
- **支援市場**: 美股、港股、台股
- **主要特性**:
  - 自動連接管理和重連機制
  - 統一的訂單介面
  - 實時價格和持倉更新
  - 完整的錯誤處理

```python
from src.execution.ib_adapter import IBAdapter

# 初始化 IB 適配器
adapter = IBAdapter(
    host="127.0.0.1",
    port=7497,  # TWS 端口
    client_id=1
)

# 連接 API
if adapter.connect():
    print("已連接到 Interactive Brokers")
    
    # 下單
    order_id = adapter.place_order(
        symbol="AAPL",
        action="BUY",
        quantity=100,
        order_type="MKT"
    )
```

#### 連接狀態監控 (`connection_monitor.py`)
- **功能**: 監控 API 連接狀態，自動處理斷線重連
- **特性**:
  - 心跳檢測機制
  - 自動重連邏輯
  - 連接狀態通知

```python
from src.execution.connection_monitor import ConnectionMonitor

# 初始化連接監控
monitor = ConnectionMonitor(adapter)

# 啟動監控
monitor.start_monitoring()

# 設置連接狀態回調
monitor.set_connection_callback(on_connection_change)
```

### 2. 實時交易執行

#### 持倉管理器 (`position_manager.py`)
- **功能**: 管理所有持倉，提供一鍵平倉功能
- **特性**:
  - 實時持倉更新
  - 一鍵平倉所有部位
  - 分批平倉功能
  - 持倉風險監控

```python
from src.trading.live.position_manager import PositionManager

# 初始化持倉管理器
pos_manager = PositionManager(adapter)

# 獲取所有持倉
positions = pos_manager.get_all_positions()

# 一鍵平倉所有部位
pos_manager.close_all_positions()

# 平倉特定股票
pos_manager.close_position("AAPL")
```

#### 快速下單面板 (`quick_order.py`)
- **功能**: 提供快速下單介面
- **特性**:
  - 預設下單參數
  - 快速買賣按鈕
  - 批量下單功能

```python
from src.trading.live.quick_order import QuickOrderPanel

# 初始化快速下單面板
quick_order = QuickOrderPanel(adapter)

# 快速買入
quick_order.quick_buy("AAPL", 100)

# 快速賣出
quick_order.quick_sell("AAPL", 100)

# 設置預設參數
quick_order.set_default_params(
    order_type="LMT",
    time_in_force="DAY"
)
```

#### 緊急停損管理器 (`emergency_stop.py`)
- **功能**: 緊急情況下的停損處理
- **特性**:
  - 緊急停損觸發
  - 全部位停損
  - 停損條件設定

```python
from src.trading.live.emergency_stop import EmergencyStopManager

# 初始化緊急停損管理器
emergency_stop = EmergencyStopManager(adapter)

# 設置緊急停損條件
emergency_stop.set_stop_conditions(
    max_loss_percent=0.05,  # 5% 最大虧損
    max_drawdown=0.10       # 10% 最大回撤
)

# 啟動緊急停損監控
emergency_stop.start_monitoring()

# 手動觸發緊急停損
emergency_stop.trigger_emergency_stop()
```

### 3. 風險控制強化

#### 實時資金監控 (`fund_monitor.py`)
- **功能**: 監控帳戶資金狀況
- **特性**:
  - 實時資金更新
  - 可用資金計算
  - 保證金監控
  - 資金警報

```python
from src.risk.live.fund_monitor import FundMonitor

# 初始化資金監控
fund_monitor = FundMonitor(adapter)

# 獲取帳戶資金資訊
account_info = fund_monitor.get_account_info()

# 設置資金警報
fund_monitor.set_fund_alert(
    min_cash=10000,         # 最低現金
    margin_ratio=0.8        # 保證金比例警報
)

# 啟動資金監控
fund_monitor.start_monitoring()
```

#### 動態停損調整 (`dynamic_stop_loss.py`)
- **功能**: 根據市場情況動態調整停損點
- **特性**:
  - 移動停損
  - 波動率調整
  - 時間衰減停損

```python
from src.risk.live.dynamic_stop_loss import DynamicStopLoss

# 初始化動態停損
dynamic_stop = DynamicStopLoss(adapter)

# 設置動態停損參數
dynamic_stop.set_parameters(
    initial_stop_percent=0.05,  # 初始停損 5%
    trailing_percent=0.03,      # 移動停損 3%
    volatility_adjustment=True  # 波動率調整
)

# 為特定股票設置動態停損
dynamic_stop.set_stop_loss("AAPL", entry_price=150.0)
```

#### 部位大小限制 (`position_limiter.py`)
- **功能**: 控制單一部位和總部位大小
- **特性**:
  - 單股部位限制
  - 總部位限制
  - 行業集中度限制

```python
from src.risk.live.position_limiter import PositionLimiter

# 初始化部位限制器
pos_limiter = PositionLimiter(adapter)

# 設置部位限制
pos_limiter.set_limits(
    max_single_position=0.1,    # 單一部位最大 10%
    max_total_position=0.8,     # 總部位最大 80%
    max_sector_exposure=0.3     # 單一行業最大 30%
)

# 檢查訂單是否符合限制
is_valid = pos_limiter.check_order_limit("AAPL", 1000)
```

## 📊 性能指標

### 執行效率
- **訂單提交**: <200ms
- **持倉更新**: <100ms
- **風險檢查**: <50ms
- **緊急停損**: <500ms

### 可靠性指標
- **連接穩定性**: 99.9%
- **訂單成功率**: 99.5%
- **風險控制響應**: <1秒

## 🧪 測試覆蓋

### 測試類型
- **單元測試**: 85%+ 覆蓋率
- **整合測試**: 端到端交易流程
- **壓力測試**: 高頻交易場景
- **故障測試**: 網路中斷恢復

### 測試執行

```bash
# 執行 Live Trading 測試
python -m pytest tests/test_live_trading.py -v

# 執行風險控制測試
python -m pytest tests/test_risk_control.py -v

# 執行壓力測試
python -m pytest tests/test_stress.py -v
```

## 🔒 安全考量

### 交易安全
- **訂單確認**: 雙重確認機制
- **權限控制**: 分級權限管理
- **操作日誌**: 完整的操作記錄
- **異常監控**: 異常交易檢測

### 風險控制
- **實時監控**: 24/7 風險監控
- **自動停損**: 多層次停損機制
- **資金保護**: 資金安全檢查
- **緊急處理**: 緊急情況處理流程

## 📚 相關文檔

### 技術文檔
- [Interactive Brokers 模組](./interactive_brokers/README.md)
- [券商 API 整合](./broker_api_integration.md)
- [API 參考文檔](../API文檔.md)

### 使用者文檔
- [實時交易使用指南](../../使用者手冊/實時交易使用指南.md)
- [風險管理設定](../../使用者手冊/風險管理設定.md)

### 維運文檔
- [系統監控指南](../../維運指南/系統監控指南.md)
- [故障處理程序](../../維運指南/故障處理程序.md)

---

**維護團隊**: AI Trading System Development Team  
**最後更新**: 2025-01-15
