"""健康檢查基礎類別

此模組定義健康檢查的基礎類別和數據結構，包括：
- 健康狀態枚舉
- 健康檢查結果數據類
- 基礎健康檢查器介面

遵循 Google Style Docstring 標準和 Phase 5.3 開發規範。
"""

from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass, field
from enum import Enum


class HealthStatus(Enum):
    """健康狀態枚舉"""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """健康檢查結果數據類

    Attributes:
        name: 檢查項目名稱
        status: 健康狀態
        score: 健康分數 (0-100)
        message: 狀態訊息
        details: 詳細資訊
        timestamp: 檢查時間
        duration: 檢查耗時（秒）
    """

    name: str
    status: HealthStatus
    score: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式

        Returns:
            Dict[str, Any]: 字典格式的檢查結果
        """
        return {
            "name": self.name,
            "status": self.status.value,
            "score": self.score,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "duration": self.duration,
        }

    def is_healthy(self) -> bool:
        """檢查是否健康

        Returns:
            bool: 健康狀態為 HEALTHY 或 WARNING 時返回 True
        """
        return self.status in [HealthStatus.HEALTHY, HealthStatus.WARNING]

    def is_critical(self) -> bool:
        """檢查是否為嚴重狀態

        Returns:
            bool: 健康狀態為 CRITICAL 時返回 True
        """
        return self.status == HealthStatus.CRITICAL


class BaseHealthChecker:
    """基礎健康檢查器

    定義健康檢查器的基本介面和通用功能。
    """

    def __init__(self, name: str):
        """初始化基礎健康檢查器

        Args:
            name: 檢查器名稱
        """
        self.name = name

    def check(self) -> HealthCheckResult:
        """執行健康檢查

        Returns:
            HealthCheckResult: 檢查結果

        Raises:
            NotImplementedError: 子類必須實現此方法
        """
        raise NotImplementedError("子類必須實現 check 方法")

    def is_enabled(self) -> bool:
        """檢查是否啟用

        Returns:
            bool: 預設返回 True
        """
        return True

    def get_timeout(self) -> float:
        """獲取檢查超時時間

        Returns:
            float: 超時時間（秒），預設 30 秒
        """
        return 30.0


class HealthCheckError(Exception):
    """健康檢查異常

    用於健康檢查過程中的異常處理。
    """

    def __init__(self, message: str, checker_name: str = None):
        """初始化健康檢查異常

        Args:
            message: 異常訊息
            checker_name: 檢查器名稱
        """
        super().__init__(message)
        self.checker_name = checker_name

    def __str__(self) -> str:
        """返回異常字串表示

        Returns:
            str: 異常字串
        """
        if self.checker_name:
            return f"[{self.checker_name}] {super().__str__()}"
        return super().__str__()


class HealthCheckConfig:
    """健康檢查配置

    管理健康檢查的配置參數。
    """

    def __init__(self, config_dict: Dict[str, Any] = None):
        """初始化健康檢查配置

        Args:
            config_dict: 配置字典
        """
        self.config = config_dict or {}

    def get_interval(self) -> int:
        """獲取檢查間隔

        Returns:
            int: 檢查間隔（秒），預設 60 秒
        """
        return self.config.get("interval", 60)

    def get_timeout(self) -> int:
        """獲取檢查超時時間

        Returns:
            int: 超時時間（秒），預設 30 秒
        """
        return self.config.get("timeout", 30)

    def is_check_enabled(self, check_name: str) -> bool:
        """檢查指定檢查項目是否啟用

        Args:
            check_name: 檢查項目名稱

        Returns:
            bool: 啟用返回 True，否則返回 False
        """
        checks_config = self.config.get("checks", {})
        check_config = checks_config.get(check_name, {})
        return check_config.get("enabled", True)

    def get_check_config(self, check_name: str) -> Dict[str, Any]:
        """獲取指定檢查項目的配置

        Args:
            check_name: 檢查項目名稱

        Returns:
            Dict[str, Any]: 檢查項目配置
        """
        checks_config = self.config.get("checks", {})
        return checks_config.get(check_name, {})

    def get_thresholds(self, check_name: str) -> Dict[str, float]:
        """獲取指定檢查項目的閾值配置

        Args:
            check_name: 檢查項目名稱

        Returns:
            Dict[str, float]: 閾值配置
        """
        check_config = self.get_check_config(check_name)
        return check_config.get("thresholds", {})


def calculate_overall_score(results: Dict[str, HealthCheckResult]) -> float:
    """計算整體健康分數

    Args:
        results: 檢查結果字典

    Returns:
        float: 整體健康分數 (0-100)
    """
    if not results:
        return 0.0

    total_score = sum(result.score for result in results.values())
    return total_score / len(results)


def get_overall_status(results: Dict[str, HealthCheckResult]) -> HealthStatus:
    """獲取整體健康狀態

    Args:
        results: 檢查結果字典

    Returns:
        HealthStatus: 整體健康狀態
    """
    if not results:
        return HealthStatus.UNKNOWN

    # 統計各狀態數量
    critical_count = sum(
        1 for result in results.values() if result.status == HealthStatus.CRITICAL
    )
    warning_count = sum(
        1 for result in results.values() if result.status == HealthStatus.WARNING
    )

    # 確定整體狀態
    if critical_count > 0:
        return HealthStatus.CRITICAL
    if warning_count > 0:
        return HealthStatus.WARNING
    return HealthStatus.HEALTHY


def create_summary_result(
    results: Dict[str, HealthCheckResult], name: str = "overall"
) -> HealthCheckResult:
    """創建摘要檢查結果

    Args:
        results: 檢查結果字典
        name: 摘要結果名稱

    Returns:
        HealthCheckResult: 摘要檢查結果
    """
    if not results:
        return HealthCheckResult(
            name=name,
            status=HealthStatus.UNKNOWN,
            score=0.0,
            message="尚未執行健康檢查",
        )

    overall_score = calculate_overall_score(results)
    overall_status = get_overall_status(results)

    # 統計詳情
    critical_count = sum(
        1 for result in results.values() if result.status == HealthStatus.CRITICAL
    )
    warning_count = sum(
        1 for result in results.values() if result.status == HealthStatus.WARNING
    )
    healthy_count = sum(
        1 for result in results.values() if result.status == HealthStatus.HEALTHY
    )

    # 生成狀態訊息
    if critical_count > 0:
        message = f"系統存在 {critical_count} 個嚴重問題"
    elif warning_count > 0:
        message = f"系統存在 {warning_count} 個警告"
    else:
        message = "系統運行正常"

    details = {
        "total_checks": len(results),
        "healthy_count": healthy_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "average_score": round(overall_score, 2),
    }

    return HealthCheckResult(
        name=name,
        status=overall_status,
        score=overall_score,
        message=message,
        details=details,
    )
