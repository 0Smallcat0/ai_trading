"""兩步驗證模組

此模組提供兩步驗證相關功能。
"""

import streamlit as st
from .utils import SERVICES_AVAILABLE, USERS
from .session_manager import complete_2fa_login, complete_simple_2fa_login


def show_2fa_form() -> bool:
    """顯示兩步驗證表單

    Returns:
        bool: 是否驗證成功
    """
    st.subheader("🔐 兩步驗證")
    st.info("請輸入您的驗證器應用程式中顯示的6位數驗證碼")

    with st.form("2fa_form"):
        totp_code = st.text_input(
            "驗證碼",
            max_chars=6,
            placeholder="請輸入6位數驗證碼",
            help="請使用Google Authenticator或其他TOTP應用程式",
        )

        col1, col2 = st.columns(2)
        with col1:
            verify_button = st.form_submit_button("✅ 驗證", use_container_width=True)
        with col2:
            cancel_button = st.form_submit_button("❌ 取消", use_container_width=True)

        if cancel_button:
            return _handle_2fa_cancellation()

        if verify_button:
            return _handle_2fa_verification(totp_code)

    return False


def _handle_2fa_cancellation() -> bool:
    """處理2FA取消邏輯

    Returns:
        bool: 總是返回False表示取消
    """
    st.session_state.awaiting_2fa = False
    st.session_state.temp_user_id = None
    st.session_state.temp_session_id = None
    st.rerun()
    return False


def _handle_2fa_verification(totp_code: str) -> bool:
    """處理2FA驗證邏輯

    Args:
        totp_code: 用戶輸入的驗證碼

    Returns:
        bool: 是否驗證成功
    """
    if not totp_code or len(totp_code) != 6:
        st.error("請輸入6位數驗證碼")
        return False

    # 驗證2FA
    if SERVICES_AVAILABLE and "auth_service" in st.session_state:
        return _verify_2fa_with_service(totp_code)

    return _verify_2fa_simple(totp_code)


def _verify_2fa_with_service(totp_code: str) -> bool:
    """使用服務層驗證2FA

    Args:
        totp_code: 驗證碼

    Returns:
        bool: 是否驗證成功
    """
    try:
        auth_service = st.session_state.auth_service
        user_id = st.session_state.temp_user_id
        temp_session_id = st.session_state.temp_session_id

        success, message, result = auth_service.verify_2fa_totp(
            user_id, totp_code, temp_session_id
        )

        if success:
            return complete_2fa_login(result)

        st.error(f"驗證失敗: {message}")
        return False

    except Exception as e:
        st.error(f"驗證過程發生錯誤: {e}")
        return False


def _verify_2fa_simple(totp_code: str) -> bool:
    """簡化的2FA驗證（用於測試）

    Args:
        totp_code: 驗證碼

    Returns:
        bool: 是否驗證成功
    """
    if totp_code == "123456":  # 測試用驗證碼
        user_id = st.session_state.temp_user_id

        # 從USERS中找到對應使用者
        for username, user_data in USERS.items():
            if user_data["user_id"] == user_id:
                return complete_simple_2fa_login(username, user_data)

        st.error("使用者資料錯誤")
        return False

    st.error("驗證碼錯誤，測試環境請使用: 123456")
    return False
