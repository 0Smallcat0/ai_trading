"""
異常檢測模組

此模組實現了異常檢測，用於檢測事件中的異常模式。
"""

import logging
import time
import numpy as np
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics

from .event import Event, EventType, EventSeverity, EventSource
from .event_processor import EventProcessor

# 設定日誌
logger = logging.getLogger("events.anomaly_detector")


class AnomalyDetector(EventProcessor):
    """
    異常檢測器基類
    
    異常檢測器負責：
    1. 檢測事件中的異常模式
    2. 生成異常事件
    """
    
    def __init__(self, name: str, event_types: List[EventType], window_size: int = 300):
        """
        初始化異常檢測器
        
        Args:
            name: 檢測器名稱
            event_types: 要處理的事件類型列表
            window_size: 時間窗口大小（秒）
        """
        super().__init__(name, event_types)
        self.window_size = window_size
        logger.info(f"異常檢測器 '{name}' 已初始化，時間窗口: {window_size}秒")
    
    def process_event(self, event: Event) -> Optional[Event]:
        """
        處理事件，檢測異常
        
        Args:
            event: 要處理的事件
            
        Returns:
            Optional[Event]: 異常事件或None
        """
        return self.detect_anomaly(event)
    
    def detect_anomaly(self, event: Event) -> Optional[Event]:
        """
        檢測異常的抽象方法，子類必須實現
        
        Args:
            event: 要檢測的事件
            
        Returns:
            Optional[Event]: 異常事件或None
        """
        raise NotImplementedError("子類必須實現 detect_anomaly 方法")


class FrequencyAnomalyDetector(AnomalyDetector):
    """
    頻率異常檢測器，檢測事件頻率異常
    """
    
    def __init__(self, name: str, event_types: List[EventType], window_size: int = 300, threshold: float = 3.0):
        """
        初始化頻率異常檢測器
        
        Args:
            name: 檢測器名稱
            event_types: 要處理的事件類型列表
            window_size: 時間窗口大小（秒）
            threshold: 異常閾值（標準差倍數）
        """
        super().__init__(name, event_types, window_size)
        self.threshold = threshold
        self.event_counts = defaultdict(list)  # 事件計數歷史
        self.last_window_time = time.time()  # 上一個窗口時間
        self.current_window_counts = defaultdict(int)  # 當前窗口事件計數
        logger.info(f"頻率異常檢測器 '{name}' 已初始化，閾值: {threshold}")
    
    def detect_anomaly(self, event: Event) -> Optional[Event]:
        """
        檢測事件頻率異常
        
        Args:
            event: 要檢測的事件
            
        Returns:
            Optional[Event]: 異常事件或None
        """
        # 更新當前窗口計數
        event_key = (event.event_type, event.source)
        self.current_window_counts[event_key] += 1
        
        # 檢查是否需要結束當前窗口
        current_time = time.time()
        if current_time - self.last_window_time >= self.window_size:
            # 結束當前窗口
            for key, count in self.current_window_counts.items():
                self.event_counts[key].append(count)
                
                # 限制歷史記錄長度
                if len(self.event_counts[key]) > 10:
                    self.event_counts[key] = self.event_counts[key][-10:]
            
            # 重置當前窗口
            self.current_window_counts = defaultdict(int)
            self.last_window_time = current_time
            
            # 更新當前事件計數
            self.current_window_counts[event_key] = 1
        
        # 檢測異常
        return self._check_anomaly(event_key, event)
    
    def _check_anomaly(self, event_key: Tuple[EventType, EventSource], event: Event) -> Optional[Event]:
        """
        檢查事件頻率是否異常
        
        Args:
            event_key: 事件鍵（類型，來源）
            event: 原始事件
            
        Returns:
            Optional[Event]: 異常事件或None
        """
        # 如果歷史記錄不足，則無法檢測異常
        if len(self.event_counts[event_key]) < 3:
            return None
        
        # 計算歷史平均值和標準差
        history = self.event_counts[event_key]
        mean = statistics.mean(history)
        stdev = statistics.stdev(history) if len(history) > 1 else 1.0
        
        # 獲取當前計數
        current_count = self.current_window_counts[event_key]
        
        # 計算Z分數
        z_score = (current_count - mean) / max(stdev, 1.0)
        
        # 檢查是否超過閾值
        if z_score > self.threshold:
            # 生成異常事件
            return Event(
                event_type=EventType.COMPOSITE_EVENT,
                source=EventSource.MONITORING,
                severity=EventSeverity.WARNING,
                subject=f"Frequency Anomaly: {event_key[0].name}",
                message=f"Detected abnormal frequency for {event_key[0].name} events from {event_key[1].name}",
                data={
                    "event_type": event_key[0].name,
                    "source": event_key[1].name,
                    "current_count": current_count,
                    "mean": mean,
                    "stdev": stdev,
                    "z_score": z_score,
                    "threshold": self.threshold,
                    "window_size": self.window_size
                },
                tags=["anomaly", "frequency", event_key[0].name],
                related_events=[event.id]
            )
        
        return None


class PatternAnomalyDetector(AnomalyDetector):
    """
    模式異常檢測器，檢測事件模式異常
    """
    
    def __init__(self, name: str, event_types: List[EventType], window_size: int = 300, pattern_size: int = 3):
        """
        初始化模式異常檢測器
        
        Args:
            name: 檢測器名稱
            event_types: 要處理的事件類型列表
            window_size: 時間窗口大小（秒）
            pattern_size: 模式大小
        """
        super().__init__(name, event_types, window_size)
        self.pattern_size = pattern_size
        self.event_buffer = deque(maxlen=1000)  # 事件緩衝區
        self.pattern_counts = defaultdict(int)  # 模式計數
        self.total_patterns = 0  # 總模式數
        logger.info(f"模式異常檢測器 '{name}' 已初始化，模式大小: {pattern_size}")
    
    def detect_anomaly(self, event: Event) -> Optional[Event]:
        """
        檢測事件模式異常
        
        Args:
            event: 要檢測的事件
            
        Returns:
            Optional[Event]: 異常事件或None
        """
        # 添加事件到緩衝區
        self.event_buffer.append(event)
        
        # 如果緩衝區不足以形成模式，則返回
        if len(self.event_buffer) < self.pattern_size:
            return None
        
        # 獲取當前模式
        current_pattern = tuple(e.event_type for e in list(self.event_buffer)[-self.pattern_size:])
        
        # 更新模式計數
        self.pattern_counts[current_pattern] += 1
        self.total_patterns += 1
        
        # 檢測異常
        return self._check_anomaly(current_pattern, event)
    
    def _check_anomaly(self, pattern: Tuple[EventType, ...], event: Event) -> Optional[Event]:
        """
        檢查事件模式是否異常
        
        Args:
            pattern: 事件模式
            event: 原始事件
            
        Returns:
            Optional[Event]: 異常事件或None
        """
        # 如果總模式數不足，則無法檢測異常
        if self.total_patterns < 10:
            return None
        
        # 計算模式頻率
        pattern_freq = self.pattern_counts[pattern] / self.total_patterns
        
        # 如果模式頻率很低，則可能是異常
        if 0 < pattern_freq < 0.01:
            # 生成異常事件
            return Event(
                event_type=EventType.COMPOSITE_EVENT,
                source=EventSource.MONITORING,
                severity=EventSeverity.WARNING,
                subject=f"Pattern Anomaly",
                message=f"Detected rare event pattern: {' -> '.join([p.name for p in pattern])}",
                data={
                    "pattern": [p.name for p in pattern],
                    "frequency": pattern_freq,
                    "count": self.pattern_counts[pattern],
                    "total_patterns": self.total_patterns
                },
                tags=["anomaly", "pattern", pattern[-1].name],
                related_events=[event.id]
            )
        
        return None


class ValueAnomalyDetector(AnomalyDetector):
    """
    數值異常檢測器，檢測事件數據中的數值異常
    """
    
    def __init__(self, name: str, event_types: List[EventType], data_field: str, window_size: int = 300, threshold: float = 3.0):
        """
        初始化數值異常檢測器
        
        Args:
            name: 檢測器名稱
            event_types: 要處理的事件類型列表
            data_field: 要檢測的數據字段
            window_size: 時間窗口大小（秒）
            threshold: 異常閾值（標準差倍數）
        """
        super().__init__(name, event_types, window_size)
        self.data_field = data_field
        self.threshold = threshold
        self.values = defaultdict(list)  # 數值歷史
        logger.info(f"數值異常檢測器 '{name}' 已初始化，數據字段: {data_field}，閾值: {threshold}")
    
    def detect_anomaly(self, event: Event) -> Optional[Event]:
        """
        檢測事件數據中的數值異常
        
        Args:
            event: 要檢測的事件
            
        Returns:
            Optional[Event]: 異常事件或None
        """
        # 檢查事件數據中是否包含指定字段
        if self.data_field not in event.data:
            return None
        
        # 獲取數值
        value = event.data[self.data_field]
        
        # 檢查數值是否為數字
        if not isinstance(value, (int, float)):
            return None
        
        # 獲取事件主題
        subject = event.subject or "unknown"
        
        # 更新數值歷史
        self.values[subject].append(value)
        
        # 限制歷史記錄長度
        if len(self.values[subject]) > 100:
            self.values[subject] = self.values[subject][-100:]
        
        # 檢測異常
        return self._check_anomaly(subject, value, event)
    
    def _check_anomaly(self, subject: str, value: float, event: Event) -> Optional[Event]:
        """
        檢查數值是否異常
        
        Args:
            subject: 事件主題
            value: 數值
            event: 原始事件
            
        Returns:
            Optional[Event]: 異常事件或None
        """
        # 如果歷史記錄不足，則無法檢測異常
        if len(self.values[subject]) < 10:
            return None
        
        # 計算歷史平均值和標準差
        history = self.values[subject][:-1]  # 不包括當前值
        mean = statistics.mean(history)
        stdev = statistics.stdev(history) if len(history) > 1 else 1.0
        
        # 計算Z分數
        z_score = (value - mean) / max(stdev, 1e-10)
        
        # 檢查是否超過閾值
        if abs(z_score) > self.threshold:
            # 生成異常事件
            return Event(
                event_type=EventType.COMPOSITE_EVENT,
                source=EventSource.MONITORING,
                severity=EventSeverity.WARNING,
                subject=f"Value Anomaly: {subject}",
                message=f"Detected abnormal value for {self.data_field} in {subject}",
                data={
                    "field": self.data_field,
                    "subject": subject,
                    "value": value,
                    "mean": mean,
                    "stdev": stdev,
                    "z_score": z_score,
                    "threshold": self.threshold
                },
                tags=["anomaly", "value", self.data_field],
                related_events=[event.id]
            )
        
        return None
