"""安全工具單元測試

此模組測試安全工具的核心功能，包括 Token 驗證、權限檢查等。
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from src.api.utils.security import (
    verify_token,
    get_current_user,
    get_current_active_user,
    require_permission,
)


class TestSecurityUtils:
    """安全工具測試類"""

    @pytest.mark.asyncio
    @patch('src.api.utils.security.TokenBlacklist')
    @patch('src.api.utils.security.TokenManager')
    async def test_verify_token_success(self, mock_token_manager, mock_token_blacklist):
        """測試 Token 驗證成功"""
        # 設置模擬
        mock_token_blacklist.is_blacklisted.return_value = False
        mock_token_manager.verify_token.return_value = {
            "user_id": "test_user_123",
            "username": "testuser",
            "role": "user"
        }

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid_token"
        )

        # 執行測試
        result = await verify_token(credentials)

        # 驗證結果
        assert result["user_id"] == "test_user_123"
        assert result["username"] == "testuser"
        assert result["role"] == "user"

        # 驗證方法調用
        mock_token_blacklist.is_blacklisted.assert_called_once_with("valid_token")
        mock_token_manager.verify_token.assert_called_once_with("valid_token")

    @pytest.mark.asyncio
    @patch('src.api.utils.security.TokenBlacklist')
    async def test_verify_token_blacklisted(self, mock_token_blacklist):
        """測試 Token 在黑名單中"""
        # 設置模擬
        mock_token_blacklist.is_blacklisted.return_value = True

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="blacklisted_token"
        )

        # 執行測試並驗證異常
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(credentials)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Token 已失效"

    @pytest.mark.asyncio
    @patch('src.api.utils.security.TokenBlacklist')
    @patch('src.api.utils.security.TokenManager')
    async def test_verify_token_invalid(self, mock_token_manager, mock_token_blacklist):
        """測試無效 Token"""
        # 設置模擬
        mock_token_blacklist.is_blacklisted.return_value = False
        mock_token_manager.verify_token.side_effect = Exception("Token 無效")

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid_token"
        )

        # 執行測試並驗證異常
        with pytest.raises(HTTPException) as exc_info:
            await verify_token(credentials)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Token 驗證失敗"

    @pytest.mark.asyncio
    async def test_get_current_user_success(self):
        """測試獲取當前用戶成功"""
        token_payload = {
            "user_id": "test_user_123",
            "username": "testuser",
            "role": "user"
        }

        # 執行測試
        result = await get_current_user(token_payload)

        # 驗證結果
        assert result["user_id"] == "test_user_123"
        assert result["username"] == "testuser"
        assert result["role"] == "user"

    @pytest.mark.asyncio
    async def test_get_current_active_user_success(self):
        """測試獲取當前活躍用戶成功"""
        current_user = {
            "user_id": "test_user_123",
            "username": "testuser",
            "role": "user"
        }

        # 執行測試
        result = await get_current_active_user(current_user)

        # 驗證結果
        assert result == current_user

    @pytest.mark.asyncio
    async def test_get_current_active_user_no_user_id(self):
        """測試獲取當前活躍用戶但無用戶ID"""
        current_user = {
            "username": "testuser",
            "role": "user"
            # 缺少 user_id
        }

        # 執行測試並驗證異常
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(current_user)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "用戶未認證"

    @patch('src.api.utils.security.PermissionChecker')
    @pytest.mark.asyncio
    async def test_require_permission_success(self, mock_permission_checker):
        """測試權限檢查成功"""
        # 設置模擬
        mock_permission_checker.has_permission.return_value = True

        # 獲取權限檢查器
        permission_checker = require_permission("read_data")

        # 創建模擬用戶
        current_user = {
            "user_id": "test_user_123",
            "username": "testuser",
            "role": "admin"
        }

        # 執行測試（這是一個異步函數）
        result = await permission_checker(current_user)

        # 驗證結果（應該返回用戶資訊）
        assert result == current_user

        # 驗證方法調用
        mock_permission_checker.has_permission.assert_called_once_with("admin", "read_data")

    @patch('src.api.utils.security.PermissionChecker')
    @pytest.mark.asyncio
    async def test_require_permission_denied(self, mock_permission_checker):
        """測試權限檢查失敗"""
        # 設置模擬
        mock_permission_checker.has_permission.return_value = False

        # 獲取權限檢查器
        permission_checker = require_permission("admin_access")

        # 創建模擬用戶
        current_user = {
            "user_id": "test_user_123",
            "username": "testuser",
            "role": "user"
        }

        # 執行測試並驗證異常
        with pytest.raises(HTTPException) as exc_info:
            await permission_checker(current_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN

    def test_require_permission_decorator_structure(self):
        """測試權限要求裝飾器結構"""
        # 執行測試
        decorator = require_permission("test_permission")

        # 驗證結構
        assert callable(decorator)
        # 權限檢查器本身就是一個可調用的函數

    @pytest.mark.asyncio
    async def test_get_current_user_missing_fields(self):
        """測試獲取當前用戶但缺少欄位"""
        token_payload = {
            "user_id": "test_user_123",
            # 缺少 username 和 role
        }

        # 執行測試
        result = await get_current_user(token_payload)

        # 驗證結果（應該處理缺少的欄位）
        assert result["user_id"] == "test_user_123"
        assert result["username"] is None
        assert result["role"] is None

    @pytest.mark.asyncio
    async def test_get_current_user_empty_payload(self):
        """測試獲取當前用戶但載荷為空"""
        token_payload = {}

        # 執行測試
        result = await get_current_user(token_payload)

        # 驗證結果
        assert result["user_id"] is None
        assert result["username"] is None
        assert result["role"] is None

    @pytest.mark.asyncio
    @patch('src.api.utils.security.TokenBlacklist')
    @patch('src.api.utils.security.TokenManager')
    async def test_verify_token_with_logging(self, mock_token_manager, mock_token_blacklist):
        """測試 Token 驗證時的日誌記錄"""
        # 設置模擬
        mock_token_blacklist.is_blacklisted.return_value = False
        mock_token_manager.verify_token.side_effect = Exception("測試錯誤")

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="test_token"
        )

        # 使用 patch 來模擬 logger
        with patch('src.api.utils.security.logger') as mock_logger:
            # 執行測試並驗證異常
            with pytest.raises(HTTPException):
                await verify_token(credentials)

            # 驗證日誌記錄
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args[0]
            assert "Token 驗證錯誤" in call_args[0]

    @pytest.mark.asyncio
    async def test_get_current_active_user_with_none_user_id(self):
        """測試獲取當前活躍用戶但用戶ID為None"""
        current_user = {
            "user_id": None,
            "username": "testuser",
            "role": "user"
        }

        # 執行測試並驗證異常
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(current_user)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "用戶未認證"

    @pytest.mark.asyncio
    async def test_get_current_active_user_with_empty_user_id(self):
        """測試獲取當前活躍用戶但用戶ID為空字符串"""
        current_user = {
            "user_id": "",
            "username": "testuser",
            "role": "user"
        }

        # 執行測試並驗證異常
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(current_user)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "用戶未認證"
