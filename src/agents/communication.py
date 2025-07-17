# -*- coding: utf-8 -*-
"""
代理間通信模組

此模組實現代理間的通信機制，包括：
- 消息路由和傳遞
- 消息隊列管理
- 廣播和點對點通信
- 消息優先級處理

主要功能：
- 管理代理間的消息傳遞
- 實現消息隊列和路由
- 支持同步和異步通信
- 提供消息過濾和優先級處理
"""

import logging
import threading
import queue
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio

from .base import AgentMessage, AgentError

# 設定日誌
logger = logging.getLogger(__name__)


class CommunicationError(AgentError):
    """通信錯誤"""
    pass


class MessageQueue:
    """消息隊列類"""
    
    def __init__(self, max_size: int = 1000):
        """
        初始化消息隊列。
        
        Args:
            max_size: 隊列最大大小
        """
        self.max_size = max_size
        self.queue = queue.PriorityQueue(maxsize=max_size)
        self.message_count = 0
        self._lock = threading.Lock()
    
    def put(self, message: AgentMessage, priority: Optional[int] = None) -> bool:
        """
        添加消息到隊列。
        
        Args:
            message: 代理消息
            priority: 優先級（覆蓋消息自身優先級）
            
        Returns:
            bool: 是否成功添加
        """
        try:
            with self._lock:
                # 使用負數使高優先級排在前面
                msg_priority = -(priority or message.priority)
                
                # 創建優先級元組 (priority, timestamp, message)
                priority_item = (
                    msg_priority,
                    message.timestamp.timestamp(),
                    self.message_count,
                    message
                )
                
                self.queue.put_nowait(priority_item)
                self.message_count += 1
                return True
                
        except queue.Full:
            logger.warning("消息隊列已滿，丟棄消息")
            return False
        except Exception as e:
            logger.error(f"添加消息到隊列失敗: {e}")
            return False
    
    def get(self, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """
        從隊列獲取消息。
        
        Args:
            timeout: 超時時間（秒）
            
        Returns:
            Optional[AgentMessage]: 消息，如果超時則返回None
        """
        try:
            if timeout is None:
                priority_item = self.queue.get_nowait()
            else:
                priority_item = self.queue.get(timeout=timeout)
            
            # 返回消息部分
            return priority_item[3]
            
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"從隊列獲取消息失敗: {e}")
            return None
    
    def size(self) -> int:
        """獲取隊列大小"""
        return self.queue.qsize()
    
    def is_empty(self) -> bool:
        """檢查隊列是否為空"""
        return self.queue.empty()
    
    def clear(self) -> None:
        """清空隊列"""
        with self._lock:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                except queue.Empty:
                    break


class AgentCommunication:
    """
    代理間通信管理器。
    
    負責管理代理間的消息傳遞、路由和隊列管理。
    
    Attributes:
        agent_queues (Dict[str, MessageQueue]): 代理消息隊列
        message_handlers (Dict[str, Callable]): 消息處理器
        broadcast_history (deque): 廣播消息歷史
        is_running (bool): 通信系統運行狀態
    """
    
    def __init__(
        self,
        max_queue_size: int = 1000,
        max_history_size: int = 10000,
        enable_logging: bool = True
    ):
        """
        初始化通信管理器。
        
        Args:
            max_queue_size: 每個代理的最大隊列大小
            max_history_size: 最大歷史記錄大小
            enable_logging: 是否啟用消息日誌
        """
        self.max_queue_size = max_queue_size
        self.max_history_size = max_history_size
        self.enable_logging = enable_logging
        
        # 代理管理
        self.agent_queues: Dict[str, MessageQueue] = {}
        self.registered_agents: set = set()
        
        # 消息處理
        self.message_handlers: Dict[str, Callable] = {}
        self.message_filters: List[Callable] = []
        
        # 歷史記錄
        self.broadcast_history: deque = deque(maxlen=max_history_size)
        self.message_stats = {
            'total_sent': 0,
            'total_received': 0,
            'total_broadcast': 0,
            'failed_deliveries': 0
        }
        
        # 狀態管理
        self.is_running = False
        self._lock = threading.Lock()
        
        logger.info("初始化代理通信管理器")
    
    def register_agent(self, agent_id: str) -> bool:
        """
        註冊代理到通信系統。
        
        Args:
            agent_id: 代理ID
            
        Returns:
            bool: 註冊是否成功
        """
        try:
            with self._lock:
                if agent_id in self.registered_agents:
                    logger.warning(f"代理已註冊: {agent_id}")
                    return True
                
                # 創建消息隊列
                self.agent_queues[agent_id] = MessageQueue(self.max_queue_size)
                self.registered_agents.add(agent_id)
                
                logger.info(f"註冊代理到通信系統: {agent_id[:8]}")
                return True
                
        except Exception as e:
            logger.error(f"註冊代理失敗: {e}")
            return False
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        從通信系統註銷代理。
        
        Args:
            agent_id: 代理ID
            
        Returns:
            bool: 註銷是否成功
        """
        try:
            with self._lock:
                if agent_id not in self.registered_agents:
                    logger.warning(f"代理未註冊: {agent_id}")
                    return True
                
                # 清理消息隊列
                if agent_id in self.agent_queues:
                    self.agent_queues[agent_id].clear()
                    del self.agent_queues[agent_id]
                
                self.registered_agents.remove(agent_id)
                
                logger.info(f"從通信系統註銷代理: {agent_id[:8]}")
                return True
                
        except Exception as e:
            logger.error(f"註銷代理失敗: {e}")
            return False
    
    def send_message(
        self,
        message: AgentMessage,
        priority_override: Optional[int] = None
    ) -> bool:
        """
        發送消息。
        
        Args:
            message: 要發送的消息
            priority_override: 優先級覆蓋
            
        Returns:
            bool: 發送是否成功
        """
        try:
            # 檢查發送者是否註冊
            if message.sender_id not in self.registered_agents:
                logger.error(f"發送者未註冊: {message.sender_id}")
                return False
            
            # 應用消息過濾器
            for filter_func in self.message_filters:
                if not filter_func(message):
                    logger.debug(f"消息被過濾器拒絕: {message.message_type}")
                    return False
            
            # 廣播消息
            if message.receiver_id is None:
                return self._broadcast_message(message, priority_override)
            
            # 點對點消息
            else:
                return self._send_direct_message(message, priority_override)
                
        except Exception as e:
            logger.error(f"發送消息失敗: {e}")
            self.message_stats['failed_deliveries'] += 1
            return False
    
    def _send_direct_message(
        self,
        message: AgentMessage,
        priority_override: Optional[int] = None
    ) -> bool:
        """發送點對點消息"""
        receiver_id = message.receiver_id
        
        if receiver_id not in self.registered_agents:
            logger.error(f"接收者未註冊: {receiver_id}")
            return False
        
        if receiver_id not in self.agent_queues:
            logger.error(f"接收者隊列不存在: {receiver_id}")
            return False
        
        # 添加到接收者隊列
        success = self.agent_queues[receiver_id].put(message, priority_override)
        
        if success:
            self.message_stats['total_sent'] += 1
            if self.enable_logging:
                logger.debug(f"消息已發送: {message.sender_id[:8]} -> {receiver_id[:8]}")
        
        return success
    
    def _broadcast_message(
        self,
        message: AgentMessage,
        priority_override: Optional[int] = None
    ) -> bool:
        """廣播消息給所有代理"""
        success_count = 0
        
        for agent_id in self.registered_agents:
            if agent_id != message.sender_id:  # 不發送給自己
                if agent_id in self.agent_queues:
                    if self.agent_queues[agent_id].put(message, priority_override):
                        success_count += 1
        
        # 記錄廣播歷史
        self.broadcast_history.append({
            'message': message,
            'timestamp': datetime.now(),
            'recipients': success_count
        })
        
        self.message_stats['total_broadcast'] += 1
        self.message_stats['total_sent'] += success_count
        
        if self.enable_logging:
            logger.debug(f"廣播消息: {message.sender_id[:8]} -> {success_count} 個代理")
        
        return success_count > 0
    
    def receive_message(
        self,
        agent_id: str,
        timeout: Optional[float] = None
    ) -> Optional[AgentMessage]:
        """
        接收消息。
        
        Args:
            agent_id: 代理ID
            timeout: 超時時間（秒）
            
        Returns:
            Optional[AgentMessage]: 接收到的消息
        """
        try:
            if agent_id not in self.agent_queues:
                logger.error(f"代理隊列不存在: {agent_id}")
                return None
            
            message = self.agent_queues[agent_id].get(timeout)
            
            if message:
                self.message_stats['total_received'] += 1
                
                # 調用消息處理器
                handler = self.message_handlers.get(message.message_type)
                if handler:
                    try:
                        handler(message)
                    except Exception as e:
                        logger.error(f"消息處理器執行失敗: {e}")
            
            return message

        except Exception as e:
            logger.error(f"接收消息失敗: {e}")
            return None

    def register_message_handler(
        self,
        message_type: str,
        handler: Callable[[AgentMessage], None]
    ) -> None:
        """
        註冊消息處理器。

        Args:
            message_type: 消息類型
            handler: 處理器函數
        """
        self.message_handlers[message_type] = handler
        logger.debug(f"註冊消息處理器: {message_type}")

    def unregister_message_handler(self, message_type: str) -> None:
        """
        註銷消息處理器。

        Args:
            message_type: 消息類型
        """
        if message_type in self.message_handlers:
            del self.message_handlers[message_type]
            logger.debug(f"註銷消息處理器: {message_type}")

    def add_message_filter(self, filter_func: Callable[[AgentMessage], bool]) -> None:
        """
        添加消息過濾器。

        Args:
            filter_func: 過濾器函數，返回True表示允許消息通過
        """
        self.message_filters.append(filter_func)
        logger.debug("添加消息過濾器")

    def remove_message_filter(self, filter_func: Callable[[AgentMessage], bool]) -> None:
        """
        移除消息過濾器。

        Args:
            filter_func: 要移除的過濾器函數
        """
        if filter_func in self.message_filters:
            self.message_filters.remove(filter_func)
            logger.debug("移除消息過濾器")

    def get_queue_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        獲取代理隊列狀態。

        Args:
            agent_id: 代理ID

        Returns:
            Optional[Dict]: 隊列狀態信息
        """
        if agent_id not in self.agent_queues:
            return None

        queue = self.agent_queues[agent_id]
        return {
            'agent_id': agent_id,
            'queue_size': queue.size(),
            'is_empty': queue.is_empty(),
            'max_size': queue.max_size
        }

    def get_communication_stats(self) -> Dict[str, Any]:
        """
        獲取通信統計信息。

        Returns:
            Dict: 通信統計
        """
        queue_stats = {}
        for agent_id, queue in self.agent_queues.items():
            queue_stats[agent_id] = {
                'size': queue.size(),
                'is_empty': queue.is_empty()
            }

        return {
            'registered_agents': len(self.registered_agents),
            'message_stats': self.message_stats.copy(),
            'queue_stats': queue_stats,
            'broadcast_history_size': len(self.broadcast_history),
            'message_handlers': list(self.message_handlers.keys()),
            'message_filters': len(self.message_filters),
            'is_running': self.is_running
        }

    def clear_all_queues(self) -> None:
        """清空所有代理的消息隊列"""
        with self._lock:
            for queue in self.agent_queues.values():
                queue.clear()
            logger.info("已清空所有消息隊列")

    def clear_agent_queue(self, agent_id: str) -> bool:
        """
        清空指定代理的消息隊列。

        Args:
            agent_id: 代理ID

        Returns:
            bool: 清空是否成功
        """
        if agent_id not in self.agent_queues:
            return False

        self.agent_queues[agent_id].clear()
        logger.debug(f"已清空代理隊列: {agent_id[:8]}")
        return True

    def get_recent_broadcasts(self, count: int = 10) -> List[Dict[str, Any]]:
        """
        獲取最近的廣播消息。

        Args:
            count: 返回的消息數量

        Returns:
            List[Dict]: 最近的廣播消息列表
        """
        return list(self.broadcast_history)[-count:]

    def start_communication(self) -> bool:
        """啟動通信系統"""
        try:
            self.is_running = True
            logger.info("代理通信系統已啟動")
            return True
        except Exception as e:
            logger.error(f"啟動通信系統失敗: {e}")
            return False

    def stop_communication(self) -> bool:
        """停止通信系統"""
        try:
            self.is_running = False
            self.clear_all_queues()
            logger.info("代理通信系統已停止")
            return True
        except Exception as e:
            logger.error(f"停止通信系統失敗: {e}")
            return False

    def create_system_message(
        self,
        message_type: str,
        content: Dict[str, Any],
        priority: int = 3
    ) -> AgentMessage:
        """
        創建系統消息。

        Args:
            message_type: 消息類型
            content: 消息內容
            priority: 優先級

        Returns:
            AgentMessage: 系統消息
        """
        return AgentMessage(
            sender_id="system",
            receiver_id=None,  # 廣播
            message_type=message_type,
            content=content,
            priority=priority
        )

    def send_system_broadcast(
        self,
        message_type: str,
        content: Dict[str, Any],
        priority: int = 3
    ) -> bool:
        """
        發送系統廣播消息。

        Args:
            message_type: 消息類型
            content: 消息內容
            priority: 優先級

        Returns:
            bool: 發送是否成功
        """
        message = self.create_system_message(message_type, content, priority)
        return self.send_message(message)

    def __len__(self) -> int:
        """返回註冊的代理數量"""
        return len(self.registered_agents)

    def __contains__(self, agent_id: str) -> bool:
        """檢查代理是否已註冊"""
        return agent_id in self.registered_agents

    def __str__(self) -> str:
        """字符串表示"""
        return f"AgentCommunication(agents={len(self.registered_agents)}, running={self.is_running})"
