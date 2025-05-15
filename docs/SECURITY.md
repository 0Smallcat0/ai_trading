# 安全指南
# Security Guidelines

## 敏感資訊處理
## Sensitive Information Handling

本專案包含敏感資訊，如 API 金鑰、密碼等。請遵循以下指南以確保安全：
This project contains sensitive information such as API keys, passwords, etc. Please follow these guidelines to ensure security:

### 環境變數
### Environment Variables

1. 所有敏感資訊應存儲在環境變數中，而不是硬編碼在源代碼中
   All sensitive information should be stored in environment variables, not hardcoded in source code

2. 使用 `.env` 文件存儲環境變數，但不要將此文件提交到版本控制系統
   Use `.env` files to store environment variables, but do not commit these files to version control

3. 提供 `.env.example` 文件作為範例，但不包含實際的敏感資訊
   Provide `.env.example` files as examples, but do not include actual sensitive information

### API 金鑰
### API Keys

1. 不要在源代碼中硬編碼 API 金鑰
   Do not hardcode API keys in source code

2. 使用環境變數或安全的金鑰管理系統存儲 API 金鑰
   Use environment variables or secure key management systems to store API keys

3. 如果需要在配置文件中存儲 API 金鑰，請確保這些文件不會被提交到版本控制系統
   If you need to store API keys in configuration files, make sure these files are not committed to version control

### 私鑰
### Private Keys

1. 不要將私鑰提交到版本控制系統
   Do not commit private keys to version control

2. 使用 `.gitignore` 排除私鑰文件
   Use `.gitignore` to exclude private key files

3. 如果需要在本地存儲私鑰，請確保它們存儲在安全的位置，並且有適當的訪問控制
   If you need to store private keys locally, make sure they are stored in a secure location with appropriate access controls

## 設置環境
## Setting Up Environment

1. 複製 `.env.example` 文件為 `.env`，並填入您的實際設定值
   Copy `.env.example` file to `.env` and fill in your actual settings

2. 複製 `.envs/.env.template` 文件為 `.envs/.env.{環境}`，並填入您的實際設定值
   Copy `.envs/.env.template` file to `.envs/.env.{environment}` and fill in your actual settings

3. 運行 `scripts/powershell/setup_clean_env.ps1` 腳本以設置乾淨的環境
   Run `scripts/powershell/setup_clean_env.ps1` script to set up a clean environment

## 清理 Git 歷史
## Cleaning Git History

如果您不小心將敏感資訊提交到版本控制系統，請按照以下步驟清理 Git 歷史：
If you accidentally commit sensitive information to version control, follow these steps to clean Git history:

1. 運行 `scripts/powershell/clean_git_history.ps1` 腳本以清理 Git 歷史
   Run `scripts/powershell/clean_git_history.ps1` script to clean Git history

2. 使用 `--force` 推送到遠端
   Use `--force` to push to remote

## 安全最佳實踐
## Security Best Practices

1. 定期更換 API 金鑰和密碼
   Regularly rotate API keys and passwords

2. 使用最小權限原則，只授予必要的權限
   Use the principle of least privilege, only grant necessary permissions

3. 使用多因素認證
   Use multi-factor authentication

4. 定期審查代碼中的安全問題
   Regularly review code for security issues

5. 保持依賴項更新，以修復已知的安全漏洞
   Keep dependencies updated to fix known security vulnerabilities
