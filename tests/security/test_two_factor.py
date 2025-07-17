"""
多重身份驗證測試

此模組測試 2FA/MFA 功能的完整性和安全性。
"""

import pytest
import time
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from src.core.two_factor_service import TwoFactorService, SMSService
from src.database.schema import User


class TestTwoFactorService:
    """測試 TwoFactorService 類別"""
    
    @pytest.fixture
    def two_factor_service(self):
        """創建 TwoFactorService 實例"""
        with patch('src.core.two_factor_service.create_engine'):
            service = TwoFactorService()
            return service
    
    @pytest.fixture
    def mock_user(self):
        """創建模擬使用者"""
        user = Mock(spec=User)
        user.user_id = "test_user_123"
        user.email = "test@example.com"
        user.two_factor_enabled = False
        user.two_factor_secret = None
        user.backup_codes = None
        user.failed_login_attempts = 0
        user.is_locked = False
        user.locked_at = None
        return user
    
    def test_setup_totp_success(self, two_factor_service, mock_user):
        """測試 TOTP 設定成功"""
        with patch.object(two_factor_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            result = two_factor_service.setup_totp("test_user_123", "test@example.com")
            
            assert "secret" in result
            assert "qr_code" in result
            assert "backup_codes" in result
            assert "setup_token" in result
            assert len(result["backup_codes"]) == 10
    
    def test_setup_totp_user_not_found(self, two_factor_service):
        """測試使用者不存在的情況"""
        with patch.object(two_factor_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = None
            
            with pytest.raises(ValueError, match="使用者不存在"):
                two_factor_service.setup_totp("nonexistent_user", "test@example.com")
    
    def test_setup_totp_already_enabled(self, two_factor_service, mock_user):
        """測試已啟用 2FA 的情況"""
        mock_user.two_factor_enabled = True
        
        with patch.object(two_factor_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            with pytest.raises(ValueError, match="使用者已啟用兩步驗證"):
                two_factor_service.setup_totp("test_user_123", "test@example.com")
    
    @patch('pyotp.TOTP')
    def test_verify_totp_success(self, mock_totp_class, two_factor_service, mock_user):
        """測試 TOTP 驗證成功"""
        mock_user.two_factor_enabled = True
        mock_user.two_factor_secret = "test_secret"
        
        mock_totp = Mock()
        mock_totp.verify.return_value = True
        mock_totp_class.return_value = mock_totp
        
        with patch.object(two_factor_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            success, message = two_factor_service.verify_totp("test_user_123", "123456")
            
            assert success is True
            assert message == "驗證成功"
            assert mock_user.failed_login_attempts == 0
    
    @patch('pyotp.TOTP')
    def test_verify_totp_failure(self, mock_totp_class, two_factor_service, mock_user):
        """測試 TOTP 驗證失敗"""
        mock_user.two_factor_enabled = True
        mock_user.two_factor_secret = "test_secret"
        
        mock_totp = Mock()
        mock_totp.verify.return_value = False
        mock_totp_class.return_value = mock_totp
        
        with patch.object(two_factor_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            success, message = two_factor_service.verify_totp("test_user_123", "wrong_code")
            
            assert success is False
            assert "驗證碼錯誤" in message
            assert mock_user.failed_login_attempts == 1
    
    def test_verify_backup_code_success(self, two_factor_service, mock_user):
        """測試備用碼驗證成功"""
        import hashlib
        
        backup_code = "12345678"
        backup_code_hash = hashlib.sha256(backup_code.encode()).hexdigest()
        
        mock_user.two_factor_enabled = True
        mock_user.backup_codes = [backup_code_hash, "other_hash"]
        
        with patch.object(two_factor_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            success, message = two_factor_service.verify_backup_code("test_user_123", backup_code)
            
            assert success is True
            assert "驗證成功" in message
            assert backup_code_hash not in mock_user.backup_codes
    
    def test_verify_backup_code_failure(self, two_factor_service, mock_user):
        """測試備用碼驗證失敗"""
        mock_user.two_factor_enabled = True
        mock_user.backup_codes = ["some_hash"]
        
        with patch.object(two_factor_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            success, message = two_factor_service.verify_backup_code("test_user_123", "wrong_code")
            
            assert success is False
            assert message == "備用碼錯誤"
    
    def test_disable_2fa_success(self, two_factor_service, mock_user):
        """測試停用 2FA 成功"""
        mock_user.two_factor_enabled = True
        mock_user.two_factor_secret = "test_secret"
        mock_user.backup_codes = ["hash1", "hash2"]
        
        with patch.object(two_factor_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            success, message = two_factor_service.disable_2fa("test_user_123", "password")
            
            assert success is True
            assert message == "兩步驗證已停用"
            assert mock_user.two_factor_enabled is False
            assert mock_user.two_factor_secret is None
            assert mock_user.backup_codes is None
    
    def test_regenerate_backup_codes(self, two_factor_service, mock_user):
        """測試重新生成備用碼"""
        mock_user.two_factor_enabled = True
        
        with patch.object(two_factor_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            success, message, codes = two_factor_service.regenerate_backup_codes("test_user_123")
            
            assert success is True
            assert message == "備用碼已重新生成"
            assert len(codes) == 10
            assert all(len(code) == 8 for code in codes)
    
    def test_get_2fa_status(self, two_factor_service, mock_user):
        """測試獲取 2FA 狀態"""
        mock_user.two_factor_enabled = True
        mock_user.backup_codes = ["hash1", "hash2", "hash3"]
        mock_user.failed_login_attempts = 1
        
        with patch.object(two_factor_service, 'session_factory') as mock_session_factory:
            mock_session = Mock()
            mock_session_factory.return_value.__enter__.return_value = mock_session
            mock_session.query.return_value.filter.return_value.first.return_value = mock_user
            
            status = two_factor_service.get_2fa_status("test_user_123")
            
            assert status["enabled"] is True
            assert status["backup_codes_count"] == 3
            assert status["failed_attempts"] == 1
    
    def test_generate_backup_codes(self, two_factor_service):
        """測試生成備用碼"""
        codes = two_factor_service._generate_backup_codes()
        
        assert len(codes) == 10
        assert all(len(code) == 8 for code in codes)
        assert all(code.isdigit() for code in codes)
        assert len(set(codes)) == 10  # 確保所有碼都不同
    
    def test_setup_token_generation_and_verification(self, two_factor_service):
        """測試設定令牌的生成和驗證"""
        user_id = "test_user_123"
        secret = "test_secret"
        
        # 生成令牌
        token = two_factor_service._generate_setup_token(user_id, secret)
        
        # 驗證令牌
        assert two_factor_service._verify_setup_token(token, user_id) is True
        
        # 驗證錯誤的使用者 ID
        assert two_factor_service._verify_setup_token(token, "wrong_user") is False
        
        # 提取 secret
        extracted_secret = two_factor_service._extract_secret_from_token(token)
        assert extracted_secret == secret
    
    def test_user_lockout(self, two_factor_service, mock_user):
        """測試使用者鎖定機制"""
        mock_user.two_factor_enabled = True
        mock_user.two_factor_secret = "test_secret"
        mock_user.failed_login_attempts = 2  # 接近鎖定閾值
        
        with patch('pyotp.TOTP') as mock_totp_class:
            mock_totp = Mock()
            mock_totp.verify.return_value = False
            mock_totp_class.return_value = mock_totp
            
            with patch.object(two_factor_service, 'session_factory') as mock_session_factory:
                mock_session = Mock()
                mock_session_factory.return_value.__enter__.return_value = mock_session
                mock_session.query.return_value.filter.return_value.first.return_value = mock_user
                
                success, message = two_factor_service.verify_totp("test_user_123", "wrong_code")
                
                assert success is False
                assert "帳戶已被鎖定" in message
                assert mock_user.is_locked is True
                assert mock_user.locked_reason == "2FA 驗證失敗次數過多"


class TestSMSService:
    """測試 SMSService 類別"""
    
    @pytest.fixture
    def sms_service(self):
        """創建 SMSService 實例"""
        return SMSService()
    
    def test_send_verification_code_success(self, sms_service):
        """測試發送驗證碼成功"""
        phone_number = "+886912345678"
        user_id = "test_user_123"
        
        success, message = sms_service.send_verification_code(phone_number, user_id)
        
        assert success is True
        assert message == "驗證碼已發送"
        assert phone_number in sms_service._verification_codes
    
    def test_send_verification_code_rate_limit(self, sms_service):
        """測試發送頻率限制"""
        phone_number = "+886912345678"
        user_id = "test_user_123"
        
        # 第一次發送
        sms_service.send_verification_code(phone_number, user_id)
        
        # 立即再次發送應該被限制
        success, message = sms_service.send_verification_code(phone_number, user_id)
        
        assert success is False
        assert "發送過於頻繁" in message
    
    def test_verify_sms_code_success(self, sms_service):
        """測試 SMS 驗證碼驗證成功"""
        phone_number = "+886912345678"
        user_id = "test_user_123"
        
        # 發送驗證碼
        sms_service.send_verification_code(phone_number, user_id)
        
        # 獲取驗證碼
        code = sms_service._verification_codes[phone_number]["code"]
        
        # 驗證
        success, message = sms_service.verify_sms_code(phone_number, code, user_id)
        
        assert success is True
        assert message == "驗證成功"
        assert phone_number not in sms_service._verification_codes
    
    def test_verify_sms_code_failure(self, sms_service):
        """測試 SMS 驗證碼驗證失敗"""
        phone_number = "+886912345678"
        user_id = "test_user_123"
        
        # 發送驗證碼
        sms_service.send_verification_code(phone_number, user_id)
        
        # 使用錯誤的驗證碼
        success, message = sms_service.verify_sms_code(phone_number, "wrong_code", user_id)
        
        assert success is False
        assert "驗證碼錯誤" in message
    
    def test_verify_sms_code_expired(self, sms_service):
        """測試過期的 SMS 驗證碼"""
        phone_number = "+886912345678"
        user_id = "test_user_123"
        
        # 發送驗證碼
        sms_service.send_verification_code(phone_number, user_id)
        
        # 模擬時間過去
        sms_service._verification_codes[phone_number]["created_at"] = time.time() - 400  # 超過 5 分鐘
        
        code = sms_service._verification_codes[phone_number]["code"]
        success, message = sms_service.verify_sms_code(phone_number, code, user_id)
        
        assert success is False
        assert "驗證碼已過期" in message
    
    def test_verify_sms_code_max_attempts(self, sms_service):
        """測試 SMS 驗證碼最大嘗試次數"""
        phone_number = "+886912345678"
        user_id = "test_user_123"
        
        # 發送驗證碼
        sms_service.send_verification_code(phone_number, user_id)
        
        # 嘗試 3 次錯誤驗證
        for i in range(3):
            success, message = sms_service.verify_sms_code(phone_number, "wrong_code", user_id)
            assert success is False
        
        # 第 4 次嘗試應該被拒絕
        success, message = sms_service.verify_sms_code(phone_number, "wrong_code", user_id)
        assert success is False
        assert "驗證失敗次數過多" in message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
