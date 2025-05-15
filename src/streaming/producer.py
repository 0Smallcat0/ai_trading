"""
生產者模組

此模組實現了各種數據生產者，用於從不同來源獲取數據並發布到數據流中。
"""

import logging
import threading
import time
import json
import websocket
import queue
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime

from .message import Message, MessageType, MessagePriority

# 設定日誌
logger = logging.getLogger("streaming.producer")

# 嘗試導入 Kafka
try:
    from kafka import KafkaProducer as KafkaClient

    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("Kafka 套件未安裝，KafkaProducer 將不可用")


class Producer(ABC):
    """
    生產者抽象基類

    生產者負責：
    1. 從數據源獲取數據
    2. 將數據轉換為消息
    3. 發布消息到數據流
    """

    def __init__(self, name: str, stream_manager=None):
        """
        初始化生產者

        Args:
            name: 生產者名稱
            stream_manager: 流管理器實例，如果為None則使用全局實例
        """
        self.name = name
        self.running = False
        self.thread = None

        # 如果未提供流管理器，則導入全局實例
        if stream_manager is None:
            from .stream_manager import stream_manager
        self.stream_manager = stream_manager

        # 統計信息
        self.stats = {
            "messages_produced": 0,
            "errors": 0,
            "start_time": None,
            "last_message_time": None,
        }

        logger.info(f"生產者 '{name}' 已初始化")

    def start(self):
        """啟動生產者"""
        if self.running:
            logger.warning(f"生產者 '{self.name}' 已經在運行中")
            return

        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

        # 更新統計信息
        self.stats["start_time"] = time.time()

        logger.info(f"生產者 '{self.name}' 已啟動")

    def stop(self):
        """停止生產者"""
        if not self.running:
            logger.warning(f"生產者 '{self.name}' 未運行")
            return

        self.running = False
        if self.thread:
            self.thread.join(timeout=10)

        logger.info(f"生產者 '{self.name}' 已停止")

    def publish(self, message: Message) -> bool:
        """
        發布消息

        Args:
            message: 消息實例

        Returns:
            bool: 是否成功發布
        """
        # 設置消息來源
        if not message.source:
            message.source = self.name

        # 發布消息
        result = self.stream_manager.publish(message)

        # 更新統計信息
        if result:
            self.stats["messages_produced"] += 1
            self.stats["last_message_time"] = time.time()
        else:
            self.stats["errors"] += 1

        return result

    @abstractmethod
    def _run(self):
        """運行生產者的抽象方法，子類必須實現"""
        pass

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

        # 計算消息生產速率
        messages_per_second = (
            self.stats["messages_produced"] / uptime if uptime > 0 else 0
        )

        # 構建統計信息
        stats = {
            **self.stats,
            "uptime": uptime,
            "messages_per_second": messages_per_second,
            "running": self.running,
        }

        return stats


class WebSocketProducer(Producer):
    """
    WebSocket 生產者，從 WebSocket 獲取數據
    """

    def __init__(
        self,
        name: str,
        url: str,
        message_type: MessageType,
        stream_manager=None,
        headers: Optional[Dict[str, str]] = None,
        on_connect: Optional[Callable] = None,
        message_converter: Optional[Callable[[Any], Message]] = None,
        reconnect_interval: int = 5,
        max_reconnect: int = 10,
    ):
        """
        初始化 WebSocket 生產者

        Args:
            name: 生產者名稱
            url: WebSocket URL
            message_type: 消息類型
            stream_manager: 流管理器實例
            headers: HTTP 頭信息
            on_connect: 連接成功時的回調函數
            message_converter: 消息轉換函數，將 WebSocket 消息轉換為 Message 實例
            reconnect_interval: 重連間隔（秒）
            max_reconnect: 最大重連次數
        """
        super().__init__(name, stream_manager)
        self.url = url
        self.message_type = message_type
        self.headers = headers
        self.on_connect = on_connect
        self.message_converter = message_converter
        self.reconnect_interval = reconnect_interval
        self.max_reconnect = max_reconnect

        # WebSocket 客戶端
        self.ws = None
        self.reconnect_count = 0

        logger.info(f"WebSocket 生產者 '{name}' 已初始化，URL: {url}")

    def _run(self):
        """運行 WebSocket 生產者"""
        while self.running:
            try:
                # 創建 WebSocket 連接
                self.ws = websocket.WebSocketApp(
                    self.url,
                    header=self.headers,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open,
                )

                # 運行 WebSocket 客戶端
                self.ws.run_forever()

                # 如果連接關閉且仍在運行，則嘗試重連
                if self.running:
                    self.reconnect_count += 1
                    if (
                        self.max_reconnect > 0
                        and self.reconnect_count > self.max_reconnect
                    ):
                        logger.error(
                            f"WebSocket 生產者 '{self.name}' 重連次數超過上限 ({self.max_reconnect})，停止重連"
                        )
                        self.running = False
                        break

                    logger.warning(
                        f"WebSocket 生產者 '{self.name}' 連接關閉，{self.reconnect_interval} 秒後重連 (第 {self.reconnect_count} 次)"
                    )
                    time.sleep(self.reconnect_interval)
            except Exception as e:
                logger.error(f"WebSocket 生產者 '{self.name}' 運行時發生錯誤: {e}")
                self.stats["errors"] += 1
                time.sleep(self.reconnect_interval)

    def _on_message(self, ws, message):
        """
        WebSocket 消息處理函數

        Args:
            ws: WebSocket 連接
            message: 收到的消息
        """
        try:
            # 如果提供了消息轉換函數，則使用它
            if self.message_converter:
                msg = self.message_converter(message)
                if msg:
                    self.publish(msg)
            else:
                # 默認處理：嘗試解析 JSON
                try:
                    data = json.loads(message)
                    msg = Message(
                        message_type=self.message_type, data=data, source=self.name
                    )
                    self.publish(msg)
                except json.JSONDecodeError:
                    # 如果不是 JSON，則作為字符串處理
                    msg = Message(
                        message_type=self.message_type,
                        data={"raw": message},
                        source=self.name,
                    )
                    self.publish(msg)
        except Exception as e:
            logger.error(f"WebSocket 生產者 '{self.name}' 處理消息時發生錯誤: {e}")
            self.stats["errors"] += 1

    def _on_error(self, ws, error):
        """
        WebSocket 錯誤處理函數

        Args:
            ws: WebSocket 連接
            error: 錯誤
        """
        logger.error(f"WebSocket 生產者 '{self.name}' 發生錯誤: {error}")
        self.stats["errors"] += 1

    def _on_close(self, ws, close_status_code, close_msg):
        """
        WebSocket 關閉處理函數

        Args:
            ws: WebSocket 連接
            close_status_code: 關閉狀態碼
            close_msg: 關閉消息
        """
        logger.info(
            f"WebSocket 生產者 '{self.name}' 連接關閉: {close_status_code} {close_msg}"
        )

    def _on_open(self, ws):
        """
        WebSocket 打開處理函數

        Args:
            ws: WebSocket 連接
        """
        logger.info(f"WebSocket 生產者 '{self.name}' 連接成功")
        self.reconnect_count = 0

        # 如果提供了連接回調，則調用它
        if self.on_connect:
            try:
                self.on_connect(ws)
            except Exception as e:
                logger.error(f"WebSocket 生產者 '{self.name}' 連接回調時發生錯誤: {e}")
                self.stats["errors"] += 1


class KafkaProducer(Producer):
    """
    Kafka 生產者，將消息發布到 Kafka
    """

    def __init__(
        self,
        name: str,
        bootstrap_servers: Union[str, List[str]],
        topic: str,
        stream_manager=None,
        **kafka_config,
    ):
        """
        初始化 Kafka 生產者

        Args:
            name: 生產者名稱
            bootstrap_servers: Kafka 服務器地址
            topic: Kafka 主題
            stream_manager: 流管理器實例
            **kafka_config: Kafka 配置參數
        """
        if not KAFKA_AVAILABLE:
            raise ImportError("Kafka 套件未安裝，請先安裝: pip install kafka-python")

        super().__init__(name, stream_manager)
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.kafka_config = kafka_config

        # Kafka 客戶端
        self.producer = None

        # 消息隊列
        self.message_queue = queue.Queue()

        logger.info(
            f"Kafka 生產者 '{name}' 已初始化，服務器: {bootstrap_servers}, 主題: {topic}"
        )

    def _run(self):
        """運行 Kafka 生產者"""
        try:
            # 創建 Kafka 生產者
            self.producer = KafkaClient(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                **self.kafka_config,
            )

            # 處理消息隊列
            while self.running:
                try:
                    # 從隊列中獲取消息
                    message = self.message_queue.get(timeout=0.1)

                    # 發送消息到 Kafka
                    self.producer.send(self.topic, value=message.to_dict())

                    # 標記任務完成
                    self.message_queue.task_done()

                    # 更新統計信息
                    self.stats["messages_produced"] += 1
                    self.stats["last_message_time"] = time.time()
                except queue.Empty:
                    # 隊列為空，繼續等待
                    continue
                except Exception as e:
                    logger.error(f"Kafka 生產者 '{self.name}' 發送消息時發生錯誤: {e}")
                    self.stats["errors"] += 1
                    time.sleep(1)  # 避免在錯誤情況下過度消耗 CPU
        except Exception as e:
            logger.error(f"Kafka 生產者 '{self.name}' 運行時發生錯誤: {e}")
            self.stats["errors"] += 1
        finally:
            # 關閉 Kafka 生產者
            if self.producer:
                self.producer.close()

    def publish(self, message: Message) -> bool:
        """
        發布消息到 Kafka

        Args:
            message: 消息實例

        Returns:
            bool: 是否成功發布
        """
        try:
            # 設置消息來源
            if not message.source:
                message.source = self.name

            # 將消息放入隊列
            self.message_queue.put(message, block=False)
            return True
        except queue.Full:
            logger.error(f"Kafka 生產者 '{self.name}' 消息隊列已滿")
            self.stats["errors"] += 1
            return False
        except Exception as e:
            logger.error(f"Kafka 生產者 '{self.name}' 發布消息時發生錯誤: {e}")
            self.stats["errors"] += 1
            return False
