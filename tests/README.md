# 測試框架使用指南

本專案包含完整的效能測試和安全測試框架，用於確保 API 的效能和安全性。

## 📁 目錄結構

```
tests/
├── performance/           # 效能測試框架
│   ├── __init__.py
│   ├── conftest.py       # pytest 配置
│   ├── test_api_performance.py    # API 效能測試
│   ├── test_load_testing.py       # 負載測試
│   ├── test_memory_profiling.py   # 記憶體分析
│   ├── utils/            # 效能測試工具
│   │   ├── performance_monitor.py
│   │   ├── load_tester.py
│   │   ├── memory_profiler.py
│   │   └── report_generator.py
│   └── reports/          # 測試報告輸出
├── security/             # 安全測試框架
│   ├── __init__.py
│   ├── conftest.py       # pytest 配置
│   ├── test_jwt_security.py       # JWT 安全測試
│   ├── test_sql_injection.py      # SQL 注入測試
│   ├── test_xss_protection.py     # XSS 防護測試
│   ├── test_rbac_permissions.py   # 權限控制測試
│   ├── test_data_leakage.py       # 資料洩漏測試
│   ├── utils/            # 安全測試工具
│   │   ├── security_scanner.py
│   │   ├── auth_tester.py
│   │   ├── injection_tester.py
│   │   └── vulnerability_tester.py
│   └── reports/          # 安全報告輸出
└── README.md             # 本文件
```

## 🚀 快速開始

### 1. 安裝依賴

```bash
# 安裝效能測試依賴
python run_performance_tests.py --install-deps

# 或手動安裝
pip install pytest-benchmark locust pytest-asyncio aiohttp httpx psutil memory-profiler

# 安裝安全測試依賴
pip install pytest-security bandit safety sqlparse pytest-html
```

### 2. 運行效能測試

```bash
# 運行所有效能測試
python run_performance_tests.py --test-suite performance

# 運行特定類型的效能測試
python run_performance_tests.py --test-suite performance --test-type api
python run_performance_tests.py --test-suite performance --test-type load
python run_performance_tests.py --test-suite performance --test-type memory

# 直接使用 pytest
pytest tests/performance/ -v -m performance
```

### 3. 運行安全測試

```bash
# 運行所有安全測試
python run_security_tests.py

# 運行特定類型的安全測試
pytest tests/security/test_jwt_security.py -v
pytest tests/security/test_sql_injection.py -v
pytest tests/security/test_xss_protection.py -v

# 運行代碼安全掃描
bandit -r src/ -f json -o tests/security/reports/bandit_report.json
safety check --json --output tests/security/reports/safety_report.json
```

## 📊 效能測試

### API 效能測試
- **目標**: API 回應時間 < 100ms
- **測試內容**: 
  - 健康檢查端點
  - 認證端點
  - 資料管理 API
  - 策略管理 API
  - 異步 API 效能

### 負載測試
- **測試場景**:
  - 輕負載: 5 個併發用戶
  - 中等負載: 25 個併發用戶
  - 重負載: 50 個併發用戶
  - 壓力測試: 100 個併發用戶

### 記憶體分析
- **檢測項目**:
  - 記憶體洩漏 (閾值: 10MB/hour)
  - 記憶體使用基線
  - 長時間運行穩定性
  - 垃圾回收效果

## 🔒 安全測試

### JWT 安全測試
- Token 驗證機制
- 過期 Token 處理
- 無效簽名檢測
- 權限提升防護
- 算法混淆攻擊防護

### SQL 注入測試
- 查詢參數注入
- POST 資料注入
- 盲 SQL 注入
- Union 型注入
- 錯誤型注入
- 時間型注入

### XSS 防護測試
- 反射型 XSS
- 儲存型 XSS
- DOM 型 XSS
- 過濾器繞過
- JSONP XSS

### 權限控制測試
- RBAC 權限驗證
- 資料隔離
- 資源所有權
- 跨租戶訪問防護

### 資料洩漏測試
- 密碼洩漏檢測
- API 金鑰洩漏
- 個人資訊保護
- 系統資訊洩漏
- JWT Token 洩漏

## 📈 報告生成

### 效能報告
- HTML 格式: `tests/performance/reports/performance_report_YYYYMMDD_HHMMSS.html`
- JSON 格式: `tests/performance/reports/performance_report_YYYYMMDD_HHMMSS.json`
- 基準測試: `tests/performance/reports/benchmark_results.json`

### 安全報告
- pytest 報告: `tests/security/reports/pytest_security_report.html`
- Bandit 掃描: `tests/security/reports/bandit_report.json`
- Safety 檢查: `tests/security/reports/safety_report.json`
- 安全摘要: `tests/security/reports/security_summary.html`

## 🎯 品質標準

### 效能標準
- API 回應時間: < 100ms (平均)
- P95 回應時間: < 150ms
- P99 回應時間: < 200ms
- 吞吐量: > 50 req/s
- 記憶體增長率: < 10MB/hour
- 併發支援: 50+ 用戶

### 安全標準
- 無高危安全漏洞
- 無 SQL 注入漏洞
- 無 XSS 漏洞
- 完整的認證授權
- 敏感資料保護
- 安全評分: ≥ 80/100

## 🔧 自定義配置

### 效能測試配置
```python
# tests/performance/__init__.py
PERFORMANCE_CONFIG = {
    "api_response_time_threshold": 100,  # ms
    "memory_leak_threshold": 10,  # MB per hour
    "concurrent_users_max": 100,
    "test_duration": 60,  # seconds
    "benchmark_rounds": 10
}
```

### 安全測試配置
```python
# tests/security/__init__.py
SECURITY_CONFIG = {
    "jwt_test_cases": [...],
    "sql_injection_payloads": [...],
    "xss_payloads": [...],
    "sensitive_data_patterns": [...]
}
```

## 🚨 故障排除

### 常見問題

1. **測試依賴缺失**
   ```bash
   pip install -r requirements-test.txt
   ```

2. **API 服務未啟動**
   ```bash
   # 確保 API 服務在 http://127.0.0.1:8000 運行
   python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8000
   ```

3. **權限問題**
   ```bash
   # 確保測試用戶有適當權限
   # 檢查 JWT 配置和用戶角色設定
   ```

4. **記憶體測試失敗**
   ```bash
   # 增加記憶體閾值或檢查記憶體洩漏
   # 確保測試環境有足夠記憶體
   ```

### 調試模式
```bash
# 詳細輸出
pytest tests/performance/ -v -s

# 只運行失敗的測試
pytest tests/security/ --lf

# 停在第一個失敗
pytest tests/ -x
```

## 📚 進階使用

### 自定義測試場景
```python
# 創建自定義負載測試場景
test_scenarios = [
    {"method": "GET", "url": "/api/v1/custom/", "headers": auth_headers},
    {"method": "POST", "url": "/api/v1/custom/", "json": test_data}
]

load_tester = LoadTester()
result = load_tester.run_load_test(test_scenarios, config, auth_headers)
```

### 自定義安全檢查
```python
# 添加自定義安全掃描
scanner = SecurityScanner()
scan_result = scanner.scan_api_security(client, endpoints, auth_headers)
```

## 🤝 貢獻指南

1. 添加新的測試用例時，請遵循現有的命名規範
2. 確保新測試有適當的文檔字符串
3. 更新相關的配置文件
4. 運行完整測試套件確保無回歸
5. 更新本 README 文件

## 📞 支援

如有問題或建議，請：
1. 檢查本文件的故障排除部分
2. 查看測試日誌和報告
3. 提交 Issue 或 Pull Request
