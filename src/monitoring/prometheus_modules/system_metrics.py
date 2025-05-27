"""系統資源指標收集器

此模組實現系統資源指標的收集，包括 CPU、記憶體、磁碟、網路等。
"""

import logging
import os
from typing import Dict, Any

try:
    import psutil
except ImportError:
    psutil = None

try:
    from prometheus_client import Gauge, Counter
except ImportError:
    Gauge = None
    Counter = None

from .base import PrometheusCollectorBase

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class SystemMetricsCollector(PrometheusCollectorBase):
    """系統資源指標收集器

    收集系統 CPU、記憶體、磁碟、網路等資源使用情況。

    Attributes:
        cpu_usage: CPU 使用率指標
        memory_usage: 記憶體使用率指標
        disk_usage: 磁碟使用率指標
        network_bytes: 網路流量指標
    """

    def __init__(self, collection_interval: int = 15):
        """初始化系統資源指標收集器

        Args:
            collection_interval: 指標收集間隔，預設 15 秒

        Raises:
            ImportError: 當必要套件未安裝時
        """
        if psutil is None:
            raise ImportError("psutil 套件未安裝")
        if Gauge is None or Counter is None:
            raise ImportError("prometheus_client 套件未安裝")

        super().__init__(collection_interval)
        self._init_metrics()

    def _init_metrics(self) -> None:
        """初始化系統資源指標"""
        try:
            # CPU 使用率
            self.metrics["cpu_usage"] = Gauge(
                "system_cpu_usage_percent",
                "系統 CPU 使用率百分比",
                registry=self.registry
            )

            # 記憶體使用率
            self.metrics["memory_usage"] = Gauge(
                "system_memory_usage_percent",
                "系統記憶體使用率百分比",
                registry=self.registry
            )

            # 記憶體使用量（位元組）
            self.metrics["memory_used_bytes"] = Gauge(
                "system_memory_used_bytes",
                "系統記憶體使用量（位元組）",
                registry=self.registry
            )

            # 記憶體總量（位元組）
            self.metrics["memory_total_bytes"] = Gauge(
                "system_memory_total_bytes",
                "系統記憶體總量（位元組）",
                registry=self.registry
            )

            # 磁碟使用率
            self.metrics["disk_usage"] = Gauge(
                "system_disk_usage_percent",
                "系統磁碟使用率百分比",
                ["device"],
                registry=self.registry
            )

            # 磁碟讀取位元組數
            self.metrics["disk_read_bytes"] = Counter(
                "system_disk_read_bytes_total",
                "系統磁碟讀取位元組總數",
                ["device"],
                registry=self.registry
            )

            # 磁碟寫入位元組數
            self.metrics["disk_write_bytes"] = Counter(
                "system_disk_write_bytes_total",
                "系統磁碟寫入位元組總數",
                ["device"],
                registry=self.registry
            )

            # 網路接收位元組數
            self.metrics["network_recv_bytes"] = Counter(
                "system_network_recv_bytes_total",
                "系統網路接收位元組總數",
                ["interface"],
                registry=self.registry
            )

            # 網路發送位元組數
            self.metrics["network_sent_bytes"] = Counter(
                "system_network_sent_bytes_total",
                "系統網路發送位元組總數",
                ["interface"],
                registry=self.registry
            )

            # 進程數量
            self.metrics["process_count"] = Gauge(
                "system_process_count",
                "系統進程數量",
                registry=self.registry
            )

            # 系統負載
            if hasattr(os, "getloadavg"):
                self.metrics["load_average"] = Gauge(
                    "system_load_average",
                    "系統負載平均值",
                    ["period"],
                    registry=self.registry
                )

            module_logger.info("系統資源指標初始化完成")

        except Exception as e:
            module_logger.error("系統資源指標初始化失敗: %s", e)
            raise

    def _collect_metrics(self) -> None:
        """收集系統資源指標"""
        try:
            # 收集 CPU 使用率
            self._collect_cpu_metrics()

            # 收集記憶體使用情況
            self._collect_memory_metrics()

            # 收集磁碟使用情況
            self._collect_disk_metrics()

            # 收集網路使用情況
            self._collect_network_metrics()

            # 收集進程資訊
            self._collect_process_metrics()

            # 收集系統負載
            self._collect_load_metrics()

        except Exception as e:
            module_logger.error("收集系統資源指標時發生錯誤: %s", e)

    def _collect_cpu_metrics(self) -> None:
        """收集 CPU 指標"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics["cpu_usage"].set(cpu_percent)
        except Exception as e:
            module_logger.error("收集 CPU 指標失敗: %s", e)

    def _collect_memory_metrics(self) -> None:
        """收集記憶體指標"""
        try:
            memory = psutil.virtual_memory()
            self.metrics["memory_usage"].set(memory.percent)
            self.metrics["memory_used_bytes"].set(memory.used)
            self.metrics["memory_total_bytes"].set(memory.total)
        except Exception as e:
            module_logger.error("收集記憶體指標失敗: %s", e)

    def _collect_disk_metrics(self) -> None:
        """收集磁碟指標"""
        try:
            # 收集磁碟使用率
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    device = partition.device.replace(":", "").replace("\\", "")
                    self.metrics["disk_usage"].labels(device=device).set(
                        (usage.used / usage.total) * 100
                    )
                except (PermissionError, FileNotFoundError):
                    continue

            # 收集磁碟 I/O 統計
            disk_io = psutil.disk_io_counters(perdisk=True)
            if disk_io:
                for device, stats in disk_io.items():
                    self.metrics["disk_read_bytes"].labels(
                        device=device
                    )._value._value = stats.read_bytes
                    self.metrics["disk_write_bytes"].labels(
                        device=device
                    )._value._value = stats.write_bytes

        except Exception as e:
            module_logger.error("收集磁碟指標失敗: %s", e)

    def _collect_network_metrics(self) -> None:
        """收集網路指標"""
        try:
            network_io = psutil.net_io_counters(pernic=True)
            if network_io:
                for interface, stats in network_io.items():
                    self.metrics["network_recv_bytes"].labels(
                        interface=interface
                    )._value._value = stats.bytes_recv
                    self.metrics["network_sent_bytes"].labels(
                        interface=interface
                    )._value._value = stats.bytes_sent
        except Exception as e:
            module_logger.error("收集網路指標失敗: %s", e)

    def _collect_process_metrics(self) -> None:
        """收集進程指標"""
        try:
            process_count = len(psutil.pids())
            self.metrics["process_count"].set(process_count)
        except Exception as e:
            module_logger.error("收集進程指標失敗: %s", e)

    def _collect_load_metrics(self) -> None:
        """收集系統負載指標"""
        try:
            if "load_average" in self.metrics and hasattr(os, "getloadavg"):
                load1, load5, load15 = os.getloadavg()
                self.metrics["load_average"].labels(period="1m").set(load1)
                self.metrics["load_average"].labels(period="5m").set(load5)
                self.metrics["load_average"].labels(period="15m").set(load15)
        except Exception as e:
            module_logger.error("收集系統負載指標失敗: %s", e)
