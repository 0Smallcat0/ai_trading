# n8n 工作流範例

本文檔提供了使用 n8n 自動化交易系統的工作流範例。

## 設置 n8n

1. 安裝 n8n:
```bash
npm install -g n8n
```

2. 啟動 n8n:
```bash
n8n start
```

3. 訪問 n8n 界面:
```
http://localhost:5678
```

## 工作流範例

### 1. 數據獲取工作流

此工作流每15分鐘獲取一次市場數據，並進行處理。

```json
{
  "name": "數據獲取工作流",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "minute",
              "minuteInterval": 15
            }
          ]
        }
      },
      "name": "每15分鐘觸發",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1,
      "position": [0, 0]
    },
    {
      "parameters": {
        "url": "http://localhost:8000/api/market-data/fetch",
        "method": "POST",
        "jsonParameters": true,
        "options": {}
      },
      "name": "獲取市場數據",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 3,
      "position": [220, 0],
      "credentials": {
        "httpHeaderAuth": {
          "name": "Trading API Auth",
          "id": "1"
        }
      }
    },
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{ $json.success }}",
              "operation": "equal",
              "value2": "true"
            }
          ]
        }
      },
      "name": "檢查結果",
      "type": "n8n-nodes-base.if",
      "typeVersion": 1,
      "position": [440, 0]
    },
    {
      "parameters": {
        "url": "http://localhost:8000/api/market-data/process",
        "method": "POST",
        "jsonParameters": true,
        "options": {}
      },
      "name": "處理市場數據",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 3,
      "position": [660, -100],
      "credentials": {
        "httpHeaderAuth": {
          "name": "Trading API Auth",
          "id": "1"
        }
      }
    },
    {
      "parameters": {
        "text": "=數據獲取失敗: {{ $json.error }}",
        "channel": "trading-alerts",
        "attachments": [],
        "otherOptions": {}
      },
      "name": "發送錯誤通知",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 1,
      "position": [660, 100],
      "credentials": {
        "slackApi": {
          "id": "1",
          "name": "Slack Account"
        }
      }
    }
  ],
  "connections": {
    "每15分鐘觸發": {
      "main": [
        [
          {
            "node": "獲取市場數據",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "獲取市場數據": {
      "main": [
        [
          {
            "node": "檢查結果",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "檢查結果": {
      "main": [
        [
          {
            "node": "處理市場數據",
            "type": "main",
            "index": 0
          }
        ],
        [
          {
            "node": "發送錯誤通知",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "active": false,
  "settings": {
    "saveManualExecutions": true,
    "callerPolicy": "workflowsFromSameOwner",
    "errorWorkflow": ""
  },
  "tags": ["數據", "自動化"]
}
```

### 2. 交易訊號生成工作流

此工作流每30分鐘生成一次交易訊號，並執行交易。

```json
{
  "name": "交易訊號生成工作流",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "field": "minute",
              "minuteInterval": 30
            }
          ]
        }
      },
      "name": "每30分鐘觸發",
      "type": "n8n-nodes-base.scheduleTrigger",
      "typeVersion": 1,
      "position": [0, 0]
    },
    {
      "parameters": {
        "url": "http://localhost:8000/api/strategy/generate-signals",
        "method": "POST",
        "jsonParameters": true,
        "options": {}
      },
      "name": "生成交易訊號",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 3,
      "position": [220, 0],
      "credentials": {
        "httpHeaderAuth": {
          "name": "Trading API Auth",
          "id": "1"
        }
      }
    },
    {
      "parameters": {
        "conditions": {
          "string": [
            {
              "value1": "={{ $json.success }}",
              "operation": "equal",
              "value2": "true"
            }
          ]
        }
      },
      "name": "檢查結果",
      "type": "n8n-nodes-base.if",
      "typeVersion": 1,
      "position": [440, 0]
    },
    {
      "parameters": {
        "url": "http://localhost:8000/api/trade/execute",
        "method": "POST",
        "jsonParameters": true,
        "options": {}
      },
      "name": "執行交易",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 3,
      "position": [660, -100],
      "credentials": {
        "httpHeaderAuth": {
          "name": "Trading API Auth",
          "id": "1"
        }
      }
    },
    {
      "parameters": {
        "text": "=交易訊號生成失敗: {{ $json.error }}",
        "channel": "trading-alerts",
        "attachments": [],
        "otherOptions": {}
      },
      "name": "發送錯誤通知",
      "type": "n8n-nodes-base.slack",
      "typeVersion": 1,
      "position": [660, 100],
      "credentials": {
        "slackApi": {
          "id": "1",
          "name": "Slack Account"
        }
      }
    }
  ],
  "connections": {
    "每30分鐘觸發": {
      "main": [
        [
          {
            "node": "生成交易訊號",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "生成交易訊號": {
      "main": [
        [
          {
            "node": "檢查結果",
            "type": "main",
            "index": 0
          }
        ]
      ]
    },
    "檢查結果": {
      "main": [
        [
          {
            "node": "執行交易",
            "type": "main",
            "index": 0
          }
        ],
        [
          {
            "node": "發送錯誤通知",
            "type": "main",
            "index": 0
          }
        ]
      ]
    }
  },
  "active": false,
  "settings": {
    "saveManualExecutions": true,
    "callerPolicy": "workflowsFromSameOwner",
    "errorWorkflow": ""
  },
  "tags": ["交易", "自動化"]
}
```
