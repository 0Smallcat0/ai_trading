"""
Web UI 認證組件模組

此模組提供 Web UI 的認證相關組件，包括：
- 用戶認證檢查
- 登入表單顯示
- 權限驗證

主要功能：
- 實現用戶身份驗證流程
- 提供登入介面組件
- 管理用戶會話狀態
- 處理權限檢查邏輯

Example:
    >>> from src.ui.components.auth_component import check_auth, show_login
    >>> authenticated, user_role = check_auth()
    >>> if not authenticated:
    ...     show_login()
"""

import logging
from typing import Tuple, Optional

import streamlit as st

logger = logging.getLogger(__name__)


def check_auth() -> Tuple[bool, str]:
    """檢查用戶認證狀態.

    Returns:
        Tuple[bool, str]: (是否已認證, 用戶角色)

    Example:
        >>> authenticated, role = check_auth()
        >>> if authenticated:
        ...     print(f"用戶角色: {role}")
    """
    try:
        # 檢查 session state 中的認證狀態
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
            st.session_state.user_role = ""

        authenticated = st.session_state.get("authenticated", False)
        user_role = st.session_state.get("user_role", "")

        logger.debug("認證檢查 - 已認證: %s, 角色: %s", authenticated, user_role)
        return authenticated, user_role

    except Exception as e:
        logger.error("認證檢查時發生錯誤: %s", e, exc_info=True)
        return False, ""


def show_login() -> None:
    """顯示登入表單.

    Note:
        此函數會修改 st.session_state 中的認證狀態

    Example:
        >>> show_login()  # 顯示登入表單
    """
    try:
        st.title("🔐 AI 股票自動交易系統")
        st.markdown("---")

        # 創建登入表單
        with st.form("login_form"):
            st.subheader("用戶登入")
            
            username = st.text_input("用戶名", placeholder="請輸入用戶名")
            password = st.text_input("密碼", type="password", placeholder="請輸入密碼")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                remember_me = st.checkbox("記住我")
            with col2:
                submit_button = st.form_submit_button("登入", use_container_width=True)

            if submit_button:
                if _authenticate_user(username, password):
                    st.success("登入成功！")
                    st.rerun()
                else:
                    st.error("用戶名或密碼錯誤")

        # 顯示示範帳戶資訊
        _show_demo_accounts()

    except Exception as e:
        logger.error("顯示登入表單時發生錯誤: %s", e, exc_info=True)
        st.error("登入系統發生錯誤，請重新整理頁面")


def _authenticate_user(username: str, password: str) -> bool:
    """驗證用戶身份.

    Args:
        username: 用戶名
        password: 密碼

    Returns:
        bool: 是否驗證成功

    Example:
        >>> success = _authenticate_user("admin", "admin123")
        >>> print(success)
        True
    """
    try:
        # 簡化的認證邏輯（實際應用中應該調用 API）
        valid_users = {
            "admin": {"password": "admin123", "role": "admin"},
            "trader": {"password": "trader123", "role": "trader"},
            "analyst": {"password": "analyst123", "role": "analyst"},
            "demo": {"password": "demo123", "role": "demo"}
        }

        if username in valid_users and valid_users[username]["password"] == password:
            # 設定認證狀態
            st.session_state.authenticated = True
            st.session_state.user_role = valid_users[username]["role"]
            st.session_state.username = username
            
            logger.info("用戶 %s 登入成功，角色: %s", username, valid_users[username]["role"])
            return True
        else:
            logger.warning("用戶 %s 登入失敗", username)
            return False

    except Exception as e:
        logger.error("用戶認證時發生錯誤: %s", e, exc_info=True)
        return False


def _show_demo_accounts() -> None:
    """顯示示範帳戶資訊.

    Example:
        >>> _show_demo_accounts()  # 顯示示範帳戶列表
    """
    try:
        st.markdown("---")
        st.subheader("📋 示範帳戶")
        
        demo_accounts = [
            {"username": "admin", "password": "admin123", "role": "系統管理員", "desc": "完整系統權限"},
            {"username": "trader", "password": "trader123", "role": "交易員", "desc": "交易執行權限"},
            {"username": "analyst", "password": "analyst123", "role": "分析師", "desc": "數據分析權限"},
            {"username": "demo", "password": "demo123", "role": "示範用戶", "desc": "只讀權限"}
        ]

        for account in demo_accounts:
            with st.expander(f"👤 {account['role']} ({account['username']})"):
                col1, col2 = st.columns([1, 2])
                with col1:
                    st.write(f"**用戶名**: {account['username']}")
                    st.write(f"**密碼**: {account['password']}")
                with col2:
                    st.write(f"**角色**: {account['role']}")
                    st.write(f"**權限**: {account['desc']}")

    except Exception as e:
        logger.error("顯示示範帳戶時發生錯誤: %s", e, exc_info=True)


def logout_user() -> None:
    """登出用戶.

    Note:
        清除 session state 中的認證資訊

    Example:
        >>> logout_user()  # 登出當前用戶
    """
    try:
        # 清除認證狀態
        st.session_state.authenticated = False
        st.session_state.user_role = ""
        st.session_state.username = ""
        
        # 清除其他可能的用戶相關狀態
        keys_to_clear = [key for key in st.session_state.keys() 
                        if key.startswith(('user_', 'auth_', 'session_'))]
        
        for key in keys_to_clear:
            del st.session_state[key]
        
        logger.info("用戶已登出")
        st.success("已成功登出")
        st.rerun()

    except Exception as e:
        logger.error("用戶登出時發生錯誤: %s", e, exc_info=True)
        st.error("登出時發生錯誤")


def get_current_user_info() -> Optional[dict]:
    """獲取當前用戶資訊.

    Returns:
        Optional[dict]: 用戶資訊字典，如果未認證則返回 None

    Example:
        >>> user_info = get_current_user_info()
        >>> if user_info:
        ...     print(f"當前用戶: {user_info['username']}")
    """
    try:
        if not st.session_state.get("authenticated", False):
            return None

        return {
            "username": st.session_state.get("username", ""),
            "role": st.session_state.get("user_role", ""),
            "authenticated": st.session_state.get("authenticated", False)
        }

    except Exception as e:
        logger.error("獲取用戶資訊時發生錯誤: %s", e, exc_info=True)
        return None


def check_user_permission(required_role: str) -> bool:
    """檢查用戶是否具有指定角色權限.

    Args:
        required_role: 所需的角色

    Returns:
        bool: 是否具有權限

    Example:
        >>> has_admin = check_user_permission("admin")
        >>> if has_admin:
        ...     print("用戶具有管理員權限")
    """
    try:
        authenticated, user_role = check_auth()
        
        if not authenticated:
            return False

        # 角色權限層級
        role_hierarchy = {
            "admin": 4,
            "trader": 3,
            "analyst": 2,
            "demo": 1,
            "viewer": 1
        }

        user_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        return user_level >= required_level

    except Exception as e:
        logger.error("檢查用戶權限時發生錯誤: %s", e, exc_info=True)
        return False


def require_auth(func):
    """認證裝飾器.

    Args:
        func: 需要認證的函數

    Returns:
        裝飾後的函數

    Example:
        >>> @require_auth
        ... def protected_function():
        ...     return "Protected content"
    """
    def wrapper(*args, **kwargs):
        authenticated, _ = check_auth()
        if not authenticated:
            st.warning("請先登入以訪問此功能")
            show_login()
            return None
        return func(*args, **kwargs)
    
    return wrapper


def require_role(required_role: str):
    """角色權限裝飾器.

    Args:
        required_role: 所需角色

    Returns:
        裝飾器函數

    Example:
        >>> @require_role("admin")
        ... def admin_only_function():
        ...     return "Admin only content"
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not check_user_permission(required_role):
                st.error(f"此功能需要 {required_role} 權限")
                return None
            return func(*args, **kwargs)
        return wrapper
    return decorator
