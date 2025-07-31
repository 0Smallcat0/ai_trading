"""通知服務管理器

此模組實現了統一通知服務管理功能，管理所有通知渠道，提供統一的通知介面，
支援多通道同時發送、失敗重試機制等功能。

遵循 Google Style Docstring 標準和 Phase 5.3 開發規範。
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Any

import yaml

from .notification_base import NotificationChannel
from .email_service import EmailChannel
from .webhook_service import WebhookChannel
from .slack_service import SlackChannel
from .telegram_service import TelegramChannel
from .line_service import LineChannel

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class NotificationServices:
    """統一通知服務管理器

    管理所有通知渠道，提供統一的通知介面，支援多通道同時發送、
    失敗重試機制等功能。

    Attributes:
        channels: 通知渠道字典
        config: 通知配置
        retry_enabled: 是否啟用重試
        max_retries: 最大重試次數
    """

    def __init__(self, config_file: str = "config/monitoring.yaml"):
        """初始化通知服務

        Args:
            config_file: 配置檔案路徑

        Raises:
            Exception: 初始化失敗時拋出異常
        """
        try:
            self.config_file = Path(config_file)
            self.config = self._load_config()

            # 初始化通知渠道
            self.channels: Dict[str, NotificationChannel] = {}
            self._init_channels()

            # 重試配置
            self.retry_enabled = True
            self.max_retries = 3
            self.retry_delay = 5  # 秒

            module_logger.info("通知服務初始化成功")

        except Exception as e:
            module_logger.error("通知服務初始化失敗: %s", e)
            raise

    def _load_config(self) -> Dict[str, Any]:
        """載入配置檔案

        Returns:
            Dict[str, Any]: 配置字典
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    return config.get("notifications", {})
            else:
                module_logger.warning("配置檔案不存在: %s", self.config_file)
                return {}

        except Exception as e:
            module_logger.error("載入配置檔案失敗: %s", e)
            return {}

    def _init_channels(self) -> None:
        """初始化所有通知渠道"""
        channels_config = self.config.get("channels", {})

        # 渠道類別映射
        channel_classes = {
            "email": EmailChannel,
            "webhook": WebhookChannel,
            "slack": SlackChannel,
            "telegram": TelegramChannel,
            "line": LineChannel,
        }

        # 初始化各個渠道
        for channel_name, channel_class in channel_classes.items():
            if channel_name in channels_config:
                try:
                    self.channels[channel_name] = channel_class(
                        channels_config[channel_name]
                    )
                    module_logger.info("%s 通知渠道初始化成功", channel_name.title())
                except Exception as e:
                    module_logger.error(
                        "%s 通知渠道初始化失敗: %s", channel_name.title(), e
                    )

    def send_notification(self, channel_name: str, data: Dict[str, Any]) -> bool:
        """發送單一渠道通知

        Args:
            channel_name: 渠道名稱
            data: 通知數據

        Returns:
            bool: 發送成功返回 True，否則返回 False
        """
        if channel_name not in self.channels:
            module_logger.warning("通知渠道不存在: %s", channel_name)
            return False

        channel = self.channels[channel_name]

        if not channel.is_enabled():
            module_logger.debug("通知渠道未啟用: %s", channel_name)
            return False

        # 嘗試發送通知（含重試機制）
        for attempt in range(self.max_retries + 1):
            try:
                success = channel.send(data)

                if success:
                    return True
                if attempt < self.max_retries:
                    module_logger.warning(
                        "通知發送失敗，%s秒後重試 (%s/%s)",
                        self.retry_delay,
                        attempt + 1,
                        self.max_retries,
                    )
                    time.sleep(self.retry_delay)

            except Exception as e:
                module_logger.error("通知發送錯誤 (嘗試 %s): %s", attempt + 1, e)
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay)

        module_logger.error("通知發送最終失敗: %s", channel_name)
        return False

    def send_to_multiple_channels(
        self, channel_names: List[str], data: Dict[str, Any]
    ) -> Dict[str, bool]:
        """發送多渠道通知

        Args:
            channel_names: 渠道名稱列表
            data: 通知數據

        Returns:
            Dict[str, bool]: 各渠道發送結果
        """
        results = {}

        for channel_name in channel_names:
            results[channel_name] = self.send_notification(channel_name, data)

        return results

    def test_all_channels(self) -> Dict[str, bool]:
        """測試所有渠道連接

        Returns:
            Dict[str, bool]: 各渠道測試結果
        """
        results = {}

        for channel_name, channel in self.channels.items():
            if channel.is_enabled():
                try:
                    results[channel_name] = channel.test_connection()
                    if results[channel_name]:
                        module_logger.info("通知渠道測試成功: %s", channel_name)
                    else:
                        module_logger.warning("通知渠道測試失敗: %s", channel_name)
                except Exception as e:
                    module_logger.error("通知渠道測試錯誤: %s, %s", channel_name, e)
                    results[channel_name] = False
            else:
                results[channel_name] = False

        return results

    def get_enabled_channels(self) -> List[str]:
        """獲取已啟用的渠道列表

        Returns:
            List[str]: 已啟用的渠道名稱列表
        """
        return [name for name, channel in self.channels.items() if channel.is_enabled()]

    def get_channel_status(self) -> Dict[str, Dict[str, Any]]:
        """獲取所有渠道狀態

        Returns:
            Dict[str, Dict[str, Any]]: 渠道狀態資訊
        """
        status = {}

        for channel_name, channel in self.channels.items():
            status[channel_name] = {
                "enabled": channel.is_enabled(),
                "name": channel.name,
                "config": {
                    "timeout": channel.timeout,
                    "retry_count": channel.retry_count,
                },
            }

        return status

    def reload_config(self) -> bool:
        """重新載入配置

        Returns:
            bool: 重新載入成功返回 True，否則返回 False
        """
        try:
            self.config = self._load_config()
            self.channels.clear()
            self._init_channels()

            module_logger.info("通知服務配置重新載入成功")
            return True

        except Exception as e:
            module_logger.error("重新載入配置失敗: %s", e)
            return False
