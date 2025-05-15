"""
工作流配置模組

此模組提供n8n工作流的配置模板和工具函數。
"""

import os
import json
from typing import Dict, List, Any, Optional, Union

# 基本工作流模板
BASE_WORKFLOW_TEMPLATE = {
    "name": "",
    "nodes": [],
    "connections": {},
    "active": False,
    "settings": {
        "saveManualExecutions": True,
        "callerPolicy": "workflowsFromSameOwner",
        "errorWorkflow": "",
    },
    "tags": [],
    "pinData": {},
}

# 節點模板
NODE_TEMPLATES = {
    # 觸發器節點
    "schedule_trigger": {
        "parameters": {
            "rule": {
                "interval": [
                    {
                        "field": "minute",
                        "minuteInterval": 5
                    }
                ]
            }
        },
        "name": "Schedule Trigger",
        "type": "n8n-nodes-base.scheduleTrigger",
        "typeVersion": 1,
        "position": [
            0,
            0
        ]
    },
    "webhook_trigger": {
        "parameters": {
            "path": "",
            "responseMode": "lastNode",
            "options": {}
        },
        "name": "Webhook Trigger",
        "type": "n8n-nodes-base.webhook",
        "typeVersion": 1,
        "position": [
            0,
            0
        ]
    },
    
    # HTTP請求節點
    "http_request": {
        "parameters": {
            "url": "",
            "method": "GET",
            "authentication": "genericCredentialType",
            "genericAuthType": "httpHeaderAuth",
            "options": {}
        },
        "name": "HTTP Request",
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 3,
        "position": [
            0,
            0
        ],
        "credentials": {
            "httpHeaderAuth": {
                "name": "Trading API Auth",
                "id": "1"
            }
        }
    },
    
    # 函數節點
    "function": {
        "parameters": {
            "functionCode": ""
        },
        "name": "Function",
        "type": "n8n-nodes-base.function",
        "typeVersion": 1,
        "position": [
            0,
            0
        ]
    },
    
    # IF節點
    "if": {
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
        "name": "IF",
        "type": "n8n-nodes-base.if",
        "typeVersion": 1,
        "position": [
            0,
            0
        ]
    },
    
    # 錯誤處理節點
    "error_trigger": {
        "parameters": {},
        "name": "Error Trigger",
        "type": "n8n-nodes-base.errorTrigger",
        "typeVersion": 1,
        "position": [
            0,
            0
        ]
    },
    
    # 通知節點
    "slack": {
        "parameters": {
            "text": "",
            "channel": "",
            "attachments": [],
            "otherOptions": {}
        },
        "name": "Slack",
        "type": "n8n-nodes-base.slack",
        "typeVersion": 1,
        "position": [
            0,
            0
        ],
        "credentials": {
            "slackApi": {
                "id": "1",
                "name": "Slack Account"
            }
        }
    },
    
    # 電子郵件節點
    "email": {
        "parameters": {
            "fromEmail": "",
            "toEmail": "",
            "subject": "",
            "text": "",
            "options": {}
        },
        "name": "Email",
        "type": "n8n-nodes-base.emailSend",
        "typeVersion": 1,
        "position": [
            0,
            0
        ],
        "credentials": {
            "smtp": {
                "id": "1",
                "name": "SMTP Account"
            }
        }
    }
}

# 工作流模板
WORKFLOW_TEMPLATES = {
    # 數據獲取工作流
    "data_ingestion": {
        "name": "數據獲取工作流",
        "nodes": [
            {
                **NODE_TEMPLATES["schedule_trigger"],
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
                "position": [0, 0]
            },
            {
                **NODE_TEMPLATES["http_request"],
                "parameters": {
                    "url": "http://localhost:8000/api/market-data/fetch",
                    "method": "POST",
                    "jsonParameters": True,
                    "options": {}
                },
                "name": "獲取市場數據",
                "position": [220, 0]
            },
            {
                **NODE_TEMPLATES["if"],
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
                "position": [440, 0]
            },
            {
                **NODE_TEMPLATES["http_request"],
                "parameters": {
                    "url": "http://localhost:8000/api/market-data/process",
                    "method": "POST",
                    "jsonParameters": True,
                    "options": {}
                },
                "name": "處理市場數據",
                "position": [660, -100]
            },
            {
                **NODE_TEMPLATES["slack"],
                "parameters": {
                    "text": "=數據獲取失敗: {{ $json.error }}",
                    "channel": "trading-alerts",
                    "attachments": [],
                    "otherOptions": {}
                },
                "name": "發送錯誤通知",
                "position": [660, 100]
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
        "active": False,
        "settings": {
            "saveManualExecutions": True,
            "callerPolicy": "workflowsFromSameOwner",
            "errorWorkflow": "",
        },
        "tags": ["數據", "自動化"],
    },
    
    # 交易訊號生成工作流
    "signal_generation": {
        "name": "交易訊號生成工作流",
        "nodes": [
            {
                **NODE_TEMPLATES["schedule_trigger"],
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
                "position": [0, 0]
            },
            {
                **NODE_TEMPLATES["http_request"],
                "parameters": {
                    "url": "http://localhost:8000/api/strategy/generate-signals",
                    "method": "POST",
                    "jsonParameters": True,
                    "options": {}
                },
                "name": "生成交易訊號",
                "position": [220, 0]
            },
            {
                **NODE_TEMPLATES["if"],
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
                "position": [440, 0]
            },
            {
                **NODE_TEMPLATES["http_request"],
                "parameters": {
                    "url": "http://localhost:8000/api/trade/execute",
                    "method": "POST",
                    "jsonParameters": True,
                    "options": {}
                },
                "name": "執行交易",
                "position": [660, -100]
            },
            {
                **NODE_TEMPLATES["slack"],
                "parameters": {
                    "text": "=交易訊號生成失敗: {{ $json.error }}",
                    "channel": "trading-alerts",
                    "attachments": [],
                    "otherOptions": {}
                },
                "name": "發送錯誤通知",
                "position": [660, 100]
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
        "active": False,
        "settings": {
            "saveManualExecutions": True,
            "callerPolicy": "workflowsFromSameOwner",
            "errorWorkflow": "",
        },
        "tags": ["交易", "自動化"],
    },
}
