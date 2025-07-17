"""統一服務管理系統

此模組提供統一的服務管理架構，支援：
- 服務註冊和發現
- 依賴注入
- 生命週期管理
- 健康檢查
- 服務監控

主要組件：
- BaseService: 服務基類
- ServiceRegistry: 服務註冊器
- ServiceManager: 服務管理器
- UIServiceClient: UI 服務客戶端
"""

from .auth_service import AuthenticationService

# 嘗試導入新的服務管理組件（如果存在）
try:
    from .base_service import BaseService
    from .service_registry import ServiceRegistry
    from .service_manager import ServiceManager
    from .ui_service_client import UIServiceClient

    # 擴展導出列表
    __all__ = [
        "AuthenticationService",
        "BaseService",
        "ServiceRegistry",
        "ServiceManager",
        "UIServiceClient",
        "get_service_manager",
        "get_ui_client",
    ]

    # 全局服務管理器實例
    _service_manager = None
    _ui_client = None

    def get_service_manager() -> ServiceManager:
        """獲取全局服務管理器實例"""
        global _service_manager
        if _service_manager is None:
            _service_manager = ServiceManager()
        return _service_manager

    def get_ui_client() -> UIServiceClient:
        """獲取 UI 服務客戶端實例"""
        global _ui_client
        if _ui_client is None:
            _ui_client = UIServiceClient()
        return _ui_client

except ImportError:
    # 如果新組件不存在，只導出現有的
    __all__ = ["AuthenticationService"]

    def get_service_manager():
        """臨時實現，返回 None"""
        return None

    def get_ui_client():
        """臨時實現，返回 None"""
        return None

# 版本信息
__version__ = "1.1.0"
