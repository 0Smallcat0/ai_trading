"""健康檢查服務

此模組實現了系統健康檢查功能，包括：
- 資料庫連接檢查
- API 端點健康檢查
- 外部服務連接檢查
- 系統資源檢查
- 綜合健康評分計算

遵循 Google Style Docstring 標準和 Phase 5.3 開發規範。
"""

import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import yaml
from pathlib import Path

from .health_checker_base import (
    HealthCheckResult,
    HealthStatus,
    create_summary_result,
)
from .system_resource_checker import SystemResourceChecker
from .service_checker import ServiceChecker

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class HealthChecker:
    """健康檢查服務

    提供完整的系統健康檢查功能，包括資料庫、API、外部服務
    和系統資源的健康狀態監控。

    Attributes:
        config: 健康檢查配置
        check_interval: 檢查間隔（秒）
        is_running: 是否正在運行
        last_results: 最近的檢查結果
        health_history: 健康檢查歷史
        system_checker: 系統資源檢查器
    """

    def __init__(self, config_file: str = "config/monitoring.yaml"):
        """初始化健康檢查服務

        Args:
            config_file: 配置檔案路徑

        Raises:
            Exception: 初始化失敗時拋出異常
        """
        try:
            self.config_file = Path(config_file)
            self.config = self._load_config()

            # 檢查配置
            self.check_interval = self.config.get("interval", 60)
            self.timeout = self.config.get("timeout", 30)

            # 運行狀態
            self.is_running = False
            self.check_thread: Optional[threading.Thread] = None
            self._stop_event = threading.Event()

            # 檢查結果
            self.last_results: Dict[str, HealthCheckResult] = {}
            self.health_history: List[Dict[str, HealthCheckResult]] = []
            self.max_history_size = 100

            # 初始化檢查器
            self.system_checker = SystemResourceChecker()
            self.service_checker = ServiceChecker(timeout=self.timeout)

            module_logger.info("健康檢查服務初始化成功")

        except Exception as e:
            module_logger.error("健康檢查服務初始化失敗: %s", e)
            raise

    def _load_config(self) -> Dict[str, Any]:
        """載入配置檔案

        Returns:
            Dict[str, Any]: 健康檢查配置
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                    return config.get("health_check", {})
            else:
                module_logger.warning("配置檔案不存在: %s", self.config_file)
                return {}

        except Exception as e:
            module_logger.error("載入配置檔案失敗: %s", e)
            return {}

    def start(self) -> bool:
        """啟動健康檢查服務

        Returns:
            bool: 啟動成功返回 True，否則返回 False
        """
        try:
            if self.is_running:
                module_logger.warning("健康檢查服務已在運行中")
                return True

            self.is_running = True
            self._stop_event.clear()

            # 啟動檢查線程
            self.check_thread = threading.Thread(
                target=self._check_loop, daemon=True, name="HealthChecker"
            )
            self.check_thread.start()

            module_logger.info("健康檢查服務已啟動")
            return True

        except Exception as e:
            module_logger.error("啟動健康檢查服務失敗: %s", e)
            self.is_running = False
            return False

    def stop(self) -> bool:
        """停止健康檢查服務

        Returns:
            bool: 停止成功返回 True，否則返回 False
        """
        try:
            if not self.is_running:
                module_logger.warning("健康檢查服務未在運行")
                return True

            self.is_running = False
            self._stop_event.set()

            # 等待線程結束
            if self.check_thread and self.check_thread.is_alive():
                self.check_thread.join(timeout=5.0)

            module_logger.info("健康檢查服務已停止")
            return True

        except Exception as e:
            module_logger.error("停止健康檢查服務失敗: %s", e)
            return False

    def _check_loop(self) -> None:
        """健康檢查主循環"""
        module_logger.info("健康檢查循環已啟動")

        while not self._stop_event.is_set():
            try:
                start_time = time.time()

                # 執行所有健康檢查
                results = self.run_all_checks()

                # 更新結果
                self.last_results = results

                # 添加到歷史記錄
                self._add_to_history(results)

                check_time = time.time() - start_time
                module_logger.debug("健康檢查完成，耗時: %.3f秒", check_time)

                # 等待下次檢查
                self._stop_event.wait(self.check_interval)

            except Exception as e:
                module_logger.error("健康檢查過程中發生錯誤: %s", e)
                self._stop_event.wait(min(self.check_interval, 30))

        module_logger.info("健康檢查循環已結束")

    def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """執行所有健康檢查

        Returns:
            Dict[str, HealthCheckResult]: 檢查結果字典
        """
        results = {}
        checks_config = self.config.get("checks", {})

        # 資料庫檢查
        if checks_config.get("database", {}).get("enabled", True):
            results["database"] = self.service_checker.check_database()

        # API 端點檢查
        if checks_config.get("api_endpoints", {}).get("enabled", True):
            endpoints_config = checks_config.get("api_endpoints", {})
            endpoints = endpoints_config.get("endpoints", ["/health"])
            timeout = endpoints_config.get("timeout", 10)
            base_url = "http://localhost:8000"  # 應該從配置讀取

            api_results = self.service_checker.check_api_endpoints(
                endpoints, base_url, timeout
            )
            results.update(api_results)

        # 外部服務檢查
        if checks_config.get("external_services", {}).get("enabled", True):
            services_config = checks_config.get("external_services", {})
            services = services_config.get("services", [])
            timeout = services_config.get("timeout", 15)

            service_results = self.service_checker.check_external_services(
                services, timeout
            )
            results.update(service_results)

        # 系統資源檢查
        if checks_config.get("system_resources", {}).get("enabled", True):
            resource_results = self.system_checker.check_all_resources()
            results.update(resource_results)

        return results

    def get_overall_health(self) -> HealthCheckResult:
        """獲取系統整體健康狀態

        Returns:
            HealthCheckResult: 整體健康檢查結果
        """
        return create_summary_result(self.last_results, "overall")

    def get_health_summary(self) -> Dict[str, Any]:
        """獲取健康狀態摘要

        Returns:
            Dict[str, Any]: 健康狀態摘要
        """
        overall_health = self.get_overall_health()

        summary = {
            "overall": {
                "status": overall_health.status.value,
                "score": overall_health.score,
                "message": overall_health.message,
            },
            "checks": {},
            "timestamp": datetime.now().isoformat(),
            "uptime": self.system_checker.get_system_uptime(),
        }

        # 添加各項檢查結果
        for name, result in self.last_results.items():
            summary["checks"][name] = {
                "status": result.status.value,
                "score": result.score,
                "message": result.message,
                "duration": result.duration,
            }

        return summary

    def _add_to_history(self, results: Dict[str, HealthCheckResult]) -> None:
        """添加檢查結果到歷史記錄

        Args:
            results: 檢查結果
        """
        self.health_history.append(results.copy())

        # 限制歷史記錄大小
        if len(self.health_history) > self.max_history_size:
            self.health_history = self.health_history[-self.max_history_size :]

    def is_healthy(self) -> bool:
        """檢查系統是否健康

        Returns:
            bool: 系統健康返回 True，否則返回 False
        """
        overall_health = self.get_overall_health()
        return overall_health.status in [HealthStatus.HEALTHY, HealthStatus.WARNING]

    def get_critical_issues(self) -> List[HealthCheckResult]:
        """獲取嚴重問題列表

        Returns:
            List[HealthCheckResult]: 嚴重問題列表
        """
        return [
            result
            for result in self.last_results.values()
            if result.status == HealthStatus.CRITICAL
        ]

    def get_warnings(self) -> List[HealthCheckResult]:
        """獲取警告列表

        Returns:
            List[HealthCheckResult]: 警告列表
        """
        return [
            result
            for result in self.last_results.values()
            if result.status == HealthStatus.WARNING
        ]
