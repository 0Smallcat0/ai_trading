"""
系統監控 API 測試

此模組測試系統監控 API 的所有端點，確保功能正確性和穩定性。
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

from src.api.main import app
from src.core.system_monitoring_service import SystemMonitoringService


class TestMonitoringAPI:
    """系統監控 API 測試類"""

    def setup_method(self):
        """測試前設置"""
        self.client = TestClient(app)
        self.base_url = "/api/v1/monitoring"

        # 模擬認證 token
        self.auth_headers = {"Authorization": "Bearer test_token"}

        # 測試數據
        self.test_alert_rule = {
            "name": "CPU 使用率警報",
            "description": "CPU 使用率超過 80% 時觸發警報",
            "metric_type": "cpu_usage",
            "threshold_type": "absolute",
            "threshold_value": 80.0,
            "comparison_operator": ">",
            "severity": "WARNING",
            "notification_channels": ["email", "system"],
            "enabled": True,
            "suppression_duration": 300,
        }

        self.test_system_metrics = {
            "timestamp": datetime.now(),
            "cpu_usage": 45.2,
            "memory_usage": 67.8,
            "memory_total": 16777216000,
            "memory_available": 5368709120,
            "disk_usage": 78.5,
            "disk_total": 1000000000000,
            "disk_free": 215000000000,
            "network_io_sent": 1024000,
            "network_io_recv": 2048000,
            "load_average": [1.2, 1.5, 1.8],
            "process_count": 156,
        }

    @patch("src.api.middleware.auth.verify_token")
    @patch(
        "src.core.system_monitoring_service.SystemMonitoringService.get_system_resource_metrics"
    )
    def test_get_system_resources_success(self, mock_get_metrics, mock_verify_token):
        """測試獲取系統資源監控成功"""
        # 設置模擬
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_get_metrics.return_value = [self.test_system_metrics]

        # 發送請求
        response = self.client.get(
            f"{self.base_url}/system/resources", headers=self.auth_headers
        )

        # 驗證響應
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["cpu_usage"] == 45.2

    @patch("src.api.middleware.auth.verify_token")
    @patch(
        "src.core.system_monitoring_service.SystemMonitoringService.get_trading_performance_metrics"
    )
    def test_get_trading_performance_success(
        self, mock_get_performance, mock_verify_token
    ):
        """測試獲取交易效能指標成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}

        test_performance_data = {
            "timestamp": datetime.now(),
            "api_latency_avg": 25.5,
            "api_latency_p95": 45.2,
            "api_latency_p99": 78.9,
            "trading_tps": 150.0,
            "order_success_rate": 98.5,
            "execution_success_rate": 97.8,
            "error_rate": 1.5,
            "timeout_rate": 0.5,
            "active_connections": 25,
            "queue_length": 3,
            "cache_hit_rate": 85.2,
        }

        mock_get_performance.return_value = [test_performance_data]

        response = self.client.get(
            f"{self.base_url}/trading/performance", headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"][0]["api_latency_avg"] == 25.5

    @patch("src.api.middleware.auth.verify_token")
    @patch("src.core.system_monitoring_service.SystemMonitoringService.query_logs")
    def test_get_logs_success(self, mock_query_logs, mock_verify_token):
        """測試查詢日誌成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}

        test_log_data = {
            "logs": [
                {
                    "id": "log_123",
                    "timestamp": datetime.now(),
                    "level": "INFO",
                    "module": "trading",
                    "message": "訂單創建成功",
                    "details": {"order_id": "order_456"},
                    "user_id": "user_789",
                    "session_id": "session_abc",
                    "request_id": "req_def",
                }
            ]
        }

        mock_query_logs.return_value = test_log_data

        response = self.client.get(f"{self.base_url}/logs", headers=self.auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["level"] == "INFO"

    @patch("src.api.middleware.auth.verify_token")
    @patch(
        "src.core.system_monitoring_service.SystemMonitoringService.create_alert_rule"
    )
    @patch("src.core.system_monitoring_service.SystemMonitoringService.get_alert_rule")
    def test_create_alert_rule_success(
        self, mock_get_rule, mock_create_rule, mock_verify_token
    ):
        """測試創建警報規則成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_create_rule.return_value = (True, "規則創建成功", "rule_123")

        rule_details = {
            **self.test_alert_rule,
            "id": "rule_123",
            "created_at": datetime.now(),
            "trigger_count": 0,
        }
        mock_get_rule.return_value = rule_details

        response = self.client.post(
            f"{self.base_url}/alerts",
            json=self.test_alert_rule,
            headers=self.auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "CPU 使用率警報"

    @patch("src.api.middleware.auth.verify_token")
    def test_create_alert_rule_invalid_data(self, mock_verify_token):
        """測試創建警報規則時數據驗證失敗"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}

        invalid_rule = {
            "name": "測試規則",
            "metric_type": "invalid_metric",  # 無效的指標類型
            "threshold_type": "absolute",
            "threshold_value": 80.0,
            "comparison_operator": ">",
            "severity": "WARNING",
            "notification_channels": ["email"],
        }

        response = self.client.post(
            f"{self.base_url}/alerts", json=invalid_rule, headers=self.auth_headers
        )

        assert response.status_code == 422  # 驗證錯誤

    @patch("src.api.middleware.auth.verify_token")
    @patch("src.core.system_monitoring_service.SystemMonitoringService.get_alerts")
    def test_get_alerts_success(self, mock_get_alerts, mock_verify_token):
        """測試獲取警報列表成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}

        test_alert_data = {
            "alerts": [
                {
                    "id": "alert_123",
                    "rule_id": "rule_456",
                    "rule_name": "CPU 使用率警報",
                    "severity": "WARNING",
                    "title": "CPU 使用率過高",
                    "message": "CPU 使用率達到 85%，超過閾值 80%",
                    "metric_value": 85.0,
                    "threshold_value": 80.0,
                    "status": "active",
                    "created_at": datetime.now(),
                    "notification_sent": True,
                }
            ]
        }

        mock_get_alerts.return_value = test_alert_data

        response = self.client.get(f"{self.base_url}/alerts", headers=self.auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["severity"] == "WARNING"

    @patch("src.api.middleware.auth.verify_token")
    @patch(
        "src.core.system_monitoring_service.SystemMonitoringService.perform_health_check"
    )
    def test_get_system_health_success(self, mock_health_check, mock_verify_token):
        """測試系統健康檢查成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}

        health_data = {
            "overall_status": "healthy",
            "health_score": 95.5,
            "components": {
                "api_service": "healthy",
                "database": "healthy",
                "redis": "healthy",
                "broker_connection": "healthy",
            },
            "last_check": datetime.now(),
            "uptime_seconds": 86400,
            "system_info": {"version": "1.0.0", "environment": "production"},
            "active_alerts": 2,
            "critical_issues": [],
        }

        mock_health_check.return_value = health_data

        response = self.client.get(f"{self.base_url}/health", headers=self.auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["overall_status"] == "healthy"
        assert data["data"]["health_score"] == 95.5

    @patch("src.api.middleware.auth.verify_token")
    @patch(
        "src.core.system_monitoring_service.SystemMonitoringService.generate_status_report"
    )
    def test_get_system_status_success(self, mock_generate_report, mock_verify_token):
        """測試獲取系統狀態報告成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}

        report_data = {
            "report_id": "report_123",
            "generated_at": datetime.now(),
            "period_start": datetime.now() - timedelta(hours=24),
            "period_end": datetime.now(),
            "summary": {
                "total_requests": 10000,
                "avg_response_time": 25.5,
                "error_count": 15,
            },
            "resource_usage": {"avg_cpu": 45.2, "avg_memory": 67.8, "peak_cpu": 78.5},
            "performance_metrics": {"api_latency_avg": 25.5, "trading_tps": 150.0},
            "alert_statistics": {"total_alerts": 25, "critical_alerts": 2},
            "recommendations": ["考慮增加 CPU 資源", "優化記憶體使用"],
        }

        mock_generate_report.return_value = report_data

        response = self.client.get(f"{self.base_url}/status", headers=self.auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["report_id"] == "report_123"

    @patch("src.api.middleware.auth.verify_token")
    @patch(
        "src.core.system_monitoring_service.SystemMonitoringService.acknowledge_alert"
    )
    def test_acknowledge_alert_success(self, mock_acknowledge, mock_verify_token):
        """測試確認警報成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_acknowledge.return_value = (True, "警報確認成功")

        response = self.client.put(
            f"{self.base_url}/alerts/alert_123/acknowledge?acknowledged_by=test_user&notes=已處理",
            headers=self.auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "acknowledged"

    @patch("src.api.middleware.auth.verify_token")
    def test_get_logs_with_filters(self, mock_verify_token):
        """測試帶篩選條件的日誌查詢"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}

        # 測試無效的日誌級別
        response = self.client.get(
            f"{self.base_url}/logs?log_level=INVALID", headers=self.auth_headers
        )

        assert response.status_code == 400

    def test_unauthorized_access(self):
        """測試未授權訪問"""
        response = self.client.get(f"{self.base_url}/health")

        # 應該返回 401 或重定向到登入頁面
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
