# -*- coding: utf-8 -*-
"""
多代理協作機制模組

此模組提供多代理AI交易系統的協作機制，包括：

核心組件：
- DecisionCoordinator: 決策協調器 - 整合多代理決策
- DynamicWeightAdjuster: 動態權重調整器 - 基於績效優化權重
- PortfolioAllocator: 投資組合分配器 - 多層次資產配置
- AgentCommunication: 代理間通信 - 高效異步通信

協作機制特色：
- 決策聚合算法（投票機制、加權平均、衝突解決）
- 績效追蹤和權重動態調整
- 多層次投資組合配置策略
- 異步消息和事件驅動通信
- 實時協作和決策同步

主要功能：
- 多代理決策整合和協調
- 基於績效的動態權重調整
- 風險分散的投資組合配置
- 高效的代理間通信機制
- 衝突檢測和解決
- 協作績效監控和優化
"""

# 協作機制組件
from .decision_coordinator import DecisionCoordinator, CoordinatedDecision, CoordinationMethod, ConflictResolution
from .dynamic_weight_adjuster import DynamicWeightAdjuster, WeightAdjustmentMethod, PerformanceRecord, WeightAdjustment
from .portfolio_allocator import PortfolioAllocator, AllocationMethod, AssetAllocation, PortfolioAllocation
from .agent_communication import AgentCommunication, Message, MessageType, MessagePriority, CommunicationStats

__all__ = [
    # 協作機制組件
    "DecisionCoordinator",
    "DynamicWeightAdjuster",
    "PortfolioAllocator",
    "AgentCommunication",

    # 決策協調相關
    "CoordinatedDecision",
    "CoordinationMethod",
    "ConflictResolution",

    # 權重調整相關
    "WeightAdjustmentMethod",
    "PerformanceRecord",
    "WeightAdjustment",

    # 投資組合配置相關
    "AllocationMethod",
    "AssetAllocation",
    "PortfolioAllocation",

    # 通信相關
    "Message",
    "MessageType",
    "MessagePriority",
    "CommunicationStats",
]

# 版本信息
__version__ = "1.0.0"
__author__ = "AI Trading System Team"
__description__ = "多代理協作機制 - 智能協作決策系統"
