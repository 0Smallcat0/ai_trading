# -*- coding: utf-8 -*-
"""
模型監控器

此模組實現模型監控功能，包括：
- 預測記錄和追蹤
- 模型效能監控
- 資料漂移檢測
- 監控指標計算

Classes:
    ModelMonitor: 模型監控器主類
"""

import datetime
import logging
from typing import Any, Dict, List, Optional, Union

import mlflow
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from src.config import LOG_LEVEL
from src.models.model_base import ModelBase
from .registry import ModelRegistry
from .utils import calculate_model_drift

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class ModelMonitor:
    """
    模型監控器
    
    監控模型效能、預測品質和資料漂移的工具。
    
    Attributes:
        model_name: 模型名稱
        version: 模型版本
        model: 模型實例
        registry: 模型註冊表
        monitoring_data: 監控資料列表
        
    Example:
        >>> monitor = ModelMonitor("my_model", "v1.0")
        >>> monitor.log_prediction(features, prediction, actual_value)
        >>> metrics = monitor.calculate_metrics()
        >>> drift_score = monitor.detect_drift(new_features)
        
    Note:
        監控資料會自動記錄到 MLflow
        支援分類和回歸問題的監控
        提供資料漂移檢測功能
    """

    def __init__(
        self,
        model_name: str,
        version: Optional[str] = None,
        registry: Optional[ModelRegistry] = None,
        max_records: int = 10000
    ):
        """
        初始化模型監控器

        Args:
            model_name: 模型名稱
            version: 模型版本，如果為 None 則使用最新版本
            registry: 模型註冊表實例
            max_records: 最大監控記錄數量
            
        Raises:
            ValueError: 當模型不存在時
        """
        self.model_name = model_name
        self.registry = registry or ModelRegistry()
        self.max_records = max_records

        try:
            # 獲取模型資訊
            self.model_info = self.registry.get_model_info(model_name, version)
            self.version = self.model_info["version"]

            # 載入模型
            self.model = self.registry.load_model(model_name, self.version)

            # 初始化監控資料
            self.monitoring_data: List[Dict[str, Any]] = []
            self.baseline_features: Optional[pd.DataFrame] = None
            
            logger.info(f"模型監控器已初始化: {model_name} v{self.version}")
            
        except Exception as e:
            logger.error(f"初始化模型監控器失敗: {e}")
            raise ValueError(f"無法初始化監控器: {e}") from e

    def log_prediction(
        self,
        features: Union[pd.DataFrame, pd.Series, np.ndarray],
        prediction: Union[float, int, np.ndarray, List],
        actual: Optional[Union[float, int, np.ndarray, List]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        log_to_mlflow: bool = True
    ) -> None:
        """
        記錄預測結果
        
        Args:
            features: 輸入特徵
            prediction: 預測值
            actual: 實際值（可選）
            metadata: 額外的元數據
            log_to_mlflow: 是否記錄到 MLflow
            
        Example:
            >>> monitor.log_prediction(
            ...     features=X_test.iloc[0],
            ...     prediction=0.85,
            ...     actual=1.0,
            ...     metadata={"timestamp": "2024-01-01", "source": "api"}
            ... )
        """
        try:
            # 準備特徵資料
            if isinstance(features, pd.Series):
                features_dict = features.to_dict()
            elif isinstance(features, pd.DataFrame):
                features_dict = (
                    features.iloc[0].to_dict() if len(features) == 1
                    else features.to_dict(orient="records")
                )
            elif isinstance(features, np.ndarray):
                feature_names = self.model.feature_names or [f"feature_{i}" for i in range(len(features))]
                features_dict = dict(zip(feature_names, features))
            else:
                features_dict = features

            # 準備預測值
            prediction_value = (
                prediction.tolist() if isinstance(prediction, np.ndarray)
                else prediction
            )

            # 準備實際值
            actual_value = (
                actual.tolist() if isinstance(actual, np.ndarray)
                else actual
            )

            # 創建監控記錄
            record = {
                "timestamp": datetime.datetime.now().isoformat(),
                "model_name": self.model_name,
                "version": self.version,
                "features": features_dict,
                "prediction": prediction_value,
                "actual": actual_value,
                "metadata": metadata or {}
            }

            # 添加到監控資料
            self.monitoring_data.append(record)

            # 限制記錄數量
            if len(self.monitoring_data) > self.max_records:
                self.monitoring_data = self.monitoring_data[-self.max_records:]

            # 記錄到 MLflow
            if log_to_mlflow and self.model_info.get("run_id"):
                self._log_to_mlflow(record)

            logger.debug(f"已記錄預測: {self.model_name} v{self.version}")
            
        except Exception as e:
            logger.error(f"記錄預測時發生錯誤: {e}")
            raise RuntimeError(f"預測記錄失敗: {e}") from e

    def _log_to_mlflow(self, record: Dict[str, Any]) -> None:
        """
        記錄到 MLflow
        
        Args:
            record: 監控記錄
        """
        try:
            with mlflow.start_run(run_id=self.model_info["run_id"]):
                # 記錄預測計數
                mlflow.log_metric("prediction_count", len(self.monitoring_data))

                # 記錄預測誤差（如果有實際值）
                if record["actual"] is not None:
                    prediction = record["prediction"]
                    actual = record["actual"]
                    
                    if isinstance(prediction, (list, np.ndarray)) and isinstance(actual, (list, np.ndarray)):
                        error = np.mean(np.abs(np.array(prediction) - np.array(actual)))
                    else:
                        error = abs(prediction - actual)
                    
                    mlflow.log_metric("prediction_error", error)
                    
        except Exception as e:
            logger.warning(f"MLflow 記錄失敗: {e}")

    def calculate_metrics(self) -> Dict[str, float]:
        """
        計算監控指標
        
        Returns:
            監控指標字典
            
        Example:
            >>> metrics = monitor.calculate_metrics()
            >>> print(f"Accuracy: {metrics.get('accuracy', 'N/A')}")
            >>> print(f"RMSE: {metrics.get('rmse', 'N/A')}")
        """
        if not self.monitoring_data:
            logger.warning("沒有監控資料")
            return {}

        try:
            # 提取有實際值的記錄
            valid_records = [
                record for record in self.monitoring_data
                if record["actual"] is not None
            ]

            if not valid_records:
                logger.warning("沒有包含實際值的監控資料")
                return {}

            # 提取預測值和實際值
            predictions = [record["prediction"] for record in valid_records]
            actuals = [record["actual"] for record in valid_records]

            metrics = {}

            # 判斷問題類型並計算相應指標
            if self._is_classification_problem():
                metrics.update(self._calculate_classification_metrics(actuals, predictions))
            else:
                metrics.update(self._calculate_regression_metrics(actuals, predictions))

            # 計算通用指標
            metrics["total_predictions"] = len(self.monitoring_data)
            metrics["predictions_with_actuals"] = len(valid_records)
            metrics["coverage"] = len(valid_records) / len(self.monitoring_data)

            return metrics
            
        except Exception as e:
            logger.error(f"計算監控指標時發生錯誤: {e}")
            return {}

    def _is_classification_problem(self) -> bool:
        """
        判斷是否為分類問題
        
        Returns:
            是否為分類問題
        """
        return hasattr(self.model, "is_classifier") and self.model.is_classifier

    def _calculate_classification_metrics(
        self, 
        actuals: List, 
        predictions: List
    ) -> Dict[str, float]:
        """
        計算分類指標
        
        Args:
            actuals: 實際值列表
            predictions: 預測值列表
            
        Returns:
            分類指標字典
        """
        try:
            metrics = {}
            metrics["accuracy"] = accuracy_score(actuals, predictions)
            metrics["precision"] = precision_score(actuals, predictions, average="weighted", zero_division=0)
            metrics["recall"] = recall_score(actuals, predictions, average="weighted", zero_division=0)
            metrics["f1"] = f1_score(actuals, predictions, average="weighted", zero_division=0)
            return metrics
        except Exception as e:
            logger.error(f"計算分類指標失敗: {e}")
            return {}

    def _calculate_regression_metrics(
        self, 
        actuals: List, 
        predictions: List
    ) -> Dict[str, float]:
        """
        計算回歸指標
        
        Args:
            actuals: 實際值列表
            predictions: 預測值列表
            
        Returns:
            回歸指標字典
        """
        try:
            actuals_array = np.array(actuals)
            predictions_array = np.array(predictions)
            
            metrics = {}
            
            # 基本誤差指標
            metrics["mse"] = np.mean((actuals_array - predictions_array) ** 2)
            metrics["rmse"] = np.sqrt(metrics["mse"])
            metrics["mae"] = np.mean(np.abs(actuals_array - predictions_array))
            metrics["mape"] = np.mean(np.abs((actuals_array - predictions_array) / actuals_array)) * 100

            # R² 指標
            y_mean = np.mean(actuals_array)
            ss_total = np.sum((actuals_array - y_mean) ** 2)
            ss_residual = np.sum((actuals_array - predictions_array) ** 2)
            metrics["r2"] = 1 - (ss_residual / ss_total) if ss_total != 0 else 0

            return metrics
        except Exception as e:
            logger.error(f"計算回歸指標失敗: {e}")
            return {}

    def detect_drift(
        self, 
        new_features: pd.DataFrame,
        method: str = "ks_test",
        threshold: float = 0.05
    ) -> Dict[str, Any]:
        """
        檢測資料漂移
        
        Args:
            new_features: 新的特徵資料
            method: 漂移檢測方法
            threshold: 漂移閾值
            
        Returns:
            漂移檢測結果
            
        Example:
            >>> drift_result = monitor.detect_drift(new_data)
            >>> if drift_result["drift_detected"]:
            ...     print("檢測到資料漂移!")
        """
        if self.baseline_features is None:
            logger.warning("沒有基準特徵資料，無法檢測漂移")
            return {"drift_detected": False, "message": "No baseline data"}

        try:
            drift_result = calculate_model_drift(
                baseline_features=self.baseline_features,
                new_features=new_features,
                method=method,
                threshold=threshold
            )
            
            logger.info(f"漂移檢測完成: {drift_result['drift_detected']}")
            return drift_result
            
        except Exception as e:
            logger.error(f"漂移檢測失敗: {e}")
            return {"drift_detected": False, "error": str(e)}

    def set_baseline(self, baseline_features: pd.DataFrame) -> None:
        """
        設定基準特徵資料
        
        Args:
            baseline_features: 基準特徵資料
            
        Example:
            >>> monitor.set_baseline(X_train)
        """
        self.baseline_features = baseline_features.copy()
        logger.info(f"已設定基準資料: {baseline_features.shape}")

    def get_monitoring_summary(self) -> Dict[str, Any]:
        """
        獲取監控摘要
        
        Returns:
            監控摘要字典
            
        Example:
            >>> summary = monitor.get_monitoring_summary()
            >>> print(f"Total predictions: {summary['total_predictions']}")
        """
        metrics = self.calculate_metrics()
        
        summary = {
            "model_name": self.model_name,
            "version": self.version,
            "total_predictions": len(self.monitoring_data),
            "monitoring_period": self._get_monitoring_period(),
            "latest_metrics": metrics,
            "has_baseline": self.baseline_features is not None
        }
        
        return summary

    def _get_monitoring_period(self) -> Dict[str, str]:
        """
        獲取監控時間範圍
        
        Returns:
            監控時間範圍字典
        """
        if not self.monitoring_data:
            return {"start": None, "end": None}
            
        timestamps = [record["timestamp"] for record in self.monitoring_data]
        return {
            "start": min(timestamps),
            "end": max(timestamps)
        }
