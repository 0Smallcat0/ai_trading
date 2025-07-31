#!/usr/bin/env python3
"""
資料管理 API 測試腳本

測試資料管理相關的 API 端點功能。
"""

import requests
import json
from datetime import datetime


class DataManagementAPITester:
    """資料管理 API 測試器"""

    def __init__(self, base_url="http://127.0.0.1:8000"):
        self.base_url = base_url
        self.token = None
        self.session = requests.Session()

    def login(self):
        """登入獲取 Token"""
        print("🔐 正在登入...")

        login_data = {
            "username": "admin",
            "password": "admin123",
            "remember_me": False,
            "device_info": {"user_agent": "Test Client", "ip_address": "127.0.0.1"},
        }

        response = self.session.post(
            f"{self.base_url}/api/v1/auth/login", json=login_data
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data["data"]["access_token"]
            self.session.headers.update(
                {
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                }
            )
            print("✅ 登入成功")
            return True
        else:
            print(f"❌ 登入失敗: {response.text}")
            return False

    def test_get_data_sources(self):
        """測試獲取資料來源列表"""
        print("\n📊 測試獲取資料來源列表...")

        response = self.session.get(f"{self.base_url}/api/v1/data/sources")

        if response.status_code == 200:
            data = response.json()
            print("✅ 獲取資料來源列表成功")
            print(f"   資料來源數量: {len(data['data'])}")
            for source in data["data"]:
                print(f"   - {source['name']} ({source['type']}) - {source['status']}")
            return True
        else:
            print(f"❌ 獲取資料來源列表失敗: {response.text}")
            return False

    def test_create_data_source(self):
        """測試創建資料來源"""
        print("\n➕ 測試創建資料來源...")

        source_config = {
            "name": "測試資料來源",
            "type": "csv",
            "config": {
                "file_path": "/data/test.csv",
                "delimiter": ",",
                "encoding": "utf-8",
            },
            "enabled": True,
            "update_frequency": "daily",
        }

        response = self.session.post(
            f"{self.base_url}/api/v1/data/sources", json=source_config
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 創建資料來源成功")
            print(f"   資料來源 ID: {data['data']['id']}")
            print(f"   資料來源名稱: {data['data']['name']}")
            return data["data"]["id"]
        else:
            print(f"❌ 創建資料來源失敗: {response.text}")
            return None

    def test_get_data_source_detail(self, source_id):
        """測試獲取資料來源詳情"""
        print(f"\n🔍 測試獲取資料來源詳情 (ID: {source_id})...")

        response = self.session.get(f"{self.base_url}/api/v1/data/sources/{source_id}")

        if response.status_code == 200:
            data = response.json()
            print("✅ 獲取資料來源詳情成功")
            print(f"   名稱: {data['data']['name']}")
            print(f"   類型: {data['data']['type']}")
            print(f"   狀態: {data['data']['status']}")
            return True
        else:
            print(f"❌ 獲取資料來源詳情失敗: {response.text}")
            return False

    def test_update_data(self):
        """測試資料更新"""
        print("\n🔄 測試資料更新...")

        update_request = {
            "source_names": ["Yahoo Finance"],
            "symbols": ["AAPL", "TSLA"],
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-12-31T23:59:59",
            "force_update": False,
        }

        response = self.session.post(
            f"{self.base_url}/api/v1/data/update", json=update_request
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 資料更新任務啟動成功")
            print(f"   任務 ID: {data['data']['task_id']}")
            print(f"   預估時間: {data['data']['estimated_duration']}")
            return True
        else:
            print(f"❌ 資料更新任務啟動失敗: {response.text}")
            return False

    def test_get_quality_report(self):
        """測試獲取資料品質報告"""
        print("\n📋 測試獲取資料品質報告...")

        params = {
            "symbols": "AAPL,TSLA,MSFT",
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-12-31T23:59:59",
        }

        response = self.session.get(
            f"{self.base_url}/api/v1/data/quality-report", params=params
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 獲取資料品質報告成功")
            print(f"   報告數量: {len(data['data'])}")
            for report in data["data"]:
                print(f"   - {report['symbol']}: 品質評分 {report['quality_score']}")
            return True
        else:
            print(f"❌ 獲取資料品質報告失敗: {response.text}")
            return False

    def test_clean_data(self):
        """測試資料清理"""
        print("\n🧹 測試資料清理...")

        cleaning_request = {
            "symbols": ["AAPL", "TSLA"],
            "cleaning_rules": [
                "remove_duplicates",
                "fill_missing_values",
                "remove_outliers",
            ],
            "start_date": "2024-01-01T00:00:00",
            "end_date": "2024-12-31T23:59:59",
        }

        response = self.session.post(
            f"{self.base_url}/api/v1/data/clean", json=cleaning_request
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 資料清理任務啟動成功")
            print(f"   任務 ID: {data['data']['task_id']}")
            print(f"   預估時間: {data['data']['estimated_duration']}")
            return True
        else:
            print(f"❌ 資料清理任務啟動失敗: {response.text}")
            return False

    def run_all_tests(self):
        """運行所有測試"""
        print("🚀 開始資料管理 API 測試")
        print("=" * 50)

        # 登入
        if not self.login():
            return False

        # 測試各個功能
        tests = [
            self.test_get_data_sources,
            self.test_create_data_source,
            self.test_update_data,
            self.test_get_quality_report,
            self.test_clean_data,
        ]

        passed = 0
        total = len(tests)
        source_id = None

        for i, test in enumerate(tests):
            try:
                if test == self.test_create_data_source:
                    result = test()
                    if result:
                        source_id = result
                        passed += 1
                        # 測試獲取詳情
                        if self.test_get_data_source_detail(source_id):
                            passed += 1
                        total += 1
                else:
                    if test():
                        passed += 1
            except Exception as e:
                print(f"❌ 測試 {test.__name__} 發生異常: {e}")

        print("\n" + "=" * 50)
        print(f"📊 測試結果: {passed}/{total} 通過")

        if passed == total:
            print("🎉 所有資料管理 API 測試通過！")
            return True
        else:
            print("⚠️ 部分測試失敗，請檢查 API 實現")
            return False


def main():
    """主函數"""
    tester = DataManagementAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
