"""
即時報價收集器模組

此模組提供收集即時報價資料的功能，包括：
- WebSocket 連接管理
- 即時報價資料處理
- 回壓控制機制
- 自動重連機制

支援從 Yahoo Finance、券商 API 等多個來源收集即時報價資料。
"""

import json
import logging
import os
import queue
import threading
import time
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import websocket
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import CACHE_DIR, DATA_DIR, DB_PATH
from src.data_sources.data_collector import DataCollector, RetryStrategy
from src.database.schema import MarketTick, MarketType, TimeGranularity

# 設定日誌
logger = logging.getLogger(__name__)


class RealtimeQuoteCollector(DataCollector):
    """
    即時報價收集器

    負責收集即時報價資料，支援 WebSocket 連接和自動重連機制。
    """

    def __init__(
        self,
        source: str = "yahoo",
        use_cache: bool = False,  # 即時資料通常不需要快取
        retry_strategy: Optional[RetryStrategy] = None,
        max_queue_size: int = 1000,
        batch_size: int = 100,
        save_interval: int = 5,  # 每 5 秒儲存一次資料
    ):
        """
        初始化即時報價收集器

        Args:
            source: 資料來源，預設為 'yahoo'
            use_cache: 是否使用快取
            retry_strategy: 重試策略
            max_queue_size: 最大佇列大小，用於回壓控制
            batch_size: 批次處理大小
            save_interval: 儲存間隔（秒）
        """
        super().__init__(
            name=f"RealtimeQuoteCollector_{source}",
            source=source,
            use_cache=use_cache,
            retry_strategy=retry_strategy,
        )

        self.max_queue_size = max_queue_size
        self.batch_size = batch_size
        self.save_interval = save_interval

        # 初始化資料佇列和處理執行緒
        self.data_queue = queue.Queue(maxsize=max_queue_size)
        self.processing_thread = None
        self.processing_running = False

        # 初始化 WebSocket 連接
        self.ws = None
        self.ws_thread = None
        self.ws_running = False
        self.subscribed_symbols = set()

        # 初始化資料庫連接
        self.engine = create_engine(f"sqlite:///{DB_PATH}")
        self.Session = sessionmaker(bind=self.engine)

        # 初始化最後儲存時間
        self.last_save_time = time.time()

        # 初始化資料緩衝區
        self.data_buffer = []

    def _on_message(self, ws, message):
        """
        WebSocket 訊息處理函數

        Args:
            ws: WebSocket 連接
            message: 收到的訊息
        """
        try:
            # 解析訊息
            data = json.loads(message)

            # 檢查佇列是否已滿（回壓控制）
            if self.data_queue.qsize() >= self.max_queue_size:
                logger.warning(f"資料佇列已滿 ({self.max_queue_size})，丟棄新資料")
                return

            # 將資料放入佇列
            self.data_queue.put(data)

        except json.JSONDecodeError:
            logger.error(f"解析 WebSocket 訊息失敗: {message}")
        except Exception as e:
            logger.error(f"處理 WebSocket 訊息時發生錯誤: {e}")

    def _on_error(self, ws, error):
        """
        WebSocket 錯誤處理函數

        Args:
            ws: WebSocket 連接
            error: 錯誤
        """
        logger.error(f"WebSocket 連接發生錯誤: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        """
        WebSocket 關閉處理函數

        Args:
            ws: WebSocket 連接
            close_status_code: 關閉狀態碼
            close_msg: 關閉訊息
        """
        logger.info(f"WebSocket 連接已關閉: {close_status_code} {close_msg}")

        # 如果不是主動關閉，則嘗試重新連接
        if self.ws_running:
            logger.info("嘗試重新連接 WebSocket...")
            time.sleep(5)  # 等待 5 秒後重新連接
            self._connect_websocket()

    def _on_open(self, ws):
        """
        WebSocket 開啟處理函數

        Args:
            ws: WebSocket 連接
        """
        logger.info("WebSocket 連接已開啟")

        # 重新訂閱所有股票
        for symbol in self.subscribed_symbols:
            self._subscribe_symbol(symbol)

    def _connect_websocket(self):
        """連接 WebSocket"""
        if self.source == "yahoo":
            # Yahoo Finance 的 WebSocket URL
            url = "wss://streamer.finance.yahoo.com"

            # 創建 WebSocket 連接
            self.ws = websocket.WebSocketApp(
                url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open,
            )

            # 在新執行緒中運行 WebSocket
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()

        else:
            raise ValueError(f"不支援的資料來源: {self.source}")

    def _subscribe_symbol(self, symbol: str):
        """
        訂閱股票即時報價

        Args:
            symbol: 股票代碼
        """
        if not self.ws:
            logger.warning("WebSocket 未連接，無法訂閱")
            return

        if self.source == "yahoo":
            # 格式化股票代碼
            if symbol.isdigit() and len(symbol) == 4:
                symbol = f"{symbol}.TW"

            # 建立訂閱訊息
            subscribe_msg = json.dumps({
                "subscribe": [symbol]
            })

            # 發送訂閱訊息
            self.ws.send(subscribe_msg)
            logger.info(f"已訂閱 {symbol} 的即時報價")

            # 添加到已訂閱列表
            self.subscribed_symbols.add(symbol)
        else:
            raise ValueError(f"不支援的資料來源: {self.source}")

    def _unsubscribe_symbol(self, symbol: str):
        """
        取消訂閱股票即時報價

        Args:
            symbol: 股票代碼
        """
        if not self.ws:
            logger.warning("WebSocket 未連接，無法取消訂閱")
            return

        if self.source == "yahoo":
            # 格式化股票代碼
            if symbol.isdigit() and len(symbol) == 4:
                symbol = f"{symbol}.TW"

            # 建立取消訂閱訊息
            unsubscribe_msg = json.dumps({
                "unsubscribe": [symbol]
            })

            # 發送取消訂閱訊息
            self.ws.send(unsubscribe_msg)
            logger.info(f"已取消訂閱 {symbol} 的即時報價")

            # 從已訂閱列表中移除
            self.subscribed_symbols.discard(symbol)
        else:
            raise ValueError(f"不支援的資料來源: {self.source}")

    def _process_data(self):
        """處理資料佇列中的資料"""
        while self.processing_running:
            try:
                # 批次處理資料
                batch = []
                for _ in range(min(self.batch_size, self.data_queue.qsize())):
                    if not self.data_queue.empty():
                        batch.append(self.data_queue.get())
                        self.data_queue.task_done()

                if batch:
                    # 處理批次資料
                    self._process_batch(batch)

                # 檢查是否需要儲存資料
                current_time = time.time()
                if current_time - self.last_save_time >= self.save_interval and self.data_buffer:
                    self._save_buffer_to_db()
                    self.last_save_time = current_time

                # 短暫休息，避免 CPU 使用率過高
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"處理資料時發生錯誤: {e}")

    def _process_batch(self, batch: List[Dict]):
        """
        處理批次資料

        Args:
            batch: 批次資料
        """
        for data in batch:
            try:
                # 根據資料來源處理資料
                if self.source == "yahoo":
                    # 解析 Yahoo Finance 的資料格式
                    if "data" in data and isinstance(data["data"], list):
                        for item in data["data"]:
                            if "symbol" in item and "price" in item:
                                tick_data = {
                                    "symbol": item["symbol"],
                                    "timestamp": datetime.now(),
                                    "price": item.get("price"),
                                    "volume": item.get("volume", 0),
                                    "bid_price": item.get("bid", None),
                                    "ask_price": item.get("ask", None),
                                    "market_type": MarketType.STOCK.value,
                                    "data_source": self.source,
                                }
                                self.data_buffer.append(tick_data)
            except Exception as e:
                logger.error(f"處理批次資料項目時發生錯誤: {e}")

    def _save_buffer_to_db(self):
        """將緩衝區中的資料儲存到資料庫"""
        if not self.data_buffer:
            return

        session = self.Session()
        try:
            for data in self.data_buffer:
                # 創建 MarketTick 記錄
                tick = MarketTick(
                    symbol=data["symbol"],
                    timestamp=data["timestamp"],
                    close=data["price"],  # 使用 price 作為 close
                    volume=data["volume"],
                    bid_price=data["bid_price"],
                    ask_price=data["ask_price"],
                    market_type=data["market_type"],
                    data_source=data["data_source"],
                )
                session.add(tick)

            session.commit()
            logger.info(f"已儲存 {len(self.data_buffer)} 筆即時報價資料到資料庫")

            # 清空緩衝區
            self.data_buffer = []

        except Exception as e:
            session.rollback()
            logger.error(f"儲存即時報價資料到資料庫時發生錯誤: {e}")
        finally:
            session.close()

    def start(self):
        """啟動即時報價收集器"""
        # 啟動 WebSocket 連接
        self.ws_running = True
        self._connect_websocket()

        # 啟動資料處理執行緒
        self.processing_running = True
        self.processing_thread = threading.Thread(target=self._process_data)
        self.processing_thread.daemon = True
        self.processing_thread.start()

        logger.info(f"{self.name} 已啟動")

    def stop(self):
        """停止即時報價收集器"""
        # 停止 WebSocket 連接
        self.ws_running = False
        if self.ws:
            self.ws.close()

        # 停止資料處理執行緒
        self.processing_running = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5)

        # 儲存剩餘的資料
        if self.data_buffer:
            self._save_buffer_to_db()

        logger.info(f"{self.name} 已停止")

    def collect(self, symbols: List[str]) -> bool:
        """
        收集即時報價資料

        Args:
            symbols: 股票代碼列表

        Returns:
            bool: 是否成功啟動收集
        """
        try:
            # 訂閱所有股票
            for symbol in symbols:
                self._subscribe_symbol(symbol)

            return True
        except Exception as e:
            logger.error(f"啟動即時報價收集時發生錯誤: {e}")
            return False
