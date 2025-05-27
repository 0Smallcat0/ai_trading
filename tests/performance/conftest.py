"""
效能測試 pytest 配置

此模組提供效能測試的 pytest 配置和共用 fixtures。
"""

import asyncio
import os
import pytest
import time
from datetime import datetime
from typing import Dict, Any, Generator
from unittest.mock import Mock

import httpx
from fastapi.testclient import TestClient

# 添加專案根目錄到 Python 路徑
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.api.main import app
from src.api.middleware.auth import TokenManager
from tests.performance.utils.performance_monitor import PerformanceMonitor
from tests.performance.benchmark_config import (
    API_BENCHMARKS,
    BENCHMARK_CONFIG,
    get_benchmark_for_endpoint,
    is_performance_acceptable
)


@pytest.fixture(scope="session")
def event_loop():
    """創建事件循環"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_client() -> Generator[TestClient, None, None]:
    """創建測試客戶端"""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def async_client() -> Generator[httpx.AsyncClient, None, None]:
    """創建異步測試客戶端"""

    async def _async_client():
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            yield client

    return _async_client()


@pytest.fixture(scope="session")
def auth_headers() -> Dict[str, str]:
    """創建認證標頭"""
    # 創建測試用 JWT Token
    token = TokenManager.create_access_token(
        user_id="test_user", username="test_user", role="admin"
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def performance_monitor() -> PerformanceMonitor:
    """創建效能監控器"""
    return PerformanceMonitor()


@pytest.fixture(scope="function")
def mock_database():
    """模擬資料庫連接"""
    mock_db = Mock()
    mock_db.execute.return_value = Mock()
    mock_db.fetchall.return_value = []
    mock_db.fetchone.return_value = None
    return mock_db


@pytest.fixture(scope="session")
def performance_test_config() -> Dict[str, Any]:
    """效能測試配置"""
    return {
        "api_base_url": "http://127.0.0.1:8000",
        "response_time_threshold": 100,  # ms
        "memory_threshold": 100,  # MB
        "concurrent_users": [1, 5, 10, 25, 50],
        "test_duration": 30,  # seconds
        "warmup_requests": 10,
        "benchmark_rounds": 5,
    }


@pytest.fixture(scope="session")
def api_benchmarks() -> Dict[str, Any]:
    """提供 API 效能基準配置"""
    return API_BENCHMARKS


@pytest.fixture(scope="session")
def benchmark_config() -> Dict[str, Any]:
    """提供 pytest-benchmark 配置"""
    return BENCHMARK_CONFIG


@pytest.fixture
def benchmark_validator():
    """提供基準驗證器"""

    def validate_performance(endpoint: str, method: str, actual_time_ms: float) -> Dict[str, Any]:
        """
        驗證效能是否符合基準

        Args:
            endpoint: API 端點
            method: HTTP 方法
            actual_time_ms: 實際響應時間（毫秒）

        Returns:
            Dict[str, Any]: 驗證結果
        """
        benchmark = get_benchmark_for_endpoint(endpoint, method)
        is_acceptable, status = is_performance_acceptable(actual_time_ms, benchmark)

        return {
            "endpoint": endpoint,
            "method": method,
            "actual_time_ms": actual_time_ms,
            "benchmark": {
                "max_response_time_ms": benchmark.max_response_time_ms,
                "warning_threshold_ms": benchmark.warning_threshold_ms,
                "critical_threshold_ms": benchmark.critical_threshold_ms
            },
            "is_acceptable": is_acceptable,
            "status": status,
            "performance_ratio": actual_time_ms / benchmark.max_response_time_ms
        }

    return validate_performance


@pytest.fixture(scope="function")
def test_data_generator():
    """測試資料生成器"""

    def _generate_test_data(data_type: str, count: int = 100):
        if data_type == "market_data":
            return [
                {
                    "symbol": f"TEST{i:03d}",
                    "price": 100.0 + i,
                    "volume": 1000 + i * 10,
                    "timestamp": datetime.now().isoformat(),
                }
                for i in range(count)
            ]
        elif data_type == "strategies":
            return [
                {
                    "name": f"Strategy_{i}",
                    "type": "momentum",
                    "parameters": {"period": 20 + i, "threshold": 0.02},
                }
                for i in range(count)
            ]
        elif data_type == "portfolios":
            return [
                {"name": f"Portfolio_{i}", "cash": 100000.0 + i * 1000, "positions": {}}
                for i in range(count)
            ]
        return []

    return _generate_test_data


@pytest.fixture(autouse=True)
def setup_performance_test_environment():
    """設置效能測試環境"""
    # 設置測試環境變數
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "WARNING"  # 減少日誌輸出

    yield

    # 清理測試環境
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
    if "LOG_LEVEL" in os.environ:
        del os.environ["LOG_LEVEL"]


def pytest_configure(config):
    """pytest 配置"""
    # 添加自定義標記
    config.addinivalue_line("markers", "performance: 標記效能測試")
    config.addinivalue_line("markers", "load_test: 標記負載測試")
    config.addinivalue_line("markers", "memory_test: 標記記憶體測試")
    config.addinivalue_line("markers", "benchmark: 標記基準測試")


def pytest_collection_modifyitems(config, items):
    """修改測試項目收集"""
    for item in items:
        # 為效能測試添加標記
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
