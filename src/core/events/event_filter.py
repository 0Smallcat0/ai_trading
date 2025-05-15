"""
事件過濾器模組

此模組實現了事件過濾器，用於過濾和路由事件。
"""

import logging
import re
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Pattern, Union

from .event import Event, EventSeverity, EventSource, EventType
from .event_processor import EventProcessor

# 設定日誌
logger = logging.getLogger("events.event_filter")


class EventFilter(EventProcessor):
    """
    事件過濾器基類

    事件過濾器負責：
    1. 根據條件過濾事件
    2. 路由事件到不同的處理器
    """

    def __init__(self, name: str, event_types: Optional[List[EventType]] = None):
        """
        初始化事件過濾器

        Args:
            name: 過濾器名稱
            event_types: 要處理的事件類型列表
        """
        super().__init__(name, event_types)
        logger.info(f"事件過濾器 '{name}' 已初始化")

    @abstractmethod
    def filter(self, event: Event) -> bool:
        """
        過濾事件的抽象方法，子類必須實現

        Args:
            event: 要過濾的事件

        Returns:
            bool: 是否通過過濾
        """

    def process_event(self, event: Event) -> Optional[Event]:
        """
        處理事件，如果通過過濾則返回事件，否則返回None

        Args:
            event: 要處理的事件

        Returns:
            Optional[Event]: 通過過濾的事件或None
        """
        if self.filter(event):
            return event
        return None


class TypeFilter(EventFilter):
    """
    事件類型過濾器，根據事件類型過濾事件
    """

    def __init__(
        self,
        name: str,
        include_types: List[EventType],
        exclude_types: Optional[List[EventType]] = None,
    ):
        """
        初始化類型過濾器

        Args:
            name: 過濾器名稱
            include_types: 要包含的事件類型列表
            exclude_types: 要排除的事件類型列表
        """
        super().__init__(name, include_types)
        self.include_types = set(include_types)
        self.exclude_types = set(exclude_types) if exclude_types else set()
        logger.info(
            f"類型過濾器 '{name}' 已初始化，包含類型: {[t.name for t in include_types]}, 排除類型: {[t.name for t in exclude_types] if exclude_types else '無'}"
        )

    def filter(self, event: Event) -> bool:
        """
        根據事件類型過濾事件

        Args:
            event: 要過濾的事件

        Returns:
            bool: 是否通過過濾
        """
        if event.event_type in self.exclude_types:
            return False
        return event.event_type in self.include_types


class SeverityFilter(EventFilter):
    """
    事件嚴重程度過濾器，根據事件嚴重程度過濾事件
    """

    def __init__(
        self,
        name: str,
        min_severity: EventSeverity,
        event_types: Optional[List[EventType]] = None,
    ):
        """
        初始化嚴重程度過濾器

        Args:
            name: 過濾器名稱
            min_severity: 最小嚴重程度
            event_types: 要處理的事件類型列表
        """
        super().__init__(name, event_types)
        self.min_severity = min_severity

        # 嚴重程度順序
        self.severity_order = {
            EventSeverity.DEBUG: 0,
            EventSeverity.INFO: 1,
            EventSeverity.WARNING: 2,
            EventSeverity.ERROR: 3,
            EventSeverity.CRITICAL: 4,
        }

        logger.info(
            f"嚴重程度過濾器 '{name}' 已初始化，最小嚴重程度: {min_severity.name}"
        )

    def filter(self, event: Event) -> bool:
        """
        根據事件嚴重程度過濾事件

        Args:
            event: 要過濾的事件

        Returns:
            bool: 是否通過過濾
        """
        return (
            self.severity_order[event.severity]
            >= self.severity_order[self.min_severity]
        )


class SourceFilter(EventFilter):
    """
    事件來源過濾器，根據事件來源過濾事件
    """

    def __init__(
        self,
        name: str,
        include_sources: List[EventSource],
        exclude_sources: Optional[List[EventSource]] = None,
        event_types: Optional[List[EventType]] = None,
    ):
        """
        初始化來源過濾器

        Args:
            name: 過濾器名稱
            include_sources: 要包含的事件來源列表
            exclude_sources: 要排除的事件來源列表
            event_types: 要處理的事件類型列表
        """
        super().__init__(name, event_types)
        self.include_sources = set(include_sources)
        self.exclude_sources = set(exclude_sources) if exclude_sources else set()
        logger.info(
            f"來源過濾器 '{name}' 已初始化，包含來源: {[s.name for s in include_sources]}, 排除來源: {[s.name for s in exclude_sources] if exclude_sources else '無'}"
        )

    def filter(self, event: Event) -> bool:
        """
        根據事件來源過濾事件

        Args:
            event: 要過濾的事件

        Returns:
            bool: 是否通過過濾
        """
        if event.source in self.exclude_sources:
            return False
        return event.source in self.include_sources


class SubjectFilter(EventFilter):
    """
    事件主題過濾器，根據事件主題過濾事件
    """

    def __init__(
        self,
        name: str,
        patterns: List[Union[str, Pattern]],
        event_types: Optional[List[EventType]] = None,
    ):
        """
        初始化主題過濾器

        Args:
            name: 過濾器名稱
            patterns: 主題匹配模式列表，可以是字符串或正則表達式
            event_types: 要處理的事件類型列表
        """
        super().__init__(name, event_types)

        # 將字符串模式編譯為正則表達式
        self.patterns = []
        for pattern in patterns:
            if isinstance(pattern, str):
                self.patterns.append(re.compile(pattern))
            else:
                self.patterns.append(pattern)

        logger.info(f"主題過濾器 '{name}' 已初始化，模式數量: {len(self.patterns)}")

    def filter(self, event: Event) -> bool:
        """
        根據事件主題過濾事件

        Args:
            event: 要過濾的事件

        Returns:
            bool: 是否通過過濾
        """
        if not event.subject:
            return False

        for pattern in self.patterns:
            if pattern.search(event.subject):
                return True

        return False


class CompositeFilter(EventFilter):
    """
    複合過濾器，組合多個過濾器
    """

    def __init__(
        self, name: str, filters: List[EventFilter], require_all: bool = False
    ):
        """
        初始化複合過濾器

        Args:
            name: 過濾器名稱
            filters: 過濾器列表
            require_all: 是否要求所有過濾器都通過
        """
        # 獲取所有過濾器的事件類型
        event_types = set()
        for filter_obj in filters:
            if filter_obj.event_types:
                event_types.update(filter_obj.event_types)

        super().__init__(name, list(event_types) if event_types else None)

        self.filters = filters
        self.require_all = require_all
        logger.info(
            f"複合過濾器 '{name}' 已初始化，過濾器數量: {len(filters)}, 要求全部通過: {require_all}"
        )

    def filter(self, event: Event) -> bool:
        """
        根據所有過濾器過濾事件

        Args:
            event: 要過濾的事件

        Returns:
            bool: 是否通過過濾
        """
        if self.require_all:
            # 要求所有過濾器都通過
            return all(f.filter(event) for f in self.filters)
        else:
            # 只要有一個過濾器通過即可
            return any(f.filter(event) for f in self.filters)


class DataFilter(EventFilter):
    """
    事件數據過濾器，根據事件數據過濾事件
    """

    def __init__(
        self,
        name: str,
        conditions: Dict[str, Any],
        event_types: Optional[List[EventType]] = None,
    ):
        """
        初始化數據過濾器

        Args:
            name: 過濾器名稱
            conditions: 數據條件字典，key為數據字段，value為期望值
            event_types: 要處理的事件類型列表
        """
        super().__init__(name, event_types)
        self.conditions = conditions
        logger.info(f"數據過濾器 '{name}' 已初始化，條件: {conditions}")

    def filter(self, event: Event) -> bool:
        """
        根據事件數據過濾事件

        Args:
            event: 要過濾的事件

        Returns:
            bool: 是否通過過濾
        """
        for key, expected_value in self.conditions.items():
            if key not in event.data:
                return False

            actual_value = event.data[key]

            # 處理不同類型的條件
            if callable(expected_value):
                # 如果是函數，則調用函數進行判斷
                if not expected_value(actual_value):
                    return False
            elif isinstance(expected_value, (list, tuple, set)):
                # 如果是列表、元組或集合，則檢查值是否在其中
                if actual_value not in expected_value:
                    return False
            elif isinstance(expected_value, dict):
                # 如果是字典，則檢查是否為子集
                if not all(
                    k in actual_value and actual_value[k] == v
                    for k, v in expected_value.items()
                ):
                    return False
            else:
                # 否則直接比較值
                if actual_value != expected_value:
                    return False

        return True
