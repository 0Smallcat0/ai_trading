# -*- coding: utf-8 -*-
"""
模型治理模組測試

此模組測試模型治理功能，包括：
- 模型註冊表測試
- 模型監控器測試
- 部署管理器測試
- 生命週期管理器測試
- 向後兼容性測試
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock

from src.models.model_governance import ModelRegistry, ModelMonitor
from src.models.model_governance.registry import ModelRegistry as NewModelRegistry
from src.models.model_governance.monitor import ModelMonitor as NewModelMonitor
from src.models.model_governance.deployment import DeploymentManager
from src.models.model_governance.lifecycle import ModelLifecycleManager, ModelStatus
from src.models.model_governance.utils import (
    validate_model_metadata,
    create_model_signature,
    calculate_model_drift,
)


class TestModelRegistryNew:
    """測試新的模型註冊表"""

    @pytest.fixture
    def temp_registry_path(self):
        """創建臨時註冊表路徑"""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            yield f.name
        # 清理
        if os.path.exists(f.name):
            os.unlink(f.name)

    @pytest.fixture
    def mock_model(self):
        """創建模擬模型"""
        model = Mock()
        model.trained = True
        model.name = "test_model"
        model.model_params = {"n_estimators": 100}
        model.feature_names = ["feature1", "feature2"]
        model.target_name = "target"
        model.metrics = {"accuracy": 0.95}
        model.__class__.__name__ = "TestModel"
        model.save = Mock()
        return model

    def test_registry_initialization(self, temp_registry_path):
        """測試註冊表初始化"""
        registry = NewModelRegistry(temp_registry_path)

        assert registry.registry_path == temp_registry_path
        assert "models" in registry.registry
        assert "deployments" in registry.registry
        assert "metadata" in registry.registry

    def test_register_model(self, temp_registry_path, mock_model):
        """測試模型註冊"""
        registry = NewModelRegistry(temp_registry_path)

        with patch("os.makedirs"), patch.object(mock_model, "save"):
            version = registry.register_model(
                model=mock_model, description="Test model", metrics={"accuracy": 0.95}
            )

        assert version is not None
        assert mock_model.name in registry.registry["models"]
        assert version in registry.registry["models"][mock_model.name]

    def test_register_untrained_model(self, temp_registry_path):
        """測試註冊未訓練模型"""
        registry = NewModelRegistry(temp_registry_path)

        untrained_model = Mock()
        untrained_model.trained = False

        with pytest.raises(ValueError, match="模型尚未訓練"):
            registry.register_model(untrained_model)

    def test_get_model_info(self, temp_registry_path, mock_model):
        """測試獲取模型資訊"""
        registry = NewModelRegistry(temp_registry_path)

        with patch("os.makedirs"), patch.object(mock_model, "save"):
            version = registry.register_model(mock_model)

        model_info = registry.get_model_info(mock_model.name, version)

        assert model_info["name"] == mock_model.name
        assert model_info["version"] == version
        assert model_info["model_type"] == "TestModel"

    def test_get_nonexistent_model(self, temp_registry_path):
        """測試獲取不存在的模型"""
        registry = NewModelRegistry(temp_registry_path)

        with pytest.raises(ValueError, match="模型不存在"):
            registry.get_model_info("nonexistent_model")

    def test_list_models(self, temp_registry_path, mock_model):
        """測試列出模型"""
        registry = NewModelRegistry(temp_registry_path)

        with patch("os.makedirs"), patch.object(mock_model, "save"):
            registry.register_model(mock_model)

        models = registry.list_models()
        assert mock_model.name in models

    def test_list_versions(self, temp_registry_path, mock_model):
        """測試列出版本"""
        registry = NewModelRegistry(temp_registry_path)

        with patch("os.makedirs"), patch.object(mock_model, "save"):
            version1 = registry.register_model(mock_model, version="v1.0")
            version2 = registry.register_model(mock_model, version="v2.0")

        versions = registry.list_versions(mock_model.name)
        assert "v1.0" in versions
        assert "v2.0" in versions


class TestModelMonitorNew:
    """測試新的模型監控器"""

    @pytest.fixture
    def mock_registry(self):
        """創建模擬註冊表"""
        registry = Mock()
        registry.get_model_info.return_value = {
            "version": "v1.0",
            "model_type": "TestModel",
            "feature_names": ["f1", "f2"],
            "target_name": "target",
            "metrics": {"accuracy": 0.95},
            "created_at": "2024-01-01T00:00:00",
            "run_id": "test_run_id",
        }

        mock_model = Mock()
        mock_model.is_classifier = True
        registry.load_model.return_value = mock_model

        return registry

    def test_monitor_initialization(self, mock_registry):
        """測試監控器初始化"""
        monitor = NewModelMonitor("test_model", "v1.0", mock_registry)

        assert monitor.model_name == "test_model"
        assert monitor.version == "v1.0"
        assert monitor.registry == mock_registry

    def test_log_prediction(self, mock_registry):
        """測試記錄預測"""
        monitor = NewModelMonitor("test_model", "v1.0", mock_registry)

        features = pd.Series({"f1": 1.0, "f2": 2.0})
        prediction = 0.8
        actual = 1.0

        with patch("mlflow.start_run"), patch("mlflow.log_metric"):
            monitor.log_prediction(features, prediction, actual)

        assert len(monitor.monitoring_data) == 1
        assert monitor.monitoring_data[0]["prediction"] == prediction
        assert monitor.monitoring_data[0]["actual"] == actual

    def test_calculate_classification_metrics(self, mock_registry):
        """測試計算分類指標"""
        monitor = NewModelMonitor("test_model", "v1.0", mock_registry)

        # 添加一些監控資料
        monitor.monitoring_data = [
            {"prediction": 1, "actual": 1},
            {"prediction": 0, "actual": 1},
            {"prediction": 1, "actual": 0},
            {"prediction": 0, "actual": 0},
        ]

        with patch("sklearn.metrics.accuracy_score", return_value=0.75), patch(
            "sklearn.metrics.precision_score", return_value=0.5
        ), patch("sklearn.metrics.recall_score", return_value=0.5), patch(
            "sklearn.metrics.f1_score", return_value=0.5
        ):

            metrics = monitor.calculate_metrics()

        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics

    def test_calculate_regression_metrics(self, mock_registry):
        """測試計算回歸指標"""
        # 修改模型為回歸模型
        mock_registry.load_model.return_value.is_classifier = False

        monitor = NewModelMonitor("test_model", "v1.0", mock_registry)

        # 添加一些監控資料
        monitor.monitoring_data = [
            {"prediction": 1.0, "actual": 1.1},
            {"prediction": 2.0, "actual": 1.9},
            {"prediction": 3.0, "actual": 3.2},
        ]

        metrics = monitor.calculate_metrics()

        assert "mse" in metrics
        assert "rmse" in metrics
        assert "mae" in metrics
        assert "r2" in metrics

    def test_detect_drift(self, mock_registry):
        """測試漂移檢測"""
        monitor = NewModelMonitor("test_model", "v1.0", mock_registry)

        # 設定基準資料
        baseline_features = pd.DataFrame(
            {"f1": np.random.normal(0, 1, 100), "f2": np.random.normal(0, 1, 100)}
        )
        monitor.set_baseline(baseline_features)

        # 新資料（有漂移）
        new_features = pd.DataFrame(
            {
                "f1": np.random.normal(1, 1, 50),  # 均值漂移
                "f2": np.random.normal(0, 1, 50),
            }
        )

        drift_result = monitor.detect_drift(new_features)

        assert "drift_detected" in drift_result
        assert "method" in drift_result
        assert "feature_results" in drift_result


class TestDeploymentManager:
    """測試部署管理器"""

    @pytest.fixture
    def mock_registry(self):
        """創建模擬註冊表"""
        registry = Mock()
        registry.registry = {"deployments": {}}
        registry.get_model_info.return_value = {
            "version": "v1.0",
            "model_type": "TestModel",
            "feature_names": ["f1", "f2"],
            "metrics": {"accuracy": 0.95},
        }
        registry._save_registry = Mock()
        return registry

    def test_deploy_model(self, mock_registry):
        """測試部署模型"""
        deployment_manager = DeploymentManager(mock_registry)

        deployment_info = deployment_manager.deploy_model(
            "test_model", "v1.0", "production", "Production deployment"
        )

        assert deployment_info["model_name"] == "test_model"
        assert deployment_info["version"] == "v1.0"
        assert deployment_info["environment"] == "production"
        assert deployment_info["status"] == "active"

    def test_get_deployment_info(self, mock_registry):
        """測試獲取部署資訊"""
        deployment_manager = DeploymentManager(mock_registry)

        # 先部署模型
        deployment_manager.deploy_model("test_model", "v1.0", "production")

        # 獲取部署資訊
        deployment_info = deployment_manager.get_deployment_info(
            "test_model", "production"
        )

        assert deployment_info is not None
        assert deployment_info["model_name"] == "test_model"

    def test_rollback_deployment(self, mock_registry):
        """測試回滾部署"""
        deployment_manager = DeploymentManager(mock_registry)

        # 部署第一個版本
        deployment_manager.deploy_model("test_model", "v1.0", "production")

        # 部署第二個版本
        deployment_manager.deploy_model("test_model", "v2.0", "production")

        # 回滾到第一個版本
        rollback_info = deployment_manager.rollback_deployment(
            "test_model", "production"
        )

        assert rollback_info["version"] == "v1.0"


class TestModelLifecycleManager:
    """測試模型生命週期管理器"""

    @pytest.fixture
    def mock_registry(self):
        """創建模擬註冊表"""
        registry = Mock()
        registry.registry = {
            "models": {
                "test_model": {
                    "v1.0": {
                        "status": "registered",
                        "version": "v1.0",
                        "created_at": "2024-01-01T00:00:00",
                    }
                }
            },
            "lifecycle_events": {},
        }
        registry.get_model_info.return_value = registry.registry["models"][
            "test_model"
        ]["v1.0"]
        registry._save_registry = Mock()
        registry.list_models.return_value = ["test_model"]
        registry.list_versions.return_value = ["v1.0"]
        return registry

    def test_transition_model_status(self, mock_registry):
        """測試模型狀態轉換"""
        lifecycle_manager = ModelLifecycleManager(mock_registry)

        success = lifecycle_manager.transition_model_status(
            "test_model", "v1.0", ModelStatus.VALIDATED, "Passed validation"
        )

        assert success is True
        assert (
            mock_registry.registry["models"]["test_model"]["v1.0"]["status"]
            == "validated"
        )

    def test_invalid_status_transition(self, mock_registry):
        """測試無效的狀態轉換"""
        lifecycle_manager = ModelLifecycleManager(mock_registry)

        # 嘗試從 registered 直接轉換到 retired（無效）
        success = lifecycle_manager.transition_model_status(
            "test_model", "v1.0", ModelStatus.RETIRED
        )

        assert success is False

    def test_retire_model(self, mock_registry):
        """測試退役模型"""
        lifecycle_manager = ModelLifecycleManager(mock_registry)

        success = lifecycle_manager.retire_model("test_model", "v1.0", "Outdated model")

        # 由於狀態轉換限制，直接退役會失敗
        assert success is False

    def test_get_models_by_status(self, mock_registry):
        """測試根據狀態獲取模型"""
        lifecycle_manager = ModelLifecycleManager(mock_registry)

        models = lifecycle_manager.get_models_by_status(ModelStatus.REGISTERED)

        assert len(models) == 1
        assert models[0]["name"] == "test_model"
        assert models[0]["version"] == "v1.0"


class TestLegacyCompatibility:
    """測試向後兼容性"""

    @pytest.fixture
    def temp_registry_path(self):
        """創建臨時註冊表路徑"""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            yield f.name
        if os.path.exists(f.name):
            os.unlink(f.name)

    def test_legacy_registry_interface(self, temp_registry_path):
        """測試舊版註冊表介面"""
        with patch("src.models.model_governance.legacy_interface.warnings.warn"):
            registry = ModelRegistry(temp_registry_path)

        # 驗證委託調用
        assert hasattr(registry, "_new_registry")
        assert hasattr(registry, "_deployment_manager")
        assert hasattr(registry, "_lifecycle_manager")

    def test_legacy_monitor_interface(self):
        """測試舊版監控器介面"""
        mock_registry = Mock()
        mock_registry._new_registry = Mock()

        with patch("src.models.model_governance.legacy_interface.warnings.warn"), patch(
            "src.models.model_governance.legacy_interface.NewModelMonitor"
        ):
            monitor = ModelMonitor("test_model", "v1.0", mock_registry)

        # 驗證委託調用
        assert hasattr(monitor, "_new_monitor")


class TestUtilityFunctions:
    """測試工具函數"""

    @pytest.fixture
    def mock_model(self):
        """創建模擬模型"""
        model = Mock()
        model.name = "test_model"
        model.trained = True
        model.model = Mock()
        model.feature_names = ["f1", "f2"]
        model.target_name = "target"
        model.model_params = {"n_estimators": 100}
        model.__class__.__name__ = "TestModel"
        return model

    def test_validate_model_metadata(self, mock_model):
        """測試模型元數據驗證"""
        # 有效模型應該通過驗證
        validate_model_metadata(mock_model)

    def test_validate_invalid_model_metadata(self):
        """測試無效模型元數據驗證"""
        invalid_model = Mock()
        invalid_model.name = None

        with pytest.raises(ValueError, match="模型必須有名稱"):
            validate_model_metadata(invalid_model)

    def test_create_model_signature(self, mock_model):
        """測試創建模型簽名"""
        signature = create_model_signature(mock_model)

        assert signature["model_type"] == "TestModel"
        assert signature["input_features"] == ["f1", "f2"]
        assert signature["target_name"] == "target"
        assert signature["feature_count"] == 2

    def test_calculate_model_drift_ks_test(self):
        """測試 KS 檢驗漂移計算"""
        # 創建基準和新資料
        baseline_data = pd.DataFrame(
            {"f1": np.random.normal(0, 1, 100), "f2": np.random.normal(0, 1, 100)}
        )

        new_data = pd.DataFrame(
            {
                "f1": np.random.normal(1, 1, 50),  # 有漂移
                "f2": np.random.normal(0, 1, 50),  # 無漂移
            }
        )

        drift_result = calculate_model_drift(baseline_data, new_data, method="ks_test")

        assert "drift_detected" in drift_result
        assert "feature_results" in drift_result
        assert "f1" in drift_result["feature_results"]
        assert "f2" in drift_result["feature_results"]
