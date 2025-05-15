"""
事件定義模組

此模組定義了系統中使用的各種事件類型和事件類。
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
import uuid
import json


class EventType(Enum):
    """事件類型列舉"""

    # 市場相關事件
    MARKET_DATA = auto()  # 市場數據更新
    PRICE_CHANGE = auto()  # 價格變動
    VOLUME_SPIKE = auto()  # 成交量突增
    PRICE_ANOMALY = auto()  # 價格異常
    VOLUME_ANOMALY = auto()  # 成交量異常
    MARKET_CRASH = auto()  # 市場崩盤
    MARKET_RALLY = auto()  # 市場反彈

    # 新聞和公告事件
    NEWS = auto()  # 一般新聞
    EARNINGS_ANNOUNCEMENT = auto()  # 盈利公告
    DIVIDEND_ANNOUNCEMENT = auto()  # 股息公告
    MERGER_ACQUISITION = auto()  # 併購公告
    REGULATORY_ANNOUNCEMENT = auto()  # 監管公告

    # 交易相關事件
    ORDER_CREATED = auto()  # 訂單創建
    ORDER_SUBMITTED = auto()  # 訂單提交
    ORDER_FILLED = auto()  # 訂單成交
    ORDER_PARTIALLY_FILLED = auto()  # 訂單部分成交
    ORDER_CANCELLED = auto()  # 訂單取消
    ORDER_REJECTED = auto()  # 訂單拒絕
    ORDER_EXPIRED = auto()  # 訂單過期

    # 系統相關事件
    SYSTEM_STARTUP = auto()  # 系統啟動
    SYSTEM_SHUTDOWN = auto()  # 系統關閉
    SYSTEM_ERROR = auto()  # 系統錯誤
    SYSTEM_WARNING = auto()  # 系統警告
    SYSTEM_INFO = auto()  # 系統信息

    # 策略相關事件
    STRATEGY_SIGNAL = auto()  # 策略信號
    STRATEGY_START = auto()  # 策略啟動
    STRATEGY_STOP = auto()  # 策略停止
    STRATEGY_ERROR = auto()  # 策略錯誤

    # 風險相關事件
    RISK_LIMIT_BREACH = auto()  # 風險限制突破
    DRAWDOWN_ALERT = auto()  # 回撤警報
    POSITION_LIMIT_ALERT = auto()  # 持倉限制警報
    CONCENTRATION_ALERT = auto()  # 集中度警報

    # 複合事件
    COMPOSITE_EVENT = auto()  # 複合事件（由多個事件組成）


class EventSeverity(Enum):
    """事件嚴重程度列舉"""

    DEBUG = auto()  # 調試級別
    INFO = auto()  # 信息級別
    WARNING = auto()  # 警告級別
    ERROR = auto()  # 錯誤級別
    CRITICAL = auto()  # 嚴重級別


class EventSource(Enum):
    """事件來源列舉"""

    MARKET_DATA = auto()  # 市場數據
    NEWS_FEED = auto()  # 新聞源
    TRADING_SYSTEM = auto()  # 交易系統
    RISK_SYSTEM = auto()  # 風險系統
    STRATEGY = auto()  # 策略
    MONITORING = auto()  # 監控系統
    USER = auto()  # 用戶
    EXTERNAL = auto()  # 外部系統


@dataclass
class Event:
    """事件類，用於表示系統中的各種事件"""

    event_type: EventType  # 事件類型
    source: EventSource  # 事件來源
    timestamp: datetime = field(default_factory=datetime.now)  # 事件時間戳
    id: str = field(default_factory=lambda: str(uuid.uuid4()))  # 事件ID
    severity: EventSeverity = EventSeverity.INFO  # 事件嚴重程度
    subject: Optional[str] = None  # 事件主題（如股票代號）
    message: Optional[str] = None  # 事件消息
    data: Dict[str, Any] = field(default_factory=dict)  # 事件數據
    tags: List[str] = field(default_factory=list)  # 事件標籤
    related_events: List[str] = field(default_factory=list)  # 相關事件ID列表
    processed: bool = False  # 事件是否已處理

    def to_dict(self) -> Dict[str, Any]:
        """將事件轉換為字典"""
        return {
            "id": self.id,
            "event_type": self.event_type.name,
            "source": self.source.name,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.name,
            "subject": self.subject,
            "message": self.message,
            "data": self.data,
            "tags": self.tags,
            "related_events": self.related_events,
            "processed": self.processed,
        }

    def to_json(self) -> str:
        """將事件轉換為JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """從字典創建事件"""
        # 處理枚舉類型
        event_type = EventType[data["event_type"]]
        source = EventSource[data["source"]]
        severity = EventSeverity[data["severity"]]

        # 處理時間戳
        timestamp = datetime.fromisoformat(data["timestamp"])

        # 創建事件
        return cls(
            id=data["id"],
            event_type=event_type,
            source=source,
            timestamp=timestamp,
            severity=severity,
            subject=data.get("subject"),
            message=data.get("message"),
            data=data.get("data", {}),
            tags=data.get("tags", []),
            related_events=data.get("related_events", []),
            processed=data.get("processed", False),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        """從JSON字符串創建事件"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __str__(self) -> str:
        """事件的字符串表示"""
        return (
            f"Event(id={self.id}, type={self.event_type.name}, "
            f"source={self.source.name}, severity={self.severity.name}, "
            f"subject={self.subject}, message={self.message})"
        )


def create_market_event(
    event_type: EventType,
    stock_id: str,
    price: Optional[float] = None,
    volume: Optional[int] = None,
    change: Optional[float] = None,
    change_percent: Optional[float] = None,
    severity: EventSeverity = EventSeverity.INFO,
    message: Optional[str] = None,
    **kwargs,
) -> Event:
    """
    創建市場相關事件的便捷函數

    Args:
        event_type: 事件類型
        stock_id: 股票代號
        price: 價格
        volume: 成交量
        change: 價格變動
        change_percent: 價格變動百分比
        severity: 事件嚴重程度
        message: 事件消息
        **kwargs: 其他事件數據

    Returns:
        Event: 市場事件
    """
    data = {
        "price": price,
        "volume": volume,
        "change": change,
        "change_percent": change_percent,
        **kwargs,
    }

    # 過濾掉None值
    data = {k: v for k, v in data.items() if v is not None}

    return Event(
        event_type=event_type,
        source=EventSource.MARKET_DATA,
        subject=stock_id,
        severity=severity,
        message=message,
        data=data,
    )


def create_order_event(
    event_type: EventType,
    order_id: str,
    stock_id: str,
    action: str,
    quantity: int,
    price: Optional[float] = None,
    filled_quantity: Optional[int] = None,
    filled_price: Optional[float] = None,
    severity: EventSeverity = EventSeverity.INFO,
    message: Optional[str] = None,
    **kwargs,
) -> Event:
    """
    創建訂單相關事件的便捷函數

    Args:
        event_type: 事件類型
        order_id: 訂單ID
        stock_id: 股票代號
        action: 交易動作 ('buy' 或 'sell')
        quantity: 交易數量
        price: 訂單價格
        filled_quantity: 成交數量
        filled_price: 成交價格
        severity: 事件嚴重程度
        message: 事件消息
        **kwargs: 其他事件數據

    Returns:
        Event: 訂單事件
    """
    data = {
        "order_id": order_id,
        "stock_id": stock_id,
        "action": action,
        "quantity": quantity,
        "price": price,
        "filled_quantity": filled_quantity,
        "filled_price": filled_price,
        **kwargs,
    }

    # 過濾掉None值
    data = {k: v for k, v in data.items() if v is not None}

    return Event(
        event_type=event_type,
        source=EventSource.TRADING_SYSTEM,
        subject=f"{stock_id}:{order_id}",
        severity=severity,
        message=message,
        data=data,
    )


def create_system_event(
    event_type: EventType,
    message: str,
    severity: EventSeverity = EventSeverity.INFO,
    component: Optional[str] = None,
    **kwargs,
) -> Event:
    """
    創建系統相關事件的便捷函數

    Args:
        event_type: 事件類型
        message: 事件消息
        severity: 事件嚴重程度
        component: 系統組件名稱
        **kwargs: 其他事件數據

    Returns:
        Event: 系統事件
    """
    data = {"component": component, **kwargs}

    # 過濾掉None值
    data = {k: v for k, v in data.items() if v is not None}

    return Event(
        event_type=event_type,
        source=EventSource.MONITORING,
        subject=component,
        severity=severity,
        message=message,
        data=data,
    )
