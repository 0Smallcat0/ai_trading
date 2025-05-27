"""Slack 通知服務

此模組實現了 Slack 通知功能，支援 Slack Webhook 發送通知，包含頻道路由、@mention 功能等。

遵循 Google Style Docstring 標準和 Phase 5.3 開發規範。
"""

import logging
import time
from typing import Dict, Any

import requests

from .notification_base import NotificationChannel

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class SlackChannel(NotificationChannel):
    """Slack 通知渠道

    支援 Slack Webhook 發送通知，包含頻道路由、@mention 功能等。
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化 Slack 渠道

        Args:
            config: Slack 配置
        """
        super().__init__("slack", config)

        self.webhook_url = config.get("webhook_url", "")
        self.channel = config.get("channel", "#alerts")
        self.username = config.get("username", "AI Trading Bot")
        self.icon_emoji = config.get("icon_emoji", ":warning:")

    def send(self, data: Dict[str, Any]) -> bool:
        """發送 Slack 通知

        Args:
            data: 通知數據

        Returns:
            bool: 發送成功返回 True，否則返回 False
        """
        if not self.enabled or not self.webhook_url:
            return False

        try:
            # 準備 Slack 訊息
            severity = data.get("severity", "INFO")
            color = {
                "INFO": "#36a64f",
                "WARNING": "#ff9500",
                "ERROR": "#ff4500",
                "CRITICAL": "#ff0000",
            }.get(severity, "#808080")

            payload = {
                "channel": self.channel,
                "username": self.username,
                "icon_emoji": self.icon_emoji,
                "attachments": [
                    {
                        "color": color,
                        "title": f"🚨 {data.get('title', 'Alert')}",
                        "text": data.get("message", ""),
                        "fields": [
                            {"title": "嚴重程度", "value": severity, "short": True},
                            {
                                "title": "告警 ID",
                                "value": data.get("alert_id", "N/A"),
                                "short": True,
                            },
                            {
                                "title": "當前值",
                                "value": str(data.get("metric_value", "N/A")),
                                "short": True,
                            },
                            {
                                "title": "閾值",
                                "value": str(data.get("threshold_value", "N/A")),
                                "short": True,
                            },
                        ],
                        "footer": "AI 交易系統",
                        "ts": int(time.time()),
                    }
                ],
            }

            # 發送到 Slack
            response = requests.post(
                self.webhook_url, json=payload, timeout=self.timeout
            )

            if response.status_code == 200:
                module_logger.info("Slack 通知發送成功: %s", data.get("alert_id"))
                return True

            module_logger.warning("Slack 通知發送失敗: %s", response.status_code)
            return False

        except Exception as e:
            module_logger.error("Slack 通知發送錯誤: %s", e)
            return False

    def test_connection(self) -> bool:
        """測試 Slack 連接

        Returns:
            bool: 連接成功返回 True，否則返回 False
        """
        if not self.webhook_url:
            return False

        test_payload = {
            "channel": self.channel,
            "username": self.username,
            "text": "🧪 Slack 連接測試成功！",
            "icon_emoji": ":white_check_mark:",
        }

        try:
            response = requests.post(
                self.webhook_url, json=test_payload, timeout=self.timeout
            )

            return response.status_code == 200

        except Exception:
            return False
