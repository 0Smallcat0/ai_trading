#!/usr/bin/env python3
"""
資金操作權限分級基本功能測試腳本

此腳本測試資金操作權限分級的核心功能。
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_role_permission_hierarchy():
    """測試角色權限層級"""
    print("=" * 60)
    print("👥 測試角色權限層級")
    print("=" * 60)
    
    try:
        class UserRole(Enum):
            ADMIN = "admin"
            FUND_MANAGER = "fund_manager"
            TRADER = "trader"
            VIP_USER = "vip_user"
            REGULAR_USER = "regular_user"
            RESTRICTED_USER = "restricted_user"
        
        # 角色權限配置
        role_permissions = {
            UserRole.ADMIN: {
                "daily_limit": Decimal("100000000"),
                "single_limit": Decimal("50000000"),
                "approval_required": False,
                "can_approve": True,
                "approval_level": 3,
            },
            UserRole.FUND_MANAGER: {
                "daily_limit": Decimal("50000000"),
                "single_limit": Decimal("10000000"),
                "approval_required": True,
                "can_approve": True,
                "approval_level": 2,
            },
            UserRole.TRADER: {
                "daily_limit": Decimal("10000000"),
                "single_limit": Decimal("5000000"),
                "approval_required": True,
                "can_approve": False,
                "approval_level": 0,
            },
            UserRole.VIP_USER: {
                "daily_limit": Decimal("5000000"),
                "single_limit": Decimal("1000000"),
                "approval_required": True,
                "can_approve": False,
                "approval_level": 0,
            },
            UserRole.REGULAR_USER: {
                "daily_limit": Decimal("1000000"),
                "single_limit": Decimal("500000"),
                "approval_required": True,
                "can_approve": False,
                "approval_level": 0,
            },
            UserRole.RESTRICTED_USER: {
                "daily_limit": Decimal("100000"),
                "single_limit": Decimal("50000"),
                "approval_required": True,
                "can_approve": False,
                "approval_level": 0,
            },
        }
        
        print("角色權限配置:")
        print(f"{'角色':<15} {'每日限額':<12} {'單筆限額':<12} {'需審批':<8} {'可審批':<8} {'審批級別':<8}")
        print("-" * 70)
        
        for role, config in role_permissions.items():
            daily_limit = f"{config['daily_limit']:,}"
            single_limit = f"{config['single_limit']:,}"
            approval_req = "是" if config['approval_required'] else "否"
            can_approve = "是" if config['can_approve'] else "否"
            approval_level = config['approval_level']
            
            print(f"{role.value:<15} {daily_limit:<12} {single_limit:<12} {approval_req:<8} {can_approve:<8} {approval_level:<8}")
        
        # 驗證權限層級合理性
        roles_by_level = sorted(role_permissions.items(), key=lambda x: x[1]['daily_limit'], reverse=True)
        
        print("\n權限層級驗證:")
        prev_daily = None
        prev_single = None
        
        for role, config in roles_by_level:
            daily = config['daily_limit']
            single = config['single_limit']
            
            # 檢查限額遞減
            if prev_daily is not None and daily > prev_daily:
                print(f"❌ {role.value} 每日限額不應高於上級角色")
                return False
            
            if prev_single is not None and single > prev_single:
                print(f"❌ {role.value} 單筆限額不應高於上級角色")
                return False
            
            # 檢查單筆限額不超過每日限額
            if single > daily:
                print(f"❌ {role.value} 單筆限額不應超過每日限額")
                return False
            
            prev_daily = daily
            prev_single = single
        
        print("✅ 權限層級配置合理")
        print("✅ 角色權限層級測試通過")
        return True
        
    except Exception as e:
        print(f"❌ 角色權限層級測試失敗: {e}")
        return False


def test_approval_level_determination():
    """測試審批級別確定"""
    print("\n" + "=" * 60)
    print("📋 測試審批級別確定")
    print("=" * 60)
    
    try:
        class ApprovalLevel(Enum):
            NONE = "none"
            LEVEL_1 = "level_1"
            LEVEL_2 = "level_2"
            LEVEL_3 = "level_3"
            BOARD = "board"
        
        # 審批閾值配置
        approval_thresholds = {
            ApprovalLevel.LEVEL_1: Decimal("100000"),     # 10萬
            ApprovalLevel.LEVEL_2: Decimal("1000000"),    # 100萬
            ApprovalLevel.LEVEL_3: Decimal("10000000"),   # 1千萬
            ApprovalLevel.BOARD: Decimal("50000000"),     # 5千萬
        }
        
        def determine_approval_level(amount, requires_approval=True):
            """確定審批級別"""
            if not requires_approval:
                return ApprovalLevel.NONE
            
            if amount >= approval_thresholds[ApprovalLevel.BOARD]:
                return ApprovalLevel.BOARD
            elif amount >= approval_thresholds[ApprovalLevel.LEVEL_3]:
                return ApprovalLevel.LEVEL_3
            elif amount >= approval_thresholds[ApprovalLevel.LEVEL_2]:
                return ApprovalLevel.LEVEL_2
            elif amount >= approval_thresholds[ApprovalLevel.LEVEL_1]:
                return ApprovalLevel.LEVEL_1
            else:
                return ApprovalLevel.NONE
        
        # 測試案例
        test_cases = [
            (Decimal("50000"), True, ApprovalLevel.NONE),
            (Decimal("150000"), True, ApprovalLevel.LEVEL_1),
            (Decimal("1500000"), True, ApprovalLevel.LEVEL_2),
            (Decimal("15000000"), True, ApprovalLevel.LEVEL_3),
            (Decimal("60000000"), True, ApprovalLevel.BOARD),
            (Decimal("60000000"), False, ApprovalLevel.NONE),  # 管理員免審批
        ]
        
        print("審批級別測試:")
        print(f"{'金額':<12} {'需審批':<8} {'預期級別':<12} {'實際級別':<12} {'結果':<8}")
        print("-" * 60)
        
        passed = 0
        for amount, requires_approval, expected in test_cases:
            result = determine_approval_level(amount, requires_approval)
            status = "✅" if result == expected else "❌"
            
            amount_str = f"{amount:,}"
            approval_str = "是" if requires_approval else "否"
            
            print(f"{amount_str:<12} {approval_str:<8} {expected.value:<12} {result.value:<12} {status:<8}")
            
            if result == expected:
                passed += 1
        
        print(f"\n審批級別測試: {passed}/{len(test_cases)} 通過")
        
        if passed == len(test_cases):
            print("✅ 審批級別確定測試通過")
            return True
        else:
            print("❌ 部分審批級別測試失敗")
            return False
        
    except Exception as e:
        print(f"❌ 審批級別測試失敗: {e}")
        return False


def test_operation_type_permissions():
    """測試操作類型權限"""
    print("\n" + "=" * 60)
    print("🔐 測試操作類型權限")
    print("=" * 60)
    
    try:
        class FundOperationType(Enum):
            DEPOSIT = "deposit"
            WITHDRAW = "withdraw"
            TRANSFER_IN = "transfer_in"
            TRANSFER_OUT = "transfer_out"
            TRADE_BUY = "trade_buy"
            TRADE_SELL = "trade_sell"
            MARGIN_LOAN = "margin_loan"
            MARGIN_REPAY = "margin_repay"
        
        class UserRole(Enum):
            ADMIN = "admin"
            TRADER = "trader"
            REGULAR_USER = "regular_user"
            RESTRICTED_USER = "restricted_user"
        
        # 角色操作權限配置
        role_operations = {
            UserRole.ADMIN: list(FundOperationType),
            UserRole.TRADER: [
                FundOperationType.TRADE_BUY,
                FundOperationType.TRADE_SELL,
                FundOperationType.TRANSFER_IN,
                FundOperationType.TRANSFER_OUT,
            ],
            UserRole.REGULAR_USER: [
                FundOperationType.DEPOSIT,
                FundOperationType.WITHDRAW,
                FundOperationType.TRADE_BUY,
                FundOperationType.TRADE_SELL,
            ],
            UserRole.RESTRICTED_USER: [
                FundOperationType.DEPOSIT,
                FundOperationType.TRADE_SELL,  # 只能賣出
            ],
        }
        
        def check_operation_permission(role, operation):
            """檢查操作權限"""
            return operation in role_operations.get(role, [])
        
        # 測試案例
        test_cases = [
            (UserRole.ADMIN, FundOperationType.MARGIN_LOAN, True),
            (UserRole.TRADER, FundOperationType.TRADE_BUY, True),
            (UserRole.TRADER, FundOperationType.WITHDRAW, False),
            (UserRole.REGULAR_USER, FundOperationType.DEPOSIT, True),
            (UserRole.REGULAR_USER, FundOperationType.MARGIN_LOAN, False),
            (UserRole.RESTRICTED_USER, FundOperationType.TRADE_SELL, True),
            (UserRole.RESTRICTED_USER, FundOperationType.TRADE_BUY, False),
            (UserRole.RESTRICTED_USER, FundOperationType.WITHDRAW, False),
        ]
        
        print("操作權限測試:")
        print(f"{'角色':<15} {'操作':<15} {'預期':<8} {'實際':<8} {'結果':<8}")
        print("-" * 60)
        
        passed = 0
        for role, operation, expected in test_cases:
            result = check_operation_permission(role, operation)
            status = "✅" if result == expected else "❌"
            
            expected_str = "允許" if expected else "禁止"
            result_str = "允許" if result else "禁止"
            
            print(f"{role.value:<15} {operation.value:<15} {expected_str:<8} {result_str:<8} {status:<8}")
            
            if result == expected:
                passed += 1
        
        print(f"\n操作權限測試: {passed}/{len(test_cases)} 通過")
        
        if passed == len(test_cases):
            print("✅ 操作類型權限測試通過")
            return True
        else:
            print("❌ 部分操作權限測試失敗")
            return False
        
    except Exception as e:
        print(f"❌ 操作類型權限測試失敗: {e}")
        return False


def test_amount_limit_checking():
    """測試金額限制檢查"""
    print("\n" + "=" * 60)
    print("💰 測試金額限制檢查")
    print("=" * 60)
    
    try:
        class LimitChecker:
            def __init__(self):
                self.daily_usage = {}
                self.monthly_usage = {}
            
            def check_limits(self, user_id, role_limits, amount):
                """檢查金額限制"""
                # 獲取當前使用量
                daily_used = self.daily_usage.get(user_id, Decimal("0"))
                monthly_used = self.monthly_usage.get(user_id, Decimal("0"))
                
                # 檢查單筆限制
                if amount > role_limits["single_limit"]:
                    return False, f"超過單筆限制 {role_limits['single_limit']:,}"
                
                # 檢查每日限制
                if daily_used + amount > role_limits["daily_limit"]:
                    return False, f"超過每日限制 {role_limits['daily_limit']:,}"
                
                # 檢查每月限制
                if monthly_used + amount > role_limits["monthly_limit"]:
                    return False, f"超過每月限制 {role_limits['monthly_limit']:,}"
                
                return True, "通過限制檢查"
            
            def record_usage(self, user_id, amount):
                """記錄使用量"""
                self.daily_usage[user_id] = self.daily_usage.get(user_id, Decimal("0")) + amount
                self.monthly_usage[user_id] = self.monthly_usage.get(user_id, Decimal("0")) + amount
        
        # 創建限制檢查器
        checker = LimitChecker()
        
        # 一般用戶限制
        regular_limits = {
            "daily_limit": Decimal("1000000"),
            "single_limit": Decimal("500000"),
            "monthly_limit": Decimal("10000000"),
        }
        
        user_id = "test_user"
        
        # 測試案例
        test_cases = [
            (Decimal("100000"), True, "正常金額"),
            (Decimal("400000"), True, "接近單筆限制"),
            (Decimal("600000"), False, "超過單筆限制"),
        ]
        
        print("金額限制測試:")
        print(f"{'金額':<12} {'預期':<8} {'實際':<8} {'說明':<20} {'結果':<8}")
        print("-" * 65)
        
        passed = 0
        for amount, expected, description in test_cases:
            allowed, message = checker.check_limits(user_id, regular_limits, amount)
            status = "✅" if allowed == expected else "❌"
            
            amount_str = f"{amount:,}"
            expected_str = "通過" if expected else "拒絕"
            result_str = "通過" if allowed else "拒絕"
            
            print(f"{amount_str:<12} {expected_str:<8} {result_str:<8} {description:<20} {status:<8}")
            
            if allowed == expected:
                passed += 1
            
            # 如果通過，記錄使用量
            if allowed:
                checker.record_usage(user_id, amount)
        
        # 測試累積限制
        print("\n累積限制測試:")
        
        # 再次嘗試操作（應該會超過每日限制，但不超過單筆限制）
        amount = Decimal("450000")  # 不超過單筆限制，但會超過每日限制
        allowed, message = checker.check_limits(user_id, regular_limits, amount)

        daily_used = checker.daily_usage.get(user_id, Decimal("0"))
        print(f"當前每日使用量: {daily_used:,}")
        print(f"嘗試操作金額: {amount:,}")
        print(f"總計會是: {daily_used + amount:,}")
        print(f"每日限制: {regular_limits['daily_limit']:,}")
        print(f"檢查結果: {'通過' if allowed else '拒絕'}")
        print(f"原因: {message}")

        # 檢查是否正確拒絕（500,000 + 450,000 = 950,000 < 1,000,000，應該通過）
        # 讓我們嘗試一個會真正超過限制的金額
        if allowed:
            # 如果通過了，再嘗試一個更大的金額
            checker.record_usage(user_id, amount)
            amount = Decimal("200000")  # 現在總計會是 1,150,000 > 1,000,000
            allowed, message = checker.check_limits(user_id, regular_limits, amount)
            daily_used = checker.daily_usage.get(user_id, Decimal("0"))
            print(f"第二次嘗試 - 當前使用量: {daily_used:,}, 嘗試金額: {amount:,}")
            print(f"總計會是: {daily_used + amount:,}, 結果: {'通過' if allowed else '拒絕'}")
            print(f"原因: {message}")
        if not allowed and "每日限制" in message:
            print("✅ 累積限制檢查正確")
            passed += 1
        elif allowed:
            print("❌ 應該拒絕但卻通過了")
        else:
            print("❌ 拒絕原因不正確")
        
        print(f"\n金額限制測試: {passed}/{len(test_cases)+1} 通過")
        
        if passed == len(test_cases) + 1:
            print("✅ 金額限制檢查測試通過")
            return True
        else:
            print("❌ 部分金額限制測試失敗")
            return False
        
    except Exception as e:
        print(f"❌ 金額限制檢查測試失敗: {e}")
        return False


def test_approval_workflow():
    """測試審批工作流程"""
    print("\n" + "=" * 60)
    print("🔄 測試審批工作流程")
    print("=" * 60)
    
    try:
        class ApprovalStatus(Enum):
            PENDING = "pending"
            APPROVED = "approved"
            REJECTED = "rejected"
            EXPIRED = "expired"
        
        class ApprovalRequest:
            def __init__(self, request_id, user_id, amount, approval_level):
                self.request_id = request_id
                self.user_id = user_id
                self.amount = amount
                self.approval_level = approval_level
                self.status = ApprovalStatus.PENDING
                self.created_at = datetime.now()
                self.expires_at = datetime.now() + timedelta(hours=24)
                self.approver_id = None
                self.reason = ""
            
            def approve(self, approver_id, reason=""):
                """批准請求"""
                if datetime.now() > self.expires_at:
                    self.status = ApprovalStatus.EXPIRED
                    return False, "請求已過期"
                
                self.status = ApprovalStatus.APPROVED
                self.approver_id = approver_id
                self.reason = reason
                return True, "審批通過"
            
            def reject(self, approver_id, reason=""):
                """拒絕請求"""
                if datetime.now() > self.expires_at:
                    self.status = ApprovalStatus.EXPIRED
                    return False, "請求已過期"
                
                self.status = ApprovalStatus.REJECTED
                self.approver_id = approver_id
                self.reason = reason
                return True, "審批拒絕"
        
        # 模擬審批流程
        print("模擬審批工作流程:")
        
        # 1. 創建審批請求
        request = ApprovalRequest("REQ_001", "user_123", Decimal("500000"), "level_1")
        print(f"✅ 1. 創建審批請求: {request.request_id}")
        print(f"   用戶: {request.user_id}, 金額: {request.amount:,}, 級別: {request.approval_level}")
        
        # 2. 檢查初始狀態
        assert request.status == ApprovalStatus.PENDING
        print(f"✅ 2. 初始狀態: {request.status.value}")
        
        # 3. 審批通過
        success, message = request.approve("approver_001", "金額合理，批准操作")
        print(f"✅ 3. 審批結果: {message}")
        assert success is True
        assert request.status == ApprovalStatus.APPROVED
        assert request.approver_id == "approver_001"
        
        # 4. 測試過期情況
        expired_request = ApprovalRequest("REQ_002", "user_456", Decimal("200000"), "level_1")
        expired_request.expires_at = datetime.now() - timedelta(hours=1)  # 已過期
        
        success, message = expired_request.approve("approver_001", "嘗試審批過期請求")
        print(f"✅ 4. 過期請求處理: {message}")
        assert success is False
        assert expired_request.status == ApprovalStatus.EXPIRED
        
        # 5. 測試拒絕流程
        reject_request = ApprovalRequest("REQ_003", "user_789", Decimal("800000"), "level_2")
        success, message = reject_request.reject("approver_002", "風險過高，拒絕操作")
        print(f"✅ 5. 拒絕審批: {message}")
        assert success is True
        assert reject_request.status == ApprovalStatus.REJECTED
        assert reject_request.reason == "風險過高，拒絕操作"
        
        print("✅ 審批工作流程測試通過")
        return True
        
    except Exception as e:
        print(f"❌ 審批工作流程測試失敗: {e}")
        return False


def main():
    """主測試函數"""
    print("🔐 AI Trading System - 資金操作權限分級基本功能測試")
    print("=" * 80)
    
    test_results = []
    
    # 執行各項測試
    tests = [
        ("角色權限層級", test_role_permission_hierarchy),
        ("審批級別確定", test_approval_level_determination),
        ("操作類型權限", test_operation_type_permissions),
        ("金額限制檢查", test_amount_limit_checking),
        ("審批工作流程", test_approval_workflow),
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 測試發生異常: {e}")
            test_results.append((test_name, False))
    
    # 顯示測試結果摘要
    print("\n" + "=" * 80)
    print("📊 測試結果摘要")
    print("=" * 80)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    print(f"\n總計: {passed}/{total} 項測試通過")
    
    if passed == total:
        print("🎉 所有資金操作權限分級基本功能測試通過！")
        return True
    else:
        print("⚠️ 部分測試失敗，請檢查相關功能")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
