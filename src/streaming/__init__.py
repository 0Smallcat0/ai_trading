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

from .stream_manager import StreamManager
from .message import Message, MessageType, MessageSchema
from .producer import Producer, KafkaProducer, WebSocketProducer
from .consumer import Consumer, KafkaConsumer, WebSocketConsumer
from .processor import Processor, FeatureProcessor, ModelProcessor
from .pipeline import Pipeline, StreamingPipeline
from .monitor import StreamMonitor

__all__ = [
    'StreamManager',
    'Message',
    'MessageType',
    'MessageSchema',
    'Producer',
    'KafkaProducer',
    'WebSocketProducer',
    'Consumer',
    'KafkaConsumer',
    'WebSocketConsumer',
    'Processor',
    'FeatureProcessor',
    'ModelProcessor',
    'Pipeline',
    'StreamingPipeline',
    'StreamMonitor',
]
