# 環境配置檔案說明

## 📁 目錄結構

```
config/environments/
├── .env.development    # 開發環境配置
├── .env.production     # 生產環境配置
├── .env.testing        # 測試環境配置
└── .env.example        # 配置範例檔案
```

## 🔧 使用方式

### 1. 選擇環境配置

根據您的運行環境，將對應的配置檔案複製到專案根目錄：

```bash
# 開發環境
cp config/environments/.env.development .env

# 生產環境
cp config/environments/.env.production .env

# 測試環境
cp config/environments/.env.testing .env
```

### 2. 配置說明

#### 開發環境 (.env.development)
- **用途**：本地開發和除錯
- **特點**：
  - DEBUG=true，詳細日誌輸出
  - 使用 SQLite 資料庫
  - 模擬外部 API
  - 寬鬆的風險管理設定
  - 啟用效能監控和記憶體分析

#### 生產環境 (.env.production)
- **用途**：正式部署環境
- **特點**：
  - DEBUG=false，最小日誌輸出
  - 使用 PostgreSQL 資料庫
  - 真實 API 金鑰
  - 嚴格的風險管理設定
  - 完整的監控和通知

#### 測試環境 (.env.testing)
- **用途**：自動化測試和 CI/CD
- **特點**：
  - 使用記憶體資料庫
  - 模擬所有外部服務
  - 極保守的風險設定
  - 關閉監控和通知

## 🔒 安全注意事項

1. **絕不提交真實配置到版本控制**
2. **生產環境配置包含敏感資訊**
3. **定期更新 API 金鑰和密碼**
4. **使用強密碼和加密金鑰**
5. **限制配置檔案存取權限**

## 🔄 配置更新

當需要更新配置時：

1. 修改對應的環境配置檔案
2. 重新複製到根目錄
3. 重啟應用程式

## 📝 自訂配置

如需自訂配置，請：

1. 複製 `.env.example` 作為範本
2. 根據需求修改配置值
3. 確保所有必要的環境變數都已設定
