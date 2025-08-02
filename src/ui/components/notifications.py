"""
實時通知系統 (增強版)

此模組提供完整的實時通知功能，包括：
- WebSocket 實時通知
- 通知管理和歷史
- 用戶偏好設置
- 多種通知類型和優先級
- 智能通知聚合
"""

import streamlit as st
import json
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """通知類型枚舉"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    TRADING = "trading"
    RISK = "risk"
    SYSTEM = "system"


class NotificationPriority(Enum):
    """通知優先級枚舉"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class NotificationManager:
    """實時通知管理器"""

    def __init__(self):
        """初始化通知管理器"""
        self.notifications: List[Dict[str, Any]] = []
        self.user_preferences: Dict[str, Any] = {}
        self.notification_history: List[Dict[str, Any]] = []
        self.websocket_connections: Dict[str, Any] = {}
        self.max_notifications = 100
        self.max_history = 1000

        # 初始化 session state
        if "notifications" not in st.session_state:
            st.session_state.notifications = []
        if "notification_preferences" not in st.session_state:
            st.session_state.notification_preferences = self._get_default_preferences()

    def _get_default_preferences(self) -> Dict[str, Any]:
        """獲取默認通知偏好設置"""
        return {
            "enable_sound": True,
            "enable_desktop": True,
            "enable_email": False,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00",
            "priority_filter": NotificationPriority.NORMAL.value,
            "type_filters": {
                NotificationType.TRADING.value: True,
                NotificationType.RISK.value: True,
                NotificationType.SYSTEM.value: True,
                NotificationType.INFO.value: True,
                NotificationType.SUCCESS.value: True,
                NotificationType.WARNING.value: True,
                NotificationType.ERROR.value: True,
            },
            "auto_dismiss_duration": 5,  # 秒
            "max_display_count": 5,
        }

    def add_notification(
        self,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        auto_dismiss: bool = True,
        action_callback: Optional[Callable] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """添加新通知

        Args:
            message: 通知訊息
            notification_type: 通知類型
            priority: 優先級
            auto_dismiss: 是否自動消失
            action_callback: 動作回調函數
            metadata: 額外元數據

        Returns:
            str: 通知ID
        """
        notification_id = f"notif_{datetime.now().timestamp()}"

        notification = {
            "id": notification_id,
            "message": message,
            "type": notification_type.value,
            "priority": priority.value,
            "timestamp": datetime.now(),
            "read": False,
            "auto_dismiss": auto_dismiss,
            "action_callback": action_callback,
            "metadata": metadata or {},
            "dismissed": False
        }

        # 檢查用戶偏好過濾
        if self._should_show_notification(notification):
            # 添加到當前通知列表
            st.session_state.notifications.append(notification)

            # 限制通知數量
            if len(st.session_state.notifications) > self.max_notifications:
                st.session_state.notifications = st.session_state.notifications[-self.max_notifications:]

            # 添加到歷史記錄
            self.notification_history.append(notification.copy())
            if len(self.notification_history) > self.max_history:
                self.notification_history = self.notification_history[-self.max_history:]

            logger.debug(f"新通知已添加: {notification_id}")

        return notification_id

    def _should_show_notification(self, notification: Dict[str, Any]) -> bool:
        """檢查是否應該顯示通知"""
        preferences = st.session_state.notification_preferences

        # 檢查優先級過濾
        if notification["priority"] < preferences["priority_filter"]:
            return False

        # 檢查類型過濾
        if not preferences["type_filters"].get(notification["type"], True):
            return False

        # 檢查靜音時間
        if self._is_quiet_hours():
            # 只顯示緊急通知
            return notification["priority"] >= NotificationPriority.URGENT.value

        return True

    def _is_quiet_hours(self) -> bool:
        """檢查是否在靜音時間內"""
        preferences = st.session_state.notification_preferences
        now = datetime.now().time()

        try:
            start_time = datetime.strptime(preferences["quiet_hours_start"], "%H:%M").time()
            end_time = datetime.strptime(preferences["quiet_hours_end"], "%H:%M").time()

            if start_time <= end_time:
                return start_time <= now <= end_time
            else:
                return now >= start_time or now <= end_time
        except:
            return False


# 全域通知管理器
notification_manager = NotificationManager()


def show_notification(
    message: str,
    notification_type: str = "info",
    duration: int = 3,
    priority: str = "normal",
    auto_dismiss: bool = True
) -> str:
    """顯示通知 (增強版)

    Args:
        message: 通知訊息
        notification_type: 通知類型
        duration: 顯示時間（秒）
        priority: 優先級
        auto_dismiss: 是否自動消失

    Returns:
        str: 通知ID
    """
    # 轉換類型和優先級
    try:
        notif_type = NotificationType(notification_type)
    except ValueError:
        notif_type = NotificationType.INFO

    try:
        notif_priority = NotificationPriority[priority.upper()]
    except (KeyError, AttributeError):
        notif_priority = NotificationPriority.NORMAL

    # 添加到通知管理器
    notification_id = notification_manager.add_notification(
        message=message,
        notification_type=notif_type,
        priority=notif_priority,
        auto_dismiss=auto_dismiss
    )

    # 立即顯示通知
    _display_notification_immediate(message, notification_type)

    return notification_id


def _display_notification_immediate(message: str, notification_type: str) -> None:
    """立即顯示通知"""
    if notification_type == "info":
        st.info(message)
    elif notification_type == "success":
        st.success(message)
    elif notification_type == "warning":
        st.warning(message)
    elif notification_type == "error":
        st.error(message)
    else:
        st.write(message)


def notification_center():
    """通知中心 (增強版)

    顯示系統的所有通知，支援過濾、搜索和管理功能。
    """
    st.subheader("🔔 通知中心")

    # 獲取通知數據
    notifications = st.session_state.get("notifications", [])
    history = notification_manager.notification_history

    # 統計信息
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        unread_count = len([n for n in notifications if not n.get("read", False)])
        st.metric("未讀通知", unread_count)

    with col2:
        total_today = len([n for n in history if n["timestamp"].date() == datetime.now().date()])
        st.metric("今日通知", total_today)

    with col3:
        urgent_count = len([n for n in notifications if n.get("priority", 1) >= NotificationPriority.URGENT.value])
        st.metric("緊急通知", urgent_count)

    with col4:
        if st.button("🔄 刷新"):
            st.rerun()

    # 過濾和搜索
    with st.expander("🔍 過濾選項"):
        col1, col2, col3 = st.columns(3)

        with col1:
            type_filter = st.multiselect(
                "通知類型",
                options=[t.value for t in NotificationType],
                default=[t.value for t in NotificationType]
            )

        with col2:
            priority_filter = st.selectbox(
                "最低優先級",
                options=[p.value for p in NotificationPriority],
                index=0
            )

        with col3:
            date_filter = st.date_input(
                "日期範圍",
                value=[datetime.now().date() - timedelta(days=7), datetime.now().date()],
                max_value=datetime.now().date()
            )

        search_text = st.text_input("🔍 搜索通知內容")

    # 過濾通知
    filtered_notifications = _filter_notifications(
        notifications + history,
        type_filter,
        priority_filter,
        date_filter,
        search_text
    )

    # 顯示通知
    if filtered_notifications:
        # 分頁
        items_per_page = 10
        total_pages = (len(filtered_notifications) - 1) // items_per_page + 1

        if total_pages > 1:
            page = st.selectbox("頁面", range(1, total_pages + 1)) - 1
        else:
            page = 0

        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_notifications = filtered_notifications[start_idx:end_idx]

        # 顯示通知列表
        for i, notification in enumerate(page_notifications):
            _render_notification_item(notification, i)

        # 批量操作
        st.markdown("---")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📖 全部標記為已讀"):
                _mark_all_as_read(filtered_notifications)
                st.success("已標記所有通知為已讀")
                st.rerun()

        with col2:
            if st.button("🗑️ 清除已讀通知"):
                _clear_read_notifications()
                st.success("已清除所有已讀通知")
                st.rerun()

        with col3:
            if st.button("🧹 清除所有通知"):
                _clear_all_notifications()
                st.success("已清除所有通知")
                st.rerun()

    else:
        st.info("📭 沒有符合條件的通知")


def _filter_notifications(
    notifications: List[Dict[str, Any]],
    type_filter: List[str],
    priority_filter: int,
    date_filter: List,
    search_text: str
) -> List[Dict[str, Any]]:
    """過濾通知"""
    filtered = []

    for notification in notifications:
        # 類型過濾
        if notification["type"] not in type_filter:
            continue

        # 優先級過濾
        if notification.get("priority", 1) < priority_filter:
            continue

        # 日期過濾
        if len(date_filter) == 2:
            notif_date = notification["timestamp"].date()
            if not (date_filter[0] <= notif_date <= date_filter[1]):
                continue

        # 搜索過濾
        if search_text and search_text.lower() not in notification["message"].lower():
            continue

        filtered.append(notification)

    # 按時間倒序排列
    filtered.sort(key=lambda x: x["timestamp"], reverse=True)
    return filtered


def _render_notification_item(notification: Dict[str, Any], index: int) -> None:
    """渲染單個通知項目"""
    # 通知容器
    with st.container():
        col1, col2, col3, col4 = st.columns([1, 6, 2, 1])

        # 優先級指示器
        with col1:
            priority = notification.get("priority", 1)
            priority_icons = {
                1: "🔵",  # 低
                2: "🟡",  # 普通
                3: "🟠",  # 高
                4: "🔴"   # 緊急
            }
            st.write(priority_icons.get(priority, "⚪"))

        # 通知內容
        with col2:
            # 標題和時間
            timestamp = notification["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            read_status = "✅" if notification.get("read", False) else "🔘"

            st.markdown(f"**{read_status} {notification['message']}**")
            st.caption(f"📅 {timestamp} | 🏷️ {notification['type']}")

            # 元數據
            if notification.get("metadata"):
                with st.expander("詳細信息"):
                    st.json(notification["metadata"])

        # 類型指示器
        with col3:
            type_icons = {
                "info": "ℹ️",
                "success": "✅",
                "warning": "⚠️",
                "error": "❌",
                "trading": "💰",
                "risk": "⚡",
                "system": "🔧"
            }
            icon = type_icons.get(notification["type"], "📝")
            st.write(f"{icon} {notification['type']}")

        # 操作按鈕
        with col4:
            if not notification.get("read", False):
                if st.button("✓", key=f"read_{index}", help="標記為已讀"):
                    _mark_notification_as_read(notification["id"])
                    st.rerun()

        st.markdown("---")


def _mark_notification_as_read(notification_id: str) -> None:
    """標記通知為已讀"""
    for notification in st.session_state.notifications:
        if notification["id"] == notification_id:
            notification["read"] = True
            break


def _mark_all_as_read(notifications: List[Dict[str, Any]]) -> None:
    """標記所有通知為已讀"""
    for notification in st.session_state.notifications:
        notification["read"] = True


def _clear_read_notifications() -> None:
    """清除已讀通知"""
    st.session_state.notifications = [
        n for n in st.session_state.notifications
        if not n.get("read", False)
    ]


def _clear_all_notifications() -> None:
    """清除所有通知"""
    st.session_state.notifications = []


def alert_badge(count: Optional[int] = None) -> None:
    """顯示通知徽章 (增強版)

    Args:
        count: 未讀通知數量，None 表示自動計算
    """
    if count is None:
        count = len([n for n in st.session_state.get("notifications", []) if not n.get("read", False)])

    if count > 0:
        # 根據優先級確定顏色
        urgent_count = len([
            n for n in st.session_state.get("notifications", [])
            if not n.get("read", False) and n.get("priority", 1) >= NotificationPriority.URGENT.value
        ])

        badge_color = "red" if urgent_count > 0 else "orange"

        st.markdown(
            f"""
            <div style="
                position: relative;
                display: inline-block;
                margin-right: 10px;
            ">
                <span style="
                    position: absolute;
                    top: -8px;
                    right: -8px;
                    background-color: {badge_color};
                    color: white;
                    border-radius: 50%;
                    width: 20px;
                    height: 20px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 12px;
                    font-weight: bold;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                ">{count}</span>
                <span style="font-size: 24px;">🔔</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <div style="
                position: relative;
                display: inline-block;
                margin-right: 10px;
            ">
                <span style="font-size: 24px; opacity: 0.6;">🔔</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def notification_preferences_panel() -> None:
    """通知偏好設置面板"""
    st.subheader("⚙️ 通知設定")

    preferences = st.session_state.notification_preferences

    # 基本設定
    st.markdown("### 基本設定")
    col1, col2 = st.columns(2)

    with col1:
        preferences["enable_sound"] = st.checkbox(
            "🔊 啟用聲音通知",
            value=preferences.get("enable_sound", True)
        )

        preferences["enable_desktop"] = st.checkbox(
            "💻 啟用桌面通知",
            value=preferences.get("enable_desktop", True)
        )

    with col2:
        preferences["enable_email"] = st.checkbox(
            "📧 啟用郵件通知",
            value=preferences.get("enable_email", False)
        )

        preferences["auto_dismiss_duration"] = st.slider(
            "⏱️ 自動消失時間（秒）",
            min_value=1,
            max_value=30,
            value=preferences.get("auto_dismiss_duration", 5)
        )

    # 靜音時間設定
    st.markdown("### 靜音時間")
    col1, col2 = st.columns(2)

    with col1:
        preferences["quiet_hours_start"] = st.time_input(
            "開始時間",
            value=datetime.strptime(preferences.get("quiet_hours_start", "22:00"), "%H:%M").time()
        ).strftime("%H:%M")

    with col2:
        preferences["quiet_hours_end"] = st.time_input(
            "結束時間",
            value=datetime.strptime(preferences.get("quiet_hours_end", "08:00"), "%H:%M").time()
        ).strftime("%H:%M")

    # 優先級過濾
    st.markdown("### 過濾設定")
    preferences["priority_filter"] = st.selectbox(
        "最低顯示優先級",
        options=[p.value for p in NotificationPriority],
        index=preferences.get("priority_filter", 2) - 1,
        format_func=lambda x: {
            1: "🔵 低優先級",
            2: "🟡 普通優先級",
            3: "🟠 高優先級",
            4: "🔴 緊急優先級"
        }[x]
    )

    # 通知類型過濾
    st.markdown("### 通知類型")
    type_filters = preferences.get("type_filters", {})

    col1, col2 = st.columns(2)
    with col1:
        type_filters[NotificationType.TRADING.value] = st.checkbox(
            "💰 交易通知", value=type_filters.get(NotificationType.TRADING.value, True)
        )
        type_filters[NotificationType.RISK.value] = st.checkbox(
            "⚡ 風險警報", value=type_filters.get(NotificationType.RISK.value, True)
        )
        type_filters[NotificationType.SYSTEM.value] = st.checkbox(
            "🔧 系統通知", value=type_filters.get(NotificationType.SYSTEM.value, True)
        )

    with col2:
        type_filters[NotificationType.INFO.value] = st.checkbox(
            "ℹ️ 信息通知", value=type_filters.get(NotificationType.INFO.value, True)
        )
        type_filters[NotificationType.SUCCESS.value] = st.checkbox(
            "✅ 成功通知", value=type_filters.get(NotificationType.SUCCESS.value, True)
        )
        type_filters[NotificationType.WARNING.value] = st.checkbox(
            "⚠️ 警告通知", value=type_filters.get(NotificationType.WARNING.value, True)
        )
        type_filters[NotificationType.ERROR.value] = st.checkbox(
            "❌ 錯誤通知", value=type_filters.get(NotificationType.ERROR.value, True)
        )

    preferences["type_filters"] = type_filters

    # 保存設定
    if st.button("💾 保存設定"):
        st.session_state.notification_preferences = preferences
        st.success("通知設定已保存")
        st.rerun()

    # 重置設定
    if st.button("🔄 重置為默認設定"):
        st.session_state.notification_preferences = notification_manager._get_default_preferences()
        st.success("已重置為默認設定")
        st.rerun()


def show_realtime_notifications() -> None:
    """顯示實時通知組件"""
    # 獲取未讀通知
    unread_notifications = [
        n for n in st.session_state.get("notifications", [])
        if not n.get("read", False) and not n.get("dismissed", False)
    ]

    # 按優先級排序
    unread_notifications.sort(key=lambda x: x.get("priority", 1), reverse=True)

    # 限制顯示數量
    max_display = st.session_state.notification_preferences.get("max_display_count", 5)
    display_notifications = unread_notifications[:max_display]

    # 顯示通知
    for notification in display_notifications:
        _render_realtime_notification(notification)


def _render_realtime_notification(notification: Dict[str, Any]) -> None:
    """渲染實時通知"""
    priority = notification.get("priority", 1)

    # 根據優先級選擇樣式
    if priority >= NotificationPriority.URGENT.value:
        container = st.error
    elif priority >= NotificationPriority.HIGH.value:
        container = st.warning
    elif notification["type"] == NotificationType.SUCCESS.value:
        container = st.success
    else:
        container = st.info

    with container(notification["message"]):
        col1, col2 = st.columns([3, 1])

        with col1:
            timestamp = notification["timestamp"].strftime("%H:%M:%S")
            st.caption(f"🕐 {timestamp}")

        with col2:
            if st.button("✕", key=f"dismiss_{notification['id']}", help="關閉"):
                _dismiss_notification(notification["id"])
                st.rerun()


def _dismiss_notification(notification_id: str) -> None:
    """關閉通知"""
    for notification in st.session_state.notifications:
        if notification["id"] == notification_id:
            notification["dismissed"] = True
            notification["read"] = True
            break


# 便捷函數
def show_trading_notification(message: str, success: bool = True) -> str:
    """顯示交易通知"""
    return show_notification(
        message=message,
        notification_type=NotificationType.SUCCESS.value if success else NotificationType.ERROR.value,
        priority=NotificationPriority.HIGH.value
    )


def show_risk_alert(message: str, urgent: bool = False) -> str:
    """顯示風險警報"""
    return show_notification(
        message=message,
        notification_type=NotificationType.RISK.value,
        priority=NotificationPriority.URGENT.value if urgent else NotificationPriority.HIGH.value
    )


def show_system_notification(message: str, error: bool = False) -> str:
    """顯示系統通知"""
    return show_notification(
        message=message,
        notification_type=NotificationType.ERROR.value if error else NotificationType.SYSTEM.value,
        priority=NotificationPriority.HIGH.value if error else NotificationPriority.NORMAL.value
    )
