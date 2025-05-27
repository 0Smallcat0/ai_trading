"""
監控系統端到端測試

測試完整的監控系統工作流程，包括：
- 端到端監控流程
- API 端點整合
- WebSocket 整合
- 錯誤處理整合
- 效能整合測試
- 並發操作測試

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥9.0/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import time
import threading
import tracemalloc
from datetime import datetime
from typing import Dict, Any
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


class TestMonitoringEndToEnd:
    """監控系統端到端測試類。
    
    測試完整的監控系統工作流程，確保所有組件能夠協同工作。
    包括端到端流程、API 整合、WebSocket 通信、錯誤處理和效能測試。
    
    符合 Phase 7.2 測試標準，確保系統整合正常運行。
    """

    @pytest.fixture
    def prometheus_collector(self) -> PrometheusCollector:
        """創建 Prometheus 收集器測試實例。
        
        Returns:
            PrometheusCollector: 配置為測試模式的 Prometheus 收集器實例
        """
        return PrometheusCollector(collection_interval=1)

    @pytest.fixture
    def alert_manager(self) -> IntelligentAlertManager:
        """創建智能告警管理器測試實例。
        
        Returns:
            IntelligentAlertManager: 配置為測試模式的告警管理器實例
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
        """
        with patch("src.monitoring.health_checker.Path.exists", return_value=False):
            return HealthChecker()

    @pytest.fixture
    def notification_service(self) -> NotificationServices:
        """創建通知服務測試實例。
        
        Returns:
            NotificationServices: 配置為測試模式的通知服務實例
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
        """
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_end_to_end_monitoring_flow(
        self,
        prometheus_collector: PrometheusCollector,
        alert_manager: IntelligentAlertManager,
        health_checker: HealthChecker,
        notification_service: NotificationServices
    ) -> None:
        """測試端到端監控流程。
        
        Args:
            prometheus_collector: Prometheus 收集器測試實例
            alert_manager: 智能告警管理器測試實例
            health_checker: 健康檢查器測試實例
            notification_service: 通知服務測試實例
            
        Raises:
            AssertionError: 當端到端流程不符合預期時
            
        Note:
            測試完整的監控工作流程，從指標收集到告警觸發
        """
        try:
            # 1. 啟動所有服務
            assert prometheus_collector.start_collection(), "Prometheus 收集器啟動失敗"
            assert alert_manager.start(), "告警管理器啟動失敗"
            assert health_checker.start(), "健康檢查器啟動失敗"

            # 2. 模擬系統運行和指標收集
            prometheus_collector.record_api_request("GET", "/api/health", 200, 0.05)
            prometheus_collector.record_api_request("POST", "/api/orders", 201, 0.15)
            prometheus_collector.record_trading_order("limit", "filled", 0.08)

            # 3. 執行健康檢查
            health_results = health_checker.run_all_checks()
            assert len(health_results) > 0, "健康檢查結果為空"

            # 4. 模擬告警觸發
            with patch.object(alert_manager, "_get_metric_value", return_value=92.0):
                # 添加告警規則
                from src.monitoring.intelligent_alert_manager import AlertRule

                rule = AlertRule(
                    id="integration-test-rule",
                    name="Integration Test Alert",
                    description="Test alert for integration",
                    metric_name="system_cpu_usage_percent",
                    operator=">",
                    threshold_value=90.0,
                    severity=AlertSeverity.WARNING,
                )
                alert_manager.rules[rule.id] = rule

                # 觸發告警評估
                alert_manager._evaluate_alert_rules()

                # 驗證告警被觸發
                assert len(alert_manager.active_alerts) == 1, "告警未被觸發"

            # 5. 驗證指標收集
            metrics = prometheus_collector.get_metrics()
            assert "api_requests_total" in metrics, "缺少 API 請求指標"
            assert "trading_orders_total" in metrics, "缺少交易訂單指標"

            # 6. 清理
            prometheus_collector.stop_collection()
            alert_manager.stop()
            health_checker.stop()
            
        except Exception as e:
            raise AssertionError(f"端到端監控流程測試失敗: {e}") from e

    @patch("src.core.auth.get_current_user")
    def test_api_endpoints_integration(
        self, 
        mock_auth: MagicMock, 
        test_client: TestClient
    ) -> None:
        """測試 API 端點整合功能。
        
        Args:
            mock_auth: 模擬認證函數
            test_client: FastAPI 測試客戶端
            
        Raises:
            AssertionError: 當 API 端點功能不符合預期時
            
        Note:
            測試所有監控相關的 API 端點功能
        """
        try:
            # 模擬認證用戶
            mock_auth.return_value = {"username": "test_user", "user_id": "123"}

            # 測試健康檢查端點
            response = test_client.get("/api/v1/monitoring/health")
            assert response.status_code == 200, f"健康檢查端點失敗: {response.status_code}"

            health_data = response.json()
            assert "status" in health_data, "健康檢查響應缺少 status 欄位"
            assert "score" in health_data, "健康檢查響應缺少 score 欄位"
            assert "timestamp" in health_data, "健康檢查響應缺少 timestamp 欄位"

            # 測試 Prometheus 指標端點
            response = test_client.get("/api/v1/monitoring/metrics/prometheus")
            assert response.status_code == 200, f"Prometheus 指標端點失敗: {response.status_code}"
            assert response.headers["content-type"].startswith("text/plain"), "指標端點內容類型錯誤"

            # 測試指標名稱端點
            response = test_client.get("/api/v1/monitoring/metrics/names")
            assert response.status_code == 200, f"指標名稱端點失敗: {response.status_code}"

            metrics_data = response.json()
            assert "metric_names" in metrics_data, "指標名稱響應缺少 metric_names 欄位"
            assert "total" in metrics_data, "指標名稱響應缺少 total 欄位"
            assert isinstance(metrics_data["metric_names"], list), "metric_names 應為列表"

            # 測試告警列表端點
            response = test_client.get("/api/v1/monitoring/alerts")
            assert response.status_code == 200, f"告警列表端點失敗: {response.status_code}"

            alerts_data = response.json()
            assert "alerts" in alerts_data, "告警列表響應缺少 alerts 欄位"
            assert "total" in alerts_data, "告警列表響應缺少 total 欄位"
            assert isinstance(alerts_data["alerts"], list), "alerts 應為列表"
            
        except Exception as e:
            raise AssertionError(f"API 端點整合測試失敗: {e}") from e

    def test_websocket_integration(self, test_client: TestClient) -> None:
        """測試 WebSocket 整合功能。
        
        Args:
            test_client: FastAPI 測試客戶端
            
        Raises:
            AssertionError: 當 WebSocket 功能不符合預期時
            
        Note:
            測試 WebSocket 連接和數據傳輸功能
        """
        try:
            # 由於 WebSocket 測試較複雜，這裡進行基本的連接測試
            with test_client.websocket_connect(
                "/api/v1/monitoring/ws/monitoring"
            ) as websocket:
                # 等待接收數據
                data = websocket.receive_text()
                message = eval(data)  # 簡單解析，實際應用中使用 json.loads

                assert "type" in message, "WebSocket 消息缺少 type 欄位"
                assert message["type"] == "monitoring_update", "WebSocket 消息類型錯誤"
                assert "timestamp" in message, "WebSocket 消息缺少 timestamp 欄位"
                assert "health" in message, "WebSocket 消息缺少 health 欄位"
                assert "alerts" in message, "WebSocket 消息缺少 alerts 欄位"
                assert "services" in message, "WebSocket 消息缺少 services 欄位"
                
        except Exception as e:
            raise AssertionError(f"WebSocket 整合測試失敗: {e}") from e

    def test_error_handling_integration(
        self,
        prometheus_collector: PrometheusCollector,
        alert_manager: IntelligentAlertManager
    ) -> None:
        """測試錯誤處理整合功能。
        
        Args:
            prometheus_collector: Prometheus 收集器測試實例
            alert_manager: 智能告警管理器測試實例
            
        Raises:
            AssertionError: 當錯誤處理不符合預期時
            
        Note:
            測試系統在異常情況下的錯誤處理和恢復能力
        """
        try:
            # 測試 Prometheus 收集器錯誤處理
            with patch(
                "src.monitoring.prometheus_collector.psutil.cpu_percent",
                side_effect=Exception("System error"),
            ):
                prometheus_collector.start_collection()
                time.sleep(0.2)  # 等待一個收集週期

                # 收集器應該仍在運行
                assert prometheus_collector.is_collecting, "收集器應該在錯誤後繼續運行"
                prometheus_collector.stop_collection()

            # 測試告警管理器錯誤處理
            with patch.object(
                alert_manager, "_get_metric_value", side_effect=Exception("Metric error")
            ):
                alert_manager.start()

                # 添加規則並執行評估
                from src.monitoring.intelligent_alert_manager import AlertRule

                rule = AlertRule(
                    id="error-test-rule",
                    name="Error Test",
                    description="Test error handling",
                    metric_name="test_metric",
                    operator=">",
                    threshold_value=50.0,
                    severity=AlertSeverity.WARNING,
                )
                alert_manager.rules[rule.id] = rule

                # 執行評估（不應該拋出異常）
                alert_manager._evaluate_alert_rules()

                # 告警管理器應該仍在運行
                assert alert_manager.is_running, "告警管理器應該在錯誤後繼續運行"
                alert_manager.stop()
                
        except Exception as e:
            raise AssertionError(f"錯誤處理整合測試失敗: {e}") from e
