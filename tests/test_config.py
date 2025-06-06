#!/usr/bin/env python
"""
配置載入測試腳本

此腳本用於測試環境變數和配置文件的載入是否正確。
"""

import os
import sys
import pytest
from pathlib import Path

# 添加專案根目錄到 Python 路徑
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

# 導入配置模組
from src import config


def print_separator(title):
    """打印分隔線"""
    print("\n" + "=" * 50)
    print(f" {title} ".center(50, "="))
    print("=" * 50)


def test_db_url():
    """測試資料庫URL配置"""
    assert config.DB_URL is not None
    assert isinstance(config.DB_URL, str)
    assert len(config.DB_URL) > 0


def test_api_key():
    """測試API金鑰配置"""
    assert config.API_KEY is not None
    assert isinstance(config.API_KEY, str)
    assert len(config.API_KEY) > 0


def test_env_loading():
    """測試環境變數載入"""
    print_separator("環境變數載入測試")

    print(f"當前環境: {config.ENV}")
    print(f"根目錄 .env 文件: {os.path.join(config.ROOT_DIR, '.env')}")
    print(
        f"環境特定文件: {os.path.join(config.ROOT_DIR, '.envs', f'.env.{config.ENV}')}"
    )

    # 測試基本環境變數
    print("\n基本環境變數:")
    print(f"- DB_URL: {config.DB_URL}")
    print(f"- API_KEY: {'已設置' if config.API_KEY else '未設置'}")
    print(f"- LOG_LEVEL: {config.LOG_LEVEL}")
    print(f"- DEBUG_MODE: {config.DEBUG_MODE}")

    # 測試目錄設定
    print("\n目錄設定:")
    print(f"- DATA_DIR: {config.DATA_DIR}")
    print(f"- LOGS_DIR: {config.LOGS_DIR}")
    print(f"- RESULTS_DIR: {config.RESULTS_DIR}")

    # 測試其他設定
    print("\n其他設定:")
    print(f"- TRADING_HOURS_START: {config.TRADING_HOURS_START}")
    print(f"- TRADING_HOURS_END: {config.TRADING_HOURS_END}")
    print(f"- MAX_POSITION_SIZE: {config.MAX_POSITION_SIZE}")
    print(f"- STOP_LOSS_THRESHOLD: {config.STOP_LOSS_THRESHOLD}")

    # 基本斷言測試
    assert hasattr(config, "ENV")
    assert hasattr(config, "ROOT_DIR")
    assert hasattr(config, "DB_URL")
    assert hasattr(config, "LOG_LEVEL")


def test_config_file_loading():
    """測試配置文件載入"""
    print_separator("配置文件載入測試")

    # 測試 brokers.yaml 載入
    brokers_config_path = os.path.join(config.ROOT_DIR, "config", "brokers.yaml")
    brokers_config = config.load_config_file(brokers_config_path)

    print(f"券商配置文件: {brokers_config_path}")
    if brokers_config:
        print(f"已載入券商配置，包含 {len(brokers_config)} 個券商:")
        for broker_name in brokers_config:
            print(f"- {broker_name}")
        assert isinstance(brokers_config, dict)
        assert len(brokers_config) > 0
    else:
        print("未能載入券商配置")

    # 測試不存在的配置文件
    non_existent_path = os.path.join(config.ROOT_DIR, "config", "non_existent.yaml")
    default_config = {"test": "default"}
    result = config.load_config_file(non_existent_path, default=default_config)
    print(f"\n測試不存在的配置文件: {non_existent_path}")
    print(f"返回默認配置: {result}")

    assert result == default_config


def test_override_behavior():
    """測試環境變數覆蓋行為"""
    print_separator("環境變數覆蓋測試")

    # 設置臨時環境變數
    original_log_level = os.environ.get("LOG_LEVEL")
    os.environ["LOG_LEVEL"] = "DEBUG"

    # 重新導入配置模組
    import importlib

    importlib.reload(config)

    print(f"設置臨時環境變數 LOG_LEVEL=DEBUG")
    print(f"重新載入後的 LOG_LEVEL: {config.LOG_LEVEL}")

    # 驗證覆蓋行為
    assert config.LOG_LEVEL == "DEBUG"

    # 恢復原始環境變數
    if original_log_level:
        os.environ["LOG_LEVEL"] = original_log_level
    else:
        del os.environ["LOG_LEVEL"]


def test_directory_configurations():
    """測試目錄配置"""
    # 測試目錄配置存在且為字符串
    assert hasattr(config, "DATA_DIR")
    assert hasattr(config, "LOGS_DIR")
    assert hasattr(config, "RESULTS_DIR")

    if hasattr(config, "DATA_DIR") and config.DATA_DIR:
        assert isinstance(config.DATA_DIR, str)
    if hasattr(config, "LOGS_DIR") and config.LOGS_DIR:
        assert isinstance(config.LOGS_DIR, str)
    if hasattr(config, "RESULTS_DIR") and config.RESULTS_DIR:
        assert isinstance(config.RESULTS_DIR, str)


def test_trading_configurations():
    """測試交易相關配置"""
    # 測試交易時間配置
    if hasattr(config, "TRADING_HOURS_START"):
        assert config.TRADING_HOURS_START is not None
    if hasattr(config, "TRADING_HOURS_END"):
        assert config.TRADING_HOURS_END is not None

    # 測試風險管理配置
    if hasattr(config, "MAX_POSITION_SIZE"):
        assert config.MAX_POSITION_SIZE is not None
    if hasattr(config, "STOP_LOSS_THRESHOLD"):
        assert config.STOP_LOSS_THRESHOLD is not None


if __name__ == "__main__":
    """主函數 - 用於直接運行測試"""
    print_separator("配置測試開始")
    print(f"專案根目錄: {ROOT_DIR}")

    test_env_loading()
    test_config_file_loading()
    test_override_behavior()

    print_separator("配置測試完成")
