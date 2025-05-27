"""警報管理器

此模組提供警報管理功能，用於處理系統警報和通知。
"""

import json
import os
import smtplib
import threading
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Callable, Dict, List, Optional

import requests

# 導入配置
from src.config import CHECK_INTERVAL
from src.core.logger import get_logger

# 設置日誌
logger = get_logger("alert_manager")


# 警報嚴重性
class AlertSeverity:
    """警報嚴重性"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# 警報類型
class AlertType:
    """警報類型"""

    SYSTEM = "system"
    API = "api"
    DATA = "data"
    MODEL = "model"
    TRADE = "trade"
    SECURITY = "security"


class Alert:
    """警報類"""

    def __init__(
        self,
        alert_id: str,
        alert_type: str,
        severity: str,
        title: str,
        description: str,
        source: str,
        timestamp: Optional[datetime] = None,
        details: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ):
        """初始化警報

        Args:
            alert_id: 警報 ID
            alert_type: 警報類型
            severity: 嚴重性
            title: 標題
            description: 描述
            source: 來源
            timestamp: 時間戳
            details: 詳細信息
            tags: 標籤
        """
        self.alert_id = alert_id
        self.alert_type = alert_type
        self.severity = severity
        self.title = title
        self.description = description
        self.source = source
        self.timestamp = timestamp or datetime.now()
        self.details = details or {}
        self.tags = tags or []
        self.acknowledged = False
        self.resolved = False
        self.resolved_time = None
        self.acknowledged_time = None
        self.acknowledged_by = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典

        Returns:
            Dict[str, Any]: 字典
        """
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
            "tags": self.tags,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "resolved_time": (
                self.resolved_time.isoformat() if self.resolved_time else None
            ),
            "acknowledged_time": (
                self.acknowledged_time.isoformat() if self.acknowledged_time else None
            ),
            "acknowledged_by": self.acknowledged_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Alert":
        """從字典創建警報

        Args:
            data: 字典

        Returns:
            Alert: 警報
        """
        alert = cls(
            alert_id=data["alert_id"],
            alert_type=data["alert_type"],
            severity=data["severity"],
            title=data["title"],
            description=data["description"],
            source=data["source"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            details=data.get("details", {}),
            tags=data.get("tags", []),
        )
        alert.acknowledged = data.get("acknowledged", False)
        alert.resolved = data.get("resolved", False)
        if data.get("resolved_time"):
            alert.resolved_time = datetime.fromisoformat(data["resolved_time"])
        if data.get("acknowledged_time"):
            alert.acknowledged_time = datetime.fromisoformat(data["acknowledged_time"])
        alert.acknowledged_by = data.get("acknowledged_by")
        return alert

    def acknowledge(self, user: str) -> None:
        """確認警報

        Args:
            user: 用戶
        """
        self.acknowledged = True
        self.acknowledged_time = datetime.now()
        self.acknowledged_by = user

    def resolve(self) -> None:
        """解決警報"""
        self.resolved = True
        self.resolved_time = datetime.now()


class AlertManager:
    """警報管理器"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """實現單例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AlertManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(
        self,
        alert_log_dir: str = "logs/alerts",
        check_interval: int = CHECK_INTERVAL,
        email_config: Optional[Dict[str, Any]] = None,
        slack_webhook_url: Optional[str] = None,
        sms_config: Optional[Dict[str, Any]] = None,
    ):
        """初始化警報管理器

        Args:
            alert_log_dir: 警報日誌目錄
            check_interval: 檢查間隔（秒）
            email_config: 電子郵件配置
            slack_webhook_url: Slack Webhook URL
            sms_config: SMS 配置
        """
        # 避免重複初始化
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.alert_log_dir = alert_log_dir
        self.check_interval = check_interval
        self.email_config = email_config
        self.slack_webhook_url = slack_webhook_url
        self.sms_config = sms_config

        # 創建警報日誌目錄
        os.makedirs(alert_log_dir, exist_ok=True)

        # 警報列表
        self.alerts: List[Alert] = []

        # 警報回調
        self.alert_callbacks: List[Callable[[Alert], None]] = []

        # 警報處理線程
        self.processing_thread = None
        self.running = False

        # 警報計數
        self.alert_count = 0

        # SLA 配置
        self.sla_config = {
            AlertSeverity.INFO: 24 * 60 * 60,  # 24 小時
            AlertSeverity.WARNING: 4 * 60 * 60,  # 4 小時
            AlertSeverity.ERROR: 60 * 60,  # 1 小時
            AlertSeverity.CRITICAL: 5 * 60,  # 5 分鐘
        }

        # 標記為已初始化
        self._initialized = True
        logger.info("警報管理器已初始化")

    def start(self):
        """啟動警報管理器"""
        if self.running:
            logger.warning("警報管理器已經在運行中")
            return

        # 啟動處理線程
        self.running = True
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()

        logger.info("警報管理器已啟動")

    def stop(self):
        """停止警報管理器"""
        if not self.running:
            logger.warning("警報管理器未運行")
            return

        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=10)

        logger.info("警報管理器已停止")

    def _processing_loop(self):
        """處理循環"""
        while self.running:
            try:
                # 檢查 SLA
                self._check_sla()

                # 等待下一個檢查間隔
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error("警報處理循環發生錯誤: %s", e)
                time.sleep(10)  # 發生錯誤時等待較長時間

    def _check_sla(self):
        """檢查 SLA"""
        now = datetime.now()
        for alert in self.alerts:
            if not alert.resolved and not alert.acknowledged:
                # 計算警報時間
                alert_time = (now - alert.timestamp).total_seconds()
                sla_time = self.sla_config.get(alert.severity, 24 * 60 * 60)

                # 檢查是否超過 SLA
                if alert_time > sla_time:
                    logger.warning(
                        "警報 %s 已超過 SLA: %.2f 秒 > %s 秒",
                        alert.alert_id, alert_time, sla_time
                    )
                    # 升級警報
                    self._escalate_alert(alert)

    def _escalate_alert(self, alert: Alert):
        """升級警報

        Args:
            alert: 警報
        """
        # 根據嚴重性升級
        if alert.severity == AlertSeverity.INFO:
            alert.severity = AlertSeverity.WARNING
        elif alert.severity == AlertSeverity.WARNING:
            alert.severity = AlertSeverity.ERROR
        elif alert.severity == AlertSeverity.ERROR:
            alert.severity = AlertSeverity.CRITICAL

        # 發送升級通知
        self._send_notification(
            alert,
            f"警報已升級: {alert.title}",
            f"警報 {alert.alert_id} 已超過 SLA，已升級為 {alert.severity}",
        )

    def create_alert(
        self,
        alert_type: str,
        severity: str,
        title: str,
        description: str,
        source: str,
        details: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Alert:
        """創建警報

        Args:
            alert_type: 警報類型
            severity: 嚴重性
            title: 標題
            description: 描述
            source: 來源
            details: 詳細信息
            tags: 標籤

        Returns:
            Alert: 警報
        """
        # 生成警報 ID
        self.alert_count += 1
        alert_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{self.alert_count}"

        # 創建警報
        alert = Alert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            source=source,
            details=details,
            tags=tags,
        )

        # 添加到警報列表
        self.alerts.append(alert)

        # 記錄警報
        self._log_alert(alert)

        # 發送通知
        self._send_notification(alert)

        # 調用回調
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error("調用警報回調時發生錯誤: %s", e)

        logger.info("已創建警報: %s - %s", alert_id, title)
        return alert

    def _log_alert(self, alert: Alert):
        """記錄警報

        Args:
            alert: 警報
        """
        # 創建日誌文件名
        log_file = os.path.join(
            self.alert_log_dir, f"alerts_{datetime.now().strftime('%Y%m%d')}.json"
        )

        try:
            # 寫入日誌
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("寫入警報日誌時發生錯誤: %s", e)

    def _send_notification(
        self, alert: Alert, title: Optional[str] = None, message: Optional[str] = None
    ):
        """發送通知

        Args:
            alert: 警報
            title: 標題
            message: 消息
        """
        # 使用提供的標題和消息，或者從警報中獲取
        title = title or alert.title
        message = message or alert.description

        # 根據嚴重性決定通知方式
        if alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
            # 發送電子郵件
            self._send_email(alert, title, message)

            # 發送 Slack 消息
            self._send_slack(alert, title, message)

            # 發送 SMS
            if alert.severity == AlertSeverity.CRITICAL:
                self._send_sms(alert, title, message)
        elif alert.severity == AlertSeverity.WARNING:
            # 發送 Slack 消息
            self._send_slack(alert, title, message)
        else:
            # 只記錄日誌
            logger.info("警報通知: %s - %s", title, message)

    def _send_email(self, alert: Alert, title: str, message: str):
        """發送電子郵件

        Args:
            alert: 警報
            title: 標題
            message: 消息
        """
        if not self.email_config:
            logger.warning("未配置電子郵件，無法發送通知")
            return

        try:
            # 創建郵件
            msg = MIMEMultipart()
            msg["From"] = self.email_config.get("from", "alerts@example.com")
            msg["To"] = self.email_config.get("to", "admin@example.com")
            msg["Subject"] = f"[{alert.severity.upper()}] {title}"

            # 添加正文
            body = f"""
            <html>
            <body>
                <h2>{title}</h2>
                <p><strong>描述:</strong> {message}</p>
                <p><strong>嚴重性:</strong> {alert.severity}</p>
                <p><strong>類型:</strong> {alert.alert_type}</p>
                <p><strong>來源:</strong> {alert.source}</p>
                <p><strong>時間:</strong> {alert.timestamp.isoformat()}</p>
                <p><strong>ID:</strong> {alert.alert_id}</p>
                <h3>詳細信息:</h3>
                <pre>{json.dumps(alert.details, indent=2, ensure_ascii=False)}</pre>
            </body>
            </html>
            """
            msg.attach(MIMEText(body, "html"))

            # 發送郵件
            with smtplib.SMTP(
                self.email_config.get("smtp_server", "localhost"),
                self.email_config.get("smtp_port", 25),
            ) as server:
                if self.email_config.get("use_tls", False):
                    server.starttls()
                if self.email_config.get("username") and self.email_config.get(
                    "password"
                ):
                    server.login(
                        self.email_config["username"], self.email_config["password"]
                    )
                server.send_message(msg)

            logger.info("已發送電子郵件通知: %s", title)
        except Exception as e:
            logger.error("發送電子郵件通知時發生錯誤: %s", e)

    def _send_slack(self, alert: Alert, title: str, message: str):
        """發送 Slack 消息

        Args:
            alert: 警報
            title: 標題
            message: 消息
        """
        if not self.slack_webhook_url:
            logger.warning("未配置 Slack Webhook URL，無法發送通知")
            return

        try:
            # 設置顏色
            color = "#36a64f"  # 綠色
            if alert.severity == AlertSeverity.WARNING:
                color = "#ffcc00"  # 黃色
            elif alert.severity == AlertSeverity.ERROR:
                color = "#ff9900"  # 橙色
            elif alert.severity == AlertSeverity.CRITICAL:
                color = "#ff0000"  # 紅色

            # 創建 Slack 消息
            payload = {
                "attachments": [
                    {
                        "fallback": f"{title}: {message}",
                        "color": color,
                        "title": title,
                        "text": message,
                        "fields": [
                            {"title": "嚴重性", "value": alert.severity, "short": True},
                            {"title": "類型", "value": alert.alert_type, "short": True},
                            {"title": "來源", "value": alert.source, "short": True},
                            {"title": "ID", "value": alert.alert_id, "short": True},
                        ],
                        "footer": f"警報時間: {alert.timestamp.isoformat()}",
                    }
                ]
            }

            # 發送 Slack 消息
            response = requests.post(
                self.slack_webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()

            logger.info("已發送 Slack 通知: %s", title)
        except Exception as e:
            logger.error("發送 Slack 通知時發生錯誤: %s", e)

    def _send_sms(self, alert: Alert, title: str, message: str):
        """發送 SMS 消息

        Args:
            alert: 警報
            title: 標題
            message: 消息
        """
        if not self.sms_config:
            logger.warning("未配置 SMS，無法發送通知")
            return

        try:
            # 這裡應該實現 SMS 發送邏輯
            # 由於 SMS 服務提供商不同，這裡只是一個示例
            logger.info("已發送 SMS 通知: %s", title)
        except Exception as e:
            logger.error("發送 SMS 通知時發生錯誤: %s", e)

    def get_alerts(
        self,
        alert_type: Optional[str] = None,
        severity: Optional[str] = None,
        resolved: Optional[bool] = None,
        acknowledged: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Alert]:
        """獲取警報列表

        Args:
            alert_type: 警報類型
            severity: 嚴重性
            resolved: 是否已解決
            acknowledged: 是否已確認
            start_time: 開始時間
            end_time: 結束時間
            limit: 限制數量

        Returns:
            List[Alert]: 警報列表
        """
        # 過濾警報
        filtered_alerts = self.alerts

        if alert_type:
            filtered_alerts = [a for a in filtered_alerts if a.alert_type == alert_type]

        if severity:
            filtered_alerts = [a for a in filtered_alerts if a.severity == severity]

        if resolved is not None:
            filtered_alerts = [a for a in filtered_alerts if a.resolved == resolved]

        if acknowledged is not None:
            filtered_alerts = [
                a for a in filtered_alerts if a.acknowledged == acknowledged
            ]

        if start_time:
            filtered_alerts = [a for a in filtered_alerts if a.timestamp >= start_time]

        if end_time:
            filtered_alerts = [a for a in filtered_alerts if a.timestamp <= end_time]

        # 按時間排序
        filtered_alerts.sort(key=lambda a: a.timestamp, reverse=True)

        # 限制數量
        return filtered_alerts[:limit]

    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """
        確認警報

        Args:
            alert_id: 警報 ID
            user: 用戶

        Returns:
            bool: 是否成功
        """
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledge(user)
                self._log_alert(alert)
                logger.info("警報 %s 已被 %s 確認", alert_id, user)
                return True

        logger.warning("找不到警報 %s", alert_id)
        return False

    def resolve_alert(self, alert_id: str) -> bool:
        """解決警報

        Args:
            alert_id: 警報 ID

        Returns:
            bool: 是否成功
        """
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.resolve()
                self._log_alert(alert)
                logger.info("警報 %s 已解決", alert_id)
                return True

        logger.warning("找不到警報 %s", alert_id)
        return False

    def add_callback(self, callback: Callable[[Alert], None]):
        """添加警報回調

        Args:
            callback: 回調函數
        """
        self.alert_callbacks.append(callback)

    def remove_callback(self, callback: Callable[[Alert], None]):
        """移除警報回調

        Args:
            callback: 回調函數
        """
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)


# 創建全局警報管理器實例
alert_manager = AlertManager()
