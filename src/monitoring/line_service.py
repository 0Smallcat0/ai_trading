"""Line 通知服務

此模組實現了 Line 通知功能，支援 Line Notify API 發送通知。

遵循 Google Style Docstring 標準和 Phase 5.3 開發規範。
"""

import logging
from typing import Dict, Any

import requests

from .notification_base import NotificationChannel

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class LineChannel(NotificationChannel):
    """Line 通知渠道

    支援 Line Notify API 發送通知。
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化 Line 渠道

        Args:
            config: Line 配置
        """
        super().__init__("line", config)

        self.access_token = config.get("access_token", "")
        self.api_url = "https://notify-api.line.me/api/notify"

    def send(self, data: Dict[str, Any]) -> bool:
        """發送 Line 通知

        Args:
            data: 通知數據

        Returns:
            bool: 發送成功返回 True，否則返回 False
        """
        if not self.enabled or not self.access_token:
            return False

        try:
            # 準備 Line 訊息
            severity = data.get("severity", "INFO")
            severity_emoji = {
                "INFO": "ℹ️",
                "WARNING": "⚠️",
                "ERROR": "❌",
                "CRITICAL": "🚨",
            }.get(severity, "📢")

            message = f"""
{severity_emoji} {data.get('title', 'Alert')}

嚴重程度: {severity}
告警 ID: {data.get('alert_id', 'N/A')}
觸發時間: {data.get('created_at', 'N/A')}

描述: {data.get('message', '')}

當前值: {data.get('metric_value', 'N/A')}
閾值: {data.get('threshold_value', 'N/A')}

--- AI 交易系統 ---
            """.strip()

            # 發送到 Line
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            payload = {"message": message}

            response = requests.post(
                self.api_url, headers=headers, data=payload, timeout=self.timeout
            )

            if response.status_code == 200:
                module_logger.info("Line 通知發送成功: %s", data.get("alert_id"))
                return True

            module_logger.warning("Line 通知發送失敗: %s", response.status_code)
            return False

        except Exception as e:
            module_logger.error("Line 通知發送錯誤: %s", e)
            return False

    def test_connection(self) -> bool:
        """測試 Line 連接

        Returns:
            bool: 連接成功返回 True，否則返回 False
        """
        if not self.access_token:
            return False

        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            payload = {"message": "🧪 Line 連接測試成功！"}

            response = requests.post(
                self.api_url, headers=headers, data=payload, timeout=self.timeout
            )

            return response.status_code == 200

        except Exception:
            return False
