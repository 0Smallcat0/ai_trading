#!/usr/bin/env python
"""
配置管理器測試腳本

此腳本用於測試配置管理器功能。
"""

import os
import sys
import tempfile
from pathlib import Path

# 添加專案根目錄到 Python 路徑
ROOT_DIR = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT_DIR))

# 導入配置管理模組
from src.utils.config_manager import (
    ConfigManager,
    EnvConfigProvider,
    FileConfigProvider,
    MemoryConfigProvider,
    create_default_config_manager
)

def print_separator(title):
    """打印分隔線"""
    print("\n" + "=" * 50)
    print(f" {title} ".center(50, "="))
    print("=" * 50)

def test_env_provider():
    """測試環境變數提供者"""
    print_separator("環境變數提供者測試")

    # 設置測試環境變數
    os.environ["TEST_ENV_VAR1"] = "value1"
    os.environ["TEST_ENV_VAR2"] = "value2"

    # 創建環境變數提供者
    provider = EnvConfigProvider()

    # 測試獲取配置項
    print(f"TEST_ENV_VAR1: {provider.get('TEST_ENV_VAR1')}")
    print(f"TEST_ENV_VAR2: {provider.get('TEST_ENV_VAR2')}")
    print(f"TEST_ENV_VAR3 (不存在): {provider.get('TEST_ENV_VAR3', '默認值')}")

    # 測試設置配置項
    provider.set("TEST_ENV_VAR3", "value3")
    print(f"設置後 TEST_ENV_VAR3: {provider.get('TEST_ENV_VAR3')}")

    # 測試刪除配置項
    provider.delete("TEST_ENV_VAR2")
    print(f"刪除後 TEST_ENV_VAR2: {provider.get('TEST_ENV_VAR2', '已刪除')}")

    # 測試列出配置項
    print("\n列出 TEST_ 開頭的配置項:")
    for key, value in provider.list("TEST_").items():
        print(f"- {key}: {value}")

    # 清理測試環境變數
    del os.environ["TEST_ENV_VAR1"]
    if "TEST_ENV_VAR2" in os.environ:
        del os.environ["TEST_ENV_VAR2"]
    if "TEST_ENV_VAR3" in os.environ:
        del os.environ["TEST_ENV_VAR3"]

def test_file_provider():
    """測試文件提供者"""
    print_separator("文件提供者測試")

    # 創建臨時文件
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp:
        temp_path = temp.name

    try:
        # 創建文件提供者
        provider = FileConfigProvider(temp_path)

        # 測試設置配置項
        provider.set("database.url", "sqlite:///test.db")
        provider.set("database.pool_size", 10)
        provider.set("api.key", "test-key")
        provider.set("api.timeout", 30)

        # 測試獲取配置項
        print(f"database.url: {provider.get('database.url')}")
        print(f"database.pool_size: {provider.get('database.pool_size')}")
        print(f"api.key: {provider.get('api.key')}")
        print(f"api.timeout: {provider.get('api.timeout')}")
        print(f"api.retry (不存在): {provider.get('api.retry', 3)}")

        # 測試刪除配置項
        provider.delete("api.key")
        print(f"刪除後 api.key: {provider.get('api.key', '已刪除')}")

        # 測試列出配置項
        print("\n列出所有配置項:")
        for key, value in provider.list().items():
            print(f"- {key}: {value}")

        print("\n列出 database. 開頭的配置項:")
        for key, value in provider.list("database").items():
            print(f"- {key}: {value}")
    finally:
        # 刪除臨時文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)

def test_memory_provider():
    """測試內存提供者"""
    print_separator("內存提供者測試")

    # 創建內存提供者
    provider = MemoryConfigProvider()

    # 測試設置配置項
    provider.set("key1", "value1")
    provider.set("key2", 123)
    provider.set("key3", True)
    provider.set("nested.key", "nested-value")

    # 測試獲取配置項
    print(f"key1: {provider.get('key1')}")
    print(f"key2: {provider.get('key2')}")
    print(f"key3: {provider.get('key3')}")
    print(f"nested.key: {provider.get('nested.key')}")
    print(f"key4 (不存在): {provider.get('key4', '默認值')}")

    # 測試刪除配置項
    provider.delete("key2")
    print(f"刪除後 key2: {provider.get('key2', '已刪除')}")

    # 測試列出配置項
    print("\n列出所有配置項:")
    for key, value in provider.list().items():
        print(f"- {key}: {value}")

def test_config_manager():
    """測試配置管理器"""
    print_separator("配置管理器測試")

    # 設置測試環境變數
    os.environ["TEST_VAR1"] = "env-value1"
    os.environ["TEST_INT"] = "123"
    os.environ["TEST_FLOAT"] = "123.45"
    os.environ["TEST_BOOL"] = "true"
    os.environ["TEST_LIST"] = "a,b,c"

    # 創建配置管理器
    manager = ConfigManager()

    # 添加提供者
    env_provider = EnvConfigProvider()  # 這將載入當前環境變數
    memory_provider = MemoryConfigProvider()

    # 設置內存配置項
    memory_provider.set("TEST_VAR2", "memory-value2")

    # 添加提供者到管理器
    manager.add_provider("env", env_provider, priority=100)
    manager.add_provider("memory", memory_provider, priority=50)

    # 測試獲取配置項
    print("測試優先級:")
    print(f"TEST_VAR1 (應該是環境變數值): {manager.get('TEST_VAR1')}")
    print(f"TEST_VAR2 (應該是內存值): {manager.get('TEST_VAR2')}")
    print(f"TEST_VAR3 (不存在): {manager.get('TEST_VAR3', '默認值')}")

    print("\n測試類型轉換:")
    print(f"TEST_INT: {manager.get_int('TEST_INT')}")
    print(f"TEST_FLOAT: {manager.get_float('TEST_FLOAT')}")
    print(f"TEST_BOOL: {manager.get_bool('TEST_BOOL')}")
    print(f"TEST_LIST: {manager.get_list('TEST_LIST')}")

    # 測試設置配置項
    manager.set("TEST_VAR3", "new-value", provider_name="memory")
    print(f"\n設置後 TEST_VAR3: {manager.get('TEST_VAR3')}")

    # 測試列出配置項
    print("\n列出 TEST_ 開頭的配置項:")
    for key, value in manager.list("TEST_").items():
        print(f"- {key}: {value}")

    # 清理測試環境變數
    del os.environ["TEST_VAR1"]
    del os.environ["TEST_INT"]
    del os.environ["TEST_FLOAT"]
    del os.environ["TEST_BOOL"]
    del os.environ["TEST_LIST"]

def test_default_config_manager():
    """測試默認配置管理器"""
    print_separator("默認配置管理器測試")

    # 設置測試環境變數
    os.environ["TEST_DEFAULT_VAR"] = "default-value"

    # 重新創建默認配置管理器以載入新的環境變數
    from src.utils.config_manager import create_default_config_manager
    test_config_manager = create_default_config_manager()

    # 測試獲取配置項
    print(f"TEST_DEFAULT_VAR: {test_config_manager.get('TEST_DEFAULT_VAR')}")
    print(f"TEST_DEFAULT_VAR2 (不存在): {test_config_manager.get('TEST_DEFAULT_VAR2', '默認值')}")

    # 測試設置內存配置項
    test_config_manager.set("TEST_DEFAULT_VAR2", "memory-value", provider_name="memory")
    print(f"設置後 TEST_DEFAULT_VAR2: {test_config_manager.get('TEST_DEFAULT_VAR2')}")

    # 清理測試環境變數
    del os.environ["TEST_DEFAULT_VAR"]

def main():
    """主函數"""
    print_separator("配置管理器測試開始")

    test_env_provider()
    test_file_provider()
    test_memory_provider()
    test_config_manager()
    test_default_config_manager()

    print_separator("配置管理器測試完成")

if __name__ == "__main__":
    main()
