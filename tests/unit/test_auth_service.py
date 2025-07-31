"""認證服務單元測試

此模組測試認證服務的核心功能，包括用戶驗證、會話管理等。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any

from src.core.services.auth_service import AuthenticationService


class TestAuthenticationService:
    """認證服務測試類"""

    def test_init_with_bcrypt_available(self):
        """測試在 bcrypt 可用時的初始化"""
        with patch('src.core.services.auth_service.BCRYPT_AVAILABLE', True):
            service = AuthenticationService()
            assert service is not None

    def test_init_without_bcrypt_raises_error(self):
        """測試在 bcrypt 不可用時初始化拋出錯誤"""
        with patch('src.core.services.auth_service.BCRYPT_AVAILABLE', False):
            with pytest.raises(ImportError, match="bcrypt 套件未安裝"):
                AuthenticationService()

    @patch('src.core.services.auth_service.get_user_by_username')
    @patch('src.core.services.auth_service.verify_password')
    @patch('src.core.services.auth_service.audit_logger')
    def test_authenticate_user_success(
        self, 
        mock_audit_logger, 
        mock_verify_password, 
        mock_get_user,
        mock_user
    ):
        """測試用戶認證成功"""
        # 設置模擬
        mock_get_user.return_value = mock_user
        mock_verify_password.return_value = True
        mock_audit_logger.log_user_action = Mock()

        with patch('src.core.services.auth_service.BCRYPT_AVAILABLE', True):
            service = AuthenticationService()
            
            # 執行測試
            result = service.authenticate_user(
                username="testuser",
                password="password123",
                ip_address="127.0.0.1"
            )

            # 驗證結果
            assert result == mock_user
            mock_get_user.assert_called_once_with("testuser")
            mock_verify_password.assert_called_once_with("password123", mock_user["password_hash"])
            mock_audit_logger.log_user_action.assert_called_once()

    @patch('src.core.services.auth_service.get_user_by_username')
    @patch('src.core.services.auth_service.audit_logger')
    def test_authenticate_user_not_found(self, mock_audit_logger, mock_get_user):
        """測試用戶不存在的情況"""
        # 設置模擬
        mock_get_user.return_value = None
        mock_audit_logger.log_security_event = Mock()

        with patch('src.core.services.auth_service.BCRYPT_AVAILABLE', True):
            service = AuthenticationService()
            
            # 執行測試並驗證異常
            with pytest.raises(ValueError, match="用戶名或密碼錯誤"):
                service.authenticate_user(
                    username="nonexistent",
                    password="password123",
                    ip_address="127.0.0.1"
                )

            # 驗證安全事件記錄
            mock_audit_logger.log_security_event.assert_called_once()

    @patch('src.core.services.auth_service.get_user_by_username')
    @patch('src.core.services.auth_service.audit_logger')
    def test_authenticate_user_inactive(self, mock_audit_logger, mock_get_user, mock_user):
        """測試用戶帳戶被停用的情況"""
        # 設置模擬
        inactive_user = mock_user.copy()
        inactive_user["is_active"] = False
        mock_get_user.return_value = inactive_user
        mock_audit_logger.log_security_event = Mock()

        with patch('src.core.services.auth_service.BCRYPT_AVAILABLE', True):
            service = AuthenticationService()
            
            # 執行測試並驗證異常
            with pytest.raises(ValueError, match="帳戶已被停用"):
                service.authenticate_user(
                    username="testuser",
                    password="password123",
                    ip_address="127.0.0.1"
                )

            # 驗證安全事件記錄
            mock_audit_logger.log_security_event.assert_called_once()

    @patch('src.core.services.auth_service.get_user_by_username')
    @patch('src.core.services.auth_service.verify_password')
    @patch('src.core.services.auth_service.audit_logger')
    def test_authenticate_user_wrong_password(
        self, 
        mock_audit_logger, 
        mock_verify_password, 
        mock_get_user,
        mock_user
    ):
        """測試密碼錯誤的情況"""
        # 設置模擬
        mock_get_user.return_value = mock_user
        mock_verify_password.return_value = False
        mock_audit_logger.log_security_event = Mock()

        with patch('src.core.services.auth_service.BCRYPT_AVAILABLE', True):
            service = AuthenticationService()
            
            # 執行測試並驗證異常
            with pytest.raises(ValueError, match="用戶名或密碼錯誤"):
                service.authenticate_user(
                    username="testuser",
                    password="wrongpassword",
                    ip_address="127.0.0.1"
                )

            # 驗證安全事件記錄
            mock_audit_logger.log_security_event.assert_called_once()

    @patch('src.core.services.auth_service.TokenManager')
    @patch('src.core.services.auth_service.SessionManager')
    @patch('src.core.services.auth_service.audit_logger')
    def test_create_user_session_success(
        self, 
        mock_audit_logger, 
        mock_session_manager, 
        mock_token_manager,
        mock_user
    ):
        """測試創建用戶會話成功"""
        # 設置模擬
        mock_token_manager.create_access_token.return_value = "access_token_123"
        mock_token_manager.create_refresh_token.return_value = "refresh_token_123"
        mock_session_manager.create_session = Mock()
        mock_audit_logger.log_user_action = Mock()

        # 執行測試
        result = AuthenticationService.create_user_session(
            user=mock_user,
            remember_me=False,
            device_info={"user_agent": "test_agent"},
            ip_address="127.0.0.1"
        )

        # 驗證結果
        assert result["access_token"] == "access_token_123"
        assert result["refresh_token"] == "refresh_token_123"
        assert result["token_type"] == "bearer"
        assert result["expires_in"] == "86400"

        # 驗證方法調用
        mock_token_manager.create_access_token.assert_called_once()
        mock_token_manager.create_refresh_token.assert_called_once()
        mock_session_manager.create_session.assert_called_once()
        mock_audit_logger.log_user_action.assert_called_once()

    @patch('src.core.services.auth_service.TokenManager')
    @patch('src.core.services.auth_service.SessionManager')
    @patch('src.core.services.auth_service.audit_logger')
    def test_create_user_session_remember_me(
        self, 
        mock_audit_logger, 
        mock_session_manager, 
        mock_token_manager,
        mock_user
    ):
        """測試創建用戶會話（記住我）"""
        # 設置模擬
        mock_token_manager.create_access_token.return_value = "access_token_123"
        mock_token_manager.create_refresh_token.return_value = "refresh_token_123"
        mock_session_manager.create_session = Mock()
        mock_audit_logger.log_user_action = Mock()

        # 執行測試
        result = AuthenticationService.create_user_session(
            user=mock_user,
            remember_me=True,
            device_info={"user_agent": "test_agent"},
            ip_address="127.0.0.1"
        )

        # 驗證結果
        assert result["expires_in"] == "604800"  # 7天

        # 驗證 Token 創建時傳入了 expires_delta
        call_args = mock_token_manager.create_access_token.call_args
        assert call_args[1]["expires_delta"] is not None

    @patch('src.core.services.auth_service.TokenBlacklist')
    @patch('src.core.services.auth_service.SessionManager')
    @patch('src.core.services.auth_service.audit_logger')
    def test_logout_user_success(
        self, 
        mock_audit_logger, 
        mock_session_manager, 
        mock_token_blacklist
    ):
        """測試用戶登出成功"""
        # 設置模擬
        mock_token_blacklist.add_token = Mock()
        mock_session_manager.end_session = Mock()
        mock_audit_logger.log_user_action = Mock()

        # 執行測試
        AuthenticationService.logout_user(
            token="test_token",
            user_id="test_user_123",
            username="testuser",
            ip_address="127.0.0.1"
        )

        # 驗證方法調用
        mock_token_blacklist.add_token.assert_called_once_with("test_token")
        mock_session_manager.end_session.assert_called_once_with("test_token")
        mock_audit_logger.log_user_action.assert_called_once()

    @patch('src.core.services.auth_service.TokenManager')
    @patch('src.core.services.auth_service.audit_logger')
    def test_refresh_user_token_success(self, mock_audit_logger, mock_token_manager):
        """測試刷新用戶Token成功"""
        # 設置模擬
        mock_token_manager.refresh_access_token.return_value = "new_access_token"
        mock_token_manager.verify_token.return_value = {
            "user_id": "test_user_123",
            "username": "testuser"
        }
        mock_audit_logger.log_user_action = Mock()

        # 執行測試
        result = AuthenticationService.refresh_user_token(
            refresh_token="refresh_token_123",
            ip_address="127.0.0.1"
        )

        # 驗證結果
        assert result["access_token"] == "new_access_token"
        assert result["token_type"] == "bearer"
        assert result["expires_in"] == "86400"

        # 驗證方法調用
        mock_token_manager.refresh_access_token.assert_called_once_with("refresh_token_123")
        mock_token_manager.verify_token.assert_called_once_with("new_access_token")
        mock_audit_logger.log_user_action.assert_called_once()

    @patch('src.core.services.auth_service.TokenManager')
    def test_refresh_user_token_failure(self, mock_token_manager):
        """測試刷新用戶Token失敗"""
        # 設置模擬
        mock_token_manager.refresh_access_token.side_effect = Exception("Token 無效")

        # 執行測試並驗證異常
        with pytest.raises(ValueError, match="Token刷新失敗"):
            AuthenticationService.refresh_user_token(
                refresh_token="invalid_token",
                ip_address="127.0.0.1"
            )
