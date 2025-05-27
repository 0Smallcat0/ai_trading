# -*- coding: utf-8 -*-
"""
模型解釋性模組測試

此模組測試模型解釋性功能，包括：
- SHAP 解釋器測試
- LIME 解釋器測試
- 特徵重要性分析器測試
- 向後兼容性測試
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch, MagicMock

from src.models.model_interpretability.base import ModelInterpreter
from src.models.model_interpretability.shap_explainer import SHAPExplainer
from src.models.model_interpretability.lime_explainer import LIMEExplainer
from src.models.model_interpretability.feature_importance import (
    FeatureImportanceAnalyzer,
)
from src.models.model_interpretability.utils import (
    validate_explanation_inputs,
    save_explanation_results,
    plot_explanation_comparison,
)
from src.models.model_interpretability import ModelInterpreter as LegacyInterpreter


class TestValidateExplanationInputs:
    """測試解釋輸入驗證功能"""

    def test_valid_inputs(self):
        """測試有效的輸入"""
        X = pd.DataFrame(np.random.randn(100, 4), columns=["f1", "f2", "f3", "f4"])
        y = pd.Series(np.random.randint(0, 2, 100))
        feature_names = ["f1", "f2", "f3", "f4"]

        # 應該不拋出異常
        validate_explanation_inputs(X, y, feature_names)

    def test_none_features(self):
        """測試 None 特徵資料"""
        with pytest.raises(ValueError, match="特徵資料 X 不能為 None"):
            validate_explanation_inputs(None)

    def test_empty_features(self):
        """測試空特徵資料"""
        X = pd.DataFrame()
        with pytest.raises(ValueError, match="特徵資料 X 不能為空"):
            validate_explanation_inputs(X)

    def test_mismatched_data_length(self):
        """測試不匹配的資料長度"""
        X = pd.DataFrame(np.random.randn(100, 4))
        y = pd.Series(np.random.randn(50))  # 不同長度

        with pytest.raises(ValueError, match="特徵資料和目標資料的樣本數必須相同"):
            validate_explanation_inputs(X, y)

    def test_invalid_feature_names_type(self):
        """測試無效的特徵名稱類型"""
        X = pd.DataFrame(np.random.randn(10, 4))

        with pytest.raises(TypeError, match="feature_names 必須是列表或元組"):
            validate_explanation_inputs(X, feature_names="invalid")

    def test_mismatched_feature_names_count(self):
        """測試不匹配的特徵名稱數量"""
        X = pd.DataFrame(np.random.randn(10, 4))
        feature_names = ["f1", "f2"]  # 只有2個名稱，但有4個特徵

        with pytest.raises(ValueError, match="特徵名稱數量必須與特徵數量相同"):
            validate_explanation_inputs(X, feature_names=feature_names)


class TestModelInterpreter:
    """測試模型解釋器基礎類別"""

    @pytest.fixture
    def mock_model(self):
        """創建模擬模型"""
        model = Mock()
        model.trained = True
        model.name = "test_model"
        model.feature_names = ["f1", "f2", "f3", "f4"]
        return model

    @pytest.fixture
    def sample_data(self):
        """創建測試資料"""
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(100, 4), columns=["f1", "f2", "f3", "f4"])
        y = pd.Series(np.random.randint(0, 2, 100))
        return X, y

    def test_interpreter_initialization(self, mock_model):
        """測試解釋器初始化"""
        interpreter = ModelInterpreter(
            model=mock_model, feature_names=["f1", "f2", "f3", "f4"]
        )

        assert interpreter.model == mock_model
        assert interpreter.feature_names == ["f1", "f2", "f3", "f4"]

    def test_untrained_model_error(self):
        """測試未訓練模型錯誤"""
        model = Mock()
        model.trained = False

        with pytest.raises(ValueError, match="模型必須已經訓練完成"):
            ModelInterpreter(model)

    def test_invalid_model_type(self):
        """測試無效的模型類型"""
        with pytest.raises(ValueError, match="model 必須是 ModelBase 的實例"):
            ModelInterpreter("invalid_model")

    @patch("src.models.model_interpretability.base.os.makedirs")
    def test_output_directory_creation(self, mock_makedirs, mock_model):
        """測試輸出目錄創建"""
        interpreter = ModelInterpreter(mock_model, output_dir="./test_output")

        mock_makedirs.assert_called_once_with("./test_output", exist_ok=True)
        assert interpreter.output_dir == "./test_output"

    def test_get_model_info(self, mock_model):
        """測試獲取模型資訊"""
        interpreter = ModelInterpreter(
            mock_model, feature_names=["f1", "f2"], class_names=["class0", "class1"]
        )

        info = interpreter.get_model_info()

        assert info["name"] == "test_model"
        assert info["trained"] == True
        assert info["n_features"] == 2
        assert info["feature_names"] == ["f1", "f2"]
        assert info["class_names"] == ["class0", "class1"]


class TestSHAPExplainer:
    """測試 SHAP 解釋器"""

    @pytest.fixture
    def mock_model(self):
        """創建模擬模型"""
        model = Mock()
        model.trained = True
        model.name = "test_model"
        model.model = Mock()
        model.predict = Mock(return_value=np.array([0.1, 0.9, 0.3]))
        return model

    @pytest.fixture
    def sample_data(self):
        """創建測試資料"""
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(10, 4), columns=["f1", "f2", "f3", "f4"])
        return X

    @patch("src.models.model_interpretability.shap_explainer.SHAP_AVAILABLE", True)
    def test_shap_explainer_initialization(self, mock_model):
        """測試 SHAP 解釋器初始化"""
        explainer = SHAPExplainer(
            model=mock_model, feature_names=["f1", "f2", "f3", "f4"]
        )

        assert explainer.model == mock_model
        assert explainer.feature_names == ["f1", "f2", "f3", "f4"]

    @patch("src.models.model_interpretability.shap_explainer.SHAP_AVAILABLE", False)
    def test_shap_not_available_error(self, mock_model):
        """測試 SHAP 未安裝錯誤"""
        with pytest.raises(ImportError, match="SHAP 未安裝"):
            SHAPExplainer(mock_model)

    def test_untrained_model_error(self):
        """測試未訓練模型錯誤"""
        model = Mock()
        model.trained = False

        with pytest.raises(ValueError, match="模型必須已經訓練完成"):
            SHAPExplainer(model)


class TestLIMEExplainer:
    """測試 LIME 解釋器"""

    @pytest.fixture
    def mock_model(self):
        """創建模擬模型"""
        model = Mock()
        model.trained = True
        model.name = "test_model"
        model.model = Mock()
        model.predict = Mock(return_value=np.array([0, 1, 0]))
        model.predict_proba = Mock(
            return_value=np.array([[0.9, 0.1], [0.2, 0.8], [0.7, 0.3]])
        )
        return model

    @patch("src.models.model_interpretability.lime_explainer.LIME_AVAILABLE", True)
    def test_lime_explainer_initialization(self, mock_model):
        """測試 LIME 解釋器初始化"""
        explainer = LIMEExplainer(
            model=mock_model,
            feature_names=["f1", "f2", "f3", "f4"],
            class_names=["class0", "class1"],
        )

        assert explainer.model == mock_model
        assert explainer.feature_names == ["f1", "f2", "f3", "f4"]
        assert explainer.class_names == ["class0", "class1"]

    @patch("src.models.model_interpretability.lime_explainer.LIME_AVAILABLE", False)
    def test_lime_not_available_error(self, mock_model):
        """測試 LIME 未安裝錯誤"""
        with pytest.raises(ImportError, match="LIME 未安裝"):
            LIMEExplainer(mock_model)


class TestFeatureImportanceAnalyzer:
    """測試特徵重要性分析器"""

    @pytest.fixture
    def mock_model(self):
        """創建模擬模型"""
        model = Mock()
        model.trained = True
        model.name = "test_model"
        model.model = Mock()
        model.model.feature_importances_ = np.array([0.3, 0.2, 0.4, 0.1])
        return model

    @pytest.fixture
    def sample_data(self):
        """創建測試資料"""
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(50, 4), columns=["f1", "f2", "f3", "f4"])
        y = pd.Series(np.random.randint(0, 2, 50))
        return X, y

    def test_analyzer_initialization(self, mock_model):
        """測試分析器初始化"""
        analyzer = FeatureImportanceAnalyzer(
            model=mock_model, feature_names=["f1", "f2", "f3", "f4"]
        )

        assert analyzer.model == mock_model
        assert analyzer.feature_names == ["f1", "f2", "f3", "f4"]

    def test_untrained_model_error(self):
        """測試未訓練模型錯誤"""
        model = Mock()
        model.trained = False

        with pytest.raises(ValueError, match="模型必須已經訓練完成"):
            FeatureImportanceAnalyzer(model)

    @patch(
        "src.models.model_interpretability.feature_importance.permutation_importance"
    )
    def test_permutation_importance_calculation(
        self, mock_perm_importance, mock_model, sample_data
    ):
        """測試排列重要性計算"""
        X, y = sample_data

        # 模擬排列重要性結果
        mock_result = Mock()
        mock_result.importances_mean = np.array([0.1, 0.3, 0.2, 0.4])
        mock_result.importances_std = np.array([0.01, 0.02, 0.015, 0.03])
        mock_result.importances = np.array([[0.1, 0.3, 0.2, 0.4]])
        mock_perm_importance.return_value = mock_result

        analyzer = FeatureImportanceAnalyzer(
            mock_model, feature_names=["f1", "f2", "f3", "f4"]
        )

        with patch(
            "src.models.model_interpretability.feature_importance.save_explanation_results"
        ):
            results = analyzer.calculate_importance(X, y, method="permutation")

        assert "permutation" in results
        assert "importance" in results["permutation"]
        mock_perm_importance.assert_called_once()


class TestLegacyCompatibility:
    """測試向後兼容性"""

    @pytest.fixture
    def mock_model(self):
        """創建模擬模型"""
        model = Mock()
        model.trained = True
        model.name = "test_model"
        model.feature_names = ["f1", "f2", "f3", "f4"]
        return model

    @patch("src.models.model_interpretability.NewModelInterpreter")
    def test_legacy_interpreter_delegation(
        self, mock_new_interpreter_class, mock_model
    ):
        """測試舊版解釋器委託"""
        # 模擬新解釋器實例
        mock_new_interpreter = Mock()
        mock_new_interpreter.output_dir = "./test_output"
        mock_new_interpreter_class.return_value = mock_new_interpreter

        # 創建舊版解釋器
        legacy_interpreter = LegacyInterpreter(
            model=mock_model, feature_names=["f1", "f2", "f3", "f4"]
        )

        # 驗證委託調用
        mock_new_interpreter_class.assert_called_once_with(
            model=mock_model,
            feature_names=["f1", "f2", "f3", "f4"],
            class_names=None,
            output_dir=None,
        )

        # 驗證屬性設定
        assert legacy_interpreter.model == mock_model
        assert legacy_interpreter.feature_names == ["f1", "f2", "f3", "f4"]
        assert legacy_interpreter.output_dir == "./test_output"

    @patch("src.models.model_interpretability.NewModelInterpreter")
    def test_legacy_shap_method_delegation(
        self, mock_new_interpreter_class, mock_model
    ):
        """測試舊版 SHAP 方法委託"""
        # 模擬新解釋器和結果
        mock_new_interpreter = Mock()
        mock_new_interpreter.explain_with_shap.return_value = {
            "shap_values": np.array([[0.1, 0.2, 0.3, 0.4]]),
            "importance": pd.DataFrame(
                {"feature": ["f1", "f2"], "importance": [0.1, 0.2]}
            ),
        }
        mock_new_interpreter_class.return_value = mock_new_interpreter

        legacy_interpreter = LegacyInterpreter(mock_model)

        X = pd.DataFrame(np.random.randn(10, 4))
        results = legacy_interpreter.explain_with_shap(X, plot_type="summary")

        # 驗證委託調用
        mock_new_interpreter.explain_with_shap.assert_called_once()

        # 驗證結果
        assert "shap_values" in results
        assert legacy_interpreter.shap_values is not None
