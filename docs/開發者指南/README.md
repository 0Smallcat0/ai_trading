# AI 股票自動交易系統 - 開發者指南

## 👨‍💻 歡迎開發者

歡迎加入 AI 股票自動交易系統的開發！本指南將幫助您了解系統架構、開發流程和貢獻方式。

## 📚 指南目錄

### 系統架構與設計
- [系統架構](./系統架構.md) - 系統架構詳解、組件說明、數據流向
- [API文檔](./API文檔.md) - 服務層API接口、使用示例、最佳實踐

### 核心開發指南
- [API整合](./API整合.md) - RESTful 設計、OpenAPI 3.0、API 文檔、SDK 支援
- [部署指南](./部署指南.md) - Docker、Docker Compose、Kubernetes、零停機部署
- [代碼貢獻指南](./代碼貢獻指南.md) - 貢獻流程、代碼規範、提交規範
- [品質標準](./品質標準.md) - 代碼品質標準、測試覆蓋率要求

### 模組技術文檔 ⭐
- [Interactive Brokers 模組](./modules/interactive_brokers/README.md) - IB 適配器架構和使用指南
  - ⚠️ **重要更新**: 建議使用 `src.execution.ib_adapter_refactored` 而非 `src.execution.ib_adapter`
- [期權交易技術文檔](./modules/interactive_brokers/ib_options.md) - 期權交易功能詳解
- [券商 API 整合](./modules/broker_api_integration.md) - 券商 API 整合指南
- [即時交易核心](./modules/live_trading_core.md) - 即時交易核心模組
- [策略執行引擎](./modules/strategy_execution_engine.md) - 策略執行引擎文檔
- [風險管理模組](./modules/risk_management.md) - 模組化風險管理系統
  - ⚠️ **重要更新**: 建議使用 `src.risk_management.*` 模組而非 `src.core.risk_control`

### 測試指南
- [IB 測試指南](./testing/test_ib_adapter_enhanced.md) - 測試框架和用例

### 開發規範與工具
- [API使用手冊](API使用手冊.md) - API接口使用說明
- [Git Flow 使用指南](Git_Flow_使用指南.md) - Git工作流程規範
- [Google Style Docstring 規範](Google_Style_Docstring_規範.md) - 代碼文檔規範

### 工具與品質
- [IB 品質檢查工具](../工具使用手冊/ib_quality_check.md) - 代碼品質檢查工具使用指南
- [品質檢查工具](../工具使用手冊/品質檢查工具.md) - 通用代碼品質工具

## 🏗️ 系統架構

### 架構總覽

系統採用分層架構設計，包含以下主要層次：

```
┌─────────────────────────────────────────────────────────────┐
│                    AI 股票自動交易系統                        │
├─────────────────────────────────────────────────────────────┤
│                     使用者界面層 (UI Layer)                   │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│  │   Web 界面      │ │   移動端界面     │ │   API 界面      │ │
│  │  (Streamlit)    │ │   (Future)      │ │  (REST/GraphQL) │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                     服務管理層 (Service Layer)                │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│  │  服務管理器      │ │  服務註冊器      │ │  UI 服務客戶端   │ │
│  │ ServiceManager  │ │ServiceRegistry  │ │UIServiceClient  │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                     業務服務層 (Business Services)            │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ │
│  │   回測服務      │ │   交易服務      │ │  風險管理服務    │ │
│  │BacktestService  │ │ TradingService  │ │RiskMgmtService  │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 技術棧
- **後端**: Python 3.10+, FastAPI, SQLAlchemy
- **前端**: Streamlit, Plotly, HTML/CSS/JavaScript
- **數據庫**: SQLite (開發), InfluxDB (時序數據), Redis (快取)
- **部署**: Docker, Docker Compose, Nginx
- **快取**: Redis
- **訊息佇列**: Celery
- **監控**: Prometheus, Grafana
- **部署**: Docker, Kubernetes

### 代碼品質標準
- **Pylint 評分**: ≥8.5/10 (目標 9.0+)
- **測試覆蓋率**: ≥80% (核心模組 ≥90%)
- **函數複雜度**: ≤50行，McCabe複雜度 ≤10
- **檔案大小**: ≤300行每模組
- **文檔覆蓋率**: 100% Google Style Docstring

### 開發工具
```bash
# 代碼格式化
black src/
isort src/

# 代碼檢查
pylint src/
flake8 src/

# 類型檢查
mypy src/

# 測試執行
pytest tests/ --cov=src/
```

## 🚀 快速開始

### 環境設置

```bash
# 1. 克隆專案
git clone https://github.com/Cookieeeeeeeeeeeeeee/ai_trading.git
cd ai_trading

# 2. 安裝 Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 3. 安裝依賴
poetry install --with dev,test

# 4. 安裝 pre-commit hooks
pre-commit install

# 5. 啟動開發伺服器
poetry run web-ui  # 啟動 Web UI
# 或
poetry run api-server  # 啟動 API 伺服器
```

## 📞 開發者支援

如有任何開發相關問題，請參考 [常見問題](../Q&A常見問題.md) 或聯繫開發團隊。

## 🧪 測試策略

### 測試層級
- **單元測試**: 測試個別函數和類別
- **整合測試**: 測試模組間的整合
- **端到端測試**: 測試完整的用戶流程
- **性能測試**: 測試系統性能和負載
- **安全測試**: 測試安全漏洞和威脅

### 測試覆蓋率目標
```
整體覆蓋率: ≥80%
核心模組: ≥90%
API端點: 100%
風險管理: ≥95%
交易執行: ≥95%
```

## 📈 性能指標

### 系統性能目標
- **API響應時間**: <200ms (95th percentile)
- **頁面載入時間**: <2s
- **回測執行時間**: <1s/1000筆資料
- **即時數據延遲**: <100ms
- **系統可用性**: >99.9%

### 監控指標
- CPU 使用率 <70%
- 記憶體使用率 <80%
- 磁碟使用率 <85%
- 網路延遲 <50ms
- 錯誤率 <0.1%

## 🔒 安全要求

### 安全標準
- **認證**: JWT + 2FA/MFA
- **授權**: RBAC 權限控制
- **加密**: AES-256 數據加密
- **通訊**: TLS 1.3 加密傳輸
- **審計**: 完整操作日誌

### 安全檢查
```bash
# 依賴漏洞掃描
safety check

# 代碼安全掃描
bandit -r src/

# 密鑰檢查
truffleHog --regex --entropy=False .
```

## 📞 開發者支援

### 技術支援
- **開發者論壇**: [論壇連結]
- **技術文檔**: [文檔網站]
- **API文檔**: [API文檔網站]
- **GitHub Issues**: [Issues連結]

### 社群資源
- **開發者群組**: [Discord/Slack連結]
- **技術分享**: [技術部落格]
- **代碼範例**: [範例倉庫]
- **最佳實踐**: [最佳實踐指南]

## 🚀 發布流程

### 版本管理
- **主版本**: 重大架構變更
- **次版本**: 新功能添加
- **修訂版本**: Bug修復和小改進
- **預發布**: Alpha, Beta, RC版本

### 發布檢查清單
- [ ] 所有測試通過
- [ ] 代碼品質檢查通過
- [ ] 安全掃描通過
- [ ] 文檔更新完成
- [ ] 變更日誌更新
- [ ] 版本號更新

---

**版本**: v1.0.0  
**更新日期**: 2025年1月13日  
**維護團隊**: AI Trading System 開發團隊

**變更歷史**:
- v1.0.0 (2025-01-13): 初始版本，建立完整開發者指南結構


