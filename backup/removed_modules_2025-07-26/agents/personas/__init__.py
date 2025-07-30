# -*- coding: utf-8 -*-
"""
角色扮演代理模組

此模組提供模擬知名投資大師的角色扮演型AI交易代理，包括：

角色扮演代理：
- BuffettAgent: 巴菲特代理 - 長期價值投資風格
- SorosAgent: 索羅斯代理 - 宏觀對沖投資風格
- SimonsAgent: 西蒙斯代理 - 量化交易投資風格
- DalioAgent: 達里奧代理 - 全天候投資風格
- GrahamAgent: 格雷厄姆代理 - 深度價值投資風格

每個代理都模擬對應投資大師的：
- 投資哲學和理念
- 決策思維模式
- 風險管理方法
- 市場分析角度
- 投資時間框架

主要特色：
- 基於LLM的決策推理能力
- 情境感知和市場情緒分析
- 角色特定的投資邏輯
- 可解釋的決策過程
- 歷史投資案例學習
"""

# 角色扮演代理
from .buffett_agent import BuffettAgent
from .soros_agent import SorosAgent
from .simons_agent import SimonsAgent
from .dalio_agent import DalioAgent
from .graham_agent import GrahamAgent

__all__ = [
    # 角色扮演代理
    "BuffettAgent",
    "SorosAgent",
    "SimonsAgent",
    "DalioAgent",
    "GrahamAgent",
]

# 版本信息
__version__ = "1.0.0"
__author__ = "AI Trading System Team"
__description__ = "角色扮演代理 - 投資大師AI化身"
