"""
處理器模組

此模組實現了各種數據處理器，用於處理數據流中的消息。
"""

import logging
import threading
import time
import queue
import json
import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Callable, Set
from datetime import datetime

from .message import Message, MessageType, MessagePriority

# 設定日誌
logger = logging.getLogger("streaming.processor")


class Processor(ABC):
    """
    處理器抽象基類
    
    處理器負責：
    1. 處理數據流中的消息
    2. 轉換和豐富消息
    3. 生成新的消息
    """
    
    def __init__(self, name: str, stream_manager=None):
        """
        初始化處理器
        
        Args:
            name: 處理器名稱
            stream_manager: 流管理器實例，如果為None則使用全局實例
        """
        self.name = name
        self.running = False
        
        # 如果未提供流管理器，則導入全局實例
        if stream_manager is None:
            from .stream_manager import stream_manager
        self.stream_manager = stream_manager
        
        # 消息隊列
        self.message_queue = queue.Queue()
        self.processing_thread = None
        
        # 統計信息
        self.stats = {
            "messages_processed": 0,
            "messages_published": 0,
            "errors": 0,
            "start_time": None,
            "last_message_time": None
        }
        
        logger.info(f"處理器 '{name}' 已初始化")
    
    def start(self):
        """啟動處理器"""
        if self.running:
            logger.warning(f"處理器 '{self.name}' 已經在運行中")
            return
        
        self.running = True
        self.processing_thread = threading.Thread(target=self._process_messages)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        # 更新統計信息
        self.stats["start_time"] = time.time()
        
        logger.info(f"處理器 '{self.name}' 已啟動")
    
    def stop(self):
        """停止處理器"""
        if not self.running:
            logger.warning(f"處理器 '{self.name}' 未運行")
            return
        
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=10)
        
        logger.info(f"處理器 '{self.name}' 已停止")
    
    def process(self, message: Message):
        """
        處理消息
        
        Args:
            message: 消息實例
        """
        try:
            # 將消息放入隊列
            self.message_queue.put(message, block=False)
        except queue.Full:
            logger.error(f"處理器 '{self.name}' 消息隊列已滿")
            self.stats["errors"] += 1
    
    def publish(self, message: Message) -> bool:
        """
        發布消息
        
        Args:
            message: 消息實例
            
        Returns:
            bool: 是否成功發布
        """
        # 設置消息來源
        if not message.source:
            message.source = self.name
        
        # 發布消息
        result = self.stream_manager.publish(message)
        
        # 更新統計信息
        if result:
            self.stats["messages_published"] += 1
        else:
            self.stats["errors"] += 1
        
        return result
    
    def _process_messages(self):
        """處理消息隊列中的消息"""
        while self.running:
            try:
                # 從隊列中獲取消息
                try:
                    message = self.message_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # 處理消息
                try:
                    result = self.process_message(message)
                    
                    # 更新統計信息
                    self.stats["messages_processed"] += 1
                    self.stats["last_message_time"] = time.time()
                    
                    # 如果處理結果是一個新消息，則發布它
                    if isinstance(result, Message):
                        self.publish(result)
                    elif isinstance(result, list) and all(isinstance(m, Message) for m in result):
                        for m in result:
                            self.publish(m)
                except Exception as e:
                    logger.error(f"處理器 '{self.name}' 處理消息時發生錯誤: {e}")
                    self.stats["errors"] += 1
                
                # 標記任務完成
                self.message_queue.task_done()
            except Exception as e:
                logger.exception(f"處理器 '{self.name}' 處理消息隊列時發生錯誤: {e}")
                time.sleep(0.1)  # 避免在錯誤情況下過度消耗 CPU
    
    @abstractmethod
    def process_message(self, message: Message) -> Optional[Union[Message, List[Message]]]:
        """
        處理消息的抽象方法，子類必須實現
        
        Args:
            message: 消息實例
            
        Returns:
            Optional[Union[Message, List[Message]]]: 處理結果，可以是一個新消息、消息列表或None
        """
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """
        獲取統計信息
        
        Returns:
            Dict[str, Any]: 統計信息
        """
        # 計算運行時間
        uptime = time.time() - self.stats["start_time"] if self.stats["start_time"] else 0
        
        # 計算消息處理速率
        messages_per_second = self.stats["messages_processed"] / uptime if uptime > 0 else 0
        
        # 獲取隊列大小
        queue_size = self.message_queue.qsize()
        
        # 構建統計信息
        stats = {
            **self.stats,
            "uptime": uptime,
            "messages_per_second": messages_per_second,
            "queue_size": queue_size,
            "running": self.running
        }
        
        return stats


class FeatureProcessor(Processor):
    """
    特徵處理器，用於計算和更新特徵
    """
    
    def __init__(
        self,
        name: str,
        feature_functions: Dict[str, Callable[[Dict[str, Any]], Any]],
        input_message_types: List[MessageType],
        output_message_type: MessageType = MessageType.FEATURE_DATA,
        stream_manager=None,
        window_size: int = 100,
        update_interval: float = 0.0
    ):
        """
        初始化特徵處理器
        
        Args:
            name: 處理器名稱
            feature_functions: 特徵計算函數字典，key 為特徵名稱，value 為計算函數
            input_message_types: 輸入消息類型列表
            output_message_type: 輸出消息類型
            stream_manager: 流管理器實例
            window_size: 數據窗口大小
            update_interval: 特徵更新間隔（秒），如果為 0 則每次收到消息都更新
        """
        super().__init__(name, stream_manager)
        self.feature_functions = feature_functions
        self.input_message_types = input_message_types
        self.output_message_type = output_message_type
        self.window_size = window_size
        self.update_interval = update_interval
        
        # 數據緩存
        self.data_cache: Dict[str, List[Dict[str, Any]]] = {}
        
        # 特徵緩存
        self.feature_cache: Dict[str, Dict[str, Any]] = {}
        
        # 上次更新時間
        self.last_update_time: Dict[str, float] = {}
        
        logger.info(f"特徵處理器 '{name}' 已初始化，特徵數量: {len(feature_functions)}")
    
    def start(self):
        """啟動特徵處理器"""
        # 訂閱輸入消息類型
        for message_type in self.input_message_types:
            self.stream_manager.subscribe(self.name, [message_type])
        
        super().start()
    
    def process_message(self, message: Message) -> Optional[Message]:
        """
        處理消息，計算和更新特徵
        
        Args:
            message: 消息實例
            
        Returns:
            Optional[Message]: 特徵數據消息或None
        """
        # 檢查消息類型
        if message.message_type not in self.input_message_types:
            return None
        
        # 獲取股票代碼
        symbol = message.data.get("symbol")
        if not symbol:
            logger.warning(f"特徵處理器 '{self.name}' 收到的消息缺少股票代碼")
            return None
        
        # 更新數據緩存
        if symbol not in self.data_cache:
            self.data_cache[symbol] = []
        
        self.data_cache[symbol].append(message.data)
        
        # 限制緩存大小
        if len(self.data_cache[symbol]) > self.window_size:
            self.data_cache[symbol] = self.data_cache[symbol][-self.window_size:]
        
        # 檢查是否需要更新特徵
        current_time = time.time()
        last_update = self.last_update_time.get(symbol, 0)
        
        if current_time - last_update >= self.update_interval:
            # 計算特徵
            features = self._calculate_features(symbol)
            
            # 更新特徵緩存
            self.feature_cache[symbol] = features
            
            # 更新上次更新時間
            self.last_update_time[symbol] = current_time
            
            # 創建特徵數據消息
            return Message(
                message_type=self.output_message_type,
                data={
                    "symbol": symbol,
                    "features": features
                },
                source=self.name,
                timestamp=datetime.now()
            )
        
        return None
    
    def _calculate_features(self, symbol: str) -> Dict[str, Any]:
        """
        計算特徵
        
        Args:
            symbol: 股票代碼
            
        Returns:
            Dict[str, Any]: 特徵字典
        """
        # 獲取數據
        data = self.data_cache.get(symbol, [])
        if not data:
            return {}
        
        # 計算特徵
        features = {}
        for feature_name, feature_func in self.feature_functions.items():
            try:
                features[feature_name] = feature_func(data)
            except Exception as e:
                logger.error(f"特徵處理器 '{self.name}' 計算特徵 '{feature_name}' 時發生錯誤: {e}")
                self.stats["errors"] += 1
        
        return features
    
    def get_features(self, symbol: str) -> Dict[str, Any]:
        """
        獲取特徵
        
        Args:
            symbol: 股票代碼
            
        Returns:
            Dict[str, Any]: 特徵字典
        """
        return self.feature_cache.get(symbol, {})


class ModelProcessor(Processor):
    """
    模型處理器，用於模型推理
    """
    
    def __init__(
        self,
        name: str,
        model,
        input_message_type: MessageType = MessageType.FEATURE_DATA,
        output_message_type: MessageType = MessageType.MODEL_RESPONSE,
        stream_manager=None,
        feature_processor: Optional[FeatureProcessor] = None,
        confidence_threshold: float = 0.5
    ):
        """
        初始化模型處理器
        
        Args:
            name: 處理器名稱
            model: 模型實例
            input_message_type: 輸入消息類型
            output_message_type: 輸出消息類型
            stream_manager: 流管理器實例
            feature_processor: 特徵處理器實例
            confidence_threshold: 置信度閾值
        """
        super().__init__(name, stream_manager)
        self.model = model
        self.input_message_type = input_message_type
        self.output_message_type = output_message_type
        self.feature_processor = feature_processor
        self.confidence_threshold = confidence_threshold
        
        # 預測緩存
        self.prediction_cache: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"模型處理器 '{name}' 已初始化")
    
    def start(self):
        """啟動模型處理器"""
        # 訂閱輸入消息類型
        self.stream_manager.subscribe(self.name, [self.input_message_type])
        
        super().start()
    
    def process_message(self, message: Message) -> Optional[Message]:
        """
        處理消息，進行模型推理
        
        Args:
            message: 消息實例
            
        Returns:
            Optional[Message]: 模型響應消息或None
        """
        # 檢查消息類型
        if message.message_type != self.input_message_type:
            return None
        
        # 獲取特徵
        features = message.data.get("features")
        if not features:
            logger.warning(f"模型處理器 '{self.name}' 收到的消息缺少特徵數據")
            return None
        
        # 獲取股票代碼
        symbol = message.data.get("symbol")
        if not symbol:
            logger.warning(f"模型處理器 '{self.name}' 收到的消息缺少股票代碼")
            return None
        
        try:
            # 進行模型推理
            predictions = self._predict(features)
            
            # 更新預測緩存
            self.prediction_cache[symbol] = predictions
            
            # 創建模型響應消息
            return Message(
                message_type=self.output_message_type,
                data={
                    "symbol": symbol,
                    "predictions": predictions,
                    "confidence": predictions.get("confidence", 0.0),
                    "action": predictions.get("action", "hold")
                },
                source=self.name,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"模型處理器 '{self.name}' 進行模型推理時發生錯誤: {e}")
            self.stats["errors"] += 1
            return None
    
    def _predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        進行模型推理
        
        Args:
            features: 特徵字典
            
        Returns:
            Dict[str, Any]: 預測結果
        """
        # 轉換特徵為模型輸入格式
        try:
            # 如果模型有 predict_proba 方法，則使用它
            if hasattr(self.model, 'predict_proba'):
                probabilities = self.model.predict_proba([list(features.values())])[0]
                prediction = self.model.predict([list(features.values())])[0]
                
                # 獲取最高概率
                confidence = max(probabilities)
                
                # 根據預測結果確定動作
                if isinstance(prediction, (int, np.integer)):
                    action = "buy" if prediction > 0 else "sell" if prediction < 0 else "hold"
                else:
                    action = str(prediction)
                
                return {
                    "action": action,
                    "confidence": float(confidence),
                    "probabilities": {str(i): float(p) for i, p in enumerate(probabilities)}
                }
            else:
                # 否則使用普通的 predict 方法
                prediction = self.model.predict([list(features.values())])[0]
                
                # 根據預測結果確定動作
                if isinstance(prediction, (int, np.integer)):
                    action = "buy" if prediction > 0 else "sell" if prediction < 0 else "hold"
                else:
                    action = str(prediction)
                
                return {
                    "action": action,
                    "confidence": 1.0,  # 沒有概率信息，默認為 1.0
                    "prediction": float(prediction) if isinstance(prediction, (int, float, np.number)) else str(prediction)
                }
        except Exception as e:
            logger.error(f"模型處理器 '{self.name}' 轉換特徵時發生錯誤: {e}")
            raise
    
    def get_prediction(self, symbol: str) -> Dict[str, Any]:
        """
        獲取預測結果
        
        Args:
            symbol: 股票代碼
            
        Returns:
            Dict[str, Any]: 預測結果
        """
        return self.prediction_cache.get(symbol, {})
