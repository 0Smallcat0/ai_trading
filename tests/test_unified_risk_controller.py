"""
統一風險控制器測試

測試整合的風險控制系統功能，包括：
- 統一風險狀態監控
- 交易風險驗證
- 緊急措施觸發
- 模組間協調
"""

import pytest
import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from src.risk.live.unified_risk_controller import UnifiedRiskController
from src.risk.live.stop_loss_strategies import StopLossStrategy
from src.risk.live.emergency_risk_control import EmergencyLevel, EmergencyAction


class TestUnifiedRiskController(unittest.TestCase):
    """統一風險控制器測試類別"""
    
    def setUp(self):
        """設置測試環境"""
        self.mock_broker = Mock()
        self.risk_controller = UnifiedRiskController(self.mock_broker)
        
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
        
        self.mock_broker.get_account_info.return_value = self.mock_account_info
        self.mock_broker.get_positions.return_value = self.mock_positions
    
    def test_start_stop_risk_control(self):
        """測試啟動和停止風險控制"""
        # 測試啟動
        self.assertFalse(self.risk_controller.risk_control_active)
        self.risk_controller.start_risk_control()
        self.assertTrue(self.risk_controller.risk_control_active)
        
        # 測試停止
        self.risk_controller.stop_risk_control()
        self.assertFalse(self.risk_controller.risk_control_active)
    
    def test_get_overall_risk_status(self):
        """測試獲取整體風險狀態"""
        # 設置資金狀態
        self.risk_controller.fund_monitor.fund_status = {
            "cash": 100000,
            "total_value": 150000,
            "margin_used": 30000,
            "margin_available": 70000,
            "margin_usage_rate": 0.3,
            "last_update": datetime.now(),
        }
        
        status = self.risk_controller.get_overall_risk_status()
        
        # 檢查狀態結構
        self.assertIn("risk_control_active", status)
        self.assertIn("overall_risk_level", status)
        self.assertIn("fund_status", status)
        self.assertIn("risk_metrics", status)
        self.assertIn("emergency_status", status)
        self.assertIn("risk_warnings", status)
        
        # 檢查風險級別
        self.assertIn(status["overall_risk_level"], ["normal", "warning", "critical", "emergency", "unknown"])
    
    def test_validate_new_trade_approved(self):
        """測試交易驗證 - 通過"""
        # 設置充足的資金狀態
        self.risk_controller.fund_monitor.fund_status = {
            "cash": 100000,
            "buying_power": 200000,
            "total_value": 150000,
            "margin_used": 20000,
            "margin_available": 80000,
        }
        
        result = self.risk_controller.validate_new_trade(
            symbol="NVDA",
            quantity=50,
            price=300.0,
            trade_type="buy"
        )
        
        self.assertTrue(result.get("approved", False))
        self.assertEqual(result.get("risk_level"), "low")
        self.assertIn("feasibility", result)
        self.assertIn("leverage_check", result)
    
    def test_validate_new_trade_rejected_insufficient_funds(self):
        """測試交易驗證 - 資金不足被拒絕"""
        # 設置資金不足的狀態
        self.risk_controller.fund_monitor.fund_status = {
            "cash": 5000,  # 資金不足
            "buying_power": 10000,
            "total_value": 150000,
            "margin_used": 80000,
            "margin_available": 20000,
        }
        
        result = self.risk_controller.validate_new_trade(
            symbol="NVDA",
            quantity=100,
            price=300.0,  # 需要30000，但只有5000現金
            trade_type="buy"
        )
        
        self.assertFalse(result.get("approved", True))
        self.assertIn("資金不足", result.get("reason", ""))
        self.assertEqual(result.get("risk_level"), "high")
    
    def test_validate_new_trade_rejected_trading_suspended(self):
        """測試交易驗證 - 交易暫停被拒絕"""
        # 設置交易暫停狀態
        self.risk_controller.emergency_control.trading_suspended = True
        
        result = self.risk_controller.validate_new_trade(
            symbol="AAPL",
            quantity=10,
            price=150.0,
            trade_type="buy"
        )
        
        self.assertFalse(result.get("approved", True))
        self.assertIn("交易已暫停", result.get("reason", ""))
        self.assertEqual(result.get("risk_level"), "emergency")
    
    def test_validate_new_trade_concentration_check(self):
        """測試交易驗證 - 持倉集中度檢查"""
        # 設置總價值較小，使持倉集中度過高
        self.risk_controller.fund_monitor.fund_status = {
            "cash": 100000,
            "total_value": 50000,  # 較小的總價值
        }
        
        # 嘗試買入大量股票（超過20%限制）
        result = self.risk_controller.validate_new_trade(
            symbol="NVDA",
            quantity=100,
            price=150.0,  # 15000，佔總價值30%
            trade_type="buy"
        )
        
        self.assertFalse(result.get("approved", True))
        self.assertIn("持倉集中度", result.get("reason", ""))
        self.assertEqual(result.get("risk_level"), "medium")
    
    def test_set_position_stop_loss(self):
        """測試設置持倉停損"""
        result = self.risk_controller.set_position_stop_loss(
            symbol="AAPL",
            strategy=StopLossStrategy.TRAILING,
            custom_params={"trail_percent": 0.02}
        )
        
        # 檢查結果結構
        self.assertIn("success", result)
    
    def test_trigger_emergency_action(self):
        """測試觸發緊急行動"""
        result = self.risk_controller.trigger_emergency_action(
            level=EmergencyLevel.HIGH,
            reason="測試緊急情況",
            custom_actions=[EmergencyAction.SUSPEND_TRADING]
        )
        
        # 檢查結果
        self.assertIn("success", result)
        self.assertIn("level", result)
        self.assertEqual(result.get("level"), "high")
    
    def test_get_risk_dashboard_data(self):
        """測試獲取風險儀表板數據"""
        dashboard_data = self.risk_controller.get_risk_dashboard_data()
        
        # 檢查儀表板數據結構
        self.assertIn("overall_status", dashboard_data)
        self.assertIn("fund_history", dashboard_data)
        self.assertIn("stop_loss_performance", dashboard_data)
        self.assertIn("recent_emergency_events", dashboard_data)
        self.assertIn("risk_parameters", dashboard_data)
        self.assertIn("module_status", dashboard_data)
        
        # 檢查模組狀態
        module_status = dashboard_data["module_status"]
        self.assertIn("fund_monitor", module_status)
        self.assertIn("dynamic_stop_loss", module_status)
        self.assertIn("emergency_control", module_status)
    
    def test_update_risk_parameters(self):
        """測試更新風險參數"""
        original_leverage = self.risk_controller.risk_params["max_leverage"]
        
        success = self.risk_controller.update_risk_parameters(
            max_leverage=2.5,
            max_position_weight=0.15
        )
        
        self.assertTrue(success)
        self.assertEqual(self.risk_controller.risk_params["max_leverage"], 2.5)
        self.assertEqual(self.risk_controller.risk_params["max_position_weight"], 0.15)
    
    def test_calculate_overall_risk_level_normal(self):
        """測試計算整體風險級別 - 正常"""
        fund_analysis = {
            "risk_metrics": {
                "leverage_ratio": 1.5,
                "margin_utilization": 0.3,
                "max_position_weight": 0.1,
            }
        }
        
        emergency_status = {"emergency_active": False}
        
        risk_level = self.risk_controller._calculate_overall_risk_level(fund_analysis, emergency_status)
        self.assertEqual(risk_level, "normal")
    
    def test_calculate_overall_risk_level_warning(self):
        """測試計算整體風險級別 - 警告"""
        fund_analysis = {
            "risk_metrics": {
                "leverage_ratio": 2.5,  # 接近限制
                "margin_utilization": 0.75,  # 超過警告閾值
                "max_position_weight": 0.25,  # 超過限制
            }
        }
        
        emergency_status = {"emergency_active": False}
        
        risk_level = self.risk_controller._calculate_overall_risk_level(fund_analysis, emergency_status)
        self.assertEqual(risk_level, "warning")
    
    def test_calculate_overall_risk_level_critical(self):
        """測試計算整體風險級別 - 危險"""
        fund_analysis = {
            "risk_metrics": {
                "leverage_ratio": 3.5,  # 超過限制
                "margin_utilization": 0.9,  # 超過危險閾值
                "max_position_weight": 0.35,  # 遠超限制
            }
        }
        
        emergency_status = {"emergency_active": False}
        
        risk_level = self.risk_controller._calculate_overall_risk_level(fund_analysis, emergency_status)
        self.assertEqual(risk_level, "critical")
    
    def test_calculate_overall_risk_level_emergency(self):
        """測試計算整體風險級別 - 緊急"""
        fund_analysis = {"risk_metrics": {}}
        emergency_status = {"emergency_active": True}
        
        risk_level = self.risk_controller._calculate_overall_risk_level(fund_analysis, emergency_status)
        self.assertEqual(risk_level, "emergency")
    
    def test_generate_risk_warnings(self):
        """測試生成風險警告"""
        fund_analysis = {
            "risk_metrics": {
                "leverage_ratio": 3.5,  # 超過限制
                "margin_utilization": 0.9,  # 超過危險閾值
                "max_position_weight": 0.25,  # 超過限制
                "unrealized_pnl_ratio": -0.08,  # 超過最大損失
            }
        }
        
        warnings = self.risk_controller._generate_risk_warnings(fund_analysis)
        
        self.assertGreater(len(warnings), 0)
        
        # 檢查是否包含預期的警告
        warning_text = " ".join(warnings)
        self.assertIn("槓桿比例過高", warning_text)
        self.assertIn("保證金使用率危險", warning_text)
        self.assertIn("持倉集中度過高", warning_text)
        self.assertIn("未實現損失過大", warning_text)


if __name__ == "__main__":
    unittest.main()
