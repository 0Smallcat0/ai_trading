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
│   │   ├── data_ingest.py  # 資料擷取
│   │   ├── event_monitor.py # 事件監控
│   │   ├── executor.py     # 執行器
│   │   ├── features.py     # 特徵工程
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
- **data_api.py**: 資料 API，提供統一的資料存取介面
- **data_ingest.py**: 資料擷取，負責從各種來源獲取資料
- **event_monitor.py**: 事件監控，監控市場事件和異常情況
- **executor.py**: 執行器，負責執行交易訂單
- **features.py**: 特徵工程，處理和生成交易特徵
- **logger.py**: 日誌記錄，記錄交易活動和系統運行狀態
- **portfolio.py**: 投資組合管理，管理資產配置和持倉
- **risk_control.py**: 風險控制，管理交易風險
- **signal_gen.py**: 信號生成，生成交易信號

### 資料來源模組 (src/data_sources)

- **market_data_adapter.py**: 市場資料適配器，統一不同來源的市場資料格式
- **mcp_crawler.py**: MCP 爬蟲，使用 MCP 協議獲取網絡資料
- **twse_crawler.py**: 台股爬蟲，獲取台灣證券交易所的資料

### 資料庫模組 (src/database)

- **schema.py**: 資料庫結構，定義資料庫表結構和關係
- **parquet_utils.py**: Parquet/Arrow 格式工具，用於壓縮歷史資料並提高查詢效能

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
