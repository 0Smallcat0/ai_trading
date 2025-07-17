# API 整合指南

**版本**: v2.0
**更新日期**: 2025-07-17
**適用範圍**: 系統整合開發者和第三方開發者

## 📋 概述

本指南詳細說明如何將 AI 股票自動交易系統的 API 整合到第三方應用程式中，包括系統架構設計、API 整合模式和最佳實踐。

## 🌐 RESTful API 設計

AI 股票自動交易系統採用 RESTful 架構設計 API，確保一致性和可擴展性：

### API 設計原則

- **資源導向**：API 端點代表資源，而非操作
- **HTTP 方法**：正確使用 GET、POST、PUT、DELETE 等 HTTP 方法
- **狀態碼**：使用標準 HTTP 狀態碼表示操作結果
- **版本控制**：API 路徑包含版本號，如 `/api/v1/`
- **分頁**：大型集合支援分頁查詢
- **過濾和排序**：支援資源過濾和排序
- **冪等性**：確保 PUT 和 DELETE 操作的冪等性
- **無狀態**：每個請求包含所有必要的資訊

### 主要 API 端點

```
/api/v1/auth           # 認證相關
/api/v1/users          # 用戶管理
/api/v1/strategies     # 策略管理
/api/v1/portfolios     # 投資組合管理
/api/v1/orders         # 訂單管理
/api/v1/market-data    # 市場數據
/api/v1/backtest       # 回測功能
/api/v1/notifications  # 通知管理
/api/v1/system         # 系統管理
/api/v1/risk           # 風險管理
/api/v1/reports        # 報告生成
/api/v1/ai-models      # AI 模型管理
```

## 📝 OpenAPI 3.0 規範

系統 API 完全符合 OpenAPI 3.0 規範，提供標準化的 API 文檔：

### 文檔資源

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI 規範**: `http://localhost:8000/openapi.json`

### 規範特性

- 完整的端點描述
- 請求/回應模式定義
- 認證方式說明
- 錯誤代碼文檔
- 互動式 API 測試

## 🔧 系統整合架構

### 整合模式

#### 1. 直接 API 整合
```python
import requests

class TradingSystemClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def get_portfolio(self, portfolio_id):
        response = requests.get(
            f'{self.base_url}/api/v1/portfolios/{portfolio_id}',
            headers=self.headers
        )
        return response.json()
```

#### 2. SDK 整合
```python
from trading_system_sdk import TradingClient

client = TradingClient(
    api_key='your_api_key',
    environment='production'  # or 'sandbox'
)

# 獲取投資組合
portfolio = client.portfolios.get('portfolio_id')

# 執行交易
order = client.orders.create({
    'symbol': 'AAPL',
    'quantity': 100,
    'side': 'buy',
    'type': 'market'
})
```

#### 3. Webhook 整合
```python
from flask import Flask, request

app = Flask(__name__)

@app.route('/webhook/trading-events', methods=['POST'])
def handle_trading_event():
    event = request.json

    if event['type'] == 'order.filled':
        # 處理訂單成交事件
        process_order_filled(event['data'])
    elif event['type'] == 'risk.alert':
        # 處理風險警報
        process_risk_alert(event['data'])

    return {'status': 'received'}
```

## 🔐 認證與安全

### JWT 認證流程

```python
# 1. 獲取訪問令牌
def authenticate(username, password):
    response = requests.post('/api/v1/auth/login', {
        'username': username,
        'password': password
    })
    return response.json()['access_token']

# 2. 使用令牌進行 API 調用
def make_authenticated_request(token, endpoint):
    headers = {'Authorization': f'Bearer {token}'}
    return requests.get(endpoint, headers=headers)
```

### API 金鑰管理

```python
# 環境變數配置
import os

API_KEY = os.getenv('TRADING_SYSTEM_API_KEY')
API_SECRET = os.getenv('TRADING_SYSTEM_API_SECRET')

# 安全存儲
from cryptography.fernet import Fernet

def encrypt_api_key(key):
    f = Fernet(Fernet.generate_key())
    return f.encrypt(key.encode())
```

## 📊 數據同步策略

### 即時數據同步

```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    if data['type'] == 'market_data':
        update_local_market_data(data['payload'])
    elif data['type'] == 'portfolio_update':
        update_local_portfolio(data['payload'])

def on_error(ws, error):
    print(f"WebSocket error: {error}")

def on_close(ws):
    print("WebSocket connection closed")

# 建立 WebSocket 連接
ws = websocket.WebSocketApp(
    "ws://localhost:8000/ws/market-data",
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)
```

### 批量數據同步

```python
def sync_historical_data(start_date, end_date):
    """同步歷史數據"""
    page = 1
    while True:
        response = requests.get(f'/api/v1/market-data/history', {
            'start_date': start_date,
            'end_date': end_date,
            'page': page,
            'limit': 1000
        })

        data = response.json()
        if not data['results']:
            break

        # 處理數據
        process_market_data(data['results'])
        page += 1
```

## 🚦 錯誤處理與重試

### 錯誤處理策略

```python
import time
from requests.exceptions import RequestException

def api_call_with_retry(url, max_retries=3, backoff_factor=1):
    """帶重試機制的 API 調用"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()

        except RequestException as e:
            if attempt == max_retries - 1:
                raise e

            wait_time = backoff_factor * (2 ** attempt)
            time.sleep(wait_time)
```

### 斷路器模式

```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN

    def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e
```

## 📈 性能優化

### 連接池管理

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

session = requests.Session()

# 配置重試策略
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
)

adapter = HTTPAdapter(
    max_retries=retry_strategy,
    pool_connections=20,
    pool_maxsize=20
)

session.mount("http://", adapter)
session.mount("https://", adapter)
```

### 快取策略

```python
import redis
import json
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(expiration=300):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"

            # 嘗試從快取獲取
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return json.loads(cached_result)

            # 執行函數並快取結果
            result = func(*args, **kwargs)
            redis_client.setex(
                cache_key,
                expiration,
                json.dumps(result)
            )
            return result
        return wrapper
    return decorator
```

## 🔍 監控與日誌

### API 調用監控

```python
import logging
import time
from functools import wraps

def monitor_api_calls(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            logging.info(f"API call {func.__name__} succeeded in {duration:.2f}s")
            return result

        except Exception as e:
            duration = time.time() - start_time
            logging.error(f"API call {func.__name__} failed in {duration:.2f}s: {e}")
            raise

    return wrapper
```

### 健康檢查

```python
def health_check():
    """系統健康檢查"""
    checks = {
        'api_server': check_api_server(),
        'database': check_database(),
        'redis': check_redis(),
        'external_apis': check_external_apis()
    }

    all_healthy = all(checks.values())

    return {
        'status': 'healthy' if all_healthy else 'unhealthy',
        'checks': checks,
        'timestamp': time.time()
    }
```

## 🎯 最佳實踐

### 1. API 版本管理
- 使用語義化版本控制
- 向後兼容性保證
- 廢棄 API 的優雅處理

### 2. 安全最佳實踐
- 使用 HTTPS 進行所有通信
- 實施適當的速率限制
- 定期輪換 API 金鑰
- 記錄所有 API 訪問

### 3. 性能最佳實踐
- 實施適當的快取策略
- 使用連接池
- 批量處理減少 API 調用
- 監控 API 性能指標

### 4. 錯誤處理最佳實踐
- 實施指數退避重試
- 使用斷路器模式
- 提供詳細的錯誤信息
- 記錄所有錯誤

## 📚 相關文檔

- [API 使用手冊](./API使用手冊.md) - 詳細的 API 使用說明
- [API 文檔](./API文檔.md) - 服務層 API 參考
- [系統架構](./系統架構.md) - 系統整體架構設計

---

**文檔版本**: v2.0
**最後更新**: 2025-07-17
**維護團隊**: AI Trading System Integration Team