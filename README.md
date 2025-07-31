# AI 股票自動交易系統

![版本](https://img.shields.io/badge/版本-0.2.0-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![授權](https://img.shields.io/badge/授權-MIT-orange)
![CI/CD](https://github.com/0Smallcat0/ai_trading/workflows/CI/badge.svg)
![品質](https://img.shields.io/badge/Pylint-9.0+-brightgreen)
![測試覆蓋率](https://img.shields.io/badge/覆蓋率-90%+-brightgreen)
![檔案大小合規](https://img.shields.io/badge/檔案大小-≤300行-brightgreen)
![Poetry](https://img.shields.io/badge/依賴管理-Poetry-blue)
![安全檢查](https://img.shields.io/badge/安全檢查-Bandit-green)

AI 股票自動交易系統是一個整合人工智能技術的自動化交易平台，能夠分析多維度市場數據，生成智能交易決策，並執行自動化交易。系統專為台灣及全球股票市場設計，適合個人投資者和專業交易團隊使用。

## 🚀 新手快速開始

### 5分鐘快速啟動
```bash
# 1. 下載專案
git clone https://github.com/your-repo/ai_trading.git
cd ai_trading

# 2. 一鍵安裝依賴
python install_dependencies.py

# 3. 啟動系統 (v3.1 側邊欄整合版)
python -m streamlit run src/ui/web_ui.py --server.address=127.0.0.1 --server.port=8501

# 或使用快速啟動腳本
start.bat  # Windows

# 4. 訪問系統
# 打開瀏覽器訪問: http://localhost:8501
```

### 📚 新手指南
- [🚀 新手快速啟動指南](docs/新手快速啟動指南.md) - 5分鐘上手指南
- [📖 功能概覽](docs/使用者手冊/功能概覽.md) - 了解系統功能
- [🎯 第一次回測教程](docs/使用者手冊/第一次回測教程.md) - 學習回測操作
- [⚠️ 風險管理入門](docs/使用者手冊/風險管理入門指南.md) - 風險控制基礎

### ❓ 遇到問題？
- 查看 [常見問題解答](docs/Q&A常見問題.md)
- 運行系統健康檢查: 在Web UI中點擊"系統監控"
- 查看 [故障排除手冊](docs/使用者手冊/故障排除手冊.md)

## 系統特色

- **多維數據分析**：整合基本面、技術面和新聞情緒數據，全方位分析市場
- **AI 驅動決策**：使用機器學習和深度學習模型，自動生成交易訊號
- **自動化交易**：支援多家券商 API，實現全自動交易執行
- **風險智能管理**：內建風險控制機制，保護投資資金安全
- **策略多元化**：提供多種預設策略，並支援自定義策略開發
- **完整回測系統**：使用歷史數據評估策略表現，優化交易參數
- **視覺化監控**：直觀的儀表板展示系統運行狀態和交易績效

## 功能概覽

### 🎯 12個功能分類系統 (v3.2 重構)

系統採用模組化設計，將功能整合為12個主要分類，提供清晰的功能組織和權限控制：

#### 🖥️ 系統狀態監控
- 系統運行狀態監控和健康度檢查
- 功能狀態儀表板和性能指標追蹤
- 即時監控和警報系統

#### 🔐 安全與權限管理
- 用戶權限控制和角色管理
- 雙因子認證和安全監控
- 威脅檢測和審計日誌

#### 🤖 多代理系統管理
- 多代理協調和智能任務分配
- 代理性能監控和高級監控功能
- 協作效率優化

#### 📊 數據管理
- 多數據源整合 (Yahoo Finance, Alpha Vantage, Quandl)
- 實時數據獲取和歷史數據回填
- 數據清洗、品質檢查和數據源配置

#### 🎯 策略開發
- 策略創建、編輯和版本控制
- 強化學習策略開發和優化
- 策略測試和性能評估

#### 🧠 AI決策支援
- 智能推薦系統和LLM輔助決策
- 市場分析預測和個人化建議
- 決策分析和評估

#### 💼 投資組合管理
- 組合配置優化和績效評估
- 文本分析和市場情緒監控
- 風險分散和歸因分析

#### ⚠️ 風險管理
- 風險控制和VaR計算
- 動態風險調整和壓力測試
- 監控告警和風險報告

#### 💰 交易執行
- 多券商接口和智能訂單執行
- 實時監控和交易績效分析
- 自動化交易和警報系統

#### 🤖 AI模型管理
- 機器學習模型訓練和評估
- 模型版本控制和自動化部署
- 模型性能監控和優化

#### 📈 回測分析
- 策略回測框架和技術指標計算
- 互動式圖表分析和視覺化
- 績效評估和回測報告

#### 📚 學習中心
- 新手教學指南和知識庫管理
- 學習資源整合和進階教學
- 用戶學習進度追蹤

### 數據分析與處理

- 自動從多個來源收集市場數據
- 處理和清理數據，確保數據質量
- 生成技術指標和特徵
- 分析市場情緒和新聞影響

### 策略管理

- **模組化策略架構** (Phase 2.2 重構)
  - 基礎策略框架 (`src.strategy.base`)
  - 技術分析策略 (`src.strategy.technical`)
  - 機器學習策略 (`src.strategy.ml`)
  - 工具函數庫 (`src.strategy.utils`)
  - 評估指標模組 (`src.strategy.metrics`)

- **支援的策略類型**
  - 移動平均線交叉策略
  - RSI 相對強弱指標策略
  - 機器學習預測策略
  - 自定義策略開發框架

- **策略功能**
  - 自動參數優化
  - 策略回測與評估
  - 策略組合與資產配置
  - 向後相容性支援

### 交易執行

- 自動執行交易訂單
- 支援多種訂單類型
- 整合多家券商 API
- 訂單狀態監控與管理

### 風險管理

- 即時風險監控
- 自動止損與止盈
- 資金管理與部位控制
- 風險預警與通知

### 系統監控與報告

- 系統運行狀態監控
- 交易績效報告
- 資金變化追蹤
- 自動化異常通知

## 快速開始

### 系統需求

- **操作系統**：Windows 10/11, macOS, Linux
- **Python 版本**：Python 3.10 或更高版本
- **記憶體**：至少 8GB RAM（推薦 16GB）
- **儲存空間**：至少 10GB 可用空間
- **網路**：穩定的網路連接

### 安裝指南

#### 1. 安裝 Poetry
```bash
# macOS/Linux
curl -sSL https://install.python-poetry.org | python3 -

# Windows
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

#### 2. 克隆專案
```bash
git clone https://github.com/Cookieeeeeeeeeeeeeee/ai_trading.git
cd ai_trading
```

#### 3. 安裝依賴

**基本安裝（僅核心功能）**：
```bash
poetry install
```

**完整開發環境**：
```bash
poetry install --with dev,test,optional
```

**包含所有功能**：
```bash
poetry install --extras all --with dev,test
```

**特定功能安裝**：
```bash
# 券商 API 功能
poetry install --extras broker

# 監控功能
poetry install --extras monitoring

# 資料庫功能
poetry install --extras database
```

#### 4. 啟動應用

**Web UI**：
```bash
poetry run start
# 或
poetry run web-ui
```

**API 服務器**：
```bash
poetry run api-server
```

**品質檢查**：
```bash
poetry run quality-check
```

詳細安裝說明請參考 [安裝與依賴管理指南](docs/安裝與依賴管理指南.md)。

## 程式碼品質標準

本專案採用嚴格的程式碼品質標準，確保程式碼的可維護性、可讀性和穩定性：

### 品質指標
- **Pylint 評分**: ≥8.5/10 (核心模組 ≥9.0/10)
- **測試覆蓋率**: ≥80% (核心模組 ≥90%)
- **檔案大小**: ≤300行
- **循環複雜度**: ≤10 (函數級別)
- **可維護性指標**: ≥20

### 自動化品質檢查
- **CI/CD 流程**: GitHub Actions 自動化檢查
- **Pre-commit 鉤子**: 提交前自動檢查
- **品質報告**: 自動生成詳細品質報告
- **通知系統**: Slack/Teams 品質警報

### 品質工具
```bash
# 執行完整品質檢查
python scripts/run_quality_checks.py

# 生成品質報告
python scripts/generate_quality_report.py

# 發送品質通知
python scripts/run_notifications.py --check-alerts
```

## 分支策略

本專案採用 Git Flow 分支策略：

- **main**: 生產環境分支，包含穩定的發布版本
- **develop**: 開發主分支，包含最新的開發功能
- **feature/***: 功能開發分支
- **release/***: 發布準備分支
- **hotfix/***: 緊急修復分支

詳細使用指南請參考：[Git Flow 使用指南](docs/Git_Flow_使用指南.md)

## 安裝步驟

1. **克隆此倉庫**：
   ```bash
   git clone https://github.com/yourusername/ai_trading.git
   cd ai_trading
   ```

2. **安裝依賴**：
   ```bash
   # 安裝 Poetry
   pip install poetry

   # 使用 Poetry 安裝依賴
   poetry install

   # 啟動虛擬環境
   poetry shell
   ```

   > **注意**：使用 Poetry 虛擬環境可以避免全局依賴項衝突，確保專案在不同環境中的一致性。

3. **設置環境變數**：
   ```bash
   # 複製環境變數範例
   cp config/environments/.env.example .env

   # 編輯 .env 文件，設置必要的環境變數
   ```

   或者使用環境特定配置：
   ```bash
   # 開發環境
   cp config/environments/.env.development .env

   # 生產環境
   cp config/environments/.env.production .env

   # 測試環境
   cp config/environments/.env.testing .env
   ```

4. **初始化系統**：
   ```bash
   # 初始化資料庫
   python -m src.database.schema

   # 下載初始數據
   python -m src.core.data_ingest --init
   ```

### 啟動系統

#### 使用啟動腳本

最簡單的方法是使用提供的啟動腳本：

```bash
# Windows
.\scripts\powershell\start_app.ps1
```

#### 使用 Poetry 命令

您也可以使用 Poetry 命令運行應用：

```bash
# 🎨 最新版本 (v3.0 重新設計版 - 推薦)
poetry run python -m streamlit run src/ui/web_ui_redesigned.py --server.address=127.0.0.1 --server.port=8501

# 📊 生產版本 (v3.0 整合版 - 推薦用於生產環境)
poetry run python -m streamlit run src/ui/web_ui_production.py --server.address=127.0.0.1 --server.port=8502

# ⚠️ 傳統版本 (v2.2 - 已過時，僅供向後相容)
# 注意：此版本已被標記為過時，建議使用上述版本
poetry run python -m streamlit run src/ui/web_ui_production_legacy.py --server.address=127.0.0.1 --server.port=8503

# 🔄 版本對比測試
python launch_ui_comparison.py

# 使用 Poetry 腳本 (啟動最新版本)
poetry run web
```

啟動後，可以通過瀏覽器訪問系統儀表板：

- **最新版本 (推薦)**: <http://localhost:8501>
- **傳統版本**: <http://localhost:8502>

## 使用案例

### 個人投資者

- 自動執行交易策略，無需全天盯盤
- 基於數據分析做出更理性的投資決策
- 通過回測優化個人交易策略
- 控制風險，避免情緒化交易

### 專業交易團隊

- 同時管理多個交易策略和資產組合
- 實現策略的量化和自動化
- 提高交易效率和準確性
- 全面的風險管理和績效分析

## 支援的數據源

- **Yahoo Finance**：全球股票市場數據
- **Alpha Vantage**：基本面和技術面數據
- **FinMind**：台灣股市專用數據
- **券商 API**：即時交易數據和執行
- **新聞 API**：市場新聞和情緒分析

## 支援的券商

- **永豐證券** - 台股交易支援
- **富途證券** - 港股、美股交易支援
- **Interactive Brokers** ⭐ - 全球股票、期權、期貨、外匯交易支援
  - 股票交易：美股、台股、港股等全球市場
  - 期權交易：完整的期權策略支援 (Covered Call, Protective Put, Straddle 等)
  - Greeks 計算：Delta, Gamma, Theta, Vega 風險指標
  - 多市場整合：統一 API 介面操作全球市場
- **模擬交易** - 用於測試和學習

## 📚 文檔導航

### 🌟 主要功能指南
- [使用者功能指南](docs/使用者功能指南.md) - **完整的使用者功能說明**
  - 交易自動化功能 (自動執行策略、數據分析決策、回測優化、風險控制)
  - 券商整合功能 (永豐證券、富途證券、Interactive Brokers API 支援、模擬交易)
  - 風險管理功能 (實時監控、緊急處理、資金管理、動態停損機制、一鍵平倉)
  - 新手友好功能 (引導系統、示範策略、模擬環境、進度追蹤、量化交易教程)
  - 通知服務功能 (交易通知、風險警報、系統監控通知)

- [開發者功能指南](docs/開發者功能指南.md) - **完整的開發者功能說明**
  - API整合功能 (RESTful 設計、OpenAPI 3.0、API 文檔、SDK 支援)
  - 開發工具功能 (代碼品質工具、測試框架、CI/CD 整合)
  - 部署選項功能 (Docker、Docker Compose、Kubernetes、零停機部署)
  - 監控與日誌功能 (Prometheus/Grafana、ELK Stack、Grafana Loki、結構化日誌)
  - 安全功能 (RBAC 權限、多重身份驗證、API 金鑰管理、資料加密)
  - 完整文檔功能 (架構說明、API 指南、部署指南、貢獻指南、模組設計)

### 📖 詳細操作手冊
- [使用者手冊](docs/使用者手冊/) - 詳細的操作指南
  - [一鍵安裝指南](docs/使用者手冊/一鍵安裝指南.md) - 5分鐘快速安裝
  - [量化交易基礎教程](docs/使用者手冊/量化交易基礎教程.md) - 新手入門教程
  - [第一次回測教程](docs/使用者手冊/第一次回測教程.md) - 手把手回測指導
  - [Live Trading 安全操作指南](docs/使用者手冊/Live_Trading_安全操作指南.md) - 實盤交易安全規範
  - [券商API設定教程](docs/使用者手冊/券商API設定教程.md) - 各券商API配置
  - [風險管理入門指南](docs/使用者手冊/風險管理入門指南.md) - 風險控制基礎
  - [常見錯誤與解決方案](docs/使用者手冊/常見錯誤與解決方案.md) - 問題排除指南

### 🛠️ 技術開發文檔
- [開發者指南](docs/開發者指南/) - 完整的開發者文檔
  - [系統架構說明](docs/開發者指南/系統架構說明.md) - 系統設計和架構
  - [API使用指南](docs/開發者指南/API使用指南.md) - RESTful API 詳細說明
  - [部署指南](docs/開發者指南/部署指南.md) - 生產環境部署流程
  - [代碼貢獻指南](docs/開發者指南/代碼貢獻指南.md) - 代碼提交規範

### 🚀 Interactive Brokers 專業文檔 ⭐
- [IB 模組概述](docs/modules/interactive_brokers/README.md) - IB 適配器架構和使用指南
- [期權交易技術文檔](docs/modules/interactive_brokers/ib_options.md) - 期權交易功能詳解
- [IB API 參考](docs/API/ib_api_reference.md) - 完整的 API 參考文檔
- [IB 測試指南](docs/testing/test_ib_adapter_enhanced.md) - 測試框架和用例
- [IB 改進報告](docs/reports/IB_Adapter_Enhancement_Report.md) - 詳細的改進報告

### 📋 專案管理文檔
- [Todo List](docs/Todo_list.md) - 專案進度追蹤和任務管理
- [Google Style Docstring 規範](docs/Google_Style_Docstring_規範.md) - 文檔撰寫規範
- [Git Flow 使用指南](docs/Git_Flow_使用指南.md) - 版本控制流程
- [常見問題](docs/Q&A常見問題.md) - 常見問題與解答

### 🔧 維運與工具文檔
- [維運指南](docs/維運指南/) - 系統維運相關文檔
  - [系統監控指南](docs/維運指南/系統監控指南.md) - 系統健康狀態監控、效能指標追蹤、告警機制設定
  - [備份和恢復程序](docs/維運指南/備份和恢復程序.md) - 資料庫備份策略、設定檔備份、系統狀態快照及恢復流程
  - [災難恢復計劃](docs/維運指南/災難恢復計劃.md) - 系統故障應對方案、資料遺失恢復程序、服務中斷處理流程
  - [效能調優指南](docs/維運指南/效能調優指南.md) - 系統效能瓶頸診斷、資源使用優化、交易延遲改善
- [工具使用手冊](docs/工具使用手冊/) - 開發工具使用指南
- [最佳實踐](docs/最佳實踐/) - 開發最佳實踐

## 開發指南

### 虛擬環境管理

本專案使用 Poetry 進行依賴管理和虛擬環境設置，以下是一些常用的 Poetry 命令：

- **進入虛擬環境**：
  ```bash
  poetry shell
  ```

- **添加新依賴**：
  ```bash
  # 添加運行時依賴
  poetry add package-name

  # 添加開發依賴
  poetry add --group dev package-name
  ```

- **更新依賴**：
  ```bash
  # 更新所有依賴
  poetry update

  # 更新特定依賴
  poetry update package-name
  ```

- **查看虛擬環境信息**：
  ```bash
  poetry env info
  ```

- **列出所有依賴**：
  ```bash
  poetry show
  ```

### 常見問題解決

- **端口被占用**：如果啟動時提示端口被占用，可以使用以下命令查找並終止占用端口的進程：
  ```bash
  # Windows
  netstat -ano | findstr 8501
  taskkill /F /PID <進程ID>
  ```

- **依賴衝突**：如果遇到依賴衝突，可以嘗試更新 pyproject.toml 文件中的依賴版本，然後運行：
  ```bash
  poetry lock --no-update
  poetry install
  ```

## 社群與支援

- **GitHub Issues**：報告問題和功能請求
- **討論區**：[討論區連結](https://github.com/yourusername/ai_trading/discussions)
- **電子郵件**：[support@example.com](mailto:support@example.com)

## 授權協議

本專案採用 MIT 授權協議 - 詳見 [LICENSE](LICENSE) 文件
