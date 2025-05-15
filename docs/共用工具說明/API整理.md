# API 整理

## 目錄

- [API 概述](#api-概述)
- [RESTful API](#restful-api)
- [WebSocket API](#websocket-api)
- [API 認證](#api-認證)
- [錯誤處理](#錯誤處理)
- [速率限制](#速率限制)
- [API 版本控制](#api-版本控制)
- [API 文檔](#api-文檔)

## API 概述

AI 股票自動交易系統提供了一組 API，用於與系統進行交互，獲取數據，執行交易，管理策略等。API 分為 RESTful API 和 WebSocket API 兩種類型，分別用於不同的交互場景。

### API 設計原則

- **一致性**：所有 API 遵循一致的設計風格和命名規範
- **簡潔性**：API 設計簡潔明了，易於理解和使用
- **安全性**：所有 API 都經過安全性考慮，包括認證、授權和數據加密
- **可擴展性**：API 設計考慮了未來的擴展需求
- **文檔完整**：所有 API 都有完整的文檔說明

### API 基本信息

- **基礎 URL**：`https://api.example.com/v1`
- **API 版本**：v1
- **數據格式**：JSON
- **認證方式**：API Key + Secret
- **請求方法**：GET, POST, PUT, DELETE

## RESTful API

RESTful API 是基於 HTTP 協議的 API，用於執行各種操作，如獲取數據、執行交易、管理策略等。

### 市場數據 API

#### 獲取股票價格

```
GET /market/price
```

**參數**：

| 參數名 | 類型 | 必填 | 描述 |
|-------|------|------|------|
| symbol | string | 是 | 股票代碼 |
| interval | string | 否 | 時間間隔，如 1m, 5m, 1h, 1d，默認為 1d |
| start_date | string | 否 | 開始日期，格式為 YYYY-MM-DD |
| end_date | string | 否 | 結束日期，格式為 YYYY-MM-DD |
| limit | integer | 否 | 返回數據的最大條數，默認為 100 |

**響應**：

```json
{
  "status": "success",
  "data": [
    {
      "symbol": "2330.TW",
      "timestamp": "2023-01-01T00:00:00Z",
      "open": 500.0,
      "high": 505.0,
      "low": 495.0,
      "close": 502.0,
      "volume": 10000000
    },
    ...
  ]
}
```

#### 獲取技術指標

```
GET /market/indicators
```

**參數**：

| 參數名 | 類型 | 必填 | 描述 |
|-------|------|------|------|
| symbol | string | 是 | 股票代碼 |
| indicators | string | 是 | 技術指標列表，多個指標用逗號分隔，如 SMA,RSI,MACD |
| interval | string | 否 | 時間間隔，如 1m, 5m, 1h, 1d，默認為 1d |
| start_date | string | 否 | 開始日期，格式為 YYYY-MM-DD |
| end_date | string | 否 | 結束日期，格式為 YYYY-MM-DD |
| params | object | 否 | 指標參數，如 {"SMA": {"window": 20}, "RSI": {"window": 14}} |

**響應**：

```json
{
  "status": "success",
  "data": {
    "symbol": "2330.TW",
    "indicators": {
      "SMA": [
        {
          "timestamp": "2023-01-01T00:00:00Z",
          "value": 498.5
        },
        ...
      ],
      "RSI": [
        {
          "timestamp": "2023-01-01T00:00:00Z",
          "value": 65.2
        },
        ...
      ]
    }
  }
}
```

### 交易 API

#### 創建訂單

```
POST /trade/orders
```

**請求體**：

```json
{
  "symbol": "2330.TW",
  "side": "BUY",
  "type": "LIMIT",
  "quantity": 1000,
  "price": 500.0,
  "time_in_force": "GTC"
}
```

**響應**：

```json
{
  "status": "success",
  "data": {
    "order_id": "12345678",
    "symbol": "2330.TW",
    "side": "BUY",
    "type": "LIMIT",
    "quantity": 1000,
    "price": 500.0,
    "time_in_force": "GTC",
    "status": "NEW",
    "created_at": "2023-01-01T00:00:00Z"
  }
}
```

#### 取消訂單

```
DELETE /trade/orders/{order_id}
```

**參數**：

| 參數名 | 類型 | 必填 | 描述 |
|-------|------|------|------|
| order_id | string | 是 | 訂單 ID |

**響應**：

```json
{
  "status": "success",
  "data": {
    "order_id": "12345678",
    "status": "CANCELED",
    "canceled_at": "2023-01-01T00:05:00Z"
  }
}
```

#### 獲取訂單狀態

```
GET /trade/orders/{order_id}
```

**參數**：

| 參數名 | 類型 | 必填 | 描述 |
|-------|------|------|------|
| order_id | string | 是 | 訂單 ID |

**響應**：

```json
{
  "status": "success",
  "data": {
    "order_id": "12345678",
    "symbol": "2330.TW",
    "side": "BUY",
    "type": "LIMIT",
    "quantity": 1000,
    "price": 500.0,
    "time_in_force": "GTC",
    "status": "FILLED",
    "filled_quantity": 1000,
    "filled_price": 500.0,
    "created_at": "2023-01-01T00:00:00Z",
    "updated_at": "2023-01-01T00:01:00Z"
  }
}
```

### 策略 API

#### 獲取策略列表

```
GET /strategy/list
```

**響應**：

```json
{
  "status": "success",
  "data": [
    {
      "strategy_id": "momentum_01",
      "name": "Momentum Strategy",
      "description": "A momentum-based trading strategy",
      "status": "active",
      "created_at": "2023-01-01T00:00:00Z"
    },
    ...
  ]
}
```

#### 創建策略

```
POST /strategy/create
```

**請求體**：

```json
{
  "name": "Mean Reversion Strategy",
  "description": "A mean reversion trading strategy",
  "type": "mean_reversion",
  "parameters": {
    "window": 20,
    "std_dev": 2.0
  },
  "symbols": ["2330.TW", "2317.TW"],
  "status": "active"
}
```

**響應**：

```json
{
  "status": "success",
  "data": {
    "strategy_id": "mean_reversion_01",
    "name": "Mean Reversion Strategy",
    "description": "A mean reversion trading strategy",
    "type": "mean_reversion",
    "parameters": {
      "window": 20,
      "std_dev": 2.0
    },
    "symbols": ["2330.TW", "2317.TW"],
    "status": "active",
    "created_at": "2023-01-01T00:00:00Z"
  }
}
```

### 回測 API

#### 執行回測

```
POST /backtest/run
```

**請求體**：

```json
{
  "strategy_id": "momentum_01",
  "start_date": "2022-01-01",
  "end_date": "2022-12-31",
  "initial_capital": 1000000,
  "commission": 0.001,
  "slippage": 0.001
}
```

**響應**：

```json
{
  "status": "success",
  "data": {
    "backtest_id": "bt_12345678",
    "strategy_id": "momentum_01",
    "start_date": "2022-01-01",
    "end_date": "2022-12-31",
    "initial_capital": 1000000,
    "final_capital": 1200000,
    "total_return": 0.2,
    "annualized_return": 0.18,
    "sharpe_ratio": 1.5,
    "max_drawdown": 0.1,
    "trades": 50,
    "win_rate": 0.6,
    "status": "completed",
    "created_at": "2023-01-01T00:00:00Z",
    "completed_at": "2023-01-01T00:05:00Z"
  }
}
```

## WebSocket API

WebSocket API 提供了實時數據流，用於接收市場數據、訂單更新、交易信號等實時信息。

### 連接 WebSocket

```
wss://api.example.com/v1/ws
```

### 訂閱市場數據

```json
{
  "action": "subscribe",
  "channel": "market_data",
  "symbols": ["2330.TW", "2317.TW"]
}
```

### 訂閱訂單更新

```json
{
  "action": "subscribe",
  "channel": "order_updates",
  "order_ids": ["12345678", "12345679"]
}
```

### 訂閱交易信號

```json
{
  "action": "subscribe",
  "channel": "trade_signals",
  "strategy_ids": ["momentum_01", "mean_reversion_01"]
}
```

### 市場數據消息

```json
{
  "channel": "market_data",
  "data": {
    "symbol": "2330.TW",
    "timestamp": "2023-01-01T00:00:00Z",
    "price": 502.0,
    "volume": 10000,
    "bid": 501.5,
    "ask": 502.5
  }
}
```

### 訂單更新消息

```json
{
  "channel": "order_updates",
  "data": {
    "order_id": "12345678",
    "status": "FILLED",
    "filled_quantity": 1000,
    "filled_price": 500.0,
    "timestamp": "2023-01-01T00:01:00Z"
  }
}
```

### 交易信號消息

```json
{
  "channel": "trade_signals",
  "data": {
    "strategy_id": "momentum_01",
    "symbol": "2330.TW",
    "signal": "BUY",
    "strength": 0.8,
    "timestamp": "2023-01-01T00:00:00Z"
  }
}
```

## API 認證

所有 API 請求都需要進行認證，以確保安全性。認證使用 API Key 和 Secret 進行。

### 獲取 API Key 和 Secret

1. 登錄系統管理界面
2. 導航到 API 管理頁面
3. 點擊「創建 API Key」按鈕
4. 系統將生成 API Key 和 Secret
5. 妥善保存 API Key 和 Secret，Secret 只顯示一次

### RESTful API 認證

RESTful API 使用 API Key 和簽名進行認證。簽名的生成方式如下：

1. 將請求參數按字母順序排序
2. 將排序後的參數拼接成字符串，格式為 `key1=value1&key2=value2`
3. 使用 Secret 對拼接後的字符串進行 HMAC-SHA256 加密
4. 將加密後的結果轉換為 Base64 編碼

請求頭中需要包含以下字段：

- `X-API-Key`：API Key
- `X-Signature`：簽名
- `X-Timestamp`：請求時間戳（毫秒）

### WebSocket API 認證

WebSocket API 在連接時需要進行認證。認證方式如下：

1. 生成認證消息：

```json
{
  "action": "authenticate",
  "api_key": "your_api_key",
  "timestamp": 1609459200000,
  "signature": "your_signature"
}
```

2. 發送認證消息到 WebSocket 服務器
3. 服務器驗證認證信息，返回認證結果

## 錯誤處理

API 使用標準的 HTTP 狀態碼和錯誤響應格式來表示錯誤。

### HTTP 狀態碼

- `200 OK`：請求成功
- `400 Bad Request`：請求參數錯誤
- `401 Unauthorized`：認證失敗
- `403 Forbidden`：權限不足
- `404 Not Found`：資源不存在
- `429 Too Many Requests`：請求頻率超過限制
- `500 Internal Server Error`：服務器內部錯誤

### 錯誤響應格式

```json
{
  "status": "error",
  "code": "invalid_parameter",
  "message": "Invalid parameter: symbol",
  "details": {
    "parameter": "symbol",
    "reason": "Symbol does not exist"
  }
}
```

### 常見錯誤碼

| 錯誤碼 | 描述 |
|-------|------|
| `invalid_parameter` | 無效的參數 |
| `missing_parameter` | 缺少必要參數 |
| `authentication_failed` | 認證失敗 |
| `permission_denied` | 權限不足 |
| `resource_not_found` | 資源不存在 |
| `rate_limit_exceeded` | 超過請求頻率限制 |
| `internal_error` | 服務器內部錯誤 |

## 速率限制

為了保護 API 服務器不被過度使用，API 實施了速率限制。

### 限制規則

- 每個 API Key 每分鐘最多可以發送 60 個請求
- 每個 IP 地址每分鐘最多可以發送 30 個請求
- 某些特定的 API 端點可能有更嚴格的限制

### 限制響應

當超過速率限制時，API 將返回 `429 Too Many Requests` 狀態碼，並在響應頭中包含以下字段：

- `X-RateLimit-Limit`：速率限制的上限
- `X-RateLimit-Remaining`：當前時間窗口內剩餘的請求數
- `X-RateLimit-Reset`：速率限制重置的時間（Unix 時間戳）

### 處理速率限制

當收到速率限制響應時，客戶端應該等待一段時間再重試請求。建議的做法是：

1. 讀取 `X-RateLimit-Reset` 頭，計算需要等待的時間
2. 等待指定的時間
3. 重試請求

## API 版本控制

API 使用 URL 路徑中的版本號進行版本控制，以確保向後兼容性。

### 版本格式

版本號格式為 `v{major}`，例如 `v1`、`v2` 等。

### 版本更新策略

- **主版本更新**：當 API 有不兼容的更改時，會增加主版本號
- **次版本更新**：當 API 有向後兼容的功能增強時，不會更改版本號，但會在文檔中說明

### 版本生命週期

- **活躍版本**：當前最新的主版本，接收所有更新和修復
- **維護版本**：舊版本，只接收安全修復和關鍵錯誤修復
- **棄用版本**：即將停止支持的版本，不再接收更新
- **停止支持版本**：已停止支持的版本，不再可用

## API 文檔

完整的 API 文檔可以通過以下方式獲取：

### 在線文檔

在線 API 文檔提供了交互式的 API 探索和測試功能，可以通過以下 URL 訪問：

```
https://api.example.com/docs
```

### OpenAPI 規範

API 遵循 OpenAPI 3.0 規範，可以通過以下 URL 獲取 OpenAPI 規範文件：

```
https://api.example.com/openapi.json
```

### 客戶端 SDK

為了方便開發者使用 API，系統提供了多種語言的客戶端 SDK：

- **Python SDK**：[GitHub 倉庫](https://github.com/example/api-python-sdk)
- **JavaScript SDK**：[GitHub 倉庫](https://github.com/example/api-js-sdk)
- **Java SDK**：[GitHub 倉庫](https://github.com/example/api-java-sdk)
- **C# SDK**：[GitHub 倉庫](https://github.com/example/api-csharp-sdk)
