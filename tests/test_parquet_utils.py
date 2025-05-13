import pytest
import os
import tempfile
import pandas as pd
import numpy as np
from datetime import datetime, date, timezone, timedelta
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
    create_market_data_shard,
    load_from_shard,
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
