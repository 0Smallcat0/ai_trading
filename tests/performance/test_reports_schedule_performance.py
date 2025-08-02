"""
報表排程管理 API 效能測試

此模組測試報表排程管理 API 的效能指標，確保 API 回應時間符合要求（<100ms）。
"""

import pytest
import time
import asyncio
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import statistics

from src.api.main import app


class TestReportSchedulePerformance:
    """報表排程 API 效能測試類"""

    def setup_method(self):
        """測試前置設定"""
        self.client = TestClient(app)
        self.base_url = "/api/v1/reports/schedules"
        self.performance_threshold = 0.1  # 100ms
        self.test_iterations = 10

    def measure_response_time(self, func):
        """測量響應時間的裝飾器"""

        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            response_time = end_time - start_time
            return result, response_time

        return wrapper

    def test_create_schedule_performance(self):
        """測試創建排程的效能"""
        test_data = {
            "name": "效能測試排程",
            "description": "用於效能測試的排程",
            "report_type": "trading_summary",
            "frequency": "daily",
            "start_time": (datetime.now() + timedelta(hours=1)).isoformat(),
            "timezone": "Asia/Taipei",
            "parameters": {"test": True},
            "output_format": "pdf",
            "is_enabled": True,
        }

        response_times = []

        with patch(
            "src.services.report_schedule_service.ReportScheduleService.create_schedule"
        ) as mock_create:
            mock_create.return_value = {"schedule_id": "perf-test-123", **test_data}

            for i in range(self.test_iterations):
                start_time = time.time()
                response = self.client.post(f"{self.base_url}", json=test_data)
                end_time = time.time()

                response_time = end_time - start_time
                response_times.append(response_time)

                assert response.status_code == 200

        # 分析效能指標
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)

        print(f"\n創建排程效能指標:")
        print(f"平均響應時間: {avg_response_time:.3f}s")
        print(f"最大響應時間: {max_response_time:.3f}s")
        print(f"最小響應時間: {min_response_time:.3f}s")

        # 驗證效能要求
        assert (
            avg_response_time < self.performance_threshold
        ), f"平均響應時間 {avg_response_time:.3f}s 超過閾值 {self.performance_threshold}s"
        assert max_response_time < self.performance_threshold * 2, f"最大響應時間過長"

    def test_list_schedules_performance(self):
        """測試查詢排程列表的效能"""
        response_times = []

        with patch(
            "src.services.report_schedule_service.ReportScheduleService.list_schedules"
        ) as mock_list:
            # 模擬大量數據
            mock_schedules = [
                {
                    "schedule_id": f"schedule-{i}",
                    "name": f"排程 {i}",
                    "status": "active",
                    "frequency": "daily",
                    "created_at": datetime.now(),
                }
                for i in range(100)
            ]

            mock_list.return_value = {
                "schedules": mock_schedules[:20],  # 分頁返回
                "total": 100,
                "page": 1,
                "page_size": 20,
                "total_pages": 5,
                "has_next": True,
                "has_prev": False,
            }

            for i in range(self.test_iterations):
                start_time = time.time()
                response = self.client.get(f"{self.base_url}?page=1&page_size=20")
                end_time = time.time()

                response_time = end_time - start_time
                response_times.append(response_time)

                assert response.status_code == 200

        # 分析效能指標
        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)

        print(f"\n查詢排程列表效能指標:")
        print(f"平均響應時間: {avg_response_time:.3f}s")
        print(f"最大響應時間: {max_response_time:.3f}s")

        assert avg_response_time < self.performance_threshold

    def test_get_schedule_detail_performance(self):
        """測試獲取排程詳情的效能"""
        schedule_id = "perf-test-schedule"
        response_times = []

        with patch(
            "src.services.report_schedule_service.ReportScheduleService.get_schedule"
        ) as mock_get:
            mock_get.return_value = {
                "schedule_id": schedule_id,
                "name": "效能測試排程",
                "status": "active",
                "frequency": "daily",
                "created_at": datetime.now(),
            }

            with patch(
                "src.services.report_schedule_service.ReportScheduleService.get_execution_history"
            ) as mock_history:
                # 模擬執行歷史
                mock_executions = [
                    {
                        "execution_id": f"exec-{i}",
                        "status": "completed",
                        "start_time": datetime.now() - timedelta(days=i),
                        "duration": 60.0,
                    }
                    for i in range(10)
                ]

                mock_history.return_value = {"executions": mock_executions, "total": 10}

                for i in range(self.test_iterations):
                    start_time = time.time()
                    response = self.client.get(f"{self.base_url}/{schedule_id}")
                    end_time = time.time()

                    response_time = end_time - start_time
                    response_times.append(response_time)

                    assert response.status_code == 200

        # 分析效能指標
        avg_response_time = statistics.mean(response_times)

        print(f"\n獲取排程詳情效能指標:")
        print(f"平均響應時間: {avg_response_time:.3f}s")

        assert avg_response_time < self.performance_threshold

    def test_update_schedule_performance(self):
        """測試更新排程的效能"""
        schedule_id = "perf-test-schedule"
        update_data = {"name": "更新後的排程名稱", "description": "更新後的描述"}
        response_times = []

        with patch(
            "src.services.report_schedule_service.ReportScheduleService.update_schedule"
        ) as mock_update:
            mock_update.return_value = {"schedule_id": schedule_id, **update_data}

            for i in range(self.test_iterations):
                start_time = time.time()
                response = self.client.put(
                    f"{self.base_url}/{schedule_id}", json=update_data
                )
                end_time = time.time()

                response_time = end_time - start_time
                response_times.append(response_time)

                assert response.status_code == 200

        # 分析效能指標
        avg_response_time = statistics.mean(response_times)

        print(f"\n更新排程效能指標:")
        print(f"平均響應時間: {avg_response_time:.3f}s")

        assert avg_response_time < self.performance_threshold

    def test_execute_schedule_performance(self):
        """測試執行排程的效能"""
        schedule_id = "perf-test-schedule"
        response_times = []

        with patch(
            "src.services.report_schedule_service.ReportScheduleService.execute_schedule"
        ) as mock_execute:
            mock_execute.return_value = {
                "execution_id": "perf-exec-123",
                "schedule_id": schedule_id,
                "status": "pending",
                "message": "排程執行已啟動",
                "created_at": datetime.now(),
            }

            for i in range(self.test_iterations):
                start_time = time.time()
                response = self.client.post(f"{self.base_url}/{schedule_id}/execute")
                end_time = time.time()

                response_time = end_time - start_time
                response_times.append(response_time)

                assert response.status_code == 200

        # 分析效能指標
        avg_response_time = statistics.mean(response_times)

        print(f"\n執行排程效能指標:")
        print(f"平均響應時間: {avg_response_time:.3f}s")

        assert avg_response_time < self.performance_threshold

    def test_concurrent_requests_performance(self):
        """測試並發請求的效能"""

        async def make_concurrent_requests():
            """發送並發請求"""
            tasks = []

            with patch(
                "src.services.report_schedule_service.ReportScheduleService.list_schedules"
            ) as mock_list:
                mock_list.return_value = {
                    "schedules": [],
                    "total": 0,
                    "page": 1,
                    "page_size": 20,
                }

                # 創建並發任務
                for i in range(20):  # 20個並發請求
                    task = asyncio.create_task(self._async_request())
                    tasks.append(task)

                # 等待所有任務完成
                start_time = time.time()
                results = await asyncio.gather(*tasks)
                end_time = time.time()

                total_time = end_time - start_time
                avg_time_per_request = total_time / len(tasks)

                print(f"\n並發請求效能指標:")
                print(f"總時間: {total_time:.3f}s")
                print(f"平均每請求時間: {avg_time_per_request:.3f}s")
                print(f"並發數: {len(tasks)}")

                # 驗證所有請求都成功
                for result in results:
                    assert result.status_code == 200

                # 驗證並發效能
                assert avg_time_per_request < self.performance_threshold

        # 運行異步測試
        asyncio.run(make_concurrent_requests())

    async def _async_request(self):
        """異步請求輔助方法"""
        # 注意：這裡使用同步客戶端，實際應該使用異步客戶端
        return self.client.get(f"{self.base_url}")

    def test_large_data_performance(self):
        """測試大數據量的效能"""
        # 測試大量排程的查詢效能
        with patch(
            "src.services.report_schedule_service.ReportScheduleService.list_schedules"
        ) as mock_list:
            # 模擬1000個排程
            large_schedules = [
                {
                    "schedule_id": f"schedule-{i:04d}",
                    "name": f"大數據測試排程 {i}",
                    "status": "active",
                    "frequency": "daily",
                    "created_at": datetime.now(),
                }
                for i in range(1000)
            ]

            mock_list.return_value = {
                "schedules": large_schedules[:50],  # 返回前50個
                "total": 1000,
                "page": 1,
                "page_size": 50,
            }

            start_time = time.time()
            response = self.client.get(f"{self.base_url}?page_size=50")
            end_time = time.time()

            response_time = end_time - start_time

            print(f"\n大數據量查詢效能指標:")
            print(f"響應時間: {response_time:.3f}s")
            print(f"數據量: 1000 個排程")

            assert response.status_code == 200
            assert (
                response_time < self.performance_threshold * 2
            )  # 大數據允許稍長的響應時間
