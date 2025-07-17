# -*- coding: utf-8 -*-
"""
Legacy 模組 - 原始項目功能保留

此模組保留原始 ai_quant_trade-master 項目的核心功能，
確保向後兼容性和功能完整性。

主要功能：
- 原始回測系統
- 傳統數據處理
- 基礎投資組合管理
- 經典交易策略
- 工具集和示例

整合策略：
- 保留核心邏輯
- 提供適配器接口
- 維護向後兼容性
- 支持漸進式遷移
"""

# 版本信息
__version__ = "1.0.0"
__author__ = "Legacy Integration Team"
__description__ = "原始項目功能保留模組"

# 導入原始項目核心功能
try:
    # 這些導入將在實際整合時實現
    # from .quant_brain import *
    # from .data_io import *
    # from .backtest import *
    # from .portfolio import *
    pass
except ImportError:
    # 如果原始模組不可用，提供占位符
    pass

__all__ = [
    # 將在實際整合時添加具體的導出項目
]
