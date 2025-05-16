# 檔案組織說明

本文檔說明專案的檔案組織結構，特別是針對腳本、配置和文檔的組織方式。

## 目錄結構

專案的主要目錄結構如下：

```
auto_trading_project/
├── .envs/                  # 環境變數配置目錄
├── .github/                # GitHub 工作流配置
├── .pre-commit-config.yaml  # pre-commit 配置
├── config/                 # 配置文件目錄
│   ├── docker/             # Docker 配置文件
│   ├── keys/               # 密鑰和證書目錄（不提交到版本控制）
│   ├── brokers.yaml        # 券商配置
│   ├── mypy.ini            # mypy 配置
│   └── pytest.ini          # pytest 配置
├── data/                   # 資料目錄
├── docs/                   # 文檔目錄
│   ├── docker/             # Docker 配置說明
│   ├── scripts/            # 腳本說明
│   ├── modules/            # 模組說明文檔
│   ├── 共用工具說明/        # 共用工具說明
│   ├── 新進人員指南.md      # 開發者指南
│   ├── Q&A常見問題.md       # 常見問題與解答
│   └── SUMMARY.md          # 文檔目錄
├── logs/                   # 日誌目錄
├── models/                 # 模型存儲目錄
├── notebooks/              # Jupyter 筆記本
├── scripts/                # 腳本目錄
│   └── powershell/         # PowerShell 腳本
├── src/                    # 源代碼目錄
├── tests/                  # 測試目錄
└── utils/                  # 工具目錄
```

## 腳本組織

所有 PowerShell 腳本都放在 `scripts/powershell` 目錄下，包括：

- `audit_security.ps1`：安全審計腳本
- `clean_git_history.ps1`：清理 Git 歷史腳本
- `push_to_github.ps1`：推送到 GitHub 腳本
- `setup_clean_env.ps1`：設置乾淨環境腳本

詳細說明請參考 [PowerShell 腳本說明](scripts/powershell_scripts.md)。

## Docker 配置組織

所有 Docker 配置文件都放在 `config/docker` 目錄下，包括：

- `docker-compose-elk.yml`：ELK 堆棧配置
- `docker-compose-loki.yml`：Loki 日誌堆棧配置
- `docker-compose-monitoring.yml`：Prometheus 和 Grafana 監控堆棧配置

詳細說明請參考 [Docker 配置說明](docker/docker_configurations.md)。

## 配置文件組織

配置文件放在 `config` 目錄下，包括：

- `.pre-commit-config.yaml`：pre-commit 配置
- `brokers.yaml`：券商配置
- `mypy.ini`：mypy 配置
- `pytest.ini`：pytest 配置

敏感配置（如密鑰和證書）放在 `config/keys` 目錄下，該目錄不提交到版本控制系統。

## 環境變數組織

環境變數配置放在 `.envs` 目錄下，包括：

- `.env.template`：環境變數模板
- `.env.dev`：開發環境配置
- `.env.test`：測試環境配置
- `.env.prod`：生產環境配置

根目錄下的 `.env` 和 `.env.example` 文件用於本地開發。

## 文檔組織

文檔放在 `docs` 目錄下，按照以下方式組織：

- `docker/`：Docker 配置說明
- `scripts/`：腳本說明
- `modules/`：模組說明文檔
- `共用工具說明/`：共用工具說明
- `新進人員指南.md`：開發者指南
- `Q&A常見問題.md`：常見問題與解答
- `SUMMARY.md`：文檔目錄

## 最佳實踐

1. **腳本管理**：所有腳本都應放在 `scripts` 目錄下，按照用途分類。

2. **配置管理**：所有配置文件都應放在 `config` 目錄下，敏感配置放在 `config/keys` 目錄下。

3. **文檔管理**：所有文檔都應放在 `docs` 目錄下，按照用途分類。

4. **環境變數管理**：環境變數配置應放在 `.envs` 目錄下，不同環境使用不同的配置文件。

5. **Docker 配置管理**：所有 Docker 配置文件都應放在 `config/docker` 目錄下，使用相對路徑引用其他文件。
