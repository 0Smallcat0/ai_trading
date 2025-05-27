#!/usr/bin/env python3
"""
Phase 5.2 實作驗證測試

簡化的測試腳本，用於驗證 API 版本控制與測試框架的核心功能。
"""

import sys
import traceback
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_version_control_models():
    """測試版本控制模型"""
    print("🔄 測試版本控制模型...")

    try:
        from src.api.models.versioning import (
            SemanticVersion,
            APIVersion,
            VersionStatusEnum,
            VersionCreateRequest,
            VersionListRequest,
        )

        # 測試語義化版本
        version = SemanticVersion.parse("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3
        print("  ✅ SemanticVersion 解析正常")

        # 測試版本比較
        v1 = SemanticVersion.parse("1.0.0")
        v2 = SemanticVersion.parse("1.1.0")
        assert v1 < v2
        print("  ✅ 版本比較功能正常")

        # 測試版本創建請求
        create_request = VersionCreateRequest(
            version="1.0.0", title="測試版本", status=VersionStatusEnum.DEVELOPMENT
        )
        assert create_request.version == "1.0.0"
        print("  ✅ 版本創建請求模型正常")

        # 測試版本列表請求
        list_request = VersionListRequest(
            page=1, page_size=20, sort_by="version", sort_order="desc"
        )
        assert list_request.page == 1
        print("  ✅ 版本列表請求模型正常")

        return True

    except Exception as e:
        print(f"  ❌ 版本控制模型測試失敗: {e}")
        traceback.print_exc()
        return False


def test_version_middleware():
    """測試版本控制中間件"""
    print("🔄 測試版本控制中間件...")

    try:
        from src.api.middleware.versioning import VersioningMiddleware

        # 初始化中間件
        middleware = VersioningMiddleware(None)

        # 測試支援版本列表
        supported_versions = middleware.get_supported_versions()
        assert isinstance(supported_versions, list)
        print(f"  ✅ 支援版本列表: {supported_versions}")

        # 測試添加版本
        success = middleware.add_supported_version("2.0.0")
        assert isinstance(success, bool)
        print("  ✅ 添加版本功能正常")

        return True

    except Exception as e:
        print(f"  ❌ 版本控制中間件測試失敗: {e}")
        traceback.print_exc()
        return False


def test_version_service():
    """測試版本管理服務"""
    print("🔄 測試版本管理服務...")

    try:
        from src.services.version_service import VersionService

        # 初始化服務
        service = VersionService()
        print("  ✅ 版本管理服務初始化成功")

        return True

    except Exception as e:
        print(f"  ❌ 版本管理服務測試失敗: {e}")
        traceback.print_exc()
        return False


def test_migration_manager():
    """測試遷移管理器"""
    print("🔄 測試遷移管理器...")

    try:
        from src.tools.migration.migration_manager import MigrationManager

        # 初始化遷移管理器
        manager = MigrationManager()
        print("  ✅ 遷移管理器初始化成功")

        return True

    except Exception as e:
        print(f"  ❌ 遷移管理器測試失敗: {e}")
        traceback.print_exc()
        return False


def test_performance_tools():
    """測試效能測試工具"""
    print("🔄 測試效能測試工具...")

    try:
        from tests.performance.utils.automated_test_runner import (
            AutomatedTestRunner,
            TestType,
            TestStatus,
        )

        # 初始化測試執行器
        runner = AutomatedTestRunner()
        print("  ✅ 自動化測試執行器初始化成功")

        # 測試枚舉
        assert TestType.PERFORMANCE == "performance"
        assert TestStatus.PASSED == "passed"
        print("  ✅ 測試類型和狀態枚舉正常")

        return True

    except Exception as e:
        print(f"  ❌ 效能測試工具測試失敗: {e}")
        traceback.print_exc()
        return False


def test_security_tools():
    """測試安全測試工具"""
    print("🔄 測試安全測試工具...")

    try:
        from tests.security.utils.vulnerability_scanner import (
            VulnerabilityScanner,
            VulnerabilityLevel,
        )

        # 初始化漏洞掃描器
        scanner = VulnerabilityScanner()
        print("  ✅ 漏洞掃描器初始化成功")

        # 測試漏洞級別枚舉
        assert VulnerabilityLevel.CRITICAL == "critical"
        assert VulnerabilityLevel.HIGH == "high"
        print("  ✅ 漏洞級別枚舉正常")

        return True

    except Exception as e:
        print(f"  ❌ 安全測試工具測試失敗: {e}")
        traceback.print_exc()
        return False


def test_file_structure():
    """測試檔案結構"""
    print("🔄 測試檔案結構...")

    required_files = [
        "src/api/middleware/versioning.py",
        "src/services/version_service.py",
        "src/tools/migration/migration_manager.py",
        "src/api/models/versioning.py",
        "tests/api/test_versioning_api.py",
        "tests/performance/test_versioning_performance.py",
        "tests/performance/utils/automated_test_runner.py",
        "tests/security/test_versioning_security.py",
        "tests/security/utils/vulnerability_scanner.py",
        "docs/開發者指南/API版本控制使用指南.md",
    ]

    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)

    if missing_files:
        print(f"  ❌ 缺少檔案: {missing_files}")
        return False
    else:
        print(f"  ✅ 所有必要檔案都存在 ({len(required_files)} 個)")
        return True


def main():
    """主測試函數"""
    print("=" * 60)
    print("  Phase 5.2 API 版本控制與測試框架實作驗證")
    print("=" * 60)

    tests = [
        ("檔案結構", test_file_structure),
        ("版本控制模型", test_version_control_models),
        ("版本控制中間件", test_version_middleware),
        ("版本管理服務", test_version_service),
        ("遷移管理器", test_migration_manager),
        ("效能測試工具", test_performance_tools),
        ("安全測試工具", test_security_tools),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        try:
            result = test_func()
            results.append(result)
            if result:
                print(f"✅ {test_name} - 通過")
            else:
                print(f"❌ {test_name} - 失敗")
        except Exception as e:
            print(f"❌ {test_name} - 異常: {e}")
            results.append(False)

    # 總結
    print("\n" + "=" * 60)
    print("  測試總結")
    print("=" * 60)

    passed = sum(results)
    total = len(results)
    success_rate = (passed / total) * 100

    print(f"總測試項目: {total}")
    print(f"通過項目: {passed}")
    print(f"失敗項目: {total - passed}")
    print(f"成功率: {success_rate:.1f}%")

    if success_rate == 100:
        print("\n🎉 所有測試都通過了！Phase 5.2 實作完成。")
        return 0
    elif success_rate >= 70:
        print(f"\n⚠️  大部分測試通過，但仍有 {total - passed} 個項目需要修復。")
        return 1
    else:
        print(f"\n❌ 測試失敗，有 {total - passed} 個項目未通過。")
        return 2


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
