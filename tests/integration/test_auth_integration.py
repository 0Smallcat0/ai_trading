"""認證整合測試

此模組測試認證系統的整合功能，包括完整的登入登出流程。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from typing import Dict, Any

# 模擬 FastAPI 應用
app = FastAPI()

# 導入路由（需要模擬依賴）
with patch('src.api.routers.auth.AuthenticationService'), \
     patch('src.api.routers.auth.get_client_ip'), \
     patch('src.api.routers.auth.TokenManager'):
    from src.api.routers.auth import router as auth_router

app.include_router(auth_router, prefix="/api/v1/auth")


class TestAuthenticationIntegration:
    """認證整合測試類"""

    @pytest.fixture
    def client(self):
        """測試客戶端 Fixture"""
        return TestClient(app)

    @pytest.fixture
    def login_data(self):
        """登入數據 Fixture"""
        return {
            "username": "testuser",
            "password": "password123",
            "remember_me": False,
            "device_info": {
                "user_agent": "test_agent",
                "platform": "test"
            }
        }

    @patch('src.api.routers.auth.AuthenticationService')
    @patch('src.api.routers.auth.get_client_ip')
    def test_login_success(self, mock_get_client_ip, mock_auth_service, client, login_data, mock_user):
        """測試登入成功的完整流程"""
        # 設置模擬
        mock_get_client_ip.return_value = "127.0.0.1"
        mock_service_instance = Mock()
        mock_auth_service.return_value = mock_service_instance
        
        mock_service_instance.authenticate_user.return_value = mock_user
        mock_service_instance.create_user_session.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "token_type": "bearer",
            "expires_in": "86400"
        }

        # 執行測試
        response = client.post("/api/v1/auth/login", json=login_data)

        # 驗證回應
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

        # 驗證服務方法調用
        mock_service_instance.authenticate_user.assert_called_once_with(
            username="testuser",
            password="password123",
            ip_address="127.0.0.1"
        )
        mock_service_instance.create_user_session.assert_called_once()

    @patch('src.api.routers.auth.AuthenticationService')
    @patch('src.api.routers.auth.get_client_ip')
    def test_login_invalid_credentials(self, mock_get_client_ip, mock_auth_service, client, login_data):
        """測試登入失敗（無效憑證）"""
        # 設置模擬
        mock_get_client_ip.return_value = "127.0.0.1"
        mock_service_instance = Mock()
        mock_auth_service.return_value = mock_service_instance
        
        mock_service_instance.authenticate_user.side_effect = ValueError("用戶名或密碼錯誤")

        # 執行測試
        response = client.post("/api/v1/auth/login", json=login_data)

        # 驗證回應
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "用戶名或密碼錯誤" in data["error"]["message"]

    @patch('src.api.routers.auth.AuthenticationService')
    @patch('src.api.routers.auth.get_client_ip')
    def test_login_service_error(self, mock_get_client_ip, mock_auth_service, client, login_data):
        """測試登入時服務錯誤"""
        # 設置模擬
        mock_get_client_ip.return_value = "127.0.0.1"
        mock_service_instance = Mock()
        mock_auth_service.return_value = mock_service_instance
        
        mock_service_instance.authenticate_user.side_effect = Exception("服務錯誤")

        # 執行測試
        response = client.post("/api/v1/auth/login", json=login_data)

        # 驗證回應
        assert response.status_code == 500
        data = response.json()
        assert data["success"] is False
        assert "內部服務錯誤" in data["error"]["message"]

    def test_login_missing_username(self, client):
        """測試登入缺少用戶名"""
        login_data = {
            "password": "password123",
            "remember_me": False
        }

        # 執行測試
        response = client.post("/api/v1/auth/login", json=login_data)

        # 驗證回應
        assert response.status_code == 422  # Validation error

    def test_login_missing_password(self, client):
        """測試登入缺少密碼"""
        login_data = {
            "username": "testuser",
            "remember_me": False
        }

        # 執行測試
        response = client.post("/api/v1/auth/login", json=login_data)

        # 驗證回應
        assert response.status_code == 422  # Validation error

    @patch('src.api.routers.auth.verify_token')
    @patch('src.api.routers.auth.AuthenticationService')
    @patch('src.api.routers.auth.get_client_ip')
    def test_logout_success(self, mock_get_client_ip, mock_auth_service, mock_verify_token, client):
        """測試登出成功"""
        # 設置模擬
        mock_get_client_ip.return_value = "127.0.0.1"
        mock_verify_token.return_value = {
            "user_id": "test_user_123",
            "username": "testuser"
        }
        mock_service_instance = Mock()
        mock_auth_service.return_value = mock_service_instance

        # 執行測試
        headers = {"Authorization": "Bearer test_token"}
        response = client.post("/api/v1/auth/logout", headers=headers)

        # 驗證回應
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "登出成功"

        # 驗證服務方法調用
        mock_service_instance.logout_user.assert_called_once()

    @patch('src.api.routers.auth.verify_token')
    def test_logout_invalid_token(self, mock_verify_token, client):
        """測試登出時 Token 無效"""
        # 設置模擬
        from fastapi import HTTPException, status
        mock_verify_token.side_effect = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 無效"
        )

        # 執行測試
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.post("/api/v1/auth/logout", headers=headers)

        # 驗證回應
        assert response.status_code == 401

    def test_logout_missing_token(self, client):
        """測試登出時缺少 Token"""
        # 執行測試
        response = client.post("/api/v1/auth/logout")

        # 驗證回應
        assert response.status_code == 403  # Forbidden (no token)

    @patch('src.api.routers.auth.AuthenticationService')
    def test_refresh_token_success(self, mock_auth_service, client):
        """測試刷新 Token 成功"""
        # 設置模擬
        mock_auth_service.refresh_user_token.return_value = {
            "access_token": "new_access_token",
            "token_type": "bearer",
            "expires_in": "86400"
        }

        refresh_data = {
            "refresh_token": "valid_refresh_token"
        }

        # 執行測試
        response = client.post("/api/v1/auth/refresh", json=refresh_data)

        # 驗證回應
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["access_token"] == "new_access_token"

    @patch('src.api.routers.auth.AuthenticationService')
    def test_refresh_token_invalid(self, mock_auth_service, client):
        """測試刷新無效 Token"""
        # 設置模擬
        mock_auth_service.refresh_user_token.side_effect = ValueError("Token 無效")

        refresh_data = {
            "refresh_token": "invalid_refresh_token"
        }

        # 執行測試
        response = client.post("/api/v1/auth/refresh", json=refresh_data)

        # 驗證回應
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    def test_refresh_token_missing(self, client):
        """測試刷新 Token 時缺少 Token"""
        # 執行測試
        response = client.post("/api/v1/auth/refresh", json={})

        # 驗證回應
        assert response.status_code == 422  # Validation error

    @patch('src.api.routers.auth.verify_token')
    def test_me_endpoint_success(self, mock_verify_token, client):
        """測試獲取當前用戶資訊成功"""
        # 設置模擬
        mock_verify_token.return_value = {
            "user_id": "test_user_123",
            "username": "testuser",
            "role": "user"
        }

        # 執行測試
        headers = {"Authorization": "Bearer valid_token"}
        response = client.get("/api/v1/auth/me", headers=headers)

        # 驗證回應
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["user_id"] == "test_user_123"
        assert data["data"]["username"] == "testuser"

    @patch('src.api.routers.auth.verify_token')
    def test_me_endpoint_invalid_token(self, mock_verify_token, client):
        """測試獲取當前用戶資訊時 Token 無效"""
        # 設置模擬
        from fastapi import HTTPException, status
        mock_verify_token.side_effect = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 無效"
        )

        # 執行測試
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/auth/me", headers=headers)

        # 驗證回應
        assert response.status_code == 401

    def test_me_endpoint_missing_token(self, client):
        """測試獲取當前用戶資訊時缺少 Token"""
        # 執行測試
        response = client.get("/api/v1/auth/me")

        # 驗證回應
        assert response.status_code == 403  # Forbidden (no token)
