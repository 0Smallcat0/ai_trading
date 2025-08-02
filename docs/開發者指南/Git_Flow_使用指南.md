# Git Flow 分支策略使用指南

## 分支結構

### 主要分支
- **main**: 生產環境分支，包含穩定的發布版本
- **develop**: 開發主分支，包含最新的開發功能

### 支援分支
- **feature/**: 功能開發分支，從 develop 分出，完成後合併回 develop
- **release/**: 發布準備分支，從 develop 分出，完成後合併到 main 和 develop
- **hotfix/**: 緊急修復分支，從 main 分出，完成後合併到 main 和 develop

## 工作流程

### 1. 功能開發
```bash
# 從 develop 創建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/new-feature

# 開發完成後
git checkout develop
git pull origin develop
git merge feature/new-feature
git push origin develop
git branch -d feature/new-feature
```

### 2. 發布準備
```bash
# 從 develop 創建發布分支
git checkout develop
git pull origin develop
git checkout -b release/v1.0.0

# 發布準備完成後
git checkout main
git merge release/v1.0.0
git tag v1.0.0
git push origin main --tags

git checkout develop
git merge release/v1.0.0
git push origin develop
git branch -d release/v1.0.0
```

### 3. 緊急修復
```bash
# 從 main 創建修復分支
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug

# 修復完成後
git checkout main
git merge hotfix/critical-bug
git tag v1.0.1
git push origin main --tags

git checkout develop
git merge hotfix/critical-bug
git push origin develop
git branch -d hotfix/critical-bug
```

## 分支命名規範

### 功能分支
- 格式: `feature/{功能名稱}`
- 範例: `feature/user-authentication`, `feature/chart-optimization`

### 發布分支
- 格式: `release/v{主版本}.{次版本}.{修訂版本}`
- 範例: `release/v1.0.0`, `release/v2.3.0`

### 修復分支
- 格式: `hotfix/{問題描述}`
- 範例: `hotfix/login-crash`, `hotfix/data-corruption`

## 提交訊息規範

### 格式
```
<類型>: <簡短描述>

<詳細描述>

<相關問題>
```

### 類型
- **feat**: 新功能
- **fix**: 錯誤修復
- **docs**: 文檔更新
- **style**: 代碼風格變更
- **refactor**: 代碼重構
- **perf**: 性能優化
- **test**: 測試相關
- **chore**: 構建過程或輔助工具變更

### 範例
```
feat: 添加用戶認證功能

實現了基於 JWT 的用戶認證系統，包括登入、登出和權限控制。

Closes #123
```

## 合併請求 (Pull Request) 流程

### 1. 創建合併請求
- 推送功能分支到遠程倉庫
- 在 GitHub/GitLab 創建合併請求
- 指定目標分支 (通常是 develop)
- 填寫詳細的描述和變更說明

### 2. 代碼審查
- 至少需要一位團隊成員審查
- 解決審查中提出的問題
- 通過所有自動化測試

### 3. 合併
- 確認所有審查意見已解決
- 確認 CI/CD 管道通過
- 使用 "Squash and merge" 選項合併
- 刪除已合併的功能分支

## 版本標籤規範

### 語義化版本
- 格式: `v{主版本}.{次版本}.{修訂版本}`
- **主版本**: 不兼容的 API 變更
- **次版本**: 向後兼容的功能新增
- **修訂版本**: 向後兼容的錯誤修復

### 標籤訊息
```
Version v1.0.0

主要變更:
- 實現用戶認證系統
- 添加數據可視化功能
- 優化數據處理性能

完整變更日誌: https://github.com/org/repo/releases/tag/v1.0.0
```

## 常見問題與解決方案

### 合併衝突
1. 獲取最新的目標分支
   ```bash
   git checkout develop
   git pull origin develop
   ```
2. 切換回功能分支並變基
   ```bash
   git checkout feature/my-feature
   git rebase develop
   ```
3. 解決衝突並繼續變基
   ```bash
   # 解決衝突後
   git add .
   git rebase --continue
   ```

### 撤銷提交
- 撤銷最後一次提交 (保留變更)
  ```bash
  git reset --soft HEAD~1
  ```
- 撤銷最後一次提交 (丟棄變更)
  ```bash
  git reset --hard HEAD~1
  ```

### 臨時保存工作
- 保存當前工作
  ```bash
  git stash save "WIP: 功能實現中"
  ```
- 恢復保存的工作
  ```bash
  git stash pop
  ```

## 最佳實踐

### 1. 頻繁提交
- 小批量、頻繁地提交變更
- 每個提交專注於單一邏輯變更
- 保持提交訊息清晰明確

### 2. 定期同步
- 定期從 develop 分支同步最新變更
- 使用 rebase 保持提交歷史整潔
- 及早解決潛在的合併衝突

### 3. 分支管理
- 功能完成後及時刪除功能分支
- 避免長時間存在的功能分支
- 定期清理已合併的遠程分支

### 4. 代碼審查
- 所有代碼變更都需要審查
- 使用 PR 模板確保提供足夠信息
- 及時回應審查意見

---

**文檔版本**: v1.0  
**最後更新**: 2025-01-15  
**維護團隊**: AI Trading System Development Team
