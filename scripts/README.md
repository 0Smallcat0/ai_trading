# 腳本目錄 (Scripts)

此目錄包含獨立的執行腳本，用於自動化任務、批次處理和系統維護。這些腳本通常是獨立的，可以直接從命令行執行。

## 目錄用途

- 提供獨立的自動化腳本
- 存放批次處理和定期任務的腳本
- 包含系統維護和管理工具

## 腳本分類

### 🚀 核心功能腳本
- **資料收集**: `run_crawler.py`, `run_crawler_mcp.py`, `run_twse_crawler.py`
- **策略管理**: `run_strategy_adjustment.py`, `start_risk_management_demo.py`
- **應用啟動**: `run_web_ui.py`

### 🧪 測試執行腳本
- **基礎測試**: `run_tests.py`, `run_comprehensive_tests.py`
- **效能測試**: `run_performance_tests.py`
- **安全測試**: `run_security_tests.py`

### 🛠️ 開發工具腳本
- **代碼品質**: `code_quality_check.py`, `format_code.py`
- **測試覆蓋**: `track_coverage.py`
- **版本控制**: `setup_git_flow.py`

### 💻 PowerShell 腳本
- **環境設置**: `powershell/setup_clean_env.ps1`
- **安全審計**: `powershell/audit_security.ps1`
- **部署工具**: `powershell/push_to_github.ps1`, `powershell/start_app.ps1`

## 使用指南

此目錄中的腳本通常可以直接從命令行執行：

```bash
python scripts/script_name.py [參數]
```

PowerShell 腳本執行：
```powershell
.\scripts\powershell\script_name.ps1
```

## 注意事項

- 此目錄中的腳本應該是獨立的，不應該依賴於 `src` 目錄中的模組
- 如果腳本需要與主要應用程式整合，應該放在 `src/scripts` 目錄中
- 每個腳本應該包含完整的文檔和使用說明

## 清理記錄

**最後清理時間**: 2024-12-19
**清理內容**: 移除了 20 個一次性使用、已完成任務或重複功能的腳本
**保留標準**: 核心功能、測試執行、開發工具、維護腳本
