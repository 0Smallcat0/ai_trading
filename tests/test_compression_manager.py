# -*- coding: utf-8 -*-
"""
壓縮管理器測試模組

測試重構後的壓縮管理器的各項功能，包括：
- 自定義異常類別測試
- 多種壓縮格式支援測試
- 效能優化功能測試
- 壓縮策略測試
- 資料壓縮功能
- 格式轉換
- 自動壓縮
"""

import os
import tempfile
import threading
import time
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.schema import Base, DataShard, MarketDaily, init_db
from src.database.compression_manager import (
    CompressionManager,
    TimeBasedCompressionStrategy,
    SizeBasedCompressionStrategy,
    CompressionError,
    CompressionConfigError,
    CompressionOperationError
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
            volume=1000000
        ),
        MarketDaily(
            symbol="2330.TW",
            date=date(2024, 1, 2),
            open=103.0,
            high=108.0,
            low=101.0,
            close=106.0,
            volume=1200000
        ),
        MarketDaily(
            symbol="2454.TW",
            date=date(2024, 1, 1),
            open=50.0,
            high=52.0,
            low=49.0,
            close=51.0,
            volume=800000
        )
    ]

    for data in test_data:
        session.add(data)
    session.commit()

    yield session
    session.close()


@pytest.fixture
def compression_manager(test_session):
    """創建壓縮管理器實例"""
    return CompressionManager(test_session)


@pytest.fixture
def temp_dir():
    """創建臨時目錄"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


class TestTimeBasedCompressionStrategy:
    """測試基於時間的壓縮策略"""

    def test_should_compress_old_data(self):
        """測試舊資料應該壓縮"""
        strategy = TimeBasedCompressionStrategy(min_age_days=30)
        result = strategy.should_compress(data_size=1000000, age_days=45)
        assert result is True

    def test_should_not_compress_new_data(self):
        """測試新資料不應該壓縮"""
        strategy = TimeBasedCompressionStrategy(min_age_days=30)
        result = strategy.should_compress(data_size=1000000, age_days=15)
        assert result is False

    def test_get_compression_params(self):
        """測試獲取壓縮參數"""
        strategy = TimeBasedCompressionStrategy(compression_type="gzip")
        params = strategy.get_compression_params()
        assert params["compression"] == "gzip"


class TestSizeBasedCompressionStrategy:
    """測試基於大小的壓縮策略"""

    def test_should_compress_large_data(self):
        """測試大資料應該壓縮"""
        strategy = SizeBasedCompressionStrategy(min_size_mb=100)
        # 150MB 的資料
        result = strategy.should_compress(data_size=150 * 1024 * 1024, age_days=1)
        assert result is True

    def test_should_not_compress_small_data(self):
        """測試小資料不應該壓縮"""
        strategy = SizeBasedCompressionStrategy(min_size_mb=100)
        # 50MB 的資料
        result = strategy.should_compress(data_size=50 * 1024 * 1024, age_days=1)
        assert result is False


class TestCompressionManager:
    """測試壓縮管理器"""

    def test_register_strategy(self, compression_manager):
        """測試註冊壓縮策略"""
        custom_strategy = TimeBasedCompressionStrategy("zstd", min_age_days=7)
        compression_manager.register_strategy("custom_weekly", custom_strategy)

        assert "custom_weekly" in compression_manager.strategies
        assert compression_manager.strategies["custom_weekly"] == custom_strategy

    @patch('src.database.compression_manager.os.makedirs')
    @patch('src.database.compression_manager.os.path.getsize')
    def test_compress_table_data(self, mock_getsize, mock_makedirs, compression_manager, temp_dir):
        """測試壓縮表格資料"""
        # 模擬檔案大小
        mock_getsize.return_value = 1024

        with patch.object(compression_manager, '_save_compressed_parquet') as mock_save:
            file_path, stats = compression_manager.compress_table_data(
                MarketDaily,
                date(2024, 1, 1),
                date(2024, 1, 2),
                compression_type="snappy"
            )

            assert file_path != ""
            assert "original_size_bytes" in stats
            assert "compressed_size_bytes" in stats
            assert "compression_ratio" in stats
            assert "compression_time_seconds" in stats
            assert stats["compression_type"] == "snappy"
            assert stats["row_count"] > 0

            mock_save.assert_called_once()

    def test_compress_table_data_no_data(self, compression_manager):
        """測試壓縮沒有資料的情況"""
        file_path, stats = compression_manager.compress_table_data(
            MarketDaily,
            date(2025, 1, 1),  # 未來日期，沒有資料
            date(2025, 1, 2),
            compression_type="snappy"
        )

        assert file_path == ""
        assert stats == {}

    @patch('src.database.compression_manager.pq.write_table')
    def test_save_compressed_parquet(self, mock_write_table, compression_manager):
        """測試儲存壓縮的 Parquet 檔案"""
        df = pd.DataFrame({
            'symbol': ['2330.TW'],
            'date': [date(2024, 1, 1)],
            'close': [100.0]
        })

        with patch('src.database.compression_manager.os.makedirs'):
            compression_manager._save_compressed_parquet(
                df, "/test/path.parquet", "snappy"
            )

            mock_write_table.assert_called_once()
            args, kwargs = mock_write_table.call_args
            assert kwargs["compression"] == "snappy"

    def test_get_compression_options(self, compression_manager):
        """測試獲取壓縮選項"""
        # 測試 gzip 選項
        options = compression_manager._get_compression_options("gzip")
        assert "compression_level" in options
        assert options["compression_level"] == 6

        # 測試 zstd 選項
        options = compression_manager._get_compression_options("zstd")
        assert "compression_level" in options
        assert options["compression_level"] == 3

        # 測試 lz4 選項
        options = compression_manager._get_compression_options("lz4")
        assert "use_dictionary" in options
        assert options["use_dictionary"] is True

        # 測試未知壓縮類型
        options = compression_manager._get_compression_options("unknown")
        assert options == {}

    @patch('src.database.compression_manager.pd.read_parquet')
    @patch('src.database.compression_manager.os.path.getsize')
    @patch('src.database.compression_manager.os.makedirs')
    def test_convert_compression_format(
        self, mock_makedirs, mock_getsize, mock_read_parquet, compression_manager
    ):
        """測試轉換壓縮格式"""
        # 模擬讀取的資料
        mock_df = pd.DataFrame({
            'symbol': ['2330.TW'],
            'date': [date(2024, 1, 1)],
            'close': [100.0]
        })
        mock_read_parquet.return_value = mock_df

        # 模擬檔案大小
        mock_getsize.side_effect = [2048, 1024]  # 原始大小, 新大小

        with patch.object(compression_manager, '_save_compressed_parquet') as mock_save:
            stats = compression_manager.convert_compression_format(
                "/source/path.parquet",
                "/target/path.parquet",
                "gzip"
            )

            assert stats["original_size_bytes"] == 2048
            assert stats["new_size_bytes"] == 1024
            assert stats["size_ratio"] == 2.0
            assert stats["target_compression"] == "gzip"
            assert stats["row_count"] == 1

            mock_save.assert_called_once()

    def test_auto_compress_old_data_dry_run(self, compression_manager, test_session):
        """測試自動壓縮舊資料（試運行）"""
        # 創建未壓縮的分片
        old_shard = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="old_shard",
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=31),
            is_compressed=False,
            file_size_bytes=1024000
        )
        test_session.add(old_shard)
        test_session.commit()

        results = compression_manager.auto_compress_old_data(
            strategy_name="time_based_snappy",
            dry_run=True
        )

        assert len(results) == 1
        assert results[0]["shard_id"] == "old_shard"
        assert results[0]["status"] == "would_compress"
        assert "age_days" in results[0]
        assert "file_size_bytes" in results[0]

    def test_auto_compress_old_data_unknown_strategy(self, compression_manager):
        """測試使用未知策略時拋出異常"""
        with pytest.raises(ValueError, match="未知的壓縮策略"):
            compression_manager.auto_compress_old_data("unknown_strategy")

    def test_get_table_class(self, compression_manager):
        """測試根據表名獲取表類別"""
        assert compression_manager._get_table_class("market_daily") == MarketDaily

        with pytest.raises(ValueError, match="未知的表名"):
            compression_manager._get_table_class("unknown_table")

    def test_get_compression_statistics(self, compression_manager, test_session):
        """測試獲取壓縮統計"""
        # 創建測試分片
        compressed_shard = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="compressed_shard",
            is_compressed=True,
            compression="snappy",
            file_size_bytes=1024
        )
        uncompressed_shard = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="uncompressed_shard",
            is_compressed=False,
            file_size_bytes=2048
        )

        test_session.add_all([compressed_shard, uncompressed_shard])
        test_session.commit()

        stats = compression_manager.get_compression_statistics()

        assert stats["total_shards"] == 2
        assert stats["compressed_shards"] == 1
        assert stats["uncompressed_shards"] == 1
        assert "compression_by_type" in stats
        assert "compression_by_table" in stats
        assert "snappy" in stats["compression_by_type"]
        assert "market_daily" in stats["compression_by_table"]


class TestCompressionExceptions:
    """測試壓縮管理器的異常處理"""

    def test_compression_config_error_invalid_session(self):
        """測試無效會話配置錯誤"""
        with pytest.raises(CompressionConfigError, match="SQLAlchemy 會話不能為 None"):
            CompressionManager(None)

    def test_compression_operation_error_invalid_strategy(self, test_session):
        """測試無效策略操作錯誤"""
        manager = CompressionManager(test_session)
        with pytest.raises(CompressionOperationError, match="未知的壓縮策略"):
            manager.auto_compress_old_data("invalid_strategy")

    def test_compression_config_error_invalid_compression_type(self, test_session):
        """測試無效壓縮類型配置錯誤"""
        manager = CompressionManager(test_session)
        with pytest.raises(CompressionConfigError, match="不支援的壓縮格式"):
            manager.compress_table_data(
                MarketDaily,
                date(2024, 1, 1),
                date(2024, 1, 2),
                compression_type="invalid_format"
            )

    def test_exception_chaining(self, test_session):
        """測試異常鏈追蹤機制"""
        manager = CompressionManager(test_session)

        # 模擬內部異常
        with patch('src.database.compression_manager.query_to_dataframe') as mock_query:
            mock_query.side_effect = Exception("查詢錯誤")

            with pytest.raises(CompressionOperationError) as exc_info:
                manager.compress_table_data(
                    MarketDaily,
                    date(2024, 1, 1),
                    date(2024, 1, 2),
                    compression_type="snappy"
                )

            # 驗證異常鏈
            assert exc_info.value.__cause__ is not None
            assert "查詢錯誤" in str(exc_info.value.__cause__)


class TestCompressionFormats:
    """測試多種壓縮格式支援"""

    def test_supported_compression_formats(self, test_session):
        """測試支援的壓縮格式"""
        manager = CompressionManager(test_session)

        # 測試所有支援的格式
        supported_formats = ["snappy", "gzip", "lz4", "zstd", "brotli"]

        for format_type in supported_formats:
            try:
                # 驗證格式驗證不會拋出異常
                manager._validate_compression_type(format_type)
            except Exception as e:
                pytest.fail(f"支援的格式 {format_type} 不應該拋出異常: {e}")

    def test_compression_format_options(self, test_session):
        """測試不同壓縮格式的選項"""
        manager = CompressionManager(test_session)

        # 測試 gzip 選項
        gzip_options = manager._get_compression_options("gzip")
        assert "compression_level" in gzip_options
        assert 1 <= gzip_options["compression_level"] <= 9

        # 測試 zstd 選項
        zstd_options = manager._get_compression_options("zstd")
        assert "compression_level" in zstd_options
        assert 1 <= zstd_options["compression_level"] <= 22

        # 測試 lz4 選項
        lz4_options = manager._get_compression_options("lz4")
        assert "use_dictionary" in lz4_options
        assert isinstance(lz4_options["use_dictionary"], bool)

    def test_compression_performance_comparison(self, test_session):
        """測試不同壓縮格式的效能比較"""
        manager = CompressionManager(test_session)

        # 創建測試資料
        test_df = pd.DataFrame({
            'symbol': ['TEST.TW'] * 1000,
            'date': [date(2024, 1, 1)] * 1000,
            'close': list(range(1000))
        })

        formats = ["snappy", "gzip", "lz4"]
        results = {}

        for format_type in formats:
            with patch('src.database.compression_manager.query_to_dataframe') as mock_query:
                mock_query.return_value = test_df

                with patch('src.database.compression_manager.os.path.getsize') as mock_size:
                    mock_size.return_value = 1024

                    with patch.object(manager, '_save_compressed_parquet'):
                        _, stats = manager.compress_table_data(
                            MarketDaily,
                            date(2024, 1, 1),
                            date(2024, 1, 2),
                            compression_type=format_type
                        )
                        results[format_type] = stats

        # 驗證所有格式都有結果
        for format_type in formats:
            assert format_type in results
            assert "compression_time_seconds" in results[format_type]
            assert "compression_type" in results[format_type]


class TestCompressionPerformance:
    """測試壓縮效能優化"""

    def test_batch_compression_performance(self, test_session):
        """測試批次壓縮效能"""
        manager = CompressionManager(test_session)

        # 創建多個分片記錄
        shards = []
        for i in range(20):
            shard = DataShard(
                table_name="market_daily",
                shard_key="date",
                shard_id=f"perf_shard_{i}",
                start_date=date(2024, 1, 1) + timedelta(days=i),
                end_date=date(2024, 1, 1) + timedelta(days=i),
                is_compressed=False,
                file_size_bytes=1024000
            )
            shards.append(shard)

        test_session.add_all(shards)
        test_session.commit()

        # 測試批次處理效能
        start_time = time.time()
        results = manager.auto_compress_old_data(
            strategy_name="time_based_snappy",
            dry_run=True
        )
        end_time = time.time()

        # 驗證結果
        assert len(results) == 20

        # 驗證處理時間合理
        processing_time = end_time - start_time
        assert processing_time < 2.0  # 應該在2秒內完成

    def test_memory_efficient_compression(self, test_session):
        """測試記憶體效率壓縮"""
        manager = CompressionManager(test_session)

        # 模擬大型資料集
        large_df = pd.DataFrame({
            'symbol': ['LARGE.TW'] * 10000,
            'date': [date(2024, 1, 1)] * 10000,
            'close': list(range(10000))
        })

        with patch('src.database.compression_manager.query_to_dataframe') as mock_query:
            mock_query.return_value = large_df

            with patch('src.database.compression_manager.os.path.getsize') as mock_size:
                mock_size.return_value = 1024000

                with patch.object(manager, '_save_compressed_parquet') as mock_save:
                    # 測試記憶體使用
                    import psutil
                    import os

                    process = psutil.Process(os.getpid())
                    memory_before = process.memory_info().rss

                    _, stats = manager.compress_table_data(
                        MarketDaily,
                        date(2024, 1, 1),
                        date(2024, 1, 2),
                        compression_type="snappy"
                    )

                    memory_after = process.memory_info().rss
                    memory_increase = memory_after - memory_before

                    # 驗證記憶體使用合理（不超過100MB）
                    assert memory_increase < 100 * 1024 * 1024
                    assert stats["row_count"] == 10000

    def test_concurrent_compression_safety(self, test_session):
        """測試並發壓縮安全性"""
        manager = CompressionManager(test_session)
        results = []
        errors = []

        def worker():
            try:
                # 模擬並發壓縮操作
                stats = manager.get_compression_statistics()
                results.append(stats)
            except Exception as e:
                errors.append(e)

        # 創建多個執行緒
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # 等待所有執行緒完成
        for thread in threads:
            thread.join()

        # 驗證沒有錯誤
        assert len(errors) == 0
        assert len(results) == 10


class TestCompressionIntegration:
    """測試壓縮管理器整合功能"""

    def test_integration_with_schema_fixes(self, test_session):
        """測試與修正後的 schema 整合"""
        manager = CompressionManager(test_session)

        # 創建分片記錄，測試 file_format 欄位
        shard = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="compression_integration_shard",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            is_compressed=True,
            compression="snappy"
        )

        test_session.add(shard)
        test_session.commit()

        # 驗證 file_format 預設值
        assert shard.file_format == 'parquet'

        # 測試壓縮統計功能
        stats = manager.get_compression_statistics()
        assert stats["compressed_shards"] == 1

    def test_compression_workflow_end_to_end(self, test_session):
        """測試完整的壓縮工作流程"""
        manager = CompressionManager(test_session)

        # 1. 註冊自定義策略
        custom_strategy = TimeBasedCompressionStrategy("zstd", min_age_days=1)
        manager.register_strategy("daily_zstd", custom_strategy)

        # 2. 創建未壓縮的分片
        shard = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="workflow_test_shard",
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() - timedelta(days=4),
            is_compressed=False,
            file_size_bytes=2048000
        )
        test_session.add(shard)
        test_session.commit()

        # 3. 測試自動壓縮（試運行）
        results = manager.auto_compress_old_data(
            strategy_name="daily_zstd",
            dry_run=True
        )

        # 4. 驗證結果
        assert len(results) == 1
        assert results[0]["shard_id"] == "workflow_test_shard"
        assert results[0]["status"] == "would_compress"

        # 5. 測試統計功能
        stats = manager.get_compression_statistics()
        assert stats["uncompressed_shards"] == 1
