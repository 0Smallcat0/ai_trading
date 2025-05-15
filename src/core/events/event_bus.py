"""
事件總線模組

此模組實現了事件總線，用於事件的發布和訂閱。
"""

import logging
import threading
import queue
import time
from typing import Dict, List, Callable, Any, Optional, Set, Tuple
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .event import Event, EventType, EventSeverity, EventSource

# 設定日誌
logger = logging.getLogger("events.event_bus")


class SubscriptionType(Enum):
    """訂閱類型列舉"""

    SYNC = 1  # 同步處理
    ASYNC = 2  # 異步處理
    QUEUE = 3  # 隊列處理


class EventBus:
    """
    事件總線類，實現事件的發布-訂閱模式

    事件總線負責：
    1. 接收和分發事件
    2. 管理事件訂閱
    3. 提供同步和異步事件處理
    4. 事件優先級處理
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """實現單例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventBus, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, max_workers: int = 4, queue_size: int = 1000):
        """
        初始化事件總線

        Args:
            max_workers: 最大工作線程數
            queue_size: 事件隊列大小
        """
        # 避免重複初始化
        if self._initialized:
            return

        # 訂閱者字典，key為事件類型，value為訂閱者列表
        self._subscribers: Dict[EventType, List[Tuple[Callable, SubscriptionType]]] = {}

        # 全局訂閱者列表，接收所有事件
        self._global_subscribers: List[Tuple[Callable, SubscriptionType]] = []

        # 事件隊列
        self._event_queue = queue.PriorityQueue(maxsize=queue_size)

        # 線程池
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

        # 事件處理線程
        self._processing_thread = None
        self._running = False

        # 異步事件循環
        self._loop = None

        # 已處理的事件ID集合，用於防止重複處理
        self._processed_events: Set[str] = set()

        # 事件計數器
        self._event_count = 0

        # 標記為已初始化
        self._initialized = True

        logger.info(
            f"事件總線已初始化，最大工作線程數: {max_workers}，隊列大小: {queue_size}"
        )

    def start(self):
        """啟動事件總線"""
        if self._running:
            logger.warning("事件總線已經在運行中")
            return

        self._running = True
        self._processing_thread = threading.Thread(target=self._process_events)
        self._processing_thread.daemon = True
        self._processing_thread.start()

        logger.info("事件總線已啟動")

    def stop(self):
        """停止事件總線"""
        if not self._running:
            logger.warning("事件總線尚未啟動")
            return

        self._running = False
        if self._processing_thread:
            self._processing_thread.join(timeout=5)

        # 關閉線程池
        self._executor.shutdown(wait=False)

        logger.info("事件總線已停止")

    def subscribe(
        self,
        event_type: Optional[EventType],
        callback: Callable[[Event], Any],
        subscription_type: SubscriptionType = SubscriptionType.SYNC,
    ):
        """
        訂閱事件

        Args:
            event_type: 事件類型，如果為None則訂閱所有事件
            callback: 回調函數，接收事件作為參數
            subscription_type: 訂閱類型，決定如何處理事件

        Returns:
            tuple: (event_type, callback)，可用於取消訂閱
        """
        if event_type is None:
            # 訂閱所有事件
            self._global_subscribers.append((callback, subscription_type))
            logger.debug(f"已添加全局訂閱: {callback.__name__}")
            return (None, callback)

        # 訂閱特定事件
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append((callback, subscription_type))
        logger.debug(f"已訂閱事件 {event_type.name}: {callback.__name__}")

        return (event_type, callback)

    def unsubscribe(self, subscription: Tuple[Optional[EventType], Callable]):
        """
        取消訂閱

        Args:
            subscription: 訂閱信息，由subscribe方法返回

        Returns:
            bool: 是否成功取消訂閱
        """
        event_type, callback = subscription

        if event_type is None:
            # 取消全局訂閱
            for i, (cb, _) in enumerate(self._global_subscribers):
                if cb == callback:
                    self._global_subscribers.pop(i)
                    logger.debug(f"已取消全局訂閱: {callback.__name__}")
                    return True
            return False

        # 取消特定事件訂閱
        if event_type not in self._subscribers:
            return False

        for i, (cb, _) in enumerate(self._subscribers[event_type]):
            if cb == callback:
                self._subscribers[event_type].pop(i)
                logger.debug(f"已取消事件 {event_type.name} 訂閱: {callback.__name__}")
                return True

        return False

    def publish(self, event: Event, priority: int = 0):
        """
        發布事件

        Args:
            event: 要發布的事件
            priority: 事件優先級，數字越小優先級越高

        Returns:
            bool: 是否成功發布
        """
        if not self._running:
            logger.warning("事件總線尚未啟動，無法發布事件")
            return False

        try:
            # 將事件放入隊列，使用優先級和時間戳作為排序依據
            timestamp = time.time()
            self._event_queue.put((priority, timestamp, event), block=False)
            self._event_count += 1

            logger.debug(f"已發布事件: {event}, 優先級: {priority}")
            return True
        except queue.Full:
            logger.error(f"事件隊列已滿，無法發布事件: {event}")
            return False

    def _process_events(self):
        """事件處理循環"""
        while self._running:
            try:
                # 從隊列中獲取事件
                try:
                    priority, timestamp, event = self._event_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                # 檢查是否已處理過此事件
                if event.id in self._processed_events:
                    self._event_queue.task_done()
                    continue

                # 標記事件為已處理
                self._processed_events.add(event.id)

                # 限制已處理事件集合的大小
                if len(self._processed_events) > 10000:
                    self._processed_events = set(list(self._processed_events)[-5000:])

                # 處理事件
                self._dispatch_event(event)

                # 標記任務完成
                self._event_queue.task_done()
            except Exception as e:
                logger.exception(f"處理事件時發生錯誤: {e}")

    def _dispatch_event(self, event: Event):
        """
        分發事件到訂閱者

        Args:
            event: 要分發的事件
        """
        # 獲取此事件類型的訂閱者
        subscribers = self._subscribers.get(event.event_type, [])

        # 添加全局訂閱者
        all_subscribers = subscribers + self._global_subscribers

        # 分發事件
        for callback, subscription_type in all_subscribers:
            try:
                if subscription_type == SubscriptionType.SYNC:
                    # 同步處理
                    callback(event)
                elif subscription_type == SubscriptionType.ASYNC:
                    # 異步處理
                    self._executor.submit(callback, event)
                elif subscription_type == SubscriptionType.QUEUE:
                    # 隊列處理 - 這裡假設回調是一個隊列的put方法
                    callback(event)
            except Exception as e:
                logger.exception(f"調用訂閱者 {callback.__name__} 時發生錯誤: {e}")

    async def publish_async(self, event: Event, priority: int = 0):
        """
        異步發布事件

        Args:
            event: 要發布的事件
            priority: 事件優先級，數字越小優先級越高

        Returns:
            bool: 是否成功發布
        """
        # 使用線程池執行器來避免阻塞事件循環
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.publish, event, priority)

    def get_stats(self):
        """
        獲取事件總線統計信息

        Returns:
            dict: 統計信息
        """
        return {
            "running": self._running,
            "queue_size": self._event_queue.qsize(),
            "queue_capacity": self._event_queue.maxsize,
            "processed_events": len(self._processed_events),
            "total_events": self._event_count,
            "subscribers": {
                event_type.name: len(subscribers)
                for event_type, subscribers in self._subscribers.items()
            },
            "global_subscribers": len(self._global_subscribers),
        }

    def clear(self):
        """清空事件隊列和已處理事件集合"""
        while not self._event_queue.empty():
            try:
                self._event_queue.get(block=False)
                self._event_queue.task_done()
            except queue.Empty:
                break

        self._processed_events.clear()
        logger.info("事件總線已清空")


# 創建全局事件總線實例
event_bus = EventBus()
