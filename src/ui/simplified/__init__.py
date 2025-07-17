# -*- coding: utf-8 -*-
"""
簡化操作界面模組

此模組提供新手友好的簡化操作界面，包括：
- 預設策略模板選擇器
- 一鍵回測功能
- 風險等級選擇器
- 簡化參數設定面板

Classes:
    StrategyTemplates: 策略模板管理器
    OneClickBacktest: 一鍵回測功能
    RiskLevelSelector: 風險等級選擇器
    SimpleConfigPanel: 簡化配置面板

Functions:
    show_strategy_templates: 顯示策略模板頁面
    show_one_click_backtest: 顯示一鍵回測頁面
    show_risk_level_selector: 顯示風險等級選擇頁面
    show_simple_config_panel: 顯示簡化配置頁面

Example:
    >>> from src.ui.simplified import show_strategy_templates
    >>> show_strategy_templates()

Note:
    此模組整合到 Streamlit Web UI 架構中，提供響應式設計支援
"""

from .strategy_templates import StrategyTemplates, show_strategy_templates
from .one_click_backtest import OneClickBacktest, show_one_click_backtest
from .risk_level_selector import RiskLevelSelector, show_risk_level_selector
from .simple_config_panel import SimpleConfigPanel, show_simple_config_panel

__all__ = [
    'StrategyTemplates',
    'OneClickBacktest',
    'RiskLevelSelector',
    'SimpleConfigPanel',
    'show_strategy_templates',
    'show_one_click_backtest',
    'show_risk_level_selector',
    'show_simple_config_panel',
]
