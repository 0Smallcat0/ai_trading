"""
負載測試工具

此模組提供併發負載測試功能，模擬多用戶同時訪問 API。
"""

import asyncio
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from fastapi.testclient import TestClient

from .performance_monitor import PerformanceResult


@dataclass
class LoadTestConfig:
    """負載測試配置"""

    concurrent_users: int = 10
    test_duration: int = 60  # seconds
    ramp_up_time: int = 10  # seconds
    requests_per_user: Optional[int] = None
    think_time: float = 1.0  # seconds between requests
    timeout: float = 30.0  # request timeout


@dataclass
class UserSession:
    """用戶會話"""

    user_id: int
    start_time: datetime
    requests_sent: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    errors: List[str] = field(default_factory=list)


class LoadTester:
    """負載測試器類"""

    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        """
        初始化負載測試器

        Args:
            base_url: API 基礎 URL
        """
        self.base_url = base_url
        self.user_sessions: List[UserSession] = []
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def run_load_test(
        self,
        test_scenarios: List[Dict[str, Any]],
        config: LoadTestConfig,
        auth_headers: Optional[Dict[str, str]] = None,
    ) -> PerformanceResult:
        """
        執行負載測試

        Args:
            test_scenarios: 測試場景列表
            config: 負載測試配置
            auth_headers: 認證標頭

        Returns:
            PerformanceResult: 測試結果
        """
        self.is_running = True
        self.start_time = datetime.now()
        self.user_sessions = []

        # 使用線程池執行併發測試
        with ThreadPoolExecutor(max_workers=config.concurrent_users) as executor:
            futures = []

            # 逐步增加用戶負載（ramp-up）
            for user_id in range(config.concurrent_users):
                # 計算用戶啟動延遲
                delay = (user_id * config.ramp_up_time) / config.concurrent_users

                future = executor.submit(
                    self._simulate_user,
                    user_id,
                    test_scenarios,
                    config,
                    auth_headers,
                    delay,
                )
                futures.append(future)

            # 等待所有用戶完成
            for future in as_completed(futures):
                try:
                    user_session = future.result()
                    self.user_sessions.append(user_session)
                except Exception as e:
                    print(f"用戶模擬失敗: {e}")

        self.end_time = datetime.now()
        self.is_running = False

        return self._generate_load_test_result()

    def _simulate_user(
        self,
        user_id: int,
        test_scenarios: List[Dict[str, Any]],
        config: LoadTestConfig,
        auth_headers: Optional[Dict[str, str]],
        start_delay: float,
    ) -> UserSession:
        """
        模擬單個用戶行為

        Args:
            user_id: 用戶 ID
            test_scenarios: 測試場景
            config: 測試配置
            auth_headers: 認證標頭
            start_delay: 啟動延遲

        Returns:
            UserSession: 用戶會話結果
        """
        # 等待啟動延遲
        time.sleep(start_delay)

        session = UserSession(user_id=user_id, start_time=datetime.now())

        # 使用全局 app 實例
        from src.api.main import app

        with TestClient(app) as client:
            test_end_time = session.start_time.timestamp() + config.test_duration
            scenario_index = 0

            while datetime.now().timestamp() < test_end_time and (
                config.requests_per_user is None
                or session.requests_sent < config.requests_per_user
            ):

                try:
                    # 選擇測試場景
                    scenario = test_scenarios[scenario_index % len(test_scenarios)]
                    scenario_index += 1

                    # 執行請求
                    response_time = self._execute_request(
                        client, scenario, auth_headers
                    )

                    session.requests_sent += 1
                    session.successful_requests += 1
                    session.total_response_time += response_time

                except Exception as e:
                    session.requests_sent += 1
                    session.failed_requests += 1
                    session.errors.append(str(e))

                # 思考時間
                if config.think_time > 0:
                    time.sleep(config.think_time)

        return session

    def _execute_request(
        self,
        client: TestClient,
        scenario: Dict[str, Any],
        auth_headers: Optional[Dict[str, str]],
    ) -> float:
        """
        執行單個請求

        Args:
            client: 測試客戶端
            scenario: 測試場景
            auth_headers: 認證標頭

        Returns:
            float: 回應時間（毫秒）
        """
        start_time = time.time()

        method = scenario.get("method", "GET").upper()
        url = scenario.get("url", "/")
        headers = {**(auth_headers or {}), **scenario.get("headers", {})}
        json_data = scenario.get("json", None)
        params = scenario.get("params", None)

        if method == "GET":
            response = client.get(url, headers=headers, params=params)
        elif method == "POST":
            response = client.post(url, headers=headers, json=json_data, params=params)
        elif method == "PUT":
            response = client.put(url, headers=headers, json=json_data, params=params)
        elif method == "DELETE":
            response = client.delete(url, headers=headers, params=params)
        else:
            raise ValueError(f"不支援的 HTTP 方法: {method}")

        response_time = (time.time() - start_time) * 1000  # ms

        # 檢查回應狀態
        if response.status_code >= 400:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        return response_time

    async def run_async_load_test(
        self,
        test_scenarios: List[Dict[str, Any]],
        config: LoadTestConfig,
        auth_headers: Optional[Dict[str, str]] = None,
    ) -> PerformanceResult:
        """
        執行異步負載測試

        Args:
            test_scenarios: 測試場景列表
            config: 負載測試配置
            auth_headers: 認證標頭

        Returns:
            PerformanceResult: 測試結果
        """
        self.is_running = True
        self.start_time = datetime.now()
        self.user_sessions = []

        # 創建異步任務
        tasks = []
        for user_id in range(config.concurrent_users):
            delay = (user_id * config.ramp_up_time) / config.concurrent_users
            task = asyncio.create_task(
                self._simulate_async_user(
                    user_id, test_scenarios, config, auth_headers, delay
                )
            )
            tasks.append(task)

        # 等待所有任務完成
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, UserSession):
                self.user_sessions.append(result)
            elif isinstance(result, Exception):
                print(f"異步用戶模擬失敗: {result}")

        self.end_time = datetime.now()
        self.is_running = False

        return self._generate_load_test_result()

    async def _simulate_async_user(
        self,
        user_id: int,
        test_scenarios: List[Dict[str, Any]],
        config: LoadTestConfig,
        auth_headers: Optional[Dict[str, str]],
        start_delay: float,
    ) -> UserSession:
        """
        模擬異步用戶行為

        Args:
            user_id: 用戶 ID
            test_scenarios: 測試場景
            config: 測試配置
            auth_headers: 認證標頭
            start_delay: 啟動延遲

        Returns:
            UserSession: 用戶會話結果
        """
        await asyncio.sleep(start_delay)

        session = UserSession(user_id=user_id, start_time=datetime.now())

        async with httpx.AsyncClient(base_url=self.base_url) as client:
            test_end_time = session.start_time.timestamp() + config.test_duration
            scenario_index = 0

            while datetime.now().timestamp() < test_end_time and (
                config.requests_per_user is None
                or session.requests_sent < config.requests_per_user
            ):

                try:
                    scenario = test_scenarios[scenario_index % len(test_scenarios)]
                    scenario_index += 1

                    response_time = await self._execute_async_request(
                        client, scenario, auth_headers
                    )

                    session.requests_sent += 1
                    session.successful_requests += 1
                    session.total_response_time += response_time

                except Exception as e:
                    session.requests_sent += 1
                    session.failed_requests += 1
                    session.errors.append(str(e))

                if config.think_time > 0:
                    await asyncio.sleep(config.think_time)

        return session

    async def _execute_async_request(
        self,
        client: httpx.AsyncClient,
        scenario: Dict[str, Any],
        auth_headers: Optional[Dict[str, str]],
    ) -> float:
        """
        執行異步請求

        Args:
            client: 異步客戶端
            scenario: 測試場景
            auth_headers: 認證標頭

        Returns:
            float: 回應時間（毫秒）
        """
        start_time = time.time()

        method = scenario.get("method", "GET").upper()
        url = scenario.get("url", "/")
        headers = {**(auth_headers or {}), **scenario.get("headers", {})}
        json_data = scenario.get("json", None)
        params = scenario.get("params", None)

        if method == "GET":
            response = await client.get(url, headers=headers, params=params)
        elif method == "POST":
            response = await client.post(
                url, headers=headers, json=json_data, params=params
            )
        elif method == "PUT":
            response = await client.put(
                url, headers=headers, json=json_data, params=params
            )
        elif method == "DELETE":
            response = await client.delete(url, headers=headers, params=params)
        else:
            raise ValueError(f"不支援的 HTTP 方法: {method}")

        response_time = (time.time() - start_time) * 1000  # ms

        if response.status_code >= 400:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        return response_time

    def _generate_load_test_result(self) -> PerformanceResult:
        """生成負載測試結果"""
        if not self.start_time or not self.end_time:
            raise ValueError("測試尚未完成")

        duration = (self.end_time - self.start_time).total_seconds()

        # 聚合所有用戶會話的統計
        total_requests = sum(session.requests_sent for session in self.user_sessions)
        successful_requests = sum(
            session.successful_requests for session in self.user_sessions
        )
        failed_requests = sum(session.failed_requests for session in self.user_sessions)

        # 計算回應時間統計
        all_response_times = []
        all_errors = []

        for session in self.user_sessions:
            if session.successful_requests > 0:
                avg_session_time = (
                    session.total_response_time / session.successful_requests
                )
                all_response_times.extend(
                    [avg_session_time] * session.successful_requests
                )
            all_errors.extend(session.errors)

        if all_response_times:
            avg_response_time = sum(all_response_times) / len(all_response_times)
            min_response_time = min(all_response_times)
            max_response_time = max(all_response_times)
            sorted_times = sorted(all_response_times)
            p95_response_time = sorted_times[int(len(sorted_times) * 0.95)]
            p99_response_time = sorted_times[int(len(sorted_times) * 0.99)]
        else:
            avg_response_time = min_response_time = max_response_time = 0
            p95_response_time = p99_response_time = 0

        throughput = total_requests / duration if duration > 0 else 0

        return PerformanceResult(
            test_name="Load Test",
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
            avg_memory_usage=0,  # 在負載測試中不監控記憶體
            max_memory_usage=0,
            avg_cpu_usage=0,
            max_cpu_usage=0,
            errors=all_errors,
        )
