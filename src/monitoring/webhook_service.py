"""Webhook 通知服務

此模組實現了 Webhook 通知功能，支援 HTTP POST 請求發送通知到指定的 Webhook URL。

遵循 Google Style Docstring 標準和 Phase 5.3 開發規範。
"""

import logging
from datetime import datetime
from typing import Dict, Any

import requests

from .notification_base import NotificationChannel

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class WebhookChannel(NotificationChannel):
    """Webhook 通知渠道

    支援 HTTP POST 請求發送通知到指定的 Webhook URL。
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化 Webhook 渠道

        Args:
            config: Webhook 配置
        """
        super().__init__("webhook", config)

        self.urls = config.get("urls", [])
        self.headers = config.get("headers", {"Content-Type": "application/json"})

    def send(self, data: Dict[str, Any]) -> bool:
        """發送 Webhook 通知

        Args:
            data: 通知數據

        Returns:
            bool: 發送成功返回 True，否則返回 False
        """
        if not self.enabled or not self.urls:
            return False

        success_count = 0

        for url in self.urls:
            try:
                # 準備 Webhook 負載
                payload = {
                    "timestamp": datetime.now().isoformat(),
                    "source": "ai-trading-system",
                    "alert": data,
                }

                # 發送 POST 請求
                response = requests.post(
                    url, json=payload, headers=self.headers, timeout=self.timeout
                )

                if response.status_code == 200:
                    success_count += 1
                    module_logger.info("Webhook 通知發送成功: %s", url)
                else:
                    module_logger.warning(
                        "Webhook 通知發送失敗: %s, 狀態碼: %s",
                        url,
                        response.status_code,
                    )

            except Exception as e:
                module_logger.error("Webhook 通知發送錯誤: %s, 錯誤: %s", url, e)

        return success_count > 0

    def test_connection(self) -> bool:
        """測試 Webhook 連接

        Returns:
            bool: 連接成功返回 True，否則返回 False
        """
        if not self.urls:
            return False

        test_payload = {
            "timestamp": datetime.now().isoformat(),
            "source": "ai-trading-system",
            "test": True,
            "message": "Webhook 連接測試",
        }

        for url in self.urls:
            try:
                response = requests.post(
                    url, json=test_payload, headers=self.headers, timeout=self.timeout
                )

                if response.status_code != 200:
                    return False

            except Exception:
                return False

        return True
