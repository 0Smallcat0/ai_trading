# -*- coding: utf-8 -*-
"""
模型訓練管道模組

此模組提供標準化的模型訓練流程，包括：
- 資料準備
- 模型訓練
- 模型評估
- 模型保存
- 交叉驗證
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import cross_val_score, KFold, TimeSeriesSplit
import mlflow
import mlflow.sklearn
import mlflow.tensorflow
import mlflow.xgboost
import mlflow.lightgbm

from src.config import LOG_LEVEL, MODELS_DIR
from src.models.model_base import ModelBase
from src.models.model_factory import create_model
from src.models.dataset import TimeSeriesSplit as TSS, FeatureProcessor
from src.models.performance_metrics import (
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_calmar_ratio,
    calculate_max_drawdown,
    calculate_win_rate,
    calculate_pnl_ratio,
    calculate_all_metrics
)

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class ModelTrainer:
    """
    模型訓練器

    提供標準化的模型訓練流程。
    """

    def __init__(
        self,
        model: ModelBase,
        experiment_name: str = "default",
        tracking_uri: Optional[str] = None,
        metrics_threshold: Optional[Dict[str, float]] = None
    ):
        """
        初始化模型訓練器

        Args:
            model (ModelBase): 要訓練的模型
            experiment_name (str): MLflow 實驗名稱
            tracking_uri (Optional[str]): MLflow 追蹤伺服器 URI
            metrics_threshold (Optional[Dict[str, float]]): 指標閾值，用於模型接受標準
        """
        self.model = model
        self.experiment_name = experiment_name
        self.tracking_uri = tracking_uri
        self.metrics_threshold = metrics_threshold or {
            "sharpe_ratio": 1.2,
            "max_drawdown": -0.2,
            "win_rate": 0.55
        }
        
        # 初始化 MLflow
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
        mlflow.set_experiment(experiment_name)
        
        # 訓練結果
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
        **train_params
    ) -> Dict[str, Any]:
        """
        訓練模型

        Args:
            X_train (pd.DataFrame): 訓練特徵
            y_train (pd.Series): 訓練目標
            X_val (Optional[pd.DataFrame]): 驗證特徵
            y_val (Optional[pd.Series]): 驗證目標
            log_to_mlflow (bool): 是否記錄到 MLflow
            **train_params: 其他訓練參數

        Returns:
            Dict[str, Any]: 訓練結果
        """
        # 開始 MLflow 追蹤
        if log_to_mlflow:
            mlflow.start_run()
            self.run_id = mlflow.active_run().info.run_id
            
            # 記錄模型參數
            mlflow.log_params(self.model.get_params())
            
            # 記錄訓練參數
            for key, value in train_params.items():
                mlflow.log_param(key, value)
        
        try:
            # 訓練模型
            logger.info(f"開始訓練模型: {self.model.name}")
            train_result = self.model.train(X_train, y_train, **train_params)
            
            # 評估訓練集表現
            self.train_metrics = self.model.evaluate(X_train, y_train)
            logger.info(f"訓練集評估結果: {self.train_metrics}")
            
            # 評估驗證集表現
            if X_val is not None and y_val is not None:
                self.val_metrics = self.model.evaluate(X_val, y_val)
                logger.info(f"驗證集評估結果: {self.val_metrics}")
            
            # 獲取特徵重要性
            self.feature_importance = self.model.feature_importance()
            
            # 記錄指標到 MLflow
            if log_to_mlflow:
                # 記錄訓練指標
                for key, value in self.train_metrics.items():
                    mlflow.log_metric(f"train_{key}", value)
                
                # 記錄驗證指標
                for key, value in self.val_metrics.items():
                    mlflow.log_metric(f"val_{key}", value)
                
                # 記錄特徵重要性
                if not self.feature_importance.empty:
                    fig, ax = plt.figure(figsize=(10, 6)), plt.subplot(111)
                    sns.barplot(x="importance", y="feature", data=self.feature_importance, ax=ax)
                    plt.title("Feature Importance")
                    plt.tight_layout()
                    mlflow.log_figure(fig, "feature_importance.png")
                    plt.close(fig)
                
                # 保存模型到 MLflow
                if hasattr(self.model.model, "save_model"):
                    # XGBoost, LightGBM 等
                    model_path = os.path.join(MODELS_DIR, self.model.name, "model")
                    os.makedirs(model_path, exist_ok=True)
                    self.model.model.save_model(os.path.join(model_path, "model.txt"))
                    mlflow.log_artifacts(model_path, "model")
                else:
                    # 使用 MLflow 內建的模型記錄功能
                    if hasattr(mlflow, self.model.__class__.__module__.split(".")[-1]):
                        getattr(mlflow, self.model.__class__.__module__.split(".")[-1]).log_model(
                            self.model.model, "model"
                        )
                    else:
                        mlflow.sklearn.log_model(self.model.model, "model")
            
            # 保存模型
            model_path = self.model.save()
            logger.info(f"模型已保存至: {model_path}")
            
            # 檢查模型是否達到接受標準
            accepted = self._check_acceptance_criteria(self.val_metrics or self.train_metrics)
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
                "run_id": self.run_id
            }
        
        except Exception as e:
            logger.error(f"訓練模型時發生錯誤: {e}")
            if log_to_mlflow:
                mlflow.end_run()
            raise

    def cross_validate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        cv: int = 5,
        time_series: bool = True,
        log_to_mlflow: bool = True,
        **train_params
    ) -> Dict[str, Any]:
        """
        交叉驗證

        Args:
            X (pd.DataFrame): 特徵
            y (pd.Series): 目標
            cv (int): 折數
            time_series (bool): 是否使用時間序列分割
            log_to_mlflow (bool): 是否記錄到 MLflow
            **train_params: 其他訓練參數

        Returns:
            Dict[str, Any]: 交叉驗證結果
        """
        # 選擇分割器
        if time_series:
            splitter = TimeSeriesSplit(n_splits=cv)
        else:
            splitter = KFold(n_splits=cv, shuffle=True, random_state=42)
        
        # 開始 MLflow 追蹤
        if log_to_mlflow:
            mlflow.start_run()
            self.run_id = mlflow.active_run().info.run_id
            
            # 記錄模型參數
            mlflow.log_params(self.model.get_params())
            
            # 記錄交叉驗證參數
            mlflow.log_param("cv", cv)
            mlflow.log_param("time_series", time_series)
            
            # 記錄訓練參數
            for key, value in train_params.items():
                mlflow.log_param(key, value)
        
        try:
            # 執行交叉驗證
            logger.info(f"開始交叉驗證: {self.model.name}, cv={cv}, time_series={time_series}")
            
            cv_results = []
            fold = 1
            
            for train_idx, val_idx in splitter.split(X):
                logger.info(f"訓練折 {fold}/{cv}")
                
                # 分割資料
                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
                
                # 訓練模型
                model_copy = create_model(
                    self.model.__class__.__name__.lower().replace("model", ""),
                    name=f"{self.model.name}_fold{fold}",
                    **self.model.get_params()
                )
                model_copy.train(X_train, y_train, **train_params)
                
                # 評估模型
                train_metrics = model_copy.evaluate(X_train, y_train)
                val_metrics = model_copy.evaluate(X_val, y_val)
                
                # 記錄結果
                result = {
                    "fold": fold,
                    "train_metrics": train_metrics,
                    "val_metrics": val_metrics
                }
                cv_results.append(result)
                
                # 記錄到 MLflow
                if log_to_mlflow:
                    for key, value in train_metrics.items():
                        mlflow.log_metric(f"fold{fold}_train_{key}", value)
                    for key, value in val_metrics.items():
                        mlflow.log_metric(f"fold{fold}_val_{key}", value)
                
                fold += 1
            
            # 計算平均指標
            avg_train_metrics = {}
            avg_val_metrics = {}
            
            for metric in cv_results[0]["train_metrics"].keys():
                avg_train_metrics[metric] = np.mean([r["train_metrics"][metric] for r in cv_results])
                avg_val_metrics[metric] = np.mean([r["val_metrics"][metric] for r in cv_results])
            
            logger.info(f"交叉驗證平均訓練指標: {avg_train_metrics}")
            logger.info(f"交叉驗證平均驗證指標: {avg_val_metrics}")
            
            # 記錄平均指標到 MLflow
            if log_to_mlflow:
                for key, value in avg_train_metrics.items():
                    mlflow.log_metric(f"avg_train_{key}", value)
                for key, value in avg_val_metrics.items():
                    mlflow.log_metric(f"avg_val_{key}", value)
                
                mlflow.end_run()
            
            return {
                "cv_results": cv_results,
                "avg_train_metrics": avg_train_metrics,
                "avg_val_metrics": avg_val_metrics,
                "run_id": self.run_id
            }
        
        except Exception as e:
            logger.error(f"交叉驗證時發生錯誤: {e}")
            if log_to_mlflow:
                mlflow.end_run()
            raise

    def evaluate_on_test(
        self,
        X_test: pd.DataFrame,
        y_test: pd.Series,
        log_to_mlflow: bool = True
    ) -> Dict[str, float]:
        """
        在測試集上評估模型

        Args:
            X_test (pd.DataFrame): 測試特徵
            y_test (pd.Series): 測試目標
            log_to_mlflow (bool): 是否記錄到 MLflow

        Returns:
            Dict[str, float]: 測試指標
        """
        if not self.model.trained:
            logger.error("模型尚未訓練，無法評估")
            raise ValueError("模型尚未訓練，無法評估")
        
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

    def _check_acceptance_criteria(self, metrics: Dict[str, float]) -> bool:
        """
        檢查模型是否達到接受標準

        Args:
            metrics (Dict[str, float]): 模型指標

        Returns:
            bool: 是否達到接受標準
        """
        for metric, threshold in self.metrics_threshold.items():
            if metric not in metrics:
                logger.warning(f"指標 {metric} 不在評估結果中")
                continue
            
            # 檢查是否達到閾值
            if metric in ["max_drawdown"]:
                # 對於最大回撤等負向指標，實際值應小於閾值
                if metrics[metric] < threshold:
                    logger.warning(f"指標 {metric} = {metrics[metric]} 未達到閾值 {threshold}")
                    return False
            else:
                # 對於夏普比率等正向指標，實際值應大於閾值
                if metrics[metric] < threshold:
                    logger.warning(f"指標 {metric} = {metrics[metric]} 未達到閾值 {threshold}")
                    return False
        
        return True
