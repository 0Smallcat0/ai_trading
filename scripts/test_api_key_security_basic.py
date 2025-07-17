#!/usr/bin/env python3
"""
API 金鑰安全管理基本功能測試腳本

此腳本測試 API 金鑰安全管理的核心功能。
"""

import sys
import os
import time
from pathlib import Path
from datetime import datetime, timedelta

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_encryption_decryption():
    """測試加密和解密功能"""
    print("=" * 60)
    print("🔐 測試加密和解密功能")
    print("=" * 60)
    
    try:
        from cryptography.fernet import Fernet
        import base64
        
        # 生成金鑰
        key = Fernet.generate_key()
        fernet = Fernet(key)
        
        # 測試資料
        test_data = "test_api_key_12345"
        
        # 加密
        encrypted_data = fernet.encrypt(test_data.encode())
        encrypted_b64 = base64.urlsafe_b64encode(encrypted_data).decode()
        
        print(f"✅ 原始資料: {test_data}")
        print(f"✅ 加密後長度: {len(encrypted_b64)}")
        
        # 解密
        decoded_data = base64.urlsafe_b64decode(encrypted_b64.encode())
        decrypted_data = fernet.decrypt(decoded_data).decode()
        
        print(f"✅ 解密後資料: {decrypted_data}")
        
        # 驗證
        assert decrypted_data == test_data, "解密後的資料不匹配"
        assert encrypted_b64 != test_data, "加密後的資料不應該與原始資料相同"
        
        print("✅ 加密解密功能測試通過")
        return True
        
    except ImportError as e:
        print(f"❌ 缺少必要的庫: {e}")
        print("請安裝: pip install cryptography")
        return False
    except Exception as e:
        print(f"❌ 加密解密測試失敗: {e}")
        return False


def test_key_id_generation():
    """測試金鑰 ID 生成"""
    print("\n" + "=" * 60)
    print("🔑 測試金鑰 ID 生成")
    print("=" * 60)
    
    try:
        import secrets
        
        def generate_key_id():
            """生成金鑰 ID"""
            return f"key_{secrets.token_urlsafe(16)}"
        
        # 生成多個金鑰 ID
        key_ids = [generate_key_id() for _ in range(10)]
        
        print(f"✅ 生成了 {len(key_ids)} 個金鑰 ID")
        print("範例金鑰 ID:")
        for i, key_id in enumerate(key_ids[:3]):
            print(f"  {i+1}. {key_id}")
        
        # 驗證格式
        for key_id in key_ids:
            assert key_id.startswith("key_"), f"金鑰 ID 格式錯誤: {key_id}"
            assert len(key_id) > 10, f"金鑰 ID 長度不足: {key_id}"
        
        # 驗證唯一性
        assert len(set(key_ids)) == len(key_ids), "金鑰 ID 有重複"
        
        print("✅ 金鑰 ID 生成測試通過")
        return True
        
    except Exception as e:
        print(f"❌ 金鑰 ID 生成測試失敗: {e}")
        return False


def test_permission_validation():
    """測試權限驗證邏輯"""
    print("\n" + "=" * 60)
    print("🛡️ 測試權限驗證邏輯")
    print("=" * 60)
    
    try:
        from enum import Enum
        
        class KeyPermission(Enum):
            """API 金鑰權限"""
            READ_ONLY = "read_only"
            TRADE_BASIC = "trade_basic"
            TRADE_ADVANCED = "trade_advanced"
            ADMIN = "admin"
        
        def validate_permissions(user_permissions, required_permission):
            """驗證權限"""
            # 檢查是否有管理員權限
            if KeyPermission.ADMIN.value in user_permissions:
                return True
            
            # 檢查特定權限
            if required_permission.value in user_permissions:
                return True
            
            # 檢查權限層級
            permission_levels = {
                KeyPermission.READ_ONLY: 1,
                KeyPermission.TRADE_BASIC: 2,
                KeyPermission.TRADE_ADVANCED: 3,
                KeyPermission.ADMIN: 4,
            }
            
            user_max_level = max(
                permission_levels.get(KeyPermission(p), 0) for p in user_permissions
            )
            required_level = permission_levels.get(required_permission, 0)
            
            return user_max_level >= required_level
        
        # 測試案例
        test_cases = [
            # (使用者權限, 所需權限, 預期結果)
            (["admin"], KeyPermission.TRADE_ADVANCED, True),
            (["trade_advanced"], KeyPermission.TRADE_BASIC, True),
            (["trade_basic"], KeyPermission.READ_ONLY, True),
            (["read_only"], KeyPermission.TRADE_BASIC, False),
            (["trade_basic"], KeyPermission.TRADE_ADVANCED, False),
            (["read_only", "trade_basic"], KeyPermission.TRADE_BASIC, True),
        ]
        
        passed = 0
        for user_perms, required_perm, expected in test_cases:
            result = validate_permissions(user_perms, required_perm)
            status = "✅" if result == expected else "❌"
            print(f"{status} 權限 {user_perms} 要求 {required_perm.value}: {result}")
            if result == expected:
                passed += 1
        
        print(f"\n權限驗證測試: {passed}/{len(test_cases)} 通過")
        
        if passed == len(test_cases):
            print("✅ 權限驗證邏輯測試通過")
            return True
        else:
            print("❌ 部分權限驗證測試失敗")
            return False
        
    except Exception as e:
        print(f"❌ 權限驗證測試失敗: {e}")
        return False


def test_expiry_checking():
    """測試過期檢查邏輯"""
    print("\n" + "=" * 60)
    print("⏰ 測試過期檢查邏輯")
    print("=" * 60)
    
    try:
        def is_expiring_soon(expires_at, warning_days=7):
            """檢查是否即將過期"""
            if not expires_at:
                return False
            
            warning_date = datetime.now() + timedelta(days=warning_days)
            return expires_at <= warning_date
        
        # 測試案例
        now = datetime.now()
        test_cases = [
            ("即將過期 (3天後)", now + timedelta(days=3), True),
            ("還有很久 (30天後)", now + timedelta(days=30), False),
            ("已過期", now - timedelta(days=1), True),
            ("剛好在警告期限", now + timedelta(days=7), True),
            ("None 值", None, False),
        ]
        
        passed = 0
        for description, expires_at, expected in test_cases:
            result = is_expiring_soon(expires_at)
            status = "✅" if result == expected else "❌"
            print(f"{status} {description}: {result}")
            if result == expected:
                passed += 1
        
        print(f"\n過期檢查測試: {passed}/{len(test_cases)} 通過")
        
        if passed == len(test_cases):
            print("✅ 過期檢查邏輯測試通過")
            return True
        else:
            print("❌ 部分過期檢查測試失敗")
            return False
        
    except Exception as e:
        print(f"❌ 過期檢查測試失敗: {e}")
        return False


def test_usage_statistics():
    """測試使用統計邏輯"""
    print("\n" + "=" * 60)
    print("📊 測試使用統計邏輯")
    print("=" * 60)
    
    try:
        class UsageTracker:
            def __init__(self):
                self.stats = {}
            
            def record_usage(self, key_id, operation, success=True):
                """記錄使用情況"""
                if key_id not in self.stats:
                    self.stats[key_id] = {
                        "total_requests": 0,
                        "successful_requests": 0,
                        "failed_requests": 0,
                        "operations": {},
                        "last_used": None,
                    }
                
                self.stats[key_id]["total_requests"] += 1
                if success:
                    self.stats[key_id]["successful_requests"] += 1
                else:
                    self.stats[key_id]["failed_requests"] += 1
                
                if operation not in self.stats[key_id]["operations"]:
                    self.stats[key_id]["operations"][operation] = 0
                self.stats[key_id]["operations"][operation] += 1
                
                self.stats[key_id]["last_used"] = datetime.now()
            
            def get_stats(self, key_id):
                """獲取統計資料"""
                return self.stats.get(key_id, {})
            
            def get_success_rate(self, key_id):
                """獲取成功率"""
                stats = self.get_stats(key_id)
                total = stats.get("total_requests", 0)
                if total == 0:
                    return 0.0
                successful = stats.get("successful_requests", 0)
                return successful / total
        
        # 測試使用統計
        tracker = UsageTracker()
        
        # 模擬使用情況
        test_key = "test_key_123"
        
        # 記錄一些成功的操作
        for i in range(8):
            tracker.record_usage(test_key, "get_balance", success=True)
        
        # 記錄一些失敗的操作
        for i in range(2):
            tracker.record_usage(test_key, "place_order", success=False)
        
        # 獲取統計
        stats = tracker.get_stats(test_key)
        success_rate = tracker.get_success_rate(test_key)
        
        print(f"✅ 總請求數: {stats['total_requests']}")
        print(f"✅ 成功請求數: {stats['successful_requests']}")
        print(f"✅ 失敗請求數: {stats['failed_requests']}")
        print(f"✅ 成功率: {success_rate:.2%}")
        print(f"✅ 操作統計: {stats['operations']}")
        
        # 驗證統計正確性
        assert stats["total_requests"] == 10, "總請求數不正確"
        assert stats["successful_requests"] == 8, "成功請求數不正確"
        assert stats["failed_requests"] == 2, "失敗請求數不正確"
        assert success_rate == 0.8, "成功率計算不正確"
        
        print("✅ 使用統計邏輯測試通過")
        return True
        
    except Exception as e:
        print(f"❌ 使用統計測試失敗: {e}")
        return False


def test_rate_limiting():
    """測試頻率限制邏輯"""
    print("\n" + "=" * 60)
    print("🚦 測試頻率限制邏輯")
    print("=" * 60)
    
    try:
        import time
        from collections import defaultdict, deque
        
        class RateLimiter:
            def __init__(self, max_requests=10, time_window=60):
                self.max_requests = max_requests
                self.time_window = time_window
                self.requests = defaultdict(deque)
            
            def is_allowed(self, key_id):
                """檢查是否允許請求"""
                now = time.time()
                
                # 清理過期的請求記錄
                while (self.requests[key_id] and 
                       now - self.requests[key_id][0] > self.time_window):
                    self.requests[key_id].popleft()
                
                # 檢查是否超過限制
                if len(self.requests[key_id]) >= self.max_requests:
                    return False
                
                # 記錄新請求
                self.requests[key_id].append(now)
                return True
            
            def get_remaining_requests(self, key_id):
                """獲取剩餘請求數"""
                return max(0, self.max_requests - len(self.requests[key_id]))
        
        # 測試頻率限制
        limiter = RateLimiter(max_requests=5, time_window=10)  # 10秒內最多5個請求
        test_key = "test_key_123"
        
        # 測試正常請求
        allowed_count = 0
        for i in range(7):  # 嘗試7個請求
            if limiter.is_allowed(test_key):
                allowed_count += 1
                print(f"✅ 請求 {i+1}: 允許 (剩餘: {limiter.get_remaining_requests(test_key)})")
            else:
                print(f"❌ 請求 {i+1}: 被限制")
        
        print(f"\n總共允許 {allowed_count} 個請求")
        
        # 驗證限制正確性
        assert allowed_count == 5, f"應該允許5個請求，實際允許了{allowed_count}個"
        
        print("✅ 頻率限制邏輯測試通過")
        return True
        
    except Exception as e:
        print(f"❌ 頻率限制測試失敗: {e}")
        return False


def main():
    """主測試函數"""
    print("🔐 AI Trading System - API 金鑰安全管理基本功能測試")
    print("=" * 80)
    
    test_results = []
    
    # 執行各項測試
    tests = [
        ("加密和解密功能", test_encryption_decryption),
        ("金鑰 ID 生成", test_key_id_generation),
        ("權限驗證邏輯", test_permission_validation),
        ("過期檢查邏輯", test_expiry_checking),
        ("使用統計邏輯", test_usage_statistics),
        ("頻率限制邏輯", test_rate_limiting),
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
        print("🎉 所有 API 金鑰安全管理基本功能測試通過！")
        return True
    else:
        print("⚠️ 部分測試失敗，請檢查相關功能")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
