"""
工作流模組

此模組提供自動化工作流功能，包括n8n工作流設計和管理。
"""

from .manager import WorkflowManager, workflow_manager
from .templates import (
    get_market_data_workflow,
    strategy_execution_workflow,
    portfolio_rebalance_workflow,
    risk_monitoring_workflow,
    reporting_workflow
)

__all__ = [
    'WorkflowManager',
    'workflow_manager',
    'get_market_data_workflow',
    'strategy_execution_workflow',
    'portfolio_rebalance_workflow',
    'risk_monitoring_workflow',
    'reporting_workflow'
]
