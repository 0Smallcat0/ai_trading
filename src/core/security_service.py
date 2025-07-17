"""
安全服務

此模組實現了系統安全管理的核心功能，包括：
- 權限管理與角色控制
- 重要操作安全確認
- 操作日誌與審計追蹤
- 數據安全與隱私保護
- 安全事件監控與響應

遵循與其他服務層相同的架構模式，提供完整的安全管理功能。
"""

import logging
import os
import uuid
import hashlib
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
import ipaddress

# 導入加密相關庫
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    import hashlib
    import secrets

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# 導入資料庫相關模組
from sqlalchemy import create_engine, desc, func, and_, or_
from sqlalchemy.orm import sessionmaker, Session

# 導入配置和資料庫模型
from src.config import DB_URL
from src.database.schema import (
    User,
    Role,
    UserRole,
    Permission,
    SecurityEvent,
    AuditLog,
    UserSession,
)

# 設置日誌
logger = logging.getLogger(__name__)


class SecurityService:
    """
    安全服務

    提供完整的系統安全管理功能，包括權限控制、安全監控、
    審計追蹤和數據保護。
    """

    def __init__(self):
        """初始化安全服務"""
        try:
            # 初始化資料庫連接
            self.engine = create_engine(DB_URL)
            self.session_factory = sessionmaker(bind=self.engine)
            logger.info("安全服務資料庫連接初始化成功")

            # 初始化加密設定
            self._init_encryption()

            # 初始化安全配置
            self.security_config = {
                "password_min_length": 8,
                "password_require_uppercase": True,
                "password_require_lowercase": True,
                "password_require_numbers": True,
                "password_require_symbols": True,
                "password_history_count": 5,
                "max_login_attempts": 5,
                "account_lockout_duration": 30,  # 分鐘
                "session_timeout": 480,  # 分鐘 (8小時)
                "two_factor_required_roles": ["admin", "trader"],
                "high_risk_operations": [
                    "user_create",
                    "user_delete",
                    "role_assign",
                    "permission_grant",
                    "system_config",
                    "data_export",
                ],
            }

            logger.info("安全服務初始化完成")

        except Exception as e:
            logger.error(f"安全服務初始化失敗: {e}")
            raise

    def _init_encryption(self):
        """初始化加密設定"""
        try:
            # 獲取或生成加密密鑰
            key_file = Path("security.key")
            if key_file.exists():
                with open(key_file, "rb") as f:
                    self.encryption_key = f.read()
            else:
                self.encryption_key = Fernet.generate_key()
                with open(key_file, "wb") as f:
                    f.write(self.encryption_key)
                os.chmod(key_file, 0o600)  # 只有擁有者可讀寫

            self.cipher_suite = Fernet(self.encryption_key)

        except Exception as e:
            logger.error(f"加密設定初始化失敗: {e}")
            raise

    def hash_password(self, password: str) -> Tuple[str, str]:
        """
        密碼雜湊處理

        Args:
            password: 明文密碼

        Returns:
            Tuple[str, str]: (雜湊值, 鹽值)
        """
        try:
            if BCRYPT_AVAILABLE:
                # 使用 bcrypt
                salt = bcrypt.gensalt()
                password_hash = bcrypt.hashpw(password.encode("utf-8"), salt)
                return password_hash.decode("utf-8"), salt.decode("utf-8")
            else:
                # 使用 hashlib 作為後備方案
                salt = secrets.token_hex(16)
                password_hash = hashlib.pbkdf2_hmac(
                    'sha256',
                    password.encode('utf-8'),
                    salt.encode('utf-8'),
                    100000
                )
                # 格式: pbkdf2$salt$hash
                combined_hash = f"pbkdf2${salt}${password_hash.hex()}"
                return combined_hash, salt

        except Exception as e:
            logger.error(f"密碼雜湊處理失敗: {e}")
            raise

    def verify_password(self, password: str, password_hash: str) -> bool:
        """
        驗證密碼

        Args:
            password: 明文密碼
            password_hash: 儲存的雜湊值

        Returns:
            bool: 密碼是否正確
        """
        try:
            if BCRYPT_AVAILABLE and not password_hash.startswith("pbkdf2$"):
                # 使用 bcrypt 驗證
                return bcrypt.checkpw(
                    password.encode("utf-8"), password_hash.encode("utf-8")
                )
            else:
                # 使用 hashlib 後備方案驗證
                if password_hash.startswith("pbkdf2$"):
                    # 解析格式: pbkdf2$salt$hash
                    parts = password_hash.split("$")
                    if len(parts) != 3:
                        return False

                    salt = parts[1]
                    stored_hash = parts[2]

                    # 重新計算雜湊值
                    computed_hash = hashlib.pbkdf2_hmac(
                        'sha256',
                        password.encode('utf-8'),
                        salt.encode('utf-8'),
                        100000
                    ).hex()

                    return computed_hash == stored_hash
                else:
                    # 嘗試 bcrypt 驗證（如果可用）
                    if BCRYPT_AVAILABLE:
                        return bcrypt.checkpw(
                            password.encode("utf-8"), password_hash.encode("utf-8")
                        )
                    else:
                        logger.warning("無法驗證密碼：不支援的雜湊格式")
                        return False

        except Exception as e:
            logger.error(f"密碼驗證失敗: {e}")
            return False

    def validate_password_strength(self, password: str) -> Tuple[bool, List[str]]:
        """
        驗證密碼強度

        Args:
            password: 密碼

        Returns:
            Tuple[bool, List[str]]: (是否通過, 錯誤訊息列表)
        """
        errors = []

        # 檢查長度
        if len(password) < self.security_config["password_min_length"]:
            errors.append(
                f"密碼長度至少需要 {self.security_config['password_min_length']} 個字符"
            )

        # 檢查大寫字母
        if self.security_config["password_require_uppercase"] and not any(
            c.isupper() for c in password
        ):
            errors.append("密碼必須包含至少一個大寫字母")

        # 檢查小寫字母
        if self.security_config["password_require_lowercase"] and not any(
            c.islower() for c in password
        ):
            errors.append("密碼必須包含至少一個小寫字母")

        # 檢查數字
        if self.security_config["password_require_numbers"] and not any(
            c.isdigit() for c in password
        ):
            errors.append("密碼必須包含至少一個數字")

        # 檢查特殊字符
        if self.security_config["password_require_symbols"]:
            symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in symbols for c in password):
                errors.append("密碼必須包含至少一個特殊字符")

        return len(errors) == 0, errors

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: str = None,
        role_id: str = None,
        created_by: str = "system",
    ) -> Tuple[bool, str, Optional[str]]:
        """
        創建使用者

        Args:
            username: 使用者名稱
            email: 電子郵件
            password: 密碼
            full_name: 全名
            role_id: 角色ID
            created_by: 創建者

        Returns:
            Tuple[bool, str, Optional[str]]: (成功, 訊息, 使用者ID)
        """
        try:
            # 驗證密碼強度
            is_valid, errors = self.validate_password_strength(password)
            if not is_valid:
                return False, "; ".join(errors), None

            with self.session_factory() as session:
                # 檢查使用者名稱是否已存在
                existing_user = (
                    session.query(User)
                    .filter(or_(User.username == username, User.email == email))
                    .first()
                )

                if existing_user:
                    return False, "使用者名稱或電子郵件已存在", None

                # 生成使用者ID
                user_id = str(uuid.uuid4())

                # 雜湊密碼
                password_hash, salt = self.hash_password(password)

                # 創建使用者
                user = User(
                    user_id=user_id,
                    username=username,
                    email=email,
                    password_hash=password_hash,
                    salt=salt,
                    full_name=full_name,
                    default_role_id=role_id,
                    created_by=created_by,
                    is_active=True,
                    is_verified=False,
                )

                session.add(user)

                # 分配預設角色
                if role_id:
                    user_role = UserRole(
                        user_id=user_id,
                        role_id=role_id,
                        assigned_by=created_by,
                        assignment_reason="初始角色分配",
                    )
                    session.add(user_role)

                session.commit()

                # 記錄審計日誌
                self.log_audit_event(
                    operation_type="user_create",
                    operation_name="創建使用者",
                    user_id=created_by,
                    resource_type="user",
                    resource_id=user_id,
                    operation_description=f"創建使用者: {username}",
                    session=session,
                )

                return True, f"使用者 {username} 創建成功", user_id

        except Exception as e:
            logger.error(f"創建使用者失敗: {e}")
            return False, f"創建失敗: {e}", None

    def authenticate_user(
        self,
        username: str,
        password: str,
        ip_address: str = None,
        user_agent: str = None,
    ) -> Tuple[bool, str, Optional[Dict]]:
        """
        使用者認證

        Args:
            username: 使用者名稱
            password: 密碼
            ip_address: IP地址
            user_agent: 使用者代理

        Returns:
            Tuple[bool, str, Optional[Dict]]: (成功, 訊息, 使用者資訊)
        """
        try:
            with self.session_factory() as session:
                # 查找使用者
                user = (
                    session.query(User)
                    .filter(or_(User.username == username, User.email == username))
                    .first()
                )

                if not user:
                    # 記錄安全事件
                    self.log_security_event(
                        event_type="login_failed",
                        event_description=f"使用者不存在: {username}",
                        username=username,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        session=session,
                    )
                    return False, "使用者名稱或密碼錯誤", None

                # 檢查帳戶狀態
                if not user.is_active:
                    return False, "帳戶已被停用", None

                if user.is_locked:
                    return False, "帳戶已被鎖定，請聯繫管理員", None

                # 驗證密碼
                if not self.verify_password(password, user.password_hash):
                    # 增加失敗次數
                    user.failed_login_attempts += 1

                    # 檢查是否需要鎖定帳戶
                    if (
                        user.failed_login_attempts
                        >= self.security_config["max_login_attempts"]
                    ):
                        user.is_locked = True
                        user.locked_at = datetime.now()
                        user.locked_reason = "登入失敗次數過多"

                    session.commit()

                    # 記錄安全事件
                    self.log_security_event(
                        event_type="login_failed",
                        event_description=f"密碼錯誤: {username}",
                        user_id=user.user_id,
                        username=username,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        session=session,
                    )

                    return False, "使用者名稱或密碼錯誤", None

                # 登入成功，重置失敗次數
                user.failed_login_attempts = 0
                user.last_login_at = datetime.now()
                user.last_login_ip = ip_address

                session.commit()

                # 獲取使用者角色和權限
                user_info = {
                    "user_id": user.user_id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_verified": user.is_verified,
                    "two_factor_enabled": user.two_factor_enabled,
                    "roles": self.get_user_roles(user.user_id),
                    "permissions": self.get_user_permissions(user.user_id),
                }

                # 記錄安全事件
                self.log_security_event(
                    event_type="login_success",
                    event_description=f"登入成功: {username}",
                    user_id=user.user_id,
                    username=username,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session=session,
                )

                return True, "登入成功", user_info

        except Exception as e:
            logger.error(f"使用者認證失敗: {e}")
            return False, f"認證失敗: {e}", None

    def get_user_roles(self, user_id: str) -> List[Dict[str, Any]]:
        """獲取使用者角色"""
        try:
            with self.session_factory() as session:
                # 查詢有效的角色分配
                user_roles = (
                    session.query(UserRole, Role)
                    .join(Role, UserRole.role_id == Role.role_id)
                    .filter(
                        and_(
                            UserRole.user_id == user_id,
                            UserRole.is_active == True,
                            Role.is_active == True,
                            or_(
                                UserRole.effective_until.is_(None),
                                UserRole.effective_until > datetime.now(),
                            ),
                        )
                    )
                    .all()
                )

                roles = []
                for user_role, role in user_roles:
                    roles.append(
                        {
                            "role_id": role.role_id,
                            "role_name": role.role_name,
                            "role_code": role.role_code,
                            "role_level": role.role_level,
                            "assignment_type": user_role.assignment_type,
                            "effective_from": user_role.effective_from,
                            "effective_until": user_role.effective_until,
                        }
                    )

                return roles

        except Exception as e:
            logger.error(f"獲取使用者角色失敗: {e}")
            return []

    def get_user_permissions(self, user_id: str) -> List[str]:
        """獲取使用者權限"""
        try:
            with self.session_factory() as session:
                # 通過角色獲取權限
                user_roles = (
                    session.query(UserRole)
                    .filter(
                        and_(
                            UserRole.user_id == user_id,
                            UserRole.is_active == True,
                            or_(
                                UserRole.effective_until.is_(None),
                                UserRole.effective_until > datetime.now(),
                            ),
                        )
                    )
                    .all()
                )

                permissions = set()

                for user_role in user_roles:
                    # 獲取角色權限
                    role = (
                        session.query(Role)
                        .filter(Role.role_id == user_role.role_id)
                        .first()
                    )

                    if role and role.permissions:
                        role_permissions = role.permissions
                        if isinstance(role_permissions, list):
                            permissions.update(role_permissions)
                        elif isinstance(role_permissions, dict):
                            permissions.update(role_permissions.get("permissions", []))

                return list(permissions)

        except Exception as e:
            logger.error(f"獲取使用者權限失敗: {e}")
            return []

    def check_permission(
        self, user_id: str, permission_code: str, resource_id: str = None
    ) -> bool:
        """
        檢查使用者權限

        Args:
            user_id: 使用者ID
            permission_code: 權限代碼
            resource_id: 資源ID

        Returns:
            bool: 是否有權限
        """
        try:
            # 獲取使用者權限
            user_permissions = self.get_user_permissions(user_id)

            # 檢查是否有該權限
            if permission_code in user_permissions:
                return True

            # 檢查萬用權限
            if "admin.all" in user_permissions:
                return True

            # 檢查模組權限
            module_permission = permission_code.split(".")[0] + ".all"
            if module_permission in user_permissions:
                return True

            return False

        except Exception as e:
            logger.error(f"檢查使用者權限失敗: {e}")
            return False

    def create_session(
        self,
        user_id: str,
        username: str,
        ip_address: str = None,
        user_agent: str = None,
        remember_me: bool = False,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        創建使用者會話

        Args:
            user_id: 使用者ID
            username: 使用者名稱
            ip_address: IP地址
            user_agent: 使用者代理
            remember_me: 是否記住登入

        Returns:
            Tuple[bool, str, Optional[str]]: (成功, 訊息, 會話ID)
        """
        try:
            with self.session_factory() as session:
                # 生成會話ID
                session_id = secrets.token_urlsafe(64)

                # 計算過期時間
                if remember_me:
                    expires_at = datetime.now() + timedelta(days=30)
                else:
                    expires_at = datetime.now() + timedelta(
                        minutes=self.security_config["session_timeout"]
                    )

                # 創建會話記錄
                user_session = UserSession(
                    session_id=session_id,
                    user_id=user_id,
                    username=username,
                    session_status="active",
                    login_method="password",
                    is_remember_me=remember_me,
                    last_activity=datetime.now(),
                    expires_at=expires_at,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    is_secure=True,
                )

                session.add(user_session)
                session.commit()

                return True, "會話創建成功", session_id

        except Exception as e:
            logger.error(f"創建會話失敗: {e}")
            return False, f"創建會話失敗: {e}", None

    def validate_session(self, session_id: str) -> Tuple[bool, Optional[Dict]]:
        """
        驗證會話

        Args:
            session_id: 會話ID

        Returns:
            Tuple[bool, Optional[Dict]]: (有效, 會話資訊)
        """
        try:
            with self.session_factory() as session:
                user_session = (
                    session.query(UserSession)
                    .filter(UserSession.session_id == session_id)
                    .first()
                )

                if not user_session:
                    return False, None

                # 檢查會話狀態
                if user_session.session_status != "active":
                    return False, None

                # 檢查過期時間
                if user_session.expires_at and user_session.expires_at < datetime.now():
                    # 標記會話為過期
                    user_session.session_status = "expired"
                    user_session.logout_reason = "session_timeout"
                    session.commit()
                    return False, None

                # 更新最後活動時間
                user_session.last_activity = datetime.now()
                session.commit()

                session_info = {
                    "session_id": user_session.session_id,
                    "user_id": user_session.user_id,
                    "username": user_session.username,
                    "login_method": user_session.login_method,
                    "is_remember_me": user_session.is_remember_me,
                    "created_at": user_session.created_at,
                    "last_activity": user_session.last_activity,
                    "expires_at": user_session.expires_at,
                    "ip_address": user_session.ip_address,
                }

                return True, session_info

        except Exception as e:
            logger.error(f"驗證會話失敗: {e}")
            return False, None

    def logout_session(self, session_id: str, reason: str = "user_logout") -> bool:
        """
        登出會話

        Args:
            session_id: 會話ID
            reason: 登出原因

        Returns:
            bool: 是否成功
        """
        try:
            with self.session_factory() as session:
                user_session = (
                    session.query(UserSession)
                    .filter(UserSession.session_id == session_id)
                    .first()
                )

                if user_session:
                    user_session.session_status = "logged_out"
                    user_session.logout_at = datetime.now()
                    user_session.logout_reason = reason
                    session.commit()

                    # 記錄安全事件
                    self.log_security_event(
                        event_type="logout",
                        event_description=f"使用者登出: {reason}",
                        user_id=user_session.user_id,
                        username=user_session.username,
                        session_id=session_id,
                        session=session,
                    )

                    return True

                return False

        except Exception as e:
            logger.error(f"登出會話失敗: {e}")
            return False

    def log_security_event(
        self,
        event_type: str,
        event_description: str,
        user_id: str = None,
        username: str = None,
        session_id: str = None,
        ip_address: str = None,
        user_agent: str = None,
        event_data: Dict = None,
        session: Session = None,
    ) -> bool:
        """
        記錄安全事件

        Args:
            event_type: 事件類型
            event_description: 事件描述
            user_id: 使用者ID
            username: 使用者名稱
            session_id: 會話ID
            ip_address: IP地址
            user_agent: 使用者代理
            event_data: 事件數據
            session: 資料庫會話

        Returns:
            bool: 是否成功
        """
        try:
            # 如果沒有提供會話，創建新的
            if session is None:
                with self.session_factory() as session:
                    return self._create_security_event(
                        session,
                        event_type,
                        event_description,
                        user_id,
                        username,
                        session_id,
                        ip_address,
                        user_agent,
                        event_data,
                    )
            else:
                return self._create_security_event(
                    session,
                    event_type,
                    event_description,
                    user_id,
                    username,
                    session_id,
                    ip_address,
                    user_agent,
                    event_data,
                )

        except Exception as e:
            logger.error(f"記錄安全事件失敗: {e}")
            return False

    def _create_security_event(
        self,
        session: Session,
        event_type: str,
        event_description: str,
        user_id: str = None,
        username: str = None,
        session_id: str = None,
        ip_address: str = None,
        user_agent: str = None,
        event_data: Dict = None,
    ) -> bool:
        """創建安全事件記錄"""
        try:
            # 生成事件ID
            event_id = str(uuid.uuid4())

            # 評估風險等級
            risk_score = self._calculate_risk_score(event_type, ip_address, user_id)
            threat_level = self._determine_threat_level(risk_score)

            # 創建安全事件
            security_event = SecurityEvent(
                event_id=event_id,
                event_type=event_type,
                event_category=self._get_event_category(event_type),
                event_level=self._get_event_level(event_type),
                event_source="security_service",
                user_id=user_id,
                username=username,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                event_description=event_description,
                event_data=event_data,
                risk_score=risk_score,
                threat_level=threat_level,
                is_suspicious=risk_score > 7.0,
                status="new",
            )

            session.add(security_event)
            session.commit()

            return True

        except Exception as e:
            logger.error(f"創建安全事件失敗: {e}")
            return False

    def _calculate_risk_score(
        self, event_type: str, ip_address: str = None, user_id: str = None
    ) -> float:
        """計算風險分數"""
        try:
            base_scores = {
                "login_failed": 3.0,
                "login_success": 1.0,
                "logout": 0.5,
                "permission_denied": 5.0,
                "data_access": 2.0,
                "config_change": 7.0,
                "user_create": 6.0,
                "user_delete": 8.0,
                "role_assign": 7.0,
            }

            risk_score = base_scores.get(event_type, 2.0)

            # IP地址風險評估
            if ip_address:
                if self._is_suspicious_ip(ip_address):
                    risk_score += 3.0
                if self._is_foreign_ip(ip_address):
                    risk_score += 1.0

            # 使用者行為風險評估
            if user_id:
                if self._has_recent_suspicious_activity(user_id):
                    risk_score += 2.0

            return min(risk_score, 10.0)  # 最高10分

        except Exception as e:
            logger.error(f"計算風險分數失敗: {e}")
            return 5.0  # 預設中等風險

    def _determine_threat_level(self, risk_score: float) -> str:
        """確定威脅等級"""
        if risk_score >= 8.0:
            return "critical"
        elif risk_score >= 6.0:
            return "high"
        elif risk_score >= 4.0:
            return "medium"
        elif risk_score >= 2.0:
            return "low"
        else:
            return "info"

    def _get_event_category(self, event_type: str) -> str:
        """獲取事件分類"""
        categories = {
            "login_failed": "authentication",
            "login_success": "authentication",
            "logout": "authentication",
            "permission_denied": "authorization",
            "data_access": "data_access",
            "config_change": "configuration",
            "user_create": "user_management",
            "user_delete": "user_management",
            "role_assign": "role_management",
        }
        return categories.get(event_type, "general")

    def _get_event_level(self, event_type: str) -> str:
        """獲取事件等級"""
        levels = {
            "login_failed": "warning",
            "login_success": "info",
            "logout": "info",
            "permission_denied": "warning",
            "data_access": "info",
            "config_change": "warning",
            "user_create": "info",
            "user_delete": "warning",
            "role_assign": "info",
        }
        return levels.get(event_type, "info")

    def _is_suspicious_ip(self, ip_address: str) -> bool:
        """檢查是否為可疑IP"""
        try:
            # 這裡可以整合IP威脅情報資料庫
            # 暫時使用簡單的黑名單檢查
            suspicious_ips = [
                "192.168.1.100",  # 示例可疑IP
            ]
            return ip_address in suspicious_ips
        except:
            return False

    def _is_foreign_ip(self, ip_address: str) -> bool:
        """檢查是否為國外IP"""
        try:
            # 這裡可以整合地理位置資料庫
            # 暫時使用簡單的檢查
            ip = ipaddress.ip_address(ip_address)
            return not ip.is_private
        except:
            return False

    def _has_recent_suspicious_activity(self, user_id: str) -> bool:
        """檢查是否有近期可疑活動"""
        try:
            with self.session_factory() as session:
                # 檢查過去24小時內的可疑事件
                recent_events = (
                    session.query(SecurityEvent)
                    .filter(
                        and_(
                            SecurityEvent.user_id == user_id,
                            SecurityEvent.is_suspicious == True,
                            SecurityEvent.created_at
                            > datetime.now() - timedelta(hours=24),
                        )
                    )
                    .count()
                )

                return recent_events > 0
        except:
            return False

    def log_audit_event(
        self,
        operation_type: str,
        operation_name: str,
        user_id: str = None,
        username: str = None,
        resource_type: str = None,
        resource_id: str = None,
        operation_description: str = None,
        input_parameters: Dict = None,
        output_result: Dict = None,
        session: Session = None,
    ) -> bool:
        """
        記錄審計事件

        Args:
            operation_type: 操作類型
            operation_name: 操作名稱
            user_id: 使用者ID
            username: 使用者名稱
            resource_type: 資源類型
            resource_id: 資源ID
            operation_description: 操作描述
            input_parameters: 輸入參數
            output_result: 輸出結果
            session: 資料庫會話

        Returns:
            bool: 是否成功
        """
        try:
            # 如果沒有提供會話，創建新的
            if session is None:
                with self.session_factory() as session:
                    return self._create_audit_log(
                        session,
                        operation_type,
                        operation_name,
                        user_id,
                        username,
                        resource_type,
                        resource_id,
                        operation_description,
                        input_parameters,
                        output_result,
                    )
            else:
                return self._create_audit_log(
                    session,
                    operation_type,
                    operation_name,
                    user_id,
                    username,
                    resource_type,
                    resource_id,
                    operation_description,
                    input_parameters,
                    output_result,
                )

        except Exception as e:
            logger.error(f"記錄審計事件失敗: {e}")
            return False

    def _create_audit_log(
        self,
        session: Session,
        operation_type: str,
        operation_name: str,
        user_id: str = None,
        username: str = None,
        resource_type: str = None,
        resource_id: str = None,
        operation_description: str = None,
        input_parameters: Dict = None,
        output_result: Dict = None,
    ) -> bool:
        """創建審計日誌記錄"""
        try:
            # 生成審計ID
            audit_id = str(uuid.uuid4())

            # 評估風險等級
            risk_level = self._get_operation_risk_level(operation_type)

            # 創建審計日誌
            audit_log = AuditLog(
                audit_id=audit_id,
                operation_type=operation_type,
                operation_name=operation_name,
                module_name="security_service",
                user_id=user_id,
                username=username,
                resource_type=resource_type,
                resource_id=resource_id,
                operation_description=operation_description,
                input_parameters=input_parameters,
                output_result=output_result,
                operation_status="success",
                risk_level=risk_level,
                requires_approval=operation_type
                in self.security_config["high_risk_operations"],
                is_sensitive=risk_level in ["high", "critical"],
            )

            session.add(audit_log)
            session.commit()

            return True

        except Exception as e:
            logger.error(f"創建審計日誌失敗: {e}")
            return False

    def _get_operation_risk_level(self, operation_type: str) -> str:
        """獲取操作風險等級"""
        high_risk_ops = [
            "user_delete",
            "role_assign",
            "permission_grant",
            "system_config",
            "data_export",
            "security_config",
        ]

        medium_risk_ops = [
            "user_create",
            "user_update",
            "role_create",
            "permission_create",
            "data_access",
        ]

        if operation_type in high_risk_ops:
            return "high"
        elif operation_type in medium_risk_ops:
            return "medium"
        else:
            return "low"

    def encrypt_sensitive_data(self, data: str) -> str:
        """加密敏感數據"""
        try:
            return self.cipher_suite.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"數據加密失敗: {e}")
            raise

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """解密敏感數據"""
        try:
            return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"數據解密失敗: {e}")
            raise

    def get_security_events(
        self,
        user_id: str = None,
        event_type: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """獲取安全事件列表"""
        try:
            with self.session_factory() as session:
                query = session.query(SecurityEvent)

                if user_id:
                    query = query.filter(SecurityEvent.user_id == user_id)

                if event_type:
                    query = query.filter(SecurityEvent.event_type == event_type)

                if start_date:
                    query = query.filter(SecurityEvent.created_at >= start_date)

                if end_date:
                    query = query.filter(SecurityEvent.created_at <= end_date)

                events = (
                    query.order_by(desc(SecurityEvent.created_at)).limit(limit).all()
                )

                result = []
                for event in events:
                    result.append(
                        {
                            "event_id": event.event_id,
                            "event_type": event.event_type,
                            "event_category": event.event_category,
                            "event_level": event.event_level,
                            "user_id": event.user_id,
                            "username": event.username,
                            "ip_address": event.ip_address,
                            "event_description": event.event_description,
                            "risk_score": event.risk_score,
                            "threat_level": event.threat_level,
                            "is_suspicious": event.is_suspicious,
                            "status": event.status,
                            "created_at": event.created_at.isoformat(),
                        }
                    )

                return result

        except Exception as e:
            logger.error(f"獲取安全事件失敗: {e}")
            return []

    def get_audit_logs(
        self,
        user_id: str = None,
        operation_type: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """獲取審計日誌列表"""
        try:
            with self.session_factory() as session:
                query = session.query(AuditLog)

                if user_id:
                    query = query.filter(AuditLog.user_id == user_id)

                if operation_type:
                    query = query.filter(AuditLog.operation_type == operation_type)

                if start_date:
                    query = query.filter(AuditLog.created_at >= start_date)

                if end_date:
                    query = query.filter(AuditLog.created_at <= end_date)

                logs = query.order_by(desc(AuditLog.created_at)).limit(limit).all()

                result = []
                for log in logs:
                    result.append(
                        {
                            "audit_id": log.audit_id,
                            "operation_type": log.operation_type,
                            "operation_name": log.operation_name,
                            "user_id": log.user_id,
                            "username": log.username,
                            "resource_type": log.resource_type,
                            "resource_id": log.resource_id,
                            "operation_description": log.operation_description,
                            "operation_status": log.operation_status,
                            "risk_level": log.risk_level,
                            "created_at": log.created_at.isoformat(),
                        }
                    )

                return result

        except Exception as e:
            logger.error(f"獲取審計日誌失敗: {e}")
            return []
