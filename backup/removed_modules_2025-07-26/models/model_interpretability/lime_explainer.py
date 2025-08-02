# -*- coding: utf-8 -*-
"""
LIME 解釋器

此模組實現基於 LIME (Local Interpretable Model-agnostic Explanations) 的模型解釋功能，提供：
- 表格資料解釋器
- 局部解釋生成
- 解釋結果視覺化

Classes:
    LIMEExplainer: LIME 解釋器主類
"""

import logging
import os
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import LOG_LEVEL
from src.models.model_base import ModelBase
from .utils import validate_explanation_inputs, save_explanation_results

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))

# 檢查 LIME 是否可用
try:
    import lime
    import lime.lime_tabular

    LIME_AVAILABLE = True
except ImportError:
    LIME_AVAILABLE = False
    logger.warning("LIME 未安裝，LIME 解釋功能將無法使用")


class LIMEExplainer:
    """
    LIME 解釋器

    使用 LIME (Local Interpretable Model-agnostic Explanations) 方法
    為個別預測提供局部解釋。

    Attributes:
        model: 要解釋的模型實例
        feature_names: 特徵名稱列表
        class_names: 類別名稱列表
        output_dir: 結果輸出目錄
        explainer: LIME 解釋器實例

    Example:
        >>> explainer = LIMEExplainer(model, feature_names=features)
        >>> results = explainer.explain(X_test, y_test, num_features=10)

    Note:
        需要安裝 lime 套件才能使用此功能
        LIME 主要用於局部解釋，適合解釋個別預測
    """

    def __init__(
        self,
        model: ModelBase,
        feature_names: Optional[List[str]] = None,
        class_names: Optional[List[str]] = None,
        output_dir: Optional[str] = None,
    ) -> None:
        """
        初始化 LIME 解釋器

        Args:
            model: 要解釋的模型，必須是已訓練的 ModelBase 實例
            feature_names: 特徵名稱列表
            class_names: 類別名稱列表
            output_dir: 結果輸出目錄

        Raises:
            ImportError: 當 LIME 未安裝時
            ValueError: 當模型未訓練時

        Example:
            >>> explainer = LIMEExplainer(
            ...     model=my_model,
            ...     feature_names=['age', 'income'],
            ...     class_names=['low_risk', 'high_risk']
            ... )
        """
        if not LIME_AVAILABLE:
            raise ImportError("LIME 未安裝，無法使用 LIME 解釋功能")

        if not model.trained:
            raise ValueError("模型必須已經訓練完成")

        self.model = model
        self.feature_names = feature_names
        self.class_names = class_names
        self.output_dir = output_dir or "./lime_results"
        self.explainer: Optional[Any] = None

        # 創建輸出目錄
        os.makedirs(self.output_dir, exist_ok=True)

        logger.info(f"LIME 解釋器已初始化: {model.name}")

    def _create_explainer(self, X_train: Any) -> Any:
        """
        創建 LIME 表格解釋器

        Args:
            X_train: 訓練資料，用於建立解釋器的背景分佈

        Returns:
            LIME 表格解釋器實例

        Raises:
            ValueError: 當無法創建解釋器時
        """
        try:
            # 確定模式（分類或回歸）
            mode = "classification" if self.class_names else "regression"

            # 創建 LIME 表格解釋器
            explainer = lime.lime_tabular.LimeTabularExplainer(
                training_data=X_train.values if hasattr(X_train, "values") else X_train,
                feature_names=self.feature_names,
                class_names=self.class_names,
                mode=mode,
                discretize_continuous=True,
                random_state=42,
            )

            logger.info(f"LIME 解釋器已創建，模式: {mode}")
            return explainer

        except Exception as e:
            logger.error(f"創建 LIME 解釋器時發生錯誤: {e}")
            raise ValueError(f"無法創建 LIME 解釋器: {e}") from e

    def explain(
        self,
        X: Any,
        y: Optional[Any] = None,
        X_train: Optional[Any] = None,
        num_samples: int = 5000,
        num_features: int = 10,
        num_instances: int = 5,
        log_to_mlflow: bool = True,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        執行 LIME 解釋

        Args:
            X: 要解釋的特徵資料
            y: 目標資料（可選）
            X_train: 訓練資料，用於建立背景分佈
            num_samples: 每個實例的採樣數量
            num_features: 顯示的特徵數量
            num_instances: 解釋的實例數量
            log_to_mlflow: 是否記錄到 MLflow
            **kwargs: 額外參數

        Returns:
            包含 LIME 解釋結果的字典

        Raises:
            ValueError: 當輸入資料無效時
            RuntimeError: 當解釋過程失敗時

        Example:
            >>> results = explainer.explain(
            ...     X_test, y_test, X_train=X_train, num_features=10
            ... )
        """
        # 驗證輸入
        validate_explanation_inputs(X, y, self.feature_names)

        # 使用提供的訓練資料或使用測試資料作為背景
        background_data = X_train if X_train is not None else X

        try:
            # 創建解釋器
            if self.explainer is None:
                self.explainer = self._create_explainer(background_data)

            # 選擇要解釋的實例
            n_instances = min(num_instances, len(X))
            instance_indices = np.random.choice(len(X), n_instances, replace=False)

            explanations = []
            importance_data = []

            logger.info(f"開始 LIME 解釋，實例數: {n_instances}")

            for i, idx in enumerate(instance_indices):
                # 獲取單個實例
                instance = X.iloc[idx] if hasattr(X, "iloc") else X[idx]

                # 生成解釋
                explanation = self.explainer.explain_instance(
                    data_row=(
                        instance.values if hasattr(instance, "values") else instance
                    ),
                    predict_fn=self._predict_fn,
                    num_samples=num_samples,
                    num_features=num_features,
                    **kwargs,
                )

                explanations.append(explanation)

                # 提取特徵重要性
                feature_importance = explanation.as_list()
                for feature_name, importance in feature_importance:
                    importance_data.append(
                        {
                            "instance": i,
                            "feature": feature_name,
                            "importance": importance,
                        }
                    )

                # 保存個別解釋圖
                fig = explanation.as_pyplot_figure()
                plot_path = os.path.join(
                    self.output_dir, f"lime_explanation_instance_{i}.png"
                )
                fig.savefig(plot_path, dpi=300, bbox_inches="tight")
                plt.close(fig)

            # 創建整體重要性資料框
            importance_df = pd.DataFrame(importance_data)

            # 計算平均重要性
            avg_importance = (
                importance_df.groupby("feature")["importance"]
                .agg(["mean", "std", "count"])
                .reset_index()
            )
            avg_importance.columns = ["feature", "importance", "std", "count"]
            avg_importance = avg_importance.sort_values(
                "importance", key=abs, ascending=False
            )

            # 創建整體視覺化
            overall_plot_path = self._create_overall_plot(avg_importance)

            # 準備結果
            results = {
                "explanations": explanations,
                "importance": avg_importance,
                "instance_importance": importance_df,
                "plot_path": overall_plot_path,
                "feature_names": self.feature_names,
                "num_instances": n_instances,
                "num_features": num_features,
            }

            # 保存結果
            saved_paths = save_explanation_results(
                results, self.output_dir, "lime", log_to_mlflow
            )
            results["saved_paths"] = saved_paths

            logger.info(f"LIME 解釋完成，實例數: {n_instances}")

            return results

        except Exception as e:
            logger.error(f"LIME 解釋時發生錯誤: {e}")
            raise RuntimeError(f"LIME 解釋執行失敗: {e}") from e

    def _predict_fn(self, X: Any) -> Any:
        """
        預測函數，用於 LIME 解釋器

        Args:
            X: 特徵資料

        Returns:
            預測結果
        """
        try:
            # 轉換為適當的格式
            if hasattr(X, "shape") and len(X.shape) == 1:
                X = X.reshape(1, -1)

            # 如果是分類問題，返回機率
            if self.class_names:
                if hasattr(self.model, "predict_proba"):
                    return self.model.predict_proba(X)
                else:
                    # 如果沒有 predict_proba，使用 predict 並轉換為機率格式
                    predictions = self.model.predict(X)
                    # 簡單的二元分類機率轉換
                    if len(self.class_names) == 2:
                        proba = np.column_stack([1 - predictions, predictions])
                        return proba
                    else:
                        return predictions
            else:
                # 回歸問題
                return self.model.predict(X)

        except Exception as e:
            logger.error(f"預測函數執行錯誤: {e}")
            raise RuntimeError(f"預測失敗: {e}") from e

    def _create_overall_plot(self, importance_df: pd.DataFrame) -> str:
        """
        創建整體重要性視覺化圖表

        Args:
            importance_df: 重要性資料框

        Returns:
            圖表檔案路徑
        """
        try:
            plt.figure(figsize=(12, 8))

            # 選擇前 N 個重要特徵
            top_features = importance_df.head(15)

            # 創建水平條形圖
            colors = ["red" if x < 0 else "blue" for x in top_features["importance"]]

            plt.barh(range(len(top_features)), top_features["importance"], color=colors)
            plt.yticks(range(len(top_features)), top_features["feature"])
            plt.xlabel("Average LIME Importance")
            plt.title("LIME Feature Importance (Average across instances)")
            plt.grid(axis="x", alpha=0.3)

            # 添加零線
            plt.axvline(x=0, color="black", linestyle="-", alpha=0.5)

            plt.tight_layout()

            # 保存圖表
            plot_path = os.path.join(self.output_dir, "lime_overall_importance.png")
            plt.savefig(plot_path, dpi=300, bbox_inches="tight")
            plt.close()

            logger.info(f"LIME 整體重要性圖已保存: {plot_path}")
            return plot_path

        except Exception as e:
            logger.error(f"創建 LIME 整體圖表時發生錯誤: {e}")
            plt.close()  # 確保關閉圖表
            return ""
