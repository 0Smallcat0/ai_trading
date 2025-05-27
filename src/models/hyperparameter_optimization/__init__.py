# -*- coding: utf-8 -*-
"""
超參數優化模組

此模組提供完整的超參數優化功能，包括：
- 網格搜索 (Grid Search)
- 隨機搜索 (Random Search)  
- 貝葉斯優化 (Bayesian Optimization)
- 結果視覺化和分析

Classes:
    HyperparameterTuner: 主要的超參數調優器
    GridSearchOptimizer: 網格搜索優化器
    RandomSearchOptimizer: 隨機搜索優化器
    BayesianOptimizer: 貝葉斯優化器

Functions:
    create_tuner: 創建調優器的工廠函數
    compare_optimization_methods: 比較不同優化方法的性能

Example:
    >>> from src.models.hyperparameter_optimization import HyperparameterTuner
    >>> tuner = HyperparameterTuner(
    ...     model_type="random_forest",
    ...     param_grid={"n_estimators": [100, 200], "max_depth": [5, 10]}
    ... )
    >>> results = tuner.grid_search(X_train, y_train)
"""

from .base import HyperparameterTuner
from .grid_search import GridSearchOptimizer
from .random_search import RandomSearchOptimizer
from .bayesian_optimization import BayesianOptimizer
from .utils import (
    validate_param_grid,
    log_tuning_params,
    save_results,
    plot_param_importance,
    compare_optimization_methods
)

__all__ = [
    "HyperparameterTuner",
    "GridSearchOptimizer", 
    "RandomSearchOptimizer",
    "BayesianOptimizer",
    "validate_param_grid",
    "log_tuning_params",
    "save_results",
    "plot_param_importance",
    "compare_optimization_methods"
]

# 版本資訊
__version__ = "1.0.0"
__author__ = "AI Trading System Team"
