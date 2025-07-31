"""
SQL 注入防護測試

此模組測試 API 端點對 SQL 注入攻擊的防護能力。
"""

import pytest
from typing import Dict, List, Any

from fastapi.testclient import TestClient

from tests.security.utils.injection_tester import InjectionTester
from tests.security.utils.security_scanner import SecurityScanner


@pytest.mark.security
@pytest.mark.injection_test
class TestSQLInjection:
    """SQL 注入測試類"""

    def test_sql_injection_in_query_parameters(
        self,
        security_test_client: TestClient,
        valid_auth_headers: Dict[str, str],
        sql_injection_payloads: List[str],
    ):
        """測試查詢參數中的 SQL 注入"""
        # 定義要測試的端點
        test_endpoints = [
            {"url": "/api/v1/data/", "method": "GET"},
            {"url": "/api/v1/strategies/", "method": "GET"},
            {"url": "/api/v1/models/", "method": "GET"},
            {"url": "/api/v1/portfolio/", "method": "GET"},
        ]

        injection_tester = InjectionTester()

        # 執行 SQL 注入測試
        results = injection_tester.test_sql_injection(
            security_test_client, test_endpoints, valid_auth_headers
        )

        # 檢查是否發現漏洞
        vulnerabilities = [
            result for result in results if result.vulnerability_detected
        ]

        if vulnerabilities:
            print("\n❌ 發現 SQL 注入漏洞:")
            for vuln in vulnerabilities:
                print(f"   - {vuln.endpoint} ({vuln.method}): {vuln.payload}")
                print(f"     證據: {vuln.evidence}")

        assert len(vulnerabilities) == 0, f"發現 {len(vulnerabilities)} 個 SQL 注入漏洞"

        print(f"✅ SQL 注入防護測試通過 ({len(results)} 個測試)")

    def test_sql_injection_in_post_data(
        self,
        security_test_client: TestClient,
        valid_auth_headers: Dict[str, str],
        sql_injection_payloads: List[str],
    ):
        """測試 POST 資料中的 SQL 注入"""
        # 定義支援 POST 的端點
        post_endpoints = [
            {"url": "/api/v1/data/sources", "method": "POST"},
            {"url": "/api/v1/strategies/", "method": "POST"},
            {"url": "/api/v1/models/", "method": "POST"},
        ]

        injection_tester = InjectionTester()

        results = injection_tester.test_sql_injection(
            security_test_client, post_endpoints, valid_auth_headers
        )

        vulnerabilities = [
            result for result in results if result.vulnerability_detected
        ]

        assert (
            len(vulnerabilities) == 0
        ), f"POST 資料中發現 {len(vulnerabilities)} 個 SQL 注入漏洞"

        print(f"✅ POST 資料 SQL 注入防護測試通過")

    def test_blind_sql_injection(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """測試盲 SQL 注入"""
        # 盲注測試載荷
        blind_payloads = [
            "1' AND (SELECT COUNT(*) FROM users) > 0 --",
            "1' AND (SELECT SUBSTRING(username,1,1) FROM users WHERE id=1)='a'--",
            "1' AND ASCII(SUBSTRING((SELECT username FROM users LIMIT 1),1,1))>64--",
            "1' AND (SELECT COUNT(*) FROM information_schema.tables)>0--",
        ]

        test_endpoint = "/api/v1/data/"

        for payload in blind_payloads:
            # 測試布林盲注
            params = {"id": payload}
            response = security_test_client.get(
                test_endpoint, params=params, headers=valid_auth_headers
            )

            # 檢查回應是否異常
            assert response.status_code != 500, f"盲 SQL 注入導致伺服器錯誤: {payload}"

            # 檢查回應時間（簡單檢查）
            # 在實際測試中，應該測量回應時間來檢測時間盲注

        print("✅ 盲 SQL 注入防護測試通過")

    def test_union_based_sql_injection(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """測試 UNION 型 SQL 注入"""
        union_payloads = [
            "1' UNION SELECT NULL--",
            "1' UNION SELECT 1,2,3--",
            "1' UNION SELECT username,password,email FROM users--",
            "1' UNION SELECT table_name,column_name,data_type FROM information_schema.columns--",
            "1' UNION SELECT version(),user(),database()--",
        ]

        test_endpoint = "/api/v1/data/"

        for payload in union_payloads:
            params = {"search": payload}
            response = security_test_client.get(
                test_endpoint, params=params, headers=valid_auth_headers
            )

            # 檢查回應長度（UNION 注入可能返回額外資料）
            response_text = response.text
            assert (
                len(response_text) < 10000
            ), f"UNION 注入可能成功，回應過長: {len(response_text)} 字符"

            # 檢查是否包含敏感資訊
            sensitive_patterns = [
                "root:",
                "admin:",
                "password",
                "mysql",
                "postgresql",
                "information_schema",
            ]

            for pattern in sensitive_patterns:
                assert (
                    pattern.lower() not in response_text.lower()
                ), f"UNION 注入洩漏敏感資訊: {pattern}"

        print("✅ UNION 型 SQL 注入防護測試通過")

    def test_error_based_sql_injection(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """測試錯誤型 SQL 注入"""
        error_payloads = [
            "1' AND EXTRACTVALUE(1, CONCAT(0x7e, (SELECT version()), 0x7e))--",
            "1' AND (SELECT * FROM (SELECT COUNT(*),CONCAT(version(),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x)a)--",
            "1' AND UPDATEXML(1,CONCAT(0x7e,(SELECT version()),0x7e),1)--",
            "1' AND EXP(~(SELECT * FROM (SELECT version())a))--",
        ]

        test_endpoint = "/api/v1/data/"

        for payload in error_payloads:
            params = {"id": payload}
            response = security_test_client.get(
                test_endpoint, params=params, headers=valid_auth_headers
            )

            response_text = response.text.lower()

            # 檢查是否洩漏資料庫版本資訊
            version_patterns = [
                "mysql",
                "postgresql",
                "sqlite",
                "oracle",
                "sql server",
                "mariadb",
            ]

            for pattern in version_patterns:
                assert (
                    pattern not in response_text
                ), f"錯誤型 SQL 注入洩漏資料庫資訊: {pattern}"

        print("✅ 錯誤型 SQL 注入防護測試通過")

    def test_time_based_sql_injection(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """測試時間型 SQL 注入"""
        import time

        time_payloads = [
            "1'; WAITFOR DELAY '00:00:05'--",  # SQL Server
            "1' AND (SELECT SLEEP(5))--",  # MySQL
            "1' AND (SELECT pg_sleep(5))--",  # PostgreSQL
            "1'; SELECT CASE WHEN (1=1) THEN pg_sleep(5) ELSE pg_sleep(0) END--",
        ]

        test_endpoint = "/api/v1/data/"

        for payload in time_payloads:
            start_time = time.time()

            params = {"id": payload}
            response = security_test_client.get(
                test_endpoint, params=params, headers=valid_auth_headers
            )

            elapsed_time = time.time() - start_time

            # 如果回應時間超過 3 秒，可能存在時間注入
            assert (
                elapsed_time < 3.0
            ), f"時間型 SQL 注入可能成功，回應時間: {elapsed_time:.2f}s"

        print("✅ 時間型 SQL 注入防護測試通過")

    def test_stacked_queries_injection(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """測試堆疊查詢注入"""
        stacked_payloads = [
            "1'; DROP TABLE test_table; --",
            "1'; INSERT INTO users VALUES ('hacker','password'); --",
            "1'; UPDATE users SET password='hacked' WHERE id=1; --",
            "1'; CREATE TABLE evil_table (id INT); --",
            "1'; DELETE FROM logs WHERE 1=1; --",
        ]

        test_endpoint = "/api/v1/data/"

        for payload in stacked_payloads:
            params = {"id": payload}
            response = security_test_client.get(
                test_endpoint, params=params, headers=valid_auth_headers
            )

            # 堆疊查詢通常會導致錯誤或異常行為
            assert response.status_code != 500, f"堆疊查詢注入導致伺服器錯誤: {payload}"

            # 檢查回應中是否有執行成功的跡象
            response_text = response.text.lower()
            success_indicators = [
                "table dropped",
                "record inserted",
                "record updated",
                "table created",
                "record deleted",
            ]

            for indicator in success_indicators:
                assert (
                    indicator not in response_text
                ), f"堆疊查詢可能執行成功: {indicator}"

        print("✅ 堆疊查詢注入防護測試通過")

    def test_second_order_sql_injection(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """測試二階 SQL 注入"""
        # 二階注入：先存儲惡意資料，然後在其他操作中觸發

        # 第一步：嘗試存儲包含 SQL 注入的資料
        malicious_data = {
            "name": "admin'; UPDATE users SET password='hacked' WHERE username='admin'--",
            "description": "test' OR '1'='1",
            "content": "'; DROP TABLE users; --",
        }

        # 嘗試創建包含惡意資料的記錄
        response = security_test_client.post(
            "/api/v1/strategies/", json=malicious_data, headers=valid_auth_headers
        )

        # 即使創建成功，也不應該執行 SQL 注入
        if response.status_code in [200, 201]:
            # 第二步：嘗試觸發存儲的惡意資料
            response = security_test_client.get(
                "/api/v1/strategies/", headers=valid_auth_headers
            )

            # 檢查是否有異常行為
            assert response.status_code == 200, "二階 SQL 注入可能導致系統異常"

        print("✅ 二階 SQL 注入防護測試通過")

    def test_comprehensive_sql_injection_scan(
        self, security_test_client: TestClient, valid_auth_headers: Dict[str, str]
    ):
        """全面的 SQL 注入掃描"""
        scanner = SecurityScanner()

        # 定義要掃描的端點
        endpoints = [
            {"url": "/api/v1/data/", "method": "GET"},
            {"url": "/api/v1/data/sources", "method": "GET"},
            {"url": "/api/v1/strategies/", "method": "GET"},
            {"url": "/api/v1/models/", "method": "GET"},
            {"url": "/api/v1/portfolio/", "method": "GET"},
        ]

        # 執行安全掃描
        scan_result = scanner.scan_api_security(
            security_test_client, endpoints, valid_auth_headers
        )

        # 檢查 SQL 注入相關問題
        sql_injection_issues = [
            issue
            for issue in scan_result.issues_found
            if issue.category == "sql_injection"
        ]

        if sql_injection_issues:
            print(f"\n❌ 發現 {len(sql_injection_issues)} 個 SQL 注入問題:")
            for issue in sql_injection_issues:
                print(f"   - {issue.endpoint}: {issue.title}")
                print(f"     嚴重程度: {issue.severity}")
                print(f"     證據: {issue.evidence}")

        assert (
            len(sql_injection_issues) == 0
        ), f"全面掃描發現 {len(sql_injection_issues)} 個 SQL 注入漏洞"

        print(
            f"✅ 全面 SQL 注入掃描通過 (安全評分: {scan_result.security_score:.1f}/100)"
        )
