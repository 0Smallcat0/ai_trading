"""
敏感資料洩漏測試

此模組測試 API 回應中是否洩漏敏感資料，如密碼、API 金鑰、個人資訊等。
"""

import pytest
import re
from typing import Dict, List, Any

from fastapi.testclient import TestClient

from tests.security.utils.security_scanner import SecurityScanner


@pytest.mark.security
@pytest.mark.data_leak_test
class TestDataLeakage:
    """敏感資料洩漏測試類"""

    def test_password_leakage_prevention(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """測試密碼洩漏防護"""
        # 測試各種可能洩漏密碼的端點
        test_endpoints = [
            "/api/v1/auth/me",
            "/api/v1/users/profile",
            "/api/v1/admin/users",
            "/api/v1/data/",
            "/api/v1/strategies/",
        ]

        password_patterns = [
            r'password\s*[:=]\s*[\'"]?([^\'"\\s]+)',
            r'"password"\s*:\s*"([^"]+)"',
            r'pwd\s*[:=]\s*[\'"]?([^\'"\\s]+)',
            r'passwd\s*[:=]\s*[\'"]?([^\'"\\s]+)',
            r'secret\s*[:=]\s*[\'"]?([^\'"\\s]+)',
        ]

        for endpoint in test_endpoints:
            response = security_test_client.get(endpoint, headers=valid_auth_headers)

            if response.status_code == 200:
                response_text = response.text.lower()

                # 檢查是否洩漏密碼
                for pattern in password_patterns:
                    matches = re.findall(pattern, response_text, re.IGNORECASE)
                    assert len(matches) == 0, f"在 {endpoint} 發現密碼洩漏: {matches}"

                # 檢查常見的密碼欄位
                sensitive_fields = [
                    '"password"',
                    '"pwd"',
                    '"passwd"',
                    '"secret"',
                    '"api_key"',
                    '"private_key"',
                ]

                for field in sensitive_fields:
                    if field in response_text:
                        # 如果包含敏感欄位，值應該被遮罩或移除
                        field_pattern = f'{field}\\s*:\\s*"([^"]*)"'
                        field_matches = re.findall(field_pattern, response_text)
                        for match in field_matches:
                            assert match in [
                                "",
                                "***",
                                "[REDACTED]",
                                None,
                            ] or match.startswith(
                                "*"
                            ), f"敏感欄位 {field} 在 {endpoint} 未被遮罩: {match}"

        print("✅ 密碼洩漏防護測試通過")

    def test_api_key_leakage_prevention(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """測試 API 金鑰洩漏防護"""
        test_endpoints = [
            "/api/v1/data/sources",
            "/api/v1/models/",
            "/api/v1/strategies/",
            "/api/info",
        ]

        api_key_patterns = [
            r'api[_-]?key\s*[:=]\s*[\'"]?([^\'"\\s]+)',
            r'access[_-]?token\s*[:=]\s*[\'"]?([^\'"\\s]+)',
            r'secret[_-]?key\s*[:=]\s*[\'"]?([^\'"\\s]+)',
            r'private[_-]?key\s*[:=]\s*[\'"]?([^\'"\\s]+)',
            r"sk_[a-zA-Z0-9]{20,}",  # Stripe-style secret keys
            r"pk_[a-zA-Z0-9]{20,}",  # Stripe-style public keys
            r"AIza[0-9A-Za-z\\-_]{35}",  # Google API keys
            r"AKIA[0-9A-Z]{16}",  # AWS access keys
        ]

        for endpoint in test_endpoints:
            response = security_test_client.get(endpoint, headers=valid_auth_headers)

            if response.status_code == 200:
                response_text = response.text

                for pattern in api_key_patterns:
                    matches = re.findall(pattern, response_text, re.IGNORECASE)
                    assert (
                        len(matches) == 0
                    ), f"在 {endpoint} 發現 API 金鑰洩漏: {matches}"

        print("✅ API 金鑰洩漏防護測試通過")

    def test_personal_information_leakage(
        self,
        security_test_client: TestClient,
        valid_auth_headers: Dict[str, str],
        sensitive_test_data: Dict[str, Any],
    ):
        """測試個人資訊洩漏防護"""
        # 先嘗試創建包含敏感資料的記錄
        test_data = {
            "name": "Test User",
            "email": sensitive_test_data["email"],
            "phone": sensitive_test_data["phone"],
            "description": f"SSN: {sensitive_test_data['ssn']}, Credit Card: {sensitive_test_data['credit_card']}",
        }

        # 嘗試創建記錄
        create_response = security_test_client.post(
            "/api/v1/strategies/", json=test_data, headers=valid_auth_headers
        )

        # 檢查創建回應是否洩漏敏感資料
        if create_response.status_code in [200, 201]:
            response_text = create_response.text

            # 檢查個人資訊模式
            pii_patterns = [
                r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
                r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
                r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Credit card
                r"\b\d{3}-\d{3}-\d{4}\b",  # Phone number
                r"\b\d{10}\b",  # 10-digit numbers
            ]

            for pattern in pii_patterns:
                matches = re.findall(pattern, response_text)
                if matches:
                    # 檢查是否被適當遮罩
                    for match in matches:
                        if "*" not in match and "xxx" not in match.lower():
                            print(f"⚠️ 可能的個人資訊洩漏: {match}")

        # 檢查查詢回應
        list_response = security_test_client.get(
            "/api/v1/strategies/", headers=valid_auth_headers
        )
        if list_response.status_code == 200:
            response_text = list_response.text

            # 確保敏感資料不會在列表中洩漏
            assert (
                sensitive_test_data["ssn"] not in response_text
            ), "SSN 在列表回應中洩漏"
            assert (
                sensitive_test_data["credit_card"] not in response_text
            ), "信用卡號在列表回應中洩漏"

        print("✅ 個人資訊洩漏防護測試通過")

    def test_system_information_leakage(self, security_test_client: TestClient):
        """測試系統資訊洩漏防護"""
        # 測試錯誤回應是否洩漏系統資訊

        # 嘗試觸發各種錯誤
        error_endpoints = [
            "/api/v1/nonexistent",
            "/api/v1/data/999999",
            "/api/v1/strategies/invalid_id",
        ]

        system_info_patterns = [
            r"traceback",
            r"stack trace",
            r'file ".*\.py"',
            r"line \d+",
            r"exception:",
            r"error:.*\.py",
            r"django",
            r"flask",
            r"fastapi",
            r"uvicorn",
            r"gunicorn",
            r"/usr/local/",
            r"/home/",
            r"c:\\",
            r"python \d+\.\d+",
            r"version \d+\.\d+\.\d+",
        ]

        for endpoint in error_endpoints:
            response = security_test_client.get(endpoint)
            response_text = response.text.lower()

            for pattern in system_info_patterns:
                matches = re.findall(pattern, response_text, re.IGNORECASE)
                assert (
                    len(matches) == 0
                ), f"在 {endpoint} 錯誤回應中洩漏系統資訊: {matches}"

        print("✅ 系統資訊洩漏防護測試通過")

    def test_database_information_leakage(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """測試資料庫資訊洩漏防護"""
        # 測試是否洩漏資料庫結構或內部資訊

        test_endpoints = ["/api/v1/data/", "/api/v1/strategies/", "/api/v1/models/"]

        db_info_patterns = [
            r"select \* from",
            r"insert into",
            r"update .* set",
            r"delete from",
            r"create table",
            r"drop table",
            r"alter table",
            r"information_schema",
            r"mysql",
            r"postgresql",
            r"sqlite",
            r"oracle",
            r"sql server",
            r"database",
            r"table",
            r"column",
            r"primary key",
            r"foreign key",
        ]

        for endpoint in test_endpoints:
            response = security_test_client.get(endpoint, headers=valid_auth_headers)

            if response.status_code == 200:
                response_text = response.text.lower()

                for pattern in db_info_patterns:
                    matches = re.findall(pattern, response_text, re.IGNORECASE)
                    assert (
                        len(matches) == 0
                    ), f"在 {endpoint} 發現資料庫資訊洩漏: {pattern}"

        print("✅ 資料庫資訊洩漏防護測試通過")

    def test_internal_path_leakage(self, security_test_client: TestClient):
        """測試內部路徑洩漏防護"""
        # 測試錯誤回應是否洩漏內部檔案路徑

        # 嘗試訪問不存在的檔案
        file_endpoints = [
            "/api/v1/files/../../etc/passwd",
            "/api/v1/download/..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "/api/v1/static/../../../app/config.py",
        ]

        path_patterns = [
            r"/etc/",
            r"/usr/",
            r"/var/",
            r"/home/",
            r"/root/",
            r"c:\\",
            r"d:\\",
            r"\\windows\\",
            r"\\program files\\",
            r"\.py",
            r"\.conf",
            r"\.ini",
            r"\.env",
        ]

        for endpoint in file_endpoints:
            response = security_test_client.get(endpoint)
            response_text = response.text.lower()

            for pattern in path_patterns:
                matches = re.findall(pattern, response_text, re.IGNORECASE)
                assert len(matches) == 0, f"在 {endpoint} 發現內部路徑洩漏: {pattern}"

        print("✅ 內部路徑洩漏防護測試通過")

    def test_jwt_token_leakage(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """測試 JWT Token 洩漏防護"""
        # 測試回應中是否洩漏 JWT Token

        test_endpoints = ["/api/v1/auth/me", "/api/v1/data/", "/api/v1/strategies/"]

        jwt_patterns = [
            r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",  # JWT format
            r"bearer [A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+",
            r"authorization:\s*bearer\s+[A-Za-z0-9_-]+",
            r"access_token.*eyJ[A-Za-z0-9_-]+",
        ]

        for endpoint in test_endpoints:
            response = security_test_client.get(endpoint, headers=valid_auth_headers)

            if response.status_code == 200:
                response_text = response.text

                for pattern in jwt_patterns:
                    matches = re.findall(pattern, response_text, re.IGNORECASE)
                    assert (
                        len(matches) == 0
                    ), f"在 {endpoint} 發現 JWT Token 洩漏: {matches}"

        print("✅ JWT Token 洩漏防護測試通過")

    def test_comprehensive_data_leakage_scan(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """全面的資料洩漏掃描"""
        scanner = SecurityScanner()

        # 定義要掃描的端點
        endpoints = [
            {"url": "/api/v1/data/", "method": "GET"},
            {"url": "/api/v1/strategies/", "method": "GET"},
            {"url": "/api/v1/models/", "method": "GET"},
            {"url": "/api/v1/auth/me", "method": "GET"},
            {"url": "/api/info", "method": "GET"},
        ]

        # 執行安全掃描
        scan_result = scanner.scan_api_security(
            security_test_client, endpoints, valid_auth_headers
        )

        # 檢查資料洩漏相關問題
        data_exposure_issues = [
            issue
            for issue in scan_result.issues_found
            if issue.category == "data_exposure"
        ]

        if data_exposure_issues:
            print(f"\n❌ 發現 {len(data_exposure_issues)} 個資料洩漏問題:")
            for issue in data_exposure_issues:
                print(f"   - {issue.endpoint}: {issue.title}")
                print(f"     嚴重程度: {issue.severity}")
                print(f"     證據: {issue.evidence}")

        assert (
            len(data_exposure_issues) == 0
        ), f"全面掃描發現 {len(data_exposure_issues)} 個資料洩漏問題"

        print(
            f"✅ 全面資料洩漏掃描通過 (安全評分: {scan_result.security_score:.1f}/100)"
        )

    def test_response_header_information_leakage(
        self, security_test_client: TestClient
    ):
        """測試回應標頭資訊洩漏"""
        response = security_test_client.get("/api/info")

        # 檢查是否洩漏敏感的伺服器資訊
        sensitive_headers = [
            "server",
            "x-powered-by",
            "x-aspnet-version",
            "x-aspnetmvc-version",
        ]

        for header in sensitive_headers:
            header_value = response.headers.get(header, "").lower()
            if header_value:
                # 檢查是否洩漏版本資訊
                version_patterns = [
                    r"\d+\.\d+",
                    r"version",
                    r"apache",
                    r"nginx",
                    r"iis",
                ]
                for pattern in version_patterns:
                    matches = re.findall(pattern, header_value)
                    if matches:
                        print(f"⚠️ 標頭 {header} 可能洩漏版本資訊: {header_value}")

        print("✅ 回應標頭資訊洩漏測試通過")
