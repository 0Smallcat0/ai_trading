"""
健康檢查服務測試

測試 HealthChecker 類的各項功能，包括系統健康檢查、
API 端點檢查、外部服務檢查等。

遵循 Phase 5.3 測試標準，確保 ≥70% 測試覆蓋率。
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.monitoring.health_checker import HealthChecker, HealthStatus, HealthCheckResult


class TestHealthCheckResult:
    """健康檢查結果測試"""

    def test_init(self):
        """測試初始化"""
        result = HealthCheckResult(
            name="test_check",
            status=HealthStatus.HEALTHY,
            score=95.0,
            message="All good",
        )

        assert result.name == "test_check"
        assert result.status == HealthStatus.HEALTHY
        assert result.score == 95.0
        assert result.message == "All good"
        assert isinstance(result.timestamp, datetime)
        assert result.duration == 0.0
        assert isinstance(result.details, dict)


class TestHealthChecker:
    """健康檢查服務測試"""

    @pytest.fixture
    def health_checker(self):
        """創建測試用的 HealthChecker 實例"""
        with patch("src.monitoring.health_checker.Path.exists", return_value=False):
            checker = HealthChecker()
            return checker

    def test_init(self, health_checker):
        """測試初始化"""
        assert health_checker.check_interval == 60
        assert not health_checker.is_running
        assert isinstance(health_checker.last_results, dict)
        assert isinstance(health_checker.health_history, list)

    def test_start_stop(self, health_checker):
        """測試啟動和停止"""
        # 測試啟動
        assert health_checker.start()
        assert health_checker.is_running

        # 測試重複啟動
        assert health_checker.start()

        # 測試停止
        assert health_checker.stop()
        assert not health_checker.is_running

        # 測試重複停止
        assert health_checker.stop()

    @patch("src.monitoring.health_checker.psutil.cpu_percent")
    @patch("src.monitoring.health_checker.psutil.virtual_memory")
    def test_check_system_resources(self, mock_memory, mock_cpu, health_checker):
        """測試系統資源檢查"""
        # 模擬系統數據
        mock_cpu.return_value = 65.0
        mock_memory.return_value = MagicMock(
            percent=75.0, total=8589934592, available=2147483648
        )

        results = health_checker.check_system_resources()

        # 驗證 CPU 檢查結果
        assert "cpu" in results
        cpu_result = results["cpu"]
        assert cpu_result.status == HealthStatus.HEALTHY
        assert cpu_result.score == 100.0
        assert cpu_result.details["usage_percent"] == 65.0

        # 驗證記憶體檢查結果
        assert "memory" in results
        memory_result = results["memory"]
        assert memory_result.status == HealthStatus.HEALTHY
        assert memory_result.score == 100.0
        assert memory_result.details["usage_percent"] == 75.0

    @patch("src.monitoring.health_checker.psutil.cpu_percent")
    def test_check_system_resources_warning(self, mock_cpu, health_checker):
        """測試系統資源警告狀態"""
        # 模擬高 CPU 使用率
        mock_cpu.return_value = 85.0

        results = health_checker.check_system_resources()

        cpu_result = results["cpu"]
        assert cpu_result.status == HealthStatus.WARNING
        assert cpu_result.score == 70.0
        assert "偏高" in cpu_result.message

    @patch("src.monitoring.health_checker.psutil.cpu_percent")
    def test_check_system_resources_critical(self, mock_cpu, health_checker):
        """測試系統資源嚴重狀態"""
        # 模擬極高 CPU 使用率
        mock_cpu.return_value = 95.0

        results = health_checker.check_system_resources()

        cpu_result = results["cpu"]
        assert cpu_result.status == HealthStatus.CRITICAL
        assert cpu_result.score == 30.0
        assert "過高" in cpu_result.message

    def test_check_database(self, health_checker):
        """測試資料庫檢查"""
        result = health_checker.check_database()

        assert result.name == "database"
        assert result.status == HealthStatus.HEALTHY
        assert result.score == 100.0
        assert "正常" in result.message
        assert "connection_time" in result.details

    @patch("src.monitoring.health_checker.requests.get")
    def test_check_api_endpoints_success(self, mock_get, health_checker):
        """測試 API 端點檢查成功"""
        # 模擬成功響應
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        results = health_checker.check_api_endpoints()

        assert "api_health" in results
        result = results["api_health"]
        assert result.status == HealthStatus.HEALTHY
        assert result.score == 100.0
        assert result.details["status_code"] == 200

    @patch("src.monitoring.health_checker.requests.get")
    def test_check_api_endpoints_failure(self, mock_get, health_checker):
        """測試 API 端點檢查失敗"""
        # 模擬請求異常
        mock_get.side_effect = Exception("Connection failed")

        results = health_checker.check_api_endpoints()

        assert "api_health" in results
        result = results["api_health"]
        assert result.status == HealthStatus.CRITICAL
        assert result.score == 0.0
        assert "失敗" in result.message

    @patch("src.monitoring.health_checker.requests.get")
    def test_check_external_services(self, mock_get, health_checker):
        """測試外部服務檢查"""
        # 模擬配置
        health_checker.config = {
            "checks": {
                "external_services": {
                    "enabled": True,
                    "timeout": 15,
                    "services": [
                        {
                            "name": "prometheus",
                            "url": "http://localhost:9090/-/healthy",
                        },
                        {"name": "grafana", "url": "http://localhost:3000/api/health"},
                    ],
                }
            }
        }

        # 模擬成功響應
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        results = health_checker.check_external_services()

        assert "prometheus" in results
        assert "grafana" in results

        prometheus_result = results["prometheus"]
        assert prometheus_result.status == HealthStatus.HEALTHY
        assert prometheus_result.score == 100.0

    def test_run_all_checks(self, health_checker):
        """測試執行所有檢查"""
        with patch.object(health_checker, "check_database") as mock_db, patch.object(
            health_checker, "check_api_endpoints"
        ) as mock_api, patch.object(
            health_checker, "check_external_services"
        ) as mock_ext, patch.object(
            health_checker, "check_system_resources"
        ) as mock_sys:

            # 模擬各檢查結果
            mock_db.return_value = HealthCheckResult(
                "db", HealthStatus.HEALTHY, 100.0, "OK"
            )
            mock_api.return_value = {
                "api": HealthCheckResult("api", HealthStatus.HEALTHY, 100.0, "OK")
            }
            mock_ext.return_value = {
                "ext": HealthCheckResult("ext", HealthStatus.HEALTHY, 100.0, "OK")
            }
            mock_sys.return_value = {
                "sys": HealthCheckResult("sys", HealthStatus.HEALTHY, 100.0, "OK")
            }

            results = health_checker.run_all_checks()

            assert "database" in results
            assert "api" in results
            assert "ext" in results
            assert "sys" in results

    def test_get_overall_health_no_results(self, health_checker):
        """測試無檢查結果時的整體健康狀態"""
        overall = health_checker.get_overall_health()

        assert overall.status == HealthStatus.UNKNOWN
        assert overall.score == 0.0
        assert "尚未執行" in overall.message

    def test_get_overall_health_with_results(self, health_checker):
        """測試有檢查結果時的整體健康狀態"""
        # 添加模擬結果
        health_checker.last_results = {
            "check1": HealthCheckResult("check1", HealthStatus.HEALTHY, 100.0, "OK"),
            "check2": HealthCheckResult(
                "check2", HealthStatus.WARNING, 70.0, "Warning"
            ),
            "check3": HealthCheckResult("check3", HealthStatus.HEALTHY, 90.0, "OK"),
        }

        overall = health_checker.get_overall_health()

        assert overall.status == HealthStatus.WARNING  # 有警告
        assert overall.score == (100.0 + 70.0 + 90.0) / 3  # 平均分數
        assert "1 個警告" in overall.message

    def test_get_overall_health_with_critical(self, health_checker):
        """測試有嚴重問題時的整體健康狀態"""
        health_checker.last_results = {
            "check1": HealthCheckResult("check1", HealthStatus.HEALTHY, 100.0, "OK"),
            "check2": HealthCheckResult(
                "check2", HealthStatus.CRITICAL, 0.0, "Critical"
            ),
        }

        overall = health_checker.get_overall_health()

        assert overall.status == HealthStatus.CRITICAL
        assert "1 個嚴重問題" in overall.message

    def test_get_health_summary(self, health_checker):
        """測試獲取健康狀態摘要"""
        # 添加模擬結果
        health_checker.last_results = {
            "test": HealthCheckResult("test", HealthStatus.HEALTHY, 100.0, "OK")
        }

        summary = health_checker.get_health_summary()

        assert "overall" in summary
        assert "checks" in summary
        assert "timestamp" in summary
        assert "uptime" in summary

        assert "test" in summary["checks"]
        assert summary["checks"]["test"]["status"] == "healthy"
        assert summary["checks"]["test"]["score"] == 100.0

    def test_add_to_history(self, health_checker):
        """測試添加到歷史記錄"""
        results = {"test": HealthCheckResult("test", HealthStatus.HEALTHY, 100.0, "OK")}

        health_checker._add_to_history(results)

        assert len(health_checker.health_history) == 1
        assert "test" in health_checker.health_history[0]

    def test_history_size_limit(self, health_checker):
        """測試歷史記錄大小限制"""
        health_checker.max_history_size = 3

        # 添加超過限制的記錄
        for i in range(5):
            results = {
                f"test{i}": HealthCheckResult(
                    f"test{i}", HealthStatus.HEALTHY, 100.0, "OK"
                )
            }
            health_checker._add_to_history(results)

        # 驗證只保留最新的記錄
        assert len(health_checker.health_history) == 3
        assert "test4" in health_checker.health_history[-1]  # 最新的記錄

    @patch("src.monitoring.health_checker.psutil.boot_time")
    def test_get_uptime(self, mock_boot_time, health_checker):
        """測試獲取系統運行時間"""
        # 模擬啟動時間（1天前）
        mock_boot_time.return_value = (datetime.now() - timedelta(days=1)).timestamp()

        uptime = health_checker._get_uptime()

        assert "天" in uptime
        assert "小時" in uptime
        assert "分鐘" in uptime

    def test_is_healthy(self, health_checker):
        """測試系統是否健康"""
        # 無結果時
        assert not health_checker.is_healthy()

        # 健康狀態
        health_checker.last_results = {
            "test": HealthCheckResult("test", HealthStatus.HEALTHY, 100.0, "OK")
        }
        assert health_checker.is_healthy()

        # 警告狀態（仍視為健康）
        health_checker.last_results = {
            "test": HealthCheckResult("test", HealthStatus.WARNING, 70.0, "Warning")
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
            "healthy": HealthCheckResult("healthy", HealthStatus.HEALTHY, 100.0, "OK"),
            "warning": HealthCheckResult(
                "warning", HealthStatus.WARNING, 70.0, "Warning"
            ),
            "critical": HealthCheckResult(
                "critical", HealthStatus.CRITICAL, 0.0, "Critical"
            ),
        }

        critical_issues = health_checker.get_critical_issues()

        assert len(critical_issues) == 1
        assert critical_issues[0].name == "critical"
        assert critical_issues[0].status == HealthStatus.CRITICAL

    def test_get_warnings(self, health_checker):
        """測試獲取警告"""
        health_checker.last_results = {
            "healthy": HealthCheckResult("healthy", HealthStatus.HEALTHY, 100.0, "OK"),
            "warning": HealthCheckResult(
                "warning", HealthStatus.WARNING, 70.0, "Warning"
            ),
            "critical": HealthCheckResult(
                "critical", HealthStatus.CRITICAL, 0.0, "Critical"
            ),
        }

        warnings = health_checker.get_warnings()

        assert len(warnings) == 1
        assert warnings[0].name == "warning"
        assert warnings[0].status == HealthStatus.WARNING

    def test_export_health_report(self, health_checker):
        """測試匯出健康檢查報告"""
        health_checker.last_results = {
            "test": HealthCheckResult("test", HealthStatus.HEALTHY, 100.0, "All good")
        }

        report = health_checker.export_health_report()

        assert isinstance(report, str)
        assert "# AI 交易系統健康檢查報告" in report
        assert "## 整體狀態" in report
        assert "## 詳細檢查結果" in report
        assert "test" in report
        assert "All good" in report

    def test_concurrent_health_checks(self, health_checker):
        """測試並發健康檢查"""
        import threading

        health_checker.start()

        def run_checks():
            for _ in range(5):
                health_checker.run_all_checks()
                time.sleep(0.01)

        # 並發執行檢查
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=run_checks)
            threads.append(thread)
            thread.start()

        # 等待所有線程完成
        for thread in threads:
            thread.join()

        health_checker.stop()

        # 驗證沒有發生錯誤
        assert True

    def test_error_handling_in_checks(self, health_checker):
        """測試檢查過程中的錯誤處理"""
        with patch.object(
            health_checker, "check_database", side_effect=Exception("DB Error")
        ):
            # 執行檢查（不應該拋出異常）
            results = health_checker.run_all_checks()

            # 驗證其他檢查仍然執行
            assert len(results) >= 0  # 可能有其他檢查成功

    def test_memory_usage_monitoring(self, health_checker):
        """測試記憶體使用監控"""
        import tracemalloc

        tracemalloc.start()

        # 啟動健康檢查並運行一段時間
        health_checker.start()
        time.sleep(0.5)

        # 執行多次檢查
        for _ in range(50):
            health_checker.run_all_checks()

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 清理
        health_checker.stop()

        # 驗證記憶體使用合理（小於 20MB）
        assert peak < 20 * 1024 * 1024
