"""資料收集配置管理模組

配置管理器職責分工：
- CollectionConfigManager: 資料收集配置 (本檔案)
- ConfigManager: 通用系統配置 (src/utils/config_manager.py)
- ConfigManagementService: 圖表視覺化配置 (src/core/visualization/config_management.py)
詳見：docs/開發者指南/配置管理器使用指南.md

此模組負責管理資料收集系統的配置，包括：
- 預設配置定義
- 配置檔案載入和儲存
- 配置驗證

Example:
    >>> config_manager = CollectionConfigManager()
    >>> config = config_manager.load_config("config.json")
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from src.config import DEFAULT_SYMBOLS

logger = logging.getLogger(__name__)


class CollectionConfigManager:
    """資料收集配置管理器
    
    負責管理資料收集系統的所有配置相關操作。
    """

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """獲取預設配置
        
        Returns:
            Dict[str, Any]: 預設配置字典
        """
        return {
            "symbols": DEFAULT_SYMBOLS,
            "collectors": {
                "market_data": {
                    "enabled": True,
                    "source": "yahoo",
                    "use_cache": True,
                    "cache_expiry_days": 1,
                    "schedule": {
                        "daily": "18:00",
                        "minute": {
                            "enabled": True,
                            "interval": 60,  # 分鐘
                            "symbols": ["2330.TW", "2317.TW"]
                        }
                    }
                },
                "realtime_quote": {
                    "enabled": False,
                    "source": "yahoo",
                    "symbols": ["2330.TW", "2317.TW"]
                },
                "financial_statement": {
                    "enabled": True,
                    "source": "yahoo",
                    "use_cache": True,
                    "cache_expiry_days": 30,
                    "schedule": {
                        "daily": "19:00"
                    }
                },
                "news_sentiment": {
                    "enabled": True,
                    "source": "mcp",
                    "use_cache": True,
                    "cache_expiry_days": 1,
                    "sentiment_model": "simple",
                    "schedule": {
                        "daily": "20:00"
                    }
                }
            }
        }

    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """載入配置
        
        Args:
            config_path: 配置檔案路徑，如果為 None 則使用預設配置
            
        Returns:
            Dict[str, Any]: 配置字典
        """
        default_config = self.get_default_config()
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                logger.info("已從 %s 載入配置", config_path)
                return config
            except Exception as e:
                logger.error("載入配置檔案 %s 時發生錯誤: %s", config_path, e)
                return default_config
        else:
            logger.info("使用預設配置")
            return default_config

    def save_config(self, config: Dict[str, Any], config_path: str) -> bool:
        """儲存配置到檔案
        
        Args:
            config: 要儲存的配置
            config_path: 配置檔案路徑
            
        Returns:
            bool: 是否儲存成功
        """
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            logger.info("已儲存配置到 %s", config_path)
            return True
        except Exception as e:
            logger.error("儲存配置到 %s 時發生錯誤: %s", config_path, e)
            return False

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """驗證配置的有效性
        
        Args:
            config: 要驗證的配置
            
        Returns:
            bool: 配置是否有效
        """
        required_keys = ["symbols", "collectors"]
        
        # 檢查必要的鍵
        for key in required_keys:
            if key not in config:
                logger.error("配置缺少必要的鍵: %s", key)
                return False
        
        # 檢查 symbols 是否為列表
        if not isinstance(config["symbols"], list):
            logger.error("symbols 必須是列表")
            return False
        
        # 檢查 collectors 是否為字典
        if not isinstance(config["collectors"], dict):
            logger.error("collectors 必須是字典")
            return False
        
        return True
