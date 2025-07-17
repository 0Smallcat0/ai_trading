"""認證服務層

此模組提供認證相關的業務邏輯，包括用戶驗證、Token 管理、會話管理等核心功能。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

try:
    import bcrypt  # pylint: disable=unused-import
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logging.warning("bcrypt 套件未安裝，將使用備用密碼驗證方法")

from src.api.middleware.auth import TokenManager, SessionManager, TokenBlacklist
from src.api.middleware.logging import audit_logger
from src.api.auth import (
    get_user_by_username,
    verify_password,
)

logger = logging.getLogger(__name__)


class AuthenticationService:
    """認證服務類
    
    提供完整的用戶認證、會話管理和安全功能。
    """

    def __init__(self) -> None:
        """初始化認證服務
        
        Raises:
            ImportError: 當必要的依賴套件未安裝時
        """
        self._validate_dependencies()

    def _validate_dependencies(self) -> None:
        """驗證必要的依賴套件
        
        Raises:
            ImportError: 當 bcrypt 套件未安裝時
        """
        if not BCRYPT_AVAILABLE:
            raise ImportError(
                "bcrypt 套件未安裝，請執行: pip install bcrypt"
            )

    def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: str
    ) -> Dict[str, Any]:
        """驗證用戶登入

        Args:
            username: 用戶名
            password: 密碼
            ip_address: 客戶端IP地址

        Returns:
            Dict[str, Any]: 認證結果，包含用戶資訊

        Raises:
            ValueError: 認證失敗時
        """
        try:
            # 檢查用戶是否存在
            user = get_user_by_username(username)
            if not user:
                self._log_failed_login(username, ip_address, "用戶名不存在")
                raise ValueError("用戶名或密碼錯誤")

            # 檢查用戶是否啟用
            if not user.get("is_active", True):
                self._log_failed_login(username, ip_address, "嘗試登入已停用帳戶")
                raise ValueError("帳戶已被停用")

            # 驗證密碼
            if not verify_password(password, user["password_hash"]):
                self._log_failed_login(username, ip_address, "密碼錯誤")
                raise ValueError("用戶名或密碼錯誤")

            # 記錄成功登入
            self._log_successful_login(user, ip_address)

            return user

        except ValueError:
            raise
        except Exception as e:
            logger.error("認證過程中發生錯誤: %s", str(e))
            raise ValueError("認證服務暫時不可用") from e

    def _log_failed_login(
        self,
        username: str,
        ip_address: str,
        reason: str
    ) -> None:
        """記錄登入失敗事件
        
        Args:
            username: 用戶名
            ip_address: IP地址
            reason: 失敗原因
        """
        try:
            audit_logger.log_security_event(
                event_type="login_failed",
                severity="medium",
                description=f"{reason}: {username}",
                user_id=None,
                details={"ip_address": ip_address}
            )
        except Exception as e:
            logger.error("記錄安全事件失敗: %s", str(e))

    def _log_successful_login(
        self,
        user: Dict[str, Any],
        ip_address: str
    ) -> None:
        """記錄成功登入事件
        
        Args:
            user: 用戶資訊
            ip_address: IP地址
        """
        try:
            audit_logger.log_user_action(
                user_id=user.get("user_id"),
                action="login",
                resource="auth",
                details={
                    "username": user.get("username"),
                    "ip_address": ip_address
                }
            )
        except Exception as e:
            logger.error("記錄用戶行為失敗: %s", str(e))

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

        Raises:
            ValueError: 會話創建失敗時
        """
        try:
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
                user_id=user["user_id"],
                token=access_token,
                device_info=device_info
            )

            # 記錄會話創建
            audit_logger.log_user_action(
                user_id=user["user_id"],
                action="session_create",
                resource="auth",
                details={
                    "username": user["username"],
                    "remember_me": remember_me,
                    "ip_address": ip_address,
                }
            )

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": "604800" if remember_me else "86400",
            }

        except Exception as e:
            logger.error("創建用戶會話失敗: %s", str(e))
            raise ValueError("會話創建失敗") from e

    @staticmethod
    def logout_user(
        token: str,
        user_id: str,
        username: str,
        ip_address: str,
    ) -> None:
        """用戶登出

        Args:
            token: 訪問令牌
            user_id: 用戶ID
            username: 用戶名
            ip_address: 客戶端IP地址

        Raises:
            ValueError: 登出失敗時
        """
        try:
            # 將 Token 加入黑名單
            TokenBlacklist.add_token(token)

            # 結束會話
            SessionManager.end_session(token)

            # 記錄登出事件
            audit_logger.log_user_action(
                user_id=user_id,
                action="logout",
                resource="auth",
                details={
                    "username": username,
                    "ip_address": ip_address,
                }
            )

        except Exception as e:
            logger.error("用戶登出失敗: %s", str(e))
            raise ValueError("登出失敗") from e

    @staticmethod
    def refresh_user_token(refresh_token: str, ip_address: str) -> Dict[str, str]:
        """刷新用戶Token

        Args:
            refresh_token: 刷新Token
            ip_address: 客戶端IP地址

        Returns:
            Dict[str, str]: 新的Token資訊

        Raises:
            ValueError: Token刷新失敗時
        """
        try:
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
                }
            )

            return {
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": "86400",
            }

        except Exception as e:
            logger.error("Token刷新失敗: %s", str(e))
            raise ValueError("Token刷新失敗") from e
