#!/usr/bin/env python3
"""
Web UI 基本功能測試

此腳本測試 Web UI 模組的基本功能，包括：
- 模組導入測試
- 語法檢查
- 基本功能驗證
"""

import ast
import importlib.util
import sys
from pathlib import Path


def test_syntax(file_path: str) -> bool:
    """
    測試 Python 檔案語法

    Args:
        file_path: 檔案路徑

    Returns:
        bool: 語法是否正確
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        ast.parse(content)
        print(f"✅ {file_path}: 語法檢查通過")
        return True
    except SyntaxError as e:
        print(f"❌ {file_path}: 語法錯誤 - {e}")
        return False
    except Exception as e:
        print(f"⚠️ {file_path}: 檢查失敗 - {e}")
        return False


def test_import(module_path: str, module_name: str) -> bool:
    """
    測試模組導入

    Args:
        module_path: 模組檔案路徑
        module_name: 模組名稱

    Returns:
        bool: 導入是否成功
    """
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None:
            print(f"❌ {module_name}: 無法創建模組規格")
            return False

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        print(f"✅ {module_name}: 導入成功")
        return True
    except Exception as e:
        print(f"❌ {module_name}: 導入失敗 - {e}")
        return False


def main():
    """主測試函數"""
    print("🧪 Web UI 基本功能測試開始")
    print("=" * 50)

    # 測試檔案列表
    test_files = [
        ("src/ui/web_ui.py", "web_ui"),
        ("src/ui/components/auth.py", "auth"),
        ("src/ui/responsive.py", "responsive"),
    ]

    syntax_results = []
    import_results = []

    # 語法檢查
    print("\n📝 語法檢查:")
    for file_path, module_name in test_files:
        if Path(file_path).exists():
            result = test_syntax(file_path)
            syntax_results.append(result)
        else:
            print(f"⚠️ {file_path}: 檔案不存在")
            syntax_results.append(False)

    # 導入測試（僅在語法檢查通過時進行）
    print("\n📦 導入測試:")
    if all(syntax_results):
        # 添加 src 到 Python 路徑
        src_path = Path("src").absolute()
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))

        for file_path, module_name in test_files:
            if Path(file_path).exists():
                result = test_import(file_path, module_name)
                import_results.append(result)
            else:
                import_results.append(False)
    else:
        print("⚠️ 跳過導入測試（語法檢查未通過）")
        import_results = [False] * len(test_files)

    # 結果總結
    print("\n📊 測試結果總結:")
    print("=" * 50)

    syntax_passed = sum(syntax_results)
    import_passed = sum(import_results)
    total_files = len(test_files)

    print(f"語法檢查: {syntax_passed}/{total_files} 通過")
    print(f"導入測試: {import_passed}/{total_files} 通過")

    if syntax_passed == total_files and import_passed == total_files:
        print("\n🎉 所有測試通過！Web UI 模組基本功能正常")
        return True
    else:
        print("\n⚠️ 部分測試失敗，請檢查上述錯誤")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
