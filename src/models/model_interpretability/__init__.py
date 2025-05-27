# -*- coding: utf-8 -*-
"""
模型解釋性模組

此模組提供完整的模型解釋性功能，包括：
- SHAP (SHapley Additive exPlanations) 解釋
- LIME (Local Interpretable Model-agnostic Explanations) 解釋
- 特徵重要性分析
- 部分依賴圖
- 解釋結果視覺化

Classes:
    ModelInterpreter: 主要的模型解釋器
    SHAPExplainer: SHAP 解釋器
    LIMEExplainer: LIME 解釋器
    FeatureImportanceAnalyzer: 特徵重要性分析器

Functions:
    create_interpreter: 創建解釋器的工廠函數
    compare_explanations: 比較不同解釋方法的結果
    generate_explanation_report: 生成完整的解釋報告

Example:
    >>> from src.models.model_interpretability import ModelInterpreter
    >>> interpreter = ModelInterpreter(model, feature_names=feature_names)
    >>> shap_results = interpreter.explain_with_shap(X_test)
    >>> lime_results = interpreter.explain_with_lime(X_test, y_test)

Note:
    需要安裝 shap 和 lime 套件才能使用相應的解釋功能
    某些解釋方法可能需要較長的計算時間
"""

from .base import ModelInterpreter
from .shap_explainer import SHAPExplainer
from .lime_explainer import LIMEExplainer
from .feature_importance import FeatureImportanceAnalyzer
from .utils import (
    validate_explanation_inputs,
    save_explanation_results,
    plot_explanation_comparison,
    generate_explanation_report,
    create_interpreter,
)

__all__ = [
    "ModelInterpreter",
    "SHAPExplainer",
    "LIMEExplainer",
    "FeatureImportanceAnalyzer",
    "validate_explanation_inputs",
    "save_explanation_results",
    "plot_explanation_comparison",
    "generate_explanation_report",
    "create_interpreter",
]

# 版本資訊
__version__ = "1.0.0"
__author__ = "AI Trading System Team"

# 檢查依賴套件
try:
    import shap

    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

try:
    import lime

    LIME_AVAILABLE = True
except ImportError:
    LIME_AVAILABLE = False

# 導出可用性檢查
__all__.extend(["SHAP_AVAILABLE", "LIME_AVAILABLE"])
