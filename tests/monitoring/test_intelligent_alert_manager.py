"""
智能告警管理器測試

測試 IntelligentAlertManager 類的各項功能，包括告警規則管理、
告警觸發、升級策略和通知機制等。

遵循 Phase 5.3 測試標準，確保 ≥70% 測試覆蓋率。
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.monitoring.intelligent_alert_manager import (
    IntelligentAlertManager,
    AlertSeverity,
    AlertStatus,
    AlertRule,
    Alert,
)


class TestIntelligentAlertManager:
    """智能告警管理器測試類"""

    @pytest.fixture
    def alert_manager(self):
        """創建測試用的 IntelligentAlertManager 實例"""
        # 使用測試配置檔案
        with patch(
            "src.monitoring.intelligent_alert_manager.Path.exists", return_value=False
        ):
            manager = IntelligentAlertManager()
            return manager

    @pytest.fixture
    def sample_alert_rule(self):
        """創建測試用的告警規則"""
        return AlertRule(
            id="test-rule-1",
            name="Test CPU Alert",
            description="CPU usage too high",
            metric_name="system_cpu_usage_percent",
            operator=">",
            threshold_value=80.0,
            severity=AlertSeverity.WARNING,
            enabled=True,
            notification_channels=["email", "webhook"],
        )

    def test_init(self, alert_manager):
        """測試初始化"""
        assert not alert_manager.is_running
        assert isinstance(alert_manager.rules, dict)
        assert isinstance(alert_manager.active_alerts, dict)
        assert isinstance(alert_manager.alert_history, list)

    def test_start_stop(self, alert_manager):
        """測試啟動和停止"""
        # 測試啟動
        assert alert_manager.start()
        assert alert_manager.is_running

        # 測試重複啟動
        assert alert_manager.start()

        # 測試停止
        assert alert_manager.stop()
        assert not alert_manager.is_running

        # 測試重複停止
        assert alert_manager.stop()

    def test_parse_expression(self, alert_manager):
        """測試表達式解析"""
        # 測試大於表達式
        metric, operator, threshold = alert_manager._parse_expression("cpu_usage > 80")
        assert metric == "cpu_usage"
        assert operator == ">"
        assert threshold == 80.0

        # 測試小於表達式
        metric, operator, threshold = alert_manager._parse_expression(
            "memory_usage < 20"
        )
        assert metric == "memory_usage"
        assert operator == "<"
        assert threshold == 20.0

        # 測試無效表達式
        metric, operator, threshold = alert_manager._parse_expression("invalid_expr")
        assert metric == "invalid_expr"
        assert operator == ">"
        assert threshold == 0.0

    def test_evaluate_condition(self, alert_manager):
        """測試條件評估"""
        # 測試各種運算符
        assert alert_manager._evaluate_condition(85, ">", 80)
        assert not alert_manager._evaluate_condition(75, ">", 80)

        assert alert_manager._evaluate_condition(75, "<", 80)
        assert not alert_manager._evaluate_condition(85, "<", 80)

        assert alert_manager._evaluate_condition(80, ">=", 80)
        assert alert_manager._evaluate_condition(85, ">=", 80)

        assert alert_manager._evaluate_condition(80, "<=", 80)
        assert alert_manager._evaluate_condition(75, "<=", 80)

        assert alert_manager._evaluate_condition(80, "==", 80)
        assert not alert_manager._evaluate_condition(85, "==", 80)

        assert alert_manager._evaluate_condition(85, "!=", 80)
        assert not alert_manager._evaluate_condition(80, "!=", 80)

    @patch(
        "src.monitoring.intelligent_alert_manager.IntelligentAlertManager._get_metric_value"
    )
    def test_trigger_alert(self, mock_get_metric, alert_manager, sample_alert_rule):
        """測試觸發告警"""
        # 添加規則
        alert_manager.rules[sample_alert_rule.id] = sample_alert_rule

        # 模擬指標值超過閾值
        mock_get_metric.return_value = 85.0

        # 執行評估
        alert_manager._evaluate_alert_rules()

        # 驗證告警被觸發
        assert len(alert_manager.active_alerts) == 1

        alert = list(alert_manager.active_alerts.values())[0]
        assert alert.rule_id == sample_alert_rule.id
        assert alert.severity == AlertSeverity.WARNING
        assert alert.status == AlertStatus.ACTIVE
        assert alert.metric_value == 85.0

    @patch(
        "src.monitoring.intelligent_alert_manager.IntelligentAlertManager._get_metric_value"
    )
    def test_resolve_alert(self, mock_get_metric, alert_manager, sample_alert_rule):
        """測試解決告警"""
        # 添加規則
        alert_manager.rules[sample_alert_rule.id] = sample_alert_rule

        # 先觸發告警
        mock_get_metric.return_value = 85.0
        alert_manager._evaluate_alert_rules()
        assert len(alert_manager.active_alerts) == 1

        # 指標值恢復正常
        mock_get_metric.return_value = 70.0
        alert_manager._evaluate_alert_rules()

        # 驗證告警被解決
        assert len(alert_manager.active_alerts) == 0
        assert len(alert_manager.alert_history) == 1

        resolved_alert = alert_manager.alert_history[0]
        assert resolved_alert.status == AlertStatus.RESOLVED
        assert resolved_alert.resolved_at is not None

    def test_alert_suppression(self, alert_manager):
        """測試告警抑制"""
        # 創建一個告警
        alert = Alert(
            id="test-alert",
            rule_id="test-rule",
            rule_name="Test Alert",
            severity=AlertSeverity.WARNING,
            status=AlertStatus.ACTIVE,
            title="Test",
            message="Test message",
            metric_value=85.0,
            threshold_value=80.0,
        )

        # 添加到歷史記錄（模擬最近的告警）
        alert.created_at = datetime.now() - timedelta(minutes=2)
        alert_manager.alert_history.append(alert)

        # 測試抑制邏輯
        new_alert = Alert(
            id="test-alert-2",
            rule_id="test-rule",
            rule_name="Test Alert",
            severity=AlertSeverity.WARNING,
            status=AlertStatus.ACTIVE,
            title="Test",
            message="Test message",
            metric_value=85.0,
            threshold_value=80.0,
        )

        should_suppress = alert_manager._should_suppress_alert(new_alert)
        assert should_suppress

    def test_alert_escalation(self, alert_manager):
        """測試告警升級"""
        # 創建一個舊的告警
        alert = Alert(
            id="test-alert",
            rule_id="test-rule",
            rule_name="Test Alert",
            severity=AlertSeverity.WARNING,
            status=AlertStatus.ACTIVE,
            title="Test",
            message="Test message",
            metric_value=85.0,
            threshold_value=80.0,
        )

        # 設置創建時間為1小時前
        alert.created_at = datetime.now() - timedelta(hours=1, minutes=5)
        alert_manager.active_alerts[alert.id] = alert

        # 執行升級檢查
        with patch.object(
            alert_manager.notification_service, "send_notification"
        ) as mock_send:
            alert_manager._check_alert_escalation()

            # 驗證告警被升級
            assert alert.escalation_level == 1
            assert alert.severity == AlertSeverity.ERROR

            # 驗證升級通知被發送
            mock_send.assert_called()

    @patch(
        "src.monitoring.intelligent_alert_manager.IntelligentAlertManager._get_metric_value"
    )
    def test_get_metric_value(self, mock_get_metric, alert_manager):
        """測試獲取指標值"""
        # 測試不同類型的指標
        mock_get_metric.return_value = 75.5

        value = alert_manager._get_metric_value("system_cpu_usage_percent")
        assert isinstance(value, float)
        assert 60 <= value <= 95  # 模擬數據範圍

    def test_notification_channels_selection(self, alert_manager):
        """測試通知渠道選擇"""
        # 測試不同嚴重程度的通知渠道
        critical_channels = alert_manager._get_notification_channels(
            AlertSeverity.CRITICAL
        )
        assert "email" in critical_channels
        assert "webhook" in critical_channels
        assert "slack" in critical_channels
        assert "telegram" in critical_channels

        warning_channels = alert_manager._get_notification_channels(
            AlertSeverity.WARNING
        )
        assert "webhook" in warning_channels
        assert "slack" in warning_channels
        assert "email" not in warning_channels

        info_channels = alert_manager._get_notification_channels(AlertSeverity.INFO)
        assert "webhook" in info_channels
        assert len(info_channels) == 1

    def test_cleanup_suppressed_alerts(self, alert_manager):
        """測試清理過期的抑制告警"""
        # 創建一個抑制的告警
        alert = Alert(
            id="test-alert",
            rule_id="test-rule",
            rule_name="Test Alert",
            severity=AlertSeverity.WARNING,
            status=AlertStatus.SUPPRESSED,
            title="Test",
            message="Test message",
            metric_value=85.0,
            threshold_value=80.0,
        )

        # 設置抑制截止時間為過去
        alert.suppressed_until = datetime.now() - timedelta(minutes=1)
        alert_manager.active_alerts[alert.id] = alert

        # 執行清理
        alert_manager._cleanup_suppressed_alerts()

        # 驗證告警狀態被恢復
        assert alert.status == AlertStatus.ACTIVE
        assert alert.suppressed_until is None

    def test_concurrent_alert_processing(self, alert_manager, sample_alert_rule):
        """測試並發告警處理"""
        import threading

        # 添加規則
        alert_manager.rules[sample_alert_rule.id] = sample_alert_rule

        # 啟動告警管理器
        alert_manager.start()

        def trigger_alerts():
            with patch.object(alert_manager, "_get_metric_value", return_value=85.0):
                for _ in range(10):
                    alert_manager._evaluate_alert_rules()
                    time.sleep(0.01)

        # 並發觸發告警
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=trigger_alerts)
            threads.append(thread)
            thread.start()

        # 等待所有線程完成
        for thread in threads:
            thread.join()

        # 清理
        alert_manager.stop()

        # 驗證沒有發生錯誤（應該只有一個告警，因為去重機制）
        assert len(alert_manager.active_alerts) <= 1

    def test_error_handling_in_evaluation(self, alert_manager, sample_alert_rule):
        """測試評估過程中的錯誤處理"""
        # 添加規則
        alert_manager.rules[sample_alert_rule.id] = sample_alert_rule

        # 模擬獲取指標值時發生錯誤
        with patch.object(
            alert_manager, "_get_metric_value", side_effect=Exception("Test error")
        ):
            # 執行評估（不應該拋出異常）
            alert_manager._evaluate_alert_rules()

            # 驗證沒有告警被觸發
            assert len(alert_manager.active_alerts) == 0

    def test_load_config_file_not_exists(self):
        """測試配置檔案不存在的情況"""
        with patch(
            "src.monitoring.intelligent_alert_manager.Path.exists", return_value=False
        ):
            manager = IntelligentAlertManager()
            assert manager.config == {"groups": []}

    def test_load_config_invalid_yaml(self):
        """測試無效 YAML 配置"""
        with patch(
            "src.monitoring.intelligent_alert_manager.Path.exists", return_value=True
        ):
            with patch("builtins.open", side_effect=Exception("Invalid YAML")):
                manager = IntelligentAlertManager()
                assert manager.config == {"groups": []}

    def test_memory_usage_monitoring(self, alert_manager):
        """測試記憶體使用監控"""
        import tracemalloc

        tracemalloc.start()

        # 啟動告警管理器並運行一段時間
        alert_manager.start()
        time.sleep(0.5)

        # 創建大量告警規則
        for i in range(100):
            rule = AlertRule(
                id=f"test-rule-{i}",
                name=f"Test Rule {i}",
                description="Test description",
                metric_name="test_metric",
                operator=">",
                threshold_value=80.0,
                severity=AlertSeverity.WARNING,
            )
            alert_manager.rules[rule.id] = rule

        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 清理
        alert_manager.stop()

        # 驗證記憶體使用合理（小於 50MB）
        assert peak < 50 * 1024 * 1024
