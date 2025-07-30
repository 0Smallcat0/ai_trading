# -*- coding: utf-8 -*-
"""
模型重訓練模組

此模組負責檢查模型性能並在需要時重訓練模型。
主要功能：
- 檢查模型性能指標
- 根據準確率下降閾值確定何時需要重訓練模型
- 自動化重訓練過程
- 在部署前驗證新模型
- 實現回滾機制
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import mlflow
import numpy as np
import pandas as pd
from mlflow.tracking import MlflowClient

from src.config import RESULTS_DIR
from src.core.logger import get_logger
from src.models.dataset import DatasetLoader
from src.models.model_factory import create_model
from src.models.model_governance import ModelRegistry
from src.models.performance_metrics import calculate_all_metrics
from src.models.training_pipeline import ModelTrainer

# 設定日誌
logger = get_logger("model_retrainer")


class ModelRetrainer:
    """模型重訓練類"""

    def __init__(
        self,
        model_registry: Optional[ModelRegistry] = None,
        mlflow_tracking_uri: Optional[str] = None,
    ):
        """
        初始化模型重訓練類

        Args:
            model_registry: 模型註冊表
            mlflow_tracking_uri: MLflow 追蹤 URI
        """
        # 初始化模型註冊表
        self.model_registry = model_registry or ModelRegistry()

        # 設置 MLflow 追蹤 URI
        if mlflow_tracking_uri:
            mlflow.set_tracking_uri(mlflow_tracking_uri)
        self.mlflow_client = MlflowClient()

        # 初始化資料集載入器
        self.dataset_loader = DatasetLoader()

        # 初始化模型性能歷史
        self.performance_history = self._load_performance_history()

        logger.info("模型重訓練器初始化完成")

    def _load_performance_history(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        載入模型性能歷史

        Returns:
            Dict[str, List[Dict[str, Any]]]: 模型性能歷史
        """
        history_path = os.path.join(RESULTS_DIR, "model_performance_history.json")
        if os.path.exists(history_path):
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"載入模型性能歷史時發生錯誤: {e}")
                return {}
        else:
            return {}

    def _save_performance_history(self):
        """保存模型性能歷史"""
        history_path = os.path.join(RESULTS_DIR, "model_performance_history.json")
        try:
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(self.performance_history, f, indent=2)
            logger.info(f"模型性能歷史已保存至: {history_path}")
        except Exception as e:
            logger.error(f"保存模型性能歷史時發生錯誤: {e}")

    def check_model_performance(
        self,
        models: Optional[List[str]] = None,
        accuracy_threshold: float = 0.05,
        sharpe_threshold: float = 0.2,
    ) -> List[str]:
        """
        檢查模型性能

        Args:
            models: 要檢查的模型列表，如果為 None，則檢查所有已註冊的模型
            accuracy_threshold: 準確率下降閾值
            sharpe_threshold: 夏普比率下降閾值

        Returns:
            List[str]: 需要重訓練的模型列表
        """
        # 如果未指定模型，則獲取所有已註冊的模型
        if models is None:
            models = self.model_registry.list_models()

        # 需要重訓練的模型列表
        models_to_retrain = []

        # 檢查每個模型的性能
        for model_name in models:
            try:
                # 獲取模型最新版本
                latest_version = self.model_registry.get_latest_version(model_name)
                if not latest_version:
                    logger.warning(f"找不到模型 {model_name} 的最新版本")
                    continue

                # 獲取模型性能指標
                metrics = self._evaluate_model(model_name, latest_version)

                # 檢查是否需要重訓練
                if self._needs_retraining(
                    model_name, metrics, accuracy_threshold, sharpe_threshold
                ):
                    models_to_retrain.append(model_name)
                    logger.info(f"模型 {model_name} 需要重訓練")
                else:
                    logger.info(f"模型 {model_name} 性能良好，無需重訓練")

                # 更新性能歷史
                if model_name not in self.performance_history:
                    self.performance_history[model_name] = []
                self.performance_history[model_name].append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "version": latest_version,
                        "metrics": metrics,
                    }
                )

                # 保存性能歷史
                self._save_performance_history()
            except Exception as e:
                logger.error(f"檢查模型 {model_name} 性能時發生錯誤: {e}")

        return models_to_retrain

    def _evaluate_model(self, model_name: str, version: str) -> Dict[str, float]:
        """
        評估模型性能

        Args:
            model_name: 模型名稱
            version: 模型版本

        Returns:
            Dict[str, float]: 性能指標
        """
        try:
            # 載入模型
            model = self.model_registry.load_model(model_name, version)

            # 準備評估資料
            test_data = self._prepare_test_data(model_name)
            if test_data is None:
                logger.error(f"無法準備模型 {model_name} 的測試資料")
                return {}

            X_test, y_test = test_data

            # 評估模型
            metrics = model.evaluate(X_test, y_test)

            # 如果是交易模型，計算額外的指標
            if hasattr(model, "predict_proba"):
                try:
                    # 獲取預測概率
                    y_pred_proba = model.predict_proba(X_test)
                    # 獲取預測類別
                    y_pred = (
                        np.argmax(y_pred_proba, axis=1)
                        if y_pred_proba.ndim > 1
                        else (y_pred_proba > 0.5).astype(int)
                    )
                    # 計算交易指標
                    trade_metrics = self._calculate_trade_metrics(y_test, y_pred)
                    # 合併指標
                    metrics.update(trade_metrics)
                except Exception as e:
                    logger.error(f"計算模型 {model_name} 的交易指標時發生錯誤: {e}")

            return metrics
        except Exception as e:
            logger.error(f"評估模型 {model_name} 時發生錯誤: {e}")
            return {}

    def _prepare_test_data(
        self, model_name: str
    ) -> Optional[Tuple[pd.DataFrame, pd.Series]]:
        """
        準備測試資料

        Args:
            model_name: 模型名稱

        Returns:
            Optional[Tuple[pd.DataFrame, pd.Series]]: 測試資料
        """
        try:
            # 獲取模型資訊
            model_info = self.model_registry.get_model_info(model_name)
            if not model_info:
                logger.error(f"找不到模型 {model_name} 的資訊")
                return None

            # 獲取模型參數
            model_params = model_info.get("params", {})
            target_type = model_params.get("target_type", "direction")
            target_horizon = model_params.get("target_horizon", 5)
            symbols = model_params.get("symbols", ["AAPL", "MSFT", "GOOG"])

            # 載入最新資料
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            self.dataset_loader.load_from_database(
                symbols=symbols, start_date=start_date, end_date=end_date
            )

            # 準備特徵
            features = self.dataset_loader.prepare_features(
                target_type=target_type, target_horizon=target_horizon
            )

            # 分割資料
            from src.models.dataset import TimeSeriesSplit

            splitter = TimeSeriesSplit()
            _, _, test = splitter.split(features)

            # 準備測試資料
            X_test = test.drop(["target", "date", "symbol"], axis=1, errors="ignore")
            y_test = test["target"]

            return X_test, y_test
        except Exception as e:
            logger.error(f"準備模型 {model_name} 的測試資料時發生錯誤: {e}")
            return None

    def _calculate_trade_metrics(
        self, y_true: np.ndarray, y_pred: np.ndarray
    ) -> Dict[str, float]:
        """
        計算交易指標

        Args:
            y_true: 真實標籤
            y_pred: 預測標籤

        Returns:
            Dict[str, float]: 交易指標
        """
        # 模擬交易
        returns = np.zeros(len(y_true))
        for i in range(len(y_true)):
            if y_pred[i] == 1:  # 買入信號
                returns[i] = 0.01 if y_true[i] == 1 else -0.01
            elif y_pred[i] == 0:  # 賣出信號
                returns[i] = 0.01 if y_true[i] == 0 else -0.01

        # 計算交易指標
        trade_metrics = calculate_all_metrics(returns)

        return trade_metrics

    def _needs_retraining(
        self,
        model_name: str,
        current_metrics: Dict[str, float],
        accuracy_threshold: float,
        sharpe_threshold: float,
    ) -> bool:
        """
        判斷模型是否需要重訓練

        Args:
            model_name: 模型名稱
            current_metrics: 當前性能指標
            accuracy_threshold: 準確率下降閾值
            sharpe_threshold: 夏普比率下降閾值

        Returns:
            bool: 是否需要重訓練
        """
        # 如果沒有歷史性能記錄，則不需要重訓練
        if (
            model_name not in self.performance_history
            or not self.performance_history[model_name]
        ):
            return False

        # 獲取上一次的性能指標
        last_metrics = self.performance_history[model_name][-1]["metrics"]

        # 檢查準確率下降
        if "accuracy" in current_metrics and "accuracy" in last_metrics:
            accuracy_drop = last_metrics["accuracy"] - current_metrics["accuracy"]
            if accuracy_drop > accuracy_threshold:
                logger.info(
                    f"模型 {model_name} 的準確率下降了 {accuracy_drop:.4f}，超過閾值 {accuracy_threshold}"
                )
                return True

        # 檢查夏普比率下降
        if "sharpe_ratio" in current_metrics and "sharpe_ratio" in last_metrics:
            sharpe_drop = last_metrics["sharpe_ratio"] - current_metrics["sharpe_ratio"]
            if sharpe_drop > sharpe_threshold:
                logger.info(
                    f"模型 {model_name} 的夏普比率下降了 {sharpe_drop:.4f}，超過閾值 {sharpe_threshold}"
                )
                return True

        return False

    def retrain_models(self, models: List[str]) -> Dict[str, Any]:
        """
        重訓練模型

        Args:
            models: 要重訓練的模型列表

        Returns:
            Dict[str, Any]: 重訓練結果
        """
        results = {}

        for model_name in models:
            try:
                logger.info(f"開始重訓練模型: {model_name}")

                # 獲取模型資訊
                model_info = self.model_registry.get_model_info(model_name)
                if not model_info:
                    logger.error(f"找不到模型 {model_name} 的資訊")
                    results[model_name] = {
                        "status": "failed",
                        "error": "找不到模型資訊",
                    }
                    continue

                # 獲取模型參數
                model_params = model_info.get("params", {})
                model_type = model_info.get("type", "random_forest")

                # 準備訓練資料
                train_data = self._prepare_training_data(model_name)
                if train_data is None:
                    logger.error(f"無法準備模型 {model_name} 的訓練資料")
                    results[model_name] = {
                        "status": "failed",
                        "error": "無法準備訓練資料",
                    }
                    continue

                X_train, y_train, X_val, y_val = train_data

                # 創建模型
                model = create_model(model_type, name=model_name, **model_params)

                # 創建訓練器
                trainer = ModelTrainer(
                    model=model,
                    experiment_name=f"{model_name}_retraining",
                    metrics_threshold={"accuracy": 0.6, "f1": 0.6},
                )

                # 訓練模型
                training_result = trainer.train(
                    X_train=X_train,
                    y_train=y_train,
                    X_val=X_val,
                    y_val=y_val,
                    log_to_mlflow=True,
                )

                # 檢查訓練結果
                if training_result["accepted"]:
                    # 註冊模型
                    version = self.model_registry.register_model(
                        model=model,
                        description=f"重訓練模型 {model_name}",
                        metrics=training_result["val_metrics"]
                        or training_result["train_metrics"],
                        run_id=training_result["run_id"],
                    )

                    # 部署模型
                    self.model_registry.deploy_model(
                        model_name=model_name,
                        version=version,
                        environment="production",
                    )

                    results[model_name] = {
                        "status": "success",
                        "version": version,
                        "metrics": training_result["val_metrics"]
                        or training_result["train_metrics"],
                    }
                    logger.info(f"模型 {model_name} 重訓練成功，新版本: {version}")
                else:
                    results[model_name] = {
                        "status": "failed",
                        "error": "模型未達到接受標準",
                        "metrics": training_result["val_metrics"]
                        or training_result["train_metrics"],
                    }
                    logger.warning(f"模型 {model_name} 重訓練失敗，未達到接受標準")
            except Exception as e:
                logger.error(f"重訓練模型 {model_name} 時發生錯誤: {e}")
                results[model_name] = {"status": "failed", "error": str(e)}

        return results

    def _prepare_training_data(
        self, model_name: str
    ) -> Optional[Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]]:
        """
        準備訓練資料

        Args:
            model_name: 模型名稱

        Returns:
            Optional[Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]]: 訓練資料
        """
        try:
            # 獲取模型資訊
            model_info = self.model_registry.get_model_info(model_name)
            if not model_info:
                logger.error(f"找不到模型 {model_name} 的資訊")
                return None

            # 獲取模型參數
            model_params = model_info.get("params", {})
            target_type = model_params.get("target_type", "direction")
            target_horizon = model_params.get("target_horizon", 5)
            symbols = model_params.get("symbols", ["AAPL", "MSFT", "GOOG"])

            # 載入最新資料
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            self.dataset_loader.load_from_database(
                symbols=symbols, start_date=start_date, end_date=end_date
            )

            # 準備特徵
            features = self.dataset_loader.prepare_features(
                target_type=target_type, target_horizon=target_horizon
            )

            # 分割資料
            from src.models.dataset import TimeSeriesSplit

            splitter = TimeSeriesSplit()
            train, val, _ = splitter.split(features)

            # 準備訓練資料
            X_train = train.drop(["target", "date", "symbol"], axis=1, errors="ignore")
            y_train = train["target"]
            X_val = val.drop(["target", "date", "symbol"], axis=1, errors="ignore")
            y_val = val["target"]

            return X_train, y_train, X_val, y_val
        except Exception as e:
            logger.error(f"準備模型 {model_name} 的訓練資料時發生錯誤: {e}")
            return None


if __name__ == "__main__":
    # 創建模型重訓練器
    retrainer = ModelRetrainer()
    # 檢查模型性能
    models_to_retrain = retrainer.check_model_performance()
    # 重訓練模型
    if models_to_retrain:
        results = retrainer.retrain_models(models_to_retrain)
        print(f"重訓練結果: {results}")
    else:
        print("所有模型性能良好，無需重訓練")
