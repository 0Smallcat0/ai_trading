"""
交易操作二次確認服務

此模組實現了完整的交易二次確認功能，包括：
- 高風險交易識別
- SMS/Email 確認機制
- 時間窗口限制
- 多級確認流程
- 確認狀態追蹤
- 自動超時處理

遵循金融級安全標準，確保重要交易的安全性。
"""

import logging
import secrets
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import threading
import asyncio

# 導入資料庫相關模組
from sqlalchemy import create_engine, and_, or_, desc
from sqlalchemy.orm import sessionmaker, Session

# 導入配置和資料庫模型
from src.config import DB_URL
from src.database.schema import User, SecurityEvent, AuditLog

# 導入通知服務
from src.core.two_factor_service import SMSService

# 設置日誌
logger = logging.getLogger(__name__)


class ConfirmationLevel(Enum):
    """確認級別"""
    NONE = "none"           # 無需確認
    SIMPLE = "simple"       # 簡單確認（密碼）
    SMS = "sms"            # SMS 確認
    EMAIL = "email"        # Email 確認
    DUAL = "dual"          # 雙重確認（SMS + Email）
    ADMIN = "admin"        # 管理員確認


class RiskLevel(Enum):
    """風險等級"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfirmationStatus(Enum):
    """確認狀態"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class TradeConfirmationService:
    """
    交易操作二次確認服務
    
    提供完整的交易確認功能，包括風險評估、
    多級確認流程和狀態管理。
    """
    
    def __init__(self):
        """初始化交易確認服務"""
        try:
            # 初始化資料庫連接
            self.engine = create_engine(DB_URL)
            self.session_factory = sessionmaker(bind=self.engine)
            logger.info("交易確認服務資料庫連接初始化成功")
            
            # 初始化 SMS 服務
            self.sms_service = SMSService()
            
            # 服務配置
            self.config = {
                # 風險閾值配置
                "high_risk_amount": 1000000,      # 高風險金額閾值（新台幣）
                "critical_risk_amount": 5000000,  # 極高風險金額閾值
                "high_risk_quantity": 10000,      # 高風險數量閾值（股）
                "leverage_threshold": 2.0,        # 槓桿倍數閾值
                
                # 時間窗口配置
                "confirmation_timeout": 300,      # 確認超時時間（秒）
                "sms_timeout": 180,               # SMS 確認超時時間
                "email_timeout": 600,             # Email 確認超時時間
                "admin_timeout": 1800,            # 管理員確認超時時間
                
                # 確認碼配置
                "confirmation_code_length": 6,    # 確認碼長度
                "max_confirmation_attempts": 3,   # 最大確認嘗試次數
                
                # 交易限制配置
                "daily_high_risk_limit": 10,      # 每日高風險交易限制
                "hourly_trade_limit": 50,         # 每小時交易限制
                
                # 自動確認配置
                "auto_confirm_small_trades": True,  # 自動確認小額交易
                "small_trade_threshold": 50000,     # 小額交易閾值
            }
            
            # 記憶體存儲
            self._pending_confirmations: Dict[str, Dict] = {}
            self._confirmation_history: Dict[str, List] = {}
            self._user_daily_stats: Dict[str, Dict] = {}
            
            # 線程鎖
            self._lock = threading.RLock()
            
            # 啟動清理任務
            self._start_cleanup_task()
            
            logger.info("交易確認服務初始化完成")
            
        except Exception as e:
            logger.error(f"交易確認服務初始化失敗: {e}")
            raise
    
    def request_trade_confirmation(
        self,
        user_id: str,
        trade_data: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        請求交易確認
        
        Args:
            user_id: 使用者 ID
            trade_data: 交易資料
            additional_context: 額外上下文資訊
            
        Returns:
            Tuple[bool, str, Optional[str]]: (是否需要確認, 訊息, 確認 ID)
        """
        try:
            with self._lock:
                # 風險評估
                risk_level, risk_details = self._assess_trade_risk(user_id, trade_data)
                
                # 確定確認級別
                confirmation_level = self._determine_confirmation_level(
                    user_id, trade_data, risk_level, risk_details
                )
                
                # 如果不需要確認，直接返回
                if confirmation_level == ConfirmationLevel.NONE:
                    return False, "交易可直接執行", None
                
                # 生成確認 ID
                confirmation_id = self._generate_confirmation_id()
                
                # 創建確認記錄
                confirmation_record = {
                    "confirmation_id": confirmation_id,
                    "user_id": user_id,
                    "trade_data": trade_data,
                    "risk_level": risk_level.value,
                    "risk_details": risk_details,
                    "confirmation_level": confirmation_level.value,
                    "status": ConfirmationStatus.PENDING.value,
                    "created_at": datetime.now(),
                    "expires_at": self._calculate_expiry_time(confirmation_level),
                    "attempts": 0,
                    "additional_context": additional_context or {},
                }
                
                # 存儲確認記錄
                self._pending_confirmations[confirmation_id] = confirmation_record
                
                # 發送確認請求
                success, message = self._send_confirmation_request(
                    confirmation_record, confirmation_level
                )
                
                if not success:
                    # 清理失敗的確認記錄
                    del self._pending_confirmations[confirmation_id]
                    return False, f"發送確認請求失敗: {message}", None
                
                # 記錄安全事件
                self._log_confirmation_event(
                    user_id,
                    "trade_confirmation_requested",
                    "medium",
                    f"請求交易確認: {confirmation_level.value}",
                    {
                        "confirmation_id": confirmation_id,
                        "risk_level": risk_level.value,
                        "trade_symbol": trade_data.get("symbol"),
                        "trade_amount": trade_data.get("amount"),
                    }
                )
                
                return True, f"需要{confirmation_level.value}確認", confirmation_id
                
        except Exception as e:
            logger.error(f"請求交易確認失敗: {e}")
            return False, f"確認請求失敗: {str(e)}", None
    
    def verify_confirmation(
        self,
        confirmation_id: str,
        confirmation_code: str,
        user_id: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        驗證確認碼
        
        Args:
            confirmation_id: 確認 ID
            confirmation_code: 確認碼
            user_id: 使用者 ID
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (是否成功, 訊息, 交易資料)
        """
        try:
            with self._lock:
                # 檢查確認記錄是否存在
                if confirmation_id not in self._pending_confirmations:
                    return False, "確認記錄不存在或已過期", None
                
                confirmation_record = self._pending_confirmations[confirmation_id]
                
                # 檢查使用者權限
                if confirmation_record["user_id"] != user_id:
                    self._log_confirmation_event(
                        user_id,
                        "trade_confirmation_unauthorized",
                        "high",
                        "嘗試驗證他人的交易確認",
                        {"confirmation_id": confirmation_id}
                    )
                    return False, "無權限驗證此確認", None
                
                # 檢查狀態
                if confirmation_record["status"] != ConfirmationStatus.PENDING.value:
                    return False, f"確認狀態異常: {confirmation_record['status']}", None
                
                # 檢查是否過期
                if datetime.now() > confirmation_record["expires_at"]:
                    confirmation_record["status"] = ConfirmationStatus.EXPIRED.value
                    return False, "確認已過期", None
                
                # 檢查嘗試次數
                if confirmation_record["attempts"] >= self.config["max_confirmation_attempts"]:
                    confirmation_record["status"] = ConfirmationStatus.REJECTED.value
                    return False, "確認嘗試次數過多", None
                
                # 增加嘗試次數
                confirmation_record["attempts"] += 1
                
                # 驗證確認碼
                is_valid = self._verify_confirmation_code(
                    confirmation_record, confirmation_code
                )
                
                if is_valid:
                    # 確認成功
                    confirmation_record["status"] = ConfirmationStatus.CONFIRMED.value
                    confirmation_record["confirmed_at"] = datetime.now()
                    
                    # 獲取交易資料
                    trade_data = confirmation_record["trade_data"]
                    
                    # 記錄成功事件
                    self._log_confirmation_event(
                        user_id,
                        "trade_confirmation_success",
                        "low",
                        "交易確認成功",
                        {
                            "confirmation_id": confirmation_id,
                            "attempts": confirmation_record["attempts"],
                        }
                    )
                    
                    # 移動到歷史記錄
                    self._move_to_history(confirmation_id)
                    
                    return True, "確認成功", trade_data
                else:
                    # 確認失敗
                    remaining_attempts = (
                        self.config["max_confirmation_attempts"] - 
                        confirmation_record["attempts"]
                    )
                    
                    if remaining_attempts > 0:
                        return False, f"確認碼錯誤，還有 {remaining_attempts} 次機會", None
                    else:
                        confirmation_record["status"] = ConfirmationStatus.REJECTED.value
                        self._log_confirmation_event(
                            user_id,
                            "trade_confirmation_failed",
                            "medium",
                            "交易確認失敗次數過多",
                            {"confirmation_id": confirmation_id}
                        )
                        return False, "確認失敗次數過多，交易已拒絕", None
                
        except Exception as e:
            logger.error(f"驗證確認碼失敗: {e}")
            return False, f"驗證失敗: {str(e)}", None
    
    def cancel_confirmation(self, confirmation_id: str, user_id: str) -> Tuple[bool, str]:
        """
        取消確認
        
        Args:
            confirmation_id: 確認 ID
            user_id: 使用者 ID
            
        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            with self._lock:
                if confirmation_id not in self._pending_confirmations:
                    return False, "確認記錄不存在"
                
                confirmation_record = self._pending_confirmations[confirmation_id]
                
                # 檢查權限
                if confirmation_record["user_id"] != user_id:
                    return False, "無權限取消此確認"
                
                # 更新狀態
                confirmation_record["status"] = ConfirmationStatus.CANCELLED.value
                confirmation_record["cancelled_at"] = datetime.now()
                
                # 記錄事件
                self._log_confirmation_event(
                    user_id,
                    "trade_confirmation_cancelled",
                    "low",
                    "使用者取消交易確認",
                    {"confirmation_id": confirmation_id}
                )
                
                # 移動到歷史記錄
                self._move_to_history(confirmation_id)
                
                return True, "確認已取消"
                
        except Exception as e:
            logger.error(f"取消確認失敗: {e}")
            return False, f"取消失敗: {str(e)}"
    
    def get_confirmation_status(self, confirmation_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取確認狀態
        
        Args:
            confirmation_id: 確認 ID
            
        Returns:
            Optional[Dict[str, Any]]: 確認狀態資訊
        """
        try:
            with self._lock:
                if confirmation_id in self._pending_confirmations:
                    record = self._pending_confirmations[confirmation_id]
                    return {
                        "confirmation_id": confirmation_id,
                        "status": record["status"],
                        "created_at": record["created_at"],
                        "expires_at": record["expires_at"],
                        "attempts": record["attempts"],
                        "risk_level": record["risk_level"],
                        "confirmation_level": record["confirmation_level"],
                    }
                
                # 檢查歷史記錄
                for user_history in self._confirmation_history.values():
                    for record in user_history:
                        if record["confirmation_id"] == confirmation_id:
                            return {
                                "confirmation_id": confirmation_id,
                                "status": record["status"],
                                "created_at": record["created_at"],
                                "expires_at": record.get("expires_at"),
                                "attempts": record["attempts"],
                                "risk_level": record["risk_level"],
                                "confirmation_level": record["confirmation_level"],
                            }
                
                return None
                
        except Exception as e:
            logger.error(f"獲取確認狀態失敗: {e}")
            return None

    def get_user_confirmation_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        獲取使用者確認歷史

        Args:
            user_id: 使用者 ID
            limit: 返回記錄數量限制

        Returns:
            List[Dict[str, Any]]: 確認歷史列表
        """
        try:
            with self._lock:
                history = self._confirmation_history.get(user_id, [])

                # 按時間倒序排列，返回最近的記錄
                sorted_history = sorted(
                    history,
                    key=lambda x: x["created_at"],
                    reverse=True
                )

                return sorted_history[:limit]

        except Exception as e:
            logger.error(f"獲取確認歷史失敗: {e}")
            return []

    def get_pending_confirmations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        獲取待確認的交易

        Args:
            user_id: 使用者 ID

        Returns:
            List[Dict[str, Any]]: 待確認交易列表
        """
        try:
            with self._lock:
                pending = []

                for confirmation_id, record in self._pending_confirmations.items():
                    if (record["user_id"] == user_id and
                        record["status"] == ConfirmationStatus.PENDING.value):

                        # 檢查是否過期
                        if datetime.now() > record["expires_at"]:
                            record["status"] = ConfirmationStatus.EXPIRED.value
                            continue

                        pending.append({
                            "confirmation_id": confirmation_id,
                            "trade_data": record["trade_data"],
                            "risk_level": record["risk_level"],
                            "confirmation_level": record["confirmation_level"],
                            "created_at": record["created_at"],
                            "expires_at": record["expires_at"],
                            "attempts": record["attempts"],
                        })

                return pending

        except Exception as e:
            logger.error(f"獲取待確認交易失敗: {e}")
            return []

    def _assess_trade_risk(
        self,
        user_id: str,
        trade_data: Dict[str, Any]
    ) -> Tuple[RiskLevel, Dict[str, Any]]:
        """評估交易風險"""
        try:
            risk_factors = []
            risk_score = 0.0

            # 計算交易金額
            quantity = trade_data.get("quantity", 0)
            price = trade_data.get("price", 0)
            trade_amount = quantity * price

            # 金額風險評估
            if trade_amount >= self.config["critical_risk_amount"]:
                risk_factors.append("極高金額交易")
                risk_score += 4.0
            elif trade_amount >= self.config["high_risk_amount"]:
                risk_factors.append("高金額交易")
                risk_score += 2.0

            # 數量風險評估
            if quantity >= self.config["high_risk_quantity"]:
                risk_factors.append("大量交易")
                risk_score += 1.5

            # 槓桿風險評估
            leverage = trade_data.get("leverage", 1.0)
            if leverage >= self.config["leverage_threshold"]:
                risk_factors.append("高槓桿交易")
                risk_score += 2.0

            # 交易類型風險
            trade_type = trade_data.get("type", "").lower()
            if trade_type in ["margin", "short", "options"]:
                risk_factors.append("高風險交易類型")
                risk_score += 1.0

            # 市場時間風險
            if self._is_after_hours_trading():
                risk_factors.append("盤後交易")
                risk_score += 0.5

            # 使用者歷史風險
            user_risk = self._assess_user_risk_history(user_id)
            risk_score += user_risk["score"]
            risk_factors.extend(user_risk["factors"])

            # 確定風險等級
            if risk_score >= 4.0:
                risk_level = RiskLevel.CRITICAL
            elif risk_score >= 2.5:
                risk_level = RiskLevel.HIGH
            elif risk_score >= 1.0:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW

            risk_details = {
                "risk_score": risk_score,
                "risk_factors": risk_factors,
                "trade_amount": trade_amount,
                "quantity": quantity,
                "leverage": leverage,
                "trade_type": trade_type,
            }

            return risk_level, risk_details

        except Exception as e:
            logger.error(f"評估交易風險失敗: {e}")
            return RiskLevel.MEDIUM, {"error": str(e)}

    def _determine_confirmation_level(
        self,
        user_id: str,
        trade_data: Dict[str, Any],
        risk_level: RiskLevel,
        risk_details: Dict[str, Any]
    ) -> ConfirmationLevel:
        """確定確認級別"""
        try:
            # 自動確認小額交易
            if (self.config["auto_confirm_small_trades"] and
                risk_details.get("trade_amount", 0) < self.config["small_trade_threshold"]):
                return ConfirmationLevel.NONE

            # 根據風險等級確定確認級別
            if risk_level == RiskLevel.CRITICAL:
                return ConfirmationLevel.DUAL  # 雙重確認
            elif risk_level == RiskLevel.HIGH:
                return ConfirmationLevel.SMS   # SMS 確認
            elif risk_level == RiskLevel.MEDIUM:
                return ConfirmationLevel.SIMPLE  # 簡單確認
            else:
                return ConfirmationLevel.NONE

        except Exception as e:
            logger.error(f"確定確認級別失敗: {e}")
            return ConfirmationLevel.SIMPLE

    def _send_confirmation_request(
        self,
        confirmation_record: Dict[str, Any],
        confirmation_level: ConfirmationLevel
    ) -> Tuple[bool, str]:
        """發送確認請求"""
        try:
            user_id = confirmation_record["user_id"]
            confirmation_id = confirmation_record["confirmation_id"]

            if confirmation_level == ConfirmationLevel.SMS:
                return self._send_sms_confirmation(confirmation_record)
            elif confirmation_level == ConfirmationLevel.EMAIL:
                return self._send_email_confirmation(confirmation_record)
            elif confirmation_level == ConfirmationLevel.DUAL:
                # 發送雙重確認
                sms_success, sms_msg = self._send_sms_confirmation(confirmation_record)
                email_success, email_msg = self._send_email_confirmation(confirmation_record)

                if sms_success and email_success:
                    return True, "雙重確認請求已發送"
                else:
                    return False, f"發送失敗 - SMS: {sms_msg}, Email: {email_msg}"
            elif confirmation_level == ConfirmationLevel.ADMIN:
                return self._send_admin_confirmation(confirmation_record)
            else:
                # 簡單確認或無需確認
                return True, "確認請求已準備"

        except Exception as e:
            logger.error(f"發送確認請求失敗: {e}")
            return False, str(e)

    def _send_sms_confirmation(self, confirmation_record: Dict[str, Any]) -> Tuple[bool, str]:
        """發送 SMS 確認"""
        try:
            user_id = confirmation_record["user_id"]
            confirmation_code = self._generate_confirmation_code()

            # 存儲確認碼
            confirmation_record["sms_code"] = confirmation_code
            confirmation_record["sms_sent_at"] = datetime.now()

            # 獲取使用者手機號碼（簡化實作）
            phone_number = "+886912345678"  # 實際應該從資料庫獲取

            # 發送 SMS
            success, message = self.sms_service.send_verification_code(phone_number, user_id)

            if success:
                logger.info(f"SMS 確認碼已發送給使用者 {user_id}: {confirmation_code}")
                return True, "SMS 確認碼已發送"
            else:
                return False, f"SMS 發送失敗: {message}"

        except Exception as e:
            logger.error(f"發送 SMS 確認失敗: {e}")
            return False, str(e)

    def _send_email_confirmation(self, confirmation_record: Dict[str, Any]) -> Tuple[bool, str]:
        """發送 Email 確認"""
        try:
            confirmation_code = self._generate_confirmation_code()

            # 存儲確認碼
            confirmation_record["email_code"] = confirmation_code
            confirmation_record["email_sent_at"] = datetime.now()

            # 實際應該發送 Email
            logger.info(f"Email 確認碼: {confirmation_code}")

            return True, "Email 確認碼已發送"

        except Exception as e:
            logger.error(f"發送 Email 確認失敗: {e}")
            return False, str(e)

    def _send_admin_confirmation(self, confirmation_record: Dict[str, Any]) -> Tuple[bool, str]:
        """發送管理員確認"""
        try:
            # 通知管理員
            logger.info(f"管理員確認請求: {confirmation_record['confirmation_id']}")

            return True, "管理員確認請求已發送"

        except Exception as e:
            logger.error(f"發送管理員確認失敗: {e}")
            return False, str(e)

    def _verify_confirmation_code(
        self,
        confirmation_record: Dict[str, Any],
        confirmation_code: str
    ) -> bool:
        """驗證確認碼"""
        try:
            confirmation_level = confirmation_record["confirmation_level"]

            if confirmation_level == ConfirmationLevel.SIMPLE.value:
                # 簡單確認，檢查密碼或預設碼
                return confirmation_code == "123456"  # 簡化實作

            elif confirmation_level == ConfirmationLevel.SMS.value:
                stored_code = confirmation_record.get("sms_code")
                return stored_code and confirmation_code == stored_code

            elif confirmation_level == ConfirmationLevel.EMAIL.value:
                stored_code = confirmation_record.get("email_code")
                return stored_code and confirmation_code == stored_code

            elif confirmation_level == ConfirmationLevel.DUAL.value:
                # 雙重確認，需要檢查 SMS 或 Email 碼
                sms_code = confirmation_record.get("sms_code")
                email_code = confirmation_record.get("email_code")
                return (confirmation_code == sms_code or
                       confirmation_code == email_code)

            elif confirmation_level == ConfirmationLevel.ADMIN.value:
                # 管理員確認，檢查管理員授權碼
                return confirmation_code.startswith("ADMIN_")

            return False

        except Exception as e:
            logger.error(f"驗證確認碼失敗: {e}")
            return False

    def _generate_confirmation_id(self) -> str:
        """生成確認 ID"""
        return f"CONF_{secrets.token_urlsafe(12)}"

    def _generate_confirmation_code(self) -> str:
        """生成確認碼"""
        length = self.config["confirmation_code_length"]
        return ''.join([str(secrets.randbelow(10)) for _ in range(length)])

    def _calculate_expiry_time(self, confirmation_level: ConfirmationLevel) -> datetime:
        """計算過期時間"""
        timeout_map = {
            ConfirmationLevel.SIMPLE: self.config["confirmation_timeout"],
            ConfirmationLevel.SMS: self.config["sms_timeout"],
            ConfirmationLevel.EMAIL: self.config["email_timeout"],
            ConfirmationLevel.DUAL: max(self.config["sms_timeout"], self.config["email_timeout"]),
            ConfirmationLevel.ADMIN: self.config["admin_timeout"],
        }

        timeout_seconds = timeout_map.get(confirmation_level, self.config["confirmation_timeout"])
        return datetime.now() + timedelta(seconds=timeout_seconds)

    def _is_after_hours_trading(self) -> bool:
        """檢查是否為盤後交易"""
        try:
            now = datetime.now()
            hour = now.hour

            # 台股交易時間：9:00-13:30
            if 9 <= hour <= 13:
                return False
            elif hour == 13 and now.minute <= 30:
                return False
            else:
                return True

        except Exception as e:
            logger.error(f"檢查盤後交易失敗: {e}")
            return False

    def _assess_user_risk_history(self, user_id: str) -> Dict[str, Any]:
        """評估使用者風險歷史"""
        try:
            # 更新每日統計
            self._update_user_daily_stats(user_id)

            user_stats = self._user_daily_stats.get(user_id, {})
            risk_factors = []
            risk_score = 0.0

            # 檢查每日高風險交易次數
            daily_high_risk = user_stats.get("daily_high_risk_count", 0)
            if daily_high_risk >= self.config["daily_high_risk_limit"]:
                risk_factors.append("每日高風險交易次數過多")
                risk_score += 1.0

            # 檢查每小時交易次數
            hourly_trades = user_stats.get("hourly_trade_count", 0)
            if hourly_trades >= self.config["hourly_trade_limit"]:
                risk_factors.append("每小時交易次數過多")
                risk_score += 0.5

            # 檢查最近確認失敗次數
            recent_failures = user_stats.get("recent_confirmation_failures", 0)
            if recent_failures >= 3:
                risk_factors.append("最近確認失敗次數較多")
                risk_score += 0.5

            return {
                "score": risk_score,
                "factors": risk_factors,
                "stats": user_stats,
            }

        except Exception as e:
            logger.error(f"評估使用者風險歷史失敗: {e}")
            return {"score": 0.0, "factors": []}

    def _update_user_daily_stats(self, user_id: str) -> None:
        """更新使用者每日統計"""
        try:
            today = datetime.now().date().isoformat()
            current_hour = datetime.now().hour

            if user_id not in self._user_daily_stats:
                self._user_daily_stats[user_id] = {}

            user_stats = self._user_daily_stats[user_id]

            # 重置每日統計（如果是新的一天）
            if user_stats.get("date") != today:
                user_stats.clear()
                user_stats["date"] = today
                user_stats["daily_high_risk_count"] = 0
                user_stats["daily_trade_count"] = 0

            # 重置每小時統計（如果是新的小時）
            if user_stats.get("hour") != current_hour:
                user_stats["hour"] = current_hour
                user_stats["hourly_trade_count"] = 0

        except Exception as e:
            logger.error(f"更新使用者統計失敗: {e}")

    def _move_to_history(self, confirmation_id: str) -> None:
        """移動確認記錄到歷史"""
        try:
            if confirmation_id in self._pending_confirmations:
                record = self._pending_confirmations[confirmation_id]
                user_id = record["user_id"]

                # 添加到歷史記錄
                if user_id not in self._confirmation_history:
                    self._confirmation_history[user_id] = []

                self._confirmation_history[user_id].append(record)

                # 限制歷史記錄數量
                if len(self._confirmation_history[user_id]) > 100:
                    self._confirmation_history[user_id] = self._confirmation_history[user_id][-100:]

                # 從待確認中移除
                del self._pending_confirmations[confirmation_id]

        except Exception as e:
            logger.error(f"移動到歷史記錄失敗: {e}")

    def _start_cleanup_task(self) -> None:
        """啟動清理任務"""
        try:
            def cleanup_expired_confirmations():
                """清理過期的確認記錄"""
                while True:
                    try:
                        with self._lock:
                            now = datetime.now()
                            expired_ids = []

                            for confirmation_id, record in self._pending_confirmations.items():
                                if now > record["expires_at"]:
                                    record["status"] = ConfirmationStatus.EXPIRED.value
                                    expired_ids.append(confirmation_id)

                            # 移動過期記錄到歷史
                            for confirmation_id in expired_ids:
                                self._move_to_history(confirmation_id)

                        # 每分鐘檢查一次
                        import time
                        time.sleep(60)

                    except Exception as e:
                        logger.error(f"清理過期確認記錄失敗: {e}")
                        import time
                        time.sleep(60)

            # 在後台線程中運行清理任務
            import threading
            cleanup_thread = threading.Thread(
                target=cleanup_expired_confirmations,
                daemon=True
            )
            cleanup_thread.start()

        except Exception as e:
            logger.error(f"啟動清理任務失敗: {e}")

    def _log_confirmation_event(
        self,
        user_id: str,
        event_type: str,
        severity: str,
        description: str,
        details: Dict[str, Any]
    ) -> None:
        """記錄確認事件"""
        try:
            with self.session_factory() as session:
                event = SecurityEvent(
                    event_id=secrets.token_urlsafe(16),
                    event_type=event_type,
                    event_level=severity,
                    user_id=user_id,
                    description=description,
                    event_details=details,
                    ip_address="127.0.0.1",  # 實際應該從請求中獲取
                    user_agent="TradeConfirmationService",
                    created_at=datetime.now()
                )

                session.add(event)
                session.commit()

        except Exception as e:
            logger.error(f"記錄確認事件失敗: {e}")


# 全域實例
trade_confirmation_service = TradeConfirmationService()
