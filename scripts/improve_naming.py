#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
改進命名規則腳本

此腳本用於檢查和改進專案中的命名規則，包括：
- 檢查變數名稱是否符合 snake_case 命名規則
- 檢查類別名稱是否符合 PascalCase 命名規則
- 檢查常數名稱是否符合 UPPER_CASE 命名規則
- 識別過度縮寫的變數名稱並建議更具描述性的名稱

使用方法：
    python scripts/improve_naming.py [--path PATH] [--check-only]

參數：
    --path PATH: 要檢查的路徑，預設為 src
    --check-only: 僅檢查問題，不提供修復建議
"""

import os
import sys
import ast
import re
import argparse
from pathlib import Path
from typing import Dict, List, Set, Tuple


class NamingVisitor(ast.NodeVisitor):
    """
    命名訪問器

    用於訪問 AST 中的命名節點。
    """

    def __init__(self):
        self.variables = []
        self.classes = []
        self.functions = []
        self.constants = []
        self.assignments = {}

    def visit_Name(self, node):
        """
        訪問名稱節點

        Args:
            node (ast.Name): 名稱節點
        """
        if isinstance(node.ctx, ast.Store):
            self.variables.append(node.id)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """
        訪問類別定義節點

        Args:
            node (ast.ClassDef): 類別定義節點
        """
        self.classes.append(node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """
        訪問函式定義節點

        Args:
            node (ast.FunctionDef): 函式定義節點
        """
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_Assign(self, node):
        """
        訪問賦值節點

        Args:
            node (ast.Assign): 賦值節點
        """
        for target in node.targets:
            if isinstance(target, ast.Name):
                if target.id.isupper():
                    self.constants.append(target.id)
                if isinstance(node.value, ast.Constant):
                    self.assignments[target.id] = node.value.value
        self.generic_visit(node)


def is_snake_case(name: str) -> bool:
    """
    檢查名稱是否符合 snake_case 命名規則

    Args:
        name (str): 名稱

    Returns:
        bool: 是否符合 snake_case 命名規則
    """
    return re.match(r"^[a-z][a-z0-9_]*$", name) is not None


def is_pascal_case(name: str) -> bool:
    """
    檢查名稱是否符合 PascalCase 命名規則

    Args:
        name (str): 名稱

    Returns:
        bool: 是否符合 PascalCase 命名規則
    """
    return re.match(r"^[A-Z][a-zA-Z0-9]*$", name) is not None


def is_upper_case(name: str) -> bool:
    """
    檢查名稱是否符合 UPPER_CASE 命名規則

    Args:
        name (str): 名稱

    Returns:
        bool: 是否符合 UPPER_CASE 命名規則
    """
    return re.match(r"^[A-Z][A-Z0-9_]*$", name) is not None


def is_abbreviated(name: str) -> bool:
    """
    檢查名稱是否過度縮寫

    Args:
        name (str): 名稱

    Returns:
        bool: 是否過度縮寫
    """
    # 排除常見的縮寫
    common_abbreviations = {"id", "db", "url", "api", "ui", "io", "ip", "os", "fs"}
    if name.lower() in common_abbreviations:
        return False

    # 檢查是否只有一個或兩個字母
    if len(name) <= 2 and name.isalpha():
        return True

    # 檢查是否由多個單字母組成
    parts = name.split("_")
    return any(len(part) == 1 for part in parts if part.isalpha())


def suggest_better_name(name: str, context: str = None) -> str:
    """
    建議更好的名稱

    Args:
        name (str): 名稱
        context (str, optional): 上下文

    Returns:
        str: 建議的名稱
    """
    # 常見縮寫對應的完整名稱
    abbreviations = {
        "i": "index",
        "j": "index2",
        "k": "index3",
        "n": "count",
        "x": "value_x",
        "y": "value_y",
        "z": "value_z",
        "fn": "function",
        "cb": "callback",
        "ctx": "context",
        "req": "request",
        "res": "response",
        "cfg": "config",
        "conf": "config",
        "auth": "authentication",
        "obj": "object",
        "arr": "array",
        "dict": "dictionary",
        "str": "string",
        "num": "number",
        "val": "value",
        "var": "variable",
        "param": "parameter",
        "arg": "argument",
        "tmp": "temporary",
        "temp": "temporary",
        "buf": "buffer",
        "src": "source",
        "dest": "destination",
        "prev": "previous",
        "curr": "current",
        "next": "next",
        "min": "minimum",
        "max": "maximum",
        "avg": "average",
        "calc": "calculate",
        "proc": "process",
        "exec": "execute",
        "init": "initialize",
        "util": "utility",
        "lib": "library",
        "mod": "module",
        "pkg": "package",
        "impl": "implementation",
        "msg": "message",
        "err": "error",
        "exc": "exception",
        "warn": "warning",
        "info": "information",
        "debug": "debug",
        "log": "logger",
        "fmt": "format",
        "addr": "address",
        "dir": "directory",
        "path": "file_path",
        "fname": "file_name",
        "ext": "extension",
        "img": "image",
        "pic": "picture",
        "doc": "document",
        "txt": "text",
        "btn": "button",
        "dlg": "dialog",
        "win": "window",
        "frm": "form",
        "pnl": "panel",
        "lbl": "label",
        "chk": "checkbox",
        "rad": "radio",
        "lst": "list",
        "tbl": "table",
        "col": "column",
        "row": "row",
        "idx": "index",
        "pos": "position",
        "len": "length",
        "sz": "size",
        "cnt": "count",
        "num": "number",
        "qty": "quantity",
        "amt": "amount",
        "tot": "total",
        "sum": "sum",
        "diff": "difference",
        "dist": "distance",
        "dur": "duration",
        "tm": "time",
        "dt": "date",
        "ts": "timestamp",
        "sec": "second",
        "min": "minute",
        "hr": "hour",
        "day": "day",
        "wk": "week",
        "mo": "month",
        "yr": "year",
    }

    # 如果是單個字母或常見縮寫，直接查表
    if name in abbreviations:
        return abbreviations[name]

    # 如果是由多個縮寫組成，嘗試拆分並替換
    parts = name.split("_")
    new_parts = []
    for part in parts:
        if part in abbreviations:
            new_parts.append(abbreviations[part])
        else:
            new_parts.append(part)
    
    return "_".join(new_parts)


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

    visitor = NamingVisitor()
    visitor.visit(tree)

    result = {
        "file": file_path,
        "issues": {
            "non_snake_case_variables": [],
            "non_pascal_case_classes": [],
            "non_snake_case_functions": [],
            "non_upper_case_constants": [],
            "abbreviated_names": []
        }
    }

    # 檢查變數命名
    for var in visitor.variables:
        if var.startswith("_"):  # 忽略私有變數
            continue
        if not is_snake_case(var) and var not in visitor.constants:
            result["issues"]["non_snake_case_variables"].append(var)
        if is_abbreviated(var):
            result["issues"]["abbreviated_names"].append({
                "name": var,
                "type": "variable",
                "suggestion": suggest_better_name(var)
            })

    # 檢查類別命名
    for cls in visitor.classes:
        if not is_pascal_case(cls):
            result["issues"]["non_pascal_case_classes"].append(cls)

    # 檢查函式命名
    for func in visitor.functions:
        if func.startswith("__"):  # 忽略魔術方法
            continue
        if not is_snake_case(func):
            result["issues"]["non_snake_case_functions"].append(func)
        if is_abbreviated(func):
            result["issues"]["abbreviated_names"].append({
                "name": func,
                "type": "function",
                "suggestion": suggest_better_name(func)
            })

    # 檢查常數命名
    for const in visitor.constants:
        if not is_upper_case(const):
            result["issues"]["non_upper_case_constants"].append(const)

    return result


def main():
    """
    主函式
    """
    parser = argparse.ArgumentParser(description="改進命名規則腳本")
    parser.add_argument("--path", default="src", help="要檢查的路徑，預設為 src")
    parser.add_argument("--check-only", action="store_true", help="僅檢查問題，不提供修復建議")

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
    all_issues = []
    for file in python_files:
        result = analyze_file(file)
        if result:
            has_issues = any(len(issues) > 0 for issues in result["issues"].values())
            if has_issues:
                all_issues.append(result)

    # 輸出結果
    if not all_issues:
        print("沒有發現命名規則問題")
        return 0

    print(f"在 {len(all_issues)} 個檔案中發現命名規則問題:")
    for result in all_issues:
        print(f"\n檔案: {result['file']}")
        
        if result["issues"]["non_snake_case_variables"]:
            print("  不符合 snake_case 的變數:")
            for var in result["issues"]["non_snake_case_variables"]:
                print(f"    - {var}")
        
        if result["issues"]["non_pascal_case_classes"]:
            print("  不符合 PascalCase 的類別:")
            for cls in result["issues"]["non_pascal_case_classes"]:
                print(f"    - {cls}")
        
        if result["issues"]["non_snake_case_functions"]:
            print("  不符合 snake_case 的函式:")
            for func in result["issues"]["non_snake_case_functions"]:
                print(f"    - {func}")
        
        if result["issues"]["non_upper_case_constants"]:
            print("  不符合 UPPER_CASE 的常數:")
            for const in result["issues"]["non_upper_case_constants"]:
                print(f"    - {const}")
        
        if not args.check_only and result["issues"]["abbreviated_names"]:
            print("  過度縮寫的名稱:")
            for item in result["issues"]["abbreviated_names"]:
                print(f"    - {item['name']} ({item['type']}): 建議改為 {item['suggestion']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
