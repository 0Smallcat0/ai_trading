# -*- coding: utf-8 -*-
"""
投資風格代理模組

此模組提供不同投資風格的交易代理實現，包括：

投資風格代理：
- ValueInvestor: 價值投資代理
- TechnicalTrader: 技術分析代理
- MomentumTrader: 動量交易代理
- ArbitrageTrader: 套利交易代理
- RiskParityAgent: 風險平價代理

每個代理都有獨特的投資哲學和決策邏輯：
- 價值投資：關注基本面分析，尋找被低估的股票
- 技術分析：基於技術指標和圖形模式進行交易
- 動量交易：追蹤價格和成交量動量，快速進出
- 套利交易：尋找價格差異機會，市場中性策略
- 風險平價：基於風險貢獻的資產配置，分散投資

主要特色：
- 每個代理有獨特的投資風格和風險偏好
- 基於不同的市場數據和指標進行決策
- 支援自定義參數和策略調整
- 完整的績效追蹤和風險管理
"""

# 投資風格代理
from .value_investor import ValueInvestor
from .technical_trader import TechnicalTrader
from .momentum_trader import MomentumTrader
from .arbitrage_trader import ArbitrageTrader
from .risk_parity_agent import RiskParityAgent

__all__ = [
    # 投資風格代理
    "ValueInvestor",
    "TechnicalTrader",
    "MomentumTrader",
    "ArbitrageTrader",
    "RiskParityAgent",
]

# 版本信息
__version__ = "1.0.0"
__author__ = "AI Trading System Team"
__description__ = "投資風格代理 - 多樣化投資策略實現"
