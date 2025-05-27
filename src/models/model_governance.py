# -*- coding: utf-8 -*-
"""
模型治理模組 (向後兼容)

此模組提供模型治理功能的向後兼容介面。
新的模組化實現位於 model_governance 子模組中。

Classes:
    ModelRegistry: 模型註冊表（向後兼容）
    ModelMonitor: 模型監控器（向後兼容）

Functions:
    create_model_registry: 創建模型註冊表
    create_model_monitor: 創建模型監控器

Example:
    >>> from src.models.model_governance import ModelRegistry, ModelMonitor
    >>> registry = ModelRegistry()
    >>> version = registry.register_model(trained_model, description="Production model")
    >>> monitor = ModelMonitor("my_model", version, registry)

Note:
    建議使用新的模組化介面：
    from src.models.model_governance import ModelRegistry, ModelMonitor
"""

import warnings
from typing import Any, Dict, List, Optional, Union

import pandas as pd

# 導入新的模組化實現
from .model_governance.legacy_interface import (
    ModelRegistry,
    ModelMonitor
)
from .model_governance import (
    create_model_registry,
    create_model_monitor,
    register_model,
    deploy_model
)
from .model_governance.registry import ModelRegistry as NewModelRegistry
from .model_governance.monitor import ModelMonitor as NewModelMonitor
from .model_governance.deployment import DeploymentManager
from .model_governance.lifecycle import ModelLifecycleManager


# 向後兼容的導出
__all__ = [
    # Legacy classes
    "ModelRegistry",
    "ModelMonitor",

    # New modular classes
    "NewModelRegistry",
    "NewModelMonitor",
    "DeploymentManager",
    "ModelLifecycleManager",

    # Convenience functions
    "create_model_registry",
    "create_model_monitor",
    "register_model",
    "deploy_model"
]
