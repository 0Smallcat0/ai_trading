#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
語法檢查腳本
檢查任務3.1相關程式碼檔案的語法錯誤
"""

import ast
import os
import sys


def check_syntax(file_path):
    """檢查單個檔案的語法"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        ast.parse(content)
        return True, "語法正確"
    except SyntaxError as e:
        return False, f"語法錯誤 - 行 {e.lineno}: {e.msg}"
    except FileNotFoundError:
        return False, "檔案不存在"
    except Exception as e:
        return False, f"其他錯誤 - {e}"


def main():
    """主函數"""
    files_to_check = [
        "src/models/strategy_research.py",
        "src/models/model_factory.py",
        "src/models/dataset.py",
        "src/models/rule_based_models.py",
        "src/models/ml_models.py",
        "src/models/dl_models.py",
        "src/models/model_base.py",
        "src/strategy/__init__.py",
        "src/strategy/strategy.py",
        "src/strategy/base.py",
        "src/strategy/technical/__init__.py",
        "src/strategy/ml/__init__.py",
        "src/core/features.py",
        "src/core/feature_engineering_service.py",
    ]

    print("=" * 60)
    print("任務3.1 策略研究與模型選擇 - 程式碼語法檢查")
    print("=" * 60)

    all_passed = True

    for file_path in files_to_check:
        if os.path.exists(file_path):
            passed, message = check_syntax(file_path)
            status = "✓" if passed else "✗"
            print(f"{status} {file_path}: {message}")
            if not passed:
                all_passed = False
        else:
            print(f"✗ {file_path}: 檔案不存在")
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("✓ 所有檔案語法檢查通過")
    else:
        print("✗ 發現語法錯誤，需要修正")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
