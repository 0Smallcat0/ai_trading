"""
整合模組

此模組提供與外部系統和服務的整合功能，包括：
- API服務
- 自動化工作流
- 模型上下文協議(MCP)整合
"""

from .api import api_router, create_app
from .workflows import workflow_manager
from .mcp import mcp_client

__all__ = [
    'api_router',
    'create_app',
    'workflow_manager',
    'mcp_client',
]
