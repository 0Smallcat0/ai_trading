"""
API 版本控制效能測試

此模組包含 API 版本控制相關功能的效能測試，驗證在高負載情況下
系統的響應時間和穩定性。
"""

import pytest
import asyncio
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

# 導入被測試的模組
from src.api.routers.versioning import router
from src.api.models.versioning import VersionStatusEnum
from src.services.version_service import VersionService
from src.tools.migration.migration_manager import MigrationManager


# 創建測試應用
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestVersioningPerformance:
    """版本控制效能測試類"""

    def setup_method(self):
        """測試前置設定"""
        self.test_user = "test_user"

        # Mock 認證和權限
        self.auth_patcher = patch("src.api.routers.versioning.get_current_user")
        self.mock_auth = self.auth_patcher.start()
        self.mock_auth.return_value = self.test_user

        self.perm_patcher = patch("src.api.routers.versioning.require_permissions")
        self.mock_perm = self.perm_patcher.start()
        self.mock_perm.return_value = None

        # 效能測試目標
        self.target_response_time = 0.1  # 100ms
        self.concurrent_requests = 20
        self.large_dataset_size = 1000

    def teardown_method(self):
        """測試後清理"""
        self.auth_patcher.stop()
        self.perm_patcher.stop()

    def measure_response_time(self, func, *args, **kwargs):
        """測量響應時間"""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        response_time = end_time - start_time
        return result, response_time

    def measure_concurrent_requests(self, func, request_count=20):
        """測量並發請求效能"""
        response_times = []
        success_count = 0
        error_count = 0

        with ThreadPoolExecutor(max_workers=request_count) as executor:
            futures = [executor.submit(func) for _ in range(request_count)]

            for future in as_completed(futures):
                try:
                    start_time = time.time()
                    result = future.result()
                    end_time = time.time()

                    response_time = end_time - start_time
                    response_times.append(response_time)

                    if hasattr(result, "status_code") and result.status_code == 200:
                        success_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    error_count += 1
                    print(f"請求失敗: {e}")

        return {
            "response_times": response_times,
            "success_count": success_count,
            "error_count": error_count,
            "avg_response_time": (
                statistics.mean(response_times) if response_times else 0
            ),
            "max_response_time": max(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
        }

    # ==================== 版本管理效能測試 ====================

    @patch("src.api.routers.versioning.version_service")
    def test_create_version_performance(self, mock_service):
        """測試創建版本效能"""
        mock_service.create_version.return_value = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "title": "測試版本",
            "status": VersionStatusEnum.DEVELOPMENT.value,
        }

        version_data = {
            "version": "1.0.0",
            "title": "效能測試版本",
            "status": VersionStatusEnum.DEVELOPMENT.value,
        }

        # 單次請求效能測試
        response, response_time = self.measure_response_time(
            client.post, "/api/v1/versions/", json=version_data
        )

        assert response.status_code == 200
        assert (
            response_time < self.target_response_time
        ), f"響應時間 {response_time:.3f}s 超過目標 {self.target_response_time}s"

        print(f"創建版本響應時間: {response_time:.3f}s")

    @patch("src.api.routers.versioning.version_service")
    def test_list_versions_performance(self, mock_service):
        """測試查詢版本列表效能"""
        # 模擬大量版本數據
        versions = []
        for i in range(self.large_dataset_size):
            versions.append(
                {
                    "version": {"major": 1, "minor": i // 100, "patch": i % 100},
                    "title": f"版本 1.{i // 100}.{i % 100}",
                    "status": VersionStatusEnum.STABLE.value,
                }
            )

        mock_service.list_versions.return_value = {
            "versions": versions[:20],  # 分頁返回
            "total": len(versions),
            "page": 1,
            "page_size": 20,
            "total_pages": len(versions) // 20,
            "has_next": True,
            "has_prev": False,
        }

        # 單次請求效能測試
        response, response_time = self.measure_response_time(
            client.get, "/api/v1/versions/"
        )

        assert response.status_code == 200
        assert (
            response_time < self.target_response_time
        ), f"響應時間 {response_time:.3f}s 超過目標 {self.target_response_time}s"

        print(f"查詢版本列表響應時間: {response_time:.3f}s")

    @patch("src.api.routers.versioning.version_service")
    def test_get_version_performance(self, mock_service):
        """測試獲取版本詳情效能"""
        mock_service.get_version.return_value = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "title": "版本 1.0.0",
            "status": VersionStatusEnum.STABLE.value,
            "release_date": "2024-01-01T00:00:00",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # 單次請求效能測試
        response, response_time = self.measure_response_time(
            client.get, "/api/v1/versions/1.0.0"
        )

        assert response.status_code == 200
        assert (
            response_time < self.target_response_time
        ), f"響應時間 {response_time:.3f}s 超過目標 {self.target_response_time}s"

        print(f"獲取版本詳情響應時間: {response_time:.3f}s")

    @patch("src.api.routers.versioning.version_service")
    def test_update_version_performance(self, mock_service):
        """測試更新版本效能"""
        mock_service.update_version.return_value = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "title": "更新後的版本",
            "status": VersionStatusEnum.STABLE.value,
        }

        update_data = {
            "title": "更新後的版本",
            "status": VersionStatusEnum.STABLE.value,
        }

        # 單次請求效能測試
        response, response_time = self.measure_response_time(
            client.put, "/api/v1/versions/1.0.0", json=update_data
        )

        assert response.status_code == 200
        assert (
            response_time < self.target_response_time
        ), f"響應時間 {response_time:.3f}s 超過目標 {self.target_response_time}s"

        print(f"更新版本響應時間: {response_time:.3f}s")

    # ==================== 並發效能測試 ====================

    @patch("src.api.routers.versioning.version_service")
    def test_concurrent_version_requests(self, mock_service):
        """測試並發版本請求效能"""
        mock_service.get_version.return_value = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "title": "版本 1.0.0",
            "status": VersionStatusEnum.STABLE.value,
        }

        def make_request():
            return client.get("/api/v1/versions/1.0.0")

        # 並發請求測試
        results = self.measure_concurrent_requests(
            make_request, self.concurrent_requests
        )

        # 驗證結果
        assert (
            results["success_count"] >= self.concurrent_requests * 0.95
        ), "成功率低於 95%"
        assert (
            results["avg_response_time"] < self.target_response_time
        ), f"平均響應時間 {results['avg_response_time']:.3f}s 超過目標"
        assert (
            results["max_response_time"] < self.target_response_time * 2
        ), "最大響應時間過長"

        print(f"並發請求結果:")
        print(f"  成功數量: {results['success_count']}/{self.concurrent_requests}")
        print(f"  平均響應時間: {results['avg_response_time']:.3f}s")
        print(f"  最大響應時間: {results['max_response_time']:.3f}s")
        print(f"  最小響應時間: {results['min_response_time']:.3f}s")

    # ==================== 相容性檢查效能測試 ====================

    @patch("src.api.routers.versioning.version_service")
    def test_compatibility_check_performance(self, mock_service):
        """測試相容性檢查效能"""
        mock_service.check_compatibility.return_value = {
            "check_result": {
                "source_version": "1.0.0",
                "target_version": "1.1.0",
                "compatibility_level": "backward",
                "is_compatible": True,
                "breaking_changes": [],
                "warnings": [],
                "recommendations": [],
            },
            "recommendations": [],
            "migration_plan": None,
        }

        # 單次請求效能測試
        response, response_time = self.measure_response_time(
            client.post,
            "/api/v1/versions/compatibility/check",
            params={"source_version": "1.0.0", "target_version": "1.1.0"},
        )

        assert response.status_code == 200
        assert (
            response_time < self.target_response_time
        ), f"響應時間 {response_time:.3f}s 超過目標 {self.target_response_time}s"

        print(f"相容性檢查響應時間: {response_time:.3f}s")

    # ==================== 遷移管理效能測試 ====================

    @patch("src.api.routers.versioning.migration_manager")
    def test_migration_operations_performance(self, mock_manager):
        """測試遷移操作效能"""
        # Mock 遷移管理器
        mock_plan = Mock()
        mock_plan.migration_id = "test-migration-id"
        mock_plan.model_dump.return_value = {
            "migration_id": "test-migration-id",
            "name": "效能測試遷移",
        }

        mock_manager.create_migration_plan = AsyncMock(return_value=mock_plan)
        mock_manager.execute_migration = AsyncMock(return_value={"success": True})
        mock_manager.get_migration_status = AsyncMock(
            return_value={"status": "completed"}
        )

        # 測試創建遷移計劃效能
        response, response_time = self.measure_response_time(
            client.post,
            "/api/v1/versions/migrations",
            params={
                "source_version": "1.0.0",
                "target_version": "2.0.0",
                "name": "效能測試遷移",
            },
        )

        assert response.status_code == 200
        assert (
            response_time < self.target_response_time
        ), f"創建遷移計劃響應時間 {response_time:.3f}s 超過目標"

        print(f"創建遷移計劃響應時間: {response_time:.3f}s")

        # 測試獲取遷移狀態效能
        response, response_time = self.measure_response_time(
            client.get, "/api/v1/versions/migrations/test-id/status"
        )

        assert response.status_code == 200
        assert (
            response_time < self.target_response_time
        ), f"獲取遷移狀態響應時間 {response_time:.3f}s 超過目標"

        print(f"獲取遷移狀態響應時間: {response_time:.3f}s")

    # ==================== 大數據量測試 ====================

    @patch("src.api.routers.versioning.migration_manager")
    def test_large_migration_list_performance(self, mock_manager):
        """測試大量遷移記錄查詢效能"""
        # 模擬大量遷移記錄
        migrations = []
        for i in range(self.large_dataset_size):
            migrations.append(
                {
                    "migration_id": f"migration-{i}",
                    "name": f"遷移 {i}",
                    "status": "completed" if i % 2 == 0 else "pending",
                }
            )

        mock_manager.list_migrations = AsyncMock(
            return_value=migrations[:50]
        )  # 限制返回數量

        # 效能測試
        response, response_time = self.measure_response_time(
            client.get, "/api/v1/versions/migrations"
        )

        assert response.status_code == 200
        assert (
            response_time < self.target_response_time
        ), f"大數據量查詢響應時間 {response_time:.3f}s 超過目標"

        print(f"大數據量遷移記錄查詢響應時間: {response_time:.3f}s")

    # ==================== 記憶體使用測試 ====================

    def test_memory_usage_under_load(self):
        """測試高負載下的記憶體使用"""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 執行大量操作
        with patch("src.api.routers.versioning.version_service") as mock_service:
            mock_service.list_versions.return_value = {
                "versions": [],
                "total": 0,
                "page": 1,
                "page_size": 20,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
            }

            # 執行 100 次請求
            for _ in range(100):
                client.get("/api/v1/versions/")

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"初始記憶體使用: {initial_memory:.2f} MB")
        print(f"最終記憶體使用: {final_memory:.2f} MB")
        print(f"記憶體增長: {memory_increase:.2f} MB")

        # 記憶體增長不應超過 50MB
        assert memory_increase < 50, f"記憶體增長過多: {memory_increase:.2f} MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
