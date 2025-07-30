# -*- coding: utf-8 -*-
"""
超參數優化工具函數

此模組提供超參數優化過程中使用的工具函數，包括：
- 參數驗證
- 結果記錄
- 視覺化功能
- 比較分析

Functions:
    validate_param_grid: 驗證參數網格格式
    log_tuning_params: 記錄調優參數到 MLflow
    save_results: 保存調優結果
    plot_param_importance: 繪製參數重要性圖
    compare_optimization_methods: 比較不同優化方法
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Union

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
import seaborn as sns

from src.config import LOG_LEVEL

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


def validate_param_grid(param_grid: Dict[str, Any]) -> None:
    """
    驗證參數網格格式

    Args:
        param_grid: 參數網格字典

    Raises:
        ValueError: 當參數網格格式不正確時

    Example:
        >>> validate_param_grid({"n_estimators": [100, 200]})
    """
    if not isinstance(param_grid, dict):
        raise ValueError("參數網格必須是字典格式")

    if not param_grid:
        raise ValueError("參數網格不能為空")

    for param, values in param_grid.items():
        if not isinstance(param, str):
            raise ValueError(f"參數名稱必須是字串: {param}")

        if not isinstance(values, (list, tuple)):
            raise ValueError(f"參數值必須是列表或元組: {param}")

        if len(values) == 0:
            raise ValueError(f"參數值不能為空: {param}")


def log_tuning_params(
    method: str,
    model_type: str,
    param_grid: Dict[str, Any],
    cv: int,
    scoring: Optional[Union[str, Callable]],
    **kwargs: Any,
) -> None:
    """
    記錄調優參數到 MLflow

    Args:
        method: 調優方法名稱
        model_type: 模型類型
        param_grid: 參數網格
        cv: 交叉驗證折數
        scoring: 評分函數
        **kwargs: 其他參數

    Example:
        >>> log_tuning_params("grid_search", "random_forest", param_grid, 5, "accuracy")
    """
    mlflow.log_param("tuning_method", method)
    mlflow.log_param("model_type", model_type)
    mlflow.log_param("cv", cv)
    mlflow.log_param("scoring", str(scoring))

    # 記錄參數網格
    for param, values in param_grid.items():
        mlflow.log_param(f"param_grid_{param}", str(values))

    # 記錄其他參數
    for key, value in kwargs.items():
        mlflow.log_param(key, value)


def save_results(
    results: pd.DataFrame, best_params: Dict[str, Any], best_score: float, method: str
) -> str:
    """
    保存調優結果

    Args:
        results: 調優結果資料框
        best_params: 最佳參數
        best_score: 最佳分數
        method: 調優方法

    Returns:
        結果檔案路徑

    Example:
        >>> path = save_results(results_df, best_params, 0.95, "grid_search")
    """
    filename = f"{method}_results.csv"
    results.to_csv(filename, index=False)
    mlflow.log_artifact(filename)

    # 記錄最佳參數和分數
    for param, value in best_params.items():
        mlflow.log_param(f"best_{param}", value)
    mlflow.log_metric("best_score", best_score)

    return filename


def plot_param_importance(
    results: pd.DataFrame, save_path: str = "param_importance.png"
) -> None:
    """
    繪製參數重要性圖

    Args:
        results: 調優結果資料框
        save_path: 圖片保存路徑

    Example:
        >>> plot_param_importance(results_df)
    """
    if results is None or results.empty:
        logger.warning("無調優結果，跳過參數重要性圖繪製")
        return

    try:
        # 計算每個參數的重要性
        param_names = [col for col in results.columns if col.startswith("param_")]
        importance_data = []

        for param in param_names:
            # 確保參數列為字串類型
            param_values = results[param].astype(str)

            # 計算參數與分數的關係
            if "mean_test_score" in results.columns:
                grouped_scores = results.groupby(param_values)["mean_test_score"].mean()

                # 計算參數的重要性（最大分數 - 最小分數）
                if len(grouped_scores) > 1:
                    importance = grouped_scores.max() - grouped_scores.min()
                    importance_data.append(
                        {
                            "parameter": param.replace("param_", ""),
                            "importance": importance,
                        }
                    )

        if not importance_data:
            logger.warning("無法計算參數重要性")
            return

        # 創建重要性資料框
        importance_df = pd.DataFrame(importance_data)
        importance_df = importance_df.sort_values("importance", ascending=False)

        # 繪製參數重要性圖
        plt.figure(figsize=(10, 6))
        sns.barplot(
            x="importance", y="parameter", data=importance_df, palette="viridis"
        )
        plt.title("Parameter Importance", fontsize=14, fontweight="bold")
        plt.xlabel("Importance (Score Range)", fontsize=12)
        plt.ylabel("Parameter", fontsize=12)
        plt.tight_layout()

        # 保存圖表
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        plt.close()

        # 記錄到 MLflow
        if mlflow.active_run():
            mlflow.log_artifact(save_path)

        logger.info(f"參數重要性圖已保存: {save_path}")

    except Exception as e:
        logger.error(f"繪製參數重要性圖時發生錯誤: {e}")
        plt.close()  # 確保關閉圖表以釋放記憶體


def compare_optimization_methods(
    results_dict: Dict[str, Dict[str, Any]],
    save_path: str = "optimization_comparison.png",
) -> pd.DataFrame:
    """
    比較不同優化方法的性能

    Args:
        results_dict: 不同方法的結果字典
        save_path: 比較圖保存路徑

    Returns:
        比較結果資料框

    Example:
        >>> comparison = compare_optimization_methods({
        ...     "grid_search": grid_results,
        ...     "random_search": random_results
        ... })
    """
    comparison_data = []

    for method, results in results_dict.items():
        comparison_data.append(
            {
                "method": method,
                "best_score": results.get("best_score", 0),
                "n_trials": (
                    len(results.get("results", []))
                    if results.get("results") is not None
                    else 0
                ),
            }
        )

    comparison_df = pd.DataFrame(comparison_data)

    # 繪製比較圖
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # 最佳分數比較
    sns.barplot(x="method", y="best_score", data=comparison_df, ax=ax1)
    ax1.set_title("Best Score Comparison")
    ax1.set_ylabel("Best Score")

    # 試驗次數比較
    sns.barplot(x="method", y="n_trials", data=comparison_df, ax=ax2)
    ax2.set_title("Number of Trials Comparison")
    ax2.set_ylabel("Number of Trials")

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.close()

    if mlflow.active_run():
        mlflow.log_artifact(save_path)

    return comparison_df
