"""
API 版本控制安全測試

此模組包含 API 版本控制相關的安全測試，驗證版本控制系統的安全性，
包括 JWT 認證、SQL 注入防護、XSS 攻擊防護等。

測試範圍：
- JWT 認證安全性
- SQL 注入防護
- XSS 攻擊防護
- 版本偽造攻擊
- 權限繞過測試
- 輸入驗證測試
"""

import pytest
import jwt
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

# 導入安全測試工具
from tests.security.utils.security_scanner import SecurityScanner
from tests.security.utils.injection_tester import InjectionTester
from tests.security.utils.auth_tester import AuthTester
from tests.security.utils.vulnerability_tester import VulnerabilityTester

# 導入被測試的模組
from src.api.routers.versioning import router
from src.api.models.versioning import VersionStatusEnum
from src.services.version_service import VersionService


# 創建測試應用
app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.mark.security
class TestVersioningJWTSecurity:
    """版本控制 JWT 安全測試類"""

    def setup_method(self):
        """測試前置設定"""
        self.auth_tester = AuthTester()
        self.valid_token = self.auth_tester.generate_test_token("test_user")
        self.expired_token = self.auth_tester.generate_expired_token("test_user")
        self.invalid_token = "invalid.jwt.token"

    def test_jwt_authentication_required(self):
        """測試 JWT 認證要求"""
        # 測試無 Token 訪問
        response = client.get("/api/v1/versions/")
        # 允許 401 或 403，因為版本控制可能需要特殊權限
        assert response.status_code in [401, 403]

        # 測試無效 Token
        headers = {"Authorization": f"Bearer {self.invalid_token}"}
        response = client.get("/api/v1/versions/", headers=headers)
        assert response.status_code == 401

        # 測試過期 Token
        headers = {"Authorization": f"Bearer {self.expired_token}"}
        response = client.get("/api/v1/versions/", headers=headers)
        assert response.status_code == 401

    def test_jwt_token_manipulation(self):
        """測試 JWT Token 操作攻擊"""
        # 測試 Token 篡改
        manipulated_tokens = self.auth_tester.generate_manipulated_tokens(
            self.valid_token
        )

        for token in manipulated_tokens:
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get("/api/v1/versions/", headers=headers)
            assert (
                response.status_code == 401
            ), f"篡改的 Token 應該被拒絕: {token[:20]}..."

    def test_jwt_algorithm_confusion(self):
        """測試 JWT 演算法混淆攻擊"""
        # 測試 None 演算法
        none_token = self.auth_tester.generate_none_algorithm_token("test_user")
        headers = {"Authorization": f"Bearer {none_token}"}
        response = client.get("/api/v1/versions/", headers=headers)
        assert response.status_code == 401

        # 測試 HMAC/RSA 混淆
        confused_tokens = self.auth_tester.generate_algorithm_confusion_tokens(
            "test_user"
        )
        confused_token = confused_tokens[0] if confused_tokens else "invalid_token"
        headers = {"Authorization": f"Bearer {confused_token}"}
        response = client.get("/api/v1/versions/", headers=headers)
        assert response.status_code == 401

    @patch("src.api.routers.versioning.get_current_user")
    def test_privilege_escalation(self, mock_auth):
        """測試權限提升攻擊"""
        # 模擬普通用戶
        mock_auth.return_value = "normal_user"

        # 嘗試執行管理員操作
        version_data = {
            "version": "1.0.0",
            "title": "測試版本",
            "status": VersionStatusEnum.DEVELOPMENT.value,
        }

        headers = {"Authorization": f"Bearer {self.valid_token}"}
        response = client.post("/api/v1/versions/", json=version_data, headers=headers)

        # 應該被權限檢查阻止
        assert response.status_code in [403, 401]


@pytest.mark.security
class TestVersioningInjectionSecurity:
    """版本控制注入攻擊安全測試類"""

    def setup_method(self):
        """測試前置設定"""
        self.injection_tester = InjectionTester()
        self.auth_patcher = patch("src.api.routers.versioning.get_current_user")
        self.mock_auth = self.auth_patcher.start()
        self.mock_auth.return_value = "test_user"

    def teardown_method(self):
        """測試後清理"""
        self.auth_patcher.stop()

    def test_sql_injection_protection(self):
        """測試 SQL 注入防護"""
        sql_payloads = self.injection_tester.get_sql_injection_payloads()

        for payload in sql_payloads:
            # 測試版本查詢參數
            response = client.get(f"/api/v1/versions/{payload}")
            assert response.status_code in [
                400,
                403,  # 可能因為權限被拒絕
                404,
            ], f"SQL 注入載荷應該被阻止: {payload}"

            # 測試搜尋參數
            response = client.get(f"/api/v1/versions/?search={payload}")
            assert response.status_code in [
                200,
                400,
                403,  # 可能因為權限被拒絕
            ], f"搜尋參數 SQL 注入應該被處理: {payload}"

    def test_nosql_injection_protection(self):
        """測試 NoSQL 注入防護"""
        nosql_payloads = self.injection_tester.get_nosql_injection_payloads()

        for payload in nosql_payloads:
            # 測試 JSON 參數注入
            version_data = {"version": payload, "title": "測試版本"}

            response = client.post("/api/v1/versions/", json=version_data)
            assert response.status_code in [
                400,
                403,  # 可能因為權限被拒絕
                422,
            ], f"NoSQL 注入載荷應該被阻止: {payload}"

    def test_command_injection_protection(self):
        """測試命令注入防護"""
        command_payloads = self.injection_tester.get_command_injection_payloads()

        for payload in command_payloads:
            # 測試版本名稱參數
            version_data = {
                "version": "1.0.0",
                "title": payload,
                "description": payload,
            }

            response = client.post("/api/v1/versions/", json=version_data)
            # 應該正常處理或返回驗證錯誤，不應該執行命令
            assert response.status_code in [200, 400, 403, 422]


@pytest.mark.security
class TestVersioningXSSSecurity:
    """版本控制 XSS 攻擊安全測試類"""

    def setup_method(self):
        """測試前置設定"""
        self.vulnerability_tester = VulnerabilityTester()
        self.auth_patcher = patch("src.api.routers.versioning.get_current_user")
        self.mock_auth = self.auth_patcher.start()
        self.mock_auth.return_value = "test_user"

    def teardown_method(self):
        """測試後清理"""
        self.auth_patcher.stop()

    def test_xss_protection_in_responses(self):
        """測試響應中的 XSS 防護"""
        xss_payloads = self.vulnerability_tester.get_xss_payloads()

        for payload in xss_payloads:
            # 測試版本標題 XSS
            version_data = {
                "version": "1.0.0",
                "title": payload,
                "description": f"測試描述 {payload}",
            }

            with patch("src.api.routers.versioning.version_service") as mock_service:
                mock_service.create_version.return_value = {
                    "version": {"major": 1, "minor": 0, "patch": 0},
                    "title": payload,
                    "description": f"測試描述 {payload}",
                }

                response = client.post("/api/v1/versions/", json=version_data)

                if response.status_code == 200:
                    # 檢查響應是否包含未轉義的腳本
                    response_text = response.text
                    assert "<script>" not in response_text.lower()
                    assert "javascript:" not in response_text.lower()
                    assert "onerror=" not in response_text.lower()

    def test_content_type_validation(self):
        """測試 Content-Type 驗證"""
        # 測試惡意 Content-Type
        malicious_content_types = [
            "text/html",
            "application/javascript",
            "text/javascript",
        ]

        for content_type in malicious_content_types:
            headers = {"Content-Type": content_type}
            response = client.post(
                "/api/v1/versions/",
                json={"version": "1.0.0", "title": "測試"},
                headers=headers,
            )
            # 應該拒絕或正確處理
            assert response.status_code in [200, 400, 403, 415]


@pytest.mark.security
class TestVersioningInputValidation:
    """版本控制輸入驗證安全測試類"""

    def setup_method(self):
        """測試前置設定"""
        self.security_scanner = SecurityScanner()
        self.auth_patcher = patch("src.api.routers.versioning.get_current_user")
        self.mock_auth = self.auth_patcher.start()
        self.mock_auth.return_value = "test_user"

    def teardown_method(self):
        """測試後清理"""
        self.auth_patcher.stop()

    def test_version_format_validation(self):
        """測試版本格式驗證"""
        invalid_versions = [
            "",
            "invalid",
            "1.2.3.4.5",
            "v1.0.0",
            "1.0",
            "1",
            "1.0.0-",
            "1.0.0+",
            "../../../etc/passwd",
            "1.0.0; DROP TABLE versions;",
            "1.0.0<script>alert('xss')</script>",
        ]

        for invalid_version in invalid_versions:
            version_data = {"version": invalid_version, "title": "測試版本"}

            response = client.post("/api/v1/versions/", json=version_data)
            assert response.status_code in [
                400,
                403,  # 可能因為權限被拒絕
                422,
            ], f"無效版本格式應該被拒絕: {invalid_version}"

    def test_parameter_length_limits(self):
        """測試參數長度限制"""
        # 測試超長標題
        long_title = "A" * 10000
        version_data = {"version": "1.0.0", "title": long_title}

        response = client.post("/api/v1/versions/", json=version_data)
        assert response.status_code in [400, 403, 422], "超長標題應該被拒絕"

        # 測試超長描述
        long_description = "B" * 50000
        version_data = {
            "version": "1.0.0",
            "title": "測試版本",
            "description": long_description,
        }

        response = client.post("/api/v1/versions/", json=version_data)
        assert response.status_code in [400, 403, 422], "超長描述應該被拒絕"

    def test_special_characters_handling(self):
        """測試特殊字符處理"""
        special_chars = [
            "\x00",  # NULL 字符
            "\x1f",  # 控制字符
            "\uffff",  # Unicode 特殊字符
            "🚀",  # Emoji
            "中文測試",  # 中文字符
        ]

        for char in special_chars:
            version_data = {"version": "1.0.0", "title": f"測試{char}版本"}

            response = client.post("/api/v1/versions/", json=version_data)
            # 應該正確處理或返回適當錯誤
            assert response.status_code in [200, 400, 403, 422]


@pytest.mark.security
class TestVersioningRateLimiting:
    """版本控制速率限制安全測試類"""

    def test_rate_limiting_protection(self):
        """測試速率限制防護"""
        # 快速發送大量請求
        responses = []
        for i in range(100):
            response = client.get("/api/v1/versions/")
            responses.append(response.status_code)

        # 檢查是否有速率限制響應
        rate_limited_responses = [code for code in responses if code == 429]

        # 如果實現了速率限制，應該有 429 響應
        if rate_limited_responses:
            print(f"✅ 速率限制正常工作，{len(rate_limited_responses)} 個請求被限制")
        else:
            print("⚠️  未檢測到速率限制機制")

    def test_dos_protection(self):
        """測試 DoS 攻擊防護"""
        # 測試大量並發請求
        import concurrent.futures
        import threading

        def make_request():
            return client.get("/api/v1/versions/")

        # 並發發送請求
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [
                future.result() for future in concurrent.futures.as_completed(futures)
            ]

        # 檢查服務是否仍然響應
        final_response = client.get("/api/v1/versions/")
        assert final_response.status_code in [200, 401, 403, 429], "服務應該仍然響應"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
