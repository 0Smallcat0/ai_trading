#!/usr/bin/env python3
"""
測試框架驗證腳本

此腳本驗證效能測試和安全測試框架是否正確安裝和配置。
"""

import os
import sys
import importlib
from pathlib import Path


def check_file_exists(file_path, description):
    """檢查文件是否存在"""
    if Path(file_path).exists():
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} (不存在)")
        return False


def check_import(module_name, description):
    """檢查模組是否可以導入"""
    try:
        importlib.import_module(module_name)
        print(f"✅ {description}: {module_name}")
        return True
    except ImportError as e:
        print(f"❌ {description}: {module_name} (導入失敗: {e})")
        return False


def verify_performance_framework():
    """驗證效能測試框架"""
    print("\n🚀 驗證效能測試框架...")

    success = True

    # 檢查核心文件
    files_to_check = [
        ("tests/performance/__init__.py", "效能測試初始化文件"),
        ("tests/performance/conftest.py", "效能測試 pytest 配置"),
        ("tests/performance/test_api_performance.py", "API 效能測試"),
        ("tests/performance/test_load_testing.py", "負載測試"),
        ("tests/performance/test_memory_profiling.py", "記憶體分析測試"),
        ("tests/performance/utils/__init__.py", "效能工具初始化"),
        ("tests/performance/utils/performance_monitor.py", "效能監控器"),
        ("tests/performance/utils/load_tester.py", "負載測試器"),
        ("tests/performance/utils/memory_profiler.py", "記憶體分析器"),
        ("tests/performance/utils/report_generator.py", "報告生成器"),
    ]

    for file_path, description in files_to_check:
        success &= check_file_exists(file_path, description)

    # 檢查目錄
    directories = ["tests/performance/reports", "tests/performance/utils"]

    for directory in directories:
        if Path(directory).exists():
            print(f"✅ 目錄存在: {directory}")
        else:
            print(f"❌ 目錄不存在: {directory}")
            success = False

    return success


def verify_security_framework():
    """驗證安全測試框架"""
    print("\n🔒 驗證安全測試框架...")

    success = True

    # 檢查核心文件
    files_to_check = [
        ("tests/security/__init__.py", "安全測試初始化文件"),
        ("tests/security/conftest.py", "安全測試 pytest 配置"),
        ("tests/security/test_jwt_security.py", "JWT 安全測試"),
        ("tests/security/test_sql_injection.py", "SQL 注入測試"),
        ("tests/security/test_xss_protection.py", "XSS 防護測試"),
        ("tests/security/test_rbac_permissions.py", "權限控制測試"),
        ("tests/security/test_data_leakage.py", "資料洩漏測試"),
        ("tests/security/utils/__init__.py", "安全工具初始化"),
        ("tests/security/utils/security_scanner.py", "安全掃描器"),
        ("tests/security/utils/auth_tester.py", "認證測試器"),
        ("tests/security/utils/injection_tester.py", "注入測試器"),
        ("tests/security/utils/vulnerability_tester.py", "漏洞測試器"),
    ]

    for file_path, description in files_to_check:
        success &= check_file_exists(file_path, description)

    # 檢查目錄
    directories = ["tests/security/reports", "tests/security/utils"]

    for directory in directories:
        if Path(directory).exists():
            print(f"✅ 目錄存在: {directory}")
        else:
            print(f"❌ 目錄不存在: {directory}")
            success = False

    return success


def verify_test_scripts():
    """驗證測試運行腳本"""
    print("\n📜 驗證測試運行腳本...")

    success = True

    scripts_to_check = [
        ("scripts/run_performance_tests.py", "效能測試運行腳本"),
        ("scripts/run_security_tests.py", "安全測試運行腳本"),
        ("tests/README.md", "測試框架使用指南"),
    ]

    for script_path, description in scripts_to_check:
        success &= check_file_exists(script_path, description)

    return success


def verify_dependencies():
    """驗證依賴包"""
    print("\n📦 驗證測試依賴包...")

    # 核心依賴
    core_deps = [
        ("pytest", "pytest 測試框架"),
        ("fastapi", "FastAPI 框架"),
    ]

    # 效能測試依賴
    performance_deps = [
        ("psutil", "系統監控"),
        ("time", "時間測量"),
        ("threading", "多線程"),
        ("asyncio", "異步支援"),
    ]

    # 安全測試依賴
    security_deps = [
        ("jwt", "JWT 處理"),
        ("re", "正則表達式"),
        ("json", "JSON 處理"),
    ]

    success = True

    all_deps = core_deps + performance_deps + security_deps

    for dep_name, description in all_deps:
        success &= check_import(dep_name, description)

    return success


def verify_configuration():
    """驗證配置文件"""
    print("\n⚙️ 驗證配置...")

    success = True

    # 檢查 pyproject.toml 中的測試依賴
    pyproject_file = Path("../pyproject.toml")
    if pyproject_file.exists():
        content = pyproject_file.read_text(encoding="utf-8")

        required_deps = [
            "pytest-benchmark",
            "locust",
            "pytest-asyncio",
            "httpx",
            "bandit",
            "safety",
        ]

        for dep in required_deps:
            if dep in content:
                print(f"✅ pyproject.toml 包含依賴: {dep}")
            else:
                print(f"⚠️ pyproject.toml 缺少依賴: {dep}")
    else:
        print("❌ pyproject.toml 不存在")
        success = False

    return success


def main():
    """主函數"""
    print("🔍 開始驗證測試框架...")

    # 添加專案根目錄到 Python 路徑
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    # 執行各項驗證
    performance_ok = verify_performance_framework()
    security_ok = verify_security_framework()
    scripts_ok = verify_test_scripts()
    deps_ok = verify_dependencies()
    config_ok = verify_configuration()

    # 總結
    print("\n" + "=" * 60)
    print("📋 驗證結果總結:")
    print("=" * 60)

    results = [
        ("效能測試框架", performance_ok),
        ("安全測試框架", security_ok),
        ("測試運行腳本", scripts_ok),
        ("依賴包", deps_ok),
        ("配置文件", config_ok),
    ]

    all_passed = True
    for name, passed in results:
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{name}: {status}")
        all_passed &= passed

    print("=" * 60)

    if all_passed:
        print("🎉 所有驗證通過！測試框架已準備就緒。")
        print("\n📚 使用指南:")
        print("1. 運行效能測試: python scripts/run_performance_tests.py")
        print("2. 運行安全測試: python scripts/run_security_tests.py")
        print("3. 查看詳細說明: tests/README.md")
        return 0
    else:
        print("💥 部分驗證失敗，請檢查上述錯誤並修復。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
