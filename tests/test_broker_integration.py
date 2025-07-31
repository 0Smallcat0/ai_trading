"""券商 API 整合測試

此模組測試券商 API 整合功能的基本操作。
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# 添加 src 目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from execution.shioaji_adapter import ShioajiAdapter
from execution.ib_adapter import IBAdapter
from execution.broker_base import Order, OrderType, OrderStatus


class TestShioajiAdapter(unittest.TestCase):
    """永豐證券 API 適配器測試"""

    def setUp(self):
        """設置測試環境"""
        self.adapter = ShioajiAdapter(
            api_key="test_key",
            api_secret="test_secret",
            account_id="test_account"
        )

    @patch('execution.shioaji_adapter.sj')
    def test_connect_success(self, mock_sj):
        """測試連接成功"""
        # 模擬 API 物件
        mock_api = Mock()
        mock_api.Contracts = Mock()
        mock_sj.Shioaji.return_value = mock_api
        
        # 模擬帳戶
        mock_account = Mock()
        mock_account.account_id = "test_account"
        mock_api.list_accounts.return_value = [mock_account]
        
        self.adapter.api = mock_api
        
        # 測試連接
        result = self.adapter._validate_credentials()
        self.assertTrue(result)

    def test_get_connection_info(self):
        """測試獲取連接資訊"""
        info = self.adapter.get_connection_info()
        
        self.assertIn("connected", info)
        self.assertIn("account_id", info)
        self.assertIn("connection_errors", info)

    def test_order_creation(self):
        """測試訂單創建"""
        order = Order(
            stock_id="2330",
            action="buy",
            quantity=1000,
            price=500.0,
            order_type=OrderType.LIMIT
        )
        
        self.assertEqual(order.stock_id, "2330")
        self.assertEqual(order.action, "buy")
        self.assertEqual(order.quantity, 1000)
        self.assertEqual(order.price, 500.0)
        self.assertEqual(order.order_type, OrderType.LIMIT)


class TestIBAdapter(unittest.TestCase):
    """Interactive Brokers API 適配器測試"""

    def setUp(self):
        """設置測試環境"""
        with patch('execution.ib_adapter.EClient'), \
             patch('execution.ib_adapter.IBWrapper'):
            self.adapter = IBAdapter(
                host="127.0.0.1",
                port=7497,
                client_id=1
            )

    def test_connection_info(self):
        """測試連接資訊"""
        info = self.adapter.get_connection_info()
        
        self.assertIn("connected", info)
        self.assertIn("host", info)
        self.assertIn("port", info)
        self.assertIn("client_id", info)

    def test_contract_creation(self):
        """測試合約創建"""
        # 測試美股合約
        contract = self.adapter._create_contract("AAPL")
        self.assertIsNotNone(contract)
        
        # 測試台股合約
        contract = self.adapter._create_contract("2330.TW")
        self.assertIsNotNone(contract)
        
        # 測試港股合約
        contract = self.adapter._create_contract("0700.HK")
        self.assertIsNotNone(contract)

    def test_market_data_request(self):
        """測試市場資料請求"""
        with patch.object(self.adapter, 'connected', True):
            market_data = self.adapter.get_market_data("AAPL")
            
            self.assertIn("stock_id", market_data)
            self.assertIn("price", market_data)
            self.assertIn("bid", market_data)
            self.assertIn("ask", market_data)


class TestBrokerIntegration(unittest.TestCase):
    """券商整合測試"""

    def test_adapter_factory(self):
        """測試適配器工廠模式"""
        # 測試創建不同類型的適配器
        adapters = {
            'shioaji': ShioajiAdapter,
            'ib': IBAdapter,
        }
        
        for adapter_type, adapter_class in adapters.items():
            with self.subTest(adapter_type=adapter_type):
                if adapter_type == 'shioaji':
                    adapter = adapter_class(
                        api_key="test",
                        api_secret="test"
                    )
                else:  # ib
                    with patch('execution.ib_adapter.EClient'), \
                         patch('execution.ib_adapter.IBWrapper'):
                        adapter = adapter_class()
                
                self.assertIsNotNone(adapter)
                self.assertFalse(adapter.connected)

    def test_order_status_conversion(self):
        """測試訂單狀態轉換"""
        adapter = ShioajiAdapter()
        
        # 測試狀態轉換
        test_cases = [
            ("Submitted", OrderStatus.SUBMITTED),
            ("Filled", OrderStatus.FILLED),
            ("Cancelled", OrderStatus.CANCELLED),
        ]
        
        for input_status, expected_status in test_cases:
            with self.subTest(input_status=input_status):
                # 這裡需要根據實際的狀態轉換邏輯進行測試
                pass


if __name__ == '__main__':
    # 設置測試環境
    os.environ['TESTING'] = '1'
    
    # 運行測試
    unittest.main(verbosity=2)
