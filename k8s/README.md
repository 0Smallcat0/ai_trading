# AI 股票自動交易系統 Kubernetes 部署指南

本目錄包含 AI 股票自動交易系統的完整 Kubernetes 部署配置，使用 Kustomize 進行多環境管理。

## 📁 目錄結構

```
k8s/
├── base/                           # 基礎配置
│   ├── namespace.yaml             # 命名空間定義
│   ├── configmap.yaml             # 配置映射
│   ├── secret.yaml                # 密鑰配置
│   ├── rbac.yaml                  # 權限控制
│   ├── pvc.yaml                   # 持久化存儲
│   ├── deployment.yaml            # 部署配置
│   ├── service.yaml               # 服務配置
│   ├── ingress.yaml               # 入口配置
│   └── kustomization.yaml         # Kustomize 基礎配置
├── overlays/                      # 環境特定覆蓋
│   ├── development/               # 開發環境
│   │   ├── kustomization.yaml
│   │   ├── development-resources.yaml
│   │   └── development-config.yaml
│   └── production/                # 生產環境
│       ├── kustomization.yaml
│       ├── production-resources.yaml
│       └── production-security.yaml
└── README.md                      # 本文檔
```

## 🚀 快速開始

### 前置需求

1. **Kubernetes 集群** (v1.20+)
2. **kubectl** 命令行工具
3. **Kustomize** (v4.0+，或使用 kubectl 內建的 kustomize)
4. **Ingress Controller** (推薦 NGINX Ingress Controller)
5. **StorageClass** 配置 (用於 PVC)

### 安裝步驟

#### 1. 準備環境

```bash
# 檢查 Kubernetes 集群狀態
kubectl cluster-info

# 檢查 Kustomize 版本
kubectl version --client | grep kustomize
```

#### 2. 配置密鑰

在部署前，需要更新 `base/secret.yaml` 中的密鑰值：

```bash
# 生成 base64 編碼的密鑰
echo -n "your_actual_password" | base64

# 編輯 secret.yaml 文件，替換範例值
kubectl edit -f base/secret.yaml
```

#### 3. 部署到開發環境

```bash
# 預覽部署配置
kubectl kustomize overlays/development

# 部署到開發環境
kubectl apply -k overlays/development

# 檢查部署狀態
kubectl get all -n ai-trading-dev
```

#### 4. 部署到生產環境

```bash
# 預覽生產環境配置
kubectl kustomize overlays/production

# 部署到生產環境
kubectl apply -k overlays/production

# 檢查部署狀態
kubectl get all -n ai-trading-prod
```

## 🔧 配置說明

### 基礎組件

- **應用程式**: AI 交易系統主應用 (Streamlit UI + FastAPI)
- **資料庫**: PostgreSQL 15
- **快取**: Redis 7
- **監控**: Prometheus + Grafana
- **反向代理**: Nginx (通過 Ingress)

### 環境差異

| 組件 | 開發環境 | 生產環境 |
|------|----------|----------|
| 副本數 | 1 | 3-5 |
| 資源限制 | 較小 | 較大 |
| 存儲大小 | 5-10GB | 50-100GB |
| 安全策略 | 寬鬆 | 嚴格 |
| 網路策略 | 開放 | 限制 |
| 健康檢查 | 寬鬆 | 嚴格 |

### 存儲配置

系統使用以下 PVC：

- `ai-trading-data-pvc`: 應用程式資料 (10GB/50GB)
- `postgres-data-pvc`: 資料庫資料 (20GB/100GB)
- `redis-data-pvc`: Redis 資料 (1GB)
- `prometheus-data-pvc`: 監控資料 (15GB/50GB)
- `grafana-data-pvc`: Grafana 配置 (2GB)

## 🔐 安全配置

### RBAC 權限

系統使用最小權限原則：

- `ai-trading-service-account`: 應用程式服務帳戶
- `ai-trading-monitoring-service-account`: 監控服務帳戶

### 網路策略

- 限制 Pod 間通信
- 只允許必要的入站/出站流量
- 隔離不同環境的網路

### Pod 安全

- 非 root 用戶運行
- 只讀根檔案系統 (部分容器)
- 禁用特權提升
- Seccomp 配置

## 📊 監控與日誌

### Prometheus 指標

- 應用程式指標: `http://app:9091/metrics`
- 系統指標: Node Exporter
- 資料庫指標: PostgreSQL Exporter

### Grafana 儀表板

- 系統概覽
- 應用程式性能
- 資料庫監控
- 交易指標

### 日誌收集

日誌存儲在 PVC 中，可以配置外部日誌收集系統 (如 ELK Stack)。

## 🔄 維護操作

### 更新部署

```bash
# 更新映像標籤
kubectl patch deployment ai-trading-app -n ai-trading-prod \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"ai-trading-app","image":"ai-trading:v1.1.0"}]}}}}'

# 或使用 Kustomize 更新
# 編輯 overlays/production/kustomization.yaml 中的 newTag
kubectl apply -k overlays/production
```

### 擴展副本

```bash
# 手動擴展
kubectl scale deployment ai-trading-app -n ai-trading-prod --replicas=5

# 或編輯 kustomization.yaml 中的 replicas 配置
```

### 備份與恢復

```bash
# 備份資料庫
kubectl exec -n ai-trading-prod postgres-xxx -- pg_dump -U postgres ai_trading > backup.sql

# 恢復資料庫
kubectl exec -i -n ai-trading-prod postgres-xxx -- psql -U postgres ai_trading < backup.sql
```

## 🐛 故障排除

### 常見問題

1. **Pod 無法啟動**
   ```bash
   kubectl describe pod <pod-name> -n <namespace>
   kubectl logs <pod-name> -n <namespace>
   ```

2. **PVC 無法綁定**
   ```bash
   kubectl get pv,pvc -n <namespace>
   kubectl describe pvc <pvc-name> -n <namespace>
   ```

3. **服務無法訪問**
   ```bash
   kubectl get svc,endpoints -n <namespace>
   kubectl describe ingress -n <namespace>
   ```

### 健康檢查

```bash
# 檢查所有資源狀態
kubectl get all -n ai-trading-prod

# 檢查 Pod 健康狀態
kubectl get pods -n ai-trading-prod -o wide

# 檢查服務端點
kubectl get endpoints -n ai-trading-prod
```

## 📚 相關文檔

- [Kubernetes 官方文檔](https://kubernetes.io/docs/)
- [Kustomize 文檔](https://kustomize.io/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
- [Prometheus Operator](https://prometheus-operator.dev/)

## 🤝 貢獻

如需修改部署配置，請：

1. 在 `base/` 目錄修改基礎配置
2. 在 `overlays/` 目錄添加環境特定配置
3. 測試配置變更
4. 提交 Pull Request
