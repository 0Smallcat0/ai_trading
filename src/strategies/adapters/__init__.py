# -*- coding: utf-8 -*-
"""
策略適配器模組

此模組提供將外部策略庫整合到當前AI交易系統的適配器框架，包括：

基礎適配器：
- LegacyStrategyAdapter: 舊版策略適配器基類
- DataFormatConverter: 數據格式轉換器
- StrategyWrapper: 策略包裝器

具體適配器：
- DoubleMaAdapter: 雙移動平均線策略適配器
- Alpha101Adapter: Alpha101因子庫適配器
- RLStrategyAdapter: 強化學習策略適配器
- FactorMiningAdapter: 因子挖掘系統適配器
- MarketWatchAdapter: 市場看盤工具適配器

主要功能：
- 零修改原則：保持原始策略代碼完全不變
- 統一接口：提供標準Strategy接口包裝
- 數據轉換：處理不同數據格式間的轉換
- 錯誤處理：統一的異常處理和日誌記錄
- 性能優化：確保適配器不影響策略性能
"""

from .base import (
    LegacyStrategyAdapter,
    DataFormatConverter,
    StrategyWrapper,
    AdapterError,
    DataConversionError,
    StrategyExecutionError,
)

from .double_ma_adapter import DoubleMaAdapter
from .alpha101_adapter import Alpha101Adapter
from .rl_strategy_adapter import RLStrategyAdapter
from .factor_mining_adapter import FactorMiningAdapter
from .market_watch_adapter import MarketWatchAdapter

__all__ = [
    # 基礎適配器
    "LegacyStrategyAdapter",
    "DataFormatConverter",
    "StrategyWrapper",
    # 異常類別
    "AdapterError",
    "DataConversionError",
    "StrategyExecutionError",
    # 具體適配器
    "DoubleMaAdapter",
    "Alpha101Adapter",
    "RLStrategyAdapter",
    "FactorMiningAdapter",
    "MarketWatchAdapter",
]

__version__ = "1.0.0"
__author__ = "Strategy Integration Team"
__description__ = "策略庫擴展整合適配器模組"
