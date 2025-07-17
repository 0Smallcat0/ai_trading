# -*- coding: utf-8 -*-
"""
新手引導系統模組

此模組提供完整的新手引導功能，包括：
- 一鍵安裝和環境配置嚮導
- 互動式快速入門教程
- 預建示範策略模板
- 模擬交易練習環境
- 學習進度追蹤儀表板

Classes:
    OnboardingManager: 新手引導管理器
    SetupWizard: 安裝配置嚮導
    QuickStartGuide: 快速入門指南
    DemoStrategies: 示範策略管理
    PracticeMode: 練習模式管理
    ProgressDashboard: 進度追蹤儀表板

Functions:
    show_onboarding_page: 顯示新手引導主頁面
    check_setup_status: 檢查系統設定狀態
    get_user_progress: 獲取用戶學習進度

Example:
    >>> from src.ui.onboarding import show_onboarding_page
    >>> show_onboarding_page()

Note:
    此模組整合到 Streamlit Web UI 架構中，提供響應式設計支援
"""

from .setup_wizard import SetupWizard, show_setup_wizard
from .quick_start_guide import QuickStartGuide, show_quick_start_guide
from .demo_strategies import DemoStrategies, show_demo_strategies
from .practice_mode import PracticeMode, show_practice_mode
from .progress_dashboard import ProgressDashboard, show_progress_dashboard
from .decision_logger import DecisionLogger, show_decision_logger
from .performance_analyzer import PerformanceAnalyzer, show_performance_analyzer
from .mistake_analyzer import MistakeAnalyzer, show_mistake_analyzer

__all__ = [
    'SetupWizard',
    'QuickStartGuide',
    'DemoStrategies',
    'PracticeMode',
    'ProgressDashboard',
    'DecisionLogger',
    'PerformanceAnalyzer',
    'MistakeAnalyzer',
    'show_setup_wizard',
    'show_quick_start_guide',
    'show_demo_strategies',
    'show_practice_mode',
    'show_progress_dashboard',
    'show_decision_logger',
    'show_performance_analyzer',
    'show_mistake_analyzer',
]
