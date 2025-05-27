# -*- coding: utf-8 -*-
"""
訓練管道工具函數

此模組提供訓練管道過程中使用的工具函數，包括：
- 輸入資料驗證
- MLflow 設定
- 訓練產物保存
- 模型接受標準檢查

Functions:
    validate_training_inputs: 驗證訓練輸入資料
    setup_mlflow_tracking: 設定 MLflow 追蹤
    save_training_artifacts: 保存訓練產物
    check_acceptance_criteria: 檢查模型接受標準
"""

import logging
import os
from typing import Any, Dict, Optional

import mlflow
import mlflow.lightgbm
import mlflow.sklearn
import mlflow.xgboost
import pandas as pd

from src.config import LOG_LEVEL, MODELS_DIR
from src.models.model_base import ModelBase
from .config import TrainingConfig

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))

# TensorFlow 延遲載入以避免 DLL 問題
try:
    import mlflow.tensorflow
    TENSORFLOW_MLFLOW_AVAILABLE = True
except ImportError as e:
    TENSORFLOW_MLFLOW_AVAILABLE = False
    logger.warning(f"MLflow TensorFlow 支援不可用: {e}")


def validate_training_inputs(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: Optional[pd.DataFrame] = None,
    y_val: Optional[pd.Series] = None
) -> None:
    """
    驗證訓練輸入資料格式

    Args:
        X_train: 訓練特徵
        y_train: 訓練目標
        X_val: 驗證特徵（可選）
        y_val: 驗證目標（可選）

    Raises:
        ValueError: 當輸入資料格式不正確時
        TypeError: 當資料類型不正確時

    Example:
        >>> validate_training_inputs(X_train, y_train, X_val, y_val)
    """
    # 檢查訓練資料
    if not isinstance(X_train, pd.DataFrame):
        raise TypeError("X_train 必須是 pandas DataFrame")

    if not isinstance(y_train, pd.Series):
        raise TypeError("y_train 必須是 pandas Series")

    if X_train.empty:
        raise ValueError("X_train 不能為空")

    if y_train.empty:
        raise ValueError("y_train 不能為空")

    if len(X_train) != len(y_train):
        raise ValueError("X_train 和 y_train 的樣本數必須相同")

    # 檢查是否有缺失值
    if X_train.isnull().any().any():
        logger.warning("X_train 包含缺失值")

    if y_train.isnull().any():
        logger.warning("y_train 包含缺失值")

    # 檢查驗證資料（如果提供）
    if X_val is not None or y_val is not None:
        if X_val is None or y_val is None:
            raise ValueError("X_val 和 y_val 必須同時提供或同時為 None")

        if not isinstance(X_val, pd.DataFrame):
            raise TypeError("X_val 必須是 pandas DataFrame")

        if not isinstance(y_val, pd.Series):
            raise TypeError("y_val 必須是 pandas Series")

        if X_val.empty:
            raise ValueError("X_val 不能為空")

        if y_val.empty:
            raise ValueError("y_val 不能為空")

        if len(X_val) != len(y_val):
            raise ValueError("X_val 和 y_val 的樣本數必須相同")

        # 檢查特徵一致性
        if list(X_train.columns) != list(X_val.columns):
            raise ValueError("X_train 和 X_val 的特徵必須相同")

        if X_val.isnull().any().any():
            logger.warning("X_val 包含缺失值")

        if y_val.isnull().any():
            logger.warning("y_val 包含缺失值")

    logger.debug("訓練輸入資料驗證通過")


def setup_mlflow_tracking(config: TrainingConfig) -> None:
    """
    設定 MLflow 追蹤

    Args:
        config: 訓練配置實例

    Example:
        >>> config = TrainingConfig(experiment_name="my_experiment")
        >>> setup_mlflow_tracking(config)
    """
    try:
        # 設定追蹤 URI
        if config.tracking_uri:
            mlflow.set_tracking_uri(config.tracking_uri)
            logger.info(f"MLflow 追蹤 URI 已設定: {config.tracking_uri}")

        # 設定實驗
        mlflow.set_experiment(config.experiment_name)
        logger.info(f"MLflow 實驗已設定: {config.experiment_name}")

    except Exception as e:
        logger.error(f"設定 MLflow 追蹤失敗: {e}")
        raise RuntimeError(f"MLflow 設定失敗: {e}") from e


def save_training_artifacts(
    model: ModelBase,
    run_id: Optional[str] = None
) -> None:
    """
    保存訓練產物到 MLflow

    Args:
        model: 訓練好的模型實例
        run_id: MLflow 運行 ID（可選）

    Example:
        >>> save_training_artifacts(trained_model, run_id)
    """
    try:
        # 確定模型類型並選擇適當的記錄方法
        model_class_name = model.__class__.__name__.lower()

        if hasattr(model.model, "save_model"):
            # XGBoost, LightGBM 等有 save_model 方法的模型
            model_path = os.path.join(MODELS_DIR, model.name, "model")
            os.makedirs(model_path, exist_ok=True)

            model_file_path = os.path.join(model_path, "model.txt")
            model.model.save_model(model_file_path)
            mlflow.log_artifacts(model_path, "model")

            logger.info(f"模型已保存到 MLflow: {model_file_path}")

        elif "xgb" in model_class_name or "xgboost" in model_class_name:
            # XGBoost 模型
            mlflow.xgboost.log_model(model.model, "model")
            logger.info("XGBoost 模型已記錄到 MLflow")

        elif "lgb" in model_class_name or "lightgbm" in model_class_name:
            # LightGBM 模型
            mlflow.lightgbm.log_model(model.model, "model")
            logger.info("LightGBM 模型已記錄到 MLflow")

        elif "tensorflow" in model_class_name or "keras" in model_class_name:
            # TensorFlow/Keras 模型
            if TENSORFLOW_MLFLOW_AVAILABLE:
                mlflow.tensorflow.log_model(model.model, "model")
                logger.info("TensorFlow 模型已記錄到 MLflow")
            else:
                logger.warning("TensorFlow MLflow 支援不可用，跳過 TensorFlow 模型記錄")

        else:
            # 使用 sklearn 作為預設
            mlflow.sklearn.log_model(model.model, "model")
            logger.info("Sklearn 模型已記錄到 MLflow")

        # 記錄模型元數據
        mlflow.log_params({
            "model_name": model.name,
            "model_type": model.__class__.__name__,
            "feature_count": len(model.feature_names) if model.feature_names else 0,
            "target_name": model.target_name
        })

    except Exception as e:
        logger.error(f"保存訓練產物失敗: {e}")
        # 不拋出異常，因為這不是關鍵錯誤


def check_acceptance_criteria(
    metrics: Dict[str, float],
    thresholds: Dict[str, float]
) -> bool:
    """
    檢查模型是否達到接受標準

    Args:
        metrics: 模型指標字典
        thresholds: 接受標準閾值字典

    Returns:
        是否達到接受標準

    Example:
        >>> metrics = {"accuracy": 0.85, "f1": 0.80}
        >>> thresholds = {"accuracy": 0.8, "f1": 0.75}
        >>> accepted = check_acceptance_criteria(metrics, thresholds)
        >>> print(f"Model accepted: {accepted}")
    """
    if not metrics or not thresholds:
        logger.warning("指標或閾值為空，無法檢查接受標準")
        return False

    try:
        passed_criteria = 0
        total_criteria = 0

        for metric, threshold in thresholds.items():
            if metric not in metrics:
                logger.warning(f"指標 {metric} 不在評估結果中")
                continue

            total_criteria += 1
            metric_value = metrics[metric]

            # 檢查是否達到閾值
            if metric in ["max_drawdown", "loss", "error", "mse", "mae"]:
                # 對於負向指標，實際值應小於閾值
                if metric_value <= threshold:
                    passed_criteria += 1
                    logger.info(f"✓ {metric}: {metric_value:.4f} <= {threshold:.4f}")
                else:
                    logger.warning(f"✗ {metric}: {metric_value:.4f} > {threshold:.4f}")
            else:
                # 對於正向指標，實際值應大於等於閾值
                if metric_value >= threshold:
                    passed_criteria += 1
                    logger.info(f"✓ {metric}: {metric_value:.4f} >= {threshold:.4f}")
                else:
                    logger.warning(f"✗ {metric}: {metric_value:.4f} < {threshold:.4f}")

        # 所有標準都必須通過
        acceptance_rate = passed_criteria / total_criteria if total_criteria > 0 else 0
        accepted = passed_criteria == total_criteria

        logger.info(f"接受標準檢查結果: {passed_criteria}/{total_criteria} 通過 ({acceptance_rate:.1%})")

        return accepted

    except Exception as e:
        logger.error(f"檢查接受標準時發生錯誤: {e}")
        return False


def create_model_summary(
    model: ModelBase,
    train_metrics: Dict[str, float],
    val_metrics: Dict[str, float],
    test_metrics: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    創建模型摘要

    Args:
        model: 模型實例
        train_metrics: 訓練指標
        val_metrics: 驗證指標
        test_metrics: 測試指標（可選）

    Returns:
        模型摘要字典

    Example:
        >>> summary = create_model_summary(model, train_metrics, val_metrics)
        >>> print(f"Model: {summary['model_name']}")
    """
    try:
        summary = {
            "model_name": model.name,
            "model_type": model.__class__.__name__,
            "trained": model.trained,
            "feature_count": len(model.feature_names) if model.feature_names else 0,
            "target_name": model.target_name,
            "train_metrics": train_metrics,
            "val_metrics": val_metrics,
            "test_metrics": test_metrics or {},
            "has_feature_importance": hasattr(model, 'feature_importance'),
            "model_params": model.get_params()
        }

        # 計算改進指標
        if train_metrics and val_metrics:
            # 計算過擬合程度
            common_metrics = set(train_metrics.keys()) & set(val_metrics.keys())
            overfit_scores = {}

            for metric in common_metrics:
                train_val = train_metrics[metric]
                val_val = val_metrics[metric]

                if metric in ["accuracy", "f1", "precision", "recall", "r2"]:
                    # 正向指標：訓練分數 - 驗證分數
                    overfit_scores[metric] = train_val - val_val
                elif metric in ["loss", "mse", "mae"]:
                    # 負向指標：驗證分數 - 訓練分數
                    overfit_scores[metric] = val_val - train_val

            summary["overfit_analysis"] = overfit_scores

        return summary

    except Exception as e:
        logger.error(f"創建模型摘要失敗: {e}")
        return {
            "model_name": getattr(model, 'name', 'unknown'),
            "error": str(e)
        }


def format_metrics_for_display(metrics: Dict[str, float]) -> str:
    """
    格式化指標用於顯示

    Args:
        metrics: 指標字典

    Returns:
        格式化的指標字串

    Example:
        >>> metrics = {"accuracy": 0.8567, "f1": 0.7234}
        >>> formatted = format_metrics_for_display(metrics)
        >>> print(formatted)  # "accuracy: 0.857, f1: 0.723"
    """
    if not metrics:
        return "No metrics available"

    formatted_items = []
    for metric, value in metrics.items():
        if isinstance(value, float):
            formatted_items.append(f"{metric}: {value:.3f}")
        else:
            formatted_items.append(f"{metric}: {value}")

    return ", ".join(formatted_items)
