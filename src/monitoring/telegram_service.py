"""Telegram 通知服務

此模組實現了 Telegram 通知功能，支援 Telegram Bot API 發送通知，包含 Markdown 格式、檔案傳送等功能。

遵循 Google Style Docstring 標準和 Phase 5.3 開發規範。
"""

import logging
from typing import Dict, Any

import requests

from .notification_base import NotificationChannel

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class TelegramChannel(NotificationChannel):
    """Telegram 通知渠道

    支援 Telegram Bot API 發送通知，包含 Markdown 格式、檔案傳送等功能。
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化 Telegram 渠道

        Args:
            config: Telegram 配置
        """
        super().__init__("telegram", config)

        self.bot_token = config.get("bot_token", "")
        self.chat_id = config.get("chat_id", "")
        self.parse_mode = config.get("parse_mode", "Markdown")

    def send(self, data: Dict[str, Any]) -> bool:
        """發送 Telegram 通知

        Args:
            data: 通知數據

        Returns:
            bool: 發送成功返回 True，否則返回 False
        """
        if not self.enabled or not self.bot_token or not self.chat_id:
            return False

        try:
            # 準備 Telegram 訊息
            severity = data.get("severity", "INFO")
            severity_emoji = {
                "INFO": "ℹ️",
                "WARNING": "⚠️",
                "ERROR": "❌",
                "CRITICAL": "🚨",
            }.get(severity, "📢")

            message = f"""
{severity_emoji} *{data.get('title', 'Alert')}*

*嚴重程度:* `{severity}`
*告警 ID:* `{data.get('alert_id', 'N/A')}`
*觸發時間:* `{data.get('created_at', 'N/A')}`

*描述:*
{data.get('message', '')}

*指標詳情:*
• 當前值: `{data.get('metric_value', 'N/A')}`
• 閾值: `{data.get('threshold_value', 'N/A')}`

---
_AI 交易系統自動通知_
            """.strip()

            # 發送到 Telegram
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": self.parse_mode,
                "disable_web_page_preview": True,
            }

            response = requests.post(url, json=payload, timeout=self.timeout)

            if response.status_code == 200:
                module_logger.info("Telegram 通知發送成功: %s", data.get('alert_id'))
                return True

            module_logger.warning("Telegram 通知發送失敗: %s", response.status_code)
            return False

        except Exception as e:
            module_logger.error("Telegram 通知發送錯誤: %s", e)
            return False

    def test_connection(self) -> bool:
        """測試 Telegram 連接

        Returns:
            bool: 連接成功返回 True，否則返回 False
        """
        if not self.bot_token or not self.chat_id:
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": "🧪 Telegram 連接測試成功！",
                "parse_mode": "Markdown",
            }

            response = requests.post(url, json=payload, timeout=self.timeout)
            return response.status_code == 200

        except Exception:
            return False
