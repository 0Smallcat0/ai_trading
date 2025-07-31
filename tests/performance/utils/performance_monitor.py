"""
效能監控器

此模組提供 API 效能監控功能，包括回應時間測量、資源使用監控等。
"""

import asyncio
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from contextlib import contextmanager
import statistics

import httpx
from fastapi.testclient import TestClient


@dataclass
class PerformanceMetrics:
    """效能指標資料類"""

    response_time: float = 0.0
    memory_usage: float = 0.0
    cpu_usage: float = 0.0
    request_count: int = 0
    error_count: int = 0
    throughput: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PerformanceResult:
    """效能測試結果"""

    test_name: str
    duration: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput: float
    avg_memory_usage: float
    max_memory_usage: float
    avg_cpu_usage: float
    max_cpu_usage: float
    errors: List[str] = field(default_factory=list)


class PerformanceMonitor:
    """效能監控器類"""

    def __init__(self):
        """初始化效能監控器"""
        self.metrics_history: List[PerformanceMetrics] = []
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.start_time: Optional[datetime] = None
        self.response_times: List[float] = []
        self.memory_readings: List[float] = []
        self.cpu_readings: List[float] = []
        self.error_messages: List[str] = []

    def start_monitoring(self, interval: float = 1.0):
        """
        開始效能監控

        Args:
            interval: 監控間隔（秒）
        """
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.start_time = datetime.now()
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, args=(interval,), daemon=True
        )
        self.monitor_thread.start()

    def stop_monitoring(self) -> PerformanceResult:
        """
        停止效能監控並返回結果

        Returns:
            PerformanceResult: 效能測試結果
        """
        self.is_monitoring = False

        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)

        return self._generate_result()

    def _monitor_loop(self, interval: float):
        """監控循環"""
        process = psutil.Process()

        while self.is_monitoring:
            try:
                # 收集系統指標
                memory_usage = process.memory_info().rss / 1024 / 1024  # MB
                cpu_usage = process.cpu_percent()

                self.memory_readings.append(memory_usage)
                self.cpu_readings.append(cpu_usage)

                # 創建指標記錄
                metrics = PerformanceMetrics(
                    memory_usage=memory_usage,
                    cpu_usage=cpu_usage,
                    request_count=len(self.response_times),
                    error_count=len(self.error_messages),
                )
                self.metrics_history.append(metrics)

                time.sleep(interval)

            except Exception as e:
                self.error_messages.append(f"監控錯誤: {str(e)}")

    @contextmanager
    def measure_request(self):
        """
        測量單個請求的效能

        使用方法:
            with monitor.measure_request():
                response = client.get("/api/endpoint")
        """
        start_time = time.time()
        try:
            yield
            response_time = (time.time() - start_time) * 1000  # ms
            self.response_times.append(response_time)
        except Exception as e:
            response_time = (time.time() - start_time) * 1000  # ms
            self.response_times.append(response_time)
            self.error_messages.append(str(e))
            raise

    def measure_api_response_time(
        self,
        client: TestClient,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        測量 API 回應時間

        Args:
            client: 測試客戶端
            method: HTTP 方法
            url: API 端點
            headers: 請求標頭
            json_data: JSON 資料
            params: 查詢參數

        Returns:
            float: 回應時間（毫秒）
        """
        with self.measure_request():
            if method.upper() == "GET":
                response = client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = client.post(
                    url, headers=headers, json=json_data, params=params
                )
            elif method.upper() == "PUT":
                response = client.put(
                    url, headers=headers, json=json_data, params=params
                )
            elif method.upper() == "DELETE":
                response = client.delete(url, headers=headers, params=params)
            else:
                raise ValueError(f"不支援的 HTTP 方法: {method}")

        return self.response_times[-1] if self.response_times else 0.0

    async def measure_async_api_response_time(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        測量異步 API 回應時間

        Args:
            client: 異步客戶端
            method: HTTP 方法
            url: API 端點
            headers: 請求標頭
            json_data: JSON 資料
            params: 查詢參數

        Returns:
            float: 回應時間（毫秒）
        """
        start_time = time.time()
        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                response = await client.post(
                    url, headers=headers, json=json_data, params=params
                )
            elif method.upper() == "PUT":
                response = await client.put(
                    url, headers=headers, json=json_data, params=params
                )
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers, params=params)
            else:
                raise ValueError(f"不支援的 HTTP 方法: {method}")

            response_time = (time.time() - start_time) * 1000  # ms
            self.response_times.append(response_time)
            return response_time

        except Exception as e:
            response_time = (time.time() - start_time) * 1000  # ms
            self.response_times.append(response_time)
            self.error_messages.append(str(e))
            raise

    def _generate_result(self) -> PerformanceResult:
        """生成效能測試結果"""
        if not self.start_time:
            raise ValueError("監控尚未開始")

        duration = (datetime.now() - self.start_time).total_seconds()
        total_requests = len(self.response_times)
        failed_requests = len(self.error_messages)
        successful_requests = total_requests - failed_requests

        # 計算回應時間統計
        if self.response_times:
            avg_response_time = statistics.mean(self.response_times)
            min_response_time = min(self.response_times)
            max_response_time = max(self.response_times)
            sorted_times = sorted(self.response_times)
            p95_response_time = (
                sorted_times[int(len(sorted_times) * 0.95)] if sorted_times else 0
            )
            p99_response_time = (
                sorted_times[int(len(sorted_times) * 0.99)] if sorted_times else 0
            )
        else:
            avg_response_time = min_response_time = max_response_time = 0
            p95_response_time = p99_response_time = 0

        # 計算吞吐量
        throughput = total_requests / duration if duration > 0 else 0

        # 計算資源使用統計
        avg_memory_usage = (
            statistics.mean(self.memory_readings) if self.memory_readings else 0
        )
        max_memory_usage = max(self.memory_readings) if self.memory_readings else 0
        avg_cpu_usage = statistics.mean(self.cpu_readings) if self.cpu_readings else 0
        max_cpu_usage = max(self.cpu_readings) if self.cpu_readings else 0

        return PerformanceResult(
            test_name="Performance Test",
            duration=duration,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            throughput=throughput,
            avg_memory_usage=avg_memory_usage,
            max_memory_usage=max_memory_usage,
            avg_cpu_usage=avg_cpu_usage,
            max_cpu_usage=max_cpu_usage,
            errors=self.error_messages.copy(),
        )

    def reset(self):
        """重置監控器狀態"""
        self.metrics_history.clear()
        self.response_times.clear()
        self.memory_readings.clear()
        self.cpu_readings.clear()
        self.error_messages.clear()
        self.start_time = None
        self.is_monitoring = False
