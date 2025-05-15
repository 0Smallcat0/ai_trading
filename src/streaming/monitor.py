"""
監控器模組

此模組實現了數據流監控器，用於監控數據流的狀態和性能。
"""

import logging
import threading
import time
import json
import os
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
import psutil

from .message import Message, MessageType, MessagePriority

# 設定日誌
logger = logging.getLogger("streaming.monitor")


class StreamMonitor:
    """
    數據流監控器，用於監控數據流的狀態和性能
    
    監控器負責：
    1. 監控數據流的狀態
    2. 收集性能指標
    3. 檢測異常情況
    4. 生成監控報告
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        """實現單例模式"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(StreamMonitor, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self, stream_manager=None, monitoring_interval: int = 60, log_dir: str = "logs/monitor"):
        """
        初始化監控器
        
        Args:
            stream_manager: 流管理器實例，如果為None則使用全局實例
            monitoring_interval: 監控間隔（秒）
            log_dir: 日誌目錄
        """
        # 避免重複初始化
        if self._initialized:
            return
        
        # 如果未提供流管理器，則導入全局實例
        if stream_manager is None:
            from .stream_manager import stream_manager
        self.stream_manager = stream_manager
        
        self.monitoring_interval = monitoring_interval
        self.log_dir = log_dir
        
        # 創建日誌目錄
        os.makedirs(log_dir, exist_ok=True)
        
        # 監控線程
        self.monitoring_thread = None
        self.running = False
        
        # 監控數據
        self.metrics = {
            "stream_manager": {},
            "producers": {},
            "consumers": {},
            "processors": {},
            "pipelines": {},
            "system": {},
            "timestamp": None
        }
        
        # 警報閾值
        self.thresholds = {
            "queue_usage": 0.8,  # 隊列使用率閾值
            "error_rate": 0.01,  # 錯誤率閾值
            "cpu_usage": 80.0,   # CPU 使用率閾值
            "memory_usage": 80.0  # 內存使用率閾值
        }
        
        # 警報回調
        self.alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        self._initialized = True
        logger.info("數據流監控器已初始化")
    
    def start(self):
        """啟動監控器"""
        if self.running:
            logger.warning("監控器已經在運行中")
            return
        
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        logger.info("數據流監控器已啟動")
    
    def stop(self):
        """停止監控器"""
        if not self.running:
            logger.warning("監控器未運行")
            return
        
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=10)
        
        logger.info("數據流監控器已停止")
    
    def _monitoring_loop(self):
        """監控循環"""
        while self.running:
            try:
                # 收集指標
                self._collect_metrics()
                
                # 檢查異常
                self._check_anomalies()
                
                # 記錄指標
                self._log_metrics()
                
                # 等待下一個監控間隔
                time.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"監控循環發生錯誤: {e}")
                time.sleep(10)  # 發生錯誤時等待較長時間
    
    def _collect_metrics(self):
        """收集指標"""
        # 更新時間戳
        self.metrics["timestamp"] = datetime.now().isoformat()
        
        # 收集流管理器指標
        self.metrics["stream_manager"] = self.stream_manager.get_stats()
        
        # 收集生產者指標
        self.metrics["producers"] = {
            name: producer.get_stats()
            for name, producer in self.stream_manager.producers.items()
        }
        
        # 收集消費者指標
        self.metrics["consumers"] = {
            name: consumer.get_stats()
            for name, consumer in self.stream_manager.consumers.items()
        }
        
        # 收集處理器指標
        self.metrics["processors"] = {
            name: processor.get_stats()
            for name, processor in self.stream_manager.processors.items()
        }
        
        # 收集管道指標
        self.metrics["pipelines"] = {
            name: pipeline.get_stats()
            for name, pipeline in self.stream_manager.pipelines.items()
        }
        
        # 收集系統指標
        self.metrics["system"] = self._collect_system_metrics()
    
    def _collect_system_metrics(self) -> Dict[str, Any]:
        """
        收集系統指標
        
        Returns:
            Dict[str, Any]: 系統指標
        """
        # 獲取 CPU 使用率
        cpu_usage = psutil.cpu_percent(interval=1)
        
        # 獲取內存使用率
        memory = psutil.virtual_memory()
        memory_usage = memory.percent
        
        # 獲取磁盤使用率
        disk = psutil.disk_usage("/")
        disk_usage = disk.percent
        
        # 獲取網絡 IO 統計
        net_io = psutil.net_io_counters()
        
        return {
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "memory_total": memory.total,
            "memory_available": memory.available,
            "disk_usage": disk_usage,
            "disk_total": disk.total,
            "disk_free": disk.free,
            "net_bytes_sent": net_io.bytes_sent,
            "net_bytes_recv": net_io.bytes_recv,
            "net_packets_sent": net_io.packets_sent,
            "net_packets_recv": net_io.packets_recv
        }
    
    def _check_anomalies(self):
        """檢查異常情況"""
        # 檢查隊列使用率
        queue_usage = self.metrics["stream_manager"].get("queue_usage", 0)
        if queue_usage > self.thresholds["queue_usage"]:
            self._trigger_alert(
                "queue_usage",
                f"隊列使用率過高: {queue_usage:.2%}",
                {
                    "queue_usage": queue_usage,
                    "threshold": self.thresholds["queue_usage"],
                    "queue_size": self.metrics["stream_manager"].get("queue_size", 0),
                    "queue_capacity": self.metrics["stream_manager"].get("queue_capacity", 0)
                }
            )
        
        # 檢查錯誤率
        messages_processed = self.metrics["stream_manager"].get("messages_processed", 0)
        errors = self.metrics["stream_manager"].get("errors", 0)
        if messages_processed > 0:
            error_rate = errors / messages_processed
            if error_rate > self.thresholds["error_rate"]:
                self._trigger_alert(
                    "error_rate",
                    f"錯誤率過高: {error_rate:.2%}",
                    {
                        "error_rate": error_rate,
                        "threshold": self.thresholds["error_rate"],
                        "errors": errors,
                        "messages_processed": messages_processed
                    }
                )
        
        # 檢查 CPU 使用率
        cpu_usage = self.metrics["system"].get("cpu_usage", 0)
        if cpu_usage > self.thresholds["cpu_usage"]:
            self._trigger_alert(
                "cpu_usage",
                f"CPU 使用率過高: {cpu_usage:.2f}%",
                {
                    "cpu_usage": cpu_usage,
                    "threshold": self.thresholds["cpu_usage"]
                }
            )
        
        # 檢查內存使用率
        memory_usage = self.metrics["system"].get("memory_usage", 0)
        if memory_usage > self.thresholds["memory_usage"]:
            self._trigger_alert(
                "memory_usage",
                f"內存使用率過高: {memory_usage:.2f}%",
                {
                    "memory_usage": memory_usage,
                    "threshold": self.thresholds["memory_usage"],
                    "memory_total": self.metrics["system"].get("memory_total", 0),
                    "memory_available": self.metrics["system"].get("memory_available", 0)
                }
            )
        
        # 檢查處理器錯誤
        for name, stats in self.metrics["processors"].items():
            errors = stats.get("errors", 0)
            messages_processed = stats.get("messages_processed", 0)
            if messages_processed > 0:
                error_rate = errors / messages_processed
                if error_rate > self.thresholds["error_rate"]:
                    self._trigger_alert(
                        "processor_error_rate",
                        f"處理器 '{name}' 錯誤率過高: {error_rate:.2%}",
                        {
                            "processor": name,
                            "error_rate": error_rate,
                            "threshold": self.thresholds["error_rate"],
                            "errors": errors,
                            "messages_processed": messages_processed
                        }
                    )
    
    def _trigger_alert(self, alert_type: str, message: str, data: Dict[str, Any]):
        """
        觸發警報
        
        Args:
            alert_type: 警報類型
            message: 警報消息
            data: 警報數據
        """
        logger.warning(f"警報: {message}")
        
        # 記錄警報
        alert_data = {
            "type": alert_type,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # 寫入警報日誌
        alert_log_path = os.path.join(self.log_dir, "alerts.json")
        try:
            with open(alert_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert_data, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"寫入警報日誌時發生錯誤: {e}")
        
        # 調用警報回調
        for callback in self.alert_callbacks:
            try:
                callback(alert_type, alert_data)
            except Exception as e:
                logger.error(f"調用警報回調時發生錯誤: {e}")
        
        # 發布警報消息
        try:
            # 如果未提供流管理器，則導入全局實例
            if self.stream_manager:
                # 創建警報消息
                alert_message = Message(
                    message_type=MessageType.WARNING,
                    data=alert_data,
                    source="stream_monitor",
                    priority=MessagePriority.HIGH
                )
                
                # 發布消息
                self.stream_manager.publish(alert_message)
        except Exception as e:
            logger.error(f"發布警報消息時發生錯誤: {e}")
    
    def _log_metrics(self):
        """記錄指標"""
        # 創建日誌文件名
        log_file = os.path.join(self.log_dir, f"metrics_{datetime.now().strftime('%Y%m%d')}.json")
        
        try:
            # 寫入日誌
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(self.metrics, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"寫入指標日誌時發生錯誤: {e}")
    
    def register_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """
        註冊警報回調
        
        Args:
            callback: 警報回調函數，接收警報類型和警報數據
        """
        if callback not in self.alert_callbacks:
            self.alert_callbacks.append(callback)
            logger.info(f"已註冊警報回調: {callback.__name__}")
    
    def unregister_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """
        取消註冊警報回調
        
        Args:
            callback: 警報回調函數
        """
        if callback in self.alert_callbacks:
            self.alert_callbacks.remove(callback)
            logger.info(f"已取消註冊警報回調: {callback.__name__}")
    
    def set_threshold(self, threshold_type: str, value: float):
        """
        設置警報閾值
        
        Args:
            threshold_type: 閾值類型
            value: 閾值
        """
        if threshold_type in self.thresholds:
            self.thresholds[threshold_type] = value
            logger.info(f"已設置 {threshold_type} 閾值為 {value}")
        else:
            logger.warning(f"未知的閾值類型: {threshold_type}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        獲取指標
        
        Returns:
            Dict[str, Any]: 指標數據
        """
        return self.metrics.copy()


# 創建全局監控器實例
stream_monitor = StreamMonitor()
