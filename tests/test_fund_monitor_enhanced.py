"""
增強資金監控測試

測試新增的資金監控功能，包括：
- 詳細資金分析
- 槓桿控制
- 交易可行性驗證
- 風險指標計算
"""

import pytest
import unittest
from unittest.mock import Mock, patch
from datetime import datetime

from src.risk.live.fund_monitor import FundMonitor
from src.risk.live.fund_calculator import FundCalculator, FundAlertLevel


class TestFundMonitorEnhanced(unittest.TestCase):
    """增強資金監控測試類別"""
    
    def setUp(self):
        """設置測試環境"""
        self.mock_broker = Mock()
        self.fund_monitor = FundMonitor(self.mock_broker)
        
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
                "quantity": -50,
                "avg_price": 200.0,
                "current_price": 195.0,
                "market_value": -9750,
                "unrealized_pnl": 250,
            },
            "MSFT": {
                "quantity": 200,
                "avg_price": 100.0,
                "current_price": 105.0,
                "market_value": 21000,
                "unrealized_pnl": 1000,
            },
        }
        
        self.mock_broker.get_account_info.return_value = self.mock_account_info
        self.mock_broker.get_positions.return_value = self.mock_positions
    
    def test_calculate_leverage_ratio(self):
        """測試槓桿比例計算"""
        # 設置資金狀態
        self.fund_monitor.fund_status = {
            "total_value": 150000,
            "cash": 100000,
        }
        
        leverage_ratio = self.fund_monitor.calculate_leverage_ratio()
        
        # 預期槓桿比例 = 總價值 / 現金 = 150000 / 100000 = 1.5
        self.assertAlmostEqual(leverage_ratio, 1.5, places=2)
    
    def test_calculate_available_buying_power(self):
        """測試可用購買力計算"""
        # 設置資金狀態
        self.fund_monitor.fund_status = {
            "cash": 100000,
            "margin_available": 70000,
        }
        
        buying_power = self.fund_monitor.calculate_available_buying_power()
        
        # 預期購買力 = 現金 + 可用保證金 = 100000 + 70000 = 170000
        self.assertEqual(buying_power, 170000)
    
    def test_check_margin_requirements_sufficient(self):
        """測試保證金需求檢查 - 充足情況"""
        # 設置資金狀態
        self.fund_monitor.fund_status = {
            "margin_used": 30000,
            "margin_available": 70000,
        }
        
        result = self.fund_monitor.check_margin_requirements(50000)
        
        self.assertTrue(result["sufficient"])
        self.assertEqual(result["available_margin"], 70000)
        self.assertEqual(result["required_margin"], 50000)
        self.assertEqual(result["shortage"], 0)
    
    def test_check_margin_requirements_insufficient(self):
        """測試保證金需求檢查 - 不足情況"""
        # 設置資金狀態
        self.fund_monitor.fund_status = {
            "margin_used": 30000,
            "margin_available": 70000,
        }
        
        result = self.fund_monitor.check_margin_requirements(80000)
        
        self.assertFalse(result["sufficient"])
        self.assertEqual(result["shortage"], 10000)
        self.assertTrue(result["exceeds_critical"])
    
    def test_get_detailed_fund_analysis(self):
        """測試詳細資金分析"""
        # 設置資金狀態
        self.fund_monitor.fund_status = {
            "cash": 100000,
            "total_value": 150000,
            "margin_used": 30000,
            "margin_available": 70000,
            "positions_value": 26750,  # 15500 + 9750 + 21000 - 9750 (空頭絕對值)
            "unrealized_pnl": 1750,
            "last_update": datetime.now(),
        }
        
        analysis = self.fund_monitor.get_detailed_fund_analysis()
        
        # 檢查分析結果結構
        self.assertIn("fund_summary", analysis)
        self.assertIn("risk_metrics", analysis)
        self.assertIn("position_breakdown", analysis)
        self.assertIn("analysis_timestamp", analysis)
        
        # 檢查風險指標
        risk_metrics = analysis["risk_metrics"]
        self.assertIn("leverage_ratio", risk_metrics)
        self.assertIn("margin_utilization", risk_metrics)
        self.assertIn("position_count", risk_metrics)
        
        # 檢查持倉分解
        position_breakdown = analysis["position_breakdown"]
        self.assertIn("total_position_value", position_breakdown)
        self.assertIn("position_count", position_breakdown)
        self.assertEqual(position_breakdown["position_count"], 3)
    
    def test_check_leverage_limits_within_limit(self):
        """測試槓桿限制檢查 - 在限制內"""
        # 設置資金狀態
        self.fund_monitor.fund_status = {
            "total_value": 150000,
            "cash": 100000,
        }
        
        result = self.fund_monitor.check_leverage_limits(max_leverage=3.0)
        
        self.assertFalse(result["exceeds_limit"])
        self.assertAlmostEqual(result["current_leverage"], 1.5, places=2)
        self.assertAlmostEqual(result["leverage_buffer"], 1.5, places=2)
        self.assertGreater(result["additional_buying_power"], 0)
    
    def test_check_leverage_limits_exceeds_limit(self):
        """測試槓桿限制檢查 - 超過限制"""
        # 設置資金狀態
        self.fund_monitor.fund_status = {
            "total_value": 400000,
            "cash": 100000,
        }
        
        result = self.fund_monitor.check_leverage_limits(max_leverage=3.0)
        
        self.assertTrue(result["exceeds_limit"])
        self.assertAlmostEqual(result["current_leverage"], 4.0, places=2)
        self.assertLess(result["leverage_buffer"], 0)
        self.assertEqual(result["additional_buying_power"], 0.0)
    
    def test_validate_trade_feasibility_buy_feasible(self):
        """測試交易可行性驗證 - 買入可行"""
        # 設置資金狀態
        self.fund_monitor.fund_status = {
            "cash": 100000,
            "buying_power": 200000,
            "margin_used": 30000,
            "margin_available": 70000,
            "total_value": 150000,
        }
        
        result = self.fund_monitor.validate_trade_feasibility(
            symbol="NVDA",
            quantity=100,
            price=300.0,
            trade_type="buy"
        )
        
        self.assertTrue(result["feasible"])
        self.assertEqual(result["trade_value"], 30000)
        self.assertTrue(result["cash_sufficient"])
        self.assertTrue(result["buying_power_sufficient"])
        self.assertEqual(result["cash_after_trade"], 70000)
    
    def test_validate_trade_feasibility_buy_insufficient_cash(self):
        """測試交易可行性驗證 - 買入現金不足"""
        # 設置資金狀態
        self.fund_monitor.fund_status = {
            "cash": 20000,
            "buying_power": 200000,
            "margin_used": 30000,
            "margin_available": 70000,
            "total_value": 150000,
        }
        
        result = self.fund_monitor.validate_trade_feasibility(
            symbol="NVDA",
            quantity=100,
            price=300.0,
            trade_type="buy"
        )
        
        self.assertFalse(result["feasible"])
        self.assertFalse(result["cash_sufficient"])
        self.assertIn("現金不足", " ".join(result["warnings"]))
    
    def test_validate_trade_feasibility_sell(self):
        """測試交易可行性驗證 - 賣出"""
        # 設置資金狀態
        self.fund_monitor.fund_status = {
            "cash": 100000,
        }
        
        result = self.fund_monitor.validate_trade_feasibility(
            symbol="AAPL",
            quantity=50,
            price=150.0,
            trade_type="sell"
        )
        
        self.assertTrue(result["feasible"])
        self.assertEqual(result["trade_value"], 7500)
        self.assertEqual(result["cash_after_trade"], 107500)
    
    def test_fund_calculator_position_value_breakdown(self):
        """測試資金計算器的持倉價值分解"""
        calculator = FundCalculator(self.fund_monitor.monitor_params)
        
        breakdown = calculator.calculate_position_value_breakdown(self.mock_positions)
        
        self.assertEqual(breakdown["position_count"], 3)
        self.assertGreater(breakdown["total_long_value"], 0)
        self.assertGreater(breakdown["total_short_value"], 0)
        self.assertEqual(breakdown["total_unrealized_pnl"], 1750)  # 500 + 250 + 1000
        
        # 檢查持倉詳情
        self.assertEqual(len(breakdown["position_details"]), 3)
        
        # 檢查權重計算
        total_weights = sum(detail["weight"] for detail in breakdown["position_details"])
        self.assertAlmostEqual(total_weights, 1.0, places=2)
    
    def test_fund_calculator_risk_metrics(self):
        """測試資金計算器的風險指標計算"""
        calculator = FundCalculator(self.fund_monitor.monitor_params)
        
        fund_status = {
            "total_value": 150000,
            "cash": 100000,
            "margin_used": 30000,
            "margin_available": 70000,
        }
        
        risk_metrics = calculator.calculate_risk_metrics(fund_status, self.mock_positions)
        
        # 檢查基本指標
        self.assertAlmostEqual(risk_metrics["cash_ratio"], 100000/150000, places=2)
        self.assertAlmostEqual(risk_metrics["leverage_ratio"], 1.5, places=2)
        self.assertAlmostEqual(risk_metrics["margin_utilization"], 0.3, places=2)
        self.assertAlmostEqual(risk_metrics["margin_buffer"], 0.7, places=2)
        
        # 檢查持倉相關指標
        self.assertEqual(risk_metrics["position_count"], 3)
        self.assertGreater(risk_metrics["max_position_weight"], 0)
        self.assertAlmostEqual(risk_metrics["total_unrealized_pnl"], 1750, places=2)


if __name__ == "__main__":
    unittest.main()
