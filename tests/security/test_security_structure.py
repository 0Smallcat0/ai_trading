#!/usr/bin/env python3
"""
安全模組結構測試腳本

此腳本用於測試 Phase 5.3 權限與安全模組的檔案結構和程式碼完整性，
不依賴任何外部套件，只檢查檔案存在性和基本結構。

使用方法：
    python scripts/test_security_structure.py
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def test_file_structure():
    """測試檔案結構"""
    print("=" * 60)
    print("📁 測試檔案結構")
    print("=" * 60)

    # 定義預期的檔案結構
    expected_files = [
        # 核心服務層
        "src/core/security_service.py",
        "src/core/authentication_service.py",
        # UI頁面
        "src/ui/pages/security_management.py",
        # 測試腳本
        "tests/security/test_security_core.py",
        "scripts/test_security_basic.py",
        "tests/security/test_security_structure.py",
    ]

    test_results = []

    for file_path in expected_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
            test_results.append((file_path, True))
        else:
            print(f"❌ {file_path} - 檔案不存在")
            test_results.append((file_path, False))

    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    print(f"\n檔案結構測試: {passed}/{total} 項通過")

    return test_results


def test_code_structure():
    """測試程式碼結構"""
    print("\n" + "=" * 60)
    print("🔍 測試程式碼結構")
    print("=" * 60)

    test_results = []

    # 測試安全服務檔案
    security_service_path = project_root / "src/core/security_service.py"
    if security_service_path.exists():
        print("1. 檢查安全服務檔案...")
        with open(security_service_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 檢查重要類別和方法
        security_checks = [
            ("SecurityService 類別", "class SecurityService"),
            ("密碼雜湊方法", "def hash_password"),
            ("密碼驗證方法", "def verify_password"),
            ("使用者創建方法", "def create_user"),
            ("使用者認證方法", "def authenticate_user"),
            ("權限檢查方法", "def check_permission"),
            ("會話創建方法", "def create_session"),
            ("安全事件記錄", "def log_security_event"),
            ("審計日誌記錄", "def log_audit_event"),
            ("數據加密方法", "def encrypt_sensitive_data"),
        ]

        for check_name, check_pattern in security_checks:
            if check_pattern in content:
                print(f"  ✅ {check_name}")
                test_results.append((f"安全服務-{check_name}", True))
            else:
                print(f"  ❌ {check_name}")
                test_results.append((f"安全服務-{check_name}", False))
    else:
        print("❌ 安全服務檔案不存在")
        test_results.append(("安全服務檔案", False))

    # 測試認證服務檔案
    auth_service_path = project_root / "src/core/authentication_service.py"
    if auth_service_path.exists():
        print("\n2. 檢查認證服務檔案...")
        with open(auth_service_path, "r", encoding="utf-8") as f:
            content = f.read()

        auth_checks = [
            ("AuthenticationService 類別", "class AuthenticationService"),
            ("密碼登入方法", "def login_with_password"),
            ("2FA驗證方法", "def verify_2fa_totp"),
            ("JWT生成方法", "def generate_jwt_token"),
            ("JWT驗證方法", "def verify_jwt_token"),
            ("2FA設定方法", "def setup_2fa_totp"),
            ("密碼變更方法", "def change_password"),
            ("登出方法", "def logout"),
        ]

        for check_name, check_pattern in auth_checks:
            if check_pattern in content:
                print(f"  ✅ {check_name}")
                test_results.append((f"認證服務-{check_name}", True))
            else:
                print(f"  ❌ {check_name}")
                test_results.append((f"認證服務-{check_name}", False))
    else:
        print("❌ 認證服務檔案不存在")
        test_results.append(("認證服務檔案", False))

    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    print(f"\n程式碼結構測試: {passed}/{total} 項通過")

    return test_results


def test_database_schema():
    """測試資料庫模式"""
    print("\n" + "=" * 60)
    print("🗄️ 測試資料庫模式")
    print("=" * 60)

    schema_path = project_root / "src/database/schema.py"
    if not schema_path.exists():
        print("❌ 資料庫模式檔案不存在")
        return [("資料庫模式檔案", False)]

    with open(schema_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 檢查安全相關表格
    table_checks = [
        ("User 表格", "class User(Base)"),
        ("Role 表格", "class Role(Base)"),
        ("UserRole 表格", "class UserRole(Base)"),
        ("Permission 表格", "class Permission(Base)"),
        ("SecurityEvent 表格", "class SecurityEvent(Base)"),
        ("AuditLog 表格", "class AuditLog(Base)"),
        ("UserSession 表格", "class UserSession(Base)"),
    ]

    test_results = []

    for check_name, check_pattern in table_checks:
        if check_pattern in content:
            print(f"✅ {check_name}")
            test_results.append((f"資料庫-{check_name}", True))
        else:
            print(f"❌ {check_name}")
            test_results.append((f"資料庫-{check_name}", False))

    # 檢查重要欄位
    field_checks = [
        ("使用者密碼雜湊", "password_hash"),
        ("兩步驗證設定", "two_factor_enabled"),
        ("角色權限設定", "permissions"),
        ("安全事件類型", "event_type"),
        ("審計操作類型", "operation_type"),
        ("會話狀態", "session_status"),
    ]

    for check_name, check_pattern in field_checks:
        if check_pattern in content:
            print(f"✅ {check_name}")
            test_results.append((f"欄位-{check_name}", True))
        else:
            print(f"❌ {check_name}")
            test_results.append((f"欄位-{check_name}", False))

    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    print(f"\n資料庫模式測試: {passed}/{total} 項通過")

    return test_results


def run_all_tests():
    """運行所有測試"""
    print("🚀 開始 Phase 5.3 權限與安全模組結構測試")
    print("測試時間:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print(f"專案根目錄: {project_root}")

    # 運行各項測試
    all_results = []

    file_results = test_file_structure()
    all_results.extend(file_results)

    code_results = test_code_structure()
    all_results.extend(code_results)

    db_results = test_database_schema()
    all_results.extend(db_results)

    # 顯示測試結果摘要
    print("\n" + "=" * 60)
    print("📊 測試結果摘要")
    print("=" * 60)

    passed = sum(1 for _, result in all_results if result)
    total = len(all_results)

    print(f"總計: {passed}/{total} 項測試通過")
    print(f"通過率: {passed/total*100:.1f}%")

    if passed == total:
        print("🎉 所有結構測試通過！Phase 5.3 權限與安全模組結構完整")
    elif passed >= total * 0.8:
        print("✅ 大部分測試通過，模組結構基本完整")
    else:
        print("⚠️ 多項測試失敗，請檢查模組結構")

    # 顯示失敗的測試項目
    failed_tests = [name for name, result in all_results if not result]
    if failed_tests:
        print(f"\n❌ 失敗的測試項目 ({len(failed_tests)} 項):")
        for test_name in failed_tests:
            print(f"  - {test_name}")

    return passed >= total * 0.8  # 80%通過率視為成功


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
