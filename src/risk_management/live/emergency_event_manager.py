"""
緊急事件管理模組

此模組提供緊急事件的記錄和管理功能，包括：
- 事件記錄
- 事件查詢
- 事件統計
"""

import logging
import threading
from datetime import datetime
from typing import Any, Dict, List
from enum import Enum

# 設定日誌
logger = logging.getLogger("risk.live.emergency_event_manager")


class EmergencyLevel(Enum):
    """緊急級別枚舉"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EmergencyEventManager:
    """緊急事件管理器"""
    
    def __init__(self, max_events_size: int = 1000):
        """
        初始化緊急事件管理器
        
        Args:
            max_events_size (int): 最大事件記錄數量
        """
        self.emergency_events: List[Dict[str, Any]] = []
        self.max_events_size = max_events_size
        self._event_lock = threading.Lock()
    
    def create_event(
        self, 
        event_type: str, 
        level: EmergencyLevel,
        reason: str, 
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        創建緊急事件記錄
        
        Args:
            event_type (str): 事件類型
            level (EmergencyLevel): 緊急級別
            reason (str): 事件原因
            data (Dict[str, Any]): 事件數據
            
        Returns:
            Dict[str, Any]: 事件記錄
        """
        try:
            with self._event_lock:
                event = {
                    "timestamp": datetime.now(),
                    "event_type": event_type,
                    "level": level.value,
                    "reason": reason,
                    "data": data,
                }
                
                self.emergency_events.append(event)
                
                # 保持事件記錄在合理範圍內
                if len(self.emergency_events) > self.max_events_size:
                    self.emergency_events = self.emergency_events[-self.max_events_size//2:]
                
                logger.info(f"緊急事件已記錄: {event_type} - {level.value} - {reason}")
                
                return event
                
        except Exception as e:
            logger.exception(f"創建緊急事件記錄失敗: {e}")
            return {
                "timestamp": datetime.now(),
                "event_type": "error",
                "level": level.value,
                "reason": f"創建事件記錄失敗: {str(e)}",
                "data": {},
            }
    
    def get_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        獲取緊急事件記錄
        
        Args:
            limit (int): 限制數量
            
        Returns:
            List[Dict[str, Any]]: 緊急事件記錄
        """
        with self._event_lock:
            return self.emergency_events[-limit:] if self.emergency_events else []
    
    def get_events_by_type(self, event_type: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        根據類型獲取事件記錄
        
        Args:
            event_type (str): 事件類型
            limit (int): 限制數量
            
        Returns:
            List[Dict[str, Any]]: 事件記錄
        """
        with self._event_lock:
            filtered_events = [
                event for event in self.emergency_events 
                if event.get("event_type") == event_type
            ]
            return filtered_events[-limit:] if filtered_events else []
    
    def get_events_by_level(self, level: EmergencyLevel, limit: int = 50) -> List[Dict[str, Any]]:
        """
        根據級別獲取事件記錄
        
        Args:
            level (EmergencyLevel): 緊急級別
            limit (int): 限制數量
            
        Returns:
            List[Dict[str, Any]]: 事件記錄
        """
        with self._event_lock:
            filtered_events = [
                event for event in self.emergency_events 
                if event.get("level") == level.value
            ]
            return filtered_events[-limit:] if filtered_events else []
    
    def get_latest_event(self) -> Dict[str, Any]:
        """
        獲取最新事件
        
        Returns:
            Dict[str, Any]: 最新事件記錄，如果沒有事件則返回 None
        """
        with self._event_lock:
            return self.emergency_events[-1] if self.emergency_events else None
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """
        獲取事件統計
        
        Returns:
            Dict[str, Any]: 事件統計信息
        """
        with self._event_lock:
            if not self.emergency_events:
                return {
                    "total_events": 0,
                    "by_level": {},
                    "by_type": {},
                    "latest_event": None,
                }
            
            # 按級別統計
            level_stats = {}
            for level in EmergencyLevel:
                level_stats[level.value] = sum(
                    1 for event in self.emergency_events 
                    if event.get("level") == level.value
                )
            
            # 按類型統計
            type_stats = {}
            for event in self.emergency_events:
                event_type = event.get("event_type", "unknown")
                type_stats[event_type] = type_stats.get(event_type, 0) + 1
            
            return {
                "total_events": len(self.emergency_events),
                "by_level": level_stats,
                "by_type": type_stats,
                "latest_event": self.emergency_events[-1],
            }
    
    def clear_events(self) -> int:
        """
        清除所有事件記錄
        
        Returns:
            int: 清除的事件數量
        """
        with self._event_lock:
            count = len(self.emergency_events)
            self.emergency_events.clear()
            logger.info(f"已清除 {count} 個緊急事件記錄")
            return count
    
    def export_events(self) -> List[Dict[str, Any]]:
        """
        導出所有事件記錄
        
        Returns:
            List[Dict[str, Any]]: 所有事件記錄的副本
        """
        with self._event_lock:
            return [event.copy() for event in self.emergency_events]
