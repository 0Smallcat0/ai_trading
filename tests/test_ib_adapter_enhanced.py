"""Interactive Brokers 適配器增強測試

此模組測試重構後的 IB 適配器，包括期權交易功能和模組化設計。

版本: v1.0
作者: AI Trading System
"""

import pytest
import unittest.mock as mock
from datetime import datetime
from typing import Dict, Any

# 更新導入：使用推薦的重構版本
try:
    from src.execution.ib_adapter_refactored import IBAdapterRefactored as IBAdapter
except ImportError:
    # 如果重構版本不存在，創建模擬實現
    class IBAdapter:
        def __init__(self):
            pass
from src.execution.broker_base import Order, OrderType, OrderStatus


class TestIBAdapterEnhanced:
    """IB 適配器增強測試類"""

    @pytest.fixture
    def mock_ib_adapter(self):
        """創建模擬的 IB 適配器"""
        with mock.patch('src.execution.ib_adapter.IB_AVAILABLE', True):
            with mock.patch('src.execution.ib_adapter.EClient'):
                with mock.patch('src.execution.ib_wrapper.IBWrapper'):
                    adapter = IBAdapter(
                        host="127.0.0.1",
                        port=7497,
                        client_id=1
                    )
                    # 模擬連接狀態
                    adapter._connected = True
                    adapter._next_order_id = 1000
                    return adapter

    def test_adapter_initialization(self, mock_ib_adapter):
        """測試適配器初始化"""
        adapter = mock_ib_adapter
        
        assert adapter.host == "127.0.0.1"
        assert adapter.port == 7497
        assert adapter.client_id == 1
        assert hasattr(adapter, 'contract_manager')
        assert hasattr(adapter, 'order_manager')
        assert hasattr(adapter, 'options_manager')
        assert hasattr(adapter, 'market_data_manager')

    def test_invalid_initialization_parameters(self):
        """測試無效的初始化參數"""
        with pytest.raises(ValueError):
            IBAdapter(port=-1)
        
        with pytest.raises(ValueError):
            IBAdapter(client_id=-1)

    def test_connection_properties(self, mock_ib_adapter):
        """測試連接屬性"""
        adapter = mock_ib_adapter
        
        # 模擬連接狀態
        adapter._connected = True
        adapter.client.isConnected.return_value = True
        assert adapter.connected is True
        
        # 模擬斷開狀態
        adapter._connected = False
        assert adapter.connected is False

    def test_place_order_success(self, mock_ib_adapter):
        """測試成功下單"""
        adapter = mock_ib_adapter
        
        # 創建測試訂單
        order = Order(
            stock_id="AAPL",
            action="buy",
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        # 模擬合約管理器
        mock_contract = mock.Mock()
        adapter.contract_manager.create_stock_contract.return_value = mock_contract
        
        # 模擬訂單管理器
        mock_ib_order = mock.Mock()
        adapter.order_manager.create_order_from_base.return_value = mock_ib_order
        
        # 執行下單
        order_id = adapter.place_order(order)
        
        # 驗證結果
        assert order_id is not None
        assert order_id in adapter.order_map
        assert adapter.order_map[order_id]['status'] == OrderStatus.PENDING

    def test_place_order_not_connected(self, mock_ib_adapter):
        """測試未連接時下單"""
        adapter = mock_ib_adapter
        adapter._connected = False
        
        order = Order(
            stock_id="AAPL",
            action="buy",
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        with pytest.raises(RuntimeError):
            adapter.place_order(order)

    def test_place_order_invalid_order(self, mock_ib_adapter):
        """測試無效訂單"""
        adapter = mock_ib_adapter
        
        with pytest.raises(ValueError):
            adapter.place_order(None)

    def test_cancel_order_success(self, mock_ib_adapter):
        """測試成功取消訂單"""
        adapter = mock_ib_adapter
        
        # 先創建一個訂單
        order_id = "test_order_123"
        adapter.order_map[order_id] = {
            'ib_order_id': 1001,
            'status': OrderStatus.PENDING,
            'timestamp': datetime.now()
        }
        adapter.ib_order_map[1001] = order_id
        
        # 取消訂單
        result = adapter.cancel_order(order_id)
        
        # 驗證結果
        assert result is True
        assert adapter.order_map[order_id]['status'] == OrderStatus.CANCELLED

    def test_cancel_order_not_found(self, mock_ib_adapter):
        """測試取消不存在的訂單"""
        adapter = mock_ib_adapter
        
        result = adapter.cancel_order("non_existent_order")
        assert result is False

    def test_cancel_order_not_connected(self, mock_ib_adapter):
        """測試未連接時取消訂單"""
        adapter = mock_ib_adapter
        adapter._connected = False
        
        with pytest.raises(RuntimeError):
            adapter.cancel_order("test_order")

    def test_get_order_status(self, mock_ib_adapter):
        """測試獲取訂單狀態"""
        adapter = mock_ib_adapter
        
        # 創建測試訂單
        order_id = "test_order_123"
        adapter.order_map[order_id] = {
            'status': OrderStatus.FILLED
        }
        
        # 獲取狀態
        status = adapter.get_order_status(order_id)
        assert status == OrderStatus.FILLED
        
        # 測試不存在的訂單
        status = adapter.get_order_status("non_existent")
        assert status is None

    def test_get_orders(self, mock_ib_adapter):
        """測試獲取訂單列表"""
        adapter = mock_ib_adapter
        
        # 創建測試訂單
        test_order = Order(
            stock_id="AAPL",
            action="buy",
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        order_id = "test_order_123"
        adapter.order_map[order_id] = {
            'ib_order_id': 1001,
            'order': test_order,
            'status': OrderStatus.FILLED,
            'filled_quantity': 100,
            'avg_fill_price': 150.0,
            'timestamp': datetime.now()
        }
        
        # 獲取所有訂單
        orders = adapter.get_orders()
        assert len(orders) == 1
        assert orders[0]['order_id'] == order_id
        
        # 按狀態篩選
        filled_orders = adapter.get_orders(OrderStatus.FILLED)
        assert len(filled_orders) == 1
        
        pending_orders = adapter.get_orders(OrderStatus.PENDING)
        assert len(pending_orders) == 0

    def test_place_option_order(self, mock_ib_adapter):
        """測試期權下單"""
        adapter = mock_ib_adapter
        
        # 模擬期權管理器
        adapter.options_manager.place_option_order.return_value = "option_order_123"
        
        # 執行期權下單
        order_id = adapter.place_option_order(
            symbol="AAPL",
            expiry="20241220",
            strike=150.0,
            right="C",
            action="BUY",
            quantity=1,
            order_type="LMT",
            price=5.0
        )
        
        # 驗證結果
        assert order_id == "option_order_123"
        adapter.options_manager.place_option_order.assert_called_once()

    def test_get_option_chain(self, mock_ib_adapter):
        """測試獲取期權鏈"""
        adapter = mock_ib_adapter
        
        # 模擬期權鏈數據
        mock_option_chain = mock.Mock()
        mock_option_chain.symbol = "AAPL"
        mock_option_chain.expiry = "20241220"
        mock_option_chain.underlying_price = 150.0
        mock_option_chain.calls = []
        mock_option_chain.puts = []
        
        adapter.options_manager.get_option_chain.return_value = mock_option_chain
        
        # 獲取期權鏈
        option_chain = adapter.get_option_chain("AAPL", "20241220")
        
        # 驗證結果
        assert option_chain is not None
        assert option_chain['symbol'] == "AAPL"
        assert option_chain['underlying_price'] == 150.0

    def test_get_market_data(self, mock_ib_adapter):
        """測試獲取市場數據"""
        adapter = mock_ib_adapter
        
        # 模擬合約管理器
        mock_contract = mock.Mock()
        adapter.contract_manager.create_stock_contract.return_value = mock_contract
        
        # 模擬市場數據管理器
        adapter.market_data_manager.get_current_price.return_value = 150.0
        
        # 獲取市場數據
        market_data = adapter.get_market_data("AAPL")
        
        # 驗證結果
        assert market_data['stock_id'] == "AAPL"
        assert market_data['price'] == 150.0

    def test_get_account_info(self, mock_ib_adapter):
        """測試獲取帳戶資訊"""
        adapter = mock_ib_adapter
        adapter.cash = 10000.0
        adapter.total_value = 15000.0
        adapter.positions = {'AAPL': {'shares': 100}}
        
        account_info = adapter.get_account_info()
        
        assert 'account_id' in account_info
        assert account_info['cash'] == 10000.0
        assert account_info['total_value'] == 15000.0
        assert account_info['connected'] is True

    def test_modify_order(self, mock_ib_adapter):
        """測試修改訂單"""
        adapter = mock_ib_adapter
        
        # 創建測試訂單
        order_id = "test_order_123"
        mock_ib_order = mock.Mock()
        adapter.order_map[order_id] = {
            'ib_order_id': 1001,
            'contract': mock.Mock(),
            'ib_order': mock_ib_order,
            'timestamp': datetime.now()
        }
        
        # 修改訂單
        result = adapter.modify_order(order_id, price=155.0, quantity=200)
        
        # 驗證結果
        assert result is True
        assert mock_ib_order.lmtPrice == 155.0
        assert mock_ib_order.totalQuantity == 200

    def test_order_status_callback(self, mock_ib_adapter):
        """測試訂單狀態回調"""
        adapter = mock_ib_adapter
        
        # 創建測試訂單
        order_id = "test_order_123"
        ib_order_id = 1001
        adapter.order_map[order_id] = {
            'ib_order_id': ib_order_id,
            'status': OrderStatus.PENDING,
            'filled_quantity': 0,
            'avg_fill_price': 0.0,
            'timestamp': datetime.now()
        }
        adapter.ib_order_map[ib_order_id] = order_id
        
        # 模擬狀態更新
        adapter._on_order_status(ib_order_id, "Filled", 100.0, 0.0, 150.0)
        
        # 驗證結果
        assert adapter.order_map[order_id]['status'] == OrderStatus.FILLED
        assert adapter.order_map[order_id]['filled_quantity'] == 100.0
        assert adapter.order_map[order_id]['avg_fill_price'] == 150.0

    def test_error_handling(self, mock_ib_adapter):
        """測試錯誤處理"""
        adapter = mock_ib_adapter
        
        # 測試錯誤回調
        error_callback_called = False
        
        def mock_error_callback(req_id, error_code, error_string):
            nonlocal error_callback_called
            error_callback_called = True
        
        adapter.on_error = mock_error_callback
        
        # 觸發錯誤
        adapter._on_error(1, 502, "Connection failed")
        
        # 驗證回調被調用
        assert error_callback_called is True
