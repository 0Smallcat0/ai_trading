"""
API 認證模組

此模組提供 API 認證和授權的核心功能，包括用戶身份驗證、權限檢查等。
用於支援其他 API 模組的認證需求。
"""

import logging
import bcrypt
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from fastapi import HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.api.middleware.auth import TokenManager, TokenBlacklist

logger = logging.getLogger(__name__)
security = HTTPBearer()


# 模擬用戶資料庫（與 routers/auth.py 保持一致）
USERS_DB = {
    "admin": {
        "user_id": "user_001",
        "username": "admin",
        "email": "admin@trading.com",
        "password_hash": bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode(),
        "full_name": "系統管理員",
        "role": "admin",
        "is_active": True,
        "created_at": datetime(2024, 1, 1),
        "last_login": None,
    },
    "user": {
        "user_id": "user_002",
        "username": "user",
        "email": "user@trading.com",
        "password_hash": bcrypt.hashpw("user123".encode(), bcrypt.gensalt()).decode(),
        "full_name": "一般用戶",
        "role": "user",
        "is_active": True,
        "created_at": datetime(2024, 1, 15),
        "last_login": None,
    },
    "demo": {
        "user_id": "user_003",
        "username": "demo",
        "email": "demo@trading.com",
        "password_hash": bcrypt.hashpw("demo123".encode(), bcrypt.gensalt()).decode(),
        "full_name": "演示用戶",
        "role": "readonly",
        "is_active": True,
        "created_at": datetime(2024, 2, 1),
        "last_login": None,
    },
}


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    根據用戶名獲取用戶資訊。

    Args:
        username: 用戶名

    Returns:
        Optional[Dict[str, Any]]: 用戶資訊字典，如果用戶不存在則返回 None

    Note:
        實際應用中應該從資料庫查詢用戶資訊。
    """
    return USERS_DB.get(username)


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    根據郵箱獲取用戶資訊。

    Args:
        email: 郵箱地址

    Returns:
        Optional[Dict[str, Any]]: 用戶資訊字典，如果用戶不存在則返回 None
    """
    for user in USERS_DB.values():
        if user["email"] == email:
            return user
    return None


def verify_password(password: str, password_hash: str) -> bool:
    """
    驗證密碼。

    Args:
        password: 明文密碼
        password_hash: 加密後的密碼哈希

    Returns:
        bool: 密碼是否正確
    """
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def hash_password(password: str) -> str:
    """
    加密密碼。

    Args:
        password: 明文密碼

    Returns:
        str: 加密後的密碼哈希
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


class PermissionError(HTTPException):
    """權限錯誤異常"""

    def __init__(self, detail: str = "權限不足"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    獲取當前認證用戶資訊。

    Args:
        credentials: HTTP Bearer 認證憑證

    Returns:
        Dict[str, Any]: 用戶資訊字典

    Raises:
        HTTPException: 當認證失敗時拋出 401 錯誤

    Example:
        ```python
        @router.get("/protected")
        async def protected_endpoint(
            current_user: Dict[str, Any] = Depends(get_current_user)
        ):
            return {"user": current_user["username"]}
        ```
    """
    try:
        token = credentials.credentials

        # 檢查 Token 是否在黑名單中
        if TokenBlacklist.is_blacklisted(token):
            logger.warning("嘗試使用已失效的 Token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token 已失效",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 驗證 Token
        payload = TokenManager.verify_token(token)
        username = payload.get("username")

        if not username:
            logger.warning("Token 中缺少用戶名資訊")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無效的認證憑證",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 獲取用戶資訊
        user = get_user_by_username(username)
        if not user:
            logger.warning(f"用戶不存在: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用戶不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 檢查用戶是否啟用
        if not user.get("is_active", False):
            logger.warning(f"嘗試使用已停用的帳戶: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="帳戶已被停用",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 返回用戶資訊（移除敏感資訊）
        user_info = {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user.get("full_name"),
            "role": user["role"],
            "is_active": user["is_active"],
            "created_at": user["created_at"],
            "last_login": user.get("last_login"),
        }

        logger.debug(f"用戶認證成功: {username}")
        return user_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"認證過程中發生錯誤: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認證失敗",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_permissions(
    required_permissions: List[str],
    require_all: bool = True
) -> Callable:
    """
    權限檢查裝飾器。

    Args:
        required_permissions: 所需權限列表
        require_all: 是否需要所有權限（True）或任一權限（False）

    Returns:
        Callable: 裝飾器函數

    Raises:
        PermissionError: 當權限不足時拋出 403 錯誤

    Example:
        ```python
        @router.get("/admin-only")
        @require_permissions(["admin"], require_all=True)
        async def admin_endpoint(
            current_user: Dict[str, Any] = Depends(get_current_user)
        ):
            return {"message": "管理員專用端點"}
        ```
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 從參數中獲取當前用戶
            current_user = None
            for arg in args:
                if isinstance(arg, dict) and "user_id" in arg:
                    current_user = arg
                    break

            # 從關鍵字參數中獲取當前用戶
            if not current_user:
                current_user = kwargs.get("current_user")

            if not current_user:
                logger.error("權限檢查失敗: 無法獲取當前用戶資訊")
                raise PermissionError("無法驗證用戶身份")

            user_role = current_user.get("role", "")
            user_permissions = _get_role_permissions(user_role)

            # 檢查權限
            if require_all:
                # 需要所有權限
                missing_permissions = [
                    perm for perm in required_permissions
                    if perm not in user_permissions
                ]
                if missing_permissions:
                    logger.warning(
                        f"用戶 {current_user.get('username')} 缺少權限: "
                        f"{missing_permissions}"
                    )
                    raise PermissionError(
                        f"缺少必要權限: {', '.join(missing_permissions)}"
                    )
            else:
                # 需要任一權限
                has_permission = any(
                    perm in user_permissions for perm in required_permissions
                )
                if not has_permission:
                    logger.warning(
                        f"用戶 {current_user.get('username')} 沒有任何所需權限: "
                        f"{required_permissions}"
                    )
                    raise PermissionError(
                        f"需要以下任一權限: {', '.join(required_permissions)}"
                    )

            logger.debug(
                f"用戶 {current_user.get('username')} 權限檢查通過: "
                f"{required_permissions}"
            )
            return await func(*args, **kwargs)

        return wrapper
    return decorator


def _get_role_permissions(role: str) -> List[str]:
    """
    根據角色獲取權限列表。

    Args:
        role: 用戶角色

    Returns:
        List[str]: 權限列表

    Note:
        實際應用中應該從資料庫或配置文件中獲取角色權限映射。
    """
    role_permissions = {
        "admin": [
            "admin", "user_management", "system_config", "data_management",
            "strategy_management", "ai_models", "backtest", "portfolio",
            "risk_management", "trading", "monitoring", "reports", "versioning"
        ],
        "user": [
            "data_management", "strategy_management", "ai_models", "backtest",
            "portfolio", "risk_management", "trading", "monitoring", "reports"
        ],
        "readonly": [
            "backtest", "portfolio", "monitoring", "reports"
        ],
        "demo": [
            "backtest", "portfolio", "monitoring", "reports"
        ]
    }

    return role_permissions.get(role, [])


def check_user_permission(user: Dict[str, Any], permission: str) -> bool:
    """
    檢查用戶是否具有特定權限。

    Args:
        user: 用戶資訊字典
        permission: 權限名稱

    Returns:
        bool: 是否具有權限

    Example:
        ```python
        if check_user_permission(current_user, "admin"):
            # 執行管理員操作
            pass
        ```
    """
    if not user or not isinstance(user, dict):
        return False

    user_role = user.get("role", "")
    user_permissions = _get_role_permissions(user_role)

    return permission in user_permissions


def get_user_permissions(user: Dict[str, Any]) -> List[str]:
    """
    獲取用戶的所有權限。

    Args:
        user: 用戶資訊字典

    Returns:
        List[str]: 用戶權限列表

    Example:
        ```python
        permissions = get_user_permissions(current_user)
        print(f"用戶權限: {permissions}")
        ```
    """
    if not user or not isinstance(user, dict):
        return []

    user_role = user.get("role", "")
    return _get_role_permissions(user_role)
