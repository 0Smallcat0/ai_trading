"""
測試訊號執行器

此模組測試訊號執行器的功能，包括：
- 訊號處理與轉換
- 訂單生成與管理
- 交易執行
- 交易狀態監控
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.execution.signal_executor import SignalExecutor
from src.execution.order_manager import OrderManager
from src.execution.broker_base import BrokerBase, Order, OrderStatus, OrderType


class MockBroker(BrokerBase):
    """模擬券商 API"""

    def __init__(self):
        super().__init__()
        self.connected = False
        self.orders = {}
        self.positions = {}
        self.cash = 100000.0
        self.total_value = 100000.0
        self.next_order_id = 1

    def connect(self):
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False
        return True

    def place_order(self, order):
        order_id = str(self.next_order_id)
        self.next_order_id += 1
        order.order_id = order_id
        order.status = OrderStatus.SUBMITTED
        self.orders[order_id] = order
        return order_id

    def cancel_order(self, order_id):
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            return True
        return False

    def get_order(self, order_id):
        return self.orders.get(order_id)

    def get_orders(self, status=None):
        if status is None:
            return list(self.orders.values())
        return [order for order in self.orders.values() if order.status == status]

    def get_positions(self):
        return self.positions

    def get_account_info(self):
        return {
            "cash": self.cash,
            "total_value": self.total_value,
        }

    def get_market_data(self, stock_id):
        return {
            "last_price": 100.0,
        }


class TestSignalExecutor(unittest.TestCase):
    """測試訊號執行器"""

    def setUp(self):
        """設置測試環境"""
        self.broker = MockBroker()
        self.order_manager = OrderManager(self.broker)
        self.signal_executor = SignalExecutor(self.order_manager)

        # 啟動訊號執行器
        self.signal_executor.start()

    def tearDown(self):
        """清理測試環境"""
        self.signal_executor.stop()

    def test_execute_signals_buy(self):
        """測試執行買入訊號"""
        # 創建買入訊號
        signals = pd.DataFrame({
            "buy_signal": [1, 0, 1],
            "sell_signal": [0, 0, 0],
            "close": [100.0, 150.0, 200.0],
        }, index=["AAPL", "MSFT", "GOOG"])

        # 執行訊號
        order_ids = self.signal_executor.execute_signals(signals)

        # 驗證結果
        self.assertEqual(len(order_ids), 2)  # 應該有 2 個買入訂單 (AAPL, GOOG)
        self.assertEqual(len(self.broker.orders), 2)

        # 檢查訂單詳情
        orders = self.broker.get_orders()
        for order in orders:
            self.assertEqual(order.action, "buy")
            self.assertEqual(order.order_type, OrderType.MARKET)
            self.assertIn(order.stock_id, ["AAPL", "GOOG"])

    def test_execute_signals_sell(self):
        """測試執行賣出訊號"""
        # 設置持倉
        self.broker.positions = {
            "AAPL": {
                "stock_id": "AAPL",
                "shares": 100,
                "cost": 10000.0,
                "value": 10000.0,
                "current_price": 100.0,
            },
            "MSFT": {
                "stock_id": "MSFT",
                "shares": 50,
                "cost": 7500.0,
                "value": 7500.0,
                "current_price": 150.0,
            },
        }

        # 創建賣出訊號
        signals = pd.DataFrame({
            "buy_signal": [0, 0],
            "sell_signal": [1, 0],
            "close": [100.0, 150.0],
        }, index=["AAPL", "MSFT"])

        # 執行訊號
        order_ids = self.signal_executor.execute_signals(signals)

        # 驗證結果
        self.assertEqual(len(order_ids), 1)  # 應該有 1 個賣出訂單 (AAPL)
        self.assertEqual(len(self.broker.orders), 1)

        # 檢查訂單詳情
        orders = self.broker.get_orders()
        for order in orders:
            self.assertEqual(order.action, "sell")
            self.assertEqual(order.order_type, OrderType.MARKET)
            self.assertEqual(order.stock_id, "AAPL")
            self.assertEqual(order.quantity, 100)  # 賣出全部持倉

    def test_execute_signals_mixed(self):
        """測試執行混合訊號"""
        # 設置持倉
        self.broker.positions = {
            "AAPL": {
                "stock_id": "AAPL",
                "shares": 100,
                "cost": 10000.0,
                "value": 10000.0,
                "current_price": 100.0,
            },
        }

        # 創建混合訊號
        signals = pd.DataFrame({
            "buy_signal": [0, 1, 1],
            "sell_signal": [1, 0, 0],
            "close": [100.0, 150.0, 200.0],
        }, index=["AAPL", "MSFT", "GOOG"])

        # 執行訊號
        order_ids = self.signal_executor.execute_signals(signals)

        # 驗證結果
        self.assertEqual(len(order_ids), 3)  # 應該有 3 個訂單 (1 賣出, 2 買入)
        self.assertEqual(len(self.broker.orders), 3)

        # 檢查訂單詳情
        sell_orders = [order for order in self.broker.orders.values() if order.action == "sell"]
        buy_orders = [order for order in self.broker.orders.values() if order.action == "buy"]

        self.assertEqual(len(sell_orders), 1)
        self.assertEqual(len(buy_orders), 2)

        self.assertEqual(sell_orders[0].stock_id, "AAPL")
        self.assertIn(buy_orders[0].stock_id, ["MSFT", "GOOG"])
        self.assertIn(buy_orders[1].stock_id, ["MSFT", "GOOG"])

    def test_order_callbacks(self):
        """測試訂單回調函數"""
        # 模擬回調函數
        self.signal_executor._on_order_status_change = MagicMock()
        self.signal_executor._on_order_filled = MagicMock()
        self.signal_executor._on_order_rejected = MagicMock()

        # 創建買入訊號
        signals = pd.DataFrame({
            "buy_signal": [1],
            "sell_signal": [0],
            "close": [100.0],
        }, index=["AAPL"])

        # 執行訊號
        order_ids = self.signal_executor.execute_signals(signals)
        self.assertEqual(len(order_ids), 1)

        # 獲取訂單
        order = self.broker.get_order(order_ids[0])

        # 模擬訂單狀態變更
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = 100.0

        # 調用回調函數
        self.order_manager.on_order_status_change(order)
        self.order_manager.on_order_filled(order)

        # 驗證回調函數被調用
        self.signal_executor._on_order_status_change.assert_called_once()
        self.signal_executor._on_order_filled.assert_called_once()
        self.signal_executor._on_order_rejected.assert_not_called()


if __name__ == "__main__":
    unittest.main()
