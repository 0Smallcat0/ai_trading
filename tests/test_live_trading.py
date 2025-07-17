"""
Live Trading 核心功能測試

測試 4.3 Live Trading 核心功能的各個模組
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# 導入要測試的模組
# 更新導入：使用推薦的重構版本
try:
    from src.execution.ib_adapter_refactored import IBAdapterRefactored as IBAdapter
except ImportError:
    # 向後相容：如果重構版本不存在，使用原版本
    from src.execution.ib_adapter import IBAdapter
from src.execution.connection_monitor import ConnectionMonitor, ConnectionStatus
from src.execution.order_tracker import OrderTracker, OrderEvent
from src.trading.live.position_manager import PositionManager, ClosePositionMode
from src.trading.live.quick_order import QuickOrderPanel, QuickOrderTemplate
from src.trading.live.emergency_stop import EmergencyStopManager, StopLossType
from src.trading.live.order_confirmation import OrderConfirmationManager, ConfirmationLevel
from src.risk.live.fund_monitor import FundMonitor, FundAlertLevel
from src.risk.live.dynamic_stop_loss import DynamicStopLoss, StopLossStrategy
from src.risk.live.position_limiter import PositionLimiter, LimitType
from src.risk.live.trade_limiter import TradeLimiter
from src.risk.live.loss_alert import LossAlertManager, AlertLevel

from src.execution.broker_base import Order, OrderType, OrderStatus


class TestIBAdapter(unittest.TestCase):
    """測試 Interactive Brokers API 適配器"""
    
    def setUp(self):
        """設置測試環境"""
        with patch('src.execution.ib_adapter.IB_AVAILABLE', True):
            self.adapter = IBAdapter()
    
    def test_init(self):
        """測試初始化"""
        self.assertIsNotNone(self.adapter)
        self.assertEqual(self.adapter.host, "127.0.0.1")
        self.assertEqual(self.adapter.port, 7497)
        self.assertEqual(self.adapter.client_id, 1)
    
    @patch('src.execution.ib_adapter.EClient')
    def test_connect(self, mock_client):
        """測試連接功能"""
        # 模擬連接成功
        self.adapter._connected = True
        self.adapter._next_order_id = 1
        
        result = self.adapter.connect()
        self.assertTrue(result)
    
    def test_create_contract(self):
        """測試創建合約"""
        # 測試台股
        contract = self.adapter._create_contract("2330.TW")
        self.assertIsNotNone(contract)
        
        # 測試美股
        contract = self.adapter._create_contract("AAPL")
        self.assertIsNotNone(contract)
        
        # 測試港股
        contract = self.adapter._create_contract("0700.HK")
        self.assertIsNotNone(contract)


class TestConnectionMonitor(unittest.TestCase):
    """測試連接監控系統"""
    
    def setUp(self):
        """設置測試環境"""
        self.monitor = ConnectionMonitor()
        self.mock_adapter = Mock()
        self.mock_adapter.connected = True
    
    def test_add_adapter(self):
        """測試添加適配器"""
        self.monitor.add_adapter("test", self.mock_adapter)
        self.assertIn("test", self.monitor.adapters)
        self.assertEqual(self.monitor.connection_status["test"], ConnectionStatus.DISCONNECTED)
    
    def test_get_status(self):
        """測試獲取狀態"""
        self.monitor.add_adapter("test", self.mock_adapter)
        status = self.monitor.get_status("test")
        self.assertIsNotNone(status)
    
    def test_force_reconnect(self):
        """測試強制重連"""
        self.monitor.add_adapter("test", self.mock_adapter)
        self.mock_adapter.connect.return_value = True
        
        result = self.monitor.force_reconnect("test")
        self.assertTrue(result)


class TestOrderTracker(unittest.TestCase):
    """測試訂單追蹤系統"""
    
    def setUp(self):
        """設置測試環境"""
        self.tracker = OrderTracker()
        self.test_order = Order(
            stock_id="AAPL",
            action="buy",
            quantity=100,
            order_type=OrderType.MARKET
        )
        self.test_order.order_id = "test_order_1"
    
    def test_track_order(self):
        """測試追蹤訂單"""
        self.tracker.track_order(self.test_order, "test_broker")
        self.assertIn("test_order_1", self.tracker.tracking_orders)
    
    def test_update_order_status(self):
        """測試更新訂單狀態"""
        self.tracker.track_order(self.test_order, "test_broker")
        
        self.tracker.update_order_status(
            "test_order_1",
            OrderStatus.FILLED,
            filled_quantity=100,
            avg_fill_price=150.0
        )
        
        order_info = self.tracker.get_order_info("test_order_1")
        self.assertEqual(order_info.status, OrderStatus.FILLED)
        self.assertEqual(order_info.filled_quantity, 100)
    
    def test_get_statistics(self):
        """測試獲取統計資訊"""
        self.tracker.track_order(self.test_order, "test_broker")
        stats = self.tracker.get_statistics()
        
        self.assertEqual(stats["total_orders"], 1)
        self.assertEqual(stats["active_orders"], 1)


class TestPositionManager(unittest.TestCase):
    """測試持倉管理器"""
    
    def setUp(self):
        """設置測試環境"""
        self.mock_broker = Mock()
        self.manager = PositionManager(self.mock_broker)
        
        # 模擬持倉
        self.test_positions = {
            "AAPL": {
                "quantity": 100,
                "avg_price": 150.0,
                "current_price": 155.0,
                "market_value": 15500,
            }
        }
    
    def test_update_positions(self):
        """測試更新持倉"""
        self.manager.update_positions(self.test_positions)
        positions = self.manager.get_positions()
        self.assertEqual(len(positions), 1)
        self.assertIn("AAPL", positions)
    
    def test_close_position_by_symbol(self):
        """測試按股票平倉"""
        self.manager.update_positions(self.test_positions)
        self.mock_broker.place_order.return_value = "order_123"
        
        result = self.manager.close_position_by_symbol("AAPL", confirm=True)
        self.assertTrue(result["success"])
        self.mock_broker.place_order.assert_called_once()
    
    def test_get_position_summary(self):
        """測試獲取持倉摘要"""
        self.manager.update_positions(self.test_positions)
        summary = self.manager.get_position_summary()
        
        self.assertEqual(summary["total_positions"], 1)
        self.assertEqual(summary["total_value"], 15500)


class TestQuickOrderPanel(unittest.TestCase):
    """測試快速下單面板"""
    
    def setUp(self):
        """設置測試環境"""
        self.mock_broker = Mock()
        self.mock_broker.connected = True
        self.panel = QuickOrderPanel(self.mock_broker)
    
    def test_add_template(self):
        """測試添加模板"""
        template = QuickOrderTemplate(
            name="AAPL Buy",
            symbol="AAPL",
            action="buy",
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        result = self.panel.add_template(template)
        self.assertTrue(result)
        self.assertIn("AAPL Buy", self.panel.templates)
    
    def test_quick_buy(self):
        """測試快速買入"""
        self.mock_broker.place_order.return_value = "order_123"
        
        result = self.panel.quick_buy("AAPL", 100)
        self.assertTrue(result["success"])
        self.mock_broker.place_order.assert_called_once()
    
    def test_batch_order(self):
        """測試批量下單"""
        self.mock_broker.place_order.return_value = "order_123"
        
        orders = [
            {"symbol": "AAPL", "action": "buy", "quantity": 100},
            {"symbol": "GOOGL", "action": "buy", "quantity": 50},
        ]
        
        result = self.panel.batch_order(orders)
        self.assertTrue(result["success"])
        self.assertEqual(len(result["successful_orders"]), 2)


class TestEmergencyStopManager(unittest.TestCase):
    """測試緊急停損管理器"""
    
    def setUp(self):
        """設置測試環境"""
        self.mock_broker = Mock()
        self.manager = EmergencyStopManager(self.mock_broker)
        
        # 模擬持倉
        self.test_positions = {
            "AAPL": {
                "quantity": 100,
                "avg_price": 150.0,
                "current_price": 145.0,
            }
        }
    
    def test_emergency_stop_all(self):
        """測試緊急停損所有持倉"""
        self.mock_broker.get_positions.return_value = self.test_positions
        self.mock_broker.place_order.return_value = "order_123"
        
        result = self.manager.emergency_stop_all("測試緊急停損")
        self.assertTrue(result["success"])
        self.assertEqual(result["positions_closed"], 1)
    
    def test_set_auto_stop_loss(self):
        """測試設定自動停損"""
        self.mock_broker.get_positions.return_value = self.test_positions
        self.mock_broker.place_order.return_value = "order_123"
        
        result = self.manager.set_auto_stop_loss("AAPL", 140.0)
        self.assertTrue(result["success"])
        self.mock_broker.place_order.assert_called_once()


class TestFundMonitor(unittest.TestCase):
    """測試資金監控器"""
    
    def setUp(self):
        """設置測試環境"""
        self.mock_broker = Mock()
        self.monitor = FundMonitor(self.mock_broker)
        
        # 模擬帳戶資訊
        self.test_account = {
            "cash": 50000,
            "buying_power": 100000,
            "total_value": 200000,
            "margin_used": 80000,
            "margin_available": 20000,
        }
    
    def test_update_fund_status(self):
        """測試更新資金狀態"""
        self.mock_broker.get_account_info.return_value = self.test_account
        self.mock_broker.get_positions.return_value = {}
        
        result = self.monitor._update_fund_status()
        self.assertTrue(result)
        
        status = self.monitor.get_fund_status()
        self.assertEqual(status["cash"], 50000)
        self.assertEqual(status["margin_usage_rate"], 0.8)
    
    def test_get_fund_summary(self):
        """測試獲取資金摘要"""
        self.monitor.fund_status = {
            "cash": 50000,
            "buying_power": 100000,
            "total_value": 200000,
            "positions_value": 150000,
            "unrealized_pnl": 5000,
            "margin_used": 80000,
            "margin_available": 20000,
            "margin_usage_rate": 0.8,
            "last_update": datetime.now(),
        }
        
        summary = self.monitor.get_fund_summary()
        self.assertIn("basic_info", summary)
        self.assertIn("margin_info", summary)
        self.assertIn("risk_indicators", summary)


class TestDynamicStopLoss(unittest.TestCase):
    """測試動態停損調整器"""
    
    def setUp(self):
        """設置測試環境"""
        self.mock_broker = Mock()
        self.stop_loss = DynamicStopLoss(self.mock_broker)
        
        # 模擬持倉
        self.test_position = {
            "quantity": 100,
            "avg_price": 150.0,
            "current_price": 155.0,
        }
    
    def test_set_position_stop_loss(self):
        """測試設定持倉停損"""
        self.mock_broker.get_positions.return_value = {"AAPL": self.test_position}
        
        result = self.stop_loss.set_position_stop_loss(
            "AAPL", 
            StopLossStrategy.TRAILING
        )
        
        self.assertTrue(result["success"])
        self.assertIn("AAPL", self.stop_loss.position_stops)
    
    def test_calculate_initial_stop_price(self):
        """測試計算初始停損價格"""
        stop_price = self.stop_loss._calculate_initial_stop_price(
            "AAPL",
            self.test_position,
            StopLossStrategy.TRAILING,
            {"trail_percent": 0.02}
        )
        
        expected_price = 155.0 * 0.98  # 2% 追蹤停損
        self.assertAlmostEqual(stop_price, expected_price, places=2)


if __name__ == "__main__":
    # 運行所有測試
    unittest.main(verbosity=2)
