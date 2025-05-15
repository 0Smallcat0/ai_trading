"""
Kafka 流處理示例

此示例展示了如何使用 Kafka 進行流處理。
"""

import os
import sys
import time
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import threading
import queue
from typing import Dict, List, Any, Optional, Union

# 添加項目根目錄到 Python 路徑
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)

# 導入流處理模組
from src.streaming import (
    StreamManager,
    Message,
    MessageType,
    MessagePriority,
    Producer,
    KafkaProducer,
    Consumer,
    KafkaConsumer,
    Processor,
    FeatureProcessor,
    ModelProcessor,
    Pipeline,
    StreamingPipeline,
    StreamMonitor,
)

# 設定日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("kafka_example")


# Kafka 消息轉換函數
def kafka_to_message(value: Dict[str, Any]) -> Optional[Message]:
    """
    將 Kafka 消息轉換為 Message 實例

    Args:
        value: Kafka 消息值

    Returns:
        Optional[Message]: Message 實例或 None
    """
    try:
        # 檢查消息格式
        if not isinstance(value, dict):
            logger.warning(f"無效的消息格式: {value}")
            return None

        # 檢查必要字段
        if "message_type" not in value or "data" not in value:
            logger.warning(f"消息缺少必要字段: {value}")
            return None

        # 獲取消息類型
        try:
            message_type = MessageType[value["message_type"]]
        except KeyError:
            logger.warning(f"無效的消息類型: {value['message_type']}")
            return None

        # 獲取優先級
        priority = MessagePriority.NORMAL
        if "priority" in value:
            try:
                priority = MessagePriority[value["priority"]]
            except KeyError:
                pass

        # 創建消息
        return Message(
            message_type=message_type,
            data=value["data"],
            source=value.get("source"),
            destination=value.get("destination"),
            priority=priority,
            correlation_id=value.get("correlation_id"),
        )
    except Exception as e:
        logger.error(f"轉換 Kafka 消息時發生錯誤: {e}")
        return None


# 市場數據處理器
class MarketDataProcessor(Processor):
    """市場數據處理器"""

    def __init__(self, name: str, stream_manager=None):
        """
        初始化市場數據處理器

        Args:
            name: 處理器名稱
            stream_manager: 流管理器實例
        """
        super().__init__(name, stream_manager)

        # 市場數據緩存
        self.market_data = {}

        logger.info(f"市場數據處理器 '{name}' 已初始化")

    def process_message(self, message: Message) -> Optional[Message]:
        """
        處理消息

        Args:
            message: 消息實例

        Returns:
            Optional[Message]: 處理結果
        """
        # 檢查消息類型
        if message.message_type != MessageType.MARKET_DATA:
            return None

        # 獲取股票代碼
        symbol = message.data.get("symbol")
        if not symbol:
            logger.warning(f"市場數據處理器 '{self.name}' 收到的消息缺少股票代碼")
            return None

        # 更新市場數據緩存
        if symbol not in self.market_data:
            self.market_data[symbol] = []

        self.market_data[symbol].append(message.data)

        # 限制緩存大小
        if len(self.market_data[symbol]) > 100:
            self.market_data[symbol] = self.market_data[symbol][-100:]

        # 計算簡單統計
        prices = [
            data.get("price", 0) for data in self.market_data[symbol] if "price" in data
        ]
        volumes = [
            data.get("volume", 0)
            for data in self.market_data[symbol]
            if "volume" in data
        ]

        if prices:
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)

            # 創建統計消息
            return Message(
                message_type=MessageType.INFO,
                data={
                    "symbol": symbol,
                    "avg_price": avg_price,
                    "min_price": min_price,
                    "max_price": max_price,
                    "price_count": len(prices),
                    "volume_sum": sum(volumes) if volumes else 0,
                    "timestamp": datetime.now().isoformat(),
                },
                source=self.name,
            )

        return None


def main():
    """主函數"""
    # 檢查 Kafka 是否可用
    try:
        from kafka import KafkaProducer as KafkaClient
    except ImportError:
        logger.error("Kafka 套件未安裝，請先安裝: pip install kafka-python")
        return

    # 創建流管理器
    manager = StreamManager()

    # 創建監控器
    monitor = StreamMonitor(manager)

    # Kafka 配置
    bootstrap_servers = "localhost:9092"

    # 創建 Kafka 生產者
    try:
        kafka_producer = KafkaProducer(
            "kafka_producer", bootstrap_servers, "market_data", manager
        )

        # 註冊生產者
        manager.register_producer("kafka_producer", kafka_producer)
    except Exception as e:
        logger.error(f"創建 Kafka 生產者時發生錯誤: {e}")
        kafka_producer = None

    # 創建 Kafka 消費者
    try:
        kafka_consumer = KafkaConsumer(
            "kafka_consumer",
            bootstrap_servers,
            ["market_data"],
            manager,
            group_id="trading_group",
            message_converter=kafka_to_message,
        )

        # 註冊消費者
        manager.register_consumer("kafka_consumer", kafka_consumer)
    except Exception as e:
        logger.error(f"創建 Kafka 消費者時發生錯誤: {e}")
        kafka_consumer = None

    # 創建市場數據處理器
    market_processor = MarketDataProcessor("market_processor", manager)

    # 註冊處理器
    manager.register_processor("market_processor", market_processor)

    # 訂閱消息
    manager.subscribe("market_processor", [MessageType.MARKET_DATA])

    # 啟動監控器
    monitor.start()

    # 啟動流管理器
    manager.start()

    # 生成模擬市場數據
    symbols = ["2330", "2317", "2454", "2412", "2308"]
    prices = {symbol: 100.0 for symbol in symbols}

    try:
        # 運行一段時間
        logger.info("系統已啟動，按 Ctrl+C 停止")

        count = 0
        while count < 100:  # 生成 100 條消息後停止
            # 為每個股票生成數據
            for symbol in symbols:
                try:
                    # 生成隨機價格變動
                    price_change = np.random.normal(0, 0.01)
                    new_price = prices[symbol] * (1 + price_change)
                    prices[symbol] = new_price

                    # 生成隨機成交量
                    volume = np.random.randint(1000, 10000)

                    # 創建市場數據消息
                    data = {
                        "symbol": symbol,
                        "price": new_price,
                        "volume": volume,
                        "timestamp": datetime.now().isoformat(),
                    }

                    # 創建消息
                    message = Message(
                        message_type=MessageType.MARKET_DATA,
                        data=data,
                        source="simulator",
                    )

                    # 發布消息到 Kafka
                    if kafka_producer:
                        kafka_producer.publish(message)

                    count += 1
                except Exception as e:
                    logger.error(f"生成市場數據時發生錯誤: {e}")

            # 等待一秒
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("接收到停止信號")
    finally:
        # 停止流管理器
        manager.stop()

        # 停止監控器
        monitor.stop()

        logger.info("系統已停止")


if __name__ == "__main__":
    main()
