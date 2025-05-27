"""認證中間件

此模組實現了 JWT Token 認證中間件，提供安全的 API 訪問控制。
包含 Token 驗證、用戶身份識別、權限檢查等功能。
"""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging
import os

logger = logging.getLogger(__name__)

# JWT 配置 - 從環境變數讀取，提供安全的預設值
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY",
    "dev-secret-key-change-in-production"  # 開發環境預設值，生產環境必須設定
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

# 檢查生產環境是否使用了不安全的預設密鑰
if (JWT_SECRET_KEY == "dev-secret-key-change-in-production" and
    os.getenv("ENVIRONMENT") == "production"):
    logger.error("⚠️  生產環境使用了不安全的預設 JWT 密鑰，請設定 JWT_SECRET_KEY 環境變數")
    raise ValueError("生產環境必須設定安全的 JWT_SECRET_KEY")


class AuthMiddleware(BaseHTTPMiddleware):
    """認證中間件"""

    def __init__(self, app):
        super().__init__(app)
        self.security = HTTPBearer()

        # 不需要認證的路徑
        self.public_paths = {
            "/",
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/info",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
        }

    async def dispatch(self, request: Request, call_next):
        """處理請求認證"""
        # 檢查是否為公開路徑
        if request.url.path in self.public_paths:
            return await call_next(request)

        # 檢查是否為靜態資源
        if request.url.path.startswith("/static/"):
            return await call_next(request)

        # 獲取 Authorization 標頭
        authorization = request.headers.get("Authorization")

        if not authorization:
            return self._unauthorized_response("缺少 Authorization 標頭")

        # 驗證 Bearer Token 格式
        if not authorization.startswith("Bearer "):
            return self._unauthorized_response("無效的 Authorization 格式")

        # 提取 Token
        token = authorization.split(" ")[1]

        # 檢查 Token 是否在黑名單中
        if TokenBlacklist.is_blacklisted(token):
            return self._unauthorized_response("Token 已失效")

        # 驗證 Token
        try:
            logger.debug("驗證 Token: %s...", token[:20])
            payload = self._verify_token(token)
            logger.debug("Token 驗證成功，用戶: %s", payload.get('username'))

            # 將用戶資訊添加到請求狀態
            request.state.user = payload
            request.state.user_id = payload.get("user_id")
            request.state.username = payload.get("username")
            request.state.role = payload.get("role")

        except HTTPException as e:
            logger.warning("Token 驗證失敗 (HTTPException): %s", e.detail)
            return self._unauthorized_response(e.detail)
        except Exception as e:
            logger.error("Token 驗證錯誤: %s", e)
            return self._unauthorized_response("Token 驗證失敗")

        # 繼續處理請求
        response = await call_next(request)
        return response

    def _verify_token(self, token: str) -> Dict[str, Any]:
        """驗證 JWT Token"""
        try:
            # 解碼 Token
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

            # 檢查過期時間
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.now():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 已過期"
                )

            # 檢查必要欄位
            required_fields = ["user_id", "username", "role"]
            for field in required_fields:
                if field not in payload:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Token 缺少必要欄位: {field}",
                    )

            return payload

        except jwt.ExpiredSignatureError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 已過期"
            ) from e
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="無效的 Token"
            ) from e

    def _unauthorized_response(self, message: str) -> JSONResponse:
        """返回未授權響應"""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "success": False,
                "error_code": 401,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            },
        )


class TokenManager:
    """Token 管理器"""

    @staticmethod
    def create_access_token(
        user_id: str,
        username: str,
        role: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """創建訪問 Token"""
        if expires_delta:
            expire = datetime.now() + expires_delta
        else:
            expire = datetime.now() + timedelta(hours=JWT_EXPIRATION_HOURS)

        payload = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "exp": int(expire.timestamp()),
            "iat": int(datetime.now().timestamp()),
            "type": "access",
        }

        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def create_refresh_token(
        user_id: str, username: str, expires_delta: Optional[timedelta] = None
    ) -> str:
        """創建刷新 Token"""
        if expires_delta:
            expire = datetime.now() + expires_delta
        else:
            expire = datetime.now() + timedelta(days=30)  # 刷新 Token 有效期 30 天

        payload = {
            "user_id": user_id,
            "username": username,
            "exp": int(expire.timestamp()),
            "iat": int(datetime.now().timestamp()),
            "type": "refresh",
        }

        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """驗證 Token"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 已過期"
            ) from e
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="無效的 Token"
            ) from e

    @staticmethod
    def refresh_access_token(refresh_token: str) -> str:
        """使用刷新 Token 獲取新的訪問 Token"""
        try:
            payload = TokenManager.verify_token(refresh_token)

            # 檢查是否為刷新 Token
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="無效的刷新 Token"
                )

            # 創建新的訪問 Token
            # 注意：這裡需要從資料庫獲取最新的用戶角色資訊
            user_id = payload.get("user_id")
            username = payload.get("username")

            # 模擬從資料庫獲取用戶角色
            role = "user"  # 實際應該從資料庫查詢

            return TokenManager.create_access_token(user_id, username, role)

        except Exception as e:
            logger.error("刷新 Token 錯誤: %s", e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 刷新失敗"
            ) from e


class PermissionChecker:
    """權限檢查器"""

    # 角色權限映射
    ROLE_PERMISSIONS = {
        "admin": [
            "user_management",
            "role_management",
            "system_config",
            "data_management",
            "strategy_management",
            "trading",
            "monitoring",
            "reports",
            "api_access",
        ],
        "user": [
            "data_management",
            "strategy_management",
            "trading",
            "monitoring",
            "reports",
        ],
        "readonly": ["monitoring", "reports"],
    }

    @classmethod
    def has_permission(cls, role: str, permission: str) -> bool:
        """檢查角色是否有指定權限"""
        role_permissions = cls.ROLE_PERMISSIONS.get(role, [])
        return permission in role_permissions

    @classmethod
    def require_permission(cls, permission: str):
        """權限裝飾器"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                # 從請求中獲取用戶角色
                # 這裡需要根據實際的請求處理方式來實現
                user_role = kwargs.get("current_user", {}).get("role")

                if not cls.has_permission(user_role, permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"權限不足，需要 {permission} 權限",
                    )

                return func(*args, **kwargs)

            return wrapper

        return decorator

    @classmethod
    def require_role(cls, required_role: str):
        """角色要求裝飾器"""

        def decorator(func):
            def wrapper(*args, **kwargs):
                user_role = kwargs.get("current_user", {}).get("role")

                # 角色等級檢查
                role_levels = {"admin": 3, "user": 2, "readonly": 1}
                required_level = role_levels.get(required_role, 0)
                user_level = role_levels.get(user_role, 0)

                if user_level < required_level:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"權限不足，需要 {required_role} 或更高角色",
                    )

                return func(*args, **kwargs)

            return wrapper

        return decorator


# Token 黑名單管理（簡化版本，實際應該使用 Redis）
class TokenBlacklist:
    """Token 黑名單管理"""

    _blacklist = set()

    @classmethod
    def add_token(cls, token: str):
        """添加 Token 到黑名單"""
        cls._blacklist.add(token)

    @classmethod
    def is_blacklisted(cls, token: str) -> bool:
        """檢查 Token 是否在黑名單中"""
        return token in cls._blacklist

    @classmethod
    def remove_token(cls, token: str):
        """從黑名單移除 Token"""
        cls._blacklist.discard(token)

    @classmethod
    def clear_expired_tokens(cls):
        """清理過期的 Token（定期任務）"""
        # 實際實現中應該檢查 Token 的過期時間
        # 這裡簡化處理
        logger.info("清理過期 Token 任務執行（簡化版本）")


# 用戶會話管理
class SessionManager:
    """用戶會話管理"""

    _active_sessions = {}  # 實際應該使用 Redis

    @classmethod
    def create_session(cls, user_id: str, token: str, device_info: Dict[str, Any]):
        """創建用戶會話"""
        session_data = {
            "user_id": user_id,
            "token": token,
            "device_info": device_info,
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
        }

        cls._active_sessions[token] = session_data

    @classmethod
    def update_activity(cls, token: str):
        """更新會話活動時間"""
        if token in cls._active_sessions:
            cls._active_sessions[token]["last_activity"] = datetime.now()

    @classmethod
    def end_session(cls, token: str):
        """結束會話"""
        cls._active_sessions.pop(token, None)
        TokenBlacklist.add_token(token)

    @classmethod
    def get_user_sessions(cls, user_id: str) -> List[Dict[str, Any]]:
        """獲取用戶的所有會話"""
        return [
            session
            for session in cls._active_sessions.values()
            if session["user_id"] == user_id
        ]

    @classmethod
    def end_all_user_sessions(cls, user_id: str):
        """結束用戶的所有會話"""
        tokens_to_remove = [
            token
            for token, session in cls._active_sessions.items()
            if session["user_id"] == user_id
        ]

        for token in tokens_to_remove:
            cls.end_session(token)
