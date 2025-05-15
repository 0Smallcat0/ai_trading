"""
API 金鑰安全管理模組

此模組負責 API 金鑰的加密、解密和安全存儲。
使用環境變數和加密技術來保護敏感資訊。
"""

import os
import base64
import logging
import json
from typing import Dict, Optional, Any, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import hashlib

# 嘗試導入加密庫
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

# 設定日誌
logger = logging.getLogger("execution.security")


def generate_key(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    使用密碼生成加密金鑰

    Args:
        password (str): 密碼
        salt (bytes, optional): 鹽值，如果為 None 則隨機生成

    Returns:
        Tuple[bytes, bytes]: (金鑰, 鹽值)
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        raise ImportError("請安裝 cryptography 套件: pip install cryptography")

    # 如果沒有提供鹽值，則隨機生成
    if salt is None:
        import os

        salt = os.urandom(16)

    # 使用 PBKDF2 生成金鑰
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key, salt


def encrypt_api_key(api_key: str, password: str) -> str:
    """
    加密 API 金鑰

    Args:
        api_key (str): API 金鑰
        password (str): 加密密碼

    Returns:
        str: 加密後的 API 金鑰 (格式: base64(salt):base64(encrypted_data))
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        logger.warning("未安裝 cryptography 套件，無法加密 API 金鑰")
        return api_key

    try:
        # 生成加密金鑰
        key, salt = generate_key(password)

        # 使用 Fernet 加密
        f = Fernet(key)
        encrypted_data = f.encrypt(api_key.encode())

        # 將鹽值和加密數據組合
        result = (
            base64.urlsafe_b64encode(salt).decode()
            + ":"
            + base64.urlsafe_b64encode(encrypted_data).decode()
        )
        return result
    except Exception as e:
        logger.error(f"加密 API 金鑰時發生錯誤: {e}")
        return api_key


def decrypt_api_key(encrypted_api_key: str, password: str) -> str:
    """
    解密 API 金鑰

    Args:
        encrypted_api_key (str): 加密後的 API 金鑰
        password (str): 解密密碼

    Returns:
        str: 解密後的 API 金鑰
    """
    if not CRYPTOGRAPHY_AVAILABLE:
        logger.warning("未安裝 cryptography 套件，無法解密 API 金鑰")
        return encrypted_api_key

    try:
        # 檢查是否為加密格式
        if ":" not in encrypted_api_key:
            return encrypted_api_key

        # 分離鹽值和加密數據
        salt_b64, data_b64 = encrypted_api_key.split(":", 1)
        salt = base64.urlsafe_b64decode(salt_b64)
        encrypted_data = base64.urlsafe_b64decode(data_b64)

        # 使用密碼和鹽值生成金鑰
        key, _ = generate_key(password, salt)

        # 使用 Fernet 解密
        f = Fernet(key)
        decrypted_data = f.decrypt(encrypted_data)
        return decrypted_data.decode()
    except Exception as e:
        logger.error(f"解密 API 金鑰時發生錯誤: {e}")
        return encrypted_api_key


def save_api_keys(
    broker_name: str,
    api_key: str,
    api_secret: str,
    account_id: Optional[str] = None,
    encrypt: bool = True,
    password: Optional[str] = None,
    config_dir: str = "config",
) -> bool:
    """
    保存 API 金鑰到配置文件

    Args:
        broker_name (str): 券商名稱
        api_key (str): API 金鑰
        api_secret (str): API 密鑰
        account_id (str, optional): 帳戶 ID
        encrypt (bool): 是否加密
        password (str, optional): 加密密碼，如果為 None 則使用環境變數 API_KEY_PASSWORD
        config_dir (str): 配置文件目錄

    Returns:
        bool: 是否保存成功
    """
    try:
        # 創建配置目錄
        os.makedirs(config_dir, exist_ok=True)

        # 配置文件路徑
        config_file = Path(config_dir) / "api_keys.json"

        # 讀取現有配置
        config = {}
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

        # 如果需要加密
        if encrypt:
            # 獲取密碼
            if password is None:
                password = os.getenv("API_KEY_PASSWORD")
                if password is None:
                    logger.error("未提供加密密碼，無法加密 API 金鑰")
                    return False

            # 加密 API 金鑰
            api_key = encrypt_api_key(api_key, password)
            api_secret = encrypt_api_key(api_secret, password)

        # 更新配置
        if broker_name not in config:
            config[broker_name] = {}
        config[broker_name]["api_key"] = api_key
        config[broker_name]["api_secret"] = api_secret
        if account_id:
            config[broker_name]["account_id"] = account_id
        config[broker_name]["encrypted"] = encrypt
        config[broker_name]["updated_at"] = datetime.now().isoformat()

        # 保存配置
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        logger.info(f"已保存 {broker_name} 的 API 金鑰")
        return True
    except Exception as e:
        logger.error(f"保存 API 金鑰時發生錯誤: {e}")
        return False


def load_api_keys(
    broker_name: str,
    password: Optional[str] = None,
    config_dir: str = "config",
) -> Dict[str, str]:
    """
    從配置文件加載 API 金鑰

    Args:
        broker_name (str): 券商名稱
        password (str, optional): 解密密碼，如果為 None 則使用環境變數 API_KEY_PASSWORD
        config_dir (str): 配置文件目錄

    Returns:
        Dict[str, str]: API 金鑰字典，包含 api_key, api_secret, account_id
    """
    try:
        # 配置文件路徑
        config_file = Path(config_dir) / "api_keys.json"

        # 檢查配置文件是否存在
        if not config_file.exists():
            logger.error(f"配置文件不存在: {config_file}")
            return {}

        # 讀取配置
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 檢查券商配置是否存在
        if broker_name not in config:
            logger.error(f"找不到 {broker_name} 的 API 金鑰配置")
            return {}

        broker_config = config[broker_name]
        api_key = broker_config.get("api_key", "")
        api_secret = broker_config.get("api_secret", "")
        account_id = broker_config.get("account_id", "")
        encrypted = broker_config.get("encrypted", False)

        # 如果需要解密
        if encrypted:
            # 獲取密碼
            if password is None:
                password = os.getenv("API_KEY_PASSWORD")
                if password is None:
                    logger.error("未提供解密密碼，無法解密 API 金鑰")
                    return {}

            # 解密 API 金鑰
            api_key = decrypt_api_key(api_key, password)
            api_secret = decrypt_api_key(api_secret, password)

        return {
            "api_key": api_key,
            "api_secret": api_secret,
            "account_id": account_id,
        }
    except Exception as e:
        logger.error(f"加載 API 金鑰時發生錯誤: {e}")
        return {}
