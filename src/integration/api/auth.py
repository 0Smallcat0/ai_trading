"""
API認證模組

此模組實現了API認證功能，包括JWT令牌生成和驗證。
"""

import os
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import OAuth2PasswordBearer, SecurityScopes
from pydantic import BaseModel, ValidationError

from src.core.logger import logger
from .models import UserModel, TokenModel

# 獲取密鑰
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key")  # 在生產環境中應該使用環境變量
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 創建OAuth2密碼承載
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/auth/token",
    scopes={
        "read": "讀取權限",
        "write": "寫入權限",
        "admin": "管理員權限"
    }
)


# 模擬用戶數據庫
fake_users_db = {
    "admin": {
        "username": "admin",
        "email": "admin@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
        "disabled": False,
        "scopes": ["read", "write", "admin"]
    },
    "user": {
        "username": "user",
        "email": "user@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "password"
        "disabled": False,
        "scopes": ["read"]
    }
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    驗證密碼
    
    Args:
        plain_password: 明文密碼
        hashed_password: 哈希密碼
        
    Returns:
        bool: 密碼是否正確
    """
    # 在實際應用中，應該使用密碼哈希庫進行驗證
    # 這裡為了簡化，直接比較哈希值
    return hashed_password == "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW" and plain_password == "password"


def get_user(username: str) -> Optional[UserModel]:
    """
    獲取用戶
    
    Args:
        username: 用戶名
        
    Returns:
        Optional[UserModel]: 用戶模型
    """
    if username in fake_users_db:
        user_dict = fake_users_db[username]
        return UserModel(**user_dict)
    return None


def authenticate(username: str, password: str) -> Optional[UserModel]:
    """
    認證用戶
    
    Args:
        username: 用戶名
        password: 密碼
        
    Returns:
        Optional[UserModel]: 用戶模型
    """
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    創建訪問令牌
    
    Args:
        data: 令牌數據
        expires_delta: 過期時間
        
    Returns:
        str: 訪問令牌
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    security_scopes: SecurityScopes,
    token: str = Depends(oauth2_scheme)
) -> UserModel:
    """
    獲取當前用戶
    
    Args:
        security_scopes: 安全作用域
        token: 訪問令牌
        
    Returns:
        UserModel: 用戶模型
    """
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="無法驗證憑據",
        headers={"WWW-Authenticate": authenticate_value},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_scopes = payload.get("scopes", [])
    except (jwt.PyJWTError, ValidationError):
        raise credentials_exception
    
    user = get_user(username)
    if user is None:
        raise credentials_exception
    
    for scope in security_scopes.scopes:
        if scope not in token_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"權限不足: {scope}",
                headers={"WWW-Authenticate": authenticate_value},
            )
    
    return user
