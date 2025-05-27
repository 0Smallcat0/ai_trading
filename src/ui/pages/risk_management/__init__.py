"""風險管理模組主入口

此模組提供風險管理頁面的主要入口點，整合所有子模組功能：
- 風險參數設定 (parameters.py)
- 風險指標監控 (indicators.py)
- 風控機制管理 (controls.py)
- 風險警報記錄 (alerts.py)
- 共用工具函數 (utils.py)

Author: AI Trading System
Version: 1.0.0
"""

from typing import Optional

import streamlit as st

from .alerts import get_alert_summary, show_risk_alerts
from .controls import show_risk_controls
from .indicators import show_risk_indicators, show_risk_summary

# 導入子模組
from .parameters import show_risk_parameters
from .utils import get_default_risk_parameters, get_risk_management_service


def show() -> None:
    """顯示風險管理頁面

    主要入口函數，顯示風險管理頁面的標籤頁界面。
    提供完整的風險管理功能，包括參數設定、指標監控、
    機制控制和警報管理。

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示風險管理頁面
        - 初始化必要的 session_state 變數
    """
    # 頁面標題和描述
    st.title("🛡️ 風險管理系統")
    st.markdown(
        """
    **風險管理系統** 提供全面的投資組合風險控制功能，包括：
    - 📊 **風險指標監控**: 即時監控 VaR、回撤、波動率等關鍵指標
    - ⚙️ **風險參數設定**: 設定停損停利、部位限制、資金控管等參數
    - 🔧 **風控機制管理**: 控制各種風控機制的啟用狀態
    - 🚨 **風險警報記錄**: 查看和管理風險事件與警報
    """
    )

    # 檢查系統狀態
    _check_system_status()

    # 創建標籤頁
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 風險指標", "⚙️ 參數設定", "🔧 風控機制", "🚨 警報記錄"]
    )

    with tab1:
        show_risk_indicators()

    with tab2:
        show_risk_parameters()

    with tab3:
        show_risk_controls()

    with tab4:
        show_risk_alerts()

    # 顯示頁面底部信息
    _show_footer_info()


def _check_system_status() -> None:
    """檢查系統狀態並顯示警告"""
    # 檢查風險管理服務狀態
    risk_service = get_risk_management_service()

    if not risk_service:
        st.warning(
            """
        ⚠️ **風險管理服務未啟用**

        目前使用模擬數據進行演示。在生產環境中，請確保：
        1. 風險管理服務正常運行
        2. 數據庫連接正常
        3. 相關配置文件正確設置
        """
        )

    # 檢查緊急停止狀態
    if st.session_state.get("risk_controls_status", {}).get(
        "emergency_stop_active", False
    ):
        st.error(
            """
        🚨 **緊急停止模式啟用**

        所有交易活動已暫停。請檢查風險狀況後在「風控機制」頁面重啟系統。
        """
        )

    # 檢查主開關狀態
    if not st.session_state.get("master_risk_switch", True):
        st.error(
            """
        🔴 **風控主開關已關閉**

        所有風控機制已停用。請在「風控機制」頁面重新啟用。
        """
        )


def _show_footer_info() -> None:
    """顯示頁面底部信息"""
    st.divider()

    # 系統狀態摘要
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # 風險評分
        show_risk_summary()

    with col2:
        # 警報摘要
        alert_summary = get_alert_summary()
        st.metric(
            "待處理警報",
            alert_summary["pending"],
            f"高風險: {alert_summary['high_severity']}",
        )

    with col3:
        # 系統狀態
        risk_service = get_risk_management_service()
        if risk_service:
            st.metric("系統狀態", "🟢 正常", "服務運行中")
        else:
            st.metric("系統狀態", "🟡 演示", "使用模擬數據")

    with col4:
        # 最後更新時間
        from datetime import datetime

        st.metric("最後更新", datetime.now().strftime("%H:%M:%S"), "即時監控")

    # 版本信息和幫助
    st.markdown(
        """
    ---
    **風險管理系統 v1.0.0** |
    [📖 使用手冊](docs/risk_management_guide.md) |
    [🔧 系統設定](docs/system_config.md) |
    [❓ 常見問題](docs/faq.md)
    """
    )


# 向後兼容性：保持原有的函數名稱
def show_risk_management() -> None:
    """向後兼容的函數名稱

    為了保持與現有代碼的兼容性，提供原有的函數名稱。

    Returns:
        None
    """
    show()


# 導出主要函數和類別
__all__ = [
    "show",
    "show_risk_management",
    "show_risk_parameters",
    "show_risk_indicators",
    "show_risk_controls",
    "show_risk_alerts",
    "get_risk_management_service",
    "get_default_risk_parameters",
    "get_alert_summary",
]


# 模組級別的配置
RISK_MANAGEMENT_VERSION = "1.0.0"
SUPPORTED_FEATURES = [
    "stop_loss",
    "take_profit",
    "position_limits",
    "var_monitoring",
    "drawdown_protection",
    "correlation_analysis",
    "sector_limits",
    "real_time_alerts",
]


def get_module_info() -> dict:
    """獲取模組信息

    Returns:
        dict: 包含模組版本和功能信息的字典
    """
    return {
        "version": RISK_MANAGEMENT_VERSION,
        "features": SUPPORTED_FEATURES,
        "submodules": ["parameters", "indicators", "controls", "alerts", "utils"],
    }
