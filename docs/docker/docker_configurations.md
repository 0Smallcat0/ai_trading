# Docker 配置說明

本文檔說明專案中使用的 Docker 配置文件及其功能。

## 配置概述

專案中的 Docker 配置文件主要用於設置監控和日誌系統。所有 Docker 配置文件都位於 `config/docker` 目錄下。

## 配置文件列表

### 1. `docker-compose-elk.yml`

**功能**：設置 ELK (Elasticsearch, Logstash, Kibana) 堆棧，用於集中式日誌管理。

**主要組件**：
- **Elasticsearch**：用於存儲和索引日誌數據
- **Logstash**：用於收集、處理和轉發日誌
- **Kibana**：用於可視化和分析日誌數據
- **Filebeat**：用於收集和轉發日誌文件

**使用方法**：
```bash
docker-compose -f config/docker/docker-compose-elk.yml up -d
```

**配置說明**：
- Elasticsearch 運行在端口 9200 和 9300
- Logstash 運行在端口 5044、5000 和 9600
- Kibana 運行在端口 5601
- 所有組件共享 `elk` 網絡

### 2. `docker-compose-loki.yml`

**功能**：設置 Loki 日誌堆棧，作為 ELK 的輕量級替代方案。

**主要組件**：
- **Loki**：用於存儲和查詢日誌
- **Promtail**：用於收集和轉發日誌
- **Grafana**：用於可視化和分析日誌數據

**使用方法**：
```bash
docker-compose -f config/docker/docker-compose-loki.yml up -d
```

**配置說明**：
- Loki 運行在端口 3100
- Grafana 運行在端口 3000
- 所有組件共享 `loki` 網絡

### 3. `docker-compose-monitoring.yml`

**功能**：設置 Prometheus 和 Grafana 監控堆棧，用於系統和應用程序監控。

**主要組件**：
- **Prometheus**：用於收集和存儲指標數據
- **Alertmanager**：用於處理警報
- **Grafana**：用於可視化和分析指標數據
- **Node Exporter**：用於收集主機指標

**使用方法**：
```bash
docker-compose -f config/docker/docker-compose-monitoring.yml up -d
```

**配置說明**：
- Prometheus 運行在端口 9090
- Alertmanager 運行在端口 9093
- Grafana 運行在端口 3000
- Node Exporter 運行在端口 9100
- 所有組件共享 `monitoring` 網絡

## 與系統的集成

### 日誌系統集成

系統通過 `src/logging/config.py` 模組與 ELK 和 Loki 日誌系統集成：

```python
# ELK配置
ELK_CONFIG = {
    "enabled": os.getenv("ELK_ENABLED", "False").lower() == "true",
    "elasticsearch_url": os.getenv("ELASTICSEARCH_URL", "http://localhost:9200"),
    "elasticsearch_index": os.getenv("ELASTICSEARCH_INDEX", "trading-logs"),
    "elasticsearch_auth": None,  # 格式為(username, password)
    "logstash_url": os.getenv("LOGSTASH_URL", "http://localhost:5044"),
    "kibana_url": os.getenv("KIBANA_URL", "http://localhost:5601"),
}

# Loki配置
LOKI_CONFIG = {
    "enabled": os.getenv("LOKI_ENABLED", "False").lower() == "true",
    "loki_url": os.getenv("LOKI_URL", "http://localhost:3100/loki/api/v1/push"),
    "batch_size": int(os.getenv("LOKI_BATCH_SIZE", "100")),
    "batch_interval": float(os.getenv("LOKI_BATCH_INTERVAL", "1.0")),
}
```

### 監控系統集成

系統通過 `src/monitoring/config.py` 模組與 Prometheus 和 Grafana 監控系統集成：

```python
# Prometheus 配置
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_PORT", "9090"))
PROMETHEUS_COLLECTION_INTERVAL = int(
    os.getenv("PROMETHEUS_COLLECTION_INTERVAL", str(CHECK_INTERVAL))
)

# Grafana 配置
GRAFANA_PORT = int(os.getenv("GRAFANA_PORT", "3000"))
GRAFANA_ADMIN_USER = os.getenv("GRAFANA_ADMIN_USER", "admin")
GRAFANA_ADMIN_PASSWORD = os.getenv("GRAFANA_ADMIN_PASSWORD", "admin")
```

## 最佳實踐

1. **資源管理**：根據系統資源調整 Docker 容器的資源限制，特別是 Elasticsearch 和 Prometheus 的內存設置。

2. **持久化存儲**：確保使用卷（volumes）持久化重要數據，如 Elasticsearch 索引、Prometheus 時序數據和 Grafana 儀表板。

3. **安全性**：在生產環境中，更改默認密碼並啟用 TLS 加密。

4. **備份**：定期備份重要數據，特別是 Elasticsearch 索引和 Grafana 儀表板。

## 注意事項

- 這些 Docker 配置文件設計用於開發和測試環境。在生產環境中，可能需要進一步調整和加強安全性。
- 在資源有限的環境中，可以選擇使用 Loki 而不是 ELK，因為 Loki 的資源消耗較少。
- 監控和日誌系統可能會生成大量數據，需要定期清理或歸檔。
