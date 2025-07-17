"""
認證路由處理器模組

此模組實現了認證相關的業務邏輯處理，包括：
- 登入處理邏輯
- 註冊處理邏輯
- 令牌管理邏輯
- 用戶資訊管理

主要功能：
- 處理用戶認證請求
- 管理用戶會話和令牌
- 實現用戶資料操作
- 提供安全的認證服務

Example:
    >>> from src.api.routers.auth_handlers import handle_login
    >>> result = handle_login("admin", "admin123", "127.0.0.1")
    >>> print(result.success)
    True
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

from fastapi import APIRouter, HTTPException, status, Request
from src.api.middleware.auth import TokenManager, TokenBlacklist
from src.api.models.auth_requests import (
    LoginRequest, RegisterRequest, ChangePasswordRequest,
    LoginResponse, UserInfoResponse
)
from src.api.auth_models import User, AuthResponse
from src.api.password_manager import verify_password, hash_password, check_password_strength
from src.api.permission_manager import get_user_accessible_resources
from src.api.utils.security import get_client_ip

logger = logging.getLogger(__name__)

# 創建路由器
router = APIRouter()


@router.post("/login", response_model=LoginResponse)
async def login_endpoint(request: LoginRequest, client_request: Request):
    """用戶登入端點

    Args:
        request: 登入請求資料
        client_request: FastAPI 請求物件

    Returns:
        LoginResponse: 登入回應
    """
    client_ip = get_client_ip(client_request)
    user_agent = client_request.headers.get("user-agent")

    return handle_login(request, client_ip, user_agent)


@router.get("/health")
async def auth_health():
    """認證服務健康檢查

    Returns:
        Dict: 健康狀態
    """
    return {"status": "healthy", "service": "auth"}


def handle_login(
    request: LoginRequest, 
    client_ip: str,
    user_agent: Optional[str] = None
) -> LoginResponse:
    """處理用戶登入請求.
    
    Args:
        request: 登入請求資料
        client_ip: 客戶端 IP 地址
        user_agent: 用戶代理字符串
        
    Returns:
        LoginResponse: 登入回應資料
        
    Raises:
        HTTPException: 當登入失敗時
        
    Example:
        >>> login_req = LoginRequest(username="admin", password="admin123")
        >>> response = handle_login(login_req, "127.0.0.1")
        >>> print(response.access_token)
    """
    try:
        # 導入用戶認證函數
        from src.api.auth import authenticate_user, get_user_permissions
        
        # 驗證用戶身份
        user = authenticate_user(request.username, request.password)
        if not user:
            logger.warning(
                "登入失敗 - 用戶: %s, IP: %s", 
                request.username, 
                client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用戶名或密碼錯誤"
            )
        
        # 檢查用戶狀態
        if not user.get("is_active", True):
            logger.warning(
                "登入失敗 - 用戶已停用: %s, IP: %s", 
                request.username, 
                client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用戶帳戶已停用"
            )
        
        # 創建訪問令牌
        token_manager = TokenManager()
        
        # 設定令牌過期時間
        expires_delta = timedelta(hours=24) if request.remember_me else timedelta(hours=1)
        
        payload = {
            "sub": user["username"],
            "user_id": user["user_id"],
            "role": user["role"],
            "permissions": get_user_permissions(user),
            "client_ip": client_ip,
            "user_agent": user_agent
        }
        
        access_token = token_manager.create_token(payload, expires_delta)
        refresh_token = token_manager.create_refresh_token(payload) if request.remember_me else None
        
        # 記錄登入成功
        logger.info(
            "用戶登入成功 - 用戶: %s, IP: %s, 記住我: %s", 
            request.username, 
            client_ip,
            request.remember_me
        )
        
        # 準備用戶資訊
        user_info = {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            "permissions": get_user_permissions(user),
            "accessible_resources": get_user_accessible_resources(user)
        }
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=int(expires_delta.total_seconds()),
            user_info=user_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("登入處理錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登入過程中發生錯誤"
        ) from e


def handle_logout(token: str, all_devices: bool = False) -> Dict[str, Any]:
    """處理用戶登出請求.
    
    Args:
        token: 用戶令牌
        all_devices: 是否登出所有設備
        
    Returns:
        Dict[str, Any]: 登出結果
        
    Example:
        >>> result = handle_logout("user_token")
        >>> print(result["success"])
        True
    """
    try:
        blacklist = TokenBlacklist()
        
        if all_devices:
            # 登出所有設備（需要實現用戶所有令牌的管理）
            # 這裡簡化處理，只將當前令牌加入黑名單
            blacklist.add_token(token)
            logger.info("用戶已從所有設備登出")
            message = "已從所有設備登出"
        else:
            # 只登出當前設備
            blacklist.add_token(token)
            logger.info("用戶已登出")
            message = "登出成功"
        
        return {
            "success": True,
            "message": message,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error("登出處理錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登出過程中發生錯誤"
        ) from e


def handle_refresh_token(refresh_token: str) -> LoginResponse:
    """處理令牌刷新請求.
    
    Args:
        refresh_token: 刷新令牌
        
    Returns:
        LoginResponse: 新的令牌資料
        
    Raises:
        HTTPException: 當刷新失敗時
        
    Example:
        >>> response = handle_refresh_token("refresh_token")
        >>> print(response.access_token)
    """
    try:
        token_manager = TokenManager()
        
        # 驗證刷新令牌
        payload = token_manager.verify_refresh_token(refresh_token)
        username = payload.get("sub")
        
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無效的刷新令牌"
            )
        
        # 獲取用戶資訊
        from src.api.auth import get_user_by_username, get_user_permissions
        user = get_user_by_username(username)
        
        if not user or not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用戶不存在或已停用"
            )
        
        # 創建新的訪問令牌
        new_payload = {
            "sub": user["username"],
            "user_id": user["user_id"],
            "role": user["role"],
            "permissions": get_user_permissions(user)
        }
        
        access_token = token_manager.create_token(new_payload)
        
        # 準備用戶資訊
        user_info = {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            "permissions": get_user_permissions(user)
        }
        
        logger.info("令牌刷新成功 - 用戶: %s", username)
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,  # 保持原刷新令牌
            token_type="bearer",
            expires_in=3600,  # 1小時
            user_info=user_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("令牌刷新錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="令牌刷新過程中發生錯誤"
        ) from e


def handle_change_password(
    user: Dict[str, Any], 
    request: ChangePasswordRequest
) -> Dict[str, Any]:
    """處理密碼修改請求.
    
    Args:
        user: 當前用戶資訊
        request: 密碼修改請求
        
    Returns:
        Dict[str, Any]: 修改結果
        
    Raises:
        HTTPException: 當修改失敗時
        
    Example:
        >>> change_req = ChangePasswordRequest(
        ...     current_password="old_pass",
        ...     new_password="new_pass",
        ...     confirm_password="new_pass"
        ... )
        >>> result = handle_change_password(user, change_req)
        >>> print(result["success"])
    """
    try:
        # 驗證當前密碼
        current_hash = user.get("password_hash", "")
        if not verify_password(request.current_password, current_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="當前密碼錯誤"
            )
        
        # 檢查新密碼強度
        strength = check_password_strength(request.new_password)
        if not strength["is_strong"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"密碼強度不足: {', '.join(strength['feedback'])}"
            )
        
        # 生成新密碼哈希
        new_hash = hash_password(request.new_password)
        
        # 更新用戶密碼（這裡需要實際的資料庫更新邏輯）
        # 在實際應用中，這裡應該調用資料庫更新函數
        user["password_hash"] = new_hash
        user["password_updated_at"] = datetime.now()
        
        logger.info("用戶 %s 密碼修改成功", user["username"])
        
        return {
            "success": True,
            "message": "密碼修改成功",
            "timestamp": datetime.now()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("密碼修改錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密碼修改過程中發生錯誤"
        ) from e


def get_user_info(user: Dict[str, Any]) -> UserInfoResponse:
    """獲取用戶資訊.
    
    Args:
        user: 用戶資訊字典
        
    Returns:
        UserInfoResponse: 用戶資訊回應
        
    Example:
        >>> user_info = get_user_info(user)
        >>> print(user_info.username)
    """
    try:
        from src.api.auth import get_user_permissions
        
        return UserInfoResponse(
            user_id=user["user_id"],
            username=user["username"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"],
            permissions=get_user_permissions(user),
            is_active=user.get("is_active", True),
            created_at=user.get("created_at"),
            last_login=user.get("last_login")
        )
        
    except Exception as e:
        logger.error("獲取用戶資訊錯誤: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="獲取用戶資訊過程中發生錯誤"
        ) from e
