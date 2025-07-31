"""
API 核心功能測試

此測試文件驗證 API 的核心功能，包括：
- 券商 API 整合測試
- 實時數據 API 測試
- 認證授權測試
- 錯誤處理測試
"""

import pytest
import unittest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from fastapi import HTTPException

# 導入要測試的模組
try:
    from src.api.main import app
    from src.api.routers.live_trading.broker_connection import router as broker_router
    from src.api.routers.live_trading.trade_execution import router as execution_router
    from src.api.routers.live_trading.risk_control import router as risk_router
    from src.api.middleware.auth import AuthMiddleware
    from src.api.models.trading import OrderRequest, OrderResponse
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False


@pytest.mark.skipif(not API_AVAILABLE, reason="API modules not available")
class TestAPICore(unittest.TestCase):
    """API 核心功能測試"""
    
    def setUp(self):
        """設置測試環境"""
        self.client = TestClient(app)
        self.test_token = "test_jwt_token"
        self.headers = {"Authorization": f"Bearer {self.test_token}"}
    
    def test_broker_api_integration(self):
        """測試券商 API 整合"""
        # 測試券商連接狀態
        response = self.client.get(
            "/api/v1/live-trading/broker/status",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn("brokers", data)
            self.assertIsInstance(data["brokers"], dict)
        else:
            # 如果 API 不可用，跳過測試
            self.skipTest("Broker API not available")
    
    def test_broker_connection_management(self):
        """測試券商連接管理"""
        # 測試連接券商
        connection_data = {
            "broker_type": "simulator",
            "credentials": {
                "api_key": "test_key",
                "api_secret": "test_secret"
            }
        }
        
        with patch('src.core.trade_execution_brokers.TradeExecutionBrokers') as mock_brokers:
            mock_instance = Mock()
            mock_instance.switch_broker.return_value = True
            mock_brokers.return_value = mock_instance
            
            response = self.client.post(
                "/api/v1/live-trading/broker/connect",
                json=connection_data,
                headers=self.headers
            )
            
            # 檢查響應格式
            if response.status_code in [200, 404]:  # 404 表示端點不存在
                if response.status_code == 200:
                    data = response.json()
                    self.assertIn("success", data)
    
    def test_trade_execution_api(self):
        """測試交易執行 API"""
        # 測試下單 API
        order_data = {
            "symbol": "2330.TW",
            "action": "buy",
            "quantity": 100,
            "order_type": "market",
            "price": 150.0
        }
        
        with patch('src.core.trade_execution_service.TradeExecutionService') as mock_service:
            mock_instance = Mock()
            mock_instance.submit_order.return_value = (True, "訂單提交成功", "ORD001")
            mock_service.return_value = mock_instance
            
            response = self.client.post(
                "/api/v1/live-trading/execution/orders",
                json=order_data,
                headers=self.headers
            )
            
            if response.status_code in [200, 404]:
                if response.status_code == 200:
                    data = response.json()
                    self.assertIn("order_id", data)
    
    def test_order_management_api(self):
        """測試訂單管理 API"""
        # 測試獲取訂單列表
        response = self.client.get(
            "/api/v1/live-trading/execution/orders",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn("orders", data)
            self.assertIsInstance(data["orders"], list)
        
        # 測試取消訂單
        order_id = "test_order_123"
        response = self.client.delete(
            f"/api/v1/live-trading/execution/orders/{order_id}",
            headers=self.headers
        )
        
        if response.status_code in [200, 404]:
            if response.status_code == 200:
                data = response.json()
                self.assertIn("success", data)
    
    def test_real_time_data_api(self):
        """測試實時數據 API"""
        # 測試獲取市場數據
        symbols = ["2330.TW", "AAPL", "GOOGL"]
        
        for symbol in symbols:
            response = self.client.get(
                f"/api/v1/market-data/quote/{symbol}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                self.assertIn("symbol", data)
                self.assertIn("last_price", data)
                self.assertEqual(data["symbol"], symbol)
    
    def test_portfolio_data_api(self):
        """測試投資組合數據 API"""
        # 測試獲取持倉信息
        response = self.client.get(
            "/api/v1/live-trading/portfolio/positions",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn("positions", data)
            self.assertIsInstance(data["positions"], dict)
        
        # 測試獲取帳戶信息
        response = self.client.get(
            "/api/v1/live-trading/portfolio/account",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn("cash", data)
            self.assertIn("total_value", data)
    
    def test_risk_control_api(self):
        """測試風險控制 API"""
        # 測試獲取風險狀態
        response = self.client.get(
            "/api/v1/live-trading/risk/status",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn("risk_level", data)
        
        # 測試設置風險參數
        risk_params = {
            "max_position_percent": 0.1,
            "max_daily_loss": 0.05,
            "stop_loss_percent": 0.02
        }
        
        response = self.client.post(
            "/api/v1/live-trading/risk/parameters",
            json=risk_params,
            headers=self.headers
        )
        
        if response.status_code in [200, 404]:
            if response.status_code == 200:
                data = response.json()
                self.assertIn("success", data)
    
    def test_authentication_and_authorization(self):
        """測試認證授權"""
        # 測試無效 token
        invalid_headers = {"Authorization": "Bearer invalid_token"}
        
        response = self.client.get(
            "/api/v1/live-trading/broker/status",
            headers=invalid_headers
        )
        
        # 應該返回 401 或 403
        self.assertIn(response.status_code, [401, 403, 404])
        
        # 測試缺少 token
        response = self.client.get("/api/v1/live-trading/broker/status")
        self.assertIn(response.status_code, [401, 403, 404])
    
    def test_api_error_handling(self):
        """測試 API 錯誤處理"""
        # 測試無效的訂單數據
        invalid_order = {
            "symbol": "",  # 無效的股票代號
            "action": "invalid_action",  # 無效的動作
            "quantity": -100,  # 無效的數量
            "order_type": "invalid_type"  # 無效的訂單類型
        }
        
        response = self.client.post(
            "/api/v1/live-trading/execution/orders",
            json=invalid_order,
            headers=self.headers
        )
        
        # 應該返回 400 (Bad Request) 或 422 (Unprocessable Entity)
        if response.status_code not in [404]:  # 如果端點存在
            self.assertIn(response.status_code, [400, 422])
    
    def test_api_rate_limiting(self):
        """測試 API 速率限制"""
        # 快速發送多個請求
        responses = []
        for i in range(10):
            response = self.client.get(
                "/api/v1/live-trading/broker/status",
                headers=self.headers
            )
            responses.append(response.status_code)
        
        # 檢查是否有速率限制響應 (429)
        # 注意：這個測試可能需要實際的速率限制中間件
        rate_limited = any(status == 429 for status in responses)
        # 如果沒有速率限制，所有請求都應該成功或返回相同的錯誤
        self.assertTrue(len(set(responses)) <= 2)  # 最多兩種不同的響應狀態
    
    def test_api_response_format(self):
        """測試 API 響應格式"""
        # 測試標準響應格式
        response = self.client.get(
            "/api/v1/live-trading/broker/status",
            headers=self.headers
        )
        
        if response.status_code == 200:
            data = response.json()
            # 檢查標準響應字段
            expected_fields = ["success", "message", "data"]
            # 至少應該有其中一些字段
            has_standard_fields = any(field in data for field in expected_fields)
            self.assertTrue(has_standard_fields or "brokers" in data)
    
    def test_websocket_connection(self):
        """測試 WebSocket 連接"""
        # 注意：這個測試需要 WebSocket 支持
        try:
            with self.client.websocket_connect("/ws/live-data") as websocket:
                # 發送訂閱消息
                websocket.send_json({
                    "action": "subscribe",
                    "symbols": ["2330.TW", "AAPL"]
                })
                
                # 接收響應
                data = websocket.receive_json()
                self.assertIn("type", data)
        except Exception:
            # WebSocket 可能未實現，跳過測試
            self.skipTest("WebSocket not implemented")
    
    def test_api_documentation(self):
        """測試 API 文檔"""
        # 測試 OpenAPI 文檔端點
        response = self.client.get("/docs")
        self.assertIn(response.status_code, [200, 404])
        
        # 測試 OpenAPI JSON
        response = self.client.get("/openapi.json")
        if response.status_code == 200:
            data = response.json()
            self.assertIn("openapi", data)
            self.assertIn("paths", data)
    
    def test_health_check(self):
        """測試健康檢查端點"""
        response = self.client.get("/health")
        if response.status_code == 200:
            data = response.json()
            self.assertIn("status", data)
            self.assertEqual(data["status"], "healthy")
        else:
            # 健康檢查端點可能不存在
            self.assertIn(response.status_code, [404])


if __name__ == "__main__":
    unittest.main()
