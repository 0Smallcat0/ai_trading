"""
事件關聯分析模組

此模組實現了事件關聯分析，用於發現事件之間的關聯和模式。
"""

import logging
import time
from collections import Counter, defaultdict, deque
from typing import Callable, List, Optional

from .event import Event, EventSeverity, EventSource, EventType
from .event_processor import EventProcessor

# 設定日誌
logger = logging.getLogger("events.event_correlation")


class EventCorrelator(EventProcessor):
    """
    事件關聯分析器基類

    事件關聯分析器負責：
    1. 分析事件之間的關聯
    2. 發現事件模式
    3. 生成複合事件
    """

    def __init__(self, name: str, event_types: List[EventType], window_size: int = 300):
        """
        初始化事件關聯分析器

        Args:
            name: 分析器名稱
            event_types: 要處理的事件類型列表
            window_size: 時間窗口大小（秒）
        """
        super().__init__(name, event_types)
        self.window_size = window_size
        self.event_buffer = deque(maxlen=1000)  # 事件緩衝區
        logger.info(f"事件關聯分析器 '{name}' 已初始化，時間窗口: {window_size}秒")

    def process_event(self, event: Event) -> Optional[Event]:
        """
        處理事件，將事件添加到緩衝區並進行關聯分析

        Args:
            event: 要處理的事件

        Returns:
            Optional[Event]: 關聯事件或None
        """
        # 添加事件到緩衝區
        self.event_buffer.append(event)

        # 清理過期事件
        self._clean_expired_events()

        # 進行關聯分析
        return self.correlate(event)

    def _clean_expired_events(self):
        """清理過期事件"""
        current_time = time.time()
        cutoff_time = current_time - self.window_size

        # 將事件緩衝區轉換為列表
        events = list(self.event_buffer)

        # 過濾出未過期的事件
        valid_events = [
            event for event in events if event.timestamp.timestamp() >= cutoff_time
        ]

        # 清空緩衝區並添加有效事件
        self.event_buffer.clear()
        for event in valid_events:
            self.event_buffer.append(event)

    def correlate(self, event: Event) -> Optional[Event]:
        """
        關聯分析的抽象方法，子類必須實現

        Args:
            event: 觸發關聯分析的事件

        Returns:
            Optional[Event]: 關聯事件或None
        """
        raise NotImplementedError("子類必須實現 correlate 方法")


class SequenceCorrelator(EventCorrelator):
    """
    序列關聯分析器，檢測事件序列模式
    """

    def __init__(
        self,
        name: str,
        sequence: List[EventType],
        window_size: int = 300,
        generate_event: bool = True,
    ):
        """
        初始化序列關聯分析器

        Args:
            name: 分析器名稱
            sequence: 要檢測的事件類型序列
            window_size: 時間窗口大小（秒）
            generate_event: 是否生成關聯事件
        """
        super().__init__(name, sequence, window_size)
        self.sequence = sequence
        self.generate_event = generate_event
        self.sequence_events = []  # 當前匹配的序列事件
        logger.info(
            f"序列關聯分析器 '{name}' 已初始化，序列: {[s.name for s in sequence]}"
        )

    def correlate(self, event: Event) -> Optional[Event]:
        """
        檢測事件序列模式

        Args:
            event: 觸發關聯分析的事件

        Returns:
            Optional[Event]: 關聯事件或None
        """
        # 如果事件類型與當前期望的序列事件類型匹配
        expected_index = len(self.sequence_events)
        if (
            expected_index < len(self.sequence)
            and event.event_type == self.sequence[expected_index]
        ):
            # 添加到序列事件
            self.sequence_events.append(event)

            # 檢查是否完成序列
            if len(self.sequence_events) == len(self.sequence):
                # 生成關聯事件
                if self.generate_event:
                    correlated_event = self._create_correlated_event()

                    # 重置序列事件
                    self.sequence_events = []

                    return correlated_event
                else:
                    # 重置序列事件
                    self.sequence_events = []
        else:
            # 如果不匹配，則檢查是否匹配序列的第一個事件
            if event.event_type == self.sequence[0]:
                self.sequence_events = [event]
            else:
                # 不匹配任何序列事件，重置
                self.sequence_events = []

        return None

    def _create_correlated_event(self) -> Event:
        """
        創建關聯事件

        Returns:
            Event: 關聯事件
        """
        # 獲取序列中的第一個和最後一個事件
        first_event = self.sequence_events[0]
        last_event = self.sequence_events[-1]

        # 計算序列持續時間
        duration = (last_event.timestamp - first_event.timestamp).total_seconds()

        # 生成關聯事件
        return Event(
            event_type=EventType.COMPOSITE_EVENT,
            source=EventSource.MONITORING,
            severity=EventSeverity.WARNING,
            subject=f"Sequence Pattern Detected",
            message=f"Detected event sequence pattern: {' -> '.join([s.name for s in self.sequence])}",
            data={
                "sequence": [s.name for s in self.sequence],
                "duration": duration,
                "event_ids": [event.id for event in self.sequence_events],
                "subjects": [
                    event.subject for event in self.sequence_events if event.subject
                ],
            },
            tags=["correlated", "sequence", "pattern"],
            related_events=[event.id for event in self.sequence_events],
        )


class SubjectCorrelator(EventCorrelator):
    """
    主題關聯分析器，關聯相同主題的事件
    """

    def __init__(
        self,
        name: str,
        event_types: List[EventType],
        window_size: int = 300,
        threshold: int = 3,
    ):
        """
        初始化主題關聯分析器

        Args:
            name: 分析器名稱
            event_types: 要處理的事件類型列表
            window_size: 時間窗口大小（秒）
            threshold: 觸發閾值
        """
        super().__init__(name, event_types, window_size)
        self.threshold = threshold
        self.subject_events = defaultdict(list)  # 按主題分組的事件
        self.last_correlation_time = {}  # 上次關聯時間
        logger.info(f"主題關聯分析器 '{name}' 已初始化，閾值: {threshold}")

    def correlate(self, event: Event) -> Optional[Event]:
        """
        關聯相同主題的事件

        Args:
            event: 觸發關聯分析的事件

        Returns:
            Optional[Event]: 關聯事件或None
        """
        if not event.subject:
            return None

        # 添加事件到主題分組
        self.subject_events[event.subject].append(event)

        # 獲取當前時間
        current_time = time.time()

        # 檢查是否需要關聯
        if len(self.subject_events[event.subject]) >= self.threshold and (
            event.subject not in self.last_correlation_time
            or current_time - self.last_correlation_time[event.subject]
            >= self.window_size
        ):
            # 獲取相同主題的事件
            subject_events = self.subject_events[event.subject]

            # 生成關聯事件
            correlated_event = self._create_correlated_event(
                event.subject, subject_events
            )

            # 更新上次關聯時間
            self.last_correlation_time[event.subject] = current_time

            # 清空主題事件
            self.subject_events[event.subject] = []

            return correlated_event

        return None

    def _create_correlated_event(self, subject: str, events: List[Event]) -> Event:
        """
        創建關聯事件

        Args:
            subject: 事件主題
            events: 相關事件列表

        Returns:
            Event: 關聯事件
        """
        # 統計事件類型
        type_counter = Counter(event.event_type for event in events)
        most_common_type = type_counter.most_common(1)[0][0]

        # 統計事件來源
        source_counter = Counter(event.source for event in events)
        most_common_source = source_counter.most_common(1)[0][0]

        # 獲取最高嚴重程度
        severity_order = {
            EventSeverity.DEBUG: 0,
            EventSeverity.INFO: 1,
            EventSeverity.WARNING: 2,
            EventSeverity.ERROR: 3,
            EventSeverity.CRITICAL: 4,
        }
        max_severity = max(events, key=lambda e: severity_order[e.severity]).severity

        # 生成關聯事件
        return Event(
            event_type=EventType.COMPOSITE_EVENT,
            source=most_common_source,
            severity=max_severity,
            subject=subject,
            message=f"Correlated {len(events)} events for {subject}",
            data={
                "count": len(events),
                "type_counts": {t.name: c for t, c in type_counter.items()},
                "source_counts": {s.name: c for s, c in source_counter.items()},
                "event_ids": [event.id for event in events],
            },
            tags=["correlated", "subject", most_common_type.name],
            related_events=[event.id for event in events[:10]],  # 只包含前10個相關事件
        )


class RuleBasedCorrelator(EventCorrelator):
    """
    規則基礎關聯分析器，根據自定義規則關聯事件
    """

    def __init__(
        self,
        name: str,
        event_types: List[EventType],
        rules: List[Callable[[Event, List[Event]], bool]],
        window_size: int = 300,
    ):
        """
        初始化規則基礎關聯分析器

        Args:
            name: 分析器名稱
            event_types: 要處理的事件類型列表
            rules: 關聯規則列表，每個規則是一個函數，接收當前事件和事件緩衝區，返回是否匹配
            window_size: 時間窗口大小（秒）
        """
        super().__init__(name, event_types, window_size)
        self.rules = rules
        logger.info(f"規則基礎關聯分析器 '{name}' 已初始化，規則數量: {len(rules)}")

    def correlate(self, event: Event) -> Optional[List[Event]]:
        """
        根據規則關聯事件

        Args:
            event: 觸發關聯分析的事件

        Returns:
            Optional[List[Event]]: 關聯事件列表或None
        """
        # 獲取事件緩衝區
        buffer_events = list(self.event_buffer)

        # 應用規則
        correlated_events = []

        for rule in self.rules:
            # 檢查規則是否匹配
            if rule(event, buffer_events):
                # 創建關聯事件
                correlated_event = self._create_rule_event(
                    event, buffer_events, self.rules.index(rule)
                )
                correlated_events.append(correlated_event)

        return correlated_events if correlated_events else None

    def _create_rule_event(
        self, event: Event, buffer_events: List[Event], rule_index: int
    ) -> Event:
        """
        創建規則關聯事件

        Args:
            event: 觸發事件
            buffer_events: 事件緩衝區
            rule_index: 規則索引

        Returns:
            Event: 關聯事件
        """
        return Event(
            event_type=EventType.COMPOSITE_EVENT,
            source=EventSource.MONITORING,
            severity=EventSeverity.WARNING,
            subject=f"Rule {rule_index} Triggered",
            message=f"Rule-based correlation detected for event {event.id}",
            data={
                "rule_index": rule_index,
                "trigger_event_id": event.id,
                "buffer_size": len(buffer_events),
            },
            tags=["correlated", "rule", f"rule_{rule_index}"],
            related_events=[event.id],
        )
