"""
WebSocket 客戶端模組

此模組提供與 WebSocket 服務器連接的功能，
支援自動重連和背壓控制。

主要功能：
- 建立 WebSocket 連接
- 自動重連機制
- 消息處理和回調
- 背壓控制
"""

import json
import time
import logging
import threading
import queue
import random
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
import websocket
from datetime import datetime, timedelta

# 設定日誌
logger = logging.getLogger(__name__)


class WebSocketClient:
    """WebSocket 客戶端，支援自動重連和背壓控制"""

    def __init__(
        self,
        url: str,
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
    ):
        """
        初始化 WebSocket 客戶端

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
        self.is_connected = False
        self.reconnect_count = 0
        self.last_reconnect_time = 0
        self.should_reconnect = True

        # 消息隊列和處理線程
        self.message_queue = queue.Queue(maxsize=max_queue_size)
        self.processing_thread = None
        self.is_processing = False
        self.lock = threading.RLock()

        # 統計信息
        self.stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "reconnect_attempts": 0,
            "errors": 0,
            "last_message_time": None,
            "queue_high_water_mark": 0,
        }

    def connect(self):
        """建立 WebSocket 連接"""
        if self.is_connected:
            logger.warning("WebSocket 已連接")
            return

        logger.info(f"正在連接 WebSocket: {self.url}")

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
            logger.error(f"WebSocket 運行時發生錯誤: {e}")
            self._handle_reconnect()

    def _on_message(self, ws, message):
        """
        收到消息時的回調

        Args:
            ws: WebSocket 連接
            message: 收到的消息
        """
        try:
            # 更新統計信息
            self.stats["messages_received"] += 1
            self.stats["last_message_time"] = datetime.now()

            # 檢查隊列大小，實現背壓控制
            if self.message_queue.qsize() >= self.max_queue_size * 0.9:
                logger.warning(
                    f"消息隊列接近滿載 ({self.message_queue.qsize()}/{self.max_queue_size})，可能需要增加處理速度"
                )

            # 將消息放入隊列
            self.message_queue.put(message, block=False)

            # 更新隊列高水位標記
            queue_size = self.message_queue.qsize()
            if queue_size > self.stats["queue_high_water_mark"]:
                self.stats["queue_high_water_mark"] = queue_size

        except queue.Full:
            logger.error("消息隊列已滿，丟棄消息")
            # 可以在這裡實現更複雜的背壓策略，如通知服務器減慢發送速度
        except Exception as e:
            logger.error(f"處理 WebSocket 消息時發生錯誤: {e}")
            self.stats["errors"] += 1
            if self.on_error_callback:
                self.on_error_callback(e)

    def _on_error(self, ws, error):
        """
        發生錯誤時的回調

        Args:
            ws: WebSocket 連接
            error: 錯誤信息
        """
        logger.error(f"WebSocket 錯誤: {error}")
        self.stats["errors"] += 1
        if self.on_error_callback:
            self.on_error_callback(error)

    def _on_close(self, ws, close_status_code, close_msg):
        """
        連接關閉時的回調

        Args:
            ws: WebSocket 連接
            close_status_code: 關閉狀態碼
            close_msg: 關閉消息
        """
        logger.info(f"WebSocket 連接關閉: {close_status_code} {close_msg}")
        self.is_connected = False
        if self.on_close_callback:
            self.on_close_callback()

        # 嘗試重連
        if self.should_reconnect:
            self._handle_reconnect()

    def _on_open(self, ws):
        """
        連接建立時的回調

        Args:
            ws: WebSocket 連接
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
                    f"已達最大重連嘗試次數 ({self.max_reconnect_attempts})，停止重連"
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
                f"將在 {wait_time:.2f} 秒後進行第 {self.reconnect_count} 次重連"
            )
            self.last_reconnect_time = time.time()

        # 等待後重連
        time.sleep(wait_time)
        self.connect()

    def _process_messages(self):
        """處理消息隊列中的消息"""
        while self.is_processing:
            try:
                # 從隊列中獲取消息，設置超時以便定期檢查 is_processing 標誌
                try:
                    message = self.message_queue.get(timeout=self.process_interval)

                    # 處理消息
                    if self.on_message_callback:
                        self.on_message_callback(message)

                    # 更新統計信息
                    self.stats["messages_processed"] += 1

                    # 標記任務完成
                    self.message_queue.task_done()

                except queue.Empty:
                    # 隊列為空，繼續等待
                    continue

            except Exception as e:
                logger.error(f"處理消息時發生錯誤: {e}")
                self.stats["errors"] += 1
                time.sleep(0.1)  # 避免在錯誤情況下過度消耗 CPU

    def send(self, message: Union[str, Dict, List]):
        """
        發送消息

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
            logger.error(f"發送消息時發生錯誤: {e}")
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
        """
        獲取統計信息

        Returns:
            Dict[str, Any]: 統計信息
        """
        stats = self.stats.copy()
        stats["is_connected"] = self.is_connected
        stats["reconnect_count"] = self.reconnect_count
        stats["queue_size"] = self.message_queue.qsize()
        return stats
