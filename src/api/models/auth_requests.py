"""
認證請求模型模組

此模組定義了認證相關的請求和回應模型，包括：
- 登入請求模型
- 註冊請求模型
- 令牌刷新模型
- 密碼重設模型

主要功能：
- 提供標準化的 API 請求格式
- 實現資料驗證和格式化
- 支援多種認證場景

Example:
    >>> from src.api.models.auth_requests import LoginRequest
    >>> login_data = LoginRequest(username="admin", password="admin123")
    >>> print(login_data.username)
    'admin'
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator

# 暫時使用 str 類型代替 EmailStr 以避免依賴衝突
# TODO: 當升級到支援的 pydantic 版本時，恢復 EmailStr
EmailStr = str


class LoginRequest(BaseModel):
    """登入請求模型.
    
    Attributes:
        username: 用戶名
        password: 密碼
        remember_me: 是否記住登入狀態
        device_info: 設備資訊
    """
    username: str = Field(..., min_length=3, max_length=50, description="用戶名")
    password: str = Field(..., min_length=6, max_length=100, description="密碼")
    remember_me: bool = Field(default=False, description="記住我")
    device_info: Optional[Dict[str, str]] = Field(default=None, description="設備資訊")

    @validator('username')
    def validate_username(cls, v):
        """驗證用戶名格式."""
        if not v.strip():
            raise ValueError('用戶名不能為空')
        return v.strip().lower()

    @validator('password')
    def validate_password(cls, v):
        """驗證密碼格式."""
        if not v.strip():
            raise ValueError('密碼不能為空')
        return v


class RegisterRequest(BaseModel):
    """註冊請求模型.
    
    Attributes:
        username: 用戶名
        email: 電子郵件地址
        password: 密碼
        confirm_password: 確認密碼
        full_name: 完整姓名
        role: 用戶角色
    """
    username: str = Field(..., min_length=3, max_length=50, description="用戶名")
    email: EmailStr = Field(..., description="郵箱地址")
    password: str = Field(..., min_length=6, max_length=100, description="密碼")
    confirm_password: str = Field(
        ..., min_length=6, max_length=100, description="確認密碼"
    )
    full_name: Optional[str] = Field(default=None, max_length=100, description="全名")
    role: Optional[str] = Field(default="user", description="用戶角色")

    @validator('username')
    def validate_username(cls, v):
        """驗證用戶名格式."""
        if not v.strip():
            raise ValueError('用戶名不能為空')
        # 檢查用戶名是否包含特殊字符
        import re
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用戶名只能包含字母、數字和下劃線')
        return v.strip().lower()

    @validator('confirm_password')
    def validate_passwords_match(cls, v, values):
        """驗證密碼確認."""
        if 'password' in values and v != values['password']:
            raise ValueError('密碼和確認密碼不匹配')
        return v

    @validator('role')
    def validate_role(cls, v):
        """驗證用戶角色."""
        valid_roles = ['admin', 'trader', 'analyst', 'viewer', 'demo']
        if v and v not in valid_roles:
            raise ValueError(f'無效的用戶角色，有效角色: {", ".join(valid_roles)}')
        return v


class RefreshTokenRequest(BaseModel):
    """刷新令牌請求模型.
    
    Attributes:
        refresh_token: 刷新令牌
    """
    refresh_token: str = Field(..., description="刷新令牌")

    @validator('refresh_token')
    def validate_refresh_token(cls, v):
        """驗證刷新令牌格式."""
        if not v.strip():
            raise ValueError('刷新令牌不能為空')
        return v.strip()


class PasswordResetRequest(BaseModel):
    """密碼重設請求模型.
    
    Attributes:
        email: 電子郵件地址
    """
    email: EmailStr = Field(..., description="註冊時使用的郵箱地址")


class PasswordResetConfirmRequest(BaseModel):
    """密碼重設確認請求模型.
    
    Attributes:
        token: 重設令牌
        new_password: 新密碼
        confirm_password: 確認新密碼
    """
    token: str = Field(..., description="密碼重設令牌")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密碼")
    confirm_password: str = Field(
        ..., min_length=6, max_length=100, description="確認新密碼"
    )

    @validator('confirm_password')
    def validate_passwords_match(cls, v, values):
        """驗證密碼確認."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('新密碼和確認密碼不匹配')
        return v


class ChangePasswordRequest(BaseModel):
    """修改密碼請求模型.
    
    Attributes:
        current_password: 當前密碼
        new_password: 新密碼
        confirm_password: 確認新密碼
    """
    current_password: str = Field(..., description="當前密碼")
    new_password: str = Field(..., min_length=6, max_length=100, description="新密碼")
    confirm_password: str = Field(
        ..., min_length=6, max_length=100, description="確認新密碼"
    )

    @validator('confirm_password')
    def validate_passwords_match(cls, v, values):
        """驗證密碼確認."""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('新密碼和確認密碼不匹配')
        return v

    @validator('new_password')
    def validate_new_password_different(cls, v, values):
        """驗證新密碼與當前密碼不同."""
        if 'current_password' in values and v == values['current_password']:
            raise ValueError('新密碼不能與當前密碼相同')
        return v


class LogoutRequest(BaseModel):
    """登出請求模型.
    
    Attributes:
        all_devices: 是否登出所有設備
    """
    all_devices: bool = Field(default=False, description="是否登出所有設備")


class UserProfileUpdateRequest(BaseModel):
    """用戶資料更新請求模型.
    
    Attributes:
        full_name: 完整姓名
        email: 電子郵件地址
        preferences: 用戶偏好設定
    """
    full_name: Optional[str] = Field(default=None, max_length=100, description="全名")
    email: Optional[EmailStr] = Field(default=None, description="郵箱地址")
    preferences: Optional[Dict[str, Any]] = Field(default=None, description="用戶偏好")

    @validator('full_name')
    def validate_full_name(cls, v):
        """驗證姓名格式."""
        if v is not None and not v.strip():
            raise ValueError('姓名不能為空字符串')
        return v.strip() if v else v


class TokenValidationRequest(BaseModel):
    """令牌驗證請求模型.
    
    Attributes:
        token: 要驗證的令牌
    """
    token: str = Field(..., description="要驗證的令牌")

    @validator('token')
    def validate_token(cls, v):
        """驗證令牌格式."""
        if not v.strip():
            raise ValueError('令牌不能為空')
        return v.strip()


# 回應模型
class LoginResponse(BaseModel):
    """登入回應模型.
    
    Attributes:
        access_token: 訪問令牌
        refresh_token: 刷新令牌
        token_type: 令牌類型
        expires_in: 過期時間（秒）
        user_info: 用戶資訊
    """
    access_token: str = Field(..., description="訪問令牌")
    refresh_token: Optional[str] = Field(default=None, description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌類型")
    expires_in: int = Field(..., description="過期時間（秒）")
    user_info: Dict[str, Any] = Field(..., description="用戶資訊")


class UserInfoResponse(BaseModel):
    """用戶資訊回應模型.
    
    Attributes:
        user_id: 用戶 ID
        username: 用戶名
        email: 電子郵件
        full_name: 完整姓名
        role: 用戶角色
        permissions: 權限列表
        is_active: 是否啟用
        created_at: 創建時間
        last_login: 最後登入時間
    """
    user_id: str = Field(..., description="用戶 ID")
    username: str = Field(..., description="用戶名")
    email: str = Field(..., description="電子郵件")
    full_name: str = Field(..., description="完整姓名")
    role: str = Field(..., description="用戶角色")
    permissions: List[str] = Field(..., description="權限列表")
    is_active: bool = Field(..., description="是否啟用")
    created_at: Optional[datetime] = Field(default=None, description="創建時間")
    last_login: Optional[datetime] = Field(default=None, description="最後登入時間")


class TokenValidationResponse(BaseModel):
    """令牌驗證回應模型.
    
    Attributes:
        valid: 令牌是否有效
        user_id: 用戶 ID
        username: 用戶名
        role: 用戶角色
        expires_at: 過期時間
    """
    valid: bool = Field(..., description="令牌是否有效")
    user_id: Optional[str] = Field(default=None, description="用戶 ID")
    username: Optional[str] = Field(default=None, description="用戶名")
    role: Optional[str] = Field(default=None, description="用戶角色")
    expires_at: Optional[datetime] = Field(default=None, description="過期時間")
