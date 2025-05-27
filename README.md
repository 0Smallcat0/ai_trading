# AI 股票自動交易系統

![版本](https://img.shields.io/badge/版本-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-3.8+-green)
![授權](https://img.shields.io/badge/授權-MIT-orange)

AI 股票自動交易系統是一個整合人工智能技術的自動化交易平台，能夠分析多維度市場數據，生成智能交易決策，並執行自動化交易。系統專為台灣及全球股票市場設計，適合個人投資者和專業交易團隊使用。

## 系統特色

- **多維數據分析**：整合基本面、技術面和新聞情緒數據，全方位分析市場
- **AI 驅動決策**：使用機器學習和深度學習模型，自動生成交易訊號
- **自動化交易**：支援多家券商 API，實現全自動交易執行
- **風險智能管理**：內建風險控制機制，保護投資資金安全
- **策略多元化**：提供多種預設策略，並支援自定義策略開發
- **完整回測系統**：使用歷史數據評估策略表現，優化交易參數
- **視覺化監控**：直觀的儀表板展示系統運行狀態和交易績效

## 功能概覽

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
- **Python 版本**：Python 3.8 或更高版本
- **記憶體**：至少 8GB RAM
- **儲存空間**：至少 10GB 可用空間
- **網路**：穩定的網路連接

#
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
# 使用 Poetry 腳本
poetry run web

# 或者直接運行 Streamlit
poetry run python -m streamlit run src\ui\web_ui.py --server.address=127.0.0.1 --server.port=8501 --server.headless=true
```

啟動後，可以通過瀏覽器訪問系統儀表板：`http://localhost:8501`

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

- **永豐證券**
- **富途證券**
- **Interactive Brokers**
- **模擬交易**（用於測試）

## 文檔導航

### 使用者文檔
- [使用者手冊](docs/使用者手冊.md) - 系統使用指南
- [常見問題](docs/Q&A常見問題.md) - 常見問題與解答
- [配置說明](docs/配置說明.md) - 系統配置結構與使用方法

### 開發者文檔
- [策略開發指南](docs/策略開發指南.md) - 自定義策略開發
- [API 文檔](docs/共用工具說明/API整理.md) - API 使用說明
- [策略模組結構](docs/modules/strategy_module_structure.md) - Phase 2.2 模組化架構
- [Phase 2.2 遷移指南](docs/Phase2.2_遷移指南.md) - 從舊 API 遷移到新 API

### 維運文檔
- [系統監控指南](docs/維運指南/系統監控指南.md) - 系統健康狀態監控、效能指標追蹤、告警機制設定
- [備份和恢復程序](docs/維運指南/備份和恢復程序.md) - 資料庫備份策略、設定檔備份、系統狀態快照及恢復流程
- [災難恢復計劃](docs/維運指南/災難恢復計劃.md) - 系統故障應對方案、資料遺失恢復程序、服務中斷處理流程
- [效能調優指南](docs/維運指南/效能調優指南.md) - 系統效能瓶頸診斷、資源使用優化、交易延遲改善

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
