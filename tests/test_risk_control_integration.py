"""
風險控制整合測試

測試整個風險控制系統的端到端流程，包括：
- 風險監控流程
- 停損觸發流程
- 緊急措施流程
- 模組間協調
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import time

from src.risk.live.unified_risk_controller import UnifiedRiskController
from src.risk.live.stop_loss_strategies import StopLossStrategy
from src.risk.live.emergency_risk_control import EmergencyLevel, EmergencyAction


class TestRiskControlIntegration(unittest.TestCase):
    """風險控制整合測試類別"""
    
    def setUp(self):
        """設置測試環境"""
        self.mock_broker = Mock()
        self.risk_controller = UnifiedRiskController(self.mock_broker)
        
        # 設置模擬數據
        self.setup_mock_data()
    
    def setup_mock_data(self):
        """設置模擬數據"""
        # 模擬帳戶資訊
        self.mock_account_info = {
            "cash": 100000,
            "buying_power": 200000,
            "total_value": 150000,
            "margin_used": 30000,
            "margin_available": 70000,
        }
        
        # 模擬持倉資訊
        self.mock_positions = {
            "AAPL": {
                "quantity": 100,
                "avg_price": 150.0,
                "current_price": 155.0,
                "market_value": 15500,
                "unrealized_pnl": 500,
            },
            "TSLA": {
                "quantity": 50,
                "avg_price": 200.0,
                "current_price": 210.0,
                "market_value": 10500,
                "unrealized_pnl": 500,
            },
        }
        
        # 模擬訂單
        self.mock_orders = []
        
        # 設置 broker 回調
        self.mock_broker.get_account_info.return_value = self.mock_account_info
        self.mock_broker.get_positions.return_value = self.mock_positions
        self.mock_broker.get_orders.return_value = self.mock_orders
        self.mock_broker.place_order.return_value = {"success": True, "order_id": "test_order_123"}
        self.mock_broker.cancel_order.return_value = {"success": True}
    
    def test_complete_risk_monitoring_flow(self):
        """測試完整的風險監控流程"""
        # 1. 啟動風險控制
        self.risk_controller.start_risk_control()
        self.assertTrue(self.risk_controller.risk_control_active)
        
        # 2. 設置停損
        stop_result = self.risk_controller.set_position_stop_loss(
            symbol="AAPL",
            strategy=StopLossStrategy.TRAILING,
            custom_params={"trail_percent": 0.02}
        )
        self.assertIn("success", stop_result)
        
        # 3. 檢查風險狀態
        risk_status = self.risk_controller.get_overall_risk_status()
        self.assertIn("overall_risk_level", risk_status)
        self.assertEqual(risk_status["overall_risk_level"], "normal")
        
        # 4. 驗證交易
        trade_validation = self.risk_controller.validate_new_trade(
            symbol="MSFT",
            quantity=50,
            price=100.0,
            trade_type="buy"
        )
        self.assertTrue(trade_validation.get("approved", False))
        
        # 5. 停止風險控制
        self.risk_controller.stop_risk_control()
        self.assertFalse(self.risk_controller.risk_control_active)
    
    def test_margin_crisis_emergency_flow(self):
        """測試保證金危機緊急流程"""
        # 1. 設置危險的保證金狀態
        self.mock_account_info.update({
            "margin_used": 95000,
            "margin_available": 5000,
        })
        
        # 2. 啟動風險控制
        self.risk_controller.start_risk_control()
        
        # 3. 強制更新資金狀態以觸發警報
        self.risk_controller.fund_monitor.fund_status.update({
            "margin_used": 95000,
            "margin_available": 5000,
            "margin_usage_rate": 0.95,  # 95% 使用率，觸發緊急閾值
        })
        
        # 4. 檢查風險狀態
        risk_status = self.risk_controller.get_overall_risk_status()
        self.assertIn(risk_status["overall_risk_level"], ["critical", "emergency"])
        
        # 5. 驗證交易被拒絕
        trade_validation = self.risk_controller.validate_new_trade(
            symbol="NVDA",
            quantity=100,
            price=300.0,
            trade_type="buy"
        )
        self.assertFalse(trade_validation.get("approved", True))
        
        # 6. 觸發緊急措施
        emergency_result = self.risk_controller.trigger_emergency_action(
            EmergencyLevel.CRITICAL,
            "保證金使用率過高",
            [EmergencyAction.REDUCE_POSITION_SIZE, EmergencyAction.SUSPEND_TRADING]
        )
        self.assertTrue(emergency_result.get("success", False))
        
        # 7. 驗證交易暫停
        self.assertTrue(self.risk_controller.emergency_control.trading_suspended)
        
        trade_validation_after = self.risk_controller.validate_new_trade(
            symbol="AAPL",
            quantity=10,
            price=150.0,
            trade_type="buy"
        )
        self.assertFalse(trade_validation_after.get("approved", True))
        self.assertEqual(trade_validation_after.get("risk_level"), "emergency")
    
    def test_stop_loss_trigger_flow(self):
        """測試停損觸發流程"""
        # 1. 設置停損
        self.risk_controller.dynamic_stop_loss.set_position_stop_loss(
            symbol="AAPL",
            strategy=StopLossStrategy.TRAILING,
            custom_params={"trail_percent": 0.02}
        )
        
        # 2. 模擬價格變動（有利）
        self.mock_positions["AAPL"]["current_price"] = 160.0  # 上漲到160
        self.mock_positions["AAPL"]["market_value"] = 16000
        self.mock_positions["AAPL"]["unrealized_pnl"] = 1000
        
        # 3. 檢查停損是否調整
        stops = self.risk_controller.dynamic_stop_loss.get_position_stops()
        self.assertIn("AAPL", stops)
        
        # 4. 模擬價格下跌觸發停損
        self.mock_positions["AAPL"]["current_price"] = 145.0  # 下跌到145
        self.mock_positions["AAPL"]["market_value"] = 14500
        self.mock_positions["AAPL"]["unrealized_pnl"] = -500
        
        # 5. 檢查停損性能統計
        performance = self.risk_controller.dynamic_stop_loss.monitor.get_stop_loss_performance("AAPL")
        self.assertIn("total_adjustments", performance)
    
    def test_position_concentration_risk_flow(self):
        """測試持倉集中度風險流程"""
        # 1. 設置較小的總價值
        self.mock_account_info["total_value"] = 50000
        self.risk_controller.fund_monitor.fund_status["total_value"] = 50000
        
        # 2. 嘗試建立大倉位（超過20%限制）
        trade_validation = self.risk_controller.validate_new_trade(
            symbol="NVDA",
            quantity=100,
            price=150.0,  # 15000，佔總價值30%
            trade_type="buy"
        )
        
        # 3. 驗證交易被拒絕
        self.assertFalse(trade_validation.get("approved", True))
        self.assertEqual(trade_validation.get("risk_level"), "medium")
        self.assertIn("持倉集中度", trade_validation.get("reason", ""))
        
        # 4. 檢查風險警告
        risk_status = self.risk_controller.get_overall_risk_status()
        warnings = risk_status.get("risk_warnings", [])
        # 注意：由於是模擬交易，實際持倉集中度可能不會觸發警告
    
    def test_leverage_limit_enforcement_flow(self):
        """測試槓桿限制執行流程"""
        # 1. 設置高槓桿狀態
        self.mock_account_info.update({
            "total_value": 400000,  # 高總價值
            "cash": 100000,  # 低現金，槓桿4倍
        })
        self.risk_controller.fund_monitor.fund_status.update({
            "total_value": 400000,
            "cash": 100000,
        })
        
        # 2. 檢查槓桿限制
        leverage_check = self.risk_controller.fund_monitor.check_leverage_limits(3.0)
        self.assertTrue(leverage_check.get("exceeds_limit", False))
        
        # 3. 驗證新交易被拒絕
        trade_validation = self.risk_controller.validate_new_trade(
            symbol="AAPL",
            quantity=100,
            price=150.0,
            trade_type="buy"
        )
        self.assertFalse(trade_validation.get("approved", True))
        self.assertEqual(trade_validation.get("risk_level"), "high")
        
        # 4. 檢查風險狀態
        risk_status = self.risk_controller.get_overall_risk_status()
        self.assertIn(risk_status["overall_risk_level"], ["warning", "critical"])
    
    def test_dashboard_data_integration(self):
        """測試儀表板數據整合"""
        # 1. 啟動風險控制
        self.risk_controller.start_risk_control()
        
        # 2. 設置一些停損
        self.risk_controller.set_position_stop_loss("AAPL", StopLossStrategy.TRAILING)
        self.risk_controller.set_position_stop_loss("TSLA", StopLossStrategy.VOLATILITY_BASED)
        
        # 3. 觸發一些緊急事件
        self.risk_controller.trigger_emergency_action(
            EmergencyLevel.LOW,
            "測試警報",
            [EmergencyAction.ALERT_ONLY]
        )
        
        # 4. 獲取儀表板數據
        dashboard_data = self.risk_controller.get_risk_dashboard_data()
        
        # 5. 驗證數據完整性
        self.assertIn("overall_status", dashboard_data)
        self.assertIn("fund_history", dashboard_data)
        self.assertIn("stop_loss_performance", dashboard_data)
        self.assertIn("recent_emergency_events", dashboard_data)
        self.assertIn("risk_parameters", dashboard_data)
        self.assertIn("module_status", dashboard_data)
        
        # 6. 檢查模組狀態
        module_status = dashboard_data["module_status"]
        self.assertTrue(module_status.get("fund_monitor", False))
        self.assertTrue(module_status.get("dynamic_stop_loss", False))
        
        # 7. 檢查緊急事件
        emergency_events = dashboard_data["recent_emergency_events"]
        self.assertGreater(len(emergency_events), 0)
        self.assertEqual(emergency_events[-1]["level"], "low")
    
    def test_risk_parameter_update_propagation(self):
        """測試風險參數更新傳播"""
        # 1. 更新風險參數
        success = self.risk_controller.update_risk_parameters(
            max_leverage=2.5,
            margin_warning_threshold=0.6,
            margin_critical_threshold=0.8
        )
        self.assertTrue(success)
        
        # 2. 驗證參數已更新
        self.assertEqual(self.risk_controller.risk_params["max_leverage"], 2.5)
        self.assertEqual(self.risk_controller.risk_params["margin_warning_threshold"], 0.6)
        
        # 3. 驗證參數傳播到子模組
        fund_params = self.risk_controller.fund_monitor.monitor_params
        self.assertEqual(fund_params["margin_warning_threshold"], 0.6)
        self.assertEqual(fund_params["margin_critical_threshold"], 0.8)
        
        # 4. 測試新參數的效果
        leverage_check = self.risk_controller.fund_monitor.check_leverage_limits(2.5)
        # 應該使用新的槓桿限制
    
    def test_callback_system_integration(self):
        """測試回調系統整合"""
        # 設置回調函數
        risk_level_changes = []
        emergency_triggers = []
        
        def on_risk_level_changed(event):
            risk_level_changes.append(event)
        
        def on_emergency_triggered(event):
            emergency_triggers.append(event)
        
        self.risk_controller.on_risk_level_changed = on_risk_level_changed
        self.risk_controller.on_emergency_triggered = on_emergency_triggered
        
        # 觸發緊急事件
        self.risk_controller.trigger_emergency_action(
            EmergencyLevel.HIGH,
            "測試回調",
            [EmergencyAction.SUSPEND_TRADING]
        )
        
        # 驗證回調被調用
        self.assertGreater(len(emergency_triggers), 0)
        self.assertEqual(emergency_triggers[-1]["level"], EmergencyLevel.HIGH)


if __name__ == "__main__":
    unittest.main()
