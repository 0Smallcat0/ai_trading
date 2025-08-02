"""
健康檢查服務重構後測試

測試重構後的健康檢查服務模組，包括：
- 基礎健康檢查器測試
- 系統資源檢查器測試
- 服務檢查器測試
- 整合測試

遵循 Phase 5.3 測試標準。
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from src.monitoring.health_checker import HealthChecker
from src.monitoring.health_checker_base import (
    HealthCheckResult,
    HealthStatus,
    create_summary_result,
)
from src.monitoring.system_resource_checker import SystemResourceChecker
from src.monitoring.service_checker import ServiceChecker


class TestHealthCheckerBase:
    """健康檢查基礎類別測試"""

    def test_health_check_result_creation(self):
        """測試健康檢查結果創建"""
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.HEALTHY,
            score=100.0,
            message="測試正常",
        )

        assert result.name == "test"
        assert result.status == HealthStatus.HEALTHY
        assert result.score == 100.0
        assert result.message == "測試正常"
        assert result.is_healthy()
        assert not result.is_critical()

    def test_create_summary_result(self):
        """測試創建摘要結果"""
        results = {
            "test1": HealthCheckResult("test1", HealthStatus.HEALTHY, 100.0, "OK"),
            "test2": HealthCheckResult("test2", HealthStatus.WARNING, 70.0, "Warning"),
        }

        summary = create_summary_result(results)

        assert summary.name == "overall"
        assert summary.status == HealthStatus.WARNING
        assert summary.score == 85.0  # (100 + 70) / 2
        assert "1 個警告" in summary.message


class TestSystemResourceChecker:
    """系統資源檢查器測試"""

    @pytest.fixture
    def resource_checker(self):
        """創建系統資源檢查器實例"""
        return SystemResourceChecker()

    @patch("src.monitoring.system_resource_checker.psutil.cpu_percent")
    def test_check_cpu_usage(self, mock_cpu_percent, resource_checker):
        """測試 CPU 使用率檢查"""
        mock_cpu_percent.return_value = 50.0

        result = resource_checker.check_cpu_usage()

        assert result.name == "cpu"
        assert result.status == HealthStatus.HEALTHY
        assert result.score == 100.0
        assert "正常" in result.message
        assert result.details["usage_percent"] == 50.0

    @patch("src.monitoring.system_resource_checker.psutil.virtual_memory")
    def test_check_memory_usage(self, mock_memory, resource_checker):
        """測試記憶體使用率檢查"""
        mock_memory_obj = MagicMock()
        mock_memory_obj.percent = 60.0
        mock_memory_obj.total = 8 * 1024**3  # 8GB
        mock_memory_obj.available = 3 * 1024**3  # 3GB
        mock_memory_obj.used = 5 * 1024**3  # 5GB
        mock_memory.return_value = mock_memory_obj

        result = resource_checker.check_memory_usage()

        assert result.name == "memory"
        assert result.status == HealthStatus.HEALTHY
        assert result.score == 100.0
        assert result.details["usage_percent"] == 60.0
        assert result.details["total_gb"] == 8.0

    def test_check_all_resources(self, resource_checker):
        """測試檢查所有系統資源"""
        with patch.multiple(
            resource_checker,
            check_cpu_usage=MagicMock(
                return_value=HealthCheckResult("cpu", HealthStatus.HEALTHY, 100.0, "OK")
            ),
            check_memory_usage=MagicMock(
                return_value=HealthCheckResult(
                    "memory", HealthStatus.HEALTHY, 100.0, "OK"
                )
            ),
            check_disk_usage=MagicMock(
                return_value=HealthCheckResult(
                    "disk", HealthStatus.HEALTHY, 100.0, "OK"
                )
            ),
        ):
            results = resource_checker.check_all_resources()

            assert len(results) == 3
            assert "cpu" in results
            assert "memory" in results
            assert "disk" in results


class TestServiceChecker:
    """服務檢查器測試"""

    @pytest.fixture
    def service_checker(self):
        """創建服務檢查器實例"""
        return ServiceChecker()

    def test_check_database(self, service_checker):
        """測試資料庫檢查"""
        result = service_checker.check_database()

        assert result.name == "database"
        assert result.status == HealthStatus.HEALTHY
        assert result.score == 100.0
        assert "正常" in result.message

    @patch("src.monitoring.service_checker.requests.get")
    def test_check_api_endpoints_success(self, mock_get, service_checker):
        """測試 API 端點檢查成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        results = service_checker.check_api_endpoints(["/health"])

        assert len(results) == 1
        assert "api_health" in results
        assert results["api_health"].status == HealthStatus.HEALTHY

    @patch("src.monitoring.service_checker.requests.get")
    def test_check_external_services_success(self, mock_get, service_checker):
        """測試外部服務檢查成功"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        services = [{"name": "test_service", "url": "http://test.com/health"}]
        results = service_checker.check_external_services(services)

        assert len(results) == 1
        assert "test_service" in results
        assert results["test_service"].status == HealthStatus.HEALTHY


class TestHealthChecker:
    """健康檢查服務整合測試"""

    @pytest.fixture
    def health_checker(self):
        """創建健康檢查器實例"""
        with patch("src.monitoring.health_checker.Path.exists", return_value=False):
            checker = HealthChecker()
            return checker

    def test_init(self, health_checker):
        """測試初始化"""
        assert health_checker.check_interval == 60
        assert not health_checker.is_running
        assert isinstance(health_checker.last_results, dict)
        assert isinstance(health_checker.health_history, list)
        assert health_checker.system_checker is not None
        assert health_checker.service_checker is not None

    def test_start_stop(self, health_checker):
        """測試啟動和停止"""
        # 測試啟動
        assert health_checker.start()
        assert health_checker.is_running

        # 等待一小段時間
        time.sleep(0.1)

        # 測試停止
        assert health_checker.stop()
        assert not health_checker.is_running

    def test_run_all_checks(self, health_checker):
        """測試執行所有檢查"""
        with patch.multiple(
            health_checker.service_checker,
            check_database=MagicMock(
                return_value=HealthCheckResult(
                    "database", HealthStatus.HEALTHY, 100.0, "OK"
                )
            ),
            check_api_endpoints=MagicMock(return_value={}),
            check_external_services=MagicMock(return_value={}),
        ), patch.object(
            health_checker.system_checker,
            "check_all_resources",
            return_value={
                "cpu": HealthCheckResult("cpu", HealthStatus.HEALTHY, 100.0, "OK")
            },
        ):
            results = health_checker.run_all_checks()

            assert isinstance(results, dict)
            assert "database" in results
            assert "cpu" in results

    def test_get_overall_health(self, health_checker):
        """測試獲取整體健康狀態"""
        # 設置模擬結果
        health_checker.last_results = {
            "test": HealthCheckResult("test", HealthStatus.HEALTHY, 100.0, "OK")
        }

        overall_health = health_checker.get_overall_health()

        assert overall_health.name == "overall"
        assert overall_health.status == HealthStatus.HEALTHY
        assert overall_health.score == 100.0

    def test_get_health_summary(self, health_checker):
        """測試獲取健康狀態摘要"""
        # 設置模擬結果
        health_checker.last_results = {
            "test": HealthCheckResult("test", HealthStatus.HEALTHY, 100.0, "OK")
        }

        with patch.object(
            health_checker.system_checker,
            "get_system_uptime",
            return_value="1天 2小時 3分鐘",
        ):
            summary = health_checker.get_health_summary()

            assert "overall" in summary
            assert "checks" in summary
            assert "timestamp" in summary
            assert "uptime" in summary
            assert summary["uptime"] == "1天 2小時 3分鐘"

    def test_is_healthy(self, health_checker):
        """測試系統是否健康"""
        # 無結果時
        assert not health_checker.is_healthy()

        # 健康狀態
        health_checker.last_results = {
            "test": HealthCheckResult("test", HealthStatus.HEALTHY, 100.0, "OK")
        }
        assert health_checker.is_healthy()

        # 嚴重狀態
        health_checker.last_results = {
            "test": HealthCheckResult("test", HealthStatus.CRITICAL, 0.0, "Critical")
        }
        assert not health_checker.is_healthy()

    def test_get_critical_issues(self, health_checker):
        """測試獲取嚴重問題"""
        health_checker.last_results = {
            "test1": HealthCheckResult("test1", HealthStatus.HEALTHY, 100.0, "OK"),
            "test2": HealthCheckResult("test2", HealthStatus.CRITICAL, 0.0, "Critical"),
        }

        critical_issues = health_checker.get_critical_issues()

        assert len(critical_issues) == 1
        assert critical_issues[0].name == "test2"

    def test_get_warnings(self, health_checker):
        """測試獲取警告"""
        health_checker.last_results = {
            "test1": HealthCheckResult("test1", HealthStatus.HEALTHY, 100.0, "OK"),
            "test2": HealthCheckResult("test2", HealthStatus.WARNING, 70.0, "Warning"),
        }

        warnings = health_checker.get_warnings()

        assert len(warnings) == 1
        assert warnings[0].name == "test2"
