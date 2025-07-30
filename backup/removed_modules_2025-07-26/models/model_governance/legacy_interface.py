# -*- coding: utf-8 -*-
"""
模型治理向後兼容介面

此模組提供與原始 model_governance.py 相容的介面，
確保現有代碼可以無縫遷移到新的模組化實現。

Classes:
    ModelRegistry: 向後兼容的模型註冊表
    ModelMonitor: 向後兼容的模型監控器
"""

import logging
import warnings
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from src.config import LOG_LEVEL
from src.models.model_base import ModelBase
from .registry import ModelRegistry as NewModelRegistry
from .monitor import ModelMonitor as NewModelMonitor
from .deployment import DeploymentManager
from .lifecycle import ModelLifecycleManager

# 設定日誌
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, LOG_LEVEL))


class ModelRegistry:
    """
    模型註冊表 (向後兼容)

    此類別提供與原始 ModelRegistry 相同的介面，
    內部委託給新的模組化實現。

    Example:
        >>> registry = ModelRegistry()
        >>> version = registry.register_model(trained_model, description="Production model")
        >>> model = registry.load_model("my_model", version)
    """

    def __init__(self, registry_path: Optional[str] = None):
        """
        初始化模型註冊表 (向後兼容)

        Args:
            registry_path: 註冊表路徑
        """
        # 發出遷移警告
        warnings.warn(
            "使用舊版 ModelRegistry 介面。建議遷移到新的模組化介面。",
            DeprecationWarning,
            stacklevel=2,
        )

        # 委託給新實現
        self._new_registry = NewModelRegistry(registry_path)
        self._deployment_manager = DeploymentManager(self._new_registry)
        self._lifecycle_manager = ModelLifecycleManager(self._new_registry)

    def register_model(
        self,
        model: ModelBase,
        version: Optional[str] = None,
        description: Optional[str] = None,
        metrics: Optional[Dict[str, float]] = None,
        run_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> str:
        """
        註冊模型 (向後兼容)

        Args:
            model: 要註冊的模型實例
            version: 版本號
            description: 模型描述
            metrics: 模型指標
            run_id: MLflow 運行 ID
            tags: 模型標籤
            **kwargs: 其他元數據

        Returns:
            模型版本號
        """
        return self._new_registry.register_model(
            model=model,
            version=version,
            description=description,
            metrics=metrics,
            run_id=run_id,
            tags=tags,
            **kwargs
        )

    def load_model(self, model_name: str, version: Optional[str] = None) -> ModelBase:
        """
        載入模型 (向後兼容)

        Args:
            model_name: 模型名稱
            version: 版本號

        Returns:
            載入的模型實例
        """
        return self._new_registry.load_model(model_name, version)

    def get_model_info(
        self, model_name: str, version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        獲取模型資訊 (向後兼容)

        Args:
            model_name: 模型名稱
            version: 版本號

        Returns:
            模型資訊字典
        """
        return self._new_registry.get_model_info(model_name, version)

    def list_models(self) -> List[str]:
        """
        列出所有模型名稱 (向後兼容)

        Returns:
            模型名稱列表
        """
        return self._new_registry.list_models()

    def list_versions(self, model_name: str) -> List[str]:
        """
        列出模型的所有版本 (向後兼容)

        Args:
            model_name: 模型名稱

        Returns:
            版本號列表
        """
        return self._new_registry.list_versions(model_name)

    def deploy_model(
        self,
        model_name: str,
        version: str,
        environment: str = "production",
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        部署模型 (向後兼容)

        Args:
            model_name: 模型名稱
            version: 版本號
            environment: 部署環境
            description: 部署描述

        Returns:
            部署資訊字典
        """
        return self._deployment_manager.deploy_model(
            model_name=model_name,
            version=version,
            environment=environment,
            description=description,
        )

    def get_deployment_info(
        self, model_name: str, environment: str
    ) -> Optional[Dict[str, Any]]:
        """
        獲取部署資訊 (向後兼容)

        Args:
            model_name: 模型名稱
            environment: 環境名稱

        Returns:
            部署資訊字典
        """
        return self._deployment_manager.get_deployment_info(model_name, environment)

    def rollback_deployment(
        self, model_name: str, environment: str, description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        回滾部署 (向後兼容)

        Args:
            model_name: 模型名稱
            environment: 環境名稱
            description: 回滾描述

        Returns:
            回滾後的部署資訊
        """
        return self._deployment_manager.rollback_deployment(
            model_name, environment, description
        )

    # 提供對新功能的訪問
    @property
    def deployment_manager(self) -> DeploymentManager:
        """獲取部署管理器"""
        return self._deployment_manager

    @property
    def lifecycle_manager(self) -> ModelLifecycleManager:
        """獲取生命週期管理器"""
        return self._lifecycle_manager


class ModelMonitor:
    """
    模型監控器 (向後兼容)

    此類別提供與原始 ModelMonitor 相同的介面，
    內部委託給新的模組化實現。

    Example:
        >>> monitor = ModelMonitor("my_model", "v1.0")
        >>> monitor.log_prediction(features, prediction, actual_value)
        >>> metrics = monitor.calculate_metrics()
    """

    def __init__(
        self,
        model_name: str,
        version: Optional[str] = None,
        registry: Optional[ModelRegistry] = None,
        max_records: int = 10000,
    ):
        """
        初始化模型監控器 (向後兼容)

        Args:
            model_name: 模型名稱
            version: 模型版本
            registry: 模型註冊表實例
            max_records: 最大監控記錄數量
        """
        # 發出遷移警告
        warnings.warn(
            "使用舊版 ModelMonitor 介面。建議遷移到新的模組化介面。",
            DeprecationWarning,
            stacklevel=2,
        )

        # 處理註冊表參數
        if registry is not None:
            new_registry = registry._new_registry
        else:
            new_registry = NewModelRegistry()

        # 委託給新實現
        self._new_monitor = NewModelMonitor(
            model_name=model_name,
            version=version,
            registry=new_registry,
            max_records=max_records,
        )

    def log_prediction(
        self,
        features: Union[pd.DataFrame, pd.Series],
        prediction: Union[float, int, List],
        actual: Optional[Union[float, int, List]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        log_to_mlflow: bool = True,
    ) -> None:
        """
        記錄預測結果 (向後兼容)

        Args:
            features: 輸入特徵
            prediction: 預測值
            actual: 實際值
            metadata: 額外的元數據
            log_to_mlflow: 是否記錄到 MLflow
        """
        self._new_monitor.log_prediction(
            features=features,
            prediction=prediction,
            actual=actual,
            metadata=metadata,
            log_to_mlflow=log_to_mlflow,
        )

    def calculate_metrics(self) -> Dict[str, float]:
        """
        計算監控指標 (向後兼容)

        Returns:
            監控指標字典
        """
        return self._new_monitor.calculate_metrics()

    def detect_drift(
        self,
        new_features: pd.DataFrame,
        method: str = "ks_test",
        threshold: float = 0.05,
    ) -> Dict[str, Any]:
        """
        檢測資料漂移 (向後兼容)

        Args:
            new_features: 新的特徵資料
            method: 漂移檢測方法
            threshold: 漂移閾值

        Returns:
            漂移檢測結果
        """
        return self._new_monitor.detect_drift(
            new_features=new_features, method=method, threshold=threshold
        )

    def set_baseline(self, baseline_features: pd.DataFrame) -> None:
        """
        設定基準特徵資料 (向後兼容)

        Args:
            baseline_features: 基準特徵資料
        """
        self._new_monitor.set_baseline(baseline_features)

    def get_monitoring_summary(self) -> Dict[str, Any]:
        """
        獲取監控摘要 (向後兼容)

        Returns:
            監控摘要字典
        """
        return self._new_monitor.get_monitoring_summary()

    # 提供對新功能的訪問
    @property
    def model_name(self) -> str:
        """模型名稱"""
        return self._new_monitor.model_name

    @property
    def version(self) -> str:
        """模型版本"""
        return self._new_monitor.version

    @property
    def monitoring_data(self) -> List[Dict[str, Any]]:
        """監控資料"""
        return self._new_monitor.monitoring_data
