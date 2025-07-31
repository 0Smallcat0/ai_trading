"""登入表單模組

此模組提供用戶登入表單和相關功能。
"""

import streamlit as st
import logging
from .utils import SERVICES_AVAILABLE, USERS, get_authentication_service
from .session_manager import set_user_session, set_service_user_session
from .two_factor import show_2fa_form


def login_form() -> bool:
    """顯示登入表單

    提供完整的用戶登入界面，包括：
    - 標準用戶名/密碼登入
    - 開發模式快速登入
    - 兩步驗證支援
    - 錯誤處理和用戶反饋

    Returns:
        bool: 是否登入成功

    Example:
        ```python
        if login_form():
            st.success("登入成功")
        ```

    Note:
        可能修改 st.session_state 中的認證相關狀態
    """
    try:
        st.title("🔐 AI 股票自動交易系統")
        st.markdown("---")

        # 檢查是否已經在2FA驗證流程中
        if st.session_state.get("awaiting_2fa", False):
            return show_2fa_form()

        # 顯示系統狀態
        _show_system_status()

        # 添加自動登入選項（僅用於開發環境）
        _show_development_login()

        # 顯示主要登入表單
        return _show_main_login_form()

    except Exception as e:
        logging.error("登入表單顯示錯誤: %s", e, exc_info=True)
        st.error("登入系統發生錯誤，請重新整理頁面")
        return False


def _show_system_status() -> None:
    """顯示系統狀態信息"""
    with st.expander("📊 系統狀態", expanded=False):
        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "認證服務",
                "可用" if SERVICES_AVAILABLE else "簡化模式",
                "✅" if SERVICES_AVAILABLE else "⚠️",
            )

        with col2:
            st.metric(
                "登入方式",
                "完整認證" if SERVICES_AVAILABLE else "基本認證",
                "🔒" if SERVICES_AVAILABLE else "🔓",
            )


def _show_development_login() -> bool:
    """顯示開發模式登入選項

    Returns:
        bool: 是否通過開發模式登入成功
    """
    with st.expander("🔧 開發模式", expanded=False):
        st.warning("⚠️ 此功能僅用於開發和測試環境")

        if st.checkbox("啟用自動登入（開發模式）"):
            username = st.selectbox("選擇使用者", list(USERS.keys()))

            # 顯示選中用戶的信息
            if username in USERS:
                user_info = USERS[username]
                st.info(
                    f"**角色**: {user_info['role']} | **名稱**: {user_info['name']}"
                )

            if st.button("自動登入", key="dev_login"):
                try:
                    user_data = USERS[username]
                    set_user_session(username, user_data)
                    st.success("自動登入成功！")
                    st.rerun()
                    return True
                except Exception as e:
                    logging.error("自動登入失敗: %s", e)
                    st.error("自動登入失敗")
                    return False

    return False


def _show_main_login_form() -> bool:
    """顯示主要登入表單

    Returns:
        bool: 是否登入成功
    """
    # 創建登入表單
    with st.form("login_form"):
        st.subheader("🔑 使用者登入")

        col1, col2 = st.columns([2, 1])

        with col1:
            username = st.text_input(
                "👤 使用者名稱或電子郵件",
                placeholder="請輸入使用者名稱",
                help="支援使用者名稱或電子郵件登入",
            )
            password = st.text_input(
                "🔒 密碼",
                type="password",
                placeholder="請輸入密碼",
                help="請輸入您的登入密碼",
            )

            col_remember, col_submit = st.columns([1, 1])
            with col_remember:
                remember_me = st.checkbox("記住登入狀態", help="下次訪問時自動登入")
            with col_submit:
                submit = st.form_submit_button("🚀 登入", use_container_width=True)

        with col2:
            _show_test_accounts()

        if submit:
            return _process_login(username, password, remember_me)

    return False


def _show_test_accounts() -> None:
    """顯示測試帳號信息"""
    st.markdown("### 📋 測試帳號")

    accounts_info = [
        ("管理員", "admin", "admin123", "完整權限"),
        ("交易員", "trader", "trader123", "需2FA"),
        ("分析師", "analyst", "analyst123", "分析權限"),
        ("一般用戶", "user", "user123", "基本權限"),
        ("訪客", "guest", "guest123", "只讀權限"),
    ]

    for role, username, password, note in accounts_info:
        st.markdown(f"**{role}**: `{username}` / `{password}`")
        if note:
            st.caption(f"({note})")


def _process_login(username: str, password: str, remember_me: bool) -> bool:
    """處理登入邏輯

    Args:
        username: 使用者名稱
        password: 密碼
        remember_me: 是否記住登入狀態

    Returns:
        bool: 是否登入成功
    """
    if not username or not password:
        st.error("請輸入使用者名稱和密碼")
        return False

    try:
        # 獲取客戶端資訊
        ip_address = "127.0.0.1"  # 在實際應用中應該獲取真實IP
        user_agent = "Streamlit App"

        # 嘗試使用服務層進行認證
        if SERVICES_AVAILABLE:
            return _service_login(
                username, password, ip_address, user_agent, remember_me
            )

        # 使用簡化認證
        return _simple_login(username, password, remember_me)

    except Exception as e:
        logging.error("登入處理過程發生錯誤: %s", e, exc_info=True)
        st.error("登入過程發生錯誤，請稍後再試")
        return False


def _service_login(
    username: str, password: str, ip_address: str, user_agent: str, remember_me: bool
) -> bool:
    """使用服務層進行認證

    Args:
        username: 使用者名稱
        password: 密碼
        ip_address: IP地址
        user_agent: 用戶代理
        remember_me: 是否記住登入狀態

    Returns:
        bool: 是否登入成功
    """
    try:
        # 初始化認證服務
        if "auth_service" not in st.session_state:
            st.session_state.auth_service = get_authentication_service()

        auth_service = st.session_state.auth_service

        # 進行認證
        success, message, result = auth_service.login_with_password(
            username, password, ip_address, user_agent, remember_me
        )

        if success:
            if result.get("requires_2fa", False):
                # 需要兩步驗證
                st.session_state.awaiting_2fa = True
                st.session_state.temp_user_id = result["user_id"]
                st.session_state.temp_session_id = result.get("temp_session_id")
                st.info("請輸入兩步驗證碼")
                st.rerun()
                return False

            # 登入成功
            user_info = result["user_info"]
            set_service_user_session(user_info, result)
            st.success(f"登入成功！歡迎 {user_info['full_name']}")
            st.rerun()
            return True

        st.error(f"登入失敗: {message}")
        return False

    except Exception as e:
        logging.warning("認證服務暫時不可用: %s", e)
        st.warning("認證服務暫時不可用，使用簡化認證")
        # 降級到簡化認證
        return _simple_login(username, password, remember_me)


def _simple_login(username: str, password: str, remember_me: bool = False) -> bool:
    """簡化登入邏輯（當服務不可用時使用）

    Args:
        username: 使用者名稱或電子郵件
        password: 密碼
        remember_me: 是否記住登入狀態（暫未實現）

    Returns:
        bool: 是否登入成功
    """
    # 忽略未使用的參數
    _ = remember_me

    # 檢查使用者名稱或電子郵件
    user_data = None
    matched_username = None

    for uname, data in USERS.items():
        if username in (uname, data["email"]):
            user_data = data
            matched_username = uname
            break

    if user_data and user_data["password"] == password:
        if user_data["two_factor_enabled"]:
            # 需要兩步驗證
            st.session_state.awaiting_2fa = True
            st.session_state.temp_user_id = user_data["user_id"]
            st.session_state.temp_session_id = "temp_session_123"
            st.info("請輸入兩步驗證碼")
            st.rerun()
            return False

        # 直接登入成功
        st.session_state.authenticated = True
        st.session_state.username = matched_username
        st.session_state.user_role = user_data["role"]
        st.session_state.user_name = user_data["name"]
        st.session_state.user_id = user_data["user_id"]
        st.session_state.email = user_data["email"]
        st.success(f"登入成功！歡迎 {user_data['name']}")
        st.rerun()
        return True

    st.error("使用者名稱或密碼錯誤！")
    return False
