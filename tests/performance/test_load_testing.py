"""
負載測試

此模組測試 API 在不同負載條件下的效能表現，包括併發用戶和持續負載測試。
"""

import pytest
import asyncio
from typing import Dict, List, Any

from fastapi.testclient import TestClient

from tests.performance.utils.load_tester import LoadTester, LoadTestConfig
from tests.performance.utils.performance_monitor import PerformanceMonitor
from tests.performance.utils.report_generator import ReportGenerator


@pytest.mark.performance
@pytest.mark.load_test
class TestLoadTesting:
    """負載測試類"""

    def test_light_load_performance(
        self, test_client: TestClient, auth_headers: Dict[str, str]
    ):
        """輕負載測試 - 5 個併發用戶"""
        load_tester = LoadTester()

        # 定義測試場景
        test_scenarios = [
            {"method": "GET", "url": "/health"},
            {"method": "GET", "url": "/api/info"},
            {"method": "GET", "url": "/api/v1/data/", "headers": auth_headers},
        ]

        # 配置輕負載測試
        config = LoadTestConfig(
            concurrent_users=5,
            test_duration=30,  # 30 秒
            ramp_up_time=5,  # 5 秒內啟動所有用戶
            think_time=0.5,  # 用戶間隔 0.5 秒
        )

        # 執行負載測試
        result = load_tester.run_load_test(test_scenarios, config, auth_headers)

        # 驗證結果
        assert (
            result.avg_response_time < 100
        ), f"輕負載下平均回應時間 {result.avg_response_time:.1f}ms 超過閾值"
        assert result.throughput > 10, f"吞吐量 {result.throughput:.1f} req/s 過低"
        assert result.failed_requests == 0, f"發現 {result.failed_requests} 個失敗請求"

        print(f"✅ 輕負載測試通過:")
        print(f"   併發用戶: {config.concurrent_users}")
        print(f"   平均回應時間: {result.avg_response_time:.1f}ms")
        print(f"   吞吐量: {result.throughput:.1f} req/s")
        print(
            f"   成功率: {(result.successful_requests/result.total_requests*100):.1f}%"
        )

    def test_medium_load_performance(
        self, test_client: TestClient, auth_headers: Dict[str, str]
    ):
        """中等負載測試 - 25 個併發用戶"""
        load_tester = LoadTester()

        test_scenarios = [
            {"method": "GET", "url": "/health"},
            {"method": "GET", "url": "/api/v1/data/", "headers": auth_headers},
            {"method": "GET", "url": "/api/v1/strategies/", "headers": auth_headers},
            {
                "method": "POST",
                "url": "/api/v1/auth/login",
                "json": {"username": "admin", "password": "admin123"},
            },
        ]

        config = LoadTestConfig(
            concurrent_users=25, test_duration=60, ramp_up_time=10, think_time=1.0
        )

        result = load_tester.run_load_test(test_scenarios, config, auth_headers)

        # 中等負載的寬鬆標準
        assert result.avg_response_time < 150, f"中等負載下平均回應時間超過閾值"
        assert result.throughput > 20, f"中等負載下吞吐量過低"
        assert (
            result.successful_requests / result.total_requests
        ) > 0.95, "成功率低於 95%"

        print(f"✅ 中等負載測試通過:")
        print(f"   併發用戶: {config.concurrent_users}")
        print(f"   平均回應時間: {result.avg_response_time:.1f}ms")
        print(f"   P95 回應時間: {result.p95_response_time:.1f}ms")
        print(f"   吞吐量: {result.throughput:.1f} req/s")
        print(
            f"   成功率: {(result.successful_requests/result.total_requests*100):.1f}%"
        )

    def test_heavy_load_performance(
        self, test_client: TestClient, auth_headers: Dict[str, str]
    ):
        """重負載測試 - 50 個併發用戶"""
        load_tester = LoadTester()

        test_scenarios = [
            {"method": "GET", "url": "/health"},
            {"method": "GET", "url": "/api/v1/data/", "headers": auth_headers},
            {"method": "GET", "url": "/api/v1/strategies/", "headers": auth_headers},
            {"method": "GET", "url": "/api/v1/models/", "headers": auth_headers},
            {
                "method": "POST",
                "url": "/api/v1/auth/login",
                "json": {"username": "admin", "password": "admin123"},
            },
        ]

        config = LoadTestConfig(
            concurrent_users=50, test_duration=90, ramp_up_time=15, think_time=1.5
        )

        result = load_tester.run_load_test(test_scenarios, config, auth_headers)

        # 重負載的更寬鬆標準
        assert result.avg_response_time < 200, f"重負載下平均回應時間超過閾值"
        assert result.throughput > 30, f"重負載下吞吐量過低"
        assert (
            result.successful_requests / result.total_requests
        ) > 0.90, "成功率低於 90%"

        print(f"✅ 重負載測試通過:")
        print(f"   併發用戶: {config.concurrent_users}")
        print(f"   平均回應時間: {result.avg_response_time:.1f}ms")
        print(f"   P95 回應時間: {result.p95_response_time:.1f}ms")
        print(f"   P99 回應時間: {result.p99_response_time:.1f}ms")
        print(f"   吞吐量: {result.throughput:.1f} req/s")
        print(
            f"   成功率: {(result.successful_requests/result.total_requests*100):.1f}%"
        )

    @pytest.mark.asyncio
    async def test_async_load_performance(self, auth_headers: Dict[str, str]):
        """異步負載測試"""
        load_tester = LoadTester("http://127.0.0.1:8000")

        test_scenarios = [
            {"method": "GET", "url": "/health"},
            {"method": "GET", "url": "/api/info"},
            {"method": "GET", "url": "/api/v1/data/", "headers": auth_headers},
        ]

        config = LoadTestConfig(
            concurrent_users=20, test_duration=45, ramp_up_time=5, think_time=0.5
        )

        result = await load_tester.run_async_load_test(
            test_scenarios, config, auth_headers
        )

        assert result.avg_response_time < 120, "異步負載測試回應時間超過閾值"
        assert result.throughput > 15, "異步負載測試吞吐量過低"

        print(f"✅ 異步負載測試通過:")
        print(f"   平均回應時間: {result.avg_response_time:.1f}ms")
        print(f"   吞吐量: {result.throughput:.1f} req/s")

    def test_stress_testing(
        self, test_client: TestClient, auth_headers: Dict[str, str]
    ):
        """壓力測試 - 測試系統極限"""
        load_tester = LoadTester()

        # 簡化的測試場景，專注於核心端點
        test_scenarios = [
            {"method": "GET", "url": "/health"},
            {"method": "GET", "url": "/api/v1/data/", "headers": auth_headers},
        ]

        config = LoadTestConfig(
            concurrent_users=100,  # 高併發
            test_duration=60,
            ramp_up_time=20,
            think_time=0.1,  # 最小間隔
        )

        result = load_tester.run_load_test(test_scenarios, config, auth_headers)

        # 壓力測試的基本要求
        assert result.avg_response_time < 500, f"壓力測試下平均回應時間過長"
        assert (
            result.successful_requests / result.total_requests
        ) > 0.80, "壓力測試成功率低於 80%"

        print(f"✅ 壓力測試完成:")
        print(f"   併發用戶: {config.concurrent_users}")
        print(f"   平均回應時間: {result.avg_response_time:.1f}ms")
        print(f"   最大回應時間: {result.max_response_time:.1f}ms")
        print(f"   吞吐量: {result.throughput:.1f} req/s")
        print(
            f"   成功率: {(result.successful_requests/result.total_requests*100):.1f}%"
        )
        print(f"   失敗請求: {result.failed_requests}")

    def test_endurance_testing(
        self, test_client: TestClient, auth_headers: Dict[str, str]
    ):
        """耐久性測試 - 長時間運行"""
        load_tester = LoadTester()

        test_scenarios = [
            {"method": "GET", "url": "/health"},
            {"method": "GET", "url": "/api/v1/data/", "headers": auth_headers},
        ]

        config = LoadTestConfig(
            concurrent_users=10,
            test_duration=300,  # 5 分鐘
            ramp_up_time=30,
            think_time=2.0,
        )

        result = load_tester.run_load_test(test_scenarios, config, auth_headers)

        # 耐久性測試關注穩定性
        assert result.avg_response_time < 150, "耐久性測試平均回應時間超過閾值"
        assert (
            result.successful_requests / result.total_requests
        ) > 0.95, "耐久性測試成功率過低"

        print(f"✅ 耐久性測試通過:")
        print(f"   測試時長: {result.duration:.1f}s")
        print(f"   總請求數: {result.total_requests:,}")
        print(f"   平均回應時間: {result.avg_response_time:.1f}ms")
        print(
            f"   成功率: {(result.successful_requests/result.total_requests*100):.1f}%"
        )

    @pytest.mark.parametrize("concurrent_users", [1, 5, 10, 25, 50])
    def test_scalability_analysis(
        self,
        test_client: TestClient,
        auth_headers: Dict[str, str],
        concurrent_users: int,
    ):
        """可擴展性分析 - 測試不同併發級別"""
        load_tester = LoadTester()

        test_scenarios = [
            {"method": "GET", "url": "/health"},
            {"method": "GET", "url": "/api/v1/data/", "headers": auth_headers},
        ]

        config = LoadTestConfig(
            concurrent_users=concurrent_users,
            test_duration=30,
            ramp_up_time=5,
            think_time=1.0,
        )

        result = load_tester.run_load_test(test_scenarios, config, auth_headers)

        # 記錄可擴展性數據
        print(f"📊 可擴展性數據 - {concurrent_users} 用戶:")
        print(f"   平均回應時間: {result.avg_response_time:.1f}ms")
        print(f"   吞吐量: {result.throughput:.1f} req/s")
        print(
            f"   成功率: {(result.successful_requests/result.total_requests*100):.1f}%"
        )

        # 基本驗證
        assert result.avg_response_time < 300, f"{concurrent_users} 用戶下回應時間過長"
        assert (
            result.successful_requests / result.total_requests
        ) > 0.85, f"{concurrent_users} 用戶下成功率過低"

    def test_generate_load_test_report(
        self, test_client: TestClient, auth_headers: Dict[str, str]
    ):
        """生成負載測試報告"""
        report_generator = ReportGenerator()
        load_tester = LoadTester()
        results = []

        # 執行不同負載級別的測試
        test_configs = [
            ("輕負載", 5, 30),
            ("中等負載", 15, 45),
            ("重負載", 30, 60),
        ]

        test_scenarios = [
            {"method": "GET", "url": "/health"},
            {"method": "GET", "url": "/api/v1/data/", "headers": auth_headers},
        ]

        for test_name, users, duration in test_configs:
            config = LoadTestConfig(
                concurrent_users=users,
                test_duration=duration,
                ramp_up_time=10,
                think_time=1.0,
            )

            result = load_tester.run_load_test(test_scenarios, config, auth_headers)
            result.test_name = f"{test_name} ({users} 用戶)"
            results.append(result)

        # 生成報告
        html_report = report_generator.generate_performance_report(
            results, "load_test_report", "html"
        )
        json_report = report_generator.generate_performance_report(
            results, "load_test_report", "json"
        )

        print(f"✅ 負載測試報告已生成:")
        print(f"   HTML: {html_report}")
        print(f"   JSON: {json_report}")

        # 驗證報告檔案
        import os

        assert os.path.exists(html_report), "HTML 報告檔案不存在"
        assert os.path.exists(json_report), "JSON 報告檔案不存在"


@pytest.mark.performance
@pytest.mark.load_test
class TestSpecificEndpointLoad:
    """特定端點負載測試"""

    def test_auth_endpoint_load(self, test_client: TestClient):
        """認證端點負載測試"""
        load_tester = LoadTester()

        test_scenarios = [
            {
                "method": "POST",
                "url": "/api/v1/auth/login",
                "json": {"username": "admin", "password": "admin123"},
            }
        ]

        config = LoadTestConfig(
            concurrent_users=20,
            test_duration=60,
            ramp_up_time=10,
            think_time=2.0,  # 認證請求間隔較長
        )

        result = load_tester.run_load_test(test_scenarios, config)

        assert result.avg_response_time < 200, "認證端點負載測試回應時間超過閾值"
        assert (
            result.successful_requests / result.total_requests
        ) > 0.95, "認證端點成功率過低"

        print(
            f"✅ 認證端點負載測試通過 - 平均回應時間: {result.avg_response_time:.1f}ms"
        )

    def test_data_api_load(self, test_client: TestClient, auth_headers: Dict[str, str]):
        """資料 API 負載測試"""
        load_tester = LoadTester()

        test_scenarios = [
            {"method": "GET", "url": "/api/v1/data/", "headers": auth_headers},
            {"method": "GET", "url": "/api/v1/data/sources", "headers": auth_headers},
            {
                "method": "GET",
                "url": "/api/v1/data/quality/summary",
                "headers": auth_headers,
            },
        ]

        config = LoadTestConfig(
            concurrent_users=30, test_duration=90, ramp_up_time=15, think_time=1.0
        )

        result = load_tester.run_load_test(test_scenarios, config, auth_headers)

        assert result.avg_response_time < 150, "資料 API 負載測試回應時間超過閾值"
        assert result.throughput > 25, "資料 API 吞吐量過低"

        print(f"✅ 資料 API 負載測試通過 - 吞吐量: {result.throughput:.1f} req/s")
