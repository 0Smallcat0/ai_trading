"""
角色基於訪問控制 (RBAC) 模組

此模組實現了角色基於訪問控制 (RBAC) 功能，用於管理用戶權限。
"""

import os
import logging
import json
from enum import Enum
from typing import Dict, List, Set, Optional, Any, Union
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import SecurityScopes

from src.core.logger import logger
from .models import UserModel


class Role(str, Enum):
    """角色枚舉"""

    ADMIN = "admin"
    MANAGER = "manager"
    TRADER = "trader"
    ANALYST = "analyst"
    VIEWER = "viewer"


class Permission(str, Enum):
    """權限枚舉"""

    # 系統管理權限
    MANAGE_USERS = "manage_users"
    MANAGE_ROLES = "manage_roles"
    MANAGE_SYSTEM = "manage_system"
    VIEW_LOGS = "view_logs"

    # 交易權限
    EXECUTE_TRADES = "execute_trades"
    APPROVE_TRADES = "approve_trades"
    VIEW_TRADES = "view_trades"

    # 策略權限
    MANAGE_STRATEGIES = "manage_strategies"
    RUN_BACKTEST = "run_backtest"
    VIEW_STRATEGIES = "view_strategies"

    # 資料權限
    MANAGE_DATA = "manage_data"
    VIEW_DATA = "view_data"

    # 工作流權限
    MANAGE_WORKFLOWS = "manage_workflows"
    VIEW_WORKFLOWS = "view_workflows"


# 角色權限映射
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.ADMIN: [
        # 管理員擁有所有權限
        Permission.MANAGE_USERS,
        Permission.MANAGE_ROLES,
        Permission.MANAGE_SYSTEM,
        Permission.VIEW_LOGS,
        Permission.EXECUTE_TRADES,
        Permission.APPROVE_TRADES,
        Permission.VIEW_TRADES,
        Permission.MANAGE_STRATEGIES,
        Permission.RUN_BACKTEST,
        Permission.VIEW_STRATEGIES,
        Permission.MANAGE_DATA,
        Permission.VIEW_DATA,
        Permission.MANAGE_WORKFLOWS,
        Permission.VIEW_WORKFLOWS,
    ],
    Role.MANAGER: [
        # 經理擁有大部分權限，但不能管理用戶和角色
        Permission.MANAGE_SYSTEM,
        Permission.VIEW_LOGS,
        Permission.APPROVE_TRADES,
        Permission.VIEW_TRADES,
        Permission.MANAGE_STRATEGIES,
        Permission.RUN_BACKTEST,
        Permission.VIEW_STRATEGIES,
        Permission.MANAGE_DATA,
        Permission.VIEW_DATA,
        Permission.MANAGE_WORKFLOWS,
        Permission.VIEW_WORKFLOWS,
    ],
    Role.TRADER: [
        # 交易員只能執行交易和查看相關資訊
        Permission.EXECUTE_TRADES,
        Permission.VIEW_TRADES,
        Permission.VIEW_STRATEGIES,
        Permission.RUN_BACKTEST,
        Permission.VIEW_DATA,
        Permission.VIEW_WORKFLOWS,
    ],
    Role.ANALYST: [
        # 分析師只能管理策略和查看資料
        Permission.VIEW_TRADES,
        Permission.MANAGE_STRATEGIES,
        Permission.RUN_BACKTEST,
        Permission.VIEW_STRATEGIES,
        Permission.VIEW_DATA,
        Permission.VIEW_WORKFLOWS,
    ],
    Role.VIEWER: [
        # 觀察者只能查看資訊
        Permission.VIEW_TRADES,
        Permission.VIEW_STRATEGIES,
        Permission.VIEW_DATA,
        Permission.VIEW_WORKFLOWS,
    ],
}


class RBACManager:
    """
    RBAC 管理器

    管理用戶角色和權限。
    """

    def __init__(self):
        """初始化 RBAC 管理器"""
        # 用戶角色映射
        self.user_roles: Dict[str, List[Role]] = {}

        # 用戶自定義權限映射
        self.user_permissions: Dict[str, Dict[Permission, bool]] = {}

    def get_user_roles(self, username: str) -> List[Role]:
        """
        獲取用戶角色

        Args:
            username: 用戶名

        Returns:
            List[Role]: 角色列表
        """
        return self.user_roles.get(username, [])

    def set_user_roles(self, username: str, roles: List[Role]) -> None:
        """
        設置用戶角色

        Args:
            username: 用戶名
            roles: 角色列表
        """
        self.user_roles[username] = roles
        logger.info(f"已設置用戶 {username} 的角色: {roles}")

    def add_user_role(self, username: str, role: Role) -> None:
        """
        添加用戶角色

        Args:
            username: 用戶名
            role: 角色
        """
        if username not in self.user_roles:
            self.user_roles[username] = []

        if role not in self.user_roles[username]:
            self.user_roles[username].append(role)
            logger.info(f"已添加用戶 {username} 的角色: {role}")

    def remove_user_role(self, username: str, role: Role) -> None:
        """
        移除用戶角色

        Args:
            username: 用戶名
            role: 角色
        """
        if username in self.user_roles and role in self.user_roles[username]:
            self.user_roles[username].remove(role)
            logger.info(f"已移除用戶 {username} 的角色: {role}")

    def get_user_permissions(self, username: str) -> Set[Permission]:
        """
        獲取用戶權限

        Args:
            username: 用戶名

        Returns:
            Set[Permission]: 權限集合
        """
        # 獲取用戶角色
        roles = self.get_user_roles(username)

        # 獲取角色權限
        permissions: Set[Permission] = set()
        for role in roles:
            permissions.update(ROLE_PERMISSIONS.get(role, []))

        # 獲取用戶自定義權限
        user_custom_permissions = self.user_permissions.get(username, {})
        for permission, granted in user_custom_permissions.items():
            if granted and permission not in permissions:
                permissions.add(permission)
            elif not granted and permission in permissions:
                permissions.remove(permission)

        return permissions

    def has_permission(self, username: str, permission: Permission) -> bool:
        """
        檢查用戶是否擁有權限

        Args:
            username: 用戶名
            permission: 權限

        Returns:
            bool: 是否擁有權限
        """
        return permission in self.get_user_permissions(username)

    def grant_permission(self, username: str, permission: Permission) -> None:
        """
        授予用戶權限

        Args:
            username: 用戶名
            permission: 權限
        """
        if username not in self.user_permissions:
            self.user_permissions[username] = {}

        self.user_permissions[username][permission] = True
        logger.info(f"已授予用戶 {username} 權限: {permission}")

    def revoke_permission(self, username: str, permission: Permission) -> None:
        """
        撤銷用戶權限

        Args:
            username: 用戶名
            permission: 權限
        """
        if username not in self.user_permissions:
            self.user_permissions[username] = {}

        self.user_permissions[username][permission] = False
        logger.info(f"已撤銷用戶 {username} 權限: {permission}")

    def save_to_file(self, file_path: str = "config/rbac.json") -> bool:
        """
        保存 RBAC 配置到文件

        Args:
            file_path: 文件路徑

        Returns:
            bool: 是否成功
        """
        try:
            # 創建目錄
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 準備數據
            data = {
                "user_roles": {
                    username: [role.value for role in roles]
                    for username, roles in self.user_roles.items()
                },
                "user_permissions": {
                    username: {
                        permission.value: granted
                        for permission, granted in permissions.items()
                    }
                    for username, permissions in self.user_permissions.items()
                },
            }

            # 保存到文件
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info(f"已保存 RBAC 配置到文件: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存 RBAC 配置到文件時發生錯誤: {e}")
            return False

    def load_from_file(self, file_path: str = "config/rbac.json") -> bool:
        """
        從文件加載 RBAC 配置

        Args:
            file_path: 文件路徑

        Returns:
            bool: 是否成功
        """
        try:
            # 檢查文件是否存在
            if not os.path.exists(file_path):
                logger.warning(f"RBAC 配置文件不存在: {file_path}")
                return False

            # 從文件加載
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 解析數據
            self.user_roles = {
                username: [Role(role) for role in roles]
                for username, roles in data.get("user_roles", {}).items()
            }

            self.user_permissions = {
                username: {
                    Permission(permission): granted
                    for permission, granted in permissions.items()
                }
                for username, permissions in data.get("user_permissions", {}).items()
            }

            logger.info(f"已從文件加載 RBAC 配置: {file_path}")
            return True
        except Exception as e:
            logger.error(f"從文件加載 RBAC 配置時發生錯誤: {e}")
            return False


# 創建全局 RBAC 管理器實例
rbac_manager = RBACManager()

# 嘗試從文件加載 RBAC 配置
rbac_manager.load_from_file()


async def check_permission(
    request: Request,
    permission: Permission,
    user: UserModel = Security(Depends(lambda: None)),
) -> bool:
    """
    檢查用戶是否擁有權限

    Args:
        request: 請求
        permission: 權限
        user: 用戶模型

    Returns:
        bool: 是否擁有權限
    """
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未認證",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not rbac_manager.has_permission(user.username, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"權限不足: {permission}",
        )

    return True
