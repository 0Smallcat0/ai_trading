# -*- coding: utf-8 -*-
"""
校驗碼管理器測試模組

測試校驗碼管理器的各項功能，包括：
- 校驗策略測試
- 校驗碼生成和驗證
- 批量完整性檢查
- 自動校驗碼創建
"""

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.schema import Base, DataChecksum, MarketDaily, init_db
from src.database.checksum_manager import (
    ChecksumManager,
    TimeBasedChecksumStrategy,
    CriticalDataChecksumStrategy,
)


@pytest.fixture
def test_session():
    """創建測試資料庫會話"""
    # 使用記憶體資料庫進行測試
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    # 添加測試資料
    test_data = [
        MarketDaily(
            symbol="2330.TW",
            date=date(2024, 1, 1),
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
            volume=1000000,
        ),
        MarketDaily(
            symbol="2330.TW",
            date=date(2024, 1, 2),
            open=103.0,
            high=108.0,
            low=101.0,
            close=106.0,
            volume=1200000,
        ),
        MarketDaily(
            symbol="2454.TW",
            date=date(2024, 1, 1),
            open=50.0,
            high=52.0,
            low=49.0,
            close=51.0,
            volume=800000,
        ),
    ]

    for data in test_data:
        session.add(data)
    session.commit()

    yield session
    session.close()


@pytest.fixture
def checksum_manager(test_session):
    """創建校驗碼管理器實例"""
    return ChecksumManager(test_session)


class TestTimeBasedChecksumStrategy:
    """測試基於時間的校驗策略"""

    def test_should_verify_old_verification(self):
        """測試舊驗證應該重新驗證"""
        strategy = TimeBasedChecksumStrategy(
            fields=["symbol", "date", "close"], verify_interval_days=7
        )
        result = strategy.should_verify(record_age_days=30, last_verified_days=10)
        assert result is True

    def test_should_not_verify_recent_verification(self):
        """測試最近驗證不應該重新驗證"""
        strategy = TimeBasedChecksumStrategy(
            fields=["symbol", "date", "close"], verify_interval_days=7
        )
        result = strategy.should_verify(record_age_days=30, last_verified_days=3)
        assert result is False


class TestCriticalDataChecksumStrategy:
    """測試關鍵資料校驗策略"""

    def test_should_verify_frequently(self):
        """測試關鍵資料應該頻繁驗證"""
        strategy = CriticalDataChecksumStrategy(
            fields=["symbol", "date", "close"], verify_interval_days=1
        )
        result = strategy.should_verify(record_age_days=10, last_verified_days=2)
        assert result is True

    def test_should_not_verify_very_recent(self):
        """測試非常最近的驗證不需要重新驗證"""
        strategy = CriticalDataChecksumStrategy(
            fields=["symbol", "date", "close"], verify_interval_days=1
        )
        result = strategy.should_verify(record_age_days=10, last_verified_days=0)
        assert result is False


class TestChecksumManager:
    """測試校驗碼管理器"""

    def test_register_strategy(self, checksum_manager):
        """測試註冊校驗策略"""
        custom_strategy = TimeBasedChecksumStrategy(
            fields=["symbol", "close"], verify_interval_days=3
        )
        checksum_manager.register_strategy("custom_strategy", custom_strategy)

        assert "custom_strategy" in checksum_manager.strategies
        assert checksum_manager.strategies["custom_strategy"] == custom_strategy

    def test_generate_checksum_for_record(self, checksum_manager, test_session):
        """測試為記錄生成校驗碼"""
        record = test_session.query(MarketDaily).filter_by(symbol="2330.TW").first()
        fields = ["symbol", "date", "open", "high", "low", "close", "volume"]

        checksum = checksum_manager.generate_checksum_for_record(record, fields)

        # 驗證校驗碼格式
        assert len(checksum) == 64  # SHA-256 產生 64 字元的十六進位字串
        assert all(c in "0123456789abcdef" for c in checksum)

        # 驗證校驗碼的一致性
        checksum2 = checksum_manager.generate_checksum_for_record(record, fields)
        assert checksum == checksum2

    def test_generate_checksum_with_different_fields(
        self, checksum_manager, test_session
    ):
        """測試使用不同欄位生成不同的校驗碼"""
        record = test_session.query(MarketDaily).filter_by(symbol="2330.TW").first()

        checksum1 = checksum_manager.generate_checksum_for_record(
            record, ["symbol", "date", "close"]
        )
        checksum2 = checksum_manager.generate_checksum_for_record(
            record, ["symbol", "date", "open", "close"]
        )

        assert checksum1 != checksum2

    def test_create_checksum_record(self, checksum_manager, test_session):
        """測試創建校驗記錄"""
        record = test_session.query(MarketDaily).filter_by(symbol="2330.TW").first()

        checksum_record = checksum_manager.create_checksum_record(
            MarketDaily, record.id, "market_daily_standard"
        )

        assert checksum_record.table_name == "market_daily"
        assert checksum_record.record_id == record.id
        assert checksum_record.checksum is not None
        assert checksum_record.checksum_fields is not None
        assert checksum_record.is_valid is True
        assert checksum_record.verified_at is not None

    def test_create_checksum_record_unknown_strategy(self, checksum_manager):
        """測試使用未知策略創建校驗記錄時拋出異常"""
        with pytest.raises(ValueError, match="未知的校驗策略"):
            checksum_manager.create_checksum_record(MarketDaily, 1, "unknown_strategy")

    def test_create_checksum_record_nonexistent_record(self, checksum_manager):
        """測試為不存在的記錄創建校驗記錄時拋出異常"""
        with pytest.raises(ValueError, match="找不到記錄"):
            checksum_manager.create_checksum_record(
                MarketDaily, 99999, "market_daily_standard"
            )

    def test_verify_record_integrity_valid(self, checksum_manager, test_session):
        """測試驗證有效記錄的完整性"""
        record = test_session.query(MarketDaily).filter_by(symbol="2330.TW").first()

        # 先創建校驗記錄
        checksum_record = checksum_manager.create_checksum_record(
            MarketDaily, record.id, "market_daily_standard"
        )

        # 驗證完整性
        result = checksum_manager.verify_record_integrity(MarketDaily, record.id)

        assert result["is_valid"] is True
        assert result["record_id"] == record.id
        assert result["table_name"] == "market_daily"
        assert result["stored_checksum"] == result["current_checksum"]
        assert "verified_at" in result

    def test_verify_record_integrity_invalid(self, checksum_manager, test_session):
        """測試驗證無效記錄的完整性"""
        record = test_session.query(MarketDaily).filter_by(symbol="2330.TW").first()

        # 創建校驗記錄
        checksum_record = checksum_manager.create_checksum_record(
            MarketDaily, record.id, "market_daily_standard"
        )

        # 修改記錄以使其無效
        record.close = 999.99
        test_session.commit()

        # 驗證完整性
        result = checksum_manager.verify_record_integrity(MarketDaily, record.id)

        assert result["is_valid"] is False
        assert result["record_id"] == record.id
        assert result["stored_checksum"] != result["current_checksum"]

    def test_verify_record_integrity_no_record(self, checksum_manager):
        """測試驗證不存在記錄的完整性"""
        result = checksum_manager.verify_record_integrity(MarketDaily, 99999)

        assert result["is_valid"] is False
        assert "找不到記錄" in result["error"]
        assert result["record_id"] == 99999

    def test_verify_record_integrity_no_checksum(self, checksum_manager, test_session):
        """測試驗證沒有校驗記錄的記錄完整性"""
        record = test_session.query(MarketDaily).filter_by(symbol="2330.TW").first()

        result = checksum_manager.verify_record_integrity(MarketDaily, record.id)

        assert result["is_valid"] is False
        assert "找不到校驗記錄" in result["error"]
        assert result["record_id"] == record.id

    def test_batch_verify_integrity(self, checksum_manager, test_session):
        """測試批量驗證完整性"""
        # 為所有記錄創建校驗記錄
        records = test_session.query(MarketDaily).all()
        for record in records:
            checksum_manager.create_checksum_record(
                MarketDaily, record.id, "market_daily_standard"
            )

        # 修改其中一個記錄的驗證時間，使其需要重新驗證
        checksum_record = test_session.query(DataChecksum).first()
        checksum_record.verified_at = datetime.now(timezone.utc) - timedelta(days=10)
        test_session.commit()

        # 執行批量驗證
        result = checksum_manager.batch_verify_integrity(
            MarketDaily, "market_daily_standard"
        )

        assert result["total_checked"] >= 1
        assert result["valid_records"] >= 0
        assert result["invalid_records"] >= 0
        assert result["errors"] >= 0
        assert "verification_time" in result

    def test_auto_create_checksums(self, checksum_manager, test_session):
        """測試自動創建校驗碼"""
        # 確保沒有現有的校驗記錄
        test_session.query(DataChecksum).delete()
        test_session.commit()

        result = checksum_manager.auto_create_checksums(
            MarketDaily, "market_daily_standard", batch_size=10
        )

        assert result["total_processed"] > 0
        assert result["successful_creates"] > 0
        assert result["errors"] == 0
        assert "processing_time" in result

        # 驗證校驗記錄已創建
        checksum_count = test_session.query(DataChecksum).count()
        assert checksum_count == result["successful_creates"]

    def test_auto_create_checksums_unknown_strategy(self, checksum_manager):
        """測試使用未知策略自動創建校驗碼時拋出異常"""
        with pytest.raises(ValueError, match="未知的校驗策略"):
            checksum_manager.auto_create_checksums(MarketDaily, "unknown_strategy")

    def test_get_integrity_report(self, checksum_manager, test_session):
        """測試獲取完整性報告"""
        # 創建一些校驗記錄
        records = test_session.query(MarketDaily).all()
        for i, record in enumerate(records):
            checksum_record = checksum_manager.create_checksum_record(
                MarketDaily, record.id, "market_daily_standard"
            )

            # 設定不同的驗證狀態
            if i == 0:
                checksum_record.is_valid = False
            elif i == 1:
                checksum_record.verified_at = datetime.now(timezone.utc) - timedelta(
                    days=10
                )

        test_session.commit()

        # 獲取報告
        report = checksum_manager.get_integrity_report("market_daily")

        assert report["total_records"] == len(records)
        assert "valid_records" in report
        assert "invalid_records" in report
        assert "unverified_records" in report
        assert "by_table" in report
        assert "verification_age_distribution" in report
        assert "integrity_percentage" in report
        assert "market_daily" in report["by_table"]

    def test_get_integrity_report_all_tables(self, checksum_manager, test_session):
        """測試獲取所有表的完整性報告"""
        # 創建校驗記錄
        record = test_session.query(MarketDaily).first()
        checksum_manager.create_checksum_record(
            MarketDaily, record.id, "market_daily_standard"
        )

        # 獲取所有表的報告
        report = checksum_manager.get_integrity_report()

        assert report["total_records"] >= 1
        assert "by_table" in report
        assert "market_daily" in report["by_table"]

    @patch("threading.Thread")
    def test_schedule_integrity_check(self, mock_thread, checksum_manager):
        """測試排程完整性檢查"""
        checksum_manager.schedule_integrity_check(
            MarketDaily, "market_daily_standard", check_interval_hours=1
        )

        # 驗證執行緒已啟動
        mock_thread.assert_called_once()
        args, kwargs = mock_thread.call_args
        assert kwargs["daemon"] is True

        # 驗證 start 方法被調用
        mock_thread.return_value.start.assert_called_once()
