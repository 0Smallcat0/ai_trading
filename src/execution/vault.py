"""
Vault 整合模組

此模組提供與 HashiCorp Vault 的整合，用於安全地存儲和管理敏感資訊，
如 API 金鑰、密碼和其他機密資料。
"""

import os
import logging
import json
import base64
import threading
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime, timedelta

# 嘗試導入 hvac (HashiCorp Vault 客戶端)
try:
    import hvac
    from hvac.exceptions import InvalidPath, VaultError

    VAULT_AVAILABLE = True
except ImportError:
    VAULT_AVAILABLE = False

from src.core.logger import logger


class VaultClient:
    """
    Vault 客戶端

    提供與 HashiCorp Vault 的整合，用於安全地存儲和管理敏感資訊。
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """實現單例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(VaultClient, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        mount_point: str = "secret",
        path_prefix: str = "trading",
    ):
        """
        初始化 Vault 客戶端

        Args:
            url: Vault 服務器 URL
            token: Vault 令牌
            mount_point: 掛載點
            path_prefix: 路徑前綴
        """
        # 避免重複初始化
        if self._initialized:
            return

        # 檢查 Vault 是否可用
        if not VAULT_AVAILABLE:
            logger.warning("未安裝 hvac 套件，無法使用 Vault 功能")
            self.client = None
            self._initialized = True
            return

        # 獲取 Vault 配置
        self.url = url or os.environ.get("VAULT_ADDR", "http://localhost:8200")
        self.token = token or os.environ.get("VAULT_TOKEN")
        self.mount_point = mount_point
        self.path_prefix = path_prefix

        # 初始化 Vault 客戶端
        try:
            self.client = hvac.Client(url=self.url, token=self.token)
            if not self.client.is_authenticated():
                logger.error("Vault 認證失敗")
                self.client = None
            else:
                logger.info(f"已連接到 Vault 服務器: {self.url}")
        except Exception as e:
            logger.error(f"連接 Vault 服務器時發生錯誤: {e}")
            self.client = None

        self._initialized = True

    def is_available(self) -> bool:
        """
        檢查 Vault 是否可用

        Returns:
            bool: Vault 是否可用
        """
        return (
            VAULT_AVAILABLE
            and self.client is not None
            and self.client.is_authenticated()
        )

    def _get_full_path(self, path: str) -> str:
        """
        獲取完整路徑

        Args:
            path: 路徑

        Returns:
            str: 完整路徑
        """
        return f"{self.path_prefix}/{path}"

    def store_secret(self, path: str, data: Dict[str, Any]) -> bool:
        """
        存儲機密

        Args:
            path: 路徑
            data: 機密數據

        Returns:
            bool: 是否成功
        """
        if not self.is_available():
            logger.warning("Vault 不可用，無法存儲機密")
            return False

        try:
            full_path = self._get_full_path(path)
            self.client.secrets.kv.v2.create_or_update_secret(
                path=full_path,
                secret=data,
                mount_point=self.mount_point,
            )
            logger.info(f"已存儲機密: {full_path}")
            return True
        except Exception as e:
            logger.error(f"存儲機密時發生錯誤: {e}")
            return False

    def get_secret(self, path: str) -> Optional[Dict[str, Any]]:
        """
        獲取機密

        Args:
            path: 路徑

        Returns:
            Optional[Dict[str, Any]]: 機密數據
        """
        if not self.is_available():
            logger.warning("Vault 不可用，無法獲取機密")
            return None

        try:
            full_path = self._get_full_path(path)
            response = self.client.secrets.kv.v2.read_secret_version(
                path=full_path,
                mount_point=self.mount_point,
            )
            return response["data"]["data"]
        except InvalidPath:
            logger.warning(f"機密不存在: {full_path}")
            return None
        except Exception as e:
            logger.error(f"獲取機密時發生錯誤: {e}")
            return None

    def delete_secret(self, path: str) -> bool:
        """
        刪除機密

        Args:
            path: 路徑

        Returns:
            bool: 是否成功
        """
        if not self.is_available():
            logger.warning("Vault 不可用，無法刪除機密")
            return False

        try:
            full_path = self._get_full_path(path)
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=full_path,
                mount_point=self.mount_point,
            )
            logger.info(f"已刪除機密: {full_path}")
            return True
        except Exception as e:
            logger.error(f"刪除機密時發生錯誤: {e}")
            return False

    def store_api_keys(
        self,
        broker_name: str,
        api_key: str,
        api_secret: str,
        account_id: Optional[str] = None,
    ) -> bool:
        """
        存儲 API 金鑰

        Args:
            broker_name: 券商名稱
            api_key: API 金鑰
            api_secret: API 密鑰
            account_id: 帳戶 ID

        Returns:
            bool: 是否成功
        """
        data = {
            "api_key": api_key,
            "api_secret": api_secret,
        }
        if account_id:
            data["account_id"] = account_id

        return self.store_secret(f"api_keys/{broker_name}", data)

    def get_api_keys(self, broker_name: str) -> Optional[Dict[str, str]]:
        """
        獲取 API 金鑰

        Args:
            broker_name: 券商名稱

        Returns:
            Optional[Dict[str, str]]: API 金鑰
        """
        return self.get_secret(f"api_keys/{broker_name}")


# 創建全局 Vault 客戶端實例
vault_client = VaultClient()
