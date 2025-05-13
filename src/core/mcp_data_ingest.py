"""
MCP 資料擷取模組

此模組負責從 MCP (Market Content Provider) 獲取市場新聞和資訊，
並進行必要的預處理和分析。

主要功能：
- 獲取市場新聞
- 分析市場情緒
- 獲取公司公告
- 獲取產業報告
"""

import os
import time
import logging
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
import threading
import queue
import json
import re

from src.data_sources.mcp_crawler import crawl_stock_news
from src.core.rate_limiter import RateLimiter
from src.core.websocket_client import WebSocketClient
from src.config import DATA_DIR, CACHE_DIR, LOGS_DIR

# 設定日誌
logger = logging.getLogger(__name__)
handler = logging.FileHandler(os.path.join(LOGS_DIR, "mcp_data_ingest.log"))
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# 建立快取目錄
MCP_CACHE_DIR = os.path.join(CACHE_DIR, "mcp")
os.makedirs(MCP_CACHE_DIR, exist_ok=True)

# 建立速率限制器 (每分鐘最多 30 次請求)
rate_limiter = RateLimiter(max_calls=30, period=60)


class MCPDataIngestor:
    """MCP 資料擷取器"""

    def __init__(
        self,
        use_cache: bool = True,
        cache_expiry_days: int = 1,
        max_workers: int = 5,
        rate_limit_max_calls: int = 30,
        rate_limit_period: int = 60,
    ):
        """
        初始化 MCP 資料擷取器

        Args:
            use_cache: 是否使用快取
            cache_expiry_days: 快取過期天數
            max_workers: 最大工作執行緒數
            rate_limit_max_calls: 速率限制最大請求數
            rate_limit_period: 速率限制時間段（秒）
        """
        self.use_cache = use_cache
        self.cache_expiry_days = cache_expiry_days
        self.max_workers = max_workers

        # 初始化速率限制器
        self.rate_limiter = RateLimiter(
            max_calls=rate_limit_max_calls,
            period=rate_limit_period,
            retry_count=3,
            retry_backoff=2.0,
            jitter=0.1,
        )

        # 初始化 WebSocket 客戶端
        self.websocket_client = None

        # 初始化資料處理隊列和背壓控制
        self.data_queue = queue.Queue(maxsize=1000)
        self.is_processing = False
        self.processing_thread = None

        # 統計信息
        self.stats = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "data_points_total": 0,
        }

        logger.info("MCP 資料擷取器初始化完成")

    def fetch_market_news(
        self,
        query: str,
        days: int = 7,
        fulltext: bool = False,
        use_cache: Optional[bool] = None,
    ) -> pd.DataFrame:
        """
        獲取市場新聞

        Args:
            query: 查詢關鍵字
            days: 往前查詢的天數
            fulltext: 是否獲取全文
            use_cache: 是否使用快取，如果為 None 則使用類別設定

        Returns:
            pd.DataFrame: 新聞資料框
        """
        # 使用速率限制器
        with self.rate_limiter:
            # 更新統計信息
            self.stats["requests_total"] += 1

            # 檢查是否使用快取
            use_cache = self.use_cache if use_cache is None else use_cache
            cache_path = self._get_cache_path(
                "news", {"query": query, "days": days, "fulltext": fulltext}
            )

            if use_cache and self._is_cache_valid(cache_path):
                logger.info(f"從快取讀取新聞資料: {query}")
                df = pd.read_csv(cache_path, index_col=0)

                # 更新統計信息
                self.stats["requests_success"] += 1
                self.stats["data_points_total"] += len(df)

                return df

            try:
                logger.info(f"從 MCP 獲取新聞資料: {query}")
                news = crawl_stock_news(query, days=days, fulltext=fulltext)
                df = pd.DataFrame(news)

                # 儲存到快取
                if use_cache and not df.empty:
                    df.to_csv(cache_path)

                # 更新統計信息
                self.stats["requests_success"] += 1
                self.stats["data_points_total"] += len(df)

                return df

            except Exception as e:
                logger.error(f"獲取新聞資料時發生錯誤: {e}")
                self.stats["requests_failed"] += 1
                return pd.DataFrame()

    def _get_cache_path(self, data_type: str, params: Dict[str, Any] = None) -> str:
        """
        獲取快取檔案路徑

        Args:
            data_type: 資料類型
            params: 參數字典

        Returns:
            str: 快取檔案路徑
        """
        if params:
            param_str = "_".join(f"{k}_{v}" for k, v in params.items())
            return os.path.join(MCP_CACHE_DIR, f"{data_type}_{param_str}.csv")
        else:
            return os.path.join(MCP_CACHE_DIR, f"{data_type}.csv")

    def _is_cache_valid(self, cache_path: str) -> bool:
        """
        檢查快取是否有效

        Args:
            cache_path: 快取檔案路徑

        Returns:
            bool: 快取是否有效
        """
        if not os.path.exists(cache_path):
            return False

        # 檢查檔案修改時間
        file_time = os.path.getmtime(cache_path)
        file_date = datetime.fromtimestamp(file_time)
        now = datetime.now()
        return (now - file_date).days < self.cache_expiry_days

    def connect_websocket(
        self,
        on_message: Callable[[str], None],
        symbols: Optional[List[str]] = None,
    ) -> bool:
        """
        連接 WebSocket 獲取即時新聞

        Args:
            on_message: 收到消息時的回調函數
            symbols: 股票代碼列表，如果為 None 則訂閱所有新聞

        Returns:
            bool: 是否成功連接
        """
        try:
            # WebSocket URL
            url = "wss://mcp.example.com/ws"

            # 定義回調函數
            def on_message_with_backpressure(message):
                """添加背壓控制的消息回調"""
                try:
                    # 檢查隊列大小，實現背壓控制
                    if self.data_queue.qsize() >= self.data_queue.maxsize * 0.9:
                        logger.warning(
                            f"消息隊列接近滿載 ({self.data_queue.qsize()}/{self.data_queue.maxsize})，可能需要增加處理速度"
                        )

                    # 將消息放入隊列
                    self.data_queue.put((message, on_message), block=False)

                except queue.Full:
                    logger.error("消息隊列已滿，丟棄消息")

            def on_error(error):
                """錯誤回調"""
                logger.error(f"WebSocket 錯誤: {error}")

            def on_open():
                """連接建立回調"""
                logger.info(f"WebSocket 連接已建立，訂閱新聞")
                # 訂閱新聞
                if symbols:
                    self.websocket_client.send(
                        {"action": "subscribe", "symbols": symbols}
                    )
                else:
                    self.websocket_client.send({"action": "subscribe", "type": "news"})

            # 創建 WebSocket 客戶端
            self.websocket_client = WebSocketClient(
                url=url,
                on_message=on_message_with_backpressure,
                on_error=on_error,
                on_open=on_open,
                reconnect_interval=5.0,
                max_reconnect_attempts=10,
                backoff_factor=1.5,
                jitter=0.1,
                max_queue_size=1000,
            )

            # 啟動處理線程
            if not self.is_processing:
                self.is_processing = True
                self.processing_thread = threading.Thread(
                    target=self._process_messages, daemon=True
                )
                self.processing_thread.start()

            # 連接 WebSocket
            self.websocket_client.connect()

            return True

        except Exception as e:
            logger.error(f"連接 WebSocket 時發生錯誤: {e}")
            return False

    def disconnect_websocket(self) -> bool:
        """
        斷開 WebSocket 連接

        Returns:
            bool: 是否成功斷開
        """
        if not self.websocket_client:
            logger.warning("WebSocket 客戶端不存在")
            return False

        try:
            # 關閉 WebSocket 客戶端
            self.websocket_client.close()
            self.websocket_client = None

            return True

        except Exception as e:
            logger.error(f"斷開 WebSocket 連接時發生錯誤: {e}")
            return False

    def _process_messages(self):
        """處理消息隊列中的消息"""
        while self.is_processing:
            try:
                # 從隊列中獲取消息，設置超時以便定期檢查 is_processing 標誌
                try:
                    message, callback = self.data_queue.get(timeout=0.1)

                    # 處理消息
                    callback(message)

                    # 標記任務完成
                    self.data_queue.task_done()

                except queue.Empty:
                    # 隊列為空，繼續等待
                    continue

            except Exception as e:
                logger.error(f"處理消息時發生錯誤: {e}")
                time.sleep(0.1)  # 避免在錯誤情況下過度消耗 CPU

    def get_stats(self) -> Dict[str, Any]:
        """
        獲取統計信息

        Returns:
            Dict[str, Any]: 統計信息
        """
        stats = self.stats.copy()
        stats["queue_size"] = (
            self.data_queue.qsize() if hasattr(self, "data_queue") else 0
        )
        stats["is_websocket_connected"] = (
            self.websocket_client is not None and self.websocket_client.is_connected
            if self.websocket_client
            else False
        )
        return stats

    def close(self):
        """關閉 MCP 資料擷取器"""
        logger.info("正在關閉 MCP 資料擷取器")

        # 關閉 WebSocket 客戶端
        if self.websocket_client:
            try:
                self.websocket_client.close()
            except Exception as e:
                logger.error(f"關閉 WebSocket 客戶端時發生錯誤: {e}")

        # 停止處理線程
        self.is_processing = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)

        logger.info("MCP 資料擷取器已關閉")


def analyze_market_sentiment(news_df):
    """
    分析市場情緒

    Args:
        news_df (pandas.DataFrame): 新聞資料框

    Returns:
        dict: 情緒分析結果，包含以下欄位：
            - sentiment (str): 情緒，'positive', 'negative', 或 'neutral'
            - score (float): 情緒分數，範圍為 [-1, 1]
            - count (int): 新聞數量
            - positive_count (int): 正面新聞數量
            - negative_count (int): 負面新聞數量
    """
    if news_df.empty:
        return {
            "sentiment": "neutral",
            "score": 0,
            "count": 0,
            "positive_count": 0,
            "negative_count": 0,
        }

    # 檢查是否有情緒欄位
    if "sentiment" not in news_df.columns:
        # 如果沒有情緒欄位，嘗試使用標題和內容進行簡單的情緒分析
        positive_words = [
            "漲",
            "上升",
            "增長",
            "獲利",
            "成長",
            "突破",
            "利多",
            "看好",
            "樂觀",
        ]
        negative_words = [
            "跌",
            "下降",
            "虧損",
            "衰退",
            "破產",
            "危機",
            "利空",
            "看壞",
            "悲觀",
        ]

        # 計算正面和負面詞彙出現的次數
        pos = 0
        neg = 0

        # 檢查標題
        if "title" in news_df.columns:
            for word in positive_words:
                pos += news_df["title"].str.count(word).sum()
            for word in negative_words:
                neg += news_df["title"].str.count(word).sum()

        # 檢查內容
        if "content" in news_df.columns:
            for word in positive_words:
                pos += news_df["content"].str.count(word).sum()
            for word in negative_words:
                neg += news_df["content"].str.count(word).sum()
    else:
        # 如果有情緒欄位，直接使用
        pos = news_df["sentiment"].str.count("positive").sum()
        neg = news_df["sentiment"].str.count("negative").sum()

    total = pos + neg
    score = (pos - neg) / (total if total else 1)  # 避免除以零

    # 根據分數判斷情緒
    sentiment = "positive" if score > 0.2 else "negative" if score < -0.2 else "neutral"

    return {
        "sentiment": sentiment,
        "score": score,
        "count": len(news_df),
        "positive_count": pos,
        "negative_count": neg,
    }
