# -*- coding: utf-8 -*-
"""
模型解釋性基礎類別

此模組定義模型解釋性的基礎類別和介面，提供：
- 統一的解釋介面
- 結果管理和視覺化
- 輸出目錄管理

Classes:
    ModelInterpreter: 模型解釋器基礎類別
"""

import logging
import os
from abc import ABC
from typing import Any, Dict, List, Optional

from src.config import LOG_LEVEL, RESULTS_DIR
from src.models.model_base import ModelBase
from .utils import validate_explanation_inputs

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class ModelInterpreter:
    """
    模型解釋器基礎類別
    
    提供統一的模型解釋介面，支援多種解釋方法和結果管理。
    
    Attributes:
        model: 要解釋的模型實例
        feature_names: 特徵名稱列表
        class_names: 類別名稱列表（分類問題）
        output_dir: 結果輸出目錄
        
    Example:
        >>> interpreter = ModelInterpreter(
        ...     model=trained_model,
        ...     feature_names=['feature1', 'feature2'],
        ...     class_names=['class0', 'class1']
        ... )
        >>> results = interpreter.explain_with_shap(X_test)
        
    Note:
        這是基礎類別，提供通用功能和介面
        具體的解釋方法由專門的解釋器類別實現
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
            model: 要解釋的模型，必須是已訓練的 ModelBase 實例
            feature_names: 特徵名稱列表，None 表示使用模型的特徵名稱
            class_names: 類別名稱列表，用於分類問題的標籤顯示
            output_dir: 結果輸出目錄，None 表示使用預設目錄
            
        Raises:
            ValueError: 當模型未訓練或參數無效時
            OSError: 當無法創建輸出目錄時
            
        Example:
            >>> interpreter = ModelInterpreter(
            ...     model=my_model,
            ...     feature_names=['age', 'income', 'score'],
            ...     output_dir='./explanations'
            ... )
        """
        # 驗證模型
        if not isinstance(model, ModelBase):
            raise ValueError("model 必須是 ModelBase 的實例")
            
        if not model.trained:
            raise ValueError("模型必須已經訓練完成")
        
        self.model = model
        self.feature_names = feature_names or getattr(model, 'feature_names', None)
        self.class_names = class_names
        
        # 設定輸出目錄
        if output_dir is None:
            output_dir = os.path.join(
                RESULTS_DIR, "model_interpretation", model.name
            )
        self.output_dir = output_dir
        
        # 創建輸出目錄
        try:
            os.makedirs(self.output_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"無法創建輸出目錄 {self.output_dir}: {e}")
            raise OSError(f"輸出目錄創建失敗: {e}") from e
        
        logger.info(f"模型解釋器已初始化: {model.name}, 輸出目錄: {self.output_dir}")

    def explain_with_shap(
        self,
        X: Any,
        plot_type: str = "summary",
        sample_size: Optional[int] = None,
        log_to_mlflow: bool = True,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        使用 SHAP 解釋模型
        
        Args:
            X: 特徵資料
            plot_type: 圖表類型
            sample_size: 樣本大小
            log_to_mlflow: 是否記錄到 MLflow
            **kwargs: 額外參數
            
        Returns:
            SHAP 解釋結果字典
            
        Note:
            此方法委託給 SHAPExplainer 實現
        """
        from .shap_explainer import SHAPExplainer
        
        explainer = SHAPExplainer(
            model=self.model,
            feature_names=self.feature_names,
            class_names=self.class_names,
            output_dir=self.output_dir
        )
        
        return explainer.explain(
            X=X,
            plot_type=plot_type,
            sample_size=sample_size,
            log_to_mlflow=log_to_mlflow,
            **kwargs
        )

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
        使用 LIME 解釋模型
        
        Args:
            X: 特徵資料
            y: 目標資料
            num_samples: 樣本數量
            num_features: 特徵數量
            log_to_mlflow: 是否記錄到 MLflow
            **kwargs: 額外參數
            
        Returns:
            LIME 解釋結果字典
            
        Note:
            此方法委託給 LIMEExplainer 實現
        """
        from .lime_explainer import LIMEExplainer
        
        explainer = LIMEExplainer(
            model=self.model,
            feature_names=self.feature_names,
            class_names=self.class_names,
            output_dir=self.output_dir
        )
        
        return explainer.explain(
            X=X,
            y=y,
            num_samples=num_samples,
            num_features=num_features,
            log_to_mlflow=log_to_mlflow,
            **kwargs
        )

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
        計算特徵重要性
        
        Args:
            X: 特徵資料
            y: 目標資料
            method: 計算方法
            n_repeats: 重複次數
            log_to_mlflow: 是否記錄到 MLflow
            **kwargs: 額外參數
            
        Returns:
            特徵重要性結果
            
        Note:
            此方法委託給 FeatureImportanceAnalyzer 實現
        """
        from .feature_importance import FeatureImportanceAnalyzer
        
        analyzer = FeatureImportanceAnalyzer(
            model=self.model,
            feature_names=self.feature_names,
            output_dir=self.output_dir
        )
        
        return analyzer.calculate_importance(
            X=X,
            y=y,
            method=method,
            n_repeats=n_repeats,
            log_to_mlflow=log_to_mlflow,
            **kwargs
        )

    def get_model_info(self) -> Dict[str, Any]:
        """
        獲取模型資訊
        
        Returns:
            模型資訊字典
            
        Example:
            >>> info = interpreter.get_model_info()
            >>> print(f"Model: {info['name']}, Features: {info['n_features']}")
        """
        return {
            "name": self.model.name,
            "type": self.model.__class__.__name__,
            "trained": self.model.trained,
            "n_features": len(self.feature_names) if self.feature_names else None,
            "feature_names": self.feature_names,
            "class_names": self.class_names,
            "output_dir": self.output_dir
        }

    def __repr__(self) -> str:
        """字串表示"""
        return (
            f"{self.__class__.__name__}("
            f"model='{self.model.name}', "
            f"n_features={len(self.feature_names) if self.feature_names else 'Unknown'}, "
            f"output_dir='{self.output_dir}'"
            f")"
        )
