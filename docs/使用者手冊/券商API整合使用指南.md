# 券商 API 整合使用指南

**版本**: v1.1
**更新日期**: 2025-07-17
**適用範圍**: 終端用戶和交易員

## 概述

本指南將幫助您快速上手使用 AI 交易系統的券商 API 整合功能，包括永豐證券和 Interactive Brokers 的 API 連接和交易操作。

**變更歷史**:
- v1.1 (2025-07-17): 添加版本資訊，文檔標準化
- v1.0 (2025-07-10): 初始版本，券商API整合指南

## 🚀 快速開始

### 1. 環境準備

#### 安裝依賴套件
```bash
# 永豐證券 API
pip install shioaji

# Interactive Brokers API
pip install ibapi

# 其他依賴
pip install pandas numpy
```

#### 設定環境變數
```bash
# 永豐證券
export BROKER_API_KEY="your_shioaji_api_key"
export BROKER_API_SECRET="your_shioaji_api_secret"
export BROKER_PERSON_ID="your_person_id"

# Interactive Brokers (通常不需要 API 金鑰)
export IB_HOST="127.0.0.1"
export IB_PORT="7497"
export IB_CLIENT_ID="1"
```

### 2. 基本使用

#### 永豐證券 API 連接
```python
from src.execution.shioaji_adapter import ShioajiAdapter
from src.execution.broker_base import Order, OrderType

# 初始化適配器
adapter = ShioajiAdapter(
    api_key="your_api_key",
    api_secret="your_api_secret",
    person_id="your_person_id"
)

# 連接 API
if adapter.connect():
    print("✅ 成功連接到永豐證券 API")
    
    # 查詢帳戶資訊
    account_info = adapter.get_account_info()
    print(f"帳戶餘額: {account_info.get('cash', 0):,.0f}")
    
    # 查詢持倉
    positions = adapter.get_positions()
    for stock_id, position in positions.items():
        print(f"{stock_id}: {position['shares']} 股")
else:
    print("❌ 連接失敗")
```

#### Interactive Brokers API 連接
```python
from src.execution.ib_adapter import IBAdapter

# 初始化適配器 (需要先啟動 TWS 或 IB Gateway)
adapter = IBAdapter(
    host="127.0.0.1",
    port=7497,  # TWS 端口
    client_id=1
)

# 連接 API
if adapter.connect():
    print("✅ 成功連接到 IB API")
    
    # 獲取連接資訊
    info = adapter.get_connection_info()
    print(f"連接狀態: {info}")
else:
    print("❌ 連接失敗")
```

## 📈 交易操作

### 1. 下單操作

#### 市價單
```python
from src.execution.broker_base import Order, OrderType

# 創建市價買單
order = Order(
    stock_id="2330",  # 台積電
    action="buy",
    quantity=1000,
    order_type=OrderType.MARKET
)

# 下單
order_id = adapter.place_order(order)
if order_id:
    print(f"✅ 訂單已提交，訂單 ID: {order_id}")
else:
    print("❌ 下單失敗")
```

#### 限價單
```python
# 創建限價買單
order = Order(
    stock_id="2330",
    action="buy",
    quantity=1000,
    price=500.0,  # 限價 500 元
    order_type=OrderType.LIMIT
)

order_id = adapter.place_order(order)
```

#### 美股交易 (使用 IB)
```python
# 美股限價單
order = Order(
    stock_id="AAPL",
    action="buy",
    quantity=100,
    price=150.0,
    order_type=OrderType.LIMIT
)

order_id = ib_adapter.place_order(order)
```

### 2. 訂單管理

#### 查詢訂單狀態
```python
# 查詢特定訂單
order = adapter.get_order(order_id)
if order:
    print(f"訂單狀態: {order.status.value}")
    print(f"已成交數量: {order.filled_quantity}")
    print(f"平均成交價: {order.filled_price}")

# 查詢所有訂單
all_orders = adapter.get_orders()
for order in all_orders:
    print(f"{order.order_id}: {order.status.value}")
```

#### 取消訂單
```python
# 取消訂單
if adapter.cancel_order(order_id):
    print("✅ 訂單已取消")
else:
    print("❌ 取消訂單失敗")
```

### 3. 市場資料

#### 獲取即時報價
```python
# 永豐證券
market_data = adapter.get_market_data("2330")
print(f"最新價格: {market_data.get('price', 0)}")
print(f"成交量: {market_data.get('volume', 0)}")

# Interactive Brokers
market_data = ib_adapter.get_market_data("AAPL")
print(f"買價: {market_data.get('bid', 0)}")
print(f"賣價: {market_data.get('ask', 0)}")
```

## 🔧 進階功能

### 1. 連接監控

#### 設定連接狀態回調
```python
def on_connection_status(status, message):
    print(f"連接狀態變更: {status} - {message}")

adapter.on_connection_status = on_connection_status
```

#### 檢查連接狀態
```python
# 獲取連接資訊
info = adapter.get_connection_info()
print(f"連接狀態: {info['connected']}")
print(f"最後心跳: {info.get('last_heartbeat', 'N/A')}")
print(f"連接錯誤次數: {info.get('connection_errors', 0)}")
```

#### 強制重連
```python
if adapter.force_reconnect():
    print("✅ 重連成功")
else:
    print("❌ 重連失敗")
```

### 2. 訂單狀態監控

#### 設定訂單狀態回調
```python
def on_order_status(order):
    print(f"訂單 {order.order_id} 狀態更新: {order.status.value}")
    if order.status == OrderStatus.FILLED:
        print(f"✅ 訂單已完全成交，成交價: {order.filled_price}")

adapter.on_order_status = on_order_status
```

### 3. 錯誤處理

#### 統一錯誤處理
```python
try:
    order_id = adapter.place_order(order)
except Exception as e:
    print(f"❌ 下單發生錯誤: {e}")
    # 檢查是否為連接問題
    if not adapter.connected:
        print("🔄 嘗試重新連接...")
        adapter.force_reconnect()
```

## 🛡️ 安全注意事項

### 1. API 金鑰管理
- ❌ 不要在代碼中硬編碼 API 金鑰
- ✅ 使用環境變數或配置文件
- ✅ 定期更換 API 金鑰
- ✅ 限制 API 權限範圍

### 2. 交易風險控制
```python
# 設定最大單筆交易金額
MAX_ORDER_VALUE = 100000  # 10萬元

def safe_place_order(adapter, order):
    order_value = order.quantity * order.price
    if order_value > MAX_ORDER_VALUE:
        print(f"❌ 訂單金額 {order_value:,.0f} 超過限制")
        return None
    
    return adapter.place_order(order)
```

### 3. 連接安全
- ✅ 使用 SSL/TLS 加密連接
- ✅ 驗證 API 端點憑證
- ✅ 監控異常連接活動

## 🔍 故障排除

### 常見問題

#### 1. 連接失敗
```python
# 檢查網路連接
import requests
try:
    response = requests.get("https://www.google.com", timeout=5)
    print("✅ 網路連接正常")
except:
    print("❌ 網路連接異常")

# 檢查 API 服務狀態
if not adapter.connected:
    print("🔍 檢查 API 金鑰和密鑰是否正確")
    print("🔍 檢查帳戶是否有 API 權限")
    print("🔍 檢查是否在交易時間內")
```

#### 2. 下單失敗
```python
# 檢查帳戶狀態
account_info = adapter.get_account_info()
if account_info.get('cash', 0) < order_value:
    print("❌ 帳戶餘額不足")

# 檢查股票代號
if not adapter._get_contract(order.stock_id):
    print("❌ 無效的股票代號")
```

#### 3. 資料延遲
```python
# 檢查訂閱狀態
market_data = adapter.get_market_data("2330")
if not market_data.get('timestamp'):
    print("🔄 重新訂閱市場資料...")
    # 重新訂閱邏輯
```

## 📞 技術支援

如果遇到問題，請檢查：
1. 📋 日誌文件 (`logs/shioaji.log`, `logs/ib.log`)
2. 📊 連接狀態監控
3. 🔧 API 服務狀態
4. 📖 券商官方文檔

更多詳細資訊請參考：
- [券商API設定教程](券商API設定教程.md)
- [API 技術文檔](../modules/broker_api_integration.md)
