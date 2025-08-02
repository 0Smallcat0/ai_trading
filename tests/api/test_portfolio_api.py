"""
投資組合管理 API 測試

此模組包含投資組合管理 API 的完整測試套件，包括：
- 投資組合 CRUD 操作測試
- 再平衡功能測試
- 績效指標計算測試
- 風險指標計算測試
- 錯誤處理測試
"""

import pytest
import uuid
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from src.api.main import app
from src.core.portfolio_service import Portfolio, PortfolioHolding


@pytest.fixture
def client():
    """測試客戶端"""
    return TestClient(app)


@pytest.fixture
def mock_portfolio_service():
    """模擬投資組合服務"""
    with patch("src.api.routers.portfolio.portfolio_service") as mock:
        yield mock


@pytest.fixture
def sample_portfolio():
    """範例投資組合"""
    holdings = [
        PortfolioHolding(
            symbol="2330.TW",
            name="台積電",
            quantity=100,
            price=500.0,
            market_value=50000.0,
            weight=0.5,
            sector="半導體",
            exchange="TWSE",
        ),
        PortfolioHolding(
            symbol="2317.TW",
            name="鴻海",
            quantity=500,
            price=100.0,
            market_value=50000.0,
            weight=0.5,
            sector="電子零組件",
            exchange="TWSE",
        ),
    ]

    return Portfolio(
        id=str(uuid.uuid4()),
        name="測試投資組合",
        description="這是一個測試投資組合",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        total_value=100000.0,
        holdings=holdings,
        benchmark="^TWII",
        risk_free_rate=0.02,
    )


@pytest.fixture
def sample_create_request():
    """範例創建請求"""
    return {
        "name": "新投資組合",
        "description": "測試創建的投資組合",
        "benchmark": "^TWII",
        "risk_free_rate": 0.02,
        "holdings": [
            {
                "symbol": "2330.TW",
                "name": "台積電",
                "quantity": 100,
                "price": 500.0,
                "sector": "半導體",
                "exchange": "TWSE",
            },
            {
                "symbol": "2317.TW",
                "name": "鴻海",
                "quantity": 500,
                "price": 100.0,
                "sector": "電子零組件",
                "exchange": "TWSE",
            },
        ],
    }


class TestPortfolioAPI:
    """投資組合 API 測試類"""

    def test_create_portfolio_success(
        self, client, mock_portfolio_service, sample_create_request, sample_portfolio
    ):
        """測試成功創建投資組合"""
        # 設定模擬
        mock_portfolio_service.create_portfolio.return_value = sample_portfolio

        # 發送請求
        response = client.post(
            "/api/v1/portfolio/portfolios", json=sample_create_request
        )

        # 驗證響應
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "投資組合創建成功"
        assert data["data"]["name"] == sample_portfolio.name
        assert len(data["data"]["holdings"]) == 2

    def test_create_portfolio_validation_error(self, client):
        """測試創建投資組合驗證錯誤"""
        invalid_request = {"name": "", "holdings": []}  # 空名稱  # 空持倉

        response = client.post("/api/v1/portfolio/portfolios", json=invalid_request)

        assert response.status_code == 422  # 驗證錯誤

    def test_list_portfolios_success(
        self, client, mock_portfolio_service, sample_portfolio
    ):
        """測試成功獲取投資組合列表"""
        # 設定模擬
        mock_portfolio_service.list_portfolios.return_value = ([sample_portfolio], 1)

        # 發送請求
        response = client.get("/api/v1/portfolio/portfolios")

        # 驗證響應
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 1
        assert data["pagination"]["total_items"] == 1

    def test_get_portfolio_success(
        self, client, mock_portfolio_service, sample_portfolio
    ):
        """測試成功獲取投資組合詳情"""
        # 設定模擬
        mock_portfolio_service.get_portfolio.return_value = sample_portfolio

        # 發送請求
        response = client.get(f"/api/v1/portfolio/portfolios/{sample_portfolio.id}")

        # 驗證響應
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == sample_portfolio.id
        assert data["data"]["name"] == sample_portfolio.name

    def test_get_portfolio_not_found(self, client, mock_portfolio_service):
        """測試獲取不存在的投資組合"""
        # 設定模擬
        mock_portfolio_service.get_portfolio.return_value = None

        # 發送請求
        response = client.get("/api/v1/portfolio/portfolios/nonexistent")

        # 驗證響應
        assert response.status_code == 404

    def test_update_portfolio_success(
        self, client, mock_portfolio_service, sample_portfolio
    ):
        """測試成功更新投資組合"""
        # 設定模擬
        mock_portfolio_service.get_portfolio.return_value = sample_portfolio
        updated_portfolio = sample_portfolio
        updated_portfolio.name = "更新後的投資組合"
        mock_portfolio_service.update_portfolio.return_value = updated_portfolio

        update_request = {"name": "更新後的投資組合", "description": "更新後的描述"}

        # 發送請求
        response = client.put(
            f"/api/v1/portfolio/portfolios/{sample_portfolio.id}", json=update_request
        )

        # 驗證響應
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "更新後的投資組合"

    def test_delete_portfolio_success(
        self, client, mock_portfolio_service, sample_portfolio
    ):
        """測試成功刪除投資組合"""
        # 設定模擬
        mock_portfolio_service.get_portfolio.return_value = sample_portfolio
        mock_portfolio_service.delete_portfolio.return_value = True

        # 發送請求
        response = client.delete(f"/api/v1/portfolio/portfolios/{sample_portfolio.id}")

        # 驗證響應
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["portfolio_id"] == sample_portfolio.id

    def test_rebalance_portfolio_success(
        self, client, mock_portfolio_service, sample_portfolio
    ):
        """測試成功執行投資組合再平衡"""
        # 設定模擬
        mock_portfolio_service.get_portfolio.return_value = sample_portfolio
        mock_portfolio_service.rebalance_portfolio.return_value = {
            "old_weights": {"2330.TW": 0.5, "2317.TW": 0.5},
            "new_weights": {"2330.TW": 0.6, "2317.TW": 0.4},
            "weight_changes": {"2330.TW": 0.1, "2317.TW": -0.1},
            "expected_return": 0.08,
            "expected_risk": 0.15,
            "rebalance_cost": 100.0,
        }

        rebalance_request = {"method": "equal_weight"}

        # 發送請求
        response = client.post(
            f"/api/v1/portfolio/portfolios/{sample_portfolio.id}/rebalance",
            json=rebalance_request,
        )

        # 驗證響應
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["method"] == "equal_weight"
        assert "old_weights" in data["data"]
        assert "new_weights" in data["data"]

    def test_get_performance_metrics_success(
        self, client, mock_portfolio_service, sample_portfolio
    ):
        """測試成功獲取績效指標"""
        # 設定模擬
        mock_portfolio_service.get_portfolio.return_value = sample_portfolio
        mock_portfolio_service.calculate_performance_metrics.return_value = {
            "total_return": 0.15,
            "annual_return": 0.12,
            "volatility": 0.18,
            "sharpe_ratio": 0.67,
            "max_drawdown": -0.08,
            "calmar_ratio": 1.5,
            "sortino_ratio": 0.85,
            "information_ratio": 0.5,
            "beta": 1.0,
            "alpha": 0.02,
            "tracking_error": 0.03,
        }

        # 發送請求
        response = client.get(
            f"/api/v1/portfolio/portfolios/{sample_portfolio.id}/performance"
        )

        # 驗證響應
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_return"] == 0.15
        assert data["data"]["sharpe_ratio"] == 0.67

    def test_get_risk_metrics_success(
        self, client, mock_portfolio_service, sample_portfolio
    ):
        """測試成功獲取風險指標"""
        # 設定模擬
        mock_portfolio_service.get_portfolio.return_value = sample_portfolio
        mock_portfolio_service.calculate_risk_metrics.return_value = {
            "var_95": -0.025,
            "var_99": -0.045,
            "cvar_95": -0.035,
            "cvar_99": -0.055,
            "volatility": 0.18,
            "downside_deviation": 0.12,
            "max_drawdown": -0.08,
            "correlation_matrix": {
                "2330.TW": {"2330.TW": 1.0, "2317.TW": 0.3},
                "2317.TW": {"2330.TW": 0.3, "2317.TW": 1.0},
            },
            "concentration_risk": 0.5,
        }

        # 發送請求
        response = client.get(
            f"/api/v1/portfolio/portfolios/{sample_portfolio.id}/risk-metrics"
        )

        # 驗證響應
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["var_95"] == -0.025
        assert data["data"]["concentration_risk"] == 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
