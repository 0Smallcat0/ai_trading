# -*- coding: utf-8 -*-
"""
整合測試模組

測試多個管理器協同工作，包括：
- 完整的資料流程：分片 → 壓縮 → 校驗 → 查詢
- 修正後的資料庫 schema 與所有模組的相容性測試
- DataShard.file_format 欄位的預設值和功能測試
- 端到端功能驗證
"""

import os
import tempfile
import time
from datetime import date, timedelta
from unittest.mock import patch

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.schema import DataShard, MarketDaily, init_db
from src.database.sharding_manager import ShardingManager
from src.database.compression_manager import CompressionManager
from src.database.checksum_manager import ChecksumManager
from src.database.database_manager import DatabaseManager
from src.database.parquet_utils import (
    save_to_parquet,
    read_from_parquet,
    create_market_data_shard,
    load_from_shard,
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
    test_data = []
    for i in range(10):
        data = MarketDaily(
            symbol="2330.TW",
            date=date(2024, 1, 1) + timedelta(days=i),
            open=100.0 + i,
            high=105.0 + i,
            low=98.0 + i,
            close=103.0 + i,
            volume=1000000 + i * 10000,
        )
        test_data.append(data)

    for data in test_data:
        session.add(data)
    session.commit()

    yield session
    session.close()


@pytest.fixture
def temp_dir():
    """創建臨時目錄"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


class TestSchemaIntegration:
    """測試與修正後的 schema 整合"""

    def test_data_shard_file_format_default(self, test_session):
        """測試 DataShard.file_format 欄位預設值"""
        # 創建分片記錄
        shard = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="test_default_format",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        test_session.add(shard)
        test_session.commit()

        # 驗證預設值
        assert shard.file_format == "parquet"

        # 從資料庫重新查詢驗證
        queried_shard = (
            test_session.query(DataShard)
            .filter_by(shard_id="test_default_format")
            .first()
        )
        assert queried_shard.file_format == "parquet"

    def test_all_managers_with_schema(self, test_session):
        """測試所有管理器與修正後的 schema 相容性"""
        # 測試分片管理器
        sharding_manager = ShardingManager(test_session)
        sharding_stats = sharding_manager.get_shard_statistics()
        assert isinstance(sharding_stats, dict)

        # 測試壓縮管理器
        compression_manager = CompressionManager(test_session)
        compression_stats = compression_manager.get_compression_statistics()
        assert isinstance(compression_stats, dict)

        # 測試校驗管理器
        checksum_manager = ChecksumManager(test_session)
        checksum_stats = checksum_manager.get_checksum_statistics()
        assert isinstance(checksum_stats, dict)

        # 測試統一資料庫管理器
        database_manager = DatabaseManager(test_session)
        db_status = database_manager.get_database_status()
        assert "sharding_stats" in db_status
        assert "compression_stats" in db_status
        assert "integrity_stats" in db_status


class TestDataFlowIntegration:
    """測試完整的資料流程整合"""

    def test_complete_data_workflow(self, test_session, temp_dir):
        """測試完整的資料工作流程：分片 → 壓縮 → 校驗 → 查詢"""
        # 1. 創建分片
        with patch("src.database.parquet_utils.DATA_DIR", temp_dir):
            with patch("src.database.parquet_utils.save_to_parquet") as mock_save:
                mock_save.return_value = os.path.join(temp_dir, "test_shard.parquet")

                with patch("os.path.getsize") as mock_size:
                    mock_size.return_value = 2048

                    shard, file_path = create_market_data_shard(
                        test_session,
                        MarketDaily,
                        date(2024, 1, 1),
                        date(2024, 1, 5),
                        compression="snappy",
                    )

                    # 驗證分片創建
                    assert shard.table_name == "market_daily"
                    assert shard.file_format == "parquet"
                    assert shard.is_compressed is True
                    assert shard.compression == "snappy"

        # 2. 測試壓縮管理
        compression_manager = CompressionManager(test_session)
        compression_stats = compression_manager.get_compression_statistics()
        assert compression_stats["compressed_shards"] >= 1

        # 3. 測試校驗管理
        checksum_manager = ChecksumManager(test_session)

        # 創建校驗記錄
        checksum_result = checksum_manager.create_checksum(
            table_name="market_daily",
            record_id=shard.id,
            data={"test": "data"},
            strategy_name="md5",
        )
        assert checksum_result is not None

        # 4. 測試查詢功能
        sharding_manager = ShardingManager(test_session)
        shard_stats = sharding_manager.get_shard_statistics("market_daily")
        assert shard_stats["shard_count"] >= 1

        # 5. 測試統一管理器
        database_manager = DatabaseManager(test_session)
        status = database_manager.get_database_status()

        assert status["sharding_stats"]["market_daily"]["shard_count"] >= 1
        assert status["compression_stats"]["compressed_shards"] >= 1
        assert status["integrity_stats"]["total_checksums"] >= 1

    def test_parquet_arrow_integration(self, test_session, temp_dir):
        """測試 Parquet 和 Arrow 格式整合"""
        # 創建測試資料
        test_df = pd.DataFrame(
            {
                "symbol": ["TEST.TW"] * 5,
                "date": [date(2024, 1, i) for i in range(1, 6)],
                "close": [100.0 + i for i in range(5)],
                "volume": [1000000 + i * 10000 for i in range(5)],
            }
        )

        # 1. 測試 Parquet 格式
        parquet_path = os.path.join(temp_dir, "test_data.parquet")
        save_to_parquet(test_df, parquet_path, compression="snappy")

        parquet_shard = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="parquet_integration_shard",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 5),
            file_path=parquet_path,
            file_format="parquet",
            compression="snappy",
            is_compressed=True,
        )

        test_session.add(parquet_shard)
        test_session.commit()

        # 2. 測試 Arrow 格式
        from src.database.parquet_utils import save_to_arrow

        arrow_path = os.path.join(temp_dir, "test_data.feather")
        save_to_arrow(test_df, arrow_path, compression="lz4")

        arrow_shard = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="arrow_integration_shard",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 5),
            file_path=arrow_path,
            file_format="arrow",
            compression="lz4",
            is_compressed=True,
        )

        test_session.add(arrow_shard)
        test_session.commit()

        # 3. 測試載入功能
        parquet_df = load_from_shard(test_session, "parquet_integration_shard")
        arrow_df = load_from_shard(test_session, "arrow_integration_shard")

        # 驗證資料一致性
        assert len(parquet_df) == len(arrow_df) == 5
        assert parquet_df["symbol"].tolist() == arrow_df["symbol"].tolist()
        assert parquet_df["close"].tolist() == arrow_df["close"].tolist()


class TestManagerCoordination:
    """測試管理器協調功能"""

    def test_database_manager_coordination(self, test_session, temp_dir):
        """測試資料庫管理器協調所有子管理器"""
        database_manager = DatabaseManager(test_session)

        # 創建測試分片
        with patch("src.database.parquet_utils.DATA_DIR", temp_dir):
            shard = DataShard(
                table_name="market_daily",
                shard_key="date",
                shard_id="coordination_test_shard",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 10),
                file_path=os.path.join(temp_dir, "coordination_test.parquet"),
                file_format="parquet",
                compression="snappy",
                is_compressed=True,
                row_count=10,
                file_size_bytes=2048,
            )

            test_session.add(shard)
            test_session.commit()

        # 測試狀態報告協調
        status = database_manager.get_database_status()

        # 驗證所有子管理器的統計都包含在內
        assert "sharding_stats" in status
        assert "compression_stats" in status
        assert "integrity_stats" in status

        # 驗證統計資料的一致性
        sharding_stats = status["sharding_stats"]
        compression_stats = status["compression_stats"]

        if "market_daily" in sharding_stats:
            assert sharding_stats["market_daily"]["shard_count"] >= 1

        assert compression_stats["compressed_shards"] >= 1

        # 測試維護任務協調
        maintenance_result = database_manager.perform_maintenance(
            auto_shard=False, auto_compress=False, verify_integrity=False
        )

        assert "start_time" in maintenance_result
        assert "end_time" in maintenance_result
        assert "duration_seconds" in maintenance_result
        assert "tasks_performed" in maintenance_result

    def test_concurrent_manager_operations(self, test_session):
        """測試並發管理器操作"""
        import threading

        results = []
        errors = []

        def worker(manager_class):
            try:
                manager = manager_class(test_session)
                if hasattr(manager, "get_shard_statistics"):
                    result = manager.get_shard_statistics()
                elif hasattr(manager, "get_compression_statistics"):
                    result = manager.get_compression_statistics()
                elif hasattr(manager, "get_checksum_statistics"):
                    result = manager.get_checksum_statistics()
                elif hasattr(manager, "get_database_status"):
                    result = manager.get_database_status()
                else:
                    result = {}
                results.append(result)
            except Exception as e:
                errors.append(e)

        # 創建多個管理器執行緒
        managers = [
            ShardingManager,
            CompressionManager,
            ChecksumManager,
            DatabaseManager,
        ]
        threads = []

        for manager_class in managers:
            thread = threading.Thread(target=worker, args=(manager_class,))
            threads.append(thread)
            thread.start()

        # 等待所有執行緒完成
        for thread in threads:
            thread.join()

        # 驗證結果
        assert len(errors) == 0
        assert len(results) == 4
        assert all(isinstance(result, dict) for result in results)


class TestPerformanceIntegration:
    """測試整合效能"""

    def test_end_to_end_performance(self, test_session, temp_dir):
        """測試端到端效能"""
        # 創建大量測試資料
        large_data = []
        for i in range(100):
            data = MarketDaily(
                symbol=f"TEST{i:03d}.TW",
                date=date(2024, 1, 1) + timedelta(days=i % 30),
                open=100.0 + i,
                high=105.0 + i,
                low=98.0 + i,
                close=103.0 + i,
                volume=1000000 + i * 10000,
            )
            large_data.append(data)

        test_session.add_all(large_data)
        test_session.commit()

        # 測試統一管理器效能
        database_manager = DatabaseManager(test_session)

        start_time = time.time()
        status = database_manager.get_database_status()
        status_time = time.time() - start_time

        start_time = time.time()
        maintenance_result = database_manager.perform_maintenance(
            auto_shard=False, auto_compress=False, verify_integrity=False
        )
        maintenance_time = time.time() - start_time

        # 驗證效能
        assert status_time < 2.0  # 狀態報告應該在2秒內完成
        assert maintenance_time < 1.0  # 維護任務應該在1秒內完成

        # 驗證結果完整性
        assert "sharding_stats" in status
        assert "compression_stats" in status
        assert "integrity_stats" in status
        assert "duration_seconds" in maintenance_result

    def test_scalability_with_multiple_shards(self, test_session, temp_dir):
        """測試多分片可擴展性"""
        # 創建多個分片記錄
        shards = []
        for i in range(50):
            shard = DataShard(
                table_name="market_daily",
                shard_key="date",
                shard_id=f"scalability_shard_{i:03d}",
                start_date=date(2024, 1, 1) + timedelta(days=i),
                end_date=date(2024, 1, 1) + timedelta(days=i),
                file_path=os.path.join(temp_dir, f"shard_{i:03d}.parquet"),
                file_format="parquet",
                compression="snappy",
                is_compressed=True,
                row_count=1000,
                file_size_bytes=1024000,
            )
            shards.append(shard)

        test_session.add_all(shards)
        test_session.commit()

        # 測試各管理器的可擴展性
        managers = [
            ShardingManager(test_session),
            CompressionManager(test_session),
            ChecksumManager(test_session),
            DatabaseManager(test_session),
        ]

        for manager in managers:
            start_time = time.time()

            if hasattr(manager, "get_shard_statistics"):
                stats = manager.get_shard_statistics()
            elif hasattr(manager, "get_compression_statistics"):
                stats = manager.get_compression_statistics()
            elif hasattr(manager, "get_checksum_statistics"):
                stats = manager.get_checksum_statistics()
            elif hasattr(manager, "get_database_status"):
                stats = manager.get_database_status()

            processing_time = time.time() - start_time

            # 驗證效能（即使有50個分片，也應該在合理時間內完成）
            assert processing_time < 3.0
            assert isinstance(stats, dict)
