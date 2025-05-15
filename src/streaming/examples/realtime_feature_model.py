"""
實時特徵更新和模型推理示例

此示例展示了如何使用流處理框架進行實時特徵更新和模型推理。
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
    WebSocketProducer,
    KafkaProducer,
    Consumer,
    WebSocketConsumer,
    KafkaConsumer,
    Processor,
    FeatureProcessor,
    ModelProcessor,
    Pipeline,
    StreamingPipeline,
    FeaturePipeline,
    ModelPipeline,
    StreamMonitor,
)

# 導入特徵計算函數
from src.core.features import (
    calculate_rsi,
    calculate_macd,
    calculate_bollinger_bands,
    calculate_atr,
    calculate_obv,
    calculate_vwap,
)

# 導入模型
from src.models.model_loader import load_model

# 設定日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("realtime_example")


# 定義特徵計算函數
def calculate_features(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    計算特徵

    Args:
        data: 市場數據列表

    Returns:
        Dict[str, Any]: 特徵字典
    """
    # 轉換為 DataFrame
    df = pd.DataFrame(data)

    # 確保數據按時間排序
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")

    # 計算特徵
    features = {}

    # 檢查是否有足夠的數據
    if len(df) < 14:
        logger.warning(f"數據不足，無法計算特徵: {len(df)} < 14")
        return features

    try:
        # 計算 RSI
        features["rsi"] = calculate_rsi(df["price"].values, period=14)[-1]

        # 計算 MACD
        macd, signal, hist = calculate_macd(df["price"].values)
        features["macd"] = macd[-1]
        features["macd_signal"] = signal[-1]
        features["macd_hist"] = hist[-1]

        # 計算布林帶
        upper, middle, lower = calculate_bollinger_bands(df["price"].values)
        features["bb_upper"] = upper[-1]
        features["bb_middle"] = middle[-1]
        features["bb_lower"] = lower[-1]

        # 計算 ATR
        if all(col in df.columns for col in ["high", "low", "price"]):
            features["atr"] = calculate_atr(
                df["high"].values, df["low"].values, df["price"].values
            )[-1]

        # 計算 OBV
        if "volume" in df.columns:
            features["obv"] = calculate_obv(df["price"].values, df["volume"].values)[-1]

        # 計算 VWAP
        if all(col in df.columns for col in ["price", "volume"]):
            features["vwap"] = calculate_vwap(df["price"].values, df["volume"].values)[
                -1
            ]

        # 添加最新價格
        features["price"] = df["price"].iloc[-1]

        # 添加價格變化率
        features["price_change"] = df["price"].pct_change().iloc[-1]

        # 添加成交量變化率
        if "volume" in df.columns:
            features["volume_change"] = df["volume"].pct_change().iloc[-1]
    except Exception as e:
        logger.error(f"計算特徵時發生錯誤: {e}")

    return features


# 模擬市場數據生產者
class MarketDataProducer(Producer):
    """模擬市場數據生產者"""

    def __init__(
        self, name: str, symbols: List[str], stream_manager=None, interval: float = 1.0
    ):
        """
        初始化市場數據生產者

        Args:
            name: 生產者名稱
            symbols: 股票代碼列表
            stream_manager: 流管理器實例
            interval: 數據生成間隔（秒）
        """
        super().__init__(name, stream_manager)
        self.symbols = symbols
        self.interval = interval

        # 初始價格
        self.prices = {symbol: 100.0 for symbol in symbols}

        logger.info(f"市場數據生產者 '{name}' 已初始化，股票: {symbols}")

    def _run(self):
        """運行市場數據生產者"""
        while self.running:
            # 為每個股票生成數據
            for symbol in self.symbols:
                try:
                    # 生成隨機價格變動
                    price_change = np.random.normal(0, 0.01)
                    new_price = self.prices[symbol] * (1 + price_change)
                    self.prices[symbol] = new_price

                    # 生成隨機成交量
                    volume = np.random.randint(1000, 10000)

                    # 生成高低價
                    high = new_price * (1 + abs(np.random.normal(0, 0.005)))
                    low = new_price * (1 - abs(np.random.normal(0, 0.005)))

                    # 創建市場數據消息
                    data = {
                        "symbol": symbol,
                        "price": new_price,
                        "volume": volume,
                        "high": high,
                        "low": low,
                        "timestamp": datetime.now().isoformat(),
                    }

                    # 創建消息
                    message = Message(
                        message_type=MessageType.MARKET_DATA,
                        data=data,
                        source=self.name,
                    )

                    # 發布消息
                    self.publish(message)
                except Exception as e:
                    logger.error(f"生成市場數據時發生錯誤: {e}")

            # 等待下一個間隔
            time.sleep(self.interval)


# 交易信號處理器
class TradingSignalProcessor(Processor):
    """交易信號處理器"""

    def __init__(
        self, name: str, stream_manager=None, confidence_threshold: float = 0.6
    ):
        """
        初始化交易信號處理器

        Args:
            name: 處理器名稱
            stream_manager: 流管理器實例
            confidence_threshold: 置信度閾值
        """
        super().__init__(name, stream_manager)
        self.confidence_threshold = confidence_threshold

        # 交易信號緩存
        self.signals = {}

        logger.info(f"交易信號處理器 '{name}' 已初始化")

    def process_message(self, message: Message) -> Optional[Message]:
        """
        處理消息，生成交易信號

        Args:
            message: 消息實例

        Returns:
            Optional[Message]: 交易信號消息或None
        """
        # 檢查消息類型
        if message.message_type != MessageType.MODEL_RESPONSE:
            return None

        # 獲取預測結果
        predictions = message.data.get("predictions")
        if not predictions:
            logger.warning(f"交易信號處理器 '{self.name}' 收到的消息缺少預測結果")
            return None

        # 獲取股票代碼
        symbol = message.data.get("symbol")
        if not symbol:
            logger.warning(f"交易信號處理器 '{self.name}' 收到的消息缺少股票代碼")
            return None

        # 獲取置信度和動作
        confidence = predictions.get("confidence", 0.0)
        action = predictions.get("action", "hold")

        # 檢查置信度是否超過閾值
        if confidence < self.confidence_threshold:
            logger.info(
                f"股票 {symbol} 的置信度 {confidence:.2f} 低於閾值 {self.confidence_threshold:.2f}，不生成交易信號"
            )
            return None

        # 檢查是否與上一個信號相同
        if symbol in self.signals and self.signals[symbol]["action"] == action:
            logger.info(f"股票 {symbol} 的交易信號與上一個相同 ({action})，不重複生成")
            return None

        # 更新交易信號緩存
        self.signals[symbol] = {
            "action": action,
            "confidence": confidence,
            "timestamp": datetime.now(),
        }

        # 創建交易信號消息
        return Message(
            message_type=MessageType.TRADE_SIGNAL,
            data={
                "symbol": symbol,
                "action": action,
                "confidence": confidence,
                "price": message.data.get("price"),
                "timestamp": datetime.now().isoformat(),
            },
            source=self.name,
            priority=MessagePriority.HIGH,
        )


def main():
    """主函數"""
    # 創建流管理器
    manager = StreamManager()

    # 創建監控器
    monitor = StreamMonitor(manager)

    # 設置股票列表
    symbols = ["2330", "2317", "2454", "2412", "2308"]

    # 創建市場數據生產者
    market_producer = MarketDataProducer("market_data", symbols, manager)

    # 註冊生產者
    manager.register_producer("market_data", market_producer)

    # 創建特徵處理器
    feature_processor = FeatureProcessor(
        "feature_processor",
        {"features": calculate_features},
        [MessageType.MARKET_DATA],
        MessageType.FEATURE_DATA,
        manager,
        window_size=100,
        update_interval=1.0,
    )

    # 註冊處理器
    manager.register_processor("feature_processor", feature_processor)

    # 加載模型
    try:
        model = load_model("latest")

        # 創建模型處理器
        model_processor = ModelProcessor(
            "model_processor",
            model,
            MessageType.FEATURE_DATA,
            MessageType.MODEL_RESPONSE,
            manager,
            feature_processor,
            confidence_threshold=0.5,
        )

        # 註冊處理器
        manager.register_processor("model_processor", model_processor)
    except Exception as e:
        logger.error(f"加載模型時發生錯誤: {e}")
        model_processor = None

    # 創建交易信號處理器
    signal_processor = TradingSignalProcessor(
        "signal_processor", manager, confidence_threshold=0.6
    )

    # 註冊處理器
    manager.register_processor("signal_processor", signal_processor)

    # 訂閱消息
    manager.subscribe("feature_processor", [MessageType.MARKET_DATA])
    if model_processor:
        manager.subscribe("model_processor", [MessageType.FEATURE_DATA])
        manager.subscribe("signal_processor", [MessageType.MODEL_RESPONSE])

    # 啟動監控器
    monitor.start()

    # 啟動流管理器
    manager.start()

    try:
        # 運行一段時間
        logger.info("系統已啟動，按 Ctrl+C 停止")
        while True:
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
