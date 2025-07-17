# -*- coding: utf-8 -*-
"""
速率限制和成本控制模組

此模組提供智能的速率限制和成本控制機制。

主要功能：
- 多層級速率限制
- 動態速率調整
- 成本監控和預算控制
- 使用配額管理
- 智能流量整形
"""

import logging
import time
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
from collections import deque
import threading

# 設定日誌
logger = logging.getLogger(__name__)


class LimitType(Enum):
    """限制類型枚舉"""
    REQUESTS_PER_SECOND = "requests_per_second"
    REQUESTS_PER_MINUTE = "requests_per_minute"
    REQUESTS_PER_HOUR = "requests_per_hour"
    REQUESTS_PER_DAY = "requests_per_day"
    TOKENS_PER_MINUTE = "tokens_per_minute"
    TOKENS_PER_HOUR = "tokens_per_hour"
    COST_PER_HOUR = "cost_per_hour"
    COST_PER_DAY = "cost_per_day"
    COST_PER_MONTH = "cost_per_month"


class PriorityLevel(Enum):
    """優先級等級枚舉"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class RateLimit:
    """速率限制配置"""
    limit_type: LimitType
    limit_value: float
    window_size: int  # 時間窗口大小（秒）
    burst_allowance: float = 0.0  # 突發允許量
    priority_multiplier: Dict[PriorityLevel, float] = None


@dataclass
class CostBudget:
    """成本預算配置"""
    daily_budget: float
    monthly_budget: float
    alert_threshold: float = 0.8  # 警告閾值
    hard_limit_threshold: float = 0.95  # 硬限制閾值


@dataclass
class UsageRecord:
    """使用記錄"""
    timestamp: datetime
    request_count: int = 0
    token_count: int = 0
    cost: float = 0.0
    priority: PriorityLevel = PriorityLevel.NORMAL
    provider: str = ""
    model: str = ""


class RateLimitExceededError(Exception):
    """速率限制超出錯誤"""
    
    def __init__(self, message: str, retry_after: float = 0.0):
        super().__init__(message)
        self.retry_after = retry_after


class BudgetExceededError(Exception):
    """預算超出錯誤"""


class TokenBucket:
    """令牌桶算法實現"""

    def __init__(self, capacity: float, refill_rate: float):
        """初始化令牌桶。

        Args:
            capacity: 桶容量
            refill_rate: 填充速率（令牌/秒）
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
        self._lock = threading.Lock()

    def consume(self, tokens: float = 1.0) -> bool:
        """消費令牌。

        Args:
            tokens: 需要消費的令牌數

        Returns:
            是否成功消費
        """
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            else:
                return False

    def wait_time(self, tokens: float = 1.0) -> float:
        """計算等待時間。

        Args:
            tokens: 需要的令牌數

        Returns:
            等待時間（秒）
        """
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                return 0.0
            
            needed_tokens = tokens - self.tokens
            return needed_tokens / self.refill_rate

    def _refill(self) -> None:
        """填充令牌。"""
        now = time.time()
        time_passed = now - self.last_refill
        
        new_tokens = time_passed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_refill = now

    def get_status(self) -> Dict[str, Any]:
        """獲取狀態。

        Returns:
            狀態信息字典
        """
        with self._lock:
            self._refill()
            return {
                'capacity': self.capacity,
                'current_tokens': self.tokens,
                'refill_rate': self.refill_rate,
                'utilization': 1.0 - (self.tokens / self.capacity)
            }


class SlidingWindowCounter:
    """滑動窗口計數器"""

    def __init__(self, window_size: int, bucket_count: int = 60):
        """初始化滑動窗口計數器。

        Args:
            window_size: 窗口大小（秒）
            bucket_count: 桶數量
        """
        self.window_size = window_size
        self.bucket_count = bucket_count
        self.bucket_duration = window_size / bucket_count
        self.buckets = deque(maxlen=bucket_count)
        self.last_update = time.time()
        self._lock = threading.Lock()

    def add(self, value: float = 1.0) -> None:
        """添加計數。

        Args:
            value: 計數值
        """
        with self._lock:
            self._update_buckets()
            
            if self.buckets:
                self.buckets[-1]['count'] += value
            else:
                self.buckets.append({
                    'timestamp': time.time(),
                    'count': value
                })

    def get_count(self) -> float:
        """獲取當前窗口內的總計數。

        Returns:
            總計數
        """
        with self._lock:
            self._update_buckets()
            return sum(bucket['count'] for bucket in self.buckets)

    def _update_buckets(self) -> None:
        """更新桶。"""
        now = time.time()
        
        # 計算需要添加的新桶數量
        time_passed = now - self.last_update
        new_buckets_needed = int(time_passed / self.bucket_duration)
        
        if new_buckets_needed > 0:
            # 添加新桶
            for _ in range(min(new_buckets_needed, self.bucket_count)):
                self.buckets.append({
                    'timestamp': now,
                    'count': 0.0
                })
            
            self.last_update = now

    def get_rate(self) -> float:
        """獲取當前速率。

        Returns:
            速率（計數/秒）
        """
        count = self.get_count()
        return count / self.window_size


class RateLimiter:
    """速率限制器"""

    def __init__(self, limits: List[RateLimit]):
        """初始化速率限制器。

        Args:
            limits: 速率限制列表
        """
        self.limits = limits
        self.token_buckets = {}
        self.sliding_windows = {}
        
        # 初始化令牌桶和滑動窗口
        for limit in limits:
            if limit.limit_type in [LimitType.REQUESTS_PER_SECOND]:
                # 使用令牌桶
                self.token_buckets[limit.limit_type] = TokenBucket(
                    capacity=limit.limit_value + limit.burst_allowance,
                    refill_rate=limit.limit_value
                )
            else:
                # 使用滑動窗口
                self.sliding_windows[limit.limit_type] = SlidingWindowCounter(
                    window_size=limit.window_size
                )

    async def acquire(
        self,
        request_count: int = 1,
        token_count: int = 0,
        priority: PriorityLevel = PriorityLevel.NORMAL
    ) -> None:
        """獲取許可。

        Args:
            request_count: 請求數量
            token_count: 令牌數量
            priority: 優先級

        Raises:
            RateLimitExceededError: 當超過速率限制時
        """
        max_wait_time = 0.0
        
        # 檢查所有限制
        for limit in self.limits:
            wait_time = self._check_limit(limit, request_count, token_count, priority)
            max_wait_time = max(max_wait_time, wait_time)
        
        # 如果需要等待
        if max_wait_time > 0:
            if max_wait_time > 60:  # 超過1分鐘則拒絕
                raise RateLimitExceededError(
                    f"速率限制超出，需等待 {max_wait_time:.2f} 秒",
                    retry_after=max_wait_time
                )
            
            logger.info(f"速率限制，等待 {max_wait_time:.2f} 秒")
            await asyncio.sleep(max_wait_time)
        
        # 消費資源
        self._consume_resources(request_count, token_count)

    def _check_limit(
        self,
        limit: RateLimit,
        request_count: int,
        token_count: int,
        priority: PriorityLevel
    ) -> float:
        """檢查單個限制。

        Args:
            limit: 速率限制
            request_count: 請求數量
            token_count: 令牌數量
            priority: 優先級

        Returns:
            等待時間（秒）
        """
        # 根據優先級調整限制
        priority_multiplier = 1.0
        if limit.priority_multiplier and priority in limit.priority_multiplier:
            priority_multiplier = limit.priority_multiplier[priority]
        
        effective_limit = limit.limit_value * priority_multiplier
        
        # 確定消費量
        if limit.limit_type in [
            LimitType.REQUESTS_PER_SECOND,
            LimitType.REQUESTS_PER_MINUTE,
            LimitType.REQUESTS_PER_HOUR,
            LimitType.REQUESTS_PER_DAY
        ]:
            consumption = request_count
        elif limit.limit_type in [
            LimitType.TOKENS_PER_MINUTE,
            LimitType.TOKENS_PER_HOUR
        ]:
            consumption = token_count
        else:
            consumption = 0
        
        # 檢查令牌桶
        if limit.limit_type in self.token_buckets:
            bucket = self.token_buckets[limit.limit_type]
            if not bucket.consume(consumption):
                return bucket.wait_time(consumption)
        
        # 檢查滑動窗口
        if limit.limit_type in self.sliding_windows:
            window = self.sliding_windows[limit.limit_type]
            current_count = window.get_count()
            
            if current_count + consumption > effective_limit:
                # 計算等待時間
                excess = current_count + consumption - effective_limit
                wait_time = excess / (effective_limit / limit.window_size)
                return wait_time
        
        return 0.0

    def _consume_resources(self, request_count: int, token_count: int) -> None:
        """消費資源。

        Args:
            request_count: 請求數量
            token_count: 令牌數量
        """
        # 更新滑動窗口
        for limit in self.limits:
            if limit.limit_type in self.sliding_windows:
                window = self.sliding_windows[limit.limit_type]
                
                if limit.limit_type in [
                    LimitType.REQUESTS_PER_MINUTE,
                    LimitType.REQUESTS_PER_HOUR,
                    LimitType.REQUESTS_PER_DAY
                ]:
                    window.add(request_count)
                elif limit.limit_type in [
                    LimitType.TOKENS_PER_MINUTE,
                    LimitType.TOKENS_PER_HOUR
                ]:
                    window.add(token_count)

    def get_status(self) -> Dict[str, Any]:
        """獲取狀態。

        Returns:
            狀態信息字典
        """
        status = {
            'token_buckets': {},
            'sliding_windows': {}
        }
        
        # 令牌桶狀態
        for limit_type, bucket in self.token_buckets.items():
            status['token_buckets'][limit_type.value] = bucket.get_status()
        
        # 滑動窗口狀態
        for limit_type, window in self.sliding_windows.items():
            status['sliding_windows'][limit_type.value] = {
                'current_count': window.get_count(),
                'current_rate': window.get_rate(),
                'window_size': window.window_size
            }
        
        return status


class CostController:
    """成本控制器"""

    def __init__(self, budget: CostBudget):
        """初始化成本控制器。

        Args:
            budget: 成本預算
        """
        self.budget = budget
        self.usage_records = []
        self.daily_cost = 0.0
        self.monthly_cost = 0.0
        self.last_reset_date = datetime.now().date()
        self._lock = threading.Lock()

    def check_budget(self, estimated_cost: float) -> None:
        """檢查預算。

        Args:
            estimated_cost: 預估成本

        Raises:
            BudgetExceededError: 當超出預算時
        """
        with self._lock:
            self._update_costs()
            
            # 檢查日預算
            if self.daily_cost + estimated_cost > self.budget.daily_budget * self.budget.hard_limit_threshold:
                raise BudgetExceededError(f"日預算即將超出: {self.daily_cost + estimated_cost:.4f} > {self.budget.daily_budget * self.budget.hard_limit_threshold:.4f}")
            
            # 檢查月預算
            if self.monthly_cost + estimated_cost > self.budget.monthly_budget * self.budget.hard_limit_threshold:
                raise BudgetExceededError(f"月預算即將超出: {self.monthly_cost + estimated_cost:.4f} > {self.budget.monthly_budget * self.budget.hard_limit_threshold:.4f}")
            
            # 檢查警告閾值
            if self.daily_cost + estimated_cost > self.budget.daily_budget * self.budget.alert_threshold:
                logger.warning(f"日預算警告: {self.daily_cost + estimated_cost:.4f} > {self.budget.daily_budget * self.budget.alert_threshold:.4f}")
            
            if self.monthly_cost + estimated_cost > self.budget.monthly_budget * self.budget.alert_threshold:
                logger.warning(f"月預算警告: {self.monthly_cost + estimated_cost:.4f} > {self.budget.monthly_budget * self.budget.alert_threshold:.4f}")

    def record_usage(self, cost: float, **kwargs) -> None:
        """記錄使用情況。

        Args:
            cost: 成本
            **kwargs: 其他使用信息
        """
        with self._lock:
            record = UsageRecord(
                timestamp=datetime.now(),
                cost=cost,
                **kwargs
            )
            
            self.usage_records.append(record)
            self._update_costs()
            
            # 限制記錄數量
            if len(self.usage_records) > 10000:
                self.usage_records = self.usage_records[-5000:]

    def _update_costs(self) -> None:
        """更新成本統計。"""
        today = datetime.now().date()
        current_month = datetime.now().replace(day=1).date()
        
        # 重置日成本
        if today != self.last_reset_date:
            self.last_reset_date = today
        
        # 計算日成本
        self.daily_cost = sum(
            record.cost for record in self.usage_records
            if record.timestamp.date() == today
        )
        
        # 計算月成本
        self.monthly_cost = sum(
            record.cost for record in self.usage_records
            if record.timestamp.date() >= current_month
        )

    def get_cost_summary(self) -> Dict[str, Any]:
        """獲取成本摘要。

        Returns:
            成本摘要字典
        """
        with self._lock:
            self._update_costs()
            
            return {
                'daily_cost': self.daily_cost,
                'daily_budget': self.budget.daily_budget,
                'daily_utilization': self.daily_cost / self.budget.daily_budget,
                'monthly_cost': self.monthly_cost,
                'monthly_budget': self.budget.monthly_budget,
                'monthly_utilization': self.monthly_cost / self.budget.monthly_budget,
                'alert_threshold': self.budget.alert_threshold,
                'hard_limit_threshold': self.budget.hard_limit_threshold
            }

    def estimate_cost(
        self,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """估算成本。

        Args:
            provider: 提供商
            model: 模型
            input_tokens: 輸入令牌數
            output_tokens: 輸出令牌數

        Returns:
            估算成本
        """
        # 這裡應該根據實際的定價表計算
        # 暫時使用簡化的計算方式
        base_cost_per_1k_tokens = {
            'openai': {
                'gpt-3.5-turbo': 0.002,
                'gpt-4': 0.03
            },
            'claude': {
                'claude-3-haiku': 0.00025,
                'claude-3-sonnet': 0.003
            }
        }
        
        provider_pricing = base_cost_per_1k_tokens.get(provider.lower(), {})
        model_cost = provider_pricing.get(model, 0.001)  # 默認成本
        
        total_tokens = input_tokens + output_tokens
        return (total_tokens / 1000) * model_cost
