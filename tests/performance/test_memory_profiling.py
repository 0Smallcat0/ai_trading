"""
記憶體分析測試

此模組測試 API 的記憶體使用情況，檢測記憶體洩漏和優化記憶體使用。
"""

import pytest
import gc
import time
from typing import Dict, List, Any

from fastapi.testclient import TestClient

from tests.performance.utils.memory_profiler import MemoryProfiler
from tests.performance.utils.report_generator import ReportGenerator


@pytest.mark.performance
@pytest.mark.memory_test
class TestMemoryProfiling:
    """記憶體分析測試類"""

    def test_api_memory_usage_baseline(
        self, test_client: TestClient, auth_headers: Dict[str, str]
    ):
        """測試 API 基線記憶體使用"""
        memory_profiler = MemoryProfiler(leak_threshold=5.0)  # 5MB/hour

        def api_calls():
            """執行一系列 API 調用"""
            test_client.get("/health")
            test_client.get("/api/info")
            test_client.get("/api/v1/data/", headers=auth_headers)
            test_client.get("/api/v1/strategies/", headers=auth_headers)

        # 測量記憶體使用
        result, memory_growth, peak_memory = memory_profiler.measure_memory_usage(
            api_calls
        )

        # 驗證記憶體使用合理
        assert memory_growth < 10, f"API 調用記憶體增長 {memory_growth:.1f}MB 過大"
        assert peak_memory < 50, f"峰值記憶體使用 {peak_memory:.1f}MB 過大"

        print(f"✅ API 基線記憶體測試通過:")
        print(f"   記憶體增長: {memory_growth:.1f}MB")
        print(f"   峰值記憶體: {peak_memory:.1f}MB")

    def test_memory_leak_detection_simple(
        self, test_client: TestClient, auth_headers: Dict[str, str]
    ):
        """簡單記憶體洩漏檢測"""
        memory_profiler = MemoryProfiler(leak_threshold=2.0)  # 2MB/hour

        def single_api_call():
            """單個 API 調用"""
            response = test_client.get("/api/v1/data/", headers=auth_headers)
            return response.status_code

        # 執行循環測試檢測記憶體洩漏
        result = memory_profiler.detect_memory_leaks_in_loop(
            single_api_call, iterations=100
        )

        # 驗證沒有記憶體洩漏
        assert (
            not result.leak_detected
        ), f"檢測到記憶體洩漏: {result.memory_growth_rate:.2f}MB/h"
        assert (
            result.memory_growth < 20
        ), f"記憶體增長 {result.memory_growth:.1f}MB 過大"

        print(f"✅ 簡單記憶體洩漏檢測通過:")
        print(f"   記憶體增長率: {result.memory_growth_rate:.2f}MB/h")
        print(f"   總記憶體增長: {result.memory_growth:.1f}MB")
        print(f"   峰值記憶體: {result.peak_memory:.1f}MB")

    def test_memory_leak_detection_complex(
        self, test_client: TestClient, auth_headers: Dict[str, str]
    ):
        """複雜記憶體洩漏檢測 - 多種 API 調用"""
        memory_profiler = MemoryProfiler(leak_threshold=3.0)

        def complex_api_calls():
            """複雜的 API 調用序列"""
            # 認證相關
            login_data = {"username": "admin", "password": "admin123"}
            test_client.post("/api/v1/auth/login", json=login_data)

            # 資料管理
            test_client.get("/api/v1/data/", headers=auth_headers)
            test_client.get("/api/v1/data/sources", headers=auth_headers)

            # 策略管理
            test_client.get("/api/v1/strategies/", headers=auth_headers)
            test_client.get("/api/v1/strategies/types", headers=auth_headers)

            # AI 模型
            test_client.get("/api/v1/models/", headers=auth_headers)

            # 強制垃圾回收
            gc.collect()

        result = memory_profiler.detect_memory_leaks_in_loop(
            complex_api_calls, iterations=50  # 較少迭代但更複雜
        )

        assert not result.leak_detected, f"複雜 API 調用檢測到記憶體洩漏"
        assert result.memory_growth < 30, f"複雜 API 調用記憶體增長過大"

        print(f"✅ 複雜記憶體洩漏檢測通過:")
        print(f"   記憶體增長率: {result.memory_growth_rate:.2f}MB/h")
        print(f"   總記憶體增長: {result.memory_growth:.1f}MB")

    def test_memory_usage_under_load(
        self, test_client: TestClient, auth_headers: Dict[str, str]
    ):
        """負載下的記憶體使用測試"""
        memory_profiler = MemoryProfiler(leak_threshold=5.0)

        # 開始記憶體監控
        memory_profiler.start_monitoring(interval=2.0)

        try:
            # 模擬負載
            for i in range(200):
                test_client.get("/health")
                test_client.get("/api/v1/data/", headers=auth_headers)

                # 每 50 次請求強制垃圾回收
                if i % 50 == 0:
                    gc.collect()
                    time.sleep(0.1)  # 讓監控器記錄

        finally:
            result = memory_profiler.stop_monitoring()

        # 驗證負載下記憶體使用
        assert not result.leak_detected, "負載下檢測到記憶體洩漏"
        assert (
            result.memory_growth < 50
        ), f"負載下記憶體增長 {result.memory_growth:.1f}MB 過大"

        print(f"✅ 負載下記憶體測試通過:")
        print(f"   測試時長: {result.duration:.1f}s")
        print(f"   記憶體增長: {result.memory_growth:.1f}MB")
        print(f"   峰值記憶體: {result.peak_memory:.1f}MB")

    def test_memory_profiling_specific_endpoints(
        self, test_client: TestClient, auth_headers: Dict[str, str]
    ):
        """特定端點記憶體分析"""
        memory_profiler = MemoryProfiler()

        endpoints_to_test = [
            ("健康檢查", lambda: test_client.get("/health")),
            (
                "資料管理",
                lambda: test_client.get("/api/v1/data/", headers=auth_headers),
            ),
            (
                "策略管理",
                lambda: test_client.get("/api/v1/strategies/", headers=auth_headers),
            ),
            (
                "AI 模型",
                lambda: test_client.get("/api/v1/models/", headers=auth_headers),
            ),
        ]

        for endpoint_name, api_call in endpoints_to_test:
            # 測量單次調用的記憶體使用
            result, memory_growth, peak_memory = memory_profiler.measure_memory_usage(
                api_call
            )

            # 驗證記憶體使用合理
            assert (
                memory_growth < 5
            ), f"{endpoint_name} 記憶體增長 {memory_growth:.1f}MB 過大"
            assert (
                peak_memory < 20
            ), f"{endpoint_name} 峰值記憶體 {peak_memory:.1f}MB 過大"

            print(f"✅ {endpoint_name} 記憶體分析:")
            print(f"   記憶體增長: {memory_growth:.1f}MB")
            print(f"   峰值記憶體: {peak_memory:.1f}MB")

    def test_long_running_memory_stability(
        self, test_client: TestClient, auth_headers: Dict[str, str]
    ):
        """長時間運行記憶體穩定性測試"""
        memory_profiler = MemoryProfiler(leak_threshold=1.0)  # 嚴格的閾值

        # 開始長時間監控
        memory_profiler.start_monitoring(interval=5.0)

        try:
            # 模擬長時間運行
            for i in range(300):  # 300 次請求
                test_client.get("/health")

                if i % 10 == 0:
                    test_client.get("/api/v1/data/", headers=auth_headers)

                if i % 20 == 0:
                    gc.collect()

                # 短暫暫停
                time.sleep(0.1)

        finally:
            result = memory_profiler.stop_monitoring()

        # 長時間運行的記憶體穩定性要求
        assert not result.leak_detected, f"長時間運行檢測到記憶體洩漏"
        assert (
            result.memory_growth_rate < 1.0
        ), f"記憶體增長率 {result.memory_growth_rate:.2f}MB/h 過高"

        print(f"✅ 長時間記憶體穩定性測試通過:")
        print(f"   運行時長: {result.duration:.1f}s")
        print(f"   記憶體增長率: {result.memory_growth_rate:.2f}MB/h")
        print(f"   總記憶體增長: {result.memory_growth:.1f}MB")

    def test_memory_cleanup_after_errors(
        self, test_client: TestClient, auth_headers: Dict[str, str]
    ):
        """錯誤後記憶體清理測試"""
        memory_profiler = MemoryProfiler()

        def api_calls_with_errors():
            """包含錯誤的 API 調用"""
            # 正常調用
            test_client.get("/health")

            # 錯誤調用（應該返回 404）
            test_client.get("/api/v1/nonexistent")

            # 未授權調用
            test_client.get("/api/v1/data/")  # 沒有認證標頭

            # 正常調用
            test_client.get("/api/v1/data/", headers=auth_headers)

            gc.collect()

        result = memory_profiler.detect_memory_leaks_in_loop(
            api_calls_with_errors, iterations=100
        )

        # 即使有錯誤也不應該洩漏記憶體
        assert not result.leak_detected, "錯誤處理後檢測到記憶體洩漏"
        assert result.memory_growth < 25, "錯誤處理記憶體增長過大"

        print(f"✅ 錯誤後記憶體清理測試通過:")
        print(f"   記憶體增長: {result.memory_growth:.1f}MB")
        print(f"   記憶體增長率: {result.memory_growth_rate:.2f}MB/h")

    def test_generate_memory_report(
        self, test_client: TestClient, auth_headers: Dict[str, str]
    ):
        """生成記憶體測試報告"""
        report_generator = ReportGenerator()
        memory_profiler = MemoryProfiler()
        results = []

        # 執行多個記憶體測試
        test_cases = [
            ("基線測試", lambda: test_client.get("/health"), 50),
            (
                "資料 API",
                lambda: test_client.get("/api/v1/data/", headers=auth_headers),
                30,
            ),
            (
                "策略 API",
                lambda: test_client.get("/api/v1/strategies/", headers=auth_headers),
                30,
            ),
        ]

        for test_name, api_call, iterations in test_cases:
            result = memory_profiler.detect_memory_leaks_in_loop(
                api_call, iterations=iterations
            )
            result.test_name = test_name
            results.append(result)

        # 生成報告
        html_report = report_generator.generate_memory_report(
            results, "memory_test_report", "html"
        )
        json_report = report_generator.generate_memory_report(
            results, "memory_test_report", "json"
        )

        print(f"✅ 記憶體測試報告已生成:")
        print(f"   HTML: {html_report}")
        print(f"   JSON: {json_report}")

        # 驗證報告檔案
        import os

        assert os.path.exists(html_report), "HTML 報告檔案不存在"
        assert os.path.exists(json_report), "JSON 報告檔案不存在"


@pytest.mark.performance
@pytest.mark.memory_test
class TestMemoryOptimization:
    """記憶體優化測試"""

    def test_garbage_collection_effectiveness(
        self, test_client: TestClient, auth_headers: Dict[str, str]
    ):
        """垃圾回收效果測試"""
        memory_profiler = MemoryProfiler()

        # 記錄初始記憶體
        initial_result, _, _ = memory_profiler.measure_memory_usage(lambda: None)

        # 執行大量 API 調用
        def heavy_api_usage():
            for _ in range(100):
                test_client.get("/api/v1/data/", headers=auth_headers)

        # 測量大量調用後的記憶體
        after_calls_result, memory_growth, _ = memory_profiler.measure_memory_usage(
            heavy_api_usage
        )

        # 強制垃圾回收
        gc.collect()
        time.sleep(1)  # 等待垃圾回收完成

        # 測量垃圾回收後的記憶體
        after_gc_result, _, _ = memory_profiler.measure_memory_usage(lambda: None)

        # 計算垃圾回收效果
        memory_recovered = memory_growth - (after_gc_result - initial_result)
        recovery_rate = (
            (memory_recovered / memory_growth) * 100 if memory_growth > 0 else 100
        )

        print(f"✅ 垃圾回收效果測試:")
        print(f"   記憶體增長: {memory_growth:.1f}MB")
        print(f"   記憶體回收: {memory_recovered:.1f}MB")
        print(f"   回收率: {recovery_rate:.1f}%")

        # 驗證垃圾回收效果
        assert recovery_rate > 70, f"垃圾回收效果不佳，回收率僅 {recovery_rate:.1f}%"

    @pytest.mark.parametrize(
        "endpoint",
        [
            "/health",
            "/api/info",
            "/api/v1/data/",
            "/api/v1/strategies/",
        ],
    )
    def test_endpoint_memory_efficiency(
        self, test_client: TestClient, auth_headers: Dict[str, str], endpoint: str
    ):
        """端點記憶體效率測試"""
        memory_profiler = MemoryProfiler()

        def api_call():
            headers = auth_headers if endpoint.startswith("/api/v1/") else None
            return test_client.get(endpoint, headers=headers)

        # 測量記憶體效率
        result, memory_growth, peak_memory = memory_profiler.measure_memory_usage(
            api_call
        )

        # 記憶體效率標準
        assert memory_growth < 2, f"{endpoint} 記憶體增長 {memory_growth:.1f}MB 過大"
        assert peak_memory < 10, f"{endpoint} 峰值記憶體 {peak_memory:.1f}MB 過大"

        print(f"✅ {endpoint} 記憶體效率測試通過:")
        print(f"   記憶體增長: {memory_growth:.1f}MB")
        print(f"   峰值記憶體: {peak_memory:.1f}MB")
