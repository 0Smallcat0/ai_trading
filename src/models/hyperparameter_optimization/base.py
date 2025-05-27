# -*- coding: utf-8 -*-
"""
超參數調優基礎類別

此模組定義超參數調優的基礎類別和介面，提供：
- 統一的調優介面
- MLflow 實驗追蹤整合
- 結果管理和視覺化

Classes:
    HyperparameterTuner: 超參數調優器基礎類別
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Union

import mlflow
import pandas as pd

from src.config import LOG_LEVEL
from .utils import validate_param_grid

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class HyperparameterTuner(ABC):
    """
    超參數調優器基礎類別
    
    提供統一的超參數調優介面，支援多種優化方法和 MLflow 實驗追蹤。
    
    Attributes:
        model_type: 模型類型名稱
        param_grid: 參數搜索空間
        experiment_name: MLflow 實驗名稱
        tracking_uri: MLflow 追蹤伺服器 URI
        scoring: 評分函數或指標名稱
        cv: 交叉驗證折數
        n_jobs: 並行任務數
        best_params: 最佳參數組合
        best_score: 最佳評分
        results: 完整調優結果
        run_id: MLflow 運行 ID
        
    Example:
        >>> tuner = HyperparameterTuner(
        ...     model_type="random_forest",
        ...     param_grid={"n_estimators": [100, 200], "max_depth": [5, 10]},
        ...     scoring="accuracy",
        ...     cv=5
        ... )
        
    Note:
        這是抽象基礎類別，需要繼承並實現具體的優化方法
    """

    def __init__(
        self,
        model_type: str,
        param_grid: Dict[str, Any],
        experiment_name: str = "hyperparameter_tuning",
        tracking_uri: Optional[str] = None,
        scoring: Optional[Union[str, Callable]] = None,
        cv: int = 5,
        n_jobs: int = -1,
    ) -> None:
        """
        初始化超參數調優器

        Args:
            model_type: 模型類型，必須是 model_factory 支援的類型
            param_grid: 參數網格，定義搜索空間
            experiment_name: MLflow 實驗名稱，用於組織實驗
            tracking_uri: MLflow 追蹤伺服器 URI，None 表示使用本地
            scoring: 評分函數或指標名稱，None 表示使用預設指標
            cv: 交叉驗證折數，必須 >= 2
            n_jobs: 並行任務數，-1 表示使用所有 CPU 核心
            
        Raises:
            ValueError: 當參數格式不正確時
            TypeError: 當參數類型不正確時
            RuntimeError: 當 MLflow 初始化失敗時
            
        Example:
            >>> tuner = HyperparameterTuner(
            ...     model_type="xgboost",
            ...     param_grid={"n_estimators": [100, 200], "learning_rate": [0.01, 0.1]}
            ... )
        """
        # 驗證輸入參數
        if not isinstance(model_type, str) or not model_type.strip():
            raise ValueError("model_type 必須是非空字串")
            
        if cv < 2:
            raise ValueError("cv 必須 >= 2")
            
        validate_param_grid(param_grid)
        
        self.model_type = model_type
        self.param_grid = param_grid
        self.experiment_name = experiment_name
        self.tracking_uri = tracking_uri
        self.scoring = scoring
        self.cv = cv
        self.n_jobs = n_jobs

        # 初始化 MLflow
        try:
            if tracking_uri:
                mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment(experiment_name)
        except Exception as e:
            logger.error(f"初始化 MLflow 時發生錯誤: {e}")
            raise RuntimeError(f"MLflow 初始化失敗: {e}") from e

        # 調優結果
        self.best_params: Optional[Dict[str, Any]] = None
        self.best_score: Optional[float] = None
        self.results: Optional[pd.DataFrame] = None
        self.run_id: Optional[str] = None

    @abstractmethod
    def optimize(
        self, 
        X: pd.DataFrame, 
        y: pd.Series, 
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        執行超參數優化
        
        Args:
            X: 特徵資料
            y: 目標變數
            **kwargs: 額外參數
            
        Returns:
            優化結果字典
            
        Note:
            子類別必須實現此方法
        """
        pass

    def get_best_params(self) -> Optional[Dict[str, Any]]:
        """
        獲取最佳參數
        
        Returns:
            最佳參數字典，如果尚未執行優化則返回 None
            
        Example:
            >>> best_params = tuner.get_best_params()
            >>> print(best_params)
        """
        return self.best_params

    def get_best_score(self) -> Optional[float]:
        """
        獲取最佳分數
        
        Returns:
            最佳分數，如果尚未執行優化則返回 None
            
        Example:
            >>> best_score = tuner.get_best_score()
            >>> print(f"Best score: {best_score:.4f}")
        """
        return self.best_score

    def get_results(self) -> Optional[pd.DataFrame]:
        """
        獲取完整優化結果
        
        Returns:
            結果資料框，如果尚未執行優化則返回 None
            
        Example:
            >>> results = tuner.get_results()
            >>> print(results.head())
        """
        return self.results

    def summary(self) -> Dict[str, Any]:
        """
        獲取優化結果摘要
        
        Returns:
            包含關鍵資訊的摘要字典
            
        Example:
            >>> summary = tuner.summary()
            >>> print(f"Best score: {summary['best_score']}")
        """
        return {
            "model_type": self.model_type,
            "best_params": self.best_params,
            "best_score": self.best_score,
            "n_trials": len(self.results) if self.results is not None else 0,
            "cv_folds": self.cv,
            "scoring": str(self.scoring),
            "run_id": self.run_id
        }

    def __repr__(self) -> str:
        """字串表示"""
        return (
            f"{self.__class__.__name__}("
            f"model_type='{self.model_type}', "
            f"cv={self.cv}, "
            f"scoring='{self.scoring}'"
            f")"
        )
