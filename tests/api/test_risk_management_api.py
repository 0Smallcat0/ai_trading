"""
風險管理系統 API 測試

此模組測試風險管理系統 API 的所有端點，確保功能正確性和穩定性。
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

from src.api.main import app
from src.core.risk_management_service import RiskManagementService


class TestRiskManagementAPI:
    """風險管理 API 測試類"""

    def setup_method(self):
        """測試前設置"""
        self.client = TestClient(app)
        self.base_url = "/api/v1/risk"

        # 模擬認證 token
        self.auth_headers = {"Authorization": "Bearer test_token"}

        # 測試數據
        self.test_risk_parameters = {
            "stop_loss_type": "percent",
            "stop_loss_value": 0.05,
            "take_profit_type": "percent",
            "take_profit_value": 0.1,
            "max_position_size": 0.15,
            "max_portfolio_risk": 0.02,
            "max_daily_loss": 0.05,
            "max_drawdown": 0.15,
            "var_confidence_level": 0.95,
            "var_time_horizon": 1,
            "var_method": "historical",
            "max_correlation": 0.7,
            "correlation_lookback": 60,
            "max_sector_exposure": 0.3,
            "max_single_stock": 0.15,
        }

    @patch("src.api.middleware.auth.verify_token")
    @patch("src.core.risk_management_service.RiskManagementService.set_risk_parameters")
    @patch("src.core.risk_management_service.RiskManagementService.get_risk_parameters")
    def test_set_risk_parameters_success(
        self, mock_get_params, mock_set_params, mock_verify_token
    ):
        """測試設定風險參數成功"""
        # 設置模擬
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_set_params.return_value = True
        mock_get_params.return_value = self.test_risk_parameters

        # 發送請求
        response = self.client.post(
            f"{self.base_url}/parameters",
            json=self.test_risk_parameters,
            headers=self.auth_headers,
        )

        # 驗證響應
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "風險參數設定成功"
        assert data["data"]["stop_loss_type"] == "percent"
        assert data["data"]["stop_loss_value"] == 0.05

    @patch("src.api.middleware.auth.verify_token")
    def test_set_risk_parameters_invalid_data(self, mock_verify_token):
        """測試設定風險參數時數據驗證失敗"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}

        # 無效的請求數據
        invalid_request = {
            "stop_loss_type": "invalid_type",  # 無效類型
            "stop_loss_value": 0.05,
            "take_profit_type": "percent",
            "take_profit_value": 0.1,
        }

        response = self.client.post(
            f"{self.base_url}/parameters",
            json=invalid_request,
            headers=self.auth_headers,
        )

        assert response.status_code == 422  # 驗證錯誤

    @patch("src.api.middleware.auth.verify_token")
    @patch("src.core.risk_management_service.RiskManagementService.get_risk_parameters")
    def test_get_risk_parameters_success(self, mock_get_params, mock_verify_token):
        """測試獲取風險參數成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_get_params.return_value = self.test_risk_parameters

        response = self.client.get(
            f"{self.base_url}/parameters", headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["stop_loss_type"] == "percent"

    @patch("src.api.middleware.auth.verify_token")
    @patch(
        "src.core.risk_management_service.RiskManagementService.calculate_risk_metrics"
    )
    def test_get_risk_metrics_success(self, mock_calculate_metrics, mock_verify_token):
        """測試獲取風險指標成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_calculate_metrics.return_value = {
            "volatility": 0.15,
            "sharpe_ratio": 1.2,
            "max_drawdown": -0.08,
            "current_drawdown": -0.02,
            "var_95": -0.025,
            "var_99": -0.045,
        }

        response = self.client.get(
            f"{self.base_url}/metrics", headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "portfolio_value" in data["data"]
        assert "volatility" in data["data"]

    @patch("src.api.middleware.auth.verify_token")
    @patch(
        "src.core.risk_management_service.RiskManagementService.calculate_risk_metrics"
    )
    def test_get_position_risk_metrics_success(
        self, mock_calculate_metrics, mock_verify_token
    ):
        """測試獲取部位風險指標成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_calculate_metrics.return_value = {
            "volatility": 0.18,
            "sharpe_ratio": 1.0,
            "beta": 1.2,
            "var_95": -0.03,
        }

        response = self.client.get(
            f"{self.base_url}/metrics/position/2330.TW", headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["symbol"] == "2330.TW"
        assert "volatility" in data["data"]

    @patch("src.api.middleware.auth.verify_token")
    def test_get_risk_controls_success(self, mock_verify_token):
        """測試獲取風控機制狀態成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}

        response = self.client.get(
            f"{self.base_url}/controls", headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0

        # 檢查第一個風控機制
        first_control = data["data"][0]
        assert "control_name" in first_control
        assert "enabled" in first_control
        assert "status" in first_control

    @patch("src.api.middleware.auth.verify_token")
    def test_toggle_risk_control_success(self, mock_verify_token):
        """測試切換風控機制成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}

        toggle_request = {
            "control_name": "stop_loss",
            "enabled": False,
            "reason": "測試停用停損機制",
        }

        response = self.client.post(
            f"{self.base_url}/controls/toggle",
            json=toggle_request,
            headers=self.auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["control_name"] == "stop_loss"
        assert data["data"]["enabled"] is False

    @patch("src.api.middleware.auth.verify_token")
    def test_emergency_stop_success(self, mock_verify_token):
        """測試緊急停止成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}

        response = self.client.post(
            f"{self.base_url}/controls/emergency-stop?reason=測試緊急停止",
            headers=self.auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "emergency_stop_active"
        assert data["data"]["reason"] == "測試緊急停止"

    @patch("src.api.middleware.auth.verify_token")
    def test_get_risk_alerts_success(self, mock_verify_token):
        """測試獲取風險警報成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}

        response = self.client.get(f"{self.base_url}/alerts", headers=self.auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)

    @patch("src.api.middleware.auth.verify_token")
    def test_acknowledge_alerts_success(self, mock_verify_token):
        """測試確認警報成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}

        acknowledge_request = {
            "alert_ids": ["alert_001", "alert_002"],
            "acknowledged_by": "test_user",
            "notes": "已確認並處理",
        }

        response = self.client.post(
            f"{self.base_url}/alerts/acknowledge",
            json=acknowledge_request,
            headers=self.auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["acknowledged_count"] == 2

    @patch("src.api.middleware.auth.verify_token")
    def test_get_alert_statistics_success(self, mock_verify_token):
        """測試獲取警報統計成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}

        response = self.client.get(
            f"{self.base_url}/alerts/statistics", headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "total_alerts" in data["data"]
        assert "alert_by_severity" in data["data"]
        assert "alert_by_type" in data["data"]

    def test_unauthorized_access(self):
        """測試未授權訪問"""
        response = self.client.get(f"{self.base_url}/parameters")

        # 應該返回 401 或重定向到登入頁面
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
