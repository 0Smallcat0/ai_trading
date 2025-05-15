"""
事件處理器模組

此模組實現了事件處理器，用於處理和轉換事件。
"""

import logging
import threading
import time
from typing import Dict, List, Callable, Any, Optional, Set, Tuple, Union
from abc import ABC, abstractmethod
import queue

from .event import Event, EventType, EventSeverity, EventSource
from .event_bus import event_bus, SubscriptionType

# 設定日誌
logger = logging.getLogger("events.event_processor")


class EventProcessor(ABC):
    """
    事件處理器抽象基類
    
    事件處理器負責：
    1. 接收和處理事件
    2. 轉換和豐富事件
    3. 生成新的事件
    """
    
    def __init__(self, name: str, event_types: Optional[List[EventType]] = None):
        """
        初始化事件處理器
        
        Args:
            name: 處理器名稱
            event_types: 要處理的事件類型列表，如果為None則處理所有事件
        """
        self.name = name
        self.event_types = event_types
        self.subscriptions = []
        self.running = False
        self.processed_count = 0
        self.error_count = 0
        self.last_processed_time = None
        
        logger.info(f"事件處理器 '{name}' 已初始化")
    
    def start(self):
        """啟動事件處理器"""
        if self.running:
            logger.warning(f"事件處理器 '{self.name}' 已經在運行中")
            return
        
        self.running = True
        
        # 訂閱事件
        if self.event_types:
            for event_type in self.event_types:
                subscription = event_bus.subscribe(
                    event_type, self._handle_event, SubscriptionType.ASYNC
                )
                self.subscriptions.append(subscription)
        else:
            # 訂閱所有事件
            subscription = event_bus.subscribe(
                None, self._handle_event, SubscriptionType.ASYNC
            )
            self.subscriptions.append(subscription)
        
        logger.info(f"事件處理器 '{self.name}' 已啟動")
    
    def stop(self):
        """停止事件處理器"""
        if not self.running:
            logger.warning(f"事件處理器 '{self.name}' 尚未啟動")
            return
        
        self.running = False
        
        # 取消訂閱
        for subscription in self.subscriptions:
            event_bus.unsubscribe(subscription)
        
        self.subscriptions = []
        
        logger.info(f"事件處理器 '{self.name}' 已停止")
    
    def _handle_event(self, event: Event):
        """
        處理事件的內部方法
        
        Args:
            event: 要處理的事件
        """
        if not self.running:
            return
        
        try:
            # 處理事件
            result = self.process_event(event)
            
            # 更新統計信息
            self.processed_count += 1
            self.last_processed_time = time.time()
            
            # 如果處理結果是一個新事件，則發布它
            if isinstance(result, Event):
                event_bus.publish(result)
            elif isinstance(result, list) and all(isinstance(e, Event) for e in result):
                for e in result:
                    event_bus.publish(e)
        except Exception as e:
            self.error_count += 1
            logger.exception(f"事件處理器 '{self.name}' 處理事件時發生錯誤: {e}")
    
    @abstractmethod
    def process_event(self, event: Event) -> Optional[Union[Event, List[Event]]]:
        """
        處理事件的抽象方法，子類必須實現
        
        Args:
            event: 要處理的事件
            
        Returns:
            Optional[Union[Event, List[Event]]]: 處理結果，可以是一個新事件、事件列表或None
        """
        pass
    
    def get_stats(self):
        """
        獲取處理器統計信息
        
        Returns:
            dict: 統計信息
        """
        return {
            "name": self.name,
            "running": self.running,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "last_processed_time": self.last_processed_time,
            "event_types": [et.name for et in self.event_types] if self.event_types else "all"
        }


class CompositeEventProcessor(EventProcessor):
    """
    複合事件處理器，用於組合多個處理器
    """
    
    def __init__(self, name: str, processors: List[EventProcessor]):
        """
        初始化複合事件處理器
        
        Args:
            name: 處理器名稱
            processors: 處理器列表
        """
        # 獲取所有處理器的事件類型
        event_types = set()
        for processor in processors:
            if processor.event_types:
                event_types.update(processor.event_types)
        
        super().__init__(name, list(event_types) if event_types else None)
        
        self.processors = processors
        logger.info(f"複合事件處理器 '{name}' 已初始化，包含 {len(processors)} 個處理器")
    
    def start(self):
        """啟動所有處理器"""
        super().start()
        for processor in self.processors:
            processor.start()
    
    def stop(self):
        """停止所有處理器"""
        super().stop()
        for processor in self.processors:
            processor.stop()
    
    def process_event(self, event: Event) -> Optional[Union[Event, List[Event]]]:
        """
        處理事件，將事件傳遞給所有處理器
        
        Args:
            event: 要處理的事件
            
        Returns:
            Optional[Union[Event, List[Event]]]: 處理結果
        """
        results = []
        
        for processor in self.processors:
            if not processor.running:
                continue
                
            # 檢查處理器是否處理此類型的事件
            if processor.event_types and event.event_type not in processor.event_types:
                continue
                
            try:
                result = processor.process_event(event)
                if result:
                    if isinstance(result, list):
                        results.extend(result)
                    else:
                        results.append(result)
            except Exception as e:
                logger.exception(f"處理器 '{processor.name}' 處理事件時發生錯誤: {e}")
        
        return results if results else None


class EventProcessorRegistry:
    """
    事件處理器註冊表，用於管理所有事件處理器
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """實現單例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventProcessorRegistry, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """初始化註冊表"""
        # 避免重複初始化
        if self._initialized:
            return
        
        self.processors = {}
        self._initialized = True
        logger.info("事件處理器註冊表已初始化")
    
    def register(self, processor: EventProcessor):
        """
        註冊處理器
        
        Args:
            processor: 要註冊的處理器
            
        Returns:
            bool: 是否成功註冊
        """
        if processor.name in self.processors:
            logger.warning(f"處理器 '{processor.name}' 已存在，無法重複註冊")
            return False
        
        self.processors[processor.name] = processor
        logger.info(f"處理器 '{processor.name}' 已註冊")
        return True
    
    def unregister(self, name: str):
        """
        取消註冊處理器
        
        Args:
            name: 處理器名稱
            
        Returns:
            bool: 是否成功取消註冊
        """
        if name not in self.processors:
            logger.warning(f"處理器 '{name}' 不存在，無法取消註冊")
            return False
        
        processor = self.processors.pop(name)
        
        # 如果處理器正在運行，則停止它
        if processor.running:
            processor.stop()
        
        logger.info(f"處理器 '{name}' 已取消註冊")
        return True
    
    def get_processor(self, name: str) -> Optional[EventProcessor]:
        """
        獲取處理器
        
        Args:
            name: 處理器名稱
            
        Returns:
            Optional[EventProcessor]: 處理器或None
        """
        return self.processors.get(name)
    
    def start_all(self):
        """啟動所有處理器"""
        for name, processor in self.processors.items():
            if not processor.running:
                processor.start()
        
        logger.info(f"已啟動所有處理器，共 {len(self.processors)} 個")
    
    def stop_all(self):
        """停止所有處理器"""
        for name, processor in self.processors.items():
            if processor.running:
                processor.stop()
        
        logger.info(f"已停止所有處理器，共 {len(self.processors)} 個")
    
    def get_stats(self):
        """
        獲取所有處理器的統計信息
        
        Returns:
            dict: 統計信息
        """
        return {
            name: processor.get_stats() 
            for name, processor in self.processors.items()
        }


# 創建全局註冊表實例
processor_registry = EventProcessorRegistry()
