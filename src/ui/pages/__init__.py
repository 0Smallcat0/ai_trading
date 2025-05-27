"""
頁面模組

此模組包含所有 Web UI 的頁面實現。
"""

from .data_management import show as data_management_show
from .feature_engineering import show as feature_engineering_show
from .strategy_management import show as strategy_management_show
from .ai_models import show as ai_models_show
from .backtest import show as backtest_show
from .portfolio_management import show as portfolio_management_show
from .risk_management import show as risk_management_show
from .trade_execution import show as trade_execution_show
from .system_monitoring import show as system_monitoring_show
from .reports import show as reports_show

__all__ = [
    "data_management_show",
    "feature_engineering_show",
    "strategy_management_show",
    "ai_models_show",
    "backtest_show",
    "portfolio_management_show",
    "risk_management_show",
    "trade_execution_show",
    "system_monitoring_show",
    "reports_show",
]
