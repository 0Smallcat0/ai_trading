# -*- coding: utf-8 -*-
"""
訓練管道向後兼容介面

此模組提供與原始 training_pipeline.py 相容的介面，
確保現有代碼可以無縫遷移到新的模組化實現。

Classes:
    ModelTrainer: 向後兼容的模型訓練器
"""

import logging
import warnings
from typing import Any, Dict, Optional

import pandas as pd

from src.config import LOG_LEVEL
from src.models.model_base import ModelBase
from .trainer import ModelTrainer as NewModelTrainer
from .cross_validator import CrossValidator
from .config import TrainingConfig

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class ModelTrainer:
    """
    模型訓練器 (向後兼容)

    此類別提供與原始 ModelTrainer 相同的介面，
    內部委託給新的模組化實現。

    Example:
        >>> trainer = ModelTrainer(model, experiment_name="my_experiment")
        >>> results = trainer.train(X_train, y_train, X_val, y_val)
        >>> cv_results = trainer.cross_validate(X, y, cv=5)
    """

    def __init__(
        self,
        model: ModelBase,
        experiment_name: str = "default",
        tracking_uri: Optional[str] = None,
        metrics_threshold: Optional[Dict[str, float]] = None,
    ):
        """
        初始化模型訓練器 (向後兼容)

        Args:
            model: 要訓練的模型
            experiment_name: MLflow 實驗名稱
            tracking_uri: MLflow 追蹤伺服器 URI
            metrics_threshold: 指標閾值，用於模型接受標準
        """
        # 發出遷移警告
        warnings.warn(
            "使用舊版 ModelTrainer 介面。建議遷移到新的模組化介面。",
            DeprecationWarning,
            stacklevel=2,
        )

        # 創建訓練配置
        self.config = TrainingConfig(
            experiment_name=experiment_name,
            tracking_uri=tracking_uri,
            metrics_threshold=metrics_threshold
            or {
                "sharpe_ratio": 1.2,
                "max_drawdown": -0.2,
                "win_rate": 0.55,
            },
        )

        # 委託給新實現
        self._new_trainer = NewModelTrainer(model, self.config)
        self._cross_validator = CrossValidator(model, self.config)

        # 向後兼容的屬性
        self.model = model
        self.experiment_name = experiment_name
        self.tracking_uri = tracking_uri
        self.metrics_threshold = self.config.metrics_threshold

        # 訓練結果（向後兼容）
        self.train_metrics = {}
        self.val_metrics = {}
        self.test_metrics = {}
        self.feature_importance = None
        self.run_id = None

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        log_to_mlflow: bool = True,
        **train_params: Any,
    ) -> Dict[str, Any]:
        """
        訓練模型 (向後兼容)

        Args:
            X_train: 訓練特徵
            y_train: 訓練目標
            X_val: 驗證特徵
            y_val: 驗證目標
            log_to_mlflow: 是否記錄到 MLflow
            **train_params: 其他訓練參數

        Returns:
            訓練結果字典
        """
        # 委託給新實現
        results = self._new_trainer.train(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            log_to_mlflow=log_to_mlflow,
            **train_params,
        )

        # 更新向後兼容的屬性
        self.train_metrics = results.get("train_metrics", {})
        self.val_metrics = results.get("val_metrics", {})
        self.feature_importance = results.get("feature_importance")
        self.run_id = results.get("run_id")

        return results

    def cross_validate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        cv: int = 5,
        time_series: bool = True,
        log_to_mlflow: bool = True,
        **train_params: Any,
    ) -> Dict[str, Any]:
        """
        交叉驗證 (向後兼容)

        Args:
            X: 特徵
            y: 目標
            cv: 折數
            time_series: 是否使用時間序列分割
            log_to_mlflow: 是否記錄到 MLflow
            **train_params: 其他訓練參數

        Returns:
            交叉驗證結果字典
        """
        # 委託給新實現
        results = self._cross_validator.cross_validate(
            X=X,
            y=y,
            cv=cv,
            time_series=time_series,
            log_to_mlflow=log_to_mlflow,
            **train_params,
        )

        # 更新向後兼容的屬性
        self.run_id = results.get("run_id")

        # 轉換結果格式以保持向後兼容
        legacy_results = {
            "cv_results": results.get("cv_results", []),
            "avg_train_metrics": results.get("statistics", {}).get(
                "avg_train_metrics", {}
            ),
            "avg_val_metrics": results.get("statistics", {}).get("avg_val_metrics", {}),
            "run_id": results.get("run_id"),
        }

        return legacy_results

    def evaluate_on_test(
        self, X_test: pd.DataFrame, y_test: pd.Series, log_to_mlflow: bool = True
    ) -> Dict[str, float]:
        """
        在測試集上評估模型 (向後兼容)

        Args:
            X_test: 測試特徵
            y_test: 測試目標
            log_to_mlflow: 是否記錄到 MLflow

        Returns:
            測試指標字典
        """
        # 委託給新實現
        test_metrics = self._new_trainer.evaluate_on_test(
            X_test=X_test, y_test=y_test, log_to_mlflow=log_to_mlflow
        )

        # 更新向後兼容的屬性
        self.test_metrics = test_metrics

        return test_metrics

    def _check_acceptance_criteria(self, metrics: Dict[str, float]) -> bool:
        """
        檢查模型是否達到接受標準 (向後兼容)

        Args:
            metrics: 模型指標

        Returns:
            是否達到接受標準
        """
        from .utils import check_acceptance_criteria

        return check_acceptance_criteria(metrics, self.metrics_threshold)

    # 提供對新功能的訪問
    @property
    def new_trainer(self) -> NewModelTrainer:
        """獲取新的訓練器實例"""
        return self._new_trainer

    @property
    def cross_validator(self) -> CrossValidator:
        """獲取交叉驗證器實例"""
        return self._cross_validator

    @property
    def training_config(self) -> TrainingConfig:
        """獲取訓練配置"""
        return self.config

    def get_training_summary(self) -> Dict[str, Any]:
        """
        獲取訓練摘要 (新功能)

        Returns:
            訓練摘要字典
        """
        return self._new_trainer.get_training_summary()

    def update_config(self, **kwargs: Any) -> None:
        """
        更新訓練配置 (新功能)

        Args:
            **kwargs: 要更新的配置參數
        """
        self.config.update(**kwargs)

        # 更新向後兼容的屬性
        self.metrics_threshold = self.config.metrics_threshold
