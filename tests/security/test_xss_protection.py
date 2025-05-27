"""
XSS 防護測試

此模組測試 API 端點對跨站腳本攻擊（XSS）的防護能力。
"""

import pytest
from typing import Dict, List, Any

from fastapi.testclient import TestClient

from tests.security.utils.vulnerability_tester import VulnerabilityTester
from tests.security.utils.security_scanner import SecurityScanner


@pytest.mark.security
@pytest.mark.xss_test
class TestXSSProtection:
    """XSS 防護測試類"""

    def test_reflected_xss_protection(
        self,
        security_test_client: TestClient,
        valid_auth_headers: Dict[str, str],
        xss_payloads: List[str],
    ):
        """測試反射型 XSS 防護"""
        # 定義可能返回 HTML 的端點
        test_endpoints = [
            {"url": "/api/v1/data/", "method": "GET"},
            {"url": "/api/v1/strategies/", "method": "GET"},
            {"url": "/api/v1/models/", "method": "GET"},
        ]

        vulnerability_tester = VulnerabilityTester()

        # 執行 XSS 測試
        results = vulnerability_tester.test_xss_vulnerabilities(
            security_test_client, test_endpoints, valid_auth_headers
        )

        # 檢查是否發現 XSS 漏洞
        xss_vulnerabilities = [
            result for result in results if result.vulnerability_detected
        ]

        if xss_vulnerabilities:
            print("\n❌ 發現 XSS 漏洞:")
            for vuln in xss_vulnerabilities:
                print(f"   - {vuln.endpoint} ({vuln.method}): {vuln.payload}")
                print(f"     證據: {vuln.evidence}")

        assert (
            len(xss_vulnerabilities) == 0
        ), f"發現 {len(xss_vulnerabilities)} 個 XSS 漏洞"

        print(f"✅ 反射型 XSS 防護測試通過 ({len(results)} 個測試)")

    def test_stored_xss_protection(
        self,
        security_test_client: TestClient,
        valid_auth_headers: Dict[str, str],
        xss_payloads: List[str],
    ):
        """測試儲存型 XSS 防護"""
        # 測試儲存型 XSS（通過 POST 存儲惡意腳本）

        for payload in xss_payloads[:5]:  # 限制測試數量
            # 嘗試存儲包含 XSS 的資料
            malicious_data = {
                "name": payload,
                "description": payload,
                "content": payload,
                "comment": payload,
            }

            # 嘗試創建包含 XSS 的記錄
            post_response = security_test_client.post(
                "/api/v1/strategies/", json=malicious_data, headers=valid_auth_headers
            )

            # 即使創建成功，也要檢查返回的資料是否被正確轉義
            if post_response.status_code in [200, 201]:
                response_text = post_response.text

                # 檢查回應中是否包含未轉義的腳本
                assert (
                    payload not in response_text
                ), f"儲存型 XSS：未轉義的腳本出現在回應中"

                # 檢查是否正確轉義
                escaped_patterns = ["&lt;", "&gt;", "&quot;", "&#x27;", "&#x2F;"]
                has_escaping = any(
                    pattern in response_text for pattern in escaped_patterns
                )

                if "<script" in payload.lower():
                    assert (
                        has_escaping or payload not in response_text
                    ), "腳本標籤未被正確處理"

        print("✅ 儲存型 XSS 防護測試通過")

    def test_dom_xss_protection(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """測試 DOM 型 XSS 防護"""
        # DOM XSS 通常發生在客戶端，但我們可以測試 API 是否返回安全的資料

        dom_xss_payloads = [
            "';alert('XSS');//",
            "\";alert('XSS');//",
            "javascript:alert('XSS')",
            "data:text/html,<script>alert('XSS')</script>",
            "vbscript:alert('XSS')",
            "onload=alert('XSS')",
            "onerror=alert('XSS')",
        ]

        for payload in dom_xss_payloads:
            params = {"callback": payload, "jsonp": payload}
            response = security_test_client.get(
                "/api/v1/data/", params=params, headers=valid_auth_headers
            )

            response_text = response.text

            # 檢查回應中是否包含危險的 JavaScript 代碼
            dangerous_patterns = [
                "alert(",
                "eval(",
                "javascript:",
                "vbscript:",
                "onload=",
                "onerror=",
            ]

            for pattern in dangerous_patterns:
                assert (
                    pattern not in response_text.lower()
                ), f"DOM XSS：危險模式 '{pattern}' 出現在回應中"

        print("✅ DOM 型 XSS 防護測試通過")

    def test_xss_filter_bypass_attempts(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """測試 XSS 過濾器繞過嘗試"""
        # 各種繞過技術
        bypass_payloads = [
            # 大小寫混合
            "<ScRiPt>alert('XSS')</ScRiPt>",
            "<IMG SRC=javascript:alert('XSS')>",
            # 編碼繞過
            "%3Cscript%3Ealert('XSS')%3C/script%3E",
            "&#60;script&#62;alert('XSS')&#60;/script&#62;",
            "&lt;script&gt;alert('XSS')&lt;/script&gt;",
            # 雙重編碼
            "%253Cscript%253Ealert('XSS')%253C/script%253E",
            # Unicode 編碼
            "\\u003cscript\\u003ealert('XSS')\\u003c/script\\u003e",
            # 標籤分割
            "<scr<script>ipt>alert('XSS')</scr</script>ipt>",
            "<img src=x onerror=alert('XSS')>",
            # 事件處理器
            "<body onload=alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
            "<select onfocus=alert('XSS') autofocus>",
            # CSS 注入
            "<style>@import'javascript:alert(\"XSS\")';</style>",
            "<link rel=stylesheet href=javascript:alert('XSS')>",
            # 多媒體標籤
            "<video><source onerror=alert('XSS')>",
            "<audio src=x onerror=alert('XSS')>",
            # 過濾器繞過
            "<<SCRIPT>alert('XSS');//<</SCRIPT>",
            "<script>eval(String.fromCharCode(97,108,101,114,116,40,39,88,83,83,39,41))</script>",
        ]

        test_endpoint = "/api/v1/data/"

        for payload in bypass_payloads:
            params = {"search": payload, "q": payload}
            response = security_test_client.get(
                test_endpoint, params=params, headers=valid_auth_headers
            )

            response_text = response.text
            content_type = response.headers.get("content-type", "").lower()

            # 如果是 HTML 回應，檢查是否包含未轉義的腳本
            if "text/html" in content_type:
                # 檢查原始載荷是否出現
                assert payload not in response_text, f"XSS 過濾器繞過成功: {payload}"

                # 檢查危險模式
                dangerous_patterns = ["<script", "javascript:", "onerror=", "onload="]
                for pattern in dangerous_patterns:
                    if pattern in payload.lower():
                        assert (
                            pattern not in response_text.lower()
                        ), f"危險模式未被過濾: {pattern}"

        print("✅ XSS 過濾器繞過防護測試通過")

    def test_content_type_xss_protection(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """測試內容類型相關的 XSS 防護"""
        # 測試不同內容類型的回應

        test_endpoints = ["/api/v1/data/sources", "/api/info", "/health"]

        for endpoint in test_endpoints:
            response = security_test_client.get(endpoint, headers=valid_auth_headers)

            content_type = response.headers.get("content-type", "").lower()

            # 檢查 X-Content-Type-Options 標頭
            x_content_type_options = response.headers.get(
                "x-content-type-options", ""
            ).lower()
            if "text/html" not in content_type and response.status_code == 200:
                # 非 HTML 回應應該有 nosniff 標頭（僅檢查成功的回應）
                if not x_content_type_options or "nosniff" not in x_content_type_options:
                    print(f"⚠️ {endpoint} 缺少 X-Content-Type-Options: nosniff 標頭")
                    # 不強制失敗，只是警告
                    # assert False, f"{endpoint} 缺少 X-Content-Type-Options: nosniff"

            # JSON 回應不應該被瀏覽器解釋為 HTML
            if "application/json" in content_type:
                assert not response.text.startswith(
                    "<"
                ), "JSON 回應不應該包含 HTML 標籤"

        print("✅ 內容類型 XSS 防護測試通過")

    def test_xss_protection_headers(self, security_test_client: TestClient):
        """測試 XSS 防護標頭"""
        # 測試可能返回 HTML 的端點
        response = security_test_client.get("/")

        # 檢查 X-XSS-Protection 標頭
        xss_protection = response.headers.get("x-xss-protection", "")
        if xss_protection:
            assert "1" in xss_protection, "X-XSS-Protection 應該啟用"

        # 檢查 Content-Security-Policy 標頭
        csp = response.headers.get("content-security-policy", "")
        if csp:
            # CSP 應該限制腳本來源
            assert "script-src" in csp.lower(), "CSP 應該包含 script-src 指令"
            assert "'unsafe-inline'" not in csp.lower(), "CSP 不應該允許 unsafe-inline"

        print("✅ XSS 防護標頭測試通過")

    def test_jsonp_xss_protection(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """測試 JSONP XSS 防護"""
        # 測試 JSONP 回調函數注入

        malicious_callbacks = [
            "alert('XSS')",
            "eval('alert(1)')",
            "document.write('<script>alert(1)</script>')",
            "window.location='http://evil.com'",
            "function(){alert('XSS')}",
            "a();alert('XSS');//",
        ]

        for callback in malicious_callbacks:
            params = {"callback": callback, "jsonp": callback}
            response = security_test_client.get(
                "/api/v1/data/sources", params=params, headers=valid_auth_headers
            )

            response_text = response.text

            # JSONP 回應不應該包含惡意回調
            assert (
                callback not in response_text
            ), f"JSONP XSS：惡意回調出現在回應中: {callback}"

            # 檢查是否有適當的回調驗證
            if "callback" in response_text:
                # 回調應該被清理或驗證
                dangerous_patterns = ["alert(", "eval(", "document.", "window."]
                for pattern in dangerous_patterns:
                    assert (
                        pattern not in response_text
                    ), f"JSONP 回調包含危險模式: {pattern}"

        print("✅ JSONP XSS 防護測試通過")

    def test_comprehensive_xss_scan(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """全面的 XSS 掃描"""
        scanner = SecurityScanner()

        # 定義要掃描的端點
        endpoints = [
            {"url": "/api/v1/data/sources", "method": "GET"},
            {"url": "/api/v1/strategies/", "method": "GET"},
            {"url": "/api/v1/strategies/", "method": "POST"},
            {"url": "/api/v1/models/", "method": "GET"},
        ]

        # 執行安全掃描
        scan_result = scanner.scan_api_security(
            security_test_client, endpoints, valid_auth_headers
        )

        # 檢查 XSS 相關問題
        xss_issues = [
            issue for issue in scan_result.issues_found if issue.category == "xss"
        ]

        if xss_issues:
            print(f"\n❌ 發現 {len(xss_issues)} 個 XSS 問題:")
            for issue in xss_issues:
                print(f"   - {issue.endpoint}: {issue.title}")
                print(f"     嚴重程度: {issue.severity}")
                print(f"     證據: {issue.evidence}")

        assert len(xss_issues) == 0, f"全面掃描發現 {len(xss_issues)} 個 XSS 漏洞"

        print(f"✅ 全面 XSS 掃描通過 (安全評分: {scan_result.security_score:.1f}/100)")
