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
git checkout -b hotfix/critical-fix

# 修復完成後
git checkout main
git merge hotfix/critical-fix
git tag v1.0.1
git push origin main --tags

git checkout develop
git merge hotfix/critical-fix
git push origin develop
git branch -d hotfix/critical-fix
```

## 分支保護規則

### main 分支
- 禁止直接推送
- 需要 Pull Request 審查
- 需要通過所有狀態檢查
- 需要分支是最新的

### develop 分支
- 禁止直接推送
- 需要 Pull Request 審查
- 需要通過基本狀態檢查

## 提交規範

使用 Conventional Commits 格式：
```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### 類型 (type)
- `feat`: 新功能
- `fix`: 錯誤修復
- `docs`: 文檔變更
- `style`: 代碼格式變更
- `refactor`: 重構
- `test`: 測試相關
- `chore`: 構建過程或輔助工具變更

### 範例
```
feat(auth): add JWT authentication
fix(api): resolve data validation issue
docs(readme): update installation guide
```
