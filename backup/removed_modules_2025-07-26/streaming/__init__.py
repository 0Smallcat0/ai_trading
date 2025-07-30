"""
實時數據流處理模組

此模組提供實時數據流處理的核心功能，包括：
- 數據流管道定義
- 消息格式和協議
- 數據處理階段
- 實時特徵更新
- 模型推理服務
- 流式數據更新機制
"""

from .consumer import Consumer, KafkaConsumer, WebSocketConsumer
from .message import Message, MessageSchema, MessageType
from .monitor import StreamMonitor
from .pipeline import Pipeline, StreamingPipeline
from .processor import FeatureProcessor, ModelProcessor, Processor
from .producer import KafkaProducer, Producer, WebSocketProducer
from .stream_manager import StreamManager

__all__ = [
    "StreamManager",
    "Message",
    "MessageType",
    "MessageSchema",
    "Producer",
    "KafkaProducer",
    "WebSocketProducer",
    "Consumer",
    "KafkaConsumer",
    "WebSocketConsumer",
    "Processor",
    "FeatureProcessor",
    "ModelProcessor",
    "Pipeline",
    "StreamingPipeline",
    "StreamMonitor",
]
