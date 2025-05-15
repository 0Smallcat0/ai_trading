# 清理 Git 歷史中的敏感資訊
# Clean sensitive information from Git history

# 確保當前目錄是 Git 倉庫根目錄
# Ensure current directory is Git repository root
$repoRoot = (git rev-parse --show-toplevel).Trim()
$currentPath = (Get-Location).Path.Replace("\", "/")
if ($repoRoot -ne $currentPath) {
    Write-Host "切換到 Git 倉庫根目錄: $repoRoot"
    Write-Host "Switching to Git repository root: $repoRoot"
    Set-Location $repoRoot
}

# 確認用戶是否了解此操作的風險
# Confirm user understands the risks of this operation
Write-Warning "此操作將重寫 Git 歷史，所有提交 ID 將改變"
Write-Warning "This operation will rewrite Git history, all commit IDs will change"
Write-Warning "如果此倉庫已經推送到遠端，您需要使用 --force 推送"
Write-Warning "If this repository has been pushed to remote, you will need to use --force push"
$confirm = Read-Host "是否繼續？(y/n)"
if ($confirm -ne "y") {
    Write-Host "操作已取消"
    Write-Host "Operation cancelled"
    exit 0
}

# 創建備份
# Create backup
Write-Host "創建備份..."
Write-Host "Creating backup..."
$backupDir = "../git_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Copy-Item -Path ".git" -Destination $backupDir -Recurse
Write-Host "備份已創建：$backupDir"
Write-Host "Backup created: $backupDir"

# 清理敏感文件
# Clean sensitive files
Write-Host "清理敏感文件..."
Write-Host "Cleaning sensitive files..."

# 清理 .env 文件
# Clean .env files
Write-Host "清理 .env 文件..."
Write-Host "Cleaning .env files..."
git filter-repo --path .env --invert-paths --force
git filter-repo --path .envs/.env.dev --invert-paths --force
git filter-repo --path .envs/.env.test --invert-paths --force
git filter-repo --path .envs/.env.prod --invert-paths --force

# 清理私鑰文件
# Clean private key files
Write-Host "清理私鑰文件..."
Write-Host "Cleaning private key files..."
git filter-repo --path config/keys/audit_private.pem --invert-paths --force
git filter-repo --path config/keys/audit_public.pem --invert-paths --force

# 清理可能包含 API 金鑰的文件
# Clean files that may contain API keys
Write-Host "清理可能包含 API 金鑰的文件..."
Write-Host "Cleaning files that may contain API keys..."
git filter-repo --path config/api_keys.json --invert-paths --force

# 完成
# Done
Write-Host "Git 歷史清理完成"
Write-Host "Git history cleaning completed"
Write-Host "請檢查倉庫狀態，然後使用 --force 推送到遠端"
Write-Host "Please check repository status, then use --force to push to remote"
