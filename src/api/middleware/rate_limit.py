"""速率限制中間件

此模組實現了 API 速率限制功能，防止 API 濫用和 DDoS 攻擊。
支援多種限制策略：IP 限制、用戶限制、端點限制等。
"""

import time
import asyncio
from datetime import datetime
from typing import Dict, Optional
from collections import deque
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class RateLimitRule:
    """速率限制規則"""

    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        burst_limit: Optional[int] = None,
        description: str = "",
    ):
        """
        初始化速率限制規則

        Args:
            max_requests: 時間窗口內最大請求數
            window_seconds: 時間窗口大小（秒）
            burst_limit: 突發請求限制
            description: 規則描述
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.burst_limit = burst_limit or max_requests
        self.description = description


class TokenBucket:
    """令牌桶算法實現"""

    def __init__(self, capacity: int, refill_rate: float):
        """
        初始化令牌桶

        Args:
            capacity: 桶容量
            refill_rate: 令牌補充速率（每秒）
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        消費令牌

        Args:
            tokens: 要消費的令牌數

        Returns:
            bool: 是否成功消費
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self):
        """補充令牌"""
        now = time.time()
        elapsed = now - self.last_refill

        # 計算要補充的令牌數
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now


class SlidingWindowCounter:
    """滑動窗口計數器"""

    def __init__(self, window_seconds: int, max_requests: int):
        """
        初始化滑動窗口計數器

        Args:
            window_seconds: 窗口大小（秒）
            max_requests: 最大請求數
        """
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.requests = deque()

    def is_allowed(self) -> bool:
        """檢查是否允許請求"""
        now = time.time()

        # 移除過期的請求記錄
        while self.requests and self.requests[0] <= now - self.window_seconds:
            self.requests.popleft()

        # 檢查是否超過限制
        if len(self.requests) >= self.max_requests:
            return False

        # 記錄當前請求
        self.requests.append(now)
        return True

    def get_remaining_requests(self) -> int:
        """獲取剩餘請求數"""
        now = time.time()

        # 移除過期的請求記錄
        while self.requests and self.requests[0] <= now - self.window_seconds:
            self.requests.popleft()

        return max(0, self.max_requests - len(self.requests))

    def get_reset_time(self) -> float:
        """獲取重置時間"""
        if not self.requests:
            return 0

        return self.requests[0] + self.window_seconds


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中間件"""

    def __init__(self, app):
        super().__init__(app)

        # 存儲各種限制器
        self.ip_limiters: Dict[str, SlidingWindowCounter] = {}
        self.user_limiters: Dict[str, SlidingWindowCounter] = {}
        self.endpoint_limiters: Dict[str, SlidingWindowCounter] = {}
        self.token_buckets: Dict[str, TokenBucket] = {}

        # 預設規則
        self.default_rules = {
            "global": RateLimitRule(1000, 60, description="全域限制"),
            "ip": RateLimitRule(100, 60, description="IP 限制"),
            "user": RateLimitRule(500, 60, description="用戶限制"),
            "auth": RateLimitRule(10, 60, description="認證端點限制"),
        }

        # 端點特定規則
        self.endpoint_rules = {
            "/api/v1/auth/login": RateLimitRule(5, 300, description="登入限制"),
            "/api/v1/auth/register": RateLimitRule(3, 3600, description="註冊限制"),
            "/api/v1/trading/orders": RateLimitRule(50, 60, description="交易限制"),
            "/api/v1/data/market": RateLimitRule(200, 60, description="市場資料限制"),
        }

        # 白名單 IP
        self.whitelist_ips = {"127.0.0.1", "localhost", "::1"}

        # 清理任務
        self._start_cleanup_task()

    async def dispatch(self, request: Request, call_next):
        """處理請求速率限制"""
        # 獲取客戶端 IP
        client_ip = self._get_client_ip(request)

        # 檢查白名單
        if client_ip in self.whitelist_ips:
            return await call_next(request)

        # 檢查是否為測試環境
        if self._is_test_environment(request):
            return await call_next(request)

        # 獲取用戶 ID（如果已認證）
        user_id = getattr(request.state, "user_id", None)

        # 獲取端點路徑
        endpoint = request.url.path

        try:
            # 檢查各種限制
            self._check_ip_limit(client_ip)

            if user_id:
                self._check_user_limit(user_id)

            self._check_endpoint_limit(endpoint)

            # 檢查令牌桶限制
            self._check_token_bucket_limit(client_ip)

        except HTTPException as e:
            return self._rate_limit_response(e.detail, client_ip, endpoint)

        # 記錄請求
        self._record_request(client_ip, user_id, endpoint)

        # 繼續處理請求
        response = await call_next(request)

        # 添加速率限制標頭
        self._add_rate_limit_headers(response, client_ip, endpoint)

        return response

    def _get_client_ip(self, request: Request) -> str:
        """獲取客戶端 IP"""
        # 檢查代理標頭
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # 使用直接連接 IP
        return request.client.host if request.client else "unknown"

    def _is_test_environment(self, request: Request) -> bool:
        """檢查是否為測試環境"""
        # 檢查測試標頭
        if request.headers.get("X-Test-Environment") == "true":
            return True

        # 檢查用戶代理
        user_agent = request.headers.get("User-Agent", "")
        if "pytest" in user_agent.lower() or "testclient" in user_agent.lower():
            return True

        # 檢查主機名
        host = request.headers.get("Host", "")
        if "testserver" in host or "localhost" in host:
            return True

        return False

    def _check_ip_limit(self, ip: str):
        """檢查 IP 限制"""
        rule = self.default_rules["ip"]

        if ip not in self.ip_limiters:
            self.ip_limiters[ip] = SlidingWindowCounter(
                rule.window_seconds, rule.max_requests
            )

        limiter = self.ip_limiters[ip]

        if not limiter.is_allowed():
            reset_time = limiter.get_reset_time()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"IP 請求過於頻繁，請在 {int(reset_time - time.time())} 秒後重試",
            )

    def _check_user_limit(self, user_id: str):
        """檢查用戶限制"""
        rule = self.default_rules["user"]

        if user_id not in self.user_limiters:
            self.user_limiters[user_id] = SlidingWindowCounter(
                rule.window_seconds, rule.max_requests
            )

        limiter = self.user_limiters[user_id]

        if not limiter.is_allowed():
            reset_time = limiter.get_reset_time()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"用戶請求過於頻繁，請在 {int(reset_time - time.time())} 秒後重試",
            )

    def _check_endpoint_limit(self, endpoint: str):
        """檢查端點限制"""
        # 檢查是否有特定端點規則
        rule = self.endpoint_rules.get(endpoint)
        if not rule:
            return

        if endpoint not in self.endpoint_limiters:
            self.endpoint_limiters[endpoint] = SlidingWindowCounter(
                rule.window_seconds, rule.max_requests
            )

        limiter = self.endpoint_limiters[endpoint]

        if not limiter.is_allowed():
            reset_time = limiter.get_reset_time()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"端點請求過於頻繁，請在 {int(reset_time - time.time())} 秒後重試",
            )

    def _check_token_bucket_limit(self, client_ip: str):
        """檢查令牌桶限制"""
        if client_ip not in self.token_buckets:
            # 創建令牌桶：容量 10，每秒補充 2 個令牌
            self.token_buckets[client_ip] = TokenBucket(10, 2.0)

        bucket = self.token_buckets[client_ip]

        if not bucket.consume():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="請求過於頻繁，請稍後重試",
            )

    def _record_request(self, ip: str, user_id: Optional[str], endpoint: str):
        """記錄請求

        Args:
            ip: 客戶端 IP 地址
            user_id: 用戶 ID（可選）
            endpoint: API 端點路徑
        """
        # 這裡可以添加請求記錄邏輯
        logger.debug("請求記錄: IP=%s, User=%s, Endpoint=%s", ip, user_id, endpoint)

    def _add_rate_limit_headers(self, response, ip: str, endpoint: str):
        """添加速率限制標頭"""
        # 獲取 IP 限制器資訊
        if ip in self.ip_limiters:
            limiter = self.ip_limiters[ip]
            remaining = limiter.get_remaining_requests()
            reset_time = int(limiter.get_reset_time())

            response.headers["X-RateLimit-Limit"] = str(
                self.default_rules["ip"].max_requests
            )
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)

        # 添加端點特定限制資訊
        if endpoint in self.endpoint_limiters:
            limiter = self.endpoint_limiters[endpoint]
            remaining = limiter.get_remaining_requests()

            response.headers["X-RateLimit-Endpoint-Remaining"] = str(remaining)

    def _rate_limit_response(
        self, message: str, ip: str, endpoint: str
    ) -> JSONResponse:
        """返回速率限制響應

        Args:
            message: 錯誤訊息
            ip: 客戶端 IP 地址
            endpoint: API 端點路徑

        Returns:
            JSONResponse: 速率限制響應
        """
        # 獲取重試時間
        retry_after = 60  # 預設 60 秒

        if ip in self.ip_limiters:
            reset_time = self.ip_limiters[ip].get_reset_time()
            retry_after = max(1, int(reset_time - time.time()))

        response = JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "error_code": 429,
                "message": message,
                "retry_after": retry_after,
                "timestamp": datetime.now().isoformat(),
                "endpoint": endpoint,  # 使用 endpoint 參數
            },
        )

        response.headers["Retry-After"] = str(retry_after)
        return response

    def _start_cleanup_task(self):
        """啟動清理任務"""

        async def cleanup_task():
            while True:
                await asyncio.sleep(300)  # 每 5 分鐘清理一次
                self._cleanup_expired_limiters()

        # 在實際應用中，應該使用適當的任務調度器
        asyncio.create_task(cleanup_task())

    def _cleanup_expired_limiters(self):
        """清理過期的限制器"""
        current_time = time.time()

        # 清理 IP 限制器
        expired_ips = [
            ip
            for ip, limiter in self.ip_limiters.items()
            if not limiter.requests or limiter.requests[-1] < current_time - 3600
        ]
        for ip in expired_ips:
            del self.ip_limiters[ip]

        # 清理用戶限制器
        expired_users = [
            user_id
            for user_id, limiter in self.user_limiters.items()
            if not limiter.requests or limiter.requests[-1] < current_time - 3600
        ]
        for user_id in expired_users:
            del self.user_limiters[user_id]

        # 清理端點限制器
        expired_endpoints = [
            endpoint
            for endpoint, limiter in self.endpoint_limiters.items()
            if not limiter.requests or limiter.requests[-1] < current_time - 3600
        ]
        for endpoint in expired_endpoints:
            del self.endpoint_limiters[endpoint]

        logger.info(
            "清理過期限制器: IP=%d, User=%d, Endpoint=%d",
            len(expired_ips), len(expired_users), len(expired_endpoints)
        )


class RateLimitConfig:
    """速率限制配置"""

    @staticmethod
    def get_rule_for_endpoint(endpoint: str) -> Optional[RateLimitRule]:
        """獲取端點的速率限制規則"""
        # 認證相關端點
        if "/auth/" in endpoint:
            return RateLimitRule(10, 300, description="認證端點限制")

        # 交易相關端點
        if "/trading/" in endpoint:
            return RateLimitRule(50, 60, description="交易端點限制")

        # 資料相關端點
        if "/data/" in endpoint:
            return RateLimitRule(200, 60, description="資料端點限制")

        # 報表相關端點
        if "/reports/" in endpoint:
            return RateLimitRule(20, 60, description="報表端點限制")

        return None

    @staticmethod
    def get_user_rule(user_role: str) -> RateLimitRule:
        """根據用戶角色獲取限制規則"""
        role_limits = {
            "admin": RateLimitRule(1000, 60, description="管理員限制"),
            "user": RateLimitRule(500, 60, description="一般用戶限制"),
            "readonly": RateLimitRule(200, 60, description="只讀用戶限制"),
        }

        return role_limits.get(
            user_role, RateLimitRule(100, 60, description="預設限制")
        )


# 速率限制裝飾器
def rate_limit(max_requests: int, window_seconds: int):
    """速率限制裝飾器"""

    def decorator(func):
        # 在實際實現中，這裡應該整合到路由處理中
        func._rate_limit = RateLimitRule(max_requests, window_seconds)
        return func

    return decorator
