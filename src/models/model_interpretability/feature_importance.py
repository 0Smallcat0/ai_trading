# -*- coding: utf-8 -*-
"""
特徵重要性分析器

此模組實現多種特徵重要性計算方法，提供：
- 排列重要性 (Permutation Importance)
- 模型內建重要性
- 統計重要性分析
- 重要性視覺化

Classes:
    FeatureImportanceAnalyzer: 特徵重要性分析器主類
"""

import logging
import os
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.inspection import permutation_importance

from src.config import LOG_LEVEL
from src.models.model_base import ModelBase
from .utils import validate_explanation_inputs, save_explanation_results

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class FeatureImportanceAnalyzer:
    """
    特徵重要性分析器
    
    提供多種方法計算和分析特徵重要性，包括排列重要性、
    模型內建重要性等。
    
    Attributes:
        model: 要分析的模型實例
        feature_names: 特徵名稱列表
        output_dir: 結果輸出目錄
        
    Example:
        >>> analyzer = FeatureImportanceAnalyzer(model, feature_names=features)
        >>> results = analyzer.calculate_importance(X_test, y_test, method="permutation")
        
    Note:
        不同的重要性計算方法適用於不同的模型類型
        排列重要性是模型無關的方法，適用於所有模型
    """

    def __init__(
        self,
        model: ModelBase,
        feature_names: Optional[List[str]] = None,
        output_dir: Optional[str] = None,
    ) -> None:
        """
        初始化特徵重要性分析器

        Args:
            model: 要分析的模型，必須是已訓練的 ModelBase 實例
            feature_names: 特徵名稱列表
            output_dir: 結果輸出目錄
            
        Raises:
            ValueError: 當模型未訓練時
            
        Example:
            >>> analyzer = FeatureImportanceAnalyzer(
            ...     model=my_model,
            ...     feature_names=['age', 'income', 'score']
            ... )
        """
        if not model.trained:
            raise ValueError("模型必須已經訓練完成")
        
        self.model = model
        self.feature_names = feature_names
        self.output_dir = output_dir or "./feature_importance_results"
        
        # 創建輸出目錄
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info(f"特徵重要性分析器已初始化: {model.name}")

    def calculate_importance(
        self,
        X: Any,
        y: Any,
        method: str = "permutation",
        n_repeats: int = 10,
        scoring: Optional[str] = None,
        log_to_mlflow: bool = True,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        計算特徵重要性
        
        Args:
            X: 特徵資料
            y: 目標資料
            method: 計算方法，可選 "permutation", "model", "both"
            n_repeats: 排列重要性的重複次數
            scoring: 評分函數
            log_to_mlflow: 是否記錄到 MLflow
            **kwargs: 額外參數
            
        Returns:
            包含重要性結果的字典
            
        Raises:
            ValueError: 當輸入資料或方法無效時
            RuntimeError: 當計算過程失敗時
            
        Example:
            >>> results = analyzer.calculate_importance(
            ...     X_test, y_test, method="permutation", n_repeats=10
            ... )
        """
        # 驗證輸入
        validate_explanation_inputs(X, y, self.feature_names)
        
        if method not in ["permutation", "model", "both"]:
            raise ValueError(f"未知的方法: {method}")
        
        try:
            results = {}
            
            # 計算排列重要性
            if method in ["permutation", "both"]:
                perm_results = self._calculate_permutation_importance(
                    X, y, n_repeats, scoring, **kwargs
                )
                results["permutation"] = perm_results
            
            # 計算模型內建重要性
            if method in ["model", "both"]:
                model_results = self._calculate_model_importance(X, y)
                results["model"] = model_results
            
            # 創建比較圖（如果有多種方法）
            if method == "both":
                comparison_plot_path = self._create_comparison_plot(
                    results["permutation"], results["model"]
                )
                results["comparison_plot"] = comparison_plot_path
            
            # 保存結果
            for result_type, result_data in results.items():
                if isinstance(result_data, dict) and "importance" in result_data:
                    saved_paths = save_explanation_results(
                        result_data, self.output_dir, f"feature_importance_{result_type}", 
                        log_to_mlflow
                    )
                    result_data["saved_paths"] = saved_paths
            
            logger.info(f"特徵重要性計算完成，方法: {method}")
            
            return results
            
        except Exception as e:
            logger.error(f"計算特徵重要性時發生錯誤: {e}")
            raise RuntimeError(f"特徵重要性計算失敗: {e}") from e

    def _calculate_permutation_importance(
        self,
        X: Any,
        y: Any,
        n_repeats: int,
        scoring: Optional[str],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        計算排列重要性
        
        Args:
            X: 特徵資料
            y: 目標資料
            n_repeats: 重複次數
            scoring: 評分函數
            **kwargs: 額外參數
            
        Returns:
            排列重要性結果字典
        """
        logger.info(f"計算排列重要性，重複次數: {n_repeats}")
        
        # 執行排列重要性計算
        result = permutation_importance(
            self.model.model, X, y, 
            n_repeats=n_repeats, 
            random_state=42,
            scoring=scoring,
            **kwargs
        )
        
        # 創建重要性資料框
        feature_names = self.feature_names or [f"feature_{i}" for i in range(len(result.importances_mean))]
        
        importance_df = pd.DataFrame({
            "feature": feature_names,
            "importance": result.importances_mean,
            "std": result.importances_std,
            "min": result.importances.min(axis=1),
            "max": result.importances.max(axis=1)
        }).sort_values("importance", ascending=False)
        
        # 創建視覺化
        plot_path = self._create_importance_plot(
            importance_df, "Permutation Feature Importance", "permutation"
        )
        
        return {
            "importance": importance_df,
            "raw_importances": result.importances,
            "plot_path": plot_path,
            "method": "permutation",
            "n_repeats": n_repeats
        }

    def _calculate_model_importance(self, X: Any, y: Any) -> Dict[str, Any]:
        """
        計算模型內建重要性
        
        Args:
            X: 特徵資料
            y: 目標資料
            
        Returns:
            模型重要性結果字典
        """
        logger.info("計算模型內建重要性")
        
        try:
            # 嘗試獲取模型的特徵重要性
            if hasattr(self.model, 'feature_importance'):
                importance_df = self.model.feature_importance()
            elif hasattr(self.model.model, 'feature_importances_'):
                # sklearn 模型
                importances = self.model.model.feature_importances_
                feature_names = self.feature_names or [f"feature_{i}" for i in range(len(importances))]
                importance_df = pd.DataFrame({
                    "feature": feature_names,
                    "importance": importances
                }).sort_values("importance", ascending=False)
            elif hasattr(self.model.model, 'coef_'):
                # 線性模型
                coef = self.model.model.coef_
                if len(coef.shape) > 1:
                    coef = np.abs(coef).mean(axis=0)
                else:
                    coef = np.abs(coef)
                
                feature_names = self.feature_names or [f"feature_{i}" for i in range(len(coef))]
                importance_df = pd.DataFrame({
                    "feature": feature_names,
                    "importance": coef
                }).sort_values("importance", ascending=False)
            else:
                raise ValueError("模型不支援內建特徵重要性")
            
            # 創建視覺化
            plot_path = self._create_importance_plot(
                importance_df, "Model Feature Importance", "model"
            )
            
            return {
                "importance": importance_df,
                "plot_path": plot_path,
                "method": "model"
            }
            
        except Exception as e:
            logger.warning(f"無法計算模型內建重要性: {e}")
            return {
                "importance": pd.DataFrame(),
                "plot_path": "",
                "method": "model",
                "error": str(e)
            }

    def _create_importance_plot(
        self,
        importance_df: pd.DataFrame,
        title: str,
        method: str
    ) -> str:
        """
        創建重要性視覺化圖表
        
        Args:
            importance_df: 重要性資料框
            title: 圖表標題
            method: 方法名稱
            
        Returns:
            圖表檔案路徑
        """
        try:
            plt.figure(figsize=(12, 8))
            
            # 選擇前 20 個重要特徵
            top_features = importance_df.head(20)
            
            # 創建條形圖
            if "std" in top_features.columns:
                # 有標準差的情況（排列重要性）
                plt.barh(range(len(top_features)), top_features["importance"], 
                        xerr=top_features["std"], capsize=3)
            else:
                # 沒有標準差的情況（模型重要性）
                plt.barh(range(len(top_features)), top_features["importance"])
            
            plt.yticks(range(len(top_features)), top_features["feature"])
            plt.xlabel("Importance")
            plt.title(title, fontsize=14, fontweight="bold")
            plt.grid(axis='x', alpha=0.3)
            plt.tight_layout()
            
            # 保存圖表
            plot_path = os.path.join(self.output_dir, f"feature_importance_{method}.png")
            plt.savefig(plot_path, dpi=300, bbox_inches="tight")
            plt.close()
            
            logger.info(f"重要性圖表已保存: {plot_path}")
            return plot_path
            
        except Exception as e:
            logger.error(f"創建重要性圖表時發生錯誤: {e}")
            plt.close()  # 確保關閉圖表
            return ""

    def _create_comparison_plot(
        self,
        perm_results: Dict[str, Any],
        model_results: Dict[str, Any]
    ) -> str:
        """
        創建重要性方法比較圖
        
        Args:
            perm_results: 排列重要性結果
            model_results: 模型重要性結果
            
        Returns:
            比較圖檔案路徑
        """
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 8))
            
            # 排列重要性圖
            if not perm_results["importance"].empty:
                perm_top = perm_results["importance"].head(15)
                ax1.barh(range(len(perm_top)), perm_top["importance"], 
                        xerr=perm_top["std"], capsize=3)
                ax1.set_yticks(range(len(perm_top)))
                ax1.set_yticklabels(perm_top["feature"])
                ax1.set_xlabel("Permutation Importance")
                ax1.set_title("Permutation Feature Importance")
                ax1.grid(axis='x', alpha=0.3)
            
            # 模型重要性圖
            if not model_results["importance"].empty:
                model_top = model_results["importance"].head(15)
                ax2.barh(range(len(model_top)), model_top["importance"])
                ax2.set_yticks(range(len(model_top)))
                ax2.set_yticklabels(model_top["feature"])
                ax2.set_xlabel("Model Importance")
                ax2.set_title("Model Feature Importance")
                ax2.grid(axis='x', alpha=0.3)
            
            plt.tight_layout()
            
            # 保存比較圖
            plot_path = os.path.join(self.output_dir, "feature_importance_comparison.png")
            plt.savefig(plot_path, dpi=300, bbox_inches="tight")
            plt.close()
            
            logger.info(f"重要性比較圖已保存: {plot_path}")
            return plot_path
            
        except Exception as e:
            logger.error(f"創建重要性比較圖時發生錯誤: {e}")
            plt.close()  # 確保關閉圖表
            return ""
