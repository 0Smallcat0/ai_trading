"""交易執行 API 測試模組

測試交易執行相關的 API 端點功能。
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.routers.live_trading.trade_execution import router
from src.api.routers.live_trading.models import OrderType, OrderSide, OrderStatus


# 創建測試應用
app = FastAPI()
app.include_router(router)

client = TestClient(app)


class TestTradeExecutionAPI:
    """交易執行 API 測試類"""
    
    def setup_method(self):
        """測試前設定"""
        self.mock_user = {
            "user_id": "test_user_123",
            "username": "test_user",
            "role": "trader"
        }
        
        self.place_order_request = {
            "symbol": "2330.TW",
            "side": "buy",
            "order_type": "limit",
            "quantity": 1000,
            "price": 590.0,
            "time_in_force": "DAY"
        }
        
        self.session_id = "test_session_123"
    
    @patch('src.api.routers.live_trading.trade_execution.get_current_user')
    @patch('src.api.routers.live_trading.trade_execution._perform_risk_check')
    @patch('src.api.routers.live_trading.trade_execution._execute_order')
    def test_place_order_success(self, mock_execute, mock_risk_check, mock_get_user):
        """測試下單成功"""
        mock_get_user.return_value = self.mock_user
        mock_risk_check.return_value = {"approved": True, "message": "風險檢查通過"}
        
        # 模擬訂單執行結果
        mock_order_response = MagicMock()
        mock_order_response.order_id = "ORD_TEST_001"
        mock_order_response.status = OrderStatus.PENDING
        mock_execute.return_value = mock_order_response
        
        response = client.post(
            f"/place-order?session_id={self.session_id}",
            json=self.place_order_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success"] is True
        assert "order_id" in data["data"]
        assert data["data"]["order_details"] is not None
    
    @patch('src.api.routers.live_trading.trade_execution.get_current_user')
    def test_place_order_missing_session(self, mock_get_user):
        """測試下單失敗 - 缺少會話"""
        mock_get_user.return_value = self.mock_user
        
        response = client.post("/place-order", json=self.place_order_request)
        
        assert response.status_code == 422  # 缺少必需參數
    
    @patch('src.api.routers.live_trading.trade_execution.get_current_user')
    @patch('src.api.routers.live_trading.trade_execution._perform_risk_check')
    def test_place_order_risk_check_failed(self, mock_risk_check, mock_get_user):
        """測試下單失敗 - 風險檢查未通過"""
        mock_get_user.return_value = self.mock_user
        mock_risk_check.return_value = {
            "approved": False, 
            "message": "單筆訂單金額超過限制"
        }
        
        response = client.post(
            f"/place-order?session_id={self.session_id}",
            json=self.place_order_request
        )
        
        assert response.status_code == 400
        assert "風險檢查未通過" in response.json()["detail"]
    
    @patch('src.api.routers.live_trading.trade_execution.get_current_user')
    @patch('src.api.routers.live_trading.trade_execution._active_orders')
    @patch('src.api.routers.live_trading.trade_execution._cancel_order_with_broker')
    def test_cancel_order_success(self, mock_cancel_broker, mock_orders, mock_get_user):
        """測試撤單成功"""
        mock_get_user.return_value = self.mock_user
        mock_cancel_broker.return_value = True
        
        # 模擬活躍訂單
        order_id = "ORD_TEST_001"
        mock_orders[order_id] = {
            "order_id": order_id,
            "user_id": self.mock_user["user_id"],
            "status": OrderStatus.PENDING,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        cancel_request = {"order_id": order_id}
        
        response = client.post(
            f"/cancel-order?session_id={self.session_id}",
            json=cancel_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["order_id"] == order_id
        assert data["data"]["status"] == "cancelled"
    
    @patch('src.api.routers.live_trading.trade_execution.get_current_user')
    @patch('src.api.routers.live_trading.trade_execution._active_orders')
    def test_cancel_order_not_found(self, mock_orders, mock_get_user):
        """測試撤單失敗 - 訂單不存在"""
        mock_get_user.return_value = self.mock_user
        mock_orders.clear()  # 清空訂單
        
        cancel_request = {"order_id": "NON_EXISTENT_ORDER"}
        
        response = client.post(
            f"/cancel-order?session_id={self.session_id}",
            json=cancel_request
        )
        
        assert response.status_code == 404
        assert "訂單不存在" in response.json()["detail"]
    
    @patch('src.api.routers.live_trading.trade_execution.get_current_user')
    @patch('src.api.routers.live_trading.trade_execution._active_orders')
    def test_cancel_order_wrong_user(self, mock_orders, mock_get_user):
        """測試撤單失敗 - 訂單不屬於當前用戶"""
        mock_get_user.return_value = self.mock_user
        
        # 模擬其他用戶的訂單
        order_id = "ORD_OTHER_USER_001"
        mock_orders[order_id] = {
            "order_id": order_id,
            "user_id": "other_user_456",
            "status": OrderStatus.PENDING
        }
        
        cancel_request = {"order_id": order_id}
        
        response = client.post(
            f"/cancel-order?session_id={self.session_id}",
            json=cancel_request
        )
        
        assert response.status_code == 403
        assert "無權限操作此訂單" in response.json()["detail"]
    
    @patch('src.api.routers.live_trading.trade_execution.get_current_user')
    @patch('src.api.routers.live_trading.trade_execution._active_orders')
    def test_cancel_order_already_filled(self, mock_orders, mock_get_user):
        """測試撤單失敗 - 訂單已成交"""
        mock_get_user.return_value = self.mock_user
        
        # 模擬已成交訂單
        order_id = "ORD_FILLED_001"
        mock_orders[order_id] = {
            "order_id": order_id,
            "user_id": self.mock_user["user_id"],
            "status": OrderStatus.FILLED
        }
        
        cancel_request = {"order_id": order_id}
        
        response = client.post(
            f"/cancel-order?session_id={self.session_id}",
            json=cancel_request
        )
        
        assert response.status_code == 400
        assert "訂單已完成或已取消" in response.json()["detail"]
    
    @patch('src.api.routers.live_trading.trade_execution.get_current_user')
    @patch('src.api.routers.live_trading.trade_execution._active_orders')
    @patch('src.api.routers.live_trading.trade_execution._modify_order_with_broker')
    def test_modify_order_success(self, mock_modify_broker, mock_orders, mock_get_user):
        """測試修改訂單成功"""
        mock_get_user.return_value = self.mock_user
        
        # 模擬活躍訂單
        order_id = "ORD_TEST_001"
        mock_orders[order_id] = {
            "order_id": order_id,
            "user_id": self.mock_user["user_id"],
            "status": OrderStatus.PENDING,
            "request": {
                "symbol": "2330.TW",
                "side": "buy",
                "order_type": "limit",
                "quantity": 1000,
                "price": 590.0
            },
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # 模擬修改後的訂單
        mock_updated_order = MagicMock()
        mock_updated_order.order_id = order_id
        mock_updated_order.quantity = 1500
        mock_updated_order.price = 585.0
        mock_modify_broker.return_value = mock_updated_order
        
        modify_request = {
            "order_id": order_id,
            "quantity": 1500,
            "price": 585.0
        }
        
        response = client.post(
            f"/modify-order?session_id={self.session_id}",
            json=modify_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] is not None
    
    @patch('src.api.routers.live_trading.trade_execution.get_current_user')
    @patch('src.api.routers.live_trading.trade_execution._get_current_positions')
    @patch('src.api.routers.live_trading.trade_execution._execute_order')
    def test_close_all_positions_success(self, mock_execute, mock_positions, mock_get_user):
        """測試一鍵平倉成功"""
        mock_get_user.return_value = self.mock_user
        
        # 模擬當前持倉
        mock_positions.return_value = [
            {
                "symbol": "2330.TW",
                "quantity": 1000,
                "side": "BUY",
                "current_price": 595.0
            },
            {
                "symbol": "0050.TW",
                "quantity": 500,
                "side": "BUY",
                "current_price": 141.8
            }
        ]
        
        # 模擬平倉訂單執行結果
        mock_order_response = MagicMock()
        mock_order_response.order_id = "CLOSE_TEST_001"
        mock_order_response.status = OrderStatus.FILLED
        mock_execute.return_value = mock_order_response
        
        close_request = {
            "order_type": "market"
        }
        
        response = client.post(
            f"/close-all-positions?session_id={self.session_id}",
            json=close_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 2  # 兩筆平倉訂單
        
        # 檢查所有平倉訂單都成功
        for order in data["data"]:
            assert order["success"] is True
            assert "order_id" in order
    
    @patch('src.api.routers.live_trading.trade_execution.get_current_user')
    @patch('src.api.routers.live_trading.trade_execution._get_current_positions')
    def test_close_all_positions_no_positions(self, mock_positions, mock_get_user):
        """測試一鍵平倉 - 沒有持倉"""
        mock_get_user.return_value = self.mock_user
        mock_positions.return_value = []  # 沒有持倉
        
        close_request = {
            "order_type": "market"
        }
        
        response = client.post(
            f"/close-all-positions?session_id={self.session_id}",
            json=close_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 0
        assert "沒有需要平倉的持倉" in data["message"]
    
    @patch('src.api.routers.live_trading.trade_execution.get_current_user')
    @patch('src.api.routers.live_trading.trade_execution._get_current_positions')
    @patch('src.api.routers.live_trading.trade_execution._execute_order')
    def test_close_specific_positions(self, mock_execute, mock_positions, mock_get_user):
        """測試平倉指定股票"""
        mock_get_user.return_value = self.mock_user
        
        # 模擬當前持倉
        mock_positions.return_value = [
            {
                "symbol": "2330.TW",
                "quantity": 1000,
                "side": "BUY",
                "current_price": 595.0
            },
            {
                "symbol": "0050.TW",
                "quantity": 500,
                "side": "BUY",
                "current_price": 141.8
            }
        ]
        
        # 模擬平倉訂單執行結果
        mock_order_response = MagicMock()
        mock_order_response.order_id = "CLOSE_2330_001"
        mock_order_response.status = OrderStatus.FILLED
        mock_execute.return_value = mock_order_response
        
        close_request = {
            "symbols": ["2330.TW"],  # 只平倉台積電
            "order_type": "market"
        }
        
        response = client.post(
            f"/close-all-positions?session_id={self.session_id}",
            json=close_request
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1  # 只有一筆平倉訂單
        assert data["data"][0]["success"] is True


class TestOrderValidation:
    """訂單驗證測試類"""
    
    def test_place_order_request_validation(self):
        """測試下單請求驗證"""
        from src.api.routers.live_trading.models import PlaceOrderRequest, OrderType, OrderSide
        
        # 測試有效的限價單
        valid_request = PlaceOrderRequest(
            symbol="2330.TW",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1000,
            price=590.0
        )
        assert valid_request.symbol == "2330.TW"
        assert valid_request.quantity == 1000
        assert valid_request.price == 590.0
    
    def test_place_order_request_validation_limit_order_missing_price(self):
        """測試限價單缺少價格的驗證"""
        from src.api.routers.live_trading.models import PlaceOrderRequest, OrderType, OrderSide
        from pydantic import ValidationError
        
        # 限價單必須有價格
        with pytest.raises(ValidationError) as exc_info:
            PlaceOrderRequest(
                symbol="2330.TW",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=1000
                # 缺少 price
            )
        
        assert "限價單和停損限價單必須指定價格" in str(exc_info.value)
    
    def test_place_order_request_validation_stop_order_missing_stop_price(self):
        """測試停損單缺少停損價格的驗證"""
        from src.api.routers.live_trading.models import PlaceOrderRequest, OrderType, OrderSide
        from pydantic import ValidationError
        
        # 停損單必須有停損價格
        with pytest.raises(ValidationError) as exc_info:
            PlaceOrderRequest(
                symbol="2330.TW",
                side=OrderSide.BUY,
                order_type=OrderType.STOP,
                quantity=1000
                # 缺少 stop_price
            )
        
        assert "停損單和停損限價單必須指定停損價格" in str(exc_info.value)
    
    def test_place_order_request_validation_negative_quantity(self):
        """測試負數量驗證"""
        from src.api.routers.live_trading.models import PlaceOrderRequest, OrderType, OrderSide
        from pydantic import ValidationError
        
        # 數量必須大於 0
        with pytest.raises(ValidationError):
            PlaceOrderRequest(
                symbol="2330.TW",
                side=OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=-100  # 負數量
            )


class TestRiskCheck:
    """風險檢查測試類"""
    
    @pytest.mark.asyncio
    async def test_perform_risk_check_approved(self):
        """測試風險檢查通過"""
        from src.api.routers.live_trading.trade_execution import _perform_risk_check
        from src.api.routers.live_trading.models import PlaceOrderRequest, OrderType, OrderSide
        
        request = PlaceOrderRequest(
            symbol="2330.TW",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=1000,
            price=590.0
        )
        
        user = {"user_id": "test_user"}
        
        result = await _perform_risk_check(request, user)
        
        assert result["approved"] is True
        assert "風險檢查通過" in result["message"]
    
    @pytest.mark.asyncio
    async def test_perform_risk_check_rejected_large_order(self):
        """測試風險檢查拒絕 - 訂單金額過大"""
        from src.api.routers.live_trading.trade_execution import _perform_risk_check
        from src.api.routers.live_trading.models import PlaceOrderRequest, OrderType, OrderSide
        
        request = PlaceOrderRequest(
            symbol="2330.TW",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=100000,  # 大數量
            price=1000.0      # 高價格
        )
        
        user = {"user_id": "test_user"}
        
        result = await _perform_risk_check(request, user)
        
        assert result["approved"] is False
        assert "單筆訂單金額超過限制" in result["message"]


if __name__ == "__main__":
    pytest.main([__file__])
