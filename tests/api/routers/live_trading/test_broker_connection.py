"""券商連接 API 測試模組

測試券商連接相關的 API 端點功能。
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.routers.live_trading.broker_connection import router
from src.api.routers.live_trading.models import BrokerType, OrderStatus, OrderSide, OrderType

# 創建一個簡化的 get_current_user 函數用於測試
async def mock_get_current_user():
    return {
        "user_id": "test_user_123",
        "username": "test_user",
        "role": "trader"
    }


# 創建測試應用
app = FastAPI()

# 覆蓋依賴項以使用模擬函數
from src.api.routers.live_trading.broker_connection import get_current_user
app.dependency_overrides[get_current_user] = mock_get_current_user

app.include_router(router)

client = TestClient(app)


class TestBrokerConnectionAPI:
    """券商連接 API 測試類"""
    
    def setup_method(self):
        """測試前設定"""
        self.mock_user = {
            "user_id": "test_user_123",
            "username": "test_user",
            "role": "trader"
        }

        self.auth_request = {
            "broker_type": "fubon",
            "username": "test_broker_user",
            "password": "test_password",
            "api_key": "test_api_key",
            "api_secret": "test_api_secret"
        }

        self.headers = {"Authorization": "Bearer test_token"}
    
    @patch('src.api.routers.live_trading.broker_connection.get_current_user')
    def test_authenticate_broker_success(self, mock_get_user):
        """測試券商認證成功"""
        mock_get_user.return_value = self.mock_user
        
        response = client.post("/auth", json=self.auth_request)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success"] is True
        assert data["data"]["broker_type"] == "fubon"
        assert "session_id" in data["data"]
        assert "expires_at" in data["data"]
    
    @patch('src.api.routers.live_trading.broker_connection.get_current_user')
    def test_authenticate_broker_invalid_credentials(self, mock_get_user):
        """測試券商認證失敗 - 無效憑證"""
        mock_get_user.return_value = self.mock_user
        
        invalid_request = self.auth_request.copy()
        invalid_request["password"] = "123"  # 密碼太短
        
        response = client.post("/auth", json=invalid_request, headers=self.headers)
        
        assert response.status_code == 401
        assert "券商認證失敗" in response.json()["detail"]
    
    @patch('src.api.routers.live_trading.broker_connection.get_current_user')
    def test_authenticate_broker_missing_api_key(self, mock_get_user):
        """測試券商認證失敗 - 缺少 API 金鑰"""
        mock_get_user.return_value = self.mock_user
        
        invalid_request = self.auth_request.copy()
        del invalid_request["api_key"]  # 富邦券商需要 API 金鑰
        
        response = client.post("/auth", json=invalid_request)
        
        assert response.status_code == 401
    
    @patch('src.api.routers.live_trading.broker_connection.get_current_user')
    @patch('src.api.routers.live_trading.broker_connection._broker_sessions')
    def test_get_account_info_success(self, mock_sessions, mock_get_user):
        """測試獲取帳戶資訊成功"""
        mock_get_user.return_value = self.mock_user
        
        # 模擬有效會話
        session_id = "test_session_123"
        mock_sessions[session_id] = {
            "user_id": self.mock_user["user_id"],
            "broker_type": BrokerType.FUBON,
            "expires_at": datetime.now() + timedelta(hours=1)
        }
        
        response = client.get(f"/account-info?session_id={session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "account_id" in data["data"]
        assert "total_equity" in data["data"]
        assert "available_cash" in data["data"]
    
    @patch('src.api.routers.live_trading.broker_connection.get_current_user')
    def test_get_account_info_invalid_session(self, mock_get_user):
        """測試獲取帳戶資訊失敗 - 無效會話"""
        mock_get_user.return_value = self.mock_user
        
        response = client.get("/account-info?session_id=invalid_session")
        
        assert response.status_code == 401
        assert "無效的券商會話" in response.json()["detail"]
    
    @patch('src.api.routers.live_trading.broker_connection.get_current_user')
    @patch('src.api.routers.live_trading.broker_connection._broker_sessions')
    def test_get_positions_success(self, mock_sessions, mock_get_user):
        """測試獲取持倉資訊成功"""
        mock_get_user.return_value = self.mock_user
        
        # 模擬有效會話
        session_id = "test_session_123"
        mock_sessions[session_id] = {
            "user_id": self.mock_user["user_id"],
            "broker_type": BrokerType.FUBON,
            "expires_at": datetime.now() + timedelta(hours=1)
        }
        
        response = client.get(f"/positions?session_id={session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        
        # 檢查持倉數據結構
        if data["data"]:
            position = data["data"][0]
            assert "symbol" in position
            assert "quantity" in position
            assert "average_price" in position
            assert "current_price" in position
            assert "unrealized_pnl" in position
    
    @patch('src.api.routers.live_trading.broker_connection.get_current_user')
    @patch('src.api.routers.live_trading.broker_connection._broker_sessions')
    def test_get_positions_with_symbol_filter(self, mock_sessions, mock_get_user):
        """測試獲取指定股票持倉"""
        mock_get_user.return_value = self.mock_user
        
        # 模擬有效會話
        session_id = "test_session_123"
        mock_sessions[session_id] = {
            "user_id": self.mock_user["user_id"],
            "broker_type": BrokerType.FUBON,
            "expires_at": datetime.now() + timedelta(hours=1)
        }
        
        response = client.get(f"/positions?session_id={session_id}&symbol=2330.TW")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
        # 檢查過濾結果
        for position in data["data"]:
            assert position["symbol"] == "2330.TW"
    
    @patch('src.api.routers.live_trading.broker_connection.get_current_user')
    @patch('src.api.routers.live_trading.broker_connection._broker_sessions')
    def test_get_orders_success(self, mock_sessions, mock_get_user):
        """測試獲取訂單列表成功"""
        mock_get_user.return_value = self.mock_user
        
        # 模擬有效會話
        session_id = "test_session_123"
        mock_sessions[session_id] = {
            "user_id": self.mock_user["user_id"],
            "broker_type": BrokerType.FUBON,
            "expires_at": datetime.now() + timedelta(hours=1)
        }
        
        response = client.get(f"/orders?session_id={session_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert isinstance(data["data"], list)
        
        # 檢查訂單數據結構
        if data["data"]:
            order = data["data"][0]
            assert "order_id" in order
            assert "symbol" in order
            assert "side" in order
            assert "order_type" in order
            assert "quantity" in order
            assert "status" in order
    
    @patch('src.api.routers.live_trading.broker_connection.get_current_user')
    @patch('src.api.routers.live_trading.broker_connection._broker_sessions')
    def test_get_orders_with_filters(self, mock_sessions, mock_get_user):
        """測試獲取訂單列表 - 帶過濾條件"""
        mock_get_user.return_value = self.mock_user
        
        # 模擬有效會話
        session_id = "test_session_123"
        mock_sessions[session_id] = {
            "user_id": self.mock_user["user_id"],
            "broker_type": BrokerType.FUBON,
            "expires_at": datetime.now() + timedelta(hours=1)
        }
        
        response = client.get(
            f"/orders?session_id={session_id}&status_filter=filled&symbol=2330.TW&limit=10"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) <= 10
    
    @patch('src.api.routers.live_trading.broker_connection.get_current_user')
    @patch('src.api.routers.live_trading.broker_connection._broker_sessions')
    def test_session_expiry(self, mock_sessions, mock_get_user):
        """測試會話過期處理"""
        mock_get_user.return_value = self.mock_user
        
        # 模擬過期會話
        session_id = "expired_session_123"
        mock_sessions[session_id] = {
            "user_id": self.mock_user["user_id"],
            "broker_type": BrokerType.FUBON,
            "expires_at": datetime.now() - timedelta(hours=1)  # 已過期
        }
        
        response = client.get(f"/account-info?session_id={session_id}")
        
        assert response.status_code == 401
        assert "券商會話已過期" in response.json()["detail"]
        
        # 檢查過期會話是否被清理
        assert session_id not in mock_sessions
    
    @patch('src.api.routers.live_trading.broker_connection.get_current_user')
    @patch('src.api.routers.live_trading.broker_connection._broker_sessions')
    def test_session_ownership(self, mock_sessions, mock_get_user):
        """測試會話所有權檢查"""
        mock_get_user.return_value = self.mock_user
        
        # 模擬其他用戶的會話
        session_id = "other_user_session_123"
        mock_sessions[session_id] = {
            "user_id": "other_user_456",
            "broker_type": BrokerType.FUBON,
            "expires_at": datetime.now() + timedelta(hours=1)
        }
        
        response = client.get(f"/account-info?session_id={session_id}")
        
        assert response.status_code == 403
        assert "會話不屬於當前用戶" in response.json()["detail"]


class TestBrokerCredentialValidation:
    """券商憑證驗證測試類"""
    
    def test_validate_broker_credentials_valid(self):
        """測試有效憑證驗證"""
        from src.api.routers.live_trading.broker_connection import _validate_broker_credentials
        from src.api.routers.live_trading.models import BrokerAuthRequest
        
        request = BrokerAuthRequest(
            broker_type=BrokerType.FUBON,
            username="test_user",
            password="test_password",
            api_key="test_api_key"
        )
        
        result = _validate_broker_credentials(request)
        assert result is True
    
    def test_validate_broker_credentials_invalid_username(self):
        """測試無效用戶名"""
        from src.api.routers.live_trading.broker_connection import _validate_broker_credentials
        from src.api.routers.live_trading.models import BrokerAuthRequest
        
        request = BrokerAuthRequest(
            broker_type=BrokerType.FUBON,
            username="",  # 空用戶名
            password="test_password",
            api_key="test_api_key"
        )
        
        result = _validate_broker_credentials(request)
        assert result is False
    
    def test_validate_broker_credentials_short_password(self):
        """測試密碼太短"""
        from src.api.routers.live_trading.broker_connection import _validate_broker_credentials
        from src.api.routers.live_trading.models import BrokerAuthRequest
        
        request = BrokerAuthRequest(
            broker_type=BrokerType.FUBON,
            username="test_user",
            password="123",  # 密碼太短
            api_key="test_api_key"
        )
        
        result = _validate_broker_credentials(request)
        assert result is False
    
    def test_validate_broker_credentials_fubon_missing_api_key(self):
        """測試富邦券商缺少 API 金鑰"""
        from src.api.routers.live_trading.broker_connection import _validate_broker_credentials
        from src.api.routers.live_trading.models import BrokerAuthRequest
        
        request = BrokerAuthRequest(
            broker_type=BrokerType.FUBON,
            username="test_user",
            password="test_password"
            # 缺少 api_key
        )
        
        result = _validate_broker_credentials(request)
        assert result is False
    
    def test_validate_broker_credentials_cathay_short_password(self):
        """測試國泰券商密碼長度要求"""
        from src.api.routers.live_trading.broker_connection import _validate_broker_credentials
        from src.api.routers.live_trading.models import BrokerAuthRequest
        
        request = BrokerAuthRequest(
            broker_type=BrokerType.CATHAY,
            username="test_user",
            password="1234567"  # 國泰要求至少 8 位
        )
        
        result = _validate_broker_credentials(request)
        assert result is False
        
        # 測試符合要求的密碼
        request.password = "12345678"
        result = _validate_broker_credentials(request)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__])
