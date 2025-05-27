# -*- coding: utf-8 -*-
"""
訓練管道模組測試

此模組測試訓練管道功能，包括：
- 模型訓練器測試
- 交叉驗證器測試
- 訓練配置測試
- 向後兼容性測試
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
from unittest.mock import Mock, patch, MagicMock

from src.models.training_pipeline import ModelTrainer
from src.models.training_pipeline.trainer import ModelTrainer as NewModelTrainer
from src.models.training_pipeline.cross_validator import CrossValidator
from src.models.training_pipeline.config import TrainingConfig
from src.models.training_pipeline.utils import (
    validate_training_inputs,
    check_acceptance_criteria,
    create_model_summary
)


class TestTrainingConfig:
    """測試訓練配置"""

    def test_default_config(self):
        """測試預設配置"""
        config = TrainingConfig()
        
        assert config.experiment_name == "default"
        assert config.early_stopping is False
        assert config.validation_split == 0.2
        assert config.random_seed == 42

    def test_custom_config(self):
        """測試自定義配置"""
        config = TrainingConfig(
            experiment_name="test_experiment",
            early_stopping=True,
            early_stopping_patience=5,
            metrics_threshold={"accuracy": 0.9}
        )
        
        assert config.experiment_name == "test_experiment"
        assert config.early_stopping is True
        assert config.early_stopping_patience == 5
        assert config.metrics_threshold["accuracy"] == 0.9

    def test_config_validation(self):
        """測試配置驗證"""
        # 測試無效的實驗名稱
        with pytest.raises(ValueError, match="experiment_name 必須是非空字串"):
            TrainingConfig(experiment_name="")
        
        # 測試無效的驗證分割比例
        with pytest.raises(ValueError, match="validation_split 必須在 0 和 1 之間"):
            TrainingConfig(validation_split=1.5)

    def test_config_to_dict(self):
        """測試配置轉換為字典"""
        config = TrainingConfig(experiment_name="test")
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["experiment_name"] == "test"

    def test_config_from_dict(self):
        """測試從字典創建配置"""
        config_dict = {"experiment_name": "test", "early_stopping": True}
        config = TrainingConfig.from_dict(config_dict)
        
        assert config.experiment_name == "test"
        assert config.early_stopping is True

    def test_config_update(self):
        """測試配置更新"""
        config = TrainingConfig()
        config.update(early_stopping=True, early_stopping_patience=10)
        
        assert config.early_stopping is True
        assert config.early_stopping_patience == 10


class TestNewModelTrainer:
    """測試新的模型訓練器"""

    @pytest.fixture
    def mock_model(self):
        """創建模擬模型"""
        model = Mock()
        model.name = "test_model"
        model.trained = False
        model.train = Mock()
        model.evaluate = Mock(return_value={"accuracy": 0.85, "f1": 0.80})
        model.feature_importance = Mock(return_value=pd.DataFrame({
            "feature": ["f1", "f2"], 
            "importance": [0.6, 0.4]
        }))
        model.get_params = Mock(return_value={"n_estimators": 100})
        model.save = Mock(return_value="/path/to/model")
        return model

    @pytest.fixture
    def config(self):
        """創建測試配置"""
        return TrainingConfig(
            experiment_name="test_experiment",
            metrics_threshold={"accuracy": 0.8}
        )

    @pytest.fixture
    def sample_data(self):
        """創建測試資料"""
        np.random.seed(42)
        X_train = pd.DataFrame(np.random.randn(100, 5), columns=[f"f{i}" for i in range(5)])
        y_train = pd.Series(np.random.randint(0, 2, 100))
        X_val = pd.DataFrame(np.random.randn(30, 5), columns=[f"f{i}" for i in range(5)])
        y_val = pd.Series(np.random.randint(0, 2, 30))
        return X_train, y_train, X_val, y_val

    def test_trainer_initialization(self, mock_model, config):
        """測試訓練器初始化"""
        trainer = NewModelTrainer(mock_model, config)
        
        assert trainer.model == mock_model
        assert trainer.config == config

    def test_trainer_initialization_invalid_model(self, config):
        """測試無效模型初始化"""
        with pytest.raises(ValueError, match="model 必須是 ModelBase 的實例"):
            NewModelTrainer("invalid_model", config)

    @patch('src.models.training_pipeline.trainer.setup_mlflow_tracking')
    @patch('src.models.training_pipeline.trainer.mlflow')
    def test_train_without_validation(self, mock_mlflow, mock_setup, mock_model, config, sample_data):
        """測試不使用驗證集的訓練"""
        X_train, y_train, _, _ = sample_data
        
        # 設定 MLflow 模擬
        mock_mlflow.start_run.return_value = None
        mock_mlflow.active_run.return_value.info.run_id = "test_run_id"
        
        trainer = NewModelTrainer(mock_model, config)
        results = trainer.train(X_train, y_train, log_to_mlflow=False)
        
        # 驗證訓練被調用
        mock_model.train.assert_called_once_with(X_train, y_train)
        
        # 驗證結果
        assert "train_metrics" in results
        assert "val_metrics" in results
        assert "accepted" in results

    @patch('src.models.training_pipeline.trainer.setup_mlflow_tracking')
    @patch('src.models.training_pipeline.trainer.mlflow')
    def test_train_with_validation(self, mock_mlflow, mock_setup, mock_model, config, sample_data):
        """測試使用驗證集的訓練"""
        X_train, y_train, X_val, y_val = sample_data
        
        # 設定 MLflow 模擬
        mock_mlflow.start_run.return_value = None
        mock_mlflow.active_run.return_value.info.run_id = "test_run_id"
        
        trainer = NewModelTrainer(mock_model, config)
        results = trainer.train(X_train, y_train, X_val, y_val, log_to_mlflow=False)
        
        # 驗證訓練被調用
        mock_model.train.assert_called_once_with(X_train, y_train)
        
        # 驗證評估被調用
        assert mock_model.evaluate.call_count == 2  # 訓練集和驗證集
        
        # 驗證結果
        assert results["train_metrics"]["accuracy"] == 0.85
        assert results["val_metrics"]["accuracy"] == 0.85

    def test_train_untrained_model_error(self, config, sample_data):
        """測試未訓練模型錯誤"""
        X_train, y_train, _, _ = sample_data
        
        # 創建無效模型
        invalid_model = Mock()
        invalid_model.name = "invalid"
        
        with pytest.raises(ValueError):
            trainer = NewModelTrainer(invalid_model, config)

    @patch('src.models.training_pipeline.trainer.setup_mlflow_tracking')
    def test_evaluate_on_test(self, mock_setup, mock_model, config, sample_data):
        """測試測試集評估"""
        _, _, X_test, y_test = sample_data
        
        # 設定模型為已訓練
        mock_model.trained = True
        
        trainer = NewModelTrainer(mock_model, config)
        test_metrics = trainer.evaluate_on_test(X_test, y_test, log_to_mlflow=False)
        
        # 驗證評估被調用
        mock_model.evaluate.assert_called_with(X_test, y_test)
        
        # 驗證結果
        assert test_metrics["accuracy"] == 0.85

    def test_evaluate_on_test_untrained_model(self, mock_model, config, sample_data):
        """測試未訓練模型的測試集評估"""
        _, _, X_test, y_test = sample_data
        
        # 設定模型為未訓練
        mock_model.trained = False
        
        trainer = NewModelTrainer(mock_model, config)
        
        with pytest.raises(ValueError, match="模型尚未訓練"):
            trainer.evaluate_on_test(X_test, y_test)

    def test_get_training_summary(self, mock_model, config):
        """測試獲取訓練摘要"""
        trainer = NewModelTrainer(mock_model, config)
        trainer.train_metrics = {"accuracy": 0.85}
        trainer.val_metrics = {"accuracy": 0.80}
        
        summary = trainer.get_training_summary()
        
        assert summary["model_name"] == "test_model"
        assert summary["train_metrics"]["accuracy"] == 0.85
        assert summary["val_metrics"]["accuracy"] == 0.80


class TestCrossValidator:
    """測試交叉驗證器"""

    @pytest.fixture
    def mock_model(self):
        """創建模擬模型"""
        model = Mock()
        model.name = "test_model"
        model.__class__.__name__ = "TestModel"
        model.get_params = Mock(return_value={"n_estimators": 100})
        return model

    @pytest.fixture
    def config(self):
        """創建測試配置"""
        return TrainingConfig(experiment_name="cv_test")

    @pytest.fixture
    def sample_data(self):
        """創建測試資料"""
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 3), columns=["f1", "f2", "f3"])
        y = pd.Series(np.random.randint(0, 2, 100))
        return X, y

    def test_cross_validator_initialization(self, mock_model, config):
        """測試交叉驗證器初始化"""
        validator = CrossValidator(mock_model, config)
        
        assert validator.model == mock_model
        assert validator.config == config

    @patch('src.models.training_pipeline.cross_validator.create_model')
    @patch('src.models.training_pipeline.cross_validator.setup_mlflow_tracking')
    def test_cross_validate_time_series(self, mock_setup, mock_create_model, mock_model, config, sample_data):
        """測試時間序列交叉驗證"""
        X, y = sample_data
        
        # 設定模型副本
        mock_model_copy = Mock()
        mock_model_copy.train = Mock()
        mock_model_copy.evaluate = Mock(return_value={"accuracy": 0.85})
        mock_create_model.return_value = mock_model_copy
        
        validator = CrossValidator(mock_model, config)
        
        with patch('src.models.training_pipeline.cross_validator.mlflow'):
            results = validator.cross_validate(X, y, cv=3, time_series=True, log_to_mlflow=False)
        
        # 驗證結果
        assert "cv_results" in results
        assert "statistics" in results
        assert len(results["cv_results"]) == 3

    @patch('src.models.training_pipeline.cross_validator.create_model')
    @patch('src.models.training_pipeline.cross_validator.setup_mlflow_tracking')
    def test_cross_validate_kfold(self, mock_setup, mock_create_model, mock_model, config, sample_data):
        """測試 K-折交叉驗證"""
        X, y = sample_data
        
        # 設定模型副本
        mock_model_copy = Mock()
        mock_model_copy.train = Mock()
        mock_model_copy.evaluate = Mock(return_value={"accuracy": 0.85})
        mock_create_model.return_value = mock_model_copy
        
        validator = CrossValidator(mock_model, config)
        
        with patch('src.models.training_pipeline.cross_validator.mlflow'):
            results = validator.cross_validate(X, y, cv=3, time_series=False, log_to_mlflow=False)
        
        # 驗證結果
        assert "cv_results" in results
        assert "statistics" in results
        assert len(results["cv_results"]) == 3

    @patch('src.models.training_pipeline.cross_validator.create_model')
    def test_get_best_model(self, mock_create_model, mock_model, config, sample_data):
        """測試獲取最佳模型"""
        X, y = sample_data
        
        # 設定模型副本
        mock_model_copy = Mock()
        mock_model_copy.train = Mock()
        mock_model_copy.evaluate = Mock(return_value={"accuracy": 0.85})
        mock_create_model.return_value = mock_model_copy
        
        validator = CrossValidator(mock_model, config)
        
        with patch('src.models.training_pipeline.cross_validator.setup_mlflow_tracking'), \
             patch('src.models.training_pipeline.cross_validator.mlflow'):
            validator.cross_validate(X, y, cv=2, log_to_mlflow=False)
        
        best_model = validator.get_best_model()
        assert best_model is not None


class TestUtilityFunctions:
    """測試工具函數"""

    def test_validate_training_inputs_valid(self):
        """測試有效輸入驗證"""
        X_train = pd.DataFrame({"f1": [1, 2, 3], "f2": [4, 5, 6]})
        y_train = pd.Series([0, 1, 0])
        
        # 應該不拋出異常
        validate_training_inputs(X_train, y_train)

    def test_validate_training_inputs_invalid_type(self):
        """測試無效類型輸入驗證"""
        X_train = [[1, 2], [3, 4]]  # 不是 DataFrame
        y_train = pd.Series([0, 1])
        
        with pytest.raises(TypeError, match="X_train 必須是 pandas DataFrame"):
            validate_training_inputs(X_train, y_train)

    def test_validate_training_inputs_mismatched_length(self):
        """測試長度不匹配的輸入驗證"""
        X_train = pd.DataFrame({"f1": [1, 2, 3], "f2": [4, 5, 6]})
        y_train = pd.Series([0, 1])  # 長度不匹配
        
        with pytest.raises(ValueError, match="X_train 和 y_train 的樣本數必須相同"):
            validate_training_inputs(X_train, y_train)

    def test_check_acceptance_criteria_pass(self):
        """測試通過接受標準檢查"""
        metrics = {"accuracy": 0.9, "f1": 0.85}
        thresholds = {"accuracy": 0.8, "f1": 0.8}
        
        result = check_acceptance_criteria(metrics, thresholds)
        assert result is True

    def test_check_acceptance_criteria_fail(self):
        """測試未通過接受標準檢查"""
        metrics = {"accuracy": 0.7, "f1": 0.85}
        thresholds = {"accuracy": 0.8, "f1": 0.8}
        
        result = check_acceptance_criteria(metrics, thresholds)
        assert result is False

    def test_check_acceptance_criteria_negative_metrics(self):
        """測試負向指標的接受標準檢查"""
        metrics = {"max_drawdown": -0.15, "loss": 0.1}
        thresholds = {"max_drawdown": -0.2, "loss": 0.2}
        
        result = check_acceptance_criteria(metrics, thresholds)
        assert result is True

    def test_create_model_summary(self):
        """測試創建模型摘要"""
        mock_model = Mock()
        mock_model.name = "test_model"
        mock_model.__class__.__name__ = "TestModel"
        mock_model.trained = True
        mock_model.feature_names = ["f1", "f2"]
        mock_model.target_name = "target"
        mock_model.get_params = Mock(return_value={"n_estimators": 100})
        
        train_metrics = {"accuracy": 0.9}
        val_metrics = {"accuracy": 0.85}
        
        summary = create_model_summary(mock_model, train_metrics, val_metrics)
        
        assert summary["model_name"] == "test_model"
        assert summary["model_type"] == "TestModel"
        assert summary["feature_count"] == 2
        assert summary["train_metrics"]["accuracy"] == 0.9
        assert summary["val_metrics"]["accuracy"] == 0.85


class TestLegacyCompatibility:
    """測試向後兼容性"""

    @pytest.fixture
    def mock_model(self):
        """創建模擬模型"""
        model = Mock()
        model.name = "test_model"
        model.trained = True
        return model

    def test_legacy_trainer_interface(self, mock_model):
        """測試舊版訓練器介面"""
        with patch('src.models.training_pipeline.legacy_interface.warnings.warn'):
            trainer = ModelTrainer(mock_model, experiment_name="test")
        
        # 驗證委託調用
        assert hasattr(trainer, '_new_trainer')
        assert hasattr(trainer, '_cross_validator')
        assert trainer.experiment_name == "test"
