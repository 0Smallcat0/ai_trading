"""
報表排程管理 API 測試

此模組測試報表排程管理相關的 API 端點，包括創建、查詢、更新、刪除、
執行排程等功能的完整測試覆蓋。
"""

import pytest
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from src.api.main import app
from src.api.models.reports import (
    ScheduleFrequencyEnum,
    ScheduleStatusEnum,
    ExecutionStatusEnum,
    ReportTypeEnum,
    ExportFormatEnum,
)


# 模擬認證依賴
def mock_verify_token():
    """模擬 Token 驗證"""
    return {"user_id": "test_user_123", "username": "test_user", "role": "admin"}


def mock_get_current_user():
    """模擬當前用戶"""
    return {"user_id": "test_user_123", "username": "test_user", "role": "admin"}


# 覆蓋認證依賴
app.dependency_overrides = {}


class TestReportScheduleAPI:
    """報表排程 API 測試類"""

    def setup_method(self):
        """測試前置設定"""
        # 覆蓋認證依賴
        from src.api.utils.security import verify_token, get_current_user

        app.dependency_overrides[verify_token] = mock_verify_token
        app.dependency_overrides[get_current_user] = mock_get_current_user

        self.client = TestClient(app)
        self.base_url = "/api/v1/reports/schedules"
        self.test_schedule_data = {
            "name": "每日交易報表",
            "description": "每日自動生成交易摘要報表",
            "report_type": "trading_summary",
            "frequency": "daily",
            "start_time": (datetime.now() + timedelta(hours=1)).isoformat(),
            "timezone": "Asia/Taipei",
            "parameters": {"symbols": ["2330.TW", "2317.TW"], "include_charts": True},
            "output_format": "pdf",
            "is_enabled": True,
            "tags": ["daily", "trading"],
        }

    def test_create_schedule_success(self):
        """測試成功創建排程"""
        with patch(
            "src.services.report_schedule_service.ReportScheduleService.create_schedule"
        ) as mock_create:
            # 模擬服務返回
            mock_create.return_value = {
                "schedule_id": "test-schedule-123",
                "name": self.test_schedule_data["name"],
                "status": "active",
                "created_at": datetime.now(),
                **self.test_schedule_data,
            }

            response = self.client.post(
                f"{self.base_url}", json=self.test_schedule_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "排程" in data["message"]
            assert "創建成功" in data["message"]
            assert data["data"]["schedule"]["name"] == self.test_schedule_data["name"]

    def test_create_schedule_invalid_data(self):
        """測試創建排程時數據驗證失敗"""
        invalid_data = {
            "name": "",  # 空名稱
            "report_type": "invalid_type",  # 無效類型
            "frequency": "invalid_frequency",  # 無效頻率
        }

        response = self.client.post(f"{self.base_url}", json=invalid_data)

        assert response.status_code == 422  # 驗證錯誤

    def test_create_schedule_custom_cron(self):
        """測試創建自定義 Cron 排程"""
        custom_data = {
            **self.test_schedule_data,
            "frequency": "custom",
            "cron_expression": "0 9 * * 1-5",  # 工作日上午9點
        }

        with patch(
            "src.services.report_schedule_service.ReportScheduleService.create_schedule"
        ) as mock_create:
            mock_create.return_value = {
                "schedule_id": "test-schedule-456",
                **custom_data,
            }

            response = self.client.post(f"{self.base_url}", json=custom_data)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_list_schedules_success(self):
        """測試成功查詢排程列表"""
        with patch(
            "src.services.report_schedule_service.ReportScheduleService.list_schedules"
        ) as mock_list:
            # 模擬服務返回
            mock_list.return_value = {
                "schedules": [
                    {
                        "schedule_id": "schedule-1",
                        "name": "每日報表",
                        "status": "active",
                        "frequency": "daily",
                    },
                    {
                        "schedule_id": "schedule-2",
                        "name": "週報",
                        "status": "active",
                        "frequency": "weekly",
                    },
                ],
                "total": 2,
                "page": 1,
                "page_size": 20,
                "total_pages": 1,
                "has_next": False,
                "has_prev": False,
            }

            response = self.client.get(f"{self.base_url}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["schedules"]) == 2
            assert data["data"]["total"] == 2

    def test_list_schedules_with_filters(self):
        """測試帶篩選條件的排程列表查詢"""
        params = {
            "page": 1,
            "page_size": 10,
            "search": "交易",
            "report_type": "trading_summary",
            "status": "active",
            "frequency": "daily",
            "is_enabled": True,
            "tags": "daily,trading",
            "sort_by": "created_at",
            "sort_order": "desc",
        }

        with patch(
            "src.services.report_schedule_service.ReportScheduleService.list_schedules"
        ) as mock_list:
            mock_list.return_value = {
                "schedules": [],
                "total": 0,
                "page": 1,
                "page_size": 10,
                "total_pages": 0,
                "has_next": False,
                "has_prev": False,
            }

            response = self.client.get(f"{self.base_url}", params=params)

            assert response.status_code == 200
            # 驗證服務被正確調用
            mock_list.assert_called_once()

    def test_get_schedule_success(self):
        """測試成功獲取排程詳情"""
        schedule_id = "test-schedule-123"

        with patch(
            "src.services.report_schedule_service.ReportScheduleService.get_schedule"
        ) as mock_get:
            mock_get.return_value = {
                "schedule_id": schedule_id,
                "name": "測試排程",
                "status": "active",
                "frequency": "daily",
            }

            with patch(
                "src.services.report_schedule_service.ReportScheduleService.get_execution_history"
            ) as mock_history:
                mock_history.return_value = {
                    "executions": [
                        {
                            "execution_id": "exec-1",
                            "status": "completed",
                            "start_time": datetime.now(),
                        }
                    ]
                }

                response = self.client.get(f"{self.base_url}/{schedule_id}")

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["data"]["schedule"]["schedule_id"] == schedule_id

    def test_get_schedule_not_found(self):
        """測試獲取不存在的排程"""
        schedule_id = "non-existent-schedule"

        with patch(
            "src.services.report_schedule_service.ReportScheduleService.get_schedule"
        ) as mock_get:
            mock_get.return_value = None

            response = self.client.get(f"{self.base_url}/{schedule_id}")

            assert response.status_code == 404

    def test_update_schedule_success(self):
        """測試成功更新排程"""
        schedule_id = "test-schedule-123"
        update_data = {
            "name": "更新後的排程名稱",
            "description": "更新後的描述",
            "is_enabled": False,
        }

        with patch(
            "src.services.report_schedule_service.ReportScheduleService.update_schedule"
        ) as mock_update:
            mock_update.return_value = {
                "schedule_id": schedule_id,
                "name": update_data["name"],
                "description": update_data["description"],
                "is_enabled": update_data["is_enabled"],
            }

            response = self.client.put(
                f"{self.base_url}/{schedule_id}", json=update_data
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "更新成功" in data["message"]

    def test_delete_schedule_success(self):
        """測試成功刪除排程"""
        schedule_id = "test-schedule-123"

        with patch(
            "src.services.report_schedule_service.ReportScheduleService.delete_schedule"
        ) as mock_delete:
            mock_delete.return_value = True

            response = self.client.delete(f"{self.base_url}/{schedule_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "刪除成功" in data["message"]

    def test_delete_schedule_not_found(self):
        """測試刪除不存在的排程"""
        schedule_id = "non-existent-schedule"

        with patch(
            "src.services.report_schedule_service.ReportScheduleService.delete_schedule"
        ) as mock_delete:
            mock_delete.return_value = False

            response = self.client.delete(f"{self.base_url}/{schedule_id}")

            assert response.status_code == 404

    def test_execute_schedule_success(self):
        """測試成功執行排程"""
        schedule_id = "test-schedule-123"

        with patch(
            "src.services.report_schedule_service.ReportScheduleService.execute_schedule"
        ) as mock_execute:
            mock_execute.return_value = {
                "execution_id": "exec-123",
                "schedule_id": schedule_id,
                "status": "pending",
                "message": "排程執行已啟動",
                "created_at": datetime.now(),
            }

            response = self.client.post(f"{self.base_url}/{schedule_id}/execute")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "已啟動" in data["message"]

    def test_execute_schedule_invalid_status(self):
        """測試執行無效狀態的排程"""
        schedule_id = "test-schedule-123"

        with patch(
            "src.services.report_schedule_service.ReportScheduleService.execute_schedule"
        ) as mock_execute:
            mock_execute.side_effect = ValueError("排程狀態不允許執行")

            response = self.client.post(f"{self.base_url}/{schedule_id}/execute")

            assert response.status_code == 400

    def test_get_execution_history_success(self):
        """測試成功獲取執行歷史"""
        schedule_id = "test-schedule-123"

        with patch(
            "src.services.report_schedule_service.ReportScheduleService.get_execution_history"
        ) as mock_history:
            mock_history.return_value = {
                "executions": [
                    {
                        "execution_id": "exec-1",
                        "status": "completed",
                        "start_time": datetime.now(),
                        "duration": 120.5,
                    },
                    {
                        "execution_id": "exec-2",
                        "status": "failed",
                        "start_time": datetime.now() - timedelta(days=1),
                        "error_message": "測試錯誤",
                    },
                ],
                "total": 2,
                "page": 1,
                "page_size": 20,
            }

            response = self.client.get(f"{self.base_url}/{schedule_id}/executions")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]["executions"]) == 2

    def test_invalid_schedule_id_format(self):
        """測試無效的排程ID格式"""
        invalid_ids = ["", "123", "abc"]

        for invalid_id in invalid_ids:
            response = self.client.get(f"{self.base_url}/{invalid_id}")
            assert response.status_code == 400
