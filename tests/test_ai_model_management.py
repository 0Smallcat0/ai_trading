"""
AI 模型管理模組測試

此測試模組驗證 AI 模型管理的核心功能，包括：
- 模型創建和管理
- 模型訓練功能
- 模型推論功能
- 模型解釋性分析
- 模型上傳和下載
"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np

# 導入被測試的模組
import sys

sys.path.append(str(Path(__file__).parent.parent))

from src.core.ai_model_management_service import AIModelManagementService


class TestAIModelManagementService:
    """AI 模型管理服務測試類"""

    @pytest.fixture
    def temp_db_path(self):
        """創建臨時資料庫路徑"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        # 清理
        if os.path.exists(f.name):
            os.unlink(f.name)

    @pytest.fixture
    def service(self, temp_db_path):
        """創建 AI 模型管理服務實例"""
        return AIModelManagementService(db_path=temp_db_path)

    def test_service_initialization(self, service):
        """測試服務初始化"""
        assert service is not None
        assert hasattr(service, "db_path")
        assert hasattr(service, "models_dir")

    def test_get_model_types(self, service):
        """測試獲取模型類型"""
        model_types = service.get_model_types()

        assert isinstance(model_types, dict)
        assert "機器學習模型" in model_types
        assert "深度學習模型" in model_types
        assert "規則型模型" in model_types
        assert "集成模型" in model_types

        # 檢查每個類型都有子類型
        for model_type, sub_types in model_types.items():
            assert isinstance(sub_types, list)
            assert len(sub_types) > 0

    def test_create_model(self, service):
        """測試創建模型"""
        model_id = service.create_model(
            name="測試模型",
            model_type="機器學習模型",
            sub_type="隨機森林 (Random Forest)",
            description="這是一個測試模型",
            author="測試用戶",
            parameters={"n_estimators": 100, "max_depth": 10},
            features=["close", "volume", "rsi"],
            target="direction",
        )

        assert model_id is not None
        assert isinstance(model_id, str)

        # 驗證模型是否正確創建
        models = service.get_models()
        created_model = next((m for m in models if m["id"] == model_id), None)

        assert created_model is not None
        assert created_model["name"] == "測試模型"
        assert created_model["type"] == "機器學習模型"
        assert created_model["sub_type"] == "隨機森林 (Random Forest)"
        assert created_model["status"] == "created"

    def test_get_models(self, service):
        """測試獲取模型列表"""
        # 創建幾個測試模型
        model_ids = []
        for i in range(3):
            model_id = service.create_model(
                name=f"測試模型_{i}",
                model_type="機器學習模型",
                sub_type="XGBoost",
                description=f"測試模型 {i}",
                author="測試用戶",
            )
            model_ids.append(model_id)

        # 獲取模型列表
        models = service.get_models()

        assert isinstance(models, list)
        assert len(models) >= 3

        # 驗證創建的模型都在列表中
        model_names = [m["name"] for m in models]
        for i in range(3):
            assert f"測試模型_{i}" in model_names

    def test_get_model_by_id(self, service):
        """測試根據ID獲取模型"""
        # 創建測試模型
        model_id = service.create_model(
            name="ID測試模型",
            model_type="深度學習模型",
            sub_type="LSTM (Long Short-Term Memory)",
            description="用於測試ID查詢的模型",
        )

        # 根據ID獲取模型
        model = service.get_model_by_id(model_id)

        assert model is not None
        assert model["id"] == model_id
        assert model["name"] == "ID測試模型"
        assert model["type"] == "深度學習模型"

    def test_update_model_status(self, service):
        """測試更新模型狀態"""
        # 創建測試模型
        model_id = service.create_model(
            name="狀態測試模型",
            model_type="機器學習模型",
            sub_type="SVM (Support Vector Machine)",
        )

        # 更新狀態為訓練中
        service.update_model_status(model_id, "training")

        # 驗證狀態更新
        model = service.get_model_by_id(model_id)
        assert model["status"] == "training"

        # 更新狀態為已訓練
        service.update_model_status(model_id, "trained")

        # 再次驗證
        model = service.get_model_by_id(model_id)
        assert model["status"] == "trained"

    def test_start_training(self, service):
        """測試啟動模型訓練"""
        # 創建測試模型
        model_id = service.create_model(
            name="訓練測試模型",
            model_type="機器學習模型",
            sub_type="隨機森林 (Random Forest)",
        )

        # 準備訓練數據
        training_data = {
            "stocks": ["AAPL"],
            "date_range": ["2023-01-01", "2023-12-31"],
            "features": ["close", "volume", "rsi"],
            "target": "direction",
            "train_ratio": 0.8,
            "val_ratio": 0.15,
        }

        training_params = {"n_estimators": 100, "max_depth": 10, "random_state": 42}

        # 啟動訓練
        training_id = service.start_training(
            model_id=model_id,
            training_data=training_data,
            training_params=training_params,
        )

        assert training_id is not None
        assert isinstance(training_id, str)

        # 驗證模型狀態已更新為訓練中
        model = service.get_model_by_id(model_id)
        assert model["status"] == "training"

    def test_run_inference(self, service):
        """測試模型推論"""
        # 創建並設置為已訓練狀態的模型
        model_id = service.create_model(
            name="推論測試模型",
            model_type="機器學習模型",
            sub_type="隨機森林 (Random Forest)",
            features=["close", "volume", "rsi", "macd"],
        )

        # 設置為已訓練狀態
        service.update_model_status(model_id, "trained")

        # 準備推論數據
        input_data = {"close": 150.0, "volume": 1000000, "rsi": 65.0, "macd": 0.5}

        # 執行推論
        result = service.run_inference(
            model_id=model_id,
            input_data=input_data,
            return_probabilities=True,
            return_confidence=True,
        )

        assert result is not None
        assert isinstance(result, dict)
        assert "prediction" in result
        assert "confidence" in result

        # 驗證返回值類型
        assert isinstance(result["prediction"], (int, float))
        assert isinstance(result["confidence"], float)
        assert 0 <= result["confidence"] <= 1

    def test_explain_prediction(self, service):
        """測試預測解釋"""
        # 創建測試模型
        model_id = service.create_model(
            name="解釋測試模型",
            model_type="機器學習模型",
            sub_type="隨機森林 (Random Forest)",
            features=["close", "volume", "rsi"],
        )

        # 設置為已訓練狀態
        service.update_model_status(model_id, "trained")

        # 準備解釋數據
        input_data = {
            "close": [150.0, 155.0, 160.0],
            "volume": [1000000, 1200000, 800000],
            "rsi": [65.0, 70.0, 45.0],
        }

        # 執行解釋
        explanation = service.explain_prediction(
            model_id=model_id, input_data=input_data, method="特徵重要性"
        )

        assert explanation is not None
        assert isinstance(explanation, dict)

        # 驗證解釋結果包含必要的字段
        if "error" not in explanation:
            assert (
                "feature_importance" in explanation
                or "local_explanation" in explanation
            )

    def test_upload_model(self, service):
        """測試模型上傳"""
        # 創建模擬模型檔案
        model_data = b"fake_model_data_for_testing"

        # 上傳模型
        model_id = service.upload_model(
            model_file=model_data,
            model_name="上傳測試模型",
            model_type="機器學習模型",
            sub_type="XGBoost",
            description="通過上傳創建的測試模型",
            author="測試用戶",
            parameters={"learning_rate": 0.1},
            features=["close", "volume"],
            target="price",
        )

        assert model_id is not None
        assert isinstance(model_id, str)

        # 驗證模型記錄
        model = service.get_model_by_id(model_id)
        assert model is not None
        assert model["name"] == "上傳測試模型"
        assert model["type"] == "機器學習模型"

        # 驗證模型檔案是否保存
        model_dir = service.models_dir / model_id
        assert model_dir.exists()

    def test_download_model(self, service):
        """測試模型下載"""
        # 先上傳一個模型
        model_data = b"test_model_content_for_download"
        model_id = service.upload_model(
            model_file=model_data,
            model_name="下載測試模型",
            model_type="機器學習模型",
            sub_type="LightGBM",
        )

        # 下載模型
        downloaded_data = service.download_model(model_id)

        assert downloaded_data is not None
        assert isinstance(downloaded_data, bytes)
        assert downloaded_data == model_data

    def test_delete_model(self, service):
        """測試刪除模型"""
        # 創建測試模型
        model_id = service.create_model(
            name="刪除測試模型",
            model_type="機器學習模型",
            sub_type="決策樹 (Decision Tree)",
        )

        # 驗證模型存在
        model = service.get_model_by_id(model_id)
        assert model is not None

        # 刪除模型
        success = service.delete_model(model_id)
        assert success is True

        # 驗證模型已被刪除
        model = service.get_model_by_id(model_id)
        assert model is None

    def test_get_training_logs(self, service):
        """測試獲取訓練日誌"""
        # 創建測試模型並啟動訓練
        model_id = service.create_model(
            name="日誌測試模型",
            model_type="機器學習模型",
            sub_type="隨機森林 (Random Forest)",
        )

        training_data = {
            "stocks": ["AAPL"],
            "features": ["close", "volume"],
            "target": "direction",
        }

        training_id = service.start_training(
            model_id=model_id, training_data=training_data
        )

        # 獲取訓練日誌
        logs = service.get_training_logs(model_id)

        assert isinstance(logs, list)
        # 至少應該有一條啟動訓練的日誌
        assert len(logs) >= 1

        # 驗證日誌格式
        if logs:
            log = logs[0]
            assert "model_id" in log
            assert "training_id" in log
            assert "status" in log
            assert log["model_id"] == model_id


if __name__ == "__main__":
    # 運行測試
    pytest.main([__file__, "-v"])
