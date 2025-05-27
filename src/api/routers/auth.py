"""認證路由

此模組實現了用戶認證相關的 API 端點，包括登入、登出、註冊、Token 刷新等功能。
提供完整的 JWT 認證機制和用戶管理功能。
"""

from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
import logging

from src.api.models.responses import APIResponse, COMMON_RESPONSES
from src.api.middleware.auth import TokenManager
from src.core.authentication_service import AuthenticationService
from src.api.utils.security import get_client_ip

logger = logging.getLogger(__name__)
security = HTTPBearer()

# 創建路由器
router = APIRouter()


# 請求模型
class LoginRequest(BaseModel):
    """登入請求模型"""

    username: str = Field(..., min_length=3, max_length=50, description="用戶名")
    password: str = Field(..., min_length=6, max_length=100, description="密碼")
    remember_me: bool = Field(default=False, description="記住我")
    device_info: Optional[Dict[str, str]] = Field(default=None, description="設備資訊")


class RegisterRequest(BaseModel):
    """註冊請求模型"""

    username: str = Field(..., min_length=3, max_length=50, description="用戶名")
    email: EmailStr = Field(..., description="郵箱地址")
    password: str = Field(..., min_length=6, max_length=100, description="密碼")
    confirm_password: str = Field(
        ..., min_length=6, max_length=100, description="確認密碼"
    )
    full_name: Optional[str] = Field(default=None, max_length=100, description="全名")
    role: Optional[str] = Field(default="user", description="用戶角色")


class RefreshTokenRequest(BaseModel):
    """刷新 Token 請求模型"""

    refresh_token: str = Field(..., description="刷新 Token")


class ChangePasswordRequest(BaseModel):
    """修改密碼請求模型"""

    current_password: str = Field(..., description="當前密碼")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密碼")
    confirm_password: str = Field(
        ..., min_length=6, max_length=100, description="確認新密碼"
    )


class ResetPasswordRequest(BaseModel):
    """重置密碼請求模型"""

    email: EmailStr = Field(..., description="郵箱地址")


class ResetPasswordConfirmRequest(BaseModel):
    """確認重置密碼請求模型"""

    token: str = Field(..., description="重置 Token")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密碼")
    confirm_password: str = Field(
        ..., min_length=6, max_length=100, description="確認新密碼"
    )


# 響應模型
class LoginResponse(BaseModel):
    """登入響應模型"""

    access_token: str = Field(..., description="訪問 Token")
    refresh_token: str = Field(..., description="刷新 Token")
    token_type: str = Field(default="bearer", description="Token 類型")
    expires_in: int = Field(..., description="過期時間（秒）")
    user_info: Dict[str, Any] = Field(..., description="用戶資訊")


class UserInfo(BaseModel):
    """用戶資訊模型"""

    user_id: str = Field(..., description="用戶 ID")
    username: str = Field(..., description="用戶名")
    email: str = Field(..., description="郵箱")
    full_name: Optional[str] = Field(default=None, description="全名")
    role: str = Field(..., description="角色")
    is_active: bool = Field(..., description="是否啟用")
    created_at: datetime = Field(..., description="創建時間")
    last_login: Optional[datetime] = Field(default=None, description="最後登入時間")


@router.post(
    "/login",
    response_model=APIResponse[LoginResponse],
    responses=COMMON_RESPONSES,
    summary="用戶登入",
    description="使用用戶名和密碼進行登入，返回 JWT Token",
)
async def login(request: Request, login_data: LoginRequest):
    """用戶登入"""
    try:
        ip_address = get_client_ip(request)

        # 驗證用戶
        user = AuthenticationService.authenticate_user(
            username=login_data.username,
            password=login_data.password,
            ip_address=ip_address,
        )

        # 創建會話
        device_info = login_data.device_info or {
            "user_agent": request.headers.get("user-agent", ""),
            "ip_address": ip_address,
        }

        token_data = AuthenticationService.create_user_session(
            user=user,
            remember_me=login_data.remember_me,
            device_info=device_info,
            ip_address=ip_address,
        )

        # 準備響應
        login_response = LoginResponse(
            access_token=token_data["access_token"],
            refresh_token=token_data["refresh_token"],
            token_type=token_data["token_type"],
            expires_in=int(token_data["expires_in"]),
            user_info={
                "user_id": user["user_id"],
                "username": user["username"],
                "email": user["email"],
                "full_name": user["full_name"],
                "role": user["role"],
                "is_active": user["is_active"],
                "last_login": (
                    user["last_login"].isoformat() if user["last_login"] else None
                ),
            },
        )

        return APIResponse(success=True, message="登入成功", data=login_response)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)
        ) from e
    except Exception as e:
        logger.error("登入錯誤: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登入過程中發生錯誤",
        ) from e


@router.post(
    "/logout",
    response_model=APIResponse,
    responses=COMMON_RESPONSES,
    summary="用戶登出",
    description="登出當前用戶，使 Token 失效",
)
async def logout(
    request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """用戶登出"""
    try:
        token = credentials.credentials
        ip_address = get_client_ip(request)

        # 驗證 Token
        payload = TokenManager.verify_token(token)
        user_id = payload.get("user_id")
        username = payload.get("username")

        # 執行登出
        AuthenticationService.logout_user(
            token=token,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
        )

        return APIResponse(success=True, message="登出成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("登出錯誤: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登出過程中發生錯誤",
        ) from e


@router.post(
    "/refresh",
    response_model=APIResponse[Dict[str, str]],
    responses=COMMON_RESPONSES,
    summary="刷新 Token",
    description="使用刷新 Token 獲取新的訪問 Token",
)
async def refresh_token(request: Request, refresh_data: RefreshTokenRequest):
    """刷新 Token"""
    try:
        ip_address = get_client_ip(request)

        # 刷新 Token
        token_data = AuthenticationService.refresh_user_token(
            refresh_token=refresh_data.refresh_token,
            ip_address=ip_address,
        )

        return APIResponse(
            success=True,
            message="Token 刷新成功",
            data=token_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token 刷新錯誤: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token 刷新過程中發生錯誤",
        ) from e


@router.post(
    "/register",
    response_model=APIResponse[UserInfo],
    responses=COMMON_RESPONSES,
    summary="用戶註冊",
    description="註冊新用戶帳戶",
)
async def register(request: Request, register_data: RegisterRequest):
    """用戶註冊"""
    try:
        ip_address = get_client_ip(request)

        # 註冊用戶
        new_user = AuthenticationService.register_user(
            username=register_data.username,
            email=register_data.email,
            password=register_data.password,
            confirm_password=register_data.confirm_password,
            full_name=register_data.full_name,
            role=register_data.role,
            ip_address=ip_address,
        )

        # 準備響應
        user_info = UserInfo(
            user_id=new_user["user_id"],
            username=new_user["username"],
            email=new_user["email"],
            full_name=new_user["full_name"],
            role=new_user["role"],
            is_active=new_user["is_active"],
            created_at=new_user["created_at"],
        )

        return APIResponse(success=True, message="註冊成功", data=user_info)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        logger.error("註冊錯誤: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="註冊過程中發生錯誤",
        ) from e


@router.get(
    "/me",
    response_model=APIResponse[UserInfo],
    responses=COMMON_RESPONSES,
    summary="獲取當前用戶資訊",
    description="獲取當前登入用戶的詳細資訊",
)
async def get_current_user_info(request: Request):
    """獲取當前用戶資訊"""
    try:
        # 從請求狀態獲取用戶資訊（已經通過認證中間件驗證）
        username = getattr(request.state, "username", None)
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="未授權訪問"
            )

        # 獲取用戶資訊
        user = AuthenticationService.get_user_info(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="用戶不存在"
            )

        user_info = UserInfo(
            user_id=user["user_id"],
            username=user["username"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"],
            last_login=user["last_login"],
        )

        return APIResponse(success=True, message="用戶資訊獲取成功", data=user_info)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取用戶資訊錯誤: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="獲取用戶資訊過程中發生錯誤",
        ) from e
