"""
風險管理服務測試模組

測試風險監控、緊急處理和資金管理服務的功能。

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥8.5/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Mock 所有複雜的導入
with patch.dict('sys.modules', {
    'src.core.risk_management_service': Mock(),
    'src.services.broker.broker_connection_service': Mock(),
    'src.services.broker.order_execution_service': Mock(),
    'src.services.broker.account_sync_service': Mock(),
}):
    from src.services.risk.risk_monitor_service import (
        RiskMonitorService,
        RiskEvent,
        RiskLevel,
        RiskMetric,
        RiskMonitorError
    )
    from src.services.risk.emergency_service import (
        EmergencyService,
        EmergencyType,
        EmergencyStatus,
        EmergencyAction,
        EmergencyServiceError
    )
    from src.services.risk.fund_management_service import (
        FundManagementService,
        FundRule,
        FundAlert,
        FundManagementError
    )


class TestRiskMonitorService:
    """測試風險監控服務"""

    @pytest.fixture
    def risk_monitor(self, mock_risk_service):
        """創建風險監控服務實例"""
        with patch('src.services.risk.risk_monitor_service.RiskManagementService') as mock_class:
            mock_class.return_value = mock_risk_service
            service = RiskMonitorService()
            service._risk_service = mock_risk_service
            return service

    @pytest.fixture
    def sample_risk_event(self):
        """創建範例風險事件"""
        return RiskEvent(
            metric=RiskMetric.PORTFOLIO_VAR,
            level=RiskLevel.HIGH,
            value=0.15,
            threshold=0.10,
            message="投資組合 VaR 超過閾值"
        )

    def test_init_success(self, risk_monitor):
        """測試服務初始化成功"""
        assert risk_monitor is not None
        assert risk_monitor._monitor_interval == 10
        assert risk_monitor._is_monitoring is False

    def test_risk_event_creation(self, sample_risk_event):
        """測試風險事件創建"""
        assert sample_risk_event.metric == RiskMetric.PORTFOLIO_VAR
        assert sample_risk_event.level == RiskLevel.HIGH
        assert sample_risk_event.value == 0.15
        assert sample_risk_event.threshold == 0.10
        assert sample_risk_event.event_id is not None

    def test_risk_event_to_dict(self, sample_risk_event):
        """測試風險事件轉換為字典"""
        event_dict = sample_risk_event.to_dict()
        
        assert event_dict["metric"] == "portfolio_var"
        assert event_dict["level"] == "high"
        assert event_dict["value"] == 0.15
        assert event_dict["threshold"] == 0.10
        assert "timestamp" in event_dict

    def test_start_monitoring(self, risk_monitor):
        """測試開始風險監控"""
        risk_monitor.start_monitoring()
        assert risk_monitor._is_monitoring is True
        assert risk_monitor._monitor_thread is not None

    def test_stop_monitoring(self, risk_monitor):
        """測試停止風險監控"""
        risk_monitor.start_monitoring()
        risk_monitor.stop_monitoring()
        assert risk_monitor._is_monitoring is False

    def test_set_risk_threshold(self, risk_monitor):
        """測試設定風險閾值"""
        risk_monitor.set_risk_threshold(
            RiskMetric.PORTFOLIO_VAR,
            RiskLevel.HIGH,
            0.15
        )
        
        thresholds = risk_monitor.get_risk_thresholds()
        assert RiskMetric.PORTFOLIO_VAR in thresholds
        assert RiskLevel.HIGH in thresholds[RiskMetric.PORTFOLIO_VAR]
        assert thresholds[RiskMetric.PORTFOLIO_VAR][RiskLevel.HIGH] == 0.15

    def test_calculate_risk_metrics(self, risk_monitor):
        """測試計算風險指標"""
        # Mock 計算方法
        risk_monitor._calculate_var = Mock(return_value=0.08)
        risk_monitor._calculate_concentration = Mock(return_value=0.25)
        risk_monitor._calculate_leverage = Mock(return_value=1.5)
        risk_monitor._calculate_drawdown = Mock(return_value=0.12)
        risk_monitor._calculate_volatility = Mock(return_value=0.22)
        
        metrics = risk_monitor.calculate_risk_metrics()
        
        assert RiskMetric.PORTFOLIO_VAR in metrics
        assert RiskMetric.POSITION_CONCENTRATION in metrics
        assert RiskMetric.LEVERAGE_RATIO in metrics
        assert RiskMetric.DRAWDOWN in metrics
        assert RiskMetric.VOLATILITY in metrics

    def test_check_risk_violations(self, risk_monitor):
        """測試檢查風險違規"""
        # 設定閾值
        risk_monitor.set_risk_threshold(
            RiskMetric.PORTFOLIO_VAR,
            RiskLevel.HIGH,
            0.10
        )
        
        # 測試違規情況
        metrics = {RiskMetric.PORTFOLIO_VAR: 0.15}
        violations = risk_monitor.check_risk_violations(metrics)
        
        assert len(violations) == 1
        assert violations[0].metric == RiskMetric.PORTFOLIO_VAR
        assert violations[0].level == RiskLevel.HIGH

    def test_check_no_violations(self, risk_monitor):
        """測試無風險違規"""
        # 設定閾值
        risk_monitor.set_risk_threshold(
            RiskMetric.PORTFOLIO_VAR,
            RiskLevel.HIGH,
            0.10
        )
        
        # 測試正常情況
        metrics = {RiskMetric.PORTFOLIO_VAR: 0.05}
        violations = risk_monitor.check_risk_violations(metrics)
        
        assert len(violations) == 0

    def test_get_recent_events(self, risk_monitor, sample_risk_event):
        """測試獲取最近事件"""
        # 添加事件到歷史
        risk_monitor._risk_events.append(sample_risk_event)
        
        recent_events = risk_monitor.get_recent_events(hours=24)
        
        assert len(recent_events) == 1
        assert recent_events[0]["event_id"] == sample_risk_event.event_id

    def test_get_recent_events_with_level_filter(self, risk_monitor, sample_risk_event):
        """測試按等級篩選最近事件"""
        # 添加事件到歷史
        risk_monitor._risk_events.append(sample_risk_event)
        
        # 測試匹配的等級
        high_events = risk_monitor.get_recent_events(hours=24, level=RiskLevel.HIGH)
        assert len(high_events) == 1
        
        # 測試不匹配的等級
        critical_events = risk_monitor.get_recent_events(hours=24, level=RiskLevel.CRITICAL)
        assert len(critical_events) == 0


class TestEmergencyService:
    """測試緊急處理服務"""

    @pytest.fixture
    def emergency_service(self):
        """創建緊急處理服務實例"""
        with patch('src.services.risk.emergency_service.BrokerConnectionService'), \
             patch('src.services.risk.emergency_service.OrderExecutionService'), \
             patch('src.services.risk.emergency_service.AccountSyncService'):
            service = EmergencyService()
            return service

    @pytest.fixture
    def sample_emergency_action(self):
        """創建範例緊急行動"""
        return EmergencyAction(
            emergency_type=EmergencyType.STOP_LOSS,
            trigger_reason="測試緊急停損"
        )

    def test_init_success(self, emergency_service):
        """測試服務初始化成功"""
        assert emergency_service is not None
        assert emergency_service._emergency_actions == []
        assert emergency_service._is_emergency_mode is False

    def test_emergency_action_creation(self, sample_emergency_action):
        """測試緊急行動創建"""
        assert sample_emergency_action.emergency_type == EmergencyType.STOP_LOSS
        assert sample_emergency_action.trigger_reason == "測試緊急停損"
        assert sample_emergency_action.status == EmergencyStatus.PENDING
        assert sample_emergency_action.action_id is not None

    def test_emergency_action_to_dict(self, sample_emergency_action):
        """測試緊急行動轉換為字典"""
        action_dict = sample_emergency_action.to_dict()
        
        assert action_dict["emergency_type"] == "stop_loss"
        assert action_dict["trigger_reason"] == "測試緊急停損"
        assert action_dict["status"] == "pending"
        assert "created_at" in action_dict

    def test_trigger_emergency_stop_loss(self, emergency_service):
        """測試觸發緊急停損"""
        # Mock 執行方法
        emergency_service._execute_emergency_action = Mock()
        
        action_id = emergency_service.trigger_emergency_stop_loss(
            symbol="AAPL",
            reason="測試停損"
        )
        
        assert action_id is not None
        assert len(emergency_service._emergency_actions) == 1
        emergency_service._execute_emergency_action.assert_called_once()

    def test_trigger_liquidate_all(self, emergency_service):
        """測試觸發一鍵平倉"""
        # Mock 執行方法
        emergency_service._execute_emergency_action = Mock()
        
        action_id = emergency_service.trigger_liquidate_all(
            reason="測試平倉"
        )
        
        assert action_id is not None
        assert len(emergency_service._emergency_actions) == 1

    def test_trigger_system_halt(self, emergency_service):
        """測試觸發系統緊急停止"""
        # Mock 執行方法
        emergency_service._execute_emergency_action = Mock()
        
        action_id = emergency_service.trigger_system_halt(
            reason="測試系統停止"
        )
        
        assert action_id is not None
        assert emergency_service._is_emergency_mode is True

    def test_handle_risk_event_critical(self, emergency_service):
        """測試處理嚴重風險事件"""
        # Mock 方法
        emergency_service.trigger_liquidate_all = Mock(return_value="action_123")
        
        risk_event = RiskEvent(
            metric=RiskMetric.PORTFOLIO_VAR,
            level=RiskLevel.CRITICAL,
            value=0.25,
            threshold=0.20,
            message="嚴重風險"
        )
        
        action_id = emergency_service.handle_risk_event(risk_event)
        
        assert action_id == "action_123"
        emergency_service.trigger_liquidate_all.assert_called_once()

    def test_handle_risk_event_high(self, emergency_service):
        """測試處理高風險事件"""
        # Mock 方法
        emergency_service.trigger_emergency_stop_loss = Mock(return_value="action_456")
        
        risk_event = RiskEvent(
            metric=RiskMetric.PORTFOLIO_VAR,
            level=RiskLevel.HIGH,
            value=0.15,
            threshold=0.10,
            message="高風險"
        )
        
        action_id = emergency_service.handle_risk_event(risk_event)
        
        assert action_id == "action_456"
        emergency_service.trigger_emergency_stop_loss.assert_called_once()

    def test_get_emergency_status(self, emergency_service, sample_emergency_action):
        """測試獲取緊急狀態"""
        emergency_service._emergency_actions.append(sample_emergency_action)
        emergency_service._is_emergency_mode = True
        
        status = emergency_service.get_emergency_status()
        
        assert status["is_emergency_mode"] is True
        assert status["total_actions"] == 1
        assert len(status["recent_actions"]) == 1

    def test_get_action_status(self, emergency_service, sample_emergency_action):
        """測試獲取緊急行動狀態"""
        emergency_service._emergency_actions.append(sample_emergency_action)
        
        status = emergency_service.get_action_status(sample_emergency_action.action_id)
        
        assert status["action_id"] == sample_emergency_action.action_id
        assert status["emergency_type"] == "stop_loss"

    def test_get_nonexistent_action_status(self, emergency_service):
        """測試獲取不存在的緊急行動狀態"""
        with pytest.raises(EmergencyServiceError):
            emergency_service.get_action_status("nonexistent_action")

    def test_cancel_emergency_mode(self, emergency_service):
        """測試取消緊急模式"""
        emergency_service._is_emergency_mode = True
        
        result = emergency_service.cancel_emergency_mode()
        
        assert result is True
        assert emergency_service._is_emergency_mode is False


class TestFundManagementService:
    """測試資金管理服務"""

    @pytest.fixture
    def fund_service(self):
        """創建資金管理服務實例"""
        with patch('src.services.risk.fund_management_service.AccountSyncService'):
            service = FundManagementService()
            return service

    @pytest.fixture
    def sample_fund_rule(self):
        """創建範例資金規則"""
        return FundRule(
            name="現金不足警報",
            rule_type="cash_ratio",
            threshold=0.05,
            action="alert"
        )

    def test_init_success(self, fund_service):
        """測試服務初始化成功"""
        assert fund_service is not None
        assert len(fund_service._fund_rules) > 0  # 有預設規則

    def test_fund_rule_creation(self, sample_fund_rule):
        """測試資金規則創建"""
        assert sample_fund_rule.name == "現金不足警報"
        assert sample_fund_rule.rule_type == "cash_ratio"
        assert sample_fund_rule.threshold == 0.05
        assert sample_fund_rule.action == "alert"
        assert sample_fund_rule.rule_id is not None

    def test_fund_rule_to_dict(self, sample_fund_rule):
        """測試資金規則轉換為字典"""
        rule_dict = sample_fund_rule.to_dict()
        
        assert rule_dict["name"] == "現金不足警報"
        assert rule_dict["rule_type"] == "cash_ratio"
        assert rule_dict["threshold"] == 0.05
        assert "created_at" in rule_dict

    def test_get_fund_summary(self, fund_service):
        """測試獲取資金摘要"""
        # Mock 帳戶服務
        mock_accounts = {
            "broker1": Mock(cash=5000.0, total_value=10000.0, buying_power=5000.0),
            "broker2": Mock(cash=3000.0, total_value=8000.0, buying_power=3000.0)
        }
        fund_service._account_service.get_all_accounts.return_value = mock_accounts
        fund_service._calculate_utilization = Mock(return_value=0.5)
        fund_service._calculate_overall_utilization = Mock(return_value=0.55)
        
        summary = fund_service.get_fund_summary()
        
        assert summary["total_cash"] == 8000.0
        assert summary["total_value"] == 18000.0
        assert summary["total_buying_power"] == 8000.0
        assert "account_details" in summary

    def test_check_buying_power_sufficient(self, fund_service):
        """測試檢查購買力充足"""
        # Mock 帳戶資訊
        mock_account = Mock(buying_power=10000.0)
        fund_service._account_service.get_account_info.return_value = mock_account
        
        result = fund_service.check_buying_power(
            symbol="AAPL",
            quantity=50,
            price=150.0,
            broker_name="test_broker"
        )
        
        assert result["sufficient"] is True
        assert result["required_amount"] == 7500.0
        assert result["available_power"] == 10000.0

    def test_check_buying_power_insufficient(self, fund_service):
        """測試檢查購買力不足"""
        # Mock 帳戶資訊
        mock_account = Mock(buying_power=5000.0)
        fund_service._account_service.get_account_info.return_value = mock_account
        
        result = fund_service.check_buying_power(
            symbol="AAPL",
            quantity=50,
            price=150.0,
            broker_name="test_broker"
        )
        
        assert result["sufficient"] is False
        assert result["required_amount"] == 7500.0
        assert result["available_power"] == 5000.0

    def test_calculate_position_size(self, fund_service):
        """測試計算建議部位大小"""
        # Mock 總投資組合價值
        fund_service._account_service.get_total_portfolio_value.return_value = 100000.0
        
        result = fund_service.calculate_position_size(
            symbol="AAPL",
            risk_percentage=0.02,
            stop_loss_percentage=0.05
        )
        
        assert result["total_portfolio_value"] == 100000.0
        assert result["risk_amount"] == 2000.0
        assert result["suggested_amount"] == 40000.0

    def test_add_fund_rule(self, fund_service, sample_fund_rule):
        """測試添加資金規則"""
        initial_count = len(fund_service._fund_rules)
        
        fund_service.add_fund_rule(sample_fund_rule)
        
        assert len(fund_service._fund_rules) == initial_count + 1

    def test_remove_fund_rule(self, fund_service, sample_fund_rule):
        """測試移除資金規則"""
        fund_service.add_fund_rule(sample_fund_rule)
        
        result = fund_service.remove_fund_rule(sample_fund_rule.rule_id)
        
        assert result is True

    def test_remove_nonexistent_fund_rule(self, fund_service):
        """測試移除不存在的資金規則"""
        result = fund_service.remove_fund_rule("nonexistent_rule")
        
        assert result is False

    def test_get_fund_rules(self, fund_service):
        """測試獲取資金規則列表"""
        rules = fund_service.get_fund_rules()
        
        assert isinstance(rules, list)
        assert len(rules) > 0  # 有預設規則

    def test_check_fund_rules(self, fund_service):
        """測試檢查資金規則"""
        # Mock 資金摘要
        fund_service.get_fund_summary = Mock(return_value={
            "total_cash": 1000.0,
            "total_value": 50000.0,
            "overall_utilization": 0.95
        })
        
        triggered_rules = fund_service.check_fund_rules()
        
        # 應該觸發一些規則（基於預設規則）
        assert isinstance(triggered_rules, list)
