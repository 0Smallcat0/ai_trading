# -*- coding: utf-8 -*-
"""
AI 模型模組 - 恢復版本

此模組提供基本的AI模型功能，包括：
- 模型工廠
- 訓練管道
- 性能指標計算

版本: 1.0.0
"""

# 基本模型組件
from .model_factory import create_model, register_model, get_available_models
from .training_pipeline import ModelTrainer, create_trainer, train_model, cross_validate_model

__version__ = "1.0.0"
__author__ = "AI Trading System Team"

# 導出功能
__all__ = [
    # 模型工廠
    "create_model",
    "register_model",
    "get_available_models",

    # 訓練管道
    "ModelTrainer",
    "create_trainer",
    "train_model",
    "cross_validate_model",

    # 性能指標
    "performance_metrics"
]
