"""監控系統

此模組提供監控系統的初始化和管理功能，整合各個子模組：
- 系統資源監控（CPU、記憶體、磁碟使用率）
- API 效能監控（延遲、錯誤率、QPS）
- 模型效能監控（準確率、延遲、漂移檢測）
- 交易監控（成功率、資本變化、風險指標）

遵循 Google Style Docstring 標準和 Phase 5.3 開發規範。
"""

import argparse
import logging
import os
import sys
import time
from typing import Any, Dict, Optional

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

try:
    from src.core.logger import get_logger
except ImportError:
    def get_logger(name: str) -> logging.Logger:
        """Fallback logger function"""
        return logging.getLogger(name)

try:
    from .monitor_modules import (
        AlertHandler,
        SystemMonitor,
        ThresholdChecker,
    )
except ImportError:
    # 提供 fallback
    AlertHandler = None
    SystemMonitor = None
    ThresholdChecker = None

# 導入配置
try:
    from .config import (
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
except ImportError:
    # 提供預設值
    ALERT_CHECK_INTERVAL = 60
    ALERT_LOG_DIR = "logs/alerts"
    API_ENDPOINTS = []
    EMAIL_CONFIG = {}
    GRAFANA_PORT = 3000
    PROMETHEUS_COLLECTION_INTERVAL = 15
    PROMETHEUS_PORT = 9090
    SLACK_WEBHOOK_URL = ""
    SMS_CONFIG = {}
    THRESHOLDS = {
        "system": {"cpu_usage": 80, "memory_usage": 80, "disk_usage": 85},
        "api": {"latency": 1.0, "error_rate": 0.05},
        "model": {"accuracy": 0.8, "latency": 1.0, "drift": 0.1},
        "trade": {"success_rate": 0.7, "capital_change": -10.0}
    }

# 導入監控組件
try:
    from .prometheus_exporter import prometheus_exporter
except ImportError:
    prometheus_exporter = None

try:
    from .alert_manager import alert_manager
except ImportError:
    alert_manager = None

# 設置日誌
logger = get_logger("monitor_system")


class MonitorSystem:
    """監控系統

    整合各個子模組的監控系統，提供統一的監控管理介面。

    Attributes:
        prometheus_exporter: Prometheus 指標導出器
        alert_handler: 警報處理器
        threshold_checker: 閾值檢查器
        system_monitor: 系統監控器
        config: 系統配置
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化監控系統

        Args:
            config: 監控系統配置字典

        Raises:
            ImportError: 當必要模組未安裝時
        """
        self.config = config or self._get_default_config()

        # 檢查必要組件
        if not all([AlertHandler, SystemMonitor, ThresholdChecker]):
            raise ImportError("監控模組未正確安裝")

        # 初始化組件
        self._init_components()

        logger.info("監控系統初始化成功")

    def _get_default_config(self) -> Dict[str, Any]:
        """獲取預設配置

        Returns:
            Dict[str, Any]: 預設配置字典
        """
        return {
            "prometheus_port": PROMETHEUS_PORT,
            "grafana_port": GRAFANA_PORT,
            "prometheus_collection_interval": PROMETHEUS_COLLECTION_INTERVAL,
            "alert_check_interval": ALERT_CHECK_INTERVAL,
            "email_config": EMAIL_CONFIG,
            "slack_webhook_url": SLACK_WEBHOOK_URL,
            "sms_config": SMS_CONFIG,
            "api_endpoints": API_ENDPOINTS,
            "thresholds": THRESHOLDS,
            "alert_log_dir": ALERT_LOG_DIR,
        }

    def _init_components(self) -> None:
        """初始化各個組件"""
        try:
            # 初始化 Prometheus 指標導出器
            self.prometheus_exporter = prometheus_exporter
            if (self.prometheus_exporter and
                    hasattr(self.prometheus_exporter, 'configure')):
                self.prometheus_exporter.configure(
                    port=self.config["prometheus_port"],
                    collection_interval=self.config["prometheus_collection_interval"],
                    api_endpoints=self.config["api_endpoints"],
                )

            # 初始化警報處理器
            self.alert_handler = None
            if alert_manager and AlertHandler:
                # 配置警報管理器
                if hasattr(alert_manager, 'configure'):
                    alert_manager.configure(
                        alert_log_dir=self.config["alert_log_dir"],
                        check_interval=self.config["alert_check_interval"],
                        email_config=self.config["email_config"],
                        slack_webhook_url=self.config["slack_webhook_url"],
                        sms_config=self.config["sms_config"],
                    )

                self.alert_handler = AlertHandler(alert_manager)

            # 初始化閾值檢查器
            self.threshold_checker = None
            if self.alert_handler and ThresholdChecker:
                self.threshold_checker = ThresholdChecker(
                    self.config["thresholds"],
                    self.alert_handler
                )

            # 初始化系統監控器
            self.system_monitor = None
            if self.prometheus_exporter and self.threshold_checker and SystemMonitor:
                self.system_monitor = SystemMonitor(
                    self.prometheus_exporter,
                    self.threshold_checker,
                    self.config["alert_check_interval"]
                )

            logger.info("監控系統組件初始化完成")

        except Exception as e:
            logger.error("初始化監控系統組件失敗: %s", e)
            raise

    def start(self) -> bool:
        """啟動監控系統

        Returns:
            bool: 啟動成功返回 True，否則返回 False
        """
        try:
            if not self.system_monitor:
                logger.error("系統監控器未初始化")
                return False

            # 啟動警報管理器
            if alert_manager and hasattr(alert_manager, 'start'):
                alert_manager.start()

            # 啟動系統監控器
            success = self.system_monitor.start()

            if success:
                logger.info("監控系統已啟動")
            else:
                logger.error("監控系統啟動失敗")

            return success

        except Exception as e:
            logger.error("啟動監控系統失敗: %s", e)
            return False

    def stop(self) -> bool:
        """停止監控系統

        Returns:
            bool: 停止成功返回 True，否則返回 False
        """
        try:
            success = True

            # 停止系統監控器
            if self.system_monitor:
                if not self.system_monitor.stop():
                    success = False

            # 停止警報管理器
            if alert_manager and hasattr(alert_manager, 'stop'):
                alert_manager.stop()

            if success:
                logger.info("監控系統已停止")
            else:
                logger.warning("監控系統停止時發生部分錯誤")

            return success

        except Exception as e:
            logger.error("停止監控系統失敗: %s", e)
            return False

    def get_status(self) -> Dict[str, Any]:
        """獲取監控系統狀態

        Returns:
            Dict[str, Any]: 系統狀態字典
        """
        status = {
            "components": {
                "prometheus_exporter": self.prometheus_exporter is not None,
                "alert_handler": self.alert_handler is not None,
                "threshold_checker": self.threshold_checker is not None,
                "system_monitor": self.system_monitor is not None,
            },
            "health": {
                "overall": False,
                "details": {}
            }
        }

        try:
            # 獲取系統監控器狀態
            if self.system_monitor:
                monitor_status = self.system_monitor.get_status()
                status["system_monitor"] = monitor_status
                status["health"]["details"]["system_monitor"] = (
                    self.system_monitor.is_healthy()
                )

            # 獲取警報處理器狀態
            if self.alert_handler:
                alert_stats = self.alert_handler.get_alert_stats()
                status["alert_handler"] = alert_stats
                status["health"]["details"]["alert_handler"] = (
                    self.alert_handler.is_healthy()
                )

            # 計算整體健康狀態
            health_checks = list(status["health"]["details"].values())
            status["health"]["overall"] = all(health_checks) if health_checks else False

        except Exception as e:
            logger.error("獲取系統狀態失敗: %s", e)
            status["error"] = str(e)

        return status

    def force_check(self) -> bool:
        """強制執行一次監控檢查

        Returns:
            bool: 檢查成功返回 True，否則返回 False
        """
        try:
            if not self.system_monitor:
                logger.error("系統監控器未初始化")
                return False

            return self.system_monitor.force_check()

        except Exception as e:
            logger.error("強制檢查失敗: %s", e)
            return False

    def is_healthy(self) -> bool:
        """檢查監控系統整體健康狀態

        Returns:
            bool: 健康返回 True，否則返回 False
        """
        try:
            # 檢查核心組件
            if not self.system_monitor:
                return False

            # 檢查系統監控器健康狀態
            return self.system_monitor.is_healthy()

        except Exception as e:
            logger.error("健康檢查失敗: %s", e)
            return False


def main() -> None:
    """主函數"""
    # 解析命令行參數
    parser = argparse.ArgumentParser(description="AI 交易系統監控")
    parser.add_argument(
        "--prometheus-port",
        type=int,
        default=PROMETHEUS_PORT,
        help="Prometheus 端口"
    )
    parser.add_argument(
        "--grafana-port",
        type=int,
        default=GRAFANA_PORT,
        help="Grafana 端口"
    )
    parser.add_argument(
        "--check-interval",
        type=int,
        default=ALERT_CHECK_INTERVAL,
        help="監控檢查間隔（秒）",
    )
    args = parser.parse_args()

    # 創建配置
    config = {
        "prometheus_port": args.prometheus_port,
        "grafana_port": args.grafana_port,
        "alert_check_interval": args.check_interval,
    }

    # 創建並啟動監控系統
    try:
        monitor_system = MonitorSystem(config)

        if monitor_system.start():
            logger.info("監控系統啟動成功")

            # 保持腳本運行
            while True:
                time.sleep(1)
        else:
            logger.error("監控系統啟動失敗")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("收到中斷信號，正在停止監控系統...")
        if 'monitor_system' in locals():
            monitor_system.stop()
    except Exception as e:
        logger.error("監控系統運行失敗: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
