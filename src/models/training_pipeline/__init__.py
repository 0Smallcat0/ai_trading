# -*- coding: utf-8 -*-
"""
模型訓練管道模組

此模組提供標準化的模型訓練流程，包括：
- 模型訓練器 (ModelTrainer)
- 交叉驗證器 (CrossValidator)
- 模型評估器 (ModelEvaluator)
- 訓練配置管理 (TrainingConfig)

Classes:
    ModelTrainer: 主要的模型訓練器
    CrossValidator: 交叉驗證器
    ModelEvaluator: 模型評估器
    TrainingConfig: 訓練配置管理器

Functions:
    create_trainer: 創建模型訓練器
    train_model: 訓練模型（便利函數）
    cross_validate_model: 交叉驗證模型（便利函數）
    evaluate_model: 評估模型（便利函數）

Example:
    >>> from src.models.training_pipeline import ModelTrainer, create_trainer
    >>> trainer = create_trainer(model, experiment_name="my_experiment")
    >>> results = trainer.train(X_train, y_train, X_val, y_val)
    >>> cv_results = trainer.cross_validate(X, y, cv=5)

Note:
    所有訓練過程都整合 MLflow 進行實驗追蹤
    支援時間序列和常規交叉驗證
    提供模型接受標準檢查功能
"""

from .trainer import ModelTrainer
from .cross_validator import CrossValidator
from .evaluator import ModelEvaluator
from .config import TrainingConfig
from .utils import (
    validate_training_inputs,
    setup_mlflow_tracking,
    save_training_artifacts,
    check_acceptance_criteria
)

# 向後兼容的導入
from .legacy_interface import ModelTrainer as LegacyModelTrainer

__all__ = [
    # Core classes
    "ModelTrainer",
    "CrossValidator",
    "ModelEvaluator",
    "TrainingConfig",

    # Utility functions
    "validate_training_inputs",
    "setup_mlflow_tracking",
    "save_training_artifacts",
    "check_acceptance_criteria",

    # Legacy compatibility
    "LegacyModelTrainer"
]

# 版本資訊
__version__ = "1.0.0"
__author__ = "AI Trading System Team"


def create_trainer(
    model,
    experiment_name: str = "default",
    tracking_uri: str = None,
    metrics_threshold: dict = None,
    config: TrainingConfig = None
) -> ModelTrainer:
    """
    創建模型訓練器

    Args:
        model: 要訓練的模型實例
        experiment_name: MLflow 實驗名稱
        tracking_uri: MLflow 追蹤伺服器 URI
        metrics_threshold: 指標閾值字典
        config: 訓練配置實例

    Returns:
        ModelTrainer 實例

    Example:
        >>> trainer = create_trainer(
        ...     model=my_model,
        ...     experiment_name="production_training",
        ...     metrics_threshold={"sharpe_ratio": 1.5}
        ... )
    """
    if config is None:
        config = TrainingConfig(
            experiment_name=experiment_name,
            tracking_uri=tracking_uri,
            metrics_threshold=metrics_threshold
        )

    return ModelTrainer(model, config)


def train_model(
    model,
    X_train,
    y_train,
    X_val=None,
    y_val=None,
    experiment_name: str = "default",
    log_to_mlflow: bool = True,
    **train_params
) -> dict:
    """
    訓練模型（便利函數）

    Args:
        model: 要訓練的模型實例
        X_train: 訓練特徵
        y_train: 訓練目標
        X_val: 驗證特徵（可選）
        y_val: 驗證目標（可選）
        experiment_name: MLflow 實驗名稱
        log_to_mlflow: 是否記錄到 MLflow
        **train_params: 其他訓練參數

    Returns:
        訓練結果字典

    Example:
        >>> results = train_model(
        ...     model=my_model,
        ...     X_train=X_train,
        ...     y_train=y_train,
        ...     X_val=X_val,
        ...     y_val=y_val
        ... )
    """
    trainer = create_trainer(model, experiment_name)
    return trainer.train(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        log_to_mlflow=log_to_mlflow,
        **train_params
    )


def cross_validate_model(
    model,
    X,
    y,
    cv: int = 5,
    time_series: bool = True,
    experiment_name: str = "default",
    log_to_mlflow: bool = True,
    **train_params
) -> dict:
    """
    交叉驗證模型（便利函數）

    Args:
        model: 要驗證的模型實例
        X: 特徵資料
        y: 目標資料
        cv: 折數
        time_series: 是否使用時間序列分割
        experiment_name: MLflow 實驗名稱
        log_to_mlflow: 是否記錄到 MLflow
        **train_params: 其他訓練參數

    Returns:
        交叉驗證結果字典

    Example:
        >>> cv_results = cross_validate_model(
        ...     model=my_model,
        ...     X=X,
        ...     y=y,
        ...     cv=5,
        ...     time_series=True
        ... )
    """
    trainer = create_trainer(model, experiment_name)
    return trainer.cross_validate(
        X=X,
        y=y,
        cv=cv,
        time_series=time_series,
        log_to_mlflow=log_to_mlflow,
        **train_params
    )


def evaluate_model(
    model,
    X_test,
    y_test,
    experiment_name: str = "default",
    log_to_mlflow: bool = True
) -> dict:
    """
    評估模型（便利函數）

    Args:
        model: 要評估的模型實例
        X_test: 測試特徵
        y_test: 測試目標
        experiment_name: MLflow 實驗名稱
        log_to_mlflow: 是否記錄到 MLflow

    Returns:
        評估結果字典

    Example:
        >>> test_results = evaluate_model(
        ...     model=trained_model,
        ...     X_test=X_test,
        ...     y_test=y_test
        ... )
    """
    trainer = create_trainer(model, experiment_name)
    return trainer.evaluate_on_test(
        X_test=X_test,
        y_test=y_test,
        log_to_mlflow=log_to_mlflow
    )
