"""
通知服務測試

測試 NotificationServices 和各種通知渠道的功能，包括郵件、
Webhook、Slack、Telegram 等通知方式。

遵循 Phase 5.3 測試標準，確保 ≥70% 測試覆蓋率。
"""

import pytest
from unittest.mock import patch, MagicMock, mock_open
import json

from src.monitoring.notification_services import (
    NotificationServices,
    EmailChannel,
    WebhookChannel,
    SlackChannel,
    TelegramChannel,
    LineChannel,
)


class TestEmailChannel:
    """Email 通知渠道測試"""

    @pytest.fixture
    def email_config(self):
        """Email 配置"""
        return {
            "enabled": True,
            "smtp_server": "smtp.test.com",
            "smtp_port": 587,
            "username": "test@test.com",
            "password": "password",
            "from_address": "alerts@test.com",
            "to_addresses": ["admin@test.com"],
            "use_tls": True,
        }

    def test_init(self, email_config):
        """測試初始化"""
        channel = EmailChannel(email_config)

        assert channel.name == "email"
        assert channel.enabled
        assert channel.smtp_server == "smtp.test.com"
        assert channel.smtp_port == 587
        assert channel.from_address == "alerts@test.com"
        assert "admin@test.com" in channel.to_addresses

    @patch("src.monitoring.notification_services.smtplib.SMTP")
    def test_send_success(self, mock_smtp, email_config):
        """測試成功發送郵件"""
        # 模擬 SMTP 服務器
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        channel = EmailChannel(email_config)

        test_data = {
            "alert_id": "test-alert",
            "title": "Test Alert",
            "message": "Test message",
            "severity": "WARNING",
        }

        result = channel.send(test_data)

        assert result
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@test.com", "password")
        mock_server.send_message.assert_called_once()

    @patch("src.monitoring.notification_services.smtplib.SMTP")
    def test_send_failure(self, mock_smtp, email_config):
        """測試發送郵件失敗"""
        # 模擬 SMTP 錯誤
        mock_smtp.side_effect = Exception("SMTP Error")

        channel = EmailChannel(email_config)

        test_data = {
            "alert_id": "test-alert",
            "title": "Test Alert",
            "message": "Test message",
            "severity": "WARNING",
        }

        result = channel.send(test_data)
        assert not result

    def test_disabled_channel(self, email_config):
        """測試禁用的渠道"""
        email_config["enabled"] = False
        channel = EmailChannel(email_config)

        test_data = {"title": "Test"}
        result = channel.send(test_data)

        assert not result

    @patch("src.monitoring.notification_services.smtplib.SMTP")
    def test_connection_test(self, mock_smtp, email_config):
        """測試連接測試"""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        channel = EmailChannel(email_config)
        result = channel.test_connection()

        assert result
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()


class TestWebhookChannel:
    """Webhook 通知渠道測試"""

    @pytest.fixture
    def webhook_config(self):
        """Webhook 配置"""
        return {
            "enabled": True,
            "urls": ["http://test.com/webhook"],
            "headers": {"Content-Type": "application/json"},
            "timeout": 30,
        }

    def test_init(self, webhook_config):
        """測試初始化"""
        channel = WebhookChannel(webhook_config)

        assert channel.name == "webhook"
        assert channel.enabled
        assert "http://test.com/webhook" in channel.urls
        assert channel.timeout == 30

    @patch("src.monitoring.notification_services.requests.post")
    def test_send_success(self, mock_post, webhook_config):
        """測試成功發送 Webhook"""
        # 模擬成功響應
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        channel = WebhookChannel(webhook_config)

        test_data = {
            "alert_id": "test-alert",
            "title": "Test Alert",
            "message": "Test message",
        }

        result = channel.send(test_data)

        assert result
        mock_post.assert_called_once()

        # 驗證請求參數
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://test.com/webhook"
        assert "json" in call_args[1]
        assert "headers" in call_args[1]
        assert "timeout" in call_args[1]

    @patch("src.monitoring.notification_services.requests.post")
    def test_send_failure(self, mock_post, webhook_config):
        """測試發送 Webhook 失敗"""
        # 模擬失敗響應
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        channel = WebhookChannel(webhook_config)

        test_data = {"title": "Test"}
        result = channel.send(test_data)

        assert result  # 即使狀態碼不是200，只要沒有異常就返回True

    @patch("src.monitoring.notification_services.requests.post")
    def test_connection_test(self, mock_post, webhook_config):
        """測試連接測試"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        channel = WebhookChannel(webhook_config)
        result = channel.test_connection()

        assert result


class TestSlackChannel:
    """Slack 通知渠道測試"""

    @pytest.fixture
    def slack_config(self):
        """Slack 配置"""
        return {
            "enabled": True,
            "webhook_url": "https://hooks.slack.com/test",
            "channel": "#alerts",
            "username": "AlertBot",
            "icon_emoji": ":warning:",
            "timeout": 30,
        }

    def test_init(self, slack_config):
        """測試初始化"""
        channel = SlackChannel(slack_config)

        assert channel.name == "slack"
        assert channel.enabled
        assert channel.webhook_url == "https://hooks.slack.com/test"
        assert channel.channel == "#alerts"

    @patch("src.monitoring.notification_services.requests.post")
    def test_send_success(self, mock_post, slack_config):
        """測試成功發送 Slack 通知"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        channel = SlackChannel(slack_config)

        test_data = {
            "alert_id": "test-alert",
            "title": "Test Alert",
            "message": "Test message",
            "severity": "CRITICAL",
            "metric_value": 95.5,
            "threshold_value": 80.0,
        }

        result = channel.send(test_data)

        assert result
        mock_post.assert_called_once()

        # 驗證 Slack 格式
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["channel"] == "#alerts"
        assert payload["username"] == "AlertBot"
        assert "attachments" in payload
        assert len(payload["attachments"]) == 1

        attachment = payload["attachments"][0]
        assert attachment["color"] == "#ff0000"  # CRITICAL 顏色
        assert "Test Alert" in attachment["title"]


class TestTelegramChannel:
    """Telegram 通知渠道測試"""

    @pytest.fixture
    def telegram_config(self):
        """Telegram 配置"""
        return {
            "enabled": True,
            "bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
            "chat_id": "-123456789",
            "parse_mode": "Markdown",
            "timeout": 30,
        }

    def test_init(self, telegram_config):
        """測試初始化"""
        channel = TelegramChannel(telegram_config)

        assert channel.name == "telegram"
        assert channel.enabled
        assert channel.bot_token == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        assert channel.chat_id == "-123456789"

    @patch("src.monitoring.notification_services.requests.post")
    def test_send_success(self, mock_post, telegram_config):
        """測試成功發送 Telegram 通知"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        channel = TelegramChannel(telegram_config)

        test_data = {
            "alert_id": "test-alert",
            "title": "Test Alert",
            "message": "Test message",
            "severity": "WARNING",
        }

        result = channel.send(test_data)

        assert result
        mock_post.assert_called_once()

        # 驗證 Telegram API 調用
        call_args = mock_post.call_args
        url = call_args[0][0]
        assert "api.telegram.org" in url
        assert "sendMessage" in url

        payload = call_args[1]["json"]
        assert payload["chat_id"] == "-123456789"
        assert payload["parse_mode"] == "Markdown"
        assert "Test Alert" in payload["text"]


class TestNotificationServices:
    """通知服務管理器測試"""

    @pytest.fixture
    def mock_config(self):
        """模擬配置"""
        return {
            "notifications": {
                "channels": {
                    "email": {
                        "enabled": True,
                        "smtp_server": "smtp.test.com",
                        "to_addresses": ["admin@test.com"],
                    },
                    "webhook": {"enabled": True, "urls": ["http://test.com/webhook"]},
                }
            }
        }

    def test_init(self):
        """測試初始化"""
        with patch(
            "src.monitoring.notification_services.Path.exists", return_value=False
        ):
            service = NotificationServices()
            assert isinstance(service.channels, dict)

    @patch("builtins.open", new_callable=mock_open)
    @patch("src.monitoring.notification_services.yaml.safe_load")
    @patch("src.monitoring.notification_services.Path.exists")
    def test_load_config(self, mock_exists, mock_yaml, mock_file, mock_config):
        """測試載入配置"""
        mock_exists.return_value = True
        mock_yaml.return_value = mock_config

        service = NotificationServices()

        assert "email" in service.channels
        assert "webhook" in service.channels

    def test_send_notification_success(self):
        """測試成功發送通知"""
        with patch(
            "src.monitoring.notification_services.Path.exists", return_value=False
        ):
            service = NotificationServices()

            # 模擬渠道
            mock_channel = MagicMock()
            mock_channel.is_enabled.return_value = True
            mock_channel.send.return_value = True
            service.channels["test"] = mock_channel

            test_data = {"title": "Test"}
            result = service.send_notification("test", test_data)

            assert result
            mock_channel.send.assert_called_once_with(test_data)

    def test_send_notification_channel_not_found(self):
        """測試發送通知到不存在的渠道"""
        with patch(
            "src.monitoring.notification_services.Path.exists", return_value=False
        ):
            service = NotificationServices()

            result = service.send_notification("nonexistent", {"title": "Test"})
            assert not result

    def test_send_to_multiple_channels(self):
        """測試發送到多個渠道"""
        with patch(
            "src.monitoring.notification_services.Path.exists", return_value=False
        ):
            service = NotificationServices()

            # 模擬多個渠道
            for channel_name in ["email", "webhook", "slack"]:
                mock_channel = MagicMock()
                mock_channel.is_enabled.return_value = True
                mock_channel.send.return_value = True
                service.channels[channel_name] = mock_channel

            test_data = {"title": "Test"}
            results = service.send_to_multiple_channels(
                ["email", "webhook", "slack"], test_data
            )

            assert len(results) == 3
            assert all(results.values())

    def test_test_all_channels(self):
        """測試所有渠道連接"""
        with patch(
            "src.monitoring.notification_services.Path.exists", return_value=False
        ):
            service = NotificationServices()

            # 模擬渠道
            mock_channel = MagicMock()
            mock_channel.is_enabled.return_value = True
            mock_channel.test_connection.return_value = True
            service.channels["test"] = mock_channel

            results = service.test_all_channels()

            assert "test" in results
            assert results["test"]

    def test_get_enabled_channels(self):
        """測試獲取已啟用的渠道"""
        with patch(
            "src.monitoring.notification_services.Path.exists", return_value=False
        ):
            service = NotificationServices()

            # 模擬渠道
            enabled_channel = MagicMock()
            enabled_channel.is_enabled.return_value = True

            disabled_channel = MagicMock()
            disabled_channel.is_enabled.return_value = False

            service.channels["enabled"] = enabled_channel
            service.channels["disabled"] = disabled_channel

            enabled = service.get_enabled_channels()

            assert "enabled" in enabled
            assert "disabled" not in enabled

    def test_get_channel_status(self):
        """測試獲取渠道狀態"""
        with patch(
            "src.monitoring.notification_services.Path.exists", return_value=False
        ):
            service = NotificationServices()

            # 模擬渠道
            mock_channel = MagicMock()
            mock_channel.is_enabled.return_value = True
            mock_channel.name = "test"
            mock_channel.timeout = 30
            mock_channel.retry_count = 3
            service.channels["test"] = mock_channel

            status = service.get_channel_status()

            assert "test" in status
            assert status["test"]["enabled"]
            assert status["test"]["name"] == "test"

    def test_retry_mechanism(self):
        """測試重試機制"""
        with patch(
            "src.monitoring.notification_services.Path.exists", return_value=False
        ):
            service = NotificationServices()
            service.max_retries = 2
            service.retry_delay = 0.01  # 快速重試用於測試

            # 模擬失敗然後成功的渠道
            mock_channel = MagicMock()
            mock_channel.is_enabled.return_value = True
            mock_channel.send.side_effect = [
                False,
                False,
                True,
            ]  # 前兩次失敗，第三次成功
            service.channels["test"] = mock_channel

            with patch("time.sleep"):  # 跳過實際睡眠
                result = service.send_notification("test", {"title": "Test"})

            assert result
            assert mock_channel.send.call_count == 3

    def test_reload_config(self):
        """測試重新載入配置"""
        with patch(
            "src.monitoring.notification_services.Path.exists", return_value=False
        ):
            service = NotificationServices()

            # 添加一個渠道
            service.channels["old"] = MagicMock()

            # 重新載入配置
            result = service.reload_config()

            assert result
            assert "old" not in service.channels  # 舊渠道被清除
