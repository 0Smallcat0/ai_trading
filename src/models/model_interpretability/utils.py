# -*- coding: utf-8 -*-
"""
模型解釋性工具函數

此模組提供模型解釋性過程中使用的工具函數，包括：
- 輸入驗證
- 結果保存
- 視覺化功能
- 報告生成

Functions:
    validate_explanation_inputs: 驗證解釋輸入資料
    save_explanation_results: 保存解釋結果
    plot_explanation_comparison: 繪製解釋方法比較圖
    generate_explanation_report: 生成解釋報告
    create_interpreter: 創建解釋器的工廠函數
"""

import logging
import os
from typing import Any, Dict, List, Optional, Union

import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd
import seaborn as sns

from src.config import LOG_LEVEL
from src.models.model_base import ModelBase

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


def validate_explanation_inputs(
    X: Any,
    y: Optional[Any] = None,
    feature_names: Optional[List[str]] = None
) -> None:
    """
    驗證解釋輸入資料格式
    
    Args:
        X: 特徵資料
        y: 目標資料（可選）
        feature_names: 特徵名稱列表（可選）
        
    Raises:
        ValueError: 當輸入資料格式不正確時
        TypeError: 當資料類型不正確時
        
    Example:
        >>> validate_explanation_inputs(X_test, y_test, feature_names)
    """
    # 驗證特徵資料
    if X is None:
        raise ValueError("特徵資料 X 不能為 None")
    
    if hasattr(X, 'empty') and X.empty:
        raise ValueError("特徵資料 X 不能為空")
    
    if hasattr(X, 'shape') and len(X.shape) != 2:
        raise ValueError("特徵資料 X 必須是二維陣列")
    
    # 驗證目標資料（如果提供）
    if y is not None:
        if hasattr(y, 'empty') and y.empty:
            raise ValueError("目標資料 y 不能為空")
        
        if hasattr(X, '__len__') and hasattr(y, '__len__'):
            if len(X) != len(y):
                raise ValueError("特徵資料和目標資料的樣本數必須相同")
    
    # 驗證特徵名稱（如果提供）
    if feature_names is not None:
        if not isinstance(feature_names, (list, tuple)):
            raise TypeError("feature_names 必須是列表或元組")
        
        if hasattr(X, 'shape') and len(feature_names) != X.shape[1]:
            raise ValueError("特徵名稱數量必須與特徵數量相同")


def save_explanation_results(
    results: Dict[str, Any],
    output_dir: str,
    method_name: str,
    log_to_mlflow: bool = True
) -> Dict[str, str]:
    """
    保存解釋結果到檔案
    
    Args:
        results: 解釋結果字典
        output_dir: 輸出目錄
        method_name: 解釋方法名稱
        log_to_mlflow: 是否記錄到 MLflow
        
    Returns:
        保存的檔案路徑字典
        
    Example:
        >>> paths = save_explanation_results(
        ...     results, "./output", "shap", log_to_mlflow=True
        ... )
    """
    saved_paths = {}
    
    try:
        # 保存重要性資料
        if 'importance' in results and isinstance(results['importance'], pd.DataFrame):
            importance_path = os.path.join(output_dir, f"{method_name}_importance.csv")
            results['importance'].to_csv(importance_path, index=False)
            saved_paths['importance'] = importance_path
            
            if log_to_mlflow and mlflow.active_run():
                mlflow.log_artifact(importance_path)
        
        # 保存圖表
        if 'plot_path' in results:
            saved_paths['plot'] = results['plot_path']
            
            if log_to_mlflow and mlflow.active_run():
                mlflow.log_artifact(results['plot_path'])
        
        # 保存解釋值（如果是數值陣列）
        if 'values' in results and isinstance(results['values'], np.ndarray):
            values_path = os.path.join(output_dir, f"{method_name}_values.npy")
            np.save(values_path, results['values'])
            saved_paths['values'] = values_path
            
            if log_to_mlflow and mlflow.active_run():
                mlflow.log_artifact(values_path)
        
        logger.info(f"解釋結果已保存: {method_name}, 檔案數: {len(saved_paths)}")
        
    except Exception as e:
        logger.error(f"保存解釋結果時發生錯誤: {e}")
        raise RuntimeError(f"結果保存失敗: {e}") from e
    
    return saved_paths


def plot_explanation_comparison(
    results_dict: Dict[str, Dict[str, Any]],
    save_path: str = "explanation_comparison.png",
    figsize: tuple = (15, 10)
) -> str:
    """
    繪製不同解釋方法的比較圖
    
    Args:
        results_dict: 不同方法的結果字典
        save_path: 圖片保存路徑
        figsize: 圖片大小
        
    Returns:
        保存的圖片路徑
        
    Example:
        >>> comparison_path = plot_explanation_comparison({
        ...     "shap": shap_results,
        ...     "lime": lime_results
        ... })
    """
    try:
        n_methods = len(results_dict)
        if n_methods == 0:
            raise ValueError("至少需要一種解釋方法的結果")
        
        fig, axes = plt.subplots(1, n_methods, figsize=figsize)
        if n_methods == 1:
            axes = [axes]
        
        for idx, (method, results) in enumerate(results_dict.items()):
            ax = axes[idx]
            
            # 繪製特徵重要性（如果有）
            if 'importance' in results and isinstance(results['importance'], pd.DataFrame):
                importance_df = results['importance'].head(10)  # 只顯示前10個特徵
                
                sns.barplot(
                    x="importance",
                    y="feature",
                    data=importance_df,
                    ax=ax,
                    palette="viridis"
                )
                
                ax.set_title(f"{method.upper()} Feature Importance", fontsize=12, fontweight="bold")
                ax.set_xlabel("Importance", fontsize=10)
                ax.set_ylabel("Feature", fontsize=10)
            else:
                ax.text(0.5, 0.5, f"No importance data\nfor {method}", 
                       ha='center', va='center', transform=ax.transAxes)
                ax.set_title(f"{method.upper()}", fontsize=12)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches="tight")
        plt.close()
        
        logger.info(f"解釋比較圖已保存: {save_path}")
        
        # 記錄到 MLflow
        if mlflow.active_run():
            mlflow.log_artifact(save_path)
        
        return save_path
        
    except Exception as e:
        logger.error(f"繪製解釋比較圖時發生錯誤: {e}")
        plt.close()  # 確保關閉圖表
        raise RuntimeError(f"比較圖繪製失敗: {e}") from e


def generate_explanation_report(
    model_info: Dict[str, Any],
    explanation_results: Dict[str, Dict[str, Any]],
    output_path: str = "explanation_report.html"
) -> str:
    """
    生成完整的解釋報告
    
    Args:
        model_info: 模型資訊
        explanation_results: 解釋結果字典
        output_path: 報告保存路徑
        
    Returns:
        報告檔案路徑
        
    Example:
        >>> report_path = generate_explanation_report(
        ...     model_info, {"shap": shap_results, "lime": lime_results}
        ... )
    """
    try:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Model Explanation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1, h2 {{ color: #333; }}
                .section {{ margin: 20px 0; }}
                .info-table {{ border-collapse: collapse; width: 100%; }}
                .info-table th, .info-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .info-table th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Model Explanation Report</h1>
            
            <div class="section">
                <h2>Model Information</h2>
                <table class="info-table">
                    <tr><th>Property</th><th>Value</th></tr>
                    <tr><td>Model Name</td><td>{model_info.get('name', 'Unknown')}</td></tr>
                    <tr><td>Model Type</td><td>{model_info.get('type', 'Unknown')}</td></tr>
                    <tr><td>Number of Features</td><td>{model_info.get('n_features', 'Unknown')}</td></tr>
                    <tr><td>Trained</td><td>{model_info.get('trained', 'Unknown')}</td></tr>
                </table>
            </div>
            
            <div class="section">
                <h2>Explanation Methods Used</h2>
                <ul>
        """
        
        for method in explanation_results.keys():
            html_content += f"<li>{method.upper()}</li>"
        
        html_content += """
                </ul>
            </div>
            
            <div class="section">
                <h2>Key Findings</h2>
                <p>This report provides insights into model behavior using multiple explanation methods.</p>
            </div>
        </body>
        </html>
        """
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"解釋報告已生成: {output_path}")
        
        # 記錄到 MLflow
        if mlflow.active_run():
            mlflow.log_artifact(output_path)
        
        return output_path
        
    except Exception as e:
        logger.error(f"生成解釋報告時發生錯誤: {e}")
        raise RuntimeError(f"報告生成失敗: {e}") from e


def create_interpreter(
    model: ModelBase,
    interpreter_type: str = "default",
    **kwargs: Any
) -> Any:
    """
    創建解釋器的工廠函數
    
    Args:
        model: 要解釋的模型
        interpreter_type: 解釋器類型
        **kwargs: 額外參數
        
    Returns:
        解釋器實例
        
    Example:
        >>> interpreter = create_interpreter(model, "default", feature_names=features)
    """
    from .base import ModelInterpreter
    
    if interpreter_type == "default":
        return ModelInterpreter(model, **kwargs)
    else:
        raise ValueError(f"未知的解釋器類型: {interpreter_type}")
