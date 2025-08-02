# -*- coding: utf-8 -*-
"""
模型評估器

此模組實現模型評估功能，包括：
- 標準化評估流程
- 多種評估指標計算
- 評估結果可視化
- 評估報告生成

Classes:
    ModelEvaluator: 主要的模型評估器類別
"""

import logging
from typing import Dict

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)

from src.config import LOG_LEVEL
from src.models.model_base import ModelBase

from .config import TrainingConfig

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class ModelEvaluator:
    """
    模型評估器

    提供標準化的模型評估功能，支援分類和回歸任務。

    Attributes:
        model: 要評估的模型實例
        config: 訓練配置

    Example:
        >>> evaluator = ModelEvaluator(trained_model, config)
        >>> metrics = evaluator.evaluate(X_test, y_test)
        >>> evaluator.generate_report(X_test, y_test, "evaluation_report.html")

    Note:
        支援多種評估指標和可視化
        自動檢測任務類型（分類/回歸）
        整合 MLflow 進行結果記錄
    """

    def __init__(self, model: ModelBase, config: TrainingConfig = None):
        """
        初始化模型評估器

        Args:
            model: 要評估的模型實例
            config: 訓練配置

        Raises:
            ValueError: 當模型無效時
        """
        if not isinstance(model, ModelBase):
            raise ValueError("模型必須繼承自 ModelBase")

        self.model = model
        self.config = config or TrainingConfig()

        logger.info(f"模型評估器已初始化: {model.name}")

    def evaluate(
        self, X: pd.DataFrame, y: pd.Series, task_type: str = "auto"
    ) -> Dict[str, float]:
        """
        評估模型

        Args:
            X: 特徵數據
            y: 目標變數
            task_type: 任務類型 ("classification", "regression", "auto")

        Returns:
            評估指標字典

        Raises:
            ValueError: 當模型未訓練或數據無效時

        Example:
            >>> metrics = evaluator.evaluate(X_test, y_test)
            >>> print(f"Accuracy: {metrics.get('accuracy', 'N/A')}")
        """
        if not self.model.trained:
            raise ValueError("模型尚未訓練，無法評估")

        if X.empty or y.empty:
            raise ValueError("評估數據不能為空")

        try:
            # 預測
            y_pred = self.model.predict(X)

            # 自動檢測任務類型
            if task_type == "auto":
                task_type = self._detect_task_type(y)

            # 計算指標
            if task_type == "classification":
                metrics = self._calculate_classification_metrics(y, y_pred)
            else:
                metrics = self._calculate_regression_metrics(y, y_pred)

            logger.info(f"模型評估完成，任務類型: {task_type}")
            return metrics

        except Exception as e:
            logger.error(f"模型評估失敗: {e}")
            raise RuntimeError(f"評估失敗: {e}") from e

    def _detect_task_type(self, y: pd.Series) -> str:
        """
        自動檢測任務類型

        Args:
            y: 目標變數

        Returns:
            任務類型 ("classification" 或 "regression")
        """
        # 檢查是否為分類任務
        unique_values = y.nunique()

        # 如果唯一值少於10個且都是整數，認為是分類
        if unique_values <= 10 and y.dtype in ["int64", "int32", "object", "category"]:
            return "classification"

        # 否則認為是回歸
        return "regression"

    def _calculate_classification_metrics(
        self, y_true: pd.Series, y_pred: np.ndarray
    ) -> Dict[str, float]:
        """
        計算分類指標

        Args:
            y_true: 真實標籤
            y_pred: 預測標籤

        Returns:
            分類指標字典
        """
        metrics = {}

        try:
            metrics["accuracy"] = accuracy_score(y_true, y_pred)
            metrics["precision"] = precision_score(
                y_true, y_pred, average="weighted", zero_division=0
            )
            metrics["recall"] = recall_score(
                y_true, y_pred, average="weighted", zero_division=0
            )
            metrics["f1"] = f1_score(
                y_true, y_pred, average="weighted", zero_division=0
            )

            # 計算勝率（用於交易策略評估）
            if len(np.unique(y_true)) == 2:  # 二分類
                metrics["win_rate"] = accuracy_score(y_true, y_pred)

        except Exception as e:
            logger.warning(f"計算分類指標時出現警告: {e}")

        return metrics

    def _calculate_regression_metrics(
        self, y_true: pd.Series, y_pred: np.ndarray
    ) -> Dict[str, float]:
        """
        計算回歸指標

        Args:
            y_true: 真實值
            y_pred: 預測值

        Returns:
            回歸指標字典
        """
        metrics = {}

        try:
            metrics["mse"] = mean_squared_error(y_true, y_pred)
            metrics["rmse"] = np.sqrt(metrics["mse"])
            metrics["mae"] = mean_absolute_error(y_true, y_pred)
            metrics["r2"] = r2_score(y_true, y_pred)

            # 計算 MAPE（平均絕對百分比誤差）
            mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
            metrics["mape"] = mape

            # 計算交易相關指標
            if "return" in str(y_true.name).lower():
                metrics.update(self._calculate_trading_metrics(y_true, y_pred))

        except Exception as e:
            logger.warning(f"計算回歸指標時出現警告: {e}")

        return metrics

    def _calculate_trading_metrics(
        self, y_true: pd.Series, y_pred: np.ndarray
    ) -> Dict[str, float]:
        """
        計算交易相關指標

        Args:
            y_true: 真實收益率
            y_pred: 預測收益率

        Returns:
            交易指標字典
        """
        metrics = {}

        try:
            # 計算 Sharpe Ratio
            if np.std(y_pred) > 0:
                metrics["sharpe_ratio"] = (
                    np.mean(y_pred) / np.std(y_pred) * np.sqrt(252)
                )

            # 計算最大回撤
            cumulative_returns = (1 + pd.Series(y_pred)).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - rolling_max) / rolling_max
            metrics["max_drawdown"] = drawdown.min()

            # 計算勝率
            win_rate = (y_pred > 0).mean()
            metrics["win_rate"] = win_rate

        except Exception as e:
            logger.warning(f"計算交易指標時出現警告: {e}")

        return metrics

    def generate_report(
        self, X: pd.DataFrame, y: pd.Series, output_path: str = "evaluation_report.html"
    ) -> str:
        """
        生成評估報告

        Args:
            X: 特徵數據
            y: 目標變數
            output_path: 報告輸出路徑

        Returns:
            報告檔案路徑

        Example:
            >>> report_path = evaluator.generate_report(X_test, y_test)
        """
        try:
            # 評估模型
            metrics = self.evaluate(X, y)

            # 生成 HTML 報告
            html_content = self._generate_html_report(metrics, X, y)

            # 保存報告
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.info(f"評估報告已生成: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"生成評估報告失敗: {e}")
            raise RuntimeError(f"報告生成失敗: {e}") from e

    def _generate_html_report(
        self, metrics: Dict[str, float], X: pd.DataFrame, y: pd.Series
    ) -> str:
        """
        生成 HTML 評估報告

        Args:
            metrics: 評估指標
            X: 特徵數據
            y: 目標變數

        Returns:
            HTML 內容字符串
        """
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>模型評估報告</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .metric {{ margin: 10px 0; }}
                .metric-name {{ font-weight: bold; }}
                .metric-value {{ color: #007bff; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>模型評估報告</h1>
            <h2>模型資訊</h2>
            <p><strong>模型名稱:</strong> {model_name}</p>
            <p><strong>評估時間:</strong> {timestamp}</p>

            <h2>評估指標</h2>
            <table>
                <tr><th>指標名稱</th><th>數值</th></tr>
                {metrics_table}
            </table>

            <h2>數據概要</h2>
            <p><strong>樣本數量:</strong> {sample_count}</p>
            <p><strong>特徵數量:</strong> {feature_count}</p>
        </body>
        </html>
        """

        # 格式化指標表格
        metrics_rows = []
        for name, value in metrics.items():
            if isinstance(value, float):
                formatted_value = f"{value:.4f}"
            else:
                formatted_value = str(value)
            metrics_rows.append(f"<tr><td>{name}</td><td>{formatted_value}</td></tr>")

        metrics_table = "\n".join(metrics_rows)

        # 填充模板
        html_content = html_template.format(
            model_name=self.model.name,
            timestamp=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            metrics_table=metrics_table,
            sample_count=len(X),
            feature_count=len(X.columns),
        )

        return html_content
