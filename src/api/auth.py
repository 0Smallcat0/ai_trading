"""
認證相關功能模組

提供用戶認證、密碼管理等基礎功能。
"""

import hashlib
import secrets
from typing import Dict, Optional, Any
from datetime import datetime

# 模擬用戶數據庫
USERS_DB: Dict[str, Dict[str, Any]] = {
    "admin": {
        "username": "admin",
        "email": "admin@example.com",
        "password_hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",  # "password"
        "role": "admin",
        "created_at": datetime.now(),
        "is_active": True,
        "two_factor_enabled": False
    },
    "trader": {
        "username": "trader",
        "email": "trader@example.com", 
        "password_hash": "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",  # "password"
        "role": "trader",
        "created_at": datetime.now(),
        "is_active": True,
        "two_factor_enabled": False
    }
}


def hash_password(password: str) -> str:
    """
    對密碼進行哈希處理
    
    Args:
        password: 原始密碼
        
    Returns:
        str: 哈希後的密碼
    """
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """
    驗證密碼
    
    Args:
        password: 原始密碼
        password_hash: 哈希後的密碼
        
    Returns:
        bool: 驗證結果
    """
    return hash_password(password) == password_hash


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    根據用戶名獲取用戶信息
    
    Args:
        username: 用戶名
        
    Returns:
        Optional[Dict[str, Any]]: 用戶信息或None
    """
    return USERS_DB.get(username)


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    根據郵箱獲取用戶信息
    
    Args:
        email: 郵箱地址
        
    Returns:
        Optional[Dict[str, Any]]: 用戶信息或None
    """
    for user in USERS_DB.values():
        if user.get("email") == email:
            return user
    return None


def create_user(username: str, email: str, password: str, role: str = "trader") -> bool:
    """
    創建新用戶
    
    Args:
        username: 用戶名
        email: 郵箱
        password: 密碼
        role: 角色
        
    Returns:
        bool: 創建是否成功
    """
    if username in USERS_DB:
        return False
        
    if get_user_by_email(email):
        return False
        
    USERS_DB[username] = {
        "username": username,
        "email": email,
        "password_hash": hash_password(password),
        "role": role,
        "created_at": datetime.now(),
        "is_active": True,
        "two_factor_enabled": False
    }
    
    return True


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    用戶認證
    
    Args:
        username: 用戶名
        password: 密碼
        
    Returns:
        Optional[Dict[str, Any]]: 認證成功返回用戶信息，否則返回None
    """
    user = get_user_by_username(username)
    if user and user.get("is_active") and verify_password(password, user["password_hash"]):
        return user
    return None


def generate_api_key() -> str:
    """
    生成API密鑰
    
    Returns:
        str: API密鑰
    """
    return secrets.token_urlsafe(32)


def validate_api_key(api_key: str) -> Optional[str]:
    """
    驗證API密鑰
    
    Args:
        api_key: API密鑰
        
    Returns:
        Optional[str]: 驗證成功返回用戶名，否則返回None
    """
    # 這裡應該從數據庫中查詢API密鑰對應的用戶
    # 目前返回模擬結果
    if api_key:
        return "admin"  # 模擬返回
    return None


def update_user_password(username: str, new_password: str) -> bool:
    """
    更新用戶密碼
    
    Args:
        username: 用戶名
        new_password: 新密碼
        
    Returns:
        bool: 更新是否成功
    """
    if username in USERS_DB:
        USERS_DB[username]["password_hash"] = hash_password(new_password)
        return True
    return False


def deactivate_user(username: str) -> bool:
    """
    停用用戶
    
    Args:
        username: 用戶名
        
    Returns:
        bool: 操作是否成功
    """
    if username in USERS_DB:
        USERS_DB[username]["is_active"] = False
        return True
    return False


def activate_user(username: str) -> bool:
    """
    啟用用戶
    
    Args:
        username: 用戶名
        
    Returns:
        bool: 操作是否成功
    """
    if username in USERS_DB:
        USERS_DB[username]["is_active"] = True
        return True
    return False


def get_all_users() -> Dict[str, Dict[str, Any]]:
    """
    獲取所有用戶信息
    
    Returns:
        Dict[str, Dict[str, Any]]: 所有用戶信息
    """
    return USERS_DB.copy()


def update_user_role(username: str, new_role: str) -> bool:
    """
    更新用戶角色
    
    Args:
        username: 用戶名
        new_role: 新角色
        
    Returns:
        bool: 更新是否成功
    """
    if username in USERS_DB:
        USERS_DB[username]["role"] = new_role
        return True
    return False
