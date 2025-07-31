"""認證工具模組

此模組包含認證相關的常數、配置和工具函數。
"""

import logging

# 導入服務層
try:
    from src.core.authentication_service import AuthenticationService

    SERVICES_AVAILABLE = True
    logging.info("認證服務層導入成功")
except ImportError as e:
    SERVICES_AVAILABLE = False
    logging.warning("認證服務層不可用，使用簡化認證: %s", e)

# 模擬用戶資料庫（當服務不可用時使用）
USERS = {
    "admin": {
        "password": "admin123",
        "role": "admin",
        "name": "系統管理員",
        "user_id": "admin001",
        "email": "admin@example.com",
        "two_factor_enabled": False,
    },
    "trader": {
        "password": "trader123",
        "role": "trader",
        "name": "交易員",
        "user_id": "trader001",
        "email": "trader@example.com",
        "two_factor_enabled": True,
    },
    "analyst": {
        "password": "analyst123",
        "role": "analyst",
        "name": "分析師",
        "user_id": "analyst001",
        "email": "analyst@example.com",
        "two_factor_enabled": False,
    },
    "user": {
        "password": "user123",
        "role": "user",
        "name": "一般用戶",
        "user_id": "user001",
        "email": "user@example.com",
        "two_factor_enabled": False,
    },
    "guest": {
        "password": "guest123",
        "role": "readonly",
        "name": "訪客用戶",
        "user_id": "guest001",
        "email": "guest@example.com",
        "two_factor_enabled": False,
    },
}


def get_authentication_service():
    """獲取認證服務實例

    Returns:
        AuthenticationService: 認證服務實例，如果不可用則返回 None
    """
    if SERVICES_AVAILABLE:
        try:
            return AuthenticationService()
        except Exception as e:
            logging.error("無法創建認證服務實例: %s", e)
            return None
    return None
