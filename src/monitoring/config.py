"""監控配置模組

此模組提供監控系統的配置。
"""

import os

# 導入配置
from src.config import CHECK_INTERVAL

# Prometheus 配置
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))
PROMETHEUS_COLLECTION_INTERVAL = int(
    os.getenv("PROMETHEUS_COLLECTION_INTERVAL", str(CHECK_INTERVAL))
)

# Grafana 配置
GRAFANA_PORT = int(os.getenv("GRAFANA_PORT", "3000"))
GRAFANA_ADMIN_USER = os.getenv("GRAFANA_ADMIN_USER", "admin")
GRAFANA_ADMIN_PASSWORD = os.getenv("GRAFANA_ADMIN_PASSWORD", "admin")

# 警報配置
ALERT_LOG_DIR = os.getenv("ALERT_LOG_DIR", "logs/alerts")
ALERT_CHECK_INTERVAL = int(os.getenv("ALERT_CHECK_INTERVAL", str(CHECK_INTERVAL)))

# 電子郵件配置
EMAIL_CONFIG = {
    "from": os.getenv("ALERT_EMAIL_FROM", "alerts@example.com"),
    "to": os.getenv("ALERT_EMAIL_TO", "admin@example.com"),
    "smtp_server": os.getenv("SMTP_SERVER", "localhost"),
    "smtp_port": int(os.getenv("SMTP_PORT", "25")),
    "use_tls": os.getenv("SMTP_USE_TLS", "False").lower() == "true",
    "username": os.getenv("SMTP_USERNAME", ""),
    "password": os.getenv("SMTP_PASSWORD", ""),
}

# Slack 配置
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# SMS 配置
SMS_CONFIG = {
    "provider": os.getenv("SMS_PROVIDER", ""),
    "api_key": os.getenv("SMS_API_KEY", ""),
    "from": os.getenv("SMS_FROM", ""),
    "to": os.getenv("SMS_TO", ""),
}

# API 端點配置
API_ENDPOINTS = [
    {
        "url": "http://localhost:8000/api/health",
        "method": "GET",
        "headers": {},
        "data": None,
    },
    {
        "url": "http://localhost:8000/api/market-data/fetch",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": {"symbols": ["2330.TW"]},
    },
    {
        "url": "http://localhost:8000/api/strategy/generate-signals",
        "method": "POST",
        "headers": {"Content-Type": "application/json"},
        "data": {},
    },
]

# 監控閾值配置
THRESHOLDS = {
    # 系統閾值
    "system": {
        "cpu_usage": 80.0,  # CPU 使用率閾值（%）
        "memory_usage": 80.0,  # 內存使用率閾值（%）
        "disk_usage": 80.0,  # 磁盤使用率閾值（%）
    },
    # API 閾值
    "api": {
        "latency": 0.2,  # API 延遲閾值（秒）
        "error_rate": 0.05,  # API 錯誤率閾值
    },
    # 數據閾值
    "data": {
        "update_delay": 300,  # 數據更新延遲閾值（秒）
        "error_rate": 0.05,  # 數據錯誤率閾值
    },
    # 模型閾值
    "model": {
        "accuracy": 0.6,  # 模型準確率閾值
        "latency": 0.5,  # 模型延遲閾值（秒）
        "drift": 0.1,  # 模型漂移閾值
    },
    # 交易閾值
    "trade": {
        "success_rate": 0.7,  # 交易成功率閾值
        "capital_change": -5.0,  # 資本變化閾值（%）
    },
}

# SLA 配置（秒）
SLA_CONFIG = {
    "info": 24 * 60 * 60,  # 24 小時
    "warning": 4 * 60 * 60,  # 4 小時
    "error": 60 * 60,  # 1 小時
    "critical": 5 * 60,  # 5 分鐘
}

# 監控指標配置
METRICS = {
    # 系統指標
    "system": [
        {"name": "cpu_usage", "description": "CPU 使用率（%）", "type": "gauge"},
        {"name": "memory_usage", "description": "內存使用率（%）", "type": "gauge"},
        {"name": "disk_usage", "description": "磁盤使用率（%）", "type": "gauge"},
    ],
    # API 指標
    "api": [
        {"name": "latency", "description": "API 延遲（秒）", "type": "histogram"},
        {"name": "requests_total", "description": "API 請求總數", "type": "counter"},
        {"name": "errors_total", "description": "API 錯誤總數", "type": "counter"},
    ],
    # 數據指標
    "data": [
        {"name": "update_delay", "description": "數據更新延遲（秒）", "type": "gauge"},
        {
            "name": "update_success",
            "description": "數據更新成功次數",
            "type": "counter",
        },
        {
            "name": "update_failure",
            "description": "數據更新失敗次數",
            "type": "counter",
        },
    ],
    # 模型指標
    "model": [
        {
            "name": "prediction_accuracy",
            "description": "模型預測準確率",
            "type": "gauge",
        },
        {
            "name": "prediction_latency",
            "description": "模型預測延遲（秒）",
            "type": "histogram",
        },
        {"name": "drift", "description": "模型漂移指標", "type": "gauge"},
    ],
    # 交易指標
    "trade": [
        {"name": "success_rate", "description": "交易成功率", "type": "gauge"},
        {"name": "count", "description": "交易次數", "type": "counter"},
        {"name": "capital_change", "description": "資本變化百分比", "type": "gauge"},
        {"name": "position_value", "description": "持倉價值", "type": "gauge"},
    ],
}

# 警報規則配置
ALERT_RULES = [
    # 系統警報規則
    {
        "name": "high_cpu_usage",
        "expr": "system_cpu_usage > 80",
        "for": "5m",
        "labels": {"severity": "warning", "type": "system"},
        "annotations": {
            "summary": "高 CPU 使用率",
            "description": "CPU 使用率超過 80% 已持續 5 分鐘",
        },
    },
    {
        "name": "high_memory_usage",
        "expr": "system_memory_usage > 80",
        "for": "5m",
        "labels": {"severity": "warning", "type": "system"},
        "annotations": {
            "summary": "高內存使用率",
            "description": "內存使用率超過 80% 已持續 5 分鐘",
        },
    },
    {
        "name": "high_disk_usage",
        "expr": "system_disk_usage > 80",
        "for": "5m",
        "labels": {"severity": "warning", "type": "system"},
        "annotations": {
            "summary": "高磁盤使用率",
            "description": "磁盤使用率超過 80% 已持續 5 分鐘",
        },
    },
    # API 警報規則
    {
        "name": "high_api_latency",
        "expr": (
            "histogram_quantile(0.95, "
            "sum(rate(api_latency_seconds_bucket[5m])) by (le, endpoint)) > 0.2"
        ),
        "for": "5m",
        "labels": {"severity": "warning", "type": "api"},
        "annotations": {
            "summary": "高 API 延遲",
            "description": "API 延遲 (p95) 超過 200ms 已持續 5 分鐘: {{ $labels.endpoint }}",
        },
    },
    {
        "name": "high_api_error_rate",
        "expr": (
            "sum(rate(api_errors_total[5m])) by (endpoint) / "
            "sum(rate(api_requests_total[5m])) by (endpoint) > 0.05"
        ),
        "for": "5m",
        "labels": {"severity": "warning", "type": "api"},
        "annotations": {
            "summary": "高 API 錯誤率",
            "description": "API 錯誤率超過 5% 已持續 5 分鐘: {{ $labels.endpoint }}",
        },
    },
    # 模型警報規則
    {
        "name": "low_model_accuracy",
        "expr": "model_prediction_accuracy < 0.6",
        "for": "30m",
        "labels": {"severity": "warning", "type": "model"},
        "annotations": {
            "summary": "低模型準確率",
            "description": "模型準確率低於 60% 已持續 30 分鐘: {{ $labels.model_name }}",
        },
    },
    # 交易警報規則
    {
        "name": "low_trade_success_rate",
        "expr": "trade_success_rate < 0.7",
        "for": "1h",
        "labels": {"severity": "warning", "type": "trade"},
        "annotations": {
            "summary": "低交易成功率",
            "description": "交易成功率低於 70% 已持續 1 小時",
        },
    },
    {
        "name": "negative_capital_change",
        "expr": "capital_change_percent < -5",
        "for": "5m",
        "labels": {"severity": "critical", "type": "trade"},
        "annotations": {
            "summary": "資本大幅下降",
            "description": "資本下降超過 5% 已持續 5 分鐘",
        },
    },
]
