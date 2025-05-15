"""
模型上下文協議(MCP)整合模組

此模組提供與模型上下文協議(Model Context Protocol)的整合功能，
用於標準化模型介面和數據交換。
"""

from .client import MCPClient

# 創建全局MCP客戶端實例
mcp_client = MCPClient()

__all__ = ["mcp_client", "MCPClient"]
