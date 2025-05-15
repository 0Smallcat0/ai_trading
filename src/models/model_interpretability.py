# -*- coding: utf-8 -*-
"""
模型解釋性模組

此模組提供模型解釋性功能，包括：
- SHAP (SHapley Additive exPlanations)
- LIME (Local Interpretable Model-agnostic Explanations)
- 特徵重要性分析
- 部分依賴圖
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
import shap
import lime
import lime.lime_tabular
from sklearn.inspection import permutation_importance, partial_dependence, plot_partial_dependence
import mlflow

from src.config import LOG_LEVEL, MODELS_DIR, RESULTS_DIR
from src.models.model_base import ModelBase

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class ModelInterpreter:
    """
    模型解釋器

    提供各種模型解釋功能。
    """

    def __init__(
        self,
        model: ModelBase,
        feature_names: Optional[List[str]] = None,
        class_names: Optional[List[str]] = None,
        output_dir: Optional[str] = None
    ):
        """
        初始化模型解釋器

        Args:
            model (ModelBase): 要解釋的模型
            feature_names (Optional[List[str]]): 特徵名稱列表
            class_names (Optional[List[str]]): 類別名稱列表
            output_dir (Optional[str]): 輸出目錄
        """
        self.model = model
        self.feature_names = feature_names or model.feature_names
        self.class_names = class_names
        self.output_dir = output_dir or os.path.join(RESULTS_DIR, "model_interpretation", model.name)
        
        # 創建輸出目錄
        os.makedirs(self.output_dir, exist_ok=True)
        
        # SHAP 解釋器
        self.shap_explainer = None
        self.shap_values = None
        
        # LIME 解釋器
        self.lime_explainer = None

    def explain_with_shap(
        self,
        X: pd.DataFrame,
        plot_type: str = "summary",
        sample_size: Optional[int] = None,
        log_to_mlflow: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        使用 SHAP 解釋模型

        Args:
            X (pd.DataFrame): 特徵資料
            plot_type (str): 圖表類型，可選 "summary", "bar", "beeswarm", "waterfall", "force", "decision"
            sample_size (Optional[int]): 樣本大小，如果提供則隨機抽樣
            log_to_mlflow (bool): 是否記錄到 MLflow
            **kwargs: 其他參數

        Returns:
            Dict[str, Any]: 解釋結果
        """
        if not self.model.trained:
            logger.error("模型尚未訓練，無法解釋")
            raise ValueError("模型尚未訓練，無法解釋")
        
        # 隨機抽樣
        if sample_size is not None and sample_size < len(X):
            X_sample = X.sample(sample_size, random_state=42)
        else:
            X_sample = X
        
        # 創建 SHAP 解釋器
        logger.info(f"創建 SHAP 解釋器: {self.model.name}")
        
        try:
            # 嘗試使用 TreeExplainer
            self.shap_explainer = shap.TreeExplainer(self.model.model)
        except Exception:
            try:
                # 嘗試使用 KernelExplainer
                self.shap_explainer = shap.KernelExplainer(
                    self.model.model.predict if hasattr(self.model.model, "predict") else self.model.predict,
                    shap.sample(X_sample, 100)
                )
            except Exception as e:
                logger.error(f"創建 SHAP 解釋器時發生錯誤: {e}")
                raise
        
        # 計算 SHAP 值
        logger.info("計算 SHAP 值")
        self.shap_values = self.shap_explainer.shap_values(X_sample)
        
        # 繪製 SHAP 圖表
        logger.info(f"繪製 SHAP {plot_type} 圖表")
        plt.figure(figsize=(12, 8))
        
        if plot_type == "summary":
            shap.summary_plot(self.shap_values, X_sample, feature_names=self.feature_names, show=False)
        elif plot_type == "bar":
            shap.summary_plot(self.shap_values, X_sample, feature_names=self.feature_names, plot_type="bar", show=False)
        elif plot_type == "beeswarm":
            shap.summary_plot(self.shap_values, X_sample, feature_names=self.feature_names, plot_type="violin", show=False)
        elif plot_type == "waterfall":
            if isinstance(self.shap_values, list):
                shap.waterfall_plot(self.shap_explainer.expected_value[0], self.shap_values[0][0], feature_names=self.feature_names, show=False)
            else:
                shap.waterfall_plot(self.shap_explainer.expected_value, self.shap_values[0], feature_names=self.feature_names, show=False)
        elif plot_type == "force":
            if isinstance(self.shap_values, list):
                shap.force_plot(self.shap_explainer.expected_value[0], self.shap_values[0][0], X_sample.iloc[0], feature_names=self.feature_names, show=False)
            else:
                shap.force_plot(self.shap_explainer.expected_value, self.shap_values[0], X_sample.iloc[0], feature_names=self.feature_names, show=False)
        elif plot_type == "decision":
            if isinstance(self.shap_values, list):
                shap.decision_plot(self.shap_explainer.expected_value[0], self.shap_values[0][0], feature_names=self.feature_names, show=False)
            else:
                shap.decision_plot(self.shap_explainer.expected_value, self.shap_values[0], feature_names=self.feature_names, show=False)
        else:
            logger.error(f"未知的圖表類型: {plot_type}")
            raise ValueError(f"未知的圖表類型: {plot_type}")
        
        # 保存圖表
        plot_path = os.path.join(self.output_dir, f"shap_{plot_type}.png")
        plt.tight_layout()
        plt.savefig(plot_path)
        plt.close()
        
        # 記錄到 MLflow
        if log_to_mlflow:
            mlflow.log_artifact(plot_path)
        
        # 計算特徵重要性
        if isinstance(self.shap_values, list):
            shap_importance = np.abs(self.shap_values[0]).mean(axis=0)
        else:
            shap_importance = np.abs(self.shap_values).mean(axis=0)
        
        # 創建特徵重要性資料框
        importance_df = pd.DataFrame({
            "feature": self.feature_names or [f"feature_{i}" for i in range(len(shap_importance))],
            "importance": shap_importance
        })
        importance_df = importance_df.sort_values("importance", ascending=False)
        
        # 保存特徵重要性
        importance_path = os.path.join(self.output_dir, "shap_importance.csv")
        importance_df.to_csv(importance_path, index=False)
        
        # 記錄到 MLflow
        if log_to_mlflow:
            mlflow.log_artifact(importance_path)
        
        return {
            "shap_values": self.shap_values,
            "shap_explainer": self.shap_explainer,
            "importance": importance_df,
            "plot_path": plot_path,
            "importance_path": importance_path
        }

    def explain_with_lime(
        self,
        X: pd.DataFrame,
        y: Optional[pd.Series] = None,
        num_samples: int = 5000,
        num_features: int = 10,
        log_to_mlflow: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        使用 LIME 解釋模型

        Args:
            X (pd.DataFrame): 特徵資料
            y (Optional[pd.Series]): 目標資料
            num_samples (int): 樣本數量
            num_features (int): 特徵數量
            log_to_mlflow (bool): 是否記錄到 MLflow
            **kwargs: 其他參數

        Returns:
            Dict[str, Any]: 解釋結果
        """
        if not self.model.trained:
            logger.error("模型尚未訓練，無法解釋")
            raise ValueError("模型尚未訓練，無法解釋")
        
        # 創建 LIME 解釋器
        logger.info(f"創建 LIME 解釋器: {self.model.name}")
        
        # 判斷是分類還是回歸問題
        mode = "classification" if hasattr(self.model, "is_classifier") and self.model.is_classifier else "regression"
        
        self.lime_explainer = lime.lime_tabular.LimeTabularExplainer(
            X.values,
            feature_names=self.feature_names,
            class_names=self.class_names,
            mode=mode,
            **kwargs
        )
        
        # 選擇要解釋的樣本
        if y is not None:
            # 選擇一些正確預測和錯誤預測的樣本
            y_pred = self.model.predict(X)
            correct_idx = np.where(y == y_pred)[0]
            wrong_idx = np.where(y != y_pred)[0]
            
            # 確保有足夠的樣本
            num_correct = min(3, len(correct_idx))
            num_wrong = min(3, len(wrong_idx))
            
            # 隨機選擇樣本
            if num_correct > 0:
                correct_samples = np.random.choice(correct_idx, num_correct, replace=False)
            else:
                correct_samples = []
            
            if num_wrong > 0:
                wrong_samples = np.random.choice(wrong_idx, num_wrong, replace=False)
            else:
                wrong_samples = []
            
            sample_idx = np.concatenate([correct_samples, wrong_samples])
        else:
            # 隨機選擇樣本
            sample_idx = np.random.choice(len(X), min(6, len(X)), replace=False)
        
        # 解釋每個樣本
        explanations = []
        
        for i, idx in enumerate(sample_idx):
            logger.info(f"解釋樣本 {i+1}/{len(sample_idx)}")
            
            # 獲取樣本
            sample = X.iloc[idx].values
            
            # 解釋樣本
            if mode == "classification":
                explanation = self.lime_explainer.explain_instance(
                    sample,
                    self.model.predict_proba if hasattr(self.model, "predict_proba") else lambda x: self.model.model.predict_proba(x),
                    num_features=num_features,
                    num_samples=num_samples
                )
            else:
                explanation = self.lime_explainer.explain_instance(
                    sample,
                    self.model.predict if hasattr(self.model, "predict") else lambda x: self.model.model.predict(x),
                    num_features=num_features,
                    num_samples=num_samples
                )
            
            # 繪製解釋圖
            fig = plt.figure(figsize=(10, 6))
            explanation.as_pyplot_figure(fig)
            
            # 保存圖表
            plot_path = os.path.join(self.output_dir, f"lime_sample_{idx}.png")
            plt.tight_layout()
            plt.savefig(plot_path)
            plt.close()
            
            # 記錄到 MLflow
            if log_to_mlflow:
                mlflow.log_artifact(plot_path)
            
            # 獲取特徵重要性
            if mode == "classification":
                importance = explanation.as_list(label=explanation.available_labels()[0])
            else:
                importance = explanation.as_list()
            
            # 添加到結果
            explanations.append({
                "sample_idx": idx,
                "explanation": explanation,
                "importance": importance,
                "plot_path": plot_path
            })
        
        return {
            "lime_explainer": self.lime_explainer,
            "explanations": explanations
        }

    def feature_importance(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        method: str = "permutation",
        n_repeats: int = 10,
        log_to_mlflow: bool = True,
        **kwargs
    ) -> pd.DataFrame:
        """
        計算特徵重要性

        Args:
            X (pd.DataFrame): 特徵資料
            y (pd.Series): 目標資料
            method (str): 方法，可選 "permutation", "model"
            n_repeats (int): 重複次數
            log_to_mlflow (bool): 是否記錄到 MLflow
            **kwargs: 其他參數

        Returns:
            pd.DataFrame: 特徵重要性資料框
        """
        if not self.model.trained:
            logger.error("模型尚未訓練，無法計算特徵重要性")
            raise ValueError("模型尚未訓練，無法計算特徵重要性")
        
        # 計算特徵重要性
        logger.info(f"計算特徵重要性: {self.model.name}, 方法: {method}")
        
        if method == "permutation":
            # 使用排列重要性
            result = permutation_importance(
                self.model.model,
                X, y,
                n_repeats=n_repeats,
                random_state=42,
                **kwargs
            )
            
            # 創建特徵重要性資料框
            importance_df = pd.DataFrame({
                "feature": self.feature_names or [f"feature_{i}" for i in range(len(result.importances_mean))],
                "importance": result.importances_mean,
                "std": result.importances_std
            })
        elif method == "model":
            # 使用模型內建的特徵重要性
            importance_df = self.model.feature_importance()
        else:
            logger.error(f"未知的方法: {method}")
            raise ValueError(f"未知的方法: {method}")
        
        # 排序特徵重要性
        importance_df = importance_df.sort_values("importance", ascending=False)
        
        # 繪製特徵重要性圖
        plt.figure(figsize=(12, 8))
        sns.barplot(x="importance", y="feature", data=importance_df)
        plt.title(f"Feature Importance ({method})")
        plt.tight_layout()
        
        # 保存圖表
        plot_path = os.path.join(self.output_dir, f"feature_importance_{method}.png")
        plt.savefig(plot_path)
        plt.close()
        
        # 保存特徵重要性
        importance_path = os.path.join(self.output_dir, f"feature_importance_{method}.csv")
        importance_df.to_csv(importance_path, index=False)
        
        # 記錄到 MLflow
        if log_to_mlflow:
            mlflow.log_artifact(plot_path)
            mlflow.log_artifact(importance_path)
        
        return importance_df
