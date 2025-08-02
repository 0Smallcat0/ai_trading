# -*- coding: utf-8 -*-
"""
超參數優化模組測試

此模組測試超參數優化功能，包括：
- 網格搜索優化器測試
- 工具函數測試
- 向後兼容性測試
- 錯誤處理測試
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.models.hyperparameter_optimization.base import HyperparameterTuner
from src.models.hyperparameter_optimization.grid_search import GridSearchOptimizer
from src.models.hyperparameter_optimization.utils import (
    validate_param_grid,
    log_tuning_params,
    save_results,
    plot_param_importance,
)
from src.models.hyperparameter_tuning import HyperparameterTuner as LegacyTuner


class TestValidateParamGrid:
    """測試參數網格驗證功能"""

    def test_valid_param_grid(self):
        """測試有效的參數網格"""
        param_grid = {"n_estimators": [100, 200], "max_depth": [5, 10, 15]}
        # 應該不拋出異常
        validate_param_grid(param_grid)

    def test_empty_param_grid(self):
        """測試空參數網格"""
        with pytest.raises(ValueError, match="參數網格不能為空"):
            validate_param_grid({})

    def test_invalid_param_grid_type(self):
        """測試無效的參數網格類型"""
        with pytest.raises(ValueError, match="參數網格必須是字典格式"):
            validate_param_grid("invalid")

    def test_invalid_param_name_type(self):
        """測試無效的參數名稱類型"""
        with pytest.raises(ValueError, match="參數名稱必須是字串"):
            validate_param_grid({123: [1, 2, 3]})

    def test_invalid_param_values_type(self):
        """測試無效的參數值類型"""
        with pytest.raises(ValueError, match="參數值必須是列表或元組"):
            validate_param_grid({"param": "invalid"})

    def test_empty_param_values(self):
        """測試空參數值"""
        with pytest.raises(ValueError, match="參數值不能為空"):
            validate_param_grid({"param": []})


class TestGridSearchOptimizer:
    """測試網格搜索優化器"""

    @pytest.fixture
    def sample_data(self):
        """創建測試資料"""
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 4), columns=["f1", "f2", "f3", "f4"])
        y = pd.Series(np.random.randint(0, 2, 100))
        return X, y

    @pytest.fixture
    def param_grid(self):
        """創建測試參數網格"""
        return {"n_estimators": [10, 20], "max_depth": [3, 5]}

    def test_optimizer_initialization(self, param_grid):
        """測試優化器初始化"""
        optimizer = GridSearchOptimizer(
            model_type="random_forest", param_grid=param_grid, cv=3
        )

        assert optimizer.model_type == "random_forest"
        assert optimizer.param_grid == param_grid
        assert optimizer.cv == 3

    def test_invalid_model_type(self, param_grid):
        """測試無效的模型類型"""
        with pytest.raises(ValueError, match="model_type 必須是非空字串"):
            GridSearchOptimizer(model_type="", param_grid=param_grid)

    def test_invalid_cv(self, param_grid):
        """測試無效的交叉驗證折數"""
        with pytest.raises(ValueError, match="cv 必須 >= 2"):
            GridSearchOptimizer(model_type="random_forest", param_grid=param_grid, cv=1)

    @patch("src.models.hyperparameter_optimization.grid_search.create_model")
    @patch("src.models.hyperparameter_optimization.grid_search.mlflow")
    def test_optimize_success(
        self, mock_mlflow, mock_create_model, sample_data, param_grid
    ):
        """測試成功的優化過程"""
        X, y = sample_data

        # 模擬模型
        mock_model = Mock()
        mock_model.model = Mock()
        mock_create_model.return_value = mock_model

        # 模擬 GridSearchCV
        with patch(
            "src.models.hyperparameter_optimization.grid_search.GridSearchCV"
        ) as mock_grid_search:
            mock_search_instance = Mock()
            mock_search_instance.best_params_ = {"n_estimators": 20, "max_depth": 5}
            mock_search_instance.best_score_ = 0.85
            mock_search_instance.cv_results_ = {
                "mean_test_score": [0.8, 0.85, 0.82, 0.83],
                "param_n_estimators": [10, 20, 10, 20],
                "param_max_depth": [3, 5, 5, 3],
            }
            mock_grid_search.return_value = mock_search_instance

            # 模擬 MLflow
            mock_run = Mock()
            mock_run.info.run_id = "test_run_id"
            mock_mlflow.active_run.return_value = mock_run

            optimizer = GridSearchOptimizer(
                model_type="random_forest", param_grid=param_grid, cv=3
            )

            results = optimizer.optimize(X, y, log_to_mlflow=False)

            assert results["best_params"] == {"n_estimators": 20, "max_depth": 5}
            assert results["best_score"] == 0.85
            assert isinstance(results["results"], pd.DataFrame)

    def test_optimize_empty_data(self, param_grid):
        """測試空資料的優化"""
        optimizer = GridSearchOptimizer(
            model_type="random_forest", param_grid=param_grid
        )

        X = pd.DataFrame()
        y = pd.Series(dtype=float)

        with pytest.raises(ValueError, match="輸入資料不能為空"):
            optimizer.optimize(X, y)

    def test_optimize_mismatched_data(self, param_grid):
        """測試不匹配的資料"""
        optimizer = GridSearchOptimizer(
            model_type="random_forest", param_grid=param_grid
        )

        X = pd.DataFrame(np.random.randn(100, 4))
        y = pd.Series(np.random.randn(50))  # 不同長度

        with pytest.raises(ValueError, match="特徵和目標變數的樣本數必須相同"):
            optimizer.optimize(X, y)

    def test_get_param_combinations_count(self, param_grid):
        """測試參數組合計數"""
        optimizer = GridSearchOptimizer(
            model_type="random_forest", param_grid=param_grid
        )

        count = optimizer.get_param_combinations_count()
        assert count == 4  # 2 * 2 = 4

    def test_estimate_runtime(self, param_grid):
        """測試運行時間估算"""
        optimizer = GridSearchOptimizer(
            model_type="random_forest", param_grid=param_grid, cv=3
        )

        estimated_time = optimizer.estimate_runtime(base_time_per_fit=1.0)
        assert estimated_time == 12.0  # 4 combinations * 3 folds * 1.0 seconds


class TestLegacyCompatibility:
    """測試向後兼容性"""

    @pytest.fixture
    def param_grid(self):
        """創建測試參數網格"""
        return {"n_estimators": [10, 20], "max_depth": [3, 5]}

    def test_legacy_tuner_initialization(self, param_grid):
        """測試舊版調優器初始化"""
        tuner = LegacyTuner(model_type="random_forest", param_grid=param_grid)

        assert tuner.model_type == "random_forest"
        assert tuner.param_grid == param_grid

    @patch("src.models.hyperparameter_tuning.GridSearchOptimizer")
    def test_legacy_grid_search_delegation(self, mock_optimizer_class, param_grid):
        """測試舊版網格搜索委託"""
        # 模擬優化器實例
        mock_optimizer = Mock()
        mock_optimizer.optimize.return_value = {
            "best_params": {"n_estimators": 20},
            "best_score": 0.85,
            "results": pd.DataFrame(),
            "run_id": "test_run",
        }
        mock_optimizer_class.return_value = mock_optimizer

        tuner = LegacyTuner(model_type="random_forest", param_grid=param_grid)

        X = pd.DataFrame(np.random.randn(10, 4))
        y = pd.Series(np.random.randint(0, 2, 10))

        results = tuner.grid_search(X, y)

        # 驗證委託調用
        mock_optimizer_class.assert_called_once()
        mock_optimizer.optimize.assert_called_once()

        # 驗證結果
        assert results["best_params"] == {"n_estimators": 20}
        assert tuner.best_params == {"n_estimators": 20}

    def test_legacy_bayesian_optimization_not_implemented(self, param_grid):
        """測試舊版貝葉斯優化未實現"""
        tuner = LegacyTuner(model_type="random_forest", param_grid=param_grid)

        X = pd.DataFrame(np.random.randn(10, 4))
        y = pd.Series(np.random.randint(0, 2, 10))

        with pytest.raises(NotImplementedError):
            tuner.bayesian_optimization(X, y)


class TestUtilityFunctions:
    """測試工具函數"""

    @patch("src.models.hyperparameter_optimization.utils.mlflow")
    def test_log_tuning_params(self, mock_mlflow):
        """測試調優參數記錄"""
        param_grid = {"n_estimators": [100, 200]}

        log_tuning_params(
            method="grid_search",
            model_type="random_forest",
            param_grid=param_grid,
            cv=5,
            scoring="accuracy",
        )

        # 驗證 MLflow 調用
        mock_mlflow.log_param.assert_any_call("tuning_method", "grid_search")
        mock_mlflow.log_param.assert_any_call("model_type", "random_forest")
        mock_mlflow.log_param.assert_any_call("cv", 5)

    @patch("src.models.hyperparameter_optimization.utils.mlflow")
    def test_save_results(self, mock_mlflow):
        """測試結果保存"""
        results = pd.DataFrame({"score": [0.8, 0.85]})
        best_params = {"n_estimators": 100}
        best_score = 0.85

        filename = save_results(results, best_params, best_score, "grid_search")

        assert filename == "grid_search_results.csv"
        mock_mlflow.log_artifact.assert_called_once_with(filename)
        mock_mlflow.log_metric.assert_called_once_with("best_score", 0.85)

    @patch("src.models.hyperparameter_optimization.utils.plt")
    def test_plot_param_importance_empty_results(self, mock_plt):
        """測試空結果的參數重要性繪製"""
        results = pd.DataFrame()

        plot_param_importance(results)

        # 應該不調用繪圖函數
        mock_plt.figure.assert_not_called()
