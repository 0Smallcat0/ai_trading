"""
監控系統

此模組提供監控系統的初始化和管理功能。
"""

import argparse
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.core.logger import get_logger
from src.monitoring.alert_manager import AlertSeverity, AlertType, alert_manager

# 導入配置
from src.monitoring.config import (
    ALERT_CHECK_INTERVAL,
    ALERT_LOG_DIR,
    API_ENDPOINTS,
    EMAIL_CONFIG,
    GRAFANA_PORT,
    PROMETHEUS_COLLECTION_INTERVAL,
    PROMETHEUS_PORT,
    SLACK_WEBHOOK_URL,
    SMS_CONFIG,
    THRESHOLDS,
)

# 導入監控組件
from src.monitoring.prometheus_exporter import prometheus_exporter

# 設置日誌
logger = get_logger("monitor_system")


class MonitorSystem:
    """監控系統"""

    def __init__(
        self,
        prometheus_port: int = PROMETHEUS_PORT,
        grafana_port: int = GRAFANA_PORT,
        prometheus_collection_interval: int = PROMETHEUS_COLLECTION_INTERVAL,
        alert_check_interval: int = ALERT_CHECK_INTERVAL,
        email_config: Optional[Dict[str, Any]] = None,
        slack_webhook_url: Optional[str] = None,
        sms_config: Optional[Dict[str, Any]] = None,
        api_endpoints: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        初始化監控系統

        Args:
            prometheus_port: Prometheus 端口
            grafana_port: Grafana 端口
            prometheus_collection_interval: Prometheus 收集間隔（秒）
            alert_check_interval: 警報檢查間隔（秒）
            email_config: 電子郵件配置
            slack_webhook_url: Slack Webhook URL
            sms_config: SMS 配置
            api_endpoints: API 端點列表
        """
        self.prometheus_port = prometheus_port
        self.grafana_port = grafana_port
        self.prometheus_collection_interval = prometheus_collection_interval
        self.alert_check_interval = alert_check_interval
        self.email_config = email_config or EMAIL_CONFIG
        self.slack_webhook_url = slack_webhook_url or SLACK_WEBHOOK_URL
        self.sms_config = sms_config or SMS_CONFIG
        self.api_endpoints = api_endpoints or API_ENDPOINTS

        # 初始化 Prometheus 指標導出器
        self.prometheus_exporter = prometheus_exporter
        self.prometheus_exporter.__init__(
            port=prometheus_port,
            collection_interval=prometheus_collection_interval,
            api_endpoints=api_endpoints,
        )

        # 初始化警報管理器
        self.alert_manager = alert_manager
        self.alert_manager.__init__(
            alert_log_dir=ALERT_LOG_DIR,
            check_interval=alert_check_interval,
            email_config=email_config,
            slack_webhook_url=slack_webhook_url,
            sms_config=sms_config,
        )

        # 監控線程
        self.monitoring_thread = None
        self.running = False

        logger.info("監控系統已初始化")

    def start(self):
        """啟動監控系統"""
        if self.running:
            logger.warning("監控系統已經在運行中")
            return

        # 啟動 Prometheus 指標導出器
        self.prometheus_exporter.start()

        # 啟動警報管理器
        self.alert_manager.start()

        # 啟動監控線程
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

        logger.info("監控系統已啟動")

    def stop(self):
        """停止監控系統"""
        if not self.running:
            logger.warning("監控系統未運行")
            return

        # 停止 Prometheus 指標導出器
        self.prometheus_exporter.stop()

        # 停止警報管理器
        self.alert_manager.stop()

        # 停止監控線程
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)

        logger.info("監控系統已停止")

    def _monitoring_loop(self):
        """監控循環"""
        while self.running:
            try:
                # 檢查閾值
                self._check_thresholds()

                # 等待下一個檢查間隔
                time.sleep(self.alert_check_interval)
            except Exception as e:
                logger.error(f"監控循環發生錯誤: {e}")
                time.sleep(10)  # 發生錯誤時等待較長時間

    def _check_thresholds(self):
        """檢查閾值"""
        try:
            # 獲取指標
            metrics = self.prometheus_exporter.get_metrics()

            # 檢查系統指標
            self._check_system_metrics(metrics)

            # 檢查 API 指標
            self._check_api_metrics(metrics)

            # 檢查模型指標
            self._check_model_metrics(metrics)

            # 檢查交易指標
            self._check_trade_metrics(metrics)
        except Exception as e:
            logger.error(f"檢查閾值時發生錯誤: {e}")

    def _check_system_metrics(self, metrics: Dict[str, Any]):
        """
        檢查系統指標

        Args:
            metrics: 指標數據
        """
        # 檢查 CPU 使用率
        cpu_usage = metrics.get("system", {}).get("cpu_usage")
        if cpu_usage is not None and cpu_usage > THRESHOLDS["system"]["cpu_usage"]:
            self.alert_manager.create_alert(
                alert_type=AlertType.SYSTEM,
                severity=AlertSeverity.WARNING,
                title="高 CPU 使用率",
                description=f"CPU 使用率超過閾值: {cpu_usage:.2f}% > {THRESHOLDS['system']['cpu_usage']}%",
                source="monitor_system",
                details={
                    "cpu_usage": cpu_usage,
                    "threshold": THRESHOLDS["system"]["cpu_usage"],
                },
            )

        # 檢查內存使用率
        memory_usage = metrics.get("system", {}).get("memory_usage")
        if (
            memory_usage is not None
            and memory_usage > THRESHOLDS["system"]["memory_usage"]
        ):
            self.alert_manager.create_alert(
                alert_type=AlertType.SYSTEM,
                severity=AlertSeverity.WARNING,
                title="高內存使用率",
                description=f"內存使用率超過閾值: {memory_usage:.2f}% > {THRESHOLDS['system']['memory_usage']}%",
                source="monitor_system",
                details={
                    "memory_usage": memory_usage,
                    "threshold": THRESHOLDS["system"]["memory_usage"],
                },
            )

        # 檢查磁盤使用率
        disk_usage = metrics.get("system", {}).get("disk_usage")
        if disk_usage is not None and disk_usage > THRESHOLDS["system"]["disk_usage"]:
            self.alert_manager.create_alert(
                alert_type=AlertType.SYSTEM,
                severity=AlertSeverity.WARNING,
                title="高磁盤使用率",
                description=f"磁盤使用率超過閾值: {disk_usage:.2f}% > {THRESHOLDS['system']['disk_usage']}%",
                source="monitor_system",
                details={
                    "disk_usage": disk_usage,
                    "threshold": THRESHOLDS["system"]["disk_usage"],
                },
            )

    def _check_api_metrics(self, metrics: Dict[str, Any]):
        """
        檢查 API 指標

        Args:
            metrics: 指標數據
        """
        # 檢查 API 延遲
        api_latency = metrics.get("api", {}).get("latency", {})
        for endpoint, latency in api_latency.items():
            if latency > THRESHOLDS["api"]["latency"]:
                self.alert_manager.create_alert(
                    alert_type=AlertType.API,
                    severity=AlertSeverity.WARNING,
                    title="高 API 延遲",
                    description=f"API 延遲超過閾值: {endpoint} - {latency:.2f}s > {THRESHOLDS['api']['latency']}s",
                    source="monitor_system",
                    details={
                        "endpoint": endpoint,
                        "latency": latency,
                        "threshold": THRESHOLDS["api"]["latency"],
                    },
                )

        # 檢查 API 錯誤率
        api_requests = metrics.get("api", {}).get("requests_total", {})
        api_errors = metrics.get("api", {}).get("errors_total", {})
        for endpoint in api_requests:
            if endpoint in api_errors and api_requests[endpoint] > 0:
                error_rate = api_errors[endpoint] / api_requests[endpoint]
                if error_rate > THRESHOLDS["api"]["error_rate"]:
                    self.alert_manager.create_alert(
                        alert_type=AlertType.API,
                        severity=AlertSeverity.WARNING,
                        title="高 API 錯誤率",
                        description=f"API 錯誤率超過閾值: {endpoint} - {error_rate:.2%} > {THRESHOLDS['api']['error_rate']:.2%}",
                        source="monitor_system",
                        details={
                            "endpoint": endpoint,
                            "error_rate": error_rate,
                            "threshold": THRESHOLDS["api"]["error_rate"],
                            "requests": api_requests[endpoint],
                            "errors": api_errors[endpoint],
                        },
                    )

    def _check_model_metrics(self, metrics: Dict[str, Any]):
        """
        檢查模型指標

        Args:
            metrics: 指標數據
        """
        # 檢查模型準確率
        model_accuracy = metrics.get("model", {}).get("prediction_accuracy", {})
        for model_name, accuracy in model_accuracy.items():
            if accuracy < THRESHOLDS["model"]["accuracy"]:
                self.alert_manager.create_alert(
                    alert_type=AlertType.MODEL,
                    severity=AlertSeverity.WARNING,
                    title="低模型準確率",
                    description=f"模型準確率低於閾值: {model_name} - {accuracy:.2%} < {THRESHOLDS['model']['accuracy']:.2%}",
                    source="monitor_system",
                    details={
                        "model_name": model_name,
                        "accuracy": accuracy,
                        "threshold": THRESHOLDS["model"]["accuracy"],
                    },
                )

        # 檢查模型延遲
        model_latency = metrics.get("model", {}).get("prediction_latency", {})
        for model_name, latency in model_latency.items():
            if latency > THRESHOLDS["model"]["latency"]:
                self.alert_manager.create_alert(
                    alert_type=AlertType.MODEL,
                    severity=AlertSeverity.WARNING,
                    title="高模型延遲",
                    description=f"模型延遲超過閾值: {model_name} - {latency:.2f}s > {THRESHOLDS['model']['latency']}s",
                    source="monitor_system",
                    details={
                        "model_name": model_name,
                        "latency": latency,
                        "threshold": THRESHOLDS["model"]["latency"],
                    },
                )

        # 檢查模型漂移
        model_drift = metrics.get("model", {}).get("drift", {})
        for model_name, drift in model_drift.items():
            if drift > THRESHOLDS["model"]["drift"]:
                self.alert_manager.create_alert(
                    alert_type=AlertType.MODEL,
                    severity=AlertSeverity.WARNING,
                    title="高模型漂移",
                    description=f"模型漂移超過閾值: {model_name} - {drift:.2f} > {THRESHOLDS['model']['drift']}",
                    source="monitor_system",
                    details={
                        "model_name": model_name,
                        "drift": drift,
                        "threshold": THRESHOLDS["model"]["drift"],
                    },
                )

    def _check_trade_metrics(self, metrics: Dict[str, Any]):
        """
        檢查交易指標

        Args:
            metrics: 指標數據
        """
        # 檢查交易成功率
        trade_success_rate = metrics.get("trade", {}).get("success_rate")
        if (
            trade_success_rate is not None
            and trade_success_rate < THRESHOLDS["trade"]["success_rate"]
        ):
            self.alert_manager.create_alert(
                alert_type=AlertType.TRADE,
                severity=AlertSeverity.WARNING,
                title="低交易成功率",
                description=f"交易成功率低於閾值: {trade_success_rate:.2%} < {THRESHOLDS['trade']['success_rate']:.2%}",
                source="monitor_system",
                details={
                    "success_rate": trade_success_rate,
                    "threshold": THRESHOLDS["trade"]["success_rate"],
                },
            )

        # 檢查資本變化
        capital_change = metrics.get("trade", {}).get("capital_change")
        if (
            capital_change is not None
            and capital_change < THRESHOLDS["trade"]["capital_change"]
        ):
            self.alert_manager.create_alert(
                alert_type=AlertType.TRADE,
                severity=AlertSeverity.CRITICAL,
                title="資本大幅下降",
                description=f"資本下降超過閾值: {capital_change:.2f}% < {THRESHOLDS['trade']['capital_change']}%",
                source="monitor_system",
                details={
                    "capital_change": capital_change,
                    "threshold": THRESHOLDS["trade"]["capital_change"],
                },
            )


def main():
    """主函數"""
    # 解析命令行參數
    parser = argparse.ArgumentParser(description="監控系統")
    parser.add_argument(
        "--prometheus-port", type=int, default=PROMETHEUS_PORT, help="Prometheus 端口"
    )
    parser.add_argument(
        "--grafana-port", type=int, default=GRAFANA_PORT, help="Grafana 端口"
    )
    parser.add_argument(
        "--collection-interval",
        type=int,
        default=PROMETHEUS_COLLECTION_INTERVAL,
        help="收集間隔（秒）",
    )
    parser.add_argument(
        "--alert-interval",
        type=int,
        default=ALERT_CHECK_INTERVAL,
        help="警報檢查間隔（秒）",
    )
    parser.add_argument(
        "--slack-webhook", type=str, default=SLACK_WEBHOOK_URL, help="Slack Webhook URL"
    )
    args = parser.parse_args()

    # 創建監控系統
    monitor_system = MonitorSystem(
        prometheus_port=args.prometheus_port,
        grafana_port=args.grafana_port,
        prometheus_collection_interval=args.collection_interval,
        alert_check_interval=args.alert_interval,
        slack_webhook_url=args.slack_webhook,
    )

    # 啟動監控系統
    monitor_system.start()

    try:
        # 保持腳本運行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        # 停止監控系統
        monitor_system.stop()


if __name__ == "__main__":
    main()
