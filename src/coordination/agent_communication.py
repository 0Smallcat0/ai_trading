# -*- coding: utf-8 -*-
"""
代理間通信優化模組

此模組實現高效的代理間通信機制，支持異步消息傳遞、
事件驅動架構和消息隊列管理。

核心功能：
- 異步消息傳遞
- 事件驅動通信
- 消息隊列管理
- 廣播和點對點通信
- 消息持久化和恢復

通信模式：
- 發布-訂閱（Publish-Subscribe）
- 請求-響應（Request-Response）
- 廣播（Broadcast）
- 點對點（Peer-to-Peer）
- 事件流（Event Streaming）
"""

import logging
import asyncio
import json
import threading
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
import queue
import uuid

# 設定日誌
logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息類型枚舉"""
    DECISION = "decision"                     # 決策消息
    PERFORMANCE_UPDATE = "performance_update"  # 績效更新
    MARKET_DATA = "market_data"              # 市場數據
    COORDINATION_REQUEST = "coordination_request"  # 協調請求
    ALLOCATION_UPDATE = "allocation_update"   # 配置更新
    SYSTEM_EVENT = "system_event"            # 系統事件
    HEARTBEAT = "heartbeat"                  # 心跳消息
    ERROR = "error"                          # 錯誤消息


class MessagePriority(Enum):
    """消息優先級枚舉"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class CommunicationMode(Enum):
    """通信模式枚舉"""
    SYNC = "synchronous"                     # 同步
    ASYNC = "asynchronous"                   # 異步
    BROADCAST = "broadcast"                  # 廣播
    MULTICAST = "multicast"                  # 組播
    UNICAST = "unicast"                      # 單播


@dataclass
class Message:
    """消息對象"""
    id: str                                  # 消息ID
    type: MessageType                        # 消息類型
    sender: str                              # 發送者
    recipient: Optional[str]                 # 接收者（None表示廣播）
    content: Dict[str, Any]                  # 消息內容
    priority: MessagePriority                # 優先級
    timestamp: datetime                      # 時間戳
    expires_at: Optional[datetime]           # 過期時間
    correlation_id: Optional[str]            # 關聯ID
    reply_to: Optional[str]                  # 回復地址
    metadata: Dict[str, Any]                 # 元數據
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            'id': self.id,
            'type': self.type.value,
            'sender': self.sender,
            'recipient': self.recipient,
            'content': self.content,
            'priority': self.priority.value,
            'timestamp': self.timestamp.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'correlation_id': self.correlation_id,
            'reply_to': self.reply_to,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """從字典創建消息"""
        return cls(
            id=data['id'],
            type=MessageType(data['type']),
            sender=data['sender'],
            recipient=data.get('recipient'),
            content=data['content'],
            priority=MessagePriority(data['priority']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            correlation_id=data.get('correlation_id'),
            reply_to=data.get('reply_to'),
            metadata=data.get('metadata', {})
        )


@dataclass
class CommunicationStats:
    """通信統計"""
    total_messages_sent: int = 0
    total_messages_received: int = 0
    messages_by_type: Dict[str, int] = None
    average_latency: float = 0.0
    failed_deliveries: int = 0
    queue_sizes: Dict[str, int] = None
    active_connections: int = 0
    
    def __post_init__(self):
        if self.messages_by_type is None:
            self.messages_by_type = defaultdict(int)
        if self.queue_sizes is None:
            self.queue_sizes = {}


class AgentCommunication:
    """
    代理間通信管理器 - 高效異步通信的核心組件。
    
    提供多種通信模式和消息傳遞機制，支持大規模代理間協作。
    
    Attributes:
        max_queue_size (int): 最大隊列大小
        message_ttl (int): 消息生存時間（秒）
        heartbeat_interval (int): 心跳間隔（秒）
        max_retry_attempts (int): 最大重試次數
        enable_persistence (bool): 是否啟用持久化
        compression_enabled (bool): 是否啟用壓縮
    """
    
    def __init__(
        self,
        max_queue_size: int = 10000,
        message_ttl: int = 3600,
        heartbeat_interval: int = 30,
        max_retry_attempts: int = 3,
        enable_persistence: bool = False,
        compression_enabled: bool = False
    ) -> None:
        """
        初始化代理間通信管理器。
        
        Args:
            max_queue_size: 最大隊列大小
            message_ttl: 消息生存時間（秒）
            heartbeat_interval: 心跳間隔（秒）
            max_retry_attempts: 最大重試次數
            enable_persistence: 是否啟用持久化
            compression_enabled: 是否啟用壓縮
        """
        self.max_queue_size = max_queue_size
        self.message_ttl = message_ttl
        self.heartbeat_interval = heartbeat_interval
        self.max_retry_attempts = max_retry_attempts
        self.enable_persistence = enable_persistence
        self.compression_enabled = compression_enabled
        
        # 消息隊列（按代理ID分組）
        self.message_queues: Dict[str, queue.PriorityQueue] = defaultdict(
            lambda: queue.PriorityQueue(maxsize=max_queue_size)
        )
        
        # 訂閱管理
        self.subscriptions: Dict[MessageType, List[str]] = defaultdict(list)
        self.message_handlers: Dict[str, Dict[MessageType, Callable]] = defaultdict(dict)
        
        # 代理註冊
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_status: Dict[str, str] = {}  # online, offline, busy
        
        # 異步事件循環
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # 通信統計
        self.stats = CommunicationStats()
        self.message_history: deque = deque(maxlen=1000)
        
        # 控制標誌
        self.running = False
        self.background_tasks: List[asyncio.Task] = []
        
        # 線程安全鎖
        self.lock = threading.RLock()
        
        logger.info("初始化代理間通信管理器")
    
    def start(self) -> None:
        """啟動通信管理器"""
        if self.running:
            logger.warning("通信管理器已在運行")
            return
        
        self.running = True
        
        # 啟動事件循環
        if self.event_loop is None:
            self.event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.event_loop)
        
        # 啟動後台任務
        self._start_background_tasks()
        
        logger.info("代理間通信管理器已啟動")
    
    def stop(self) -> None:
        """停止通信管理器"""
        if not self.running:
            return
        
        self.running = False
        
        # 取消後台任務
        for task in self.background_tasks:
            task.cancel()
        
        # 關閉執行器
        self.executor.shutdown(wait=True)
        
        logger.info("代理間通信管理器已停止")
    
    def register_agent(
        self,
        agent_id: str,
        agent_info: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        註冊代理。
        
        Args:
            agent_id: 代理ID
            agent_info: 代理信息
            
        Returns:
            bool: 註冊是否成功
        """
        try:
            with self.lock:
                if agent_id in self.registered_agents:
                    logger.warning(f"代理 {agent_id} 已註冊")
                    return False
                
                self.registered_agents[agent_id] = agent_info or {}
                self.agent_status[agent_id] = "online"
                
                # 創建消息隊列
                if agent_id not in self.message_queues:
                    self.message_queues[agent_id] = queue.PriorityQueue(maxsize=self.max_queue_size)
                
                logger.info(f"代理 {agent_id} 註冊成功")
                return True
                
        except Exception as e:
            logger.error(f"代理 {agent_id} 註冊失敗: {e}")
            return False
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        取消註冊代理。
        
        Args:
            agent_id: 代理ID
            
        Returns:
            bool: 取消註冊是否成功
        """
        try:
            with self.lock:
                if agent_id not in self.registered_agents:
                    logger.warning(f"代理 {agent_id} 未註冊")
                    return False
                
                # 清理資源
                del self.registered_agents[agent_id]
                del self.agent_status[agent_id]
                
                # 清空消息隊列
                if agent_id in self.message_queues:
                    while not self.message_queues[agent_id].empty():
                        try:
                            self.message_queues[agent_id].get_nowait()
                        except queue.Empty:
                            break
                    del self.message_queues[agent_id]
                
                # 清理訂閱
                for message_type, subscribers in self.subscriptions.items():
                    if agent_id in subscribers:
                        subscribers.remove(agent_id)
                
                if agent_id in self.message_handlers:
                    del self.message_handlers[agent_id]
                
                logger.info(f"代理 {agent_id} 取消註冊成功")
                return True
                
        except Exception as e:
            logger.error(f"代理 {agent_id} 取消註冊失敗: {e}")
            return False

    def subscribe(
        self,
        agent_id: str,
        message_type: MessageType,
        handler: Optional[Callable[[Message], None]] = None
    ) -> bool:
        """
        訂閱消息類型。

        Args:
            agent_id: 代理ID
            message_type: 消息類型
            handler: 消息處理函數

        Returns:
            bool: 訂閱是否成功
        """
        try:
            with self.lock:
                if agent_id not in self.registered_agents:
                    logger.error(f"代理 {agent_id} 未註冊")
                    return False

                if agent_id not in self.subscriptions[message_type]:
                    self.subscriptions[message_type].append(agent_id)

                if handler:
                    self.message_handlers[agent_id][message_type] = handler

                logger.info(f"代理 {agent_id} 訂閱消息類型 {message_type.value}")
                return True

        except Exception as e:
            logger.error(f"代理 {agent_id} 訂閱失敗: {e}")
            return False

    def unsubscribe(self, agent_id: str, message_type: MessageType) -> bool:
        """
        取消訂閱消息類型。

        Args:
            agent_id: 代理ID
            message_type: 消息類型

        Returns:
            bool: 取消訂閱是否成功
        """
        try:
            with self.lock:
                if agent_id in self.subscriptions[message_type]:
                    self.subscriptions[message_type].remove(agent_id)

                if agent_id in self.message_handlers and message_type in self.message_handlers[agent_id]:
                    del self.message_handlers[agent_id][message_type]

                logger.info(f"代理 {agent_id} 取消訂閱消息類型 {message_type.value}")
                return True

        except Exception as e:
            logger.error(f"代理 {agent_id} 取消訂閱失敗: {e}")
            return False

    def send_message(
        self,
        sender: str,
        message_type: MessageType,
        content: Dict[str, Any],
        recipient: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        ttl: Optional[int] = None,
        correlation_id: Optional[str] = None
    ) -> Optional[str]:
        """
        發送消息。

        Args:
            sender: 發送者ID
            message_type: 消息類型
            content: 消息內容
            recipient: 接收者ID（None表示廣播）
            priority: 消息優先級
            ttl: 生存時間（秒）
            correlation_id: 關聯ID

        Returns:
            Optional[str]: 消息ID
        """
        try:
            # 創建消息
            message_id = str(uuid.uuid4())
            expires_at = None
            if ttl:
                expires_at = datetime.now() + timedelta(seconds=ttl)
            elif self.message_ttl > 0:
                expires_at = datetime.now() + timedelta(seconds=self.message_ttl)

            message = Message(
                id=message_id,
                type=message_type,
                sender=sender,
                recipient=recipient,
                content=content,
                priority=priority,
                timestamp=datetime.now(),
                expires_at=expires_at,
                correlation_id=correlation_id,
                reply_to=None,
                metadata={}
            )

            # 路由消息
            if recipient:
                # 點對點消息
                success = self._route_unicast_message(message)
            else:
                # 廣播消息
                success = self._route_broadcast_message(message)

            if success:
                # 更新統計
                with self.lock:
                    self.stats.total_messages_sent += 1
                    self.stats.messages_by_type[message_type.value] += 1
                    self.message_history.append(message)

                logger.debug(f"消息 {message_id} 發送成功")
                return message_id
            else:
                logger.error(f"消息 {message_id} 發送失敗")
                return None

        except Exception as e:
            logger.error(f"發送消息失敗: {e}")
            return None

    def receive_message(self, agent_id: str, timeout: Optional[float] = None) -> Optional[Message]:
        """
        接收消息。

        Args:
            agent_id: 代理ID
            timeout: 超時時間（秒）

        Returns:
            Optional[Message]: 接收到的消息
        """
        try:
            if agent_id not in self.message_queues:
                logger.error(f"代理 {agent_id} 消息隊列不存在")
                return None

            message_queue = self.message_queues[agent_id]

            # 從隊列獲取消息（優先級隊列）
            try:
                priority_item = message_queue.get(timeout=timeout)
                priority, message = priority_item

                # 檢查消息是否過期
                if message.expires_at and datetime.now() > message.expires_at:
                    logger.debug(f"消息 {message.id} 已過期")
                    return None

                # 更新統計
                with self.lock:
                    self.stats.total_messages_received += 1

                logger.debug(f"代理 {agent_id} 接收消息 {message.id}")
                return message

            except queue.Empty:
                return None

        except Exception as e:
            logger.error(f"代理 {agent_id} 接收消息失敗: {e}")
            return None

    def broadcast_message(
        self,
        sender: str,
        message_type: MessageType,
        content: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> List[str]:
        """
        廣播消息給所有訂閱者。

        Args:
            sender: 發送者ID
            message_type: 消息類型
            content: 消息內容
            priority: 消息優先級

        Returns:
            List[str]: 成功接收的代理ID列表
        """
        successful_recipients = []

        try:
            subscribers = self.subscriptions.get(message_type, [])

            for recipient in subscribers:
                if recipient != sender:  # 不發送給自己
                    message_id = self.send_message(
                        sender=sender,
                        message_type=message_type,
                        content=content,
                        recipient=recipient,
                        priority=priority
                    )

                    if message_id:
                        successful_recipients.append(recipient)

            logger.info(f"廣播消息給 {len(successful_recipients)} 個代理")
            return successful_recipients

        except Exception as e:
            logger.error(f"廣播消息失敗: {e}")
            return successful_recipients

    def send_request(
        self,
        sender: str,
        recipient: str,
        message_type: MessageType,
        content: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Message]:
        """
        發送請求並等待響應。

        Args:
            sender: 發送者ID
            recipient: 接收者ID
            message_type: 消息類型
            content: 消息內容
            timeout: 超時時間（秒）

        Returns:
            Optional[Message]: 響應消息
        """
        try:
            correlation_id = str(uuid.uuid4())

            # 發送請求
            request_id = self.send_message(
                sender=sender,
                message_type=message_type,
                content=content,
                recipient=recipient,
                correlation_id=correlation_id
            )

            if not request_id:
                return None

            # 等待響應
            start_time = datetime.now()
            while (datetime.now() - start_time).total_seconds() < timeout:
                response = self.receive_message(sender, timeout=1.0)

                if response and response.correlation_id == correlation_id:
                    return response

            logger.warning(f"請求 {request_id} 超時")
            return None

        except Exception as e:
            logger.error(f"發送請求失敗: {e}")
            return None

    def send_response(
        self,
        sender: str,
        original_message: Message,
        response_content: Dict[str, Any]
    ) -> Optional[str]:
        """
        發送響應消息。

        Args:
            sender: 發送者ID
            original_message: 原始請求消息
            response_content: 響應內容

        Returns:
            Optional[str]: 響應消息ID
        """
        try:
            return self.send_message(
                sender=sender,
                message_type=original_message.type,
                content=response_content,
                recipient=original_message.sender,
                correlation_id=original_message.correlation_id
            )

        except Exception as e:
            logger.error(f"發送響應失敗: {e}")
            return None

    def _route_unicast_message(self, message: Message) -> bool:
        """路由點對點消息"""
        try:
            recipient = message.recipient

            if recipient not in self.registered_agents:
                logger.error(f"接收者 {recipient} 未註冊")
                return False

            if recipient not in self.message_queues:
                logger.error(f"接收者 {recipient} 消息隊列不存在")
                return False

            # 檢查隊列是否已滿
            message_queue = self.message_queues[recipient]
            if message_queue.full():
                logger.warning(f"代理 {recipient} 消息隊列已滿")
                return False

            # 添加到隊列（優先級隊列）
            priority_value = 5 - message.priority.value  # 反轉優先級（數字越小優先級越高）
            message_queue.put((priority_value, message))

            # 觸發消息處理器
            self._trigger_message_handler(recipient, message)

            return True

        except Exception as e:
            logger.error(f"路由點對點消息失敗: {e}")
            return False

    def _route_broadcast_message(self, message: Message) -> bool:
        """路由廣播消息"""
        try:
            subscribers = self.subscriptions.get(message.type, [])
            success_count = 0

            for recipient in subscribers:
                if recipient != message.sender:  # 不發送給自己
                    # 創建副本消息
                    recipient_message = Message(
                        id=message.id,
                        type=message.type,
                        sender=message.sender,
                        recipient=recipient,
                        content=message.content,
                        priority=message.priority,
                        timestamp=message.timestamp,
                        expires_at=message.expires_at,
                        correlation_id=message.correlation_id,
                        reply_to=message.reply_to,
                        metadata=message.metadata
                    )

                    if self._route_unicast_message(recipient_message):
                        success_count += 1

            return success_count > 0

        except Exception as e:
            logger.error(f"路由廣播消息失敗: {e}")
            return False

    def _trigger_message_handler(self, agent_id: str, message: Message) -> None:
        """觸發消息處理器"""
        try:
            if agent_id in self.message_handlers:
                handler = self.message_handlers[agent_id].get(message.type)
                if handler:
                    # 在線程池中異步執行處理器
                    self.executor.submit(self._safe_handler_execution, handler, message)

        except Exception as e:
            logger.error(f"觸發消息處理器失敗: {e}")

    def _safe_handler_execution(self, handler: Callable, message: Message) -> None:
        """安全執行消息處理器"""
        try:
            handler(message)
        except Exception as e:
            logger.error(f"消息處理器執行失敗: {e}")

    def _start_background_tasks(self) -> None:
        """啟動後台任務"""
        if self.event_loop:
            # 心跳任務
            heartbeat_task = self.event_loop.create_task(self._heartbeat_task())
            self.background_tasks.append(heartbeat_task)

            # 消息清理任務
            cleanup_task = self.event_loop.create_task(self._message_cleanup_task())
            self.background_tasks.append(cleanup_task)

            # 統計更新任務
            stats_task = self.event_loop.create_task(self._stats_update_task())
            self.background_tasks.append(stats_task)

    async def _heartbeat_task(self) -> None:
        """心跳任務"""
        while self.running:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                # 發送心跳消息
                for agent_id in list(self.registered_agents.keys()):
                    if self.agent_status.get(agent_id) == "online":
                        self.send_message(
                            sender="system",
                            message_type=MessageType.HEARTBEAT,
                            content={"timestamp": datetime.now().isoformat()},
                            recipient=agent_id,
                            priority=MessagePriority.LOW
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳任務錯誤: {e}")

    async def _message_cleanup_task(self) -> None:
        """消息清理任務"""
        while self.running:
            try:
                await asyncio.sleep(300)  # 每5分鐘清理一次

                current_time = datetime.now()

                # 清理過期消息
                for agent_id, message_queue in self.message_queues.items():
                    temp_messages = []

                    # 取出所有消息
                    while not message_queue.empty():
                        try:
                            priority, message = message_queue.get_nowait()

                            # 檢查是否過期
                            if not message.expires_at or current_time <= message.expires_at:
                                temp_messages.append((priority, message))

                        except queue.Empty:
                            break

                    # 重新放入未過期的消息
                    for priority, message in temp_messages:
                        try:
                            message_queue.put_nowait((priority, message))
                        except queue.Full:
                            logger.warning(f"代理 {agent_id} 消息隊列已滿，丟棄消息")
                            break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"消息清理任務錯誤: {e}")

    async def _stats_update_task(self) -> None:
        """統計更新任務"""
        while self.running:
            try:
                await asyncio.sleep(60)  # 每分鐘更新一次

                with self.lock:
                    # 更新隊列大小統計
                    self.stats.queue_sizes = {
                        agent_id: queue.qsize()
                        for agent_id, queue in self.message_queues.items()
                    }

                    # 更新活躍連接數
                    self.stats.active_connections = len([
                        agent_id for agent_id, status in self.agent_status.items()
                        if status == "online"
                    ])

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"統計更新任務錯誤: {e}")

    def get_agent_status(self, agent_id: str) -> Optional[str]:
        """獲取代理狀態"""
        return self.agent_status.get(agent_id)

    def set_agent_status(self, agent_id: str, status: str) -> bool:
        """設置代理狀態"""
        try:
            if agent_id in self.registered_agents:
                self.agent_status[agent_id] = status
                logger.info(f"代理 {agent_id} 狀態設置為 {status}")
                return True
            else:
                logger.error(f"代理 {agent_id} 未註冊")
                return False

        except Exception as e:
            logger.error(f"設置代理狀態失敗: {e}")
            return False

    def get_queue_size(self, agent_id: str) -> int:
        """獲取代理消息隊列大小"""
        if agent_id in self.message_queues:
            return self.message_queues[agent_id].qsize()
        return 0

    def clear_queue(self, agent_id: str) -> int:
        """清空代理消息隊列"""
        cleared_count = 0

        if agent_id in self.message_queues:
            message_queue = self.message_queues[agent_id]

            while not message_queue.empty():
                try:
                    message_queue.get_nowait()
                    cleared_count += 1
                except queue.Empty:
                    break

        logger.info(f"清空代理 {agent_id} 消息隊列，清除 {cleared_count} 條消息")
        return cleared_count

    def get_communication_stats(self) -> CommunicationStats:
        """獲取通信統計"""
        with self.lock:
            return CommunicationStats(
                total_messages_sent=self.stats.total_messages_sent,
                total_messages_received=self.stats.total_messages_received,
                messages_by_type=dict(self.stats.messages_by_type),
                average_latency=self.stats.average_latency,
                failed_deliveries=self.stats.failed_deliveries,
                queue_sizes=self.stats.queue_sizes.copy(),
                active_connections=self.stats.active_connections
            )

    def get_registered_agents(self) -> List[str]:
        """獲取已註冊代理列表"""
        return list(self.registered_agents.keys())

    def get_subscriptions(self) -> Dict[str, List[str]]:
        """獲取訂閱信息"""
        return {
            message_type.value: subscribers.copy()
            for message_type, subscribers in self.subscriptions.items()
        }

    def get_message_history(self, limit: Optional[int] = None) -> List[Message]:
        """獲取消息歷史"""
        if limit:
            return list(self.message_history)[-limit:]
        return list(self.message_history)

    def __str__(self) -> str:
        """字符串表示"""
        return (f"AgentCommunication(agents={len(self.registered_agents)}, "
                f"queues={len(self.message_queues)}, "
                f"running={self.running})")
