"""
管道模組

此模組實現了數據處理管道，用於組合多個處理器形成處理流程。
"""

import logging
import threading
import time
from typing import Dict, List, Any, Optional, Union, Callable
from abc import ABC, abstractmethod

from .message import Message, MessageType
from .processor import Processor

# 設定日誌
logger = logging.getLogger("streaming.pipeline")


class Pipeline(ABC):
    """
    管道抽象基類

    管道負責：
    1. 組合多個處理器
    2. 定義數據處理流程
    3. 管理處理器之間的數據流
    """

    def __init__(self, name: str, stream_manager=None):
        """
        初始化管道

        Args:
            name: 管道名稱
            stream_manager: 流管理器實例，如果為None則使用全局實例
        """
        self.name = name
        self.running = False

        # 如果未提供流管理器，則導入全局實例
        if stream_manager is None:
            from .stream_manager import stream_manager
        self.stream_manager = stream_manager

        # 處理器列表
        self.processors: List[Processor] = []

        # 統計信息
        self.stats = {"start_time": None, "processors": 0}

        logger.info(f"管道 '{name}' 已初始化")

    def add_processor(self, processor: Processor) -> bool:
        """
        添加處理器

        Args:
            processor: 處理器實例

        Returns:
            bool: 是否成功添加
        """
        if processor in self.processors:
            logger.warning(f"處理器 '{processor.name}' 已在管道 '{self.name}' 中")
            return False

        self.processors.append(processor)
        self.stats["processors"] += 1

        logger.info(f"處理器 '{processor.name}' 已添加到管道 '{self.name}'")
        return True

    def start(self) -> bool:
        """
        啟動管道

        Returns:
            bool: 是否成功啟動
        """
        if self.running:
            logger.warning(f"管道 '{self.name}' 已經在運行中")
            return False

        # 啟動所有處理器
        for processor in self.processors:
            processor.start()

        self.running = True
        self.stats["start_time"] = time.time()

        logger.info(f"管道 '{self.name}' 已啟動")
        return True

    def stop(self) -> bool:
        """
        停止管道

        Returns:
            bool: 是否成功停止
        """
        if not self.running:
            logger.warning(f"管道 '{self.name}' 未運行")
            return False

        # 停止所有處理器
        for processor in self.processors:
            processor.stop()

        self.running = False

        logger.info(f"管道 '{self.name}' 已停止")
        return True

    def get_stats(self) -> Dict[str, Any]:
        """
        獲取統計信息

        Returns:
            Dict[str, Any]: 統計信息
        """
        # 計算運行時間
        uptime = (
            time.time() - self.stats["start_time"] if self.stats["start_time"] else 0
        )

        # 獲取處理器統計信息
        processor_stats = {
            processor.name: processor.get_stats() for processor in self.processors
        }

        # 構建統計信息
        stats = {
            **self.stats,
            "uptime": uptime,
            "running": self.running,
            "processors": len(self.processors),
            "processor_stats": processor_stats,
        }

        return stats


class StreamingPipeline(Pipeline):
    """
    流式處理管道，用於實時數據處理
    """

    def __init__(
        self,
        name: str,
        input_message_types: List[MessageType],
        output_message_types: List[MessageType],
        stream_manager=None,
    ):
        """
        初始化流式處理管道

        Args:
            name: 管道名稱
            input_message_types: 輸入消息類型列表
            output_message_types: 輸出消息類型列表
            stream_manager: 流管理器實例
        """
        super().__init__(name, stream_manager)
        self.input_message_types = input_message_types
        self.output_message_types = output_message_types

        # 處理器映射
        self.processor_map: Dict[MessageType, List[Processor]] = {}

        logger.info(f"流式處理管道 '{name}' 已初始化")

    def add_processor(
        self, processor: Processor, input_types: Optional[List[MessageType]] = None
    ) -> bool:
        """
        添加處理器

        Args:
            processor: 處理器實例
            input_types: 處理器接收的消息類型列表，如果為None則使用管道的輸入類型

        Returns:
            bool: 是否成功添加
        """
        # 添加到處理器列表
        if not super().add_processor(processor):
            return False

        # 設置處理器映射
        types = input_types or self.input_message_types
        for message_type in types:
            if message_type not in self.processor_map:
                self.processor_map[message_type] = []
            self.processor_map[message_type].append(processor)

        return True

    def start(self) -> bool:
        """
        啟動流式處理管道

        Returns:
            bool: 是否成功啟動
        """
        if self.running:
            logger.warning(f"流式處理管道 '{self.name}' 已經在運行中")
            return False

        # 訂閱輸入消息類型
        for message_type in self.input_message_types:
            self.stream_manager.subscribe(self.name, [message_type])

        # 啟動管道
        return super().start()

    def process(self, message: Message):
        """
        處理消息

        Args:
            message: 消息實例
        """
        # 檢查消息類型
        if message.message_type not in self.processor_map:
            return

        # 獲取處理器列表
        processors = self.processor_map[message.message_type]

        # 將消息發送給所有處理器
        for processor in processors:
            processor.process(message)


class FeaturePipeline(StreamingPipeline):
    """
    特徵處理管道，用於特徵計算和更新
    """

    def __init__(
        self,
        name: str,
        feature_processors: List[Processor],
        input_message_types: List[MessageType],
        output_message_type: MessageType = MessageType.FEATURE_DATA,
        stream_manager=None,
    ):
        """
        初始化特徵處理管道

        Args:
            name: 管道名稱
            feature_processors: 特徵處理器列表
            input_message_types: 輸入消息類型列表
            output_message_type: 輸出消息類型
            stream_manager: 流管理器實例
        """
        super().__init__(
            name, input_message_types, [output_message_type], stream_manager
        )

        # 添加特徵處理器
        for processor in feature_processors:
            self.add_processor(processor)

        logger.info(
            f"特徵處理管道 '{name}' 已初始化，處理器數量: {len(feature_processors)}"
        )


class ModelPipeline(StreamingPipeline):
    """
    模型處理管道，用於模型推理
    """

    def __init__(
        self,
        name: str,
        model_processors: List[Processor],
        input_message_type: MessageType = MessageType.FEATURE_DATA,
        output_message_type: MessageType = MessageType.MODEL_RESPONSE,
        stream_manager=None,
    ):
        """
        初始化模型處理管道

        Args:
            name: 管道名稱
            model_processors: 模型處理器列表
            input_message_type: 輸入消息類型
            output_message_type: 輸出消息類型
            stream_manager: 流管理器實例
        """
        super().__init__(
            name, [input_message_type], [output_message_type], stream_manager
        )

        # 添加模型處理器
        for processor in model_processors:
            self.add_processor(processor)

        logger.info(
            f"模型處理管道 '{name}' 已初始化，處理器數量: {len(model_processors)}"
        )


class TradingPipeline(StreamingPipeline):
    """
    交易處理管道，用於生成交易信號和執行交易
    """

    def __init__(
        self,
        name: str,
        trading_processors: List[Processor],
        input_message_type: MessageType = MessageType.MODEL_RESPONSE,
        output_message_type: MessageType = MessageType.TRADE_SIGNAL,
        stream_manager=None,
    ):
        """
        初始化交易處理管道

        Args:
            name: 管道名稱
            trading_processors: 交易處理器列表
            input_message_type: 輸入消息類型
            output_message_type: 輸出消息類型
            stream_manager: 流管理器實例
        """
        super().__init__(
            name, [input_message_type], [output_message_type], stream_manager
        )

        # 添加交易處理器
        for processor in trading_processors:
            self.add_processor(processor)

        logger.info(
            f"交易處理管道 '{name}' 已初始化，處理器數量: {len(trading_processors)}"
        )
