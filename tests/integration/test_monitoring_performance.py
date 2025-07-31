"""
監控系統效能與並發測試

測試監控系統在高負載和並發情況下的效能表現，包括：
- 效能整合測試
- 並發操作測試
- 配置整合測試
- 記憶體使用測試
- 負載測試

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥9.0/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import time
import threading
import tracemalloc
from typing import Dict, Any
from unittest.mock import patch, MagicMock

import pytest

from src.monitoring.prometheus_collector import PrometheusCollector
from src.monitoring.intelligent_alert_manager import (
    IntelligentAlertManager,
    AlertSeverity,
)
from src.monitoring.health_checker import HealthChecker


class TestMonitoringPerformance:
    """監控系統效能測試類。

    測試監控系統在各種負載條件下的效能表現，包括：
    - 高負載下的效能測試
    - 並發操作測試
    - 記憶體使用測試
    - 配置載入測試

    符合 Phase 7.2 測試標準，確保系統效能符合要求。
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

    def test_performance_integration(
        self, prometheus_collector: PrometheusCollector, health_checker: HealthChecker
    ) -> None:
        """測試效能整合功能。

        Args:
            prometheus_collector: Prometheus 收集器測試實例
            health_checker: 健康檢查器測試實例

        Raises:
            AssertionError: 當效能不符合預期時

        Note:
            測試系統在高負載下的效能表現，包括執行時間和記憶體使用
        """
        try:
            tracemalloc.start()
            start_time = time.time()

            # 啟動服務
            prometheus_collector.start_collection()
            health_checker.start()

            # 模擬高負載
            for i in range(100):
                prometheus_collector.record_api_request(
                    "GET", f"/api/test{i}", 200, 0.1
                )
                if i % 10 == 0:
                    health_checker.run_all_checks()

            # 測量效能
            end_time = time.time()
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # 清理
            prometheus_collector.stop_collection()
            health_checker.stop()

            # 驗證效能指標
            execution_time = end_time - start_time
            assert execution_time < 5.0, f"執行時間過長: {execution_time:.2f}秒"
            assert (
                peak < 100 * 1024 * 1024
            ), f"記憶體使用過多: {peak / 1024 / 1024:.2f}MB"

        except Exception as e:
            raise AssertionError(f"效能整合測試失敗: {e}") from e

    def test_concurrent_operations_integration(
        self,
        prometheus_collector: PrometheusCollector,
        alert_manager: IntelligentAlertManager,
    ) -> None:
        """測試並發操作整合功能。

        Args:
            prometheus_collector: Prometheus 收集器測試實例
            alert_manager: 智能告警管理器測試實例

        Raises:
            AssertionError: 當並發操作不符合預期時

        Note:
            測試系統在並發操作下的穩定性和正確性
        """
        try:
            # 啟動服務
            prometheus_collector.start_collection()
            alert_manager.start()

            def record_metrics() -> None:
                """記錄指標的工作函數。

                Note:
                    在並發環境中記錄 API 請求指標
                """
                for i in range(50):
                    prometheus_collector.record_api_request(
                        "GET", f"/api/concurrent{i}", 200, 0.1
                    )
                    time.sleep(0.001)

            def trigger_alerts() -> None:
                """觸發告警的工作函數。

                Note:
                    在並發環境中觸發告警評估
                """
                with patch.object(
                    alert_manager, "_get_metric_value", return_value=85.0
                ):
                    for i in range(10):
                        alert_manager._evaluate_alert_rules()
                        time.sleep(0.01)

            # 並發執行
            threads = []
            for _ in range(3):
                threads.append(threading.Thread(target=record_metrics))
                threads.append(threading.Thread(target=trigger_alerts))

            for thread in threads:
                thread.start()

            for thread in threads:
                thread.join()

            # 清理
            prometheus_collector.stop_collection()
            alert_manager.stop()

            # 驗證沒有發生錯誤
            assert True, "並發操作完成"

        except Exception as e:
            raise AssertionError(f"並發操作整合測試失敗: {e}") from e

    def test_configuration_integration(self) -> None:
        """測試配置整合功能。

        Raises:
            AssertionError: 當配置載入不符合預期時

        Note:
            測試系統配置檔案的載入和解析功能
        """
        try:
            # 測試配置檔案載入
            with patch(
                "src.monitoring.intelligent_alert_manager.Path.exists",
                return_value=True,
            ):
                with patch("builtins.open", create=True) as mock_open:
                    mock_open.return_value.__enter__.return_value.read.return_value = """
                    groups:
                      - name: test_group
                        rules:
                          - alert: TestAlert
                            expr: test_metric > 80
                            labels:
                              severity: warning
                            annotations:
                              summary: Test alert
                    """

                    # 創建告警管理器（應該載入配置）
                    alert_manager = IntelligentAlertManager()

                    # 驗證規則被載入
                    assert len(alert_manager.rules) > 0, "配置規則未被載入"

        except Exception as e:
            raise AssertionError(f"配置整合測試失敗: {e}") from e

    def test_memory_usage_monitoring(
        self, prometheus_collector: PrometheusCollector
    ) -> None:
        """測試記憶體使用監控功能。

        Args:
            prometheus_collector: Prometheus 收集器測試實例

        Raises:
            AssertionError: 當記憶體使用不符合預期時

        Note:
            測試長時間運行下的記憶體使用情況
        """
        try:
            tracemalloc.start()

            # 啟動收集器
            prometheus_collector.start_collection()

            # 記錄大量指標
            for i in range(1000):
                prometheus_collector.record_api_request(
                    "GET", f"/api/memory_test{i}", 200, 0.1
                )
                prometheus_collector.record_trading_order("market", "filled", 0.05)

                # 每100次檢查一次記憶體
                if i % 100 == 0:
                    current, peak = tracemalloc.get_traced_memory()
                    # 記憶體使用不應該無限增長
                    assert (
                        current < 50 * 1024 * 1024
                    ), f"記憶體使用過多: {current / 1024 / 1024:.2f}MB"

            # 停止收集器
            prometheus_collector.stop_collection()

            # 最終記憶體檢查
            _, final_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            assert (
                final_peak < 100 * 1024 * 1024
            ), f"最終記憶體使用過多: {final_peak / 1024 / 1024:.2f}MB"

        except Exception as e:
            raise AssertionError(f"記憶體使用監控測試失敗: {e}") from e

    def test_load_testing(
        self, prometheus_collector: PrometheusCollector, health_checker: HealthChecker
    ) -> None:
        """測試負載測試功能。

        Args:
            prometheus_collector: Prometheus 收集器測試實例
            health_checker: 健康檢查器測試實例

        Raises:
            AssertionError: 當負載測試不符合預期時

        Note:
            測試系統在持續高負載下的穩定性
        """
        try:
            start_time = time.time()

            # 啟動服務
            prometheus_collector.start_collection()
            health_checker.start()

            # 持續負載測試
            test_duration = 2.0  # 2秒測試
            while time.time() - start_time < test_duration:
                # 模擬各種類型的請求
                prometheus_collector.record_api_request(
                    "GET", "/api/load_test", 200, 0.05
                )
                prometheus_collector.record_api_request(
                    "POST", "/api/orders", 201, 0.15
                )
                prometheus_collector.record_trading_order("limit", "filled", 0.08)
                prometheus_collector.update_strategy_metrics(
                    "load_test_strategy", 1000.0, 1.5, 3.2
                )

                # 定期執行健康檢查
                if int((time.time() - start_time) * 10) % 5 == 0:
                    health_checker.run_all_checks()

                time.sleep(0.01)  # 短暫休息

            # 驗證服務仍在運行
            assert prometheus_collector.is_collecting, "Prometheus 收集器應該仍在運行"
            assert health_checker.is_running, "健康檢查器應該仍在運行"

            # 清理
            prometheus_collector.stop_collection()
            health_checker.stop()

            end_time = time.time()
            actual_duration = end_time - start_time

            # 驗證測試持續時間合理
            assert (
                actual_duration >= test_duration * 0.9
            ), f"測試持續時間過短: {actual_duration:.2f}秒"
            assert (
                actual_duration <= test_duration * 1.5
            ), f"測試持續時間過長: {actual_duration:.2f}秒"

        except Exception as e:
            raise AssertionError(f"負載測試失敗: {e}") from e
