"""
交易通知服務 (Trade Notification Service)

此模組提供交易通知的核心服務功能，包括：
- 交易執行通知
- 訂單狀態更新通知
- 成交確認通知
- 交易摘要報告
- 通知偏好管理

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥8.5/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable

from ..broker.order_execution_service import ExecutionStatus


logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """通知通道枚舉"""
    WEBSOCKET = "websocket"
    EMAIL = "email"
    SMS = "sms"
    SYSTEM = "system"
    PUSH = "push"


class NotificationPriority(Enum):
    """通知優先級枚舉"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TradeNotification:
    """
    交易通知類別
    
    Attributes:
        notification_id: 通知唯一識別碼
        notification_type: 通知類型
        priority: 優先級
        title: 標題
        message: 訊息內容
        data: 相關資料
        channels: 發送通道
        user_id: 目標用戶ID
        created_at: 創建時間
        sent_at: 發送時間
        read_at: 閱讀時間
    """

    def __init__(
        self,
        notification_type: str,
        title: str,
        message: str,
        data: Dict[str, Any],
        user_id: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: Optional[List[NotificationChannel]] = None
    ):
        """
        初始化交易通知
        
        Args:
            notification_type: 通知類型
            title: 標題
            message: 訊息內容
            data: 相關資料
            user_id: 目標用戶ID
            priority: 優先級
            channels: 發送通道列表
        """
        self.notification_id = f"trade_notif_{int(datetime.now().timestamp() * 1000)}"
        self.notification_type = notification_type
        self.priority = priority
        self.title = title
        self.message = message
        self.data = data
        self.channels = channels or [NotificationChannel.WEBSOCKET]
        self.user_id = user_id
        self.created_at = datetime.now()
        self.sent_at: Optional[datetime] = None
        self.read_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式
        
        Returns:
            Dict[str, Any]: 通知資訊字典
        """
        return {
            "notification_id": self.notification_id,
            "notification_type": self.notification_type,
            "priority": self.priority.value,
            "title": self.title,
            "message": self.message,
            "data": self.data,
            "channels": [channel.value for channel in self.channels],
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None
        }


class TradeNotificationError(Exception):
    """交易通知錯誤"""
    pass


class TradeNotificationService:
    """
    交易通知服務
    
    提供交易相關的通知功能，包括訂單狀態更新、
    成交確認、交易摘要等通知。
    
    Attributes:
        _notifications: 通知歷史記錄
        _user_preferences: 用戶通知偏好
        _channel_handlers: 通道處理器
        _notification_callbacks: 通知回調函數列表
    """

    def __init__(self):
        """
        初始化交易通知服務
        """
        self._notifications: List[TradeNotification] = []
        self._user_preferences: Dict[str, Dict[str, Any]] = {}
        self._channel_handlers: Dict[NotificationChannel, Callable] = {}
        self._notification_callbacks: List[Callable[[TradeNotification], None]] = []
        
        # 初始化通道處理器
        self._init_channel_handlers()
        
        logger.info("交易通知服務初始化成功")

    def send_order_notification(
        self,
        order_id: str,
        status: ExecutionStatus,
        order_data: Dict[str, Any],
        user_id: str
    ) -> str:
        """
        發送訂單通知
        
        Args:
            order_id: 訂單ID
            status: 執行狀態
            order_data: 訂單資料
            user_id: 用戶ID
            
        Returns:
            str: 通知ID
            
        Raises:
            TradeNotificationError: 發送失敗時拋出
        """
        try:
            # 根據狀態生成通知內容
            title, message, priority = self._generate_order_notification_content(
                order_id, status, order_data
            )
            
            notification = TradeNotification(
                notification_type="order_update",
                title=title,
                message=message,
                data={
                    "order_id": order_id,
                    "status": status.value,
                    "order_data": order_data
                },
                user_id=user_id,
                priority=priority
            )
            
            return self._send_notification(notification)
            
        except Exception as e:
            logger.error("發送訂單通知失敗: %s", e)
            raise TradeNotificationError("訂單通知發送失敗") from e

    def send_trade_execution_notification(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float,
        user_id: str,
        **metadata
    ) -> str:
        """
        發送交易執行通知
        
        Args:
            symbol: 股票代號
            action: 交易動作
            quantity: 數量
            price: 價格
            user_id: 用戶ID
            **metadata: 額外資訊
            
        Returns:
            str: 通知ID
        """
        try:
            title = f"交易執行確認 - {symbol}"
            message = f"{action.upper()} {quantity} 股 {symbol} @ ${price:.2f}"
            
            notification = TradeNotification(
                notification_type="trade_execution",
                title=title,
                message=message,
                data={
                    "symbol": symbol,
                    "action": action,
                    "quantity": quantity,
                    "price": price,
                    "total_amount": quantity * price,
                    "metadata": metadata
                },
                user_id=user_id,
                priority=NotificationPriority.HIGH
            )
            
            return self._send_notification(notification)
            
        except Exception as e:
            logger.error("發送交易執行通知失敗: %s", e)
            raise TradeNotificationError("交易執行通知發送失敗") from e

    def send_daily_summary(self, user_id: str, summary_data: Dict[str, Any]) -> str:
        """
        發送每日交易摘要
        
        Args:
            user_id: 用戶ID
            summary_data: 摘要資料
            
        Returns:
            str: 通知ID
        """
        try:
            title = f"每日交易摘要 - {datetime.now().strftime('%Y-%m-%d')}"
            
            # 生成摘要訊息
            total_trades = summary_data.get("total_trades", 0)
            total_pnl = summary_data.get("total_pnl", 0)
            message = f"今日共執行 {total_trades} 筆交易，總損益: ${total_pnl:.2f}"
            
            notification = TradeNotification(
                notification_type="daily_summary",
                title=title,
                message=message,
                data=summary_data,
                user_id=user_id,
                priority=NotificationPriority.NORMAL,
                channels=[NotificationChannel.EMAIL, NotificationChannel.SYSTEM]
            )
            
            return self._send_notification(notification)
            
        except Exception as e:
            logger.error("發送每日摘要失敗: %s", e)
            raise TradeNotificationError("每日摘要發送失敗") from e

    def set_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any]
    ) -> None:
        """
        設定用戶通知偏好
        
        Args:
            user_id: 用戶ID
            preferences: 偏好設定
        """
        self._user_preferences[user_id] = preferences
        logger.info("用戶 %s 通知偏好已更新", user_id)

    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        獲取用戶通知偏好
        
        Args:
            user_id: 用戶ID
            
        Returns:
            Dict[str, Any]: 偏好設定
        """
        return self._user_preferences.get(user_id, self._get_default_preferences())

    def get_notifications(
        self,
        user_id: str,
        limit: int = 50,
        unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        獲取用戶通知列表
        
        Args:
            user_id: 用戶ID
            limit: 限制數量
            unread_only: 是否只返回未讀通知
            
        Returns:
            List[Dict[str, Any]]: 通知列表
        """
        notifications = []
        
        for notification in reversed(self._notifications):
            if notification.user_id != user_id:
                continue
            
            if unread_only and notification.read_at is not None:
                continue
            
            notifications.append(notification.to_dict())
            
            if len(notifications) >= limit:
                break
        
        return notifications

    def mark_as_read(self, notification_id: str, user_id: str) -> bool:
        """
        標記通知為已讀
        
        Args:
            notification_id: 通知ID
            user_id: 用戶ID
            
        Returns:
            bool: 標記是否成功
        """
        for notification in self._notifications:
            if (notification.notification_id == notification_id and 
                notification.user_id == user_id):
                notification.read_at = datetime.now()
                logger.info("通知 %s 已標記為已讀", notification_id)
                return True
        
        logger.warning("通知 %s 不存在或無權限", notification_id)
        return False

    def register_channel_handler(
        self,
        channel: NotificationChannel,
        handler: Callable[[TradeNotification], bool]
    ) -> None:
        """
        註冊通道處理器
        
        Args:
            channel: 通知通道
            handler: 處理器函數
        """
        self._channel_handlers[channel] = handler
        logger.info("已註冊 %s 通道處理器", channel.value)

    def add_notification_callback(
        self,
        callback: Callable[[TradeNotification], None]
    ) -> None:
        """
        添加通知回調函數
        
        Args:
            callback: 回調函數
        """
        self._notification_callbacks.append(callback)

    def _send_notification(self, notification: TradeNotification) -> str:
        """
        發送通知
        
        Args:
            notification: 通知物件
            
        Returns:
            str: 通知ID
        """
        try:
            # 檢查用戶偏好
            preferences = self.get_user_preferences(notification.user_id)
            enabled_channels = self._filter_channels_by_preferences(
                notification.channels, preferences
            )
            
            # 發送到各個通道
            for channel in enabled_channels:
                if channel in self._channel_handlers:
                    try:
                        success = self._channel_handlers[channel](notification)
                        if success:
                            logger.info(
                                "通知 %s 已發送到 %s 通道",
                                notification.notification_id,
                                channel.value
                            )
                    except Exception as e:
                        logger.error(
                            "發送通知到 %s 通道失敗: %s",
                            channel.value,
                            e
                        )
            
            # 記錄通知
            notification.sent_at = datetime.now()
            self._notifications.append(notification)
            
            # 限制通知歷史數量
            if len(self._notifications) > 1000:
                self._notifications = self._notifications[-1000:]
            
            # 觸發回調
            for callback in self._notification_callbacks:
                try:
                    callback(notification)
                except Exception as e:
                    logger.error("執行通知回調時發生錯誤: %s", e)
            
            return notification.notification_id
            
        except Exception as e:
            logger.error("發送通知失敗: %s", e)
            raise

    def _generate_order_notification_content(
        self,
        order_id: str,
        status: ExecutionStatus,
        order_data: Dict[str, Any]
    ) -> tuple:
        """
        生成訂單通知內容
        
        Args:
            order_id: 訂單ID
            status: 執行狀態
            order_data: 訂單資料
            
        Returns:
            tuple: (標題, 訊息, 優先級)
        """
        symbol = order_data.get("request", {}).get("symbol", "Unknown")
        action = order_data.get("request", {}).get("action", "Unknown")
        quantity = order_data.get("request", {}).get("quantity", 0)
        
        if status == ExecutionStatus.SUBMITTED:
            title = f"訂單已提交 - {symbol}"
            message = f"{action.upper()} {quantity} 股 {symbol} 訂單已提交"
            priority = NotificationPriority.NORMAL
        elif status == ExecutionStatus.FILLED:
            title = f"訂單已成交 - {symbol}"
            message = f"{action.upper()} {quantity} 股 {symbol} 訂單已完全成交"
            priority = NotificationPriority.HIGH
        elif status == ExecutionStatus.CANCELLED:
            title = f"訂單已取消 - {symbol}"
            message = f"{action.upper()} {quantity} 股 {symbol} 訂單已取消"
            priority = NotificationPriority.NORMAL
        elif status == ExecutionStatus.REJECTED:
            title = f"訂單被拒絕 - {symbol}"
            message = f"{action.upper()} {quantity} 股 {symbol} 訂單被拒絕"
            priority = NotificationPriority.HIGH
        else:
            title = f"訂單狀態更新 - {symbol}"
            message = f"{action.upper()} {quantity} 股 {symbol} 訂單狀態: {status.value}"
            priority = NotificationPriority.NORMAL
        
        return title, message, priority

    def _filter_channels_by_preferences(
        self,
        channels: List[NotificationChannel],
        preferences: Dict[str, Any]
    ) -> List[NotificationChannel]:
        """
        根據用戶偏好篩選通道
        
        Args:
            channels: 原始通道列表
            preferences: 用戶偏好
            
        Returns:
            List[NotificationChannel]: 篩選後的通道列表
        """
        enabled_channels = []
        
        for channel in channels:
            channel_key = f"enable_{channel.value}"
            if preferences.get(channel_key, True):  # 預設啟用
                enabled_channels.append(channel)
        
        return enabled_channels

    def _get_default_preferences(self) -> Dict[str, Any]:
        """
        獲取預設通知偏好
        
        Returns:
            Dict[str, Any]: 預設偏好設定
        """
        return {
            "enable_websocket": True,
            "enable_email": True,
            "enable_sms": False,
            "enable_system": True,
            "enable_push": False,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
            "min_priority": "normal"
        }

    def _init_channel_handlers(self) -> None:
        """
        初始化通道處理器
        """
        # WebSocket 處理器 (預設實作)
        def websocket_handler(notification: TradeNotification) -> bool:
            try:
                # 這裡應該整合實際的 WebSocket 管理器
                logger.info("WebSocket 通知: %s", notification.title)
                return True
            except Exception as e:
                logger.error("WebSocket 通知發送失敗: %s", e)
                return False
        
        # 系統通知處理器
        def system_handler(notification: TradeNotification) -> bool:
            try:
                logger.info("系統通知: %s - %s", notification.title, notification.message)
                return True
            except Exception as e:
                logger.error("系統通知發送失敗: %s", e)
                return False
        
        self._channel_handlers[NotificationChannel.WEBSOCKET] = websocket_handler
        self._channel_handlers[NotificationChannel.SYSTEM] = system_handler
