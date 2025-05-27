"""認證服務層

此模組提供認證相關的業務邏輯，包括用戶驗證、Token 管理、會話管理等核心功能。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from src.api.middleware.auth import TokenManager, SessionManager, TokenBlacklist
from src.api.middleware.logging import audit_logger
from src.api.auth import (
    get_user_by_username,
    get_user_by_email,
    hash_password,
    verify_password,
    USERS_DB,
)

logger = logging.getLogger(__name__)


class AuthenticationService:
    """認證服務類"""

    @staticmethod
    def authenticate_user(
        username: str, password: str, ip_address: str
    ) -> Dict[str, Any]:
        """驗證用戶登入

        Args:
            username: 用戶名
            password: 密碼
            ip_address: 客戶端IP地址

        Returns:
            Dict[str, Any]: 認證結果

        Raises:
            ValueError: 認證失敗
        """
        # 檢查用戶是否存在
        user = get_user_by_username(username)
        if not user:
            audit_logger.log_security_event(
                event_type="login_failed",
                severity="medium",
                description=f"用戶名不存在: {username}",
                details={"ip_address": ip_address},
            )
            raise ValueError("用戶名或密碼錯誤")

        # 檢查用戶是否啟用
        if not user["is_active"]:
            audit_logger.log_security_event(
                event_type="login_failed",
                severity="medium",
                description=f"嘗試登入已停用帳戶: {username}",
                details={"ip_address": ip_address},
            )
            raise ValueError("帳戶已被停用")

        # 驗證密碼
        if not verify_password(password, user["password_hash"]):
            audit_logger.log_security_event(
                event_type="login_failed",
                severity="medium",
                description=f"密碼錯誤: {username}",
                user_id=user["user_id"],
                details={"ip_address": ip_address},
            )
            raise ValueError("用戶名或密碼錯誤")

        return user

    @staticmethod
    def create_user_session(
        user: Dict[str, Any],
        remember_me: bool,
        device_info: Dict[str, Any],
        ip_address: str,
    ) -> Dict[str, str]:
        """創建用戶會話

        Args:
            user: 用戶資訊
            remember_me: 是否記住登入
            device_info: 設備資訊
            ip_address: 客戶端IP地址

        Returns:
            Dict[str, str]: Token 資訊
        """
        # 更新最後登入時間
        user["last_login"] = datetime.now()

        # 生成 Token
        expires_delta = timedelta(days=7) if remember_me else None

        access_token = TokenManager.create_access_token(
            user_id=user["user_id"],
            username=user["username"],
            role=user["role"],
            expires_delta=expires_delta,
        )
        refresh_token = TokenManager.create_refresh_token(
            user_id=user["user_id"],
            username=user["username"],
        )

        # 創建會話
        SessionManager.create_session(
            user_id=user["user_id"], token=access_token, device_info=device_info
        )

        # 記錄審計日誌
        audit_logger.log_user_action(
            user_id=user["user_id"],
            action="login",
            resource="auth",
            details={
                "username": user["username"],
                "role": user["role"],
                "remember_me": remember_me,
                "ip_address": ip_address,
            },
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": "86400" if not remember_me else "604800",
        }

    @staticmethod
    def logout_user(token: str, user_id: str, username: str, ip_address: str) -> None:
        """用戶登出

        Args:
            token: 訪問Token
            user_id: 用戶ID
            username: 用戶名
            ip_address: 客戶端IP地址
        """
        # 將 Token 加入黑名單
        TokenBlacklist.add_token(token)

        # 結束會話
        SessionManager.end_session(token)

        # 記錄審計日誌
        audit_logger.log_user_action(
            user_id=user_id,
            action="logout",
            resource="auth",
            details={
                "username": username,
                "ip_address": ip_address,
            },
        )

    @staticmethod
    def refresh_user_token(refresh_token: str, ip_address: str) -> Dict[str, str]:
        """刷新用戶Token

        Args:
            refresh_token: 刷新Token
            ip_address: 客戶端IP地址

        Returns:
            Dict[str, str]: 新的Token資訊
        """
        # 驗證刷新 Token
        new_access_token = TokenManager.refresh_access_token(refresh_token)

        # 解析 Token 獲取用戶資訊
        payload = TokenManager.verify_token(new_access_token)

        # 記錄審計日誌
        audit_logger.log_user_action(
            user_id=payload.get("user_id"),
            action="token_refresh",
            resource="auth",
            details={
                "username": payload.get("username"),
                "ip_address": ip_address,
            },
        )

        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": "86400",
        }

    @staticmethod
    def register_user(
        username: str,
        email: str,
        password: str,
        confirm_password: str,
        *,
        full_name: str,
        role: Optional[str],
        ip_address: str,
    ) -> Dict[str, Any]:
        """註冊新用戶

        Args:
            username: 用戶名
            email: 郵箱
            password: 密碼
            confirm_password: 確認密碼
            full_name: 全名
            role: 角色
            ip_address: 客戶端IP地址

        Returns:
            Dict[str, Any]: 新用戶資訊

        Raises:
            ValueError: 註冊失敗
        """
        # 驗證密碼確認
        if password != confirm_password:
            raise ValueError("密碼確認不一致")

        # 檢查用戶名是否已存在
        if get_user_by_username(username):
            raise ValueError("用戶名已存在")

        # 檢查郵箱是否已存在
        if get_user_by_email(email):
            raise ValueError("郵箱已被使用")

        # 創建新用戶
        user_id = f"user_{len(USERS_DB) + 1:03d}"
        password_hash = hash_password(password)

        new_user = {
            "user_id": user_id,
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "full_name": full_name,
            "role": role if role in ["user", "readonly"] else "user",
            "is_active": True,
            "created_at": datetime.now(),
            "last_login": None,
        }

        # 保存用戶
        USERS_DB[username] = new_user

        # 記錄審計日誌
        audit_logger.log_user_action(
            user_id=user_id,
            action="register",
            resource="auth",
            details={
                "username": username,
                "email": email,
                "role": new_user["role"],
                "ip_address": ip_address,
            },
        )

        return new_user

    @staticmethod
    def get_user_info(username: str) -> Optional[Dict[str, Any]]:
        """獲取用戶資訊

        Args:
            username: 用戶名

        Returns:
            Optional[Dict[str, Any]]: 用戶資訊
        """
        return get_user_by_username(username)
