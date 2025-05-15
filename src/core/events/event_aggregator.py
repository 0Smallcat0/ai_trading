"""
事件聚合器模組

此模組實現了事件聚合器，用於聚合和統計事件。
"""

import logging
import time
from collections import Counter, defaultdict
from typing import List, Optional

from .event import Event, EventSeverity, EventType
from .event_processor import EventProcessor

# 設定日誌
logger = logging.getLogger("events.event_aggregator")


class EventAggregator(EventProcessor):
    """
    事件聚合器基類

    事件聚合器負責：
    1. 收集和統計事件
    2. 根據條件聚合事件
    3. 生成聚合事件
    """

    def __init__(self, name: str, event_types: List[EventType], window_size: int = 60):
        """
        初始化事件聚合器

        Args:
            name: 聚合器名稱
            event_types: 要處理的事件類型列表
            window_size: 時間窗口大小（秒）
        """
        super().__init__(name, event_types)
        self.window_size = window_size
        self.events = []
        self.last_aggregation_time = time.time()
        logger.info(f"事件聚合器 '{name}' 已初始化，時間窗口: {window_size}秒")

    def process_event(self, event: Event) -> Optional[Event]:
        """
        處理事件，將事件添加到聚合器中

        Args:
            event: 要處理的事件

        Returns:
            Optional[Event]: 聚合事件或None
        """
        # 添加事件
        self.events.append(event)

        # 檢查是否需要聚合
        current_time = time.time()
        if current_time - self.last_aggregation_time >= self.window_size:
            # 執行聚合
            aggregated_event = self.aggregate()

            # 清空事件列表
            self.events = []

            # 更新最後聚合時間
            self.last_aggregation_time = current_time

            return aggregated_event

        return None

    def aggregate(self) -> Optional[Event]:
        """
        聚合事件的抽象方法，子類必須實現

        Returns:
            Optional[Event]: 聚合事件或None
        """
        raise NotImplementedError("子類必須實現 aggregate 方法")


class CountAggregator(EventAggregator):
    """
    計數聚合器，統計事件數量
    """

    def __init__(
        self,
        name: str,
        event_types: List[EventType],
        window_size: int = 60,
        threshold: int = 10,
    ):
        """
        初始化計數聚合器

        Args:
            name: 聚合器名稱
            event_types: 要處理的事件類型列表
            window_size: 時間窗口大小（秒）
            threshold: 觸發閾值
        """
        super().__init__(name, event_types, window_size)
        self.threshold = threshold
        logger.info(f"計數聚合器 '{name}' 已初始化，閾值: {threshold}")

    def aggregate(self) -> Optional[Event]:
        """
        聚合事件，統計事件數量

        Returns:
            Optional[Event]: 聚合事件或None
        """
        if not self.events:
            return None

        # 統計事件數量
        count = len(self.events)

        # 如果數量超過閾值，則生成聚合事件
        if count >= self.threshold:
            # 統計事件類型
            type_counter = Counter(event.event_type for event in self.events)
            most_common_type = type_counter.most_common(1)[0][0]

            # 統計事件來源
            source_counter = Counter(event.source for event in self.events)
            most_common_source = source_counter.most_common(1)[0][0]

            # 生成聚合事件
            return Event(
                event_type=EventType.COMPOSITE_EVENT,
                source=most_common_source,
                severity=EventSeverity.WARNING,
                subject=f"Aggregated {most_common_type.name}",
                message=f"Detected {count} events of type {most_common_type.name} in {self.window_size} seconds",
                data={
                    "count": count,
                    "window_size": self.window_size,
                    "threshold": self.threshold,
                    "type_counts": {t.name: c for t, c in type_counter.items()},
                    "source_counts": {s.name: c for s, c in source_counter.items()},
                    "event_ids": [event.id for event in self.events],
                },
                tags=["aggregated", "count", most_common_type.name],
                related_events=[
                    event.id for event in self.events[:10]
                ],  # 只包含前10個相關事件
            )

        return None


class SubjectAggregator(EventAggregator):
    """
    主題聚合器，按主題聚合事件
    """

    def __init__(
        self,
        name: str,
        event_types: List[EventType],
        window_size: int = 60,
        threshold: int = 5,
    ):
        """
        初始化主題聚合器

        Args:
            name: 聚合器名稱
            event_types: 要處理的事件類型列表
            window_size: 時間窗口大小（秒）
            threshold: 觸發閾值
        """
        super().__init__(name, event_types, window_size)
        self.threshold = threshold
        logger.info(f"主題聚合器 '{name}' 已初始化，閾值: {threshold}")

    def aggregate(self) -> Optional[List[Event]]:
        """
        聚合事件，按主題聚合

        Returns:
            Optional[List[Event]]: 聚合事件列表或None
        """
        if not self.events:
            return None

        # 按主題分組
        subject_groups = defaultdict(list)
        for event in self.events:
            if event.subject:
                subject_groups[event.subject].append(event)

        # 生成聚合事件
        aggregated_events = []

        for subject, events in subject_groups.items():
            # 如果事件數量超過閾值，則生成聚合事件
            if len(events) >= self.threshold:
                # 統計事件類型
                type_counter = Counter(event.event_type for event in events)
                most_common_type = type_counter.most_common(1)[0][0]

                # 統計事件來源
                source_counter = Counter(event.source for event in events)
                most_common_source = source_counter.most_common(1)[0][0]

                # 生成聚合事件
                aggregated_event = Event(
                    event_type=EventType.COMPOSITE_EVENT,
                    source=most_common_source,
                    severity=EventSeverity.WARNING,
                    subject=subject,
                    message=f"Detected {len(events)} events for {subject} in {self.window_size} seconds",
                    data={
                        "count": len(events),
                        "window_size": self.window_size,
                        "threshold": self.threshold,
                        "type_counts": {t.name: c for t, c in type_counter.items()},
                        "source_counts": {s.name: c for s, c in source_counter.items()},
                        "event_ids": [event.id for event in events],
                    },
                    tags=["aggregated", "subject", most_common_type.name],
                    related_events=[
                        event.id for event in events[:10]
                    ],  # 只包含前10個相關事件
                )

                aggregated_events.append(aggregated_event)

        return aggregated_events if aggregated_events else None


class SeverityAggregator(EventAggregator):
    """
    嚴重程度聚合器，按嚴重程度聚合事件
    """

    def __init__(
        self,
        name: str,
        event_types: List[EventType],
        window_size: int = 60,
        min_severity: EventSeverity = EventSeverity.ERROR,
        threshold: int = 3,
    ):
        """
        初始化嚴重程度聚合器

        Args:
            name: 聚合器名稱
            event_types: 要處理的事件類型列表
            window_size: 時間窗口大小（秒）
            min_severity: 最小嚴重程度
            threshold: 觸發閾值
        """
        super().__init__(name, event_types, window_size)
        self.min_severity = min_severity
        self.threshold = threshold

        # 嚴重程度順序
        self.severity_order = {
            EventSeverity.DEBUG: 0,
            EventSeverity.INFO: 1,
            EventSeverity.WARNING: 2,
            EventSeverity.ERROR: 3,
            EventSeverity.CRITICAL: 4,
        }

        logger.info(
            f"嚴重程度聚合器 '{name}' 已初始化，最小嚴重程度: {min_severity.name}，閾值: {threshold}"
        )

    def aggregate(self) -> Optional[Event]:
        """
        聚合事件，按嚴重程度聚合

        Returns:
            Optional[Event]: 聚合事件或None
        """
        if not self.events:
            return None

        # 過濾嚴重程度高於閾值的事件
        severe_events = [
            event
            for event in self.events
            if self.severity_order[event.severity]
            >= self.severity_order[self.min_severity]
        ]

        # 如果嚴重事件數量超過閾值，則生成聚合事件
        if len(severe_events) >= self.threshold:
            # 統計事件類型
            type_counter = Counter(event.event_type for event in severe_events)
            type_counter.most_common(1)[0][0]

            # 統計事件來源
            source_counter = Counter(event.source for event in severe_events)
            most_common_source = source_counter.most_common(1)[0][0]

            # 生成聚合事件
            return Event(
                event_type=EventType.COMPOSITE_EVENT,
                source=most_common_source,
                severity=EventSeverity.CRITICAL,
                subject=f"Severe Events Alert",
                message=f"Detected {len(severe_events)} severe events in {self.window_size} seconds",
                data={
                    "count": len(severe_events),
                    "window_size": self.window_size,
                    "threshold": self.threshold,
                    "min_severity": self.min_severity.name,
                    "type_counts": {t.name: c for t, c in type_counter.items()},
                    "source_counts": {s.name: c for s, c in source_counter.items()},
                    "event_ids": [event.id for event in severe_events],
                },
                tags=["aggregated", "severity", self.min_severity.name],
                related_events=[
                    event.id for event in severe_events[:10]
                ],  # 只包含前10個相關事件
            )

        return None
