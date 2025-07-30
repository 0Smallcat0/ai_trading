"""排程管理混合類別模組

此模組提供資料收集器的排程功能，包括：
- 排程器管理
- 定時任務設定
- 手動觸發機制

Example:
    >>> class MyCollector(BaseDataCollector, SchedulerMixin):
    ...     def collect(self, *args, **kwargs):
    ...         return "data"
    >>> collector = MyCollector("test", "source")
    >>> collector.schedule_daily("18:00", "2330.TW")
"""

import logging
import queue
import threading
import time
import traceback
from typing import Any

import schedule

logger = logging.getLogger(__name__)


class SchedulerMixin:
    """排程管理混合類別

    提供排程相關的功能，可以與基礎收集器類別混合使用。
    """

    def __init__(self, *args, **kwargs):
        """初始化排程器"""
        super().__init__(*args, **kwargs)
        
        # 初始化排程器
        self.scheduler = schedule.Scheduler()
        self.scheduler_thread = None
        self.scheduler_running = False
        self.scheduler_queue = queue.Queue()

    def _run_scheduler(self) -> None:
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
                logger.error("排程器執行錯誤: %s\n%s", e, traceback.format_exc())

    def start_scheduler(self) -> None:
        """啟動排程器"""
        if self.scheduler_thread is None or not self.scheduler_thread.is_alive():
            self.scheduler_running = True
            self.scheduler_thread = threading.Thread(target=self._run_scheduler)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            logger.info("%s 排程器已啟動", self.name)

    def stop_scheduler(self) -> None:
        """停止排程器"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_running = False
            self.scheduler_thread.join(timeout=5)
            logger.info("%s 排程器已停止", self.name)

    def schedule_daily(self, time_str: str, *args, **kwargs) -> None:
        """設定每日執行的排程

        Args:
            time_str: 執行時間，格式為 'HH:MM'
            *args: 傳遞給 collect 方法的參數
            **kwargs: 傳遞給 collect 方法的關鍵字參數
        """
        self.scheduler.every().day.at(time_str).do(self.run, *args, **kwargs)
        logger.info("%s 已設定每日 %s 執行", self.name, time_str)

    def schedule_hourly(self, minute: int = 0, *args, **kwargs) -> None:
        """設定每小時執行的排程

        Args:
            minute: 執行的分鐘數
            *args: 傳遞給 collect 方法的參數
            **kwargs: 傳遞給 collect 方法的關鍵字參數
        """
        self.scheduler.every().hour.at(f":{minute:02d}").do(
            self.run, *args, **kwargs
        )
        logger.info("%s 已設定每小時的第 %d 分鐘執行", self.name, minute)

    def schedule_interval(
        self, interval: int, unit: str = "minutes", *args, **kwargs
    ) -> None:
        """設定固定間隔執行的排程

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
        else:
            raise ValueError(f"不支援的時間單位: {unit}")
        
        logger.info("%s 已設定每 %d %s 執行一次", self.name, interval, unit)

    def trigger_now(self, *args, **kwargs) -> Any:
        """立即觸發執行

        Args:
            *args: 傳遞給 collect 方法的參數
            **kwargs: 傳遞給 collect 方法的關鍵字參數

        Returns:
            Any: 執行結果
        """
        if self.scheduler_running:
            self.scheduler_queue.put((self.run, args, kwargs))
            logger.info("%s 已觸發立即執行", self.name)
            return None
        else:
            logger.warning("%s 排程器未啟動，直接執行", self.name)
            return self.run(*args, **kwargs)

    def clear_schedule(self) -> None:
        """清除所有排程"""
        self.scheduler.clear()
        logger.info("%s 已清除所有排程", self.name)

    def get_scheduled_jobs(self) -> list:
        """獲取所有排程任務

        Returns:
            list: 排程任務列表
        """
        return list(self.scheduler.jobs)

    def get_next_run_time(self) -> Any:
        """獲取下次執行時間

        Returns:
            Any: 下次執行時間，如果沒有排程則返回 None
        """
        if self.scheduler.jobs:
            return min(job.next_run for job in self.scheduler.jobs)
        return None
