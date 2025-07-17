"""
模擬券商 API 測試環境

此測試文件提供完整的模擬券商 API 測試環境，包括：
- 模擬券商連接測試
- 下單流程完整性測試
- 風險控制觸發測試
- 緊急停損功能測試
- 網路斷線恢復測試
- 資金計算準確性測試
"""

import pytest
import unittest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, List, Any

# 導入要測試的模組
from src.execution.simulator_adapter import SimulatorAdapter
from src.execution.broker_base import Order, OrderType, OrderStatus
from src.trading.live.emergency_stop import EmergencyStopManager
from src.risk.live.fund_monitor import FundMonitor
from src.execution.connection_monitor import ConnectionMonitor


class TestBrokerSimulation(unittest.TestCase):
    """模擬券商 API 測試環境"""
    
    def setUp(self):
        """設置測試環境"""
        self.simulator = SimulatorAdapter()
        self.simulator.connect()
        
        # 設置初始資金
        self.simulator.cash = 100000.0
        self.simulator.total_value = 100000.0
    
    def test_broker_connection(self):
        """測試券商連接功能"""
        # 測試連接
        self.assertTrue(self.simulator.connected)
        
        # 測試斷開連接
        result = self.simulator.disconnect()
        self.assertTrue(result)
        
        # 測試重新連接
        result = self.simulator.connect()
        self.assertTrue(result)
        self.assertTrue(self.simulator.connected)
    
    def test_order_flow_completeness(self):
        """測試下單流程完整性"""
        # 創建測試訂單
        order = Order(
            stock_id="2330.TW",
            action="buy",
            quantity=100,
            order_type=OrderType.MARKET,
            price=150.0
        )
        
        # 1. 下單
        order_id = self.simulator.place_order(order)
        self.assertIsNotNone(order_id)
        
        # 2. 檢查訂單狀態
        order_status = self.simulator.get_order_status(order_id)
        self.assertIn(order_status, [OrderStatus.PENDING, OrderStatus.FILLED])
        
        # 3. 獲取訂單詳情
        order_detail = self.simulator.get_order(order_id)
        self.assertIsNotNone(order_detail)
        self.assertEqual(order_detail.stock_id, "2330.TW")
        
        # 4. 檢查持倉變化
        positions = self.simulator.get_positions()
        if order_status == OrderStatus.FILLED:
            self.assertIn("2330.TW", positions)
            self.assertEqual(positions["2330.TW"]["quantity"], 100)
    
    def test_order_modification_and_cancellation(self):
        """測試訂單修改和取消"""
        # 創建限價訂單
        order = Order(
            stock_id="AAPL",
            action="buy",
            quantity=50,
            order_type=OrderType.LIMIT,
            price=180.0
        )
        
        order_id = self.simulator.place_order(order)
        self.assertIsNotNone(order_id)
        
        # 測試訂單修改
        result = self.simulator.modify_order(order_id, price=185.0)
        self.assertTrue(result)
        
        # 測試訂單取消
        result = self.simulator.cancel_order(order_id)
        self.assertTrue(result)
        
        # 檢查訂單狀態
        order_status = self.simulator.get_order_status(order_id)
        self.assertEqual(order_status, OrderStatus.CANCELLED)
    
    def test_risk_control_triggers(self):
        """測試風險控制觸發"""
        # 創建風險監控器
        fund_monitor = FundMonitor(self.simulator)
        
        # 設置風險閾值
        fund_monitor.set_risk_threshold("max_position_percent", 0.5)
        fund_monitor.set_risk_threshold("max_daily_loss", 0.1)
        
        # 測試超過持倉限制的訂單
        large_order = Order(
            stock_id="TSLA",
            action="buy",
            quantity=1000,  # 大量訂單
            order_type=OrderType.MARKET,
            price=200.0
        )
        
        # 檢查風險控制是否觸發
        risk_check = fund_monitor.check_order_risk(large_order)
        self.assertFalse(risk_check["approved"])
        self.assertIn("position_limit", risk_check["violations"])
    
    def test_emergency_stop_functionality(self):
        """測試緊急停損功能"""
        # 先建立一些持倉
        orders = [
            Order("AAPL", "buy", 100, OrderType.MARKET, 150.0),
            Order("GOOGL", "buy", 50, OrderType.MARKET, 2500.0),
            Order("MSFT", "buy", 200, OrderType.MARKET, 300.0)
        ]
        
        order_ids = []
        for order in orders:
            order_id = self.simulator.place_order(order)
            if order_id:
                order_ids.append(order_id)
        
        # 等待訂單執行
        time.sleep(0.1)
        
        # 創建緊急停損管理器
        emergency_stop = EmergencyStopManager(self.simulator)
        
        # 執行緊急停損
        result = emergency_stop.emergency_stop_all("測試緊急停損")
        
        self.assertTrue(result["success"])
        self.assertGreater(result["positions_closed"], 0)
        
        # 檢查所有持倉是否已清空
        positions = self.simulator.get_positions()
        for symbol in ["AAPL", "GOOGL", "MSFT"]:
            if symbol in positions:
                self.assertEqual(positions[symbol]["quantity"], 0)
    
    def test_network_disconnection_recovery(self):
        """測試網路斷線恢復"""
        # 創建連接監控器
        monitor = ConnectionMonitor()
        monitor.add_adapter("simulator", self.simulator)
        
        # 模擬網路斷線
        self.simulator._connected = False
        
        # 檢查連接狀態
        status = monitor.get_status("simulator")
        self.assertIsNotNone(status)
        
        # 測試自動重連
        result = monitor.force_reconnect("simulator")
        self.assertTrue(result)
        self.assertTrue(self.simulator.connected)
    
    def test_fund_calculation_accuracy(self):
        """測試資金計算準確性"""
        initial_cash = self.simulator.cash
        initial_total = self.simulator.total_value
        
        # 執行買入訂單
        buy_order = Order(
            stock_id="NVDA",
            action="buy",
            quantity=100,
            order_type=OrderType.MARKET,
            price=500.0
        )
        
        order_id = self.simulator.place_order(buy_order)
        self.assertIsNotNone(order_id)
        
        # 等待訂單執行
        time.sleep(0.1)
        
        # 檢查資金變化
        account_info = self.simulator.get_account_info()
        
        # 計算預期的資金變化
        expected_cost = 100 * 500.0  # 不考慮手續費的簡化計算
        
        # 驗證現金減少
        self.assertLess(account_info["cash"], initial_cash)
        
        # 驗證總資產變化合理
        self.assertAlmostEqual(
            account_info["total_value"], 
            initial_total, 
            delta=expected_cost * 0.1  # 允許10%的誤差
        )
    
    def test_market_data_simulation(self):
        """測試市場資料模擬"""
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
        
        for symbol in symbols:
            market_data = self.simulator.get_market_data(symbol)
            
            self.assertIsNotNone(market_data)
            self.assertIn("last_price", market_data)
            self.assertIn("bid_price", market_data)
            self.assertIn("ask_price", market_data)
            self.assertIn("volume", market_data)
            
            # 檢查價格合理性
            self.assertGreater(market_data["last_price"], 0)
            self.assertGreater(market_data["bid_price"], 0)
            self.assertGreater(market_data["ask_price"], 0)
            self.assertGreaterEqual(market_data["ask_price"], market_data["bid_price"])
    
    def test_concurrent_orders(self):
        """測試並發訂單處理"""
        def place_order_thread(symbol, quantity):
            order = Order(
                stock_id=symbol,
                action="buy",
                quantity=quantity,
                order_type=OrderType.MARKET,
                price=100.0
            )
            return self.simulator.place_order(order)
        
        # 創建多個線程同時下單
        threads = []
        results = []
        
        for i in range(5):
            thread = threading.Thread(
                target=lambda: results.append(
                    place_order_thread(f"TEST{i}", 10)
                )
            )
            threads.append(thread)
            thread.start()
        
        # 等待所有線程完成
        for thread in threads:
            thread.join()
        
        # 檢查所有訂單都成功提交
        self.assertEqual(len(results), 5)
        for result in results:
            self.assertIsNotNone(result)
    
    def test_order_history_tracking(self):
        """測試訂單歷史追蹤"""
        # 執行多個訂單
        orders = [
            Order("AAPL", "buy", 100, OrderType.MARKET, 150.0),
            Order("AAPL", "sell", 50, OrderType.LIMIT, 155.0),
            Order("GOOGL", "buy", 10, OrderType.MARKET, 2500.0)
        ]
        
        order_ids = []
        for order in orders:
            order_id = self.simulator.place_order(order)
            if order_id:
                order_ids.append(order_id)
        
        # 獲取訂單歷史
        all_orders = self.simulator.get_orders()
        
        # 檢查訂單歷史完整性
        self.assertGreaterEqual(len(all_orders), len(order_ids))
        
        # 檢查特定狀態的訂單
        filled_orders = self.simulator.get_orders(OrderStatus.FILLED)
        pending_orders = self.simulator.get_orders(OrderStatus.PENDING)
        
        self.assertIsInstance(filled_orders, list)
        self.assertIsInstance(pending_orders, list)


if __name__ == "__main__":
    unittest.main()
