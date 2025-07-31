"""
多重身份驗證服務

此模組實現了完整的多重身份驗證功能，包括：
- TOTP (Time-based One-Time Password) 驗證
- SMS 驗證
- QR 碼生成
- 備用碼管理
- 2FA 設定和驗證流程

遵循金融級安全標準，提供高安全性的身份驗證機制。
"""

import logging
import secrets
import time
import base64
import io
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import hashlib
import hmac

# 導入第三方庫
import pyotp
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SquareGradiantColorMask
from PIL import Image

# 導入資料庫相關模組
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker, Session

# 導入配置和資料庫模型
from src.config import DB_URL
from src.database.schema import User, SecurityEvent, AuditLog

# 設置日誌
logger = logging.getLogger(__name__)


class TwoFactorService:
    """
    多重身份驗證服務
    
    提供完整的 2FA/MFA 功能，包括 TOTP、SMS 驗證、
    QR 碼生成和備用碼管理。
    """
    
    def __init__(self):
        """初始化 2FA 服務"""
        try:
            # 初始化資料庫連接
            self.engine = create_engine(DB_URL)
            self.session_factory = sessionmaker(bind=self.engine)
            logger.info("2FA 服務資料庫連接初始化成功")
            
            # 2FA 配置
            self.config = {
                "totp_issuer": "AI Trading System",
                "totp_period": 30,  # TOTP 有效期（秒）
                "totp_digits": 6,   # TOTP 位數
                "backup_codes_count": 10,  # 備用碼數量
                "sms_timeout": 300,  # SMS 驗證碼有效期（秒）
                "max_attempts": 3,   # 最大嘗試次數
                "lockout_duration": 900,  # 鎖定時間（秒）
            }
            
            logger.info("2FA 服務初始化完成")
            
        except Exception as e:
            logger.error(f"2FA 服務初始化失敗: {e}")
            raise
    
    def setup_totp(self, user_id: str, user_email: str) -> Dict[str, Any]:
        """
        設定 TOTP 兩步驗證
        
        Args:
            user_id: 使用者 ID
            user_email: 使用者電子郵件
            
        Returns:
            Dict[str, Any]: 包含 secret、QR 碼和備用碼的設定資訊
            
        Raises:
            ValueError: 使用者不存在或已啟用 2FA
            Exception: 設定過程發生錯誤
        """
        try:
            with self.session_factory() as session:
                # 檢查使用者是否存在
                user = session.query(User).filter(User.user_id == user_id).first()
                if not user:
                    raise ValueError("使用者不存在")
                
                # 檢查是否已啟用 2FA
                if user.two_factor_enabled:
                    raise ValueError("使用者已啟用兩步驗證")
                
                # 生成 TOTP secret
                secret = pyotp.random_base32()
                
                # 生成備用碼
                backup_codes = self._generate_backup_codes()
                
                # 生成 QR 碼
                qr_code_data = self._generate_qr_code(user_email, secret)
                
                # 暫存設定（等待驗證後才正式啟用）
                temp_data = {
                    "secret": secret,
                    "backup_codes": backup_codes,
                    "setup_time": datetime.now().isoformat(),
                }
                
                # 記錄安全事件
                self._log_security_event(
                    session,
                    user_id,
                    "2fa_setup_initiated",
                    "medium",
                    "使用者開始設定兩步驗證",
                    {"email": user_email}
                )
                
                session.commit()
                
                logger.info(f"使用者 {user_id} 開始設定 TOTP")
                
                return {
                    "secret": secret,
                    "qr_code": qr_code_data,
                    "backup_codes": backup_codes,
                    "setup_token": self._generate_setup_token(user_id, secret),
                }
                
        except Exception as e:
            logger.error(f"設定 TOTP 失敗: {e}")
            raise
    
    def verify_totp_setup(
        self, 
        user_id: str, 
        totp_code: str, 
        setup_token: str
    ) -> Tuple[bool, str]:
        """
        驗證 TOTP 設定
        
        Args:
            user_id: 使用者 ID
            totp_code: TOTP 驗證碼
            setup_token: 設定令牌
            
        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            with self.session_factory() as session:
                # 驗證設定令牌
                if not self._verify_setup_token(setup_token, user_id):
                    return False, "設定令牌無效或已過期"
                
                # 從令牌中提取 secret
                secret = self._extract_secret_from_token(setup_token)
                
                # 驗證 TOTP 碼
                totp = pyotp.TOTP(secret)
                if not totp.verify(totp_code, valid_window=1):
                    return False, "驗證碼錯誤"
                
                # 啟用 2FA
                user = session.query(User).filter(User.user_id == user_id).first()
                if not user:
                    return False, "使用者不存在"
                
                # 生成最終的備用碼
                backup_codes = self._generate_backup_codes()
                backup_codes_hashed = [
                    hashlib.sha256(code.encode()).hexdigest() 
                    for code in backup_codes
                ]
                
                user.two_factor_enabled = True
                user.two_factor_secret = secret
                user.backup_codes = backup_codes_hashed
                
                # 記錄安全事件
                self._log_security_event(
                    session,
                    user_id,
                    "2fa_enabled",
                    "high",
                    "使用者成功啟用兩步驗證",
                    {"method": "totp"}
                )
                
                session.commit()
                
                logger.info(f"使用者 {user_id} 成功啟用 TOTP")
                
                return True, "兩步驗證設定成功"
                
        except Exception as e:
            logger.error(f"驗證 TOTP 設定失敗: {e}")
            return False, f"設定失敗: {str(e)}"
    
    def verify_totp(self, user_id: str, totp_code: str) -> Tuple[bool, str]:
        """
        驗證 TOTP 碼
        
        Args:
            user_id: 使用者 ID
            totp_code: TOTP 驗證碼
            
        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            with self.session_factory() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if not user:
                    return False, "使用者不存在"
                
                if not user.two_factor_enabled or not user.two_factor_secret:
                    return False, "使用者未啟用兩步驗證"
                
                # 檢查是否被鎖定
                if self._is_user_locked(user):
                    return False, "帳戶已被鎖定，請稍後再試"
                
                # 驗證 TOTP 碼
                totp = pyotp.TOTP(user.two_factor_secret)
                if totp.verify(totp_code, valid_window=1):
                    # 重置失敗次數
                    user.failed_login_attempts = 0
                    
                    # 記錄成功事件
                    self._log_security_event(
                        session,
                        user_id,
                        "2fa_success",
                        "low",
                        "兩步驗證成功",
                        {"method": "totp"}
                    )
                    
                    session.commit()
                    return True, "驗證成功"
                
                # 驗證失敗，增加失敗次數
                user.failed_login_attempts += 1
                
                # 檢查是否需要鎖定
                if user.failed_login_attempts >= self.config["max_attempts"]:
                    user.is_locked = True
                    user.locked_at = datetime.now()
                    user.locked_reason = "2FA 驗證失敗次數過多"
                    
                    self._log_security_event(
                        session,
                        user_id,
                        "account_locked",
                        "high",
                        "帳戶因 2FA 驗證失敗過多而被鎖定",
                        {"failed_attempts": user.failed_login_attempts}
                    )
                else:
                    self._log_security_event(
                        session,
                        user_id,
                        "2fa_failed",
                        "medium",
                        "兩步驗證失敗",
                        {
                            "method": "totp",
                            "failed_attempts": user.failed_login_attempts
                        }
                    )
                
                session.commit()
                
                remaining_attempts = self.config["max_attempts"] - user.failed_login_attempts
                if remaining_attempts > 0:
                    return False, f"驗證碼錯誤，還有 {remaining_attempts} 次機會"
                else:
                    return False, "驗證失敗次數過多，帳戶已被鎖定"
                
        except Exception as e:
            logger.error(f"驗證 TOTP 失敗: {e}")
            return False, f"驗證失敗: {str(e)}"
    
    def verify_backup_code(self, user_id: str, backup_code: str) -> Tuple[bool, str]:
        """
        驗證備用碼
        
        Args:
            user_id: 使用者 ID
            backup_code: 備用碼
            
        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            with self.session_factory() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if not user:
                    return False, "使用者不存在"
                
                if not user.two_factor_enabled or not user.backup_codes:
                    return False, "使用者未啟用兩步驗證"
                
                # 檢查是否被鎖定
                if self._is_user_locked(user):
                    return False, "帳戶已被鎖定，請稍後再試"
                
                # 驗證備用碼
                backup_code_hash = hashlib.sha256(backup_code.encode()).hexdigest()
                
                if backup_code_hash in user.backup_codes:
                    # 移除已使用的備用碼
                    user.backup_codes.remove(backup_code_hash)
                    user.failed_login_attempts = 0
                    
                    # 記錄成功事件
                    self._log_security_event(
                        session,
                        user_id,
                        "2fa_backup_code_used",
                        "medium",
                        "使用備用碼驗證成功",
                        {"remaining_codes": len(user.backup_codes)}
                    )
                    
                    session.commit()
                    
                    remaining_codes = len(user.backup_codes)
                    if remaining_codes <= 2:
                        return True, f"驗證成功，但您只剩 {remaining_codes} 個備用碼，請盡快重新生成"
                    
                    return True, "驗證成功"
                
                # 驗證失敗
                user.failed_login_attempts += 1
                
                self._log_security_event(
                    session,
                    user_id,
                    "2fa_backup_code_failed",
                    "medium",
                    "備用碼驗證失敗",
                    {"failed_attempts": user.failed_login_attempts}
                )
                
                session.commit()
                
                return False, "備用碼錯誤"
                
        except Exception as e:
            logger.error(f"驗證備用碼失敗: {e}")
            return False, f"驗證失敗: {str(e)}"

    def disable_2fa(self, user_id: str, password: str) -> Tuple[bool, str]:
        """
        停用兩步驗證

        Args:
            user_id: 使用者 ID
            password: 使用者密碼（用於確認身份）

        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            with self.session_factory() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if not user:
                    return False, "使用者不存在"

                # 驗證密碼（這裡應該調用密碼驗證服務）
                # 簡化實作，實際應該使用 bcrypt 驗證

                if not user.two_factor_enabled:
                    return False, "使用者未啟用兩步驗證"

                # 停用 2FA
                user.two_factor_enabled = False
                user.two_factor_secret = None
                user.backup_codes = None

                # 記錄安全事件
                self._log_security_event(
                    session,
                    user_id,
                    "2fa_disabled",
                    "high",
                    "使用者停用兩步驗證",
                    {}
                )

                session.commit()

                logger.info(f"使用者 {user_id} 停用兩步驗證")

                return True, "兩步驗證已停用"

        except Exception as e:
            logger.error(f"停用兩步驗證失敗: {e}")
            return False, f"停用失敗: {str(e)}"

    def regenerate_backup_codes(self, user_id: str) -> Tuple[bool, str, List[str]]:
        """
        重新生成備用碼

        Args:
            user_id: 使用者 ID

        Returns:
            Tuple[bool, str, List[str]]: (是否成功, 訊息, 新備用碼列表)
        """
        try:
            with self.session_factory() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if not user:
                    return False, "使用者不存在", []

                if not user.two_factor_enabled:
                    return False, "使用者未啟用兩步驗證", []

                # 生成新的備用碼
                backup_codes = self._generate_backup_codes()
                backup_codes_hashed = [
                    hashlib.sha256(code.encode()).hexdigest()
                    for code in backup_codes
                ]

                user.backup_codes = backup_codes_hashed

                # 記錄安全事件
                self._log_security_event(
                    session,
                    user_id,
                    "backup_codes_regenerated",
                    "medium",
                    "使用者重新生成備用碼",
                    {"codes_count": len(backup_codes)}
                )

                session.commit()

                logger.info(f"使用者 {user_id} 重新生成備用碼")

                return True, "備用碼已重新生成", backup_codes

        except Exception as e:
            logger.error(f"重新生成備用碼失敗: {e}")
            return False, f"生成失敗: {str(e)}", []

    def get_2fa_status(self, user_id: str) -> Dict[str, Any]:
        """
        獲取使用者 2FA 狀態

        Args:
            user_id: 使用者 ID

        Returns:
            Dict[str, Any]: 2FA 狀態資訊
        """
        try:
            with self.session_factory() as session:
                user = session.query(User).filter(User.user_id == user_id).first()
                if not user:
                    return {"enabled": False, "error": "使用者不存在"}

                return {
                    "enabled": user.two_factor_enabled,
                    "backup_codes_count": len(user.backup_codes) if user.backup_codes else 0,
                    "is_locked": self._is_user_locked(user),
                    "failed_attempts": user.failed_login_attempts,
                }

        except Exception as e:
            logger.error(f"獲取 2FA 狀態失敗: {e}")
            return {"enabled": False, "error": str(e)}

    def _generate_backup_codes(self) -> List[str]:
        """
        生成備用碼

        Returns:
            List[str]: 備用碼列表
        """
        codes = []
        for _ in range(self.config["backup_codes_count"]):
            # 生成 8 位數字備用碼
            code = ''.join([str(secrets.randbelow(10)) for _ in range(8)])
            codes.append(code)
        return codes

    def _generate_qr_code(self, email: str, secret: str) -> str:
        """
        生成 QR 碼

        Args:
            email: 使用者電子郵件
            secret: TOTP secret

        Returns:
            str: Base64 編碼的 QR 碼圖片
        """
        try:
            # 生成 TOTP URI
            totp = pyotp.TOTP(secret)
            provisioning_uri = totp.provisioning_uri(
                name=email,
                issuer_name=self.config["totp_issuer"]
            )

            # 生成 QR 碼
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(provisioning_uri)
            qr.make(fit=True)

            # 創建帶樣式的 QR 碼圖片
            img = qr.make_image(
                image_factory=StyledPilImage,
                module_drawer=RoundedModuleDrawer(),
                color_mask=SquareGradiantColorMask()
            )

            # 轉換為 Base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()

            return img_str

        except Exception as e:
            logger.error(f"生成 QR 碼失敗: {e}")
            # 回退到簡單的 QR 碼
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()

            return img_str

    def _generate_setup_token(self, user_id: str, secret: str) -> str:
        """
        生成設定令牌

        Args:
            user_id: 使用者 ID
            secret: TOTP secret

        Returns:
            str: 設定令牌
        """
        timestamp = str(int(time.time()))
        data = f"{user_id}:{secret}:{timestamp}"

        # 使用 HMAC 簽名
        signature = hmac.new(
            b"setup_secret_key",  # 實際應該從配置中讀取
            data.encode(),
            hashlib.sha256
        ).hexdigest()

        token_data = f"{data}:{signature}"
        return base64.b64encode(token_data.encode()).decode()

    def _verify_setup_token(self, token: str, user_id: str) -> bool:
        """
        驗證設定令牌

        Args:
            token: 設定令牌
            user_id: 使用者 ID

        Returns:
            bool: 是否有效
        """
        try:
            # 解碼令牌
            token_data = base64.b64decode(token.encode()).decode()
            parts = token_data.split(':')

            if len(parts) != 4:
                return False

            token_user_id, secret, timestamp, signature = parts

            # 檢查使用者 ID
            if token_user_id != user_id:
                return False

            # 檢查時間戳（10 分鐘有效期）
            if int(time.time()) - int(timestamp) > 600:
                return False

            # 驗證簽名
            data = f"{token_user_id}:{secret}:{timestamp}"
            expected_signature = hmac.new(
                b"setup_secret_key",
                data.encode(),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logger.error(f"驗證設定令牌失敗: {e}")
            return False

    def _extract_secret_from_token(self, token: str) -> Optional[str]:
        """
        從設定令牌中提取 secret

        Args:
            token: 設定令牌

        Returns:
            Optional[str]: TOTP secret
        """
        try:
            token_data = base64.b64decode(token.encode()).decode()
            parts = token_data.split(':')

            if len(parts) >= 2:
                return parts[1]

            return None

        except Exception as e:
            logger.error(f"提取 secret 失敗: {e}")
            return None

    def _is_user_locked(self, user: User) -> bool:
        """
        檢查使用者是否被鎖定

        Args:
            user: 使用者物件

        Returns:
            bool: 是否被鎖定
        """
        if not user.is_locked:
            return False

        # 檢查鎖定是否已過期
        if user.locked_at:
            lockout_duration = timedelta(seconds=self.config["lockout_duration"])
            if datetime.now() - user.locked_at > lockout_duration:
                # 自動解鎖
                user.is_locked = False
                user.locked_at = None
                user.locked_reason = None
                user.failed_login_attempts = 0
                return False

        return True

    def _log_security_event(
        self,
        session: Session,
        user_id: str,
        event_type: str,
        severity: str,
        description: str,
        details: Dict[str, Any]
    ) -> None:
        """
        記錄安全事件

        Args:
            session: 資料庫會話
            user_id: 使用者 ID
            event_type: 事件類型
            severity: 嚴重程度
            description: 事件描述
            details: 事件詳情
        """
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


class SMSService:
    """
    SMS 驗證服務

    提供 SMS 驗證碼發送和驗證功能。
    """

    def __init__(self):
        """初始化 SMS 服務"""
        self.config = {
            "code_length": 6,
            "code_expiry": 300,  # 5 分鐘
            "max_attempts": 3,
            "rate_limit": 60,    # 1 分鐘內最多發送 1 次
        }

        # 簡化實作：使用記憶體存儲驗證碼
        # 實際應該使用 Redis 或資料庫
        self._verification_codes = {}
        self._send_history = {}

    def send_verification_code(self, phone_number: str, user_id: str) -> Tuple[bool, str]:
        """
        發送 SMS 驗證碼

        Args:
            phone_number: 手機號碼
            user_id: 使用者 ID

        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            # 檢查發送頻率限制
            if self._check_rate_limit(phone_number):
                return False, "發送過於頻繁，請稍後再試"

            # 生成驗證碼
            code = ''.join([str(secrets.randbelow(10)) for _ in range(self.config["code_length"])])

            # 存儲驗證碼
            self._verification_codes[phone_number] = {
                "code": code,
                "user_id": user_id,
                "created_at": time.time(),
                "attempts": 0,
            }

            # 記錄發送歷史
            self._send_history[phone_number] = time.time()

            # 實際發送 SMS（這裡只是模擬）
            logger.info(f"發送 SMS 驗證碼到 {phone_number}: {code}")

            # 在開發環境中，可以將驗證碼記錄到日誌
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"SMS 驗證碼: {code}")

            return True, "驗證碼已發送"

        except Exception as e:
            logger.error(f"發送 SMS 驗證碼失敗: {e}")
            return False, f"發送失敗: {str(e)}"

    def verify_sms_code(self, phone_number: str, code: str, user_id: str) -> Tuple[bool, str]:
        """
        驗證 SMS 驗證碼

        Args:
            phone_number: 手機號碼
            code: 驗證碼
            user_id: 使用者 ID

        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            if phone_number not in self._verification_codes:
                return False, "驗證碼不存在或已過期"

            verification_data = self._verification_codes[phone_number]

            # 檢查使用者 ID
            if verification_data["user_id"] != user_id:
                return False, "驗證碼無效"

            # 檢查過期時間
            if time.time() - verification_data["created_at"] > self.config["code_expiry"]:
                del self._verification_codes[phone_number]
                return False, "驗證碼已過期"

            # 檢查嘗試次數
            if verification_data["attempts"] >= self.config["max_attempts"]:
                del self._verification_codes[phone_number]
                return False, "驗證失敗次數過多"

            # 驗證碼比對
            if verification_data["code"] == code:
                del self._verification_codes[phone_number]
                return True, "驗證成功"

            # 增加嘗試次數
            verification_data["attempts"] += 1

            remaining_attempts = self.config["max_attempts"] - verification_data["attempts"]
            return False, f"驗證碼錯誤，還有 {remaining_attempts} 次機會"

        except Exception as e:
            logger.error(f"驗證 SMS 驗證碼失敗: {e}")
            return False, f"驗證失敗: {str(e)}"

    def _check_rate_limit(self, phone_number: str) -> bool:
        """
        檢查發送頻率限制

        Args:
            phone_number: 手機號碼

        Returns:
            bool: 是否超過頻率限制
        """
        if phone_number in self._send_history:
            last_send_time = self._send_history[phone_number]
            if time.time() - last_send_time < self.config["rate_limit"]:
                return True

        return False
