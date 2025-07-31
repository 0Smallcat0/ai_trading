"""API 效能指標收集器

此模組實現 API 效能指標的收集，包括回應時間、錯誤率、QPS 統計等。
"""

import logging
import time
from typing import Dict, Any, Optional

try:
    from prometheus_client import Counter, Gauge, Histogram
except ImportError:
    Counter = None
    Gauge = None
    Histogram = None

from .base import PrometheusCollectorBase

# 設置模組日誌
module_logger = logging.getLogger(__name__)


class APIMetricsCollector(PrometheusCollectorBase):
    """API 效能指標收集器

    收集 API 服務的效能指標，包括請求處理時間、錯誤率、QPS 等。

    Attributes:
        request_duration: 請求處理時間直方圖
        request_count: 請求數量計數器
        error_count: 錯誤數量計數器
        active_connections: 活躍連接數
    """

    def __init__(self, collection_interval: int = 15):
        """初始化 API 效能指標收集器

        Args:
            collection_interval: 指標收集間隔，預設 15 秒

        Raises:
            ImportError: 當 prometheus_client 套件未安裝時
        """
        if Counter is None or Gauge is None or Histogram is None:
            raise ImportError("prometheus_client 套件未安裝")

        super().__init__(collection_interval)
        self._init_metrics()

    def _init_metrics(self) -> None:
        """初始化 API 效能指標"""
        try:
            # 請求處理時間直方圖（秒）
            self.metrics["request_duration"] = Histogram(
                "api_request_duration_seconds",
                "API 請求處理時間（秒）",
                ["method", "endpoint", "status_code"],
                buckets=[
                    0.001,
                    0.005,
                    0.01,
                    0.025,
                    0.05,
                    0.1,
                    0.25,
                    0.5,
                    1,
                    2.5,
                    5,
                    10,
                ],
                registry=self.registry,
            )

            # 請求數量計數器
            self.metrics["request_count"] = Counter(
                "api_requests_total",
                "API 請求總數",
                ["method", "endpoint", "status_code"],
                registry=self.registry,
            )

            # 錯誤數量計數器
            self.metrics["error_count"] = Counter(
                "api_errors_total",
                "API 錯誤總數",
                ["method", "endpoint", "error_type"],
                registry=self.registry,
            )

            # 活躍連接數
            self.metrics["active_connections"] = Gauge(
                "api_active_connections", "API 活躍連接數", registry=self.registry
            )

            # 請求大小（位元組）
            self.metrics["request_size"] = Histogram(
                "api_request_size_bytes",
                "API 請求大小（位元組）",
                ["method", "endpoint"],
                buckets=[64, 256, 1024, 4096, 16384, 65536, 262144, 1048576],
                registry=self.registry,
            )

            # 回應大小（位元組）
            self.metrics["response_size"] = Histogram(
                "api_response_size_bytes",
                "API 回應大小（位元組）",
                ["method", "endpoint"],
                buckets=[64, 256, 1024, 4096, 16384, 65536, 262144, 1048576],
                registry=self.registry,
            )

            # 當前 QPS
            self.metrics["current_qps"] = Gauge(
                "api_current_qps",
                "當前每秒請求數",
                ["endpoint"],
                registry=self.registry,
            )

            # 平均回應時間
            self.metrics["avg_response_time"] = Gauge(
                "api_avg_response_time_seconds",
                "平均回應時間（秒）",
                ["endpoint"],
                registry=self.registry,
            )

            # 錯誤率
            self.metrics["error_rate"] = Gauge(
                "api_error_rate_percent",
                "API 錯誤率百分比",
                ["endpoint"],
                registry=self.registry,
            )

            # 超時請求數
            self.metrics["timeout_count"] = Counter(
                "api_timeouts_total",
                "API 超時請求總數",
                ["method", "endpoint"],
                registry=self.registry,
            )

            # 限流請求數
            self.metrics["rate_limited_count"] = Counter(
                "api_rate_limited_total",
                "API 限流請求總數",
                ["endpoint"],
                registry=self.registry,
            )

            # 認證失敗數
            self.metrics["auth_failures"] = Counter(
                "api_auth_failures_total",
                "API 認證失敗總數",
                ["endpoint", "auth_type"],
                registry=self.registry,
            )

            module_logger.info("API 效能指標初始化完成")

        except Exception as e:
            module_logger.error("API 效能指標初始化失敗: %s", e)
            raise

    def _collect_metrics(self) -> None:
        """收集 API 效能指標

        Note:
            此方法需要與 API 服務整合來獲取實際數據。
            當前實現為示例，實際使用時需要連接到 API 監控數據源。
        """
        try:
            # 這裡應該從 API 服務獲取實際數據
            # 當前為示例實現
            self._collect_qps_metrics()
            self._collect_response_time_metrics()
            self._collect_error_rate_metrics()

        except Exception as e:
            module_logger.error("收集 API 效能指標時發生錯誤: %s", e)

    def _collect_qps_metrics(self) -> None:
        """收集 QPS 指標

        Note:
            需要與 API 服務整合
        """
        try:
            # 示例：這裡應該從 API 服務獲取 QPS 數據
            # 實際實現時需要替換為真實的數據源
            pass

        except Exception as e:
            module_logger.error("收集 QPS 指標失敗: %s", e)

    def _collect_response_time_metrics(self) -> None:
        """收集回應時間指標

        Note:
            需要與 API 服務整合
        """
        try:
            # 示例：這裡應該從 API 服務獲取回應時間數據
            # 實際實現時需要替換為真實的數據源
            pass

        except Exception as e:
            module_logger.error("收集回應時間指標失敗: %s", e)

    def _collect_error_rate_metrics(self) -> None:
        """收集錯誤率指標

        Note:
            需要與 API 服務整合
        """
        try:
            # 示例：這裡應該從 API 服務獲取錯誤率數據
            # 實際實現時需要替換為真實的數據源
            pass

        except Exception as e:
            module_logger.error("收集錯誤率指標失敗: %s", e)

    def record_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None,
    ) -> None:
        """記錄 API 請求

        Args:
            method: HTTP 方法
            endpoint: API 端點
            status_code: HTTP 狀態碼
            duration: 請求處理時間（秒）
            request_size: 請求大小（位元組）
            response_size: 回應大小（位元組）
        """
        try:
            # 記錄請求數量和處理時間
            self.metrics["request_count"].labels(
                method=method, endpoint=endpoint, status_code=str(status_code)
            ).inc()

            self.metrics["request_duration"].labels(
                method=method, endpoint=endpoint, status_code=str(status_code)
            ).observe(duration)

            # 記錄請求和回應大小
            if request_size is not None:
                self.metrics["request_size"].labels(
                    method=method, endpoint=endpoint
                ).observe(request_size)

            if response_size is not None:
                self.metrics["response_size"].labels(
                    method=method, endpoint=endpoint
                ).observe(response_size)

            # 記錄錯誤
            if status_code >= 400:
                error_type = self._get_error_type(status_code)
                self.metrics["error_count"].labels(
                    method=method, endpoint=endpoint, error_type=error_type
                ).inc()

        except Exception as e:
            module_logger.error("記錄 API 請求失敗: %s", e)

    def record_timeout(self, method: str, endpoint: str) -> None:
        """記錄超時請求

        Args:
            method: HTTP 方法
            endpoint: API 端點
        """
        try:
            self.metrics["timeout_count"].labels(method=method, endpoint=endpoint).inc()
        except Exception as e:
            module_logger.error("記錄超時請求失敗: %s", e)

    def record_rate_limit(self, endpoint: str) -> None:
        """記錄限流請求

        Args:
            endpoint: API 端點
        """
        try:
            self.metrics["rate_limited_count"].labels(endpoint=endpoint).inc()
        except Exception as e:
            module_logger.error("記錄限流請求失敗: %s", e)

    def record_auth_failure(self, endpoint: str, auth_type: str) -> None:
        """記錄認證失敗

        Args:
            endpoint: API 端點
            auth_type: 認證類型
        """
        try:
            self.metrics["auth_failures"].labels(
                endpoint=endpoint, auth_type=auth_type
            ).inc()
        except Exception as e:
            module_logger.error("記錄認證失敗失敗: %s", e)

    def update_active_connections(self, count: int) -> None:
        """更新活躍連接數

        Args:
            count: 活躍連接數
        """
        try:
            self.metrics["active_connections"].set(count)
        except Exception as e:
            module_logger.error("更新活躍連接數失敗: %s", e)

    def _get_error_type(self, status_code: int) -> str:
        """根據狀態碼獲取錯誤類型

        Args:
            status_code: HTTP 狀態碼

        Returns:
            str: 錯誤類型
        """
        if 400 <= status_code < 500:
            return "client_error"
        elif 500 <= status_code < 600:
            return "server_error"
        else:
            return "unknown_error"
