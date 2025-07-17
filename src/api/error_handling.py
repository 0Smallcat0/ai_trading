# -*- coding: utf-8 -*-
"""
錯誤處理和重試機制模組

此模組提供健壯的錯誤處理、重試機制和連接狀態監控功能。

主要功能：
- 指數退避重試機制
- 錯誤分類和處理
- 連接狀態監控
- 熔斷器模式
- 錯誤統計和報告
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, Callable, List, Type
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import random

# 設定日誌
logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """錯誤類型枚舉"""
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    QUOTA_EXCEEDED_ERROR = "quota_exceeded_error"
    TIMEOUT_ERROR = "timeout_error"
    SERVER_ERROR = "server_error"
    CLIENT_ERROR = "client_error"
    UNKNOWN_ERROR = "unknown_error"


class CircuitState(Enum):
    """熔斷器狀態枚舉"""
    CLOSED = "closed"      # 正常狀態
    OPEN = "open"          # 熔斷狀態
    HALF_OPEN = "half_open"  # 半開狀態


@dataclass
class RetryConfig:
    """重試配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_errors: List[ErrorType] = None


@dataclass
class CircuitBreakerConfig:
    """熔斷器配置"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 3
    timeout: float = 30.0


@dataclass
class ErrorRecord:
    """錯誤記錄"""
    error_type: ErrorType
    error_message: str
    timestamp: datetime
    retry_count: int
    response_time: float
    metadata: Optional[Dict[str, Any]] = None


class RetryableError(Exception):
    """可重試錯誤基類"""
    
    def __init__(self, message: str, error_type: ErrorType = ErrorType.UNKNOWN_ERROR):
        super().__init__(message)
        self.error_type = error_type


class NonRetryableError(Exception):
    """不可重試錯誤基類"""
    
    def __init__(self, message: str, error_type: ErrorType = ErrorType.UNKNOWN_ERROR):
        super().__init__(message)
        self.error_type = error_type


class CircuitBreakerOpenError(Exception):
    """熔斷器開啟錯誤"""


class ErrorClassifier:
    """錯誤分類器"""

    @staticmethod
    def classify_error(exception: Exception) -> ErrorType:
        """分類錯誤。

        Args:
            exception: 異常對象

        Returns:
            錯誤類型
        """
        error_message = str(exception).lower()
        
        # 網路錯誤
        if any(keyword in error_message for keyword in [
            'connection', 'network', 'timeout', 'unreachable', 'dns'
        ]):
            return ErrorType.NETWORK_ERROR
        
        # 認證錯誤
        if any(keyword in error_message for keyword in [
            'authentication', 'unauthorized', 'invalid key', 'forbidden'
        ]):
            return ErrorType.AUTHENTICATION_ERROR
        
        # 速率限制錯誤
        if any(keyword in error_message for keyword in [
            'rate limit', 'too many requests', 'quota', 'throttle'
        ]):
            return ErrorType.RATE_LIMIT_ERROR
        
        # 配額超限錯誤
        if any(keyword in error_message for keyword in [
            'quota exceeded', 'limit exceeded', 'insufficient credits'
        ]):
            return ErrorType.QUOTA_EXCEEDED_ERROR
        
        # 超時錯誤
        if any(keyword in error_message for keyword in [
            'timeout', 'timed out', 'deadline exceeded'
        ]):
            return ErrorType.TIMEOUT_ERROR
        
        # 服務器錯誤
        if any(keyword in error_message for keyword in [
            'internal server error', '500', '502', '503', '504'
        ]):
            return ErrorType.SERVER_ERROR
        
        # 客戶端錯誤
        if any(keyword in error_message for keyword in [
            'bad request', '400', '404', 'not found', 'invalid'
        ]):
            return ErrorType.CLIENT_ERROR
        
        return ErrorType.UNKNOWN_ERROR

    @staticmethod
    def is_retryable(error_type: ErrorType) -> bool:
        """判斷錯誤是否可重試。

        Args:
            error_type: 錯誤類型

        Returns:
            是否可重試
        """
        retryable_errors = {
            ErrorType.NETWORK_ERROR,
            ErrorType.RATE_LIMIT_ERROR,
            ErrorType.TIMEOUT_ERROR,
            ErrorType.SERVER_ERROR,
            ErrorType.UNKNOWN_ERROR
        }
        
        return error_type in retryable_errors


class RetryHandler:
    """重試處理器"""

    def __init__(self, config: RetryConfig):
        """初始化重試處理器。

        Args:
            config: 重試配置
        """
        self.config = config
        if config.retryable_errors is None:
            self.config.retryable_errors = [
                ErrorType.NETWORK_ERROR,
                ErrorType.RATE_LIMIT_ERROR,
                ErrorType.TIMEOUT_ERROR,
                ErrorType.SERVER_ERROR,
                ErrorType.UNKNOWN_ERROR
            ]

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """執行函數並在失敗時重試。

        Args:
            func: 要執行的函數
            *args: 位置參數
            **kwargs: 關鍵字參數

        Returns:
            函數執行結果

        Raises:
            Exception: 當所有重試都失敗時
        """
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = time.time()
                result = await func(*args, **kwargs)
                response_time = time.time() - start_time
                
                # 記錄成功
                logger.debug(f"函數執行成功，嘗試次數: {attempt + 1}, 響應時間: {response_time:.2f}s")
                return result
                
            except Exception as e:
                response_time = time.time() - start_time
                error_type = ErrorClassifier.classify_error(e)
                
                # 記錄錯誤
                logger.warning(f"函數執行失敗 (嘗試 {attempt + 1}/{self.config.max_retries + 1}): {e}")
                
                # 檢查是否可重試
                if not ErrorClassifier.is_retryable(error_type):
                    logger.error(f"不可重試的錯誤: {error_type.value}")
                    raise e
                
                # 檢查是否還有重試機會
                if attempt >= self.config.max_retries:
                    logger.error(f"已達到最大重試次數: {self.config.max_retries}")
                    raise e
                
                # 計算延遲時間
                delay = self._calculate_delay(attempt, error_type)
                logger.info(f"等待 {delay:.2f} 秒後重試...")
                
                await asyncio.sleep(delay)
                last_exception = e
        
        # 理論上不會到達這裡
        raise last_exception

    def _calculate_delay(self, attempt: int, error_type: ErrorType) -> float:
        """計算重試延遲時間。

        Args:
            attempt: 嘗試次數
            error_type: 錯誤類型

        Returns:
            延遲時間（秒）
        """
        # 基礎延遲
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        
        # 限制最大延遲
        delay = min(delay, self.config.max_delay)
        
        # 針對特定錯誤類型調整延遲
        if error_type == ErrorType.RATE_LIMIT_ERROR:
            delay *= 2  # 速率限制錯誤延遲更長
        elif error_type == ErrorType.NETWORK_ERROR:
            delay *= 1.5  # 網路錯誤適當延長
        
        # 添加隨機抖動
        if self.config.jitter:
            jitter = random.uniform(0.1, 0.3) * delay
            delay += jitter
        
        return delay


class CircuitBreaker:
    """熔斷器"""

    def __init__(self, config: CircuitBreakerConfig):
        """初始化熔斷器。

        Args:
            config: 熔斷器配置
        """
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """通過熔斷器調用函數。

        Args:
            func: 要調用的函數
            *args: 位置參數
            **kwargs: 關鍵字參數

        Returns:
            函數執行結果

        Raises:
            CircuitBreakerOpenError: 當熔斷器開啟時
            Exception: 函數執行異常
        """
        # 檢查熔斷器狀態
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info("熔斷器進入半開狀態")
            else:
                raise CircuitBreakerOpenError("熔斷器處於開啟狀態")
        
        try:
            # 執行函數
            start_time = time.time()
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.timeout
            )
            response_time = time.time() - start_time
            
            # 記錄成功
            self._record_success()
            
            return result
            
        except Exception as e:
            # 記錄失敗
            self._record_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """判斷是否應該嘗試重置熔斷器。

        Returns:
            是否應該重置
        """
        if self.last_failure_time is None:
            return True
        
        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.config.recovery_timeout

    def _record_success(self) -> None:
        """記錄成功調用。"""
        self.last_success_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                logger.info("熔斷器重置為關閉狀態")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0  # 重置失敗計數

    def _record_failure(self) -> None:
        """記錄失敗調用。"""
        self.last_failure_time = time.time()
        self.failure_count += 1
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"熔斷器開啟，失敗次數: {self.failure_count}")
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.success_count = 0
            logger.warning("熔斷器從半開狀態回到開啟狀態")

    def get_state(self) -> Dict[str, Any]:
        """獲取熔斷器狀態。

        Returns:
            狀態信息字典
        """
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time,
            'last_success_time': self.last_success_time
        }


class ErrorTracker:
    """錯誤追蹤器"""

    def __init__(self, max_records: int = 1000):
        """初始化錯誤追蹤器。

        Args:
            max_records: 最大記錄數量
        """
        self.max_records = max_records
        self.error_records: List[ErrorRecord] = []
        self.error_stats = {
            'total_errors': 0,
            'error_by_type': {},
            'error_by_hour': {},
            'average_response_time': 0.0
        }

    def record_error(
        self,
        error_type: ErrorType,
        error_message: str,
        retry_count: int = 0,
        response_time: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """記錄錯誤。

        Args:
            error_type: 錯誤類型
            error_message: 錯誤消息
            retry_count: 重試次數
            response_time: 響應時間
            metadata: 元數據
        """
        record = ErrorRecord(
            error_type=error_type,
            error_message=error_message,
            timestamp=datetime.now(),
            retry_count=retry_count,
            response_time=response_time,
            metadata=metadata
        )
        
        self.error_records.append(record)
        
        # 限制記錄數量
        if len(self.error_records) > self.max_records:
            self.error_records.pop(0)
        
        # 更新統計
        self._update_stats(record)

    def _update_stats(self, record: ErrorRecord) -> None:
        """更新統計信息。

        Args:
            record: 錯誤記錄
        """
        self.error_stats['total_errors'] += 1
        
        # 按類型統計
        error_type = record.error_type.value
        if error_type not in self.error_stats['error_by_type']:
            self.error_stats['error_by_type'][error_type] = 0
        self.error_stats['error_by_type'][error_type] += 1
        
        # 按小時統計
        hour_key = record.timestamp.strftime('%Y-%m-%d %H:00')
        if hour_key not in self.error_stats['error_by_hour']:
            self.error_stats['error_by_hour'][hour_key] = 0
        self.error_stats['error_by_hour'][hour_key] += 1
        
        # 更新平均響應時間
        total_response_time = sum(r.response_time for r in self.error_records)
        self.error_stats['average_response_time'] = total_response_time / len(self.error_records)

    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """獲取錯誤摘要。

        Args:
            hours: 統計時間範圍（小時）

        Returns:
            錯誤摘要字典
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_errors = [r for r in self.error_records if r.timestamp >= cutoff_time]
        
        summary = {
            'total_errors': len(recent_errors),
            'error_rate': len(recent_errors) / hours if hours > 0 else 0,
            'most_common_errors': {},
            'average_retry_count': 0.0,
            'average_response_time': 0.0
        }
        
        if recent_errors:
            # 最常見錯誤
            error_counts = {}
            for record in recent_errors:
                error_type = record.error_type.value
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
            summary['most_common_errors'] = dict(
                sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            )
            
            # 平均重試次數
            summary['average_retry_count'] = sum(r.retry_count for r in recent_errors) / len(recent_errors)
            
            # 平均響應時間
            summary['average_response_time'] = sum(r.response_time for r in recent_errors) / len(recent_errors)
        
        return summary

    def clear_old_records(self, days: int = 7) -> None:
        """清理舊記錄。

        Args:
            days: 保留天數
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        self.error_records = [r for r in self.error_records if r.timestamp >= cutoff_time]
        logger.info(f"清理了 {days} 天前的錯誤記錄")
