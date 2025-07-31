"""配置管理模組.

此模組提供多環境配置管理功能，支援：
- 開發環境 (development)
- 測試環境 (testing)
- 生產環境 (production)

使用方式：
    from config import get_config

    config = get_config()
    database_url = config.DATABASE_URL
"""

from .environment_config import get_config, Config

__all__ = ["get_config", "Config"]
