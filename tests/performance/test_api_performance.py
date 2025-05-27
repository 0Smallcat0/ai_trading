"""
API 效能測試

此模組測試 API 端點的回應時間和效能指標，確保符合 <100ms 的目標。
"""

import pytest
import time
import asyncio
from typing import Dict, List, Any

from fastapi.testclient import TestClient
import httpx

from tests.performance.utils.performance_monitor import PerformanceMonitor
from tests.performance.utils.report_generator import ReportGenerator


@pytest.mark.performance
@pytest.mark.benchmark
class TestAPIPerformance:
    """API 效能測試類"""

    def test_health_endpoint_response_time(
        self, test_client: TestClient, performance_monitor: PerformanceMonitor
    ):
        """測試健康檢查端點回應時間"""
        # 預熱請求
        for _ in range(5):
            test_client.get("/health")

        # 開始效能監控
        performance_monitor.start_monitoring()

        # 執行測試請求
        for _ in range(50):
            response_time = performance_monitor.measure_api_response_time(
                test_client, "GET", "/health"
            )
            assert (
                response_time < 100
            ), f"健康檢查回應時間 {response_time}ms 超過 100ms 閾值"

        # 停止監控並獲取結果
        result = performance_monitor.stop_monitoring()

        # 驗證效能指標
        assert (
            result.avg_response_time < 100
        ), f"平均回應時間 {result.avg_response_time}ms 超過閾值"
        assert (
            result.p95_response_time < 150
        ), f"P95 回應時間 {result.p95_response_time}ms 超過閾值"
        assert result.successful_requests == 50, "所有請求都應該成功"

        print(
            f"✅ 健康檢查效能測試通過 - 平均回應時間: {result.avg_response_time:.1f}ms"
        )

    def test_auth_login_performance(
        self, test_client: TestClient, performance_monitor: PerformanceMonitor
    ):
        """測試登入端點效能"""
        login_data = {"username": "admin", "password": "admin123"}

        # 預熱
        test_client.post("/api/v1/auth/login", json=login_data)

        performance_monitor.start_monitoring()

        # 執行登入測試
        for _ in range(20):
            response_time = performance_monitor.measure_api_response_time(
                test_client, "POST", "/api/v1/auth/login", json_data=login_data
            )
            assert (
                response_time < 200
            ), f"登入回應時間 {response_time}ms 超過 200ms 閾值"

        result = performance_monitor.stop_monitoring()

        assert (
            result.avg_response_time < 150
        ), f"登入平均回應時間 {result.avg_response_time}ms 超過閾值"
        assert result.failed_requests == 0, "登入請求不應該失敗"

        print(f"✅ 登入效能測試通過 - 平均回應時間: {result.avg_response_time:.1f}ms")

    def test_data_management_api_performance(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        performance_monitor: PerformanceMonitor,
    ):
        """測試資料管理 API 效能"""
        # 預熱
        test_client.get("/api/v1/data/", headers=auth_headers)

        performance_monitor.start_monitoring()

        # 測試不同的資料管理端點
        endpoints = [
            ("GET", "/api/v1/data/"),
            ("GET", "/api/v1/data/sources"),
            ("GET", "/api/v1/data/quality/summary"),
        ]

        for method, url in endpoints:
            for _ in range(10):
                response_time = performance_monitor.measure_api_response_time(
                    test_client, method, url, headers=auth_headers
                )
                assert response_time < 100, f"{url} 回應時間 {response_time}ms 超過閾值"

        result = performance_monitor.stop_monitoring()

        assert result.avg_response_time < 100, f"資料管理 API 平均回應時間超過閾值"
        assert result.successful_requests > 0, "應該有成功的請求"

        print(
            f"✅ 資料管理 API 效能測試通過 - 平均回應時間: {result.avg_response_time:.1f}ms"
        )

    def test_strategy_management_api_performance(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        performance_monitor: PerformanceMonitor,
    ):
        """測試策略管理 API 效能"""
        performance_monitor.start_monitoring()

        # 測試策略管理端點
        endpoints = [
            ("GET", "/api/v1/strategies/"),
            ("GET", "/api/v1/strategies/types"),
        ]

        for method, url in endpoints:
            for _ in range(15):
                response_time = performance_monitor.measure_api_response_time(
                    test_client, method, url, headers=auth_headers
                )
                assert response_time < 100, f"{url} 回應時間超過閾值"

        result = performance_monitor.stop_monitoring()

        assert result.avg_response_time < 100, "策略管理 API 回應時間超過閾值"
        print(
            f"✅ 策略管理 API 效能測試通過 - 平均回應時間: {result.avg_response_time:.1f}ms"
        )

    @pytest.mark.asyncio
    async def test_async_api_performance(
        self,
        async_client,
        auth_headers: Dict[str, str],
        performance_monitor: PerformanceMonitor,
    ):
        """測試異步 API 效能"""
        async with httpx.AsyncClient(app=None, base_url="http://test") as client:
            # 併發測試
            tasks = []
            for _ in range(20):
                task = performance_monitor.measure_async_api_response_time(
                    client, "GET", "/health"
                )
                tasks.append(task)

            response_times = await asyncio.gather(*tasks)

            # 驗證所有回應時間
            for response_time in response_times:
                assert (
                    response_time < 100
                ), f"異步請求回應時間 {response_time}ms 超過閾值"

            avg_time = sum(response_times) / len(response_times)
            print(f"✅ 異步 API 效能測試通過 - 平均回應時間: {avg_time:.1f}ms")

    def test_api_performance_under_load(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        performance_monitor: PerformanceMonitor,
    ):
        """測試負載下的 API 效能"""
        performance_monitor.start_monitoring()

        # 模擬高負載
        endpoints = ["/health", "/api/info", "/api/v1/data/", "/api/v1/strategies/"]

        for _ in range(100):  # 總共 400 個請求
            for endpoint in endpoints:
                headers = auth_headers if endpoint.startswith("/api/v1/") else None
                response_time = performance_monitor.measure_api_response_time(
                    test_client, "GET", endpoint, headers=headers
                )
                # 在負載下允許稍高的回應時間
                assert response_time < 200, f"負載測試中 {endpoint} 回應時間過長"

        result = performance_monitor.stop_monitoring()

        # 負載測試的寬鬆標準
        assert result.avg_response_time < 150, "負載下平均回應時間超過閾值"
        assert result.throughput > 10, "吞吐量過低"

        print(
            f"✅ 負載效能測試通過 - 平均回應時間: {result.avg_response_time:.1f}ms, "
            f"吞吐量: {result.throughput:.1f} req/s"
        )

    @pytest.mark.benchmark(group="api_endpoints")
    def test_benchmark_critical_endpoints(
        self, test_client: TestClient, auth_headers: Dict[str, str], benchmark
    ):
        """使用 pytest-benchmark 進行基準測試"""

        def api_call():
            response = test_client.get("/api/v1/data/", headers=auth_headers)
            return response.status_code

        # 基準測試
        result = benchmark(api_call)

        # benchmark 會自動記錄統計資訊
        print(f"✅ 基準測試完成")

    def test_generate_performance_report(
        self, test_client: TestClient, auth_headers: Dict[str, str]
    ):
        """生成效能測試報告"""
        report_generator = ReportGenerator()
        results = []

        # 執行多個效能測試並收集結果
        test_cases = [
            ("健康檢查", "GET", "/health", None),
            ("API 資訊", "GET", "/api/info", None),
            ("資料管理", "GET", "/api/v1/data/", auth_headers),
            ("策略管理", "GET", "/api/v1/strategies/", auth_headers),
        ]

        for test_name, method, url, headers in test_cases:
            monitor = PerformanceMonitor()
            monitor.start_monitoring()

            # 執行測試
            for _ in range(20):
                monitor.measure_api_response_time(
                    test_client, method, url, headers=headers
                )

            result = monitor.stop_monitoring()
            result.test_name = test_name
            results.append(result)

        # 生成報告
        html_report = report_generator.generate_performance_report(
            results, "api_performance_test", "html"
        )
        json_report = report_generator.generate_performance_report(
            results, "api_performance_test", "json"
        )

        print(f"✅ 效能報告已生成:")
        print(f"   HTML: {html_report}")
        print(f"   JSON: {json_report}")

        # 驗證報告檔案存在
        import os

        assert os.path.exists(html_report), "HTML 報告檔案不存在"
        assert os.path.exists(json_report), "JSON 報告檔案不存在"


@pytest.mark.performance
class TestAPIResponseTimeThresholds:
    """API 回應時間閾值測試"""

    @pytest.mark.parametrize(
        "endpoint,method,threshold",
        [
            ("/health", "GET", 50),
            ("/api/info", "GET", 100),
            ("/api/v1/auth/login", "POST", 200),
            ("/api/v1/data/", "GET", 100),
            ("/api/v1/strategies/", "GET", 100),
        ],
    )
    def test_endpoint_response_time_threshold(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        endpoint: str,
        method: str,
        threshold: int,
    ):
        """測試各端點的回應時間閾值"""
        # 準備請求參數
        headers = (
            auth_headers
            if endpoint.startswith("/api/v1/") and endpoint != "/api/v1/auth/login"
            else None
        )
        json_data = (
            {"username": "admin", "password": "admin123"}
            if endpoint == "/api/v1/auth/login"
            else None
        )

        # 預熱
        if method == "GET":
            test_client.get(endpoint, headers=headers)
        elif method == "POST":
            test_client.post(endpoint, headers=headers, json=json_data)

        # 測試回應時間
        response_times = []
        for _ in range(10):
            start_time = time.time()

            if method == "GET":
                response = test_client.get(endpoint, headers=headers)
            elif method == "POST":
                response = test_client.post(endpoint, headers=headers, json=json_data)

            response_time = (time.time() - start_time) * 1000  # ms
            response_times.append(response_time)

            assert (
                response.status_code < 400
            ), f"{endpoint} 返回錯誤狀態碼 {response.status_code}: {response.text}"

        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)

        assert (
            avg_response_time < threshold
        ), f"{endpoint} 平均回應時間 {avg_response_time:.1f}ms 超過 {threshold}ms 閾值"
        assert max_response_time < threshold * 2, f"{endpoint} 最大回應時間過長"

        print(
            f"✅ {endpoint} 回應時間測試通過 - 平均: {avg_response_time:.1f}ms, 最大: {max_response_time:.1f}ms"
        )
