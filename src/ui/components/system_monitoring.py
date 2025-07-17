"""系統監控組件

此模組整合所有系統監控相關功能，提供統一的系統監控介面：
- 系統監控基本功能
- 高級監控功能
- 功能狀態儀表板
- 多代理管理儀表板
- 安全管理
- 系統狀態監控版
- 雙因子認證管理

主要功能：
- 統一的系統監控入口
- 模組化的子功能整合
- 統一的錯誤處理機制
- 響應式設計支援

Example:
    >>> from src.ui.components.system_monitoring import show
    >>> show()  # 顯示系統監控主介面
"""

import logging
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)


def show() -> None:
    """顯示系統監控主介面.
    
    整合所有系統監控相關功能到統一的標籤頁介面中。
    提供7個子功能的完整整合，包括錯誤處理和狀態管理。
    
    主要子功能：
    - 系統監控：基本的系統狀態監控
    - 高級監控：進階監控功能和分析
    - 功能狀態：各功能模組的狀態儀表板
    - 多代理管理：多代理AI系統的管理介面
    - 安全管理：系統安全設定和監控
    - 系統狀態：系統狀態監控顯示
    - 雙因子認證：雙因子認證管理功能
    
    Returns:
        None
        
    Side Effects:
        - 渲染 Streamlit 界面組件
        - 可能修改 st.session_state 中的相關狀態
        
    Example:
        >>> show()  # 顯示完整的系統監控介面
        
    Note:
        此函數整合了多個原有頁面的功能，保持向後兼容性。
        如果某個子功能不可用，會顯示相應的錯誤訊息。
    """
    try:
        st.title("🖥️ 系統監控")
        st.markdown("---")
        
        # 創建子功能標籤頁
        tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
            "📊 系統監控",
            "🔍 高級監控", 
            "🎛️ 功能狀態",
            "🤖 多代理管理",
            "🔒 安全管理",
            "📈 系統狀態",
            "🔐 雙因子認證"
        ])
        
        with tab1:
            _show_system_monitoring()
            
        with tab2:
            _show_advanced_monitoring()
            
        with tab3:
            _show_function_status_dashboard()
            
        with tab4:
            _show_multi_agent_dashboard()
            
        with tab5:
            _show_security_management()
            
        with tab6:
            _show_system_status_enhanced()
            
        with tab7:
            _show_two_factor_management()
            
    except Exception as e:
        logger.error("顯示系統監控介面時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 系統監控介面載入失敗")
        with st.expander("錯誤詳情"):
            st.code(str(e))


def _show_system_monitoring() -> None:
    """顯示基本系統監控功能.
    
    調用原有的 system_monitoring 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入系統監控頁面失敗時
    """
    try:
        from src.ui.pages.system_monitoring import show as system_monitoring_show
        system_monitoring_show()
        
    except ImportError as e:
        logger.warning("無法導入系統監控頁面: %s", e)
        st.warning("⚠️ 系統監控功能暫時不可用")
        _show_fallback_system_monitoring()
        
    except Exception as e:
        logger.error("顯示系統監控時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 系統監控功能載入失敗")
        _show_fallback_system_monitoring()


def _show_advanced_monitoring() -> None:
    """顯示高級監控功能.
    
    調用原有的 advanced_monitoring 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入高級監控頁面失敗時
    """
    try:
        from src.ui.pages.advanced_monitoring import show as advanced_monitoring_show
        advanced_monitoring_show()
        
    except ImportError as e:
        logger.warning("無法導入高級監控頁面: %s", e)
        st.warning("⚠️ 高級監控功能暫時不可用")
        _show_fallback_advanced_monitoring()
        
    except Exception as e:
        logger.error("顯示高級監控時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 高級監控功能載入失敗")
        _show_fallback_advanced_monitoring()


def _show_function_status_dashboard() -> None:
    """顯示功能狀態儀表板.
    
    調用原有的 function_status_dashboard 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入功能狀態儀表板失敗時
    """
    try:
        from src.ui.pages.function_status_dashboard import show as function_status_show
        function_status_show()
        
    except ImportError as e:
        logger.warning("無法導入功能狀態儀表板: %s", e)
        st.warning("⚠️ 功能狀態儀表板暫時不可用")
        _show_fallback_function_status()
        
    except Exception as e:
        logger.error("顯示功能狀態儀表板時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 功能狀態儀表板載入失敗")
        _show_fallback_function_status()


def _show_multi_agent_dashboard() -> None:
    """顯示多代理管理儀表板.
    
    調用原有的 multi_agent_dashboard 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入多代理管理儀表板失敗時
    """
    try:
        from src.ui.pages.multi_agent_dashboard import show as multi_agent_show
        multi_agent_show()
        
    except ImportError as e:
        logger.warning("無法導入多代理管理儀表板: %s", e)
        st.warning("⚠️ 多代理管理功能暫時不可用")
        _show_fallback_multi_agent()
        
    except Exception as e:
        logger.error("顯示多代理管理儀表板時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 多代理管理功能載入失敗")
        _show_fallback_multi_agent()


def _show_security_management() -> None:
    """顯示安全管理功能.
    
    調用原有的 security_management 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入安全管理頁面失敗時
    """
    try:
        from src.ui.pages.security_management import show as security_show
        security_show()
        
    except ImportError as e:
        logger.warning("無法導入安全管理頁面: %s", e)
        st.warning("⚠️ 安全管理功能暫時不可用")
        _show_fallback_security_management()
        
    except Exception as e:
        logger.error("顯示安全管理時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 安全管理功能載入失敗")
        _show_fallback_security_management()


def _show_system_status_enhanced() -> None:
    """顯示增強版系統狀態.
    
    調用原有的 system_status_enhanced 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入增強版系統狀態失敗時
    """
    try:
        from src.ui.pages.system_status_enhanced import show as system_status_show
        system_status_show()
        
    except ImportError as e:
        logger.warning("無法導入增強版系統狀態: %s", e)
        st.warning("⚠️ 增強版系統狀態功能暫時不可用")
        _show_fallback_system_status()
        
    except Exception as e:
        logger.error("顯示增強版系統狀態時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 增強版系統狀態載入失敗")
        _show_fallback_system_status()


def _show_two_factor_management() -> None:
    """顯示雙因子認證管理.
    
    調用原有的 two_factor_management 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入雙因子認證管理失敗時
    """
    try:
        from src.ui.pages.two_factor_management import show as two_factor_show
        two_factor_show()
        
    except ImportError as e:
        logger.warning("無法導入雙因子認證管理: %s", e)
        st.warning("⚠️ 雙因子認證管理功能暫時不可用")
        _show_fallback_two_factor()
        
    except Exception as e:
        logger.error("顯示雙因子認證管理時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 雙因子認證管理載入失敗")
        _show_fallback_two_factor()


# 備用顯示函數
def _show_fallback_system_monitoring() -> None:
    """系統監控的備用顯示函數."""
    st.info("📊 系統監控功能正在載入中...")
    st.markdown("**基本功能**：系統狀態監控、性能指標、資源使用情況")


def _show_fallback_advanced_monitoring() -> None:
    """高級監控的備用顯示函數."""
    st.info("🔍 高級監控功能正在載入中...")
    st.markdown("**進階功能**：詳細分析、趨勢預測、異常檢測")


def _show_fallback_function_status() -> None:
    """功能狀態的備用顯示函數."""
    st.info("🎛️ 功能狀態儀表板正在載入中...")
    st.markdown("**狀態監控**：各功能模組運行狀態、健康度檢查")


def _show_fallback_multi_agent() -> None:
    """多代理管理的備用顯示函數."""
    st.info("🤖 多代理管理功能正在載入中...")
    st.markdown("**代理管理**：多代理協調、性能監控、配置管理")


def _show_fallback_security_management() -> None:
    """安全管理的備用顯示函數."""
    st.info("🔒 安全管理功能正在載入中...")
    st.markdown("**安全功能**：權限管理、安全監控、威脅檢測")


def _show_fallback_system_status() -> None:
    """系統狀態的備用顯示函數."""
    st.info("📈 增強版系統狀態正在載入中...")
    st.markdown("**狀態顯示**：詳細系統狀態、性能指標、運行統計")


def _show_fallback_two_factor() -> None:
    """雙因子認證的備用顯示函數."""
    st.info("🔐 雙因子認證管理正在載入中...")
    st.markdown("**認證管理**：雙因子設定、安全驗證、設備管理")
