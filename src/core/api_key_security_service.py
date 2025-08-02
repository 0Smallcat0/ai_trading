"""
券商 API 金鑰安全管理服務

此模組實現了完整的 API 金鑰安全管理功能，包括：
- API 金鑰加密存儲
- 定期輪換機制
- 權限控制
- 使用監控
- 存取審計
- 金鑰生命週期管理

遵循金融級安全標準，確保 API 金鑰的安全性。
"""

import logging
import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import threading

# 導入加密相關庫
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# 導入資料庫相關模組
from sqlalchemy import create_engine, and_, or_, desc
from sqlalchemy.orm import sessionmaker, Session

# 導入配置和資料庫模型
from src.config import DB_URL
from src.database.schema import User, SecurityEvent, AuditLog

# 設置日誌
logger = logging.getLogger(__name__)


class KeyStatus(Enum):
    """API 金鑰狀態"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING_ROTATION = "pending_rotation"


class KeyPermission(Enum):
    """API 金鑰權限"""
    READ_ONLY = "read_only"
    TRADE_BASIC = "trade_basic"
    TRADE_ADVANCED = "trade_advanced"
    ADMIN = "admin"


class APIKeySecurityService:
    """
    API 金鑰安全管理服務
    
    提供完整的 API 金鑰安全管理功能，包括加密存儲、
    權限控制、使用監控和定期輪換。
    """
    
    def __init__(self):
        """初始化 API 金鑰安全服務"""
        try:
            # 初始化資料庫連接
            self.engine = create_engine(DB_URL)
            self.session_factory = sessionmaker(bind=self.engine)
            logger.info("API 金鑰安全服務資料庫連接初始化成功")
            
            # 初始化加密設定
            self._init_encryption()
            
            # 服務配置
            self.config = {
                "key_rotation_days": 90,  # 金鑰輪換週期（天）
                "max_keys_per_user": 5,   # 每個使用者最大金鑰數量
                "key_expiry_warning_days": 7,  # 過期警告天數
                "audit_retention_days": 365,   # 審計記錄保留天數
                "rate_limit_per_hour": 1000,   # 每小時使用次數限制
                "encryption_algorithm": "AES-256",
                "key_length": 32,  # 金鑰長度（字節）
            }
            
            # 記憶體中的金鑰快取（用於提高性能）
            self._key_cache = {}
            self._cache_lock = threading.RLock()
            
            # 使用統計
            self._usage_stats = {}
            self._stats_lock = threading.RLock()
            
            logger.info("API 金鑰安全服務初始化完成")
            
        except Exception as e:
            logger.error(f"API 金鑰安全服務初始化失敗: {e}")
            raise
    
    def _init_encryption(self):
        """初始化加密設定"""
        try:
            # 生成或載入主加密金鑰
            self.master_key = self._get_or_create_master_key()
            self.fernet = Fernet(self.master_key)
            logger.info("加密設定初始化成功")
        except Exception as e:
            logger.error(f"加密設定初始化失敗: {e}")
            raise
    
    def _get_or_create_master_key(self) -> bytes:
        """獲取或創建主加密金鑰"""
        # 在實際環境中，這應該從安全的金鑰管理系統（如 HSM 或 Vault）中獲取
        # 這裡使用簡化的實作
        master_key_file = "config/master.key"
        
        try:
            # 嘗試讀取現有金鑰
            with open(master_key_file, "rb") as f:
                return f.read()
        except FileNotFoundError:
            # 生成新的主金鑰
            key = Fernet.generate_key()
            
            # 確保目錄存在
            import os
            os.makedirs(os.path.dirname(master_key_file), exist_ok=True)
            
            # 保存金鑰
            with open(master_key_file, "wb") as f:
                f.write(key)
            
            # 設置文件權限（僅所有者可讀寫）
            os.chmod(master_key_file, 0o600)
            
            logger.info("已生成新的主加密金鑰")
            return key
    
    def create_api_key(
        self,
        user_id: str,
        broker_name: str,
        api_key: str,
        api_secret: str,
        permissions: List[KeyPermission],
        description: str = "",
        expires_at: Optional[datetime] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        創建新的 API 金鑰記錄
        
        Args:
            user_id: 使用者 ID
            broker_name: 券商名稱
            api_key: API 金鑰
            api_secret: API 密鑰
            permissions: 權限列表
            description: 描述
            expires_at: 過期時間
            
        Returns:
            Tuple[bool, str, Optional[str]]: (是否成功, 訊息, 金鑰 ID)
        """
        try:
            with self.session_factory() as session:
                # 檢查使用者是否存在
                user = session.query(User).filter(User.user_id == user_id).first()
                if not user:
                    return False, "使用者不存在", None
                
                # 檢查金鑰數量限制
                existing_keys = self._get_user_active_keys_count(session, user_id)
                if existing_keys >= self.config["max_keys_per_user"]:
                    return False, f"已達到最大金鑰數量限制 ({self.config['max_keys_per_user']})", None
                
                # 生成金鑰 ID
                key_id = self._generate_key_id()
                
                # 加密 API 金鑰和密鑰
                encrypted_api_key = self._encrypt_data(api_key)
                encrypted_api_secret = self._encrypt_data(api_secret)
                
                # 設置過期時間（如果未指定，則使用預設輪換週期）
                if expires_at is None:
                    expires_at = datetime.now() + timedelta(days=self.config["key_rotation_days"])
                
                # 創建金鑰記錄
                key_record = {
                    "key_id": key_id,
                    "user_id": user_id,
                    "broker_name": broker_name,
                    "encrypted_api_key": encrypted_api_key,
                    "encrypted_api_secret": encrypted_api_secret,
                    "permissions": [p.value for p in permissions],
                    "description": description,
                    "status": KeyStatus.ACTIVE.value,
                    "created_at": datetime.now(),
                    "expires_at": expires_at,
                    "last_used_at": None,
                    "usage_count": 0,
                }
                
                # 保存到資料庫（這裡需要創建對應的資料庫表）
                self._save_key_record(session, key_record)
                
                # 記錄安全事件
                self._log_security_event(
                    session,
                    user_id,
                    "api_key_created",
                    "medium",
                    f"創建 {broker_name} API 金鑰",
                    {
                        "key_id": key_id,
                        "broker_name": broker_name,
                        "permissions": [p.value for p in permissions]
                    }
                )
                
                session.commit()
                
                logger.info(f"使用者 {user_id} 成功創建 {broker_name} API 金鑰: {key_id}")
                
                return True, "API 金鑰創建成功", key_id
                
        except Exception as e:
            logger.error(f"創建 API 金鑰失敗: {e}")
            return False, f"創建失敗: {str(e)}", None
    
    def get_api_key(
        self,
        user_id: str,
        key_id: str,
        check_permissions: bool = True
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        獲取 API 金鑰
        
        Args:
            user_id: 使用者 ID
            key_id: 金鑰 ID
            check_permissions: 是否檢查權限
            
        Returns:
            Tuple[bool, str, Optional[Dict[str, Any]]]: (是否成功, 訊息, 金鑰資料)
        """
        try:
            with self.session_factory() as session:
                # 檢查快取
                cache_key = f"{user_id}:{key_id}"
                with self._cache_lock:
                    if cache_key in self._key_cache:
                        cached_data = self._key_cache[cache_key]
                        if cached_data["expires"] > datetime.now():
                            return True, "獲取成功", cached_data["data"]
                
                # 從資料庫獲取
                key_record = self._get_key_record(session, key_id)
                if not key_record:
                    return False, "API 金鑰不存在", None
                
                # 檢查權限
                if check_permissions and key_record["user_id"] != user_id:
                    self._log_security_event(
                        session,
                        user_id,
                        "api_key_access_denied",
                        "high",
                        f"嘗試存取他人的 API 金鑰",
                        {"key_id": key_id, "owner_id": key_record["user_id"]}
                    )
                    return False, "無權限存取此 API 金鑰", None
                
                # 檢查金鑰狀態
                if key_record["status"] != KeyStatus.ACTIVE.value:
                    return False, f"API 金鑰狀態異常: {key_record['status']}", None
                
                # 檢查是否過期
                if key_record["expires_at"] and key_record["expires_at"] < datetime.now():
                    self._update_key_status(session, key_id, KeyStatus.EXPIRED)
                    return False, "API 金鑰已過期", None
                
                # 解密金鑰
                try:
                    api_key = self._decrypt_data(key_record["encrypted_api_key"])
                    api_secret = self._decrypt_data(key_record["encrypted_api_secret"])
                except Exception as e:
                    logger.error(f"解密 API 金鑰失敗: {e}")
                    return False, "金鑰解密失敗", None
                
                # 更新使用統計
                self._update_usage_stats(session, key_id)
                
                # 準備返回資料
                key_data = {
                    "key_id": key_id,
                    "broker_name": key_record["broker_name"],
                    "api_key": api_key,
                    "api_secret": api_secret,
                    "permissions": key_record["permissions"],
                    "description": key_record["description"],
                    "expires_at": key_record["expires_at"],
                }
                
                # 更新快取
                with self._cache_lock:
                    self._key_cache[cache_key] = {
                        "data": key_data,
                        "expires": datetime.now() + timedelta(minutes=15)  # 快取 15 分鐘
                    }
                
                # 記錄存取事件
                self._log_security_event(
                    session,
                    user_id,
                    "api_key_accessed",
                    "low",
                    f"存取 {key_record['broker_name']} API 金鑰",
                    {"key_id": key_id}
                )
                
                session.commit()
                
                return True, "獲取成功", key_data
                
        except Exception as e:
            logger.error(f"獲取 API 金鑰失敗: {e}")
            return False, f"獲取失敗: {str(e)}", None
    
    def rotate_api_key(
        self,
        user_id: str,
        key_id: str,
        new_api_key: str,
        new_api_secret: str
    ) -> Tuple[bool, str]:
        """
        輪換 API 金鑰
        
        Args:
            user_id: 使用者 ID
            key_id: 金鑰 ID
            new_api_key: 新的 API 金鑰
            new_api_secret: 新的 API 密鑰
            
        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            with self.session_factory() as session:
                # 獲取現有金鑰記錄
                key_record = self._get_key_record(session, key_id)
                if not key_record:
                    return False, "API 金鑰不存在"
                
                # 檢查權限
                if key_record["user_id"] != user_id:
                    return False, "無權限輪換此 API 金鑰"
                
                # 備份舊金鑰（用於回滾）
                old_key_backup = {
                    "key_id": key_id,
                    "encrypted_api_key": key_record["encrypted_api_key"],
                    "encrypted_api_secret": key_record["encrypted_api_secret"],
                    "rotated_at": datetime.now(),
                }
                self._save_key_backup(session, old_key_backup)
                
                # 加密新金鑰
                encrypted_new_api_key = self._encrypt_data(new_api_key)
                encrypted_new_api_secret = self._encrypt_data(new_api_secret)
                
                # 更新金鑰記錄
                self._update_key_record(session, key_id, {
                    "encrypted_api_key": encrypted_new_api_key,
                    "encrypted_api_secret": encrypted_new_api_secret,
                    "last_rotated_at": datetime.now(),
                    "expires_at": datetime.now() + timedelta(days=self.config["key_rotation_days"]),
                    "rotation_count": key_record.get("rotation_count", 0) + 1,
                })
                
                # 清除快取
                cache_key = f"{user_id}:{key_id}"
                with self._cache_lock:
                    if cache_key in self._key_cache:
                        del self._key_cache[cache_key]
                
                # 記錄安全事件
                self._log_security_event(
                    session,
                    user_id,
                    "api_key_rotated",
                    "medium",
                    f"輪換 {key_record['broker_name']} API 金鑰",
                    {
                        "key_id": key_id,
                        "rotation_count": key_record.get("rotation_count", 0) + 1
                    }
                )
                
                session.commit()
                
                logger.info(f"使用者 {user_id} 成功輪換 API 金鑰: {key_id}")
                
                return True, "API 金鑰輪換成功"
                
        except Exception as e:
            logger.error(f"輪換 API 金鑰失敗: {e}")
            return False, f"輪換失敗: {str(e)}"
    
    def revoke_api_key(self, user_id: str, key_id: str, reason: str = "") -> Tuple[bool, str]:
        """
        撤銷 API 金鑰
        
        Args:
            user_id: 使用者 ID
            key_id: 金鑰 ID
            reason: 撤銷原因
            
        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            with self.session_factory() as session:
                # 獲取金鑰記錄
                key_record = self._get_key_record(session, key_id)
                if not key_record:
                    return False, "API 金鑰不存在"
                
                # 檢查權限
                if key_record["user_id"] != user_id:
                    return False, "無權限撤銷此 API 金鑰"
                
                # 更新狀態為撤銷
                self._update_key_status(session, key_id, KeyStatus.REVOKED, reason)
                
                # 清除快取
                cache_key = f"{user_id}:{key_id}"
                with self._cache_lock:
                    if cache_key in self._key_cache:
                        del self._key_cache[cache_key]
                
                # 記錄安全事件
                self._log_security_event(
                    session,
                    user_id,
                    "api_key_revoked",
                    "high",
                    f"撤銷 {key_record['broker_name']} API 金鑰",
                    {
                        "key_id": key_id,
                        "reason": reason
                    }
                )
                
                session.commit()
                
                logger.info(f"使用者 {user_id} 撤銷 API 金鑰: {key_id}, 原因: {reason}")
                
                return True, "API 金鑰已撤銷"
                
        except Exception as e:
            logger.error(f"撤銷 API 金鑰失敗: {e}")
            return False, f"撤銷失敗: {str(e)}"

    def list_user_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """
        列出使用者的所有 API 金鑰

        Args:
            user_id: 使用者 ID

        Returns:
            List[Dict[str, Any]]: API 金鑰列表
        """
        try:
            with self.session_factory() as session:
                key_records = self._get_user_key_records(session, user_id)

                result = []
                for record in key_records:
                    # 不返回敏感資料
                    key_info = {
                        "key_id": record["key_id"],
                        "broker_name": record["broker_name"],
                        "description": record["description"],
                        "permissions": record["permissions"],
                        "status": record["status"],
                        "created_at": record["created_at"],
                        "expires_at": record["expires_at"],
                        "last_used_at": record["last_used_at"],
                        "usage_count": record["usage_count"],
                        "is_expiring_soon": self._is_expiring_soon(record["expires_at"]),
                    }
                    result.append(key_info)

                return result

        except Exception as e:
            logger.error(f"列出使用者 API 金鑰失敗: {e}")
            return []

    def get_usage_statistics(self, user_id: str, key_id: Optional[str] = None) -> Dict[str, Any]:
        """
        獲取使用統計

        Args:
            user_id: 使用者 ID
            key_id: 金鑰 ID（可選）

        Returns:
            Dict[str, Any]: 使用統計資料
        """
        try:
            with self.session_factory() as session:
                if key_id:
                    # 獲取特定金鑰的統計
                    stats = self._get_key_usage_stats(session, key_id)
                else:
                    # 獲取使用者所有金鑰的統計
                    stats = self._get_user_usage_stats(session, user_id)

                return stats

        except Exception as e:
            logger.error(f"獲取使用統計失敗: {e}")
            return {}

    def check_expiring_keys(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        檢查即將過期的金鑰

        Args:
            user_id: 使用者 ID（可選，如果不提供則檢查所有使用者）

        Returns:
            List[Dict[str, Any]]: 即將過期的金鑰列表
        """
        try:
            with self.session_factory() as session:
                warning_date = datetime.now() + timedelta(days=self.config["key_expiry_warning_days"])

                if user_id:
                    expiring_keys = self._get_user_expiring_keys(session, user_id, warning_date)
                else:
                    expiring_keys = self._get_all_expiring_keys(session, warning_date)

                return expiring_keys

        except Exception as e:
            logger.error(f"檢查即將過期的金鑰失敗: {e}")
            return []

    def validate_key_permissions(
        self,
        user_id: str,
        key_id: str,
        required_permission: KeyPermission
    ) -> bool:
        """
        驗證金鑰權限

        Args:
            user_id: 使用者 ID
            key_id: 金鑰 ID
            required_permission: 所需權限

        Returns:
            bool: 是否有權限
        """
        try:
            success, message, key_data = self.get_api_key(user_id, key_id, check_permissions=True)

            if not success or not key_data:
                return False

            permissions = key_data.get("permissions", [])

            # 檢查是否有管理員權限
            if KeyPermission.ADMIN.value in permissions:
                return True

            # 檢查特定權限
            if required_permission.value in permissions:
                return True

            # 檢查權限層級
            permission_levels = {
                KeyPermission.READ_ONLY: 1,
                KeyPermission.TRADE_BASIC: 2,
                KeyPermission.TRADE_ADVANCED: 3,
                KeyPermission.ADMIN: 4,
            }

            user_max_level = max(
                permission_levels.get(KeyPermission(p), 0) for p in permissions
            )
            required_level = permission_levels.get(required_permission, 0)

            return user_max_level >= required_level

        except Exception as e:
            logger.error(f"驗證金鑰權限失敗: {e}")
            return False

    def _encrypt_data(self, data: str) -> str:
        """加密資料"""
        try:
            encrypted_data = self.fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"加密資料失敗: {e}")
            raise

    def _decrypt_data(self, encrypted_data: str) -> str:
        """解密資料"""
        try:
            decoded_data = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.fernet.decrypt(decoded_data)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"解密資料失敗: {e}")
            raise

    def _generate_key_id(self) -> str:
        """生成金鑰 ID"""
        return f"key_{secrets.token_urlsafe(16)}"

    def _is_expiring_soon(self, expires_at: Optional[datetime]) -> bool:
        """檢查是否即將過期"""
        if not expires_at:
            return False

        warning_date = datetime.now() + timedelta(days=self.config["key_expiry_warning_days"])
        return expires_at <= warning_date

    def _get_user_active_keys_count(self, session: Session, user_id: str) -> int:
        """獲取使用者活躍金鑰數量"""
        # 這裡需要實作資料庫查詢
        # 簡化實作，返回固定值
        return 0

    def _save_key_record(self, session: Session, key_record: Dict[str, Any]) -> None:
        """保存金鑰記錄到資料庫"""
        # 這裡需要實作資料庫保存邏輯
        # 簡化實作
        pass

    def _get_key_record(self, session: Session, key_id: str) -> Optional[Dict[str, Any]]:
        """從資料庫獲取金鑰記錄"""
        # 這裡需要實作資料庫查詢邏輯
        # 簡化實作，返回模擬資料
        return {
            "key_id": key_id,
            "user_id": "test_user",
            "broker_name": "test_broker",
            "encrypted_api_key": "encrypted_key",
            "encrypted_api_secret": "encrypted_secret",
            "permissions": ["read_only"],
            "description": "Test key",
            "status": KeyStatus.ACTIVE.value,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(days=90),
            "last_used_at": None,
            "usage_count": 0,
        }

    def _update_key_status(
        self,
        session: Session,
        key_id: str,
        status: KeyStatus,
        reason: str = ""
    ) -> None:
        """更新金鑰狀態"""
        # 這裡需要實作資料庫更新邏輯
        pass

    def _update_key_record(
        self,
        session: Session,
        key_id: str,
        updates: Dict[str, Any]
    ) -> None:
        """更新金鑰記錄"""
        # 這裡需要實作資料庫更新邏輯
        pass

    def _save_key_backup(self, session: Session, backup_data: Dict[str, Any]) -> None:
        """保存金鑰備份"""
        # 這裡需要實作備份邏輯
        pass

    def _update_usage_stats(self, session: Session, key_id: str) -> None:
        """更新使用統計"""
        # 這裡需要實作統計更新邏輯
        pass

    def _get_user_key_records(self, session: Session, user_id: str) -> List[Dict[str, Any]]:
        """獲取使用者的所有金鑰記錄"""
        # 這裡需要實作資料庫查詢邏輯
        return []

    def _get_key_usage_stats(self, session: Session, key_id: str) -> Dict[str, Any]:
        """獲取金鑰使用統計"""
        return {
            "total_requests": 0,
            "requests_today": 0,
            "requests_this_week": 0,
            "requests_this_month": 0,
            "last_used_at": None,
            "average_requests_per_day": 0,
        }

    def _get_user_usage_stats(self, session: Session, user_id: str) -> Dict[str, Any]:
        """獲取使用者使用統計"""
        return {
            "total_keys": 0,
            "active_keys": 0,
            "total_requests": 0,
            "requests_today": 0,
        }

    def _get_user_expiring_keys(
        self,
        session: Session,
        user_id: str,
        warning_date: datetime
    ) -> List[Dict[str, Any]]:
        """獲取使用者即將過期的金鑰"""
        return []

    def _get_all_expiring_keys(
        self,
        session: Session,
        warning_date: datetime
    ) -> List[Dict[str, Any]]:
        """獲取所有即將過期的金鑰"""
        return []

    def _log_security_event(
        self,
        session: Session,
        user_id: str,
        event_type: str,
        severity: str,
        description: str,
        details: Dict[str, Any]
    ) -> None:
        """記錄安全事件"""
        try:
            event = SecurityEvent(
                event_id=secrets.token_urlsafe(16),
                event_type=event_type,
                event_level=severity,
                user_id=user_id,
                description=description,
                event_details=details,
                ip_address="127.0.0.1",  # 實際應該從請求中獲取
                user_agent="System",
                created_at=datetime.now()
            )

            session.add(event)

        except Exception as e:
            logger.error(f"記錄安全事件失敗: {e}")
