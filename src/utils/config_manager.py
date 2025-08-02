"""
配置管理模組

此模組提供統一的配置管理功能，支持多種配置源和格式。
"""

import json
import os
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import dotenv_values


class ConfigSource(Enum):
    """配置源類型"""

    ENV = "env"  # 環境變數
    FILE = "file"  # 文件
    CONSUL = "consul"  # Consul
    ETCD = "etcd"  # etcd
    MEMORY = "memory"  # 內存


class ConfigProvider(ABC):
    """配置提供者抽象類"""

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """獲取配置項"""

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """設置配置項"""

    @abstractmethod
    def delete(self, key: str) -> None:
        """刪除配置項"""

    @abstractmethod
    def list(self, prefix: str = "") -> Dict[str, Any]:
        """列出配置項"""


class EnvConfigProvider(ConfigProvider):
    """環境變數配置提供者"""

    def __init__(self, env_file: Optional[str] = None):
        """
        初始化環境變數配置提供者

        Args:
            env_file (str, optional): 環境變數文件路徑
        """
        self.env_vars = {}

        # 載入環境變數文件
        if env_file and os.path.exists(env_file):
            self.env_vars.update(dotenv_values(env_file))

        # 載入系統環境變數
        self.env_vars.update(dict(os.environ.items()))

    def get(self, key: str, default: Any = None) -> Any:
        """獲取配置項"""
        return self.env_vars.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """設置配置項"""
        self.env_vars[key] = str(value)
        os.environ[key] = str(value)

    def delete(self, key: str) -> None:
        """刪除配置項"""
        if key in self.env_vars:
            del self.env_vars[key]

        if key in os.environ:
            del os.environ[key]

    def list(self, prefix: str = "") -> Dict[str, Any]:
        """列出配置項"""
        return {k: v for k, v in self.env_vars.items() if k.startswith(prefix)}


class FileConfigProvider(ConfigProvider):
    """文件配置提供者"""

    def __init__(self, file_path: str):
        """
        初始化文件配置提供者

        Args:
            file_path (str): 配置文件路徑
        """
        self.file_path = Path(file_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """載入配置文件"""
        if not self.file_path.exists():
            return {}

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                if self.file_path.suffix.lower() in [".yaml", ".yml"]:
                    return yaml.safe_load(f) or {}
                if self.file_path.suffix.lower() == ".json":
                    return json.load(f)

                print(f"不支援的配置文件格式: {self.file_path.suffix}")
                return {}
        except Exception as e:
            print(f"載入配置文件時發生錯誤: {e}")
            return {}

    def _save_config(self) -> None:
        """保存配置文件"""
        try:
            # 確保目錄存在
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.file_path, "w", encoding="utf-8") as f:
                if self.file_path.suffix.lower() in [".yaml", ".yml"]:
                    yaml.dump(
                        self.config, f, default_flow_style=False, allow_unicode=True
                    )
                    return
                if self.file_path.suffix.lower() == ".json":
                    json.dump(self.config, f, ensure_ascii=False, indent=2)
                    return

                print(f"不支援的配置文件格式: {self.file_path.suffix}")
        except Exception as e:
            print(f"保存配置文件時發生錯誤: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """獲取配置項"""
        # 支持點號分隔的鍵
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """設置配置項"""
        # 支持點號分隔的鍵
        keys = key.split(".")
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            elif not isinstance(config[k], dict):
                config[k] = {}

            config = config[k]

        config[keys[-1]] = value
        self._save_config()

    def delete(self, key: str) -> None:
        """刪除配置項"""
        # 支持點號分隔的鍵
        keys = key.split(".")
        config = self.config

        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                return

            config = config[k]

        if keys[-1] in config:
            del config[keys[-1]]
            self._save_config()

    def list(self, prefix: str = "") -> Dict[str, Any]:
        """列出配置項"""
        result = {}

        def _list_recursive(config, path=""):
            if isinstance(config, dict):
                for k, v in config.items():
                    new_path = f"{path}.{k}" if path else k

                    if isinstance(v, dict):
                        _list_recursive(v, new_path)
                    else:
                        if not prefix or new_path.startswith(prefix):
                            result[new_path] = v

        _list_recursive(self.config)
        return result


class MemoryConfigProvider(ConfigProvider):
    """內存配置提供者"""

    def __init__(self):
        """初始化內存配置提供者"""
        self.config = {}

    def get(self, key: str, default: Any = None) -> Any:
        """獲取配置項"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """設置配置項"""
        self.config[key] = value

    def delete(self, key: str) -> None:
        """刪除配置項"""
        if key in self.config:
            del self.config[key]

    def list(self, prefix: str = "") -> Dict[str, Any]:
        """列出配置項"""
        return {k: v for k, v in self.config.items() if k.startswith(prefix)}


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        """初始化配置管理器"""
        self.providers = {}
        self.provider_order = []

    def add_provider(
        self, name: str, provider: ConfigProvider, priority: int = 0
    ) -> None:
        """
        添加配置提供者

        Args:
            name (str): 提供者名稱
            provider (ConfigProvider): 配置提供者
            priority (int, optional): 優先級，數字越大優先級越高
        """
        self.providers[name] = {"provider": provider, "priority": priority}

        # 按優先級排序
        self.provider_order = sorted(
            self.providers.keys(),
            key=lambda x: self.providers[x]["priority"],
            reverse=True,
        )

    def get(self, key: str, default: Any = None) -> Any:
        """
        獲取配置項

        Args:
            key (str): 配置項鍵
            default (Any, optional): 默認值

        Returns:
            Any: 配置項值
        """
        for name in self.provider_order:
            provider = self.providers[name]["provider"]
            value = provider.get(key)

            if value is not None:
                return value

        return default

    def get_int(self, key: str, default: int = 0) -> int:
        """獲取整數配置項"""
        value = self.get(key, default)

        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """獲取浮點數配置項"""
        value = self.get(key, default)

        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        """獲取布爾配置項"""
        value = self.get(key, default)

        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.lower() in ["true", "yes", "1", "y", "t"]

        return bool(value)

    def get_list(self, key: str, default: Optional[List[Any]] = None) -> List[Any]:
        """獲取列表配置項"""
        if default is None:
            default = []

        value = self.get(key, default)

        if isinstance(value, list):
            return value

        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value.split(",")

        return default

    def set(self, key: str, value: Any, provider_name: Optional[str] = None) -> None:
        """
        設置配置項

        Args:
            key (str): 配置項鍵
            value (Any): 配置項值
            provider_name (str, optional): 提供者名稱，如果為 None 則使用優先級最高的提供者
        """
        if provider_name is None:
            if not self.provider_order:
                raise ValueError("沒有可用的配置提供者")

            provider_name = self.provider_order[0]

        if provider_name not in self.providers:
            raise ValueError(f"未知的配置提供者: {provider_name}")

        provider = self.providers[provider_name]["provider"]
        provider.set(key, value)

    def delete(self, key: str, provider_name: Optional[str] = None) -> None:
        """
        刪除配置項

        Args:
            key (str): 配置項鍵
            provider_name (str, optional): 提供者名稱，如果為 None 則從所有提供者中刪除
        """
        if provider_name is None:
            for name in self.provider_order:
                provider = self.providers[name]["provider"]
                provider.delete(key)
        else:
            if provider_name not in self.providers:
                raise ValueError(f"未知的配置提供者: {provider_name}")

            provider = self.providers[provider_name]["provider"]
            provider.delete(key)

    def list(
        self, prefix: str = "", provider_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        列出配置項

        Args:
            prefix (str, optional): 前綴
            provider_name (str, optional): 提供者名稱，如果為 None 則列出所有提供者的配置項

        Returns:
            Dict[str, Any]: 配置項字典
        """
        result = {}

        if provider_name is None:
            for name in self.provider_order:
                provider = self.providers[name]["provider"]
                result.update(provider.list(prefix))
        else:
            if provider_name not in self.providers:
                raise ValueError(f"未知的配置提供者: {provider_name}")

            provider = self.providers[provider_name]["provider"]
            result.update(provider.list(prefix))

        return result


# 創建默認配置管理器
def create_default_config_manager() -> ConfigManager:
    """
    創建默認配置管理器

    Returns:
        ConfigManager: 配置管理器
    """
    manager = ConfigManager()

    # 添加環境變數提供者
    env_provider = EnvConfigProvider()
    manager.add_provider("env", env_provider, priority=100)

    # 添加內存提供者
    memory_provider = MemoryConfigProvider()
    manager.add_provider("memory", memory_provider, priority=50)

    return manager


# 默認配置管理器實例
default_config_manager = create_default_config_manager()
