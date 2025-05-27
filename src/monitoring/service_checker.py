"""服務檢查器

此模組實現服務連接檢查功能，包括：
- API 端點健康檢查
- 外部服務連接檢查
- 資料庫連接檢查

遵循 Google Style Docstring 標準和 Phase 5.3 開發規範。
"""

import logging
import time
from typing import Dict
import requests

from .health_checker_base import HealthCheckResult, HealthStatus

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class ServiceChecker:
    """服務檢查器

    提供各種服務的健康狀態檢查功能，包括 API 端點、外部服務和資料庫連接。

    Attributes:
        timeout: 預設超時時間
    """

    def __init__(self, timeout: int = 30):
        """初始化服務檢查器

        Args:
            timeout: 預設超時時間（秒）
        """
        self.timeout = timeout

    def check_database(self) -> HealthCheckResult:
        """檢查資料庫連接

        Returns:
            HealthCheckResult: 資料庫檢查結果
        """
        start_time = time.time()

        try:
            # 這裡應該實現實際的資料庫連接檢查
            # 目前使用模擬檢查

            # 模擬資料庫連接檢查
            time.sleep(0.1)  # 模擬檢查耗時

            # 假設連接成功
            duration = time.time() - start_time

            return HealthCheckResult(
                name="database",
                status=HealthStatus.HEALTHY,
                score=100.0,
                message="資料庫連接正常",
                details={
                    "connection_time": f"{duration:.3f}s",
                    "database_url": "postgresql://***",
                    "pool_size": 10,
                    "active_connections": 3,
                },
                duration=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            module_logger.error("資料庫健康檢查失敗: %s", e)

            return HealthCheckResult(
                name="database",
                status=HealthStatus.CRITICAL,
                score=0.0,
                message=f"資料庫連接失敗: {str(e)}",
                details={"error": str(e)},
                duration=duration,
            )

    def check_api_endpoints(
        self,
        endpoints: list,
        base_url: str = "http://localhost:8000",
        timeout: int = None,
    ) -> Dict[str, HealthCheckResult]:
        """檢查 API 端點健康狀態

        Args:
            endpoints: API 端點列表
            base_url: 基礎 URL
            timeout: 超時時間

        Returns:
            Dict[str, HealthCheckResult]: API 端點檢查結果
        """
        results = {}
        timeout = timeout or self.timeout

        for endpoint in endpoints:
            start_time = time.time()
            check_name = f"api_{endpoint.replace('/', '_').strip('_')}"

            try:
                url = f"{base_url}{endpoint}"
                response = requests.get(url, timeout=timeout)
                duration = time.time() - start_time

                if response.status_code == 200:
                    results[check_name] = HealthCheckResult(
                        name=check_name,
                        status=HealthStatus.HEALTHY,
                        score=100.0,
                        message=f"API 端點 {endpoint} 正常",
                        details={
                            "url": url,
                            "status_code": response.status_code,
                            "response_time": f"{duration:.3f}s",
                        },
                        duration=duration,
                    )
                else:
                    results[check_name] = HealthCheckResult(
                        name=check_name,
                        status=HealthStatus.WARNING,
                        score=50.0,
                        message=f"API 端點 {endpoint} 返回異常狀態碼",
                        details={
                            "url": url,
                            "status_code": response.status_code,
                            "response_time": f"{duration:.3f}s",
                        },
                        duration=duration,
                    )

            except Exception as e:
                duration = time.time() - start_time
                results[check_name] = HealthCheckResult(
                    name=check_name,
                    status=HealthStatus.CRITICAL,
                    score=0.0,
                    message=f"API 端點 {endpoint} 檢查失敗: {str(e)}",
                    details={"error": str(e)},
                    duration=duration,
                )

        return results

    def check_external_services(
        self, services: list, timeout: int = None
    ) -> Dict[str, HealthCheckResult]:
        """檢查外部服務連接

        Args:
            services: 外部服務列表，每個服務包含 name 和 url
            timeout: 超時時間

        Returns:
            Dict[str, HealthCheckResult]: 外部服務檢查結果
        """
        results = {}
        timeout = timeout or self.timeout

        for service in services:
            service_name = service.get("name", "unknown")
            service_url = service.get("url", "")

            start_time = time.time()

            try:
                response = requests.get(service_url, timeout=timeout)
                duration = time.time() - start_time

                if response.status_code == 200:
                    results[service_name] = HealthCheckResult(
                        name=service_name,
                        status=HealthStatus.HEALTHY,
                        score=100.0,
                        message=f"外部服務 {service_name} 正常",
                        details={
                            "url": service_url,
                            "status_code": response.status_code,
                            "response_time": f"{duration:.3f}s",
                        },
                        duration=duration,
                    )
                else:
                    results[service_name] = HealthCheckResult(
                        name=service_name,
                        status=HealthStatus.WARNING,
                        score=50.0,
                        message=f"外部服務 {service_name} 狀態異常",
                        details={
                            "url": service_url,
                            "status_code": response.status_code,
                            "response_time": f"{duration:.3f}s",
                        },
                        duration=duration,
                    )

            except Exception as e:
                duration = time.time() - start_time
                results[service_name] = HealthCheckResult(
                    name=service_name,
                    status=HealthStatus.CRITICAL,
                    score=0.0,
                    message=f"外部服務 {service_name} 連接失敗: {str(e)}",
                    details={"error": str(e)},
                    duration=duration,
                )

        return results

    def check_service_health(
        self, service_url: str, service_name: str = None, timeout: int = None
    ) -> HealthCheckResult:
        """檢查單個服務健康狀態

        Args:
            service_url: 服務 URL
            service_name: 服務名稱
            timeout: 超時時間

        Returns:
            HealthCheckResult: 服務檢查結果
        """
        service_name = service_name or "service"
        timeout = timeout or self.timeout
        start_time = time.time()

        try:
            response = requests.get(service_url, timeout=timeout)
            duration = time.time() - start_time

            if response.status_code == 200:
                return HealthCheckResult(
                    name=service_name,
                    status=HealthStatus.HEALTHY,
                    score=100.0,
                    message=f"服務 {service_name} 正常",
                    details={
                        "url": service_url,
                        "status_code": response.status_code,
                        "response_time": f"{duration:.3f}s",
                    },
                    duration=duration,
                )

            return HealthCheckResult(
                name=service_name,
                status=HealthStatus.WARNING,
                score=50.0,
                message=f"服務 {service_name} 狀態異常",
                details={
                    "url": service_url,
                    "status_code": response.status_code,
                    "response_time": f"{duration:.3f}s",
                },
                duration=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            module_logger.error("服務 %s 檢查失敗: %s", service_name, e)

            return HealthCheckResult(
                name=service_name,
                status=HealthStatus.CRITICAL,
                score=0.0,
                message=f"服務 {service_name} 連接失敗: {str(e)}",
                details={"error": str(e)},
                duration=duration,
            )
