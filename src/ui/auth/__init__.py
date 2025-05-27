"""認證模組

此模組提供用戶認證相關的功能，包括登入、登出、2FA驗證等。

主要組件：
- login_form: 登入表單
- two_factor: 兩步驗證
- session_manager: 會話管理
- utils: 認證工具函數

Example:
    使用認證模組：
    ```python
    from src.ui.auth import login_form, check_auth

    if not check_auth():
        login_form()
    else:
        st.write("已登入")
    ```
"""

# 延遲導入避免 Streamlit 依賴問題
from .utils import USERS, SERVICES_AVAILABLE


def login_form(*args, **kwargs):
    """延遲導入登入表單"""
    # pylint: disable=import-outside-toplevel
    from .login_form import login_form as _login_form

    return _login_form(*args, **kwargs)


def show_2fa_form(*args, **kwargs):
    """延遲導入兩步驗證表單"""
    # pylint: disable=import-outside-toplevel
    from .two_factor import show_2fa_form as _show_2fa_form

    return _show_2fa_form(*args, **kwargs)


def check_auth(*args, **kwargs):
    """延遲導入認證檢查"""
    # pylint: disable=import-outside-toplevel
    from .session_manager import check_auth as _check_auth

    return _check_auth(*args, **kwargs)


def get_user_role(*args, **kwargs):
    """延遲導入用戶角色獲取"""
    # pylint: disable=import-outside-toplevel
    from .session_manager import get_user_role as _get_user_role

    return _get_user_role(*args, **kwargs)


def logout(*args, **kwargs):
    """延遲導入登出功能"""
    # pylint: disable=import-outside-toplevel
    from .session_manager import logout as _logout

    return _logout(*args, **kwargs)


def require_auth(*args, **kwargs):
    """延遲導入認證裝飾器"""
    # pylint: disable=import-outside-toplevel
    from .session_manager import require_auth as _require_auth

    return _require_auth(*args, **kwargs)


__all__ = [
    "login_form",
    "show_2fa_form",
    "check_auth",
    "get_user_role",
    "logout",
    "require_auth",
    "USERS",
    "SERVICES_AVAILABLE",
]
