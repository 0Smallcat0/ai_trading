"""
安全測試 pytest 配置

此模組提供安全測試的 pytest 配置和共用 fixtures。
"""

import pytest
import jwt
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Generator
from unittest.mock import Mock

from fastapi.testclient import TestClient

# 添加專案根目錄到 Python 路徑
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from src.api.main import app
from src.api.middleware.auth import TokenManager
from tests.security.utils.security_scanner import SecurityScanner


@pytest.fixture(scope="session")
def security_test_client() -> Generator[TestClient, None, None]:
    """創建安全測試客戶端"""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def valid_auth_headers() -> Dict[str, str]:
    """創建有效的認證標頭"""
    token = TokenManager.create_access_token(
        user_id="test_user", username="test_user", role="admin"
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def user_auth_headers() -> Dict[str, str]:
    """創建普通用戶認證標頭"""
    token = TokenManager.create_access_token(
        user_id="normal_user", username="normal_user", role="user"
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def expired_token() -> str:
    """創建過期的 JWT Token"""
    payload = {
        "user_id": "test_user",
        "username": "test_user",
        "role": "admin",
        "exp": int((datetime.now() - timedelta(hours=1)).timestamp()),  # 1小時前過期
        "iat": int((datetime.now() - timedelta(hours=2)).timestamp()),
    }
    return jwt.encode(payload, "test_secret", algorithm="HS256")


@pytest.fixture(scope="function")
def invalid_signature_token() -> str:
    """創建無效簽名的 JWT Token"""
    payload = {
        "user_id": "test_user",
        "username": "test_user",
        "role": "admin",
        "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.now().timestamp()),
    }
    return jwt.encode(payload, "wrong_secret", algorithm="HS256")


@pytest.fixture(scope="function")
def malformed_tokens() -> List[str]:
    """創建格式錯誤的 Token 列表"""
    return [
        "invalid.token.format",
        "Bearer invalid_token",
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid_payload.signature",
        "",
        "null",
        "undefined",
    ]


@pytest.fixture(scope="function")
def privilege_escalation_token() -> str:
    """創建權限提升測試 Token"""
    payload = {
        "user_id": "normal_user",
        "username": "normal_user",
        "role": "super_admin",  # 嘗試提升權限
        "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
        "iat": int(datetime.now().timestamp()),
    }
    return jwt.encode(payload, "test_secret", algorithm="HS256")


@pytest.fixture(scope="function")
def sql_injection_payloads() -> List[str]:
    """SQL 注入測試載荷"""
    return [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "' UNION SELECT * FROM users --",
        "1' AND (SELECT COUNT(*) FROM users) > 0 --",
        "admin'--",
        "admin' /*",
        "' OR 1=1#",
        "' OR 'a'='a",
        "') OR ('1'='1",
        "1' OR '1'='1' /*",
        "x' AND email IS NULL; --",
        "x' AND 1=(SELECT COUNT(*) FROM tabname); --",
    ]


@pytest.fixture(scope="function")
def xss_payloads() -> List[str]:
    """XSS 攻擊測試載荷"""
    return [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg onload=alert('XSS')>",
        "javascript:alert('XSS')",
        "<iframe src=javascript:alert('XSS')></iframe>",
        "<body onload=alert('XSS')>",
        "<input onfocus=alert('XSS') autofocus>",
        "<select onfocus=alert('XSS') autofocus>",
        "<textarea onfocus=alert('XSS') autofocus>",
        "<keygen onfocus=alert('XSS') autofocus>",
        "<video><source onerror=alert('XSS')>",
        "<audio src=x onerror=alert('XSS')>",
        "';alert('XSS');//",
        "\";alert('XSS');//",
        "</script><script>alert('XSS')</script>",
        "<script>eval(String.fromCharCode(97,108,101,114,116,40,39,88,83,83,39,41))</script>",
    ]


@pytest.fixture(scope="function")
def security_scanner() -> SecurityScanner:
    """創建安全掃描器"""
    return SecurityScanner()


@pytest.fixture(scope="function")
def test_user_credentials() -> Dict[str, str]:
    """測試用戶憑證"""
    return {
        "username": "test_user",
        "password": "test_password123",
        "email": "test@example.com",
    }


@pytest.fixture(scope="function")
def admin_credentials() -> Dict[str, str]:
    """管理員憑證"""
    return {"username": "admin", "password": "admin123", "email": "admin@example.com"}


@pytest.fixture(scope="function")
def sensitive_test_data() -> Dict[str, Any]:
    """敏感測試資料"""
    return {
        "email": "user@example.com",
        "phone": "123-456-7890",
        "ssn": "123-45-6789",
        "credit_card": "4111-1111-1111-1111",
        "api_key": "sk_test_123456789abcdef",
        "password": "secret_password123",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...",
    }


@pytest.fixture(scope="function")
def mock_database():
    """模擬資料庫連接（用於注入測試）"""
    mock_db = Mock()
    mock_db.execute.return_value = Mock()
    mock_db.fetchall.return_value = []
    mock_db.fetchone.return_value = None
    mock_db.commit.return_value = None
    return mock_db


@pytest.fixture(scope="session")
def security_test_config() -> Dict[str, Any]:
    """安全測試配置"""
    return {
        "max_login_attempts": 5,
        "lockout_duration": 300,  # 5 minutes
        "password_min_length": 8,
        "password_complexity": True,
        "session_timeout": 3600,  # 1 hour
        "jwt_expiration": 3600,
        "rate_limit_requests": 100,
        "rate_limit_window": 60,
        "allowed_origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
        "sensitive_headers": ["authorization", "x-api-key", "cookie"],
        "security_headers": [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Strict-Transport-Security",
            "Content-Security-Policy",
        ],
    }


@pytest.fixture(autouse=True)
def setup_security_test_environment():
    """設置安全測試環境"""
    # 設置測試環境變數
    import os

    os.environ["SECURITY_TESTING"] = "true"
    os.environ["JWT_SECRET_KEY"] = "test_secret_key_for_security_testing"

    yield

    # 清理測試環境
    if "SECURITY_TESTING" in os.environ:
        del os.environ["SECURITY_TESTING"]
    if "JWT_SECRET_KEY" in os.environ:
        del os.environ["JWT_SECRET_KEY"]


def pytest_configure(config):
    """pytest 配置"""
    # 添加自定義標記
    config.addinivalue_line("markers", "security: 標記安全測試")
    config.addinivalue_line("markers", "auth_test: 標記認證測試")
    config.addinivalue_line("markers", "injection_test: 標記注入攻擊測試")
    config.addinivalue_line("markers", "xss_test: 標記 XSS 攻擊測試")
    config.addinivalue_line("markers", "privilege_test: 標記權限測試")
    config.addinivalue_line("markers", "data_leak_test: 標記資料洩漏測試")


def pytest_collection_modifyitems(config, items):
    """修改測試項目收集"""
    for item in items:
        # 為安全測試添加標記
        if "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)
