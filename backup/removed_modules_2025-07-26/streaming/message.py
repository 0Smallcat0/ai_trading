"""
消息定義模組

此模組定義了系統中使用的各種消息類型和消息類。
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, Optional


# 設定消息類型
class MessageType(Enum):
    """消息類型列舉"""

    # 市場數據消息
    MARKET_DATA = auto()  # 市場數據更新
    TICK_DATA = auto()  # 逐筆成交數據
    QUOTE_DATA = auto()  # 報價數據
    ORDER_BOOK = auto()  # 訂單簿數據
    TRADE_DATA = auto()  # 成交數據

    # 特徵消息
    FEATURE_DATA = auto()  # 特徵數據
    FEATURE_REQUEST = auto()  # 特徵請求
    FEATURE_RESPONSE = auto()  # 特徵響應

    # 模型消息
    MODEL_REQUEST = auto()  # 模型請求
    MODEL_RESPONSE = auto()  # 模型響應
    MODEL_UPDATE = auto()  # 模型更新

    # 交易消息
    TRADE_SIGNAL = auto()  # 交易信號
    ORDER_REQUEST = auto()  # 訂單請求
    ORDER_RESPONSE = auto()  # 訂單響應
    ORDER_STATUS = auto()  # 訂單狀態

    # 系統消息
    HEARTBEAT = auto()  # 心跳
    ERROR = auto()  # 錯誤
    INFO = auto()  # 信息
    WARNING = auto()  # 警告
    CONTROL = auto()  # 控制命令


# 消息優先級
class MessagePriority(Enum):
    """消息優先級列舉"""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


# 消息架構定義
class MessageSchema:
    """消息架構定義，用於驗證消息格式"""

    # 市場數據消息架構
    MARKET_DATA_SCHEMA = {
        "type": "object",
        "required": ["symbol", "timestamp", "data"],
        "properties": {
            "symbol": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
            "data": {
                "type": "object",
                "properties": {
                    "price": {"type": "number"},
                    "volume": {"type": "number"},
                    "open": {"type": "number"},
                    "high": {"type": "number"},
                    "low": {"type": "number"},
                    "close": {"type": "number"},
                },
            },
        },
    }

    # 特徵數據消息架構
    FEATURE_DATA_SCHEMA = {
        "type": "object",
        "required": ["symbol", "timestamp", "features"],
        "properties": {
            "symbol": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
            "features": {"type": "object"},
        },
    }

    # 模型請求消息架構
    MODEL_REQUEST_SCHEMA = {
        "type": "object",
        "required": ["model_id", "features"],
        "properties": {"model_id": {"type": "string"}, "features": {"type": "object"}},
    }

    # 模型響應消息架構
    MODEL_RESPONSE_SCHEMA = {
        "type": "object",
        "required": ["model_id", "predictions"],
        "properties": {
            "model_id": {"type": "string"},
            "predictions": {"type": "object"},
        },
    }

    # 交易信號消息架構
    TRADE_SIGNAL_SCHEMA = {
        "type": "object",
        "required": ["symbol", "timestamp", "action", "confidence"],
        "properties": {
            "symbol": {"type": "string"},
            "timestamp": {"type": "string", "format": "date-time"},
            "action": {"type": "string", "enum": ["buy", "sell", "hold"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "price": {"type": "number"},
            "quantity": {"type": "number"},
        },
    }


@dataclass
class Message:
    """消息類，用於表示系統中的各種消息"""

    message_type: MessageType  # 消息類型
    data: Dict[str, Any]  # 消息數據
    timestamp: datetime = field(default_factory=datetime.now)  # 消息時間戳
    id: str = field(default_factory=lambda: str(uuid.uuid4()))  # 消息ID
    priority: MessagePriority = MessagePriority.NORMAL  # 消息優先級
    source: Optional[str] = None  # 消息來源
    destination: Optional[str] = None  # 消息目的地
    correlation_id: Optional[str] = None  # 相關消息ID
    expiration: Optional[datetime] = None  # 消息過期時間

    def to_dict(self) -> Dict[str, Any]:
        """將消息轉換為字典"""
        return {
            "id": self.id,
            "message_type": self.message_type.name,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.name,
            "source": self.source,
            "destination": self.destination,
            "correlation_id": self.correlation_id,
            "expiration": self.expiration.isoformat() if self.expiration else None,
        }

    def to_json(self) -> str:
        """將消息轉換為JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """從字典創建消息"""
        # 處理枚舉類型
        message_type = MessageType[data["message_type"]]
        priority = (
            MessagePriority[data["priority"]]
            if "priority" in data
            else MessagePriority.NORMAL
        )

        # 處理時間戳
        timestamp = datetime.fromisoformat(data["timestamp"])
        expiration = (
            datetime.fromisoformat(data["expiration"])
            if data.get("expiration")
            else None
        )

        # 創建消息
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            message_type=message_type,
            data=data["data"],
            timestamp=timestamp,
            priority=priority,
            source=data.get("source"),
            destination=data.get("destination"),
            correlation_id=data.get("correlation_id"),
            expiration=expiration,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        """從JSON字符串創建消息"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def is_expired(self) -> bool:
        """檢查消息是否已過期"""
        if self.expiration is None:
            return False
        return datetime.now() > self.expiration

    def __str__(self) -> str:
        """消息的字符串表示"""
        return (
            f"Message(id={self.id}, type={self.message_type.name}, "
            f"priority={self.priority.name}, source={self.source}, "
            f"destination={self.destination})"
        )


# 創建消息的便捷函數
def create_market_data_message(
    symbol: str,
    price: float,
    volume: float,
    timestamp: Optional[datetime] = None,
    **kwargs,
) -> Message:
    """
    創建市場數據消息

    Args:
        symbol: 股票代碼
        price: 價格
        volume: 成交量
        timestamp: 時間戳，如果為None則使用當前時間
        **kwargs: 其他數據

    Returns:
        Message: 市場數據消息
    """
    data = {"symbol": symbol, "price": price, "volume": volume, **kwargs}

    return Message(
        message_type=MessageType.MARKET_DATA,
        data=data,
        timestamp=timestamp or datetime.now(),
        source="market_data_feed",
    )


def create_feature_data_message(
    symbol: str, features: Dict[str, Any], timestamp: Optional[datetime] = None
) -> Message:
    """
    創建特徵數據消息

    Args:
        symbol: 股票代碼
        features: 特徵數據
        timestamp: 時間戳，如果為None則使用當前時間

    Returns:
        Message: 特徵數據消息
    """
    data = {"symbol": symbol, "features": features}

    return Message(
        message_type=MessageType.FEATURE_DATA,
        data=data,
        timestamp=timestamp or datetime.now(),
        source="feature_processor",
    )


def create_model_request_message(
    model_id: str, features: Dict[str, Any], correlation_id: Optional[str] = None
) -> Message:
    """
    創建模型請求消息

    Args:
        model_id: 模型ID
        features: 特徵數據
        correlation_id: 相關消息ID

    Returns:
        Message: 模型請求消息
    """
    data = {"model_id": model_id, "features": features}

    return Message(
        message_type=MessageType.MODEL_REQUEST,
        data=data,
        source="feature_processor",
        destination="model_service",
        correlation_id=correlation_id,
        priority=MessagePriority.HIGH,
    )


def create_trade_signal_message(
    symbol: str,
    action: str,
    confidence: float,
    price: Optional[float] = None,
    quantity: Optional[float] = None,
    timestamp: Optional[datetime] = None,
) -> Message:
    """
    創建交易信號消息

    Args:
        symbol: 股票代碼
        action: 交易動作，可選 'buy', 'sell', 'hold'
        confidence: 信心值，範圍 0-1
        price: 價格
        quantity: 數量
        timestamp: 時間戳，如果為None則使用當前時間

    Returns:
        Message: 交易信號消息
    """
    data = {"symbol": symbol, "action": action, "confidence": confidence}

    if price is not None:
        data["price"] = price

    if quantity is not None:
        data["quantity"] = quantity

    return Message(
        message_type=MessageType.TRADE_SIGNAL,
        data=data,
        timestamp=timestamp or datetime.now(),
        source="model_service",
        destination="trade_executor",
        priority=MessagePriority.URGENT,
    )
