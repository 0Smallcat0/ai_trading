#!/usr/bin/env python
"""
配置驗證測試腳本

此腳本用於測試配置驗證功能。
"""

import os
import sys
from pathlib import Path

# 添加專案根目錄到 Python 路徑
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

# 導入配置驗證模組
from src.utils.config_validator import (
    ConfigSeverity,
    ConfigValidator,
    create_core_validator,
    create_trading_validator,
    create_monitoring_validator,
    validate_all_configs,
)


def print_separator(title):
    """打印分隔線"""
    print("\n" + "=" * 50)
    print(f" {title} ".center(50, "="))
    print("=" * 50)


def test_basic_validator():
    """測試基本驗證器"""
    print_separator("基本驗證器測試")

    # 創建驗證器
    validator = ConfigValidator()
    validator.add_required_config("TEST_VAR1", ConfigSeverity.ERROR, "測試變數 1")
    validator.add_required_config("TEST_VAR2", ConfigSeverity.WARNING, "測試變數 2")
    validator.add_required_config("TEST_VAR3", ConfigSeverity.INFO, "測試變數 3")

    # 設置測試環境變數
    os.environ["TEST_VAR1"] = "value1"
    os.environ["TEST_VAR3"] = "value3"

    # 驗證環境變數
    result = validator.validate_env_vars()

    print("驗證結果:")
    print(str(result))
    print(f"有錯誤: {result.has_errors}")
    print(f"有警告: {result.has_warnings}")
    print(f"有問題: {result.has_issues}")

    # 清理測試環境變數
    del os.environ["TEST_VAR1"]
    del os.environ["TEST_VAR3"]


def test_predefined_validators():
    """測試預定義驗證器"""
    print_separator("預定義驗證器測試")

    # 測試核心驗證器
    core_validator = create_core_validator()
    print("核心驗證器要求的配置項:")
    for name, severity, description in core_validator.required_configs:
        print(f"- {name} ({severity.value}): {description}")

    # 測試交易驗證器
    trading_validator = create_trading_validator()
    print("\n交易驗證器要求的配置項:")
    for name, severity, description in trading_validator.required_configs:
        print(f"- {name} ({severity.value}): {description}")

    # 測試監控驗證器
    monitoring_validator = create_monitoring_validator()
    print("\n監控驗證器要求的配置項:")
    for name, severity, description in monitoring_validator.required_configs:
        print(f"- {name} ({severity.value}): {description}")


def test_validate_all_configs():
    """測試驗證所有配置"""
    print_separator("驗證所有配置測試")

    # 驗證當前環境的所有配置
    result = validate_all_configs()

    print("驗證結果:")
    print(str(result))
    print(f"有錯誤: {result.has_errors}")
    print(f"有警告: {result.has_warnings}")
    print(f"有問題: {result.has_issues}")


def main():
    """主函數"""
    print_separator("配置驗證測試開始")

    test_basic_validator()
    test_predefined_validators()
    test_validate_all_configs()

    print_separator("配置驗證測試完成")


if __name__ == "__main__":
    main()
