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
  "success": true,
  "message": "登入成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "user_info": {
      "username": "your_username",
      "role": "trader",
      "permissions": ["read", "write", "execute"]
    }
  }
}
```

#### 2. 使用 Token
在所有需要認證的請求中，在 Header 中包含：
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### 3. 刷新 Token
```http
POST /api/v1/auth/refresh
Authorization: Bearer your_current_token
```

### 權限控制
系統採用 RBAC（角色基礎存取控制）模型：

| 角色 | 權限說明 |
|------|----------|
| admin | 完整系統權限 |
| trader | 交易執行權限 |
| analyst | 數據分析權限 |
| user | 基本查看權限 |
| guest | 只讀權限 |

---

## 📊 核心 API 端點

### 1. 資料管理 API

#### 獲取市場數據
```http
GET /api/v1/data/market?symbol=2330&start_date=2024-01-01&end_date=2024-12-31
Authorization: Bearer your_token
```

#### 數據收集
```http
POST /api/v1/data/collect
Authorization: Bearer your_token
Content-Type: application/json

{
  "symbols": ["2330", "2317", "2454"],
  "data_types": ["price", "volume", "financial"],
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```

### 2. 策略管理 API

#### 獲取策略列表
```http
GET /api/v1/strategies
Authorization: Bearer your_token
```

#### 創建新策略
```http
POST /api/v1/strategies
Authorization: Bearer your_token
Content-Type: application/json

{
  "name": "移動平均策略",
  "description": "基於移動平均線的交易策略",
  "parameters": {
    "short_window": 5,
    "long_window": 20,
    "symbols": ["2330", "2317"]
  },
  "risk_settings": {
    "max_position_size": 0.1,
    "stop_loss": 0.05,
    "take_profit": 0.1
  }
}
```

### 3. AI 模型 API

#### 獲取模型列表
```http
GET /api/v1/models
Authorization: Bearer your_token
```

#### 模型訓練
```http
POST /api/v1/models/train
Authorization: Bearer your_token
Content-Type: application/json

{
  "model_type": "random_forest",
  "features": ["ma_5", "ma_20", "rsi", "volume"],
  "target": "next_day_return",
  "training_period": {
    "start_date": "2023-01-01",
    "end_date": "2024-01-01"
  }
}
```

### 4. 回測系統 API

#### 執行回測
```http
POST /api/v1/backtest/run
Authorization: Bearer your_token
Content-Type: application/json

{
  "strategy_id": "strategy_123",
  "start_date": "2024-01-01",
  "end_date": "2024-11-30",
  "initial_capital": 1000000,
  "symbols": ["2330", "2317", "2454"]
}
```

#### 獲取回測結果
```http
GET /api/v1/backtest/results/{backtest_id}
Authorization: Bearer your_token
```

### 5. 投資組合 API

#### 獲取投資組合狀態
```http
GET /api/v1/portfolio/status
Authorization: Bearer your_token
```

#### 投資組合優化
```http
POST /api/v1/portfolio/optimize
Authorization: Bearer your_token
Content-Type: application/json

{
  "symbols": ["2330", "2317", "2454", "2412"],
  "optimization_method": "mean_variance",
  "constraints": {
    "max_weight": 0.3,
    "min_weight": 0.05
  },
  "risk_tolerance": 0.15
}
```

### 6. 風險管理 API

#### 風險評估
```http
POST /api/v1/risk/assess
Authorization: Bearer your_token
Content-Type: application/json

{
  "portfolio": {
    "2330": 0.4,
    "2317": 0.3,
    "2454": 0.3
  },
  "market_data_period": 252
}
```

### 7. 交易執行 API

#### 下單
```http
POST /api/v1/trading/orders
Authorization: Bearer your_token
Content-Type: application/json

{
  "symbol": "2330",
  "side": "buy",
  "quantity": 1000,
  "order_type": "market",
  "strategy_id": "strategy_123"
}
```

#### 獲取訂單狀態
```http
GET /api/v1/trading/orders/{order_id}
Authorization: Bearer your_token
```

### 8. 系統監控 API

#### 系統健康檢查
```http
GET /api/v1/monitoring/health
Authorization: Bearer your_token
```

#### 系統指標
```http
GET /api/v1/monitoring/metrics
Authorization: Bearer your_token
```

### 9. 報表分析 API

#### 生成報表
```http
POST /api/v1/reports/generate
Authorization: Bearer your_token
Content-Type: application/json

{
  "report_type": "performance",
  "period": {
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  },
  "format": "pdf"
}
```

---

## 📋 請求與回應格式

### 標準回應格式
所有 API 回應都遵循統一格式：

```json
{
  "success": true,
  "message": "操作成功",
  "data": {
    // 實際數據內容
  },
  "timestamp": "2024-12-19T10:30:00Z",
  "request_id": "req_123456789"
}
```

### 分頁回應格式
```json
{
  "success": true,
  "message": "查詢成功",
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "page_size": 20,
      "total_items": 100,
      "total_pages": 5,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

### 日期時間格式
- **日期**：`YYYY-MM-DD` (例：2024-12-19)
- **時間**：`HH:MM:SS` (例：14:30:00)
- **日期時間**：`YYYY-MM-DDTHH:MM:SSZ` (例：2024-12-19T14:30:00Z)

---

## ⚠️ 錯誤處理

### HTTP 狀態碼
- `200` - 成功
- `201` - 創建成功
- `400` - 請求錯誤
- `401` - 未授權
- `403` - 禁止存取
- `404` - 資源不存在
- `429` - 請求過於頻繁
- `500` - 伺服器內部錯誤

### 錯誤回應格式
```json
{
  "success": false,
  "message": "錯誤描述",
  "error": {
    "code": "E001",
    "type": "ValidationError",
    "details": "具體錯誤詳情",
    "field": "username"
  },
  "timestamp": "2024-12-19T10:30:00Z",
  "request_id": "req_123456789"
}
```

### 常見錯誤碼
- `E001` - 參數驗證錯誤
- `E002` - 認證失敗
- `E003` - 權限不足
- `E004` - 資源不存在
- `E005` - 業務邏輯錯誤

---

## 🚦 速率限制

### 限制規則
- **一般用戶**：1000 請求/分鐘
- **高級用戶**：5000 請求/分鐘
- **企業用戶**：10000 請求/分鐘

### 限制 Headers
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640000000
```

### 超出限制回應
```json
{
  "success": false,
  "message": "請求過於頻繁，請稍後再試",
  "error": {
    "code": "E429",
    "type": "RateLimitExceeded",
    "retry_after": 60
  }
}
```

---

## 🛠️ SDK 與範例

### Python SDK 範例

#### 安裝
```bash
pip install trading-system-sdk
```

#### 基本使用
```python
from trading_system_sdk import TradingSystemClient

# 初始化客戶端
client = TradingSystemClient(
    base_url="http://localhost:8000/api/v1",
    username="your_username",
    password="your_password"
)

# 獲取市場數據
market_data = client.data.get_market_data(
    symbol="2330",
    start_date="2024-01-01",
    end_date="2024-12-31"
)

# 創建策略
strategy = client.strategies.create({
    "name": "我的策略",
    "parameters": {"short_window": 5, "long_window": 20}
})

# 執行回測
backtest = client.backtest.run(
    strategy_id=strategy["id"],
    start_date="2024-01-01",
    end_date="2024-11-30",
    initial_capital=1000000
)
```

### JavaScript SDK 範例

#### 安裝
```bash
npm install trading-system-js-sdk
```

#### 基本使用
```javascript
import { TradingSystemClient } from 'trading-system-js-sdk';

// 初始化客戶端
const client = new TradingSystemClient({
  baseURL: 'http://localhost:8000/api/v1',
  username: 'your_username',
  password: 'your_password'
});

// 獲取策略列表
const strategies = await client.strategies.list();

// 執行交易
const order = await client.trading.createOrder({
  symbol: '2330',
  side: 'buy',
  quantity: 1000,
  orderType: 'market'
});
```

### cURL 範例

#### 登入獲取 Token
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

#### 獲取市場數據
```bash
curl -X GET "http://localhost:8000/api/v1/data/market?symbol=2330" \
  -H "Authorization: Bearer your_token_here"
```

#### 創建策略
```bash
curl -X POST "http://localhost:8000/api/v1/strategies" \
  -H "Authorization: Bearer your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "測試策略",
    "parameters": {
      "short_window": 5,
      "long_window": 20
    }
  }'
```

---

## 💡 最佳實踐

### 1. 認證與安全
- **安全存儲 Token**：不要在客戶端代碼中硬編碼 Token
- **定期刷新 Token**：在 Token 過期前主動刷新
- **使用 HTTPS**：生產環境必須使用 HTTPS
- **最小權限原則**：只申請必要的權限

### 2. 錯誤處理
```python
try:
    result = client.strategies.create(strategy_data)
except TradingSystemAPIError as e:
    if e.status_code == 401:
        # Token 過期，重新登入
        client.refresh_token()
        result = client.strategies.create(strategy_data)
    elif e.status_code == 429:
        # 速率限制，等待後重試
        time.sleep(60)
        result = client.strategies.create(strategy_data)
    else:
        # 其他錯誤
        logger.error(f"API 錯誤: {e.message}")
        raise
```

### 3. 效能優化
- **批次請求**：盡可能使用批次 API 減少請求次數
- **分頁查詢**：大量數據使用分頁避免超時
- **快取機制**：對不常變化的數據進行快取
- **並發控制**：合理控制並發請求數量

### 4. 監控與日誌
```python
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 記錄 API 調用
logger.info(f"調用 API: {endpoint}, 參數: {params}")

# 監控回應時間
start_time = time.time()
response = client.api_call()
duration = time.time() - start_time
logger.info(f"API 回應時間: {duration:.2f}秒")
```

### 5. 版本管理
- **指定版本**：在 URL 中明確指定 API 版本
- **向後相容**：新版本發布時測試向後相容性
- **漸進升級**：分階段升級到新版本

### 6. 測試策略
```python
import unittest
from unittest.mock import Mock, patch

class TestTradingAPI(unittest.TestCase):
    def setUp(self):
        self.client = TradingSystemClient(test_mode=True)

    def test_create_strategy(self):
        # 測試策略創建
        strategy_data = {
            "name": "測試策略",
            "parameters": {"short_window": 5}
        }
        result = self.client.strategies.create(strategy_data)
        self.assertIsNotNone(result["id"])

    @patch('requests.post')
    def test_api_error_handling(self, mock_post):
        # 測試錯誤處理
        mock_post.return_value.status_code = 400
        mock_post.return_value.json.return_value = {
            "success": False,
            "error": {"code": "E001", "message": "參數錯誤"}
        }

        with self.assertRaises(TradingSystemAPIError):
            self.client.strategies.create({})
```

---

## 📞 技術支援

### 支援管道
- **API 文檔**：http://localhost:8000/docs
- **技術論壇**：https://forum.trading-system.com
- **GitHub Issues**：https://github.com/trading-system/api/issues
- **郵件支援**：api-support@trading-system.com

### 常見問題
1. **Q: Token 過期怎麼辦？**
   A: 使用 refresh token 端點重新獲取新的 access token

2. **Q: 如何處理速率限制？**
   A: 檢查回應 headers 中的限制資訊，實施指數退避重試

3. **Q: API 回應緩慢怎麼辦？**
   A: 檢查請求參數，使用分頁，考慮快取策略

4. **Q: 如何獲得更高的速率限制？**
   A: 聯繫客戶服務升級到高級或企業方案

---

## 📝 文檔資訊

**文檔版本**：1.0
**最後更新**：2024年12月
**預計閱讀時間**：45分鐘
**目標用戶**：開發者、系統整合人員
**維護團隊**：API 開發團隊
