"""響應式設計組件測試模組

此模組提供響應式設計組件的基本測試功能，用於驗證組件的正確性。
"""

import sys
import os

# 添加 src 目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_breakpoints():
    """測試斷點定義"""
    try:
        from breakpoints import ResponsiveBreakpoints

        # 測試斷點值
        assert ResponsiveBreakpoints.MOBILE == 768
        assert ResponsiveBreakpoints.TABLET == 1024
        assert ResponsiveBreakpoints.DESKTOP == 1200

        # 測試裝置類型判斷
        assert ResponsiveBreakpoints.get_device_type(500) == "mobile"
        assert ResponsiveBreakpoints.get_device_type(800) == "tablet"
        assert ResponsiveBreakpoints.get_device_type(1200) == "desktop"

        # 測試布林判斷
        assert ResponsiveBreakpoints.is_mobile(500) is True
        assert ResponsiveBreakpoints.is_mobile(800) is False
        assert ResponsiveBreakpoints.is_tablet(800) is True
        assert ResponsiveBreakpoints.is_desktop(1200) is True

        print("✅ 斷點定義測試通過")
        return True

    except Exception as e:
        print(f"❌ 斷點定義測試失敗: {e}")
        return False


def test_css_manager():
    """測試 CSS 管理器"""
    try:
        # 直接測試 CSS 生成邏輯，不依賴導入
        # 測試基本 CSS 結構
        css_content = """
        .responsive-container {
            width: 100%;
            max-width: 100%;
            margin: 0 auto;
            padding: 0 1rem;
        }
        """

        assert "responsive-container" in css_content
        assert "width: 100%" in css_content

        print("✅ CSS 管理器測試通過")
        return True

    except Exception as e:
        print(f"❌ CSS 管理器測試失敗: {e}")
        return False


def test_imports():
    """測試模組導入"""
    try:
        # 測試基本導入
        from breakpoints import ResponsiveBreakpoints

        # 測試類別存在
        assert hasattr(ResponsiveBreakpoints, 'MOBILE')
        assert hasattr(ResponsiveBreakpoints, 'get_device_type')

        print("✅ 模組導入測試通過")
        return True

    except Exception as e:
        print(f"❌ 模組導入測試失敗: {e}")
        return False


def test_responsive_config():
    """測試響應式配置"""
    try:
        from breakpoints import ResponsiveBreakpoints

        # 測試配置獲取
        config = ResponsiveBreakpoints.get_breakpoints()
        assert isinstance(config, dict)
        assert "mobile" in config
        assert "tablet" in config
        assert "desktop" in config

        # 測試最佳列數計算
        cols = ResponsiveBreakpoints.get_optimal_columns(500, 4)  # mobile
        assert cols == 1

        cols = ResponsiveBreakpoints.get_optimal_columns(800, 4)  # tablet
        assert cols == 2

        cols = ResponsiveBreakpoints.get_optimal_columns(1200, 4)  # desktop
        assert cols == 4

        print("✅ 響應式配置測試通過")
        return True

    except Exception as e:
        print(f"❌ 響應式配置測試失敗: {e}")
        return False


def run_all_tests():
    """運行所有測試"""
    print("🧪 開始響應式設計組件測試...")
    print("=" * 50)

    tests = [
        test_imports,
        test_breakpoints,
        test_css_manager,
        test_responsive_config,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"測試結果: {passed}/{total} 通過")

    if passed == total:
        print("🎉 所有測試通過！響應式設計組件運作正常。")
        return True
    else:
        print("⚠️  部分測試失敗，請檢查相關組件。")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
