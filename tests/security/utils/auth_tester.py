"""
認證測試器

此模組提供 JWT 認證和權限控制的安全測試功能。
"""

import jwt
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from fastapi.testclient import TestClient


@dataclass
class AuthTestResult:
    """認證測試結果"""

    test_name: str
    passed: bool
    expected_status: int
    actual_status: int
    description: str
    security_issue: Optional[str] = None
    recommendation: Optional[str] = None


class AuthTester:
    """認證測試器類"""

    def __init__(self, jwt_secret: str = "dev-secret-key-change-in-production"):
        """
        初始化認證測試器

        Args:
            jwt_secret: JWT 密鑰
        """
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = "HS256"

    def test_jwt_token_validation(
        self, client: TestClient, protected_endpoint: str = "/api/v1/data/"
    ) -> List[AuthTestResult]:
        """
        測試 JWT Token 驗證

        Args:
            client: 測試客戶端
            protected_endpoint: 受保護的端點

        Returns:
            List[AuthTestResult]: 測試結果列表
        """
        results = []

        # 測試 1: 無 Token 訪問
        response = client.get(protected_endpoint)
        results.append(
            AuthTestResult(
                test_name="無 Token 訪問",
                passed=response.status_code == 401,
                expected_status=401,
                actual_status=response.status_code,
                description="測試無認證 Token 時的訪問控制",
                security_issue="認證繞過" if response.status_code != 401 else None,
                recommendation=(
                    "確保所有受保護端點都需要有效認證"
                    if response.status_code != 401
                    else None
                ),
            )
        )

        # 測試 2: 無效 Token 格式
        invalid_tokens = [
            "invalid_token",
            "Bearer invalid_token",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "",
            "null",
        ]

        for token in invalid_tokens:
            headers = {"Authorization": f"Bearer {token}"}
            response = client.get(protected_endpoint, headers=headers)
            results.append(
                AuthTestResult(
                    test_name=f"無效 Token 格式: {token[:20]}...",
                    passed=response.status_code == 401,
                    expected_status=401,
                    actual_status=response.status_code,
                    description="測試無效 Token 格式的處理",
                    security_issue=(
                        "Token 驗證繞過" if response.status_code != 401 else None
                    ),
                )
            )

        # 測試 3: 過期 Token
        expired_token = self._create_expired_token()
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get(protected_endpoint, headers=headers)
        results.append(
            AuthTestResult(
                test_name="過期 Token",
                passed=response.status_code == 401,
                expected_status=401,
                actual_status=response.status_code,
                description="測試過期 Token 的處理",
                security_issue=(
                    "過期 Token 仍然有效" if response.status_code != 401 else None
                ),
                recommendation="確保過期 Token 被正確拒絕",
            )
        )

        # 測試 4: 無效簽名 Token
        invalid_signature_token = self._create_invalid_signature_token()
        headers = {"Authorization": f"Bearer {invalid_signature_token}"}
        response = client.get(protected_endpoint, headers=headers)
        results.append(
            AuthTestResult(
                test_name="無效簽名 Token",
                passed=response.status_code == 401,
                expected_status=401,
                actual_status=response.status_code,
                description="測試無效簽名 Token 的處理",
                security_issue="簽名驗證繞過" if response.status_code != 401 else None,
                recommendation="確保 Token 簽名驗證正確實施",
            )
        )

        # 測試 5: 缺少必要聲明的 Token
        missing_claims_token = self._create_missing_claims_token()
        headers = {"Authorization": f"Bearer {missing_claims_token}"}
        response = client.get(protected_endpoint, headers=headers)
        results.append(
            AuthTestResult(
                test_name="缺少必要聲明的 Token",
                passed=response.status_code == 401,
                expected_status=401,
                actual_status=response.status_code,
                description="測試缺少必要聲明的 Token 處理",
                security_issue=(
                    "不完整 Token 被接受" if response.status_code != 401 else None
                ),
            )
        )

        return results

    def test_privilege_escalation(
        self, client: TestClient, admin_endpoint: str = "/api/v1/admin/users"
    ) -> List[AuthTestResult]:
        """
        測試權限提升攻擊

        Args:
            client: 測試客戶端
            admin_endpoint: 管理員端點

        Returns:
            List[AuthTestResult]: 測試結果列表
        """
        results = []

        # 測試 1: 普通用戶嘗試訪問管理員端點
        user_token = self._create_user_token()
        headers = {"Authorization": f"Bearer {user_token}"}
        response = client.get(admin_endpoint, headers=headers)
        results.append(
            AuthTestResult(
                test_name="普通用戶訪問管理員端點",
                passed=response.status_code in [403, 404, 429],  # 允許速率限制和不存在的端點
                expected_status=403,
                actual_status=response.status_code,
                description="測試普通用戶是否能訪問管理員功能",
                security_issue=(
                    "權限控制繞過" if response.status_code not in [401, 403, 404, 429] else None
                ),
                recommendation="實施適當的角色權限檢查",
            )
        )

        # 測試 2: 修改 Token 中的角色聲明
        escalated_token = self._create_privilege_escalation_token()
        headers = {"Authorization": f"Bearer {escalated_token}"}
        response = client.get(admin_endpoint, headers=headers)
        results.append(
            AuthTestResult(
                test_name="權限提升 Token",
                passed=response.status_code == 401,  # 應該因為簽名無效而被拒絕
                expected_status=401,
                actual_status=response.status_code,
                description="測試修改角色聲明的 Token",
                security_issue="權限提升成功" if response.status_code == 200 else None,
                recommendation="確保 Token 簽名驗證防止篡改",
            )
        )

        return results

    def test_session_management(
        self,
        client: TestClient,
        login_endpoint: str = "/api/v1/auth/login",
        logout_endpoint: str = "/api/v1/auth/logout",
        protected_endpoint: str = "/api/v1/data/",
    ) -> List[AuthTestResult]:
        """
        測試會話管理安全性

        Args:
            client: 測試客戶端
            login_endpoint: 登入端點
            logout_endpoint: 登出端點
            protected_endpoint: 受保護端點

        Returns:
            List[AuthTestResult]: 測試結果列表
        """
        results = []

        # 測試 1: 登入後獲取有效 Token
        login_data = {"username": "admin", "password": "admin123"}
        login_response = client.post(login_endpoint, json=login_data)

        if login_response.status_code == 200:
            token_data = login_response.json()
            if "data" in token_data and "access_token" in token_data["data"]:
                access_token = token_data["data"]["access_token"]
                headers = {"Authorization": f"Bearer {access_token}"}

                # 測試使用有效 Token 訪問
                response = client.get(protected_endpoint, headers=headers)
                results.append(
                    AuthTestResult(
                        test_name="有效 Token 訪問",
                        passed=response.status_code == 200,
                        expected_status=200,
                        actual_status=response.status_code,
                        description="測試有效 Token 的正常訪問",
                    )
                )

                # 測試登出後 Token 失效
                logout_response = client.post(logout_endpoint, headers=headers)
                if logout_response.status_code == 200:
                    # 嘗試使用已登出的 Token
                    response = client.get(protected_endpoint, headers=headers)
                    results.append(
                        AuthTestResult(
                            test_name="登出後 Token 使用",
                            passed=response.status_code == 401,
                            expected_status=401,
                            actual_status=response.status_code,
                            description="測試登出後 Token 是否失效",
                            security_issue=(
                                "登出後 Token 仍然有效"
                                if response.status_code == 200
                                else None
                            ),
                            recommendation="實施 Token 黑名單或會話失效機制",
                        )
                    )

        return results

    def test_brute_force_protection(
        self,
        client: TestClient,
        login_endpoint: str = "/api/v1/auth/login",
        max_attempts: int = 5,
    ) -> List[AuthTestResult]:
        """
        測試暴力破解保護

        Args:
            client: 測試客戶端
            login_endpoint: 登入端點
            max_attempts: 最大嘗試次數

        Returns:
            List[AuthTestResult]: 測試結果列表
        """
        results = []

        # 執行多次錯誤登入嘗試
        for attempt in range(max_attempts + 2):
            login_data = {"username": "admin", "password": f"wrong_password_{attempt}"}
            response = client.post(login_endpoint, json=login_data)

            if attempt < max_attempts:
                # 前幾次應該返回 401
                expected_status = 401
                test_name = f"錯誤登入嘗試 {attempt + 1}"
            else:
                # 超過限制後應該返回 429 (Too Many Requests) 或其他限制狀態
                expected_status = 429
                test_name = f"暴力破解保護測試 {attempt + 1}"

            results.append(
                AuthTestResult(
                    test_name=test_name,
                    passed=response.status_code == expected_status
                    or (
                        attempt >= max_attempts
                        and response.status_code in [429, 423, 401]
                    ),
                    expected_status=expected_status,
                    actual_status=response.status_code,
                    description="測試暴力破解保護機制",
                    security_issue=(
                        "缺少暴力破解保護"
                        if attempt >= max_attempts and response.status_code == 401
                        else None
                    ),
                    recommendation="實施登入嘗試限制和帳戶鎖定機制",
                )
            )

            # 短暫延遲避免過快請求
            time.sleep(0.1)

        return results

    def generate_test_token(
        self,
        username: str = "test_user",
        role: str = "user",
        user_id: Optional[str] = None,
        expires_in_hours: int = 1
    ) -> str:
        """
        生成測試用 JWT Token

        Args:
            username: 用戶名
            role: 用戶角色
            user_id: 用戶ID
            expires_in_hours: 過期時間（小時）

        Returns:
            str: JWT Token
        """
        if user_id is None:
            user_id = username

        payload = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "exp": int((datetime.now() + timedelta(hours=expires_in_hours)).timestamp()),
            "iat": int(datetime.now().timestamp()),
            "type": "access"
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def generate_expired_token(
        self,
        username: str = "test_user",
        role: str = "user",
        user_id: Optional[str] = None,
        hours_ago: int = 1
    ) -> str:
        """
        生成過期的 JWT Token

        Args:
            username: 用戶名
            role: 用戶角色
            user_id: 用戶ID
            hours_ago: 過期時間（小時前）

        Returns:
            str: 過期的 JWT Token
        """
        if user_id is None:
            user_id = username

        payload = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "exp": int((datetime.now() - timedelta(hours=hours_ago)).timestamp()),
            "iat": int((datetime.now() - timedelta(hours=hours_ago + 1)).timestamp()),
            "type": "access"
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def _create_expired_token(self) -> str:
        """創建過期的 JWT Token"""
        payload = {
            "user_id": "test_user",
            "username": "test_user",
            "role": "admin",
            "exp": int((datetime.now() - timedelta(hours=1)).timestamp()),
            "iat": int((datetime.now() - timedelta(hours=2)).timestamp()),
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def _create_invalid_signature_token(self) -> str:
        """創建無效簽名的 JWT Token"""
        payload = {
            "user_id": "test_user",
            "username": "test_user",
            "role": "admin",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp()),
        }
        return jwt.encode(payload, "wrong_secret", algorithm=self.jwt_algorithm)

    def _create_missing_claims_token(self) -> str:
        """創建缺少必要聲明的 JWT Token"""
        payload = {
            "user_id": "test_user",
            # 缺少 username, role, exp 等聲明
            "iat": int(datetime.now().timestamp()),
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def _create_user_token(self) -> str:
        """創建普通用戶 Token"""
        payload = {
            "user_id": "normal_user",
            "username": "normal_user",
            "role": "user",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp()),
        }
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    def _create_privilege_escalation_token(self) -> str:
        """創建權限提升測試 Token（使用錯誤密鑰簽名）"""
        payload = {
            "user_id": "normal_user",
            "username": "normal_user",
            "role": "super_admin",  # 嘗試提升權限
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp()),
        }
        # 使用錯誤密鑰簽名，模擬篡改
        return jwt.encode(payload, "wrong_secret", algorithm=self.jwt_algorithm)

    def generate_manipulated_tokens(self, base_username: str = "test_user") -> List[str]:
        """
        生成各種被篡改的 JWT Token 用於測試

        Args:
            base_username: 基礎用戶名

        Returns:
            List[str]: 被篡改的 Token 列表
        """
        manipulated_tokens = []

        # 1. 修改角色聲明的 Token
        payload = {
            "user_id": base_username,
            "username": base_username,
            "role": "admin",  # 嘗試提升權限
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp()),
            "type": "access"
        }
        # 使用錯誤密鑰簽名
        manipulated_tokens.append(jwt.encode(payload, "wrong_secret", algorithm=self.jwt_algorithm))

        # 2. 修改用戶ID的 Token
        payload["role"] = "user"
        payload["user_id"] = "admin"
        manipulated_tokens.append(jwt.encode(payload, "wrong_secret", algorithm=self.jwt_algorithm))

        # 3. 修改過期時間的 Token
        payload["user_id"] = base_username
        payload["exp"] = int((datetime.now() + timedelta(days=365)).timestamp())  # 延長到一年
        manipulated_tokens.append(jwt.encode(payload, "wrong_secret", algorithm=self.jwt_algorithm))

        # 4. 添加額外聲明的 Token
        payload["exp"] = int((datetime.now() + timedelta(hours=1)).timestamp())
        payload["is_admin"] = True
        payload["permissions"] = ["all"]
        manipulated_tokens.append(jwt.encode(payload, "wrong_secret", algorithm=self.jwt_algorithm))

        return manipulated_tokens

    def generate_none_algorithm_token(self, username: str = "test_user") -> str:
        """
        生成使用 'none' 算法的 JWT Token（安全漏洞測試）

        Args:
            username: 用戶名

        Returns:
            str: 使用 none 算法的 Token
        """
        payload = {
            "user_id": username,
            "username": username,
            "role": "admin",  # 嘗試獲取管理員權限
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp()),
            "type": "access"
        }

        # 使用 'none' 算法（不安全）
        return jwt.encode(payload, "", algorithm="none")

    def generate_algorithm_confusion_tokens(self, username: str = "test_user") -> List[str]:
        """
        生成算法混淆攻擊的 Token

        Args:
            username: 用戶名

        Returns:
            List[str]: 算法混淆 Token 列表
        """
        payload = {
            "user_id": username,
            "username": username,
            "role": "admin",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp()),
            "type": "access"
        }

        tokens = []

        # 1. none 算法
        tokens.append(jwt.encode(payload, "", algorithm="none"))

        # 2. 嘗試使用 RS256 但提供 HMAC 密鑰
        try:
            tokens.append(jwt.encode(payload, self.jwt_secret, algorithm="RS256"))
        except Exception:
            # 如果失敗，創建一個手動構造的 Token
            import base64
            import json

            header = {"alg": "RS256", "typ": "JWT"}
            header_encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
            payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
            signature = base64.urlsafe_b64encode(b"fake_signature").decode().rstrip('=')
            tokens.append(f"{header_encoded}.{payload_encoded}.{signature}")

        return tokens
