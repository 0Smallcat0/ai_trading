"""系統監控核心模組

此模組提供系統監控的核心功能，包括系統資源監控和健康狀態檢查。
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

# 嘗試導入 psutil
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


class MonitoringCoreError(Exception):
    """監控核心異常類別"""


class MonitoringCore:
    """系統監控核心類別"""

    def __init__(self):
        """初始化監控核心"""
        self.last_check_time = None
        self.health_history = []

    def get_system_metrics(self) -> Dict[str, Any]:
        """獲取系統指標

        Returns:
            Dict[str, Any]: 系統指標字典
        """
        try:
            if not PSUTIL_AVAILABLE:
                logger.warning("psutil 不可用，返回模擬數據")
                return self._get_mock_system_metrics()

            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            # 記憶體使用情況
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used
            memory_total = memory.total

            # 磁碟使用情況
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100
            disk_used = disk.used
            disk_total = disk.total

            # 網路統計
            network = psutil.net_io_counters()
            network_sent = network.bytes_sent
            network_recv = network.bytes_recv

            metrics = {
                "timestamp": datetime.now(),
                "cpu": {
                    "percent": cpu_percent,
                    "count": cpu_count,
                },
                "memory": {
                    "percent": memory_percent,
                    "used": memory_used,
                    "total": memory_total,
                    "available": memory.available,
                },
                "disk": {
                    "percent": disk_percent,
                    "used": disk_used,
                    "total": disk_total,
                    "free": disk.free,
                },
                "network": {
                    "bytes_sent": network_sent,
                    "bytes_recv": network_recv,
                },
            }

            logger.info("系統指標獲取成功")
            return metrics

        except Exception as e:
            logger.error("獲取系統指標時發生錯誤: %s", e)
            return self._get_mock_system_metrics()

    def calculate_health_score(self, metrics: Dict[str, Any]) -> float:
        """計算系統健康評分

        Args:
            metrics: 系統指標字典

        Returns:
            float: 健康評分 (0-100)
        """
        try:
            score = 100.0

            # CPU 評分 (權重: 30%)
            cpu_percent = metrics.get("cpu", {}).get("percent", 0)
            if cpu_percent > 90:
                score -= 30
            elif cpu_percent > 80:
                score -= 20
            elif cpu_percent > 70:
                score -= 10

            # 記憶體評分 (權重: 30%)
            memory_percent = metrics.get("memory", {}).get("percent", 0)
            if memory_percent > 90:
                score -= 30
            elif memory_percent > 80:
                score -= 20
            elif memory_percent > 70:
                score -= 10

            # 磁碟評分 (權重: 20%)
            disk_percent = metrics.get("disk", {}).get("percent", 0)
            if disk_percent > 95:
                score -= 20
            elif disk_percent > 90:
                score -= 15
            elif disk_percent > 85:
                score -= 10

            # 確保評分在 0-100 範圍內
            score = max(0, min(100, score))

            logger.info("健康評分計算完成: %.2f", score)
            return score

        except Exception as e:
            logger.error("計算健康評分時發生錯誤: %s", e)
            return 50.0  # 預設評分

    def check_system_health(self) -> Dict[str, Any]:
        """檢查系統健康狀態

        Returns:
            Dict[str, Any]: 健康狀態字典
        """
        try:
            metrics = self.get_system_metrics()
            health_score = self.calculate_health_score(metrics)

            # 判斷健康狀態
            if health_score >= 80:
                status = "healthy"
                level = "info"
            elif health_score >= 60:
                status = "warning"
                level = "warning"
            else:
                status = "critical"
                level = "error"

            health_data = {
                "timestamp": datetime.now(),
                "status": status,
                "level": level,
                "score": health_score,
                "metrics": metrics,
                "issues": self._identify_issues(metrics),
            }

            # 記錄健康狀態歷史
            self._record_health_history(health_data)

            logger.info("系統健康檢查完成，狀態: %s，評分: %.2f", status, health_score)
            return health_data

        except Exception as e:
            logger.error("檢查系統健康狀態時發生錯誤: %s", e)
            return {
                "timestamp": datetime.now(),
                "status": "unknown",
                "level": "error",
                "score": 0.0,
                "error": str(e),
            }

    def get_health_history(self, hours: int = 24) -> list:
        """獲取健康狀態歷史

        Args:
            hours: 查詢小時數

        Returns:
            list: 健康狀態歷史列表
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            filtered_history = [
                record
                for record in self.health_history
                if record.get("timestamp", datetime.min) >= cutoff_time
            ]

            logger.info("獲取健康狀態歷史成功，記錄數: %d", len(filtered_history))
            return filtered_history

        except Exception as e:
            logger.error("獲取健康狀態歷史時發生錯誤: %s", e)
            return []

    def _get_mock_system_metrics(self) -> Dict[str, Any]:
        """獲取模擬系統指標（內部方法）"""
        import random

        return {
            "timestamp": datetime.now(),
            "cpu": {
                "percent": random.uniform(10, 80),
                "count": 4,
            },
            "memory": {
                "percent": random.uniform(30, 70),
                "used": random.randint(2000000000, 6000000000),
                "total": 8000000000,
                "available": random.randint(2000000000, 6000000000),
            },
            "disk": {
                "percent": random.uniform(40, 80),
                "used": random.randint(50000000000, 200000000000),
                "total": 500000000000,
                "free": random.randint(300000000000, 450000000000),
            },
            "network": {
                "bytes_sent": random.randint(1000000, 10000000),
                "bytes_recv": random.randint(1000000, 10000000),
            },
        }

    def _identify_issues(self, metrics: Dict[str, Any]) -> list:
        """識別系統問題（內部方法）"""
        issues = []

        # 檢查 CPU 使用率
        cpu_percent = metrics.get("cpu", {}).get("percent", 0)
        if cpu_percent > 90:
            issues.append(
                {
                    "type": "cpu",
                    "severity": "critical",
                    "message": "CPU 使用率過高: %.1f%%" % cpu_percent,
                }
            )
        elif cpu_percent > 80:
            issues.append(
                {
                    "type": "cpu",
                    "severity": "warning",
                    "message": "CPU 使用率較高: %.1f%%" % cpu_percent,
                }
            )

        # 檢查記憶體使用率
        memory_percent = metrics.get("memory", {}).get("percent", 0)
        if memory_percent > 90:
            issues.append(
                {
                    "type": "memory",
                    "severity": "critical",
                    "message": "記憶體使用率過高: %.1f%%" % memory_percent,
                }
            )
        elif memory_percent > 80:
            issues.append(
                {
                    "type": "memory",
                    "severity": "warning",
                    "message": "記憶體使用率較高: %.1f%%" % memory_percent,
                }
            )

        # 檢查磁碟使用率
        disk_percent = metrics.get("disk", {}).get("percent", 0)
        if disk_percent > 95:
            issues.append(
                {
                    "type": "disk",
                    "severity": "critical",
                    "message": "磁碟使用率過高: %.1f%%" % disk_percent,
                }
            )
        elif disk_percent > 90:
            issues.append(
                {
                    "type": "disk",
                    "severity": "warning",
                    "message": "磁碟使用率較高: %.1f%%" % disk_percent,
                }
            )

        return issues

    def _record_health_history(self, health_data: Dict[str, Any]):
        """記錄健康狀態歷史（內部方法）"""
        try:
            self.health_history.append(health_data)

            # 保持歷史記錄在合理範圍內（最多保留 1000 條記錄）
            if len(self.health_history) > 1000:
                self.health_history = self.health_history[-1000:]

        except Exception as e:
            logger.error("記錄健康狀態歷史時發生錯誤: %s", e)
