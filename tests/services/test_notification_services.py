"""
通知服務測試模組

測試交易通知、風險警報和系統監控通知服務的功能。

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥8.5/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock 所有複雜的導入
with patch.dict('sys.modules', {
    'src.services.risk.risk_monitor_service': Mock(),
    'src.services.broker.order_execution_service': Mock(),
}):
    from src.services.notification.trade_notification_service import (
        TradeNotificationService,
        TradeNotification,
        NotificationChannel,
        NotificationPriority,
        TradeNotificationError
    )
    from src.services.notification.risk_alert_service import (
        RiskAlertService,
        AlertRule,
        AlertSeverity,
        RiskAlertError
    )
    from src.services.notification.system_notification_service import (
        SystemNotificationService,
        SystemEvent,
        SystemStatus,
        ComponentType,
        SystemNotificationError
    )
    from src.services.risk.risk_monitor_service import RiskEvent, RiskLevel, RiskMetric

# Mock ExecutionStatus
class MockExecutionStatus:
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

ExecutionStatus = MockExecutionStatus


class TestTradeNotificationService:
    """測試交易通知服務"""

    @pytest.fixture
    def notification_service(self):
        """創建交易通知服務實例"""
        return TradeNotificationService()

    @pytest.fixture
    def sample_notification(self):
        """創建範例交易通知"""
        return TradeNotification(
            notification_type="order_update",
            title="訂單更新",
            message="您的訂單已成交",
            data={"order_id": "123", "symbol": "AAPL"},
            user_id="user123"
        )

    def test_init_success(self, notification_service):
        """測試服務初始化成功"""
        assert notification_service is not None
        assert notification_service._notifications == []
        assert notification_service._user_preferences == {}

    def test_trade_notification_creation(self, sample_notification):
        """測試交易通知創建"""
        assert sample_notification.notification_type == "order_update"
        assert sample_notification.title == "訂單更新"
        assert sample_notification.message == "您的訂單已成交"
        assert sample_notification.user_id == "user123"
        assert sample_notification.notification_id is not None

    def test_trade_notification_to_dict(self, sample_notification):
        """測試交易通知轉換為字典"""
        notif_dict = sample_notification.to_dict()
        
        assert notif_dict["notification_type"] == "order_update"
        assert notif_dict["title"] == "訂單更新"
        assert notif_dict["message"] == "您的訂單已成交"
        assert notif_dict["user_id"] == "user123"
        assert "created_at" in notif_dict

    def test_send_order_notification(self, notification_service):
        """測試發送訂單通知"""
        order_data = {
            "request": {
                "symbol": "AAPL",
                "action": "buy",
                "quantity": 100
            }
        }
        
        notification_id = notification_service.send_order_notification(
            order_id="order123",
            status=ExecutionStatus.FILLED,
            order_data=order_data,
            user_id="user123"
        )
        
        assert notification_id is not None
        assert len(notification_service._notifications) == 1

    def test_send_trade_execution_notification(self, notification_service):
        """測試發送交易執行通知"""
        notification_id = notification_service.send_trade_execution_notification(
            symbol="AAPL",
            action="buy",
            quantity=100,
            price=150.0,
            user_id="user123"
        )
        
        assert notification_id is not None
        assert len(notification_service._notifications) == 1
        
        notification = notification_service._notifications[0]
        assert notification.notification_type == "trade_execution"
        assert notification.priority == NotificationPriority.HIGH

    def test_send_daily_summary(self, notification_service):
        """測試發送每日摘要"""
        summary_data = {
            "total_trades": 5,
            "total_pnl": 250.0,
            "best_trade": "AAPL +$100"
        }
        
        notification_id = notification_service.send_daily_summary(
            user_id="user123",
            summary_data=summary_data
        )
        
        assert notification_id is not None
        assert len(notification_service._notifications) == 1
        
        notification = notification_service._notifications[0]
        assert notification.notification_type == "daily_summary"
        assert NotificationChannel.EMAIL in notification.channels

    def test_set_user_preferences(self, notification_service):
        """測試設定用戶通知偏好"""
        preferences = {
            "enable_email": True,
            "enable_sms": False,
            "quiet_hours_start": "22:00"
        }
        
        notification_service.set_user_preferences("user123", preferences)
        
        assert notification_service._user_preferences["user123"] == preferences

    def test_get_user_preferences(self, notification_service):
        """測試獲取用戶通知偏好"""
        preferences = {
            "enable_email": True,
            "enable_sms": False
        }
        notification_service._user_preferences["user123"] = preferences
        
        result = notification_service.get_user_preferences("user123")
        
        assert result == preferences

    def test_get_default_preferences(self, notification_service):
        """測試獲取預設偏好"""
        result = notification_service.get_user_preferences("nonexistent_user")
        
        assert result["enable_websocket"] is True
        assert result["enable_email"] is True
        assert "quiet_hours_start" in result

    def test_get_notifications(self, notification_service, sample_notification):
        """測試獲取用戶通知列表"""
        notification_service._notifications.append(sample_notification)
        
        notifications = notification_service.get_notifications("user123")
        
        assert len(notifications) == 1
        assert notifications[0]["notification_id"] == sample_notification.notification_id

    def test_get_notifications_unread_only(self, notification_service, sample_notification):
        """測試獲取未讀通知"""
        # 添加已讀通知
        sample_notification.read_at = datetime.now()
        notification_service._notifications.append(sample_notification)
        
        notifications = notification_service.get_notifications("user123", unread_only=True)
        
        assert len(notifications) == 0

    def test_mark_as_read(self, notification_service, sample_notification):
        """測試標記通知為已讀"""
        notification_service._notifications.append(sample_notification)
        
        result = notification_service.mark_as_read(
            sample_notification.notification_id,
            "user123"
        )
        
        assert result is True
        assert sample_notification.read_at is not None

    def test_mark_as_read_nonexistent(self, notification_service):
        """測試標記不存在的通知為已讀"""
        result = notification_service.mark_as_read("nonexistent", "user123")
        
        assert result is False


class TestRiskAlertService:
    """測試風險警報服務"""

    @pytest.fixture
    def alert_service(self):
        """創建風險警報服務實例"""
        return RiskAlertService()

    @pytest.fixture
    def sample_alert_rule(self):
        """創建範例警報規則"""
        return AlertRule(
            name="嚴重風險警報",
            risk_metric=RiskMetric.PORTFOLIO_VAR,
            risk_level=RiskLevel.CRITICAL,
            severity=AlertSeverity.CRITICAL
        )

    @pytest.fixture
    def sample_risk_event(self):
        """創建範例風險事件"""
        return RiskEvent(
            metric=RiskMetric.PORTFOLIO_VAR,
            level=RiskLevel.CRITICAL,
            value=0.25,
            threshold=0.20,
            message="投資組合風險過高"
        )

    def test_init_success(self, alert_service):
        """測試服務初始化成功"""
        assert alert_service is not None
        assert len(alert_service._alert_rules) > 0  # 有預設規則
        assert alert_service._alert_history == []

    def test_alert_rule_creation(self, sample_alert_rule):
        """測試警報規則創建"""
        assert sample_alert_rule.name == "嚴重風險警報"
        assert sample_alert_rule.risk_metric == RiskMetric.PORTFOLIO_VAR
        assert sample_alert_rule.risk_level == RiskLevel.CRITICAL
        assert sample_alert_rule.severity == AlertSeverity.CRITICAL
        assert sample_alert_rule.rule_id is not None

    def test_alert_rule_can_trigger(self, sample_alert_rule):
        """測試警報規則可以觸發"""
        assert sample_alert_rule.can_trigger() is True
        
        # 設定最後觸發時間
        sample_alert_rule.last_triggered = datetime.now()
        assert sample_alert_rule.can_trigger() is False

    def test_alert_rule_to_dict(self, sample_alert_rule):
        """測試警報規則轉換為字典"""
        rule_dict = sample_alert_rule.to_dict()
        
        assert rule_dict["name"] == "嚴重風險警報"
        assert rule_dict["risk_metric"] == "portfolio_var"
        assert rule_dict["risk_level"] == "critical"
        assert rule_dict["severity"] == "critical"

    def test_handle_risk_event(self, alert_service, sample_risk_event):
        """測試處理風險事件"""
        triggered_alerts = alert_service.handle_risk_event(sample_risk_event, "user123")
        
        assert len(triggered_alerts) > 0  # 應該觸發一些警報
        assert len(alert_service._alert_history) > 0

    def test_send_emergency_alert(self, alert_service):
        """測試發送緊急警報"""
        alert_id = alert_service.send_emergency_alert(
            title="緊急警報",
            message="系統檢測到異常",
            user_id="user123",
            severity=AlertSeverity.CRITICAL
        )
        
        assert alert_id is not None
        assert len(alert_service._alert_history) == 1
        
        alert = alert_service._alert_history[0]
        assert alert["type"] == "emergency"
        assert alert["severity"] == "critical"

    def test_add_alert_rule(self, alert_service, sample_alert_rule):
        """測試添加警報規則"""
        initial_count = len(alert_service._alert_rules)
        
        alert_service.add_alert_rule(sample_alert_rule)
        
        assert len(alert_service._alert_rules) == initial_count + 1

    def test_remove_alert_rule(self, alert_service, sample_alert_rule):
        """測試移除警報規則"""
        alert_service.add_alert_rule(sample_alert_rule)
        
        result = alert_service.remove_alert_rule(sample_alert_rule.rule_id)
        
        assert result is True

    def test_get_alert_rules(self, alert_service):
        """測試獲取警報規則列表"""
        rules = alert_service.get_alert_rules()
        
        assert isinstance(rules, list)
        assert len(rules) > 0

    def test_get_alert_history(self, alert_service):
        """測試獲取警報歷史"""
        # 添加測試警報
        alert_service.send_emergency_alert(
            title="測試警報",
            message="測試訊息",
            user_id="user123"
        )
        
        history = alert_service.get_alert_history(user_id="user123")
        
        assert len(history) == 1
        assert history[0]["user_id"] == "user123"

    def test_get_alert_summary(self, alert_service):
        """測試獲取警報摘要"""
        # 添加測試警報
        alert_service.send_emergency_alert(
            title="測試警報",
            message="測試訊息",
            user_id="user123",
            severity=AlertSeverity.CRITICAL
        )
        
        summary = alert_service.get_alert_summary("user123")
        
        assert summary["total_alerts"] == 1
        assert "by_severity" in summary
        assert "recent_critical" in summary

    def test_enable_disable_rule(self, alert_service, sample_alert_rule):
        """測試啟用/停用警報規則"""
        alert_service.add_alert_rule(sample_alert_rule)
        
        # 測試停用
        result = alert_service.disable_rule(sample_alert_rule.rule_id)
        assert result is True
        assert sample_alert_rule.enabled is False
        
        # 測試啟用
        result = alert_service.enable_rule(sample_alert_rule.rule_id)
        assert result is True
        assert sample_alert_rule.enabled is True


class TestSystemNotificationService:
    """測試系統監控通知服務"""

    @pytest.fixture
    def system_service(self):
        """創建系統監控通知服務實例"""
        return SystemNotificationService()

    @pytest.fixture
    def sample_system_event(self):
        """創建範例系統事件"""
        return SystemEvent(
            component="database",
            component_type=ComponentType.DATABASE,
            event_type="status_change",
            status=SystemStatus.OFFLINE,
            message="資料庫連接失敗"
        )

    def test_init_success(self, system_service):
        """測試服務初始化成功"""
        assert system_service is not None
        assert system_service._system_events == []
        assert system_service._component_status == {}

    def test_system_event_creation(self, sample_system_event):
        """測試系統事件創建"""
        assert sample_system_event.component == "database"
        assert sample_system_event.component_type == ComponentType.DATABASE
        assert sample_system_event.event_type == "status_change"
        assert sample_system_event.status == SystemStatus.OFFLINE
        assert sample_system_event.event_id is not None

    def test_system_event_to_dict(self, sample_system_event):
        """測試系統事件轉換為字典"""
        event_dict = sample_system_event.to_dict()
        
        assert event_dict["component"] == "database"
        assert event_dict["component_type"] == "database"
        assert event_dict["event_type"] == "status_change"
        assert event_dict["status"] == "offline"
        assert "timestamp" in event_dict

    def test_report_component_status(self, system_service):
        """測試報告組件狀態"""
        event_id = system_service.report_component_status(
            component="web_server",
            component_type=ComponentType.WEB_SERVER,
            status=SystemStatus.ONLINE,
            message="Web 服務器正常運行"
        )
        
        assert event_id is not None
        assert len(system_service._system_events) == 1
        assert system_service._component_status["web_server"] == SystemStatus.ONLINE

    def test_report_performance_alert(self, system_service):
        """測試報告性能警報"""
        event_id = system_service.report_performance_alert(
            component="api_server",
            metric_name="response_time",
            current_value=2000.0,
            threshold=1000.0,
            message="API 響應時間過長"
        )
        
        assert event_id is not None
        assert len(system_service._system_events) == 1
        
        event = system_service._system_events[0]
        assert event.event_type == "performance_alert"
        assert event.status == SystemStatus.DEGRADED

    def test_report_error(self, system_service):
        """測試報告系統錯誤"""
        event_id = system_service.report_error(
            component="trading_engine",
            error_type="ConnectionError",
            error_message="無法連接到券商 API"
        )
        
        assert event_id is not None
        assert len(system_service._system_events) == 1
        
        event = system_service._system_events[0]
        assert event.event_type == "error"
        assert event.status == SystemStatus.ERROR

    def test_send_maintenance_notification(self, system_service):
        """測試發送維護通知"""
        start_time = datetime.now()
        end_time = datetime.now()
        
        event_id = system_service.send_maintenance_notification(
            title="系統維護通知",
            message="系統將於今晚進行維護",
            start_time=start_time,
            end_time=end_time,
            affected_components=["web_server", "database"]
        )
        
        assert event_id is not None
        assert len(system_service._system_events) == 1
        
        event = system_service._system_events[0]
        assert event.event_type == "maintenance"
        assert event.status == SystemStatus.MAINTENANCE

    def test_get_system_status(self, system_service):
        """測試獲取系統狀態摘要"""
        # 添加一些組件狀態
        system_service._component_status["web_server"] = SystemStatus.ONLINE
        system_service._component_status["database"] = SystemStatus.ONLINE
        system_service._component_status["api_server"] = SystemStatus.DEGRADED
        
        status = system_service.get_system_status()
        
        assert status["total_components"] == 3
        assert status["healthy_components"] == 2
        assert "component_status" in status

    def test_get_recent_events(self, system_service, sample_system_event):
        """測試獲取最近事件"""
        system_service._system_events.append(sample_system_event)
        
        recent_events = system_service.get_recent_events(hours=24)
        
        assert len(recent_events) == 1
        assert recent_events[0]["event_id"] == sample_system_event.event_id

    def test_get_recent_events_with_filters(self, system_service, sample_system_event):
        """測試使用篩選條件獲取最近事件"""
        system_service._system_events.append(sample_system_event)
        
        # 測試組件篩選
        events = system_service.get_recent_events(
            hours=24,
            component="database"
        )
        assert len(events) == 1
        
        # 測試事件類型篩選
        events = system_service.get_recent_events(
            hours=24,
            event_type="status_change"
        )
        assert len(events) == 1
        
        # 測試不匹配的篩選
        events = system_service.get_recent_events(
            hours=24,
            component="nonexistent"
        )
        assert len(events) == 0

    def test_resolve_event(self, system_service, sample_system_event):
        """測試標記事件為已解決"""
        system_service._system_events.append(sample_system_event)
        
        result = system_service.resolve_event(sample_system_event.event_id)
        
        assert result is True
        assert sample_system_event.resolved_at is not None

    def test_resolve_nonexistent_event(self, system_service):
        """測試標記不存在的事件為已解決"""
        result = system_service.resolve_event("nonexistent_event")
        
        assert result is False
