"""
Comprehensive unit tests for core event system modules

This module tests the event system components to improve test coverage.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import json

# Import event system modules
from src.core.events.event import Event, EventType, EventSeverity, EventSource
from src.core.events.event_bus import EventBus
from src.core.events.event_processor import EventProcessor
from src.core.events.event_store import EventStore
from src.core.events.event_filter import EventFilter
from src.core.events.event_aggregator import EventAggregator
from src.core.events.anomaly_detector import AnomalyDetector


class TestEvent:
    """Test Event class"""

    def test_event_creation(self):
        """Test basic event creation"""
        event = Event(
            event_type=EventType.TRADE_EXECUTED,
            source=EventSource.TRADING_ENGINE,
            data={"symbol": "AAPL", "price": 150.0},
            severity=EventSeverity.INFO
        )

        assert event.event_type == EventType.TRADE_EXECUTED
        assert event.source == EventSource.TRADING_ENGINE
        assert event.data["symbol"] == "AAPL"
        assert event.severity == EventSeverity.INFO
        assert isinstance(event.timestamp, datetime)
        assert event.id is not None

    def test_event_serialization(self):
        """Test event serialization to dict"""
        event = Event(
            event_type=EventType.PRICE_UPDATE,
            source=EventSource.MARKET_DATA,
            data={"symbol": "GOOGL", "price": 2500.0}
        )

        event_dict = event.to_dict()

        assert event_dict["event_type"] == EventType.PRICE_UPDATE.value
        assert event_dict["source"] == EventSource.MARKET_DATA.value
        assert event_dict["data"]["symbol"] == "GOOGL"
        assert "timestamp" in event_dict
        assert "id" in event_dict

    def test_event_from_dict(self):
        """Test event creation from dictionary"""
        event_data = {
            "event_type": EventType.TRADE_EXECUTED.value,
            "source": EventSource.TRADING_ENGINE.value,
            "data": {"symbol": "MSFT", "quantity": 100},
            "severity": EventSeverity.INFO.value,
            "timestamp": datetime.now().isoformat(),
            "id": "test-123"
        }

        event = Event.from_dict(event_data)

        assert event.event_type == EventType.TRADE_EXECUTED
        assert event.source == EventSource.TRADING_ENGINE
        assert event.data["symbol"] == "MSFT"
        assert event.severity == EventSeverity.INFO
        assert event.id == "test-123"


class TestEventBus:
    """Test EventBus class"""

    def setup_method(self):
        """Setup test event bus"""
        self.event_bus = EventBus()
        self.received_events = []

    def test_subscribe_and_publish(self):
        """Test basic subscribe and publish functionality"""
        def handler(event):
            self.received_events.append(event)

        # Subscribe to trade events
        self.event_bus.subscribe(EventType.TRADE_EXECUTED, handler)

        # Publish an event
        event = Event(
            event_type=EventType.TRADE_EXECUTED,
            data={"symbol": "AAPL", "price": 150.0}
        )
        self.event_bus.publish(event)

        # Check that handler was called
        assert len(self.received_events) == 1
        assert self.received_events[0].data["symbol"] == "AAPL"

    def test_multiple_subscribers(self):
        """Test multiple subscribers for same event type"""
        received_1 = []
        received_2 = []

        def handler1(event):
            received_1.append(event)

        def handler2(event):
            received_2.append(event)

        # Subscribe both handlers
        self.event_bus.subscribe(EventType.PRICE_UPDATE, handler1)
        self.event_bus.subscribe(EventType.PRICE_UPDATE, handler2)

        # Publish event
        event = Event(
            event_type=EventType.PRICE_UPDATE,
            data={"symbol": "GOOGL", "price": 2500.0}
        )
        self.event_bus.publish(event)

        # Both handlers should receive the event
        assert len(received_1) == 1
        assert len(received_2) == 1

    def test_unsubscribe(self):
        """Test unsubscribing from events"""
        def handler(event):
            self.received_events.append(event)

        # Subscribe and then unsubscribe
        self.event_bus.subscribe(EventType.TRADE_EXECUTED, handler)
        self.event_bus.unsubscribe(EventType.TRADE_EXECUTED, handler)

        # Publish event
        event = Event(
            event_type=EventType.TRADE_EXECUTED,
            data={"symbol": "AAPL", "price": 150.0}
        )
        self.event_bus.publish(event)

        # Handler should not receive the event
        assert len(self.received_events) == 0

    def test_wildcard_subscription(self):
        """Test wildcard subscription"""
        def handler(event):
            self.received_events.append(event)

        # Subscribe to all events
        self.event_bus.subscribe("*", handler)

        # Publish different types of events
        events = [
            Event(EventType.TRADE_EXECUTED, {"symbol": "AAPL"}),
            Event(EventType.PRICE_UPDATE, {"symbol": "GOOGL"}),
            Event(EventType.ORDER_PLACED, {"symbol": "MSFT"})
        ]

        for event in events:
            self.event_bus.publish(event)

        # Handler should receive all events
        assert len(self.received_events) == 3


class TestEventProcessor:
    """Test EventProcessor class"""

    def setup_method(self):
        """Setup test event processor"""
        self.processor = EventProcessor()
        self.processed_events = []

    def test_add_processor(self):
        """Test adding event processor"""
        def processor_func(event):
            self.processed_events.append(event)
            return event

        self.processor.add_processor(EventType.TRADE_EXECUTED, processor_func)

        # Process an event
        event = Event(
            event_type=EventType.TRADE_EXECUTED,
            data={"symbol": "AAPL", "price": 150.0}
        )

        result = self.processor.process(event)

        assert len(self.processed_events) == 1
        assert result == event

    def test_event_transformation(self):
        """Test event transformation during processing"""
        def transform_processor(event):
            # Add processed timestamp
            event.data["processed_at"] = datetime.now().isoformat()
            return event

        self.processor.add_processor(EventType.PRICE_UPDATE, transform_processor)

        event = Event(
            event_type=EventType.PRICE_UPDATE,
            data={"symbol": "GOOGL", "price": 2500.0}
        )

        result = self.processor.process(event)

        assert "processed_at" in result.data

    def test_multiple_processors(self):
        """Test multiple processors for same event type"""
        def processor1(event):
            event.data["step1"] = "completed"
            return event

        def processor2(event):
            event.data["step2"] = "completed"
            return event

        self.processor.add_processor(EventType.TRADE_EXECUTED, processor1)
        self.processor.add_processor(EventType.TRADE_EXECUTED, processor2)

        event = Event(
            event_type=EventType.TRADE_EXECUTED,
            data={"symbol": "AAPL", "price": 150.0}
        )

        result = self.processor.process(event)

        assert result.data["step1"] == "completed"
        assert result.data["step2"] == "completed"


class TestEventFilter:
    """Test EventFilter class"""

    def setup_method(self):
        """Setup test event filter"""
        self.filter = EventFilter()

    def test_symbol_filter(self):
        """Test filtering by symbol"""
        self.filter.add_symbol_filter(["AAPL", "GOOGL"])

        # Should pass
        event1 = Event(
            event_type=EventType.TRADE_EXECUTED,
            data={"symbol": "AAPL", "price": 150.0}
        )
        assert self.filter.should_process(event1) == True

        # Should be filtered out
        event2 = Event(
            event_type=EventType.TRADE_EXECUTED,
            data={"symbol": "MSFT", "price": 300.0}
        )
        assert self.filter.should_process(event2) == False

    def test_event_type_filter(self):
        """Test filtering by event type"""
        self.filter.add_event_type_filter([EventType.TRADE_EXECUTED])

        # Should pass
        event1 = Event(
            event_type=EventType.TRADE_EXECUTED,
            data={"symbol": "AAPL", "price": 150.0}
        )
        assert self.filter.should_process(event1) == True

        # Should be filtered out
        event2 = Event(
            event_type=EventType.PRICE_UPDATE,
            data={"symbol": "AAPL", "price": 151.0}
        )
        assert self.filter.should_process(event2) == False

    def test_time_range_filter(self):
        """Test filtering by time range"""
        now = datetime.now()
        start_time = now - timedelta(hours=1)
        end_time = now + timedelta(hours=1)

        self.filter.add_time_range_filter(start_time, end_time)

        # Should pass (current time)
        event1 = Event(
            event_type=EventType.TRADE_EXECUTED,
            data={"symbol": "AAPL", "price": 150.0}
        )
        assert self.filter.should_process(event1) == True

        # Should be filtered out (old event)
        old_event = Event(
            event_type=EventType.TRADE_EXECUTED,
            data={"symbol": "AAPL", "price": 150.0}
        )
        old_event.timestamp = now - timedelta(hours=2)
        assert self.filter.should_process(old_event) == False


class TestEventAggregator:
    """Test EventAggregator class"""

    def setup_method(self):
        """Setup test event aggregator"""
        self.aggregator = EventAggregator()

    def test_count_aggregation(self):
        """Test count aggregation"""
        # Add events
        events = [
            Event(EventType.TRADE_EXECUTED, {"symbol": "AAPL", "quantity": 100}),
            Event(EventType.TRADE_EXECUTED, {"symbol": "AAPL", "quantity": 200}),
            Event(EventType.TRADE_EXECUTED, {"symbol": "GOOGL", "quantity": 50})
        ]

        for event in events:
            self.aggregator.add_event(event)

        # Get count by symbol
        aapl_count = self.aggregator.get_count(
            event_type=EventType.TRADE_EXECUTED,
            group_by="symbol",
            value="AAPL"
        )

        assert aapl_count == 2

    def test_sum_aggregation(self):
        """Test sum aggregation"""
        events = [
            Event(EventType.TRADE_EXECUTED, {"symbol": "AAPL", "quantity": 100}),
            Event(EventType.TRADE_EXECUTED, {"symbol": "AAPL", "quantity": 200}),
        ]

        for event in events:
            self.aggregator.add_event(event)

        # Get sum of quantities
        total_quantity = self.aggregator.get_sum(
            event_type=EventType.TRADE_EXECUTED,
            field="quantity",
            group_by="symbol",
            value="AAPL"
        )

        assert total_quantity == 300

    def test_time_window_aggregation(self):
        """Test aggregation within time window"""
        now = datetime.now()

        # Add events with different timestamps
        events = [
            Event(EventType.TRADE_EXECUTED, {"symbol": "AAPL", "quantity": 100}),
            Event(EventType.TRADE_EXECUTED, {"symbol": "AAPL", "quantity": 200}),
        ]

        # Set timestamps
        events[0].timestamp = now - timedelta(minutes=30)
        events[1].timestamp = now - timedelta(minutes=10)

        for event in events:
            self.aggregator.add_event(event)

        # Get count within last hour
        count = self.aggregator.get_count_in_window(
            event_type=EventType.TRADE_EXECUTED,
            window_minutes=60,
            group_by="symbol",
            value="AAPL"
        )

        assert count == 2

        # Get count within last 20 minutes
        recent_count = self.aggregator.get_count_in_window(
            event_type=EventType.TRADE_EXECUTED,
            window_minutes=20,
            group_by="symbol",
            value="AAPL"
        )

        assert recent_count == 1


class TestAnomalyDetector:
    """Test AnomalyDetector class"""

    def setup_method(self):
        """Setup test anomaly detector"""
        self.detector = AnomalyDetector()

    def test_price_anomaly_detection(self):
        """Test price anomaly detection"""
        # Add normal price events
        normal_prices = [100, 101, 99, 102, 98, 103, 97]
        for price in normal_prices:
            event = Event(
                event_type=EventType.PRICE_UPDATE,
                data={"symbol": "AAPL", "price": price}
            )
            self.detector.add_event(event)

        # Add anomalous price
        anomaly_event = Event(
            event_type=EventType.PRICE_UPDATE,
            data={"symbol": "AAPL", "price": 150}  # 50% jump
        )

        is_anomaly = self.detector.detect_price_anomaly(anomaly_event)
        assert is_anomaly == True

    def test_volume_anomaly_detection(self):
        """Test volume anomaly detection"""
        # Add normal volume events
        normal_volumes = [1000, 1100, 900, 1200, 800, 1300, 700]
        for volume in normal_volumes:
            event = Event(
                event_type=EventType.TRADE_EXECUTED,
                data={"symbol": "AAPL", "volume": volume}
            )
            self.detector.add_event(event)

        # Add anomalous volume
        anomaly_event = Event(
            event_type=EventType.TRADE_EXECUTED,
            data={"symbol": "AAPL", "volume": 10000}  # 10x normal
        )

        is_anomaly = self.detector.detect_volume_anomaly(anomaly_event)
        assert is_anomaly == True

    def test_frequency_anomaly_detection(self):
        """Test frequency anomaly detection"""
        # Add events at normal frequency
        now = datetime.now()
        for i in range(10):
            event = Event(
                event_type=EventType.TRADE_EXECUTED,
                data={"symbol": "AAPL", "quantity": 100}
            )
            event.timestamp = now - timedelta(minutes=i)
            self.detector.add_event(event)

        # Check for frequency anomaly (too many events in short time)
        is_anomaly = self.detector.detect_frequency_anomaly(
            event_type=EventType.TRADE_EXECUTED,
            symbol="AAPL",
            window_minutes=5,
            threshold=10
        )

        assert is_anomaly == True
