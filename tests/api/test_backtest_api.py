"""
回測系統 API 測試

此模組測試回測系統 API 的所有端點，確保功能正確性和穩定性。
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

from src.api.main import app
from src.core.backtest_service import BacktestService, BacktestConfig


class TestBacktestAPI:
    """回測 API 測試類"""

    def setup_method(self):
        """測試前設置"""
        self.client = TestClient(app)
        self.base_url = "/api/v1/backtest"

        # 模擬認證 token
        self.auth_headers = {"Authorization": "Bearer test_token"}

        # 測試數據
        self.test_backtest_request = {
            "strategy_id": "test_strategy_001",
            "strategy_name": "測試策略",
            "symbols": ["2330", "2317"],
            "start_date": "2023-01-01T00:00:00",
            "end_date": "2023-12-31T23:59:59",
            "initial_capital": 100000.0,
            "commission": 0.001425,
            "slippage": 0.001,
            "tax": 0.003,
            "max_position_size": 0.2,
            "stop_loss": 0.05,
            "take_profit": 0.1,
        }

    @patch("src.api.middleware.auth.verify_token")
    @patch("src.core.backtest_service.BacktestService.start_backtest")
    @patch("src.core.backtest_service.BacktestService.get_backtest_info")
    def test_start_backtest_success(self, mock_get_info, mock_start, mock_verify_token):
        """測試啟動回測成功"""
        # 設置模擬
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_start.return_value = "backtest_123"
        mock_get_info.return_value = {
            "id": "backtest_123",
            "strategy_id": "test_strategy_001",
            "strategy_name": "測試策略",
            "status": "created",
            "progress": 0,
            "message": "回測任務已創建",
            "symbols": ["2330", "2317"],
            "start_date": datetime(2023, 1, 1),
            "end_date": datetime(2023, 12, 31),
            "initial_capital": 100000.0,
            "created_at": datetime.now(),
        }

        # 發送請求
        response = self.client.post(
            f"{self.base_url}/start",
            json=self.test_backtest_request,
            headers=self.auth_headers,
        )

        # 驗證響應
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "回測任務已啟動"
        assert data["data"]["id"] == "backtest_123"
        assert data["data"]["strategy_id"] == "test_strategy_001"

    @patch("src.api.utils.security.get_current_user")
    def test_start_backtest_invalid_data(self, mock_auth):
        """測試啟動回測時數據驗證失敗"""
        mock_auth.return_value = {"user_id": "test_user", "username": "test"}

        # 無效的請求數據（缺少必要欄位）
        invalid_request = {
            "strategy_id": "test_strategy_001",
            # 缺少其他必要欄位
        }

        response = self.client.post(
            f"{self.base_url}/start", json=invalid_request, headers=self.auth_headers
        )

        assert response.status_code == 422  # 驗證錯誤

    @patch("src.api.utils.security.get_current_user")
    @patch("src.core.backtest_service.BacktestService.get_backtest_status")
    def test_get_backtest_status_success(self, mock_get_status, mock_auth):
        """測試獲取回測狀態成功"""
        mock_auth.return_value = {"user_id": "test_user", "username": "test"}
        mock_get_status.return_value = {
            "status": "running",
            "progress": 50,
            "message": "正在執行回測",
        }

        response = self.client.get(
            f"{self.base_url}/backtest_123/status", headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "running"
        assert data["data"]["progress"] == 50

    @patch("src.api.utils.security.get_current_user")
    @patch("src.core.backtest_service.BacktestService.get_backtest_status")
    def test_get_backtest_status_not_found(self, mock_get_status, mock_auth):
        """測試獲取不存在的回測狀態"""
        mock_auth.return_value = {"user_id": "test_user", "username": "test"}
        mock_get_status.return_value = None

        response = self.client.get(
            f"{self.base_url}/nonexistent/status", headers=self.auth_headers
        )

        assert response.status_code == 404

    @patch("src.api.utils.security.get_current_user")
    @patch("src.core.backtest_service.BacktestService.get_backtest_info")
    @patch("src.core.backtest_service.BacktestService.get_backtest_results")
    @patch("src.core.backtest_service.BacktestService.get_performance_metrics")
    def test_get_backtest_results_success(
        self, mock_metrics, mock_results, mock_info, mock_auth
    ):
        """測試獲取回測結果成功"""
        mock_auth.return_value = {"user_id": "test_user", "username": "test"}

        # 設置模擬數據
        mock_info.return_value = {
            "id": "backtest_123",
            "strategy_id": "test_strategy_001",
            "strategy_name": "測試策略",
            "status": "completed",
            "symbols": ["2330", "2317"],
            "start_date": datetime(2023, 1, 1),
            "end_date": datetime(2023, 12, 31),
            "initial_capital": 100000.0,
            "created_at": datetime.now(),
        }

        mock_results.return_value = {"final_capital": 120000.0}

        mock_metrics.return_value = {
            "total_return": 0.2,
            "annual_return": 0.2,
            "sharpe_ratio": 1.5,
            "max_drawdown": -0.1,
            "win_rate": 0.6,
            "profit_factor": 2.0,
            "total_trades": 50,
            "avg_trade_return": 0.004,
            "volatility": 0.15,
            "calmar_ratio": 2.0,
        }

        response = self.client.get(
            f"{self.base_url}/backtest_123/results", headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["final_capital"] == 120000.0
        assert data["data"]["metrics"]["total_return"] == 0.2

    @patch("src.api.utils.security.get_current_user")
    @patch("src.core.backtest_service.BacktestService.get_available_strategies")
    def test_get_available_strategies(self, mock_strategies, mock_auth):
        """測試獲取可用策略列表"""
        mock_auth.return_value = {"user_id": "test_user", "username": "test"}
        mock_strategies.return_value = [
            {
                "id": "strategy_001",
                "name": "趨勢跟隨策略",
                "type": "trend_following",
                "description": "基於移動平均線的策略",
                "enabled": True,
            }
        ]

        response = self.client.get(
            f"{self.base_url}/strategies", headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["name"] == "趨勢跟隨策略"

    @patch("src.api.utils.security.get_current_user")
    @patch("src.core.backtest_service.BacktestService.get_backtest_info")
    @patch("src.core.backtest_service.BacktestService.get_performance_metrics")
    def test_get_backtest_metrics(self, mock_metrics, mock_info, mock_auth):
        """測試獲取效能指標"""
        mock_auth.return_value = {"user_id": "test_user", "username": "test"}

        mock_info.return_value = {"status": "completed"}

        mock_metrics.return_value = {
            "total_return": 0.15,
            "sharpe_ratio": 1.2,
            "max_drawdown": -0.08,
            "win_rate": 0.65,
            "profit_factor": 1.8,
            "total_trades": 30,
            "avg_trade_return": 0.005,
            "volatility": 0.12,
            "annual_return": 0.15,
            "calmar_ratio": 1.875,
        }

        response = self.client.get(
            f"{self.base_url}/backtest_123/metrics", headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_return"] == 0.15
        assert data["data"]["sharpe_ratio"] == 1.2

    @patch("src.api.utils.security.get_current_user")
    def test_configure_backtest(self, mock_auth):
        """測試配置回測參數"""
        mock_auth.return_value = {"user_id": "test_user", "username": "test"}

        config_data = {
            "commission": 0.002,
            "slippage": 0.0015,
            "tax": 0.003,
            "max_position_size": 0.25,
            "stop_loss": 0.06,
            "take_profit": 0.12,
        }

        response = self.client.post(
            f"{self.base_url}/config", json=config_data, headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["commission"] == 0.002

    def test_unauthorized_access(self):
        """測試未授權訪問"""
        response = self.client.get(f"{self.base_url}/")

        # 應該返回 401 或重定向到登入頁面
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
