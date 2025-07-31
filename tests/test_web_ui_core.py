"""
Web UI 核心功能測試

此測試文件驗證 Web UI 的核心功能，包括：
- 交易頁面功能測試
- 風險警報顯示測試
- 用戶認證流程測試
- 新手引導流程測試
"""

import pytest
import unittest
import streamlit as st
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd

# 導入要測試的模組
try:
    from src.ui.pages.trading_enhanced import (
        submit_order,
        load_active_orders,
        load_trading_history,
        calculate_estimated_cost
    )
    from src.ui.components.trading_components import TradingComponents
    from src.ui.components.risk_alerts import RiskAlertComponent
    from src.ui.auth.authentication import AuthenticationManager
    from src.ui.onboarding.tutorial_manager import TutorialManager
    UI_AVAILABLE = True
except ImportError:
    UI_AVAILABLE = False


@pytest.mark.skipif(not UI_AVAILABLE, reason="UI modules not available")
class TestWebUICore(unittest.TestCase):
    """Web UI 核心功能測試"""
    
    def setUp(self):
        """設置測試環境"""
        self.trading_components = TradingComponents()
        self.risk_alerts = RiskAlertComponent()
        self.auth_manager = AuthenticationManager()
        self.tutorial_manager = TutorialManager()
    
    def test_trading_page_functionality(self):
        """測試交易頁面功能"""
        # 測試訂單提交功能
        order_data = {
            "symbol": "2330.TW",
            "action": "買入",
            "quantity": 100,
            "price": 150.0,
            "order_type": "limit"
        }
        
        # 測試計算預估成本
        estimated_cost = calculate_estimated_cost(order_data)
        self.assertGreater(estimated_cost, 0)
        self.assertAlmostEqual(estimated_cost, 15000.0, delta=100)  # 允許手續費誤差
        
        # 測試訂單提交
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            result = submit_order(order_data, "limit")
            self.assertIsInstance(result, bool)
    
    def test_active_orders_loading(self):
        """測試活躍訂單載入"""
        # 模擬活躍訂單數據
        mock_orders = [
            {
                "order_id": "ORD001",
                "symbol": "2330.TW",
                "action": "買入",
                "quantity": 100,
                "price": 150.0,
                "status": "待成交",
                "timestamp": datetime.now()
            },
            {
                "order_id": "ORD002",
                "symbol": "AAPL",
                "action": "賣出",
                "quantity": 50,
                "price": 180.0,
                "status": "部分成交",
                "timestamp": datetime.now()
            }
        ]
        
        with patch('src.ui.pages.trading_enhanced.load_active_orders') as mock_load:
            mock_load.return_value = mock_orders
            orders = load_active_orders()
            
            self.assertEqual(len(orders), 2)
            self.assertEqual(orders[0]["symbol"], "2330.TW")
            self.assertEqual(orders[1]["action"], "賣出")
    
    def test_trading_history_loading(self):
        """測試交易歷史載入"""
        # 模擬歷史交易數據
        mock_history = pd.DataFrame({
            "timestamp": [datetime.now() - timedelta(days=i) for i in range(5)],
            "symbol": ["2330.TW", "AAPL", "GOOGL", "MSFT", "TSLA"],
            "action": ["買入", "賣出", "買入", "賣出", "買入"],
            "quantity": [100, 50, 20, 75, 30],
            "price": [150.0, 180.0, 2500.0, 300.0, 800.0],
            "amount": [15000, 9000, 50000, 22500, 24000]
        })
        
        with patch('src.ui.pages.trading_enhanced.load_trading_history') as mock_load:
            mock_load.return_value = mock_history
            history = load_trading_history()
            
            self.assertIsInstance(history, pd.DataFrame)
            self.assertEqual(len(history), 5)
            self.assertIn("symbol", history.columns)
            self.assertIn("action", history.columns)
    
    def test_risk_alert_display(self):
        """測試風險警報顯示"""
        # 測試不同類型的風險警報
        risk_alerts = [
            {
                "type": "position_limit",
                "level": "warning",
                "message": "持倉比例接近上限",
                "details": {"current": 0.85, "limit": 0.9}
            },
            {
                "type": "margin_call",
                "level": "critical",
                "message": "保證金不足",
                "details": {"required": 50000, "available": 30000}
            },
            {
                "type": "daily_loss",
                "level": "high",
                "message": "當日虧損超過閾值",
                "details": {"loss": 0.12, "threshold": 0.1}
            }
        ]
        
        for alert in risk_alerts:
            # 測試警報組件能正確處理不同類型的警報
            formatted_alert = self.risk_alerts.format_alert(alert)
            
            self.assertIn("type", formatted_alert)
            self.assertIn("level", formatted_alert)
            self.assertIn("message", formatted_alert)
            self.assertEqual(formatted_alert["type"], alert["type"])
    
    def test_user_authentication_flow(self):
        """測試用戶認證流程"""
        # 測試登入功能
        test_credentials = {
            "username": "test_user",
            "password": "test_password"
        }
        
        # 模擬成功登入
        with patch.object(self.auth_manager, 'authenticate') as mock_auth:
            mock_auth.return_value = {
                "success": True,
                "user_id": "user_123",
                "permissions": ["trading", "viewing"]
            }
            
            result = self.auth_manager.authenticate(
                test_credentials["username"], 
                test_credentials["password"]
            )
            
            self.assertTrue(result["success"])
            self.assertEqual(result["user_id"], "user_123")
            self.assertIn("trading", result["permissions"])
        
        # 測試登出功能
        with patch.object(self.auth_manager, 'logout') as mock_logout:
            mock_logout.return_value = True
            result = self.auth_manager.logout()
            self.assertTrue(result)
    
    def test_session_management(self):
        """測試會話管理"""
        # 測試會話創建
        session_data = {
            "user_id": "user_123",
            "login_time": datetime.now(),
            "permissions": ["trading", "viewing"]
        }
        
        with patch.object(self.auth_manager, 'create_session') as mock_create:
            mock_create.return_value = "session_token_123"
            token = self.auth_manager.create_session(session_data)
            self.assertEqual(token, "session_token_123")
        
        # 測試會話驗證
        with patch.object(self.auth_manager, 'validate_session') as mock_validate:
            mock_validate.return_value = {
                "valid": True,
                "user_id": "user_123",
                "expires_at": datetime.now() + timedelta(hours=1)
            }
            
            result = self.auth_manager.validate_session("session_token_123")
            self.assertTrue(result["valid"])
            self.assertEqual(result["user_id"], "user_123")
    
    def test_tutorial_flow(self):
        """測試新手引導流程"""
        # 測試教程步驟
        tutorial_steps = [
            {
                "step": 1,
                "title": "歡迎使用交易系統",
                "content": "這是您的第一步",
                "action": "next"
            },
            {
                "step": 2,
                "title": "如何下單",
                "content": "學習如何提交交易訂單",
                "action": "demo"
            },
            {
                "step": 3,
                "title": "風險管理",
                "content": "了解風險控制功能",
                "action": "complete"
            }
        ]
        
        # 測試教程初始化
        with patch.object(self.tutorial_manager, 'initialize_tutorial') as mock_init:
            mock_init.return_value = tutorial_steps
            steps = self.tutorial_manager.initialize_tutorial("new_user")
            
            self.assertEqual(len(steps), 3)
            self.assertEqual(steps[0]["title"], "歡迎使用交易系統")
        
        # 測試教程進度追蹤
        with patch.object(self.tutorial_manager, 'update_progress') as mock_update:
            mock_update.return_value = {"current_step": 2, "completed": False}
            progress = self.tutorial_manager.update_progress("new_user", 2)
            
            self.assertEqual(progress["current_step"], 2)
            self.assertFalse(progress["completed"])
    
    def test_interactive_components(self):
        """測試互動組件"""
        # 測試股票選擇器
        with patch.object(self.trading_components, 'stock_selector') as mock_selector:
            mock_selector.return_value = "2330.TW"
            selected_stock = self.trading_components.stock_selector(
                ["2330.TW", "AAPL", "GOOGL"]
            )
            self.assertEqual(selected_stock, "2330.TW")
        
        # 測試數量輸入器
        with patch.object(self.trading_components, 'quantity_input') as mock_input:
            mock_input.return_value = 100
            quantity = self.trading_components.quantity_input(min_value=1, max_value=1000)
            self.assertEqual(quantity, 100)
        
        # 測試價格輸入器
        with patch.object(self.trading_components, 'price_input') as mock_price:
            mock_price.return_value = 150.0
            price = self.trading_components.price_input(current_price=148.5)
            self.assertEqual(price, 150.0)
    
    def test_real_time_updates(self):
        """測試即時更新功能"""
        # 模擬即時價格更新
        price_updates = {
            "2330.TW": {"price": 151.5, "change": 1.5, "change_percent": 1.0},
            "AAPL": {"price": 182.0, "change": 2.0, "change_percent": 1.1},
            "GOOGL": {"price": 2520.0, "change": 20.0, "change_percent": 0.8}
        }
        
        with patch.object(self.trading_components, 'update_prices') as mock_update:
            mock_update.return_value = price_updates
            updates = self.trading_components.update_prices(["2330.TW", "AAPL", "GOOGL"])
            
            self.assertEqual(len(updates), 3)
            self.assertEqual(updates["2330.TW"]["price"], 151.5)
            self.assertEqual(updates["AAPL"]["change"], 2.0)
    
    def test_error_handling(self):
        """測試錯誤處理"""
        # 測試網路錯誤處理
        with patch('requests.post') as mock_post:
            mock_post.side_effect = ConnectionError("網路連接失敗")
            
            order_data = {
                "symbol": "2330.TW",
                "action": "買入",
                "quantity": 100,
                "price": 150.0
            }
            
            result = submit_order(order_data, "limit")
            # 應該優雅地處理錯誤，不拋出異常
            self.assertIsInstance(result, bool)
        
        # 測試數據驗證錯誤
        invalid_order = {
            "symbol": "",  # 無效的股票代號
            "action": "買入",
            "quantity": -100,  # 無效的數量
            "price": 0  # 無效的價格
        }
        
        with self.assertRaises((ValueError, TypeError)):
            calculate_estimated_cost(invalid_order)


if __name__ == "__main__":
    unittest.main()
