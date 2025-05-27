"""
資料收集器基礎模組

此模組提供資料收集的基礎類別和功能，包括：
- 資料收集器基礎類別
- 重試機制
- 錯誤處理
- 資料驗證

所有特定類型的資料收集器都應該繼承自基礎類別。
"""

import logging
import os
import queue
import threading
import time
import traceback
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import schedule

from src.config import CACHE_DIR, DATA_DIR
from src.core.rate_limiter import RateLimiter
from src.database.schema import MarketType, TimeGranularity

# 設定日誌
logger = logging.getLogger(__name__)


class RetryStrategy:
    """重試策略類別，定義重試的次數、間隔等參數"""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
    ):
        """
        初始化重試策略

        Args:
            max_retries: 最大重試次數
            initial_delay: 初始延遲時間（秒）
            backoff_factor: 退避因子，每次重試後延遲時間會乘以此因子
            max_delay: 最大延遲時間（秒）
            jitter: 是否添加隨機抖動以避免同時重試
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.jitter = jitter

    def get_delay(self, retry_count: int) -> float:
        """
        計算下一次重試的延遲時間

        Args:
            retry_count: 當前重試次數

        Returns:
            float: 延遲時間（秒）
        """
        delay = min(
            self.initial_delay * (self.backoff_factor ** retry_count), self.max_delay
        )
        if self.jitter:
            # 添加 0-30% 的隨機抖動
            import random

            delay = delay * (1 + random.random() * 0.3)
        return delay


class DataCollector(ABC):
    """
    資料收集器基礎類別

    提供資料收集的通用功能，包括重試機制、錯誤處理、資料驗證等。
    """

    def __init__(
        self,
        name: str,
        source: str,
        use_cache: bool = True,
        cache_expiry_days: int = 1,
        retry_strategy: Optional[RetryStrategy] = None,
        rate_limit_max_calls: int = 60,
        rate_limit_period: int = 60,
    ):
        """
        初始化資料收集器

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
        self.retry_strategy = retry_strategy or RetryStrategy()
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

        # 初始化排程器
        self.scheduler = schedule.Scheduler()
        self.scheduler_thread = None
        self.scheduler_running = False
        self.scheduler_queue = queue.Queue()

    def with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        使用重試機制執行函數

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
                        f"{self.name} 執行失敗，將在 {delay:.2f} 秒後重試 ({retry_count + 1}/{self.retry_strategy.max_retries}): {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"{self.name} 執行失敗，已達最大重試次數 ({self.retry_strategy.max_retries}): {e}"
                    )
                    self.error_count += 1
                    raise last_exception

    def _get_cache_path(
        self, data_type: str, identifier: str, start_date: str, end_date: str
    ) -> str:
        """
        獲取快取檔案路徑

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
        return os.path.join(
            identifier_dir, f"{data_type}_{start_date}_{end_date}.csv"
        )

    def _is_cache_valid(self, cache_path: str) -> bool:
        """
        檢查快取是否有效

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
        """
        收集資料的抽象方法，子類必須實現

        Returns:
            Any: 收集的資料
        """
        pass

    def run(self, *args, **kwargs) -> Any:
        """
        執行資料收集，包含重試機制和錯誤處理

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
            logger.error(
                f"{self.name} 執行失敗: {e}\n{traceback.format_exc()}"
            )
            return None

    def validate_data(self, data: Any) -> bool:
        """
        驗證資料的有效性

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

    def _run_scheduler(self):
        """排程器執行函數"""
        while self.scheduler_running:
            try:
                # 執行排定的任務
                self.scheduler.run_pending()

                # 檢查是否有手動觸發的任務
                try:
                    func, args, kwargs = self.scheduler_queue.get(block=False)
                    func(*args, **kwargs)
                except queue.Empty:
                    pass

                time.sleep(1)
            except Exception as e:
                logger.error(f"排程器執行錯誤: {e}\n{traceback.format_exc()}")

    def start_scheduler(self):
        """啟動排程器"""
        if self.scheduler_thread is None or not self.scheduler_thread.is_alive():
            self.scheduler_running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            logger.info(f"{self.name} 排程器已啟動")

    def stop_scheduler(self):
        """停止排程器"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_running = False
            self.scheduler_thread.join(timeout=5)
            logger.info(f"{self.name} 排程器已停止")

    def schedule_daily(self, time_str: str, *args, **kwargs):
        """
        設定每日執行的排程

        Args:
            time_str: 執行時間，格式為 'HH:MM'
            *args: 傳遞給 collect 方法的參數
            **kwargs: 傳遞給 collect 方法的關鍵字參數
        """
        self.scheduler.every().day.at(time_str).do(self.run, *args, **kwargs)
        logger.info(f"{self.name} 已設定每日 {time_str} 執行")

    def schedule_hourly(self, minute: int = 0, *args, **kwargs):
        """
        設定每小時執行的排程

        Args:
            minute: 執行的分鐘數
            *args: 傳遞給 collect 方法的參數
            **kwargs: 傳遞給 collect 方法的關鍵字參數
        """
        self.scheduler.every().hour.at(f":{minute:02d}").do(self.run, *args, **kwargs)
        logger.info(f"{self.name} 已設定每小時的第 {minute} 分鐘執行")

    def schedule_interval(self, interval: int, unit: str = "minutes", *args, **kwargs):
        """
        設定固定間隔執行的排程

        Args:
            interval: 間隔數量
            unit: 間隔單位，可選 'seconds', 'minutes', 'hours', 'days', 'weeks'
            *args: 傳遞給 collect 方法的參數
            **kwargs: 傳遞給 collect 方法的關鍵字參數
        """
        if unit == "seconds":
            self.scheduler.every(interval).seconds.do(self.run, *args, **kwargs)
        elif unit == "minutes":
            self.scheduler.every(interval).minutes.do(self.run, *args, **kwargs)
        elif unit == "hours":
            self.scheduler.every(interval).hours.do(self.run, *args, **kwargs)
        elif unit == "days":
            self.scheduler.every(interval).days.do(self.run, *args, **kwargs)
        elif unit == "weeks":
            self.scheduler.every(interval).weeks.do(self.run, *args, **kwargs)
        logger.info(f"{self.name} 已設定每 {interval} {unit} 執行一次")

    def trigger_now(self, *args, **kwargs):
        """
        立即觸發執行

        Args:
            *args: 傳遞給 collect 方法的參數
            **kwargs: 傳遞給 collect 方法的關鍵字參數
        """
        if self.scheduler_running:
            self.scheduler_queue.put((self.run, args, kwargs))
            logger.info(f"{self.name} 已觸發立即執行")
        else:
            logger.warning(f"{self.name} 排程器未啟動，無法觸發執行")
            return self.run(*args, **kwargs)
