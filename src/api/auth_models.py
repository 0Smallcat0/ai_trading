"""
API 認證模型模組

此模組定義了認證相關的資料模型和結構，包括：
- 用戶資料模型
- 認證請求模型
- 權限和角色定義

主要功能：
- 定義用戶資料結構
- 提供認證相關的資料類型
- 管理權限和角色映射

Example:
    >>> from src.api.auth_models import User, AuthRequest
    >>> user = User(username="admin", role="admin")
    >>> print(user.get_permissions())
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    BCRYPT_AVAILABLE = False
    logging.warning("bcrypt 套件未安裝，將使用備用密碼驗證方法")

logger = logging.getLogger(__name__)


@dataclass
class User:
    """用戶資料模型.
    
    Attributes:
        user_id: 用戶唯一識別碼
        username: 用戶名稱
        email: 電子郵件地址
        password_hash: 密碼哈希值
        full_name: 完整姓名
        role: 用戶角色
        is_active: 是否啟用
        created_at: 創建時間
        last_login: 最後登入時間
        permissions: 用戶權限列表
    """
    user_id: str
    username: str
    email: str
    password_hash: str
    full_name: str
    role: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    permissions: Optional[List[str]] = None

    def __post_init__(self) -> None:
        """初始化後處理."""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.permissions is None:
            self.permissions = get_role_permissions(self.role)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式.
        
        Returns:
            Dict[str, Any]: 用戶資料字典
        """
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "permissions": self.permissions or []
        }

    def has_permission(self, permission: str) -> bool:
        """檢查用戶是否具有指定權限.
        
        Args:
            permission: 權限名稱
            
        Returns:
            bool: 是否具有權限
        """
        return permission in (self.permissions or [])

    def has_role(self, role: str) -> bool:
        """檢查用戶是否具有指定角色.
        
        Args:
            role: 角色名稱
            
        Returns:
            bool: 是否具有角色
        """
        return self.role == role


@dataclass
class AuthRequest:
    """認證請求模型.
    
    Attributes:
        username: 用戶名稱
        password: 密碼
        remember_me: 是否記住登入狀態
        client_ip: 客戶端 IP 地址
        user_agent: 用戶代理字符串
    """
    username: str
    password: str
    remember_me: bool = False
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass
class AuthResponse:
    """認證回應模型.
    
    Attributes:
        success: 認證是否成功
        user: 用戶資料
        token: 認證令牌
        message: 回應訊息
        expires_at: 令牌過期時間
    """
    success: bool
    user: Optional[User] = None
    token: Optional[str] = None
    message: str = ""
    expires_at: Optional[datetime] = None


def get_role_permissions(role: str) -> List[str]:
    """獲取角色權限列表.
    
    Args:
        role: 角色名稱
        
    Returns:
        List[str]: 權限列表
        
    Example:
        >>> permissions = get_role_permissions("admin")
        >>> print("read" in permissions)
        True
    """
    role_permissions = {
        "admin": [
            "read", "write", "delete", "admin",
            "user_management", "system_config", "data_management",
            "strategy_management", "portfolio_management", "risk_management",
            "trade_execution", "system_monitoring", "reports"
        ],
        "trader": [
            "read", "write",
            "strategy_management", "portfolio_management", "risk_management",
            "trade_execution", "reports"
        ],
        "analyst": [
            "read", "write",
            "data_management", "strategy_management", "portfolio_management",
            "reports"
        ],
        "viewer": [
            "read",
            "reports"
        ],
        "demo": [
            "read",
            "strategy_management", "portfolio_management", "reports"
        ]
    }
    
    return role_permissions.get(role, ["read"])


def init_default_users() -> Dict[str, User]:
    """初始化預設用戶資料.
    
    Returns:
        Dict[str, User]: 用戶資料字典
        
    Example:
        >>> users = init_default_users()
        >>> admin_user = users["admin"]
        >>> print(admin_user.role)
        'admin'
    """
    if not BCRYPT_AVAILABLE:
        # 使用預設的哈希值（僅用於測試）
        admin_hash = "$2b$12$test.admin.hash.value"
        user_hash = "$2b$12$test.user.hash.value"
        demo_hash = "$2b$12$test.demo.hash.value"
    else:
        admin_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
        user_hash = bcrypt.hashpw("user123".encode(), bcrypt.gensalt()).decode()
        demo_hash = bcrypt.hashpw("demo123".encode(), bcrypt.gensalt()).decode()

    users = {
        "admin": User(
            user_id="user_001",
            username="admin",
            email="admin@trading.com",
            password_hash=admin_hash,
            full_name="系統管理員",
            role="admin",
            created_at=datetime(2024, 1, 1)
        ),
        "trader": User(
            user_id="user_002",
            username="trader",
            email="trader@trading.com",
            password_hash=user_hash,
            full_name="交易員",
            role="trader",
            created_at=datetime(2024, 1, 1)
        ),
        "analyst": User(
            user_id="user_003",
            username="analyst",
            email="analyst@trading.com",
            password_hash=user_hash,
            full_name="分析師",
            role="analyst",
            created_at=datetime(2024, 1, 1)
        ),
        "demo": User(
            user_id="user_004",
            username="demo",
            email="demo@trading.com",
            password_hash=demo_hash,
            full_name="示範用戶",
            role="demo",
            created_at=datetime(2024, 1, 1)
        )
    }
    
    logger.info("初始化了 %d 個預設用戶", len(users))
    return users


def validate_user_data(user_data: Dict[str, Any]) -> bool:
    """驗證用戶資料的完整性.
    
    Args:
        user_data: 用戶資料字典
        
    Returns:
        bool: 資料是否有效
        
    Example:
        >>> user_data = {"username": "test", "email": "test@example.com"}
        >>> is_valid = validate_user_data(user_data)
        >>> print(is_valid)
    """
    required_fields = ["username", "email", "password_hash", "role"]
    
    for field in required_fields:
        if field not in user_data or not user_data[field]:
            logger.warning("用戶資料缺少必要欄位: %s", field)
            return False
    
    # 驗證角色是否有效
    valid_roles = ["admin", "trader", "analyst", "viewer", "demo"]
    if user_data["role"] not in valid_roles:
        logger.warning("無效的用戶角色: %s", user_data["role"])
        return False
    
    return True


def create_user_from_dict(user_data: Dict[str, Any]) -> Optional[User]:
    """從字典創建用戶物件.
    
    Args:
        user_data: 用戶資料字典
        
    Returns:
        Optional[User]: 用戶物件，如果資料無效則返回 None
        
    Example:
        >>> user_data = {
        ...     "user_id": "001",
        ...     "username": "test",
        ...     "email": "test@example.com",
        ...     "password_hash": "hash",
        ...     "full_name": "Test User",
        ...     "role": "viewer"
        ... }
        >>> user = create_user_from_dict(user_data)
        >>> print(user.username if user else "Invalid")
    """
    if not validate_user_data(user_data):
        return None
    
    try:
        return User(
            user_id=user_data["user_id"],
            username=user_data["username"],
            email=user_data["email"],
            password_hash=user_data["password_hash"],
            full_name=user_data.get("full_name", ""),
            role=user_data["role"],
            is_active=user_data.get("is_active", True),
            created_at=user_data.get("created_at"),
            last_login=user_data.get("last_login")
        )
    except Exception as e:
        logger.error("創建用戶物件失敗: %s", e, exc_info=True)
        return None
