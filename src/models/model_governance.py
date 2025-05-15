# -*- coding: utf-8 -*-
"""
模型治理模組

此模組提供模型治理功能，包括：
- 模型版本管理
- 模型部署和回滾
- 模型監控
- 模型文檔
"""

import os
import json
import logging
import shutil
import datetime
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
import mlflow
import mlflow.sklearn
import mlflow.tensorflow
import mlflow.xgboost
import mlflow.lightgbm

from src.config import LOG_LEVEL, MODELS_DIR
from src.models.model_base import ModelBase
from src.models.model_factory import create_model

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class ModelRegistry:
    """
    模型註冊表

    管理模型版本和部署狀態。
    """

    def __init__(self, registry_path: Optional[str] = None):
        """
        初始化模型註冊表

        Args:
            registry_path (Optional[str]): 註冊表路徑
        """
        self.registry_path = registry_path or os.path.join(MODELS_DIR, "registry.json")
        self.registry = self._load_registry()

    def _load_registry(self) -> Dict[str, Any]:
        """
        載入註冊表

        Returns:
            Dict[str, Any]: 註冊表
        """
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"載入註冊表時發生錯誤: {e}")
                return self._create_empty_registry()
        else:
            return self._create_empty_registry()

    def _create_empty_registry(self) -> Dict[str, Any]:
        """
        創建空註冊表

        Returns:
            Dict[str, Any]: 空註冊表
        """
        return {
            "models": {},
            "deployments": {},
            "last_updated": datetime.datetime.now().isoformat()
        }

    def _save_registry(self) -> None:
        """
        保存註冊表
        """
        try:
            with open(self.registry_path, "w") as f:
                json.dump(self.registry, f, indent=4)
        except Exception as e:
            logger.error(f"保存註冊表時發生錯誤: {e}")

    def register_model(
        self,
        model: ModelBase,
        version: Optional[str] = None,
        description: Optional[str] = None,
        metrics: Optional[Dict[str, float]] = None,
        run_id: Optional[str] = None
    ) -> str:
        """
        註冊模型

        Args:
            model (ModelBase): 模型
            version (Optional[str]): 版本，如果為 None，則使用時間戳
            description (Optional[str]): 描述
            metrics (Optional[Dict[str, float]]): 指標
            run_id (Optional[str]): MLflow 運行 ID

        Returns:
            str: 模型版本
        """
        if not model.trained:
            logger.error("模型尚未訓練，無法註冊")
            raise ValueError("模型尚未訓練，無法註冊")
        
        # 生成版本
        if version is None:
            version = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        
        # 獲取模型資訊
        model_info = {
            "name": model.name,
            "version": version,
            "description": description or "",
            "model_type": model.__class__.__name__,
            "model_params": model.model_params,
            "feature_names": model.feature_names,
            "target_name": model.target_name,
            "metrics": metrics or model.metrics,
            "created_at": datetime.datetime.now().isoformat(),
            "run_id": run_id,
            "path": os.path.join(MODELS_DIR, model.name, version)
        }
        
        # 更新註冊表
        if model.name not in self.registry["models"]:
            self.registry["models"][model.name] = {}
        
        self.registry["models"][model.name][version] = model_info
        self.registry["last_updated"] = datetime.datetime.now().isoformat()
        
        # 保存註冊表
        self._save_registry()
        
        # 保存模型
        model_path = model.save(os.path.join(MODELS_DIR, model.name, version, f"{model.name}.joblib"))
        
        logger.info(f"模型已註冊: {model.name} v{version}")
        
        return version

    def get_model_info(self, model_name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """
        獲取模型資訊

        Args:
            model_name (str): 模型名稱
            version (Optional[str]): 版本，如果為 None，則獲取最新版本

        Returns:
            Dict[str, Any]: 模型資訊
        """
        if model_name not in self.registry["models"]:
            logger.error(f"模型不存在: {model_name}")
            raise ValueError(f"模型不存在: {model_name}")
        
        if version is None:
            # 獲取最新版本
            versions = list(self.registry["models"][model_name].keys())
            if not versions:
                logger.error(f"模型沒有版本: {model_name}")
                raise ValueError(f"模型沒有版本: {model_name}")
            
            version = sorted(versions)[-1]
        
        if version not in self.registry["models"][model_name]:
            logger.error(f"版本不存在: {model_name} v{version}")
            raise ValueError(f"版本不存在: {model_name} v{version}")
        
        return self.registry["models"][model_name][version]

    def list_models(self) -> List[str]:
        """
        列出所有模型

        Returns:
            List[str]: 模型名稱列表
        """
        return list(self.registry["models"].keys())

    def list_versions(self, model_name: str) -> List[str]:
        """
        列出模型的所有版本

        Args:
            model_name (str): 模型名稱

        Returns:
            List[str]: 版本列表
        """
        if model_name not in self.registry["models"]:
            logger.error(f"模型不存在: {model_name}")
            raise ValueError(f"模型不存在: {model_name}")
        
        return list(self.registry["models"][model_name].keys())

    def load_model(self, model_name: str, version: Optional[str] = None) -> ModelBase:
        """
        載入模型

        Args:
            model_name (str): 模型名稱
            version (Optional[str]): 版本，如果為 None，則載入最新版本

        Returns:
            ModelBase: 模型
        """
        # 獲取模型資訊
        model_info = self.get_model_info(model_name, version)
        
        # 創建模型
        model = create_model(
            model_info["model_type"].lower().replace("model", ""),
            name=model_info["name"],
            **model_info["model_params"]
        )
        
        # 載入模型
        model_path = os.path.join(model_info["path"], f"{model_name}.joblib")
        model.load(model_path)
        
        # 設定特徵名稱和目標名稱
        model.feature_names = model_info["feature_names"]
        model.target_name = model_info["target_name"]
        
        return model

    def deploy_model(
        self,
        model_name: str,
        version: Optional[str] = None,
        environment: str = "production",
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        部署模型

        Args:
            model_name (str): 模型名稱
            version (Optional[str]): 版本，如果為 None，則部署最新版本
            environment (str): 環境，例如 "production", "staging"
            description (Optional[str]): 描述

        Returns:
            Dict[str, Any]: 部署資訊
        """
        # 獲取模型資訊
        model_info = self.get_model_info(model_name, version)
        version = model_info["version"]
        
        # 創建部署資訊
        deployment_id = f"{model_name}-{environment}-{version}"
        deployment_info = {
            "id": deployment_id,
            "model_name": model_name,
            "version": version,
            "environment": environment,
            "description": description or "",
            "deployed_at": datetime.datetime.now().isoformat(),
            "status": "active",
            "model_info": model_info
        }
        
        # 更新註冊表
        self.registry["deployments"][deployment_id] = deployment_info
        self.registry["last_updated"] = datetime.datetime.now().isoformat()
        
        # 保存註冊表
        self._save_registry()
        
        logger.info(f"模型已部署: {model_name} v{version} 到 {environment}")
        
        return deployment_info

    def rollback_model(
        self,
        model_name: str,
        environment: str = "production",
        to_version: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        回滾模型

        Args:
            model_name (str): 模型名稱
            environment (str): 環境，例如 "production", "staging"
            to_version (Optional[str]): 回滾到的版本，如果為 None，則回滾到上一個版本
            description (Optional[str]): 描述

        Returns:
            Dict[str, Any]: 部署資訊
        """
        # 獲取當前部署
        current_deployment = None
        for deployment_id, deployment in self.registry["deployments"].items():
            if deployment["model_name"] == model_name and deployment["environment"] == environment and deployment["status"] == "active":
                current_deployment = deployment
                break
        
        if current_deployment is None:
            logger.error(f"沒有找到活動部署: {model_name} 在 {environment}")
            raise ValueError(f"沒有找到活動部署: {model_name} 在 {environment}")
        
        # 確定回滾版本
        if to_version is None:
            # 獲取所有版本
            versions = self.list_versions(model_name)
            
            # 找到當前版本的索引
            try:
                current_index = versions.index(current_deployment["version"])
            except ValueError:
                logger.error(f"當前版本不在版本列表中: {current_deployment['version']}")
                raise ValueError(f"當前版本不在版本列表中: {current_deployment['version']}")
            
            # 如果當前版本是最舊的版本，則無法回滾
            if current_index == 0:
                logger.error(f"當前版本是最舊的版本，無法回滾: {current_deployment['version']}")
                raise ValueError(f"當前版本是最舊的版本，無法回滾: {current_deployment['version']}")
            
            # 回滾到上一個版本
            to_version = versions[current_index - 1]
        
        # 將當前部署標記為非活動
        current_deployment["status"] = "inactive"
        current_deployment["deactivated_at"] = datetime.datetime.now().isoformat()
        
        # 部署新版本
        return self.deploy_model(model_name, to_version, environment, description or f"回滾自 {current_deployment['version']}")

    def get_deployment_info(self, model_name: str, environment: str = "production") -> Dict[str, Any]:
        """
        獲取部署資訊

        Args:
            model_name (str): 模型名稱
            environment (str): 環境，例如 "production", "staging"

        Returns:
            Dict[str, Any]: 部署資訊
        """
        for deployment_id, deployment in self.registry["deployments"].items():
            if deployment["model_name"] == model_name and deployment["environment"] == environment and deployment["status"] == "active":
                return deployment
        
        logger.error(f"沒有找到活動部署: {model_name} 在 {environment}")
        raise ValueError(f"沒有找到活動部署: {model_name} 在 {environment}")

    def list_deployments(self, environment: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有部署

        Args:
            environment (Optional[str]): 環境，如果為 None，則列出所有環境

        Returns:
            List[Dict[str, Any]]: 部署資訊列表
        """
        deployments = []
        
        for deployment_id, deployment in self.registry["deployments"].items():
            if environment is None or deployment["environment"] == environment:
                deployments.append(deployment)
        
        return deployments


class ModelMonitor:
    """
    模型監控器

    監控模型性能和漂移。
    """

    def __init__(
        self,
        model_name: str,
        version: Optional[str] = None,
        registry: Optional[ModelRegistry] = None
    ):
        """
        初始化模型監控器

        Args:
            model_name (str): 模型名稱
            version (Optional[str]): 版本，如果為 None，則使用最新版本
            registry (Optional[ModelRegistry]): 模型註冊表
        """
        self.model_name = model_name
        self.registry = registry or ModelRegistry()
        
        # 獲取模型資訊
        self.model_info = self.registry.get_model_info(model_name, version)
        self.version = self.model_info["version"]
        
        # 載入模型
        self.model = self.registry.load_model(model_name, self.version)
        
        # 監控資料
        self.monitoring_data = []

    def log_prediction(
        self,
        features: pd.DataFrame,
        prediction: Union[float, int, np.ndarray],
        actual: Optional[Union[float, int, np.ndarray]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        記錄預測

        Args:
            features (pd.DataFrame): 特徵
            prediction (Union[float, int, np.ndarray]): 預測值
            actual (Optional[Union[float, int, np.ndarray]]): 實際值
            metadata (Optional[Dict[str, Any]]): 元數據
        """
        # 創建記錄
        record = {
            "timestamp": datetime.datetime.now().isoformat(),
            "model_name": self.model_name,
            "version": self.version,
            "features": features.to_dict(orient="records")[0] if len(features) == 1 else features.to_dict(orient="records"),
            "prediction": prediction.tolist() if isinstance(prediction, np.ndarray) else prediction,
            "actual": actual.tolist() if isinstance(actual, np.ndarray) else actual,
            "metadata": metadata or {}
        }
        
        # 添加到監控資料
        self.monitoring_data.append(record)
        
        # 記錄到 MLflow
        if self.model_info.get("run_id"):
            with mlflow.start_run(run_id=self.model_info["run_id"]):
                mlflow.log_metric("prediction_count", len(self.monitoring_data))
                
                if actual is not None:
                    # 計算誤差
                    if isinstance(prediction, np.ndarray) and isinstance(actual, np.ndarray):
                        error = np.mean(np.abs(prediction - actual))
                    else:
                        error = abs(prediction - actual)
                    
                    mlflow.log_metric("prediction_error", error)

    def calculate_metrics(self) -> Dict[str, float]:
        """
        計算監控指標

        Returns:
            Dict[str, float]: 監控指標
        """
        if not self.monitoring_data:
            logger.warning("沒有監控資料")
            return {}
        
        # 提取預測值和實際值
        predictions = []
        actuals = []
        
        for record in self.monitoring_data:
            if record["actual"] is not None:
                predictions.append(record["prediction"])
                actuals.append(record["actual"])
        
        if not predictions:
            logger.warning("沒有包含實際值的監控資料")
            return {}
        
        # 計算指標
        metrics = {}
        
        # 判斷是分類還是回歸問題
        if hasattr(self.model, "is_classifier") and self.model.is_classifier:
            # 分類指標
            metrics["accuracy"] = accuracy_score(actuals, predictions)
            metrics["precision"] = precision_score(actuals, predictions, average="weighted")
            metrics["recall"] = recall_score(actuals, predictions, average="weighted")
            metrics["f1"] = f1_score(actuals, predictions, average="weighted")
        else:
            # 回歸指標
            metrics["mse"] = np.mean((np.array(actuals) - np.array(predictions)) ** 2)
            metrics["rmse"] = np.sqrt(metrics["mse"])
            metrics["mae"] = np.mean(np.abs(np.array(actuals) - np.array(predictions)))
            
            # 計算 R^2
            y_mean = np.mean(actuals)
            ss_total = np.sum((np.array(actuals) - y_mean) ** 2)
            ss_residual = np.sum((np.array(actuals) - np.array(predictions)) ** 2)
            metrics["r2"] = 1 - (ss_residual / ss_total) if ss_total != 0 else 0
        
        return metrics
