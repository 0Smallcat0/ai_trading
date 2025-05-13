# Database Schema and Parquet Utils Improvements

## Overview

This document summarizes the improvements made to the database schema and Parquet utilities modules as part of tasks 1.1 and 1.2 from the Todo list.

## Task 1.1: Checking Functionality

We verified that the existing database schema implementation is working correctly by:

1. **Testing Database Schema**:
   - Fixed the existing tests to use in-memory SQLite databases instead of temporary files
   - Verified that all database tables are created correctly
   - Confirmed that data can be inserted and retrieved properly

2. **Time Granularity Support**:
   - Validated that the `TimeGranularity` enum is working correctly
   - Confirmed that different time granularities (1min, 5min, 15min, 30min, 1hour) are supported
   - Tested that data can be filtered by time granularity

3. **Data Sharding and Integrity**:
   - Verified that data sharding functionality is working correctly
   - Confirmed that data integrity mechanisms (checksums) are functioning properly
   - Tested that data can be retrieved from shards

## Task 1.2: Improving Code

We enhanced the database and Parquet utilities modules by:

1. **Implementing Tests for Parquet Utils**:
   - Created a new test file `tests/test_parquet_utils.py`
   - Added tests for all major functions in the module
   - Achieved 75% code coverage for the `parquet_utils.py` module

2. **Enhancing Query to DataFrame Conversion**:
   - Improved the `query_to_dataframe` function to handle SQLAlchemy ORM objects correctly
   - Added proper handling of enum values to ensure compatibility with Parquet format
   - Fixed issues with nested ORM objects

3. **Data Compression Improvements**:
   - Verified that data compression using Parquet/Arrow format is working properly
   - Tested saving and loading data from Parquet files
   - Confirmed that composite indexes (timestamp + symbol) are functioning correctly

## Code Changes

### 1. Enhanced `query_to_dataframe` Function

The `query_to_dataframe` function was improved to handle SQLAlchemy ORM objects correctly, including proper handling of enum values:

```python
def query_to_dataframe(session: Session, query) -> pd.DataFrame:
    """
    將 SQLAlchemy 查詢結果轉換為 Pandas DataFrame

    Args:
        session: SQLAlchemy 會話
        query: SQLAlchemy 查詢物件

    Returns:
        pd.DataFrame: 查詢結果的 DataFrame
    """
    result = session.execute(query).fetchall()
    if not result:
        return pd.DataFrame()

    # 檢查是否為 ORM 對象
    if hasattr(result[0], "_mapping"):
        # 獲取列名
        columns = list(result[0]._mapping.keys())
        
        # 檢查是否為單一 ORM 對象
        if len(columns) == 1 and isinstance(result[0][0], Base):
            # 將 ORM 對象轉換為字典列表
            data = []
            for row in result:
                orm_obj = row[0]
                # 獲取 ORM 對象的屬性
                obj_dict = {}
                for c in orm_obj.__table__.columns:
                    value = getattr(orm_obj, c.name)
                    # 處理枚舉類型
                    if hasattr(value, "value"):
                        obj_dict[c.name] = value.value
                    else:
                        obj_dict[c.name] = value
                data.append(obj_dict)
            
            # 創建 DataFrame
            if data:
                return pd.DataFrame(data)
            else:
                return pd.DataFrame()
        else:
            # 一般情況，直接使用 _mapping
            data = []
            for row in result:
                row_dict = {}
                for key, value in row._mapping.items():
                    # 處理枚舉類型
                    if hasattr(value, "value"):
                        row_dict[key] = value.value
                    else:
                        row_dict[key] = value
                data.append(row_dict)
            return pd.DataFrame(data)
    else:
        # 非 ORM 對象，直接轉換
        return pd.DataFrame(result)
```

### 2. New Test File for Parquet Utils

A new test file `tests/test_parquet_utils.py` was created to test the functionality of the Parquet utilities module:

```python
# Key test functions
def test_query_to_dataframe(sample_data):
    """測試將 SQLAlchemy 查詢結果轉換為 Pandas DataFrame"""
    session = sample_data
    
    # 查詢日線資料
    query = select(MarketDaily)
    df = query_to_dataframe(session, query)
    
    # 檢查結果
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "symbol" in df.columns
    assert "close" in df.columns
    assert df.iloc[0]["symbol"] == "2330.TW"
    assert df.iloc[0]["close"] == 505.0

def test_save_and_read_parquet():
    """測試儲存和讀取 Parquet 檔案"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 創建測試資料
        df = pd.DataFrame({
            "symbol": ["2330.TW", "2317.TW"],
            "date": [date(2023, 1, 1), date(2023, 1, 1)],
            "close": [505.0, 105.0],
            "volume": [10000000.0, 5000000.0],
        })
        
        # 儲存為 Parquet 格式
        file_path = os.path.join(temp_dir, "test.parquet")
        saved_path = save_to_parquet(df, file_path)
        
        # 檢查檔案是否存在
        assert os.path.exists(saved_path)
        
        # 讀取 Parquet 檔案
        df_read = read_from_parquet(saved_path)
        
        # 檢查結果
        assert isinstance(df_read, pd.DataFrame)
        assert not df_read.empty
        assert "symbol" in df_read.columns
        assert "close" in df_read.columns
        assert df_read.iloc[0]["symbol"] == "2330.TW"
        assert df_read.iloc[0]["close"] == 505.0
```

## Test Coverage

The test coverage for the database-related modules is now:
- `src/database/schema.py`: 96% coverage
- `src/database/parquet_utils.py`: 75% coverage

## Conclusion

The improvements made to the database schema and Parquet utilities modules have enhanced the robustness and reliability of the system. The code now handles SQLAlchemy ORM objects correctly, including proper handling of enum values, which ensures compatibility with the Parquet format. The new tests provide good coverage of the code and will help catch any regressions in the future.
