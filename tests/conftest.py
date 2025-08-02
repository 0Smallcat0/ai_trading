"""測試配置和共用 Fixtures

此模組提供測試所需的共用配置、Fixtures 和工具函數。
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, Generator

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 設置測試環境變數
os.environ['TESTING'] = 'true'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['JWT_SECRET_KEY'] = 'test-jwt-secret'


# Define pytest configuration to filter warnings
def pytest_addoption(parser):
    """Add options to pytest command line."""
    parser.addoption(
        "--no-warnings",
        action="store_true",
        default=True,
        help="Disable warning capture",
    )


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    """Configure pytest."""
    # Disable warning capture
    config.option.showwarning = False
    config.option.filterwarnings = ["ignore::DeprecationWarning"]


@pytest.fixture(scope="function")
def mock_user() -> Dict[str, Any]:
    """模擬用戶 Fixture

    Returns:
        Dict[str, Any]: 模擬用戶資料
    """
    return {
        "user_id": "test_user_123",
        "username": "testuser",
        "email": "test@example.com",
        "role": "user",
        "is_active": True,
        "password_hash": "$2b$12$test.hash.value",
        "created_at": datetime.now(),
        "last_login": datetime.now(),
    }


@pytest.fixture(scope="function")
def mock_admin_user() -> Dict[str, Any]:
    """模擬管理員用戶 Fixture

    Returns:
        Dict[str, Any]: 模擬管理員用戶資料
    """
    return {
        "user_id": "admin_user_123",
        "username": "admin",
        "email": "admin@example.com",
        "role": "admin",
        "is_active": True,
        "password_hash": "$2b$12$admin.hash.value",
        "created_at": datetime.now(),
        "last_login": datetime.now(),
    }


@pytest.fixture(scope="function")
def mock_bcrypt():
    """模擬 bcrypt 密碼處理 Fixture

    Returns:
        Mock: 模擬的 bcrypt 模組
    """
    with patch('bcrypt.checkpw') as mock_checkpw, \
         patch('bcrypt.hashpw') as mock_hashpw, \
         patch('bcrypt.gensalt') as mock_gensalt:

        mock_checkpw.return_value = True
        mock_hashpw.return_value = b'$2b$12$mock.hash.value'
        mock_gensalt.return_value = b'$2b$12$mock.salt'

        yield {
            'checkpw': mock_checkpw,
            'hashpw': mock_hashpw,
            'gensalt': mock_gensalt
        }


@pytest.fixture
def mock_trade_executor():
    """Mock 交易執行器"""
    mock_executor = Mock()
    mock_executor.brokers = {
        "simulator": Mock(),
        "shioaji": Mock(),
        "futu": Mock(),
        "ib": Mock()
    }
    mock_executor.current_broker = mock_executor.brokers["simulator"]
    mock_executor.init_brokers = Mock()
    mock_executor.switch_broker = Mock(return_value=True)
    return mock_executor


@pytest.fixture
def mock_risk_service():
    """Mock 風險管理服務"""
    mock_service = Mock()
    mock_service.calculate_var = Mock(return_value=0.05)
    mock_service.check_risk_limits = Mock(return_value=True)
    return mock_service


@pytest.fixture
def mock_account_service():
    """Mock 帳戶同步服務"""
    mock_service = Mock()
    mock_service.get_all_accounts = Mock(return_value={})
    mock_service.get_account_info = Mock(return_value=None)
    mock_service.get_total_portfolio_value = Mock(return_value=100000.0)
    mock_service.get_total_cash = Mock(return_value=50000.0)
    return mock_service


@pytest.fixture
def mock_notification_service():
    """Mock 通知服務"""
    mock_service = Mock()
    mock_service._send_notification = Mock(return_value="notif_123")
    return mock_service


@pytest.fixture(autouse=True)
def setup_test_environment():
    """設置測試環境"""
    # 確保測試時不會載入真實的配置
    os.environ["TESTING"] = "true"
    yield
    # 清理
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
