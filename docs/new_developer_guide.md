# AI 股票自動交易系統 - 新進人員指南

嗨，歡迎加入我們的 AI 股票自動交易系統開發團隊！這份文件將幫助你快速了解專案的結構、主要模組和功能，讓你能夠更順利地參與開發。

## 專案概述

這是一個基於 Python 的 AI 驅動股票交易決策代理人系統，旨在整合多維數據（基本面、技術面、新聞情緒），自動生成交易決策，並支援自動化排程與錯誤監控。

專案目前處於開發階段，已完成基礎架構設計、數據庫結構實現和部分核心功能模組的開發。

## 專案檔案總覽

### 配置文件

- **pyproject.toml**: 專案依賴管理，使用 Poetry 進行環境管理
- **.envs/.env.template**: 環境變數模板，用於創建不同環境的配置
- **src/config.py**: 主要配置文件，包含系統各方面的配置選項

### 核心模組 (src/core/)

- **backtest.py**: 回測引擎，用於模擬交易策略的歷史表現
- **data_api.py**: 資料 API，提供統一的資料存取介面
- **data_ingest.py**: 資料擷取，負責從各種來源獲取資料
  - 從多種來源獲取股票資料（Yahoo Finance、Alpha Vantage、FinMind、券商 API）
  - 支援多種資料類型（價格、成交量、財務報表、技術指標）
  - 實現 WebSocket 自動重連和背壓控制
  - 提供請求速率限制和自動故障轉移機制
  - 資料標準化和清洗
  - 支援定時更新和資料快取
- **event_monitor.py**: 事件監控，監控市場事件和異常情況
- **executor.py**: 執行器，負責執行交易訂單
- **features.py**: 特徵工程，處理和生成交易特徵
  - 技術指標計算（RSI、MACD、KD 等）
  - 基本面指標計算（ROE、ROA、EPS 等）
  - 特徵工程和資料轉換
  - 資料清理與預處理
  - 分散式處理支援（Dask、Ray）
  - 特徵選擇與降維
  - 特徵重要性計算與視覺化
- **logger.py**: 日誌記錄，記錄交易活動和系統運行狀態
- **mcp_data_ingest.py**: MCP 資料擷取，從 MCP 獲取資料
- **portfolio.py**: 投資組合管理，管理資產配置和持倉
  - 資產配置邏輯（等權重、風險平價、最大夏普比率、最小方差等）
  - 多資產持倉動態模擬
  - 投資組合狀態與交易日誌記錄
  - 投資組合優化與再平衡
  - 績效評估與視覺化
  - 多策略投資組合整合
- **risk_control.py**: 風險控制，管理交易風險
  - 停損/停利規則實現
  - 資金配置與部位規模控制
  - 風險指標計算（VaR、CVaR、波動率等）
  - 策略與投資組合層級風險控制
  - 風險預算與風險平價
  - 動態風險調整與極端情境測試
- **signal_gen.py**: 信號生成，生成交易信號
  - 基本面策略訊號生成
  - 動量策略訊號生成
  - 均值回歸策略訊號生成
  - 新聞情緒策略訊號生成
  - 多策略訊號合併與權重調整
  - 訊號評估與視覺化
  - 訊號過濾與優化

### 資料來源模組 (src/data_sources/)

- **market_data_adapter.py**: 市場資料適配器，統一不同來源的市場資料格式
- **mcp_crawler.py**: MCP 爬蟲，使用 MCP 協議獲取網絡資料
- **twse_crawler.py**: 台股爬蟲，獲取台灣證券交易所的資料

### 資料庫模組 (src/database/)

- **schema.py**: 資料庫結構，定義資料庫表結構和關係
- **parquet_utils.py**: Parquet/Arrow 格式工具，用於壓縮歷史資料

### 策略模組 (src/strategy/)

- **mean_reversion.py**: 均值回歸策略，基於價格回歸均值的交易策略
- **momentum.py**: 動量策略，基於價格趨勢的交易策略
- **strategy.py**: 策略基類，定義策略的通用介面和功能

### 工具模組 (src/utils/)

- **utils.py**: 通用工具，提供各種輔助功能

### 測試模組 (tests/)

- **test_config.py**: 配置測試
- **test_core_imports.py**: 核心模組導入測試
- **test_database_schema.py**: 資料庫結構測試
- **test_strategy_imports.py**: 策略模組導入測試

## 主要模組詳細說明

### src/config.py

這是系統的主要配置文件，包含所有重要的設定參數。

**主要功能**：
- 載入環境變數
- 設定目錄路徑
- 配置資料庫連接
- 設定 API 參數
- 配置交易參數
- 設定監控閾值

**重要變數**：
- `ROOT_DIR`: 專案根目錄
- `DATA_DIR`: 資料目錄
- `LOGS_DIR`: 日誌目錄
- `DB_URL`: 資料庫連接 URL
- `API_KEY` / `API_SECRET`: API 金鑰
- `TRADING_HOURS_START` / `TRADING_HOURS_END`: 交易時間
- `MAX_POSITION_SIZE`: 最大持倉比例
- `STOP_LOSS_THRESHOLD`: 停損閾值

### src/core/backtest.py

回測引擎，用於模擬交易策略的歷史表現。

**主要類別**：
- `Backtest`: 回測類，用於回測交易策略
- `MarketDataSimulator`: 市場數據模擬器，用於生成模擬數據和異常情境
- `SignalStrategy`: Backtrader 策略類，用於實現基於訊號的交易策略
- `HybridBacktest`: 混合型回測引擎，支援新聞情感因子注入
- `MultiStrategyBacktest`: 多策略回測類，用於比較多個策略的表現

**主要函數**：
- `run(signals, weights=None)`: 執行回測
  - 參數：
    - `signals`: 交易信號，DataFrame 格式
    - `weights`: 投資組合權重，可選
  - 回傳：回測結果字典
- `plot_results()`: 繪製回測結果圖表
  - 回傳：matplotlib 圖表
- `get_performance_metrics()`: 獲取績效指標
  - 回傳：績效指標字典

**輔助函數**：
- `backtest_strategy()`: 便捷的回測函數
- `run_backtest()`: 執行回測並返回詳細結果
- `run_with_backtrader()`: 使用 Backtrader 框架執行回測
- `calculate_sharpe()`: 計算夏普比率
- `calculate_max_drawdown()`: 計算最大回撤

**特色功能**：
- 支援多種市場情境模擬（崩盤、流動性不足、高波動性）
- 支援多策略比較和報告生成
- 整合 Backtrader 框架提供更豐富的回測功能
- 支援新聞情感因子注入的混合型回測

### src/core/signal_gen.py

信號生成模組，負責根據不同的策略生成交易信號。

**主要類別**：
- `SignalGenerator`: 信號產生器類別
- `SignalEvaluator`: 信號評估器類別，用於評估信號的質量
- `SignalOptimizer`: 信號優化器類別，用於優化信號參數
- `SignalFilter`: 信號過濾器類別，用於過濾低質量信號

**主要方法**：
- `generate_basic()`: 生成基本面策略信號
  - 參數：
    - `pe_threshold`: 本益比閾值
    - `pb_threshold`: 股價淨值比閾值
    - `dividend_yield_threshold`: 殖利率閾值
  - 回傳：信號 DataFrame
- `generate_momentum()`: 生成動量策略信號
  - 參數：
    - `short_window`: 短期窗口大小
    - `medium_window`: 中期窗口大小
    - `long_window`: 長期窗口大小
  - 回傳：信號 DataFrame
- `generate_reversion()`: 生成均值回歸策略信號
  - 參數：
    - `window`: 移動平均窗口大小
    - `std_dev`: 標準差閾值
  - 回傳：信號 DataFrame
- `generate_sentiment()`: 生成新聞情緒策略信號
  - 參數：
    - `sentiment_threshold`: 情緒閾值
  - 回傳：信號 DataFrame
- `combine_signals()`: 合併多策略信號
  - 參數：
    - `weights`: 各策略權重字典
  - 回傳：合併後的信號 DataFrame
- `evaluate_signals()`: 評估信號質量
  - 參數：
    - `signals`: 信號 DataFrame
    - `price_data`: 價格資料
    - `metrics`: 評估指標列表
  - 回傳：評估結果字典
- `optimize_parameters()`: 優化策略參數
  - 參數：
    - `strategy`: 策略名稱
    - `param_grid`: 參數網格
    - `price_data`: 價格資料
    - `metric`: 優化指標
  - 回傳：最佳參數字典

**特色功能**：
- 支援多種策略類型（基本面、動量、均值回歸、新聞情緒）
- 信號質量評估和優化
- 多策略信號合併與權重調整
- 信號視覺化和統計分析
- 時間序列分析和模式識別

### src/database/schema.py

資料庫結構定義，包含所有資料表的結構和關係。

**主要類別**：
- `MarketDataMixin`: 市場資料基礎欄位 Mixin
- `MarketTick`: 市場 Tick 資料表
- `MarketMinute`: 市場分鐘資料表
- `MarketDaily`: 市場日線資料表
- `Fundamental`: 基本面資料表
- `TechnicalIndicator`: 技術指標資料表
- `NewsSentiment`: 新聞情緒資料表
- `TradeRecord`: 交易記錄表
- `SystemLog`: 系統日誌表
- `DataShard`: 資料分片表
- `DataChecksum`: 資料校驗表
- `DatabaseVersion`: 資料庫版本表

**主要函數**：
- `init_db(engine)`: 初始化資料庫
  - 參數：
    - `engine`: SQLAlchemy 引擎
- `create_data_shard()`: 創建資料分片
  - 參數：
    - `session`: SQLAlchemy 會話
    - `table_name`: 資料表名稱
    - `start_date`: 開始日期
    - `end_date`: 結束日期
    - `shard_key`: 分片鍵
  - 回傳：創建的資料分片記錄

### src/database/parquet_utils.py

Parquet/Arrow 格式工具模組，用於壓縮歷史資料並提高查詢效能。

**主要函數**：
- `query_to_dataframe()`: 將 SQLAlchemy 查詢結果轉換為 Pandas DataFrame
  - 參數：
    - `session`: SQLAlchemy 會話
    - `query`: SQLAlchemy 查詢物件
  - 回傳：查詢結果的 DataFrame
- `save_to_parquet()`: 將 DataFrame 儲存為 Parquet 格式
  - 參數：
    - `df`: 要儲存的 DataFrame
    - `file_path`: 檔案路徑
    - `compression`: 壓縮方式
    - `partition_cols`: 分區欄位
  - 回傳：儲存的檔案路徑
- `read_from_parquet()`: 從 Parquet 檔案讀取資料
  - 參數：
    - `file_path`: 檔案路徑
    - `columns`: 要讀取的欄位
    - `filters`: 過濾條件
  - 回傳：讀取的 DataFrame
- `create_market_data_shard()`: 創建市場資料分片並儲存為 Parquet 格式
  - 參數：
    - `session`: SQLAlchemy 會話
    - `table_class`: 資料表類別
    - `start_date`: 開始日期
    - `end_date`: 結束日期
    - `symbols`: 股票代碼列表
    - `compression`: 壓縮方式
  - 回傳：資料分片記錄和檔案路徑

## 特殊說明

### 環境變數

專案使用 `.envs` 目錄下的環境變數文件進行配置，包括：
- `.env.dev`: 開發環境
- `.env.test`: 測試環境
- `.env.prod`: 生產環境

你需要根據 `.env.template` 創建對應的環境變數文件，並設置以下重要變數：
- `DB_URL`: 資料庫連接 URL
- `API_KEY` / `API_SECRET`: API 金鑰
- `LOG_LEVEL`: 日誌級別

### API 金鑰

系統使用多個外部 API，需要設置以下 API 金鑰：
- Alpha Vantage API: 用於獲取股票資料
- Yahoo Finance API: 用於獲取股票資料
- FinMind API: 用於獲取台灣股市資料

這些金鑰應該設置在環境變數文件中，不要直接寫在代碼中。

### 資料目錄

系統使用以下目錄存放資料：
- `data/`: 存放所有資料文件
  - `cache/`: 快取資料
  - `history/`: 歷史資料
  - `parquet/`: Parquet 格式資料
- `logs/`: 存放日誌文件
- `results/`: 存放分析結果

這些目錄會在系統啟動時自動創建。

## 開始使用

1. 克隆專案並進入專案目錄
2. 安裝 Poetry: `pip install poetry`
3. 安裝依賴: `poetry install`
4. 創建環境變數文件: 複製 `.envs/.env.template` 到 `.envs/.env.dev` 並填寫必要的配置
5. 初始化資料庫: `poetry run python -m src.database.schema`
6. 運行測試: `poetry run pytest`

## 開發流程

1. 從 `main` 分支創建新的功能分支: `git checkout -b feature/your-feature-name`
2. 開發並測試你的功能
3. 提交代碼: `git commit -m "Add your feature"`
4. 推送到遠程: `git push origin feature/your-feature-name`
5. 創建 Pull Request

## 常見問題

### 如何添加新的資料來源？

1. 在 `src/data_sources/` 目錄下創建新的資料來源模組
2. 實現資料擷取和轉換功能
3. 在 `src/core/data_ingest.py` 中添加對新資料來源的支持

### 如何添加新的交易策略？

1. 在 `src/strategy/` 目錄下創建新的策略模組
2. 繼承 `strategy.py` 中的基類
3. 實現策略邏輯
4. 在 `src/core/signal_gen.py` 中添加對新策略的支持

### 如何運行回測？

使用 `src/core/backtest.py` 中的 `run_backtest()` 函數：

```python
from src.core.backtest import run_backtest
from src.core.signal_gen import SignalGenerator

# 創建信號
signal_gen = SignalGenerator(price_data=price_df)
signals = signal_gen.generate_momentum()

# 運行回測
results = run_backtest(signals, start_date="2022-01-01", end_date="2022-12-31")

# 查看結果
print(f"年化收益率: {results['annual_return']:.2%}")
print(f"夏普比率: {results['sharpe']:.2f}")
print(f"最大回撤: {results['max_drawdown']:.2%}")
```

## 聯繫方式

如果你有任何問題，請隨時聯繫團隊成員或提交 Issue。

祝你開發愉快！
