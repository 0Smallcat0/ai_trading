# 推送到 GitHub
# Push to GitHub

# 確認用戶是否了解此操作的風險
# Confirm user understands the risks of this operation
Write-Warning "此操作將使用 --force 推送到遠端，這將覆蓋遠端倉庫的歷史"
Write-Warning "This operation will use --force to push to remote, which will overwrite the history of the remote repository"
$confirm = Read-Host "是否繼續？(y/n)"
if ($confirm -ne "y") {
    Write-Host "操作已取消"
    Write-Host "Operation cancelled"
    exit 0
}

# 添加遠端倉庫
# Add remote repository
Write-Host "添加遠端倉庫..."
Write-Host "Adding remote repository..."
git remote add origin https://github.com/Cookieeeeeeeeeeeeeee/ai_trading.git

# 提交更改
# Commit changes
Write-Host "提交更改..."
Write-Host "Committing changes..."
git add .
git commit -m "Fix: Removed leaked secret key and refactored code to use environment variables"

# 推送到遠端
# Push to remote
Write-Host "推送到遠端..."
Write-Host "Pushing to remote..."
git push origin main --force

# 完成
# Done
Write-Host "推送完成"
Write-Host "Push completed"
