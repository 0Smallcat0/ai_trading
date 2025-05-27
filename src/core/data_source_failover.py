"""資料源故障轉移管理器

此模組提供資料源的健康檢查、故障轉移和自動恢復功能。

主要功能：
- 資料源健康檢查
- 自動故障轉移
- 故障恢復監控
- 資料源優先級管理
- 性能監控和統計
"""

import logging
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

# 設定日誌
logger = logging.getLogger(__name__)


class DataSourceHealth:
    """資料源健康狀態"""

    def __init__(self, source_name: str):
        """初始化資料源健康狀態

        Args:
            source_name: 資料源名稱
        """
        self.source_name = source_name
        self.is_healthy = True
        self.last_check_time = datetime.now()
        self.last_success_time = datetime.now()
        self.last_failure_time = None
        self.consecutive_failures = 0
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.average_response_time = 0.0
        self.response_times = deque(maxlen=100)
        self.error_messages = deque(maxlen=10)

    def record_success(self, response_time: float):
        """記錄成功請求"""
        self.total_requests += 1
        self.successful_requests += 1
        self.consecutive_failures = 0
        self.last_success_time = datetime.now()
        self.response_times.append(response_time)
        self._update_average_response_time()

        # 如果之前不健康，現在恢復健康
        if not self.is_healthy:
            self.is_healthy = True
            logger.info("資料源 %s 已恢復健康", self.source_name)

    def record_failure(self, error_message: str = ""):
        """記錄失敗請求"""
        self.total_requests += 1
        self.failed_requests += 1
        self.consecutive_failures += 1
        self.last_failure_time = datetime.now()
        if error_message:
            self.error_messages.append(error_message)

    def _update_average_response_time(self):
        """更新平均響應時間"""
        if self.response_times:
            self.average_response_time = (
                sum(self.response_times) / len(self.response_times)
            )

    def get_success_rate(self) -> float:
        """獲取成功率"""
        if not self.total_requests:
            return 1.0
        return self.successful_requests / self.total_requests

    def is_considered_unhealthy(self, max_consecutive_failures: int = 3) -> bool:
        """判斷是否應該被認為不健康"""
        return self.consecutive_failures >= max_consecutive_failures

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        return {
            "source_name": self.source_name,
            "is_healthy": self.is_healthy,
            "last_check_time": self.last_check_time.isoformat(),
            "last_success_time": self.last_success_time.isoformat(),
            "last_failure_time": (
                self.last_failure_time.isoformat()
                if self.last_failure_time else None
            ),
            "consecutive_failures": self.consecutive_failures,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.get_success_rate(),
            "average_response_time": self.average_response_time,
            "recent_errors": list(self.error_messages),
        }


class DataSourceFailoverManager:
    """資料源故障轉移管理器"""

    def __init__(
        self,
        *,
        health_check_interval: float = 30.0,
        max_consecutive_failures: int = 3,
        recovery_check_interval: float = 60.0,
        circuit_breaker_timeout: float = 300.0,
    ):
        """初始化故障轉移管理器

        Args:
            health_check_interval: 健康檢查間隔（秒）
            max_consecutive_failures: 最大連續失敗次數
            recovery_check_interval: 恢復檢查間隔（秒）
            circuit_breaker_timeout: 熔斷器超時時間（秒）
        """
        self.health_check_interval = health_check_interval
        self.max_consecutive_failures = max_consecutive_failures
        self.recovery_check_interval = recovery_check_interval
        self.circuit_breaker_timeout = circuit_breaker_timeout

        # 資料源配置
        self.data_sources: Dict[str, Dict[str, Any]] = {}
        self.source_priorities: Dict[str, List[str]] = {}
        self.health_status: Dict[str, DataSourceHealth] = {}

        # 熔斷器狀態
        self.circuit_breakers: Dict[str, datetime] = {}

        # 健康檢查線程
        self.health_check_thread = None
        self.is_running = False
        self.lock = threading.RLock()

        # 統計信息
        self.stats = {
            "total_failovers": 0,
            "total_recoveries": 0,
            "failover_history": deque(maxlen=100),
            "recovery_history": deque(maxlen=100),
        }

        logger.info("資料源故障轉移管理器初始化完成")

    def register_data_source(
        self,
        source_name: str,
        adapter: Any,
        *,
        health_check_func: Optional[Callable[[], bool]] = None,
        priority_groups: Optional[List[str]] = None,
    ):
        """註冊資料源

        Args:
            source_name: 資料源名稱
            adapter: 資料源適配器
            health_check_func: 健康檢查函數
            priority_groups: 優先級組列表
        """
        with self.lock:
            self.data_sources[source_name] = {
                "adapter": adapter,
                "health_check_func": health_check_func,
                "priority_groups": priority_groups or [],
            }

            # 初始化健康狀態
            self.health_status[source_name] = DataSourceHealth(source_name)

            # 更新優先級組
            if priority_groups:
                for group in priority_groups:
                    if group not in self.source_priorities:
                        self.source_priorities[group] = []
                    if source_name not in self.source_priorities[group]:
                        self.source_priorities[group].append(source_name)

            logger.info("已註冊資料源: %s", source_name)

    def set_priority_order(self, group: str, priority_order: List[str]):
        """設定優先級順序

        Args:
            group: 優先級組名稱
            priority_order: 優先級順序列表
        """
        with self.lock:
            # 驗證所有資料源都已註冊
            for source in priority_order:
                if source not in self.data_sources:
                    raise ValueError(f"資料源 {source} 未註冊")

            self.source_priorities[group] = priority_order.copy()
            logger.info("已設定 %s 組的優先級順序: %s", group, priority_order)

    def get_best_source(self, group: str) -> Optional[str]:
        """獲取最佳資料源

        Args:
            group: 優先級組名稱

        Returns:
            Optional[str]: 最佳資料源名稱，如果沒有可用的則返回 None
        """
        with self.lock:
            if group not in self.source_priorities:
                logger.warning("未找到優先級組: %s", group)
                return None

            # 按優先級檢查資料源
            for source_name in self.source_priorities[group]:
                if self._is_source_available(source_name):
                    return source_name

            logger.warning("優先級組 %s 中沒有可用的資料源", group)
            return None

    def _is_source_available(self, source_name: str) -> bool:
        """檢查資料源是否可用

        Args:
            source_name: 資料源名稱

        Returns:
            bool: 是否可用
        """
        # 檢查是否在熔斷器狀態
        if source_name in self.circuit_breakers:
            circuit_time = self.circuit_breakers[source_name]
            timeout_delta = timedelta(seconds=self.circuit_breaker_timeout)
            if datetime.now() - circuit_time < timeout_delta:
                return False
            # 熔斷器超時，移除熔斷狀態
            del self.circuit_breakers[source_name]

        # 檢查健康狀態
        health = self.health_status.get(source_name)
        if health:
            return health.is_healthy

        return True

    def record_request_result(
        self,
        source_name: str,
        success: bool,
        response_time: float = 0.0,
        error_message: str = ""
    ):
        """記錄請求結果

        Args:
            source_name: 資料源名稱
            success: 是否成功
            response_time: 響應時間
            error_message: 錯誤消息
        """
        with self.lock:
            if source_name not in self.health_status:
                logger.warning("未找到資料源 %s 的健康狀態", source_name)
                return

            health = self.health_status[source_name]

            if success:
                health.record_success(response_time)
            else:
                health.record_failure(error_message)

                # 檢查是否需要標記為不健康
                max_failures = self.max_consecutive_failures
                if health.is_considered_unhealthy(max_failures):
                    self._mark_source_unhealthy(source_name)

    def _mark_source_unhealthy(self, source_name: str):
        """標記資料源為不健康"""
        health = self.health_status[source_name]
        if health.is_healthy:
            health.is_healthy = False
            self.circuit_breakers[source_name] = datetime.now()

            # 記錄故障轉移事件
            failover_event = {
                "source_name": source_name,
                "timestamp": datetime.now().isoformat(),
                "consecutive_failures": health.consecutive_failures,
            }
            self.stats["failover_history"].append(failover_event)
            self.stats["total_failovers"] += 1

            logger.warning("資料源 %s 已標記為不健康，啟動熔斷器", source_name)

    def start_health_monitoring(self):
        """啟動健康監控"""
        if self.is_running:
            logger.warning("健康監控已在運行")
            return

        self.is_running = True
        self.health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self.health_check_thread.start()
        logger.info("健康監控已啟動")

    def stop_health_monitoring(self):
        """停止健康監控"""
        self.is_running = False
        if self.health_check_thread and self.health_check_thread.is_alive():
            self.health_check_thread.join(timeout=5.0)
        logger.info("健康監控已停止")

    def _health_check_loop(self):
        """健康檢查主循環"""
        while self.is_running:
            try:
                self._perform_health_checks()
                time.sleep(self.health_check_interval)
            except Exception as e:
                logger.error("健康檢查過程中發生錯誤: %s", e)
                time.sleep(min(self.health_check_interval, 30))

    def _perform_health_checks(self):
        """執行健康檢查"""
        with self.lock:
            for source_name, source_config in self.data_sources.items():
                try:
                    health_check_func = source_config.get("health_check_func")

                    if health_check_func:
                        # 使用自定義健康檢查函數
                        start_time = time.time()
                        is_healthy = health_check_func()
                        response_time = time.time() - start_time

                        self.record_request_result(
                            source_name,
                            is_healthy,
                            response_time,
                            "" if is_healthy else "健康檢查失敗"
                        )
                    else:
                        # 使用適配器的默認健康檢查
                        adapter = source_config.get("adapter")
                        if hasattr(adapter, "test_connection"):
                            start_time = time.time()
                            is_healthy = adapter.test_connection()
                            response_time = time.time() - start_time

                            self.record_request_result(
                                source_name,
                                is_healthy,
                                response_time,
                                "" if is_healthy else "連接測試失敗"
                            )

                    # 更新最後檢查時間
                    if source_name in self.health_status:
                        self.health_status[source_name].last_check_time = datetime.now()

                except Exception as e:
                    logger.error("檢查資料源 %s 健康狀態時發生錯誤: %s", source_name, e)
                    self.record_request_result(source_name, False, 0.0, str(e))

    def force_failover(self, source_name: str, reason: str = "手動故障轉移"):
        """強制故障轉移

        Args:
            source_name: 要故障轉移的資料源名稱
            reason: 故障轉移原因
        """
        with self.lock:
            if source_name in self.health_status:
                self.health_status[source_name].is_healthy = False
                self.circuit_breakers[source_name] = datetime.now()

                # 記錄故障轉移事件
                failover_event = {
                    "source_name": source_name,
                    "timestamp": datetime.now().isoformat(),
                    "reason": reason,
                    "type": "manual",
                }
                self.stats["failover_history"].append(failover_event)
                self.stats["total_failovers"] += 1

                logger.info("已強制故障轉移資料源 %s: %s", source_name, reason)

    def force_recovery(self, source_name: str, reason: str = "手動恢復"):
        """強制恢復資料源

        Args:
            source_name: 要恢復的資料源名稱
            reason: 恢復原因
        """
        with self.lock:
            if source_name in self.health_status:
                self.health_status[source_name].is_healthy = True
                self.health_status[source_name].consecutive_failures = 0

                # 移除熔斷器狀態
                if source_name in self.circuit_breakers:
                    del self.circuit_breakers[source_name]

                # 記錄恢復事件
                recovery_event = {
                    "source_name": source_name,
                    "timestamp": datetime.now().isoformat(),
                    "reason": reason,
                    "type": "manual",
                }
                self.stats["recovery_history"].append(recovery_event)
                self.stats["total_recoveries"] += 1

                logger.info("已強制恢復資料源 %s: %s", source_name, reason)

    def get_health_summary(self) -> Dict[str, Any]:
        """獲取健康狀態摘要

        Returns:
            Dict[str, Any]: 健康狀態摘要
        """
        with self.lock:
            healthy_sources = []
            unhealthy_sources = []
            circuit_breaker_sources = []

            for source_name, health in self.health_status.items():
                if source_name in self.circuit_breakers:
                    circuit_breaker_sources.append(source_name)
                elif health.is_healthy:
                    healthy_sources.append(source_name)
                else:
                    unhealthy_sources.append(source_name)

            return {
                "total_sources": len(self.data_sources),
                "healthy_sources": healthy_sources,
                "unhealthy_sources": unhealthy_sources,
                "circuit_breaker_sources": circuit_breaker_sources,
                "total_failovers": self.stats["total_failovers"],
                "total_recoveries": self.stats["total_recoveries"],
                "priority_groups": list(self.source_priorities.keys()),
            }

    def get_source_stats(self, source_name: str) -> Optional[Dict[str, Any]]:
        """獲取特定資料源的統計信息

        Args:
            source_name: 資料源名稱

        Returns:
            Optional[Dict[str, Any]]: 統計信息，如果資料源不存在則返回 None
        """
        with self.lock:
            if source_name in self.health_status:
                stats = self.health_status[source_name].get_stats()

                # 添加熔斷器信息
                if source_name in self.circuit_breakers:
                    circuit_time = self.circuit_breakers[source_name]
                    stats["circuit_breaker_since"] = circuit_time.isoformat()
                    elapsed = (datetime.now() - circuit_time).total_seconds()
                    remaining = max(0, self.circuit_breaker_timeout - elapsed)
                    stats["circuit_breaker_remaining"] = remaining

                return stats

            return None

    def get_all_stats(self) -> Dict[str, Any]:
        """獲取所有統計信息

        Returns:
            Dict[str, Any]: 完整統計信息
        """
        with self.lock:
            source_stats = {}
            for source_name in self.data_sources:
                source_stats[source_name] = self.get_source_stats(source_name)

            return {
                "summary": self.get_health_summary(),
                "sources": source_stats,
                "configuration": {
                    "health_check_interval": self.health_check_interval,
                    "max_consecutive_failures": self.max_consecutive_failures,
                    "recovery_check_interval": self.recovery_check_interval,
                    "circuit_breaker_timeout": self.circuit_breaker_timeout,
                },
                "priority_groups": self.source_priorities.copy(),
                "recent_failovers": list(self.stats["failover_history"]),
                "recent_recoveries": list(self.stats["recovery_history"]),
            }
