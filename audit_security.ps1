# 安全審計腳本
# Security Audit Script

# 設置顏色
# Set colors
$RED = [ConsoleColor]::Red
$GREEN = [ConsoleColor]::Green
$YELLOW = [ConsoleColor]::Yellow
$RESET = [ConsoleColor]::White

# 顯示標題
# Display title
Write-Host "========================================" -ForegroundColor $YELLOW
Write-Host "        安全審計腳本 / Security Audit Script        " -ForegroundColor $YELLOW
Write-Host "========================================" -ForegroundColor $YELLOW
Write-Host ""

# 檢查是否安裝了必要的工具
# Check if necessary tools are installed
Write-Host "檢查必要的工具..." -ForegroundColor $YELLOW
Write-Host "Checking necessary tools..." -ForegroundColor $YELLOW

$tools = @{
    "git" = "Git"
    "python" = "Python"
}

foreach ($tool in $tools.Keys) {
    try {
        $null = & $tool --version
        Write-Host "✓ $($tools[$tool]) 已安裝" -ForegroundColor $GREEN
        Write-Host "✓ $($tools[$tool]) is installed" -ForegroundColor $GREEN
    } catch {
        Write-Host "✗ $($tools[$tool]) 未安裝" -ForegroundColor $RED
        Write-Host "✗ $($tools[$tool]) is not installed" -ForegroundColor $RED
        Write-Host "請安裝 $($tools[$tool]) 後再運行此腳本" -ForegroundColor $RED
        Write-Host "Please install $($tools[$tool]) before running this script" -ForegroundColor $RED
        exit 1
    }
}

# 檢查 .gitignore 文件
# Check .gitignore file
Write-Host ""
Write-Host "檢查 .gitignore 文件..." -ForegroundColor $YELLOW
Write-Host "Checking .gitignore file..." -ForegroundColor $YELLOW

$gitignore = Get-Content .gitignore -ErrorAction SilentlyContinue
$requiredPatterns = @(
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.crt",
    "config/keys/",
    "api_keys.json"
)

$missingPatterns = @()
foreach ($pattern in $requiredPatterns) {
    if ($gitignore -notcontains $pattern) {
        $missingPatterns += $pattern
    }
}

if ($missingPatterns.Count -eq 0) {
    Write-Host "✓ .gitignore 文件包含所有必要的模式" -ForegroundColor $GREEN
    Write-Host "✓ .gitignore file contains all necessary patterns" -ForegroundColor $GREEN
} else {
    Write-Host "✗ .gitignore 文件缺少以下模式:" -ForegroundColor $RED
    Write-Host "✗ .gitignore file is missing the following patterns:" -ForegroundColor $RED
    foreach ($pattern in $missingPatterns) {
        Write-Host "  - $pattern" -ForegroundColor $RED
    }
    Write-Host "請將這些模式添加到 .gitignore 文件中" -ForegroundColor $RED
    Write-Host "Please add these patterns to the .gitignore file" -ForegroundColor $RED
}

# 檢查敏感文件
# Check sensitive files
Write-Host ""
Write-Host "檢查敏感文件..." -ForegroundColor $YELLOW
Write-Host "Checking sensitive files..." -ForegroundColor $YELLOW

$sensitiveFiles = @(
    ".env",
    ".env.dev",
    ".env.test",
    ".env.prod",
    "config/keys/audit_private.pem",
    "config/api_keys.json"
)

$trackedFiles = git ls-files

$trackedSensitiveFiles = @()
foreach ($file in $sensitiveFiles) {
    if ($trackedFiles -contains $file) {
        $trackedSensitiveFiles += $file
    }
}

if ($trackedSensitiveFiles.Count -eq 0) {
    Write-Host "✓ 沒有敏感文件被跟踪" -ForegroundColor $GREEN
    Write-Host "✓ No sensitive files are being tracked" -ForegroundColor $GREEN
} else {
    Write-Host "✗ 以下敏感文件被跟踪:" -ForegroundColor $RED
    Write-Host "✗ The following sensitive files are being tracked:" -ForegroundColor $RED
    foreach ($file in $trackedSensitiveFiles) {
        Write-Host "  - $file" -ForegroundColor $RED
    }
    Write-Host "請從版本控制中移除這些文件" -ForegroundColor $RED
    Write-Host "Please remove these files from version control" -ForegroundColor $RED
}

# 檢查硬編碼的敏感信息
# Check hardcoded sensitive information
Write-Host ""
Write-Host "檢查硬編碼的敏感信息..." -ForegroundColor $YELLOW
Write-Host "Checking hardcoded sensitive information..." -ForegroundColor $YELLOW

# 使用簡單的字符串搜索
# Use simple string search
$keywords = @(
    "API_KEY",
    "API_SECRET",
    "PASSWORD",
    "SECRET",
    "TOKEN",
    "-----BEGIN PRIVATE KEY-----",
    "-----BEGIN RSA PRIVATE KEY-----",
    "ghp_",
    "sk_live_",
    "sk_test_",
    "AIza",
    "AKIA"
)

$suspiciousFiles = @()
foreach ($keyword in $keywords) {
    $files = git grep -l $keyword -- "*.py" "*.js" "*.json" "*.yaml" "*.yml" "*.md" "*.txt" "*.html" "*.css" "*.sh" "*.ps1" 2>$null
    foreach ($file in $files) {
        if ($file -notmatch "\.env\.example$" -and $file -notmatch "\.env\.template$" -and $file -notmatch "SECURITY\.md$" -and $file -notmatch "安全指南\.md$" -and $file -notmatch "安全密鑰管理指南\.md$" -and $file -notmatch "audit_security\.ps1$") {
            $suspiciousFiles += $file
        }
    }
}

$suspiciousFiles = $suspiciousFiles | Sort-Object -Unique

if ($suspiciousFiles.Count -eq 0) {
    Write-Host "✓ 沒有發現硬編碼的敏感信息" -ForegroundColor $GREEN
    Write-Host "✓ No hardcoded sensitive information found" -ForegroundColor $GREEN
} else {
    Write-Host "✗ 以下文件可能包含硬編碼的敏感信息:" -ForegroundColor $RED
    Write-Host "✗ The following files may contain hardcoded sensitive information:" -ForegroundColor $RED
    foreach ($file in $suspiciousFiles) {
        Write-Host "  - $file" -ForegroundColor $RED
    }
    Write-Host "請檢查這些文件並移除硬編碼的敏感信息" -ForegroundColor $RED
    Write-Host "Please check these files and remove hardcoded sensitive information" -ForegroundColor $RED
}

# 檢查 .env 文件
# Check .env files
Write-Host ""
Write-Host "檢查 .env 文件..." -ForegroundColor $YELLOW
Write-Host "Checking .env files..." -ForegroundColor $YELLOW

$envFiles = @(
    ".env",
    ".envs/.env.dev",
    ".envs/.env.test",
    ".envs/.env.prod"
)

$envFilesWithKeys = @()
foreach ($file in $envFiles) {
    if (Test-Path $file) {
        $content = Get-Content $file -ErrorAction SilentlyContinue
        $hasKeys = $false
        foreach ($line in $content) {
            if ($line -match "API_KEY\s*=\s*.+$" -and $line -notmatch "API_KEY\s*=$" -and $line -notmatch "API_KEY\s*=\s*your_api_key_here$") {
                $hasKeys = $true
                break
            }
            if ($line -match "API_SECRET\s*=\s*.+$" -and $line -notmatch "API_SECRET\s*=$" -and $line -notmatch "API_SECRET\s*=\s*your_api_secret_here$") {
                $hasKeys = $true
                break
            }
        }
        if ($hasKeys) {
            $envFilesWithKeys += $file
        }
    }
}

if ($envFilesWithKeys.Count -eq 0) {
    Write-Host "✓ .env 文件不包含實際的 API 金鑰" -ForegroundColor $GREEN
    Write-Host "✓ .env files do not contain actual API keys" -ForegroundColor $GREEN
} else {
    Write-Host "✗ 以下 .env 文件包含實際的 API 金鑰:" -ForegroundColor $RED
    Write-Host "✗ The following .env files contain actual API keys:" -ForegroundColor $RED
    foreach ($file in $envFilesWithKeys) {
        Write-Host "  - $file" -ForegroundColor $RED
    }
    Write-Host "請從這些文件中移除實際的 API 金鑰" -ForegroundColor $RED
    Write-Host "Please remove actual API keys from these files" -ForegroundColor $RED
}

# 完成
# Done
Write-Host ""
Write-Host "安全審計完成" -ForegroundColor $YELLOW
Write-Host "Security audit completed" -ForegroundColor $YELLOW
Write-Host ""
