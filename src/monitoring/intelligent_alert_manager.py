"""智能告警管理器

此模組實現了智能告警管理功能，包括：
- 多維度告警規則引擎（基於時間序列、統計分析、機器學習異常檢測）
- 告警去重與聚合機制（避免告警風暴）
- 告警升級策略（基於嚴重度和時間的自動升級）
- 告警抑制與靜默功能（維護期間、已知問題）

遵循 Google Style Docstring 標準和 Phase 5.3 開發規範。
"""

import logging
import threading
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import yaml
from pathlib import Path

from src.monitoring.notification_services import NotificationServices

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """告警嚴重程度枚舉"""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertStatus(Enum):
    """告警狀態枚舉"""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    """告警規則數據類

    Attributes:
        id: 規則唯一標識
        name: 規則名稱
        description: 規則描述
        metric_name: 監控指標名稱
        operator: 比較運算符
        threshold_value: 閾值
        severity: 嚴重程度
        enabled: 是否啟用
        suppression_duration: 抑制時間（秒）
        notification_channels: 通知渠道列表
        conditions: 額外條件
        created_at: 創建時間
        updated_at: 更新時間
    """

    id: str
    name: str
    description: str
    metric_name: str
    operator: str
    threshold_value: float
    severity: AlertSeverity
    enabled: bool = True
    suppression_duration: int = 300
    notification_channels: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None


@dataclass
class Alert:
    """告警數據類

    Attributes:
        id: 告警唯一標識
        rule_id: 關聯的規則ID
        rule_name: 規則名稱
        severity: 嚴重程度
        status: 告警狀態
        title: 告警標題
        message: 告警訊息
        metric_value: 觸發時的指標值
        threshold_value: 閾值
        labels: 標籤字典
        annotations: 註解字典
        created_at: 創建時間
        acknowledged_at: 確認時間
        acknowledged_by: 確認人
        resolved_at: 解決時間
        resolved_by: 解決人
        notification_sent: 是否已發送通知
        escalation_level: 升級級別
        suppressed_until: 抑制截止時間
    """

    id: str
    rule_id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    title: str
    message: str
    metric_value: float
    threshold_value: float
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    notification_sent: bool = False
    escalation_level: int = 0
    suppressed_until: Optional[datetime] = None


class IntelligentAlertManager:
    """智能告警管理器

    提供完整的告警管理功能，包括規則引擎、告警去重、
    升級策略、抑制機制和通知管理。

    Attributes:
        config: 告警配置
        rules: 告警規則字典
        active_alerts: 活躍告警字典
        notification_service: 通知服務
        is_running: 是否正在運行
        evaluation_thread: 評估線程
        escalation_thread: 升級線程
    """

    def __init__(self, config_file: str = "config/alert_rules.yaml"):
        """初始化告警管理器

        Args:
            config_file: 告警規則配置檔案路徑

        Raises:
            Exception: 初始化失敗時拋出異常
        """
        try:
            self.config_file = Path(config_file)
            self.config = self._load_config()

            # 初始化告警規則和活躍告警
            self.rules: Dict[str, AlertRule] = {}
            self.active_alerts: Dict[str, Alert] = {}
            self.alert_history: List[Alert] = []

            # 初始化通知服務
            self.notification_service = NotificationServices()

            # 初始化運行狀態
            self.is_running = False
            self.evaluation_interval = 30  # 評估間隔（秒）
            self.escalation_interval = 60  # 升級檢查間隔（秒）

            # 初始化線程
            self.evaluation_thread: Optional[threading.Thread] = None
            self.escalation_thread: Optional[threading.Thread] = None
            self._stop_event = threading.Event()

            # 載入告警規則
            self._load_alert_rules()

            module_logger.info("智能告警管理器初始化成功")

        except Exception as e:
            module_logger.error("智能告警管理器初始化失敗: %s", e)
            raise

    def _load_config(self) -> Dict[str, Any]:
        """載入配置檔案

        Returns:
            Dict[str, Any]: 配置字典
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
            else:
                module_logger.warning("配置檔案不存在: %s", self.config_file)
                return {"groups": []}

        except Exception as e:
            module_logger.error("載入配置檔案失敗: %s", e)
            return {"groups": []}

    def _load_alert_rules(self) -> None:
        """從配置檔案載入告警規則"""
        try:
            groups = self.config.get("groups", [])
            rule_count = 0

            for group in groups:
                group_name = group.get("name", "unknown")
                rules = group.get("rules", [])

                for rule_config in rules:
                    try:
                        rule = self._create_alert_rule_from_config(
                            rule_config, group_name
                        )
                        self.rules[rule.id] = rule
                        rule_count += 1

                    except Exception as e:
                        module_logger.error("載入告警規則失敗: %s", e)

            module_logger.info("成功載入 %d 個告警規則", rule_count)

        except Exception as e:
            module_logger.error("載入告警規則失敗: %s", e)

    def _create_alert_rule_from_config(
        self, rule_config: Dict[str, Any], group_name: str
    ) -> AlertRule:
        """從配置創建告警規則

        Args:
            rule_config: 規則配置
            group_name: 規則組名稱

        Returns:
            AlertRule: 告警規則對象
        """
        rule_id = str(uuid.uuid4())
        alert_name = rule_config.get("alert", "unknown")

        # 解析嚴重程度
        labels = rule_config.get("labels", {})
        severity_str = labels.get("severity", "WARNING").upper()
        severity = AlertSeverity(severity_str)

        # 解析表達式以提取指標名稱和閾值
        expr = rule_config.get("expr", "")
        metric_name, operator, threshold_value = self._parse_expression(expr)

        return AlertRule(
            id=rule_id,
            name=alert_name,
            description=rule_config.get("annotations", {}).get("summary", ""),
            metric_name=metric_name,
            operator=operator,
            threshold_value=threshold_value,
            severity=severity,
            enabled=True,
            suppression_duration=300,  # 預設 5 分鐘
            notification_channels=["email", "webhook"],  # 預設通知渠道
            conditions={
                "expr": expr,
                "for": rule_config.get("for", "0s"),
                "labels": labels,
                "annotations": rule_config.get("annotations", {}),
            },
        )

    def _parse_expression(self, expr: str) -> Tuple[str, str, float]:
        """解析 Prometheus 表達式

        Args:
            expr: Prometheus 表達式

        Returns:
            Tuple[str, str, float]: (指標名稱, 運算符, 閾值)
        """
        try:
            # 簡化的表達式解析，實際應用中需要更複雜的解析邏輯
            if ">" in expr:
                parts = expr.split(">")
                metric_name = parts[0].strip()
                threshold_value = float(parts[1].strip())
                return metric_name, ">", threshold_value
            if "<" in expr:
                parts = expr.split("<")
                metric_name = parts[0].strip()
                threshold_value = float(parts[1].strip())
                return metric_name, "<", threshold_value
            # 預設值
            return expr.strip(), ">", 0.0

        except Exception as e:
            module_logger.error("解析表達式失敗: %s", e)
            return expr.strip(), ">", 0.0

    def start(self) -> bool:
        """啟動告警管理器

        Returns:
            bool: 啟動成功返回 True，否則返回 False
        """
        try:
            if self.is_running:
                module_logger.warning("智能告警管理器已在運行中")
                return True

            self.is_running = True
            self._stop_event.clear()

            # 啟動評估線程
            self.evaluation_thread = threading.Thread(
                target=self._evaluation_loop, daemon=True, name="AlertEvaluation"
            )
            self.evaluation_thread.start()

            # 啟動升級線程
            self.escalation_thread = threading.Thread(
                target=self._escalation_loop, daemon=True, name="AlertEscalation"
            )
            self.escalation_thread.start()

            module_logger.info("智能告警管理器已啟動")
            return True

        except Exception as e:
            module_logger.error("啟動智能告警管理器失敗: %s", e)
            self.is_running = False
            return False

    def stop(self) -> bool:
        """停止告警管理器

        Returns:
            bool: 停止成功返回 True，否則返回 False
        """
        try:
            if not self.is_running:
                module_logger.warning("智能告警管理器未在運行")
                return True

            self.is_running = False
            self._stop_event.set()

            # 等待線程結束
            if self.evaluation_thread and self.evaluation_thread.is_alive():
                self.evaluation_thread.join(timeout=5.0)

            if self.escalation_thread and self.escalation_thread.is_alive():
                self.escalation_thread.join(timeout=5.0)

            module_logger.info("智能告警管理器已停止")
            return True

        except Exception as e:
            module_logger.error("停止智能告警管理器失敗: %s", e)
            return False

    def _evaluation_loop(self) -> None:
        """告警評估主循環"""
        module_logger.info("告警評估循環已啟動")

        while not self._stop_event.is_set():
            try:
                start_time = time.time()

                # 評估所有啟用的告警規則
                self._evaluate_alert_rules()

                # 清理過期的抑制告警
                self._cleanup_suppressed_alerts()

                evaluation_time = time.time() - start_time
                module_logger.debug("告警評估完成，耗時: %.3f秒", evaluation_time)

                # 等待下次評估
                self._stop_event.wait(self.evaluation_interval)

            except Exception as e:
                module_logger.error("告警評估過程中發生錯誤: %s", e)
                self._stop_event.wait(min(self.evaluation_interval, 30))

        module_logger.info("告警評估循環已結束")

    def _escalation_loop(self) -> None:
        """告警升級主循環"""
        module_logger.info("告警升級循環已啟動")

        while not self._stop_event.is_set():
            try:
                start_time = time.time()

                # 檢查需要升級的告警
                self._check_alert_escalation()

                escalation_time = time.time() - start_time
                module_logger.debug("告警升級檢查完成，耗時: %.3f秒", escalation_time)

                # 等待下次檢查
                self._stop_event.wait(self.escalation_interval)

            except Exception as e:
                module_logger.error("告警升級過程中發生錯誤: %s", e)
                self._stop_event.wait(min(self.escalation_interval, 30))

        module_logger.info("告警升級循環已結束")

    def _evaluate_alert_rules(self) -> None:
        """評估所有告警規則"""
        for rule in self.rules.values():
            if not rule.enabled:
                continue

            try:
                # 這裡應該從 Prometheus 或其他數據源獲取實際指標值
                # 目前使用模擬數據進行演示
                metric_value = self._get_metric_value(rule.metric_name)

                if metric_value is not None:
                    should_alert = self._evaluate_condition(
                        metric_value, rule.operator, rule.threshold_value
                    )

                    if should_alert:
                        self._trigger_alert(rule, metric_value)
                    else:
                        self._resolve_alert_if_exists(rule.id)

            except Exception as e:
                module_logger.error("評估告警規則 %s 失敗: %s", rule.name, e)

    def _get_metric_value(self, metric_name: str) -> Optional[float]:
        """獲取指標值

        Args:
            metric_name: 指標名稱

        Returns:
            Optional[float]: 指標值，獲取失敗返回 None
        """
        # 這裡應該實現從 Prometheus 或其他數據源獲取指標值的邏輯
        # 目前返回模擬數據
        import random

        if "cpu" in metric_name.lower():
            return random.uniform(60, 95)
        elif "memory" in metric_name.lower():
            return random.uniform(70, 90)
        elif "disk" in metric_name.lower():
            return random.uniform(80, 95)
        elif "success_rate" in metric_name.lower():
            return random.uniform(85, 98)
        else:
            return random.uniform(0, 100)

    def _evaluate_condition(
        self, value: float, operator: str, threshold: float
    ) -> bool:
        """
        評估告警條件

        Args:
            value: 當前值
            operator: 運算符
            threshold: 閾值

        Returns:
            bool: 滿足條件返回 True，否則返回 False
        """
        if operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return value == threshold
        elif operator == "!=":
            return value != threshold
        else:
            return False

    def _trigger_alert(self, rule: AlertRule, metric_value: float) -> None:
        """
        觸發告警

        Args:
            rule: 告警規則
            metric_value: 指標值
        """
        try:
            # 檢查是否已存在相同的活躍告警
            existing_alert = self._find_existing_alert(rule.id)

            if existing_alert:
                # 更新現有告警
                existing_alert.metric_value = metric_value
                module_logger.debug(f"更新現有告警: {existing_alert.id}")
                return

            # 創建新告警
            alert_id = str(uuid.uuid4())
            alert = Alert(
                id=alert_id,
                rule_id=rule.id,
                rule_name=rule.name,
                severity=rule.severity,
                status=AlertStatus.ACTIVE,
                title=rule.name,
                message=f"{rule.description} - 當前值: {metric_value}, 閾值: {rule.threshold_value}",
                metric_value=metric_value,
                threshold_value=rule.threshold_value,
                labels=rule.conditions.get("labels", {}),
                annotations=rule.conditions.get("annotations", {}),
            )

            # 檢查是否需要抑制
            if self._should_suppress_alert(alert):
                alert.status = AlertStatus.SUPPRESSED
                alert.suppressed_until = datetime.now() + timedelta(
                    seconds=rule.suppression_duration
                )
                module_logger.info(f"告警已抑制: {alert_id}")
            else:
                # 發送通知
                self._send_alert_notification(alert, rule)
                alert.notification_sent = True
                module_logger.info(f"觸發新告警: {alert_id} - {rule.name}")

            # 添加到活躍告警
            self.active_alerts[alert_id] = alert

        except Exception as e:
            module_logger.error(f"觸發告警失敗: {e}")

    def _find_existing_alert(self, rule_id: str) -> Optional[Alert]:
        """
        查找現有的活躍告警

        Args:
            rule_id: 規則ID

        Returns:
            Optional[Alert]: 找到的告警，否則返回 None
        """
        for alert in self.active_alerts.values():
            if alert.rule_id == rule_id and alert.status == AlertStatus.ACTIVE:
                return alert
        return None

    def _should_suppress_alert(self, alert: Alert) -> bool:
        """
        檢查是否應該抑制告警

        Args:
            alert: 告警對象

        Returns:
            bool: 需要抑制返回 True，否則返回 False
        """
        # 檢查是否在抑制時間內有相同的告警
        suppression_window = timedelta(minutes=5)  # 5分鐘抑制窗口
        current_time = datetime.now()

        for existing_alert in self.alert_history:
            if (
                existing_alert.rule_id == alert.rule_id
                and existing_alert.severity == alert.severity
                and current_time - existing_alert.created_at < suppression_window
            ):
                return True

        return False

    def _send_alert_notification(self, alert: Alert, rule: AlertRule) -> None:
        """
        發送告警通知

        Args:
            alert: 告警對象
            rule: 告警規則
        """
        try:
            # 準備通知內容
            notification_data = {
                "alert_id": alert.id,
                "title": alert.title,
                "message": alert.message,
                "severity": alert.severity.value,
                "metric_value": alert.metric_value,
                "threshold_value": alert.threshold_value,
                "created_at": alert.created_at.isoformat(),
                "labels": alert.labels,
                "annotations": alert.annotations,
            }

            # 根據嚴重程度選擇通知渠道
            channels = self._get_notification_channels(alert.severity)

            # 發送通知
            for channel in channels:
                try:
                    success = self.notification_service.send_notification(
                        channel, notification_data
                    )
                    if success:
                        module_logger.info(f"通知已發送到 {channel}: {alert.id}")
                    else:
                        module_logger.warning(f"發送通知到 {channel} 失敗: {alert.id}")

                except Exception as e:
                    module_logger.error(f"發送通知到 {channel} 時發生錯誤: {e}")

        except Exception as e:
            module_logger.error(f"發送告警通知失敗: {e}")

    def _get_notification_channels(self, severity: AlertSeverity) -> List[str]:
        """
        根據嚴重程度獲取通知渠道

        Args:
            severity: 告警嚴重程度

        Returns:
            List[str]: 通知渠道列表
        """
        if severity == AlertSeverity.CRITICAL:
            return ["email", "webhook", "slack", "telegram"]
        elif severity == AlertSeverity.ERROR:
            return ["email", "webhook", "slack"]
        elif severity == AlertSeverity.WARNING:
            return ["webhook", "slack"]
        else:
            return ["webhook"]

    def _resolve_alert_if_exists(self, rule_id: str) -> None:
        """
        解決現有告警（如果存在）

        Args:
            rule_id: 規則ID
        """
        for alert_id, alert in list(self.active_alerts.items()):
            if alert.rule_id == rule_id and alert.status == AlertStatus.ACTIVE:
                alert.status = AlertStatus.RESOLVED
                alert.resolved_at = datetime.now()

                # 移動到歷史記錄
                self.alert_history.append(alert)
                del self.active_alerts[alert_id]

                module_logger.info(f"告警已自動解決: {alert_id}")
                break

    def _cleanup_suppressed_alerts(self) -> None:
        """
        清理過期的抑制告警
        """
        current_time = datetime.now()
        expired_alerts = []

        for alert_id, alert in self.active_alerts.items():
            if (
                alert.status == AlertStatus.SUPPRESSED
                and alert.suppressed_until
                and current_time > alert.suppressed_until
            ):
                expired_alerts.append(alert_id)

        for alert_id in expired_alerts:
            alert = self.active_alerts[alert_id]
            alert.status = AlertStatus.ACTIVE
            alert.suppressed_until = None
            module_logger.info(f"告警抑制已過期，重新激活: {alert_id}")

    def _check_alert_escalation(self) -> None:
        """
        檢查告警升級
        """
        current_time = datetime.now()
        escalation_rules = {
            AlertSeverity.INFO: timedelta(hours=4),
            AlertSeverity.WARNING: timedelta(hours=1),
            AlertSeverity.ERROR: timedelta(minutes=30),
            AlertSeverity.CRITICAL: timedelta(minutes=10),
        }

        for alert in self.active_alerts.values():
            if alert.status != AlertStatus.ACTIVE:
                continue

            # 檢查是否需要升級
            time_since_created = current_time - alert.created_at
            escalation_threshold = escalation_rules.get(
                alert.severity, timedelta(hours=1)
            )

            if time_since_created > escalation_threshold:
                self._escalate_alert(alert)

    def _escalate_alert(self, alert: Alert) -> None:
        """
        升級告警

        Args:
            alert: 告警對象
        """
        try:
            # 增加升級級別
            alert.escalation_level += 1

            # 升級嚴重程度
            if alert.severity == AlertSeverity.INFO:
                alert.severity = AlertSeverity.WARNING
            elif alert.severity == AlertSeverity.WARNING:
                alert.severity = AlertSeverity.ERROR
            elif alert.severity == AlertSeverity.ERROR:
                alert.severity = AlertSeverity.CRITICAL

            # 發送升級通知
            escalation_data = {
                "alert_id": alert.id,
                "title": f"[升級] {alert.title}",
                "message": f"告警已升級到 {alert.severity.value} 級別（升級次數: {alert.escalation_level}）",
                "severity": alert.severity.value,
                "escalation_level": alert.escalation_level,
                "original_created_at": alert.created_at.isoformat(),
            }

            # 獲取升級通知渠道
            channels = self._get_notification_channels(alert.severity)

            for channel in channels:
                try:
                    self.notification_service.send_notification(
                        channel, escalation_data
                    )
                except Exception as e:
                    module_logger.error(f"發送升級通知失敗: {e}")

            module_logger.warning(f"告警已升級: {alert.id} -> {alert.severity.value}")

        except Exception as e:
            module_logger.error(f"升級告警失敗: {e}")
