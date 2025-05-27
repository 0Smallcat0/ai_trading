"""系統監控器

此模組實現系統監控的核心功能。
"""

import logging
import threading
import time
from typing import Any, Dict, Optional

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class SystemMonitor:
    """系統監控器

    負責監控系統運行狀態和指標收集。

    Attributes:
        prometheus_exporter: Prometheus 指標導出器
        threshold_checker: 閾值檢查器
        check_interval: 檢查間隔（秒）
        monitoring_thread: 監控線程
        running: 運行狀態標誌
    """

    def __init__(
        self,
        prometheus_exporter: Any,
        threshold_checker: Any,
        check_interval: int = 60
    ):
        """初始化系統監控器

        Args:
            prometheus_exporter: Prometheus 指標導出器
            threshold_checker: 閾值檢查器
            check_interval: 檢查間隔（秒）

        Raises:
            ValueError: 當必要參數為空時
        """
        if not prometheus_exporter:
            raise ValueError("Prometheus 指標導出器不能為空")
        if not threshold_checker:
            raise ValueError("閾值檢查器不能為空")
        if check_interval <= 0:
            raise ValueError("檢查間隔必須大於 0")

        self.prometheus_exporter = prometheus_exporter
        self.threshold_checker = threshold_checker
        self.check_interval = check_interval
        self.monitoring_thread: Optional[threading.Thread] = None
        self.running = False

        module_logger.info("系統監控器初始化成功")

    def start(self) -> bool:
        """啟動系統監控

        Returns:
            bool: 啟動成功返回 True，否則返回 False
        """
        try:
            if self.running:
                module_logger.warning("系統監控已在運行中")
                return True

            # 啟動 Prometheus 指標導出器
            if hasattr(self.prometheus_exporter, 'start'):
                self.prometheus_exporter.start()

            # 啟動監控線程
            self.running = True
            self.monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self.monitoring_thread.start()

            module_logger.info("系統監控已啟動")
            return True

        except Exception as e:
            module_logger.error("啟動系統監控失敗: %s", e)
            self.running = False
            return False

    def stop(self) -> bool:
        """停止系統監控

        Returns:
            bool: 停止成功返回 True，否則返回 False
        """
        try:
            if not self.running:
                module_logger.warning("系統監控未運行")
                return True

            # 停止監控線程
            self.running = False
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=10)

            # 停止 Prometheus 指標導出器
            if hasattr(self.prometheus_exporter, 'stop'):
                self.prometheus_exporter.stop()

            module_logger.info("系統監控已停止")
            return True

        except Exception as e:
            module_logger.error("停止系統監控失敗: %s", e)
            return False

    def _monitoring_loop(self) -> None:
        """監控循環"""
        module_logger.info("監控循環已啟動")

        while self.running:
            try:
                # 收集指標
                metrics = self._collect_metrics()

                # 檢查閾值
                if metrics:
                    self.threshold_checker.check_all_metrics(metrics)

                # 等待下一個檢查間隔
                time.sleep(self.check_interval)

            except Exception as e:
                module_logger.error("監控循環發生錯誤: %s", e)
                # 發生錯誤時等待較短時間後重試
                time.sleep(min(10, self.check_interval))

        module_logger.info("監控循環已結束")

    def _collect_metrics(self) -> Optional[Dict[str, Any]]:
        """收集指標數據

        Returns:
            Optional[Dict[str, Any]]: 指標數據，失敗返回 None
        """
        try:
            if hasattr(self.prometheus_exporter, 'get_metrics'):
                metrics = self.prometheus_exporter.get_metrics()
                if metrics:
                    module_logger.debug("指標收集成功")
                    return metrics
                else:
                    module_logger.warning("指標收集返回空數據")
                    return None
            else:
                module_logger.error("Prometheus 導出器不支援 get_metrics 方法")
                return None

        except Exception as e:
            module_logger.error("收集指標失敗: %s", e)
            return None

    def get_status(self) -> Dict[str, Any]:
        """獲取監控器狀態

        Returns:
            Dict[str, Any]: 監控器狀態資訊
        """
        return {
            "running": self.running,
            "check_interval": self.check_interval,
            "thread_alive": (
                self.monitoring_thread.is_alive()
                if self.monitoring_thread
                else False
            ),
            "prometheus_exporter_available": self.prometheus_exporter is not None,
            "threshold_checker_available": self.threshold_checker is not None,
        }

    def update_check_interval(self, new_interval: int) -> bool:
        """更新檢查間隔

        Args:
            new_interval: 新的檢查間隔（秒）

        Returns:
            bool: 更新成功返回 True，否則返回 False
        """
        try:
            if new_interval <= 0:
                module_logger.error("檢查間隔必須大於 0")
                return False

            old_interval = self.check_interval
            self.check_interval = new_interval

            module_logger.info(
                "檢查間隔已更新: %d -> %d 秒",
                old_interval,
                new_interval
            )
            return True

        except Exception as e:
            module_logger.error("更新檢查間隔失敗: %s", e)
            return False

    def force_check(self) -> bool:
        """強制執行一次檢查

        Returns:
            bool: 檢查成功返回 True，否則返回 False
        """
        try:
            module_logger.info("執行強制檢查")

            # 收集指標
            metrics = self._collect_metrics()

            # 檢查閾值
            if metrics:
                self.threshold_checker.check_all_metrics(metrics)
                module_logger.info("強制檢查完成")
                return True
            else:
                module_logger.warning("強制檢查失敗：無法收集指標")
                return False

        except Exception as e:
            module_logger.error("強制檢查失敗: %s", e)
            return False

    def is_healthy(self) -> bool:
        """檢查監控器健康狀態

        Returns:
            bool: 健康返回 True，否則返回 False
        """
        try:
            # 檢查基本組件
            if not self.prometheus_exporter or not self.threshold_checker:
                return False

            # 檢查運行狀態
            if self.running:
                # 檢查監控線程是否活躍
                if not self.monitoring_thread or not self.monitoring_thread.is_alive():
                    return False

            # 檢查閾值檢查器健康狀態
            if hasattr(self.threshold_checker, 'is_healthy'):
                if not self.threshold_checker.is_healthy():
                    return False

            return True

        except Exception as e:
            module_logger.error("健康檢查失敗: %s", e)
            return False
