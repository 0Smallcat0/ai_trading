"""
券商配置模組

此模組負責管理券商連接的配置，包括：
- API 金鑰管理
- 環境配置 (模擬/實盤)
- 交易參數設定
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
import yaml

from .security import load_api_keys

# 設定日誌
logger = logging.getLogger("execution.config")


class TradingEnvironment(Enum):
    """交易環境列舉"""
    PAPER = "paper"  # 模擬交易
    LIVE = "live"    # 實盤交易


@dataclass
class BrokerConfig:
    """券商配置類別"""
    name: str  # 券商名稱
    type: str  # 券商類型 (simulator, shioaji, futu)
    environment: TradingEnvironment = TradingEnvironment.PAPER  # 交易環境
    api_key: Optional[str] = None  # API 金鑰
    api_secret: Optional[str] = None  # API 密鑰
    account_id: Optional[str] = None  # 帳戶 ID
    person_id: Optional[str] = None  # 身分證字號 (台灣券商需要)
    market: str = "TWN"  # 市場 (TWN, US, HK)
    order_timeout: int = 60  # 訂單超時時間 (秒)
    max_retry: int = 3  # 最大重試次數
    connection_timeout: int = 30  # 連接超時時間 (秒)
    enable_async: bool = True  # 是否啟用非同步模式
    log_level: str = "INFO"  # 日誌級別
    extra_params: Dict[str, Any] = field(default_factory=dict)  # 額外參數

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        result = asdict(self)
        result["environment"] = self.environment.value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BrokerConfig':
        """從字典創建配置"""
        # 處理環境列舉
        if "environment" in data and isinstance(data["environment"], str):
            data["environment"] = TradingEnvironment(data["environment"])
        return cls(**data)

    def load_api_keys(self, password: Optional[str] = None) -> bool:
        """
        從配置文件加載 API 金鑰

        Args:
            password (str, optional): 解密密碼

        Returns:
            bool: 是否加載成功
        """
        keys = load_api_keys(self.name, password)
        if not keys:
            return False

        self.api_key = keys.get("api_key")
        self.api_secret = keys.get("api_secret")
        self.account_id = keys.get("account_id") or self.account_id
        return True

    def validate(self) -> bool:
        """
        驗證配置是否有效

        Returns:
            bool: 配置是否有效
        """
        # 檢查必要欄位
        if not self.name or not self.type:
            logger.error("券商名稱和類型不能為空")
            return False

        # 檢查環境
        if self.environment == TradingEnvironment.LIVE:
            # 實盤交易需要 API 金鑰
            if not self.api_key or not self.api_secret:
                logger.error(f"實盤交易需要 API 金鑰和密鑰: {self.name}")
                return False

        # 檢查券商特定需求
        if self.type == "shioaji" and not self.person_id:
            logger.error("永豐證券需要身分證字號")
            return False

        return True


def load_broker_config(
    name: Optional[str] = None,
    config_file: str = "config/brokers.yaml",
    env_prefix: str = "BROKER_",
) -> Optional[BrokerConfig]:
    """
    加載券商配置

    Args:
        name (str, optional): 券商名稱，如果為 None 則使用環境變數 BROKER_NAME
        config_file (str): 配置文件路徑
        env_prefix (str): 環境變數前綴

    Returns:
        BrokerConfig: 券商配置
    """
    # 如果未指定券商名稱，則從環境變數獲取
    if name is None:
        name = os.getenv(f"{env_prefix}NAME")
        if not name:
            logger.error(f"未指定券商名稱，請設置環境變數 {env_prefix}NAME")
            return None

    # 檢查配置文件是否存在
    config_path = Path(config_file)
    if not config_path.exists():
        logger.error(f"配置文件不存在: {config_file}")
        return None

    try:
        # 讀取配置文件
        with open(config_path, "r", encoding="utf-8") as f:
            if config_path.suffix.lower() == ".yaml" or config_path.suffix.lower() == ".yml":
                config_data = yaml.safe_load(f)
            else:
                config_data = json.load(f)

        # 檢查券商配置是否存在
        if name not in config_data:
            logger.error(f"找不到券商配置: {name}")
            return None

        # 創建券商配置
        broker_config = BrokerConfig.from_dict(config_data[name])

        # 從環境變數覆蓋配置
        _override_config_from_env(broker_config, env_prefix)

        # 加載 API 金鑰
        api_key_password = os.getenv(f"{env_prefix}API_KEY_PASSWORD")
        broker_config.load_api_keys(api_key_password)

        # 驗證配置
        if not broker_config.validate():
            logger.error(f"券商配置無效: {name}")
            return None

        return broker_config
    except Exception as e:
        logger.exception(f"加載券商配置時發生錯誤: {e}")
        return None


def load_all_broker_configs(
    config_file: str = "config/brokers.yaml",
    env_prefix: str = "BROKER_",
) -> Dict[str, BrokerConfig]:
    """
    加載所有券商配置

    Args:
        config_file (str): 配置文件路徑
        env_prefix (str): 環境變數前綴

    Returns:
        Dict[str, BrokerConfig]: 券商配置字典
    """
    # 檢查配置文件是否存在
    config_path = Path(config_file)
    if not config_path.exists():
        logger.error(f"配置文件不存在: {config_file}")
        return {}

    try:
        # 讀取配置文件
        with open(config_path, "r", encoding="utf-8") as f:
            if config_path.suffix.lower() == ".yaml" or config_path.suffix.lower() == ".yml":
                config_data = yaml.safe_load(f)
            else:
                config_data = json.load(f)

        # 創建券商配置字典
        broker_configs = {}
        for name, data in config_data.items():
            broker_config = BrokerConfig.from_dict(data)
            broker_config.load_api_keys()
            if broker_config.validate():
                broker_configs[name] = broker_config
            else:
                logger.warning(f"券商配置無效: {name}")

        return broker_configs
    except Exception as e:
        logger.exception(f"加載券商配置時發生錯誤: {e}")
        return {}


def _override_config_from_env(config: BrokerConfig, prefix: str = "BROKER_"):
    """
    從環境變數覆蓋配置

    Args:
        config (BrokerConfig): 券商配置
        prefix (str): 環境變數前綴
    """
    # 映射環境變數名稱到配置欄位
    env_mapping = {
        f"{prefix}API_KEY": "api_key",
        f"{prefix}API_SECRET": "api_secret",
        f"{prefix}ACCOUNT_ID": "account_id",
        f"{prefix}PERSON_ID": "person_id",
        f"{prefix}ENVIRONMENT": "environment",
        f"{prefix}MARKET": "market",
        f"{prefix}ORDER_TIMEOUT": "order_timeout",
        f"{prefix}MAX_RETRY": "max_retry",
        f"{prefix}CONNECTION_TIMEOUT": "connection_timeout",
        f"{prefix}ENABLE_ASYNC": "enable_async",
        f"{prefix}LOG_LEVEL": "log_level",
    }

    # 從環境變數覆蓋配置
    for env_name, field_name in env_mapping.items():
        env_value = os.getenv(env_name)
        if env_value is not None:
            # 根據欄位類型轉換值
            if field_name == "environment":
                setattr(config, field_name, TradingEnvironment(env_value))
            elif field_name in ["order_timeout", "max_retry", "connection_timeout"]:
                setattr(config, field_name, int(env_value))
            elif field_name == "enable_async":
                setattr(config, field_name, env_value.lower() == "true")
            else:
                setattr(config, field_name, env_value)
