"""
API 版本控制測試

此模組包含 API 版本控制相關功能的單元測試，包括版本管理、
相容性檢查、版本協商、遷移管理等功能的測試。
"""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

# 導入被測試的模組
from src.api.routers.versioning import router
from src.api.models.versioning import (
    VersionStatusEnum,
    VersionCreateRequest,
    VersionUpdateRequest,
    VersionNegotiationRequest,
    SemanticVersion,
    APIVersion,
)
from src.services.version_service import VersionService
from src.tools.migration.migration_manager import MigrationManager


# 創建測試應用
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestVersioningAPI:
    """版本控制 API 測試類"""

    def setup_method(self):
        """測試前置設定"""
        self.test_user = "test_user"
        self.test_version = "1.0.0"

        # Mock 認證
        self.auth_patcher = patch("src.api.routers.versioning.get_current_user")
        self.mock_auth = self.auth_patcher.start()
        self.mock_auth.return_value = self.test_user

        # Mock 權限檢查
        self.perm_patcher = patch("src.api.routers.versioning.require_permissions")
        self.mock_perm = self.perm_patcher.start()
        self.mock_perm.return_value = None

    def teardown_method(self):
        """測試後清理"""
        self.auth_patcher.stop()
        self.perm_patcher.stop()

    # ==================== 版本管理測試 ====================

    @patch("src.api.routers.versioning.version_service")
    def test_create_version_success(self, mock_service):
        """測試創建版本成功"""
        # 準備測試資料
        version_data = {
            "version": self.test_version,
            "title": "測試版本",
            "description": "測試版本描述",
            "status": VersionStatusEnum.DEVELOPMENT.value,
        }

        mock_service.create_version.return_value = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "title": "測試版本",
            "status": VersionStatusEnum.DEVELOPMENT.value,
            "created_at": datetime.now().isoformat(),
        }

        # 執行測試
        response = client.post("/api/v1/versions/", json=version_data)

        # 驗證結果
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "版本創建成功"
        assert "data" in data

        # 驗證服務調用
        mock_service.create_version.assert_called_once()

    @patch("src.api.routers.versioning.version_service")
    def test_create_version_invalid_data(self, mock_service):
        """測試創建版本參數無效"""
        mock_service.create_version.side_effect = ValueError("無效的版本格式")

        version_data = {"version": "invalid_version", "title": "測試版本"}

        response = client.post("/api/v1/versions/", json=version_data)

        assert response.status_code == 400
        data = response.json()
        assert "無效的版本格式" in data["detail"]

    @patch("src.api.routers.versioning.version_service")
    def test_list_versions_success(self, mock_service):
        """測試查詢版本列表成功"""
        mock_service.list_versions.return_value = {
            "versions": [
                {
                    "version": {"major": 1, "minor": 0, "patch": 0},
                    "title": "版本 1.0.0",
                    "status": VersionStatusEnum.STABLE.value,
                }
            ],
            "total": 1,
            "page": 1,
            "page_size": 20,
            "total_pages": 1,
            "has_next": False,
            "has_prev": False,
        }

        response = client.get("/api/v1/versions/")

        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert data["total"] == 1

    @patch("src.api.routers.versioning.version_service")
    def test_get_version_success(self, mock_service):
        """測試獲取版本詳情成功"""
        mock_service.get_version.return_value = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "title": "版本 1.0.0",
            "status": VersionStatusEnum.STABLE.value,
            "release_date": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        response = client.get(f"/api/v1/versions/{self.test_version}")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "permissions" in data

    @patch("src.api.routers.versioning.version_service")
    def test_get_version_not_found(self, mock_service):
        """測試獲取不存在的版本"""
        mock_service.get_version.return_value = None

        response = client.get("/api/v1/versions/999.0.0")

        assert response.status_code == 404
        data = response.json()
        assert "不存在" in data["detail"]

    @patch("src.api.routers.versioning.version_service")
    def test_update_version_success(self, mock_service):
        """測試更新版本成功"""
        mock_service.update_version.return_value = {
            "version": {"major": 1, "minor": 0, "patch": 0},
            "title": "更新後的版本",
            "status": VersionStatusEnum.STABLE.value,
        }

        update_data = {
            "title": "更新後的版本",
            "status": VersionStatusEnum.STABLE.value,
        }

        response = client.put(f"/api/v1/versions/{self.test_version}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "版本更新成功"

    @patch("src.api.routers.versioning.version_service")
    def test_delete_version_success(self, mock_service):
        """測試刪除版本成功"""
        mock_service.delete_version.return_value = True

        response = client.delete(f"/api/v1/versions/{self.test_version}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "版本刪除成功"

    # ==================== 版本協商測試 ====================

    @patch("src.api.routers.versioning.version_service")
    def test_negotiate_version_success(self, mock_service):
        """測試版本協商成功"""
        mock_service.negotiate_version.return_value = {
            "selected_version": "1.1.0",
            "available_versions": ["1.0.0", "1.1.0", "2.0.0"],
            "compatibility_warnings": [],
            "migration_required": False,
            "migration_url": None,
        }

        negotiation_data = {
            "client_version": "1.0.0",
            "preferred_version": "1.1.0",
            "supported_versions": ["1.0.0", "1.1.0"],
        }

        response = client.post("/api/v1/versions/negotiate", json=negotiation_data)

        assert response.status_code == 200
        data = response.json()
        assert data["selected_version"] == "1.1.0"
        assert data["migration_required"] is False

    # ==================== 相容性檢查測試 ====================

    @patch("src.api.routers.versioning.version_service")
    def test_check_compatibility_success(self, mock_service):
        """測試相容性檢查成功"""
        mock_service.check_compatibility.return_value = {
            "check_result": {
                "source_version": "1.0.0",
                "target_version": "1.1.0",
                "compatibility_level": "backward",
                "is_compatible": True,
                "breaking_changes": [],
                "warnings": [],
                "recommendations": ["檢查新功能的相容性"],
            },
            "recommendations": ["檢查新功能的相容性"],
            "migration_plan": None,
        }

        response = client.post(
            "/api/v1/versions/compatibility/check",
            params={"source_version": "1.0.0", "target_version": "1.1.0"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["check_result"]["is_compatible"] is True
        assert len(data["recommendations"]) > 0

    @patch("src.api.routers.versioning.version_service")
    def test_check_compatibility_invalid_version(self, mock_service):
        """測試相容性檢查版本無效"""
        mock_service.check_compatibility.side_effect = ValueError("版本不存在")

        response = client.post(
            "/api/v1/versions/compatibility/check",
            params={"source_version": "invalid", "target_version": "1.1.0"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "版本不存在" in data["detail"]

    # ==================== 遷移管理測試 ====================

    @patch("src.api.routers.versioning.migration_manager")
    async def test_create_migration_plan_success(self, mock_manager):
        """測試創建遷移計劃成功"""
        mock_plan = Mock()
        mock_plan.migration_id = "test-migration-id"
        mock_plan.model_dump.return_value = {
            "migration_id": "test-migration-id",
            "name": "測試遷移",
            "source_version": "1.0.0",
            "target_version": "2.0.0",
        }

        mock_manager.create_migration_plan = AsyncMock(return_value=mock_plan)

        response = client.post(
            "/api/v1/versions/migrations",
            params={
                "source_version": "1.0.0",
                "target_version": "2.0.0",
                "name": "測試遷移",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "遷移計劃創建成功"

    @patch("src.api.routers.versioning.migration_manager")
    async def test_execute_migration_success(self, mock_manager):
        """測試執行遷移成功"""
        mock_manager.execute_migration = AsyncMock(
            return_value={
                "success": True,
                "total_steps": 3,
                "success_count": 3,
                "failure_count": 0,
            }
        )

        response = client.post(
            "/api/v1/versions/migrations/test-id/execute", params={"dry_run": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "遷移執行完成"

    @patch("src.api.routers.versioning.migration_manager")
    async def test_rollback_migration_success(self, mock_manager):
        """測試回滾遷移成功"""
        mock_manager.rollback_migration = AsyncMock(
            return_value={"success": True, "success_count": 3, "failure_count": 0}
        )

        response = client.post("/api/v1/versions/migrations/test-id/rollback")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "遷移回滾完成"

    @patch("src.api.routers.versioning.migration_manager")
    async def test_get_migration_status_success(self, mock_manager):
        """測試獲取遷移狀態成功"""
        mock_manager.get_migration_status = AsyncMock(
            return_value={
                "migration_id": "test-id",
                "name": "測試遷移",
                "status": "completed",
                "progress": 100.0,
            }
        )

        response = client.get("/api/v1/versions/migrations/test-id/status")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "completed"

    @patch("src.api.routers.versioning.migration_manager")
    async def test_list_migrations_success(self, mock_manager):
        """測試列出遷移記錄成功"""
        mock_manager.list_migrations = AsyncMock(
            return_value=[
                {"migration_id": "test-id-1", "name": "遷移 1", "status": "completed"},
                {"migration_id": "test-id-2", "name": "遷移 2", "status": "pending"},
            ]
        )

        response = client.get("/api/v1/versions/migrations")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["migrations"]) == 2


class TestSemanticVersion:
    """語義化版本測試類"""

    def test_semantic_version_parsing(self):
        """測試語義化版本解析"""
        # 測試標準版本
        version = SemanticVersion.parse("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease is None
        assert version.build is None

        # 測試預發布版本
        version = SemanticVersion.parse("1.2.3-alpha.1")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.prerelease == "alpha.1"

        # 測試構建版本
        version = SemanticVersion.parse("1.2.3+build.1")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        assert version.build == "build.1"

    def test_semantic_version_comparison(self):
        """測試語義化版本比較"""
        v1 = SemanticVersion.parse("1.0.0")
        v2 = SemanticVersion.parse("1.0.1")
        v3 = SemanticVersion.parse("1.1.0")
        v4 = SemanticVersion.parse("2.0.0")

        assert v1 < v2
        assert v2 < v3
        assert v3 < v4
        assert v1 <= v2
        assert v2 >= v1
        assert v1 != v2
        assert v1 == SemanticVersion.parse("1.0.0")

    def test_semantic_version_string_representation(self):
        """測試語義化版本字符串表示"""
        version = SemanticVersion(major=1, minor=2, patch=3)
        assert str(version) == "1.2.3"

        version = SemanticVersion(major=1, minor=2, patch=3, prerelease="alpha.1")
        assert str(version) == "1.2.3-alpha.1"

        version = SemanticVersion(major=1, minor=2, patch=3, build="build.1")
        assert str(version) == "1.2.3+build.1"

        version = SemanticVersion(
            major=1, minor=2, patch=3, prerelease="alpha.1", build="build.1"
        )
        assert str(version) == "1.2.3-alpha.1+build.1"

    def test_semantic_version_invalid_format(self):
        """測試無效版本格式"""
        with pytest.raises(ValueError):
            SemanticVersion.parse("invalid")

        with pytest.raises(ValueError):
            SemanticVersion.parse("1.2")

        with pytest.raises(ValueError):
            SemanticVersion.parse("1.2.3.4")


if __name__ == "__main__":
    pytest.main([__file__])
