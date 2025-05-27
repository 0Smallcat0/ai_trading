"""風險管理頁面 - 向後兼容性包裝器

此模組為向後兼容性提供包裝器，將請求重定向到新的模組化結構。

新的模組化結構位於 src/ui/pages/risk_management/ 目錄下：
- parameters.py: 風險參數設定
- indicators.py: 風險指標監控  
- controls.py: 風控機制管理
- alerts.py: 風險警報記錄
- utils.py: 共用工具函數

Author: AI Trading System
Version: 1.0.0 (Legacy Wrapper)
"""

import warnings
import streamlit as st

# 發出棄用警告
warnings.warn(
    "使用 risk_management_legacy.py 已棄用。"
    "請使用 src/ui/pages/risk_management/ 模組。",
    DeprecationWarning,
    stacklevel=2,
)


def show_legacy_migration_notice():
    """顯示遷移通知"""
    st.warning(
        """
    ⚠️ **模組已重構通知**
    
    風險管理模組已重構為模組化架構，提供更好的維護性和擴展性。
    
    **新的模組結構：**
    - 📁 `src/ui/pages/risk_management/`
      - `__init__.py` - 主入口
      - `parameters.py` - 風險參數設定
      - `indicators.py` - 風險指標監控
      - `controls.py` - 風控機制管理
      - `alerts.py` - 風險警報記錄
      - `utils.py` - 共用工具函數
    
    **遷移指南：**
    1. 更新導入語句：`from src.ui.pages.risk_management import show`
    2. 使用新的模組化 API
    3. 參考新的文檔和示例
    
    **優勢：**
    - ✅ 更好的代碼組織
    - ✅ 更容易維護和測試
    - ✅ 更好的性能
    - ✅ 支援響應式設計
    """
    )


# 導入新的模組化實現
try:
    from .risk_management import show as new_show
    from .risk_management import (
        show_risk_parameters,
        show_risk_indicators,
        show_risk_controls,
        show_risk_alerts,
        get_risk_management_service,
        get_default_risk_parameters,
    )

    def show():
        """向後兼容的主函數"""
        show_legacy_migration_notice()
        st.divider()
        new_show()

except ImportError as e:
    # 如果新模組不可用，提供基本實現
    def show():
        st.error(f"新的風險管理模組不可用: {e}")
        st.info("請檢查模組結構和依賴關係")

    def show_risk_parameters():
        st.error("風險參數模組不可用")

    def show_risk_indicators():
        st.error("風險指標模組不可用")

    def show_risk_controls():
        st.error("風控機制模組不可用")

    def show_risk_alerts():
        st.error("風險警報模組不可用")

    def get_risk_management_service():
        return None

    def get_default_risk_parameters():
        return {}


# 向後兼容的函數別名
show_risk_management = show
risk_management_page = show

# 導出向後兼容的 API
__all__ = [
    "show",
    "show_risk_management",
    "risk_management_page",
    "show_risk_parameters",
    "show_risk_indicators",
    "show_risk_controls",
    "show_risk_alerts",
    "get_risk_management_service",
    "get_default_risk_parameters",
]
