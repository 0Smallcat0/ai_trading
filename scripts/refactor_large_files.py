#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
大型檔案重構腳本

此腳本用於重構專案中的大型 Python 檔案，將其拆分為較小的模組。
腳本會識別超過指定行數的檔案，並根據類別和函式的結構將其拆分為多個檔案。

使用方法：
    python scripts/refactor_large_files.py [--path PATH] [--threshold THRESHOLD] [--dry-run]

參數：
    --path PATH: 要掃描的路徑，預設為 src
    --threshold THRESHOLD: 檔案行數閾值，超過此值的檔案將被重構，預設為 300
    --dry-run: 僅顯示將要重構的檔案，不實際執行重構
"""

import os
import sys
import ast
import argparse
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional


class ClassVisitor(ast.NodeVisitor):
    """
    類別訪問器

    用於訪問 AST 中的類別節點。
    """

    def __init__(self):
        self.classes = []

    def visit_ClassDef(self, node):
        """
        訪問類別定義節點

        Args:
            node (ast.ClassDef): 類別定義節點
        """
        self.classes.append(node)
        self.generic_visit(node)


class FunctionVisitor(ast.NodeVisitor):
    """
    函式訪問器

    用於訪問 AST 中的函式節點。
    """

    def __init__(self):
        self.functions = []

    def visit_FunctionDef(self, node):
        """
        訪問函式定義節點

        Args:
            node (ast.FunctionDef): 函式定義節點
        """
        self.functions.append(node)
        self.generic_visit(node)


def count_lines(file_path: Path) -> int:
    """
    計算檔案行數

    Args:
        file_path (Path): 檔案路徑

    Returns:
        int: 檔案行數
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return len(f.readlines())


def find_large_files(path: Path, threshold: int) -> List[Path]:
    """
    尋找大型檔案

    Args:
        path (Path): 路徑
        threshold (int): 行數閾值

    Returns:
        List[Path]: 大型檔案列表
    """
    large_files = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                lines = count_lines(file_path)
                if lines > threshold:
                    large_files.append(file_path)
    return large_files


def analyze_file(file_path: Path) -> Tuple[List[ast.ClassDef], List[ast.FunctionDef]]:
    """
    分析檔案

    Args:
        file_path (Path): 檔案路徑

    Returns:
        Tuple[List[ast.ClassDef], List[ast.FunctionDef]]: 類別和函式列表
    """
    with open(file_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())

    class_visitor = ClassVisitor()
    class_visitor.visit(tree)

    function_visitor = FunctionVisitor()
    function_visitor.visit(tree)

    return class_visitor.classes, function_visitor.functions


def suggest_refactoring(file_path: Path, classes: List[ast.ClassDef], functions: List[ast.FunctionDef]) -> Dict:
    """
    建議重構方案

    Args:
        file_path (Path): 檔案路徑
        classes (List[ast.ClassDef]): 類別列表
        functions (List[ast.FunctionDef]): 函式列表

    Returns:
        Dict: 重構方案
    """
    module_name = file_path.stem
    parent_dir = file_path.parent
    new_dir = parent_dir / module_name

    refactoring = {
        "original_file": file_path,
        "new_directory": new_dir,
        "modules": []
    }

    # 為每個類別建立一個模組
    for cls in classes:
        refactoring["modules"].append({
            "name": f"{cls.name.lower()}.py",
            "content_type": "class",
            "content_name": cls.name
        })

    # 將函式分組
    function_groups = {}
    for func in functions:
        # 跳過類別方法
        if any(func.lineno >= cls.lineno and func.end_lineno <= cls.end_lineno for cls in classes):
            continue

        # 根據函式名稱前綴分組
        prefix = func.name.split("_")[0] if "_" in func.name else "utils"
        if prefix not in function_groups:
            function_groups[prefix] = []
        function_groups[prefix].append(func.name)

    # 為每組函式建立一個模組
    for prefix, funcs in function_groups.items():
        if funcs:
            refactoring["modules"].append({
                "name": f"{prefix}_functions.py",
                "content_type": "functions",
                "content_names": funcs
            })

    # 建立 __init__.py
    refactoring["modules"].append({
        "name": "__init__.py",
        "content_type": "init",
        "imports": [m["name"][:-3] for m in refactoring["modules"] if m["name"] != "__init__.py"]
    })

    return refactoring


def main():
    """
    主函式
    """
    parser = argparse.ArgumentParser(description="大型檔案重構腳本")
    parser.add_argument("--path", default="src", help="要掃描的路徑，預設為 src")
    parser.add_argument(
        "--threshold", type=int, default=300, help="檔案行數閾值，超過此值的檔案將被重構，預設為 300"
    )
    parser.add_argument("--dry-run", action="store_true", help="僅顯示將要重構的檔案，不實際執行重構")

    args = parser.parse_args()

    # 檢查路徑是否存在
    path = Path(args.path)
    if not path.exists():
        print(f"錯誤: 路徑 {path} 不存在")
        return 1

    # 尋找大型檔案
    large_files = find_large_files(path, args.threshold)
    if not large_files:
        print(f"沒有找到超過 {args.threshold} 行的檔案")
        return 0

    print(f"找到 {len(large_files)} 個大型檔案:")
    for file in large_files:
        print(f"  - {file} ({count_lines(file)} 行)")

    # 分析檔案並建議重構方案
    refactoring_plans = []
    for file in large_files:
        try:
            classes, functions = analyze_file(file)
            plan = suggest_refactoring(file, classes, functions)
            refactoring_plans.append(plan)
            
            print(f"\n重構方案 - {file}:")
            print(f"  建立目錄: {plan['new_directory']}")
            print("  建立模組:")
            for module in plan["modules"]:
                if module["name"] == "__init__.py":
                    print(f"    - {module['name']} (導入所有模組)")
                elif module["content_type"] == "class":
                    print(f"    - {module['name']} (包含類別 {module['content_name']})")
                elif module["content_type"] == "functions":
                    print(f"    - {module['name']} (包含 {len(module['content_names'])} 個函式)")
        except Exception as e:
            print(f"分析 {file} 時發生錯誤: {e}")

    # 如果是 dry run，則不執行重構
    if args.dry_run:
        print("\n這是一個 dry run，不會實際執行重構")
        return 0

    # 詢問用戶是否要執行重構
    response = input("\n是否要執行重構? (y/n): ")
    if response.lower() != "y":
        print("已取消重構")
        return 0

    # TODO: 實作重構邏輯
    print("重構功能尚未實作，請手動執行重構")
    return 0


if __name__ == "__main__":
    sys.exit(main())
