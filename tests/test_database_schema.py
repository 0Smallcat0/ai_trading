import pytest
from datetime import datetime, date, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


def test_schema_import():
    """測試資料庫 schema 模組能否正確匯入。"""
    import src.database.schema

    assert hasattr(src.database.schema, "__file__")


def test_market_data_tables():
    """測試市場資料表結構是否正確。"""
    from src.database.schema import (
        Base,
        MarketDaily,
        MarketMinute,
        MarketTick,
        MarketType,
        TimeGranularity,
    )

    # 創建內存資料庫
    engine = create_engine("sqlite:///:memory:")

    # 創建資料表
    Base.metadata.create_all(engine)

    # 檢查資料表是否存在
    with engine.connect() as conn:
        for table_name in ["market_daily", "market_minute", "market_tick"]:
            result = conn.execute(
                text(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
                )
            )
            assert result.fetchone() is not None, f"資料表 {table_name} 不存在"

    # 測試插入資料
    with Session(engine) as session:
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

        # 檢查資料是否正確插入
        assert daily_data.id is not None
        assert minute_data.id is not None
        assert tick_data.id is not None

        # 檢查校驗碼是否已計算
        assert daily_data.checksum is not None
        assert minute_data.checksum is not None
        assert tick_data.checksum is not None

        # 檢查查詢
        result_daily = session.query(MarketDaily).filter_by(symbol="2330.TW").first()
        assert result_daily is not None
        assert result_daily.close == 505.0

        result_minute = session.query(MarketMinute).filter_by(symbol="2330.TW").first()
        assert result_minute is not None
        assert result_minute.granularity == TimeGranularity.MIN_1

        result_tick = session.query(MarketTick).filter_by(symbol="2330.TW").first()
        assert result_tick is not None
        assert result_tick.direction == "buy"


def test_data_integrity_mechanisms():
    """測試資料完整性機制是否正確。"""
    from src.database.schema import Base, MarketDaily, MarketType, DataChecksum, init_db

    # 創建內存資料庫
    engine = create_engine("sqlite:///:memory:")

    # 初始化資料庫
    init_db(engine)

    # 測試插入資料
    with Session(engine) as session:
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

        # 添加資料
        session.add(daily_data)
        session.commit()

        # 檢查校驗碼是否已計算
        assert daily_data.checksum is not None
        original_checksum = daily_data.checksum

        # 創建資料校驗記錄
        checksum_record = DataChecksum(
            table_name="market_daily",
            record_id=daily_data.id,
            checksum=daily_data.checksum,
            checksum_fields=["symbol", "open", "high", "low", "close", "volume"],
            is_valid=True,
        )
        session.add(checksum_record)
        session.commit()

        # 修改資料
        daily_data.close = 510.0
        session.commit()

        # 檢查校驗碼是否已更新
        assert daily_data.checksum != original_checksum

        # 檢查資料校驗記錄
        checksum_record = (
            session.query(DataChecksum)
            .filter_by(table_name="market_daily", record_id=daily_data.id)
            .first()
        )
        assert checksum_record is not None
        assert checksum_record.checksum != daily_data.checksum
        assert checksum_record.is_valid is True  # 尚未驗證，仍為 True


def test_data_sharding():
    """測試資料分片功能是否正確。"""
    from src.database.schema import Base, DataShard, create_data_shard

    # 創建內存資料庫
    engine = create_engine("sqlite:///:memory:")

    # 創建資料表
    Base.metadata.create_all(engine)

    # 測試創建資料分片
    with Session(engine) as session:
        # 創建資料分片
        start_date = date(2023, 1, 1)
        end_date = date(2023, 3, 31)
        shard = create_data_shard(session, "market_daily", start_date, end_date)
        session.commit()

        # 檢查資料分片是否正確創建
        assert shard.id is not None
        assert shard.table_name == "market_daily"
        assert shard.start_date == start_date
        assert shard.end_date == end_date
        assert shard.file_format == "parquet"
        assert shard.compression == "snappy"

        # 檢查查詢
        result = session.query(DataShard).filter_by(table_name="market_daily").first()
        assert result is not None
        assert (
            result.shard_id
            == f"market_daily_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        )
