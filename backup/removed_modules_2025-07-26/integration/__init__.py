# -*- coding: utf-8 -*-
"""
系統整合模組

此模組提供統一的整合層，將所有增強功能與原始項目進行深度整合。
通過適配器模式和接口封裝，確保新功能能夠無縫整合到原始項目中，
同時保持原始項目的完整性和向後兼容性。

主要功能：
- 統一的整合接口
- 適配器模式實現
- 功能路由和協調
- 配置管理和初始化
- 錯誤處理和日誌

整合組件：
- 多代理交易系統整合
- 大模型交易策略整合
- 強化學習框架整合
- 知識庫與學習系統整合
- 數據源擴展整合

設計原則：
- 保持原始項目完全不變
- 通過適配器模式實現整合
- 確保向後兼容性
- 提供統一的API接口
"""

# 版本信息
__version__ = "1.0.0"
__author__ = "Integration Team"
__description__ = "AI量化交易系統整合層"

# 保持原有的整合功能
from .api import api_router, create_app
from .mcp import mcp_client
from .workflows import workflow_manager

# 新增的系統整合組件
try:
    from .core_integration import SystemIntegrator
    from .legacy_adapter import LegacyProjectAdapter
    from .config_manager import IntegrationConfigManager
    CORE_INTEGRATION_AVAILABLE = True
except ImportError:
    CORE_INTEGRATION_AVAILABLE = False

# 功能整合適配器
try:
    from .agents_integration import MultiAgentSystemAdapter
    from .llm_integration import LLMStrategyAdapter
    from .rl_integration import ReinforcementLearningAdapter
    from .knowledge_integration import KnowledgeSystemAdapter
    from .data_integration import DataSourceAdapter
    FEATURE_ADAPTERS_AVAILABLE = True
except ImportError:
    FEATURE_ADAPTERS_AVAILABLE = False

__all__ = [
    # 原有組件
    "api_router",
    "create_app",
    "workflow_manager",
    "mcp_client",
]

# 添加新組件到導出列表
if CORE_INTEGRATION_AVAILABLE:
    __all__.extend([
        'SystemIntegrator',
        'LegacyProjectAdapter',
        'IntegrationConfigManager'
    ])

if FEATURE_ADAPTERS_AVAILABLE:
    __all__.extend([
        'MultiAgentSystemAdapter',
        'LLMStrategyAdapter',
        'ReinforcementLearningAdapter',
        'KnowledgeSystemAdapter',
        'DataSourceAdapter'
    ])

# 整合狀態常量
INTEGRATION_STATUS = {
    'CORE_INTEGRATION': CORE_INTEGRATION_AVAILABLE,
    'FEATURE_ADAPTERS': FEATURE_ADAPTERS_AVAILABLE,
    'MULTI_AGENT': FEATURE_ADAPTERS_AVAILABLE,
    'LLM_STRATEGY': FEATURE_ADAPTERS_AVAILABLE,
    'REINFORCEMENT_LEARNING': FEATURE_ADAPTERS_AVAILABLE,
    'KNOWLEDGE_SYSTEM': FEATURE_ADAPTERS_AVAILABLE,
    'DATA_SOURCES': FEATURE_ADAPTERS_AVAILABLE
}

# 兼容性版本
LEGACY_PROJECT_VERSION = "0.0.1"
INTEGRATION_VERSION = "1.0.0"
