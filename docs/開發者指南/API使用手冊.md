# API 使用手冊

本手冊詳細介紹 AI 股票自動交易系統的 RESTful API 使用方法，幫助開發者快速整合和使用系統功能。

## 📚 目錄

1. [API 概覽](#api-概覽)
2. [認證與授權](#認證與授權)
3. [核心 API 端點](#核心-api-端點)
4. [請求與回應格式](#請求與回應格式)
5. [錯誤處理](#錯誤處理)
6. [速率限制](#速率限制)
7. [SDK 與範例](#sdk-與範例)
8. [最佳實踐](#最佳實踐)

---

## 🌐 API 概覽

### 基本資訊
- **基礎 URL**：`http://localhost:8000/api/v1`
- **協議**：HTTP/HTTPS
- **格式**：JSON
- **認證**：JWT Bearer Token
- **版本控制**：URL 路徑版本控制

### API 特性
- ✅ RESTful 設計原則
- 📚 OpenAPI 3.0 規範
- 🔄 自動 API 文件
- ⚡ 高效能異步處理
- 🔒 企業級安全標準
- 📝 完整的審計日誌

### 文檔資源
- **Swagger UI**：`http://localhost:8000/docs`
- **ReDoc**：`http://localhost:8000/redoc`
- **OpenAPI 規範**：`http://localhost:8000/openapi.json`

---

## 🔐 認證與授權

### JWT Token 認證

#### 1. 獲取 Token
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**回應範例**：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

#### 2. 使用 Token
```http
GET /api/v1/portfolio/summary
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 3. 刷新 Token
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 權限等級
- **Guest**：只讀市場數據
- **User**：基本交易功能
- **Premium**：高級策略和分析
- **Admin**：系統管理功能

---

## 🔄 核心 API 端點

### 1. 認證管理
| 方法 | 端點 | 描述 |
|------|------|------|
| POST | `/auth/login` | 用戶登入 |
| POST | `/auth/logout` | 用戶登出 |
| POST | `/auth/refresh` | 刷新 Token |
| GET | `/auth/profile` | 獲取用戶資料 |

### 2. 投資組合管理
| 方法 | 端點 | 描述 |
|------|------|------|
| GET | `/portfolio/summary` | 投資組合摘要 |
| GET | `/portfolio/positions` | 持倉明細 |
| GET | `/portfolio/performance` | 績效分析 |
| POST | `/portfolio/rebalance` | 投資組合再平衡 |

### 3. 交易執行
| 方法 | 端點 | 描述 |
|------|------|------|
| POST | `/orders` | 下單 |
| GET | `/orders` | 查詢訂單 |
| GET | `/orders/{order_id}` | 訂單詳情 |
| DELETE | `/orders/{order_id}` | 取消訂單 |
| GET | `/trades` | 交易記錄 |

### 4. 策略回測
| 方法 | 端點 | 描述 |
|------|------|------|
| POST | `/backtest` | 啟動回測 |
| GET | `/backtest/{backtest_id}` | 回測狀態 |
| GET | `/backtest/{backtest_id}/results` | 回測結果 |
| GET | `/backtest/history` | 回測歷史 |

### 5. 市場數據
| 方法 | 端點 | 描述 |
|------|------|------|
| GET | `/market/quotes` | 即時報價 |
| GET | `/market/history` | 歷史數據 |
| GET | `/market/indicators` | 技術指標 |
| GET | `/market/news` | 市場新聞 |

### 6. 風險管理
| 方法 | 端點 | 描述 |
|------|------|------|
| GET | `/risk/metrics` | 風險指標 |
| GET | `/risk/alerts` | 風險警報 |
| POST | `/risk/limits` | 設定風險限制 |
| GET | `/risk/reports` | 風險報告 |

---

## 📝 請求與回應格式

### 請求格式

#### 標準請求頭
```http
Content-Type: application/json
Authorization: Bearer {token}
Accept: application/json
User-Agent: YourApp/1.0
```

#### 分頁參數
```http
GET /api/v1/orders?page=1&limit=20&sort=created_at&order=desc
```

#### 過濾參數
```http
GET /api/v1/trades?symbol=AAPL&start_date=2024-01-01&end_date=2024-12-31
```

### 回應格式

#### 成功回應
```json
{
  "success": true,
  "data": {
    // 實際數據
  },
  "message": "操作成功",
  "timestamp": "2024-07-14T10:30:00Z"
}
```

#### 分頁回應
```json
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 100,
      "pages": 5
    }
  }
}
```

#### 錯誤回應
```json
{
  "success": false,
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "參數驗證失敗",
    "details": {
      "field": "symbol",
      "reason": "股票代碼格式不正確"
    }
  },
  "timestamp": "2024-07-14T10:30:00Z"
}
```

---

## ⚠️ 錯誤處理

### HTTP 狀態碼
| 狀態碼 | 說明 | 範例 |
|--------|------|------|
| 200 | 成功 | 請求成功處理 |
| 201 | 已創建 | 訂單創建成功 |
| 400 | 請求錯誤 | 參數格式錯誤 |
| 401 | 未授權 | Token 無效或過期 |
| 403 | 禁止訪問 | 權限不足 |
| 404 | 未找到 | 資源不存在 |
| 429 | 請求過多 | 超過速率限制 |
| 500 | 伺服器錯誤 | 內部系統錯誤 |

### 錯誤代碼
| 錯誤代碼 | 說明 | 解決方案 |
|----------|------|----------|
| `AUTH_REQUIRED` | 需要認證 | 提供有效的 Token |
| `INVALID_TOKEN` | Token 無效 | 重新登入獲取新 Token |
| `INSUFFICIENT_FUNDS` | 資金不足 | 檢查帳戶餘額 |
| `MARKET_CLOSED` | 市場關閉 | 等待市場開放時間 |
| `RATE_LIMIT_EXCEEDED` | 超過速率限制 | 降低請求頻率 |

---

## 🚦 速率限制

### 限制規則
- **一般 API**：每分鐘 100 次請求
- **市場數據**：每分鐘 300 次請求
- **交易 API**：每分鐘 50 次請求
- **認證 API**：每分鐘 10 次請求

### 回應標頭
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1625097600
```

### 超限處理
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "請求頻率超過限制",
    "retry_after": 60
  }
}
```

---

## 💻 SDK 與範例

### Python SDK
```python
from ai_trading_sdk import TradingClient

# 初始化客戶端
client = TradingClient(
    base_url="http://localhost:8000/api/v1",
    username="your_username",
    password="your_password"
)

# 獲取投資組合摘要
portfolio = client.portfolio.get_summary()
print(f"總價值: {portfolio['total_value']}")

# 下單
order = client.orders.create(
    symbol="AAPL",
    side="buy",
    quantity=100,
    order_type="market"
)
print(f"訂單 ID: {order['order_id']}")
```

### JavaScript SDK
```javascript
import { TradingClient } from 'ai-trading-sdk';

const client = new TradingClient({
  baseURL: 'http://localhost:8000/api/v1',
  username: 'your_username',
  password: 'your_password'
});

// 獲取市場數據
const quotes = await client.market.getQuotes(['AAPL', 'GOOGL']);
console.log('即時報價:', quotes);

// 啟動回測
const backtest = await client.backtest.create({
  strategy: 'moving_average',
  symbols: ['AAPL'],
  start_date: '2024-01-01',
  end_date: '2024-12-31'
});
```

---

## 🎯 最佳實踐

### 1. 認證管理
- 安全存儲 Token，避免硬編碼
- 實現自動 Token 刷新機制
- 使用 HTTPS 保護傳輸安全

### 2. 錯誤處理
- 實現完整的錯誤處理邏輯
- 根據錯誤代碼進行適當的重試
- 記錄詳細的錯誤日誌

### 3. 性能優化
- 使用連接池減少連接開銷
- 實現適當的快取機制
- 批量處理減少 API 調用次數

### 4. 監控與日誌
- 監控 API 回應時間和成功率
- 記錄關鍵業務操作
- 設置適當的警報機制

---

**文檔版本**: v2.0  
**最後更新**: 2025-01-15  
**維護團隊**: AI Trading System API Team
