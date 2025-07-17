"""投資組合基礎模組

此模組提供投資組合管理的基礎功能和向後相容性支援。
為了保持 API 的向後相容性，此模組重新導出核心類別和異常。

主要功能：
- 重新導出核心類別和異常
- 提供向後相容性支援
- 統一的導入介面
"""

# 重新導出核心類別和異常以保持向後相容性
from .core import Portfolio
from .exceptions import (
    PortfolioOptimizationError,
    DependencyError,
    ValidationError,
    InsufficientFundsError,
    InvalidWeightsError,
    OptimizationConvergenceError,
    RiskConstraintViolationError,
    DataQualityError,
)


# 所有功能已移動到 core.py 和 exceptions.py
# 此檔案僅用於向後相容性

__all__ = [
    "Portfolio",
    "PortfolioOptimizationError",
    "DependencyError",
    "ValidationError",
    "InsufficientFundsError",
    "InvalidWeightsError",
    "OptimizationConvergenceError",
    "RiskConstraintViolationError",
    "DataQualityError",
]





