#!/usr/bin/env python3
"""
Git Flow 分支策略設置腳本

此腳本設置 Git Flow 分支策略，包括：
1. 創建 develop 分支
2. 設置分支保護規則
3. 更新 README.md 說明分支使用規範
"""

import os
import sys
import subprocess
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_command(command: str, cwd: str = None) -> tuple[int, str, str]:
    """執行命令並返回結果"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd or project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def check_git_status():
    """檢查 Git 狀態"""
    print("🔍 檢查 Git 狀態...")

    # 檢查是否在 Git 倉庫中
    returncode, stdout, stderr = run_command("git status --porcelain")
    if returncode != 0:
        print(f"❌ 不在 Git 倉庫中: {stderr}")
        return False

    # 檢查是否有未提交的變更
    if stdout.strip():
        print("⚠️ 發現未提交的變更")
        print("📝 未提交的檔案:")
        for line in stdout.strip().split("\n"):
            print(f"  {line}")
        return False

    print("✅ Git 狀態乾淨")
    return True


def create_develop_branch():
    """創建 develop 分支"""
    print("\n🌿 創建 develop 分支...")

    # 檢查 develop 分支是否已存在
    returncode, stdout, stderr = run_command("git branch --list develop")
    if stdout.strip():
        print("✅ develop 分支已存在")
        return True

    # 創建 develop 分支
    returncode, stdout, stderr = run_command("git checkout -b develop")
    if returncode != 0:
        print(f"❌ 創建 develop 分支失敗: {stderr}")
        return False

    print("✅ develop 分支創建成功")

    # 推送到遠程
    print("📤 推送 develop 分支到遠程...")
    returncode, stdout, stderr = run_command("git push -u origin develop")
    if returncode != 0:
        print(f"⚠️ 推送失敗: {stderr}")
        print("💡 請稍後手動推送: git push -u origin develop")
    else:
        print("✅ develop 分支已推送到遠程")

    return True


def setup_git_flow_config():
    """設置 Git Flow 配置"""
    print("\n⚙️ 設置 Git Flow 配置...")

    # Git Flow 配置
    git_flow_config = {
        "gitflow.branch.master": "main",
        "gitflow.branch.develop": "develop",
        "gitflow.prefix.feature": "feature/",
        "gitflow.prefix.release": "release/",
        "gitflow.prefix.hotfix": "hotfix/",
        "gitflow.prefix.support": "support/",
        "gitflow.prefix.versiontag": "v",
    }

    for key, value in git_flow_config.items():
        returncode, stdout, stderr = run_command(f"git config {key} {value}")
        if returncode == 0:
            print(f"✅ 設置 {key} = {value}")
        else:
            print(f"⚠️ 設置 {key} 失敗: {stderr}")

    return True


def create_gitflow_readme():
    """創建 Git Flow 使用說明"""
    print("\n📝 創建 Git Flow 使用說明...")

    gitflow_guide = """
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
"""

    gitflow_file = project_root / "docs" / "Git_Flow_使用指南.md"
    with open(gitflow_file, "w", encoding="utf-8") as f:
        f.write(gitflow_guide.strip())

    print(f"✅ Git Flow 使用指南已創建: {gitflow_file}")
    return True


def update_readme():
    """更新 README.md 添加分支說明"""
    print("\n📝 更新 README.md...")

    readme_file = project_root / "README.md"
    if not readme_file.exists():
        print("⚠️ README.md 不存在，跳過更新")
        return True

    # 讀取現有內容
    with open(readme_file, "r", encoding="utf-8") as f:
        content = f.read()

    # 檢查是否已包含分支說明
    if "## 分支策略" in content:
        print("✅ README.md 已包含分支說明")
        return True

    # 添加分支說明
    branch_section = """
## 分支策略

本專案採用 Git Flow 分支策略：

- **main**: 生產環境分支，包含穩定的發布版本
- **develop**: 開發主分支，包含最新的開發功能
- **feature/***: 功能開發分支
- **release/***: 發布準備分支
- **hotfix/***: 緊急修復分支

詳細使用指南請參考：[Git Flow 使用指南](docs/Git_Flow_使用指南.md)

"""

    # 在適當位置插入分支說明
    if "## 安裝" in content:
        content = content.replace("## 安裝", branch_section + "## 安裝")
    elif "## Installation" in content:
        content = content.replace("## Installation", branch_section + "## Installation")
    else:
        # 在文件末尾添加
        content += branch_section

    # 寫回文件
    with open(readme_file, "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ README.md 已更新")
    return True


def main():
    """主函數"""
    print("🚀 開始設置 Git Flow 分支策略")
    print("=" * 50)

    # 檢查 Git 狀態
    if not check_git_status():
        print("\n❌ Git 狀態檢查失敗")
        print("💡 請先提交或暫存所有變更，然後重新運行此腳本")
        return 1

    # 創建 develop 分支
    if not create_develop_branch():
        print("\n❌ 創建 develop 分支失敗")
        return 1

    # 設置 Git Flow 配置
    if not setup_git_flow_config():
        print("\n❌ 設置 Git Flow 配置失敗")
        return 1

    # 創建使用指南
    if not create_gitflow_readme():
        print("\n❌ 創建使用指南失敗")
        return 1

    # 更新 README
    if not update_readme():
        print("\n❌ 更新 README 失敗")
        return 1

    print("\n" + "=" * 50)
    print("✅ Git Flow 分支策略設置完成！")
    print("\n📋 後續步驟:")
    print("1. 在 GitHub 上設置分支保護規則")
    print("2. 配置 Pull Request 模板")
    print("3. 設置自動化 CI/CD 檢查")
    print("4. 培訓團隊成員使用 Git Flow")

    return 0


if __name__ == "__main__":
    sys.exit(main())
