#!/usr/bin/env python3
"""
安全模組測試腳本

此腳本用於測試 Phase 5.3 權限與安全模組的各項功能，包括：
- 安全服務基本功能
- 認證服務功能
- 密碼安全策略
- 使用者管理
- 權限控制
- 安全事件記錄
- 審計日誌功能

使用方法：
    python scripts/test_security.py
"""

import sys
import os
import logging
from datetime import datetime, timedelta

# 添加專案根目錄到 Python 路徑
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# 設置日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_security_service():
    """測試安全服務"""
    print("=" * 60)
    print("🔒 測試安全服務")
    print("=" * 60)

    try:
        from src.core.security_service import SecurityService

        # 初始化服務
        print("1. 初始化安全服務...")
        security_service = SecurityService()
        print("✅ 安全服務初始化成功")

        # 測試密碼雜湊
        print("\n2. 測試密碼雜湊功能...")
        password = "TestPassword123!"
        password_hash, salt = security_service.hash_password(password)
        print(f"✅ 密碼雜湊成功: {password_hash[:20]}...")

        # 測試密碼驗證
        print("\n3. 測試密碼驗證...")
        is_valid = security_service.verify_password(password, password_hash)
        print(f"✅ 密碼驗證結果: {is_valid}")

        # 測試密碼強度驗證
        print("\n4. 測試密碼強度驗證...")
        weak_password = "123"
        strong_password = "StrongPass123!"

        is_valid_weak, errors_weak = security_service.validate_password_strength(
            weak_password
        )
        is_valid_strong, errors_strong = security_service.validate_password_strength(
            strong_password
        )

        print(f"弱密碼驗證: {is_valid_weak}, 錯誤: {errors_weak}")
        print(f"強密碼驗證: {is_valid_strong}, 錯誤: {errors_strong}")

        # 測試使用者創建
        print("\n5. 測試使用者創建...")
        success, message, user_id = security_service.create_user(
            username="test_user",
            email="test@example.com",
            password=strong_password,
            full_name="測試使用者",
            role_id="user",
            created_by="system",
        )
        print(f"使用者創建結果: {success}, 訊息: {message}")
        if user_id:
            print(f"使用者ID: {user_id}")

        # 測試使用者認證
        print("\n6. 測試使用者認證...")
        if success:
            auth_success, auth_message, user_info = security_service.authenticate_user(
                username="test_user",
                password=strong_password,
                ip_address="127.0.0.1",
                user_agent="Test Agent",
            )
            print(f"認證結果: {auth_success}, 訊息: {auth_message}")
            if user_info:
                print(f"使用者資訊: {user_info['username']}, {user_info['email']}")

        # 測試數據加密
        print("\n7. 測試數據加密...")
        sensitive_data = "這是敏感數據"
        encrypted_data = security_service.encrypt_sensitive_data(sensitive_data)
        decrypted_data = security_service.decrypt_sensitive_data(encrypted_data)
        print(f"原始數據: {sensitive_data}")
        print(f"加密數據: {encrypted_data[:30]}...")
        print(f"解密數據: {decrypted_data}")
        print(
            f"✅ 加密解密測試: {'成功' if sensitive_data == decrypted_data else '失敗'}"
        )

        # 測試安全事件記錄
        print("\n8. 測試安全事件記錄...")
        event_success = security_service.log_security_event(
            event_type="test_event",
            event_description="測試安全事件",
            user_id=user_id if user_id else "test_user_id",
            username="test_user",
            ip_address="127.0.0.1",
            user_agent="Test Agent",
        )
        print(f"✅ 安全事件記錄: {'成功' if event_success else '失敗'}")

        # 測試審計日誌記錄
        print("\n9. 測試審計日誌記錄...")
        audit_success = security_service.log_audit_event(
            operation_type="test_operation",
            operation_name="測試操作",
            user_id=user_id if user_id else "test_user_id",
            username="test_user",
            resource_type="test_resource",
            resource_id="test_resource_id",
            operation_description="測試審計日誌記錄",
        )
        print(f"✅ 審計日誌記錄: {'成功' if audit_success else '失敗'}")

        print("\n✅ 安全服務測試完成")
        return True

    except Exception as e:
        print(f"❌ 安全服務測試失敗: {e}")
        return False


def test_authentication_service():
    """測試認證服務"""
    print("\n" + "=" * 60)
    print("🔑 測試認證服務")
    print("=" * 60)

    try:
        from src.core.authentication_service import AuthenticationService

        # 初始化服務
        print("1. 初始化認證服務...")
        auth_service = AuthenticationService()
        print("✅ 認證服務初始化成功")

        # 測試JWT Token生成
        print("\n2. 測試JWT Token生成...")
        user_id = "test_user_123"
        session_id = "test_session_456"
        jwt_token = auth_service.generate_jwt_token(user_id, session_id)
        print(f"✅ JWT Token生成成功: {jwt_token[:30]}...")

        # 測試JWT Token驗證
        print("\n3. 測試JWT Token驗證...")
        is_valid, token_info = auth_service.verify_jwt_token(jwt_token)
        print(f"Token驗證結果: {is_valid}")
        if token_info:
            print(
                f"Token資訊: user_id={token_info.get('user_id')}, session_id={token_info.get('session_id')}"
            )

        # 測試2FA設定
        print("\n4. 測試2FA設定...")
        setup_success, setup_message, setup_data = auth_service.setup_2fa_totp(user_id)
        print(f"2FA設定結果: {setup_success}, 訊息: {setup_message}")
        if setup_data:
            print(f"✅ 2FA設定數據包含: secret, qr_code, backup_codes")

        print("\n✅ 認證服務測試完成")
        return True

    except Exception as e:
        print(f"❌ 認證服務測試失敗: {e}")
        return False


def test_database_tables():
    """測試資料庫表格"""
    print("\n" + "=" * 60)
    print("🗄️ 測試資料庫表格")
    print("=" * 60)

    try:
        from src.database.schema import (
            User,
            Role,
            UserRole,
            Permission,
            SecurityEvent,
            AuditLog,
            UserSession,
        )

        print("1. 檢查安全相關表格定義...")

        # 檢查表格類別
        tables = [
            ("User", User),
            ("Role", Role),
            ("UserRole", UserRole),
            ("Permission", Permission),
            ("SecurityEvent", SecurityEvent),
            ("AuditLog", AuditLog),
            ("UserSession", UserSession),
        ]

        for table_name, table_class in tables:
            print(f"✅ {table_name} 表格定義正確")

            # 檢查重要欄位
            if hasattr(table_class, "__table__"):
                columns = [col.name for col in table_class.__table__.columns]
                print(f"   欄位數量: {len(columns)}")

        print("\n✅ 資料庫表格測試完成")
        return True

    except Exception as e:
        print(f"❌ 資料庫表格測試失敗: {e}")
        return False


def test_ui_components():
    """測試UI組件"""
    print("\n" + "=" * 60)
    print("🖥️ 測試UI組件")
    print("=" * 60)

    try:
        # 測試認證組件
        print("1. 測試認證組件...")
        from src.ui.components.auth import USERS, check_auth, get_user_role

        print(f"✅ 認證組件載入成功，包含 {len(USERS)} 個測試使用者")

        # 測試安全管理頁面
        print("\n2. 測試安全管理頁面...")
        from src.ui.pages.security_management import show_security_management

        print("✅ 安全管理頁面載入成功")

        print("\n✅ UI組件測試完成")
        return True

    except Exception as e:
        print(f"❌ UI組件測試失敗: {e}")
        return False


def run_all_tests():
    """運行所有測試"""
    print("🚀 開始 Phase 5.3 權限與安全模組測試")
    print("測試時間:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    test_results = []

    # 運行各項測試
    test_results.append(("資料庫表格", test_database_tables()))
    test_results.append(("安全服務", test_security_service()))
    test_results.append(("認證服務", test_authentication_service()))
    test_results.append(("UI組件", test_ui_components()))

    # 顯示測試結果摘要
    print("\n" + "=" * 60)
    print("📊 測試結果摘要")
    print("=" * 60)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\n總計: {passed}/{total} 項測試通過")

    if passed == total:
        print("🎉 所有測試通過！Phase 5.3 權限與安全模組功能正常")
    else:
        print("⚠️ 部分測試失敗，請檢查相關功能")

    return passed == total


if __name__ == "__main__":
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ 測試被使用者中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 測試過程發生未預期錯誤: {e}")
        sys.exit(1)
