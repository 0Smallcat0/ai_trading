"""
API 金鑰安全管理測試

此模組測試 API 金鑰安全管理功能的完整性和安全性。
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.core.api_key_security_service import APIKeySecurityService, KeyStatus, KeyPermission


class TestAPIKeySecurityService:
    """測試 APIKeySecurityService 類別"""
    
    @pytest.fixture
    def api_key_service(self):
        """創建 APIKeySecurityService 實例"""
        with patch('src.core.api_key_security_service.create_engine'):
            service = APIKeySecurityService()
            return service
    
    @pytest.fixture
    def mock_session(self):
        """創建模擬資料庫會話"""
        session = Mock()
        return session
    
    def test_encrypt_decrypt_data(self, api_key_service):
        """測試資料加密和解密"""
        original_data = "test_api_key_12345"
        
        # 加密
        encrypted_data = api_key_service._encrypt_data(original_data)
        assert encrypted_data != original_data
        assert len(encrypted_data) > 0
        
        # 解密
        decrypted_data = api_key_service._decrypt_data(encrypted_data)
        assert decrypted_data == original_data
    
    def test_generate_key_id(self, api_key_service):
        """測試金鑰 ID 生成"""
        key_id1 = api_key_service._generate_key_id()
        key_id2 = api_key_service._generate_key_id()
        
        # 檢查格式
        assert key_id1.startswith("key_")
        assert key_id2.startswith("key_")
        
        # 檢查唯一性
        assert key_id1 != key_id2
        
        # 檢查長度
        assert len(key_id1) > 10
        assert len(key_id2) > 10
    
    def test_is_expiring_soon(self, api_key_service):
        """測試過期檢查"""
        # 測試即將過期的日期
        soon_expire = datetime.now() + timedelta(days=3)
        assert api_key_service._is_expiring_soon(soon_expire) is True
        
        # 測試還有很久才過期的日期
        far_expire = datetime.now() + timedelta(days=30)
        assert api_key_service._is_expiring_soon(far_expire) is False
        
        # 測試已過期的日期
        past_expire = datetime.now() - timedelta(days=1)
        assert api_key_service._is_expiring_soon(past_expire) is True
        
        # 測試 None 值
        assert api_key_service._is_expiring_soon(None) is False
    
    @patch.object(APIKeySecurityService, '_get_user_active_keys_count')
    @patch.object(APIKeySecurityService, '_save_key_record')
    @patch.object(APIKeySecurityService, '_log_security_event')
    def test_create_api_key_success(
        self, 
        mock_log_event, 
        mock_save_record, 
        mock_get_count,
        api_key_service
    ):
        """測試成功創建 API 金鑰"""
        # 設置模擬
        mock_get_count.return_value = 2  # 少於最大限制
        
        with patch.object(api_key_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            
            # 模擬使用者存在
            mock_user = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            # 執行測試
            success, message, key_id = api_key_service.create_api_key(
                user_id="test_user",
                broker_name="test_broker",
                api_key="test_api_key",
                api_secret="test_api_secret",
                permissions=[KeyPermission.READ_ONLY, KeyPermission.TRADE_BASIC],
                description="Test API key"
            )
            
            # 驗證結果
            assert success is True
            assert "創建成功" in message
            assert key_id is not None
            assert key_id.startswith("key_")
            
            # 驗證方法被調用
            mock_save_record.assert_called_once()
            mock_log_event.assert_called_once()
    
    @patch.object(APIKeySecurityService, '_get_user_active_keys_count')
    def test_create_api_key_user_not_found(self, mock_get_count, api_key_service):
        """測試使用者不存在的情況"""
        with patch.object(api_key_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            
            # 模擬使用者不存在
            mock_session.query.return_value.filter.return_value.first.return_value = None
            
            success, message, key_id = api_key_service.create_api_key(
                user_id="nonexistent_user",
                broker_name="test_broker",
                api_key="test_api_key",
                api_secret="test_api_secret",
                permissions=[KeyPermission.READ_ONLY]
            )
            
            assert success is False
            assert "使用者不存在" in message
            assert key_id is None
    
    @patch.object(APIKeySecurityService, '_get_user_active_keys_count')
    def test_create_api_key_limit_exceeded(self, mock_get_count, api_key_service):
        """測試超過金鑰數量限制"""
        mock_get_count.return_value = 5  # 等於最大限制
        
        with patch.object(api_key_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            
            # 模擬使用者存在
            mock_user = Mock()
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            success, message, key_id = api_key_service.create_api_key(
                user_id="test_user",
                broker_name="test_broker",
                api_key="test_api_key",
                api_secret="test_api_secret",
                permissions=[KeyPermission.READ_ONLY]
            )
            
            assert success is False
            assert "最大金鑰數量限制" in message
            assert key_id is None
    
    @patch.object(APIKeySecurityService, '_get_key_record')
    @patch.object(APIKeySecurityService, '_update_usage_stats')
    @patch.object(APIKeySecurityService, '_log_security_event')
    def test_get_api_key_success(
        self, 
        mock_log_event, 
        mock_update_stats, 
        mock_get_record,
        api_key_service
    ):
        """測試成功獲取 API 金鑰"""
        # 設置模擬金鑰記錄
        mock_record = {
            "key_id": "test_key_123",
            "user_id": "test_user",
            "broker_name": "test_broker",
            "encrypted_api_key": api_key_service._encrypt_data("test_api_key"),
            "encrypted_api_secret": api_key_service._encrypt_data("test_secret"),
            "permissions": ["read_only"],
            "description": "Test key",
            "status": KeyStatus.ACTIVE.value,
            "expires_at": datetime.now() + timedelta(days=30),
        }
        mock_get_record.return_value = mock_record
        
        with patch.object(api_key_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            
            success, message, key_data = api_key_service.get_api_key(
                user_id="test_user",
                key_id="test_key_123"
            )
            
            assert success is True
            assert "獲取成功" in message
            assert key_data is not None
            assert key_data["api_key"] == "test_api_key"
            assert key_data["api_secret"] == "test_secret"
            assert key_data["broker_name"] == "test_broker"
    
    @patch.object(APIKeySecurityService, '_get_key_record')
    def test_get_api_key_not_found(self, mock_get_record, api_key_service):
        """測試金鑰不存在"""
        mock_get_record.return_value = None
        
        with patch.object(api_key_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            
            success, message, key_data = api_key_service.get_api_key(
                user_id="test_user",
                key_id="nonexistent_key"
            )
            
            assert success is False
            assert "不存在" in message
            assert key_data is None
    
    @patch.object(APIKeySecurityService, '_get_key_record')
    @patch.object(APIKeySecurityService, '_log_security_event')
    def test_get_api_key_permission_denied(
        self, 
        mock_log_event, 
        mock_get_record,
        api_key_service
    ):
        """測試無權限存取他人金鑰"""
        # 設置模擬金鑰記錄（屬於其他使用者）
        mock_record = {
            "key_id": "test_key_123",
            "user_id": "other_user",  # 不同的使用者
            "broker_name": "test_broker",
            "status": KeyStatus.ACTIVE.value,
        }
        mock_get_record.return_value = mock_record
        
        with patch.object(api_key_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            
            success, message, key_data = api_key_service.get_api_key(
                user_id="test_user",
                key_id="test_key_123"
            )
            
            assert success is False
            assert "無權限" in message
            assert key_data is None
            
            # 驗證記錄了安全事件
            mock_log_event.assert_called_once()
    
    def test_validate_key_permissions(self, api_key_service):
        """測試權限驗證"""
        # 模擬 get_api_key 方法
        with patch.object(api_key_service, 'get_api_key') as mock_get_key:
            # 測試有管理員權限
            mock_get_key.return_value = (True, "成功", {
                "permissions": [KeyPermission.ADMIN.value]
            })
            
            result = api_key_service.validate_key_permissions(
                "test_user", "test_key", KeyPermission.TRADE_ADVANCED
            )
            assert result is True
            
            # 測試有特定權限
            mock_get_key.return_value = (True, "成功", {
                "permissions": [KeyPermission.TRADE_BASIC.value]
            })
            
            result = api_key_service.validate_key_permissions(
                "test_user", "test_key", KeyPermission.TRADE_BASIC
            )
            assert result is True
            
            # 測試權限不足
            mock_get_key.return_value = (True, "成功", {
                "permissions": [KeyPermission.READ_ONLY.value]
            })
            
            result = api_key_service.validate_key_permissions(
                "test_user", "test_key", KeyPermission.TRADE_ADVANCED
            )
            assert result is False
            
            # 測試獲取金鑰失敗
            mock_get_key.return_value = (False, "失敗", None)
            
            result = api_key_service.validate_key_permissions(
                "test_user", "test_key", KeyPermission.READ_ONLY
            )
            assert result is False
    
    @patch.object(APIKeySecurityService, '_get_key_record')
    @patch.object(APIKeySecurityService, '_save_key_backup')
    @patch.object(APIKeySecurityService, '_update_key_record')
    @patch.object(APIKeySecurityService, '_log_security_event')
    def test_rotate_api_key_success(
        self, 
        mock_log_event, 
        mock_update_record, 
        mock_save_backup, 
        mock_get_record,
        api_key_service
    ):
        """測試成功輪換 API 金鑰"""
        # 設置模擬金鑰記錄
        mock_record = {
            "key_id": "test_key_123",
            "user_id": "test_user",
            "broker_name": "test_broker",
            "encrypted_api_key": "old_encrypted_key",
            "encrypted_api_secret": "old_encrypted_secret",
            "rotation_count": 1,
        }
        mock_get_record.return_value = mock_record
        
        with patch.object(api_key_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            
            success, message = api_key_service.rotate_api_key(
                user_id="test_user",
                key_id="test_key_123",
                new_api_key="new_api_key",
                new_api_secret="new_api_secret"
            )
            
            assert success is True
            assert "輪換成功" in message
            
            # 驗證方法被調用
            mock_save_backup.assert_called_once()
            mock_update_record.assert_called_once()
            mock_log_event.assert_called_once()
    
    @patch.object(APIKeySecurityService, '_get_key_record')
    @patch.object(APIKeySecurityService, '_update_key_status')
    @patch.object(APIKeySecurityService, '_log_security_event')
    def test_revoke_api_key_success(
        self, 
        mock_log_event, 
        mock_update_status, 
        mock_get_record,
        api_key_service
    ):
        """測試成功撤銷 API 金鑰"""
        # 設置模擬金鑰記錄
        mock_record = {
            "key_id": "test_key_123",
            "user_id": "test_user",
            "broker_name": "test_broker",
        }
        mock_get_record.return_value = mock_record
        
        with patch.object(api_key_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            
            success, message = api_key_service.revoke_api_key(
                user_id="test_user",
                key_id="test_key_123",
                reason="Security breach"
            )
            
            assert success is True
            assert "已撤銷" in message
            
            # 驗證方法被調用
            mock_update_status.assert_called_once_with(
                mock_session, "test_key_123", KeyStatus.REVOKED, "Security breach"
            )
            mock_log_event.assert_called_once()
    
    @patch.object(APIKeySecurityService, '_get_user_key_records')
    def test_list_user_api_keys(self, mock_get_records, api_key_service):
        """測試列出使用者 API 金鑰"""
        # 設置模擬記錄
        mock_records = [
            {
                "key_id": "key_1",
                "broker_name": "broker_1",
                "description": "Test key 1",
                "permissions": ["read_only"],
                "status": "active",
                "created_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(days=30),
                "last_used_at": None,
                "usage_count": 0,
            },
            {
                "key_id": "key_2",
                "broker_name": "broker_2",
                "description": "Test key 2",
                "permissions": ["trade_basic"],
                "status": "active",
                "created_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(days=5),  # 即將過期
                "last_used_at": datetime.now(),
                "usage_count": 10,
            }
        ]
        mock_get_records.return_value = mock_records
        
        with patch.object(api_key_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            
            result = api_key_service.list_user_api_keys("test_user")
            
            assert len(result) == 2
            assert result[0]["key_id"] == "key_1"
            assert result[0]["is_expiring_soon"] is False
            assert result[1]["key_id"] == "key_2"
            assert result[1]["is_expiring_soon"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
