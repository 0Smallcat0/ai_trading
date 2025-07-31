"""
測試背壓控制和故障轉移功能

此測試文件驗證：
1. WebSocket 背壓控制機制
2. 資料源故障轉移功能
3. 健康檢查和自動恢復
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch
from src.core.websocket_client import WebSocketClient, BackpressureController
from src.core.data_source_failover import DataSourceFailoverManager, DataSourceHealth
from src.core.data_ingest import DataIngestionManager


class TestBackpressureController:
    """測試背壓控制器"""

    def test_backpressure_controller_initialization(self):
        """測試背壓控制器初始化"""
        controller = BackpressureController(
            max_queue_size=100, warning_threshold=0.8, critical_threshold=0.95
        )

        assert controller.max_queue_size == 100
        assert controller.warning_threshold == 0.8
        assert controller.critical_threshold == 0.95
        assert controller.current_interval == controller.min_interval

    def test_backpressure_adjustment_warning(self):
        """測試警告狀態下的背壓調節"""
        controller = BackpressureController(max_queue_size=100)

        # 模擬警告狀態（隊列使用率 80%）
        queue_size = 80
        interval = controller.check_and_adjust(queue_size)

        # 應該增加處理間隔
        assert interval > controller.min_interval
        assert controller.stats["total_adjustments"] == 1

    def test_backpressure_adjustment_critical(self):
        """測試臨界狀態下的背壓調節"""
        controller = BackpressureController(max_queue_size=100)

        # 模擬臨界狀態（隊列使用率 95%）
        queue_size = 95
        interval = controller.check_and_adjust(queue_size)

        # 應該大幅增加處理間隔
        assert interval > controller.min_interval
        assert controller.stats["backpressure_events"] == 1

    def test_backpressure_recovery(self):
        """測試背壓恢復"""
        controller = BackpressureController(max_queue_size=100)

        # 先觸發背壓
        controller.check_and_adjust(95)
        high_interval = controller.current_interval

        # 然後恢復到低使用率
        controller.check_and_adjust(10)
        low_interval = controller.current_interval

        # 處理間隔應該減少
        assert low_interval < high_interval


class TestWebSocketClientBackpressure:
    """測試 WebSocket 客戶端背壓控制"""

    def test_websocket_client_with_backpressure(self):
        """測試啟用背壓控制的 WebSocket 客戶端"""
        client = WebSocketClient(
            url="ws://test.com",
            enable_backpressure=True,
            backpressure_config={"warning_threshold": 0.7, "critical_threshold": 0.9},
        )

        assert client.enable_backpressure is True
        assert client.backpressure_controller is not None
        assert client.backpressure_controller.warning_threshold == 0.7

    def test_websocket_client_without_backpressure(self):
        """測試未啟用背壓控制的 WebSocket 客戶端"""
        client = WebSocketClient(url="ws://test.com", enable_backpressure=False)

        assert client.enable_backpressure is False
        assert client.backpressure_controller is None

    @patch("websocket.WebSocketApp")
    def test_message_processing_with_backpressure(self, mock_websocket):
        """測試帶背壓控制的消息處理"""
        client = WebSocketClient(
            url="ws://test.com", enable_backpressure=True, max_queue_size=10
        )

        # 模擬收到消息
        for i in range(5):
            client._on_message(None, f"message_{i}")

        # 檢查統計信息
        stats = client.get_stats()
        assert stats["messages_received"] == 5
        assert "backpressure" in stats


class TestDataSourceHealth:
    """測試資料源健康狀態"""

    def test_data_source_health_initialization(self):
        """測試資料源健康狀態初始化"""
        health = DataSourceHealth("test_source")

        assert health.source_name == "test_source"
        assert health.is_healthy is True
        assert health.consecutive_failures == 0
        assert health.total_requests == 0

    def test_record_success(self):
        """測試記錄成功請求"""
        health = DataSourceHealth("test_source")

        health.record_success(0.1)

        assert health.total_requests == 1
        assert health.successful_requests == 1
        assert health.consecutive_failures == 0
        assert health.get_success_rate() == 1.0

    def test_record_failure(self):
        """測試記錄失敗請求"""
        health = DataSourceHealth("test_source")

        health.record_failure("Test error")

        assert health.total_requests == 1
        assert health.failed_requests == 1
        assert health.consecutive_failures == 1
        assert health.get_success_rate() == 0.0

    def test_unhealthy_detection(self):
        """測試不健康狀態檢測"""
        health = DataSourceHealth("test_source")

        # 記錄多次失敗
        for i in range(3):
            health.record_failure(f"Error {i}")

        assert health.is_considered_unhealthy(max_consecutive_failures=3) is True
        assert health.consecutive_failures == 3


class TestDataSourceFailoverManager:
    """測試資料源故障轉移管理器"""

    def test_failover_manager_initialization(self):
        """測試故障轉移管理器初始化"""
        manager = DataSourceFailoverManager()

        assert manager.health_check_interval == 30.0
        assert manager.max_consecutive_failures == 3
        assert len(manager.data_sources) == 0
        assert len(manager.source_priorities) == 0

    def test_register_data_source(self):
        """測試註冊資料源"""
        manager = DataSourceFailoverManager()
        mock_adapter = Mock()

        manager.register_data_source(
            source_name="test_source", adapter=mock_adapter, priority_groups=["price"]
        )

        assert "test_source" in manager.data_sources
        assert "test_source" in manager.health_status
        assert "price" in manager.source_priorities
        assert "test_source" in manager.source_priorities["price"]

    def test_set_priority_order(self):
        """測試設定優先級順序"""
        manager = DataSourceFailoverManager()
        mock_adapter1 = Mock()
        mock_adapter2 = Mock()

        # 註冊兩個資料源
        manager.register_data_source("source1", mock_adapter1)
        manager.register_data_source("source2", mock_adapter2)

        # 設定優先級
        manager.set_priority_order("price", ["source1", "source2"])

        assert manager.source_priorities["price"] == ["source1", "source2"]

    def test_get_best_source(self):
        """測試獲取最佳資料源"""
        manager = DataSourceFailoverManager()
        mock_adapter1 = Mock()
        mock_adapter2 = Mock()

        # 註冊資料源
        manager.register_data_source("source1", mock_adapter1)
        manager.register_data_source("source2", mock_adapter2)
        manager.set_priority_order("price", ["source1", "source2"])

        # 獲取最佳資料源
        best_source = manager.get_best_source("price")
        assert best_source == "source1"

    def test_record_request_result(self):
        """測試記錄請求結果"""
        manager = DataSourceFailoverManager()
        mock_adapter = Mock()

        manager.register_data_source("test_source", mock_adapter)

        # 記錄成功
        manager.record_request_result("test_source", True, 0.1)
        health = manager.health_status["test_source"]
        assert health.total_requests == 1
        assert health.successful_requests == 1

        # 記錄失敗
        manager.record_request_result("test_source", False, 0.0, "Test error")
        assert health.total_requests == 2
        assert health.failed_requests == 1

    def test_force_failover(self):
        """測試強制故障轉移"""
        manager = DataSourceFailoverManager()
        mock_adapter = Mock()

        manager.register_data_source("test_source", mock_adapter)

        # 強制故障轉移
        manager.force_failover("test_source", "Test failover")

        health = manager.health_status["test_source"]
        assert health.is_healthy is False
        assert "test_source" in manager.circuit_breakers
        assert manager.stats["total_failovers"] == 1

    def test_force_recovery(self):
        """測試強制恢復"""
        manager = DataSourceFailoverManager()
        mock_adapter = Mock()

        manager.register_data_source("test_source", mock_adapter)

        # 先故障轉移
        manager.force_failover("test_source")

        # 然後恢復
        manager.force_recovery("test_source", "Test recovery")

        health = manager.health_status["test_source"]
        assert health.is_healthy is True
        assert health.consecutive_failures == 0
        assert "test_source" not in manager.circuit_breakers
        assert manager.stats["total_recoveries"] == 1


class TestDataIngestionManagerIntegration:
    """測試資料擷取管理器整合功能"""

    @patch("src.data_sources.yahoo_adapter.YahooFinanceAdapter")
    @patch("src.data_sources.broker_adapter.SimulatedBrokerAdapter")
    def test_data_ingestion_manager_with_failover(self, mock_broker, mock_yahoo):
        """測試帶故障轉移的資料擷取管理器"""
        # 創建模擬適配器
        mock_yahoo_instance = Mock()
        mock_broker_instance = Mock()
        mock_yahoo.return_value = mock_yahoo_instance
        mock_broker.return_value = mock_broker_instance

        # 創建管理器
        manager = DataIngestionManager()

        # 檢查故障轉移管理器是否正確初始化
        assert manager.failover_manager is not None
        assert len(manager.failover_manager.data_sources) > 0

        # 檢查健康狀態摘要
        summary = manager.get_health_summary()
        assert "total_sources" in summary
        assert "healthy_sources" in summary

        # 測試強制故障轉移
        manager.force_failover("yahoo", "Test failover")
        summary = manager.get_health_summary()
        assert "yahoo" not in summary["healthy_sources"]

        # 測試強制恢復
        manager.force_recovery("yahoo", "Test recovery")
        summary = manager.get_health_summary()
        assert "yahoo" in summary["healthy_sources"]

        # 清理
        manager.close()


if __name__ == "__main__":
    pytest.main([__file__])
