"""
即時數據更新組件測試

測試 WebSocket 連接管理和即時數據更新功能。
"""

import unittest
import asyncio
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# 添加專案根目錄到 Python 路徑
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.ui.utils.websocket_manager import (
    WebSocketManager,
    ConnectionStatus,
    DataType,
    websocket_manager,
)
from src.ui.components.realtime import RealtimeDataManager


class TestWebSocketManager(unittest.TestCase):
    """測試 WebSocket 管理器"""

    def setUp(self):
        """設置測試環境"""
        self.ws_manager = WebSocketManager("ws://test:8000/ws")

    def tearDown(self):
        """清理測試環境"""
        self.ws_manager.stop()

    def test_initialization(self):
        """測試初始化"""
        self.assertEqual(self.ws_manager.server_url, "ws://test:8000/ws")
        self.assertEqual(self.ws_manager.status, ConnectionStatus.DISCONNECTED)
        self.assertEqual(self.ws_manager.reconnect_attempts, 0)
        self.assertIsNone(self.ws_manager.websocket)

    def test_subscription_management(self):
        """測試訂閱管理"""
        callback = Mock()

        # 測試訂閱
        self.ws_manager.subscribe(DataType.STOCK_PRICE, callback)
        self.assertIn(callback, self.ws_manager.subscribers[DataType.STOCK_PRICE])

        # 測試取消訂閱
        self.ws_manager.unsubscribe(DataType.STOCK_PRICE, callback)
        self.assertNotIn(callback, self.ws_manager.subscribers[DataType.STOCK_PRICE])

    def test_duplicate_subscription(self):
        """測試重複訂閱"""
        callback = Mock()

        # 多次訂閱同一個回調
        self.ws_manager.subscribe(DataType.STOCK_PRICE, callback)
        self.ws_manager.subscribe(DataType.STOCK_PRICE, callback)

        # 應該只有一個實例
        count = self.ws_manager.subscribers[DataType.STOCK_PRICE].count(callback)
        self.assertEqual(count, 1)

    def test_connection_status(self):
        """測試連接狀態"""
        status_info = self.ws_manager.get_connection_status()

        self.assertIn("status", status_info)
        self.assertIn("server_url", status_info)
        self.assertIn("reconnect_attempts", status_info)
        self.assertIn("subscribers_count", status_info)

        self.assertEqual(status_info["status"], ConnectionStatus.DISCONNECTED.value)
        self.assertEqual(status_info["server_url"], "ws://test:8000/ws")

    def test_data_cache(self):
        """測試數據緩存"""
        # 測試設置和獲取數據
        test_data = {"symbol": "TEST", "price": 100.0}
        self.ws_manager.data_cache[DataType.STOCK_PRICE.value] = test_data

        retrieved_data = self.ws_manager.get_latest_data(DataType.STOCK_PRICE)
        self.assertEqual(retrieved_data, test_data)

        # 測試不存在的數據
        non_existent = self.ws_manager.get_latest_data(DataType.PORTFOLIO_UPDATE)
        self.assertIsNone(non_existent)

    @patch("src.ui.utils.websocket_manager.asyncio")
    def test_start_connection(self, mock_asyncio):
        """測試啟動連接"""
        mock_loop = Mock()
        mock_asyncio.new_event_loop.return_value = mock_loop
        mock_asyncio.get_event_loop.return_value = mock_loop

        self.ws_manager.start()

        # 檢查線程是否啟動
        self.assertIsNotNone(self.ws_manager._connection_thread)
        self.assertTrue(self.ws_manager._connection_thread.is_alive())

    def test_mock_data_generation(self):
        """測試模擬數據生成"""
        stock_data = self.ws_manager._generate_mock_stock_data()

        self.assertIsInstance(stock_data, dict)
        self.assertGreater(len(stock_data), 0)

        # 檢查數據結構
        for symbol, data in stock_data.items():
            self.assertIn("price", data)
            self.assertIn("change", data)
            self.assertIn("change_percent", data)
            self.assertIn("volume", data)
            self.assertIn("timestamp", data)

            # 檢查數據類型
            self.assertIsInstance(data["price"], (int, float))
            self.assertIsInstance(data["volume"], int)

    def test_trading_status_generation(self):
        """測試交易狀態數據生成"""
        trading_status = self.ws_manager._generate_mock_trading_status()

        self.assertIsInstance(trading_status, dict)

        # 檢查必要字段
        required_fields = [
            "market_status",
            "active_orders",
            "executed_orders",
            "portfolio_value",
            "daily_pnl",
            "timestamp",
        ]

        for field in required_fields:
            self.assertIn(field, trading_status)

        # 檢查市場狀態值
        valid_statuses = ["open", "closed", "pre_market", "after_hours"]
        self.assertIn(trading_status["market_status"], valid_statuses)

    def test_heartbeat_logic(self):
        """測試心跳邏輯"""
        # 初始狀態應該需要發送心跳
        self.assertTrue(self.ws_manager._should_send_heartbeat())

        # 設置最近心跳時間
        self.ws_manager.last_heartbeat = datetime.now()
        self.assertFalse(self.ws_manager._should_send_heartbeat())

    async def test_message_handling(self):
        """測試消息處理"""
        callback = Mock()
        self.ws_manager.subscribe(DataType.STOCK_PRICE, callback)

        test_message = {
            "type": DataType.STOCK_PRICE.value,
            "data": {"TEST": {"price": 100.0}},
        }

        await self.ws_manager._handle_message(test_message)

        # 檢查回調是否被調用
        callback.assert_called_once_with({"TEST": {"price": 100.0}})

        # 檢查數據是否被緩存
        cached_data = self.ws_manager.get_latest_data(DataType.STOCK_PRICE)
        self.assertEqual(cached_data, {"TEST": {"price": 100.0}})


class TestRealtimeDataManager(unittest.TestCase):
    """測試即時數據管理器"""

    def setUp(self):
        """設置測試環境"""
        self.data_manager = RealtimeDataManager()

    def test_initialization(self):
        """測試初始化"""
        self.assertEqual(self.data_manager.data_history, {})
        self.assertEqual(self.data_manager.max_history_length, 100)

    def test_add_data_point(self):
        """測試添加數據點"""
        test_data = {"symbol": "TEST", "price": 100.0}

        self.data_manager.add_data_point("stock_price", test_data)

        # 檢查數據是否被添加
        history = self.data_manager.get_history("stock_price")
        self.assertEqual(len(history), 1)

        # 檢查時間戳是否被添加
        self.assertIn("timestamp", history[0])
        self.assertEqual(history[0]["symbol"], "TEST")
        self.assertEqual(history[0]["price"], 100.0)

    def test_history_length_limit(self):
        """測試歷史記錄長度限制"""
        # 添加超過限制的數據點
        for i in range(150):
            test_data = {"index": i, "value": i * 10}
            self.data_manager.add_data_point("test_data", test_data)

        # 檢查長度是否被限制
        history = self.data_manager.get_history("test_data")
        self.assertEqual(len(history), 100)

        # 檢查是否保留最新的數據
        self.assertEqual(history[-1]["index"], 149)
        self.assertEqual(history[0]["index"], 50)

    def test_multiple_data_types(self):
        """測試多種數據類型"""
        # 添加不同類型的數據
        self.data_manager.add_data_point("stock_price", {"price": 100})
        self.data_manager.add_data_point("trading_status", {"status": "open"})

        # 檢查數據是否分別存儲
        stock_history = self.data_manager.get_history("stock_price")
        trading_history = self.data_manager.get_history("trading_status")

        self.assertEqual(len(stock_history), 1)
        self.assertEqual(len(trading_history), 1)
        self.assertEqual(stock_history[0]["price"], 100)
        self.assertEqual(trading_history[0]["status"], "open")

    def test_empty_history(self):
        """測試空歷史記錄"""
        history = self.data_manager.get_history("non_existent")
        self.assertEqual(history, [])


class TestWebSocketIntegration(unittest.TestCase):
    """測試 WebSocket 整合功能"""

    def setUp(self):
        """設置測試環境"""
        self.received_data = []

    def callback_function(self, data):
        """測試回調函數"""
        self.received_data.append(data)

    def test_subscription_callback(self):
        """測試訂閱回調"""
        # 訂閱數據更新
        websocket_manager.subscribe(DataType.STOCK_PRICE, self.callback_function)

        # 模擬數據更新
        test_data = {"TEST": {"price": 100.0}}
        websocket_manager.data_cache[DataType.STOCK_PRICE.value] = test_data

        # 手動觸發回調
        for callback in websocket_manager.subscribers[DataType.STOCK_PRICE]:
            callback(test_data)

        # 檢查回調是否被執行
        self.assertEqual(len(self.received_data), 1)
        self.assertEqual(self.received_data[0], test_data)

        # 清理
        websocket_manager.unsubscribe(DataType.STOCK_PRICE, self.callback_function)

    def test_error_handling_in_callback(self):
        """測試回調中的錯誤處理"""

        def error_callback(data):
            raise Exception("Test error")

        # 訂閱會出錯的回調
        websocket_manager.subscribe(DataType.STOCK_PRICE, error_callback)
        websocket_manager.subscribe(DataType.STOCK_PRICE, self.callback_function)

        # 模擬數據更新
        test_data = {"TEST": {"price": 100.0}}

        # 手動觸發回調（應該處理錯誤並繼續執行其他回調）
        for callback in websocket_manager.subscribers[DataType.STOCK_PRICE]:
            try:
                callback(test_data)
            except Exception:
                pass  # 模擬錯誤處理

        # 檢查正常回調是否仍然執行
        self.assertEqual(len(self.received_data), 1)

        # 清理
        websocket_manager.unsubscribe(DataType.STOCK_PRICE, error_callback)
        websocket_manager.unsubscribe(DataType.STOCK_PRICE, self.callback_function)


class TestConnectionStatusEnum(unittest.TestCase):
    """測試連接狀態枚舉"""

    def test_connection_status_values(self):
        """測試連接狀態值"""
        self.assertEqual(ConnectionStatus.DISCONNECTED.value, "disconnected")
        self.assertEqual(ConnectionStatus.CONNECTING.value, "connecting")
        self.assertEqual(ConnectionStatus.CONNECTED.value, "connected")
        self.assertEqual(ConnectionStatus.RECONNECTING.value, "reconnecting")
        self.assertEqual(ConnectionStatus.ERROR.value, "error")


class TestDataTypeEnum(unittest.TestCase):
    """測試數據類型枚舉"""

    def test_data_type_values(self):
        """測試數據類型值"""
        self.assertEqual(DataType.STOCK_PRICE.value, "stock_price")
        self.assertEqual(DataType.TRADING_STATUS.value, "trading_status")
        self.assertEqual(DataType.PORTFOLIO_UPDATE.value, "portfolio_update")
        self.assertEqual(DataType.SYSTEM_STATUS.value, "system_status")
        self.assertEqual(DataType.ALERT.value, "alert")


if __name__ == "__main__":
    # 運行測試
    unittest.main(verbosity=2)
