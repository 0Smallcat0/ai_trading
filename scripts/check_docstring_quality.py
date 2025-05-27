#!/usr/bin/env python3
"""Google Style Docstring 品質檢查腳本.

此腳本用於檢查專案中的文檔字符串是否符合 Google Style 規範，
並提供修正建議。
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class DocstringChecker:
    """Google Style Docstring 檢查器."""

    def __init__(self):
        """初始化檢查器."""
        self.issues: List[Dict] = []
        self.stats = {
            "total_functions": 0,
            "documented_functions": 0,
            "total_classes": 0,
            "documented_classes": 0,
            "total_modules": 0,
            "documented_modules": 0,
        }

    def check_file(self, file_path: Path) -> List[Dict]:
        """檢查單個檔案的文檔字符串品質.

        Args:
            file_path: 要檢查的檔案路徑。

        Returns:
            發現的問題列表。
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            file_issues = []

            # 檢查模組文檔字符串
            module_docstring = ast.get_docstring(tree)
            self.stats["total_modules"] += 1
            if module_docstring:
                self.stats["documented_modules"] += 1
                issues = self._check_docstring_quality(
                    module_docstring, "module", str(file_path), 1
                )
                file_issues.extend(issues)
            else:
                file_issues.append(
                    {
                        "file": str(file_path),
                        "line": 1,
                        "type": "missing_docstring",
                        "target": "module",
                        "message": "模組缺少文檔字符串",
                    }
                )

            # 遍歷 AST 節點
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    self._check_function(node, file_path, file_issues)
                elif isinstance(node, ast.ClassDef):
                    self._check_class(node, file_path, file_issues)

            return file_issues

        except Exception as e:
            return [
                {
                    "file": str(file_path),
                    "line": 0,
                    "type": "parse_error",
                    "target": "file",
                    "message": f"解析檔案時發生錯誤: {e}",
                }
            ]

    def _check_function(
        self, node: ast.FunctionDef, file_path: Path, issues: List[Dict]
    ) -> None:
        """檢查函數的文檔字符串.

        Args:
            node: 函數 AST 節點。
            file_path: 檔案路徑。
            issues: 問題列表。
        """
        self.stats["total_functions"] += 1
        docstring = ast.get_docstring(node)

        if docstring:
            self.stats["documented_functions"] += 1
            doc_issues = self._check_docstring_quality(
                docstring, "function", str(file_path), node.lineno
            )
            issues.extend(doc_issues)

            # 檢查參數文檔
            self._check_function_args(node, docstring, file_path, issues)
        else:
            # 跳過私有函數和特殊方法（除了 __init__）
            if not node.name.startswith("_") or node.name == "__init__":
                issues.append(
                    {
                        "file": str(file_path),
                        "line": node.lineno,
                        "type": "missing_docstring",
                        "target": f"function:{node.name}",
                        "message": f"函數 {node.name} 缺少文檔字符串",
                    }
                )

    def _check_class(
        self, node: ast.ClassDef, file_path: Path, issues: List[Dict]
    ) -> None:
        """檢查類的文檔字符串.

        Args:
            node: 類 AST 節點。
            file_path: 檔案路徑。
            issues: 問題列表。
        """
        self.stats["total_classes"] += 1
        docstring = ast.get_docstring(node)

        if docstring:
            self.stats["documented_classes"] += 1
            doc_issues = self._check_docstring_quality(
                docstring, "class", str(file_path), node.lineno
            )
            issues.extend(doc_issues)
        else:
            # 跳過私有類
            if not node.name.startswith("_"):
                issues.append(
                    {
                        "file": str(file_path),
                        "line": node.lineno,
                        "type": "missing_docstring",
                        "target": f"class:{node.name}",
                        "message": f"類 {node.name} 缺少文檔字符串",
                    }
                )

    def _check_function_args(
        self, node: ast.FunctionDef, docstring: str, file_path: Path, issues: List[Dict]
    ) -> None:
        """檢查函數參數是否在文檔中有說明.

        Args:
            node: 函數 AST 節點。
            docstring: 文檔字符串。
            file_path: 檔案路徑。
            issues: 問題列表。
        """
        # 獲取函數參數
        args = [arg.arg for arg in node.args.args]

        # 移除 self 和 cls
        if args and args[0] in ("self", "cls"):
            args = args[1:]

        # 檢查 Args 部分
        if args and "Args:" not in docstring:
            issues.append(
                {
                    "file": str(file_path),
                    "line": node.lineno,
                    "type": "missing_args_section",
                    "target": f"function:{node.name}",
                    "message": f"函數 {node.name} 有參數但缺少 Args 部分",
                }
            )
        elif args:
            # 檢查每個參數是否有文檔
            for arg in args:
                if f"{arg}:" not in docstring:
                    issues.append(
                        {
                            "file": str(file_path),
                            "line": node.lineno,
                            "type": "missing_arg_doc",
                            "target": f"function:{node.name}",
                            "message": f"參數 {arg} 缺少文檔說明",
                        }
                    )

    def _check_docstring_quality(
        self, docstring: str, target_type: str, file_path: str, line_no: int
    ) -> List[Dict]:
        """檢查文檔字符串的品質.

        Args:
            docstring: 文檔字符串內容。
            target_type: 目標類型（module/class/function）。
            file_path: 檔案路徑。
            line_no: 行號。

        Returns:
            發現的問題列表。
        """
        issues = []
        lines = docstring.strip().split("\n")

        # 檢查第一行是否為簡短描述
        if not lines[0].strip():
            issues.append(
                {
                    "file": file_path,
                    "line": line_no,
                    "type": "empty_first_line",
                    "target": target_type,
                    "message": "文檔字符串第一行不應為空",
                }
            )
        elif len(lines[0]) > 79:
            issues.append(
                {
                    "file": file_path,
                    "line": line_no,
                    "type": "first_line_too_long",
                    "target": target_type,
                    "message": "文檔字符串第一行過長（超過 79 字符）",
                }
            )

        # 檢查是否有詳細描述（對於複雜函數）
        if len(lines) == 1 and len(lines[0]) < 20:
            issues.append(
                {
                    "file": file_path,
                    "line": line_no,
                    "type": "too_brief",
                    "target": target_type,
                    "message": "文檔字符串過於簡短，建議添加詳細描述",
                }
            )

        # 檢查 Google Style 格式
        content = "\n".join(lines)
        self._check_google_style_sections(
            content, file_path, line_no, target_type, issues
        )

        return issues

    def _check_google_style_sections(
        self,
        content: str,
        file_path: str,
        line_no: int,
        target_type: str,
        issues: List[Dict],
    ) -> None:
        """檢查 Google Style 的各個部分.

        Args:
            content: 文檔字符串內容。
            file_path: 檔案路徑。
            line_no: 行號。
            target_type: 目標類型。
            issues: 問題列表。
        """
        # 檢查常見的格式問題
        if "Args:" in content:
            # 檢查 Args 後是否有正確的縮進
            lines = content.split("\n")
            args_index = -1
            for i, line in enumerate(lines):
                if line.strip() == "Args:":
                    args_index = i
                    break

            if args_index >= 0 and args_index + 1 < len(lines):
                next_line = lines[args_index + 1]
                if next_line and not next_line.startswith("        "):
                    issues.append(
                        {
                            "file": file_path,
                            "line": line_no,
                            "type": "incorrect_indentation",
                            "target": target_type,
                            "message": "Args 部分的參數描述縮進不正確",
                        }
                    )

        # 檢查其他部分的格式
        sections = ["Returns:", "Yields:", "Raises:", "Example:", "Note:"]
        for section in sections:
            if section in content:
                # 這裡可以添加更詳細的格式檢查
                pass

    def check_directory(self, directory: Path) -> List[Dict]:
        """檢查目錄中所有 Python 檔案.

        Args:
            directory: 要檢查的目錄。

        Returns:
            所有發現的問題列表。
        """
        all_issues = []

        for py_file in directory.rglob("*.py"):
            # 跳過某些目錄
            if any(
                part in str(py_file)
                for part in ["__pycache__", ".git", "venv", "env", ".pytest_cache"]
            ):
                continue

            file_issues = self.check_file(py_file)
            all_issues.extend(file_issues)

        return all_issues

    def generate_report(self, issues: List[Dict]) -> str:
        """生成檢查報告.

        Args:
            issues: 問題列表。

        Returns:
            格式化的報告字符串。
        """
        report = []
        report.append("=" * 80)
        report.append("Google Style Docstring 品質檢查報告")
        report.append("=" * 80)

        # 統計信息
        report.append("\n📊 統計信息:")
        report.append(f"  模組總數: {self.stats['total_modules']}")
        report.append(f"  已文檔化模組: {self.stats['documented_modules']}")
        report.append(f"  類總數: {self.stats['total_classes']}")
        report.append(f"  已文檔化類: {self.stats['documented_classes']}")
        report.append(f"  函數總數: {self.stats['total_functions']}")
        report.append(f"  已文檔化函數: {self.stats['documented_functions']}")

        # 計算覆蓋率
        if self.stats["total_functions"] > 0:
            func_coverage = (
                self.stats["documented_functions"] / self.stats["total_functions"] * 100
            )
            report.append(f"  函數文檔覆蓋率: {func_coverage:.1f}%")

        if self.stats["total_classes"] > 0:
            class_coverage = (
                self.stats["documented_classes"] / self.stats["total_classes"] * 100
            )
            report.append(f"  類文檔覆蓋率: {class_coverage:.1f}%")

        # 問題統計
        report.append(f"\n🔍 發現問題總數: {len(issues)}")

        if issues:
            # 按類型分組
            issue_types = {}
            for issue in issues:
                issue_type = issue["type"]
                if issue_type not in issue_types:
                    issue_types[issue_type] = 0
                issue_types[issue_type] += 1

            report.append("\n📋 問題類型統計:")
            for issue_type, count in sorted(issue_types.items()):
                report.append(f"  {issue_type}: {count}")

            # 詳細問題列表
            report.append("\n🔧 詳細問題列表:")
            current_file = None
            for issue in sorted(issues, key=lambda x: (x["file"], x["line"])):
                if issue["file"] != current_file:
                    current_file = issue["file"]
                    report.append(f"\n📁 {current_file}:")

                report.append(f"  行 {issue['line']:4d}: {issue['message']}")
        else:
            report.append("\n✅ 未發現問題！")

        report.append("\n" + "=" * 80)
        return "\n".join(report)


def main():
    """主函數."""
    print("🚀 開始檢查 Google Style Docstring 品質")

    checker = DocstringChecker()

    # 檢查 src 目錄
    src_dir = project_root / "src"
    if src_dir.exists():
        print(f"📂 檢查目錄: {src_dir}")
        issues = checker.check_directory(src_dir)
    else:
        print("❌ src 目錄不存在")
        return 1

    # 生成報告
    report = checker.generate_report(issues)
    print(report)

    # 保存報告到檔案
    report_file = project_root / "docstring_quality_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n📄 報告已保存到: {report_file}")

    # 返回適當的退出碼
    if issues:
        print(f"\n⚠️ 發現 {len(issues)} 個問題需要修正")
        return 1
    else:
        print("\n✅ 所有文檔字符串都符合 Google Style 規範！")
        return 0


if __name__ == "__main__":
    sys.exit(main())
