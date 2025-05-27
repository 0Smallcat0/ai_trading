"""安全工具模組

此模組提供 API 安全相關的工具函數，包括 Token 驗證、用戶認證、權限檢查等功能。
"""

import re
import uuid
from typing import Dict, Any, Optional, Callable, Tuple
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from src.api.middleware.auth import TokenManager, TokenBlacklist, PermissionChecker

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """驗證 JWT Token

    Args:
        credentials: HTTP Bearer 認證憑證

    Returns:
        Dict[str, Any]: Token 載荷資料

    Raises:
        HTTPException: Token 無效或過期
    """
    try:
        token = credentials.credentials

        # 檢查 Token 是否在黑名單中
        if TokenBlacklist.is_blacklisted(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 已失效"
            )

        # 驗證 Token
        payload = TokenManager.verify_token(token)

        return payload

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token 驗證錯誤: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 驗證失敗"
        ) from e


async def get_current_user(
    token_payload: Dict[str, Any] = Depends(verify_token)
) -> Dict[str, Any]:
    """獲取當前用戶資訊

    Args:
        token_payload: Token 載荷資料

    Returns:
        Dict[str, Any]: 用戶資訊
    """
    return {
        "user_id": token_payload.get("user_id"),
        "username": token_payload.get("username"),
        "role": token_payload.get("role"),
    }


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """獲取當前活躍用戶

    Args:
        current_user: 當前用戶資訊

    Returns:
        Dict[str, Any]: 活躍用戶資訊

    Raises:
        HTTPException: 用戶未啟用
    """
    # 這裡應該從資料庫檢查用戶狀態
    # 簡化實現，假設所有用戶都是活躍的
    if not current_user.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用戶未認證"
        )

    return current_user


def require_permission(permission: str) -> Callable:
    """權限要求裝飾器

    Args:
        permission: 所需權限

    Returns:
        Callable: 裝飾器函數
    """

    async def permission_checker(
        current_user: Dict[str, Any] = Depends(get_current_user)
    ):
        user_role = current_user.get("role")

        if not PermissionChecker.has_permission(user_role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"權限不足，需要 {permission} 權限",
            )

        return current_user

    return permission_checker


def require_role(required_role: str) -> Callable:
    """角色要求裝飾器

    Args:
        required_role: 所需角色

    Returns:
        Callable: 裝飾器函數
    """

    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_role = current_user.get("role")

        # 角色等級檢查
        role_levels = {"admin": 3, "user": 2, "readonly": 1}
        required_level = role_levels.get(required_role, 0)
        user_level = role_levels.get(user_role, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"權限不足，需要 {required_role} 或更高角色",
            )

        return current_user

    return role_checker


def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """要求管理員權限

    Args:
        current_user: 當前用戶

    Returns:
        Dict[str, Any]: 用戶資訊

    Raises:
        HTTPException: 非管理員用戶
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要管理員權限"
        )

    return current_user


def get_client_ip(request: Request) -> str:
    """獲取客戶端 IP 地址

    Args:
        request: FastAPI 請求對象

    Returns:
        str: 客戶端 IP 地址
    """
    # 檢查代理標頭
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # 使用直接連接 IP
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """獲取用戶代理字串

    Args:
        request: FastAPI 請求對象

    Returns:
        str: 用戶代理字串
    """
    return request.headers.get("user-agent", "unknown")


def validate_api_key(api_key: str) -> bool:
    """驗證 API 金鑰

    Args:
        api_key: API 金鑰

    Returns:
        bool: 是否有效
    """
    # 這裡應該從資料庫或配置中驗證 API 金鑰
    # 簡化實現
    valid_api_keys = {"ak_live_1234567890", "ak_test_0987654321", "ak_demo_1111111111"}

    return api_key in valid_api_keys


def check_rate_limit(_user_id: str, _endpoint: str) -> bool:
    """檢查速率限制

    Note:
        參數使用下劃線前綴表示未使用，這是簡化實現

    Returns:
        bool: 是否允許請求
    """
    # 這裡應該實現具體的速率限制邏輯
    # 簡化實現，總是返回 True
    return True


class SecurityHeaders:
    """安全標頭管理"""

    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """獲取安全標頭

        Returns:
            Dict[str, str]: 安全標頭字典
        """
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

    @staticmethod
    def add_security_headers(response: Any):
        """添加安全標頭到響應

        Args:
            response (Any): FastAPI 響應對象
        """
        headers = SecurityHeaders.get_security_headers()
        for key, value in headers.items():
            response.headers[key] = value


class InputValidator:
    """輸入驗證器"""

    @staticmethod
    def validate_username(username: str) -> bool:
        """驗證用戶名

        Args:
            username: 用戶名

        Returns:
            bool: 是否有效
        """
        if not username or len(username) < 3 or len(username) > 50:
            return False

        # 檢查是否包含非法字符
        pattern = r"^[a-zA-Z0-9_-]+$"
        return bool(re.match(pattern, username))

    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """驗證密碼強度

        Args:
            password: 密碼

        Returns:
            Tuple[bool, str]: (是否有效, 錯誤訊息)
        """
        if not password:
            return False, "密碼不能為空"

        if len(password) < 6:
            return False, "密碼長度至少 6 個字符"

        if len(password) > 100:
            return False, "密碼長度不能超過 100 個字符"

        # 檢查是否包含數字和字母
        if not re.search(r"[a-zA-Z]", password):
            return False, "密碼必須包含字母"

        if not re.search(r"[0-9]", password):
            return False, "密碼必須包含數字"

        return True, ""

    @staticmethod
    def validate_email(email: str) -> bool:
        """驗證郵箱格式

        Args:
            email: 郵箱地址

        Returns:
            bool: 是否有效
        """
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))


class SessionSecurity:
    """會話安全管理"""

    @staticmethod
    def generate_session_id() -> str:
        """生成會話 ID

        Returns:
            str: 會話 ID
        """
        return str(uuid.uuid4())

    @staticmethod
    def validate_session(_session_id: str, _user_id: str) -> bool:
        """驗證會話

        Note:
            參數使用下劃線前綴表示未使用，這是簡化實現

        Returns:
            bool: 會話是否有效
        """
        # 這裡應該從會話存儲中驗證
        # 簡化實現
        return True

    @staticmethod
    def invalidate_session(_session_id: str):
        """使會話失效

        Note:
            參數使用下劃線前綴表示未使用，這是簡化實現
        """
        # 這裡應該從會話存儲中移除


class AuditLogger:
    """審計日誌記錄"""

    @staticmethod
    def log_authentication_event(
        event_type: str,
        user_id: Optional[str],
        *,
        ip_address: str,
        user_agent: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
    ):
        """記錄認證事件

        Args:
            event_type: 事件類型
            user_id: 用戶 ID
            ip_address: IP 地址
            user_agent: 用戶代理
            success: 是否成功
            details: 詳細資訊
        """
        # Note: This would normally import and use the audit logger
        # For now, we'll use the standard logger
        logger.info(
            "認證事件: %s, 用戶: %s, IP: %s, 代理: %s, 成功: %s, 詳情: %s",
            event_type,
            user_id,
            ip_address,
            user_agent,
            success,
            details,
        )

    @staticmethod
    def log_authorization_event(
        user_id: str, resource: str, action: str, granted: bool, ip_address: str
    ):
        """記錄授權事件

        Args:
            user_id: 用戶 ID
            resource: 資源
            action: 操作
            granted: 是否授權
            ip_address: IP 地址
        """
        # Note: This would normally import and use the audit logger
        # For now, we'll use the standard logger
        logger.info(
            "授權事件: 用戶 %s 對資源 %s 執行 %s, 授權: %s, IP: %s",
            user_id,
            resource,
            action,
            granted,
            ip_address,
        )
