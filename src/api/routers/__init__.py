# API 路由模組初始化

"""
API 路由模組

此模組包含所有 API 路由的定義和處理器。

主要路由模組：
- auth_handlers: 認證處理器
- system: 系統監控
- data_management: 數據管理
- strategy_management: 策略管理
- portfolio: 投資組合
- backtest: 回測
- ai_models: AI模型
- trading: 交易執行
- risk_management: 風險管理
- monitoring: 監控
- reports: 報告
"""

# 導入認證處理器作為 auth 模組
from . import auth_handlers as auth
from . import system
from . import data_management
from . import strategy_management
from . import portfolio
from . import backtest
from . import ai_models
from . import trading
from . import risk_management
from . import monitoring
from . import reports

__all__ = [
    "auth",
    "system",
    "data_management",
    "strategy_management",
    "portfolio",
    "backtest",
    "ai_models",
    "trading",
    "risk_management",
    "monitoring",
    "reports"
]
