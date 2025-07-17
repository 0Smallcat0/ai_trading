# -*- coding: utf-8 -*-
"""
API安全模組

此模組提供API相關的安全功能。

主要功能：
- API金鑰管理
- 權限控制
- 安全存儲
- 使用追蹤
"""

from .api_key_manager import (
    APIKeyManager,
    APIKeyInfo,
    KeyStatus,
    PermissionLevel,
    APIKeySecurityError,
    APIKeyNotFoundError,
    APIKeyExpiredError,
    APIKeyPermissionError
)

__all__ = [
    # 管理器
    "APIKeyManager",
    # 數據結構
    "APIKeyInfo",
    "KeyStatus",
    "PermissionLevel",
    # 異常
    "APIKeySecurityError",
    "APIKeyNotFoundError", 
    "APIKeyExpiredError",
    "APIKeyPermissionError",
]
