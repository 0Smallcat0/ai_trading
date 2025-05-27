"""
交易執行系統 API 測試

此模組測試交易執行系統 API 的所有端點，確保功能正確性和穩定性。
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json

from src.api.main import app
from src.core.trade_execution_service import TradeExecutionService


class TestTradingAPI:
    """交易執行 API 測試類"""

    def setup_method(self):
        """測試前設置"""
        self.client = TestClient(app)
        self.base_url = "/api/v1/trading"

        # 模擬認證 token
        self.auth_headers = {"Authorization": "Bearer test_token"}

        # 測試數據
        self.test_order_request = {
            "symbol": "2330.TW",
            "action": "buy",
            "quantity": 1000,
            "order_type": "limit",
            "price": 500.0,
            "time_in_force": "day",
            "portfolio_id": "portfolio_001",
            "notes": "測試訂單",
        }

        self.test_order_response = {
            "order_id": "order_123",
            "symbol": "2330.TW",
            "action": "buy",
            "quantity": 1000,
            "filled_quantity": 0,
            "order_type": "limit",
            "price": 500.0,
            "time_in_force": "day",
            "status": "pending",
            "created_at": datetime.now(),
            "portfolio_id": "portfolio_001",
            "notes": "測試訂單",
        }

    @patch("src.api.middleware.auth.verify_token")
    @patch("src.core.trade_execution_service.TradeExecutionService.submit_order")
    @patch("src.core.trade_execution_service.TradeExecutionService.get_order_details")
    def test_create_order_success(
        self, mock_get_details, mock_submit, mock_verify_token
    ):
        """測試創建訂單成功"""
        # 設置模擬
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_submit.return_value = (True, "訂單創建成功", "order_123")
        mock_get_details.return_value = self.test_order_response

        # 發送請求
        response = self.client.post(
            f"{self.base_url}/orders",
            json=self.test_order_request,
            headers=self.auth_headers,
        )

        # 驗證響應
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "訂單創建成功"
        assert data["data"]["order_id"] == "order_123"
        assert data["data"]["symbol"] == "2330.TW"

    @patch("src.api.middleware.auth.verify_token")
    def test_create_order_invalid_data(self, mock_verify_token):
        """測試創建訂單時數據驗證失敗"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}

        # 無效的請求數據
        invalid_request = {
            "symbol": "2330.TW",
            "action": "invalid_action",  # 無效動作
            "quantity": 1000,
            "order_type": "limit",
            "price": 500.0,
        }

        response = self.client.post(
            f"{self.base_url}/orders", json=invalid_request, headers=self.auth_headers
        )

        assert response.status_code == 422  # 驗證錯誤

    @patch("src.api.middleware.auth.verify_token")
    @patch("src.core.trade_execution_service.TradeExecutionService.get_orders_list")
    def test_get_orders_success(self, mock_get_orders, mock_verify_token):
        """測試獲取訂單列表成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_get_orders.return_value = {
            "orders": [self.test_order_response],
            "total": 1,
            "page": 1,
            "page_size": 20,
        }

        response = self.client.get(f"{self.base_url}/orders", headers=self.auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["data"][0]["order_id"] == "order_123"

    @patch("src.api.middleware.auth.verify_token")
    @patch("src.core.trade_execution_service.TradeExecutionService.get_order_details")
    def test_get_order_details_success(self, mock_get_details, mock_verify_token):
        """測試獲取訂單詳情成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_get_details.return_value = self.test_order_response

        response = self.client.get(
            f"{self.base_url}/orders/order_123", headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["order_id"] == "order_123"

    @patch("src.api.middleware.auth.verify_token")
    @patch("src.core.trade_execution_service.TradeExecutionService.get_order_details")
    def test_get_order_details_not_found(self, mock_get_details, mock_verify_token):
        """測試獲取不存在的訂單詳情"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_get_details.return_value = None

        response = self.client.get(
            f"{self.base_url}/orders/nonexistent_order", headers=self.auth_headers
        )

        assert response.status_code == 404

    @patch("src.api.middleware.auth.verify_token")
    @patch("src.core.trade_execution_service.TradeExecutionService.get_order_details")
    @patch("src.core.trade_execution_service.TradeExecutionService.update_order")
    def test_update_order_success(
        self, mock_update, mock_get_details, mock_verify_token
    ):
        """測試修改訂單成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_get_details.side_effect = [
            self.test_order_response,  # 第一次調用：檢查訂單存在
            {
                **self.test_order_response,
                "price": 510.0,
            },  # 第二次調用：獲取更新後的訂單
        ]
        mock_update.return_value = (True, "訂單修改成功")

        update_request = {"price": 510.0, "notes": "修改價格"}

        response = self.client.put(
            f"{self.base_url}/orders/order_123",
            json=update_request,
            headers=self.auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "訂單修改成功"

    @patch("src.api.middleware.auth.verify_token")
    @patch("src.core.trade_execution_service.TradeExecutionService.get_order_details")
    @patch("src.core.trade_execution_service.TradeExecutionService.cancel_order")
    def test_cancel_order_success(
        self, mock_cancel, mock_get_details, mock_verify_token
    ):
        """測試取消訂單成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_get_details.side_effect = [
            self.test_order_response,  # 第一次調用：檢查訂單存在
            {
                **self.test_order_response,
                "status": "cancelled",
            },  # 第二次調用：獲取取消後的狀態
        ]
        mock_cancel.return_value = (True, "訂單取消成功")

        response = self.client.delete(
            f"{self.base_url}/orders/order_123", headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "訂單取消成功"

    @patch("src.api.middleware.auth.verify_token")
    @patch("src.core.trade_execution_service.TradeExecutionService.submit_order")
    @patch("src.core.trade_execution_service.TradeExecutionService.get_order_details")
    @patch(
        "src.core.trade_execution_service.TradeExecutionService.get_execution_history"
    )
    def test_execute_trade_success(
        self, mock_get_executions, mock_get_details, mock_submit, mock_verify_token
    ):
        """測試執行交易成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_submit.return_value = (True, "交易執行成功", "order_123")
        mock_get_details.return_value = {**self.test_order_response, "status": "filled"}
        mock_get_executions.return_value = [
            {
                "execution_id": "exec_123",
                "order_id": "order_123",
                "symbol": "2330.TW",
                "action": "buy",
                "quantity": 1000,
                "price": 500.0,
                "amount": 500000.0,
                "commission": 1425.0,
                "tax": 0.0,
                "net_amount": 501425.0,
                "execution_time": datetime.now(),
            }
        ]

        market_order_request = {
            "symbol": "2330.TW",
            "action": "buy",
            "quantity": 1000,
            "order_type": "market",
        }

        response = self.client.post(
            f"{self.base_url}/execute",
            json=market_order_request,
            headers=self.auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "交易執行成功"
        assert data["data"]["execution_id"] == "exec_123"

    @patch("src.api.middleware.auth.verify_token")
    @patch(
        "src.core.trade_execution_service.TradeExecutionService.get_execution_history"
    )
    def test_get_trade_history_success(self, mock_get_history, mock_verify_token):
        """測試獲取交易歷史成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_get_history.return_value = [
            {
                "execution_id": "exec_123",
                "order_id": "order_123",
                "symbol": "2330.TW",
                "action": "buy",
                "quantity": 1000,
                "price": 500.0,
                "amount": 500000.0,
                "commission": 1425.0,
                "tax": 0.0,
                "net_amount": 501425.0,
                "execution_time": datetime.now(),
            }
        ]

        response = self.client.get(
            f"{self.base_url}/history", headers=self.auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1

    @patch("src.api.middleware.auth.verify_token")
    @patch("src.core.trade_execution_service.TradeExecutionService.switch_trading_mode")
    @patch("src.core.trade_execution_service.TradeExecutionService.get_trading_status")
    def test_toggle_trading_mode_success(
        self, mock_get_status, mock_switch_mode, mock_verify_token
    ):
        """測試切換交易模式成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_switch_mode.return_value = (True, "已切換到實盤交易模式")
        mock_get_status.return_value = {
            "is_simulation_mode": False,
            "broker_connected": True,
            "current_broker": "futu",
            "trading_session": "regular",
            "market_status": "open",
            "pending_orders_count": 0,
            "today_orders_count": 5,
            "today_executions_count": 3,
            "available_cash": 100000.0,
            "total_position_value": 500000.0,
            "last_update": datetime.now(),
        }

        toggle_request = {"is_simulation": False, "reason": "切換到實盤交易"}

        response = self.client.post(
            f"{self.base_url}/mode/toggle",
            json=toggle_request,
            headers=self.auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["is_simulation_mode"] is False

    @patch("src.api.middleware.auth.verify_token")
    @patch("src.core.trade_execution_service.TradeExecutionService.get_trading_status")
    def test_get_trading_status_success(self, mock_get_status, mock_verify_token):
        """測試獲取交易狀態成功"""
        mock_verify_token.return_value = {"user_id": "test_user", "username": "test"}
        mock_get_status.return_value = {
            "is_simulation_mode": True,
            "broker_connected": True,
            "current_broker": "simulator",
            "trading_session": "regular",
            "market_status": "open",
            "pending_orders_count": 2,
            "today_orders_count": 10,
            "today_executions_count": 8,
            "available_cash": 1000000.0,
            "total_position_value": 2000000.0,
            "last_update": datetime.now(),
        }

        response = self.client.get(f"{self.base_url}/status", headers=self.auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["is_simulation_mode"] is True
        assert data["data"]["current_broker"] == "simulator"

    def test_unauthorized_access(self):
        """測試未授權訪問"""
        response = self.client.get(f"{self.base_url}/orders")

        # 應該返回 401 或重定向到登入頁面
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
