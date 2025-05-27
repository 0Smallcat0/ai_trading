# -*- coding: utf-8 -*-
"""
模型訓練器

此模組實現核心的模型訓練功能，包括：
- 標準化訓練流程
- MLflow 實驗追蹤
- 模型保存和載入
- 訓練結果評估

Classes:
    ModelTrainer: 主要的模型訓練器類別
"""

import logging
import os
from typing import Any, Dict, Optional

import matplotlib.pyplot as plt
import mlflow
import pandas as pd
import seaborn as sns

from src.config import LOG_LEVEL, MODELS_DIR
from src.models.model_base import ModelBase
from .config import TrainingConfig
from .utils import (
    validate_training_inputs,
    setup_mlflow_tracking,
    save_training_artifacts,
    check_acceptance_criteria
)

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class ModelTrainer:
    """
    模型訓練器
    
    提供標準化的模型訓練流程，整合 MLflow 實驗追蹤。
    
    Attributes:
        model: 要訓練的模型實例
        config: 訓練配置
        train_metrics: 訓練指標
        val_metrics: 驗證指標
        test_metrics: 測試指標
        feature_importance: 特徵重要性
        run_id: MLflow 運行 ID
        
    Example:
        >>> config = TrainingConfig(experiment_name="my_experiment")
        >>> trainer = ModelTrainer(model, config)
        >>> results = trainer.train(X_train, y_train, X_val, y_val)
        
    Note:
        所有訓練過程都會自動記錄到 MLflow
        支援模型接受標準檢查
        提供完整的訓練結果追蹤
    """

    def __init__(self, model: ModelBase, config: TrainingConfig):
        """
        初始化模型訓練器

        Args:
            model: 要訓練的模型實例
            config: 訓練配置實例
            
        Raises:
            ValueError: 當模型或配置無效時
        """
        if not isinstance(model, ModelBase):
            raise ValueError("model 必須是 ModelBase 的實例")
        
        if not isinstance(config, TrainingConfig):
            raise ValueError("config 必須是 TrainingConfig 的實例")

        self.model = model
        self.config = config

        # 初始化 MLflow
        setup_mlflow_tracking(config)

        # 訓練結果
        self.train_metrics: Dict[str, float] = {}
        self.val_metrics: Dict[str, float] = {}
        self.test_metrics: Dict[str, float] = {}
        self.feature_importance: Optional[pd.DataFrame] = None
        self.run_id: Optional[str] = None

        logger.info(f"模型訓練器已初始化: {model.name}")

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        log_to_mlflow: bool = True,
        **train_params: Any
    ) -> Dict[str, Any]:
        """
        訓練模型
        
        Args:
            X_train: 訓練特徵
            y_train: 訓練目標
            X_val: 驗證特徵（可選）
            y_val: 驗證目標（可選）
            log_to_mlflow: 是否記錄到 MLflow
            **train_params: 其他訓練參數
            
        Returns:
            訓練結果字典
            
        Raises:
            ValueError: 當輸入資料無效時
            RuntimeError: 當訓練失敗時
            
        Example:
            >>> results = trainer.train(
            ...     X_train=X_train,
            ...     y_train=y_train,
            ...     X_val=X_val,
            ...     y_val=y_val,
            ...     epochs=100
            ... )
        """
        try:
            # 驗證輸入
            validate_training_inputs(X_train, y_train, X_val, y_val)

            # 開始 MLflow 追蹤
            if log_to_mlflow:
                mlflow.start_run()
                self.run_id = mlflow.active_run().info.run_id

                # 記錄模型參數
                mlflow.log_params(self.model.get_params())

                # 記錄訓練參數
                for key, value in train_params.items():
                    mlflow.log_param(key, value)

                # 記錄配置參數
                mlflow.log_params(self.config.to_dict())

            # 訓練模型
            logger.info(f"開始訓練模型: {self.model.name}")
            self.model.train(X_train, y_train, **train_params)

            # 評估訓練集表現
            self.train_metrics = self.model.evaluate(X_train, y_train)
            logger.info(f"訓練集評估結果: {self.train_metrics}")

            # 評估驗證集表現
            if X_val is not None and y_val is not None:
                self.val_metrics = self.model.evaluate(X_val, y_val)
                logger.info(f"驗證集評估結果: {self.val_metrics}")

            # 獲取特徵重要性
            try:
                self.feature_importance = self.model.feature_importance()
            except Exception as e:
                logger.warning(f"無法獲取特徵重要性: {e}")
                self.feature_importance = pd.DataFrame()

            # 記錄指標到 MLflow
            if log_to_mlflow:
                self._log_metrics_to_mlflow()
                self._log_feature_importance_to_mlflow()
                self._save_model_to_mlflow()

            # 保存模型
            model_path = self.model.save()
            logger.info(f"模型已保存至: {model_path}")

            # 檢查模型是否達到接受標準
            metrics_to_check = self.val_metrics or self.train_metrics
            accepted = check_acceptance_criteria(
                metrics_to_check, 
                self.config.metrics_threshold
            )
            
            if accepted:
                logger.info("模型達到接受標準")
            else:
                logger.warning("模型未達到接受標準")

            if log_to_mlflow:
                mlflow.log_param("accepted", accepted)
                mlflow.end_run()

            return {
                "train_metrics": self.train_metrics,
                "val_metrics": self.val_metrics,
                "feature_importance": self.feature_importance,
                "model_path": model_path,
                "accepted": accepted,
                "run_id": self.run_id,
            }

        except Exception as e:
            logger.error(f"訓練模型時發生錯誤: {e}")
            if log_to_mlflow and mlflow.active_run():
                mlflow.end_run()
            raise RuntimeError(f"模型訓練失敗: {e}") from e

    def evaluate_on_test(
        self, 
        X_test: pd.DataFrame, 
        y_test: pd.Series, 
        log_to_mlflow: bool = True
    ) -> Dict[str, float]:
        """
        在測試集上評估模型
        
        Args:
            X_test: 測試特徵
            y_test: 測試目標
            log_to_mlflow: 是否記錄到 MLflow
            
        Returns:
            測試指標字典
            
        Raises:
            ValueError: 當模型未訓練時
            
        Example:
            >>> test_metrics = trainer.evaluate_on_test(X_test, y_test)
            >>> print(f"Test accuracy: {test_metrics.get('accuracy', 'N/A')}")
        """
        if not self.model.trained:
            raise ValueError("模型尚未訓練，無法評估")

        try:
            # 驗證輸入
            validate_training_inputs(X_test, y_test)

            # 評估模型
            logger.info(f"在測試集上評估模型: {self.model.name}")
            self.test_metrics = self.model.evaluate(X_test, y_test)
            logger.info(f"測試集評估結果: {self.test_metrics}")

            # 記錄到 MLflow
            if log_to_mlflow and self.run_id:
                with mlflow.start_run(run_id=self.run_id):
                    for key, value in self.test_metrics.items():
                        mlflow.log_metric(f"test_{key}", value)

            return self.test_metrics
            
        except Exception as e:
            logger.error(f"測試集評估時發生錯誤: {e}")
            raise RuntimeError(f"測試集評估失敗: {e}") from e

    def _log_metrics_to_mlflow(self) -> None:
        """記錄指標到 MLflow"""
        try:
            # 記錄訓練指標
            for key, value in self.train_metrics.items():
                mlflow.log_metric(f"train_{key}", value)

            # 記錄驗證指標
            for key, value in self.val_metrics.items():
                mlflow.log_metric(f"val_{key}", value)
                
        except Exception as e:
            logger.warning(f"記錄指標到 MLflow 失敗: {e}")

    def _log_feature_importance_to_mlflow(self) -> None:
        """記錄特徵重要性到 MLflow"""
        try:
            if self.feature_importance is not None and not self.feature_importance.empty:
                # 創建特徵重要性圖表
                fig, ax = plt.subplots(figsize=(10, 6))
                sns.barplot(
                    x="importance", 
                    y="feature", 
                    data=self.feature_importance.head(20),  # 只顯示前20個特徵
                    ax=ax
                )
                ax.set_title("Top 20 Feature Importance")
                plt.tight_layout()
                
                # 記錄圖表
                mlflow.log_figure(fig, "feature_importance.png")
                plt.close(fig)
                
                # 保存特徵重要性資料
                importance_path = os.path.join(MODELS_DIR, "feature_importance.csv")
                os.makedirs(os.path.dirname(importance_path), exist_ok=True)
                self.feature_importance.to_csv(importance_path, index=False)
                mlflow.log_artifact(importance_path, "feature_importance")
                
        except Exception as e:
            logger.warning(f"記錄特徵重要性到 MLflow 失敗: {e}")

    def _save_model_to_mlflow(self) -> None:
        """保存模型到 MLflow"""
        try:
            save_training_artifacts(self.model, self.run_id)
        except Exception as e:
            logger.warning(f"保存模型到 MLflow 失敗: {e}")

    def get_training_summary(self) -> Dict[str, Any]:
        """
        獲取訓練摘要
        
        Returns:
            訓練摘要字典
            
        Example:
            >>> summary = trainer.get_training_summary()
            >>> print(f"Model: {summary['model_name']}")
            >>> print(f"Best metric: {summary['best_metric']}")
        """
        return {
            "model_name": self.model.name,
            "model_type": self.model.__class__.__name__,
            "trained": self.model.trained,
            "train_metrics": self.train_metrics,
            "val_metrics": self.val_metrics,
            "test_metrics": self.test_metrics,
            "has_feature_importance": (
                self.feature_importance is not None and 
                not self.feature_importance.empty
            ),
            "run_id": self.run_id,
            "config": self.config.to_dict()
        }
