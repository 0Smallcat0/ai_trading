# -*- coding: utf-8 -*-
"""
Parquet 工具測試模組

測試重構後的 Parquet/Arrow 工具函數，包括：
- Parquet 和 Arrow 格式的讀寫功能測試
- 異常處理測試（ParquetError, ParquetConfigError, ParquetOperationError）
- 檔案 I/O 效能優化測試
- 與資料庫整合功能測試
"""

import pytest
import os
import tempfile
import threading
import time
import pandas as pd
import numpy as np
from datetime import datetime, date, timezone, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.database.schema import (
    Base,
    MarketDaily,
    MarketMinute,
    MarketTick,
    MarketType,
    TimeGranularity,
    DataShard,
    init_db,
)
from src.database.parquet_utils import (
    query_to_dataframe,
    save_to_parquet,
    read_from_parquet,
    save_to_arrow,
    read_from_arrow,
    create_market_data_shard,
    load_from_shard,
    ParquetError,
    ParquetConfigError,
    ParquetOperationError
)


@pytest.fixture
def temp_db():
    """創建內存資料庫"""
    # 創建 SQLite 內存引擎
    engine = create_engine("sqlite:///:memory:")

    # 初始化資料庫
    init_db(engine)

    yield engine


@pytest.fixture
def sample_data(temp_db):
    """創建測試資料"""
    with Session(temp_db) as session:
        # 創建日線資料
        daily_data = MarketDaily(
            symbol="2330.TW",
            market_type=MarketType.STOCK,
            date=date(2023, 1, 1),
            open=500.0,
            high=510.0,
            low=495.0,
            close=505.0,
            volume=10000000.0,
            data_source="yahoo",
            is_adjusted=True,
        )

        # 創建分鐘資料
        minute_data = MarketMinute(
            symbol="2330.TW",
            market_type=MarketType.STOCK,
            timestamp=datetime(2023, 1, 1, 9, 0, 0, tzinfo=timezone.utc),
            granularity=TimeGranularity.MIN_1,
            open=500.0,
            high=502.0,
            low=499.0,
            close=501.0,
            volume=50000.0,
            data_source="yahoo",
        )

        # 創建 Tick 資料
        tick_data = MarketTick(
            symbol="2330.TW",
            market_type=MarketType.STOCK,
            timestamp=datetime(2023, 1, 1, 9, 0, 1, tzinfo=timezone.utc),
            open=500.0,
            high=500.0,
            low=500.0,
            close=500.0,
            volume=100.0,
            bid_price=499.5,
            ask_price=500.5,
            bid_volume=200.0,
            ask_volume=300.0,
            direction="buy",
            data_source="yahoo",
        )

        # 添加資料
        session.add_all([daily_data, minute_data, tick_data])
        session.commit()

        yield session


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
        df = pd.DataFrame(
            {
                "symbol": ["2330.TW", "2317.TW"],
                "date": [date(2023, 1, 1), date(2023, 1, 1)],
                "close": [505.0, 105.0],
                "volume": [10000000.0, 5000000.0],
            }
        )

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

        # 測試讀取部分欄位
        df_partial = read_from_parquet(saved_path, columns=["symbol", "close"])
        assert "symbol" in df_partial.columns
        assert "close" in df_partial.columns
        assert "volume" not in df_partial.columns


def test_create_market_data_shard(sample_data, monkeypatch):
    """測試創建市場資料分片並儲存為 Parquet 格式"""
    session = sample_data

    # 模擬 DATA_DIR
    with tempfile.TemporaryDirectory() as temp_dir:
        # 修改 DATA_DIR
        monkeypatch.setattr("src.database.parquet_utils.DATA_DIR", temp_dir)

        # 創建市場資料分片
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 1)
        shard, file_path = create_market_data_shard(
            session, MarketDaily, start_date, end_date
        )

        # 檢查結果
        assert shard is not None
        assert file_path is not None
        assert os.path.exists(file_path)
        assert shard.table_name == "market_daily"
        assert shard.start_date == start_date
        assert shard.end_date == end_date
        assert shard.file_format == "parquet"
        assert shard.compression == "snappy"
        assert shard.row_count > 0
        assert shard.file_size_bytes > 0
        assert shard.is_compressed is True

        # 測試讀取分片
        df = load_from_shard(session, shard.shard_id)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        assert "symbol" in df.columns
        assert "close" in df.columns
        assert df.iloc[0]["symbol"] == "2330.TW"
        assert df.iloc[0]["close"] == 505.0


def test_multiple_time_granularities(temp_db):
    """測試多種時間粒度的支援"""
    with Session(temp_db) as session:
        # 創建不同時間粒度的分鐘資料
        base_time = datetime(2023, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        granularities = [
            TimeGranularity.MIN_1,
            TimeGranularity.MIN_5,
            TimeGranularity.MIN_15,
            TimeGranularity.MIN_30,
            TimeGranularity.HOUR_1,
        ]

        for i, granularity in enumerate(granularities):
            minute_data = MarketMinute(
                symbol="2330.TW",
                market_type=MarketType.STOCK,
                timestamp=base_time + timedelta(minutes=i * 5),
                granularity=granularity,
                open=500.0 + i,
                high=510.0 + i,
                low=495.0 + i,
                close=505.0 + i,
                volume=10000000.0 + i * 1000,
                data_source="yahoo",
            )
            session.add(minute_data)

        session.commit()

        # 查詢不同時間粒度的資料
        for granularity in granularities:
            query = select(MarketMinute).where(MarketMinute.granularity == granularity)
            df = query_to_dataframe(session, query)

            # 檢查結果
            assert not df.empty
            # 枚舉值已轉換為字符串，直接比較
            assert df.iloc[0]["granularity"] == granularity.value


class TestParquetExceptions:
    """測試 Parquet 工具的異常處理"""

    def test_parquet_config_error_invalid_dataframe(self):
        """測試無效 DataFrame 配置錯誤"""
        with pytest.raises(ParquetConfigError, match="DataFrame 不能為 None"):
            save_to_parquet(None, "test.parquet")

    def test_parquet_config_error_empty_file_path(self):
        """測試空檔案路徑配置錯誤"""
        df = pd.DataFrame({'a': [1, 2, 3]})
        with pytest.raises(ParquetConfigError, match="檔案路徑不能為空"):
            save_to_parquet(df, "")

    def test_parquet_config_error_invalid_compression(self):
        """測試無效壓縮格式配置錯誤"""
        df = pd.DataFrame({'a': [1, 2, 3]})
        with pytest.raises(ParquetConfigError, match="不支援的壓縮格式"):
            save_to_parquet(df, "test.parquet", compression="invalid")

    def test_parquet_operation_error_file_not_found(self):
        """測試檔案不存在操作錯誤"""
        with pytest.raises(ParquetConfigError, match="檔案或目錄不存在"):
            read_from_parquet("/nonexistent/path.parquet")

    def test_query_config_error_invalid_session(self):
        """測試無效會話配置錯誤"""
        with pytest.raises(ParquetConfigError, match="SQLAlchemy 會話不能為 None"):
            query_to_dataframe(None, None)

    def test_exception_chaining(self):
        """測試異常鏈追蹤機制"""
        # 模擬內部異常
        with patch('src.database.parquet_utils.pa.Table.from_pandas') as mock_table:
            mock_table.side_effect = Exception("內部錯誤")

            df = pd.DataFrame({'a': [1, 2, 3]})
            with pytest.raises(ParquetOperationError) as exc_info:
                save_to_parquet(df, "test.parquet")

            # 驗證異常鏈
            assert exc_info.value.__cause__ is not None
            assert "內部錯誤" in str(exc_info.value.__cause__)


class TestArrowOperations:
    """測試 Arrow 格式操作"""

    def test_save_and_read_arrow(self):
        """測試 Arrow 儲存和讀取"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 創建測試資料
            df = pd.DataFrame({
                'id': [1, 2, 3],
                'name': ['Alice', 'Bob', 'Charlie'],
                'score': [95.5, 87.2, 92.8]
            })

            # 測試儲存
            file_path = os.path.join(temp_dir, 'test.feather')
            saved_path = save_to_arrow(df, file_path, compression="lz4")

            assert saved_path == file_path
            assert os.path.exists(file_path)

            # 測試讀取
            loaded_df = read_from_arrow(file_path)

            assert len(loaded_df) == 3
            assert list(loaded_df.columns) == ['id', 'name', 'score']
            assert loaded_df['name'].tolist() == ['Alice', 'Bob', 'Charlie']

    def test_arrow_compression_formats(self):
        """測試 Arrow 壓縮格式"""
        with tempfile.TemporaryDirectory() as temp_dir:
            df = pd.DataFrame({'x': list(range(100)), 'y': list(range(100, 200))})

            formats = ["lz4", "zstd", "uncompressed"]

            for compression in formats:
                file_path = os.path.join(temp_dir, f'test_{compression}.feather')

                # 測試儲存
                saved_path = save_to_arrow(df, file_path, compression=compression)
                assert os.path.exists(saved_path)

                # 測試讀取
                loaded_df = read_from_arrow(saved_path)
                assert len(loaded_df) == 100
                assert loaded_df['x'].tolist() == list(range(100))

    def test_arrow_config_errors(self):
        """測試 Arrow 配置錯誤"""
        df = pd.DataFrame({'a': [1, 2, 3]})

        # 測試無效壓縮格式
        with pytest.raises(ParquetConfigError, match="Arrow 格式不支援的壓縮格式"):
            save_to_arrow(df, "test.feather", compression="invalid")

        # 測試空檔案路徑
        with pytest.raises(ParquetConfigError, match="檔案路徑不能為空"):
            save_to_arrow(df, "")


class TestParquetPerformance:
    """測試 Parquet 工具效能"""

    def test_large_dataframe_performance(self):
        """測試大型 DataFrame 效能"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 創建大型測試資料
            large_df = pd.DataFrame({
                'id': list(range(10000)),
                'value': list(range(10000, 20000)),
                'category': ['A', 'B', 'C'] * (10000 // 3 + 1)
            })[:10000]

            file_path = os.path.join(temp_dir, 'large_data.parquet')

            # 測試儲存效能
            start_time = time.time()
            save_to_parquet(large_df, file_path, compression="snappy")
            save_time = time.time() - start_time

            # 測試讀取效能
            start_time = time.time()
            loaded_df = read_from_parquet(file_path)
            load_time = time.time() - start_time

            # 驗證結果
            assert len(loaded_df) == 10000
            assert save_time < 2.0  # 儲存應該在2秒內完成
            assert load_time < 1.0  # 讀取應該在1秒內完成

    def test_concurrent_operations(self):
        """測試並發操作"""
        with tempfile.TemporaryDirectory() as temp_dir:
            df = pd.DataFrame({'data': list(range(1000))})
            results = []
            errors = []

            def worker(worker_id):
                try:
                    file_path = os.path.join(temp_dir, f'concurrent_{worker_id}.parquet')
                    save_to_parquet(df, file_path)
                    loaded_df = read_from_parquet(file_path)
                    results.append(len(loaded_df))
                except Exception as e:
                    errors.append(e)

            # 創建多個執行緒
            threads = []
            for i in range(5):
                thread = threading.Thread(target=worker, args=(i,))
                threads.append(thread)
                thread.start()

            # 等待所有執行緒完成
            for thread in threads:
                thread.join()

            # 驗證結果
            assert len(errors) == 0
            assert len(results) == 5
            assert all(result == 1000 for result in results)


class TestParquetIntegration:
    """測試 Parquet 工具與資料庫整合"""

    def test_integration_with_schema_fixes(self, temp_db):
        """測試與修正後的 schema 整合"""
        with Session(temp_db) as session:
            # 創建分片記錄，測試 file_format 預設值
            shard = DataShard(
                table_name="market_daily",
                shard_key="date",
                shard_id="parquet_integration_shard",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31)
            )

            session.add(shard)
            session.commit()

            # 驗證 file_format 預設值
            assert shard.file_format == 'parquet'

            # 測試查詢功能
            query = session.query(DataShard).filter_by(shard_id="parquet_integration_shard")
            result = query.first()
            assert result is not None
            assert result.file_format == 'parquet'

    def test_load_from_shard_with_arrow_format(self, temp_db):
        """測試從 Arrow 格式分片載入資料"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with Session(temp_db) as session:
                # 創建測試資料並儲存為 Arrow 格式
                test_df = pd.DataFrame({
                    'symbol': ['TEST.TW'],
                    'date': [date(2024, 1, 1)],
                    'close': [100.0]
                })

                file_path = os.path.join(temp_dir, 'test_shard.feather')
                save_to_arrow(test_df, file_path)

                # 創建分片記錄
                shard = DataShard(
                    table_name="market_daily",
                    shard_key="date",
                    shard_id="test_arrow_shard",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 1),
                    file_path=file_path,
                    file_format="arrow"
                )

                session.add(shard)
                session.commit()

                # 測試載入
                loaded_df = load_from_shard(session, "test_arrow_shard")

                assert len(loaded_df) == 1
                assert loaded_df['symbol'].iloc[0] == 'TEST.TW'
                assert loaded_df['close'].iloc[0] == 100.0
