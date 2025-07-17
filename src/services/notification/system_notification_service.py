"""
系統監控通知服務 (System Notification Service)

此模組提供系統監控通知的核心服務功能，包括：
- 系統狀態變更通知
- 服務健康檢查警報
- 性能監控警報
- 系統維護通知
- 錯誤日誌警報

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥8.5/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable

from .trade_notification_service import (
    TradeNotification,
    NotificationChannel,
    NotificationPriority
)


logger = logging.getLogger(__name__)


class SystemStatus(Enum):
    """系統狀態枚舉"""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    ERROR = "error"


class ComponentType(Enum):
    """組件類型枚舉"""
    DATABASE = "database"
    BROKER_API = "broker_api"
    WEB_SERVER = "web_server"
    TRADING_ENGINE = "trading_engine"
    RISK_MONITOR = "risk_monitor"
    DATA_FEED = "data_feed"
    NOTIFICATION = "notification"


class SystemEvent:
    """
    系統事件類別
    
    Attributes:
        event_id: 事件唯一識別碼
        component: 組件名稱
        component_type: 組件類型
        event_type: 事件類型
        status: 系統狀態
        message: 事件訊息
        details: 詳細資訊
        timestamp: 發生時間
        resolved_at: 解決時間
    """

    def __init__(
        self,
        component: str,
        component_type: ComponentType,
        event_type: str,
        status: SystemStatus,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化系統事件
        
        Args:
            component: 組件名稱
            component_type: 組件類型
            event_type: 事件類型
            status: 系統狀態
            message: 事件訊息
            details: 詳細資訊
        """
        self.event_id = f"sys_event_{int(datetime.now().timestamp() * 1000)}"
        self.component = component
        self.component_type = component_type
        self.event_type = event_type
        self.status = status
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()
        self.resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式
        
        Returns:
            Dict[str, Any]: 系統事件資訊字典
        """
        return {
            "event_id": self.event_id,
            "component": self.component,
            "component_type": self.component_type.value,
            "event_type": self.event_type,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


class SystemNotificationError(Exception):
    """系統通知錯誤"""
    pass


class SystemNotificationService:
    """
    系統監控通知服務
    
    提供系統監控相關的通知功能，包括狀態變更、
    健康檢查、性能警報等。
    
    Attributes:
        _system_events: 系統事件歷史
        _component_status: 組件狀態記錄
        _notification_callbacks: 通知回調函數列表
        _notification_service: 通知服務 (可選)
    """

    def __init__(self, notification_service=None):
        """
        初始化系統監控通知服務
        
        Args:
            notification_service: 通知服務實例 (可選)
        """
        self._system_events: List[SystemEvent] = []
        self._component_status: Dict[str, SystemStatus] = {}
        self._notification_callbacks: List[Callable[[SystemEvent], None]] = []
        self._notification_service = notification_service
        
        logger.info("系統監控通知服務初始化成功")

    def report_component_status(
        self,
        component: str,
        component_type: ComponentType,
        status: SystemStatus,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        報告組件狀態
        
        Args:
            component: 組件名稱
            component_type: 組件類型
            status: 系統狀態
            message: 狀態訊息
            details: 詳細資訊
            user_id: 用戶ID (可選)
            
        Returns:
            str: 事件ID
        """
        try:
            # 檢查狀態是否變更
            previous_status = self._component_status.get(component)
            status_changed = previous_status != status
            
            # 創建系統事件
            event = SystemEvent(
                component=component,
                component_type=component_type,
                event_type="status_change" if status_changed else "status_update",
                status=status,
                message=message,
                details=details
            )
            
            # 記錄事件
            self._system_events.append(event)
            self._component_status[component] = status
            
            # 限制事件歷史數量
            if len(self._system_events) > 1000:
                self._system_events = self._system_events[-1000:]
            
            # 發送通知 (僅在狀態變更或錯誤時)
            if status_changed or status in [SystemStatus.ERROR, SystemStatus.OFFLINE]:
                self._send_system_notification(event, user_id)
            
            # 觸發回調
            for callback in self._notification_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error("執行系統通知回調時發生錯誤: %s", e)
            
            logger.info("組件 %s 狀態已更新: %s", component, status.value)
            return event.event_id
            
        except Exception as e:
            logger.error("報告組件狀態失敗: %s", e)
            raise SystemNotificationError("組件狀態報告失敗") from e

    def report_performance_alert(
        self,
        component: str,
        metric_name: str,
        current_value: float,
        threshold: float,
        message: str,
        user_id: Optional[str] = None
    ) -> str:
        """
        報告性能警報
        
        Args:
            component: 組件名稱
            metric_name: 指標名稱
            current_value: 當前值
            threshold: 閾值
            message: 警報訊息
            user_id: 用戶ID (可選)
            
        Returns:
            str: 事件ID
        """
        try:
            event = SystemEvent(
                component=component,
                component_type=ComponentType.WEB_SERVER,  # 預設類型
                event_type="performance_alert",
                status=SystemStatus.DEGRADED,
                message=message,
                details={
                    "metric_name": metric_name,
                    "current_value": current_value,
                    "threshold": threshold,
                    "exceeded_by": current_value - threshold
                }
            )
            
            # 記錄事件
            self._system_events.append(event)
            
            # 發送通知
            self._send_system_notification(event, user_id)
            
            logger.warning("性能警報: %s - %s", component, message)
            return event.event_id
            
        except Exception as e:
            logger.error("報告性能警報失敗: %s", e)
            raise SystemNotificationError("性能警報報告失敗") from e

    def report_error(
        self,
        component: str,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        報告系統錯誤
        
        Args:
            component: 組件名稱
            error_type: 錯誤類型
            error_message: 錯誤訊息
            stack_trace: 堆疊追蹤 (可選)
            user_id: 用戶ID (可選)
            
        Returns:
            str: 事件ID
        """
        try:
            event = SystemEvent(
                component=component,
                component_type=ComponentType.WEB_SERVER,  # 預設類型
                event_type="error",
                status=SystemStatus.ERROR,
                message=f"{error_type}: {error_message}",
                details={
                    "error_type": error_type,
                    "error_message": error_message,
                    "stack_trace": stack_trace
                }
            )
            
            # 記錄事件
            self._system_events.append(event)
            
            # 發送通知
            self._send_system_notification(event, user_id)
            
            logger.error("系統錯誤: %s - %s", component, error_message)
            return event.event_id
            
        except Exception as e:
            logger.error("報告系統錯誤失敗: %s", e)
            raise SystemNotificationError("系統錯誤報告失敗") from e

    def send_maintenance_notification(
        self,
        title: str,
        message: str,
        start_time: datetime,
        end_time: datetime,
        affected_components: List[str],
        user_id: Optional[str] = None
    ) -> str:
        """
        發送維護通知
        
        Args:
            title: 通知標題
            message: 通知訊息
            start_time: 開始時間
            end_time: 結束時間
            affected_components: 受影響的組件
            user_id: 用戶ID (可選)
            
        Returns:
            str: 事件ID
        """
        try:
            event = SystemEvent(
                component="system",
                component_type=ComponentType.WEB_SERVER,
                event_type="maintenance",
                status=SystemStatus.MAINTENANCE,
                message=message,
                details={
                    "title": title,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "affected_components": affected_components,
                    "duration_hours": (end_time - start_time).total_seconds() / 3600
                }
            )
            
            # 記錄事件
            self._system_events.append(event)
            
            # 發送通知
            if self._notification_service and user_id:
                notification = TradeNotification(
                    notification_type="system_maintenance",
                    title=title,
                    message=message,
                    data=event.to_dict(),
                    user_id=user_id,
                    priority=NotificationPriority.HIGH,
                    channels=[NotificationChannel.EMAIL, NotificationChannel.WEBSOCKET]
                )
                
                self._notification_service._send_notification(notification)
            
            logger.info("維護通知已發送: %s", title)
            return event.event_id
            
        except Exception as e:
            logger.error("發送維護通知失敗: %s", e)
            raise SystemNotificationError("維護通知發送失敗") from e

    def get_system_status(self) -> Dict[str, Any]:
        """
        獲取系統狀態摘要
        
        Returns:
            Dict[str, Any]: 系統狀態摘要
        """
        try:
            # 計算整體系統狀態
            overall_status = self._calculate_overall_status()
            
            # 統計各組件狀態
            component_summary = {}
            for component, status in self._component_status.items():
                component_summary[component] = status.value
            
            # 獲取最近事件
            recent_events = self.get_recent_events(hours=1)
            
            return {
                "overall_status": overall_status.value,
                "component_status": component_summary,
                "total_components": len(self._component_status),
                "healthy_components": sum(
                    1 for status in self._component_status.values()
                    if status == SystemStatus.ONLINE
                ),
                "recent_events_count": len(recent_events),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("獲取系統狀態失敗: %s", e)
            return {
                "overall_status": SystemStatus.ERROR.value,
                "error": str(e)
            }

    def get_recent_events(
        self,
        hours: int = 24,
        component: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        獲取最近的系統事件
        
        Args:
            hours: 時間範圍(小時)
            component: 組件篩選
            event_type: 事件類型篩選
            
        Returns:
            List[Dict[str, Any]]: 系統事件列表
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_events = []
        for event in self._system_events:
            if event.timestamp < cutoff_time:
                continue
            
            if component and event.component != component:
                continue
            
            if event_type and event.event_type != event_type:
                continue
            
            filtered_events.append(event.to_dict())
        
        return sorted(filtered_events, key=lambda x: x["timestamp"], reverse=True)

    def resolve_event(self, event_id: str) -> bool:
        """
        標記事件為已解決
        
        Args:
            event_id: 事件ID
            
        Returns:
            bool: 標記是否成功
        """
        for event in self._system_events:
            if event.event_id == event_id:
                event.resolved_at = datetime.now()
                logger.info("事件 %s 已標記為已解決", event_id)
                return True
        
        logger.warning("事件 %s 不存在", event_id)
        return False

    def add_notification_callback(self, callback: Callable[[SystemEvent], None]) -> None:
        """
        添加通知回調函數
        
        Args:
            callback: 回調函數，接收系統事件
        """
        self._notification_callbacks.append(callback)

    def _send_system_notification(
        self,
        event: SystemEvent,
        user_id: Optional[str] = None
    ) -> None:
        """
        發送系統通知
        
        Args:
            event: 系統事件
            user_id: 用戶ID (可選)
        """
        if not self._notification_service or not user_id:
            return
        
        try:
            # 根據事件類型和狀態決定優先級
            priority = self._determine_priority(event)
            
            # 根據嚴重程度決定通道
            channels = self._determine_channels(event)
            
            notification = TradeNotification(
                notification_type="system_notification",
                title=f"系統通知: {event.component}",
                message=event.message,
                data=event.to_dict(),
                user_id=user_id,
                priority=priority,
                channels=channels
            )
            
            self._notification_service._send_notification(notification)
            
        except Exception as e:
            logger.error("發送系統通知失敗: %s", e)

    def _calculate_overall_status(self) -> SystemStatus:
        """
        計算整體系統狀態
        
        Returns:
            SystemStatus: 整體系統狀態
        """
        if not self._component_status:
            return SystemStatus.ONLINE
        
        statuses = list(self._component_status.values())
        
        # 如果有任何組件離線或錯誤，系統狀態為錯誤
        if SystemStatus.ERROR in statuses or SystemStatus.OFFLINE in statuses:
            return SystemStatus.ERROR
        
        # 如果有組件在維護中，系統狀態為維護
        if SystemStatus.MAINTENANCE in statuses:
            return SystemStatus.MAINTENANCE
        
        # 如果有組件性能降級，系統狀態為降級
        if SystemStatus.DEGRADED in statuses:
            return SystemStatus.DEGRADED
        
        # 否則系統正常
        return SystemStatus.ONLINE

    def _determine_priority(self, event: SystemEvent) -> NotificationPriority:
        """
        根據事件確定通知優先級
        
        Args:
            event: 系統事件
            
        Returns:
            NotificationPriority: 通知優先級
        """
        if event.status in [SystemStatus.ERROR, SystemStatus.OFFLINE]:
            return NotificationPriority.URGENT
        elif event.status == SystemStatus.DEGRADED:
            return NotificationPriority.HIGH
        elif event.event_type == "maintenance":
            return NotificationPriority.HIGH
        else:
            return NotificationPriority.NORMAL

    def _determine_channels(self, event: SystemEvent) -> List[NotificationChannel]:
        """
        根據事件確定通知通道
        
        Args:
            event: 系統事件
            
        Returns:
            List[NotificationChannel]: 通知通道列表
        """
        if event.status in [SystemStatus.ERROR, SystemStatus.OFFLINE]:
            return [
                NotificationChannel.WEBSOCKET,
                NotificationChannel.EMAIL,
                NotificationChannel.SMS
            ]
        elif event.status == SystemStatus.DEGRADED:
            return [NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL]
        else:
            return [NotificationChannel.WEBSOCKET]
