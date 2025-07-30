# -*- coding: utf-8 -*-
"""
模型治理模組

此模組提供完整的模型治理功能，包括：
- 模型註冊與版本管理
- 模型部署與回滾
- 模型監控與效能追蹤
- 模型生命週期管理

Classes:
    ModelRegistry: 模型註冊表，管理模型版本和部署狀態
    ModelMonitor: 模型監控器，追蹤模型效能和漂移
    ModelLifecycleManager: 模型生命週期管理器
    DeploymentManager: 部署管理器

Functions:
    create_model_registry: 創建模型註冊表
    create_model_monitor: 創建模型監控器
    register_model: 註冊模型（便利函數）
    deploy_model: 部署模型（便利函數）

Example:
    >>> from src.models.model_governance import ModelRegistry, ModelMonitor
    >>> registry = ModelRegistry()
    >>> version = registry.register_model(trained_model, description="Production model v1")
    >>> deployment = registry.deploy_model("my_model", version, "production")
    >>>
    >>> monitor = ModelMonitor("my_model", version, registry)
    >>> monitor.log_prediction(features, prediction, actual_value)

Note:
    模型治理遵循 MLOps 最佳實踐
    支援多環境部署和 A/B 測試
    整合 MLflow 進行實驗追蹤
"""

from .deployment import DeploymentManager

# 向後兼容的導入
from .legacy_interface import ModelMonitor as LegacyModelMonitor
from .legacy_interface import ModelRegistry as LegacyModelRegistry
from .lifecycle import ModelLifecycleManager
from .monitor import ModelMonitor
from .registry import ModelRegistry
from .utils import (
    calculate_model_drift,
    create_model_signature,
    generate_governance_report,
    validate_model_metadata,
)

__all__ = [
    # Core classes
    "ModelRegistry",
    "ModelMonitor",
    "DeploymentManager",
    "ModelLifecycleManager",
    # Utility functions
    "validate_model_metadata",
    "create_model_signature",
    "calculate_model_drift",
    "generate_governance_report",
    # Legacy compatibility
    "LegacyModelRegistry",
    "LegacyModelMonitor",
]

# 版本資訊
__version__ = "1.0.0"
__author__ = "AI Trading System Team"


def create_model_registry(registry_path: str = None) -> ModelRegistry:
    """
    創建模型註冊表

    Args:
        registry_path: 註冊表檔案路徑

    Returns:
        ModelRegistry 實例

    Example:
        >>> registry = create_model_registry("./models/registry.json")
    """
    return ModelRegistry(registry_path)


def create_model_monitor(
    model_name: str, version: str = None, registry: ModelRegistry = None
) -> ModelMonitor:
    """
    創建模型監控器

    Args:
        model_name: 模型名稱
        version: 模型版本
        registry: 模型註冊表

    Returns:
        ModelMonitor 實例

    Example:
        >>> monitor = create_model_monitor("my_model", "v1.0")
    """
    return ModelMonitor(model_name, version, registry)


def register_model(
    model,
    name: str = None,
    version: str = None,
    description: str = None,
    registry: ModelRegistry = None,
    **kwargs
) -> str:
    """
    註冊模型（便利函數）

    Args:
        model: 要註冊的模型
        name: 模型名稱
        version: 版本號
        description: 描述
        registry: 註冊表實例
        **kwargs: 其他參數

    Returns:
        模型版本號

    Example:
        >>> version = register_model(trained_model, "my_model", description="Production model")
    """
    if registry is None:
        registry = ModelRegistry()

    if name is not None:
        model.name = name

    return registry.register_model(
        model=model, version=version, description=description, **kwargs
    )


def deploy_model(
    model_name: str,
    version: str = None,
    environment: str = "production",
    description: str = None,
    registry: ModelRegistry = None,
) -> dict:
    """
    部署模型（便利函數）

    Args:
        model_name: 模型名稱
        version: 版本號
        environment: 部署環境
        description: 部署描述
        registry: 註冊表實例

    Returns:
        部署資訊字典

    Example:
        >>> deployment = deploy_model("my_model", "v1.0", "production")
    """
    if registry is None:
        registry = ModelRegistry()

    return registry.deploy_model(
        model_name=model_name,
        version=version,
        environment=environment,
        description=description,
    )
