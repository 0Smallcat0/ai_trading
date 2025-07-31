"""系統資源檢查器

此模組實現系統資源監控功能，包括：
- CPU 使用率檢查
- 記憶體使用率檢查
- 磁碟使用率檢查
- 網路連接檢查

遵循 Google Style Docstring 標準和 Phase 5.3 開發規範。
"""

import logging
import time
from typing import Dict
import psutil

from .health_checker_base import HealthCheckResult, HealthStatus

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class SystemResourceChecker:
    """系統資源檢查器

    提供系統資源監控功能，包括 CPU、記憶體、磁碟等資源的健康狀態檢查。

    Attributes:
        cpu_warning_threshold: CPU 使用率警告閾值
        cpu_critical_threshold: CPU 使用率嚴重閾值
        memory_warning_threshold: 記憶體使用率警告閾值
        memory_critical_threshold: 記憶體使用率嚴重閾值
    """

    def __init__(
        self,
        cpu_warning_threshold: float = 70.0,
        cpu_critical_threshold: float = 90.0,
        memory_warning_threshold: float = 80.0,
        memory_critical_threshold: float = 95.0,
    ):
        """初始化系統資源檢查器

        Args:
            cpu_warning_threshold: CPU 使用率警告閾值
            cpu_critical_threshold: CPU 使用率嚴重閾值
            memory_warning_threshold: 記憶體使用率警告閾值
            memory_critical_threshold: 記憶體使用率嚴重閾值
        """
        self.cpu_warning_threshold = cpu_warning_threshold
        self.cpu_critical_threshold = cpu_critical_threshold
        self.memory_warning_threshold = memory_warning_threshold
        self.memory_critical_threshold = memory_critical_threshold

    def check_cpu_usage(self) -> HealthCheckResult:
        """檢查 CPU 使用率

        Returns:
            HealthCheckResult: CPU 使用率檢查結果
        """
        start_time = time.time()

        try:
            cpu_usage = psutil.cpu_percent(interval=1)
            duration = time.time() - start_time

            if cpu_usage < self.cpu_warning_threshold:
                status = HealthStatus.HEALTHY
                score = 100.0
                message = "CPU 使用率正常"
            elif cpu_usage < self.cpu_critical_threshold:
                status = HealthStatus.WARNING
                score = 70.0
                message = "CPU 使用率偏高"
            else:
                status = HealthStatus.CRITICAL
                score = 30.0
                message = "CPU 使用率過高"

            return HealthCheckResult(
                name="cpu",
                status=status,
                score=score,
                message=message,
                details={
                    "usage_percent": cpu_usage,
                    "warning_threshold": self.cpu_warning_threshold,
                    "critical_threshold": self.cpu_critical_threshold,
                },
                duration=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            module_logger.error("CPU 使用率檢查失敗: %s", e)

            return HealthCheckResult(
                name="cpu",
                status=HealthStatus.CRITICAL,
                score=0.0,
                message=f"CPU 使用率檢查失敗: {str(e)}",
                details={"error": str(e)},
                duration=duration,
            )

    def check_memory_usage(self) -> HealthCheckResult:
        """檢查記憶體使用率

        Returns:
            HealthCheckResult: 記憶體使用率檢查結果
        """
        start_time = time.time()

        try:
            memory = psutil.virtual_memory()
            duration = time.time() - start_time

            if memory.percent < self.memory_warning_threshold:
                status = HealthStatus.HEALTHY
                score = 100.0
                message = "記憶體使用率正常"
            elif memory.percent < self.memory_critical_threshold:
                status = HealthStatus.WARNING
                score = 70.0
                message = "記憶體使用率偏高"
            else:
                status = HealthStatus.CRITICAL
                score = 30.0
                message = "記憶體使用率過高"

            return HealthCheckResult(
                name="memory",
                status=status,
                score=score,
                message=message,
                details={
                    "usage_percent": memory.percent,
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "warning_threshold": self.memory_warning_threshold,
                    "critical_threshold": self.memory_critical_threshold,
                },
                duration=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            module_logger.error("記憶體使用率檢查失敗: %s", e)

            return HealthCheckResult(
                name="memory",
                status=HealthStatus.CRITICAL,
                score=0.0,
                message=f"記憶體使用率檢查失敗: {str(e)}",
                details={"error": str(e)},
                duration=duration,
            )

    def check_disk_usage(self) -> HealthCheckResult:
        """檢查磁碟使用率

        Returns:
            HealthCheckResult: 磁碟使用率檢查結果
        """
        start_time = time.time()

        try:
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100
            duration = time.time() - start_time

            if disk_percent < 85.0:
                status = HealthStatus.HEALTHY
                score = 100.0
                message = "磁碟使用率正常"
            elif disk_percent < 95.0:
                status = HealthStatus.WARNING
                score = 70.0
                message = "磁碟使用率偏高"
            else:
                status = HealthStatus.CRITICAL
                score = 30.0
                message = "磁碟使用率過高"

            return HealthCheckResult(
                name="disk",
                status=status,
                score=score,
                message=message,
                details={
                    "usage_percent": round(disk_percent, 2),
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                },
                duration=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            module_logger.error("磁碟使用率檢查失敗: %s", e)

            return HealthCheckResult(
                name="disk",
                status=HealthStatus.CRITICAL,
                score=0.0,
                message=f"磁碟使用率檢查失敗: {str(e)}",
                details={"error": str(e)},
                duration=duration,
            )

    def check_all_resources(self) -> Dict[str, HealthCheckResult]:
        """檢查所有系統資源

        Returns:
            Dict[str, HealthCheckResult]: 所有系統資源檢查結果
        """
        results = {}

        # CPU 檢查
        results["cpu"] = self.check_cpu_usage()

        # 記憶體檢查
        results["memory"] = self.check_memory_usage()

        # 磁碟檢查
        results["disk"] = self.check_disk_usage()

        return results

    def get_system_uptime(self) -> str:
        """獲取系統運行時間

        Returns:
            str: 系統運行時間字串
        """
        try:
            from datetime import datetime  # pylint: disable=import-outside-toplevel

            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time

            days = uptime.days
            hours, remainder = divmod(uptime.seconds, 3600)
            minutes, _ = divmod(remainder, 60)

            return f"{days}天 {hours}小時 {minutes}分鐘"

        except Exception as e:
            module_logger.error("獲取系統運行時間失敗: %s", e)
            return "未知"
