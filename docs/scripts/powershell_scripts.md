# PowerShell 腳本說明

本文檔說明專案中使用的 PowerShell 腳本及其功能。

## 腳本概述

專案中的 PowerShell 腳本主要用於自動化開發流程、環境設置和安全審計等任務。所有腳本都位於 `scripts/powershell` 目錄下。

## 腳本列表

### 1. `audit_security.ps1`

**功能**：安全審計腳本，用於檢查專案中的安全問題。

**主要功能**：
- 檢查必要工具的安裝狀態（Git、Python）
- 檢查 .gitignore 文件是否包含必要的安全模式
- 檢查敏感文件是否被跟踪
- 檢查硬編碼的敏感信息
- 檢查 .env 文件是否包含實際的 API 金鑰

**使用方法**：
```powershell
.\scripts\powershell\audit_security.ps1
```

### 2. `clean_git_history.ps1`

**功能**：清理 Git 歷史中的敏感信息。

**主要功能**：
- 創建 Git 倉庫的備份
- 清理 .env 文件
- 清理私鑰文件
- 清理可能包含 API 金鑰的文件

**使用方法**：
```powershell
.\scripts\powershell\clean_git_history.ps1
```

**注意**：此腳本會重寫 Git 歷史，所有提交 ID 將改變。如果倉庫已經推送到遠端，需要使用 --force 推送。

### 3. `push_to_github.ps1`

**功能**：推送代碼到 GitHub。

**主要功能**：
- 添加遠端倉庫
- 提交更改
- 使用 --force 推送到遠端

**使用方法**：
```powershell
.\scripts\powershell\push_to_github.ps1
```

**注意**：此腳本使用 --force 推送，會覆蓋遠端倉庫的歷史。

### 4. `setup_clean_env.ps1`

**功能**：設置乾淨的環境。

**主要功能**：
- 創建 .env 文件（如果不存在）

**使用方法**：
```powershell
.\scripts\powershell\setup_clean_env.ps1
```

## 最佳實踐

1. **安全審計**：定期運行 `audit_security.ps1` 腳本，檢查專案中的安全問題。

2. **敏感信息處理**：如果不小心將敏感信息提交到版本控制系統，使用 `clean_git_history.ps1` 腳本清理 Git 歷史。

3. **環境設置**：在新環境中設置專案時，使用 `setup_clean_env.ps1` 腳本創建必要的配置文件。

4. **代碼推送**：謹慎使用 `push_to_github.ps1` 腳本，因為它使用 --force 推送，會覆蓋遠端倉庫的歷史。

## 注意事項

- 這些腳本包含敏感操作，如清理 Git 歷史和強制推送，請謹慎使用。
- 在運行腳本前，請確保已經備份重要數據。
- 腳本中的路徑可能需要根據實際情況進行調整。
