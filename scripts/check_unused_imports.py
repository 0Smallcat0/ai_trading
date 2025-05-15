#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
檢查未使用的 import 和變數

此腳本用於檢查專案中未使用的 import 和變數，並提供修復建議。

使用方法：
    python scripts/check_unused_imports.py [--path PATH] [--fix]

參數：
    --path PATH: 要檢查的路徑，預設為 src
    --fix: 自動修復問題
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


def run_autoflake(path, fix=False):
    """
    執行 autoflake

    Args:
        path (str): 路徑
        fix (bool): 是否修復問題

    Returns:
        str: 輸出
    """
    cmd = [
        "autoflake",
        "--recursive",
        "--remove-all-unused-imports",
        "--remove-unused-variables",
    ]

    if fix:
        cmd.append("--in-place")
    else:
        cmd.append("--check")

    cmd.append(path)

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        if e.returncode == 1 and not fix:
            # 找到問題但未修復
            return e.stdout
        else:
            print(f"執行 autoflake 時發生錯誤: {e}")
            print(f"錯誤輸出: {e.stderr}")
            return None


def main():
    """
    主函式
    """
    parser = argparse.ArgumentParser(description="檢查未使用的 import 和變數")
    parser.add_argument("--path", default="src", help="要檢查的路徑，預設為 src")
    parser.add_argument("--fix", action="store_true", help="自動修復問題")

    args = parser.parse_args()

    # 檢查路徑是否存在
    path = Path(args.path)
    if not path.exists():
        print(f"錯誤: 路徑 {path} 不存在")
        return 1

    # 執行 autoflake
    print(f"檢查 {path} 中的未使用 import 和變數...")
    output = run_autoflake(args.path, args.fix)

    if output is None:
        return 1

    if not output and not args.fix:
        print("沒有找到未使用的 import 和變數")
        return 0

    if args.fix:
        print("已修復未使用的 import 和變數")
    else:
        print("找到以下未使用的 import 和變數:")
        print(output)
        print("使用 --fix 參數可自動修復這些問題")

    return 0


if __name__ == "__main__":
    sys.exit(main())
