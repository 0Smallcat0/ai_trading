#!/usr/bin/env python3
"""
策略管理 API 測試腳本

測試策略管理相關的 API 端點功能。
"""

import requests
import json
from datetime import datetime, timedelta


class StrategyManagementAPITester:
    """策略管理 API 測試器"""

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

    def test_get_strategies(self):
        """測試獲取策略列表"""
        print("\n🎯 測試獲取策略列表...")

        response = self.session.get(f"{self.base_url}/api/v1/strategies/")

        if response.status_code == 200:
            data = response.json()
            print("✅ 獲取策略列表成功")
            print(f"   策略數量: {len(data['data'])}")
            for strategy in data["data"]:
                print(
                    f"   - {strategy['name']} ({strategy['type']}) - {strategy['status']}"
                )
            return True
        else:
            print(f"❌ 獲取策略列表失敗: {response.text}")
            return False

    def test_get_strategy_types(self):
        """測試獲取策略類型"""
        print("\n📋 測試獲取策略類型...")

        response = self.session.get(
            f"{self.base_url}/api/v1/strategies/types/available"
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 獲取策略類型成功")
            print(f"   類型數量: {len(data['data'])}")
            for strategy_type in data["data"]:
                print(f"   - {strategy_type['name']} ({strategy_type['type']})")
            return True
        else:
            print(f"❌ 獲取策略類型失敗: {response.text}")
            return False

    def test_create_strategy(self):
        """測試創建策略"""
        print("\n➕ 測試創建策略...")

        strategy_config = {
            "name": "測試動量策略",
            "description": "基於價格動量的測試策略",
            "type": "momentum",
            "parameters": {
                "lookback_period": 20,
                "momentum_threshold": 0.02,
                "position_size": 0.1,
                "stop_loss": 0.05,
            },
            "enabled": True,
            "risk_level": "medium",
        }

        response = self.session.post(
            f"{self.base_url}/api/v1/strategies/", json=strategy_config
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 創建策略成功")
            print(f"   策略 ID: {data['data']['id']}")
            print(f"   策略名稱: {data['data']['name']}")
            return data["data"]["id"]
        else:
            print(f"❌ 創建策略失敗: {response.text}")
            return None

    def test_get_strategy_detail(self, strategy_id):
        """測試獲取策略詳情"""
        print(f"\n🔍 測試獲取策略詳情 (ID: {strategy_id})...")

        response = self.session.get(f"{self.base_url}/api/v1/strategies/{strategy_id}")

        if response.status_code == 200:
            data = response.json()
            print("✅ 獲取策略詳情成功")
            print(f"   名稱: {data['data']['name']}")
            print(f"   類型: {data['data']['type']}")
            print(f"   狀態: {data['data']['status']}")
            print(f"   風險等級: {data['data']['risk_level']}")
            return True
        else:
            print(f"❌ 獲取策略詳情失敗: {response.text}")
            return False

    def test_update_strategy(self, strategy_id):
        """測試更新策略"""
        print(f"\n✏️ 測試更新策略 (ID: {strategy_id})...")

        update_data = {
            "description": "更新後的策略描述",
            "parameters": {
                "lookback_period": 25,
                "momentum_threshold": 0.025,
                "position_size": 0.15,
                "stop_loss": 0.04,
            },
            "risk_level": "high",
        }

        response = self.session.put(
            f"{self.base_url}/api/v1/strategies/{strategy_id}", json=update_data
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 更新策略成功")
            print(f"   新描述: {data['data']['description']}")
            print(f"   新風險等級: {data['data']['risk_level']}")
            return True
        else:
            print(f"❌ 更新策略失敗: {response.text}")
            return False

    def test_start_backtest(self, strategy_id):
        """測試啟動回測"""
        print(f"\n📈 測試啟動回測 (策略 ID: {strategy_id})...")

        # 設定回測時間範圍（過去一年）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        backtest_request = {
            "strategy_id": strategy_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "initial_capital": 100000.0,
            "symbols": ["AAPL", "TSLA", "MSFT"],
            "benchmark": "SPY",
        }

        response = self.session.post(
            f"{self.base_url}/api/v1/strategies/{strategy_id}/backtest",
            json=backtest_request,
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 回測任務啟動成功")
            print(f"   任務 ID: {data['data']['task_id']}")
            print(f"   預估時間: {data['data']['estimated_duration']}")
            return True
        else:
            print(f"❌ 回測任務啟動失敗: {response.text}")
            return False

    def test_filtered_strategies(self):
        """測試篩選策略"""
        print("\n🔍 測試篩選策略...")

        # 測試按類型篩選
        params = {"strategy_type": "trend_following", "enabled_only": True}

        response = self.session.get(
            f"{self.base_url}/api/v1/strategies/", params=params
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 篩選策略成功")
            print(f"   趨勢跟隨策略數量: {len(data['data'])}")
            return True
        else:
            print(f"❌ 篩選策略失敗: {response.text}")
            return False

    def run_all_tests(self):
        """運行所有測試"""
        print("🚀 開始策略管理 API 測試")
        print("=" * 50)

        # 登入
        if not self.login():
            return False

        # 測試各個功能
        tests = [
            self.test_get_strategies,
            self.test_get_strategy_types,
            self.test_create_strategy,
            self.test_filtered_strategies,
        ]

        passed = 0
        total = len(tests)
        strategy_id = None

        for test in tests:
            try:
                if test == self.test_create_strategy:
                    result = test()
                    if result:
                        strategy_id = result
                        passed += 1
                        # 測試獲取詳情、更新和回測
                        if self.test_get_strategy_detail(strategy_id):
                            passed += 1
                        if self.test_update_strategy(strategy_id):
                            passed += 1
                        if self.test_start_backtest(strategy_id):
                            passed += 1
                        total += 3
                else:
                    if test():
                        passed += 1
            except Exception as e:
                print(f"❌ 測試 {test.__name__} 發生異常: {e}")

        print("\n" + "=" * 50)
        print(f"📊 測試結果: {passed}/{total} 通過")

        if passed == total:
            print("🎉 所有策略管理 API 測試通過！")
            return True
        else:
            print("⚠️ 部分測試失敗，請檢查 API 實現")
            return False


def main():
    """主函數"""
    tester = StrategyManagementAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
