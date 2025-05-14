# 資料庫模組 (Database Module)

此目錄包含與資料庫相關的模組，負責資料的儲存、驗證、備份和版本控制。

## 模組概述

### schema.py

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
- `create_data_shard()`: 創建資料分片

### parquet_utils.py

Parquet/Arrow 格式工具模組，用於壓縮歷史資料並提高查詢效能。

**主要函數**：
- `query_to_dataframe()`: 將 SQLAlchemy 查詢結果轉換為 Pandas DataFrame
- `save_to_parquet()`: 將 DataFrame 儲存為 Parquet 格式
- `read_from_parquet()`: 從 Parquet 檔案讀取資料
- `create_market_data_shard()`: 創建市場資料分片並儲存為 Parquet 格式
- `load_from_shard()`: 從資料分片讀取資料

### data_validation.py

資料驗證模組，用於確保資料的品質和完整性。

**主要類別**：
- `DataValidator`: 資料驗證器

**主要函數**：
- `validate_time_series_continuity()`: 驗證時間序列的連續性
- `check_missing_values()`: 檢查缺失值
- `detect_outliers()`: 檢測異常值
- `verify_data_integrity()`: 驗證資料完整性

### data_backup.py

資料備份與還原模組，確保資料的安全性和可恢復性。

**主要類別**：
- `DatabaseBackup`: 資料庫備份類

**主要函數**：
- `create_backup()`: 創建資料庫備份
- `restore_backup()`: 還原資料庫備份
- `schedule_backup()`: 排程備份

### data_versioning.py

資料版本控制模組，用於追蹤資料庫結構和資料的變更。

**主要類別**：
- `DataVersionManager`: 資料版本管理器

**主要函數**：
- `get_current_version()`: 獲取當前資料庫版本
- `update_version()`: 更新資料庫版本
- `compare_schema_with_models()`: 比較資料庫結構與模型定義
- `track_data_change()`: 追蹤資料變更
- `get_change_history()`: 獲取變更歷史

### data_pipeline.py

資料管道模組，整合資料擷取、驗證、儲存和備份等功能。

**主要類別**：
- `DataPipeline`: 資料管道類

**主要函數**：
- `ingest_data()`: 擷取資料
- `validate_data_quality()`: 驗證資料品質
- `backup_data()`: 備份資料
- `restore_data()`: 還原資料
- `update_schema_version()`: 更新資料庫結構版本
- `create_data_shard()`: 創建資料分片
- `load_from_shard()`: 從資料分片讀取資料

## 資料庫結構

系統使用 SQLAlchemy ORM 框架，支援多種資料庫後端（SQLite、PostgreSQL、InfluxDB 等）。

主要資料表包括：

1. **市場資料表**：
   - `market_tick`: 市場 Tick 資料表，記錄每筆交易的詳細資訊
   - `market_minute`: 市場分鐘資料表，記錄分鐘級別的 K 線資料
   - `market_daily`: 市場日線資料表，記錄日線級別的 K 線資料

2. **基本面資料表**：
   - `fundamental`: 基本面資料表，記錄公司的基本面資料

3. **技術指標資料表**：
   - `technical_indicator`: 技術指標資料表，記錄各種技術指標的計算結果

4. **新聞情緒資料表**：
   - `news_sentiment`: 新聞情緒資料表，記錄與特定股票相關的新聞情緒分析結果

5. **交易記錄表**：
   - `trade_record`: 交易記錄表，記錄系統執行的所有交易

6. **系統管理表**：
   - `system_log`: 系統日誌表，記錄系統運行過程中的各種日誌
   - `data_shard`: 資料分片表，記錄資料分片的相關資訊
   - `data_checksum`: 資料校驗表，記錄資料的校驗碼
   - `database_version`: 資料庫版本表，記錄資料庫結構的版本資訊

## 資料完整性機制

系統實現了多層次的資料完整性機制：

1. **校驗碼**：每筆資料都會計算校驗碼，用於驗證資料的完整性
2. **資料分片**：大型資料集會分片儲存，提高查詢效能並便於管理
3. **資料備份**：定期備份資料庫，確保資料的安全性
4. **版本控制**：追蹤資料庫結構和重要資料的變更歷史

## 資料品質檢查

系統提供多種資料品質檢查機制：

1. **時間序列連續性檢查**：檢查時間序列資料是否有缺失的時間點
2. **缺失值檢查**：檢查資料中的缺失值並提供報告
3. **異常值檢測**：使用統計方法檢測異常值
4. **資料類型檢查**：確保資料類型符合預期

## 使用範例

### 初始化資料管道

```python
from src.database.data_pipeline import DataPipeline

# 初始化資料管道
pipeline = DataPipeline()
```

### 擷取資料

```python
import pandas as pd
from datetime import date
from src.database.schema import MarketDaily, MarketType

# 創建資料
data = pd.DataFrame({
    "symbol": ["2330.TW"],
    "market_type": [MarketType.STOCK],
    "date": [date(2023, 1, 2)],
    "open": [500.0],
    "high": [510.0],
    "low": [495.0],
    "close": [505.0],
    "volume": [10000000.0],
    "data_source": ["yahoo"],
    "is_adjusted": [True],
})

# 擷取資料
success, record_ids = pipeline.ingest_data(data, MarketDaily)
```

### 驗證資料品質

```python
from datetime import date

# 驗證資料品質
result = pipeline.validate_data_quality(
    MarketDaily, "2330.TW", date(2023, 1, 1), date(2023, 1, 31)
)

# 檢查結果
print(f"整體品質分數: {result['overall_quality']['overall_score']}")
print(f"品質等級: {result['overall_quality']['quality_level']}")
```

### 備份資料庫

```python
# 創建備份
backup_path = pipeline.backup_data()
print(f"備份檔案: {backup_path}")

# 排程每日備份
pipeline.schedule_backup("daily")
```

### 創建資料分片

```python
from datetime import date
from src.database.schema import MarketDaily

# 創建資料分片
shard, file_path = pipeline.create_data_shard(
    MarketDaily, date(2023, 1, 1), date(2023, 1, 31), ["2330.TW"]
)

# 從分片讀取資料
df = pipeline.load_from_shard(shard.shard_id)
```

### 追蹤資料變更

```python
# 追蹤資料變更
pipeline.track_data_change(
    "market_daily",
    record_id,
    {
        "close": {
            "old": 505.0,
            "new": 506.0,
        },
    },
    "user123",
)

# 獲取變更歷史
history = pipeline.get_change_history("market_daily", record_id)
```
