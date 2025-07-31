"""
交易操作二次確認測試

此模組測試交易二次確認功能的完整性和安全性。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from src.core.trade_confirmation_service import (
    TradeConfirmationService,
    ConfirmationLevel,
    RiskLevel,
    ConfirmationStatus
)


class TestTradeConfirmationService:
    """測試 TradeConfirmationService 類別"""
    
    @pytest.fixture
    def confirmation_service(self):
        """創建 TradeConfirmationService 實例"""
        with patch('src.core.trade_confirmation_service.create_engine'):
            service = TradeConfirmationService()
            return service
    
    @pytest.fixture
    def sample_trade_data(self):
        """創建範例交易資料"""
        return {
            "symbol": "2330",
            "quantity": 1000,
            "price": 500.0,
            "type": "market",
            "side": "buy",
            "leverage": 1.0,
        }
    
    def test_assess_trade_risk_low(self, confirmation_service, sample_trade_data):
        """測試低風險交易評估"""
        # 小額交易
        trade_data = sample_trade_data.copy()
        trade_data["quantity"] = 100
        trade_data["price"] = 100.0
        
        risk_level, risk_details = confirmation_service._assess_trade_risk("test_user", trade_data)
        
        assert risk_level == RiskLevel.LOW
        assert risk_details["trade_amount"] == 10000  # 100 * 100
        assert risk_details["risk_score"] < 1.0
    
    def test_assess_trade_risk_high(self, confirmation_service, sample_trade_data):
        """測試高風險交易評估"""
        # 高金額交易
        trade_data = sample_trade_data.copy()
        trade_data["quantity"] = 10000
        trade_data["price"] = 200.0
        
        risk_level, risk_details = confirmation_service._assess_trade_risk("test_user", trade_data)
        
        assert risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert risk_details["trade_amount"] == 2000000  # 10000 * 200
        assert "高金額交易" in risk_details["risk_factors"]
    
    def test_assess_trade_risk_critical(self, confirmation_service, sample_trade_data):
        """測試極高風險交易評估"""
        # 極高金額 + 高槓桿交易
        trade_data = sample_trade_data.copy()
        trade_data["quantity"] = 50000
        trade_data["price"] = 200.0
        trade_data["leverage"] = 3.0
        trade_data["type"] = "margin"
        
        risk_level, risk_details = confirmation_service._assess_trade_risk("test_user", trade_data)
        
        assert risk_level == RiskLevel.CRITICAL
        assert risk_details["trade_amount"] == 10000000  # 50000 * 200
        assert "極高金額交易" in risk_details["risk_factors"]
        assert "高槓桿交易" in risk_details["risk_factors"]
        assert "高風險交易類型" in risk_details["risk_factors"]
    
    def test_determine_confirmation_level(self, confirmation_service, sample_trade_data):
        """測試確認級別確定"""
        # 測試不同風險等級對應的確認級別
        test_cases = [
            (RiskLevel.LOW, ConfirmationLevel.NONE),
            (RiskLevel.MEDIUM, ConfirmationLevel.SIMPLE),
            (RiskLevel.HIGH, ConfirmationLevel.SMS),
            (RiskLevel.CRITICAL, ConfirmationLevel.DUAL),
        ]
        
        for risk_level, expected_level in test_cases:
            risk_details = {"trade_amount": 100000}
            level = confirmation_service._determine_confirmation_level(
                "test_user", sample_trade_data, risk_level, risk_details
            )
            assert level == expected_level
    
    def test_auto_confirm_small_trades(self, confirmation_service):
        """測試小額交易自動確認"""
        # 小額交易
        trade_data = {
            "symbol": "2330",
            "quantity": 100,
            "price": 100.0,
            "type": "market",
        }
        
        risk_level = RiskLevel.MEDIUM
        risk_details = {"trade_amount": 10000}  # 小於閾值
        
        level = confirmation_service._determine_confirmation_level(
            "test_user", trade_data, risk_level, risk_details
        )
        
        assert level == ConfirmationLevel.NONE
    
    def test_generate_confirmation_code(self, confirmation_service):
        """測試確認碼生成"""
        code1 = confirmation_service._generate_confirmation_code()
        code2 = confirmation_service._generate_confirmation_code()
        
        # 檢查格式
        assert len(code1) == 6
        assert len(code2) == 6
        assert code1.isdigit()
        assert code2.isdigit()
        
        # 檢查唯一性
        assert code1 != code2
    
    def test_calculate_expiry_time(self, confirmation_service):
        """測試過期時間計算"""
        base_time = datetime.now()
        
        # 測試不同確認級別的過期時間
        test_cases = [
            (ConfirmationLevel.SIMPLE, 300),   # 5分鐘
            (ConfirmationLevel.SMS, 180),      # 3分鐘
            (ConfirmationLevel.EMAIL, 600),    # 10分鐘
            (ConfirmationLevel.ADMIN, 1800),   # 30分鐘
        ]
        
        for level, expected_seconds in test_cases:
            expiry_time = confirmation_service._calculate_expiry_time(level)
            time_diff = (expiry_time - base_time).total_seconds()
            
            # 允許1秒的誤差
            assert abs(time_diff - expected_seconds) <= 1
    
    @patch.object(TradeConfirmationService, '_send_sms_confirmation')
    def test_request_trade_confirmation_sms(self, mock_sms, confirmation_service, sample_trade_data):
        """測試 SMS 確認請求"""
        # 設置模擬
        mock_sms.return_value = (True, "SMS 已發送")
        
        # 高風險交易，應該需要 SMS 確認
        trade_data = sample_trade_data.copy()
        trade_data["quantity"] = 5000
        trade_data["price"] = 300.0
        
        needs_confirmation, message, confirmation_id = confirmation_service.request_trade_confirmation(
            "test_user", trade_data
        )
        
        assert needs_confirmation is True
        assert "SMS確認" in message
        assert confirmation_id is not None
        assert confirmation_id.startswith("CONF_")
        
        # 驗證確認記錄已創建
        assert confirmation_id in confirmation_service._pending_confirmations
        record = confirmation_service._pending_confirmations[confirmation_id]
        assert record["user_id"] == "test_user"
        assert record["status"] == ConfirmationStatus.PENDING.value
    
    def test_request_trade_confirmation_no_confirmation(self, confirmation_service, sample_trade_data):
        """測試無需確認的交易"""
        # 小額交易
        trade_data = sample_trade_data.copy()
        trade_data["quantity"] = 50
        trade_data["price"] = 100.0
        
        needs_confirmation, message, confirmation_id = confirmation_service.request_trade_confirmation(
            "test_user", trade_data
        )
        
        assert needs_confirmation is False
        assert "直接執行" in message
        assert confirmation_id is None
    
    def test_verify_confirmation_success(self, confirmation_service):
        """測試確認驗證成功"""
        # 創建確認記錄
        confirmation_id = "CONF_test123"
        confirmation_code = "123456"
        
        confirmation_record = {
            "confirmation_id": confirmation_id,
            "user_id": "test_user",
            "trade_data": {"symbol": "2330", "quantity": 1000},
            "confirmation_level": ConfirmationLevel.SIMPLE.value,
            "status": ConfirmationStatus.PENDING.value,
            "expires_at": datetime.now() + timedelta(minutes=5),
            "attempts": 0,
        }
        
        confirmation_service._pending_confirmations[confirmation_id] = confirmation_record
        
        # 驗證確認碼
        success, message, trade_data = confirmation_service.verify_confirmation(
            confirmation_id, confirmation_code, "test_user"
        )
        
        assert success is True
        assert "確認成功" in message
        assert trade_data is not None
        assert trade_data["symbol"] == "2330"
        
        # 確認記錄應該被移動到歷史
        assert confirmation_id not in confirmation_service._pending_confirmations
    
    def test_verify_confirmation_wrong_code(self, confirmation_service):
        """測試錯誤確認碼"""
        # 創建確認記錄
        confirmation_id = "CONF_test123"
        
        confirmation_record = {
            "confirmation_id": confirmation_id,
            "user_id": "test_user",
            "confirmation_level": ConfirmationLevel.SIMPLE.value,
            "status": ConfirmationStatus.PENDING.value,
            "expires_at": datetime.now() + timedelta(minutes=5),
            "attempts": 0,
        }
        
        confirmation_service._pending_confirmations[confirmation_id] = confirmation_record
        
        # 使用錯誤的確認碼
        success, message, trade_data = confirmation_service.verify_confirmation(
            confirmation_id, "wrong_code", "test_user"
        )
        
        assert success is False
        assert "確認碼錯誤" in message
        assert trade_data is None
        
        # 嘗試次數應該增加
        assert confirmation_record["attempts"] == 1
    
    def test_verify_confirmation_expired(self, confirmation_service):
        """測試過期確認"""
        # 創建過期的確認記錄
        confirmation_id = "CONF_test123"
        
        confirmation_record = {
            "confirmation_id": confirmation_id,
            "user_id": "test_user",
            "confirmation_level": ConfirmationLevel.SIMPLE.value,
            "status": ConfirmationStatus.PENDING.value,
            "expires_at": datetime.now() - timedelta(minutes=1),  # 已過期
            "attempts": 0,
        }
        
        confirmation_service._pending_confirmations[confirmation_id] = confirmation_record
        
        # 嘗試驗證過期的確認
        success, message, trade_data = confirmation_service.verify_confirmation(
            confirmation_id, "123456", "test_user"
        )
        
        assert success is False
        assert "已過期" in message
        assert trade_data is None
        assert confirmation_record["status"] == ConfirmationStatus.EXPIRED.value
    
    def test_verify_confirmation_unauthorized(self, confirmation_service):
        """測試無權限驗證"""
        # 創建確認記錄
        confirmation_id = "CONF_test123"
        
        confirmation_record = {
            "confirmation_id": confirmation_id,
            "user_id": "other_user",  # 不同的使用者
            "confirmation_level": ConfirmationLevel.SIMPLE.value,
            "status": ConfirmationStatus.PENDING.value,
            "expires_at": datetime.now() + timedelta(minutes=5),
            "attempts": 0,
        }
        
        confirmation_service._pending_confirmations[confirmation_id] = confirmation_record
        
        # 嘗試驗證他人的確認
        success, message, trade_data = confirmation_service.verify_confirmation(
            confirmation_id, "123456", "test_user"
        )
        
        assert success is False
        assert "無權限" in message
        assert trade_data is None
    
    def test_cancel_confirmation(self, confirmation_service):
        """測試取消確認"""
        # 創建確認記錄
        confirmation_id = "CONF_test123"
        
        confirmation_record = {
            "confirmation_id": confirmation_id,
            "user_id": "test_user",
            "status": ConfirmationStatus.PENDING.value,
        }
        
        confirmation_service._pending_confirmations[confirmation_id] = confirmation_record
        
        # 取消確認
        success, message = confirmation_service.cancel_confirmation(confirmation_id, "test_user")
        
        assert success is True
        assert "已取消" in message
        assert confirmation_record["status"] == ConfirmationStatus.CANCELLED.value
        
        # 確認記錄應該被移動到歷史
        assert confirmation_id not in confirmation_service._pending_confirmations
    
    def test_get_pending_confirmations(self, confirmation_service):
        """測試獲取待確認交易"""
        # 創建多個確認記錄
        user_id = "test_user"
        
        # 待確認的記錄
        pending_record = {
            "confirmation_id": "CONF_pending",
            "user_id": user_id,
            "trade_data": {"symbol": "2330"},
            "status": ConfirmationStatus.PENDING.value,
            "expires_at": datetime.now() + timedelta(minutes=5),
        }
        
        # 已過期的記錄
        expired_record = {
            "confirmation_id": "CONF_expired",
            "user_id": user_id,
            "status": ConfirmationStatus.PENDING.value,
            "expires_at": datetime.now() - timedelta(minutes=1),
        }
        
        # 其他使用者的記錄
        other_user_record = {
            "confirmation_id": "CONF_other",
            "user_id": "other_user",
            "status": ConfirmationStatus.PENDING.value,
            "expires_at": datetime.now() + timedelta(minutes=5),
        }
        
        confirmation_service._pending_confirmations.update({
            "CONF_pending": pending_record,
            "CONF_expired": expired_record,
            "CONF_other": other_user_record,
        })
        
        # 獲取待確認交易
        pending = confirmation_service.get_pending_confirmations(user_id)
        
        # 應該只返回有效的待確認記錄
        assert len(pending) == 1
        assert pending[0]["confirmation_id"] == "CONF_pending"
        assert pending[0]["trade_data"]["symbol"] == "2330"
        
        # 過期記錄應該被標記為過期
        assert expired_record["status"] == ConfirmationStatus.EXPIRED.value
    
    def test_is_after_hours_trading(self, confirmation_service):
        """測試盤後交易檢查"""
        with patch('src.core.trade_confirmation_service.datetime') as mock_datetime:
            # 測試交易時間內（上午10點）
            mock_datetime.now.return_value = datetime(2023, 1, 1, 10, 0, 0)
            assert confirmation_service._is_after_hours_trading() is False
            
            # 測試交易時間內（下午1點）
            mock_datetime.now.return_value = datetime(2023, 1, 1, 13, 0, 0)
            assert confirmation_service._is_after_hours_trading() is False
            
            # 測試盤後時間（下午3點）
            mock_datetime.now.return_value = datetime(2023, 1, 1, 15, 0, 0)
            assert confirmation_service._is_after_hours_trading() is True
            
            # 測試盤前時間（早上8點）
            mock_datetime.now.return_value = datetime(2023, 1, 1, 8, 0, 0)
            assert confirmation_service._is_after_hours_trading() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
