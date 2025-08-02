"""
安全測試框架

此模組提供完整的 API 安全測試基礎設施，包括：
- JWT 認證安全性測試
- SQL 注入防護測試
- XSS 攻擊防護測試
- RBAC 權限控制測試
- 敏感資料洩漏檢測
- OWASP Top 10 安全檢查

使用方法:
    pytest tests/security/ -v
    pytest tests/security/test_jwt_security.py::test_jwt_token_validation
"""

from .utils.security_scanner import SecurityScanner
from .utils.vulnerability_tester import VulnerabilityTester
from .utils.auth_tester import AuthTester
from .utils.injection_tester import InjectionTester

__all__ = ["SecurityScanner", "VulnerabilityTester", "AuthTester", "InjectionTester"]

# 安全測試配置
SECURITY_CONFIG = {
    "jwt_test_cases": [
        "expired_token",
        "invalid_signature",
        "malformed_token",
        "missing_claims",
        "privilege_escalation",
    ],
    "sql_injection_payloads": [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "' UNION SELECT * FROM users --",
        "1' AND (SELECT COUNT(*) FROM users) > 0 --",
    ],
    "xss_payloads": [
        "<script>alert('XSS')</script>",
        "javascript:alert('XSS')",
        "<img src=x onerror=alert('XSS')>",
        "';alert('XSS');//",
    ],
    "sensitive_data_patterns": [
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
        r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Credit card
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"password\s*[:=]\s*['\"]?([^'\"\\s]+)",  # Password
        r"api[_-]?key\s*[:=]\s*['\"]?([^'\"\\s]+)",  # API key
    ],
}
