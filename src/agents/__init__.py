# -*- coding: utf-8 -*-
"""
多代理AI交易系統模組

此模組提供完整的多代理交易系統功能，包括：

基礎組件：
- TradingAgent: 交易代理基類
- AgentManager: 多代理管理器
- AgentCommunication: 代理間通信
- PerformanceEvaluator: 績效評估器

投資風格代理：
- ValueInvestor: 價值投資代理
- TechnicalTrader: 技術分析代理
- MomentumTrader: 動量交易代理
- ArbitrageTrader: 套利交易代理
- RiskParityAgent: 風險平價代理

角色扮演代理：
- BuffettAgent: 巴菲特代理
- SorosAgent: 索羅斯代理
- SimonsAgent: 西蒙斯代理
- DalioAgent: 達里奧代理
- GrahamAgent: 格雷厄姆代理

主要功能：
- 多代理協作和競爭
- 動態權重調整
- 投資組合分配
- 風險控制和管理
- 績效評估和排名
"""

# 基礎組件
from .base import (
    TradingAgent,
    AgentError,
    AgentConfigError,
    AgentCommunicationError,
    InvestmentStyle,
    RiskPreference,
    AgentDecision,
    AgentMessage,
)

# 管理組件
from .manager import AgentManager, AgentManagerError
from .communication import AgentCommunication, CommunicationError, MessageQueue
from .performance_evaluator import (
    PerformanceEvaluator,
    PerformanceReport,
    PerformanceMetric,
)
# 待實現的組件
# from .coordinator import DecisionCoordinator
# from .portfolio_allocator import PortfolioAllocator

# 投資風格代理
from .styles import (
    ValueInvestor,
    TechnicalTrader,
    MomentumTrader,
    ArbitrageTrader,
    RiskParityAgent,
)

# 角色扮演代理（將在Phase 3實現）
# from .personas import (
#     BuffettAgent,
#     SorosAgent,
#     SimonsAgent,
#     DalioAgent,
#     GrahamAgent,
# )

__all__ = [
    # 基礎組件
    "TradingAgent",
    "AgentError",
    "AgentConfigError", 
    "AgentCommunicationError",
    "InvestmentStyle",
    "RiskPreference",
    "AgentDecision",
    "AgentMessage",
    # 管理組件
    "AgentManager",
    "AgentManagerError",
    "AgentCommunication",
    "CommunicationError",
    "MessageQueue",
    "PerformanceEvaluator",
    "PerformanceReport",
    "PerformanceMetric",
    # 待實現的組件
    # "DecisionCoordinator",
    # "PortfolioAllocator",
    # 投資風格代理
    "ValueInvestor",
    "TechnicalTrader",
    "MomentumTrader",
    "ArbitrageTrader",
    "RiskParityAgent",
    # 角色扮演代理（待實現）
    # "BuffettAgent",
    # "SorosAgent",
    # "SimonsAgent",
    # "DalioAgent",
    # "GrahamAgent",
]

# 版本信息
__version__ = "1.0.0"
__author__ = "AI Trading System Team"
__description__ = "多代理AI交易系統 - 智能化投資決策平台"
