# -*- coding: utf-8 -*-
"""
教育資源整合模組

此模組提供完整的量化交易教育資源，包括：
- 量化交易基礎知識
- 策略邏輯解釋器
- 風險管理教育
- 常見錯誤預防系統

Classes:
    TradingBasics: 量化交易基礎教育
    StrategyExplainer: 策略邏輯解釋器
    RiskEducation: 風險管理教育
    ErrorPrevention: 錯誤預防系統

Functions:
    show_trading_basics: 顯示基礎教育頁面
    show_strategy_explainer: 顯示策略解釋頁面
    show_risk_education: 顯示風險教育頁面
    show_error_prevention: 顯示錯誤預防頁面

Example:
    >>> from src.education import show_trading_basics
    >>> show_trading_basics()

Note:
    此模組整合到 Streamlit Web UI 架構中，提供響應式設計支援
"""

from .trading_basics import TradingBasics, show_trading_basics
from .strategy_explainer import StrategyExplainer, show_strategy_explainer
from .risk_education import RiskEducation, show_risk_education
from .error_prevention import ErrorPrevention, show_error_prevention

__all__ = [
    'TradingBasics',
    'StrategyExplainer',
    'RiskEducation',
    'ErrorPrevention',
    'show_trading_basics',
    'show_strategy_explainer',
    'show_risk_education',
    'show_error_prevention',
]
