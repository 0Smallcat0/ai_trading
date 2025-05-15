"""
消費者模組

此模組實現了各種數據消費者，用於從數據流中消費消息並處理。
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
logger = logging.getLogger("streaming.consumer")

# 嘗試導入 Kafka
try:
    from kafka import KafkaConsumer as KafkaClient
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("Kafka 套件未安裝，KafkaConsumer 將不可用")


class Consumer(ABC):
    """
    消費者抽象基類
    
    消費者負責：
    1. 從數據流中消費消息
    2. 處理消息
    3. 將處理結果發布到數據流
    """
    
    def __init__(self, name: str, stream_manager=None):
        """
        初始化消費者
        
        Args:
            name: 消費者名稱
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
            "messages_consumed": 0,
            "messages_published": 0,
            "errors": 0,
            "start_time": None,
            "last_message_time": None
        }
        
        logger.info(f"消費者 '{name}' 已初始化")
    
    def start(self):
        """啟動消費者"""
        if self.running:
            logger.warning(f"消費者 '{self.name}' 已經在運行中")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()
        
        # 更新統計信息
        self.stats["start_time"] = time.time()
        
        logger.info(f"消費者 '{self.name}' 已啟動")
    
    def stop(self):
        """停止消費者"""
        if not self.running:
            logger.warning(f"消費者 '{self.name}' 未運行")
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        
        logger.info(f"消費者 '{self.name}' 已停止")
    
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
            self.stats["messages_published"] += 1
        else:
            self.stats["errors"] += 1
        
        return result
    
    @abstractmethod
    def _run(self):
        """運行消費者的抽象方法，子類必須實現"""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """
        獲取統計信息
        
        Returns:
            Dict[str, Any]: 統計信息
        """
        # 計算運行時間
        uptime = time.time() - self.stats["start_time"] if self.stats["start_time"] else 0
        
        # 計算消息消費速率
        messages_per_second = self.stats["messages_consumed"] / uptime if uptime > 0 else 0
        
        # 構建統計信息
        stats = {
            **self.stats,
            "uptime": uptime,
            "messages_per_second": messages_per_second,
            "running": self.running
        }
        
        return stats


class WebSocketConsumer(Consumer):
    """
    WebSocket 消費者，將消息發送到 WebSocket
    """
    
    def __init__(
        self,
        name: str,
        url: str,
        message_types: List[MessageType],
        stream_manager=None,
        headers: Optional[Dict[str, str]] = None,
        on_connect: Optional[Callable] = None,
        message_converter: Optional[Callable[[Message], Any]] = None,
        reconnect_interval: int = 5,
        max_reconnect: int = 10
    ):
        """
        初始化 WebSocket 消費者
        
        Args:
            name: 消費者名稱
            url: WebSocket URL
            message_types: 要消費的消息類型列表
            stream_manager: 流管理器實例
            headers: HTTP 頭信息
            on_connect: 連接成功時的回調函數
            message_converter: 消息轉換函數，將 Message 實例轉換為 WebSocket 消息
            reconnect_interval: 重連間隔（秒）
            max_reconnect: 最大重連次數
        """
        super().__init__(name, stream_manager)
        self.url = url
        self.message_types = message_types
        self.headers = headers
        self.on_connect = on_connect
        self.message_converter = message_converter
        self.reconnect_interval = reconnect_interval
        self.max_reconnect = max_reconnect
        
        # WebSocket 客戶端
        self.ws = None
        self.reconnect_count = 0
        
        # 消息隊列
        self.message_queue = queue.Queue()
        
        logger.info(f"WebSocket 消費者 '{name}' 已初始化，URL: {url}")
    
    def _run(self):
        """運行 WebSocket 消費者"""
        # 訂閱消息類型
        for message_type in self.message_types:
            self.stream_manager.subscribe(self.name, [message_type])
        
        # 啟動 WebSocket 連接線程
        ws_thread = threading.Thread(target=self._run_websocket)
        ws_thread.daemon = True
        ws_thread.start()
        
        # 處理消息隊列
        while self.running:
            try:
                # 從隊列中獲取消息
                message = self.message_queue.get(timeout=0.1)
                
                # 如果 WebSocket 連接已建立
                if self.ws and self.ws.sock and self.ws.sock.connected:
                    # 如果提供了消息轉換函數，則使用它
                    if self.message_converter:
                        data = self.message_converter(message)
                    else:
                        # 默認轉換：將消息轉換為 JSON
                        data = json.dumps(message.to_dict())
                    
                    # 發送消息
                    self.ws.send(data)
                    
                    # 更新統計信息
                    self.stats["messages_consumed"] += 1
                    self.stats["last_message_time"] = time.time()
                else:
                    # WebSocket 未連接，將消息放回隊列
                    self.message_queue.put(message)
                    time.sleep(0.1)
                
                # 標記任務完成
                self.message_queue.task_done()
            except queue.Empty:
                # 隊列為空，繼續等待
                continue
            except Exception as e:
                logger.error(f"WebSocket 消費者 '{self.name}' 處理消息時發生錯誤: {e}")
                self.stats["errors"] += 1
                time.sleep(0.1)
    
    def _run_websocket(self):
        """運行 WebSocket 連接"""
        while self.running:
            try:
                # 創建 WebSocket 連接
                self.ws = websocket.WebSocketApp(
                    self.url,
                    header=self.headers,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                    on_open=self._on_open
                )
                
                # 運行 WebSocket 客戶端
                self.ws.run_forever()
                
                # 如果連接關閉且仍在運行，則嘗試重連
                if self.running:
                    self.reconnect_count += 1
                    if self.max_reconnect > 0 and self.reconnect_count > self.max_reconnect:
                        logger.error(f"WebSocket 消費者 '{self.name}' 重連次數超過上限 ({self.max_reconnect})，停止重連")
                        self.running = False
                        break
                    
                    logger.warning(f"WebSocket 消費者 '{self.name}' 連接關閉，{self.reconnect_interval} 秒後重連 (第 {self.reconnect_count} 次)")
                    time.sleep(self.reconnect_interval)
            except Exception as e:
                logger.error(f"WebSocket 消費者 '{self.name}' 運行時發生錯誤: {e}")
                self.stats["errors"] += 1
                time.sleep(self.reconnect_interval)
    
    def _on_message(self, ws, message):
        """
        WebSocket 消息處理函數
        
        Args:
            ws: WebSocket 連接
            message: 收到的消息
        """
        # WebSocket 消費者通常不處理接收到的消息
        logger.debug(f"WebSocket 消費者 '{self.name}' 收到消息: {message}")
    
    def _on_error(self, ws, error):
        """
        WebSocket 錯誤處理函數
        
        Args:
            ws: WebSocket 連接
            error: 錯誤
        """
        logger.error(f"WebSocket 消費者 '{self.name}' 發生錯誤: {error}")
        self.stats["errors"] += 1
    
    def _on_close(self, ws, close_status_code, close_msg):
        """
        WebSocket 關閉處理函數
        
        Args:
            ws: WebSocket 連接
            close_status_code: 關閉狀態碼
            close_msg: 關閉消息
        """
        logger.info(f"WebSocket 消費者 '{self.name}' 連接關閉: {close_status_code} {close_msg}")
    
    def _on_open(self, ws):
        """
        WebSocket 打開處理函數
        
        Args:
            ws: WebSocket 連接
        """
        logger.info(f"WebSocket 消費者 '{self.name}' 連接成功")
        self.reconnect_count = 0
        
        # 如果提供了連接回調，則調用它
        if self.on_connect:
            try:
                self.on_connect(ws)
            except Exception as e:
                logger.error(f"WebSocket 消費者 '{self.name}' 連接回調時發生錯誤: {e}")
                self.stats["errors"] += 1
    
    def process(self, message: Message):
        """
        處理消息
        
        Args:
            message: 消息實例
        """
        try:
            # 將消息放入隊列
            self.message_queue.put(message, block=False)
        except queue.Full:
            logger.error(f"WebSocket 消費者 '{self.name}' 消息隊列已滿")
            self.stats["errors"] += 1


class KafkaConsumer(Consumer):
    """
    Kafka 消費者，從 Kafka 消費消息
    """
    
    def __init__(
        self,
        name: str,
        bootstrap_servers: Union[str, List[str]],
        topics: List[str],
        stream_manager=None,
        group_id: Optional[str] = None,
        message_converter: Optional[Callable[[Any], Message]] = None,
        **kafka_config
    ):
        """
        初始化 Kafka 消費者
        
        Args:
            name: 消費者名稱
            bootstrap_servers: Kafka 服務器地址
            topics: Kafka 主題列表
            stream_manager: 流管理器實例
            group_id: 消費者組 ID
            message_converter: 消息轉換函數，將 Kafka 消息轉換為 Message 實例
            **kafka_config: Kafka 配置參數
        """
        if not KAFKA_AVAILABLE:
            raise ImportError("Kafka 套件未安裝，請先安裝: pip install kafka-python")
        
        super().__init__(name, stream_manager)
        self.bootstrap_servers = bootstrap_servers
        self.topics = topics
        self.group_id = group_id or f"consumer-{name}"
        self.message_converter = message_converter
        self.kafka_config = kafka_config
        
        # Kafka 客戶端
        self.consumer = None
        
        logger.info(f"Kafka 消費者 '{name}' 已初始化，服務器: {bootstrap_servers}, 主題: {topics}")
    
    def _run(self):
        """運行 Kafka 消費者"""
        try:
            # 創建 Kafka 消費者
            self.consumer = KafkaClient(
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                **self.kafka_config
            )
            
            # 訂閱主題
            self.consumer.subscribe(self.topics)
            
            # 消費消息
            for kafka_message in self.consumer:
                if not self.running:
                    break
                
                try:
                    # 獲取消息值
                    value = kafka_message.value
                    
                    # 如果提供了消息轉換函數，則使用它
                    if self.message_converter:
                        message = self.message_converter(value)
                    else:
                        # 默認轉換：嘗試將值轉換為 Message 實例
                        try:
                            message = Message.from_dict(value)
                        except Exception:
                            # 如果轉換失敗，則創建一個新的消息
                            message = Message(
                                message_type=MessageType.INFO,
                                data=value,
                                source=f"kafka-{kafka_message.topic}"
                            )
                    
                    # 發布消息
                    self.publish(message)
                    
                    # 更新統計信息
                    self.stats["messages_consumed"] += 1
                    self.stats["last_message_time"] = time.time()
                except Exception as e:
                    logger.error(f"Kafka 消費者 '{self.name}' 處理消息時發生錯誤: {e}")
                    self.stats["errors"] += 1
        except Exception as e:
            logger.error(f"Kafka 消費者 '{self.name}' 運行時發生錯誤: {e}")
            self.stats["errors"] += 1
        finally:
            # 關閉 Kafka 消費者
            if self.consumer:
                self.consumer.close()
    
    def process(self, message: Message):
        """
        處理消息
        
        Args:
            message: 消息實例
        """
        # Kafka 消費者通常不處理來自流管理器的消息
        logger.debug(f"Kafka 消費者 '{self.name}' 收到消息: {message}")
