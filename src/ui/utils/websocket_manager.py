"""
WebSocket 連接管理器

提供即時數據更新功能，包括股價、交易狀態的即時推送。
"""

import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import streamlit as st
import websockets
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """連接狀態枚舉"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class DataType(Enum):
    """數據類型枚舉"""

    STOCK_PRICE = "stock_price"
    TRADING_STATUS = "trading_status"
    PORTFOLIO_UPDATE = "portfolio_update"
    SYSTEM_STATUS = "system_status"
    ALERT = "alert"


class WebSocketManager:
    """WebSocket 連接管理器

    管理與後端服務的 WebSocket 連接，處理即時數據推送。
    """

    def __init__(self, server_url: str = "ws://localhost:8000/ws"):
        """初始化 WebSocket 管理器

        Args:
            server_url: WebSocket 服務器 URL
        """
        self.server_url = server_url
        self.websocket = None
        self.status = ConnectionStatus.DISCONNECTED
        self.subscribers: Dict[DataType, List[Callable]] = {
            data_type: [] for data_type in DataType
        }
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 5  # 秒
        self.last_heartbeat = None
        self.heartbeat_interval = 30  # 秒
        self._stop_event = threading.Event()
        self._connection_thread = None

        # 數據緩存
        self.data_cache: Dict[str, Any] = {}

    def start(self):
        """啟動 WebSocket 連接"""
        if self._connection_thread is None or not self._connection_thread.is_alive():
            self._stop_event.clear()
            self._connection_thread = threading.Thread(target=self._run_connection)
            self._connection_thread.daemon = True
            self._connection_thread.start()
            logger.info("WebSocket 連接線程已啟動")

    def stop(self):
        """停止 WebSocket 連接"""
        self._stop_event.set()
        if self._connection_thread and self._connection_thread.is_alive():
            self._connection_thread.join(timeout=5)
        self.status = ConnectionStatus.DISCONNECTED
        logger.info("WebSocket 連接已停止")

    def _run_connection(self):
        """運行 WebSocket 連接（在獨立線程中）"""
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()

        try:
            loop.run_until_complete(self._maintain_connection())
        except Exception as e:
            logger.error(f"WebSocket 連接線程錯誤: {e}")
        finally:
            loop.close()

    async def _maintain_connection(self):
        """維護 WebSocket 連接"""
        while not self._stop_event.is_set():
            try:
                await self._connect_and_listen()
            except Exception as e:
                logger.error(f"WebSocket 連接錯誤: {e}")
                self.status = ConnectionStatus.ERROR

                if self.reconnect_attempts < self.max_reconnect_attempts:
                    self.reconnect_attempts += 1
                    self.status = ConnectionStatus.RECONNECTING
                    logger.info(
                        f"嘗試重新連接 ({self.reconnect_attempts}/{self.max_reconnect_attempts})"
                    )
                    await asyncio.sleep(self.reconnect_delay)
                else:
                    logger.error("達到最大重連次數，停止連接")
                    break

    async def _connect_and_listen(self):
        """連接並監聽 WebSocket"""
        self.status = ConnectionStatus.CONNECTING

        try:
            # 模擬 WebSocket 連接（實際應用中應連接到真實服務器）
            self.status = ConnectionStatus.CONNECTED
            self.reconnect_attempts = 0
            self.last_heartbeat = datetime.now()

            logger.info(f"WebSocket 已連接到 {self.server_url}")

            # 模擬數據接收循環
            while not self._stop_event.is_set():
                # 模擬接收數據
                await self._simulate_data_reception()
                await asyncio.sleep(1)  # 每秒更新一次

                # 檢查心跳
                if self._should_send_heartbeat():
                    await self._send_heartbeat()

        except Exception as e:
            logger.error(f"WebSocket 監聽錯誤: {e}")
            self.status = ConnectionStatus.ERROR
            raise

    async def _simulate_data_reception(self):
        """模擬數據接收（實際應用中應從 WebSocket 接收）"""
        # 模擬股價數據
        stock_data = self._generate_mock_stock_data()
        await self._handle_message(
            {"type": DataType.STOCK_PRICE.value, "data": stock_data}
        )

        # 模擬交易狀態數據
        trading_status = self._generate_mock_trading_status()
        await self._handle_message(
            {"type": DataType.TRADING_STATUS.value, "data": trading_status}
        )

    def _generate_mock_stock_data(self) -> Dict[str, Any]:
        """生成模擬股價數據"""
        symbols = ["2330.TW", "2317.TW", "2454.TW", "AAPL", "MSFT"]
        data = {}

        for symbol in symbols:
            # 生成隨機價格變動
            base_price = self.data_cache.get(f"price_{symbol}", 100.0)
            change_percent = np.random.normal(0, 0.02)  # 2% 標準差
            new_price = base_price * (1 + change_percent)

            data[symbol] = {
                "price": round(new_price, 2),
                "change": round(new_price - base_price, 2),
                "change_percent": round(change_percent * 100, 2),
                "volume": np.random.randint(1000000, 10000000),
                "timestamp": datetime.now().isoformat(),
            }

            # 更新緩存
            self.data_cache[f"price_{symbol}"] = new_price

        return data

    def _generate_mock_trading_status(self) -> Dict[str, Any]:
        """生成模擬交易狀態數據"""
        return {
            "market_status": np.random.choice(
                ["open", "closed", "pre_market", "after_hours"]
            ),
            "active_orders": np.random.randint(0, 50),
            "executed_orders": np.random.randint(0, 20),
            "portfolio_value": round(np.random.uniform(900000, 1100000), 2),
            "daily_pnl": round(np.random.uniform(-10000, 10000), 2),
            "timestamp": datetime.now().isoformat(),
        }

    async def _handle_message(self, message: Dict[str, Any]):
        """處理接收到的消息"""
        try:
            data_type = DataType(message["type"])
            data = message["data"]

            # 更新數據緩存
            self.data_cache[data_type.value] = data

            # 通知訂閱者
            for callback in self.subscribers[data_type]:
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"回調函數執行錯誤: {e}")

        except Exception as e:
            logger.error(f"消息處理錯誤: {e}")

    def _should_send_heartbeat(self) -> bool:
        """檢查是否應該發送心跳"""
        if self.last_heartbeat is None:
            return True

        return (datetime.now() - self.last_heartbeat).seconds >= self.heartbeat_interval

    async def _send_heartbeat(self):
        """發送心跳"""
        try:
            # 實際應用中應發送心跳到服務器
            self.last_heartbeat = datetime.now()
            logger.debug("心跳已發送")
        except Exception as e:
            logger.error(f"心跳發送錯誤: {e}")

    def subscribe(
        self, data_type: DataType, callback: Callable[[Dict[str, Any]], None]
    ):
        """訂閱數據更新

        Args:
            data_type: 數據類型
            callback: 回調函數
        """
        if callback not in self.subscribers[data_type]:
            self.subscribers[data_type].append(callback)
            logger.info(f"已訂閱 {data_type.value} 數據更新")

    def unsubscribe(
        self, data_type: DataType, callback: Callable[[Dict[str, Any]], None]
    ):
        """取消訂閱數據更新

        Args:
            data_type: 數據類型
            callback: 回調函數
        """
        if callback in self.subscribers[data_type]:
            self.subscribers[data_type].remove(callback)
            logger.info(f"已取消訂閱 {data_type.value} 數據更新")

    def get_connection_status(self) -> Dict[str, Any]:
        """獲取連接狀態信息

        Returns:
            連接狀態信息
        """
        return {
            "status": self.status.value,
            "server_url": self.server_url,
            "reconnect_attempts": self.reconnect_attempts,
            "last_heartbeat": (
                self.last_heartbeat.isoformat() if self.last_heartbeat else None
            ),
            "subscribers_count": {
                data_type.value: len(callbacks)
                for data_type, callbacks in self.subscribers.items()
            },
        }

    def get_latest_data(self, data_type: DataType) -> Optional[Dict[str, Any]]:
        """獲取最新數據

        Args:
            data_type: 數據類型

        Returns:
            最新數據
        """
        return self.data_cache.get(data_type.value)


# 全域 WebSocket 管理器實例
websocket_manager = WebSocketManager()


def init_websocket_connection():
    """初始化 WebSocket 連接"""
    if "websocket_initialized" not in st.session_state:
        websocket_manager.start()
        st.session_state.websocket_initialized = True
        logger.info("WebSocket 連接已初始化")


def cleanup_websocket_connection():
    """清理 WebSocket 連接"""
    websocket_manager.stop()
    if "websocket_initialized" in st.session_state:
        del st.session_state.websocket_initialized
    logger.info("WebSocket 連接已清理")


def create_realtime_stock_widget(symbols: List[str]) -> None:
    """創建即時股價小工具

    Args:
        symbols: 股票代碼列表
    """
    st.subheader("📈 即時股價")

    # 初始化 WebSocket 連接
    init_websocket_connection()

    # 創建佔位符
    placeholder = st.empty()

    def update_stock_display(data: Dict[str, Any]):
        """更新股價顯示"""
        with placeholder.container():
            cols = st.columns(len(symbols))

            for i, symbol in enumerate(symbols):
                if symbol in data:
                    stock_info = data[symbol]

                    with cols[i]:
                        # 價格變動顏色
                        change = stock_info.get("change", 0)
                        color = "🟢" if change >= 0 else "🔴"

                        st.metric(
                            label=f"{color} {symbol}",
                            value=f"${stock_info.get('price', 0):.2f}",
                            delta=f"{stock_info.get('change_percent', 0):.2f}%",
                        )

    # 訂閱股價數據
    websocket_manager.subscribe(DataType.STOCK_PRICE, update_stock_display)

    # 顯示初始數據
    latest_data = websocket_manager.get_latest_data(DataType.STOCK_PRICE)
    if latest_data:
        update_stock_display(latest_data)


def create_connection_status_widget() -> None:
    """創建連接狀態小工具"""
    status_info = websocket_manager.get_connection_status()

    col1, col2, col3 = st.columns(3)

    with col1:
        status_color = {
            "connected": "🟢",
            "connecting": "🟡",
            "reconnecting": "🟡",
            "disconnected": "🔴",
            "error": "🔴",
        }

        st.metric(
            "連接狀態",
            f"{status_color.get(status_info['status'], '⚪')} {status_info['status'].title()}",
        )

    with col2:
        st.metric("重連次數", status_info["reconnect_attempts"])

    with col3:
        total_subscribers = sum(status_info["subscribers_count"].values())
        st.metric("訂閱數量", total_subscribers)
