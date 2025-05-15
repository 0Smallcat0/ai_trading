#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
程式碼格式化腳本

此腳本用於格式化專案中的 Python 程式碼，包括：
- 使用 Black 格式化程式碼
- 使用 isort 排序 import
- 使用 autoflake 移除未使用的 import 和變數
- 使用 flake8 檢查程式碼品質

使用方法：
    python scripts/format_code.py [--path PATH] [--black] [--isort] [--autoflake] [--flake8] [--all]

參數：
    --path PATH: 要格式化的路徑，預設為 src
    --black: 使用 Black 格式化程式碼
    --isort: 使用 isort 排序 import
    --autoflake: 使用 autoflake 移除未使用的 import 和變數
    --flake8: 使用 flake8 檢查程式碼品質
    --all: 執行所有格式化工具
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path


def run_command(command, description):
    """
    執行命令

    Args:
        command (list): 命令
        description (str): 描述

    Returns:
        bool: 是否成功
    """
    print(f"執行 {description}...")
    try:
        subprocess.run(command, check=True)
        print(f"{description} 完成")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{description} 失敗: {e}")
        return False


def format_with_black(path):
    """
    使用 Black 格式化程式碼

    Args:
        path (str): 路徑

    Returns:
        bool: 是否成功
    """
    return run_command(["black", path], "Black 格式化")


def format_with_isort(path):
    """
    使用 isort 排序 import

    Args:
        path (str): 路徑

    Returns:
        bool: 是否成功
    """
    return run_command(["isort", path], "isort 排序")


def format_with_autoflake(path):
    """
    使用 autoflake 移除未使用的 import 和變數

    Args:
        path (str): 路徑

    Returns:
        bool: 是否成功
    """
    return run_command(
        [
            "autoflake",
            "--recursive",
            "--remove-all-unused-imports",
            "--remove-unused-variables",
            "--in-place",
            path,
        ],
        "autoflake 清理",
    )


def check_with_flake8(path):
    """
    使用 flake8 檢查程式碼品質

    Args:
        path (str): 路徑

    Returns:
        bool: 是否成功
    """
    return run_command(["flake8", path], "flake8 檢查")


def main():
    """
    主函式
    """
    parser = argparse.ArgumentParser(description="程式碼格式化腳本")
    parser.add_argument("--path", default="src", help="要格式化的路徑，預設為 src")
    parser.add_argument("--black", action="store_true", help="使用 Black 格式化程式碼")
    parser.add_argument("--isort", action="store_true", help="使用 isort 排序 import")
    parser.add_argument(
        "--autoflake", action="store_true", help="使用 autoflake 移除未使用的 import 和變數"
    )
    parser.add_argument("--flake8", action="store_true", help="使用 flake8 檢查程式碼品質")
    parser.add_argument("--all", action="store_true", help="執行所有格式化工具")

    args = parser.parse_args()

    # 如果沒有指定任何工具，則使用所有工具
    if not any([args.black, args.isort, args.autoflake, args.flake8, args.all]):
        args.all = True

    # 如果指定了 --all，則使用所有工具
    if args.all:
        args.black = True
        args.isort = True
        args.autoflake = True
        args.flake8 = True

    # 檢查路徑是否存在
    path = Path(args.path)
    if not path.exists():
        print(f"錯誤: 路徑 {path} 不存在")
        return 1

    # 執行格式化
    success = True

    if args.autoflake:
        success = format_with_autoflake(args.path) and success

    if args.isort:
        success = format_with_isort(args.path) and success

    if args.black:
        success = format_with_black(args.path) and success

    if args.flake8:
        success = check_with_flake8(args.path) and success

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
