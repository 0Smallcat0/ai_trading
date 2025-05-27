"""WebSocket 客戶端模組

此模組提供與 WebSocket 服務器連接的功能，
支援自動重連和背壓控制。

主要功能：
- 建立 WebSocket 連接
- 自動重連機制
- 消息處理和回調
- 背壓控制
"""

import json
import logging
import queue
import random
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

import websocket

# 設定日誌
logger = logging.getLogger(__name__)


class BackpressureController:
    """背壓控制器，用於動態調節資料流量"""

    def __init__(
        self,
        max_queue_size: int = 1000,
        warning_threshold: float = 0.8,
        critical_threshold: float = 0.95,
        adjustment_factor: float = 0.1,
        min_interval: float = 0.001,
        max_interval: float = 1.0,
    ):
        """初始化背壓控制器

        Args:
            max_queue_size: 最大隊列大小
            warning_threshold: 警告閾值（隊列使用率）
            critical_threshold: 臨界閾值（隊列使用率）
            adjustment_factor: 調節因子
            min_interval: 最小處理間隔
            max_interval: 最大處理間隔
        """
        self.max_queue_size = max_queue_size
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.adjustment_factor = adjustment_factor
        self.min_interval = min_interval
        self.max_interval = max_interval

        # 當前處理間隔
        self.current_interval = min_interval

        # 統計信息
        self.stats = {
            "total_adjustments": 0,
            "backpressure_events": 0,
            "queue_size_history": deque(maxlen=100),
            "interval_history": deque(maxlen=100),
        }

        # 鎖
        self.lock = threading.RLock()

    def check_and_adjust(self, current_queue_size: int) -> float:
        """檢查隊列狀態並調節處理間隔

        Args:
            current_queue_size: 當前隊列大小

        Returns:
            float: 建議的處理間隔
        """
        with self.lock:
            # 計算隊列使用率
            usage_ratio = current_queue_size / self.max_queue_size

            # 記錄統計信息
            self.stats["queue_size_history"].append(current_queue_size)
            self.stats["interval_history"].append(self.current_interval)

            # 根據使用率調節間隔
            if usage_ratio >= self.critical_threshold:
                # 臨界狀態：大幅增加處理間隔
                adjustment = self.adjustment_factor * 2
                self.current_interval = min(
                    self.current_interval * (1 + adjustment), self.max_interval
                )
                self.stats["backpressure_events"] += 1
                logger.warning(
                    "背壓控制：隊列使用率 %.2f%%，調整處理間隔至 %.3fs",
                    usage_ratio * 100,
                    self.current_interval,
                )

            elif usage_ratio >= self.warning_threshold:
                # 警告狀態：適度增加處理間隔
                adjustment = self.adjustment_factor
                self.current_interval = min(
                    self.current_interval * (1 + adjustment), self.max_interval
                )
                logger.debug(
                    "背壓控制：隊列使用率 %.2f%%，調整處理間隔至 %.3fs",
                    usage_ratio * 100,
                    self.current_interval,
                )

            elif usage_ratio < self.warning_threshold * 0.5:
                # 低使用率：減少處理間隔
                adjustment = self.adjustment_factor * 0.5
                self.current_interval = max(
                    self.current_interval * (1 - adjustment), self.min_interval
                )
                logger.debug(
                    "背壓控制：隊列使用率 %.2f%%，調整處理間隔至 %.3fs",
                    usage_ratio * 100,
                    self.current_interval,
                )

            self.stats["total_adjustments"] += 1
            return self.current_interval

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息"""
        with self.lock:
            avg_queue_size = (
                sum(self.stats["queue_size_history"])
                / len(self.stats["queue_size_history"])
                if self.stats["queue_size_history"]
                else 0
            )

            avg_interval = (
                sum(self.stats["interval_history"])
                / len(self.stats["interval_history"])
                if self.stats["interval_history"]
                else 0
            )

            return {
                "current_interval": self.current_interval,
                "total_adjustments": self.stats["total_adjustments"],
                "backpressure_events": self.stats["backpressure_events"],
                "average_queue_size": avg_queue_size,
                "average_interval": avg_interval,
                "max_queue_size": self.max_queue_size,
                "warning_threshold": self.warning_threshold,
                "critical_threshold": self.critical_threshold,
            }


class WebSocketClient:
    """WebSocket 客戶端，支援自動重連和背壓控制"""

    def __init__(
        self,
        url: str,
        *,
        on_message: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_close: Optional[Callable[[], None]] = None,
        on_open: Optional[Callable[[], None]] = None,
        reconnect_interval: float = 5.0,
        max_reconnect_attempts: int = 10,
        backoff_factor: float = 1.5,
        jitter: float = 0.1,
        max_queue_size: int = 1000,
        process_interval: float = 0.1,
        headers: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
        enable_backpressure: bool = True,
        backpressure_config: Optional[Dict[str, Any]] = None,
    ):
        """初始化 WebSocket 客戶端

        Args:
            url: WebSocket 服務器 URL
            on_message: 收到消息時的回調函數
            on_error: 發生錯誤時的回調函數
            on_close: 連接關閉時的回調函數
            on_open: 連接建立時的回調函數
            reconnect_interval: 重連間隔（秒）
            max_reconnect_attempts: 最大重連嘗試次數
            backoff_factor: 重連退避因子
            jitter: 隨機抖動因子
            max_queue_size: 最大消息隊列大小
            process_interval: 處理消息間隔（秒）
            headers: HTTP 頭部
            proxy: 代理服務器
            enable_backpressure: 是否啟用背壓控制
            backpressure_config: 背壓控制配置
        """
        self.url = url
        self.on_message_callback = on_message
        self.on_error_callback = on_error
        self.on_close_callback = on_close
        self.on_open_callback = on_open
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.max_queue_size = max_queue_size
        self.process_interval = process_interval
        self.headers = headers
        self.proxy = proxy

        # WebSocket 連接
        self.ws = None
        self.ws_thread = None
        self.is_connected = False
        self.reconnect_count = 0
        self.last_reconnect_time = 0
        self.should_reconnect = True

        # 消息隊列和處理線程
        self.message_queue = queue.Queue(maxsize=max_queue_size)
        self.processing_thread = None
        self.is_processing = False
        self.lock = threading.RLock()

        # 背壓控制
        self.enable_backpressure = enable_backpressure
        if self.enable_backpressure:
            bp_config = backpressure_config or {}
            self.backpressure_controller = BackpressureController(
                max_queue_size=max_queue_size,
                warning_threshold=bp_config.get("warning_threshold", 0.8),
                critical_threshold=bp_config.get("critical_threshold", 0.95),
                adjustment_factor=bp_config.get("adjustment_factor", 0.1),
                min_interval=bp_config.get("min_interval", 0.001),
                max_interval=bp_config.get("max_interval", 1.0),
            )
        else:
            self.backpressure_controller = None

        # 統計信息
        self.stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "reconnect_attempts": 0,
            "errors": 0,
            "last_message_time": None,
            "queue_high_water_mark": 0,
            "backpressure_activations": 0,
        }

    def connect(self):
        """建立 WebSocket 連接"""
        if self.is_connected:
            logger.warning("WebSocket 已連接")
            return

        logger.info("正在連接 WebSocket: %s", self.url)

        # 設置 WebSocket 回調
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp(
            self.url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open,
            header=self.headers,
        )

        # 啟動 WebSocket 連接線程
        self.ws_thread = threading.Thread(target=self._run_websocket, daemon=True)
        self.ws_thread.start()

        # 啟動消息處理線程
        if not self.is_processing:
            self.is_processing = True
            self.processing_thread = threading.Thread(
                target=self._process_messages, daemon=True
            )
            self.processing_thread.start()

    def _run_websocket(self):
        """運行 WebSocket 連接"""
        try:
            self.ws.run_forever(
                ping_interval=30,
                ping_timeout=10,
                proxy_type=None if not self.proxy else self.proxy,
            )
        except Exception as e:
            logger.error("WebSocket 運行時發生錯誤: %s", e)
            self._handle_reconnect()

    def _on_message(self, _ws, message):
        """收到消息時的回調

        Args:
            _ws: WebSocket 連接（未使用）
            message: 收到的消息
        """
        try:
            # 更新統計信息
            self.stats["messages_received"] += 1
            self.stats["last_message_time"] = datetime.now()

            # 獲取當前隊列大小
            current_queue_size = self.message_queue.qsize()

            # 背壓控制檢查
            if self.enable_backpressure and self.backpressure_controller:
                # 檢查並調節處理間隔
                self.backpressure_controller.check_and_adjust(current_queue_size)

                # 如果隊列接近滿載，記錄背壓事件
                if current_queue_size >= self.max_queue_size * 0.9:
                    self.stats["backpressure_activations"] += 1
                    logger.warning(
                        "背壓控制啟動：隊列使用率 %.2f%%",
                        current_queue_size / self.max_queue_size * 100,
                    )

            # 將消息放入隊列
            self.message_queue.put(message, block=False)

            # 更新隊列高水位標記
            queue_size = self.message_queue.qsize()
            if queue_size > self.stats["queue_high_water_mark"]:
                self.stats["queue_high_water_mark"] = queue_size

        except queue.Full:
            logger.error("消息隊列已滿，丟棄消息")
            self.stats["backpressure_activations"] += 1
            # 可以在這裡實現更複雜的背壓策略，如通知服務器減慢發送速度
        except Exception as e:
            logger.error("處理 WebSocket 消息時發生錯誤: %s", e)
            self.stats["errors"] += 1
            if self.on_error_callback:
                self.on_error_callback(e)

    def _on_error(self, _ws, error):
        """發生錯誤時的回調

        Args:
            _ws: WebSocket 連接（未使用）
            error: 錯誤信息
        """
        logger.error("WebSocket 錯誤: %s", error)
        self.stats["errors"] += 1
        if self.on_error_callback:
            self.on_error_callback(error)

    def _on_close(self, _ws, close_status_code, close_msg):
        """連接關閉時的回調

        Args:
            _ws: WebSocket 連接（未使用）
            close_status_code: 關閉狀態碼
            close_msg: 關閉消息
        """
        logger.info("WebSocket 連接關閉: %s %s", close_status_code, close_msg)
        self.is_connected = False
        if self.on_close_callback:
            self.on_close_callback()

        # 嘗試重連
        if self.should_reconnect:
            self._handle_reconnect()

    def _on_open(self, _ws):
        """連接建立時的回調

        Args:
            _ws: WebSocket 連接（未使用）
        """
        logger.info("WebSocket 連接已建立")
        with self.lock:
            self.is_connected = True
            self.reconnect_count = 0

        if self.on_open_callback:
            self.on_open_callback()

    def _handle_reconnect(self):
        """處理重連邏輯"""
        if not self.should_reconnect:
            logger.info("不進行重連")
            return

        with self.lock:
            self.reconnect_count += 1
            self.stats["reconnect_attempts"] += 1

            if self.reconnect_count > self.max_reconnect_attempts:
                logger.error(
                    "已達最大重連嘗試次數 (%d)，停止重連", self.max_reconnect_attempts
                )
                self.should_reconnect = False
                return

            # 計算重連間隔（使用指數退避和隨機抖動）
            wait_time = self.reconnect_interval * (
                self.backoff_factor ** (self.reconnect_count - 1)
            )
            jitter_value = random.uniform(0, self.jitter * wait_time)
            wait_time += jitter_value

            logger.info(
                "將在 %.2f 秒後進行第 %d 次重連", wait_time, self.reconnect_count
            )
            self.last_reconnect_time = time.time()

        # 等待後重連
        time.sleep(wait_time)
        self.connect()

    def _process_messages(self):
        """處理消息隊列中的消息"""
        while self.is_processing:
            try:
                # 獲取動態處理間隔
                current_interval = self.process_interval
                if self.enable_backpressure and self.backpressure_controller:
                    current_interval = self.backpressure_controller.current_interval

                # 從隊列中獲取消息，設置超時以便定期檢查 is_processing 標誌
                try:
                    message = self.message_queue.get(timeout=current_interval)

                    # 處理消息
                    if self.on_message_callback:
                        self.on_message_callback(message)

                    # 更新統計信息
                    self.stats["messages_processed"] += 1

                    # 標記任務完成
                    self.message_queue.task_done()

                    # 如果啟用背壓控制，在處理完消息後稍作等待
                    if (
                        self.enable_backpressure
                        and current_interval > self.process_interval
                    ):
                        time.sleep(current_interval - self.process_interval)

                except queue.Empty:
                    # 隊列為空，繼續等待
                    continue

            except Exception as e:
                logger.error("處理消息時發生錯誤: %s", e)
                self.stats["errors"] += 1
                time.sleep(0.1)  # 避免在錯誤情況下過度消耗 CPU

    def send(self, message: Union[str, Dict, List]):
        """發送消息

        Args:
            message: 要發送的消息，可以是字符串或可序列化為 JSON 的對象

        Returns:
            bool: 是否成功發送
        """
        if not self.is_connected or not self.ws:
            logger.error("WebSocket 未連接，無法發送消息")
            return False

        try:
            # 如果消息是字典或列表，轉換為 JSON 字符串
            if isinstance(message, (dict, list)):
                message = json.dumps(message)

            self.ws.send(message)
            return True
        except Exception as e:
            logger.error("發送消息時發生錯誤: %s", e)
            self.stats["errors"] += 1
            return False

    def close(self):
        """關閉 WebSocket 連接"""
        logger.info("正在關閉 WebSocket 連接")
        self.should_reconnect = False
        self.is_processing = False

        if self.ws:
            self.ws.close()

        # 等待處理線程結束
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)

    def get_stats(self) -> Dict[str, Any]:
        """獲取統計信息

        Returns:
            Dict[str, Any]: 統計信息
        """
        stats = self.stats.copy()
        stats["is_connected"] = self.is_connected
        stats["reconnect_count"] = self.reconnect_count
        stats["queue_size"] = self.message_queue.qsize()

        # 添加背壓控制統計信息
        if self.enable_backpressure and self.backpressure_controller:
            stats["backpressure"] = self.backpressure_controller.get_stats()

        return stats

    def get_backpressure_stats(self) -> Optional[Dict[str, Any]]:
        """獲取背壓控制統計信息

        Returns:
            Optional[Dict[str, Any]]: 背壓控制統計信息，如果未啟用則返回 None
        """
        if self.enable_backpressure and self.backpressure_controller:
            return self.backpressure_controller.get_stats()
        return None
