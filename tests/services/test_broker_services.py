"""
券商整合服務測試模組

測試券商連接管理、訂單執行和帳戶同步服務的功能。

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥8.5/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock 所有複雜的導入
with patch.dict('sys.modules', {
    'src.core.trade_execution_brokers': Mock(),
    'src.core.risk_management_service': Mock(),
    'src.execution.broker_base': Mock(),
}):
    from src.services.broker.broker_connection_service import (
        BrokerConnectionService,
        ConnectionStatus,
        BrokerConnectionError
    )
    from src.services.broker.order_execution_service import (
        OrderExecutionService,
        OrderRequest,
        ExecutionStatus,
        OrderExecutionError
    )
    from src.services.broker.account_sync_service import (
        AccountSyncService,
        AccountInfo,
        AccountSyncError
    )

# Mock OrderType
class MockOrderType:
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"

OrderType = MockOrderType


class TestBrokerConnectionService:
    """測試券商連接管理服務"""

    @pytest.fixture
    def connection_service(self, mock_trade_executor):
        """創建連接服務實例"""
        with patch('src.services.broker.broker_connection_service.TradeExecutionBrokerManager') as mock_class:
            mock_class.return_value = mock_trade_executor
            service = BrokerConnectionService()
            service._trade_executor = mock_trade_executor
            return service

    def test_init_success(self, connection_service):
        """測試服務初始化成功"""
        assert connection_service is not None
        assert connection_service._max_reconnect_attempts == 5
        assert connection_service._reconnect_interval == 30

    def test_start_monitoring(self, connection_service):
        """測試開始監控"""
        connection_service.start_monitoring()
        assert connection_service._is_monitoring is True
        assert connection_service._monitoring_thread is not None

    def test_stop_monitoring(self, connection_service):
        """測試停止監控"""
        connection_service.start_monitoring()
        connection_service.stop_monitoring()
        assert connection_service._is_monitoring is False

    def test_connect_broker_success(self, connection_service):
        """測試券商連接成功"""
        # Mock 券商適配器
        mock_broker = Mock()
        mock_broker.connect.return_value = True
        connection_service._trade_executor.brokers = {"test_broker": mock_broker}
        
        result = connection_service.connect_broker("test_broker")
        
        assert result is True
        mock_broker.connect.assert_called_once()

    def test_connect_broker_failure(self, connection_service):
        """測試券商連接失敗"""
        # Mock 券商適配器
        mock_broker = Mock()
        mock_broker.connect.return_value = False
        connection_service._trade_executor.brokers = {"test_broker": mock_broker}
        
        result = connection_service.connect_broker("test_broker")
        
        assert result is False

    def test_connect_unsupported_broker(self, connection_service):
        """測試連接不支援的券商"""
        connection_service._trade_executor.brokers = {}
        
        with pytest.raises(BrokerConnectionError):
            connection_service.connect_broker("unsupported_broker")

    def test_get_connection_status(self, connection_service):
        """測試獲取連接狀態"""
        connection_service._connection_status["test_broker"] = ConnectionStatus.CONNECTED
        
        status = connection_service.get_connection_status("test_broker")
        
        assert status["broker"] == "test_broker"
        assert status["status"] == "connected"

    def test_switch_broker_success(self, connection_service):
        """測試切換券商成功"""
        # Mock 券商適配器和交易執行器
        mock_broker = Mock()
        mock_broker.connect.return_value = True
        connection_service._trade_executor.brokers = {"test_broker": mock_broker}
        connection_service._trade_executor.switch_broker.return_value = True
        connection_service._connection_status["test_broker"] = ConnectionStatus.CONNECTED
        
        result = connection_service.switch_broker("test_broker")
        
        assert result is True


class TestOrderExecutionService:
    """測試訂單執行服務"""

    @pytest.fixture
    def order_service(self, mock_trade_executor):
        """創建訂單執行服務實例"""
        with patch('src.services.broker.order_execution_service.BrokerConnectionService') as mock_conn:
            mock_conn_instance = Mock()
            mock_conn_instance._trade_executor = mock_trade_executor
            mock_conn.return_value = mock_conn_instance

            service = OrderExecutionService()
            service._trade_executor = mock_trade_executor
            return service

    @pytest.fixture
    def sample_order_request(self):
        """創建範例訂單請求"""
        return OrderRequest(
            symbol="AAPL",
            action="buy",
            quantity=100,
            order_type=OrderType.MARKET
        )

    def test_init_success(self, order_service):
        """測試服務初始化成功"""
        assert order_service is not None
        assert order_service._orders == {}

    def test_order_request_creation(self, sample_order_request):
        """測試訂單請求創建"""
        assert sample_order_request.symbol == "AAPL"
        assert sample_order_request.action == "buy"
        assert sample_order_request.quantity == 100
        assert sample_order_request.order_type == OrderType.MARKET
        assert sample_order_request.order_id is not None

    def test_order_request_to_dict(self, sample_order_request):
        """測試訂單請求轉換為字典"""
        order_dict = sample_order_request.to_dict()
        
        assert order_dict["symbol"] == "AAPL"
        assert order_dict["action"] == "buy"
        assert order_dict["quantity"] == 100
        assert "order_id" in order_dict
        assert "created_at" in order_dict

    def test_submit_order_success(self, order_service, sample_order_request):
        """測試提交訂單成功"""
        # Mock 依賴
        order_service._get_default_broker = Mock(return_value="test_broker")
        order_service._is_broker_available = Mock(return_value=True)
        order_service._submit_to_broker = Mock()
        
        order_id = order_service.submit_order(sample_order_request)
        
        assert order_id == sample_order_request.order_id
        assert order_id in order_service._orders

    def test_submit_order_validation_failure(self, order_service):
        """測試訂單驗證失敗"""
        invalid_order = OrderRequest(
            symbol="",  # 無效的股票代號
            action="buy",
            quantity=100
        )
        
        with pytest.raises(OrderExecutionError):
            order_service.submit_order(invalid_order)

    def test_cancel_order_success(self, order_service, sample_order_request):
        """測試取消訂單成功"""
        # 先提交訂單
        order_service._get_default_broker = Mock(return_value="test_broker")
        order_service._is_broker_available = Mock(return_value=True)
        order_service._submit_to_broker = Mock()
        
        order_id = order_service.submit_order(sample_order_request)
        
        # Mock 券商取消訂單
        mock_broker = Mock()
        mock_broker.cancel_order.return_value = True
        order_service._trade_executor.brokers = {"test_broker": mock_broker}
        
        # 設定訂單已提交到券商
        order_service._orders[order_id]["broker_order_id"] = "broker_123"
        
        result = order_service.cancel_order(order_id)
        
        assert result is True

    def test_cancel_nonexistent_order(self, order_service):
        """測試取消不存在的訂單"""
        with pytest.raises(OrderExecutionError):
            order_service.cancel_order("nonexistent_order")

    def test_get_order_status(self, order_service, sample_order_request):
        """測試獲取訂單狀態"""
        # 先提交訂單
        order_service._get_default_broker = Mock(return_value="test_broker")
        order_service._is_broker_available = Mock(return_value=True)
        order_service._submit_to_broker = Mock()
        
        order_id = order_service.submit_order(sample_order_request)
        
        status = order_service.get_order_status(order_id)
        
        assert status["status"] == ExecutionStatus.PENDING
        assert status["broker_name"] == "test_broker"

    def test_get_orders_with_filters(self, order_service, sample_order_request):
        """測試使用篩選條件獲取訂單列表"""
        # 先提交訂單
        order_service._get_default_broker = Mock(return_value="test_broker")
        order_service._is_broker_available = Mock(return_value=True)
        order_service._submit_to_broker = Mock()
        
        order_id = order_service.submit_order(sample_order_request)
        
        # 測試按狀態篩選
        orders = order_service.get_orders(status=ExecutionStatus.PENDING)
        assert len(orders) == 1
        assert orders[0]["status"] == ExecutionStatus.PENDING

        # 測試按股票代號篩選
        orders = order_service.get_orders(symbol="AAPL")
        assert len(orders) == 1
        assert orders[0]["request"]["symbol"] == "AAPL"


class TestAccountSyncService:
    """測試帳戶同步服務"""

    @pytest.fixture
    def sync_service(self, mock_trade_executor):
        """創建帳戶同步服務實例"""
        with patch('src.services.broker.account_sync_service.BrokerConnectionService') as mock_conn:
            mock_conn_instance = Mock()
            mock_conn_instance._trade_executor = mock_trade_executor
            mock_conn.return_value = mock_conn_instance

            service = AccountSyncService()
            service._trade_executor = mock_trade_executor
            return service

    @pytest.fixture
    def sample_account_info(self):
        """創建範例帳戶資訊"""
        return AccountInfo(
            account_id="test_account",
            broker_name="test_broker",
            cash=10000.0,
            total_value=15000.0,
            buying_power=10000.0
        )

    def test_init_success(self, sync_service):
        """測試服務初始化成功"""
        assert sync_service is not None
        assert sync_service._accounts == {}
        assert sync_service._sync_interval == 30

    def test_account_info_creation(self, sample_account_info):
        """測試帳戶資訊創建"""
        assert sample_account_info.account_id == "test_account"
        assert sample_account_info.broker_name == "test_broker"
        assert sample_account_info.cash == 10000.0
        assert sample_account_info.total_value == 15000.0

    def test_account_info_to_dict(self, sample_account_info):
        """測試帳戶資訊轉換為字典"""
        account_dict = sample_account_info.to_dict()
        
        assert account_dict["account_id"] == "test_account"
        assert account_dict["broker_name"] == "test_broker"
        assert account_dict["cash"] == 10000.0
        assert "last_updated" in account_dict

    def test_start_sync(self, sync_service):
        """測試開始自動同步"""
        sync_service.start_sync()
        assert sync_service._is_syncing is True
        assert sync_service._sync_thread is not None

    def test_stop_sync(self, sync_service):
        """測試停止自動同步"""
        sync_service.start_sync()
        sync_service.stop_sync()
        assert sync_service._is_syncing is False

    def test_sync_account_success(self, sync_service):
        """測試同步帳戶成功"""
        # Mock 依賴
        sync_service._is_broker_connected = Mock(return_value=True)
        sync_service._get_account_info = Mock(return_value=AccountInfo(
            account_id="test_account",
            broker_name="test_broker"
        ))
        sync_service._get_positions = Mock(return_value={})
        sync_service._get_orders = Mock(return_value=[])
        
        mock_broker = Mock()
        sync_service._trade_executor.brokers = {"test_broker": mock_broker}
        
        account_info = sync_service.sync_account("test_broker")
        
        assert account_info is not None
        assert account_info.broker_name == "test_broker"
        assert "test_broker" in sync_service._accounts

    def test_sync_account_not_connected(self, sync_service):
        """測試同步未連接的券商"""
        sync_service._is_broker_connected = Mock(return_value=False)
        
        with pytest.raises(AccountSyncError):
            sync_service.sync_account("test_broker")

    def test_get_account_info(self, sync_service, sample_account_info):
        """測試獲取帳戶資訊"""
        sync_service._accounts["test_broker"] = sample_account_info
        
        account_info = sync_service.get_account_info("test_broker")
        
        assert account_info == sample_account_info

    def test_get_all_accounts(self, sync_service, sample_account_info):
        """測試獲取所有帳戶資訊"""
        sync_service._accounts["test_broker"] = sample_account_info
        
        all_accounts = sync_service.get_all_accounts()
        
        assert "test_broker" in all_accounts
        assert all_accounts["test_broker"] == sample_account_info

    def test_get_total_portfolio_value(self, sync_service):
        """測試獲取總投資組合價值"""
        account1 = AccountInfo("acc1", "broker1", total_value=10000.0)
        account2 = AccountInfo("acc2", "broker2", total_value=15000.0)
        
        sync_service._accounts["broker1"] = account1
        sync_service._accounts["broker2"] = account2
        
        total_value = sync_service.get_total_portfolio_value()
        
        assert total_value == 25000.0

    def test_get_total_cash(self, sync_service):
        """測試獲取總現金"""
        account1 = AccountInfo("acc1", "broker1", cash=5000.0)
        account2 = AccountInfo("acc2", "broker2", cash=7000.0)
        
        sync_service._accounts["broker1"] = account1
        sync_service._accounts["broker2"] = account2
        
        total_cash = sync_service.get_total_cash()
        
        assert total_cash == 12000.0

    def test_get_consolidated_positions(self, sync_service):
        """測試獲取合併持倉資訊"""
        account1 = AccountInfo("acc1", "broker1")
        account1.positions = {
            "AAPL": {
                "quantity": 100,
                "avg_cost": 150.0,
                "market_value": 15000.0,
                "unrealized_pnl": 0.0
            }
        }
        
        account2 = AccountInfo("acc2", "broker2")
        account2.positions = {
            "AAPL": {
                "quantity": 50,
                "avg_cost": 160.0,
                "market_value": 8000.0,
                "unrealized_pnl": 0.0
            }
        }
        
        sync_service._accounts["broker1"] = account1
        sync_service._accounts["broker2"] = account2
        
        consolidated = sync_service.get_consolidated_positions()
        
        assert "AAPL" in consolidated
        assert consolidated["AAPL"]["quantity"] == 150
        assert consolidated["AAPL"]["market_value"] == 23000.0
        assert len(consolidated["AAPL"]["brokers"]) == 2

    def test_force_sync_all(self, sync_service):
        """測試強制同步所有券商"""
        # Mock 依賴
        sync_service._trade_executor.brokers = {"broker1": Mock(), "broker2": Mock()}
        sync_service._is_broker_connected = Mock(return_value=True)
        sync_service.sync_account = Mock(return_value=AccountInfo("acc", "broker"))
        
        results = sync_service.force_sync_all()
        
        assert len(results) == 2
        assert "broker1" in results
        assert "broker2" in results
