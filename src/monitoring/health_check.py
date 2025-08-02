"""
健康檢查模組

此模組提供系統各組件的健康檢查功能，用於監控系統狀態和自動恢復。
"""

import json
import logging
import threading
import time
import traceback
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# 導入日誌模組
try:
    from src.logging import LogCategory, get_logger

    logger = get_logger("health_check", category=LogCategory.SYSTEM)
except ImportError:
    # 如果無法導入自定義日誌模組，則使用標準日誌模組
    logger = logging.getLogger("health_check")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)


class HealthStatus(Enum):
    """健康狀態"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class HealthCheck:
    """健康檢查類"""

    def __init__(
        self,
        name: str,
        check_func: Callable[[], Union[bool, HealthStatus, Dict[str, Any]]],
        description: str = "",
        interval: float = 60.0,
        timeout: float = 10.0,
        retry_count: int = 3,
        retry_delay: float = 5.0,
        dependencies: Optional[List[str]] = None,
        recovery_func: Optional[Callable[[], bool]] = None,
        tags: Optional[List[str]] = None,
    ):
        """
        初始化健康檢查

        Args:
            name: 健康檢查名稱
            check_func: 檢查函數，返回 bool、HealthStatus 或包含 'status' 鍵的字典
            description: 健康檢查描述
            interval: 檢查間隔（秒）
            timeout: 檢查超時時間（秒）
            retry_count: 重試次數
            retry_delay: 重試延遲（秒）
            dependencies: 依賴的其他健康檢查名稱列表
            recovery_func: 恢復函數，返回是否恢復成功
            tags: 標籤列表
        """
        self.name = name
        self.check_func = check_func
        self.description = description
        self.interval = interval
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.dependencies = dependencies or []
        self.recovery_func = recovery_func
        self.tags = tags or []

        self.status = HealthStatus.UNKNOWN
        self.last_check_time = 0
        self.last_success_time = 0
        self.last_failure_time = 0
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.total_checks = 0
        self.successful_checks = 0
        self.failed_checks = 0
        self.recovery_attempts = 0
        self.successful_recoveries = 0
        self.details = {}
        self.error_message = ""

        logger.info(f"初始化健康檢查 '{name}': 間隔={interval}秒, 超時={timeout}秒")

    def check(self, force: bool = False) -> HealthStatus:
        """
        執行健康檢查

        Args:
            force: 是否強制執行檢查，忽略間隔時間

        Returns:
            HealthStatus: 健康狀態
        """
        current_time = time.time()

        # 如果不是強制檢查且未到檢查間隔，則返回當前狀態
        if not force and current_time - self.last_check_time < self.interval:
            return self.status

        self.last_check_time = current_time
        self.total_checks += 1

        # 執行檢查
        try:
            # 設置超時
            result = self._execute_with_timeout(self.check_func)

            # 解析結果
            status, details = self._parse_check_result(result)

            # 更新狀態
            self.status = status
            self.details = details

            if status == HealthStatus.HEALTHY:
                self.last_success_time = current_time
                self.consecutive_failures = 0
                self.consecutive_successes += 1
                self.successful_checks += 1
                self.error_message = ""
                logger.debug(f"健康檢查 '{self.name}' 成功")
            else:
                self.last_failure_time = current_time
                self.consecutive_successes = 0
                self.consecutive_failures += 1
                self.failed_checks += 1
                self.error_message = details.get("error", "")
                logger.warning(
                    f"健康檢查 '{self.name}' 失敗: 狀態={status.value}, 錯誤={self.error_message}"
                )

                # 嘗試恢復
                if self.recovery_func and status == HealthStatus.UNHEALTHY:
                    self._attempt_recovery()
        except Exception as e:
            self.last_failure_time = current_time
            self.consecutive_successes = 0
            self.consecutive_failures += 1
            self.failed_checks += 1
            self.status = HealthStatus.UNHEALTHY
            self.error_message = str(e)
            self.details = {
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
            logger.error(f"健康檢查 '{self.name}' 執行異常: {str(e)}")

            # 嘗試恢復
            if self.recovery_func:
                self._attempt_recovery()

        return self.status

    def _execute_with_timeout(self, func: Callable) -> Any:
        """
        使用超時執行函數

        Args:
            func: 要執行的函數

        Returns:
            Any: 函數返回值

        Raises:
            TimeoutError: 如果執行超時
        """
        # TODO: 實現真正的超時機制
        # 目前簡單實現，不支持真正的超時中斷
        start_time = time.time()
        result = func()
        elapsed_time = time.time() - start_time

        if elapsed_time > self.timeout:
            logger.warning(
                f"健康檢查 '{self.name}' 執行超時: {elapsed_time:.2f}秒 > {self.timeout}秒"
            )

        return result

    def _parse_check_result(self, result: Any) -> Tuple[HealthStatus, Dict[str, Any]]:
        """
        解析檢查結果

        Args:
            result: 檢查結果

        Returns:
            Tuple[HealthStatus, Dict[str, Any]]: 健康狀態和詳細信息
        """
        if isinstance(result, bool):
            status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
            details = {"success": result}
        elif isinstance(result, HealthStatus):
            status = result
            details = {"status": status.value}
        elif isinstance(result, dict):
            status_value = result.get("status", "unknown").lower()
            if status_value == "healthy":
                status = HealthStatus.HEALTHY
            elif status_value == "degraded":
                status = HealthStatus.DEGRADED
            elif status_value == "unhealthy":
                status = HealthStatus.UNHEALTHY
            else:
                status = HealthStatus.UNKNOWN
            details = result
        else:
            status = HealthStatus.UNKNOWN
            details = {"result": str(result)}

        return status, details

    def _attempt_recovery(self) -> bool:
        """
        嘗試恢復

        Returns:
            bool: 是否恢復成功
        """
        if not self.recovery_func:
            return False

        self.recovery_attempts += 1
        logger.info(f"嘗試恢復健康檢查 '{self.name}' (第 {self.recovery_attempts} 次)")

        try:
            success = self.recovery_func()
            if success:
                self.successful_recoveries += 1
                logger.info(f"健康檢查 '{self.name}' 恢復成功")

                # 重新檢查
                self.check(force=True)
                return True
            else:
                logger.warning(f"健康檢查 '{self.name}' 恢復失敗")
                return False
        except Exception as e:
            logger.error(f"健康檢查 '{self.name}' 恢復異常: {str(e)}")
            return False

    def get_metrics(self) -> Dict[str, Any]:
        """
        獲取健康檢查指標

        Returns:
            Dict[str, Any]: 健康檢查指標
        """
        return {
            "name": self.name,
            "status": self.status.value,
            "description": self.description,
            "last_check_time": self.last_check_time,
            "last_success_time": self.last_success_time,
            "last_failure_time": self.last_failure_time,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "total_checks": self.total_checks,
            "successful_checks": self.successful_checks,
            "failed_checks": self.failed_checks,
            "recovery_attempts": self.recovery_attempts,
            "successful_recoveries": self.successful_recoveries,
            "details": self.details,
            "error_message": self.error_message,
            "dependencies": self.dependencies,
            "tags": self.tags,
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典

        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "name": self.name,
            "status": self.status.value,
            "description": self.description,
            "details": self.details,
            "error": self.error_message,
            "last_check": self.last_check_time,
        }


class HealthCheckRegistry:
    """健康檢查註冊表"""

    def __init__(self):
        """初始化健康檢查註冊表"""
        self.health_checks: Dict[str, HealthCheck] = {}
        self.lock = threading.RLock()
        self.running = False
        self.check_thread = None

    def register(self, health_check: HealthCheck) -> None:
        """
        註冊健康檢查

        Args:
            health_check: 健康檢查
        """
        with self.lock:
            self.health_checks[health_check.name] = health_check
            logger.info(f"註冊健康檢查 '{health_check.name}'")

    def unregister(self, name: str) -> None:
        """
        取消註冊健康檢查

        Args:
            name: 健康檢查名稱
        """
        with self.lock:
            if name in self.health_checks:
                del self.health_checks[name]
                logger.info(f"取消註冊健康檢查 '{name}'")

    def get(self, name: str) -> Optional[HealthCheck]:
        """
        獲取健康檢查

        Args:
            name: 健康檢查名稱

        Returns:
            Optional[HealthCheck]: 健康檢查，如果不存在則返回 None
        """
        return self.health_checks.get(name)

    def get_all(self) -> Dict[str, HealthCheck]:
        """
        獲取所有健康檢查

        Returns:
            Dict[str, HealthCheck]: 所有健康檢查
        """
        return self.health_checks.copy()

    def check_all(self, force: bool = False) -> Dict[str, HealthStatus]:
        """
        執行所有健康檢查

        Args:
            force: 是否強制執行檢查，忽略間隔時間

        Returns:
            Dict[str, HealthStatus]: 健康檢查結果
        """
        results = {}
        for name, health_check in self.health_checks.items():
            results[name] = health_check.check(force)
        return results

    def get_overall_status(self) -> HealthStatus:
        """
        獲取整體健康狀態

        Returns:
            HealthStatus: 整體健康狀態
        """
        if not self.health_checks:
            return HealthStatus.UNKNOWN

        statuses = [health_check.status for health_check in self.health_checks.values()]

        if any(status == HealthStatus.UNHEALTHY for status in statuses):
            return HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in statuses):
            return HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN

    def start_background_checks(self, check_interval: float = 60.0) -> None:
        """
        啟動背景健康檢查

        Args:
            check_interval: 檢查間隔（秒）
        """
        with self.lock:
            if self.running:
                logger.warning("背景健康檢查已在運行")
                return

            self.running = True
            self.check_thread = threading.Thread(
                target=self._background_check_loop,
                args=(check_interval,),
                daemon=True,
            )
            self.check_thread.start()
            logger.info(f"啟動背景健康檢查，間隔={check_interval}秒")

    def stop_background_checks(self) -> None:
        """停止背景健康檢查"""
        with self.lock:
            self.running = False
            logger.info("停止背景健康檢查")

    def _background_check_loop(self, check_interval: float) -> None:
        """
        背景健康檢查循環

        Args:
            check_interval: 檢查間隔（秒）
        """
        while self.running:
            try:
                self.check_all()
            except Exception as e:
                logger.error(f"背景健康檢查異常: {str(e)}")

            # 等待下一次檢查
            for _ in range(int(check_interval)):
                if not self.running:
                    break
                time.sleep(1)

    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典

        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "overall_status": self.get_overall_status().value,
            "checks": {
                name: check.to_dict() for name, check in self.health_checks.items()
            },
        }

    def to_json(self, indent: Optional[int] = None) -> str:
        """
        轉換為 JSON 字符串

        Args:
            indent: 縮進

        Returns:
            str: JSON 字符串
        """
        return json.dumps(self.to_dict(), indent=indent)


# 創建全局健康檢查註冊表
health_check_registry = HealthCheckRegistry()


# 導出模組內容
__all__ = [
    "HealthStatus",
    "HealthCheck",
    "HealthCheckRegistry",
    "health_check_registry",
]
