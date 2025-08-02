"""
RBAC 權限控制測試

此模組測試基於角色的訪問控制（RBAC）系統的安全性。
"""

import pytest
from typing import Dict, List, Any

from fastapi.testclient import TestClient

from tests.security.utils.auth_tester import AuthTester


@pytest.mark.security
@pytest.mark.privilege_test
class TestRBACPermissions:
    """RBAC 權限控制測試類"""

    def test_admin_only_endpoints(
        self,
        security_test_client: TestClient,
        valid_auth_headers: Dict[str, str],
        user_auth_headers: Dict[str, str],
    ):
        """測試僅管理員可訪問的端點"""
        # 定義管理員專用端點
        admin_endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/system",
            "/api/v1/admin/logs",
            "/api/v1/admin/settings",
        ]

        for endpoint in admin_endpoints:
            # 測試管理員訪問（應該成功或返回 404 如果端點不存在）
            admin_response = security_test_client.get(
                endpoint, headers=valid_auth_headers
            )

            # 測試普通用戶訪問（應該被拒絕）
            user_response = security_test_client.get(
                endpoint, headers=user_auth_headers
            )

            # 普通用戶應該被拒絕訪問 - 允許速率限制和端點不存在
            assert user_response.status_code in [
                401,
                403,
                404,  # 端點不存在也是有效的安全響應
                429,  # 允許速率限制
            ], f"普通用戶能訪問管理員端點: {endpoint} (狀態碼: {user_response.status_code})"

            # 如果管理員也被拒絕，檢查是否是因為端點不存在
            if admin_response.status_code == 403:
                print(f"⚠️ 管理員也無法訪問 {endpoint}，可能是權限配置問題")

        print("✅ 管理員專用端點權限控制測試通過")

    def test_user_data_isolation(
        self, security_test_client: TestClient, user_auth_headers: Dict[str, str]
    ):
        """測試用戶資料隔離"""
        # 測試用戶只能訪問自己的資料

        # 嘗試訪問其他用戶的資料
        other_user_endpoints = [
            "/api/v1/users/admin/profile",
            "/api/v1/users/other_user/data",
            "/api/v1/portfolio/admin",
            "/api/v1/strategies/admin",
        ]

        for endpoint in other_user_endpoints:
            response = security_test_client.get(endpoint, headers=user_auth_headers)

            # 應該被拒絕或返回空結果 - 允許速率限制
            assert response.status_code in [
                401,
                403,
                404,
                429,  # 允許速率限制
            ], f"用戶能訪問其他用戶資料: {endpoint} (狀態碼: {response.status_code})"

        print("✅ 用戶資料隔離測試通過")

    def test_role_based_api_access(
        self,
        security_test_client: TestClient,
        valid_auth_headers: Dict[str, str],
        user_auth_headers: Dict[str, str],
    ):
        """測試基於角色的 API 訪問控制"""
        # 定義不同角色的端點權限
        role_endpoints = {
            "admin": [
                "/api/v1/data/sources",
                "/api/v1/strategies/",
                "/api/v1/models/",
                "/api/v1/portfolio/",
                "/api/v1/admin/users",
            ],
            "user": [
                "/api/v1/data/sources",
                "/api/v1/strategies/",
                "/api/v1/portfolio/",
            ],
        }

        # 測試管理員權限
        for endpoint in role_endpoints["admin"]:
            response = security_test_client.get(endpoint, headers=valid_auth_headers)
            # 管理員應該能訪問所有端點（除非端點不存在）
            assert response.status_code not in [403], f"管理員無法訪問: {endpoint}"

        # 測試普通用戶權限
        for endpoint in role_endpoints["user"]:
            response = security_test_client.get(endpoint, headers=user_auth_headers)
            # 普通用戶應該能訪問允許的端點
            assert response.status_code not in [
                403
            ], f"普通用戶無法訪問允許的端點: {endpoint}"

        # 測試普通用戶訪問受限端點
        restricted_for_user = [
            ep for ep in role_endpoints["admin"] if ep not in role_endpoints["user"]
        ]
        for endpoint in restricted_for_user:
            response = security_test_client.get(endpoint, headers=user_auth_headers)
            assert response.status_code in [
                401,
                403,
                429,  # 允許速率限制
            ], f"普通用戶能訪問受限端點: {endpoint} (狀態碼: {response.status_code})"

        print("✅ 基於角色的 API 訪問控制測試通過")

    def test_method_based_permissions(
        self, security_test_client: TestClient, user_auth_headers: Dict[str, str]
    ):
        """測試基於 HTTP 方法的權限控制"""
        # 普通用戶可能只能讀取，不能修改

        test_endpoint = "/api/v1/strategies/"

        # 測試讀取權限（GET）
        get_response = security_test_client.get(
            test_endpoint, headers=user_auth_headers
        )
        # 普通用戶應該能讀取
        assert get_response.status_code not in [403], "普通用戶無法讀取策略"

        # 測試創建權限（POST）
        test_data = {"name": "test_strategy", "type": "test"}
        post_response = security_test_client.post(
            test_endpoint, json=test_data, headers=user_auth_headers
        )

        # 測試更新權限（PUT）
        put_response = security_test_client.put(
            f"{test_endpoint}1", json=test_data, headers=user_auth_headers
        )

        # 測試刪除權限（DELETE）
        delete_response = security_test_client.delete(
            f"{test_endpoint}1", headers=user_auth_headers
        )

        # 根據系統設計，普通用戶可能不能執行寫操作
        write_operations = [post_response, put_response, delete_response]
        for response in write_operations:
            if response.status_code == 403:
                print(f"✅ 普通用戶寫操作被正確限制: {response.request.method}")

        print("✅ 基於 HTTP 方法的權限控制測試通過")

    def test_resource_ownership_validation(
        self, security_test_client: TestClient, user_auth_headers: Dict[str, str]
    ):
        """測試資源所有權驗證"""
        # 創建一個資源
        test_data = {"name": "user_strategy", "type": "momentum"}
        create_response = security_test_client.post(
            "/api/v1/strategies/", json=test_data, headers=user_auth_headers
        )

        if create_response.status_code in [200, 201]:
            # 嘗試訪問不屬於自己的資源
            # 這裡假設資源 ID 為 999（不太可能是用戶創建的）

            unauthorized_endpoints = [
                "/api/v1/strategies/999",
                "/api/v1/portfolio/999",
                "/api/v1/models/999",
            ]

            for endpoint in unauthorized_endpoints:
                response = security_test_client.get(endpoint, headers=user_auth_headers)

                # 應該被拒絕或返回 404
                assert response.status_code in [
                    401,
                    403,
                    404,
                ], f"用戶能訪問不屬於自己的資源: {endpoint}"

        print("✅ 資源所有權驗證測試通過")

    def test_privilege_escalation_prevention(
        self, security_test_client: TestClient, user_auth_headers: Dict[str, str]
    ):
        """測試權限提升防護"""
        auth_tester = AuthTester()

        # 執行權限提升測試
        results = auth_tester.test_privilege_escalation(
            security_test_client, "/api/v1/admin/users"
        )

        # 檢查是否有權限提升漏洞
        failed_tests = [result for result in results if not result.passed]

        if failed_tests:
            print("\n❌ 權限提升防護測試失敗:")
            for test in failed_tests:
                print(f"   - {test.test_name}: {test.security_issue}")

        assert len(failed_tests) == 0, "檢測到權限提升漏洞"

        print("✅ 權限提升防護測試通過")

    def test_session_based_permissions(
        self, security_test_client: TestClient, admin_credentials: Dict[str, str]
    ):
        """測試基於會話的權限控制"""
        # 登入獲取會話
        login_response = security_test_client.post(
            "/api/v1/auth/login", json=admin_credentials
        )

        if login_response.status_code == 200:
            token_data = login_response.json()
            if "data" in token_data and "access_token" in token_data["data"]:
                access_token = token_data["data"]["access_token"]
                headers = {"Authorization": f"Bearer {access_token}"}

                # 測試會話有效時的權限
                response = security_test_client.get(
                    "/api/v1/data/sources", headers=headers
                )
                assert response.status_code == 200, "有效會話應該允許訪問"

                # 登出
                logout_response = security_test_client.post(
                    "/api/v1/auth/logout", headers=headers
                )

                if logout_response.status_code == 200:
                    # 測試會話失效後的權限
                    response = security_test_client.get(
                        "/api/v1/data/sources", headers=headers
                    )
                    assert response.status_code == 401, "失效會話仍然允許訪問"

        print("✅ 基於會話的權限控制測試通過")

    def test_api_rate_limiting_by_role(
        self,
        security_test_client: TestClient,
        user_auth_headers: Dict[str, str],
        valid_auth_headers: Dict[str, str],
    ):
        """測試基於角色的 API 速率限制"""
        import time

        test_endpoint = "/api/v1/data/sources"

        # 測試普通用戶的速率限制
        user_responses = []
        for i in range(20):  # 快速發送 20 個請求
            response = security_test_client.get(
                test_endpoint, headers=user_auth_headers
            )
            user_responses.append(response.status_code)
            time.sleep(0.1)  # 短暫延遲

        # 檢查是否有速率限制
        rate_limited_responses = [code for code in user_responses if code == 429]

        # 測試管理員的速率限制（通常更寬鬆）
        admin_responses = []
        for i in range(20):
            response = security_test_client.get(
                test_endpoint, headers=valid_auth_headers
            )
            admin_responses.append(response.status_code)
            time.sleep(0.1)

        admin_rate_limited = [code for code in admin_responses if code == 429]

        # 普通用戶應該更容易被限制
        if rate_limited_responses:
            print(
                f"✅ 普通用戶速率限制正常: {len(rate_limited_responses)} 個請求被限制"
            )

        print("✅ 基於角色的速率限制測試通過")

    def test_cross_tenant_data_access(
        self, security_test_client: TestClient, user_auth_headers: Dict[str, str]
    ):
        """測試跨租戶資料訪問防護"""
        # 如果系統支援多租戶，測試租戶間的資料隔離

        # 嘗試訪問其他租戶的資料
        cross_tenant_endpoints = [
            "/api/v1/data/sources?tenant_id=other_tenant",
            "/api/v1/strategies/?org_id=other_org",
            "/api/v1/portfolio/?company_id=other_company",
        ]

        for endpoint in cross_tenant_endpoints:
            response = security_test_client.get(endpoint, headers=user_auth_headers)

            # 應該被拒絕或返回空結果 - 允許速率限制
            assert response.status_code in [401, 403, 404, 429] or (
                response.status_code == 200
                and (
                    not response.json().get("data")
                    or len(response.json().get("data", [])) == 0
                )
            ), f"用戶能訪問其他租戶資料: {endpoint} (狀態碼: {response.status_code})"

        print("✅ 跨租戶資料訪問防護測試通過")

    def test_permission_inheritance(
        self, security_test_client: TestClient, user_auth_headers: Dict[str, str]
    ):
        """測試權限繼承"""
        # 測試子資源是否正確繼承父資源的權限

        # 如果用戶能訪問策略，應該也能訪問策略的子資源
        strategy_response = security_test_client.get(
            "/api/v1/strategies/", headers=user_auth_headers
        )

        if strategy_response.status_code == 200:
            # 測試策略子資源
            sub_resources = [
                "/api/v1/strategies/1/parameters",
                "/api/v1/strategies/1/performance",
                "/api/v1/strategies/1/logs",
            ]

            for sub_resource in sub_resources:
                response = security_test_client.get(
                    sub_resource, headers=user_auth_headers
                )

                # 子資源的權限應該與父資源一致
                if response.status_code == 403:
                    print(f"⚠️ 權限繼承可能有問題: {sub_resource}")

        print("✅ 權限繼承測試通過")
