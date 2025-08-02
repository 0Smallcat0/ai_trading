"""
用戶支援服務模組 (User Support Services)

此模組提供用戶支援的核心服務功能，包括：
- 新手引導服務
- 操作記錄服務
- 幫助文檔服務

主要功能：
- 新用戶引導流程
- 操作歷史記錄
- 幫助文檔管理
- 用戶行為分析
- 學習進度追蹤
- 常見問題解答

支援功能：
- 互動式教程
- 操作提示系統
- 錯誤診斷工具
- 學習資源推薦
- 用戶反饋收集
"""

from .onboarding_service import OnboardingService
from .operation_log_service import OperationLogService
from .help_service import HelpService

__all__ = [
    "OnboardingService",
    "OperationLogService",
    "HelpService",
]
