"""
合規監控模組

此模組實現了合規監控功能，包括反洗錢 (AML) 和了解客戶 (KYC) 檢查，
以符合監管要求。
"""

import os
import json
import logging
import threading
from enum import Enum
from typing import Dict, List, Set, Optional, Any, Union, Tuple
from datetime import datetime, timedelta

from src.core.logger import logger


class ComplianceRiskLevel(str, Enum):
    """合規風險等級"""
    LOW = "low"  # 低風險
    MEDIUM = "medium"  # 中風險
    HIGH = "high"  # 高風險
    CRITICAL = "critical"  # 嚴重風險


class ComplianceAlertType(str, Enum):
    """合規警報類型"""
    LARGE_TRANSACTION = "large_transaction"  # 大額交易
    UNUSUAL_PATTERN = "unusual_pattern"  # 異常模式
    RESTRICTED_ENTITY = "restricted_entity"  # 受限實體
    SUSPICIOUS_ACTIVITY = "suspicious_activity"  # 可疑活動
    KYC_INCOMPLETE = "kyc_incomplete"  # KYC 不完整
    KYC_EXPIRED = "kyc_expired"  # KYC 過期
    JURISDICTION_RISK = "jurisdiction_risk"  # 司法管轄區風險


class ComplianceAlert:
    """合規警報"""
    
    def __init__(
        self,
        alert_id: str,
        alert_type: ComplianceAlertType,
        risk_level: ComplianceRiskLevel,
        user_id: str,
        timestamp: datetime,
        details: Dict[str, Any],
        status: str = "open",
    ):
        """
        初始化合規警報
        
        Args:
            alert_id: 警報 ID
            alert_type: 警報類型
            risk_level: 風險等級
            user_id: 用戶 ID
            timestamp: 時間戳
            details: 詳細信息
            status: 狀態
        """
        self.alert_id = alert_id
        self.alert_type = alert_type
        self.risk_level = risk_level
        self.user_id = user_id
        self.timestamp = timestamp
        self.details = details
        self.status = status
        self.resolution = None
        self.resolved_by = None
        self.resolved_at = None
    
    def resolve(self, resolution: str, resolved_by: str) -> None:
        """
        解決警報
        
        Args:
            resolution: 解決方案
            resolved_by: 解決者
        """
        self.status = "resolved"
        self.resolution = resolution
        self.resolved_by = resolved_by
        self.resolved_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典
        
        Returns:
            Dict[str, Any]: 字典
        """
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "risk_level": self.risk_level.value,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "status": self.status,
            "resolution": self.resolution,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComplianceAlert":
        """
        從字典創建
        
        Args:
            data: 字典
            
        Returns:
            ComplianceAlert: 合規警報
        """
        alert = cls(
            alert_id=data["alert_id"],
            alert_type=ComplianceAlertType(data["alert_type"]),
            risk_level=ComplianceRiskLevel(data["risk_level"]),
            user_id=data["user_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            details=data["details"],
            status=data["status"],
        )
        
        if data.get("resolution"):
            alert.resolution = data["resolution"]
        
        if data.get("resolved_by"):
            alert.resolved_by = data["resolved_by"]
        
        if data.get("resolved_at"):
            alert.resolved_at = datetime.fromisoformat(data["resolved_at"])
        
        return alert


class ComplianceMonitor:
    """
    合規監控器
    
    監控交易活動，檢測可能的合規風險。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """實現單例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ComplianceMonitor, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(
        self,
        config_file: str = "config/compliance.json",
        alerts_file: str = "data/compliance/alerts.json",
    ):
        """
        初始化合規監控器
        
        Args:
            config_file: 配置文件路徑
            alerts_file: 警報文件路徑
        """
        # 避免重複初始化
        if self._initialized:
            return
        
        self.config_file = config_file
        self.alerts_file = alerts_file
        
        # 默認閾值
        self.thresholds = {
            "large_transaction": 100000,  # 大額交易閾值
            "unusual_pattern_window": 24,  # 異常模式檢測窗口（小時）
            "unusual_pattern_threshold": 5,  # 異常模式閾值
            "kyc_expiry_days": 365,  # KYC 過期天數
        }
        
        # 受限實體列表
        self.restricted_entities = set()
        
        # 高風險司法管轄區
        self.high_risk_jurisdictions = set()
        
        # 警報列表
        self.alerts: List[ComplianceAlert] = []
        
        # 用戶 KYC 信息
        self.user_kyc: Dict[str, Dict[str, Any]] = {}
        
        # 用戶交易歷史
        self.user_transactions: Dict[str, List[Dict[str, Any]]] = {}
        
        # 加載配置
        self.load_config()
        
        # 加載警報
        self.load_alerts()
        
        self._initialized = True
    
    def load_config(self) -> bool:
        """
        加載配置
        
        Returns:
            bool: 是否成功
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                # 加載閾值
                if "thresholds" in config:
                    self.thresholds.update(config["thresholds"])
                
                # 加載受限實體
                if "restricted_entities" in config:
                    self.restricted_entities = set(config["restricted_entities"])
                
                # 加載高風險司法管轄區
                if "high_risk_jurisdictions" in config:
                    self.high_risk_jurisdictions = set(config["high_risk_jurisdictions"])
                
                # 加載用戶 KYC 信息
                if "user_kyc" in config:
                    self.user_kyc = config["user_kyc"]
                
                logger.info(f"已加載合規配置: {self.config_file}")
                return True
            else:
                logger.warning(f"合規配置文件不存在: {self.config_file}")
                return False
        except Exception as e:
            logger.error(f"加載合規配置時發生錯誤: {e}")
            return False
    
    def save_config(self) -> bool:
        """
        保存配置
        
        Returns:
            bool: 是否成功
        """
        try:
            # 創建目錄
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            # 準備數據
            config = {
                "thresholds": self.thresholds,
                "restricted_entities": list(self.restricted_entities),
                "high_risk_jurisdictions": list(self.high_risk_jurisdictions),
                "user_kyc": self.user_kyc,
            }
            
            # 保存到文件
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存合規配置: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存合規配置時發生錯誤: {e}")
            return False
    
    def load_alerts(self) -> bool:
        """
        加載警報
        
        Returns:
            bool: 是否成功
        """
        try:
            if os.path.exists(self.alerts_file):
                with open(self.alerts_file, "r", encoding="utf-8") as f:
                    alerts_data = json.load(f)
                
                self.alerts = [ComplianceAlert.from_dict(alert) for alert in alerts_data]
                logger.info(f"已加載 {len(self.alerts)} 個合規警報")
                return True
            else:
                logger.warning(f"合規警報文件不存在: {self.alerts_file}")
                return False
        except Exception as e:
            logger.error(f"加載合規警報時發生錯誤: {e}")
            return False
    
    def save_alerts(self) -> bool:
        """
        保存警報
        
        Returns:
            bool: 是否成功
        """
        try:
            # 創建目錄
            os.makedirs(os.path.dirname(self.alerts_file), exist_ok=True)
            
            # 準備數據
            alerts_data = [alert.to_dict() for alert in self.alerts]
            
            # 保存到文件
            with open(self.alerts_file, "w", encoding="utf-8") as f:
                json.dump(alerts_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"已保存 {len(self.alerts)} 個合規警報")
            return True
        except Exception as e:
            logger.error(f"保存合規警報時發生錯誤: {e}")
            return False
    
    def check_transaction(
        self,
        user_id: str,
        transaction_id: str,
        amount: float,
        symbol: str,
        timestamp: datetime = None,
    ) -> Tuple[bool, Optional[ComplianceAlert]]:
        """
        檢查交易
        
        Args:
            user_id: 用戶 ID
            transaction_id: 交易 ID
            amount: 金額
            symbol: 股票代碼
            timestamp: 時間戳
            
        Returns:
            Tuple[bool, Optional[ComplianceAlert]]: (是否通過, 警報)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # 記錄交易
        if user_id not in self.user_transactions:
            self.user_transactions[user_id] = []
        
        self.user_transactions[user_id].append({
            "transaction_id": transaction_id,
            "amount": amount,
            "symbol": symbol,
            "timestamp": timestamp,
        })
        
        # 檢查大額交易
        if amount >= self.thresholds["large_transaction"]:
            alert = ComplianceAlert(
                alert_id=f"LT-{transaction_id}",
                alert_type=ComplianceAlertType.LARGE_TRANSACTION,
                risk_level=ComplianceRiskLevel.MEDIUM,
                user_id=user_id,
                timestamp=timestamp,
                details={
                    "transaction_id": transaction_id,
                    "amount": amount,
                    "symbol": symbol,
                    "threshold": self.thresholds["large_transaction"],
                },
            )
            self.alerts.append(alert)
            self.save_alerts()
            return False, alert
        
        # 檢查受限實體
        if symbol in self.restricted_entities:
            alert = ComplianceAlert(
                alert_id=f"RE-{transaction_id}",
                alert_type=ComplianceAlertType.RESTRICTED_ENTITY,
                risk_level=ComplianceRiskLevel.HIGH,
                user_id=user_id,
                timestamp=timestamp,
                details={
                    "transaction_id": transaction_id,
                    "amount": amount,
                    "symbol": symbol,
                },
            )
            self.alerts.append(alert)
            self.save_alerts()
            return False, alert
        
        # 檢查 KYC
        if user_id in self.user_kyc:
            kyc_info = self.user_kyc[user_id]
            
            # 檢查 KYC 是否完整
            if not kyc_info.get("is_complete", False):
                alert = ComplianceAlert(
                    alert_id=f"KYC-{transaction_id}",
                    alert_type=ComplianceAlertType.KYC_INCOMPLETE,
                    risk_level=ComplianceRiskLevel.HIGH,
                    user_id=user_id,
                    timestamp=timestamp,
                    details={
                        "transaction_id": transaction_id,
                        "amount": amount,
                        "symbol": symbol,
                    },
                )
                self.alerts.append(alert)
                self.save_alerts()
                return False, alert
            
            # 檢查 KYC 是否過期
            if "expiry_date" in kyc_info:
                expiry_date = datetime.fromisoformat(kyc_info["expiry_date"])
                if timestamp > expiry_date:
                    alert = ComplianceAlert(
                        alert_id=f"KYCE-{transaction_id}",
                        alert_type=ComplianceAlertType.KYC_EXPIRED,
                        risk_level=ComplianceRiskLevel.MEDIUM,
                        user_id=user_id,
                        timestamp=timestamp,
                        details={
                            "transaction_id": transaction_id,
                            "amount": amount,
                            "symbol": symbol,
                            "expiry_date": kyc_info["expiry_date"],
                        },
                    )
                    self.alerts.append(alert)
                    self.save_alerts()
                    return False, alert
            
            # 檢查司法管轄區風險
            if "jurisdiction" in kyc_info and kyc_info["jurisdiction"] in self.high_risk_jurisdictions:
                alert = ComplianceAlert(
                    alert_id=f"JR-{transaction_id}",
                    alert_type=ComplianceAlertType.JURISDICTION_RISK,
                    risk_level=ComplianceRiskLevel.HIGH,
                    user_id=user_id,
                    timestamp=timestamp,
                    details={
                        "transaction_id": transaction_id,
                        "amount": amount,
                        "symbol": symbol,
                        "jurisdiction": kyc_info["jurisdiction"],
                    },
                )
                self.alerts.append(alert)
                self.save_alerts()
                return False, alert
        
        return True, None


# 創建全局合規監控器實例
compliance_monitor = ComplianceMonitor()
