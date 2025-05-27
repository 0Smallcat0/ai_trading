# -*- coding: utf-8 -*-
"""
模型解釋性模組 (向後兼容)

此模組提供模型解釋性功能的向後兼容介面。
新的模組化實現位於 model_interpretability 子模組中。

Classes:
    ModelInterpreter: 模型解釋器（向後兼容）

Example:
    >>> from src.models.model_interpretability import ModelInterpreter
    >>> interpreter = ModelInterpreter(model, feature_names=features)
    >>> shap_results = interpreter.explain_with_shap(X_test)

Note:
    建議使用新的模組化介面：
    from src.models.model_interpretability import ModelInterpreter
"""

import logging
import warnings
from typing import Any, Dict, List, Optional

from src.config import LOG_LEVEL
from src.models.model_base import ModelBase

# 導入新的模組化實現
from .model_interpretability.base import ModelInterpreter as NewModelInterpreter

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))

# 檢查依賴套件
try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP 未安裝，SHAP 解釋功能將無法使用")

try:
    import lime
    LIME_AVAILABLE = True
except ImportError:
    LIME_AVAILABLE = False
    logger.warning("LIME 未安裝，LIME 解釋功能將無法使用")


class ModelInterpreter:
    """
    模型解釋器 (向後兼容版本)

    此類提供向後兼容的模型解釋介面。
    建議使用新的模組化實現以獲得更好的功能和性能。

    Attributes:
        model: 要解釋的模型實例
        feature_names: 特徵名稱列表
        class_names: 類別名稱列表
        output_dir: 結果輸出目錄

    Example:
        >>> interpreter = ModelInterpreter(model, feature_names=features)
        >>> shap_results = interpreter.explain_with_shap(X_test)

    Note:
        此類已被標記為過時，建議使用：
        from src.models.model_interpretability import ModelInterpreter
    """

    def __init__(
        self,
        model: ModelBase,
        feature_names: Optional[List[str]] = None,
        class_names: Optional[List[str]] = None,
        output_dir: Optional[str] = None,
    ) -> None:
        """
        初始化模型解釋器

        Args:
            model: 要解釋的模型
            feature_names: 特徵名稱列表
            class_names: 類別名稱列表
            output_dir: 輸出目錄

        Example:
            >>> interpreter = ModelInterpreter(
            ...     model=my_model,
            ...     feature_names=['age', 'income']
            ... )
        """
        # 使用新的實現
        self._new_interpreter = NewModelInterpreter(
            model=model,
            feature_names=feature_names,
            class_names=class_names,
            output_dir=output_dir
        )

        # 向後兼容的屬性
        self.model = model
        self.feature_names = feature_names
        self.class_names = class_names
        self.output_dir = self._new_interpreter.output_dir

        # 舊版屬性（為了兼容性）
        self.shap_explainer = None
        self.shap_values = None
        self.lime_explainer = None

    def explain_with_shap(
        self,
        X: Any,
        plot_type: str = "summary",
        sample_size: Optional[int] = None,
        log_to_mlflow: bool = True,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        使用 SHAP 解釋模型 (向後兼容方法)

        此方法委託給新的 SHAP 解釋器實現。

        Args:
            X: 特徵資料
            plot_type: 圖表類型
            sample_size: 樣本大小
            log_to_mlflow: 是否記錄到 MLflow
            **kwargs: 額外參數

        Returns:
            SHAP 解釋結果字典

        Example:
            >>> results = interpreter.explain_with_shap(X_test, plot_type="summary")
        """
        # 使用新的實現
        results = self._new_interpreter.explain_with_shap(
            X=X,
            plot_type=plot_type,
            sample_size=sample_size,
            log_to_mlflow=log_to_mlflow,
            **kwargs
        )

        # 更新舊版屬性以保持兼容性
        if 'shap_values' in results:
            self.shap_values = results['shap_values']

        return results

    def explain_with_lime(
        self,
        X: Any,
        y: Optional[Any] = None,
        num_samples: int = 5000,
        num_features: int = 10,
        log_to_mlflow: bool = True,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        使用 LIME 解釋模型 (向後兼容方法)

        此方法委託給新的 LIME 解釋器實現。

        Args:
            X: 特徵資料
            y: 目標資料
            num_samples: 樣本數量
            num_features: 特徵數量
            log_to_mlflow: 是否記錄到 MLflow
            **kwargs: 額外參數

        Returns:
            LIME 解釋結果字典

        Example:
            >>> results = interpreter.explain_with_lime(X_test, y_test)
        """
        # 使用新的實現
        results = self._new_interpreter.explain_with_lime(
            X=X,
            y=y,
            num_samples=num_samples,
            num_features=num_features,
            log_to_mlflow=log_to_mlflow,
            **kwargs
        )

        return results

    def feature_importance(
        self,
        X: Any,
        y: Any,
        method: str = "permutation",
        n_repeats: int = 10,
        log_to_mlflow: bool = True,
        **kwargs: Any
    ) -> Any:
        """
        計算特徵重要性 (向後兼容方法)

        此方法委託給新的特徵重要性分析器實現。

        Args:
            X: 特徵資料
            y: 目標資料
            method: 計算方法
            n_repeats: 重複次數
            log_to_mlflow: 是否記錄到 MLflow
            **kwargs: 額外參數

        Returns:
            特徵重要性結果

        Example:
            >>> importance_df = interpreter.feature_importance(X_test, y_test)
        """
        # 使用新的實現
        results = self._new_interpreter.feature_importance(
            X=X,
            y=y,
            method=method,
            n_repeats=n_repeats,
            log_to_mlflow=log_to_mlflow,
            **kwargs
        )

        # 返回重要性資料框以保持向後兼容
        if isinstance(results, dict) and method in results:
            return results[method].get('importance', results[method])
        elif isinstance(results, dict) and 'importance' in results:
            return results['importance']
        else:
            return results
