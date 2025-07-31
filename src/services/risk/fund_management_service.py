"""
資金管理服務 (Fund Management Service)

此模組提供資金管理的核心服務功能，包括：
- 資金使用監控
- 保證金計算
- 購買力管理
- 資金分配策略
- 風險資本控制

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥8.5/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import logging
import threading
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable

from ..broker.account_sync_service import AccountSyncService, AccountInfo


logger = logging.getLogger(__name__)


class FundAllocationStrategy(Enum):
    """資金分配策略枚舉"""
    EQUAL_WEIGHT = "equal_weight"
    RISK_PARITY = "risk_parity"
    MARKET_CAP_WEIGHT = "market_cap_weight"
    CUSTOM = "custom"


class FundAlert(Enum):
    """資金警報類型枚舉"""
    LOW_CASH = "low_cash"
    HIGH_UTILIZATION = "high_utilization"
    MARGIN_CALL = "margin_call"
    INSUFFICIENT_BUYING_POWER = "insufficient_buying_power"


class FundRule:
    """
    資金規則類別
    
    Attributes:
        rule_id: 規則唯一識別碼
        name: 規則名稱
        rule_type: 規則類型
        threshold: 閾值
        action: 觸發動作
        enabled: 是否啟用
        created_at: 創建時間
    """

    def __init__(
        self,
        name: str,
        rule_type: str,
        threshold: float,
        action: str,
        enabled: bool = True
    ):
        """
        初始化資金規則
        
        Args:
            name: 規則名稱
            rule_type: 規則類型
            threshold: 閾值
            action: 觸發動作
            enabled: 是否啟用
        """
        self.rule_id = f"fund_rule_{int(datetime.now().timestamp())}"
        self.name = name
        self.rule_type = rule_type
        self.threshold = threshold
        self.action = action
        self.enabled = enabled
        self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式
        
        Returns:
            Dict[str, Any]: 資金規則資訊字典
        """
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "rule_type": self.rule_type,
            "threshold": self.threshold,
            "action": self.action,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat()
        }


class FundManagementError(Exception):
    """資金管理錯誤"""
    pass


class FundManagementService:
    """
    資金管理服務
    
    提供資金管理功能，包括資金監控、分配策略、
    風險控制等。
    
    Attributes:
        _account_service: 帳戶同步服務
        _fund_rules: 資金規則列表
        _allocation_strategy: 資金分配策略
        _alert_callbacks: 警報回調函數列表
        _lock: 執行緒鎖
    """

    def __init__(self, account_service: Optional[AccountSyncService] = None):
        """
        初始化資金管理服務
        
        Args:
            account_service: 帳戶同步服務實例
        """
        self._account_service = account_service or AccountSyncService()
        self._fund_rules: List[FundRule] = []
        self._allocation_strategy = FundAllocationStrategy.EQUAL_WEIGHT
        self._alert_callbacks: List[Callable[[FundAlert, Dict[str, Any]], None]] = []
        self._lock = threading.Lock()
        
        # 初始化預設規則
        self._init_default_rules()
        
        logger.info("資金管理服務初始化成功")

    def get_fund_summary(self) -> Dict[str, Any]:
        """
        獲取資金摘要
        
        Returns:
            Dict[str, Any]: 資金摘要資訊
        """
        try:
            accounts = self._account_service.get_all_accounts()
            
            total_cash = 0.0
            total_value = 0.0
            total_buying_power = 0.0
            account_details = {}
            
            for broker_name, account_info in accounts.items():
                total_cash += account_info.cash
                total_value += account_info.total_value
                total_buying_power += account_info.buying_power
                
                account_details[broker_name] = {
                    "cash": account_info.cash,
                    "total_value": account_info.total_value,
                    "buying_power": account_info.buying_power,
                    "utilization": self._calculate_utilization(account_info)
                }
            
            return {
                "total_cash": total_cash,
                "total_value": total_value,
                "total_buying_power": total_buying_power,
                "overall_utilization": self._calculate_overall_utilization(),
                "account_details": account_details,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error("獲取資金摘要失敗: %s", e)
            raise FundManagementError("資金摘要獲取失敗") from e

    def check_buying_power(
        self,
        symbol: str,
        quantity: int,
        price: float,
        broker_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        檢查購買力
        
        Args:
            symbol: 股票代號
            quantity: 數量
            price: 價格
            broker_name: 券商名稱
            
        Returns:
            Dict[str, Any]: 購買力檢查結果
        """
        try:
            required_amount = quantity * price
            
            if broker_name:
                account_info = self._account_service.get_account_info(broker_name)
                if not account_info:
                    return {
                        "sufficient": False,
                        "reason": f"券商 {broker_name} 帳戶資訊不存在"
                    }
                
                available_power = account_info.buying_power
                sufficient = available_power >= required_amount
                
                return {
                    "sufficient": sufficient,
                    "required_amount": required_amount,
                    "available_power": available_power,
                    "remaining_power": available_power - required_amount if sufficient else 0,
                    "broker_name": broker_name,
                    "reason": "購買力充足" if sufficient else "購買力不足"
                }
            else:
                # 檢查所有券商的總購買力
                total_buying_power = self._account_service.get_total_cash()  # 簡化計算
                sufficient = total_buying_power >= required_amount
                
                return {
                    "sufficient": sufficient,
                    "required_amount": required_amount,
                    "total_buying_power": total_buying_power,
                    "remaining_power": total_buying_power - required_amount if sufficient else 0,
                    "reason": "購買力充足" if sufficient else "購買力不足"
                }
                
        except Exception as e:
            logger.error("檢查購買力失敗: %s", e)
            return {
                "sufficient": False,
                "reason": f"檢查失敗: {str(e)}"
            }

    def calculate_position_size(
        self,
        symbol: str,
        risk_percentage: float = 0.02,
        stop_loss_percentage: float = 0.05
    ) -> Dict[str, Any]:
        """
        計算建議部位大小
        
        Args:
            symbol: 股票代號
            risk_percentage: 風險百分比 (預設 2%)
            stop_loss_percentage: 停損百分比 (預設 5%)
            
        Returns:
            Dict[str, Any]: 建議部位大小資訊
        """
        try:
            total_value = self._account_service.get_total_portfolio_value()
            risk_amount = total_value * risk_percentage
            
            # 簡化的部位大小計算
            # 實際應該考慮股票價格、波動率等因素
            suggested_amount = risk_amount / stop_loss_percentage
            
            return {
                "symbol": symbol,
                "total_portfolio_value": total_value,
                "risk_percentage": risk_percentage,
                "risk_amount": risk_amount,
                "stop_loss_percentage": stop_loss_percentage,
                "suggested_amount": suggested_amount,
                "max_position_percentage": suggested_amount / total_value if total_value > 0 else 0
            }
            
        except Exception as e:
            logger.error("計算建議部位大小失敗: %s", e)
            raise FundManagementError("部位大小計算失敗") from e

    def set_allocation_strategy(self, strategy: FundAllocationStrategy) -> None:
        """
        設定資金分配策略
        
        Args:
            strategy: 資金分配策略
        """
        with self._lock:
            self._allocation_strategy = strategy
        
        logger.info("資金分配策略已設定為: %s", strategy.value)

    def add_fund_rule(self, rule: FundRule) -> None:
        """
        添加資金規則
        
        Args:
            rule: 資金規則
        """
        with self._lock:
            self._fund_rules.append(rule)
        
        logger.info("已添加資金規則: %s", rule.name)

    def remove_fund_rule(self, rule_id: str) -> bool:
        """
        移除資金規則
        
        Args:
            rule_id: 規則ID
            
        Returns:
            bool: 移除是否成功
        """
        with self._lock:
            for i, rule in enumerate(self._fund_rules):
                if rule.rule_id == rule_id:
                    removed_rule = self._fund_rules.pop(i)
                    logger.info("已移除資金規則: %s", removed_rule.name)
                    return True
        
        logger.warning("資金規則 %s 不存在", rule_id)
        return False

    def get_fund_rules(self) -> List[Dict[str, Any]]:
        """
        獲取資金規則列表
        
        Returns:
            List[Dict[str, Any]]: 資金規則列表
        """
        with self._lock:
            return [rule.to_dict() for rule in self._fund_rules]

    def check_fund_rules(self) -> List[Dict[str, Any]]:
        """
        檢查資金規則
        
        Returns:
            List[Dict[str, Any]]: 觸發的規則列表
        """
        triggered_rules = []
        
        try:
            fund_summary = self.get_fund_summary()
            
            with self._lock:
                for rule in self._fund_rules:
                    if not rule.enabled:
                        continue
                    
                    if self._check_rule(rule, fund_summary):
                        triggered_rules.append({
                            "rule": rule.to_dict(),
                            "current_value": self._get_rule_value(rule, fund_summary),
                            "threshold": rule.threshold,
                            "action": rule.action
                        })
            
            return triggered_rules
            
        except Exception as e:
            logger.error("檢查資金規則失敗: %s", e)
            return []

    def add_alert_callback(
        self, 
        callback: Callable[[FundAlert, Dict[str, Any]], None]
    ) -> None:
        """
        添加警報回調函數
        
        Args:
            callback: 回調函數，接收警報類型和詳細資訊
        """
        self._alert_callbacks.append(callback)

    def _init_default_rules(self) -> None:
        """
        初始化預設資金規則
        """
        default_rules = [
            FundRule(
                name="現金不足警報",
                rule_type="cash_ratio",
                threshold=0.05,  # 現金比例低於 5%
                action="alert"
            ),
            FundRule(
                name="高資金使用率警報",
                rule_type="utilization",
                threshold=0.90,  # 資金使用率超過 90%
                action="alert"
            ),
            FundRule(
                name="購買力不足警報",
                rule_type="buying_power_ratio",
                threshold=0.10,  # 購買力比例低於 10%
                action="alert"
            )
        ]
        
        with self._lock:
            self._fund_rules.extend(default_rules)

    def _calculate_utilization(self, account_info: AccountInfo) -> float:
        """
        計算帳戶資金使用率
        
        Args:
            account_info: 帳戶資訊
            
        Returns:
            float: 資金使用率 (0-1)
        """
        if account_info.total_value <= 0:
            return 0.0
        
        used_amount = account_info.total_value - account_info.cash
        return used_amount / account_info.total_value

    def _calculate_overall_utilization(self) -> float:
        """
        計算整體資金使用率
        
        Returns:
            float: 整體資金使用率 (0-1)
        """
        total_value = self._account_service.get_total_portfolio_value()
        total_cash = self._account_service.get_total_cash()
        
        if total_value <= 0:
            return 0.0
        
        used_amount = total_value - total_cash
        return used_amount / total_value

    def _check_rule(self, rule: FundRule, fund_summary: Dict[str, Any]) -> bool:
        """
        檢查單個資金規則
        
        Args:
            rule: 資金規則
            fund_summary: 資金摘要
            
        Returns:
            bool: 規則是否被觸發
        """
        try:
            current_value = self._get_rule_value(rule, fund_summary)
            
            if rule.rule_type in ["cash_ratio", "buying_power_ratio"]:
                return current_value < rule.threshold
            elif rule.rule_type == "utilization":
                return current_value > rule.threshold
            else:
                return False
                
        except Exception as e:
            logger.error("檢查規則 %s 失敗: %s", rule.name, e)
            return False

    def _get_rule_value(self, rule: FundRule, fund_summary: Dict[str, Any]) -> float:
        """
        獲取規則對應的當前值
        
        Args:
            rule: 資金規則
            fund_summary: 資金摘要
            
        Returns:
            float: 當前值
        """
        if rule.rule_type == "cash_ratio":
            total_value = fund_summary.get("total_value", 0)
            total_cash = fund_summary.get("total_cash", 0)
            return total_cash / total_value if total_value > 0 else 0
        elif rule.rule_type == "utilization":
            return fund_summary.get("overall_utilization", 0)
        elif rule.rule_type == "buying_power_ratio":
            total_value = fund_summary.get("total_value", 0)
            total_buying_power = fund_summary.get("total_buying_power", 0)
            return total_buying_power / total_value if total_value > 0 else 0
        else:
            return 0.0
