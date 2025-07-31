"""
API 版本遷移工具包

此包提供 API 版本遷移相關的工具和腳本，包括：
- 自動化版本升級腳本
- 資料庫 schema 遷移工具
- API 端點映射和重定向機制
- 版本棄用通知系統
- 遷移狀態監控和回滾機制
"""

from .migration_manager import MigrationManager

# 其他模組將在後續階段實作
# from .schema_migrator import SchemaMigrator
# from .endpoint_mapper import EndpointMapper
# from .deprecation_notifier import DeprecationNotifier

__all__ = [
    "MigrationManager",
    # "SchemaMigrator",
    # "EndpointMapper",
    # "DeprecationNotifier"
]
