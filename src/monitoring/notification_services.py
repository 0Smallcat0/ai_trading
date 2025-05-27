"""多通道通知服務 - 主要入口模組

此模組提供多通道通知服務的統一入口，包括：
- 統一通知介面
- 多通道管理
- 失敗重試機制

遵循 Google Style Docstring 標準和 Phase 5.3 開發規範。
"""

# 導入所有通知服務
from .notification_manager import NotificationServices
from .notification_base import NotificationChannel
from .email_service import EmailChannel
from .webhook_service import WebhookChannel
from .slack_service import SlackChannel
from .telegram_service import TelegramChannel
from .line_service import LineChannel

__all__ = [
    'NotificationServices',
    'NotificationChannel',
    'EmailChannel',
    'WebhookChannel',
    'SlackChannel',
    'TelegramChannel',
    'LineChannel',
]
