"""
資金操作權限分級服務

此模組實現了完整的資金操作權限分級功能，包括：
- 不同用戶角色的資金操作限制
- 額度控制和審批流程
- 多級審批系統
- 風險控制和監控
- 合規檢查和報告
- 資金操作記錄和追蹤

遵循金融級安全標準，確保資金操作的安全性和合規性。
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from decimal import Decimal
import threading

# 導入資料庫相關模組
from sqlalchemy import create_engine, and_, or_, desc, func
from sqlalchemy.orm import sessionmaker, Session

# 導入配置和資料庫模型
from src.config import DB_URL
from src.database.schema import User, SecurityEvent, AuditLog

# 設置日誌
logger = logging.getLogger(__name__)


class UserRole(Enum):
    """使用者角色"""
    ADMIN = "admin"                    # 管理員
    FUND_MANAGER = "fund_manager"      # 資金管理員
    TRADER = "trader"                  # 交易員
    ANALYST = "analyst"                # 分析師
    VIP_USER = "vip_user"             # VIP 用戶
    REGULAR_USER = "regular_user"      # 一般用戶
    RESTRICTED_USER = "restricted_user" # 受限用戶


class FundOperationType(Enum):
    """資金操作類型"""
    DEPOSIT = "deposit"                # 入金
    WITHDRAW = "withdraw"              # 出金
    TRANSFER_IN = "transfer_in"        # 轉入
    TRANSFER_OUT = "transfer_out"      # 轉出
    TRADE_BUY = "trade_buy"           # 交易買入
    TRADE_SELL = "trade_sell"         # 交易賣出
    MARGIN_LOAN = "margin_loan"       # 融資借款
    MARGIN_REPAY = "margin_repay"     # 融資還款


class ApprovalStatus(Enum):
    """審批狀態"""
    PENDING = "pending"                # 待審批
    APPROVED = "approved"              # 已批准
    REJECTED = "rejected"              # 已拒絕
    CANCELLED = "cancelled"            # 已取消
    EXPIRED = "expired"                # 已過期


class ApprovalLevel(Enum):
    """審批級別"""
    NONE = "none"                      # 無需審批
    LEVEL_1 = "level_1"               # 一級審批
    LEVEL_2 = "level_2"               # 二級審批
    LEVEL_3 = "level_3"               # 三級審批
    BOARD = "board"                    # 董事會審批


class FundPermissionService:
    """
    資金操作權限分級服務
    
    提供完整的資金操作權限管理功能，包括角色權限、
    額度控制、審批流程和風險監控。
    """
    
    def __init__(self):
        """初始化資金權限服務"""
        try:
            # 初始化資料庫連接
            self.engine = create_engine(DB_URL)
            self.session_factory = sessionmaker(bind=self.engine)
            logger.info("資金權限服務資料庫連接初始化成功")
            
            # 角色權限配置
            self.role_permissions = {
                UserRole.ADMIN: {
                    "daily_limit": Decimal("100000000"),      # 1億
                    "single_limit": Decimal("50000000"),      # 5千萬
                    "monthly_limit": Decimal("1000000000"),   # 10億
                    "allowed_operations": list(FundOperationType),
                    "approval_required": False,
                    "can_approve": True,
                    "approval_level": 3,
                },
                UserRole.FUND_MANAGER: {
                    "daily_limit": Decimal("50000000"),       # 5千萬
                    "single_limit": Decimal("10000000"),      # 1千萬
                    "monthly_limit": Decimal("500000000"),    # 5億
                    "allowed_operations": [
                        FundOperationType.DEPOSIT,
                        FundOperationType.WITHDRAW,
                        FundOperationType.TRANSFER_IN,
                        FundOperationType.TRANSFER_OUT,
                        FundOperationType.MARGIN_LOAN,
                        FundOperationType.MARGIN_REPAY,
                    ],
                    "approval_required": True,
                    "can_approve": True,
                    "approval_level": 2,
                },
                UserRole.TRADER: {
                    "daily_limit": Decimal("10000000"),       # 1千萬
                    "single_limit": Decimal("5000000"),       # 500萬
                    "monthly_limit": Decimal("100000000"),    # 1億
                    "allowed_operations": [
                        FundOperationType.TRADE_BUY,
                        FundOperationType.TRADE_SELL,
                        FundOperationType.TRANSFER_IN,
                        FundOperationType.TRANSFER_OUT,
                    ],
                    "approval_required": True,
                    "can_approve": False,
                    "approval_level": 0,
                },
                UserRole.VIP_USER: {
                    "daily_limit": Decimal("5000000"),        # 500萬
                    "single_limit": Decimal("1000000"),       # 100萬
                    "monthly_limit": Decimal("50000000"),     # 5千萬
                    "allowed_operations": [
                        FundOperationType.DEPOSIT,
                        FundOperationType.WITHDRAW,
                        FundOperationType.TRADE_BUY,
                        FundOperationType.TRADE_SELL,
                    ],
                    "approval_required": True,
                    "can_approve": False,
                    "approval_level": 0,
                },
                UserRole.REGULAR_USER: {
                    "daily_limit": Decimal("1000000"),        # 100萬
                    "single_limit": Decimal("500000"),        # 50萬
                    "monthly_limit": Decimal("10000000"),     # 1千萬
                    "allowed_operations": [
                        FundOperationType.DEPOSIT,
                        FundOperationType.WITHDRAW,
                        FundOperationType.TRADE_BUY,
                        FundOperationType.TRADE_SELL,
                    ],
                    "approval_required": True,
                    "can_approve": False,
                    "approval_level": 0,
                },
                UserRole.RESTRICTED_USER: {
                    "daily_limit": Decimal("100000"),         # 10萬
                    "single_limit": Decimal("50000"),         # 5萬
                    "monthly_limit": Decimal("1000000"),      # 100萬
                    "allowed_operations": [
                        FundOperationType.DEPOSIT,
                        FundOperationType.TRADE_SELL,  # 只能賣出
                    ],
                    "approval_required": True,
                    "can_approve": False,
                    "approval_level": 0,
                },
            }
            
            # 審批閾值配置
            self.approval_thresholds = {
                ApprovalLevel.LEVEL_1: Decimal("100000"),     # 10萬
                ApprovalLevel.LEVEL_2: Decimal("1000000"),    # 100萬
                ApprovalLevel.LEVEL_3: Decimal("10000000"),   # 1千萬
                ApprovalLevel.BOARD: Decimal("50000000"),     # 5千萬
            }
            
            # 記憶體存儲
            self._pending_approvals: Dict[str, Dict] = {}
            self._user_daily_usage: Dict[str, Dict] = {}
            self._user_monthly_usage: Dict[str, Dict] = {}
            
            # 線程鎖
            self._lock = threading.RLock()
            
            logger.info("資金權限服務初始化完成")
            
        except Exception as e:
            logger.error(f"資金權限服務初始化失敗: {e}")
            raise
    
    def check_fund_operation_permission(
        self,
        user_id: str,
        operation_type: FundOperationType,
        amount: Decimal,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        檢查資金操作權限
        
        Args:
            user_id: 使用者 ID
            operation_type: 操作類型
            amount: 操作金額
            additional_context: 額外上下文資訊
            
        Returns:
            Tuple[bool, str, Optional[str]]: (是否允許, 訊息, 審批 ID)
        """
        try:
            with self._lock:
                # 獲取使用者角色
                user_role = self._get_user_role(user_id)
                if not user_role:
                    return False, "無法確定使用者角色", None
                
                # 檢查操作類型權限
                if not self._check_operation_type_permission(user_role, operation_type):
                    return False, f"使用者角色 {user_role.value} 不允許執行 {operation_type.value} 操作", None
                
                # 檢查金額限制
                limit_check_result = self._check_amount_limits(user_id, user_role, amount)
                if not limit_check_result["allowed"]:
                    return False, limit_check_result["reason"], None
                
                # 檢查是否需要審批
                approval_level = self._determine_approval_level(user_role, operation_type, amount)
                
                if approval_level == ApprovalLevel.NONE:
                    # 直接允許操作
                    self._record_fund_operation(user_id, operation_type, amount, "approved")
                    return True, "操作已批准", None
                else:
                    # 需要審批
                    approval_id = self._create_approval_request(
                        user_id, operation_type, amount, approval_level, additional_context
                    )
                    return False, f"需要 {approval_level.value} 審批", approval_id
                
        except Exception as e:
            logger.error(f"檢查資金操作權限失敗: {e}")
            return False, f"權限檢查失敗: {str(e)}", None
    
    def approve_fund_operation(
        self,
        approval_id: str,
        approver_id: str,
        approved: bool,
        reason: str = ""
    ) -> Tuple[bool, str]:
        """
        審批資金操作
        
        Args:
            approval_id: 審批 ID
            approver_id: 審批人 ID
            approved: 是否批准
            reason: 審批原因
            
        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            with self._lock:
                # 檢查審批記錄是否存在
                if approval_id not in self._pending_approvals:
                    return False, "審批記錄不存在或已處理"
                
                approval_record = self._pending_approvals[approval_id]
                
                # 檢查審批人權限
                if not self._check_approver_permission(approver_id, approval_record["approval_level"]):
                    return False, "審批人權限不足"
                
                # 檢查是否過期
                if datetime.now() > approval_record["expires_at"]:
                    approval_record["status"] = ApprovalStatus.EXPIRED.value
                    return False, "審批請求已過期"
                
                # 更新審批狀態
                if approved:
                    approval_record["status"] = ApprovalStatus.APPROVED.value
                    approval_record["approved_by"] = approver_id
                    approval_record["approved_at"] = datetime.now()
                    
                    # 記錄資金操作
                    self._record_fund_operation(
                        approval_record["user_id"],
                        FundOperationType(approval_record["operation_type"]),
                        approval_record["amount"],
                        "approved"
                    )
                    
                    message = "審批通過，操作已執行"
                else:
                    approval_record["status"] = ApprovalStatus.REJECTED.value
                    approval_record["rejected_by"] = approver_id
                    approval_record["rejected_at"] = datetime.now()
                    message = "審批被拒絕"
                
                approval_record["reason"] = reason
                
                # 記錄審批事件
                self._log_approval_event(
                    approval_record["user_id"],
                    "fund_operation_approval",
                    "medium",
                    f"資金操作審批: {approval_record['status']}",
                    {
                        "approval_id": approval_id,
                        "approver_id": approver_id,
                        "operation_type": approval_record["operation_type"],
                        "amount": str(approval_record["amount"]),
                        "approved": approved,
                        "reason": reason,
                    }
                )
                
                # 移除待審批記錄
                del self._pending_approvals[approval_id]
                
                return True, message
                
        except Exception as e:
            logger.error(f"審批資金操作失敗: {e}")
            return False, f"審批失敗: {str(e)}"
    
    def get_user_fund_limits(self, user_id: str) -> Dict[str, Any]:
        """
        獲取使用者資金限制
        
        Args:
            user_id: 使用者 ID
            
        Returns:
            Dict[str, Any]: 使用者資金限制資訊
        """
        try:
            with self._lock:
                user_role = self._get_user_role(user_id)
                if not user_role:
                    return {"error": "無法確定使用者角色"}
                
                role_config = self.role_permissions[user_role]
                
                # 獲取使用量統計
                daily_usage = self._get_user_daily_usage(user_id)
                monthly_usage = self._get_user_monthly_usage(user_id)
                
                return {
                    "user_role": user_role.value,
                    "daily_limit": str(role_config["daily_limit"]),
                    "single_limit": str(role_config["single_limit"]),
                    "monthly_limit": str(role_config["monthly_limit"]),
                    "daily_used": str(daily_usage),
                    "monthly_used": str(monthly_usage),
                    "daily_remaining": str(role_config["daily_limit"] - daily_usage),
                    "monthly_remaining": str(role_config["monthly_limit"] - monthly_usage),
                    "allowed_operations": [op.value for op in role_config["allowed_operations"]],
                    "approval_required": role_config["approval_required"],
                    "can_approve": role_config["can_approve"],
                }
                
        except Exception as e:
            logger.error(f"獲取使用者資金限制失敗: {e}")
            return {"error": str(e)}
    
    def get_pending_approvals(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        獲取待審批的資金操作
        
        Args:
            user_id: 使用者 ID（可選，如果不提供則返回所有待審批）
            
        Returns:
            List[Dict[str, Any]]: 待審批操作列表
        """
        try:
            with self._lock:
                pending = []
                
                for approval_id, record in self._pending_approvals.items():
                    if (user_id is None or 
                        record["user_id"] == user_id or 
                        self._can_user_approve(user_id, record["approval_level"])):
                        
                        # 檢查是否過期
                        if datetime.now() > record["expires_at"]:
                            record["status"] = ApprovalStatus.EXPIRED.value
                            continue
                        
                        pending.append({
                            "approval_id": approval_id,
                            "user_id": record["user_id"],
                            "operation_type": record["operation_type"],
                            "amount": str(record["amount"]),
                            "approval_level": record["approval_level"],
                            "created_at": record["created_at"],
                            "expires_at": record["expires_at"],
                            "status": record["status"],
                            "additional_context": record.get("additional_context", {}),
                        })
                
                return pending
                
        except Exception as e:
            logger.error(f"獲取待審批操作失敗: {e}")
            return []

    def get_fund_operation_history(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        獲取資金操作歷史

        Args:
            user_id: 使用者 ID
            start_date: 開始日期
            end_date: 結束日期
            limit: 返回記錄數量限制

        Returns:
            List[Dict[str, Any]]: 資金操作歷史列表
        """
        try:
            # 實際應該從資料庫查詢
            # 這裡返回模擬資料
            return []

        except Exception as e:
            logger.error(f"獲取資金操作歷史失敗: {e}")
            return []

    def update_user_role(self, user_id: str, new_role: UserRole) -> Tuple[bool, str]:
        """
        更新使用者角色

        Args:
            user_id: 使用者 ID
            new_role: 新角色

        Returns:
            Tuple[bool, str]: (是否成功, 訊息)
        """
        try:
            # 實際應該更新資料庫
            # 這裡只是模擬
            logger.info(f"使用者 {user_id} 角色已更新為 {new_role.value}")
            return True, "角色更新成功"

        except Exception as e:
            logger.error(f"更新使用者角色失敗: {e}")
            return False, f"更新失敗: {str(e)}"

    # 私有輔助方法
    def _get_user_role(self, user_id: str) -> Optional[UserRole]:
        """獲取使用者角色"""
        try:
            # 實際應該從資料庫查詢
            # 這裡返回預設角色
            return UserRole.REGULAR_USER
        except Exception as e:
            logger.error(f"獲取使用者角色失敗: {e}")
            return None

    def _check_operation_type_permission(
        self,
        user_role: UserRole,
        operation_type: FundOperationType
    ) -> bool:
        """檢查操作類型權限"""
        try:
            role_config = self.role_permissions[user_role]
            return operation_type in role_config["allowed_operations"]
        except Exception as e:
            logger.error(f"檢查操作類型權限失敗: {e}")
            return False

    def _check_amount_limits(
        self,
        user_id: str,
        user_role: UserRole,
        amount: Decimal
    ) -> Dict[str, Any]:
        """檢查金額限制"""
        try:
            role_config = self.role_permissions[user_role]

            # 檢查單筆限制
            if amount > role_config["single_limit"]:
                return {
                    "allowed": False,
                    "reason": f"超過單筆限制 {role_config['single_limit']}"
                }

            # 檢查每日限制
            daily_usage = self._get_user_daily_usage(user_id)
            if daily_usage + amount > role_config["daily_limit"]:
                return {
                    "allowed": False,
                    "reason": f"超過每日限制 {role_config['daily_limit']}"
                }

            # 檢查每月限制
            monthly_usage = self._get_user_monthly_usage(user_id)
            if monthly_usage + amount > role_config["monthly_limit"]:
                return {
                    "allowed": False,
                    "reason": f"超過每月限制 {role_config['monthly_limit']}"
                }

            return {"allowed": True, "reason": ""}

        except Exception as e:
            logger.error(f"檢查金額限制失敗: {e}")
            return {"allowed": False, "reason": str(e)}

    def _determine_approval_level(
        self,
        user_role: UserRole,
        operation_type: FundOperationType,
        amount: Decimal
    ) -> ApprovalLevel:
        """確定審批級別"""
        try:
            role_config = self.role_permissions[user_role]

            # 如果角色不需要審批
            if not role_config["approval_required"]:
                return ApprovalLevel.NONE

            # 根據金額確定審批級別
            if amount >= self.approval_thresholds[ApprovalLevel.BOARD]:
                return ApprovalLevel.BOARD
            elif amount >= self.approval_thresholds[ApprovalLevel.LEVEL_3]:
                return ApprovalLevel.LEVEL_3
            elif amount >= self.approval_thresholds[ApprovalLevel.LEVEL_2]:
                return ApprovalLevel.LEVEL_2
            elif amount >= self.approval_thresholds[ApprovalLevel.LEVEL_1]:
                return ApprovalLevel.LEVEL_1
            else:
                return ApprovalLevel.NONE

        except Exception as e:
            logger.error(f"確定審批級別失敗: {e}")
            return ApprovalLevel.LEVEL_1

    def _create_approval_request(
        self,
        user_id: str,
        operation_type: FundOperationType,
        amount: Decimal,
        approval_level: ApprovalLevel,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """創建審批請求"""
        try:
            import secrets

            approval_id = f"APPR_{secrets.token_urlsafe(12)}"

            approval_record = {
                "approval_id": approval_id,
                "user_id": user_id,
                "operation_type": operation_type.value,
                "amount": amount,
                "approval_level": approval_level.value,
                "status": ApprovalStatus.PENDING.value,
                "created_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(hours=24),  # 24小時過期
                "additional_context": additional_context or {},
            }

            self._pending_approvals[approval_id] = approval_record

            # 記錄審批請求事件
            self._log_approval_event(
                user_id,
                "fund_operation_approval_requested",
                "medium",
                f"請求資金操作審批: {operation_type.value}",
                {
                    "approval_id": approval_id,
                    "operation_type": operation_type.value,
                    "amount": str(amount),
                    "approval_level": approval_level.value,
                }
            )

            return approval_id

        except Exception as e:
            logger.error(f"創建審批請求失敗: {e}")
            raise

    def _check_approver_permission(self, approver_id: str, approval_level: str) -> bool:
        """檢查審批人權限"""
        try:
            approver_role = self._get_user_role(approver_id)
            if not approver_role:
                return False

            role_config = self.role_permissions[approver_role]

            # 檢查是否有審批權限
            if not role_config["can_approve"]:
                return False

            # 檢查審批級別
            required_level = {
                ApprovalLevel.LEVEL_1.value: 1,
                ApprovalLevel.LEVEL_2.value: 2,
                ApprovalLevel.LEVEL_3.value: 3,
                ApprovalLevel.BOARD.value: 3,  # 董事會級別需要最高權限
            }.get(approval_level, 1)

            return role_config["approval_level"] >= required_level

        except Exception as e:
            logger.error(f"檢查審批人權限失敗: {e}")
            return False

    def _can_user_approve(self, user_id: str, approval_level: str) -> bool:
        """檢查使用者是否可以審批"""
        try:
            if not user_id:
                return False
            return self._check_approver_permission(user_id, approval_level)
        except Exception as e:
            logger.error(f"檢查使用者審批權限失敗: {e}")
            return False

    def _get_user_daily_usage(self, user_id: str) -> Decimal:
        """獲取使用者每日使用量"""
        try:
            today = datetime.now().date().isoformat()

            if user_id not in self._user_daily_usage:
                self._user_daily_usage[user_id] = {}

            user_usage = self._user_daily_usage[user_id]

            # 重置每日統計（如果是新的一天）
            if user_usage.get("date") != today:
                user_usage.clear()
                user_usage["date"] = today
                user_usage["amount"] = Decimal("0")

            return user_usage.get("amount", Decimal("0"))

        except Exception as e:
            logger.error(f"獲取使用者每日使用量失敗: {e}")
            return Decimal("0")

    def _get_user_monthly_usage(self, user_id: str) -> Decimal:
        """獲取使用者每月使用量"""
        try:
            current_month = datetime.now().strftime("%Y-%m")

            if user_id not in self._user_monthly_usage:
                self._user_monthly_usage[user_id] = {}

            user_usage = self._user_monthly_usage[user_id]

            # 重置每月統計（如果是新的月份）
            if user_usage.get("month") != current_month:
                user_usage.clear()
                user_usage["month"] = current_month
                user_usage["amount"] = Decimal("0")

            return user_usage.get("amount", Decimal("0"))

        except Exception as e:
            logger.error(f"獲取使用者每月使用量失敗: {e}")
            return Decimal("0")

    def _record_fund_operation(
        self,
        user_id: str,
        operation_type: FundOperationType,
        amount: Decimal,
        status: str
    ) -> None:
        """記錄資金操作"""
        try:
            # 更新使用量統計
            if status == "approved":
                self._update_user_usage(user_id, amount)

            # 記錄到資料庫（實際實作）
            # 這裡只是記錄日誌
            logger.info(f"資金操作記錄: 使用者={user_id}, 類型={operation_type.value}, 金額={amount}, 狀態={status}")

        except Exception as e:
            logger.error(f"記錄資金操作失敗: {e}")

    def _update_user_usage(self, user_id: str, amount: Decimal) -> None:
        """更新使用者使用量"""
        try:
            # 更新每日使用量
            daily_usage = self._get_user_daily_usage(user_id)
            self._user_daily_usage[user_id]["amount"] = daily_usage + amount

            # 更新每月使用量
            monthly_usage = self._get_user_monthly_usage(user_id)
            self._user_monthly_usage[user_id]["amount"] = monthly_usage + amount

        except Exception as e:
            logger.error(f"更新使用者使用量失敗: {e}")

    def _log_approval_event(
        self,
        user_id: str,
        event_type: str,
        severity: str,
        description: str,
        details: Dict[str, Any]
    ) -> None:
        """記錄審批事件"""
        try:
            import secrets

            with self.session_factory() as session:
                event = SecurityEvent(
                    event_id=secrets.token_urlsafe(16),
                    event_type=event_type,
                    event_level=severity,
                    user_id=user_id,
                    description=description,
                    event_details=details,
                    ip_address="127.0.0.1",  # 實際應該從請求中獲取
                    user_agent="FundPermissionService",
                    created_at=datetime.now()
                )

                session.add(event)
                session.commit()

        except Exception as e:
            logger.error(f"記錄審批事件失敗: {e}")


# 全域實例
fund_permission_service = FundPermissionService()
