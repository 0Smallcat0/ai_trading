# -*- coding: utf-8 -*-
"""API限制管理器

此模組提供統一的API限制管理、認證機制、頻率控制和負載均衡功能，
確保各數據源的API調用符合限制要求，避免超限和封禁。

主要功能：
- 統一API限制管理
- 智能頻率控制
- 負載均衡和分散
- 認證機制管理
- 積分和配額管理

支援的限制類型：
- 每秒請求數限制 (RPS)
- 每分鐘請求數限制 (RPM)
- 每日請求數限制 (RPD)
- 積分制限制 (Points)
- 並發請求數限制 (Concurrent)

Example:
    >>> from src.utils.api_limit_manager import APILimitManager
    >>> manager = APILimitManager()
    >>> 
    >>> # 檢查是否可以發起請求
    >>> if manager.can_make_request('tushare', 'daily_data'):
    ...     response = make_api_call()
    ...     manager.record_request('tushare', 'daily_data', success=True)
"""

import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import threading
from collections import defaultdict, deque
from dataclasses import dataclass
import json

# 設定日誌
logger = logging.getLogger(__name__)


@dataclass
class APILimit:
    """API限制配置"""
    limit_type: str  # 'rps', 'rpm', 'rpd', 'points', 'concurrent'
    limit_value: int  # 限制數值
    window_seconds: int  # 時間窗口（秒）
    reset_time: Optional[datetime] = None  # 重置時間
    current_usage: int = 0  # 當前使用量


@dataclass
class RequestRecord:
    """請求記錄"""
    timestamp: datetime
    endpoint: str
    success: bool
    response_time: float
    cost: int = 1  # 請求成本（積分或次數）


class RateLimiter:
    """頻率限制器
    
    實現滑動窗口算法的頻率限制。
    """
    
    def __init__(self, limit: int, window_seconds: int):
        """初始化頻率限制器
        
        Args:
            limit: 限制數量
            window_seconds: 時間窗口（秒）
        """
        self.limit = limit
        self.window_seconds = window_seconds
        self.requests = deque()
        self.lock = threading.Lock()
    
    def can_make_request(self) -> bool:
        """檢查是否可以發起請求"""
        with self.lock:
            now = datetime.now()
            cutoff_time = now - timedelta(seconds=self.window_seconds)
            
            # 移除過期的請求記錄
            while self.requests and self.requests[0] < cutoff_time:
                self.requests.popleft()
            
            # 檢查是否超過限制
            return len(self.requests) < self.limit
    
    def record_request(self):
        """記錄請求"""
        with self.lock:
            self.requests.append(datetime.now())
    
    def get_wait_time(self) -> float:
        """獲取需要等待的時間（秒）"""
        with self.lock:
            if len(self.requests) < self.limit:
                return 0.0
            
            # 計算最早請求的過期時間
            oldest_request = self.requests[0]
            wait_until = oldest_request + timedelta(seconds=self.window_seconds)
            wait_time = (wait_until - datetime.now()).total_seconds()
            
            return max(0.0, wait_time)


class PointsManager:
    """積分管理器
    
    管理基於積分制的API限制（如Tushare Pro）。
    """
    
    def __init__(self, daily_limit: int, initial_points: int = None):
        """初始化積分管理器
        
        Args:
            daily_limit: 每日積分限制
            initial_points: 初始積分數量
        """
        self.daily_limit = daily_limit
        self.current_points = initial_points or daily_limit
        self.last_reset = datetime.now().date()
        self.usage_history = []
        self.lock = threading.Lock()
    
    def can_make_request(self, cost: int = 1) -> bool:
        """檢查是否有足夠積分"""
        with self.lock:
            self._check_daily_reset()
            return self.current_points >= cost
    
    def use_points(self, cost: int = 1) -> bool:
        """使用積分
        
        Args:
            cost: 積分成本
            
        Returns:
            是否成功使用積分
        """
        with self.lock:
            self._check_daily_reset()
            
            if self.current_points >= cost:
                self.current_points -= cost
                self.usage_history.append({
                    'timestamp': datetime.now(),
                    'cost': cost,
                    'remaining': self.current_points
                })
                return True
            
            return False
    
    def _check_daily_reset(self):
        """檢查是否需要每日重置"""
        today = datetime.now().date()
        if today > self.last_reset:
            self.current_points = self.daily_limit
            self.last_reset = today
            logger.info(f"積分已重置為 {self.daily_limit}")
    
    def get_remaining_points(self) -> int:
        """獲取剩餘積分"""
        with self.lock:
            self._check_daily_reset()
            return self.current_points
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """獲取使用統計"""
        with self.lock:
            today_usage = [
                record for record in self.usage_history
                if record['timestamp'].date() == datetime.now().date()
            ]
            
            return {
                'daily_limit': self.daily_limit,
                'current_points': self.current_points,
                'used_today': sum(record['cost'] for record in today_usage),
                'requests_today': len(today_usage),
                'usage_rate': (self.daily_limit - self.current_points) / self.daily_limit
            }


class APILimitManager:
    """API限制管理器
    
    統一管理所有數據源的API限制、認證和頻率控制。
    
    Attributes:
        limits: API限制配置
        rate_limiters: 頻率限制器
        points_managers: 積分管理器
        request_history: 請求歷史記錄
        
    Example:
        >>> manager = APILimitManager()
        >>> manager.configure_limits('tushare', {
        ...     'daily_points': 10000,
        ...     'per_minute': 200
        ... })
        >>> 
        >>> if manager.can_make_request('tushare', 'daily_data'):
        ...     # 發起API請求
        ...     manager.record_request('tushare', 'daily_data', True, 1.2)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化API限制管理器
        
        Args:
            config: 配置參數
        """
        self.config = config or {}
        
        # 限制配置
        self.limits: Dict[str, Dict[str, APILimit]] = {}
        
        # 頻率限制器
        self.rate_limiters: Dict[str, Dict[str, RateLimiter]] = defaultdict(dict)
        
        # 積分管理器
        self.points_managers: Dict[str, PointsManager] = {}
        
        # 請求歷史
        self.request_history: Dict[str, List[RequestRecord]] = defaultdict(list)
        
        # 並發控制
        self.concurrent_requests: Dict[str, int] = defaultdict(int)
        self.concurrent_locks: Dict[str, threading.Semaphore] = {}
        
        # 初始化預設配置
        self._initialize_default_limits()
        
        logger.info("API限制管理器初始化完成")
    
    def _initialize_default_limits(self):
        """初始化預設限制配置"""
        default_configs = {
            'tushare': {
                'daily_points': 10000,
                'per_minute': 200,
                'concurrent': 5
            },
            'baostock': {
                'per_second': 10,
                'per_minute': 600,
                'concurrent': 3
            },
            'qstock': {
                'per_second': 5,
                'per_minute': 300,
                'concurrent': 2
            },
            'yahoo': {
                'per_second': 2,
                'per_minute': 100,
                'concurrent': 1
            }
        }
        
        for source, config in default_configs.items():
            self.configure_limits(source, config)
    
    def configure_limits(self, source: str, limits_config: Dict[str, Any]):
        """配置數據源的API限制
        
        Args:
            source: 數據源名稱
            limits_config: 限制配置
        """
        self.limits[source] = {}
        
        # 配置頻率限制
        if 'per_second' in limits_config:
            self.rate_limiters[source]['per_second'] = RateLimiter(
                limits_config['per_second'], 1
            )
        
        if 'per_minute' in limits_config:
            self.rate_limiters[source]['per_minute'] = RateLimiter(
                limits_config['per_minute'], 60
            )
        
        if 'per_hour' in limits_config:
            self.rate_limiters[source]['per_hour'] = RateLimiter(
                limits_config['per_hour'], 3600
            )
        
        # 配置積分管理
        if 'daily_points' in limits_config:
            self.points_managers[source] = PointsManager(
                limits_config['daily_points'],
                limits_config.get('initial_points')
            )
        
        # 配置並發限制
        if 'concurrent' in limits_config:
            self.concurrent_locks[source] = threading.Semaphore(
                limits_config['concurrent']
            )
        
        logger.info(f"已配置 {source} 的API限制: {limits_config}")
    
    def can_make_request(self, source: str, endpoint: str, cost: int = 1) -> bool:
        """檢查是否可以發起請求
        
        Args:
            source: 數據源名稱
            endpoint: API端點
            cost: 請求成本（積分）
            
        Returns:
            是否可以發起請求
        """
        # 檢查頻率限制
        for limit_type, rate_limiter in self.rate_limiters.get(source, {}).items():
            if not rate_limiter.can_make_request():
                logger.debug(f"{source} {limit_type} 頻率限制觸發")
                return False
        
        # 檢查積分限制
        if source in self.points_managers:
            if not self.points_managers[source].can_make_request(cost):
                logger.debug(f"{source} 積分不足")
                return False
        
        # 檢查並發限制
        if source in self.concurrent_locks:
            if not self.concurrent_locks[source]._value > 0:
                logger.debug(f"{source} 並發限制觸發")
                return False
        
        return True
    
    def acquire_request_slot(self, source: str) -> bool:
        """獲取請求槽位（用於並發控制）
        
        Args:
            source: 數據源名稱
            
        Returns:
            是否成功獲取槽位
        """
        if source in self.concurrent_locks:
            acquired = self.concurrent_locks[source].acquire(blocking=False)
            if acquired:
                self.concurrent_requests[source] += 1
            return acquired
        
        return True
    
    def release_request_slot(self, source: str):
        """釋放請求槽位
        
        Args:
            source: 數據源名稱
        """
        if source in self.concurrent_locks:
            self.concurrent_locks[source].release()
            self.concurrent_requests[source] = max(0, self.concurrent_requests[source] - 1)
    
    def record_request(self, source: str, endpoint: str, success: bool, 
                      response_time: float, cost: int = 1):
        """記錄請求
        
        Args:
            source: 數據源名稱
            endpoint: API端點
            success: 請求是否成功
            response_time: 響應時間
            cost: 請求成本
        """
        # 記錄到頻率限制器
        for rate_limiter in self.rate_limiters.get(source, {}).values():
            rate_limiter.record_request()
        
        # 扣除積分
        if source in self.points_managers and success:
            self.points_managers[source].use_points(cost)
        
        # 記錄請求歷史
        record = RequestRecord(
            timestamp=datetime.now(),
            endpoint=endpoint,
            success=success,
            response_time=response_time,
            cost=cost
        )
        
        self.request_history[source].append(record)
        
        # 保持歷史記錄在合理範圍內
        if len(self.request_history[source]) > 10000:
            self.request_history[source] = self.request_history[source][-5000:]
        
        logger.debug(f"記錄 {source} 請求: {endpoint}, 成功: {success}, 耗時: {response_time:.2f}s")
    
    def get_wait_time(self, source: str) -> float:
        """獲取需要等待的時間
        
        Args:
            source: 數據源名稱
            
        Returns:
            等待時間（秒）
        """
        max_wait_time = 0.0
        
        for rate_limiter in self.rate_limiters.get(source, {}).values():
            wait_time = rate_limiter.get_wait_time()
            max_wait_time = max(max_wait_time, wait_time)
        
        return max_wait_time
    
    def get_source_status(self, source: str) -> Dict[str, Any]:
        """獲取數據源狀態
        
        Args:
            source: 數據源名稱
            
        Returns:
            數據源狀態信息
        """
        status = {
            'source': source,
            'can_make_request': self.can_make_request(source, 'test'),
            'wait_time': self.get_wait_time(source),
            'concurrent_requests': self.concurrent_requests.get(source, 0)
        }
        
        # 添加積分信息
        if source in self.points_managers:
            status['points'] = self.points_managers[source].get_usage_stats()
        
        # 添加頻率限制信息
        rate_limits = {}
        for limit_type, rate_limiter in self.rate_limiters.get(source, {}).items():
            rate_limits[limit_type] = {
                'limit': rate_limiter.limit,
                'window_seconds': rate_limiter.window_seconds,
                'current_usage': len(rate_limiter.requests),
                'can_request': rate_limiter.can_make_request()
            }
        status['rate_limits'] = rate_limits
        
        # 添加請求統計
        recent_requests = [
            r for r in self.request_history.get(source, [])
            if r.timestamp > datetime.now() - timedelta(hours=1)
        ]
        
        if recent_requests:
            success_count = sum(1 for r in recent_requests if r.success)
            status['recent_stats'] = {
                'total_requests': len(recent_requests),
                'success_requests': success_count,
                'success_rate': success_count / len(recent_requests),
                'avg_response_time': sum(r.response_time for r in recent_requests) / len(recent_requests)
            }
        
        return status
    
    def get_all_sources_status(self) -> Dict[str, Dict[str, Any]]:
        """獲取所有數據源狀態
        
        Returns:
            所有數據源的狀態信息
        """
        all_status = {}
        
        # 獲取所有已配置的數據源
        all_sources = set(self.limits.keys()) | set(self.rate_limiters.keys()) | set(self.points_managers.keys())
        
        for source in all_sources:
            all_status[source] = self.get_source_status(source)
        
        return all_status
    
    async def wait_for_available_slot(self, source: str, timeout: float = 60.0) -> bool:
        """等待可用的請求槽位
        
        Args:
            source: 數據源名稱
            timeout: 超時時間（秒）
            
        Returns:
            是否成功獲取槽位
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.can_make_request(source, 'wait'):
                return True
            
            wait_time = min(self.get_wait_time(source), 1.0)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            else:
                await asyncio.sleep(0.1)
        
        return False
    
    def reset_source_limits(self, source: str):
        """重置數據源限制（用於測試或緊急情況）
        
        Args:
            source: 數據源名稱
        """
        # 重置頻率限制器
        for rate_limiter in self.rate_limiters.get(source, {}).values():
            rate_limiter.requests.clear()
        
        # 重置積分（謹慎使用）
        if source in self.points_managers:
            self.points_managers[source].current_points = self.points_managers[source].daily_limit
        
        # 重置並發計數
        self.concurrent_requests[source] = 0
        
        logger.warning(f"已重置 {source} 的API限制")
    
    def export_usage_report(self, source: Optional[str] = None, 
                           hours: int = 24) -> Dict[str, Any]:
        """導出使用報告
        
        Args:
            source: 數據源名稱（None表示所有數據源）
            hours: 報告時間範圍（小時）
            
        Returns:
            使用報告
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        report = {
            'report_time': datetime.now().isoformat(),
            'time_range_hours': hours,
            'sources': {}
        }
        
        sources_to_report = [source] if source else self.request_history.keys()
        
        for src in sources_to_report:
            recent_requests = [
                r for r in self.request_history.get(src, [])
                if r.timestamp > cutoff_time
            ]
            
            if recent_requests:
                success_requests = [r for r in recent_requests if r.success]
                
                report['sources'][src] = {
                    'total_requests': len(recent_requests),
                    'success_requests': len(success_requests),
                    'failed_requests': len(recent_requests) - len(success_requests),
                    'success_rate': len(success_requests) / len(recent_requests),
                    'avg_response_time': sum(r.response_time for r in recent_requests) / len(recent_requests),
                    'total_cost': sum(r.cost for r in recent_requests),
                    'endpoints': {}
                }
                
                # 按端點統計
                endpoint_stats = defaultdict(list)
                for r in recent_requests:
                    endpoint_stats[r.endpoint].append(r)
                
                for endpoint, requests in endpoint_stats.items():
                    success_count = sum(1 for r in requests if r.success)
                    report['sources'][src]['endpoints'][endpoint] = {
                        'requests': len(requests),
                        'success_rate': success_count / len(requests),
                        'avg_response_time': sum(r.response_time for r in requests) / len(requests)
                    }
        
        return report
