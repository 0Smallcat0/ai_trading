"""
資料驗證模組測試

此模組測試資料驗證相關功能，包括：
- 時間序列連續性檢查
- 缺失值檢查
- 異常值檢測
- 資料完整性驗證
"""

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
    DataChecksum,
    init_db,
)
from src.database.data_validation import DataValidator


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
        daily_data = [
            MarketDaily(
                symbol="2330.TW",
                market_type=MarketType.STOCK,
                date=date(2023, 1, 2),  # 週一
                open=500.0,
                high=510.0,
                low=495.0,
                close=505.0,
                volume=10000000.0,
                data_source="yahoo",
                is_adjusted=True,
            ),
            MarketDaily(
                symbol="2330.TW",
                market_type=MarketType.STOCK,
                date=date(2023, 1, 3),  # 週二
                open=505.0,
                high=515.0,
                low=500.0,
                close=510.0,
                volume=12000000.0,
                data_source="yahoo",
                is_adjusted=True,
            ),
            MarketDaily(
                symbol="2330.TW",
                market_type=MarketType.STOCK,
                date=date(2023, 1, 4),  # 週三
                open=510.0,
                high=520.0,
                low=505.0,
                close=515.0,
                volume=15000000.0,
                data_source="yahoo",
                is_adjusted=True,
            ),
            # 缺少 2023-01-05 (週四)
            MarketDaily(
                symbol="2330.TW",
                market_type=MarketType.STOCK,
                date=date(2023, 1, 6),  # 週五
                open=515.0,
                high=525.0,
                low=510.0,
                close=520.0,
                volume=11000000.0,
                data_source="yahoo",
                is_adjusted=True,
            ),
            # 異常值
            MarketDaily(
                symbol="2330.TW",
                market_type=MarketType.STOCK,
                date=date(2023, 1, 9),  # 週一
                open=520.0,
                high=530.0,
                low=515.0,
                close=525.0,
                volume=50000000.0,  # 異常高的成交量
                data_source="yahoo",
                is_adjusted=True,
            ),
            # 缺失值
            MarketDaily(
                symbol="2330.TW",
                market_type=MarketType.STOCK,
                date=date(2023, 1, 10),  # 週二
                open=525.0,
                high=None,  # 缺失值
                low=None,  # 缺失值
                close=530.0,
                volume=9000000.0,
                data_source="yahoo",
                is_adjusted=True,
            ),
        ]

        # 創建分鐘資料
        minute_data = []
        base_time = datetime(2023, 1, 2, 9, 0, 0, tzinfo=timezone.utc)
        for i in range(60):  # 9:00-9:59
            minute_data.append(
                MarketMinute(
                    symbol="2330.TW",
                    market_type=MarketType.STOCK,
                    timestamp=base_time + timedelta(minutes=i),
                    granularity=TimeGranularity.MIN_1,
                    open=500.0 + i * 0.1,
                    high=500.0 + i * 0.1 + 0.5,
                    low=500.0 + i * 0.1 - 0.5,
                    close=500.0 + i * 0.1 + 0.2,
                    volume=100000.0 + i * 1000,
                    data_source="yahoo",
                )
            )

        # 缺少 10:00-10:04
        for i in range(55):  # 10:05-10:59
            minute_data.append(
                MarketMinute(
                    symbol="2330.TW",
                    market_type=MarketType.STOCK,
                    timestamp=base_time + timedelta(minutes=i + 65),  # 跳過 5 分鐘
                    granularity=TimeGranularity.MIN_1,
                    open=506.0 + i * 0.1,
                    high=506.0 + i * 0.1 + 0.5,
                    low=506.0 + i * 0.1 - 0.5,
                    close=506.0 + i * 0.1 + 0.2,
                    volume=100000.0 + i * 1000,
                    data_source="yahoo",
                )
            )

        # 添加資料
        session.add_all(daily_data + minute_data)
        session.commit()

        yield session


def test_validate_time_series_continuity(sample_data):
    """測試時間序列連續性檢查"""
    validator = DataValidator(sample_data)

    # 測試日線資料連續性
    result = validator.validate_time_series_continuity(
        MarketDaily,
        "2330.TW",
        pd.to_datetime(date(2023, 1, 2)).date(),
        pd.to_datetime(date(2023, 1, 10)).date(),
    )

    # 檢查結果
    assert not result["is_continuous"]
    assert result["continuity_score"] < 1.0
    assert len(result["missing_dates"]) > 0
    assert date(2023, 1, 5) in result["missing_dates"]  # 缺少週四

    # 測試分鐘資料連續性
    result = validator.validate_time_series_continuity(
        MarketMinute,
        "2330.TW",
        pd.to_datetime(date(2023, 1, 2)).date(),
        pd.to_datetime(date(2023, 1, 2)).date(),
    )

    # 檢查結果
    assert not result["is_continuous"]
    assert result["continuity_score"] < 1.0
    assert len(result["missing_intervals"]) > 0


def test_check_missing_values(sample_data):
    """測試缺失值檢查"""
    validator = DataValidator(sample_data)

    # 測試日線資料缺失值
    result = validator.check_missing_values(
        MarketDaily,
        "2330.TW",
        pd.to_datetime(date(2023, 1, 2)).date(),
        pd.to_datetime(date(2023, 1, 10)).date(),
    )

    # 檢查結果
    assert result["has_missing"]
    assert "high" in result["missing_counts"]
    assert "low" in result["missing_counts"]
    assert result["missing_counts"]["high"] > 0
    assert result["missing_counts"]["low"] > 0


def test_detect_outliers(sample_data):
    """測試異常值檢測"""
    validator = DataValidator(sample_data)

    # 測試日線資料異常值
    result = validator.detect_outliers(
        MarketDaily,
        "2330.TW",
        pd.to_datetime(date(2023, 1, 2)).date(),
        pd.to_datetime(date(2023, 1, 10)).date(),
        threshold=2.0,  # 降低閾值以檢測更多異常值
    )

    # 檢查結果
    assert result["has_outliers"]
    assert "volume" in result["outlier_counts"]
    assert result["outlier_counts"]["volume"] > 0


def test_verify_data_integrity(sample_data):
    """測試資料完整性驗證"""
    validator = DataValidator(sample_data)

    # 獲取一個記錄
    record = sample_data.query(MarketDaily).filter_by(symbol="2330.TW").first()

    # 創建校驗記錄
    checksum_fields = ["symbol", "date", "open", "high", "low", "close", "volume"]
    import json
    import hashlib

    record_data = {
        field: getattr(record, field)
        for field in checksum_fields
        if hasattr(record, field)
    }
    json_str = json.dumps(record_data, sort_keys=True, default=str)
    checksum = hashlib.sha256(json_str.encode()).hexdigest()

    # 添加校驗記錄
    checksum_record = DataChecksum(
        table_name="market_daily",
        record_id=record.id,
        checksum=checksum,
        checksum_fields=checksum_fields,
        is_valid=True,
    )
    sample_data.add(checksum_record)
    sample_data.commit()

    # 驗證資料完整性
    result = validator.verify_data_integrity(MarketDaily, record.id)

    # 檢查結果
    assert result["is_valid"]
    assert result["stored_checksum"] == result["current_checksum"]

    # 修改記錄
    record.close = 550.0
    sample_data.commit()

    # 再次驗證資料完整性
    result = validator.verify_data_integrity(MarketDaily, record.id)

    # 檢查結果
    assert not result["is_valid"]
    assert result["stored_checksum"] != result["current_checksum"]
