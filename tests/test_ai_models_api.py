#!/usr/bin/env python3
"""
AI 模型管理 API 測試腳本

測試 AI 模型管理相關的 API 端點功能。
"""

import requests
import json
import io
from datetime import datetime


class AIModelsAPITester:
    """AI 模型管理 API 測試器"""

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

    def test_get_models(self):
        """測試獲取 AI 模型列表"""
        print("\n🤖 測試獲取 AI 模型列表...")

        response = self.session.get(f"{self.base_url}/api/v1/models/")

        if response.status_code == 200:
            data = response.json()
            print("✅ 獲取 AI 模型列表成功")
            print(f"   模型數量: {len(data['data'])}")
            for model in data["data"]:
                print(
                    f"   - {model['name']} ({model['framework']}) - {model['status']}"
                )
            return True
        else:
            print(f"❌ 獲取 AI 模型列表失敗: {response.text}")
            return False

    def test_upload_model(self):
        """測試上傳 AI 模型"""
        print("\n📤 測試上傳 AI 模型...")

        # 創建模擬模型文件
        model_content = b"mock model data for testing"
        model_file = io.BytesIO(model_content)

        # 準備上傳參數
        files = {"file": ("test_model.pkl", model_file, "application/octet-stream")}

        params = {
            "name": "測試分類模型",
            "description": "用於測試的分類模型",
            "model_type": "classification",
            "framework": "sklearn",
            "version": "1.0.0",
            "tags": "test,classification,sklearn",
        }

        # 暫時移除 Content-Type header 以支援文件上傳
        headers = {"Authorization": f"Bearer {self.token}"}

        response = requests.post(
            f"{self.base_url}/api/v1/models/upload",
            files=files,
            params=params,
            headers=headers,
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 上傳 AI 模型成功")
            print(f"   模型 ID: {data['data']['id']}")
            print(f"   模型名稱: {data['data']['name']}")
            return data["data"]["id"]
        else:
            print(f"❌ 上傳 AI 模型失敗: {response.text}")
            return None

    def test_get_model_detail(self, model_id):
        """測試獲取模型詳情"""
        print(f"\n🔍 測試獲取模型詳情 (ID: {model_id})...")

        response = self.session.get(f"{self.base_url}/api/v1/models/{model_id}")

        if response.status_code == 200:
            data = response.json()
            print("✅ 獲取模型詳情成功")
            print(f"   名稱: {data['data']['name']}")
            print(f"   類型: {data['data']['model_type']}")
            print(f"   框架: {data['data']['framework']}")
            print(f"   狀態: {data['data']['status']}")
            return True
        else:
            print(f"❌ 獲取模型詳情失敗: {response.text}")
            return False

    def test_model_training(self, model_id):
        """測試模型訓練"""
        print(f"\n🏋️ 測試模型訓練 (模型 ID: {model_id})...")

        training_request = {
            "dataset_id": "dataset_001",
            "hyperparameters": {
                "learning_rate": 0.001,
                "batch_size": 32,
                "hidden_units": 128,
            },
            "validation_split": 0.2,
            "epochs": 50,
            "early_stopping": True,
        }

        response = self.session.post(
            f"{self.base_url}/api/v1/models/{model_id}/train", json=training_request
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 模型訓練任務啟動成功")
            print(f"   任務 ID: {data['data']['task_id']}")
            print(f"   總輪數: {data['data']['total_epochs']}")
            return True
        else:
            print(f"❌ 模型訓練任務啟動失敗: {response.text}")
            return False

    def test_model_prediction(self, model_id):
        """測試模型推理"""
        print(f"\n🔮 測試模型推理 (模型 ID: {model_id})...")

        prediction_request = {
            "input_data": [
                [1.2, 3.4, 5.6, 7.8],
                [2.1, 4.3, 6.5, 8.7],
                [3.0, 5.2, 7.4, 9.6],
            ],
            "return_probabilities": True,
            "explain": True,
        }

        response = self.session.post(
            f"{self.base_url}/api/v1/models/{model_id}/predict", json=prediction_request
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 模型推理成功")
            print(f"   預測結果數量: {len(data['data']['predictions'])}")
            print(f"   推理時間: {data['data']['inference_time']:.4f} 秒")
            print(f"   模型版本: {data['data']['model_version']}")
            return True
        elif response.status_code == 400:
            print("⚠️ 模型尚未準備就緒，跳過推理測試")
            return True  # 這是正確的業務邏輯，不算失敗
        else:
            print(f"❌ 模型推理失敗: {response.text}")
            return False

    def test_model_versions(self, model_id):
        """測試獲取模型版本"""
        print(f"\n📋 測試獲取模型版本 (模型 ID: {model_id})...")

        response = self.session.get(
            f"{self.base_url}/api/v1/models/{model_id}/versions"
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 獲取模型版本成功")
            print(f"   版本數量: {len(data['data'])}")
            for version in data["data"]:
                print(f"   - v{version['version']} ({version['status']})")
            return True
        else:
            print(f"❌ 獲取模型版本失敗: {response.text}")
            return False

    def test_model_metrics(self, model_id):
        """測試獲取模型效能指標"""
        print(f"\n📊 測試獲取模型效能指標 (模型 ID: {model_id})...")

        response = self.session.get(f"{self.base_url}/api/v1/models/{model_id}/metrics")

        if response.status_code == 200:
            data = response.json()
            print("✅ 獲取模型效能指標成功")
            print(f"   當前版本: {data['data']['current_version']}")
            if data["data"]["metrics"]:
                print(f"   效能指標: {data['data']['metrics']}")
            return True
        else:
            print(f"❌ 獲取模型效能指標失敗: {response.text}")
            return False

    def test_model_download(self, model_id):
        """測試模型下載"""
        print(f"\n📥 測試模型下載 (模型 ID: {model_id})...")

        response = self.session.get(
            f"{self.base_url}/api/v1/models/{model_id}/download"
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 模型下載連結生成成功")
            print(f"   下載 URL: {data['data']['download_url']}")
            print(f"   文件大小: {data['data']['file_size']} bytes")
            return True
        elif response.status_code == 400:
            print("⚠️ 模型尚未準備就緒，跳過下載測試")
            return True  # 這是正確的業務邏輯，不算失敗
        else:
            print(f"❌ 模型下載失敗: {response.text}")
            return False

    def test_filtered_models(self):
        """測試篩選模型"""
        print("\n🔍 測試篩選模型...")

        # 測試按框架篩選
        params = {"framework": "tensorflow", "status": "ready"}

        response = self.session.get(f"{self.base_url}/api/v1/models/", params=params)

        if response.status_code == 200:
            data = response.json()
            print("✅ 篩選模型成功")
            print(f"   TensorFlow 模型數量: {len(data['data'])}")
            return True
        else:
            print(f"❌ 篩選模型失敗: {response.text}")
            return False

    def test_ready_model_prediction(self):
        """測試已準備就緒模型的推理功能"""
        print("\n🔮 測試已準備就緒模型的推理功能...")

        # 使用預設的已準備就緒模型 (model_001)
        model_id = "model_001"

        prediction_request = {
            "input_data": [[1.2, 3.4, 5.6, 7.8], [2.1, 4.3, 6.5, 8.7]],
            "return_probabilities": True,
            "explain": True,
        }

        response = self.session.post(
            f"{self.base_url}/api/v1/models/{model_id}/predict", json=prediction_request
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 已準備模型推理成功")
            print(f"   預測結果數量: {len(data['data']['predictions'])}")
            print(f"   推理時間: {data['data']['inference_time']:.4f} 秒")
            if data["data"]["probabilities"]:
                print(f"   包含概率預測: ✓")
            if data["data"]["explanations"]:
                print(f"   包含解釋分析: ✓")
            return True
        else:
            print(f"❌ 已準備模型推理失敗: {response.text}")
            return False

    def test_ready_model_download(self):
        """測試已準備就緒模型的下載功能"""
        print("\n📥 測試已準備就緒模型的下載功能...")

        # 使用預設的已準備就緒模型 (model_002)
        model_id = "model_002"

        response = self.session.get(
            f"{self.base_url}/api/v1/models/{model_id}/download"
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ 已準備模型下載連結生成成功")
            print(f"   下載 URL: {data['data']['download_url']}")
            print(f"   文件名: {data['data']['filename']}")
            return True
        else:
            print(f"❌ 已準備模型下載失敗: {response.text}")
            return False

    def run_all_tests(self):
        """運行所有測試"""
        print("🚀 開始 AI 模型管理 API 測試")
        print("=" * 50)

        # 登入
        if not self.login():
            return False

        # 測試各個功能
        tests = [
            self.test_get_models,
            self.test_upload_model,
            self.test_filtered_models,
            self.test_ready_model_prediction,
            self.test_ready_model_download,
        ]

        passed = 0
        total = len(tests)
        model_id = None

        for test in tests:
            try:
                if test == self.test_upload_model:
                    result = test()
                    if result:
                        model_id = result
                        passed += 1
                        # 測試其他模型相關功能
                        additional_tests = [
                            self.test_get_model_detail,
                            self.test_model_training,
                            self.test_model_prediction,
                            self.test_model_versions,
                            self.test_model_metrics,
                            self.test_model_download,
                        ]
                        for additional_test in additional_tests:
                            if additional_test(model_id):
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
            print("🎉 所有 AI 模型管理 API 測試通過！")
            return True
        else:
            print("⚠️ 部分測試失敗，請檢查 API 實現")
            return False


def main():
    """主函數"""
    tester = AIModelsAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
