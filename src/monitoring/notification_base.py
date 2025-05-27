"""通知渠道基礎類別

此模組定義了所有通知渠道的基礎介面和通用功能。

遵循 Google Style Docstring 標準和 Phase 5.3 開發規範。
"""

import logging
from typing import Dict, Any

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class NotificationChannel:
    """通知渠道基類

    定義所有通知渠道的通用介面和基本功能。
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        """初始化通知渠道

        Args:
            name: 渠道名稱
            config: 渠道配置
        """
        self.name = name
        self.config = config
        self.enabled = config.get("enabled", False)
        self.retry_count = config.get("retry_count", 3)
        self.timeout = config.get("timeout", 30)

    def send(self, data: Dict[str, Any]) -> bool:
        """發送通知

        Args:
            data: 通知數據

        Returns:
            bool: 發送成功返回 True，否則返回 False
        """
        raise NotImplementedError("子類必須實現 send 方法")

    def is_enabled(self) -> bool:
        """檢查渠道是否啟用

        Returns:
            bool: 啟用返回 True，否則返回 False
        """
        return self.enabled

    def test_connection(self) -> bool:
        """測試連接

        Returns:
            bool: 連接成功返回 True，否則返回 False
        """
        return True
