"""
API 認證功能測試

此模組測試 API 認證相關功能，包括登入、登出、註冊、Token 刷新等。
"""

import pytest
import requests
import json
from datetime import datetime


class TestAPIAuth:
    """API 認證測試類"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """設置測試環境"""
        self.base_url = "http://127.0.0.1:8000"
        self.api_url = f"{self.base_url}/api/v1"
        self.access_token = None
        self.refresh_token = None

    def test_api_health(self):
        """測試 API 健康檢查"""
        print("\n🔍 測試 API 健康檢查...")

        response = requests.get(f"{self.base_url}/health")

        print(f"狀態碼: {response.status_code}")
        print(f"響應: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "healthy" in data["data"]["api"]

        print("✅ API 健康檢查通過")

    def test_api_info(self):
        """測試 API 資訊"""
        print("\n🔍 測試 API 資訊...")

        response = requests.get(f"{self.base_url}/api/info")

        print(f"狀態碼: {response.status_code}")
        print(f"響應: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "AI 交易系統 API" in data["data"]["title"]

        print("✅ API 資訊獲取成功")

    def test_login_success(self):
        """測試成功登入"""
        print("\n🔍 測試用戶登入...")

        login_data = {
            "username": "admin",
            "password": "admin123",
            "remember_me": False,
            "device_info": {"user_agent": "Test Client", "ip_address": "127.0.0.1"},
        }

        response = requests.post(
            f"{self.api_url}/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
        )

        print(f"狀態碼: {response.status_code}")
        print(f"響應: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

        # 保存 Token 供後續測試使用
        self.access_token = data["data"]["access_token"]
        self.refresh_token = data["data"]["refresh_token"]

        print("✅ 用戶登入成功")
        print(f"Access Token: {self.access_token[:50]}...")

    def test_login_failure(self):
        """測試登入失敗"""
        print("\n🔍 測試登入失敗...")

        login_data = {"username": "admin", "password": "wrong_password"}

        response = requests.post(
            f"{self.api_url}/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
        )

        print(f"狀態碼: {response.status_code}")
        print(f"響應: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "用戶名或密碼錯誤" in data["message"]

        print("✅ 登入失敗測試通過")

    def test_get_current_user(self):
        """測試獲取當前用戶資訊"""
        print("\n🔍 測試獲取當前用戶資訊...")

        if not self.access_token:
            print("❌ 需要先登入")
            return

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        response = requests.get(f"{self.api_url}/auth/me", headers=headers)

        print(f"狀態碼: {response.status_code}")
        print(f"響應: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["username"] == "admin"
        assert data["data"]["role"] == "admin"

        print("✅ 獲取用戶資訊成功")

    def test_access_protected_endpoint(self):
        """測試訪問受保護的端點"""
        print("\n🔍 測試訪問受保護端點...")

        if not self.access_token:
            print("❌ 需要先登入")
            return

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        # 測試訪問資料管理端點
        response = requests.get(f"{self.api_url}/data/", headers=headers)

        print(f"狀態碼: {response.status_code}")
        print(f"響應: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        print("✅ 受保護端點訪問成功")

    def test_access_without_token(self):
        """測試無 Token 訪問受保護端點"""
        print("\n🔍 測試無 Token 訪問...")

        response = requests.get(f"{self.api_url}/data/")

        print(f"狀態碼: {response.status_code}")
        print(f"響應: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False

        print("✅ 無 Token 訪問被正確拒絕")

    def test_refresh_token(self):
        """測試 Token 刷新"""
        print("\n🔍 測試 Token 刷新...")

        if not self.refresh_token:
            print("❌ 需要先登入獲取 refresh token")
            return

        refresh_data = {"refresh_token": self.refresh_token}

        response = requests.post(
            f"{self.api_url}/auth/refresh",
            json=refresh_data,
            headers={"Content-Type": "application/json"},
        )

        print(f"狀態碼: {response.status_code}")
        print(f"響應: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]

        # 更新 access token
        self.access_token = data["data"]["access_token"]

        print("✅ Token 刷新成功")

    def test_register_user(self):
        """測試用戶註冊"""
        print("\n🔍 測試用戶註冊...")

        register_data = {
            "username": f"test_user_{int(datetime.now().timestamp())}",
            "email": f"test_{int(datetime.now().timestamp())}@example.com",
            "password": "test123456",
            "confirm_password": "test123456",
            "full_name": "測試用戶",
            "role": "user",
        }

        response = requests.post(
            f"{self.api_url}/auth/register",
            json=register_data,
            headers={"Content-Type": "application/json"},
        )

        print(f"狀態碼: {response.status_code}")
        print(f"響應: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["username"] == register_data["username"]
        assert data["data"]["role"] == "user"

        print("✅ 用戶註冊成功")

    def test_logout(self):
        """測試用戶登出"""
        print("\n🔍 測試用戶登出...")

        if not self.access_token:
            print("❌ 需要先登入")
            return

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        response = requests.post(f"{self.api_url}/auth/logout", headers=headers)

        print(f"狀態碼: {response.status_code}")
        print(f"響應: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        print("✅ 用戶登出成功")

        # 清除 Token
        self.access_token = None
        self.refresh_token = None

    def run_all_tests(self):
        """運行所有測試"""
        print("🚀 開始 API 認證功能測試")
        print("=" * 50)

        try:
            # 基礎測試
            self.test_api_health()
            self.test_api_info()

            # 認證測試
            self.test_login_failure()  # 先測試失敗情況
            self.test_access_without_token()  # 測試無 Token 訪問

            self.test_login_success()  # 成功登入
            self.test_get_current_user()  # 獲取用戶資訊
            self.test_access_protected_endpoint()  # 訪問受保護端點
            self.test_refresh_token()  # Token 刷新

            # 註冊測試
            self.test_register_user()

            # 登出測試
            self.test_logout()

            print("\n" + "=" * 50)
            print("🎉 所有測試通過！API 認證功能正常")

        except Exception as e:
            print(f"\n❌ 測試失敗: {e}")
            raise


def main():
    """主函數"""
    tester = TestAPIAuth()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
