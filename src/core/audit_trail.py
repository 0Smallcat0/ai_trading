"""
審計跟蹤模組

此模組實現了審計跟蹤功能，用於記錄系統中的重要操作和變更，
並確保記錄的不可變性和完整性。
"""

import os
import json
import hashlib
import logging
import threading
import time
from enum import Enum
from typing import Dict, List, Set, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from pathlib import Path

# 嘗試導入加密庫
try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives.serialization import (
        load_pem_private_key,
        load_pem_public_key,
        Encoding,
        PrivateFormat,
        PublicFormat,
        NoEncryption,
    )
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

from src.core.logger import logger


class AuditEventType(str, Enum):
    """審計事件類型"""
    USER_LOGIN = "user_login"  # 用戶登錄
    USER_LOGOUT = "user_logout"  # 用戶登出
    USER_CREATED = "user_created"  # 創建用戶
    USER_UPDATED = "user_updated"  # 更新用戶
    USER_DELETED = "user_deleted"  # 刪除用戶
    PERMISSION_CHANGED = "permission_changed"  # 權限變更
    
    ORDER_CREATED = "order_created"  # 創建訂單
    ORDER_UPDATED = "order_updated"  # 更新訂單
    ORDER_CANCELLED = "order_cancelled"  # 取消訂單
    ORDER_EXECUTED = "order_executed"  # 執行訂單
    
    TRADE_EXECUTED = "trade_executed"  # 執行交易
    TRADE_SETTLED = "trade_settled"  # 結算交易
    
    STRATEGY_CREATED = "strategy_created"  # 創建策略
    STRATEGY_UPDATED = "strategy_updated"  # 更新策略
    STRATEGY_DELETED = "strategy_deleted"  # 刪除策略
    STRATEGY_EXECUTED = "strategy_executed"  # 執行策略
    
    SYSTEM_STARTUP = "system_startup"  # 系統啟動
    SYSTEM_SHUTDOWN = "system_shutdown"  # 系統關閉
    SYSTEM_CONFIG_CHANGED = "system_config_changed"  # 系統配置變更
    
    API_KEY_CREATED = "api_key_created"  # 創建 API 金鑰
    API_KEY_UPDATED = "api_key_updated"  # 更新 API 金鑰
    API_KEY_DELETED = "api_key_deleted"  # 刪除 API 金鑰
    
    DATA_IMPORTED = "data_imported"  # 導入數據
    DATA_EXPORTED = "data_exported"  # 導出數據
    DATA_DELETED = "data_deleted"  # 刪除數據
    
    COMPLIANCE_ALERT = "compliance_alert"  # 合規警報
    SECURITY_ALERT = "security_alert"  # 安全警報


class AuditEvent:
    """審計事件"""
    
    def __init__(
        self,
        event_id: str,
        event_type: AuditEventType,
        user_id: str,
        timestamp: datetime,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """
        初始化審計事件
        
        Args:
            event_id: 事件 ID
            event_type: 事件類型
            user_id: 用戶 ID
            timestamp: 時間戳
            details: 詳細信息
            ip_address: IP 地址
            user_agent: 用戶代理
        """
        self.event_id = event_id
        self.event_type = event_type
        self.user_id = user_id
        self.timestamp = timestamp
        self.details = details
        self.ip_address = ip_address
        self.user_agent = user_agent
        self.signature = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典
        
        Returns:
            Dict[str, Any]: 字典
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "signature": self.signature,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEvent":
        """
        從字典創建
        
        Args:
            data: 字典
            
        Returns:
            AuditEvent: 審計事件
        """
        event = cls(
            event_id=data["event_id"],
            event_type=AuditEventType(data["event_type"]),
            user_id=data["user_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            details=data["details"],
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
        )
        
        event.signature = data.get("signature")
        
        return event
    
    def get_data_for_signature(self) -> str:
        """
        獲取用於簽名的數據
        
        Returns:
            str: 數據
        """
        data = {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }
        
        return json.dumps(data, sort_keys=True)


class AuditTrail:
    """
    審計跟蹤
    
    記錄系統中的重要操作和變更，並確保記錄的不可變性和完整性。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """實現單例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AuditTrail, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(
        self,
        log_dir: str = "logs/audit",
        key_dir: str = "config/keys",
        rotate_interval: int = 86400,  # 24 小時
    ):
        """
        初始化審計跟蹤
        
        Args:
            log_dir: 日誌目錄
            key_dir: 密鑰目錄
            rotate_interval: 日誌輪換間隔（秒）
        """
        # 避免重複初始化
        if self._initialized:
            return
        
        self.log_dir = log_dir
        self.key_dir = key_dir
        self.rotate_interval = rotate_interval
        
        # 創建目錄
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.key_dir, exist_ok=True)
        
        # 當前日誌文件
        self.current_log_file = None
        self.current_log_start_time = None
        
        # 密鑰對
        self.private_key = None
        self.public_key = None
        
        # 加載或生成密鑰對
        self._load_or_generate_keys()
        
        # 初始化日誌文件
        self._init_log_file()
        
        self._initialized = True
    
    def _load_or_generate_keys(self) -> None:
        """加載或生成密鑰對"""
        private_key_path = os.path.join(self.key_dir, "audit_private.pem")
        public_key_path = os.path.join(self.key_dir, "audit_public.pem")
        
        # 檢查密鑰文件是否存在
        if os.path.exists(private_key_path) and os.path.exists(public_key_path):
            # 加載密鑰
            try:
                with open(private_key_path, "rb") as f:
                    self.private_key = load_pem_private_key(
                        f.read(),
                        password=None,
                    )
                
                with open(public_key_path, "rb") as f:
                    self.public_key = load_pem_public_key(f.read())
                
                logger.info("已加載審計密鑰對")
                return
            except Exception as e:
                logger.error(f"加載審計密鑰對時發生錯誤: {e}")
        
        # 生成密鑰對
        if not CRYPTOGRAPHY_AVAILABLE:
            logger.warning("未安裝 cryptography 套件，無法生成密鑰對")
            return
        
        try:
            # 生成私鑰
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            
            # 獲取公鑰
            self.public_key = self.private_key.public_key()
            
            # 保存私鑰
            with open(private_key_path, "wb") as f:
                f.write(
                    self.private_key.private_bytes(
                        encoding=Encoding.PEM,
                        format=PrivateFormat.PKCS8,
                        encryption_algorithm=NoEncryption(),
                    )
                )
            
            # 保存公鑰
            with open(public_key_path, "wb") as f:
                f.write(
                    self.public_key.public_bytes(
                        encoding=Encoding.PEM,
                        format=PublicFormat.SubjectPublicKeyInfo,
                    )
                )
            
            logger.info("已生成審計密鑰對")
        except Exception as e:
            logger.error(f"生成審計密鑰對時發生錯誤: {e}")
    
    def _init_log_file(self) -> None:
        """初始化日誌文件"""
        # 獲取當前時間
        now = datetime.now()
        
        # 設置日誌文件名
        self.current_log_file = os.path.join(
            self.log_dir,
            f"audit_{now.strftime('%Y%m%d_%H%M%S')}.jsonl",
        )
        
        # 記錄開始時間
        self.current_log_start_time = now.timestamp()
        
        logger.info(f"已初始化審計日誌文件: {self.current_log_file}")
    
    def _check_rotate_log(self) -> None:
        """檢查是否需要輪換日誌"""
        # 獲取當前時間
        now = time.time()
        
        # 檢查是否需要輪換
        if (
            self.current_log_start_time is None
            or now - self.current_log_start_time >= self.rotate_interval
        ):
            self._init_log_file()
    
    def _sign_event(self, event: AuditEvent) -> Optional[str]:
        """
        簽名事件
        
        Args:
            event: 審計事件
            
        Returns:
            Optional[str]: 簽名
        """
        if not CRYPTOGRAPHY_AVAILABLE or self.private_key is None:
            return None
        
        try:
            # 獲取數據
            data = event.get_data_for_signature().encode("utf-8")
            
            # 計算簽名
            signature = self.private_key.sign(
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            
            # 返回 Base64 編碼的簽名
            return signature.hex()
        except Exception as e:
            logger.error(f"簽名審計事件時發生錯誤: {e}")
            return None
    
    def _verify_signature(self, event: AuditEvent) -> bool:
        """
        驗證簽名
        
        Args:
            event: 審計事件
            
        Returns:
            bool: 是否有效
        """
        if not CRYPTOGRAPHY_AVAILABLE or self.public_key is None or event.signature is None:
            return False
        
        try:
            # 獲取數據
            data = event.get_data_for_signature().encode("utf-8")
            
            # 解碼簽名
            signature = bytes.fromhex(event.signature)
            
            # 驗證簽名
            self.public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            
            return True
        except Exception:
            return False
    
    def log_event(
        self,
        event_type: AuditEventType,
        user_id: str,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditEvent:
        """
        記錄事件
        
        Args:
            event_type: 事件類型
            user_id: 用戶 ID
            details: 詳細信息
            ip_address: IP 地址
            user_agent: 用戶代理
            
        Returns:
            AuditEvent: 審計事件
        """
        # 檢查是否需要輪換日誌
        self._check_rotate_log()
        
        # 創建事件
        event = AuditEvent(
            event_id=f"{int(time.time() * 1000)}_{user_id}_{event_type.value}",
            event_type=event_type,
            user_id=user_id,
            timestamp=datetime.now(),
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        # 簽名事件
        event.signature = self._sign_event(event)
        
        # 寫入日誌
        try:
            with open(self.current_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"寫入審計日誌時發生錯誤: {e}")
        
        return event
    
    def get_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_types: Optional[List[AuditEventType]] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """
        獲取事件
        
        Args:
            start_time: 開始時間
            end_time: 結束時間
            event_types: 事件類型列表
            user_id: 用戶 ID
            limit: 限制數量
            
        Returns:
            List[AuditEvent]: 事件列表
        """
        events = []
        
        # 獲取日誌文件列表
        log_files = sorted(
            [f for f in os.listdir(self.log_dir) if f.startswith("audit_") and f.endswith(".jsonl")],
            reverse=True,
        )
        
        # 讀取日誌文件
        for log_file in log_files:
            file_path = os.path.join(self.log_dir, log_file)
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        # 解析事件
                        try:
                            event_data = json.loads(line.strip())
                            event = AuditEvent.from_dict(event_data)
                            
                            # 檢查時間範圍
                            if start_time and event.timestamp < start_time:
                                continue
                            
                            if end_time and event.timestamp > end_time:
                                continue
                            
                            # 檢查事件類型
                            if event_types and event.event_type not in event_types:
                                continue
                            
                            # 檢查用戶 ID
                            if user_id and event.user_id != user_id:
                                continue
                            
                            # 驗證簽名
                            if not self._verify_signature(event):
                                logger.warning(f"審計事件簽名無效: {event.event_id}")
                                continue
                            
                            events.append(event)
                            
                            # 檢查限制
                            if len(events) >= limit:
                                return events
                        except Exception as e:
                            logger.error(f"解析審計事件時發生錯誤: {e}")
            except Exception as e:
                logger.error(f"讀取審計日誌文件時發生錯誤: {e}")
        
        return events


# 創建全局審計跟蹤實例
audit_trail = AuditTrail()
