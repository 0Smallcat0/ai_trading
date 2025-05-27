# -*- coding: utf-8 -*-
"""
模型訓練管道 (向後兼容)

此模組提供模型訓練管道功能的向後兼容介面。
新的模組化實現位於 training_pipeline 子模組中。

Classes:
    ModelTrainer: 模型訓練器（向後兼容）

Functions:
    create_trainer: 創建模型訓練器
    train_model: 訓練模型（便利函數）
    cross_validate_model: 交叉驗證模型（便利函數）
    evaluate_model: 評估模型（便利函數）

Example:
    >>> from src.models.training_pipeline import ModelTrainer
    >>> trainer = ModelTrainer(model, experiment_name="my_experiment")
    >>> results = trainer.train(X_train, y_train, X_val, y_val)

Note:
    建議使用新的模組化介面：
    from src.models.training_pipeline import ModelTrainer, create_trainer
"""

import warnings
from typing import Any, Dict, Optional

import pandas as pd

# 導入新的模組化實現
from .training_pipeline.legacy_interface import ModelTrainer
from .training_pipeline import (
    create_trainer,
    train_model,
    cross_validate_model,
    evaluate_model,
)
from .training_pipeline.trainer import ModelTrainer as NewModelTrainer
from .training_pipeline.cross_validator import CrossValidator
from .training_pipeline.config import TrainingConfig

# 向後兼容的導出
__all__ = [
    # Legacy classes
    "ModelTrainer",
    # New modular classes
    "NewModelTrainer",
    "CrossValidator",
    "TrainingConfig",
    # Convenience functions
    "create_trainer",
    "train_model",
    "cross_validate_model",
    "evaluate_model",
]
