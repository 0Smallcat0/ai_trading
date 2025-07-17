"""
風險警報服務 (Risk Alert Service)

此模組提供風險警報的核心服務功能，包括：
- 風險事件警報
- 緊急風險通知
- 風險等級升級警報
- 風險摘要報告
- 警報規則管理

符合 Phase 7.2 程式碼品質標準：
- Pylint ≥8.5/10
- 100% Google Style Docstring 覆蓋率
- 完整型別標註
- 統一錯誤處理模式
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable

from ..risk.risk_monitor_service import RiskEvent, RiskLevel, RiskMetric
from .trade_notification_service import (
    TradeNotification, 
    NotificationChannel, 
    NotificationPriority
)


logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """警報嚴重程度枚舉"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertRule:
    """
    警報規則類別
    
    Attributes:
        rule_id: 規則唯一識別碼
        name: 規則名稱
        risk_metric: 風險指標
        risk_level: 觸發風險等級
        severity: 警報嚴重程度
        channels: 通知通道
        enabled: 是否啟用
        cooldown_minutes: 冷卻時間(分鐘)
        last_triggered: 最後觸發時間
    """

    def __init__(
        self,
        name: str,
        risk_metric: RiskMetric,
        risk_level: RiskLevel,
        severity: AlertSeverity,
        channels: Optional[List[NotificationChannel]] = None,
        cooldown_minutes: int = 30
    ):
        """
        初始化警報規則
        
        Args:
            name: 規則名稱
            risk_metric: 風險指標
            risk_level: 觸發風險等級
            severity: 警報嚴重程度
            channels: 通知通道列表
            cooldown_minutes: 冷卻時間(分鐘)
        """
        self.rule_id = f"alert_rule_{int(datetime.now().timestamp())}"
        self.name = name
        self.risk_metric = risk_metric
        self.risk_level = risk_level
        self.severity = severity
        self.channels = channels or [NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL]
        self.enabled = True
        self.cooldown_minutes = cooldown_minutes
        self.last_triggered: Optional[datetime] = None

    def can_trigger(self) -> bool:
        """
        檢查是否可以觸發警報
        
        Returns:
            bool: 是否可以觸發
        """
        if not self.enabled:
            return False
        
        if self.last_triggered is None:
            return True
        
        cooldown_period = timedelta(minutes=self.cooldown_minutes)
        return datetime.now() - self.last_triggered > cooldown_period

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式
        
        Returns:
            Dict[str, Any]: 警報規則資訊字典
        """
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "risk_metric": self.risk_metric.value,
            "risk_level": self.risk_level.value,
            "severity": self.severity.value,
            "channels": [channel.value for channel in self.channels],
            "enabled": self.enabled,
            "cooldown_minutes": self.cooldown_minutes,
            "last_triggered": self.last_triggered.isoformat() if self.last_triggered else None
        }


class RiskAlertError(Exception):
    """風險警報錯誤"""
    pass


class RiskAlertService:
    """
    風險警報服務
    
    提供風險相關的警報功能，包括風險事件警報、
    緊急通知、警報規則管理等。
    
    Attributes:
        _alert_rules: 警報規則列表
        _alert_history: 警報歷史記錄
        _alert_callbacks: 警報回調函數列表
        _notification_service: 通知服務 (可選)
    """

    def __init__(self, notification_service=None):
        """
        初始化風險警報服務
        
        Args:
            notification_service: 通知服務實例 (可選)
        """
        self._alert_rules: List[AlertRule] = []
        self._alert_history: List[Dict[str, Any]] = []
        self._alert_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._notification_service = notification_service
        
        # 初始化預設警報規則
        self._init_default_rules()
        
        logger.info("風險警報服務初始化成功")

    def handle_risk_event(self, risk_event: RiskEvent, user_id: str) -> List[str]:
        """
        處理風險事件
        
        Args:
            risk_event: 風險事件
            user_id: 用戶ID
            
        Returns:
            List[str]: 觸發的警報ID列表
        """
        triggered_alerts = []
        
        try:
            # 檢查匹配的警報規則
            matching_rules = self._find_matching_rules(risk_event)
            
            for rule in matching_rules:
                if rule.can_trigger():
                    alert_id = self._trigger_alert(rule, risk_event, user_id)
                    if alert_id:
                        triggered_alerts.append(alert_id)
                        rule.last_triggered = datetime.now()
            
            return triggered_alerts
            
        except Exception as e:
            logger.error("處理風險事件失敗: %s", e)
            return []

    def send_emergency_alert(
        self,
        title: str,
        message: str,
        user_id: str,
        severity: AlertSeverity = AlertSeverity.CRITICAL,
        **metadata
    ) -> str:
        """
        發送緊急警報
        
        Args:
            title: 警報標題
            message: 警報訊息
            user_id: 用戶ID
            severity: 嚴重程度
            **metadata: 額外資訊
            
        Returns:
            str: 警報ID
        """
        try:
            alert_data = {
                "alert_id": f"emergency_{int(datetime.now().timestamp() * 1000)}",
                "type": "emergency",
                "severity": severity.value,
                "title": title,
                "message": message,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata
            }
            
            # 記錄警報
            self._alert_history.append(alert_data)
            
            # 發送通知
            if self._notification_service:
                priority = self._severity_to_priority(severity)
                channels = self._get_emergency_channels(severity)
                
                notification = TradeNotification(
                    notification_type="risk_alert",
                    title=title,
                    message=message,
                    data=alert_data,
                    user_id=user_id,
                    priority=priority,
                    channels=channels
                )
                
                self._notification_service._send_notification(notification)
            
            # 觸發回調
            for callback in self._alert_callbacks:
                try:
                    callback(alert_data)
                except Exception as e:
                    logger.error("執行警報回調時發生錯誤: %s", e)
            
            logger.critical("緊急警報已發送: %s", title)
            return alert_data["alert_id"]
            
        except Exception as e:
            logger.error("發送緊急警報失敗: %s", e)
            raise RiskAlertError("緊急警報發送失敗") from e

    def add_alert_rule(self, rule: AlertRule) -> None:
        """
        添加警報規則
        
        Args:
            rule: 警報規則
        """
        self._alert_rules.append(rule)
        logger.info("已添加警報規則: %s", rule.name)

    def remove_alert_rule(self, rule_id: str) -> bool:
        """
        移除警報規則
        
        Args:
            rule_id: 規則ID
            
        Returns:
            bool: 移除是否成功
        """
        for i, rule in enumerate(self._alert_rules):
            if rule.rule_id == rule_id:
                removed_rule = self._alert_rules.pop(i)
                logger.info("已移除警報規則: %s", removed_rule.name)
                return True
        
        logger.warning("警報規則 %s 不存在", rule_id)
        return False

    def get_alert_rules(self) -> List[Dict[str, Any]]:
        """
        獲取警報規則列表
        
        Returns:
            List[Dict[str, Any]]: 警報規則列表
        """
        return [rule.to_dict() for rule in self._alert_rules]

    def get_alert_history(
        self,
        user_id: Optional[str] = None,
        hours: int = 24,
        severity: Optional[AlertSeverity] = None
    ) -> List[Dict[str, Any]]:
        """
        獲取警報歷史
        
        Args:
            user_id: 用戶ID篩選
            hours: 時間範圍(小時)
            severity: 嚴重程度篩選
            
        Returns:
            List[Dict[str, Any]]: 警報歷史列表
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_alerts = []
        for alert in self._alert_history:
            alert_time = datetime.fromisoformat(alert["timestamp"])
            
            if alert_time < cutoff_time:
                continue
            
            if user_id and alert.get("user_id") != user_id:
                continue
            
            if severity and alert.get("severity") != severity.value:
                continue
            
            filtered_alerts.append(alert)
        
        return sorted(filtered_alerts, key=lambda x: x["timestamp"], reverse=True)

    def get_alert_summary(self, user_id: str, hours: int = 24) -> Dict[str, Any]:
        """
        獲取警報摘要
        
        Args:
            user_id: 用戶ID
            hours: 時間範圍(小時)
            
        Returns:
            Dict[str, Any]: 警報摘要
        """
        alerts = self.get_alert_history(user_id, hours)
        
        summary = {
            "total_alerts": len(alerts),
            "by_severity": {},
            "by_type": {},
            "recent_critical": [],
            "time_range_hours": hours
        }
        
        for alert in alerts:
            # 按嚴重程度統計
            severity = alert.get("severity", "unknown")
            summary["by_severity"][severity] = summary["by_severity"].get(severity, 0) + 1
            
            # 按類型統計
            alert_type = alert.get("type", "unknown")
            summary["by_type"][alert_type] = summary["by_type"].get(alert_type, 0) + 1
            
            # 收集嚴重警報
            if severity == AlertSeverity.CRITICAL.value:
                summary["recent_critical"].append(alert)
        
        # 限制嚴重警報數量
        summary["recent_critical"] = summary["recent_critical"][:10]
        
        return summary

    def enable_rule(self, rule_id: str) -> bool:
        """
        啟用警報規則
        
        Args:
            rule_id: 規則ID
            
        Returns:
            bool: 操作是否成功
        """
        for rule in self._alert_rules:
            if rule.rule_id == rule_id:
                rule.enabled = True
                logger.info("警報規則 %s 已啟用", rule.name)
                return True
        
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """
        停用警報規則
        
        Args:
            rule_id: 規則ID
            
        Returns:
            bool: 操作是否成功
        """
        for rule in self._alert_rules:
            if rule.rule_id == rule_id:
                rule.enabled = False
                logger.info("警報規則 %s 已停用", rule.name)
                return True
        
        return False

    def add_alert_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        添加警報回調函數
        
        Args:
            callback: 回調函數，接收警報資料
        """
        self._alert_callbacks.append(callback)

    def _init_default_rules(self) -> None:
        """
        初始化預設警報規則
        """
        default_rules = [
            AlertRule(
                name="嚴重風險警報",
                risk_metric=RiskMetric.PORTFOLIO_VAR,
                risk_level=RiskLevel.CRITICAL,
                severity=AlertSeverity.CRITICAL,
                channels=[NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL, NotificationChannel.SMS],
                cooldown_minutes=15
            ),
            AlertRule(
                name="高風險警報",
                risk_metric=RiskMetric.PORTFOLIO_VAR,
                risk_level=RiskLevel.HIGH,
                severity=AlertSeverity.ERROR,
                channels=[NotificationChannel.WEBSOCKET, NotificationChannel.EMAIL],
                cooldown_minutes=30
            ),
            AlertRule(
                name="持倉集中度警報",
                risk_metric=RiskMetric.POSITION_CONCENTRATION,
                risk_level=RiskLevel.HIGH,
                severity=AlertSeverity.WARNING,
                channels=[NotificationChannel.WEBSOCKET],
                cooldown_minutes=60
            ),
            AlertRule(
                name="槓桿比率警報",
                risk_metric=RiskMetric.LEVERAGE_RATIO,
                risk_level=RiskLevel.HIGH,
                severity=AlertSeverity.WARNING,
                channels=[NotificationChannel.WEBSOCKET],
                cooldown_minutes=45
            )
        ]
        
        self._alert_rules.extend(default_rules)

    def _find_matching_rules(self, risk_event: RiskEvent) -> List[AlertRule]:
        """
        尋找匹配的警報規則
        
        Args:
            risk_event: 風險事件
            
        Returns:
            List[AlertRule]: 匹配的規則列表
        """
        matching_rules = []
        
        for rule in self._alert_rules:
            if (rule.risk_metric == risk_event.metric and 
                rule.risk_level == risk_event.level):
                matching_rules.append(rule)
        
        return matching_rules

    def _trigger_alert(
        self,
        rule: AlertRule,
        risk_event: RiskEvent,
        user_id: str
    ) -> Optional[str]:
        """
        觸發警報
        
        Args:
            rule: 警報規則
            risk_event: 風險事件
            user_id: 用戶ID
            
        Returns:
            Optional[str]: 警報ID，失敗時返回 None
        """
        try:
            alert_data = {
                "alert_id": f"risk_alert_{int(datetime.now().timestamp() * 1000)}",
                "type": "risk_event",
                "rule_id": rule.rule_id,
                "rule_name": rule.name,
                "severity": rule.severity.value,
                "title": f"風險警報: {rule.name}",
                "message": risk_event.message,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "risk_event": risk_event.to_dict()
            }
            
            # 記錄警報
            self._alert_history.append(alert_data)
            
            # 發送通知
            if self._notification_service:
                priority = self._severity_to_priority(rule.severity)
                
                notification = TradeNotification(
                    notification_type="risk_alert",
                    title=alert_data["title"],
                    message=alert_data["message"],
                    data=alert_data,
                    user_id=user_id,
                    priority=priority,
                    channels=rule.channels
                )
                
                self._notification_service._send_notification(notification)
            
            # 觸發回調
            for callback in self._alert_callbacks:
                try:
                    callback(alert_data)
                except Exception as e:
                    logger.error("執行警報回調時發生錯誤: %s", e)
            
            logger.warning("風險警報已觸發: %s", rule.name)
            return alert_data["alert_id"]
            
        except Exception as e:
            logger.error("觸發警報失敗: %s", e)
            return None

    def _severity_to_priority(self, severity: AlertSeverity) -> NotificationPriority:
        """
        將警報嚴重程度轉換為通知優先級
        
        Args:
            severity: 警報嚴重程度
            
        Returns:
            NotificationPriority: 通知優先級
        """
        mapping = {
            AlertSeverity.INFO: NotificationPriority.LOW,
            AlertSeverity.WARNING: NotificationPriority.NORMAL,
            AlertSeverity.ERROR: NotificationPriority.HIGH,
            AlertSeverity.CRITICAL: NotificationPriority.URGENT
        }
        return mapping.get(severity, NotificationPriority.NORMAL)

    def _get_emergency_channels(self, severity: AlertSeverity) -> List[NotificationChannel]:
        """
        根據嚴重程度獲取緊急通知通道
        
        Args:
            severity: 嚴重程度
            
        Returns:
            List[NotificationChannel]: 通知通道列表
        """
        if severity == AlertSeverity.CRITICAL:
            return [
                NotificationChannel.WEBSOCKET,
                NotificationChannel.EMAIL,
                NotificationChannel.SMS,
                NotificationChannel.PUSH
            ]
        elif severity == AlertSeverity.ERROR:
            return [
                NotificationChannel.WEBSOCKET,
                NotificationChannel.EMAIL,
                NotificationChannel.PUSH
            ]
        else:
            return [NotificationChannel.WEBSOCKET]
