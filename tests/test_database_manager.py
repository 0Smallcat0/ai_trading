# -*- coding: utf-8 -*-
"""
資料庫管理器測試模組

測試統一的資料庫管理介面，包括：
- DatabaseManager 整合所有子管理器的功能
- 統一異常處理機制測試
- 維護任務和狀態報告功能測試
- 查詢效能優化功能測試
"""

import threading
import time
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.schema import DataShard, MarketDaily, MarketType, init_db
from src.database.database_manager import (
    DatabaseManager,
    DatabaseError,
    DatabaseConfigError,
    DatabaseOperationError,
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
            market_type=MarketType.STOCK,
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
            volume=1000000,
        ),
        MarketDaily(
            symbol="2330.TW",
            date=date(2024, 1, 2),
            market_type=MarketType.STOCK,
            open=103.0,
            high=108.0,
            low=101.0,
            close=106.0,
            volume=1200000,
        ),
    ]

    for data in test_data:
        session.add(data)
    session.commit()

    yield session
    session.close()


@pytest.fixture
def database_manager(test_session):
    """創建資料庫管理器實例"""
    return DatabaseManager(test_session)


class TestDatabaseManagerExceptions:
    """測試資料庫管理器的異常處理"""

    def test_database_config_error_invalid_session(self):
        """測試無效會話配置錯誤"""
        with pytest.raises(DatabaseConfigError, match="SQLAlchemy 會話不能為 None"):
            DatabaseManager(None)

    def test_exception_chaining(self, test_session):
        """測試異常鏈追蹤機制"""
        manager = DatabaseManager(test_session)

        # 模擬內部異常
        with patch.object(
            manager.sharding_manager, "get_shard_statistics"
        ) as mock_stats:
            mock_stats.side_effect = Exception("內部錯誤")

            with pytest.raises(DatabaseOperationError) as exc_info:
                manager.get_database_status()

            # 驗證異常鏈
            assert exc_info.value.__cause__ is not None
            assert "內部錯誤" in str(exc_info.value.__cause__)


class TestDatabaseManagerIntegration:
    """測試資料庫管理器整合功能"""

    def test_manager_initialization(self, test_session):
        """測試管理器初始化"""
        manager = DatabaseManager(test_session)

        # 驗證所有子管理器都已初始化
        assert manager.sharding_manager is not None
        assert manager.compression_manager is not None
        assert manager.checksum_manager is not None

        # 驗證執行緒鎖已初始化
        assert manager.lock is not None

    def test_database_status_report(self, database_manager):
        """測試資料庫狀態報告"""
        status = database_manager.get_database_status()

        # 驗證狀態報告結構
        assert "timestamp" in status
        assert "sharding_stats" in status
        assert "compression_stats" in status
        assert "integrity_stats" in status

        # 驗證統計資料類型
        assert isinstance(status["sharding_stats"], dict)
        assert isinstance(status["compression_stats"], dict)
        assert isinstance(status["integrity_stats"], dict)

    def test_maintenance_tasks(self, database_manager):
        """測試維護任務"""
        # 測試不執行任何維護任務
        result = database_manager.perform_maintenance(
            auto_shard=False, auto_compress=False, verify_integrity=False
        )

        # 驗證維護結果結構
        assert "start_time" in result
        assert "end_time" in result
        assert "duration_seconds" in result
        assert "tasks_performed" in result
        assert "results" in result

        # 驗證沒有執行任務
        assert len(result["tasks_performed"]) == 0

    def test_scheduled_maintenance_config(self, database_manager):
        """測試排程維護配置"""
        config = database_manager.start_scheduled_maintenance(interval_hours=24)

        # 驗證配置結構
        assert "interval_hours" in config
        assert "status" in config
        assert "next_run" in config
        assert "tasks" in config

        # 驗證配置值
        assert config["interval_hours"] == 24
        assert config["status"] == "configured"

    def test_query_performance_optimization(self, database_manager):
        """測試查詢效能優化"""
        optimization = database_manager.optimize_query_performance(
            MarketDaily, date(2024, 1, 1), date(2024, 1, 31)
        )

        # 驗證優化結果結構
        assert "query_date_range_days" in optimization
        assert "recommendation" in optimization
        assert "estimated_shards" in optimization
        assert "performance_impact" in optimization

        # 驗證日期範圍計算
        assert optimization["query_date_range_days"] == 30

    def test_thread_safety(self, database_manager):
        """測試執行緒安全機制"""
        results = []
        errors = []

        def worker():
            try:
                # 模擬並發操作
                status = database_manager.get_database_status()
                results.append(status)
            except Exception as e:
                errors.append(e)

        # 創建多個執行緒
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # 等待所有執行緒完成
        for thread in threads:
            thread.join()

        # 驗證沒有錯誤
        assert len(errors) == 0
        assert len(results) == 5


class TestDatabaseManagerPerformance:
    """測試資料庫管理器效能"""

    def test_status_report_performance(self, database_manager, test_session):
        """測試狀態報告效能"""
        # 創建多個分片記錄
        shards = []
        for i in range(50):
            shard = DataShard(
                table_name="market_daily",
                shard_key="date",
                shard_id=f"perf_shard_{i}",
                start_date=date(2024, 1, 1) + timedelta(days=i),
                end_date=date(2024, 1, 1) + timedelta(days=i),
                row_count=1000,
                file_size_bytes=1024000,
            )
            shards.append(shard)

        test_session.add_all(shards)
        test_session.commit()

        # 測試狀態報告效能
        start_time = time.time()
        status = database_manager.get_database_status()
        end_time = time.time()

        # 驗證結果
        assert "sharding_stats" in status

        # 驗證處理時間合理（應該在1秒內完成）
        processing_time = end_time - start_time
        assert processing_time < 1.0

    def test_maintenance_performance(self, database_manager):
        """測試維護任務效能"""
        start_time = time.time()

        result = database_manager.perform_maintenance(
            auto_shard=False, auto_compress=False, verify_integrity=False
        )

        end_time = time.time()
        processing_time = end_time - start_time

        # 驗證維護任務快速完成
        assert processing_time < 0.5
        assert result["duration_seconds"] < 0.5


class TestDatabaseManagerWorkflow:
    """測試資料庫管理器完整工作流程"""

    def test_comprehensive_workflow(self, database_manager, test_session):
        """測試完整的資料庫管理工作流程"""
        # 1. 獲取初始狀態
        initial_status = database_manager.get_database_status()
        assert "timestamp" in initial_status

        # 2. 創建測試分片
        shard = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="workflow_test_shard",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            is_compressed=False,
            file_size_bytes=1024000,
        )
        test_session.add(shard)
        test_session.commit()

        # 3. 執行維護任務
        maintenance_result = database_manager.perform_maintenance(
            auto_shard=False, auto_compress=False, verify_integrity=False
        )
        assert "duration_seconds" in maintenance_result

        # 4. 配置排程維護
        schedule_config = database_manager.start_scheduled_maintenance(
            interval_hours=12
        )
        assert schedule_config["interval_hours"] == 12

        # 5. 優化查詢效能
        optimization = database_manager.optimize_query_performance(
            MarketDaily, date(2024, 1, 1), date(2024, 1, 15)
        )
        assert optimization["query_date_range_days"] == 14

        # 6. 獲取最終狀態
        final_status = database_manager.get_database_status()
        assert "sharding_stats" in final_status

        # 7. 關閉管理器
        database_manager.close()

    def test_integration_with_schema_fixes(self, database_manager, test_session):
        """測試與修正後的 schema 整合"""
        # 創建分片記錄，測試 file_format 預設值
        shard = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="schema_integration_shard",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        test_session.add(shard)
        test_session.commit()

        # 驗證 file_format 預設值
        assert shard.file_format == "parquet"

        # 測試狀態報告功能
        status = database_manager.get_database_status()
        assert "sharding_stats" in status

        # 驗證統計資料包含新分片
        sharding_stats = status["sharding_stats"]
        if "market_daily" in sharding_stats:
            assert sharding_stats["market_daily"]["shard_count"] >= 1
