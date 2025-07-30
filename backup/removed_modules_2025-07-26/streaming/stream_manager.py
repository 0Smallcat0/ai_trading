"""
流管理器模組

此模組實現了流管理器，用於管理數據流的生產者、消費者和處理器。
"""

import json
import logging
import os
import queue
import threading
import time
from typing import Any, Dict, List, Optional

from .consumer import Consumer
from .message import Message, MessageType
from .pipeline import Pipeline
from .processor import Processor
from .producer import Producer

# 設定日誌
logger = logging.getLogger("streaming.manager")


class StreamManager:
    """
    流管理器類，用於管理數據流的生產者、消費者和處理器

    流管理器負責：
    1. 管理生產者和消費者
    2. 路由消息
    3. 監控數據流
    4. 處理背壓和錯誤
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """實現單例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(StreamManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化流管理器

        Args:
            config_path: 配置文件路徑
        """
        # 避免重複初始化
        if self._initialized:
            return

        # 加載配置
        self.config = self._load_config(config_path)

        # 初始化組件
        self.producers: Dict[str, Producer] = {}
        self.consumers: Dict[str, Consumer] = {}
        self.processors: Dict[str, Processor] = {}
        self.pipelines: Dict[str, Pipeline] = {}

        # 消息隊列
        self.message_queue = queue.PriorityQueue(
            maxsize=self.config.get("queue_size", 10000)
        )

        # 運行狀態
        self.running = False
        self.processing_thread = None

        # 統計信息
        self.stats = {
            "messages_processed": 0,
            "messages_dropped": 0,
            "errors": 0,
            "start_time": None,
            "last_message_time": None,
        }

        # 訂閱信息
        self.subscriptions: Dict[MessageType, List[str]] = {}

        # 標記為已初始化
        self._initialized = True
        logger.info("流管理器已初始化")

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        加載配置

        Args:
            config_path: 配置文件路徑

        Returns:
            Dict[str, Any]: 配置字典
        """
        default_config = {
            "queue_size": 10000,
            "worker_threads": 4,
            "max_retry": 3,
            "retry_interval": 5,
            "monitoring_interval": 60,
            "log_level": "INFO",
        }

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # 合併默認配置
                    return {**default_config, **config}
            except Exception as e:
                logger.error(f"加載配置文件時發生錯誤: {e}")

        return default_config

    def register_producer(self, name: str, producer: Producer) -> bool:
        """
        註冊生產者

        Args:
            name: 生產者名稱
            producer: 生產者實例

        Returns:
            bool: 是否成功註冊
        """
        if name in self.producers:
            logger.warning(f"生產者 '{name}' 已存在")
            return False

        self.producers[name] = producer
        logger.info(f"已註冊生產者: {name}")
        return True

    def register_consumer(self, name: str, consumer: Consumer) -> bool:
        """
        註冊消費者

        Args:
            name: 消費者名稱
            consumer: 消費者實例

        Returns:
            bool: 是否成功註冊
        """
        if name in self.consumers:
            logger.warning(f"消費者 '{name}' 已存在")
            return False

        self.consumers[name] = consumer
        logger.info(f"已註冊消費者: {name}")
        return True

    def register_processor(self, name: str, processor: Processor) -> bool:
        """
        註冊處理器

        Args:
            name: 處理器名稱
            processor: 處理器實例

        Returns:
            bool: 是否成功註冊
        """
        if name in self.processors:
            logger.warning(f"處理器 '{name}' 已存在")
            return False

        self.processors[name] = processor
        logger.info(f"已註冊處理器: {name}")
        return True

    def register_pipeline(self, name: str, pipeline: Pipeline) -> bool:
        """
        註冊管道

        Args:
            name: 管道名稱
            pipeline: 管道實例

        Returns:
            bool: 是否成功註冊
        """
        if name in self.pipelines:
            logger.warning(f"管道 '{name}' 已存在")
            return False

        self.pipelines[name] = pipeline
        logger.info(f"已註冊管道: {name}")
        return True

    def subscribe(self, processor_name: str, message_types: List[MessageType]) -> bool:
        """
        訂閱消息類型

        Args:
            processor_name: 處理器名稱
            message_types: 消息類型列表

        Returns:
            bool: 是否成功訂閱
        """
        if processor_name not in self.processors:
            logger.warning(f"處理器 '{processor_name}' 不存在")
            return False

        for message_type in message_types:
            if message_type not in self.subscriptions:
                self.subscriptions[message_type] = []

            if processor_name not in self.subscriptions[message_type]:
                self.subscriptions[message_type].append(processor_name)

        logger.info(
            f"處理器 '{processor_name}' 已訂閱消息類型: {[mt.name for mt in message_types]}"
        )
        return True

    def unsubscribe(
        self, processor_name: str, message_types: Optional[List[MessageType]] = None
    ) -> bool:
        """
        取消訂閱消息類型

        Args:
            processor_name: 處理器名稱
            message_types: 消息類型列表，如果為None則取消所有訂閱

        Returns:
            bool: 是否成功取消訂閱
        """
        if processor_name not in self.processors:
            logger.warning(f"處理器 '{processor_name}' 不存在")
            return False

        if message_types is None:
            # 取消所有訂閱
            for subs in self.subscriptions.values():
                if processor_name in subs:
                    subs.remove(processor_name)

            logger.info(f"處理器 '{processor_name}' 已取消所有訂閱")
            return True

        # 取消特定訂閱
        for message_type in message_types:
            if (
                message_type in self.subscriptions
                and processor_name in self.subscriptions[message_type]
            ):
                self.subscriptions[message_type].remove(processor_name)

        logger.info(
            f"處理器 '{processor_name}' 已取消訂閱消息類型: {[mt.name for mt in message_types]}"
        )
        return True

    def publish(self, message: Message) -> bool:
        """
        發布消息

        Args:
            message: 消息實例

        Returns:
            bool: 是否成功發布
        """
        if not self.running:
            logger.warning("流管理器未運行，無法發布消息")
            return False

        try:
            # 獲取優先級
            priority = message.priority.value

            # 將消息放入隊列
            self.message_queue.put((priority, time.time(), message), block=False)

            # 更新統計信息
            self.stats["last_message_time"] = time.time()

            logger.debug(f"已發布消息: {message}")
            return True
        except queue.Full:
            # 隊列已滿，增加丟棄計數
            self.stats["messages_dropped"] += 1
            logger.error(f"消息隊列已滿，丟棄消息: {message}")
            return False
        except Exception as e:
            # 其他錯誤
            self.stats["errors"] += 1
            logger.error(f"發布消息時發生錯誤: {e}")
            return False

    def start(self) -> bool:
        """
        啟動流管理器

        Returns:
            bool: 是否成功啟動
        """
        if self.running:
            logger.warning("流管理器已經在運行中")
            return False

        try:
            # 啟動所有生產者
            for name, producer in self.producers.items():
                producer.start()

            # 啟動所有消費者
            for name, consumer in self.consumers.items():
                consumer.start()

            # 啟動所有處理器
            for name, processor in self.processors.items():
                processor.start()

            # 啟動所有管道
            for name, pipeline in self.pipelines.items():
                pipeline.start()

            # 啟動消息處理線程
            self.running = True
            self.processing_thread = threading.Thread(target=self._process_messages)
            self.processing_thread.daemon = True
            self.processing_thread.start()

            # 更新統計信息
            self.stats["start_time"] = time.time()

            logger.info("流管理器已啟動")
            return True
        except Exception as e:
            logger.error(f"啟動流管理器時發生錯誤: {e}")
            self.stop()
            return False

    def stop(self) -> bool:
        """
        停止流管理器

        Returns:
            bool: 是否成功停止
        """
        if not self.running:
            logger.warning("流管理器未運行")
            return False

        try:
            # 停止消息處理
            self.running = False
            if self.processing_thread:
                self.processing_thread.join(timeout=10)

            # 停止所有管道
            for name, pipeline in self.pipelines.items():
                pipeline.stop()

            # 停止所有處理器
            for name, processor in self.processors.items():
                processor.stop()

            # 停止所有消費者
            for name, consumer in self.consumers.items():
                consumer.stop()

            # 停止所有生產者
            for name, producer in self.producers.items():
                producer.stop()

            logger.info("流管理器已停止")
            return True
        except Exception as e:
            logger.error(f"停止流管理器時發生錯誤: {e}")
            return False

    def _process_messages(self):
        """處理消息隊列中的消息"""
        while self.running:
            try:
                # 從隊列中獲取消息
                try:
                    _, _, message = self.message_queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                # 檢查消息是否過期
                if message.is_expired():
                    logger.warning(f"消息已過期: {message}")
                    self.message_queue.task_done()
                    continue

                # 路由消息
                self._route_message(message)

                # 更新統計信息
                self.stats["messages_processed"] += 1

                # 標記任務完成
                self.message_queue.task_done()
            except Exception as e:
                # 更新錯誤計數
                self.stats["errors"] += 1
                logger.exception(f"處理消息時發生錯誤: {e}")
                time.sleep(0.1)  # 避免在錯誤情況下過度消耗 CPU

    def _route_message(self, message: Message):
        """
        路由消息到訂閱的處理器

        Args:
            message: 消息實例
        """
        # 檢查是否有處理器訂閱了此類型的消息
        if message.message_type not in self.subscriptions:
            logger.debug(f"沒有處理器訂閱消息類型: {message.message_type.name}")
            return

        # 獲取訂閱的處理器
        processor_names = self.subscriptions[message.message_type]

        # 如果指定了目的地，則只發送給指定的處理器
        if message.destination and message.destination in self.processors:
            if message.destination in processor_names:
                processor = self.processors[message.destination]
                try:
                    processor.process(message)
                except Exception as e:
                    logger.error(
                        f"處理器 '{message.destination}' 處理消息時發生錯誤: {e}"
                    )
            return

        # 發送給所有訂閱的處理器
        for processor_name in processor_names:
            processor = self.processors.get(processor_name)
            if processor:
                try:
                    processor.process(message)
                except Exception as e:
                    logger.error(f"處理器 '{processor_name}' 處理消息時發生錯誤: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """
        獲取統計信息

        Returns:
            Dict[str, Any]: 統計信息
        """
        # 計算運行時間
        uptime = (
            time.time() - self.stats["start_time"] if self.stats["start_time"] else 0
        )

        # 計算消息處理速率
        messages_per_second = (
            self.stats["messages_processed"] / uptime if uptime > 0 else 0
        )

        # 獲取隊列大小
        queue_size = self.message_queue.qsize()
        queue_capacity = self.message_queue.maxsize

        # 構建統計信息
        stats = {
            **self.stats,
            "uptime": uptime,
            "messages_per_second": messages_per_second,
            "queue_size": queue_size,
            "queue_capacity": queue_capacity,
            "queue_usage": queue_size / queue_capacity if queue_capacity > 0 else 0,
            "producers": len(self.producers),
            "consumers": len(self.consumers),
            "processors": len(self.processors),
            "pipelines": len(self.pipelines),
            "subscriptions": {k.name: v for k, v in self.subscriptions.items()},
            "running": self.running,
        }

        return stats


# 創建全局流管理器實例
stream_manager = StreamManager()
