"""Email 通知服務

此模組實現了 Email 通知功能，支援 HTML 模板、批次發送、發送狀態追蹤。

遵循 Google Style Docstring 標準和 Phase 5.3 開發規範。
"""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any

from .notification_base import NotificationChannel

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class EmailChannel(NotificationChannel):
    """Email 通知渠道

    支援 HTML 模板、批次發送、發送狀態追蹤等功能。
    """

    def __init__(self, config: Dict[str, Any]):
        """初始化 Email 渠道

        Args:
            config: Email 配置
        """
        super().__init__("email", config)

        self.smtp_server = config.get("smtp_server", "localhost")
        self.smtp_port = config.get("smtp_port", 587)
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.from_address = config.get("from_address", "alerts@trading-system.com")
        self.to_addresses = config.get("to_addresses", [])
        self.use_tls = config.get("use_tls", True)

    def send(self, data: Dict[str, Any]) -> bool:
        """發送 Email 通知

        Args:
            data: 通知數據

        Returns:
            bool: 發送成功返回 True，否則返回 False
        """
        if not self.enabled or not self.to_addresses:
            return False

        try:
            # 創建郵件
            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_address
            msg["To"] = ", ".join(self.to_addresses)
            msg["Subject"] = (
                f"[{data.get('severity', 'INFO')}] {data.get('title', 'Alert')}"
            )

            # 創建 HTML 內容
            html_content = self._create_html_content(data)
            html_part = MIMEText(html_content, "html", "utf-8")
            msg.attach(html_part)

            # 發送郵件
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()

                if self.username and self.password:
                    server.login(self.username, self.password)

                server.send_message(msg)

            module_logger.info("Email 通知發送成功: %s", data.get("alert_id"))
            return True

        except Exception as e:
            module_logger.error("Email 通知發送失敗: %s", e)
            return False

    def _create_html_content(self, data: Dict[str, Any]) -> str:
        """創建 HTML 郵件內容

        Args:
            data: 通知數據

        Returns:
            str: HTML 內容
        """
        severity = data.get("severity", "INFO")
        severity_color = {
            "INFO": "#17a2b8",
            "WARNING": "#ffc107",
            "ERROR": "#fd7e14",
            "CRITICAL": "#dc3545",
        }.get(severity, "#6c757d")

        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>系統告警通知</title>
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background-color: #f8f9fa; 
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 0 auto; 
                    background-color: white; 
                    border-radius: 8px; 
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
                }}
                .header {{ 
                    background-color: {severity_color}; 
                    color: white; 
                    padding: 20px; 
                    border-radius: 8px 8px 0 0; 
                }}
                .content {{ padding: 20px; }}
                .severity {{ 
                    display: inline-block; 
                    padding: 4px 12px; 
                    border-radius: 4px; 
                    color: white; 
                    background-color: {severity_color}; 
                    font-weight: bold; 
                }}
                .details {{ 
                    background-color: #f8f9fa; 
                    padding: 15px; 
                    border-radius: 4px; 
                    margin: 15px 0; 
                }}
                .footer {{ 
                    padding: 20px; 
                    text-align: center; 
                    color: #6c757d; 
                    border-top: 1px solid #dee2e6; 
                }}
                table {{ width: 100%; border-collapse: collapse; }}
                td {{ padding: 8px; border-bottom: 1px solid #dee2e6; }}
                .label {{ font-weight: bold; width: 30%; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 系統告警通知</h1>
                    <p>{data.get('title', 'Alert')}</p>
                </div>
                <div class="content">
                    <p><span class="severity">{severity}</span></p>
                    <p>{data.get('message', '')}</p>

                    <div class="details">
                        <h3>告警詳情</h3>
                        <table>
                            <tr>
                                <td class="label">告警 ID:</td>
                                <td>{data.get('alert_id', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td class="label">觸發時間:</td>
                                <td>{data.get('created_at', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td class="label">當前值:</td>
                                <td>{data.get('metric_value', 'N/A')}</td>
                            </tr>
                            <tr>
                                <td class="label">閾值:</td>
                                <td>{data.get('threshold_value', 'N/A')}</td>
                            </tr>
                        </table>
                    </div>
                </div>
                <div class="footer">
                    <p>此郵件由 AI 交易系統自動發送</p>
                    <p>發送時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
            </div>
        </body>
        </html>
        """

        return html_template

    def test_connection(self) -> bool:
        """測試 SMTP 連接

        Returns:
            bool: 連接成功返回 True，否則返回 False
        """
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()

                if self.username and self.password:
                    server.login(self.username, self.password)

            return True

        except Exception as e:
            module_logger.error("Email 連接測試失敗: %s", e)
            return False
