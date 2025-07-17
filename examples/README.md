# AI 股票自動交易系統 - 示例代碼

**版本**: v2.0  
**更新日期**: 2025-01-15  
**適用範圍**: AI 股票自動交易系統

## 📋 概述

本目錄包含 AI 股票自動交易系統的各種示例代碼，展示系統的核心功能和使用方法。這些示例整合了 ai_quant_trade-0.0.1 項目中的有價值功能，並按照當前項目的品質標準進行了重構。

## 📁 目錄結構

```
examples/
├── README.md                           # 本文件
├── nlp/                               # 自然語言處理示例
│   └── financial_report_generation_demo.py
├── factor_mining/                     # 因子挖掘示例
│   └── tsfresh_factor_extraction_demo.py
├── backtest/                          # 回測系統示例
│   ├── demo_backtest_enhanced.py
│   └── simple_backfill_demo.py
├── data_processing/                   # 數據處理示例
│   ├── data_cleaning_example.py
│   └── feature_engineering_example.py
├── indicators/                       # 技術指標示例
│   ├── indicators_example.py
│   └── enhanced_indicators_demo.py
└── system/                           # 系統功能示例
    ├── logging_features_demo.py
    ├── backpressure_and_failover_demo.py
    └── demo_responsive.py
```

## 🆕 新增示例（來自 ai_quant_trade-0.0.1 整合）

### 1. 金融報告生成示例
**文件**: `nlp/financial_report_generation_demo.py`

基於大語言模型和網絡搜索的智能金融分析報告生成系統。

**功能特色**:
- 自動網絡搜索相關信息
- 基於 LLM 的智能分析
- 結構化報告生成
- 批量主題處理

**使用方法**:
```bash
# 設置 API 密鑰
export OPENAI_API_KEY="your-openai-api-key"
export TAVILY_API_KEY="your-tavily-api-key"

# 運行示例
python examples/nlp/financial_report_generation_demo.py
```

**示例功能**:
- 單個報告生成
- 批量報告生成
- 自定義主題分析
- 錯誤處理演示

### 2. tsfresh 自動因子挖掘示例
**文件**: `factor_mining/tsfresh_factor_extraction_demo.py`

展示如何使用 tsfresh 從股票價格數據中自動提取大量特徵因子。

**功能特色**:
- 自動從時間序列提取 5000+ 特徵
- 統計檢驗特徵選擇
- 並行處理和性能優化
- 因子評估和分析

**使用方法**:
```bash
# 安裝依賴
pip install tsfresh pandas numpy scikit-learn

# 運行示例
python examples/factor_mining/tsfresh_factor_extraction_demo.py
```

**示例功能**:
- 基礎因子提取
- 因子選擇和篩選
- 因子評估和排序
- 性能優化比較

## 🔧 現有示例說明

### 回測系統示例
- **demo_backtest_enhanced.py**: 增強版回測系統演示
- **simple_backfill_demo.py**: 簡單的歷史數據回填示例

### 數據處理示例
- **data_cleaning_example.py**: 數據清洗和預處理
- **feature_engineering_example.py**: 特徵工程和因子構建

### 技術指標示例
- **indicators_example.py**: 基礎技術指標計算
- **enhanced_indicators_demo.py**: 增強版技術指標演示

### 系統功能示例
- **logging_features_demo.py**: 日誌功能演示
- **backpressure_and_failover_demo.py**: 背壓和故障轉移
- **demo_responsive.py**: 響應式系統演示

## 🚀 快速開始

### 環境準備
```bash
# 1. 安裝基礎依賴
pip install -r requirements.txt

# 2. 安裝可選依賴（根據需要）
pip install tsfresh                    # 因子挖掘
pip install langchain langchain-openai # NLP 功能
pip install plotly                     # 可視化

# 3. 設置環境變數
export OPENAI_API_KEY="your-key"      # OpenAI API
export TAVILY_API_KEY="your-key"      # Tavily 搜索 API
```

### 運行示例
```bash
# 運行特定示例
python examples/nlp/financial_report_generation_demo.py

# 運行所有示例（如果有測試腳本）
python -m pytest examples/ -v
```

## 📊 示例分類

### 按功能分類
| 功能類別 | 示例數量 | 主要文件 |
|---------|---------|---------|
| **NLP 處理** | 1 | financial_report_generation_demo.py |
| **因子挖掘** | 1 | tsfresh_factor_extraction_demo.py |
| **回測系統** | 2 | demo_backtest_enhanced.py |
| **數據處理** | 2 | data_cleaning_example.py |
| **技術指標** | 2 | indicators_example.py |
| **系統功能** | 3 | logging_features_demo.py |

### 按難度分類
- **初級** (🟢): 基礎功能演示，適合新手
- **中級** (🟡): 複合功能應用，需要一定基礎
- **高級** (🔴): 高級功能整合，需要深入理解

| 示例文件 | 難度 | 說明 |
|---------|------|------|
| simple_backfill_demo.py | 🟢 | 簡單數據回填 |
| indicators_example.py | 🟢 | 基礎技術指標 |
| data_cleaning_example.py | 🟡 | 數據清洗流程 |
| financial_report_generation_demo.py | 🟡 | LLM 報告生成 |
| tsfresh_factor_extraction_demo.py | 🔴 | 自動因子挖掘 |
| demo_backtest_enhanced.py | 🔴 | 增強版回測 |

## 💡 使用建議

### 學習路徑
1. **新手入門**: 從基礎示例開始，了解系統架構
2. **功能探索**: 運行各類功能示例，熟悉 API 使用
3. **深入應用**: 結合實際需求，修改和擴展示例
4. **系統整合**: 將多個功能組合，構建完整策略

### 最佳實踐
1. **環境隔離**: 使用虛擬環境運行示例
2. **配置管理**: 使用環境變數管理敏感信息
3. **錯誤處理**: 參考示例中的錯誤處理模式
4. **性能優化**: 關注示例中的性能優化技巧

### 常見問題
1. **依賴問題**: 確保安裝所有必要依賴
2. **API 密鑰**: 正確設置相關 API 密鑰
3. **數據格式**: 注意數據格式要求和轉換
4. **內存使用**: 大數據處理時注意內存管理

## 🔄 更新記錄

### v2.0 (2025-01-15)
- ✅ 整合 ai_quant_trade-0.0.1 有價值功能
- ✅ 新增 NLP 報告生成示例
- ✅ 新增 tsfresh 因子挖掘示例
- ✅ 完善示例文檔和使用指南
- ✅ 統一代碼品質標準

### v1.x (歷史版本)
- ✅ 基礎回測系統示例
- ✅ 數據處理和技術指標示例
- ✅ 系統功能演示

## 📞 支援與反饋

### 獲取幫助
- **文檔**: 查看 `docs/` 目錄中的詳細文檔
- **API 參考**: 參考各模組的 docstring 說明
- **常見問題**: 查看 `docs/Q&A常見問題.md`

### 貢獻示例
歡迎貢獻新的示例代碼！請遵循以下規範：
1. **代碼品質**: Pylint 評分 ≥8.5/10
2. **文檔完整**: 完整的 Google Style Docstring
3. **測試覆蓋**: 提供基本的測試用例
4. **使用說明**: 在示例中包含詳細的使用說明

---

**免責聲明**: 本示例代碼僅供學習和研究使用，實際投資請謹慎評估風險。
