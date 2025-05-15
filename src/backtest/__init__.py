# -*- coding: utf-8 -*-
"""
回測模組

此模組提供回測功能，包括：
- Backtrader 整合
- 自定義策略
- 交易成本模擬
- 回測分析
- 壓力測試
"""

from .backtrader_integration import BacktestEngine, ModelSignalStrategy, PandasDataFeed
from .custom_strategies import MLStrategy, EnsembleStrategy, TechnicalStrategy
from .transaction_costs import (
    FixedCommissionScheme,
    PercentCommissionScheme,
    TieredCommissionScheme,
    TaxScheme,
    CombinedCostScheme,
    TWStockCostScheme,
    USStockCostScheme,
    get_cost_scheme
)
from .analysis import BacktestAnalyzer
from .stress_testing import StressTester
