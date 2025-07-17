"""
資金操作權限分級測試

此模組測試資金操作權限分級功能的完整性和安全性。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal

from src.core.fund_permission_service import (
    FundPermissionService,
    UserRole,
    FundOperationType,
    ApprovalStatus,
    ApprovalLevel
)


class TestFundPermissionService:
    """測試 FundPermissionService 類別"""
    
    @pytest.fixture
    def fund_service(self):
        """創建 FundPermissionService 實例"""
        with patch('src.core.fund_permission_service.create_engine'):
            service = FundPermissionService()
            return service
    
    def test_role_permissions_configuration(self, fund_service):
        """測試角色權限配置"""
        # 檢查所有角色都有配置
        for role in UserRole:
            assert role in fund_service.role_permissions
            
            config = fund_service.role_permissions[role]
            
            # 檢查必要的配置項目
            assert "daily_limit" in config
            assert "single_limit" in config
            assert "monthly_limit" in config
            assert "allowed_operations" in config
            assert "approval_required" in config
            assert "can_approve" in config
            assert "approval_level" in config
            
            # 檢查限制合理性
            assert config["single_limit"] <= config["daily_limit"]
            assert config["daily_limit"] <= config["monthly_limit"]
    
    def test_admin_permissions(self, fund_service):
        """測試管理員權限"""
        admin_config = fund_service.role_permissions[UserRole.ADMIN]
        
        # 管理員應該有最高權限
        assert admin_config["daily_limit"] == Decimal("100000000")
        assert admin_config["approval_required"] is False
        assert admin_config["can_approve"] is True
        assert admin_config["approval_level"] == 3
        assert len(admin_config["allowed_operations"]) == len(FundOperationType)
    
    def test_restricted_user_permissions(self, fund_service):
        """測試受限用戶權限"""
        restricted_config = fund_service.role_permissions[UserRole.RESTRICTED_USER]
        
        # 受限用戶應該有最低權限
        assert restricted_config["daily_limit"] == Decimal("100000")
        assert restricted_config["approval_required"] is True
        assert restricted_config["can_approve"] is False
        assert restricted_config["approval_level"] == 0
        
        # 只能執行特定操作
        allowed_ops = restricted_config["allowed_operations"]
        assert FundOperationType.DEPOSIT in allowed_ops
        assert FundOperationType.TRADE_SELL in allowed_ops
        assert FundOperationType.TRADE_BUY not in allowed_ops
        assert FundOperationType.WITHDRAW not in allowed_ops
    
    @patch.object(FundPermissionService, '_get_user_role')
    def test_check_operation_type_permission(self, mock_get_role, fund_service):
        """測試操作類型權限檢查"""
        # 設置模擬
        mock_get_role.return_value = UserRole.TRADER
        
        # 交易員可以執行交易操作
        assert fund_service._check_operation_type_permission(
            UserRole.TRADER, FundOperationType.TRADE_BUY
        ) is True
        
        assert fund_service._check_operation_type_permission(
            UserRole.TRADER, FundOperationType.TRADE_SELL
        ) is True
        
        # 交易員不能執行出金操作
        assert fund_service._check_operation_type_permission(
            UserRole.TRADER, FundOperationType.WITHDRAW
        ) is False
    
    @patch.object(FundPermissionService, '_get_user_role')
    @patch.object(FundPermissionService, '_get_user_daily_usage')
    @patch.object(FundPermissionService, '_get_user_monthly_usage')
    def test_check_amount_limits(self, mock_monthly, mock_daily, mock_role, fund_service):
        """測試金額限制檢查"""
        # 設置模擬
        mock_role.return_value = UserRole.REGULAR_USER
        mock_daily.return_value = Decimal("100000")  # 已使用10萬
        mock_monthly.return_value = Decimal("1000000")  # 已使用100萬
        
        user_id = "test_user"
        user_role = UserRole.REGULAR_USER
        
        # 測試單筆限制
        result = fund_service._check_amount_limits(user_id, user_role, Decimal("600000"))
        assert result["allowed"] is False
        assert "單筆限制" in result["reason"]
        
        # 測試每日限制
        result = fund_service._check_amount_limits(user_id, user_role, Decimal("400000"))
        assert result["allowed"] is False
        assert "每日限制" in result["reason"]
        
        # 測試每月限制
        mock_daily.return_value = Decimal("0")  # 重置每日使用量
        result = fund_service._check_amount_limits(user_id, user_role, Decimal("400000"))
        assert result["allowed"] is True
    
    def test_determine_approval_level(self, fund_service):
        """測試審批級別確定"""
        # 測試不同金額對應的審批級別
        test_cases = [
            (Decimal("50000"), ApprovalLevel.NONE),      # 5萬，無需審批
            (Decimal("150000"), ApprovalLevel.LEVEL_1),   # 15萬，一級審批
            (Decimal("1500000"), ApprovalLevel.LEVEL_2),  # 150萬，二級審批
            (Decimal("15000000"), ApprovalLevel.LEVEL_3), # 1500萬，三級審批
            (Decimal("60000000"), ApprovalLevel.BOARD),   # 6000萬，董事會審批
        ]
        
        for amount, expected_level in test_cases:
            level = fund_service._determine_approval_level(
                UserRole.REGULAR_USER, FundOperationType.WITHDRAW, amount
            )
            assert level == expected_level
    
    @patch.object(FundPermissionService, '_get_user_role')
    def test_check_fund_operation_permission_allowed(self, mock_get_role, fund_service):
        """測試允許的資金操作"""
        # 設置模擬
        mock_get_role.return_value = UserRole.ADMIN
        
        # 管理員小額操作應該直接允許
        allowed, message, approval_id = fund_service.check_fund_operation_permission(
            "admin_user", FundOperationType.WITHDRAW, Decimal("50000")
        )
        
        assert allowed is True
        assert "已批准" in message
        assert approval_id is None
    
    @patch.object(FundPermissionService, '_get_user_role')
    def test_check_fund_operation_permission_needs_approval(self, mock_get_role, fund_service):
        """測試需要審批的資金操作"""
        # 設置模擬
        mock_get_role.return_value = UserRole.REGULAR_USER
        
        # 一般用戶大額操作需要審批
        allowed, message, approval_id = fund_service.check_fund_operation_permission(
            "regular_user", FundOperationType.WITHDRAW, Decimal("200000")
        )
        
        assert allowed is False
        assert "審批" in message
        assert approval_id is not None
        assert approval_id.startswith("APPR_")
    
    @patch.object(FundPermissionService, '_get_user_role')
    def test_check_fund_operation_permission_forbidden(self, mock_get_role, fund_service):
        """測試禁止的資金操作"""
        # 設置模擬
        mock_get_role.return_value = UserRole.RESTRICTED_USER
        
        # 受限用戶不能執行買入操作
        allowed, message, approval_id = fund_service.check_fund_operation_permission(
            "restricted_user", FundOperationType.TRADE_BUY, Decimal("10000")
        )
        
        assert allowed is False
        assert "不允許執行" in message
        assert approval_id is None
    
    @patch.object(FundPermissionService, '_get_user_role')
    @patch.object(FundPermissionService, '_check_approver_permission')
    def test_approve_fund_operation_success(self, mock_check_approver, mock_get_role, fund_service):
        """測試成功審批資金操作"""
        # 設置模擬
        mock_get_role.return_value = UserRole.REGULAR_USER
        mock_check_approver.return_value = True
        
        # 創建審批請求
        approval_id = fund_service._create_approval_request(
            "test_user", FundOperationType.WITHDRAW, Decimal("200000"), ApprovalLevel.LEVEL_1
        )
        
        # 審批通過
        success, message = fund_service.approve_fund_operation(
            approval_id, "approver_user", True, "審批通過"
        )
        
        assert success is True
        assert "審批通過" in message
        assert approval_id not in fund_service._pending_approvals
    
    @patch.object(FundPermissionService, '_get_user_role')
    @patch.object(FundPermissionService, '_check_approver_permission')
    def test_approve_fund_operation_rejected(self, mock_check_approver, mock_get_role, fund_service):
        """測試拒絕審批資金操作"""
        # 設置模擬
        mock_get_role.return_value = UserRole.REGULAR_USER
        mock_check_approver.return_value = True
        
        # 創建審批請求
        approval_id = fund_service._create_approval_request(
            "test_user", FundOperationType.WITHDRAW, Decimal("200000"), ApprovalLevel.LEVEL_1
        )
        
        # 審批拒絕
        success, message = fund_service.approve_fund_operation(
            approval_id, "approver_user", False, "風險過高"
        )
        
        assert success is True
        assert "被拒絕" in message
        assert approval_id not in fund_service._pending_approvals
    
    @patch.object(FundPermissionService, '_get_user_role')
    @patch.object(FundPermissionService, '_check_approver_permission')
    def test_approve_fund_operation_insufficient_permission(self, mock_check_approver, mock_get_role, fund_service):
        """測試審批人權限不足"""
        # 設置模擬
        mock_get_role.return_value = UserRole.REGULAR_USER
        mock_check_approver.return_value = False  # 權限不足
        
        # 創建審批請求
        approval_id = fund_service._create_approval_request(
            "test_user", FundOperationType.WITHDRAW, Decimal("200000"), ApprovalLevel.LEVEL_1
        )
        
        # 嘗試審批
        success, message = fund_service.approve_fund_operation(
            approval_id, "low_privilege_user", True, "嘗試審批"
        )
        
        assert success is False
        assert "權限不足" in message
    
    def test_check_approver_permission(self, fund_service):
        """測試審批人權限檢查"""
        with patch.object(fund_service, '_get_user_role') as mock_get_role:
            # 管理員可以審批所有級別
            mock_get_role.return_value = UserRole.ADMIN
            assert fund_service._check_approver_permission("admin", ApprovalLevel.LEVEL_1.value) is True
            assert fund_service._check_approver_permission("admin", ApprovalLevel.LEVEL_3.value) is True
            assert fund_service._check_approver_permission("admin", ApprovalLevel.BOARD.value) is True
            
            # 資金管理員可以審批二級以下
            mock_get_role.return_value = UserRole.FUND_MANAGER
            assert fund_service._check_approver_permission("fund_mgr", ApprovalLevel.LEVEL_1.value) is True
            assert fund_service._check_approver_permission("fund_mgr", ApprovalLevel.LEVEL_2.value) is True
            
            # 交易員不能審批
            mock_get_role.return_value = UserRole.TRADER
            assert fund_service._check_approver_permission("trader", ApprovalLevel.LEVEL_1.value) is False
    
    @patch.object(FundPermissionService, '_get_user_role')
    def test_get_user_fund_limits(self, mock_get_role, fund_service):
        """測試獲取使用者資金限制"""
        # 設置模擬
        mock_get_role.return_value = UserRole.VIP_USER
        
        limits = fund_service.get_user_fund_limits("vip_user")
        
        assert limits["user_role"] == "vip_user"
        assert "daily_limit" in limits
        assert "single_limit" in limits
        assert "monthly_limit" in limits
        assert "daily_used" in limits
        assert "monthly_used" in limits
        assert "allowed_operations" in limits
        assert limits["approval_required"] is True
        assert limits["can_approve"] is False
    
    def test_get_pending_approvals(self, fund_service):
        """測試獲取待審批操作"""
        # 創建測試審批請求
        approval_id1 = fund_service._create_approval_request(
            "user1", FundOperationType.WITHDRAW, Decimal("200000"), ApprovalLevel.LEVEL_1
        )
        
        approval_id2 = fund_service._create_approval_request(
            "user2", FundOperationType.TRANSFER_OUT, Decimal("500000"), ApprovalLevel.LEVEL_2
        )
        
        # 獲取所有待審批
        pending = fund_service.get_pending_approvals()
        
        assert len(pending) == 2
        
        approval_ids = [p["approval_id"] for p in pending]
        assert approval_id1 in approval_ids
        assert approval_id2 in approval_ids
        
        # 獲取特定用戶的待審批
        user1_pending = fund_service.get_pending_approvals("user1")
        assert len(user1_pending) == 1
        assert user1_pending[0]["approval_id"] == approval_id1
    
    def test_user_usage_tracking(self, fund_service):
        """測試使用者使用量追蹤"""
        user_id = "test_user"
        
        # 初始使用量應該為0
        daily_usage = fund_service._get_user_daily_usage(user_id)
        monthly_usage = fund_service._get_user_monthly_usage(user_id)
        
        assert daily_usage == Decimal("0")
        assert monthly_usage == Decimal("0")
        
        # 更新使用量
        fund_service._update_user_usage(user_id, Decimal("100000"))
        
        # 檢查更新後的使用量
        daily_usage = fund_service._get_user_daily_usage(user_id)
        monthly_usage = fund_service._get_user_monthly_usage(user_id)
        
        assert daily_usage == Decimal("100000")
        assert monthly_usage == Decimal("100000")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
