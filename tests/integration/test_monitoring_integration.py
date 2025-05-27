"""
監控系統整合測試

測試 Phase 5.3 監控與告警系統各組件之間的整合，
包括 Prometheus 收集器、智能告警管理器、通知服務、
健康檢查器和 API 端點的協同工作。

遵循 Phase 5.3 測試標準，確保系統整合正常運行。
符合 Phase 7.2 程式碼品質標準：
- Pylint ≥9.0/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import time
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.monitoring.prometheus_collector import PrometheusCollector
from src.monitoring.intelligent_alert_manager import (
    IntelligentAlertManager,
    AlertSeverity,
)
from src.monitoring.health_checker import HealthChecker, HealthStatus
from src.monitoring.notification_services import NotificationServices
from src.api.routers.monitoring_v2 import router


class TestMonitoringSystemIntegration:
    """監控系統整合測試類。

    測試監控系統各組件之間的整合功能，包括：
    - Prometheus 收集器整合
    - 智能告警管理器整合
    - 健康檢查器整合
    - 通知服務整合
    - API 端點整合
    - 端到端監控流程

    符合 Phase 7.2 測試標準，確保系統整合正常運行。
    """

    @pytest.fixture
    def prometheus_collector(self) -> PrometheusCollector:
        """創建 Prometheus 收集器測試實例。

        Returns:
            PrometheusCollector: 配置為測試模式的 Prometheus 收集器實例

        Note:
            使用較短的收集間隔以加速測試執行
        """
        return PrometheusCollector(collection_interval=1)

    @pytest.fixture
    def alert_manager(self) -> IntelligentAlertManager:
        """創建智能告警管理器測試實例。

        Returns:
            IntelligentAlertManager: 配置為測試模式的告警管理器實例

        Note:
            模擬配置檔案不存在的情況，使用預設配置
        """
        with patch(
            "src.monitoring.intelligent_alert_manager.Path.exists", return_value=False
        ):
            return IntelligentAlertManager()

    @pytest.fixture
    def health_checker(self) -> HealthChecker:
        """創建健康檢查器測試實例。

        Returns:
            HealthChecker: 配置為測試模式的健康檢查器實例

        Note:
            模擬配置檔案不存在的情況，使用預設配置
        """
        with patch("src.monitoring.health_checker.Path.exists", return_value=False):
            return HealthChecker()

    @pytest.fixture
    def notification_service(self) -> NotificationServices:
        """創建通知服務測試實例。

        Returns:
            NotificationServices: 配置為測試模式的通知服務實例

        Note:
            模擬配置檔案不存在的情況，使用預設配置
        """
        with patch(
            "src.monitoring.notification_services.Path.exists", return_value=False
        ):
            return NotificationServices()

    @pytest.fixture
    def test_client(self) -> TestClient:
        """創建測試客戶端。

        Returns:
            TestClient: FastAPI 測試客戶端實例

        Note:
            包含監控路由器的完整 FastAPI 應用程式
        """
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_prometheus_collector_integration(
        self, prometheus_collector: PrometheusCollector
    ) -> None:
        """測試 Prometheus 收集器整合功能。

        Args:
            prometheus_collector: Prometheus 收集器測試實例

        Raises:
            AssertionError: 當收集器功能不符合預期時

        Note:
            測試收集器的啟動、指標記錄、指標獲取和停止功能
        """
        try:
            # 啟動收集器
            assert prometheus_collector.start_collection(), "收集器啟動失敗"

            # 記錄一些指標
            prometheus_collector.record_api_request("GET", "/api/test", 200, 0.123)
            prometheus_collector.record_trading_order("market", "filled", 0.05)
            prometheus_collector.update_strategy_metrics(
                "test_strategy", 1500.0, 1.8, 5.2
            )

            # 獲取指標
            metrics = prometheus_collector.get_metrics()
            assert isinstance(metrics, str), "指標格式應為字串"
            assert len(metrics) > 0, "指標內容不應為空"

            # 驗證指標內容
            assert "api_requests_total" in metrics, "缺少 API 請求指標"
            assert "trading_orders_total" in metrics, "缺少交易訂單指標"
            assert "strategy_pnl" in metrics, "缺少策略損益指標"

            # 停止收集器
            assert prometheus_collector.stop_collection(), "收集器停止失敗"

        except Exception as e:
            raise AssertionError(f"Prometheus 收集器整合測試失敗: {e}") from e

    def test_alert_manager_integration(
        self,
        alert_manager: IntelligentAlertManager,
        notification_service: NotificationServices,
    ) -> None:
        """測試智能告警管理器整合功能。

        Args:
            alert_manager: 智能告警管理器測試實例
            notification_service: 通知服務測試實例

        Raises:
            AssertionError: 當告警管理器功能不符合預期時

        Note:
            測試告警規則添加、評估、觸發和通知功能
        """
        try:
            # 模擬通知服務
            with patch.object(
                alert_manager, "notification_service", notification_service
            ):
                # 啟動告警管理器
                assert alert_manager.start(), "告警管理器啟動失敗"

                # 模擬高 CPU 使用率觸發告警
                with patch.object(
                    alert_manager, "_get_metric_value", return_value=95.0
                ):
                    # 添加一個測試規則
                    from src.monitoring.intelligent_alert_manager import AlertRule

                    rule = AlertRule(
                        id="test-cpu-rule",
                        name="High CPU Usage",
                        description="CPU usage too high",
                        metric_name="system_cpu_usage_percent",
                        operator=">",
                        threshold_value=80.0,
                        severity=AlertSeverity.CRITICAL,
                    )
                    alert_manager.rules[rule.id] = rule

                    # 執行評估
                    alert_manager._evaluate_alert_rules()

                    # 驗證告警被觸發
                    assert len(alert_manager.active_alerts) == 1, "告警未被觸發"

                    alert = list(alert_manager.active_alerts.values())[0]
                    assert alert.severity == AlertSeverity.CRITICAL, "告警嚴重性不正確"
                    assert alert.metric_value == 95.0, "告警指標值不正確"

                # 停止告警管理器
                assert alert_manager.stop(), "告警管理器停止失敗"

        except Exception as e:
            raise AssertionError(f"智能告警管理器整合測試失敗: {e}") from e

    def test_health_checker_integration(self, health_checker: HealthChecker) -> None:
        """測試健康檢查器整合功能。

        Args:
            health_checker: 健康檢查器測試實例

        Raises:
            AssertionError: 當健康檢查器功能不符合預期時

        Note:
            測試健康檢查器的啟動、檢查執行、狀態獲取和停止功能
        """
        try:
            # 啟動健康檢查器
            assert health_checker.start(), "健康檢查器啟動失敗"

            # 等待一次檢查完成
            time.sleep(0.2)

            # 手動執行檢查
            results = health_checker.run_all_checks()
            assert isinstance(results, dict), "健康檢查結果應為字典"
            assert len(results) > 0, "健康檢查結果不應為空"

            # 獲取整體健康狀態
            overall_health = health_checker.get_overall_health()
            assert overall_health.status in [
                HealthStatus.HEALTHY,
                HealthStatus.WARNING,
                HealthStatus.CRITICAL,
            ], f"健康狀態無效: {overall_health.status}"

            # 獲取健康摘要
            summary = health_checker.get_health_summary()
            assert "overall" in summary, "健康摘要缺少 overall 欄位"
            assert "checks" in summary, "健康摘要缺少 checks 欄位"
            assert "timestamp" in summary, "健康摘要缺少 timestamp 欄位"

            # 停止健康檢查器
            assert health_checker.stop(), "健康檢查器停止失敗"

        except Exception as e:
            raise AssertionError(f"健康檢查器整合測試失敗: {e}") from e

    def test_notification_service_integration(
        self, notification_service: NotificationServices
    ) -> None:
        """測試通知服務整合功能。

        Args:
            notification_service: 通知服務測試實例

        Raises:
            AssertionError: 當通知服務功能不符合預期時

        Note:
            測試通知服務的單一和多渠道通知功能
        """
        try:
            # 測試通知數據
            test_data = {
                "alert_id": "test-alert-123",
                "title": "Integration Test Alert",
                "message": "This is a test alert for integration testing",
                "severity": "WARNING",
                "metric_value": 85.0,
                "threshold_value": 80.0,
                "created_at": datetime.now().isoformat(),
            }

            # 測試 Webhook 通知（如果配置了）
            enabled_channels = notification_service.get_enabled_channels()

            if "webhook" in enabled_channels:
                with patch("requests.post") as mock_post:
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_post.return_value = mock_response

                    result = notification_service.send_notification(
                        "webhook", test_data
                    )
                    assert result, "Webhook 通知發送失敗"
                    mock_post.assert_called_once()

            # 測試多渠道發送
            if enabled_channels:
                results = notification_service.send_to_multiple_channels(
                    enabled_channels[:2], test_data  # 測試前兩個渠道
                )
                assert isinstance(results, dict), "多渠道發送結果應為字典"

        except Exception as e:
            raise AssertionError(f"通知服務整合測試失敗: {e}") from e

    # Note: 端到端測試、API 整合測試、WebSocket 測試、錯誤處理測試、
    # 效能測試和並發測試已移至專門的測試檔案：
    # - test_monitoring_e2e.py: 端到端和 API 整合測試
    # - test_monitoring_performance.py: 效能和並發測試
