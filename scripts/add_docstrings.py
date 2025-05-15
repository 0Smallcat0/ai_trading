#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
添加文檔字符串腳本

此腳本用於檢查專案中的函式和類別是否有文檔字符串，並為缺少文檔字符串的函式和類別添加模板。

使用方法：
    python scripts/add_docstrings.py [--path PATH] [--check-only]

參數：
    --path PATH: 要檢查的路徑，預設為 src
    --check-only: 僅檢查問題，不修改檔案
"""

import os
import sys
import ast
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional


class DocstringVisitor(ast.NodeVisitor):
    """
    文檔字符串訪問器

    用於訪問 AST 中的函式和類別節點，檢查是否有文檔字符串。
    """

    def __init__(self):
        self.missing_docstrings = {
            "functions": [],
            "classes": [],
            "methods": []
        }
        self.current_class = None

    def visit_FunctionDef(self, node):
        """
        訪問函式定義節點

        Args:
            node (ast.FunctionDef): 函式定義節點
        """
        # 檢查是否有文檔字符串
        has_docstring = (
            len(node.body) > 0
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        )

        if not has_docstring:
            if self.current_class:
                self.missing_docstrings["methods"].append({
                    "class_name": self.current_class,
                    "method_name": node.name,
                    "lineno": node.lineno,
                    "args": [arg.arg for arg in node.args.args if arg.arg != "self"],
                    "returns": self._get_return_type(node)
                })
            else:
                self.missing_docstrings["functions"].append({
                    "name": node.name,
                    "lineno": node.lineno,
                    "args": [arg.arg for arg in node.args.args],
                    "returns": self._get_return_type(node)
                })

        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """
        訪問類別定義節點

        Args:
            node (ast.ClassDef): 類別定義節點
        """
        # 檢查是否有文檔字符串
        has_docstring = (
            len(node.body) > 0
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        )

        if not has_docstring:
            self.missing_docstrings["classes"].append({
                "name": node.name,
                "lineno": node.lineno
            })

        # 記錄當前類別名稱，以便在訪問方法時使用
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def _get_return_type(self, node):
        """
        獲取函式的返回類型

        Args:
            node (ast.FunctionDef): 函式定義節點

        Returns:
            Optional[str]: 返回類型
        """
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return node.returns.id
            elif isinstance(node.returns, ast.Subscript):
                if isinstance(node.returns.value, ast.Name):
                    return f"{node.returns.value.id}[...]"
            elif isinstance(node.returns, ast.Attribute):
                if isinstance(node.returns.value, ast.Name):
                    return f"{node.returns.value.id}.{node.returns.attr}"
                else:
                    return "complex_type"
        return None


def generate_function_docstring(name, args, returns=None):
    """
    生成函式的文檔字符串

    Args:
        name (str): 函式名稱
        args (List[str]): 參數列表
        returns (Optional[str]): 返回類型

    Returns:
        str: 文檔字符串
    """
    docstring = f'"""\n{name}\n\n'

    if args:
        docstring += "Args:\n"
        for arg in args:
            docstring += f"    {arg}: \n"

    if returns:
        docstring += "\nReturns:\n"
        docstring += f"    {returns}: \n"

    docstring += '"""'
    return docstring


def generate_method_docstring(name, args, returns=None):
    """
    生成方法的文檔字符串

    Args:
        name (str): 方法名稱
        args (List[str]): 參數列表
        returns (Optional[str]): 返回類型

    Returns:
        str: 文檔字符串
    """
    docstring = f'"""\n{name}\n\n'

    if args:
        docstring += "Args:\n"
        for arg in args:
            docstring += f"    {arg}: \n"

    if returns:
        docstring += "\nReturns:\n"
        docstring += f"    {returns}: \n"

    docstring += '"""'
    return docstring


def generate_class_docstring(name):
    """
    生成類別的文檔字符串

    Args:
        name (str): 類別名稱

    Returns:
        str: 文檔字符串
    """
    return f'"""\n{name}\n\n"""'


def analyze_file(file_path: Path) -> Dict:
    """
    分析檔案

    Args:
        file_path (Path): 檔案路徑

    Returns:
        Dict: 分析結果
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"分析 {file_path} 時發生語法錯誤: {e}")
        return None

    visitor = DocstringVisitor()
    visitor.visit(tree)

    return {
        "file": file_path,
        "missing_docstrings": visitor.missing_docstrings
    }


def add_docstrings_to_file(file_path: Path, missing_docstrings: Dict) -> bool:
    """
    為檔案添加文檔字符串

    Args:
        file_path (Path): 檔案路徑
        missing_docstrings (Dict): 缺少文檔字符串的函式和類別

    Returns:
        bool: 是否成功添加文檔字符串
    """
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 按行號排序，從後往前添加，以避免行號變化
    all_items = []
    for item in missing_docstrings["functions"]:
        all_items.append({
            "type": "function",
            "lineno": item["lineno"],
            "data": item
        })
    for item in missing_docstrings["classes"]:
        all_items.append({
            "type": "class",
            "lineno": item["lineno"],
            "data": item
        })
    for item in missing_docstrings["methods"]:
        all_items.append({
            "type": "method",
            "lineno": item["lineno"],
            "data": item
        })

    all_items.sort(key=lambda x: x["lineno"], reverse=True)

    for item in all_items:
        lineno = item["lineno"]
        indent = len(lines[lineno - 1]) - len(lines[lineno - 1].lstrip())
        indent_str = " " * indent

        if item["type"] == "function":
            docstring = generate_function_docstring(
                item["data"]["name"],
                item["data"]["args"],
                item["data"]["returns"]
            )
        elif item["type"] == "class":
            docstring = generate_class_docstring(item["data"]["name"])
        elif item["type"] == "method":
            docstring = generate_method_docstring(
                item["data"]["method_name"],
                item["data"]["args"],
                item["data"]["returns"]
            )

        # 添加縮排
        docstring = "\n".join(indent_str + line for line in docstring.split("\n"))

        # 找到函式/類別定義的下一行
        next_line = lineno
        while next_line < len(lines) and (lines[next_line].strip() == "" or lines[next_line].strip().startswith("#")):
            next_line += 1

        # 插入文檔字符串
        lines.insert(next_line, docstring + "\n")

    # 寫回檔案
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return True


def main():
    """
    主函式
    """
    parser = argparse.ArgumentParser(description="添加文檔字符串腳本")
    parser.add_argument("--path", default="src", help="要檢查的路徑，預設為 src")
    parser.add_argument("--check-only", action="store_true", help="僅檢查問題，不修改檔案")

    args = parser.parse_args()

    # 檢查路徑是否存在
    path = Path(args.path)
    if not path.exists():
        print(f"錯誤: 路徑 {path} 不存在")
        return 1

    # 掃描 Python 檔案
    python_files = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".py"):
                python_files.append(Path(root) / file)

    if not python_files:
        print(f"在 {path} 中沒有找到 Python 檔案")
        return 0

    print(f"掃描 {len(python_files)} 個 Python 檔案...")

    # 分析檔案
    all_results = []
    for file in python_files:
        result = analyze_file(file)
        if result:
            has_missing = any(len(items) > 0 for items in result["missing_docstrings"].values())
            if has_missing:
                all_results.append(result)

    # 輸出結果
    if not all_results:
        print("所有函式和類別都有文檔字符串")
        return 0

    total_missing = sum(
        sum(len(items) for items in result["missing_docstrings"].values())
        for result in all_results
    )
    print(f"在 {len(all_results)} 個檔案中發現 {total_missing} 個缺少文檔字符串的函式和類別")

    for result in all_results:
        print(f"\n檔案: {result['file']}")

        if result["missing_docstrings"]["functions"]:
            print(f"  缺少文檔字符串的函式: {len(result['missing_docstrings']['functions'])}")
            for func in result["missing_docstrings"]["functions"][:5]:  # 只顯示前 5 個
                print(f"    - {func['name']} (行 {func['lineno']})")
            if len(result["missing_docstrings"]["functions"]) > 5:
                print(f"    ... 還有 {len(result['missing_docstrings']['functions']) - 5} 個")

        if result["missing_docstrings"]["classes"]:
            print(f"  缺少文檔字符串的類別: {len(result['missing_docstrings']['classes'])}")
            for cls in result["missing_docstrings"]["classes"][:5]:  # 只顯示前 5 個
                print(f"    - {cls['name']} (行 {cls['lineno']})")
            if len(result["missing_docstrings"]["classes"]) > 5:
                print(f"    ... 還有 {len(result['missing_docstrings']['classes']) - 5} 個")

        if result["missing_docstrings"]["methods"]:
            print(f"  缺少文檔字符串的方法: {len(result['missing_docstrings']['methods'])}")
            for method in result["missing_docstrings"]["methods"][:5]:  # 只顯示前 5 個
                print(f"    - {method['class_name']}.{method['method_name']} (行 {method['lineno']})")
            if len(result["missing_docstrings"]["methods"]) > 5:
                print(f"    ... 還有 {len(result['missing_docstrings']['methods']) - 5} 個")

    # 如果不是僅檢查，則添加文檔字符串
    if not args.check_only:
        print("\n開始添加文檔字符串...")
        for result in all_results:
            try:
                if add_docstrings_to_file(result["file"], result["missing_docstrings"]):
                    print(f"已為 {result['file']} 添加文檔字符串")
            except Exception as e:
                print(f"為 {result['file']} 添加文檔字符串時發生錯誤: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
