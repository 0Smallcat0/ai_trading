# -*- coding: utf-8 -*-
"""
交叉驗證器

此模組實現模型交叉驗證功能，包括：
- 時間序列交叉驗證
- K-折交叉驗證
- 自定義分割策略
- 驗證結果統計

Classes:
    CrossValidator: 交叉驗證器主類
"""

import logging
from typing import Any, Dict, List, Optional

import mlflow
import numpy as np
import pandas as pd
from sklearn.model_selection import KFold, TimeSeriesSplit

from src.config import LOG_LEVEL
from src.models.model_base import ModelBase
from src.models.model_factory import create_model
from .config import TrainingConfig
from .utils import validate_training_inputs, setup_mlflow_tracking

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class CrossValidator:
    """
    交叉驗證器
    
    提供多種交叉驗證策略，特別適用於時間序列資料。
    
    Attributes:
        model: 要驗證的模型實例
        config: 訓練配置
        cv_results: 交叉驗證結果
        
    Example:
        >>> validator = CrossValidator(model, config)
        >>> results = validator.cross_validate(X, y, cv=5, time_series=True)
        >>> print(f"Average validation score: {results['avg_val_metrics']}")
        
    Note:
        支援時間序列和常規交叉驗證
        自動記錄每折的訓練結果
        提供詳細的統計分析
    """

    def __init__(self, model: ModelBase, config: TrainingConfig):
        """
        初始化交叉驗證器

        Args:
            model: 要驗證的模型實例
            config: 訓練配置實例
            
        Raises:
            ValueError: 當模型或配置無效時
        """
        if not isinstance(model, ModelBase):
            raise ValueError("model 必須是 ModelBase 的實例")
        
        if not isinstance(config, TrainingConfig):
            raise ValueError("config 必須是 TrainingConfig 的實例")

        self.model = model
        self.config = config
        self.cv_results: List[Dict[str, Any]] = []

        logger.info(f"交叉驗證器已初始化: {model.name}")

    def cross_validate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        cv: int = 5,
        time_series: bool = True,
        log_to_mlflow: bool = True,
        **train_params: Any
    ) -> Dict[str, Any]:
        """
        執行交叉驗證
        
        Args:
            X: 特徵資料
            y: 目標資料
            cv: 折數
            time_series: 是否使用時間序列分割
            log_to_mlflow: 是否記錄到 MLflow
            **train_params: 其他訓練參數
            
        Returns:
            交叉驗證結果字典
            
        Raises:
            ValueError: 當輸入資料無效時
            RuntimeError: 當交叉驗證失敗時
            
        Example:
            >>> results = validator.cross_validate(
            ...     X=X, y=y, cv=5, time_series=True,
            ...     epochs=50, batch_size=32
            ... )
        """
        try:
            # 驗證輸入
            validate_training_inputs(X, y)

            # 選擇分割器
            splitter = self._create_splitter(cv, time_series)

            # 開始 MLflow 追蹤
            run_id = None
            if log_to_mlflow:
                setup_mlflow_tracking(self.config)
                mlflow.start_run()
                run_id = mlflow.active_run().info.run_id

                # 記錄交叉驗證參數
                mlflow.log_params({
                    "cv_folds": cv,
                    "time_series": time_series,
                    "model_type": self.model.__class__.__name__,
                    **self.model.get_params(),
                    **train_params
                })

            # 執行交叉驗證
            logger.info(
                f"開始交叉驗證: {self.model.name}, cv={cv}, time_series={time_series}"
            )

            self.cv_results = []
            fold = 1

            for train_idx, val_idx in splitter.split(X):
                logger.info(f"訓練折 {fold}/{cv}")

                # 分割資料
                X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
                y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

                # 創建模型副本
                model_copy = self._create_model_copy(fold)

                # 訓練模型
                model_copy.train(X_train, y_train, **train_params)

                # 評估模型
                train_metrics = model_copy.evaluate(X_train, y_train)
                val_metrics = model_copy.evaluate(X_val, y_val)

                # 記錄結果
                fold_result = {
                    "fold": fold,
                    "train_size": len(X_train),
                    "val_size": len(X_val),
                    "train_metrics": train_metrics,
                    "val_metrics": val_metrics,
                    "model": model_copy
                }
                self.cv_results.append(fold_result)

                # 記錄到 MLflow
                if log_to_mlflow:
                    self._log_fold_metrics(fold, train_metrics, val_metrics)

                fold += 1

            # 計算統計結果
            stats_results = self._calculate_cv_statistics()

            # 記錄統計結果到 MLflow
            if log_to_mlflow:
                self._log_cv_statistics(stats_results)
                mlflow.end_run()

            logger.info("交叉驗證完成")
            logger.info(f"平均驗證指標: {stats_results['avg_val_metrics']}")

            return {
                "cv_results": self.cv_results,
                "statistics": stats_results,
                "run_id": run_id,
                "config": {
                    "cv_folds": cv,
                    "time_series": time_series,
                    "train_params": train_params
                }
            }

        except Exception as e:
            logger.error(f"交叉驗證時發生錯誤: {e}")
            if log_to_mlflow and mlflow.active_run():
                mlflow.end_run()
            raise RuntimeError(f"交叉驗證失敗: {e}") from e

    def _create_splitter(self, cv: int, time_series: bool):
        """
        創建資料分割器
        
        Args:
            cv: 折數
            time_series: 是否使用時間序列分割
            
        Returns:
            分割器實例
        """
        if time_series:
            return TimeSeriesSplit(n_splits=cv)
        else:
            return KFold(n_splits=cv, shuffle=True, random_state=42)

    def _create_model_copy(self, fold: int) -> ModelBase:
        """
        創建模型副本
        
        Args:
            fold: 折數
            
        Returns:
            模型副本實例
        """
        try:
            model_type = self.model.__class__.__name__.lower().replace("model", "")
            model_copy = create_model(
                model_type=model_type,
                name=f"{self.model.name}_fold{fold}",
                **self.model.get_params()
            )
            return model_copy
        except Exception as e:
            logger.error(f"創建模型副本失敗: {e}")
            raise RuntimeError(f"無法創建模型副本: {e}") from e

    def _log_fold_metrics(
        self, 
        fold: int, 
        train_metrics: Dict[str, float], 
        val_metrics: Dict[str, float]
    ) -> None:
        """
        記錄單折指標到 MLflow
        
        Args:
            fold: 折數
            train_metrics: 訓練指標
            val_metrics: 驗證指標
        """
        try:
            for key, value in train_metrics.items():
                mlflow.log_metric(f"fold{fold}_train_{key}", value)
            for key, value in val_metrics.items():
                mlflow.log_metric(f"fold{fold}_val_{key}", value)
        except Exception as e:
            logger.warning(f"記錄折 {fold} 指標失敗: {e}")

    def _calculate_cv_statistics(self) -> Dict[str, Any]:
        """
        計算交叉驗證統計結果
        
        Returns:
            統計結果字典
        """
        if not self.cv_results:
            return {}

        try:
            # 提取所有指標
            all_train_metrics = [r["train_metrics"] for r in self.cv_results]
            all_val_metrics = [r["val_metrics"] for r in self.cv_results]

            # 計算平均值和標準差
            avg_train_metrics = self._calculate_metric_statistics(all_train_metrics, "mean")
            std_train_metrics = self._calculate_metric_statistics(all_train_metrics, "std")
            avg_val_metrics = self._calculate_metric_statistics(all_val_metrics, "mean")
            std_val_metrics = self._calculate_metric_statistics(all_val_metrics, "std")

            return {
                "avg_train_metrics": avg_train_metrics,
                "std_train_metrics": std_train_metrics,
                "avg_val_metrics": avg_val_metrics,
                "std_val_metrics": std_val_metrics,
                "n_folds": len(self.cv_results),
                "best_fold": self._find_best_fold(),
                "worst_fold": self._find_worst_fold()
            }
        except Exception as e:
            logger.error(f"計算統計結果失敗: {e}")
            return {}

    def _calculate_metric_statistics(
        self, 
        metrics_list: List[Dict[str, float]], 
        stat_type: str
    ) -> Dict[str, float]:
        """
        計算指標統計值
        
        Args:
            metrics_list: 指標列表
            stat_type: 統計類型 ("mean" 或 "std")
            
        Returns:
            統計結果字典
        """
        if not metrics_list:
            return {}

        # 獲取所有指標名稱
        metric_names = set()
        for metrics in metrics_list:
            metric_names.update(metrics.keys())

        # 計算統計值
        result = {}
        for metric_name in metric_names:
            values = [
                metrics.get(metric_name, 0) 
                for metrics in metrics_list 
                if metric_name in metrics
            ]
            
            if values:
                if stat_type == "mean":
                    result[metric_name] = np.mean(values)
                elif stat_type == "std":
                    result[metric_name] = np.std(values)

        return result

    def _find_best_fold(self) -> Dict[str, Any]:
        """
        找到最佳折
        
        Returns:
            最佳折資訊
        """
        if not self.cv_results:
            return {}

        # 使用主要指標（如果有的話）來判斷最佳折
        primary_metric = self._get_primary_metric()
        
        best_fold = max(
            self.cv_results,
            key=lambda x: x["val_metrics"].get(primary_metric, 0)
        )
        
        return {
            "fold": best_fold["fold"],
            "metric": primary_metric,
            "value": best_fold["val_metrics"].get(primary_metric, 0),
            "all_metrics": best_fold["val_metrics"]
        }

    def _find_worst_fold(self) -> Dict[str, Any]:
        """
        找到最差折
        
        Returns:
            最差折資訊
        """
        if not self.cv_results:
            return {}

        primary_metric = self._get_primary_metric()
        
        worst_fold = min(
            self.cv_results,
            key=lambda x: x["val_metrics"].get(primary_metric, 0)
        )
        
        return {
            "fold": worst_fold["fold"],
            "metric": primary_metric,
            "value": worst_fold["val_metrics"].get(primary_metric, 0),
            "all_metrics": worst_fold["val_metrics"]
        }

    def _get_primary_metric(self) -> str:
        """
        獲取主要評估指標
        
        Returns:
            主要指標名稱
        """
        # 根據模型類型選擇主要指標
        if hasattr(self.model, 'is_classifier') and self.model.is_classifier:
            return "accuracy"
        else:
            return "r2"

    def _log_cv_statistics(self, stats: Dict[str, Any]) -> None:
        """
        記錄交叉驗證統計結果到 MLflow
        
        Args:
            stats: 統計結果字典
        """
        try:
            # 記錄平均指標
            for key, value in stats.get("avg_train_metrics", {}).items():
                mlflow.log_metric(f"cv_avg_train_{key}", value)
            
            for key, value in stats.get("avg_val_metrics", {}).items():
                mlflow.log_metric(f"cv_avg_val_{key}", value)
            
            # 記錄標準差
            for key, value in stats.get("std_train_metrics", {}).items():
                mlflow.log_metric(f"cv_std_train_{key}", value)
            
            for key, value in stats.get("std_val_metrics", {}).items():
                mlflow.log_metric(f"cv_std_val_{key}", value)
            
            # 記錄最佳和最差折資訊
            best_fold = stats.get("best_fold", {})
            if best_fold:
                mlflow.log_metric("cv_best_fold", best_fold["fold"])
                mlflow.log_metric(f"cv_best_{best_fold['metric']}", best_fold["value"])
            
            worst_fold = stats.get("worst_fold", {})
            if worst_fold:
                mlflow.log_metric("cv_worst_fold", worst_fold["fold"])
                mlflow.log_metric(f"cv_worst_{worst_fold['metric']}", worst_fold["value"])
                
        except Exception as e:
            logger.warning(f"記錄交叉驗證統計結果失敗: {e}")

    def get_best_model(self) -> Optional[ModelBase]:
        """
        獲取最佳模型
        
        Returns:
            最佳模型實例，如果沒有則返回 None
            
        Example:
            >>> best_model = validator.get_best_model()
            >>> if best_model:
            ...     predictions = best_model.predict(X_test)
        """
        if not self.cv_results:
            return None

        primary_metric = self._get_primary_metric()
        
        best_fold = max(
            self.cv_results,
            key=lambda x: x["val_metrics"].get(primary_metric, 0)
        )
        
        return best_fold["model"]
