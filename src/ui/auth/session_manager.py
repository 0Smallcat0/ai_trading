"""會話管理模組

此模組提供用戶會話狀態管理功能。
"""

import streamlit as st
import logging
from typing import Dict, Any
from .utils import USERS


def set_user_session(username: str, user_data: Dict[str, Any]) -> None:
    """設定用戶會話狀態（簡化模式）

    Args:
        username: 使用者名稱
        user_data: 用戶資料
    """
    st.session_state.authenticated = True
    st.session_state.username = username
    st.session_state.user_role = user_data["role"]
    st.session_state.user_name = user_data["name"]
    st.session_state.user_id = user_data["user_id"]
    st.session_state.email = user_data["email"]
    logging.info("用戶 %s 登入成功（簡化模式）", username)


def set_service_user_session(
    user_info: Dict[str, Any], result: Dict[str, Any]
) -> None:
    """設定用戶會話狀態（服務模式）

    Args:
        user_info: 用戶信息
        result: 認證結果
    """
    st.session_state.authenticated = True
    st.session_state.username = user_info["username"]
    roles = user_info.get("roles", [{}])
    st.session_state.user_role = roles[0].get("role_code", "user")
    st.session_state.user_name = user_info["full_name"]
    st.session_state.user_id = user_info["user_id"]
    st.session_state.email = user_info["email"]
    st.session_state.session_id = result["session_id"]
    st.session_state.jwt_token = result["jwt_token"]
    logging.info("用戶 %s 登入成功（服務模式）", user_info['username'])


def logout():
    """登出用戶"""
    if "authenticated" in st.session_state:
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.user_role = None
        st.session_state.user_name = None

    return True


def check_auth():
    """檢查用戶是否已認證

    Returns:
        bool: 是否已認證
    """
    return st.session_state.get("authenticated", False)


def get_user_role():
    """獲取當前用戶角色

    Returns:
        str: 用戶角色
    """
    return st.session_state.get("user_role", None)


def require_auth(role=None):
    """要求用戶認證的裝飾器

    Args:
        role (str, optional): 要求的最低角色級別. Defaults to None.

    Returns:
        function: 裝飾器函數
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            if not check_auth():
                # 延遲導入避免循環導入
                from .login_form import login_form  # pylint: disable=import-outside-toplevel
                login_form()
                return None

            if role is not None:
                user_role = get_user_role()
                role_levels = {"admin": 3, "user": 2, "readonly": 1}

                if role_levels.get(user_role, 0) < role_levels.get(role, 0):
                    st.error("您沒有權限執行此操作！")
                    return None

            return func(*args, **kwargs)

        return wrapper

    return decorator


def complete_2fa_login(result: Dict[str, Any]) -> bool:
    """完成服務層2FA登入

    Args:
        result: 認證結果

    Returns:
        bool: 總是返回True表示成功
    """
    # 2FA驗證成功
    st.session_state.authenticated = True
    st.session_state.username = result["username"]
    st.session_state.user_id = result["user_id"]
    st.session_state.session_id = result["session_id"]
    st.session_state.jwt_token = result["jwt_token"]
    st.session_state.awaiting_2fa = False
    st.session_state.temp_user_id = None
    st.session_state.temp_session_id = None

    # 從USERS中獲取其他資訊（臨時方案）
    for _, user_data in USERS.items():
        if user_data["user_id"] == result["user_id"]:
            st.session_state.user_role = user_data["role"]
            st.session_state.user_name = user_data["name"]
            st.session_state.email = user_data["email"]
            break

    st.success("兩步驗證成功！")
    st.rerun()
    return True


def complete_simple_2fa_login(username: str, user_data: Dict[str, Any]) -> bool:
    """完成簡化2FA登入

    Args:
        username: 用戶名
        user_data: 用戶資料

    Returns:
        bool: 總是返回True表示成功
    """
    st.session_state.authenticated = True
    st.session_state.username = username
    st.session_state.user_role = user_data["role"]
    st.session_state.user_name = user_data["name"]
    st.session_state.user_id = user_data["user_id"]
    st.session_state.email = user_data["email"]
    st.session_state.awaiting_2fa = False
    st.session_state.temp_user_id = None
    st.session_state.temp_session_id = None
    st.success("兩步驗證成功！")
    st.rerun()
    return True
