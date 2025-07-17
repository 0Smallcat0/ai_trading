#!/usr/bin/env python3
"""
本地品質檢查腳本

此腳本在本地執行完整的程式碼品質檢查，包括：
- 程式碼格式化檢查
- 靜態分析
- 型別檢查
- 安全掃描
- 測試覆蓋率
- 檔案大小檢查

Example:
    >>> python scripts/run_quality_checks.py
    >>> python scripts/run_quality_checks.py --fix
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


class QualityChecker:
    """品質檢查器.
    
    執行各種程式碼品質檢查並生成報告。
    """

    def __init__(self, fix_issues: bool = False):
        """初始化品質檢查器.
        
        Args:
            fix_issues: 是否自動修復可修復的問題
        """
        self.fix_issues = fix_issues
        self.project_root = Path(__file__).parent.parent
        self.src_dir = self.project_root / "src"
        self.tests_dir = self.project_root / "tests"

    def run_all_checks(self) -> bool:
        """執行所有品質檢查.
        
        Returns:
            bool: 是否所有檢查都通過
        """
        print("🚀 開始執行程式碼品質檢查...")
        print("=" * 60)

        checks = [
            ("檔案大小檢查", self.check_file_sizes),
            ("程式碼格式化檢查", self.check_formatting),
            ("導入排序檢查", self.check_imports),
            ("程式碼風格檢查", self.check_style),
            ("靜態分析", self.check_pylint),
            ("型別檢查", self.check_types),
            ("安全掃描", self.check_security),
            ("依賴漏洞檢查", self.check_dependencies),
            ("測試覆蓋率", self.check_coverage),
        ]

        results = []
        for name, check_func in checks:
            print(f"\n📋 {name}...")
            try:
                success = check_func()
                results.append((name, success))
                if success:
                    print(f"✅ {name} 通過")
                else:
                    print(f"❌ {name} 失敗")
            except Exception as e:
                print(f"💥 {name} 執行錯誤: {e}")
                results.append((name, False))

        # 顯示總結
        print("\n" + "=" * 60)
        print("📊 品質檢查總結:")
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for name, success in results:
            status = "✅" if success else "❌"
            print(f"  {status} {name}")
        
        print(f"\n通過率: {passed}/{total} ({passed/total*100:.1f}%)")
        
        if passed == total:
            print("🎉 所有品質檢查都通過！")
            return True
        else:
            print("⚠️ 部分品質檢查未通過，請修復問題後重新檢查")
            return False

    def check_file_sizes(self) -> bool:
        """檢查檔案大小."""
        max_lines = 300
        violations = []
        
        for py_file in self.src_dir.rglob("*.py"):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    line_count = len(f.readlines())
                
                if line_count > max_lines:
                    violations.append((py_file, line_count))
            except Exception as e:
                print(f"⚠️ 無法讀取檔案 {py_file}: {e}")
        
        if violations:
            print("發現超過 300 行的檔案:")
            for filepath, line_count in violations:
                print(f"  {filepath.relative_to(self.project_root)}: {line_count} 行")
            return False
        
        return True

    def check_formatting(self) -> bool:
        """檢查程式碼格式化."""
        cmd = ["black", "--check", "--diff", str(self.src_dir)]
        if self.tests_dir.exists():
            cmd.append(str(self.tests_dir))
        
        if self.fix_issues:
            cmd = ["black", str(self.src_dir)]
            if self.tests_dir.exists():
                cmd.append(str(self.tests_dir))
        
        return self._run_command(cmd, "Black 格式化")

    def check_imports(self) -> bool:
        """檢查導入排序."""
        cmd = ["isort", "--check-only", "--diff", str(self.src_dir)]
        if self.tests_dir.exists():
            cmd.append(str(self.tests_dir))
        
        if self.fix_issues:
            cmd = ["isort", str(self.src_dir)]
            if self.tests_dir.exists():
                cmd.append(str(self.tests_dir))
        
        return self._run_command(cmd, "isort 導入排序")

    def check_style(self) -> bool:
        """檢查程式碼風格."""
        cmd = [
            "flake8", 
            str(self.src_dir),
            "--max-line-length=88",
            "--extend-ignore=E203,W503"
        ]
        if self.tests_dir.exists():
            cmd.append(str(self.tests_dir))
        
        return self._run_command(cmd, "Flake8 風格檢查")

    def check_pylint(self) -> bool:
        """執行 Pylint 靜態分析."""
        # 檢查核心模組（要求更高標準）
        core_modules = ["src/risk_management/"]
        for module in core_modules:
            module_path = self.project_root / module
            if module_path.exists():
                cmd = [
                    "pylint", 
                    str(module_path),
                    "--fail-under=9.0",
                    "--output-format=text"
                ]
                if not self._run_command(cmd, f"Pylint 核心模組 {module}"):
                    return False
        
        # 檢查一般模組
        general_modules = ["src/api/", "src/ui/", "src/core/"]
        for module in general_modules:
            module_path = self.project_root / module
            if module_path.exists():
                cmd = [
                    "pylint", 
                    str(module_path),
                    "--fail-under=8.5",
                    "--output-format=text"
                ]
                if not self._run_command(cmd, f"Pylint 一般模組 {module}"):
                    return False
        
        return True

    def check_types(self) -> bool:
        """檢查型別註解."""
        cmd = [
            "mypy", 
            str(self.src_dir),
            "--ignore-missing-imports",
            "--show-error-codes"
        ]
        return self._run_command(cmd, "MyPy 型別檢查")

    def check_security(self) -> bool:
        """執行安全掃描."""
        cmd = [
            "bandit", 
            "-r", str(self.src_dir),
            "-f", "txt"
        ]
        return self._run_command(cmd, "Bandit 安全掃描")

    def check_dependencies(self) -> bool:
        """檢查依賴漏洞."""
        cmd = ["safety", "check"]
        return self._run_command(cmd, "Safety 依賴檢查")

    def check_coverage(self) -> bool:
        """檢查測試覆蓋率."""
        if not self.tests_dir.exists():
            print("⚠️ 沒有找到測試目錄，跳過覆蓋率檢查")
            return True
        
        cmd = [
            "pytest", 
            str(self.tests_dir),
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-fail-under=80",
            "--quiet"
        ]
        return self._run_command(cmd, "測試覆蓋率檢查")

    def _run_command(self, cmd: List[str], description: str) -> bool:
        """執行命令並返回結果.
        
        Args:
            cmd: 要執行的命令
            description: 命令描述
            
        Returns:
            bool: 命令是否成功執行
        """
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300,
                cwd=self.project_root
            )
            
            if result.returncode == 0:
                return True
            else:
                print(f"❌ {description} 失敗:")
                if result.stdout:
                    print("標準輸出:")
                    print(result.stdout)
                if result.stderr:
                    print("錯誤輸出:")
                    print(result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {description} 執行超時")
            return False
        except FileNotFoundError:
            print(f"⚠️ {description} 工具未安裝: {cmd[0]}")
            return False
        except Exception as e:
            print(f"💥 {description} 執行錯誤: {e}")
            return False

    def install_tools(self) -> bool:
        """安裝品質檢查工具."""
        print("📦 安裝品質檢查工具...")
        
        tools = [
            "black", "isort", "flake8", "pylint", 
            "mypy", "bandit", "safety", "pytest", "pytest-cov"
        ]
        
        cmd = ["pip", "install"] + tools
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✅ 品質檢查工具安裝完成")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ 工具安裝失敗: {e}")
            print(e.stdout)
            print(e.stderr)
            return False


def main():
    """主函數."""
    parser = argparse.ArgumentParser(description="執行程式碼品質檢查")
    parser.add_argument(
        "--fix", 
        action="store_true", 
        help="自動修復可修復的問題"
    )
    parser.add_argument(
        "--install-tools", 
        action="store_true", 
        help="安裝品質檢查工具"
    )
    
    args = parser.parse_args()
    
    checker = QualityChecker(fix_issues=args.fix)
    
    if args.install_tools:
        if not checker.install_tools():
            return 1
    
    success = checker.run_all_checks()
    
    if success:
        print("\n🎉 所有品質檢查通過！")
        return 0
    else:
        print("\n❌ 品質檢查未通過，請修復問題")
        if not args.fix:
            print("💡 提示: 使用 --fix 參數自動修復部分問題")
        return 1


if __name__ == "__main__":
    sys.exit(main())
