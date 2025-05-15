# AI 股票自動交易系統 - 檔案結構說明

## 目錄結構

```
auto_trading_project/
├── .envs/                  # 環境變數目錄
│   ├── .env.dev            # 開發環境變數
│   ├── .env.test           # 測試環境變數
│   ├── .env.prod           # 生產環境變數
│   └── .env.template       # 環境變數模板
├── .github/                # GitHub 相關配置
├── data/                   # 資料目錄
│   ├── cache/              # 快取資料
│   ├── history/            # 歷史資料
│   ├── parquet/            # Parquet 格式資料
│   │   ├── market_daily/   # 日線資料
│   │   ├── market_minute/  # 分鐘資料
│   │   └── market_tick/    # Tick 資料
│   ├── market_data.db      # 市場資料資料庫
│   └── market_info.db      # 市場資訊資料庫
├── docs/                   # 文檔目錄
│   └── new_developer_guide.md # 新進人員指南
├── logs/                   # 日誌目錄
│   ├── event_monitor.log   # 事件監控日誌
│   ├── trading.log         # 交易日誌
│   └── shioaji.log         # 券商 API 日誌
├── mcp_crawler/            # MCP 爬蟲服務
│   ├── node_modules/       # Node.js 模組
│   ├── package.json        # Node.js 套件配置
│   └── server.cjs          # MCP 爬蟲服務器
├── notebooks/              # Jupyter 筆記本
│   └── data/               # 筆記本資料
├── results/                # 結果輸出目錄
│   └── factor_efficacy_report.csv  # 因子效能報告
├── src/                    # 源代碼目錄
│   ├── core/               # 核心功能模組
│   │   ├── backtest.py     # 回測引擎
│   │   ├── data_api.py     # 資料 API
│   │   ├── data_cleaning.py # 資料清理
│   │   ├── data_ingest.py  # 資料擷取
│   │   ├── event_monitor.py # 事件監控
│   │   ├── executor.py     # 執行器
│   │   ├── features.py     # 特徵工程
│   │   ├── indicators.py   # 技術指標計算
│   │   ├── logger.py       # 日誌記錄
│   │   ├── main.py         # 主程式
│   │   ├── mcp_connection_check.py # MCP 連接檢查
│   │   ├── mcp_data_ingest.py # MCP 資料擷取
│   │   ├── portfolio.py    # 投資組合管理
│   │   ├── research.py     # 研究工具
│   │   ├── risk_control.py # 風險控制
│   │   ├── run_crawler.py  # 爬蟲執行
│   │   ├── run_crawler_mcp.py # MCP 爬蟲執行
│   │   ├── run_twse_crawler.py # 台股爬蟲執行
│   │   ├── signal_gen.py   # 信號生成
│   │   └── start_mcp_trading.py # MCP 交易啟動
│   ├── data_sources/       # 資料來源模組
│   │   ├── market_data_adapter.py # 市場資料適配器
│   │   ├── mcp_crawler.py  # MCP 爬蟲
│   │   └── twse_crawler.py # 台股爬蟲
│   ├── database/           # 資料庫模組
│   │   ├── parquet_utils.py # Parquet 格式工具
│   │   └── schema.py       # 資料庫結構
│   ├── integration/        # 整合模組
│   │   └── brige.py        # 橋接模組
│   ├── models/             # 模型模組
│   │   ├── dataset.py      # 資料集處理
│   │   ├── dl_models.py    # 深度學習模型
│   │   ├── ml_models.py    # 機器學習模型
│   │   ├── model_factory.py # 模型工廠
│   │   ├── rule_based_models.py # 規則型模型
│   │   ├── strategy_research.py # 策略研究
│   │   └── training_pipeline.py # 訓練管道
│   ├── backtest/           # 回測模組
│   │   ├── backtrader_integration.py # Backtrader 整合
│   │   ├── performance_analysis.py # 績效分析
│   │   └── strategy_templates.py # 策略模板
│   ├── strategy/           # 策略模組
│   │   ├── mean_reversion.py # 均值回歸策略
│   │   ├── momentum.py     # 動量策略
│   │   └── strategy.py     # 策略基類
│   ├── utils/              # 工具模組
│   │   └── utils.py        # 通用工具
│   ├── __init__.py         # 套件初始化
│   └── config.py           # 配置文件
├── tests/                  # 測試目錄
│   ├── test_config.py      # 配置測試
│   ├── test_core_imports.py # 核心模組導入測試
│   ├── test_database_schema.py # 資料庫結構測試
│   └── test_strategy_imports.py # 策略模組導入測試
├── .coverage               # 測試覆蓋率報告
├── .flake8                 # Flake8 配置
├── .gitattributes          # Git 屬性配置
├── .gitignore              # Git 忽略配置
├── .pre-commit-config.yaml # Pre-commit 配置
├── auto_trading_project.code-workspace # VS Code 工作區配置
├── mypy.ini                # Mypy 配置
├── poetry.lock             # Poetry 鎖定文件
├── pyproject.toml          # Python 項目配置
├── README.md               # 項目說明
├── requirements.txt        # 依賴需求
├── STRUCTURE.md            # 檔案結構說明
├── ta_lib-0.6.3-cp310-cp310-win_amd64.whl # TA-Lib 輪子文件
└── Todo_list.md            # 待辦事項列表
```

## 主要模組說明

### 核心模組 (src/core)

- **backtest.py**: 回測引擎，用於模擬交易策略的歷史表現
  - 策略執行迴圈（包含資金/部位追蹤）
  - 資料模擬器與歷史資料讀取
  - 輸出策略績效指標（報酬率、夏普比率、最大回撤）
  - 支援多策略切換與比較
  - 異常情境模擬（崩盤、流動性不足）
  - 支援 Backtrader 框架整合
  - 混合型回測引擎（支援新聞情感因子注入）
  - 多策略回測比較與報告生成
- **data_api.py**: 資料 API，提供統一的資料存取介面
- **data_cleaning.py**: 資料清理，處理缺失值、異常值和標準化價格
  - 缺失值處理（插補、刪除等）
  - 異常值處理（Z-score、IQR、截斷等）
  - 價格標準化（調整收盤價邏輯）
  - 資料清理工作流
- **data_ingest.py**: 資料擷取，負責從各種來源獲取資料
  - 從多種來源獲取股票資料（Yahoo Finance、Alpha Vantage、FinMind、券商 API）
  - 支援多種資料類型（價格、成交量、財務報表、技術指標）
  - 實現 WebSocket 自動重連和背壓控制
  - 提供請求速率限制和自動故障轉移機制
  - 資料標準化和清洗
  - 支援定時更新和資料快取
  - 資料驗證與完整性檢查
- **event_monitor.py**: 事件監控，監控市場事件和異常情況
- **executor.py**: 執行器，負責執行交易訂單
- **features.py**: 特徵工程，處理和生成交易特徵
  - 計算技術指標（RSI、MACD、KD 等）
  - 計算基本面指標（ROE、ROA、EPS 等）
  - 特徵工程和資料轉換
  - 資料清理與預處理
  - 分散式處理支援（Dask、Ray）
  - 滾動視窗特徵生成
  - 特徵選擇與降維
  - 特徵重要性計算與視覺化
  - 特徵存儲與版本控制
- **indicators.py**: 技術指標計算，提供各種技術指標的計算函數
  - 移動平均線（SMA、EMA、WMA）
  - 動量指標（MACD、RSI、KD）
  - 波動指標（ATR、布林帶）
  - 成交量指標（OBV、CMF）
- **logger.py**: 日誌記錄，記錄交易活動和系統運行狀態
- **portfolio.py**: 投資組合管理，管理資產配置和持倉
  - 資產配置邏輯（等權重、風險平價等）
  - 多資產持倉動態模擬
  - 投資組合狀態與交易日誌記錄
  - 投資組合優化（最大夏普比率、最小方差等）
  - 投資組合績效評估與視覺化
  - 投資組合再平衡策略
  - 多策略投資組合整合
- **risk_control.py**: 風險控制，管理交易風險
  - 停損/停利規則
  - 資金配置比例
  - 風險指標計算（VaR、CVaR、波動率等）
  - 策略與投資組合層級風險控制
  - 風險預算與風險平價
  - 風險監控與預警
  - 動態風險調整
  - 極端情境測試
- **signal_gen.py**: 信號生成，生成交易信號
  - 基本面策略訊號
  - 動量策略訊號
  - 均值回歸策略訊號
  - 新聞情緒策略訊號
  - 突破、交叉、背離策略訊號
  - 多策略訊號合併
  - 訊號過濾與優化
  - 訊號評估與視覺化
  - 訊號時間序列分析

### 資料來源模組 (src/data_sources)

- **broker_adapter.py**: 券商 API 適配器，統一不同券商 API 的介面
- **data_collection_system.py**: 資料收集系統，整合所有資料收集器
  - 排程管理
  - 資料收集任務協調
  - 錯誤處理與通知
  - 資料驗證與儲存
- **data_collector.py**: 資料收集器基類，定義資料收集的通用介面
- **financial_statement_collector.py**: 財務報表收集器，收集公司財務資料
- **market_data_adapter.py**: 市場資料適配器，統一不同來源的市場資料格式
- **market_data_collector.py**: 市場資料收集器，收集股票價格資料
- **mcp_crawler.py**: MCP 爬蟲，使用 MCP 協議獲取網絡資料
- **news_sentiment_collector.py**: 新聞情緒收集器，收集與分析新聞情緒
- **realtime_quote_collector.py**: 即時報價收集器，收集即時市場報價
- **twse_crawler.py**: 台股爬蟲，獲取台灣證券交易所的資料
- **yahoo_adapter.py**: Yahoo Finance 適配器，獲取 Yahoo Finance 的資料

### 資料庫模組 (src/database)

- **data_backup.py**: 資料備份，提供資料庫備份與還原功能
- **data_pipeline.py**: 資料管道，整合資料擷取、驗證、儲存和備份等功能
- **data_validation.py**: 資料驗證，確保資料的品質和完整性
  - 時間序列連續性檢查
  - 缺失值檢查和報告
  - 異常值檢測和標記
  - 資料完整性驗證
- **data_versioning.py**: 資料版本控制，追蹤資料庫結構和資料的變更
- **parquet_utils.py**: Parquet/Arrow 格式工具，用於壓縮歷史資料並提高查詢效能
- **schema.py**: 資料庫結構，定義資料庫表結構和關係
  - 多時間粒度的市場資料表（Tick、分鐘、日線）
  - 基本面資料表
  - 技術指標資料表
  - 新聞情緒資料表
  - 資料分片與校驗機制

### 模型模組 (src/models)

- **dataset.py**: 資料集處理，用於準備模型訓練和測試資料
  - 時間序列資料分割（訓練/驗證/測試）
  - 特徵處理和標準化
  - 資料集載入和轉換
  - 防止前瞻偏差的時間序列處理
- **dl_models.py**: 深度學習模型，實現各種深度學習模型
  - LSTM 模型實現
  - GRU 模型實現
  - Transformer 模型實現
  - 模型訓練和評估功能
- **ml_models.py**: 機器學習模型，實現各種傳統機器學習模型
  - 隨機森林模型
  - XGBoost 模型
  - LightGBM 模型
  - SVM 模型
  - 模型訓練和評估功能
- **model_factory.py**: 模型工廠，用於創建和管理模型
  - 模型註冊和創建
  - 模型配置管理
  - 模型版本控制
- **rule_based_models.py**: 規則型模型，實現基於規則的交易模型
  - 移動平均線交叉策略
  - RSI 策略
  - 布林帶策略
  - 規則組合和優化
- **strategy_research.py**: 策略研究，用於研究和評估交易策略
  - 策略回測和評估
  - 策略參數優化
  - 策略比較和選擇
- **training_pipeline.py**: 訓練管道，用於模型訓練和評估
  - 資料準備和特徵工程
  - 模型訓練和調參
  - 模型評估和選擇
  - 模型部署和版本控制

### 回測模組 (src/backtest)

- **backtrader_integration.py**: Backtrader 整合，整合 Backtrader 框架
  - 自定義策略類
  - 資料饋送器
  - 績效分析器
  - 視覺化工具
- **performance_analysis.py**: 績效分析，分析交易策略的績效
  - 計算績效指標（夏普比率、索提諾比率、最大回撤等）
  - 生成績效報告
  - 視覺化績效結果
- **strategy_templates.py**: 策略模板，提供各種策略模板
  - 基本策略模板
  - 技術指標策略模板
  - 機器學習策略模板
  - 多策略組合模板

### 策略模組 (src/strategy)

- **mean_reversion.py**: 均值回歸策略，基於價格回歸均值的交易策略
- **momentum.py**: 動量策略，基於價格趨勢的交易策略
- **strategy.py**: 策略基類，定義策略的通用介面和功能

### 工具模組 (src/utils)

- **utils.py**: 通用工具，提供各種輔助功能

## 資料庫結構

系統使用 SQLAlchemy ORM 定義資料庫結構，主要資料表包括：

- **MarketTick**: 市場 Tick 資料表，記錄每筆交易的詳細資訊
- **MarketMinute**: 市場分鐘資料表，記錄分鐘級別的 K 線資料
- **MarketDaily**: 市場日線資料表，記錄日線級別的 K 線資料
- **Fundamental**: 基本面資料表，記錄公司的基本面資料
- **TechnicalIndicator**: 技術指標資料表，記錄各種技術指標的計算結果
- **NewsSentiment**: 新聞情緒資料表，記錄與特定股票相關的新聞情緒分析結果
- **TradeRecord**: 交易記錄表，記錄系統執行的所有交易
- **SystemLog**: 系統日誌表，記錄系統運行過程中的各種日誌
- **DataShard**: 資料分片表，記錄資料分片的相關資訊
- **DataChecksum**: 資料校驗表，記錄資料的校驗碼
- **DatabaseVersion**: 資料庫版本表，記錄資料庫結構的版本資訊

## 配置系統

系統使用多層次的配置管理：

- **config.py**: 主要配置文件，包含系統各方面的配置選項
- **.env 文件**: 環境變數文件，用於存儲敏感資訊和環境特定配置
- **命令行參數**: 用於臨時覆蓋配置選項

主要配置項包括：

- **目錄設定**: 資料目錄、日誌目錄、結果目錄等
- **資料庫設定**: 資料庫連接 URL、資料庫名稱等
- **API 設定**: API 金鑰、API 密鑰等
- **日誌設定**: 日誌級別、日誌格式等
- **交易設定**: 交易時間、最大持倉比例、停損閾值等
- **爬蟲設定**: 請求超時時間、重試次數等
- **監控設定**: 價格異常閾值、成交量異常閾值、檢查間隔等

## 日誌系統

所有日誌文件統一存放在 `logs/` 目錄下，包括：

- **event_monitor.log**: 事件監控日誌，記錄市場事件和異常情況
- **trading.log**: 交易日誌，記錄交易活動和系統運行狀態
- **shioaji.log**: 券商 API 日誌，記錄與券商 API 的通信

系統使用 Python 的 logging 模組進行日誌記錄，支援多種日誌級別和格式。

## 資料存儲

系統使用多種格式存儲資料：

- **SQLite 資料庫**: 存儲結構化資料，如市場資料、交易記錄等
- **Parquet 格式**: 存儲壓縮的歷史資料，提高查詢效能
- **CSV 文件**: 存儲分析結果和報告
- **JSON 文件**: 存儲配置和中間結果

資料文件存放在 `data/` 目錄下，包括：

- **market_data.db**: 市場資料資料庫，存儲市場資料
- **market_info.db**: 市場資訊資料庫，存儲市場資訊
- **parquet/**: Parquet 格式資料目錄，存儲壓縮的歷史資料
- **cache/**: 快取資料目錄，存儲臨時資料
- **history/**: 歷史資料目錄，存儲歷史資料

## 結果輸出

分析結果和報告存放在 `results/` 目錄下，包括：

- **performance_report.html**: 績效報告，包含回測結果和績效指標
- **factor_efficacy_report.csv**: 因子效能報告，評估各因子的預測能力
- **strategy_comparison.html**: 策略比較報告，比較不同策略的表現
