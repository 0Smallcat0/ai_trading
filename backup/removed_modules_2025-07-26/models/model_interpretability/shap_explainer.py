# -*- coding: utf-8 -*-
"""
SHAP 解釋器

此模組實現基於 SHAP (SHapley Additive exPlanations) 的模型解釋功能，提供：
- 樹模型解釋器
- 線性模型解釋器
- 深度學習模型解釋器
- SHAP 值計算和視覺化

Classes:
    SHAPExplainer: SHAP 解釋器主類
"""

import logging
import os
from typing import Any, Dict, List, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import LOG_LEVEL
from src.models.model_base import ModelBase
from .utils import validate_explanation_inputs, save_explanation_results

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))

# 檢查 SHAP 是否可用
try:
    import shap

    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP 未安裝，SHAP 解釋功能將無法使用")


class SHAPExplainer:
    """
    SHAP 解釋器

    使用 SHAP (SHapley Additive exPlanations) 方法解釋模型預測結果。
    支援多種模型類型和視覺化選項。

    Attributes:
        model: 要解釋的模型實例
        feature_names: 特徵名稱列表
        class_names: 類別名稱列表
        output_dir: 結果輸出目錄
        explainer: SHAP 解釋器實例

    Example:
        >>> explainer = SHAPExplainer(model, feature_names=features)
        >>> results = explainer.explain(X_test, plot_type="summary")

    Note:
        需要安裝 shap 套件才能使用此功能
        不同模型類型會自動選擇適當的 SHAP 解釋器
    """

    def __init__(
        self,
        model: ModelBase,
        feature_names: Optional[List[str]] = None,
        class_names: Optional[List[str]] = None,
        output_dir: Optional[str] = None,
    ) -> None:
        """
        初始化 SHAP 解釋器

        Args:
            model: 要解釋的模型，必須是已訓練的 ModelBase 實例
            feature_names: 特徵名稱列表
            class_names: 類別名稱列表
            output_dir: 結果輸出目錄

        Raises:
            ImportError: 當 SHAP 未安裝時
            ValueError: 當模型未訓練時

        Example:
            >>> explainer = SHAPExplainer(
            ...     model=my_model,
            ...     feature_names=['age', 'income'],
            ...     output_dir='./shap_results'
            ... )
        """
        if not SHAP_AVAILABLE:
            raise ImportError("SHAP 未安裝，無法使用 SHAP 解釋功能")

        if not model.trained:
            raise ValueError("模型必須已經訓練完成")

        self.model = model
        self.feature_names = feature_names
        self.class_names = class_names
        self.output_dir = output_dir or "./shap_results"
        self.explainer: Optional[Any] = None

        # 創建輸出目錄
        os.makedirs(self.output_dir, exist_ok=True)

        logger.info(f"SHAP 解釋器已初始化: {model.name}")

    def _create_explainer(self, X: Any) -> Any:
        """
        創建適當的 SHAP 解釋器

        Args:
            X: 特徵資料

        Returns:
            SHAP 解釋器實例

        Raises:
            ValueError: 當無法確定適當的解釋器類型時
        """
        model_type = self.model.__class__.__name__.lower()

        try:
            # 根據模型類型選擇解釋器
            if any(
                tree_type in model_type
                for tree_type in ["tree", "forest", "xgb", "lgb"]
            ):
                # 樹模型解釋器
                explainer = shap.TreeExplainer(self.model.model)
                logger.info("使用 TreeExplainer")

            elif any(
                linear_type in model_type for linear_type in ["linear", "logistic"]
            ):
                # 線性模型解釋器
                explainer = shap.LinearExplainer(self.model.model, X)
                logger.info("使用 LinearExplainer")

            else:
                # 通用解釋器（適用於任何模型）
                explainer = shap.Explainer(self.model.predict, X)
                logger.info("使用通用 Explainer")

            return explainer

        except Exception as e:
            logger.error(f"創建 SHAP 解釋器時發生錯誤: {e}")
            raise ValueError(f"無法創建適當的 SHAP 解釋器: {e}") from e

    def explain(
        self,
        X: Any,
        plot_type: str = "summary",
        sample_size: Optional[int] = None,
        log_to_mlflow: bool = True,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        執行 SHAP 解釋

        Args:
            X: 特徵資料
            plot_type: 圖表類型，可選 "summary", "waterfall", "force", "dependence"
            sample_size: 樣本大小，None 表示使用全部資料
            log_to_mlflow: 是否記錄到 MLflow
            **kwargs: 額外參數

        Returns:
            包含 SHAP 解釋結果的字典

        Raises:
            ValueError: 當輸入資料無效時
            RuntimeError: 當解釋過程失敗時

        Example:
            >>> results = explainer.explain(X_test, plot_type="summary")
            >>> print(f"SHAP values shape: {results['shap_values'].shape}")
        """
        # 驗證輸入
        validate_explanation_inputs(X, feature_names=self.feature_names)

        # 採樣資料（如果指定）
        if sample_size is not None and len(X) > sample_size:
            sample_indices = np.random.choice(len(X), sample_size, replace=False)
            X_sample = (
                X.iloc[sample_indices] if hasattr(X, "iloc") else X[sample_indices]
            )
        else:
            X_sample = X

        try:
            # 創建解釋器
            if self.explainer is None:
                self.explainer = self._create_explainer(X_sample)

            # 計算 SHAP 值
            logger.info(f"計算 SHAP 值，樣本數: {len(X_sample)}")
            shap_values = self.explainer(X_sample)

            # 提取 SHAP 值（處理不同的返回格式）
            if hasattr(shap_values, "values"):
                values = shap_values.values
                base_values = shap_values.base_values
            else:
                values = shap_values
                base_values = None

            # 創建特徵重要性資料框
            if len(values.shape) == 2:
                # 回歸或二元分類
                importance = np.abs(values).mean(axis=0)
            else:
                # 多元分類
                importance = np.abs(values).mean(axis=(0, 2))

            feature_names = self.feature_names or [
                f"feature_{i}" for i in range(len(importance))
            ]
            importance_df = pd.DataFrame(
                {"feature": feature_names, "importance": importance}
            ).sort_values("importance", ascending=False)

            # 繪製圖表
            plot_path = self._create_plot(shap_values, X_sample, plot_type, **kwargs)

            # 準備結果
            results = {
                "shap_values": values,
                "base_values": base_values,
                "importance": importance_df,
                "plot_path": plot_path,
                "feature_names": feature_names,
                "sample_size": len(X_sample),
            }

            # 保存結果
            saved_paths = save_explanation_results(
                results, self.output_dir, "shap", log_to_mlflow
            )
            results["saved_paths"] = saved_paths

            logger.info(f"SHAP 解釋完成，樣本數: {len(X_sample)}")

            return results

        except Exception as e:
            logger.error(f"SHAP 解釋時發生錯誤: {e}")
            raise RuntimeError(f"SHAP 解釋執行失敗: {e}") from e

    def _create_plot(
        self, shap_values: Any, X: Any, plot_type: str, **kwargs: Any
    ) -> str:
        """
        創建 SHAP 視覺化圖表

        Args:
            shap_values: SHAP 值
            X: 特徵資料
            plot_type: 圖表類型
            **kwargs: 額外參數

        Returns:
            圖表檔案路徑
        """
        try:
            plt.figure(figsize=(12, 8))

            if plot_type == "summary":
                shap.summary_plot(
                    shap_values,
                    X,
                    feature_names=self.feature_names,
                    show=False,
                    **kwargs,
                )
            elif plot_type == "waterfall":
                if hasattr(shap_values, "values"):
                    shap.waterfall_plot(shap_values[0], show=False, **kwargs)
                else:
                    logger.warning("Waterfall plot 需要 Explanation 物件")
            elif plot_type == "force":
                if hasattr(shap_values, "values"):
                    shap.force_plot(
                        shap_values.base_values[0],
                        shap_values.values[0],
                        X.iloc[0] if hasattr(X, "iloc") else X[0],
                        feature_names=self.feature_names,
                        matplotlib=True,
                        show=False,
                        **kwargs,
                    )
                else:
                    logger.warning("Force plot 需要 Explanation 物件")
            else:
                logger.warning(f"未知的圖表類型: {plot_type}，使用 summary plot")
                shap.summary_plot(
                    shap_values,
                    X,
                    feature_names=self.feature_names,
                    show=False,
                    **kwargs,
                )

            # 保存圖表
            plot_path = os.path.join(self.output_dir, f"shap_{plot_type}_plot.png")
            plt.savefig(plot_path, dpi=300, bbox_inches="tight")
            plt.close()

            logger.info(f"SHAP 圖表已保存: {plot_path}")
            return plot_path

        except Exception as e:
            logger.error(f"創建 SHAP 圖表時發生錯誤: {e}")
            plt.close()  # 確保關閉圖表
            # 返回空路徑而不是拋出異常
            return ""
