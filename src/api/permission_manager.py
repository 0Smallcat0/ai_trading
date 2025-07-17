"""
權限管理模組

此模組負責處理用戶權限和授權相關的功能，包括：
- 權限檢查和驗證
- 角色權限管理
- 裝飾器權限控制

主要功能：
- 實現基於角色的權限控制
- 提供權限檢查裝飾器
- 管理權限層級和繼承
- 支援動態權限分配

Example:
    >>> from src.api.permission_manager import require_permission, check_permission
    >>> @require_permission("admin")
    ... def admin_only_function():
    ...     return "Admin access granted"
"""

import logging
from functools import wraps
from typing import Dict, Any, List, Callable, Optional, Tuple
from fastapi import HTTPException, status, Request

logger = logging.getLogger(__name__)


class PermissionLevel:
    """權限級別常數."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    
    # 功能權限
    USER_MANAGEMENT = "user_management"
    SYSTEM_CONFIG = "system_config"
    DATA_MANAGEMENT = "data_management"
    STRATEGY_MANAGEMENT = "strategy_management"
    PORTFOLIO_MANAGEMENT = "portfolio_management"
    RISK_MANAGEMENT = "risk_management"
    TRADE_EXECUTION = "trade_execution"
    SYSTEM_MONITORING = "system_monitoring"
    REPORTS = "reports"


class RoleLevel:
    """角色級別常數."""
    ADMIN = "admin"
    TRADER = "trader"
    ANALYST = "analyst"
    VIEWER = "viewer"
    DEMO = "demo"


def get_permission_hierarchy() -> Dict[str, List[str]]:
    """獲取權限層級結構.
    
    Returns:
        Dict[str, List[str]]: 權限層級映射
        
    Example:
        >>> hierarchy = get_permission_hierarchy()
        >>> print(PermissionLevel.ADMIN in hierarchy[PermissionLevel.ADMIN])
        True
    """
    return {
        PermissionLevel.READ: [PermissionLevel.READ],
        PermissionLevel.WRITE: [PermissionLevel.READ, PermissionLevel.WRITE],
        PermissionLevel.DELETE: [
            PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.DELETE
        ],
        PermissionLevel.ADMIN: [
            PermissionLevel.READ, PermissionLevel.WRITE, 
            PermissionLevel.DELETE, PermissionLevel.ADMIN
        ]
    }


def get_role_permissions_mapping() -> Dict[str, List[str]]:
    """獲取角色權限映射.
    
    Returns:
        Dict[str, List[str]]: 角色權限映射
        
    Example:
        >>> mapping = get_role_permissions_mapping()
        >>> admin_perms = mapping[RoleLevel.ADMIN]
        >>> print(PermissionLevel.ADMIN in admin_perms)
        True
    """
    return {
        RoleLevel.ADMIN: [
            PermissionLevel.READ, PermissionLevel.WRITE, 
            PermissionLevel.DELETE, PermissionLevel.ADMIN,
            PermissionLevel.USER_MANAGEMENT, PermissionLevel.SYSTEM_CONFIG,
            PermissionLevel.DATA_MANAGEMENT, PermissionLevel.STRATEGY_MANAGEMENT,
            PermissionLevel.PORTFOLIO_MANAGEMENT, PermissionLevel.RISK_MANAGEMENT,
            PermissionLevel.TRADE_EXECUTION, PermissionLevel.SYSTEM_MONITORING,
            PermissionLevel.REPORTS
        ],
        RoleLevel.TRADER: [
            PermissionLevel.READ, PermissionLevel.WRITE,
            PermissionLevel.STRATEGY_MANAGEMENT, PermissionLevel.PORTFOLIO_MANAGEMENT,
            PermissionLevel.RISK_MANAGEMENT, PermissionLevel.TRADE_EXECUTION,
            PermissionLevel.REPORTS
        ],
        RoleLevel.ANALYST: [
            PermissionLevel.READ, PermissionLevel.WRITE,
            PermissionLevel.DATA_MANAGEMENT, PermissionLevel.STRATEGY_MANAGEMENT,
            PermissionLevel.PORTFOLIO_MANAGEMENT, PermissionLevel.REPORTS
        ],
        RoleLevel.VIEWER: [
            PermissionLevel.READ, PermissionLevel.REPORTS
        ],
        RoleLevel.DEMO: [
            PermissionLevel.READ, PermissionLevel.STRATEGY_MANAGEMENT,
            PermissionLevel.PORTFOLIO_MANAGEMENT, PermissionLevel.REPORTS
        ]
    }


def check_permission(user: Dict[str, Any], required_permission: str) -> bool:
    """檢查用戶是否具有指定權限.
    
    Args:
        user: 用戶資料字典
        required_permission: 所需權限
        
    Returns:
        bool: 是否具有權限
        
    Example:
        >>> user = {"role": "admin", "permissions": ["read", "write", "admin"]}
        >>> has_perm = check_permission(user, "admin")
        >>> print(has_perm)
        True
    """
    if not user or not isinstance(user, dict):
        logger.warning("無效的用戶資料")
        return False
    
    # 檢查用戶是否啟用
    if not user.get("is_active", True):
        logger.warning("用戶帳戶已停用: %s", user.get("username", "unknown"))
        return False
    
    # 獲取用戶權限
    user_permissions = user.get("permissions", [])
    if not user_permissions:
        # 如果沒有明確的權限列表，根據角色獲取
        user_role = user.get("role", "")
        role_permissions = get_role_permissions_mapping()
        user_permissions = role_permissions.get(user_role, [])
    
    # 檢查直接權限
    if required_permission in user_permissions:
        return True
    
    # 檢查權限層級（例如：admin 權限包含所有其他權限）
    hierarchy = get_permission_hierarchy()
    for user_perm in user_permissions:
        if user_perm in hierarchy:
            if required_permission in hierarchy[user_perm]:
                return True
    
    logger.debug(
        "用戶 %s 缺少權限 %s，當前權限: %s", 
        user.get("username", "unknown"), 
        required_permission, 
        user_permissions
    )
    return False


def require_permission(required_permission: str) -> Callable:
    """權限檢查裝飾器.
    
    Args:
        required_permission: 所需權限
        
    Returns:
        Callable: 裝飾器函數
        
    Example:
        >>> @require_permission("admin")
        ... def admin_function(user):
        ...     return "Admin only"
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 嘗試從參數中獲取用戶資料
            user = None
            
            # 檢查關鍵字參數
            if "user" in kwargs:
                user = kwargs["user"]
            elif "current_user" in kwargs:
                user = kwargs["current_user"]
            
            # 檢查位置參數（通常第一個參數是用戶）
            if not user and args:
                for arg in args:
                    if isinstance(arg, dict) and "username" in arg:
                        user = arg
                        break
            
            if not user:
                logger.error("無法獲取用戶資料進行權限檢查")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="認證失敗"
                )
            
            if not check_permission(user, required_permission):
                logger.warning(
                    "用戶 %s 嘗試訪問需要 %s 權限的資源", 
                    user.get("username", "unknown"), 
                    required_permission
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"需要 {required_permission} 權限"
                )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_role(required_role: str) -> Callable:
    """角色檢查裝飾器.
    
    Args:
        required_role: 所需角色
        
    Returns:
        Callable: 裝飾器函數
        
    Example:
        >>> @require_role("admin")
        ... def admin_only_function(user):
        ...     return "Admin access"
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 獲取用戶資料（同 require_permission）
            user = None
            
            if "user" in kwargs:
                user = kwargs["user"]
            elif "current_user" in kwargs:
                user = kwargs["current_user"]
            
            if not user and args:
                for arg in args:
                    if isinstance(arg, dict) and "username" in arg:
                        user = arg
                        break
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="認證失敗"
                )
            
            user_role = user.get("role", "")
            if user_role != required_role:
                logger.warning(
                    "用戶 %s (角色: %s) 嘗試訪問需要 %s 角色的資源", 
                    user.get("username", "unknown"), 
                    user_role,
                    required_role
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"需要 {required_role} 角色"
                )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def get_user_accessible_resources(user: Dict[str, Any]) -> List[str]:
    """獲取用戶可訪問的資源列表.
    
    Args:
        user: 用戶資料字典
        
    Returns:
        List[str]: 可訪問的資源列表
        
    Example:
        >>> user = {"role": "trader"}
        >>> resources = get_user_accessible_resources(user)
        >>> print("strategy_management" in resources)
        True
    """
    if not user:
        return []
    
    user_permissions = user.get("permissions", [])
    if not user_permissions:
        user_role = user.get("role", "")
        role_permissions = get_role_permissions_mapping()
        user_permissions = role_permissions.get(user_role, [])
    
    # 資源權限映射
    resource_permissions = {
        "dashboard": [PermissionLevel.READ],
        "data_management": [PermissionLevel.DATA_MANAGEMENT],
        "strategy_management": [PermissionLevel.STRATEGY_MANAGEMENT],
        "portfolio_management": [PermissionLevel.PORTFOLIO_MANAGEMENT],
        "risk_management": [PermissionLevel.RISK_MANAGEMENT],
        "trade_execution": [PermissionLevel.TRADE_EXECUTION],
        "reports": [PermissionLevel.REPORTS],
        "system_monitoring": [PermissionLevel.SYSTEM_MONITORING],
        "user_management": [PermissionLevel.USER_MANAGEMENT],
        "system_config": [PermissionLevel.SYSTEM_CONFIG]
    }
    
    accessible_resources = []
    for resource, required_perms in resource_permissions.items():
        if any(perm in user_permissions for perm in required_perms):
            accessible_resources.append(resource)
    
    return accessible_resources


def validate_permission_request(
    user: Dict[str, Any], 
    resource: str, 
    action: str
) -> Tuple[bool, str]:
    """驗證權限請求.
    
    Args:
        user: 用戶資料
        resource: 資源名稱
        action: 操作類型
        
    Returns:
        Tuple[bool, str]: (是否允許, 錯誤訊息)
        
    Example:
        >>> user = {"role": "admin"}
        >>> allowed, msg = validate_permission_request(user, "users", "create")
        >>> print(allowed)
        True
    """
    if not user:
        return False, "用戶未認證"
    
    if not user.get("is_active", True):
        return False, "用戶帳戶已停用"
    
    # 資源-操作權限映射
    resource_action_permissions = {
        ("users", "read"): [PermissionLevel.USER_MANAGEMENT, PermissionLevel.ADMIN],
        ("users", "create"): [PermissionLevel.USER_MANAGEMENT, PermissionLevel.ADMIN],
        ("users", "update"): [PermissionLevel.USER_MANAGEMENT, PermissionLevel.ADMIN],
        ("users", "delete"): [PermissionLevel.USER_MANAGEMENT, PermissionLevel.ADMIN],
        ("strategies", "read"): [PermissionLevel.STRATEGY_MANAGEMENT, PermissionLevel.READ],
        ("strategies", "create"): [PermissionLevel.STRATEGY_MANAGEMENT, PermissionLevel.WRITE],
        ("strategies", "update"): [PermissionLevel.STRATEGY_MANAGEMENT, PermissionLevel.WRITE],
        ("strategies", "delete"): [PermissionLevel.STRATEGY_MANAGEMENT, PermissionLevel.DELETE],
        ("trades", "execute"): [PermissionLevel.TRADE_EXECUTION],
        ("reports", "view"): [PermissionLevel.REPORTS, PermissionLevel.READ]
    }
    
    required_permissions = resource_action_permissions.get((resource, action), [])
    if not required_permissions:
        return False, f"未定義的資源操作: {resource}.{action}"
    
    for required_perm in required_permissions:
        if check_permission(user, required_perm):
            return True, ""
    
    return False, f"缺少執行 {resource}.{action} 所需的權限"
