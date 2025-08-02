# 設置乾淨的環境
# Set up a clean environment

# 創建 .env 文件（如果不存在）
# Create .env file (if not exists)
if (-not (Test-Path .env)) {
    Write-Host "創建 .env 文件..."
    Write-Host "Creating .env file..."
    if (Test-Path .env.example) {
        Copy-Item .env.example .env
    } else {
        Copy-Item .envs/.env.template .env
    }
    Write-Host ".env 文件已創建，請編輯此文件並填入您的實際設定值"
    Write-Host ".env file created, please edit this file and fill in your actual settings"
}

# 創建環境特定的 .env 文件（如果不存在）
# Create environment-specific .env files (if not exist)
$envs = @("dev", "test", "prod")
foreach ($env in $envs) {
    $envFile = ".envs/.env.$env"
    if (-not (Test-Path $envFile)) {
        Write-Host "創建 $envFile 文件..."
        Write-Host "Creating $envFile file..."
        Copy-Item .envs/.env.template $envFile
        Write-Host "$envFile 文件已創建，請編輯此文件並填入您的實際設定值"
        Write-Host "$envFile file created, please edit this file and fill in your actual settings"
    }
}

# 創建 config/keys 目錄（如果不存在）
# Create config/keys directory (if not exists)
if (-not (Test-Path config/keys)) {
    Write-Host "創建 config/keys 目錄..."
    Write-Host "Creating config/keys directory..."
    New-Item -ItemType Directory -Path config/keys -Force | Out-Null
    Write-Host "config/keys 目錄已創建"
    Write-Host "config/keys directory created"
}

# 完成
# Done
Write-Host "環境設置完成"
Write-Host "Environment setup completed"
Write-Host "請確保您的 .env 文件和 .envs/.env.* 文件包含正確的設定值"
Write-Host "Please ensure your .env file and .envs/.env.* files contain correct settings"
