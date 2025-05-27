# -*- coding: utf-8 -*-
"""
分片管理器測試模組

測試重構後的分片管理器的各項功能，包括：
- 自定義異常類別測試
- 型別提示和 Google Style Docstring 驗證
- 拆分後的輔助方法功能測試
- 執行緒安全機制測試
- 分片策略測試
- 自動分片創建
- 跨分片查詢
- 分片統計
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

from src.database.schema import Base, DataShard, MarketDaily, MarketMinute, MarketTick, init_db
from src.database.sharding_manager import (
    ShardingManager,
    TimeBasedShardingStrategy,
    SizeBasedShardingStrategy,
    ShardingError,
    ShardingConfigError,
    ShardingOperationError
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
def sharding_manager(test_session):
    """創建分片管理器實例"""
    return ShardingManager(test_session)


class TestTimeBasedShardingStrategy:
    """測試基於時間的分片策略"""

    def test_should_create_shard_no_existing_shard(self, test_session):
        """測試沒有現有分片時應該創建分片"""
        strategy = TimeBasedShardingStrategy(shard_interval_days=30)
        result = strategy.should_create_shard(MarketDaily, test_session)
        assert result is True

    def test_should_create_shard_with_old_shard(self, test_session):
        """測試有舊分片時應該創建新分片"""
        # 創建一個舊的分片記錄
        old_shard = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="test_shard",
            start_date=date.today() - timedelta(days=60),
            end_date=date.today() - timedelta(days=31)
        )
        test_session.add(old_shard)
        test_session.commit()

        strategy = TimeBasedShardingStrategy(shard_interval_days=30)
        result = strategy.should_create_shard(MarketDaily, test_session)
        assert result is True

    def test_should_not_create_shard_with_recent_shard(self, test_session):
        """測試有最近分片時不應該創建新分片"""
        # 創建一個最近的分片記錄
        recent_shard = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="recent_shard",
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=1)
        )
        test_session.add(recent_shard)
        test_session.commit()

        strategy = TimeBasedShardingStrategy(shard_interval_days=30)
        result = strategy.should_create_shard(MarketDaily, test_session)
        assert result is False

    def test_get_shard_parameters(self, test_session):
        """測試獲取分片參數"""
        strategy = TimeBasedShardingStrategy(shard_interval_days=30)
        params = strategy.get_shard_parameters(MarketDaily, test_session)

        assert "start_date" in params
        assert "end_date" in params
        assert "shard_key" in params
        assert params["shard_key"] == "date"

        # 檢查日期範圍
        date_diff = (params["end_date"] - params["start_date"]).days
        assert date_diff == 29  # 30天間隔 - 1


class TestSizeBasedShardingStrategy:
    """測試基於大小的分片策略"""

    def test_should_create_shard_large_table(self, test_session):
        """測試大表應該創建分片"""
        strategy = SizeBasedShardingStrategy(max_rows_per_shard=2)
        result = strategy.should_create_shard(MarketDaily, test_session)
        assert result is True  # 測試資料有3筆記錄，超過限制的2筆

    def test_should_not_create_shard_small_table(self, test_session):
        """測試小表不應該創建分片"""
        strategy = SizeBasedShardingStrategy(max_rows_per_shard=10)
        result = strategy.should_create_shard(MarketDaily, test_session)
        assert result is False  # 測試資料只有3筆記錄，未超過限制的10筆


class TestShardingManager:
    """測試分片管理器"""

    def test_register_strategy(self, sharding_manager):
        """測試註冊分片策略"""
        custom_strategy = TimeBasedShardingStrategy(shard_interval_days=7)
        sharding_manager.register_strategy("custom_weekly", custom_strategy)

        assert "custom_weekly" in sharding_manager.strategies
        assert sharding_manager.strategies["custom_weekly"] == custom_strategy

    @patch('src.database.sharding_manager.create_market_data_shard')
    def test_create_shard_if_needed_success(self, mock_create_shard, sharding_manager):
        """測試成功創建分片"""
        # 模擬創建分片的返回值
        mock_shard = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="test_shard_123",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        mock_create_shard.return_value = (mock_shard, "/path/to/shard.parquet")

        result = sharding_manager.create_shard_if_needed(MarketDaily, "time_based")

        assert result is not None
        shard, file_path = result
        assert shard.shard_id == "test_shard_123"
        assert file_path == "/path/to/shard.parquet"
        mock_create_shard.assert_called_once()

    def test_create_shard_if_needed_not_needed(self, sharding_manager, test_session):
        """測試不需要創建分片的情況"""
        # 創建一個最近的分片記錄
        recent_shard = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="recent_shard",
            start_date=date.today() - timedelta(days=10),
            end_date=date.today() - timedelta(days=1)
        )
        test_session.add(recent_shard)
        test_session.commit()

        result = sharding_manager.create_shard_if_needed(MarketDaily, "time_based")
        assert result is None

    def test_create_shard_if_needed_unknown_strategy(self, sharding_manager):
        """測試使用未知策略時拋出異常"""
        with pytest.raises(ValueError, match="未知的分片策略"):
            sharding_manager.create_shard_if_needed(MarketDaily, "unknown_strategy")

    def test_get_shards_for_query(self, sharding_manager, test_session):
        """測試獲取查詢所需的分片"""
        # 創建測試分片
        shard1 = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="shard_2024_01",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        shard2 = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="shard_2024_02",
            start_date=date(2024, 2, 1),
            end_date=date(2024, 2, 29)
        )
        shard3 = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="shard_2024_03",
            start_date=date(2024, 3, 1),
            end_date=date(2024, 3, 31)
        )

        test_session.add_all([shard1, shard2, shard3])
        test_session.commit()

        # 查詢跨越兩個分片的日期範圍
        shards = sharding_manager.get_shards_for_query(
            MarketDaily,
            date(2024, 1, 15),
            date(2024, 2, 15)
        )

        assert len(shards) == 2
        assert shards[0].shard_id == "shard_2024_01"
        assert shards[1].shard_id == "shard_2024_02"

    @patch('src.database.sharding_manager.load_from_shard')
    def test_query_across_shards(self, mock_load_shard, sharding_manager, test_session):
        """測試跨分片查詢"""
        # 創建測試分片
        shard1 = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="shard_2024_01",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        test_session.add(shard1)
        test_session.commit()

        # 模擬從分片讀取的資料
        mock_data = pd.DataFrame({
            'symbol': ['2330.TW', '2454.TW'],
            'date': [date(2024, 1, 1), date(2024, 1, 1)],
            'close': [100.0, 50.0]
        })
        mock_load_shard.return_value = mock_data

        result = sharding_manager.query_across_shards(
            MarketDaily,
            date(2024, 1, 1),
            date(2024, 1, 31)
        )

        assert not result.empty
        assert len(result) == 2
        assert 'symbol' in result.columns
        assert 'date' in result.columns
        assert 'close' in result.columns

    def test_get_shard_statistics(self, sharding_manager, test_session):
        """測試獲取分片統計"""
        # 創建測試分片
        shard1 = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="shard_1",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            row_count=1000,
            file_size_bytes=1024000
        )
        shard2 = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="shard_2",
            start_date=date(2024, 2, 1),
            end_date=date(2024, 2, 29),
            row_count=1200,
            file_size_bytes=1228800
        )

        test_session.add_all([shard1, shard2])
        test_session.commit()

        # 測試特定表的統計
        stats = sharding_manager.get_shard_statistics("market_daily")

        assert stats["table_name"] == "market_daily"
        assert stats["shard_count"] == 2
        assert stats["total_rows"] == 2200
        assert stats["total_size_bytes"] == 2252800
        assert len(stats["shards"]) == 2

        # 測試所有表的統計
        all_stats = sharding_manager.get_shard_statistics()
        assert "market_daily" in all_stats
        assert all_stats["market_daily"]["shard_count"] == 2


class TestShardingExceptions:
    """測試分片管理器的異常處理"""

    def test_sharding_config_error_invalid_session(self):
        """測試無效會話配置錯誤"""
        with pytest.raises(ShardingConfigError, match="SQLAlchemy 會話不能為 None"):
            ShardingManager(None)

    def test_sharding_operation_error_invalid_strategy(self, test_session):
        """測試無效策略操作錯誤"""
        manager = ShardingManager(test_session)
        with pytest.raises(ShardingOperationError, match="未知的分片策略"):
            manager.create_shard_if_needed(MarketDaily, "invalid_strategy")

    def test_sharding_config_error_invalid_table_class(self, test_session):
        """測試無效表類別配置錯誤"""
        manager = ShardingManager(test_session)
        with pytest.raises(ShardingConfigError, match="表類別不能為 None"):
            manager.create_shard_if_needed(None, "time_based")

    def test_exception_chaining(self, test_session):
        """測試異常鏈追蹤機制"""
        manager = ShardingManager(test_session)

        # 模擬內部異常
        with patch('src.database.sharding_manager.create_market_data_shard') as mock_create:
            mock_create.side_effect = Exception("內部錯誤")

            with pytest.raises(ShardingOperationError) as exc_info:
                manager.create_shard_if_needed(MarketDaily, "time_based")

            # 驗證異常鏈
            assert exc_info.value.__cause__ is not None
            assert "內部錯誤" in str(exc_info.value.__cause__)


class TestShardingManagerRefactored:
    """測試重構後的分片管理器功能"""

    def test_type_hints_validation(self, test_session):
        """測試型別提示驗證"""
        import inspect
        from src.database.sharding_manager import ShardingManager

        # 檢查 __init__ 方法的型別提示
        init_signature = inspect.signature(ShardingManager.__init__)
        assert init_signature.parameters['session'].annotation is not None

        # 檢查其他方法的型別提示
        create_signature = inspect.signature(ShardingManager.create_shard_if_needed)
        assert create_signature.return_annotation is not None

    def test_google_style_docstring(self, test_session):
        """測試 Google Style Docstring"""
        manager = ShardingManager(test_session)

        # 檢查類別文檔
        assert manager.__class__.__doc__ is not None
        assert "分片管理器" in manager.__class__.__doc__

        # 檢查方法文檔
        assert manager.create_shard_if_needed.__doc__ is not None
        assert "Args:" in manager.create_shard_if_needed.__doc__
        assert "Returns:" in manager.create_shard_if_needed.__doc__

    def test_thread_safety(self, test_session):
        """測試執行緒安全機制"""
        manager = ShardingManager(test_session)
        results = []
        errors = []

        def worker():
            try:
                # 模擬並發操作
                result = manager.get_shard_statistics("market_daily")
                results.append(result)
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

    def test_auxiliary_methods(self, test_session):
        """測試拆分後的輔助方法"""
        manager = ShardingManager(test_session)

        # 測試 _validate_inputs 方法
        with pytest.raises(ShardingConfigError):
            manager._validate_inputs(None, "time_based")

        with pytest.raises(ShardingConfigError):
            manager._validate_inputs(MarketDaily, "")

        # 正常情況不應該拋出異常
        try:
            manager._validate_inputs(MarketDaily, "time_based")
        except Exception:
            pytest.fail("_validate_inputs 不應該拋出異常")

    def test_performance_optimization(self, test_session):
        """測試效能優化功能"""
        manager = ShardingManager(test_session)

        # 創建多個分片記錄
        shards = []
        for i in range(10):
            shard = DataShard(
                table_name="market_daily",
                shard_key="date",
                shard_id=f"shard_{i}",
                start_date=date(2024, 1, 1) + timedelta(days=i*30),
                end_date=date(2024, 1, 31) + timedelta(days=i*30),
                row_count=1000,
                file_size_bytes=1024000
            )
            shards.append(shard)

        test_session.add_all(shards)
        test_session.commit()

        # 測試批次查詢效能
        start_time = time.time()
        stats = manager.get_shard_statistics("market_daily")
        end_time = time.time()

        # 驗證結果
        assert stats["shard_count"] == 10
        assert stats["total_rows"] == 10000

        # 驗證查詢時間合理（應該很快）
        assert (end_time - start_time) < 1.0  # 應該在1秒內完成

    def test_error_recovery(self, test_session):
        """測試錯誤恢復機制"""
        manager = ShardingManager(test_session)

        # 模擬資料庫連接錯誤
        with patch.object(test_session, 'query') as mock_query:
            mock_query.side_effect = Exception("資料庫連接錯誤")

            with pytest.raises(ShardingOperationError) as exc_info:
                manager.get_shard_statistics("market_daily")

            # 驗證錯誤訊息包含有用資訊
            assert "獲取分片統計時發生錯誤" in str(exc_info.value)
            assert exc_info.value.__cause__ is not None


class TestShardingIntegration:
    """測試分片管理器整合功能"""

    def test_integration_with_schema_fixes(self, test_session):
        """測試與修正後的 schema 整合"""
        manager = ShardingManager(test_session)

        # 創建分片記錄，測試 file_format 預設值
        shard = DataShard(
            table_name="market_daily",
            shard_key="date",
            shard_id="test_integration_shard",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )

        test_session.add(shard)
        test_session.commit()

        # 驗證 file_format 預設值
        assert shard.file_format == 'parquet'

        # 測試查詢功能
        stats = manager.get_shard_statistics("market_daily")
        assert stats["shard_count"] == 1

    def test_multiple_table_types(self, test_session):
        """測試多種表類型支援"""
        manager = ShardingManager(test_session)

        # 測試不同表類型的分片策略
        table_types = [MarketDaily, MarketMinute, MarketTick]

        for table_type in table_types:
            try:
                # 應該能夠處理不同的表類型
                result = manager.create_shard_if_needed(table_type, "time_based")
                # 由於沒有實際資料，可能返回 None，但不應該拋出異常
            except Exception as e:
                pytest.fail(f"處理 {table_type.__name__} 時不應該拋出異常: {e}")

    def test_comprehensive_workflow(self, test_session):
        """測試完整的工作流程"""
        manager = ShardingManager(test_session)

        # 1. 註冊自定義策略
        custom_strategy = TimeBasedShardingStrategy(shard_interval_days=7)
        manager.register_strategy("weekly", custom_strategy)

        # 2. 檢查策略是否註冊成功
        assert "weekly" in manager.strategies

        # 3. 創建測試資料
        test_data = MarketDaily(
            symbol="TEST.TW",
            date=date(2024, 1, 1),
            open=100.0,
            high=105.0,
            low=98.0,
            close=103.0,
            volume=1000000
        )
        test_session.add(test_data)
        test_session.commit()

        # 4. 測試分片創建（模擬）
        with patch('src.database.sharding_manager.create_market_data_shard') as mock_create:
            mock_shard = DataShard(
                table_name="market_daily",
                shard_key="date",
                shard_id="weekly_shard_001",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 7)
            )
            mock_create.return_value = (mock_shard, "/path/to/weekly_shard.parquet")

            result = manager.create_shard_if_needed(MarketDaily, "weekly")
            assert result is not None

        # 5. 測試統計功能
        stats = manager.get_shard_statistics()
        assert isinstance(stats, dict)
