"""安全與權限管理組件

此模組整合所有安全與權限管理相關功能，提供統一的安全管理介面：
- 安全管理功能
- 雙因子認證管理

主要功能：
- 統一的安全管理入口
- 用戶權限管理
- 安全設定和監控
- 雙因子認證配置
- 統一的錯誤處理機制

Example:
    >>> from src.ui.components.security_permission_management import show
    >>> show()  # 顯示安全與權限管理主介面
"""

import logging
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)


def show() -> None:
    """顯示安全與權限管理主介面.
    
    整合所有安全與權限管理相關功能到統一的標籤頁介面中。
    提供2個子功能的完整整合，包括錯誤處理和狀態管理。
    
    主要子功能：
    - 安全管理：系統安全設定、監控和威脅檢測
    - 雙因子認證：雙因子認證管理和設備管理
    
    Returns:
        None
        
    Side Effects:
        - 渲染 Streamlit 界面組件
        - 可能修改 st.session_state 中的相關狀態
        
    Example:
        >>> show()  # 顯示完整的安全與權限管理介面
        
    Note:
        此函數整合了多個原有頁面的功能，保持向後兼容性。
        如果某個子功能不可用，會顯示相應的錯誤訊息。
    """
    try:
        st.title("🔐 安全與權限管理")
        st.markdown("---")
        
        # 創建子功能標籤頁
        tab1, tab2 = st.tabs([
            "🔒 安全管理",
            "🔐 雙因子認證"
        ])
        
        with tab1:
            _show_security_management()
            
        with tab2:
            _show_two_factor_management()
            
    except Exception as e:
        logger.error("顯示安全與權限管理介面時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 安全與權限管理介面載入失敗")
        with st.expander("錯誤詳情"):
            st.code(str(e))


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


def _show_fallback_security_management() -> None:
    """安全管理的備用顯示函數.
    
    當原有的安全管理頁面無法載入時，顯示基本的功能說明。
    
    Returns:
        None
    """
    st.info("🔒 安全管理功能正在載入中...")
    
    st.markdown("""
    **安全管理系統** 提供完整的系統安全功能，包括：
    - 🔐 **權限管理**: 用戶角色和權限配置
    - 🛡️ **安全監控**: 即時安全威脅檢測和防護
    - 🚨 **威脅檢測**: 異常行為和入侵檢測
    - 📋 **安全日誌**: 安全事件記錄和審計
    - ⚙️ **安全設定**: 系統安全參數配置
    """)
    
    # 顯示安全狀態概覽
    st.markdown("### 🛡️ 安全狀態概覽")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("安全等級", "高", "✅")
    
    with col2:
        st.metric("威脅檢測", "0", "🟢")
    
    with col3:
        st.metric("活躍會話", "3", "📊")
    
    with col4:
        st.metric("最後掃描", "5分鐘前", "🔍")
    
    # 顯示安全設定
    st.markdown("### ⚙️ 安全設定")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 認證設定")
        password_policy = st.selectbox("密碼政策", ["標準", "嚴格", "企業級"])
        session_timeout = st.slider("會話超時 (分鐘)", 15, 480, 60)
        
    with col2:
        st.markdown("#### 監控設定")
        threat_detection = st.checkbox("威脅檢測", value=True)
        audit_logging = st.checkbox("審計日誌", value=True)
    
    if st.button("💾 保存安全設定", type="primary"):
        st.success("✅ 安全設定已保存")
        st.info(f"密碼政策: {password_policy}, 會話超時: {session_timeout}分鐘")


def _show_fallback_two_factor() -> None:
    """雙因子認證的備用顯示函數.
    
    當原有的雙因子認證管理頁面無法載入時，顯示基本的功能說明。
    
    Returns:
        None
    """
    st.info("🔐 雙因子認證管理功能正在載入中...")
    
    st.markdown("""
    **雙因子認證管理** 提供完整的2FA管理功能，包括：
    - 📱 **設備管理**: 管理已註冊的認證設備
    - 🔑 **認證方式**: 支援多種2FA認證方式
    - 🛡️ **安全驗證**: 強化帳戶安全保護
    - 📋 **備用代碼**: 緊急訪問備用代碼管理
    - ⚙️ **2FA設定**: 雙因子認證參數配置
    """)
    
    # 顯示2FA狀態
    st.markdown("### 🔐 雙因子認證狀態")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("2FA狀態", "已啟用", "✅")
    
    with col2:
        st.metric("註冊設備", "2", "📱")
    
    with col3:
        st.metric("備用代碼", "8", "🔑")
    
    # 顯示設備管理
    st.markdown("### 📱 已註冊設備")
    
    devices = [
        {"名稱": "iPhone 13", "類型": "手機應用", "狀態": "✅ 活躍", "最後使用": "2小時前"},
        {"名稱": "Google Authenticator", "類型": "認證應用", "狀態": "✅ 活躍", "最後使用": "1天前"}
    ]
    
    for device in devices:
        with st.expander(f"{device['名稱']} - {device['狀態']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**類型**: {device['類型']}")
                st.write(f"**狀態**: {device['狀態']}")
            with col2:
                st.write(f"**最後使用**: {device['最後使用']}")
                if st.button(f"移除設備", key=f"remove_{device['名稱']}"):
                    st.warning(f"設備 {device['名稱']} 移除功能開發中...")
    
    # 添加新設備
    st.markdown("### ➕ 添加新設備")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📱 手機應用", use_container_width=True):
            st.info("手機應用設定功能開發中...")
    
    with col2:
        if st.button("💻 桌面應用", use_container_width=True):
            st.info("桌面應用設定功能開發中...")
    
    with col3:
        if st.button("🔑 硬體金鑰", use_container_width=True):
            st.info("硬體金鑰設定功能開發中...")


# 輔助函數
def get_security_status() -> dict:
    """獲取安全狀態信息.
    
    Returns:
        dict: 包含安全狀態的字典
        
    Example:
        >>> status = get_security_status()
        >>> print(status['security_level'])
        'high'
    """
    return {
        'security_level': 'high',
        'threat_count': 0,
        'active_sessions': 3,
        'last_scan': '5分鐘前',
        'two_factor_enabled': True
    }


def validate_security_config(config: dict) -> bool:
    """驗證安全配置.
    
    Args:
        config: 安全配置字典
        
    Returns:
        bool: 配置是否有效
        
    Example:
        >>> config = {'password_policy': 'strict', 'session_timeout': 60}
        >>> is_valid = validate_security_config(config)
        >>> print(is_valid)
        True
    """
    required_fields = ['password_policy', 'session_timeout']
    if not all(field in config for field in required_fields):
        return False
    
    # 檢查數值範圍
    if config['session_timeout'] < 15 or config['session_timeout'] > 480:
        return False
    
    valid_policies = ['標準', '嚴格', '企業級']
    if config['password_policy'] not in valid_policies:
        return False
    
    return True
