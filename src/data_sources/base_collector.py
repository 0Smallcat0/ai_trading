"""基礎收集器模組

此模組提供資料收集器的基礎類別，包括：
- 抽象基礎類別
- 快取管理
- 資料驗證
- 重試機制

Example:
    >>> class MyCollector(BaseDataCollector):
    ...     def collect(self, *args, **kwargs):
    ...         return "collected data"
"""

import logging
import os
import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Optional

import pandas as pd

from src.config import CACHE_DIR
from src.core.rate_limiter import RateLimiter
from src.utils.retry import ExponentialRetryStrategy

logger = logging.getLogger(__name__)


class BaseDataCollector(ABC):
    """資料收集器基礎類別

    提供資料收集的通用功能，包括重試機制、錯誤處理、資料驗證等。
    """

    def __init__(
        self,
        name: str,
        source: str,
        use_cache: bool = True,
        cache_expiry_days: int = 1,
        retry_strategy: Optional[ExponentialRetryStrategy] = None,
        rate_limit_max_calls: int = 60,
        rate_limit_period: int = 60,
    ):
        """初始化資料收集器

        Args:
            name: 收集器名稱
            source: 資料來源名稱
            use_cache: 是否使用快取
            cache_expiry_days: 快取過期天數
            retry_strategy: 重試策略，如果為 None 則使用預設策略
            rate_limit_max_calls: 速率限制最大請求數
            rate_limit_period: 速率限制時間段（秒）
        """
        self.name = name
        self.source = source
        self.use_cache = use_cache
        self.cache_expiry_days = cache_expiry_days
        self.retry_strategy = retry_strategy or ExponentialRetryStrategy()
        self.last_run_time = None
        self.last_run_status = None
        self.error_count = 0
        self.success_count = 0

        # 建立快取目錄
        self.cache_dir = os.path.join(CACHE_DIR, source)
        os.makedirs(self.cache_dir, exist_ok=True)

        # 建立速率限制器
        self.rate_limiter = RateLimiter(
            max_calls=rate_limit_max_calls,
            period=rate_limit_period,
        )

    def with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """使用重試機制執行函數

        Args:
            func: 要執行的函數
            *args: 函數參數
            **kwargs: 函數關鍵字參數

        Returns:
            Any: 函數執行結果

        Raises:
            Exception: 如果所有重試都失敗，則拋出最後一次的異常
        """
        last_exception = None
        for retry_count in range(self.retry_strategy.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if retry_count < self.retry_strategy.max_retries:
                    delay = self.retry_strategy.get_delay(retry_count)
                    logger.warning(
                        "%s 執行失敗，將在 %.2f 秒後重試 (%d/%d): %s",
                        self.name, delay, retry_count + 1,
                        self.retry_strategy.max_retries, e
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "%s 執行失敗，已達最大重試次數 (%d): %s",
                        self.name, self.retry_strategy.max_retries, e
                    )
                    self.error_count += 1
                    raise last_exception from e

    def _get_cache_path(
        self, data_type: str, identifier: str, start_date: str, end_date: str
    ) -> str:
        """獲取快取檔案路徑

        Args:
            data_type: 資料類型
            identifier: 識別符（如股票代碼）
            start_date: 開始日期
            end_date: 結束日期

        Returns:
            str: 快取檔案路徑
        """
        identifier_dir = os.path.join(self.cache_dir, identifier.replace(".", "_"))
        os.makedirs(identifier_dir, exist_ok=True)
        return os.path.join(identifier_dir, f"{data_type}_{start_date}_{end_date}.csv")

    def _is_cache_valid(self, cache_path: str) -> bool:
        """檢查快取是否有效

        Args:
            cache_path: 快取檔案路徑

        Returns:
            bool: 快取是否有效
        """
        if not os.path.exists(cache_path):
            return False

        # 檢查檔案修改時間
        file_time = os.path.getmtime(cache_path)
        file_date = datetime.fromtimestamp(file_time)
        now = datetime.now()
        return (now - file_date).days < self.cache_expiry_days

    @abstractmethod
    def collect(self, *args, **kwargs) -> Any:
        """收集資料的抽象方法，子類必須實現

        Returns:
            Any: 收集的資料
        """

    def run(self, *args, **kwargs) -> Any:
        """執行資料收集，包含重試機制和錯誤處理

        Returns:
            Any: 收集的資料
        """
        self.last_run_time = datetime.now()
        try:
            result = self.with_retry(self.collect, *args, **kwargs)
            self.last_run_status = "success"
            self.success_count += 1
            return result
        except Exception as e:
            self.last_run_status = "error"
            logger.error("%s 執行失敗: %s\n%s", self.name, e, traceback.format_exc())
            return None

    def validate_data(self, data: Any) -> bool:
        """驗證資料的有效性

        Args:
            data: 要驗證的資料

        Returns:
            bool: 資料是否有效
        """
        # 基本驗證，子類可以覆寫此方法提供更詳細的驗證
        if data is None:
            return False
        if isinstance(data, pd.DataFrame) and data.empty:
            return False
        return True

    def get_statistics(self) -> dict:
        """獲取收集器統計資訊

        Returns:
            dict: 統計資訊字典
        """
        return {
            "name": self.name,
            "source": self.source,
            "last_run_time": self.last_run_time,
            "last_run_status": self.last_run_status,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "total_runs": self.error_count + self.success_count,
            "success_rate": (
                self.success_count / (self.error_count + self.success_count)
                if (self.error_count + self.success_count) > 0 else 0
            )
        }

    def reset_statistics(self) -> None:
        """重置統計資訊"""
        self.error_count = 0
        self.success_count = 0
        self.last_run_time = None
        self.last_run_status = None
        logger.info("%s 統計資訊已重置", self.name)
