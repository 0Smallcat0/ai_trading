# -*- coding: utf-8 -*-
"""
API金鑰安全管理模組

此模組提供API金鑰的安全存儲、管理和輪換功能。

主要功能：
- API金鑰加密存儲
- 環境變數管理
- 金鑰輪換機制
- 權限控制
- 使用追蹤
"""

import logging
import os
import json
import hashlib
import secrets
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# 設定日誌
logger = logging.getLogger(__name__)


class KeyStatus(Enum):
    """金鑰狀態枚舉"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    REVOKED = "revoked"


class PermissionLevel(Enum):
    """權限等級枚舉"""
    READ_ONLY = "read_only"
    LIMITED = "limited"
    FULL_ACCESS = "full_access"
    ADMIN = "admin"


@dataclass
class APIKeyInfo:
    """API金鑰信息"""
    key_id: str
    provider: str
    key_hash: str
    status: KeyStatus
    permission_level: PermissionLevel
    created_at: datetime
    last_used: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    usage_count: int = 0
    daily_limit: Optional[int] = None
    monthly_limit: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class APIKeySecurityError(Exception):
    """API金鑰安全錯誤基類"""


class APIKeyNotFoundError(APIKeySecurityError):
    """API金鑰未找到錯誤"""


class APIKeyExpiredError(APIKeySecurityError):
    """API金鑰過期錯誤"""


class APIKeyPermissionError(APIKeySecurityError):
    """API金鑰權限錯誤"""


class APIKeyManager:
    """API金鑰管理器"""

    def __init__(
        self,
        storage_path: str = "config/keys",
        master_key: Optional[str] = None,
        auto_rotation_days: int = 90
    ):
        """初始化API金鑰管理器。

        Args:
            storage_path: 金鑰存儲路徑
            master_key: 主加密金鑰
            auto_rotation_days: 自動輪換天數
        """
        self.storage_path = storage_path
        self.auto_rotation_days = auto_rotation_days
        
        # 確保存儲目錄存在
        os.makedirs(storage_path, exist_ok=True)
        
        # 初始化加密器
        self._init_encryption(master_key)
        
        # 載入金鑰信息
        self.keys_info = self._load_keys_info()
        
        # 使用統計
        self.usage_stats = {
            'total_requests': 0,
            'daily_requests': {},
            'provider_usage': {}
        }

    def _init_encryption(self, master_key: Optional[str] = None) -> None:
        """初始化加密器。

        Args:
            master_key: 主加密金鑰
        """
        if master_key:
            # 使用提供的主金鑰
            key = master_key.encode()
        else:
            # 從環境變數獲取或生成新的主金鑰
            key = os.environ.get('API_KEY_MASTER_KEY')
            if not key:
                # 生成新的主金鑰並保存到環境變數
                key = Fernet.generate_key()
                logger.warning("生成新的主加密金鑰，請將其保存到環境變數 API_KEY_MASTER_KEY")
                logger.warning(f"主金鑰: {key.decode()}")
            else:
                key = key.encode()
        
        # 創建加密器
        if len(key) != 44:  # Fernet金鑰長度
            # 使用PBKDF2從密碼派生金鑰
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'api_key_salt',  # 在生產環境中應使用隨機鹽
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(key))
        
        self.cipher = Fernet(key)

    def _load_keys_info(self) -> Dict[str, APIKeyInfo]:
        """載入金鑰信息。

        Returns:
            金鑰信息字典
        """
        info_file = os.path.join(self.storage_path, 'keys_info.json')
        
        if not os.path.exists(info_file):
            return {}
        
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            keys_info = {}
            for key_id, info_dict in data.items():
                # 轉換日期字符串為datetime對象
                info_dict['created_at'] = datetime.fromisoformat(info_dict['created_at'])
                if info_dict.get('last_used'):
                    info_dict['last_used'] = datetime.fromisoformat(info_dict['last_used'])
                if info_dict.get('expires_at'):
                    info_dict['expires_at'] = datetime.fromisoformat(info_dict['expires_at'])
                
                # 轉換枚舉
                info_dict['status'] = KeyStatus(info_dict['status'])
                info_dict['permission_level'] = PermissionLevel(info_dict['permission_level'])
                
                keys_info[key_id] = APIKeyInfo(**info_dict)
            
            return keys_info
            
        except Exception as e:
            logger.error(f"載入金鑰信息失敗: {e}")
            return {}

    def _save_keys_info(self) -> None:
        """保存金鑰信息。"""
        info_file = os.path.join(self.storage_path, 'keys_info.json')
        
        try:
            # 轉換為可序列化的格式
            data = {}
            for key_id, info in self.keys_info.items():
                info_dict = asdict(info)
                # 轉換datetime為字符串
                info_dict['created_at'] = info.created_at.isoformat()
                if info.last_used:
                    info_dict['last_used'] = info.last_used.isoformat()
                if info.expires_at:
                    info_dict['expires_at'] = info.expires_at.isoformat()
                
                # 轉換枚舉為字符串
                info_dict['status'] = info.status.value
                info_dict['permission_level'] = info.permission_level.value
                
                data[key_id] = info_dict
            
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.error(f"保存金鑰信息失敗: {e}")

    def add_api_key(
        self,
        provider: str,
        api_key: str,
        permission_level: PermissionLevel = PermissionLevel.LIMITED,
        expires_days: Optional[int] = None,
        daily_limit: Optional[int] = None,
        monthly_limit: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """添加API金鑰。

        Args:
            provider: 提供商名稱
            api_key: API金鑰
            permission_level: 權限等級
            expires_days: 過期天數
            daily_limit: 日使用限制
            monthly_limit: 月使用限制
            metadata: 元數據

        Returns:
            金鑰ID

        Raises:
            APIKeySecurityError: 當添加失敗時
        """
        try:
            # 生成金鑰ID
            key_id = self._generate_key_id(provider)
            
            # 計算金鑰哈希
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # 加密並存儲金鑰
            encrypted_key = self.cipher.encrypt(api_key.encode())
            key_file = os.path.join(self.storage_path, f"{key_id}.key")
            
            with open(key_file, 'wb') as f:
                f.write(encrypted_key)
            
            # 創建金鑰信息
            expires_at = None
            if expires_days:
                expires_at = datetime.now() + timedelta(days=expires_days)
            
            key_info = APIKeyInfo(
                key_id=key_id,
                provider=provider,
                key_hash=key_hash,
                status=KeyStatus.ACTIVE,
                permission_level=permission_level,
                created_at=datetime.now(),
                expires_at=expires_at,
                daily_limit=daily_limit,
                monthly_limit=monthly_limit,
                metadata=metadata or {}
            )
            
            # 保存金鑰信息
            self.keys_info[key_id] = key_info
            self._save_keys_info()
            
            logger.info(f"添加API金鑰成功: {key_id} ({provider})")
            return key_id
            
        except Exception as e:
            logger.error(f"添加API金鑰失敗: {e}")
            raise APIKeySecurityError(f"添加API金鑰失敗: {e}") from e

    def get_api_key(self, key_id: str) -> str:
        """獲取API金鑰。

        Args:
            key_id: 金鑰ID

        Returns:
            解密的API金鑰

        Raises:
            APIKeyNotFoundError: 當金鑰不存在時
            APIKeyExpiredError: 當金鑰過期時
            APIKeySecurityError: 當解密失敗時
        """
        # 檢查金鑰是否存在
        if key_id not in self.keys_info:
            raise APIKeyNotFoundError(f"API金鑰不存在: {key_id}")
        
        key_info = self.keys_info[key_id]
        
        # 檢查金鑰狀態
        if key_info.status != KeyStatus.ACTIVE:
            raise APIKeyExpiredError(f"API金鑰狀態無效: {key_info.status.value}")
        
        # 檢查是否過期
        if key_info.expires_at and datetime.now() > key_info.expires_at:
            # 自動標記為過期
            key_info.status = KeyStatus.EXPIRED
            self._save_keys_info()
            raise APIKeyExpiredError(f"API金鑰已過期: {key_id}")
        
        try:
            # 讀取並解密金鑰
            key_file = os.path.join(self.storage_path, f"{key_id}.key")
            
            with open(key_file, 'rb') as f:
                encrypted_key = f.read()
            
            decrypted_key = self.cipher.decrypt(encrypted_key).decode()
            
            # 更新使用記錄
            key_info.last_used = datetime.now()
            key_info.usage_count += 1
            self._save_keys_info()
            
            return decrypted_key
            
        except Exception as e:
            logger.error(f"獲取API金鑰失敗: {e}")
            raise APIKeySecurityError(f"獲取API金鑰失敗: {e}") from e

    def revoke_api_key(self, key_id: str) -> None:
        """撤銷API金鑰。

        Args:
            key_id: 金鑰ID

        Raises:
            APIKeyNotFoundError: 當金鑰不存在時
        """
        if key_id not in self.keys_info:
            raise APIKeyNotFoundError(f"API金鑰不存在: {key_id}")
        
        # 標記為撤銷
        self.keys_info[key_id].status = KeyStatus.REVOKED
        self._save_keys_info()
        
        # 刪除金鑰文件
        key_file = os.path.join(self.storage_path, f"{key_id}.key")
        if os.path.exists(key_file):
            os.remove(key_file)
        
        logger.info(f"撤銷API金鑰: {key_id}")

    def rotate_api_key(self, key_id: str, new_api_key: str) -> None:
        """輪換API金鑰。

        Args:
            key_id: 金鑰ID
            new_api_key: 新的API金鑰

        Raises:
            APIKeyNotFoundError: 當金鑰不存在時
            APIKeySecurityError: 當輪換失敗時
        """
        if key_id not in self.keys_info:
            raise APIKeyNotFoundError(f"API金鑰不存在: {key_id}")
        
        try:
            key_info = self.keys_info[key_id]
            
            # 更新金鑰哈希
            key_info.key_hash = hashlib.sha256(new_api_key.encode()).hexdigest()
            
            # 加密並保存新金鑰
            encrypted_key = self.cipher.encrypt(new_api_key.encode())
            key_file = os.path.join(self.storage_path, f"{key_id}.key")
            
            with open(key_file, 'wb') as f:
                f.write(encrypted_key)
            
            # 重置使用統計
            key_info.usage_count = 0
            key_info.last_used = None
            
            # 延長過期時間
            if key_info.expires_at:
                key_info.expires_at = datetime.now() + timedelta(days=self.auto_rotation_days)
            
            self._save_keys_info()
            
            logger.info(f"輪換API金鑰成功: {key_id}")
            
        except Exception as e:
            logger.error(f"輪換API金鑰失敗: {e}")
            raise APIKeySecurityError(f"輪換API金鑰失敗: {e}") from e

    def check_permission(self, key_id: str, required_level: PermissionLevel) -> bool:
        """檢查權限。

        Args:
            key_id: 金鑰ID
            required_level: 所需權限等級

        Returns:
            是否有權限

        Raises:
            APIKeyNotFoundError: 當金鑰不存在時
        """
        if key_id not in self.keys_info:
            raise APIKeyNotFoundError(f"API金鑰不存在: {key_id}")
        
        key_info = self.keys_info[key_id]
        
        # 權限等級映射
        level_hierarchy = {
            PermissionLevel.READ_ONLY: 1,
            PermissionLevel.LIMITED: 2,
            PermissionLevel.FULL_ACCESS: 3,
            PermissionLevel.ADMIN: 4
        }
        
        current_level = level_hierarchy.get(key_info.permission_level, 0)
        required_level_value = level_hierarchy.get(required_level, 0)
        
        return current_level >= required_level_value

    def _generate_key_id(self, provider: str) -> str:
        """生成金鑰ID。

        Args:
            provider: 提供商名稱

        Returns:
            金鑰ID
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_suffix = secrets.token_hex(4)
        return f"{provider}_{timestamp}_{random_suffix}"

    def list_keys(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出金鑰。

        Args:
            provider: 提供商過濾

        Returns:
            金鑰信息列表
        """
        keys = []
        
        for key_id, info in self.keys_info.items():
            if provider and info.provider != provider:
                continue
            
            key_data = {
                'key_id': key_id,
                'provider': info.provider,
                'status': info.status.value,
                'permission_level': info.permission_level.value,
                'created_at': info.created_at.isoformat(),
                'last_used': info.last_used.isoformat() if info.last_used else None,
                'expires_at': info.expires_at.isoformat() if info.expires_at else None,
                'usage_count': info.usage_count,
                'daily_limit': info.daily_limit,
                'monthly_limit': info.monthly_limit
            }
            
            keys.append(key_data)
        
        return keys

    def get_usage_stats(self) -> Dict[str, Any]:
        """獲取使用統計。

        Returns:
            使用統計字典
        """
        stats = {
            'total_keys': len(self.keys_info),
            'active_keys': len([k for k in self.keys_info.values() if k.status == KeyStatus.ACTIVE]),
            'expired_keys': len([k for k in self.keys_info.values() if k.status == KeyStatus.EXPIRED]),
            'revoked_keys': len([k for k in self.keys_info.values() if k.status == KeyStatus.REVOKED]),
            'provider_distribution': {},
            'permission_distribution': {}
        }
        
        # 統計提供商分佈
        for info in self.keys_info.values():
            provider = info.provider
            if provider not in stats['provider_distribution']:
                stats['provider_distribution'][provider] = 0
            stats['provider_distribution'][provider] += 1
        
        # 統計權限分佈
        for info in self.keys_info.values():
            level = info.permission_level.value
            if level not in stats['permission_distribution']:
                stats['permission_distribution'][level] = 0
            stats['permission_distribution'][level] += 1
        
        return stats
