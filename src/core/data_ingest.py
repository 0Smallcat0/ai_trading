"""
資料蒐集與預處理模組

此模組負責從各種來源獲取股票資料，包括價格、成交量、財務報表等，
並進行必要的預處理，為後續的特徵計算和策略研究提供基礎資料。

主要功能：
- 從多種來源獲取股票資料（Yahoo Finance、Alpha Vantage、FinMind、券商 API）
- 支援多種資料類型（價格、成交量、財務報表、技術指標）
- 實現 WebSocket 自動重連和背壓控制
- 提供請求速率限制和自動故障轉移機制
- 資料標準化和清洗
"""

import datetime
import logging
import os
import queue
import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Union

import pandas as pd
from tqdm import tqdm

# 配置模組
from src.config import CACHE_DIR, DATA_DIR, LOGS_DIR

# 工具模組
from src.core.rate_limiter import AdaptiveRateLimiter
from src.core.websocket_client import WebSocketClient
from src.data_sources.broker_adapter import SimulatedBrokerAdapter

# 資料來源適配器
from src.data_sources.twse_crawler import twse_crawler
from src.data_sources.yahoo_adapter import YahooFinanceAdapter

# 資料庫模組


# 設定日誌
logger = logging.getLogger(__name__)
handler = logging.FileHandler(os.path.join(LOGS_DIR, "data_ingest.log"))
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# 設定資料存放路徑
HISTORY_DIR = os.path.join(DATA_DIR, "history")
ITEMS_DIR = os.path.join(HISTORY_DIR, "items")
TABLES_DIR = os.path.join(HISTORY_DIR, "tables")
FINANCIAL_STATEMENT_DIR = os.path.join(HISTORY_DIR, "financial_statement")
DB_PATH = os.path.join(DATA_DIR, "market_data.db")

# 確保目錄存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(ITEMS_DIR, exist_ok=True)
os.makedirs(TABLES_DIR, exist_ok=True)
os.makedirs(FINANCIAL_STATEMENT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# API 金鑰
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
FINMIND_API_KEY = os.getenv("FINMIND_API_KEY", "")
BROKER_API_KEY = os.getenv("BROKER_API_KEY", "")
BROKER_API_SECRET = os.getenv("BROKER_API_SECRET", "")

# 記錄日期範圍的檔案
date_range_record_file = os.path.join(HISTORY_DIR, "date_range.pickle")


class DataIngestionManager:
    """
    資料擷取管理器

    負責協調不同資料來源的資料擷取，並提供統一的介面。
    支援多種資料來源、自動重連、背壓控制和故障轉移。
    """

    def __init__(
        self,
        use_cache: bool = True,
        cache_expiry_days: int = 1,
        max_workers: int = 5,
        rate_limit_max_calls: int = 60,
        rate_limit_period: int = 60,
    ):
        """
        初始化資料擷取管理器

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

        # 初始化資料來源適配器
        self.adapters = {}
        self.init_adapters()

        # 初始化速率限制器
        self.rate_limiter = AdaptiveRateLimiter(
            max_calls=rate_limit_max_calls,
            period=rate_limit_period,
            retry_count=3,
            retry_backoff=2.0,
            jitter=0.1,
        )

        # 初始化 WebSocket 客戶端
        self.websocket_clients = {}

        # 初始化資料處理隊列和背壓控制
        self.data_queue = queue.Queue(maxsize=1000)
        self.is_processing = False
        self.processing_thread = None

        # 初始化故障轉移機制
        self.source_priorities = {
            "price": ["yahoo", "finmind", "alpha_vantage", "broker"],
            "fundamental": ["finmind", "yahoo", "alpha_vantage"],
            "news": ["mcp", "finmind", "yahoo"],
        }
        self.source_status = {
            "yahoo": True,
            "finmind": True,
            "alpha_vantage": True,
            "broker": True,
            "mcp": True,
        }

        # 統計信息
        self.stats = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "data_points_total": 0,
            "source_usage": {
                "yahoo": 0,
                "finmind": 0,
                "alpha_vantage": 0,
                "broker": 0,
                "mcp": 0,
            },
        }

        logger.info("資料擷取管理器初始化完成")

    def init_adapters(self):
        """初始化所有資料來源適配器"""
        # Yahoo Finance 適配器
        self.adapters["yahoo"] = YahooFinanceAdapter(
            use_cache=self.use_cache,
            cache_expiry_days=self.cache_expiry_days,
        )

        # 模擬券商適配器
        self.adapters["broker"] = SimulatedBrokerAdapter(
            api_key=BROKER_API_KEY,
            api_secret=BROKER_API_SECRET,
            use_cache=self.use_cache,
            cache_expiry_days=self.cache_expiry_days,
        )

        logger.info("資料來源適配器初始化完成")

    def get_historical_data(
        self,
        symbols: Union[str, List[str]],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1d",
        source: Optional[str] = None,
        use_cache: Optional[bool] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        獲取歷史價格資料

        Args:
            symbols: 股票代碼或代碼列表
            start_date: 開始日期，格式為 'YYYY-MM-DD'
            end_date: 結束日期，格式為 'YYYY-MM-DD'
            interval: 時間間隔，如 '1d', '1h', '5m' 等
            source: 資料來源，如果為 None 則自動選擇
            use_cache: 是否使用快取，如果為 None 則使用類別設定

        Returns:
            Dict[str, pd.DataFrame]: 股票代碼到歷史價格資料的映射
        """
        # 使用速率限制器
        with self.rate_limiter:
            # 更新統計信息
            self.stats["requests_total"] += 1

            # 轉換單一股票代碼為列表
            if isinstance(symbols, str):
                symbols = [symbols]

            # 如果未指定資料來源，使用故障轉移機制
            if source is None:
                source = self._get_best_source("price")

            # 檢查資料來源是否可用
            if not self.source_status.get(source, False):
                logger.warning(f"資料來源 {source} 不可用，嘗試使用備用來源")
                source = self._get_best_source("price")

            try:
                # 獲取適配器
                adapter = self.adapters.get(source)
                if not adapter:
                    logger.error(f"找不到資料來源 {source} 的適配器")
                    self.stats["requests_failed"] += 1
                    return {}

                # 獲取資料
                if len(symbols) == 1:
                    # 單一股票
                    df = adapter.get_historical_data(
                        symbols[0], start_date, end_date, interval, use_cache
                    )
                    result = {symbols[0]: df} if not df.empty else {}
                else:
                    # 多個股票
                    if hasattr(adapter, "get_multiple_historical_data"):
                        result = adapter.get_multiple_historical_data(
                            symbols,
                            start_date,
                            end_date,
                            interval,
                            use_cache,
                            self.max_workers,
                        )
                    else:
                        # 使用執行緒池並行獲取資料
                        result = {}
                        with ThreadPoolExecutor(
                            max_workers=self.max_workers
                        ) as executor:
                            future_to_symbol = {
                                executor.submit(
                                    adapter.get_historical_data,
                                    symbol,
                                    start_date,
                                    end_date,
                                    interval,
                                    use_cache,
                                ): symbol
                                for symbol in symbols
                            }

                            for future in as_completed(future_to_symbol):
                                symbol = future_to_symbol[future]
                                try:
                                    data = future.result()
                                    if not data.empty:
                                        result[symbol] = data
                                except Exception as e:
                                    logger.error(
                                        f"獲取 {symbol} 的歷史資料時發生錯誤: {e}"
                                    )

                # 更新統計信息
                self.stats["requests_success"] += 1
                self.stats["source_usage"][source] += 1
                self.stats["data_points_total"] += sum(
                    len(df) for df in result.values()
                )

                # 報告成功
                self.rate_limiter.report_success()

                return result

            except Exception as e:
                logger.error(f"獲取歷史價格資料時發生錯誤: {e}")
                self.stats["requests_failed"] += 1

                # 報告失敗
                self.rate_limiter.report_failure()

                # 標記資料來源為不可用
                self.source_status[source] = False

                # 嘗試使用備用來源
                if source != self._get_best_source("price"):
                    logger.info(f"嘗試使用備用來源獲取資料")
                    return self.get_historical_data(
                        symbols, start_date, end_date, interval, None, use_cache
                    )

                return {}

    def get_quote(
        self, symbols: Union[str, List[str]], source: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        獲取即時報價

        Args:
            symbols: 股票代碼或代碼列表
            source: 資料來源，如果為 None 則自動選擇

        Returns:
            Dict[str, Dict[str, Any]]: 股票代碼到即時報價的映射
        """
        # 使用速率限制器
        with self.rate_limiter:
            # 更新統計信息
            self.stats["requests_total"] += 1

            # 轉換單一股票代碼為列表
            if isinstance(symbols, str):
                symbols = [symbols]

            # 如果未指定資料來源，使用故障轉移機制
            if source is None:
                source = self._get_best_source("price")

            # 檢查資料來源是否可用
            if not self.source_status.get(source, False):
                logger.warning(f"資料來源 {source} 不可用，嘗試使用備用來源")
                source = self._get_best_source("price")

            try:
                # 獲取適配器
                adapter = self.adapters.get(source)
                if not adapter:
                    logger.error(f"找不到資料來源 {source} 的適配器")
                    self.stats["requests_failed"] += 1
                    return {}

                # 獲取資料
                result = {}
                for symbol in symbols:
                    try:
                        quote = adapter.get_quote(symbol)
                        if quote:
                            result[symbol] = quote
                    except Exception as e:
                        logger.error(f"獲取 {symbol} 的即時報價時發生錯誤: {e}")

                # 更新統計信息
                self.stats["requests_success"] += 1
                self.stats["source_usage"][source] += 1
                self.stats["data_points_total"] += len(result)

                # 報告成功
                self.rate_limiter.report_success()

                return result

            except Exception as e:
                logger.error(f"獲取即時報價時發生錯誤: {e}")
                self.stats["requests_failed"] += 1

                # 報告失敗
                self.rate_limiter.report_failure()

                # 標記資料來源為不可用
                self.source_status[source] = False

                # 嘗試使用備用來源
                if source != self._get_best_source("price"):
                    logger.info(f"嘗試使用備用來源獲取資料")
                    return self.get_quote(symbols, None)

                return {}

    def connect_websocket(
        self,
        symbols: Union[str, List[str]],
        on_message: Callable[[str], None],
        source: str = "broker",
    ) -> bool:
        """
        連接 WebSocket 獲取即時資料

        Args:
            symbols: 股票代碼或代碼列表
            on_message: 收到消息時的回調函數
            source: 資料來源

        Returns:
            bool: 是否成功連接
        """
        # 轉換單一股票代碼為列表
        if isinstance(symbols, str):
            symbols = [symbols]

        # 檢查資料來源是否可用
        if not self.source_status.get(source, False):
            logger.warning(f"資料來源 {source} 不可用，嘗試使用備用來源")
            source = self._get_best_source("price")

        try:
            # 根據資料來源選擇 WebSocket URL
            if source == "broker":
                url = "wss://api.broker.com/ws"
            else:
                logger.error(f"資料來源 {source} 不支援 WebSocket")
                return False

            # 創建 WebSocket 客戶端
            client_id = f"{source}_{'-'.join(symbols)}"

            # 檢查是否已存在相同的客戶端
            if client_id in self.websocket_clients:
                logger.info(f"WebSocket 客戶端 {client_id} 已存在，關閉舊連接")
                self.websocket_clients[client_id].close()

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
                self.source_status[source] = False

            def on_open():
                """連接建立回調"""
                logger.info(f"WebSocket 連接已建立，訂閱 {symbols}")
                # 訂閱股票
                client = self.websocket_clients[client_id]
                client.send({"action": "subscribe", "symbols": symbols})

            # 創建 WebSocket 客戶端
            client = WebSocketClient(
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

            # 儲存客戶端
            self.websocket_clients[client_id] = client

            # 啟動處理線程
            if not self.is_processing:
                self.is_processing = True
                self.processing_thread = threading.Thread(
                    target=self._process_messages, daemon=True
                )
                self.processing_thread.start()

            # 連接 WebSocket
            client.connect()

            return True

        except Exception as e:
            logger.error(f"連接 WebSocket 時發生錯誤: {e}")
            self.source_status[source] = False
            return False

    def disconnect_websocket(
        self, symbols: Union[str, List[str]], source: str = "broker"
    ) -> bool:
        """
        斷開 WebSocket 連接

        Args:
            symbols: 股票代碼或代碼列表
            source: 資料來源

        Returns:
            bool: 是否成功斷開
        """
        # 轉換單一股票代碼為列表
        if isinstance(symbols, str):
            symbols = [symbols]

        # 生成客戶端 ID
        client_id = f"{source}_{'-'.join(symbols)}"

        # 檢查客戶端是否存在
        if client_id not in self.websocket_clients:
            logger.warning(f"WebSocket 客戶端 {client_id} 不存在")
            return False

        try:
            # 關閉 WebSocket 客戶端
            client = self.websocket_clients[client_id]
            client.close()

            # 移除客戶端
            del self.websocket_clients[client_id]

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

    def _get_best_source(self, data_type: str) -> str:
        """
        獲取最佳資料來源

        根據優先級和可用性選擇最佳資料來源。

        Args:
            data_type: 資料類型，如 'price', 'fundamental', 'news'

        Returns:
            str: 最佳資料來源
        """
        # 獲取資料類型的優先級列表
        priorities = self.source_priorities.get(data_type, [])

        # 按優先級檢查資料來源是否可用
        for source in priorities:
            if self.source_status.get(source, False) and source in self.adapters:
                return source

        # 如果沒有可用的資料來源，返回第一個
        if priorities:
            logger.warning(f"沒有可用的資料來源，使用 {priorities[0]}")
            return priorities[0]

        # 如果沒有優先級列表，返回 'yahoo'
        return "yahoo"

    def get_stats(self) -> Dict[str, Any]:
        """
        獲取統計信息

        Returns:
            Dict[str, Any]: 統計信息
        """
        stats = self.stats.copy()
        stats["queue_size"] = self.data_queue.qsize()
        stats["websocket_clients"] = len(self.websocket_clients)
        stats["source_status"] = self.source_status.copy()
        return stats

    def reset_source_status(self, source: Optional[str] = None):
        """
        重置資料來源狀態

        Args:
            source: 資料來源，如果為 None 則重置所有資料來源
        """
        if source is None:
            # 重置所有資料來源
            for src in self.source_status:
                self.source_status[src] = True
        else:
            # 重置指定資料來源
            self.source_status[source] = True

        logger.info(f"已重置資料來源狀態: {self.source_status}")

    def close(self):
        """關閉資料擷取管理器"""
        logger.info("正在關閉資料擷取管理器")

        # 關閉所有 WebSocket 客戶端
        for client_id, client in list(self.websocket_clients.items()):
            try:
                client.close()
            except Exception as e:
                logger.error(f"關閉 WebSocket 客戶端 {client_id} 時發生錯誤: {e}")

        # 停止處理線程
        self.is_processing = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5.0)

        logger.info("資料擷取管理器已關閉")


def import_or_install(package):
    """
    檢查並安裝必要的套件

    Args:
        package (str): 套件名稱
    """
    try:
        __import__(package)
    except ImportError:
        print(f"Please install {package} (pip install {package})")


# 確保 lxml 已安裝
import_or_install("lxml")


def load_data(start_date=None, end_date=None, data_types=None):
    """
    載入指定日期範圍和類型的資料

    Args:
        start_date (datetime.date, optional): 開始日期，如果為 None 則使用最早的資料
        end_date (datetime.date, optional): 結束日期，如果為 None 則使用最新的資料
        data_types (list, optional): 資料類型列表，如果為 None 則載入所有類型

    Returns:
        dict: 包含各種資料的字典
    """
    if start_date is None:
        start_date = datetime.date(2010, 1, 1)
    if end_date is None:
        end_date = datetime.date.today()
    if data_types is None:
        data_types = ["price", "bargin", "pe", "monthly_report", "benchmark"]

    result = {}

    if "price" in data_types:
        price_file = os.path.join(TABLES_DIR, "price.pkl")
        if os.path.exists(price_file):
            result["price"] = pd.read_pickle(price_file)
            df = result["price"]
            if isinstance(df.index, pd.MultiIndex) and "date" in df.index.names:
                mask = (
                    df.index.get_level_values("date") >= pd.to_datetime(start_date)
                ) & (df.index.get_level_values("date") <= pd.to_datetime(end_date))
                result["price"] = df[mask]
            elif isinstance(df.index, pd.DatetimeIndex):
                result["price"] = df[
                    (df.index >= pd.to_datetime(start_date))
                    & (df.index <= pd.to_datetime(end_date))
                ]
            else:
                result["price"] = df

    if "bargin" in data_types:
        bargin_file = os.path.join(TABLES_DIR, "bargin_report.pkl")
        if os.path.exists(bargin_file):
            result["bargin"] = pd.read_pickle(bargin_file)
            df = result["bargin"]
            if isinstance(df.index, pd.MultiIndex) and "date" in df.index.names:
                mask = (
                    df.index.get_level_values("date") >= pd.to_datetime(start_date)
                ) & (df.index.get_level_values("date") <= pd.to_datetime(end_date))
                result["bargin"] = df[mask]
            elif isinstance(df.index, pd.DatetimeIndex):
                result["bargin"] = df[
                    (df.index >= pd.to_datetime(start_date))
                    & (df.index <= pd.to_datetime(end_date))
                ]
            else:
                result["bargin"] = df

    if "pe" in data_types:
        pe_file = os.path.join(TABLES_DIR, "pe.pkl")
        if os.path.exists(pe_file):
            result["pe"] = pd.read_pickle(pe_file)
            df = result["pe"]
            if isinstance(df.index, pd.MultiIndex) and "date" in df.index.names:
                mask = (
                    df.index.get_level_values("date") >= pd.to_datetime(start_date)
                ) & (df.index.get_level_values("date") <= pd.to_datetime(end_date))
                result["pe"] = df[mask]
            elif isinstance(df.index, pd.DatetimeIndex):
                result["pe"] = df[
                    (df.index >= pd.to_datetime(start_date))
                    & (df.index <= pd.to_datetime(end_date))
                ]
            else:
                result["pe"] = df

    if "monthly_report" in data_types:
        monthly_report_file = os.path.join(TABLES_DIR, "monthly_report.pkl")
        if os.path.exists(monthly_report_file):
            result["monthly_report"] = pd.read_pickle(monthly_report_file)
            df = result["monthly_report"]
            if isinstance(df.index, pd.MultiIndex) and "date" in df.index.names:
                mask = (
                    df.index.get_level_values("date") >= pd.to_datetime(start_date)
                ) & (df.index.get_level_values("date") <= pd.to_datetime(end_date))
                result["monthly_report"] = df[mask]
            elif isinstance(df.index, pd.DatetimeIndex):
                result["monthly_report"] = df[
                    (df.index >= pd.to_datetime(start_date))
                    & (df.index <= pd.to_datetime(end_date))
                ]
            else:
                result["monthly_report"] = df

    if "benchmark" in data_types:
        benchmark_file = os.path.join(TABLES_DIR, "benchmark.pkl")
        if os.path.exists(benchmark_file):
            result["benchmark"] = pd.read_pickle(benchmark_file)
            df = result["benchmark"]
            if isinstance(df.index, pd.MultiIndex) and "date" in df.index.names:
                mask = (
                    df.index.get_level_values("date") >= pd.to_datetime(start_date)
                ) & (df.index.get_level_values("date") <= pd.to_datetime(end_date))
                result["benchmark"] = df[mask]
            elif isinstance(df.index, pd.DatetimeIndex):
                result["benchmark"] = df[
                    (df.index >= pd.to_datetime(start_date))
                    & (df.index <= pd.to_datetime(end_date))
                ]
            else:
                result["benchmark"] = df

    return result


def update_data(start_date=None, end_date=None, data_types=None):
    """
    更新指定日期範圍和類型的資料

    Args:
        start_date (datetime.date, optional): 開始日期，如果為 None 則使用最早的資料
        end_date (datetime.date, optional): 結束日期，如果為 None 則使用最新的資料
        data_types (list, optional): 資料類型列表，如果為 None 則更新所有類型

    Returns:
        dict: 包含各種資料的字典
    """
    if start_date is None:
        start_date = datetime.date(2010, 1, 1)
    if end_date is None:
        end_date = datetime.date.today()
    if data_types is None:
        data_types = ["price", "bargin", "pe", "monthly_report", "benchmark"]

    # 生成日期範圍
    date_range = pd.date_range(start=start_date, end=end_date, freq="B")

    # 更新各種資料
    for date in tqdm(date_range, desc="更新資料"):
        date = date.date()

        if "price" in data_types:
            twe_price = twse_crawler.price_twe(date)
            otc_price = twse_crawler.price_otc(date)
            if not twe_price.empty or not otc_price.empty:
                price = pd.concat([twe_price, otc_price])
                price_file = os.path.join(TABLES_DIR, "price.pkl")
                if os.path.exists(price_file):
                    old_price = pd.read_pickle(price_file)
                    price = pd.concat([old_price, price])
                    price = price[~price.index.duplicated(keep="last")]
                price.to_pickle(price_file)

        if "bargin" in data_types:
            twe_bargin = twse_crawler.bargin_twe(date)
            otc_bargin = twse_crawler.bargin_otc(date)
            if not twe_bargin.empty or not otc_bargin.empty:
                bargin = pd.concat([twe_bargin, otc_bargin])
                bargin_file = os.path.join(TABLES_DIR, "bargin_report.pkl")
                if os.path.exists(bargin_file):
                    old_bargin = pd.read_pickle(bargin_file)
                    bargin = pd.concat([old_bargin, bargin])
                    bargin = bargin[~bargin.index.duplicated(keep="last")]
                bargin.to_pickle(bargin_file)

        if "pe" in data_types:
            twe_pe = twse_crawler.pe_twe(date)
            otc_pe = twse_crawler.pe_otc(date)
            # 防呆：檢查是否有 'stock_id' 欄位
            if (not twe_pe.empty and "stock_id" in twe_pe.columns) or (
                not otc_pe.empty and "stock_id" in otc_pe.columns
            ):
                # 只合併有 stock_id 欄位的 DataFrame
                pe_list = []
                if not twe_pe.empty and "stock_id" in twe_pe.columns:
                    pe_list.append(twe_pe)
                if not otc_pe.empty and "stock_id" in otc_pe.columns:
                    pe_list.append(otc_pe)
                if pe_list:
                    pe = pd.concat(pe_list)
                pe_file = os.path.join(TABLES_DIR, "pe.pkl")
                if os.path.exists(pe_file):
                    old_pe = pd.read_pickle(pe_file)
                    pe = pd.concat([old_pe, pe])
                    pe = pe[~pe.index.duplicated(keep="last")]
                pe.to_pickle(pe_file)
            else:
                print(
                    f"警告: {date} pe 資料缺少 stock_id 欄位，twe_pe columns: {twe_pe.columns}, otc_pe columns: {otc_pe.columns}"
                )

        if "monthly_report" in data_types and date.day <= 10:
            monthly_report = twse_crawler.month_revenue(None, date)
            if not monthly_report.empty:
                monthly_report_file = os.path.join(TABLES_DIR, "monthly_report.pkl")
                if os.path.exists(monthly_report_file):
                    old_monthly_report = pd.read_pickle(monthly_report_file)
                    monthly_report = pd.concat([old_monthly_report, monthly_report])
                    monthly_report = monthly_report[
                        ~monthly_report.index.duplicated(keep="last")
                    ]
                monthly_report.to_pickle(monthly_report_file)

        if "benchmark" in data_types:
            benchmark = twse_crawler.crawl_benchmark(date)
            if not benchmark.empty:
                benchmark_file = os.path.join(TABLES_DIR, "benchmark.pkl")
                if os.path.exists(benchmark_file):
                    old_benchmark = pd.read_pickle(benchmark_file)
                    benchmark = pd.concat([old_benchmark, benchmark])
                    benchmark = benchmark[~benchmark.index.duplicated(keep="last")]
                benchmark.to_pickle(benchmark_file)

    # 返回更新後的資料
    return load_data(start_date, end_date, data_types)


# FinMind API 相關函數
def fetch_finmind_data(data_type, stock_id=None, start_date=None, end_date=None):
    """
    使用 FinMind API 獲取資料

    Args:
        data_type (str): 資料類型，如 'TaiwanStockPrice', 'TaiwanStockFinancialStatement'
        stock_id (str, optional): 股票代號，如果為 None 則獲取所有股票
        start_date (str, optional): 開始日期，格式為 'YYYY-MM-DD'
        end_date (str, optional): 結束日期，格式為 'YYYY-MM-DD'

    Returns:
        pandas.DataFrame: 獲取的資料
    """
    try:
        # 初始化 FinMind API
        api = DataLoader()

        # 設定參數
        params = {}
        if stock_id:
            params["stock_id"] = stock_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        # 獲取資料
        if data_type == "TaiwanStockPrice":
            df = api.taiwan_stock_daily(**params)
        elif data_type == "TaiwanStockFinancialStatement":
            df = api.taiwan_stock_financial_statement(**params)
        elif data_type == "TaiwanStockBalanceSheet":
            df = api.taiwan_stock_balance_sheet(**params)
        elif data_type == "TaiwanStockCashFlowsStatement":
            df = api.taiwan_stock_cash_flows_statement(**params)
        elif data_type == "TaiwanStockNews":
            df = api.taiwan_stock_news(**params)
        else:
            df = pd.DataFrame()

        # 快取資料
        if not df.empty:
            cache_file = os.path.join(
                CACHE_DIR, f"finmind_{data_type}_{start_date}_{end_date}.csv"
            )
            df.to_csv(cache_file, index=False)

        return df
    except Exception as e:
        print(f"獲取 FinMind 資料時發生錯誤: {e}")
        return pd.DataFrame()


# Yahoo Finance API 相關函數
def fetch_yahoo_finance_data(stock_ids, start_date=None, end_date=None):
    """
    使用 Yahoo Finance API 獲取資料

    Args:
        stock_ids (list): 股票代號列表，如 ['2330.TW', '2317.TW']
        start_date (str, optional): 開始日期，格式為 'YYYY-MM-DD'
        end_date (str, optional): 結束日期，格式為 'YYYY-MM-DD'

    Returns:
        dict: 包含各股票資料的字典
    """
    try:
        result = {}

        for stock_id in stock_ids:
            # 獲取股票資料
            stock = yf.Ticker(stock_id)

            # 獲取歷史價格
            hist = stock.history(start=start_date, end=end_date)

            # 獲取基本面資料
            info = stock.info

            # 獲取財務報表
            financials = stock.financials
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow

            # 合併資料
            result[stock_id] = {
                "history": hist,
                "info": info,
                "financials": financials,
                "balance_sheet": balance_sheet,
                "cash_flow": cash_flow,
            }

            # 快取資料
            cache_dir = os.path.join(CACHE_DIR, f"yahoo_{stock_id}")
            os.makedirs(cache_dir, exist_ok=True)

            hist.to_csv(os.path.join(cache_dir, "history.csv"))
            pd.DataFrame([info]).to_csv(os.path.join(cache_dir, "info.csv"))
            financials.to_csv(os.path.join(cache_dir, "financials.csv"))
            balance_sheet.to_csv(os.path.join(cache_dir, "balance_sheet.csv"))
            cash_flow.to_csv(os.path.join(cache_dir, "cash_flow.csv"))

        return result
    except Exception as e:
        print(f"獲取 Yahoo Finance 資料時發生錯誤: {e}")
        return {}


# Alpha Vantage API 相關函數
def fetch_alpha_vantage_data(function, symbol, **kwargs):
    """
    使用 Alpha Vantage API 獲取資料

    Args:
        function (str): API 函數，如 'TIME_SERIES_DAILY', 'SMA', 'OVERVIEW'
        symbol (str): 股票代號，如 '2330.TW'
        **kwargs: 其他參數

    Returns:
        pandas.DataFrame: 獲取的資料
    """
    try:
        if not ALPHA_VANTAGE_API_KEY:
            print("未設定 Alpha Vantage API 金鑰")
            return pd.DataFrame()

        # 根據函數類型選擇適當的 API
        if function in [
            "TIME_SERIES_DAILY",
            "TIME_SERIES_WEEKLY",
            "TIME_SERIES_MONTHLY",
        ]:
            ts = TimeSeries(key=ALPHA_VANTAGE_API_KEY, output_format="pandas")
            data, meta_data = ts.get_daily(symbol=symbol, outputsize="full")
        elif function in ["SMA", "EMA", "RSI", "MACD"]:
            ti = TechIndicators(key=ALPHA_VANTAGE_API_KEY, output_format="pandas")
            if function == "SMA":
                data, meta_data = ti.get_sma(symbol=symbol, **kwargs)
            elif function == "EMA":
                data, meta_data = ti.get_ema(symbol=symbol, **kwargs)
            elif function == "RSI":
                data, meta_data = ti.get_rsi(symbol=symbol, **kwargs)
            elif function == "MACD":
                data, meta_data = ti.get_macd(symbol=symbol, **kwargs)
        elif function in ["OVERVIEW", "INCOME_STATEMENT", "BALANCE_SHEET", "CASH_FLOW"]:
            fd = FundamentalData(key=ALPHA_VANTAGE_API_KEY, output_format="pandas")
            if function == "OVERVIEW":
                data, meta_data = fd.get_company_overview(symbol=symbol)
            elif function == "INCOME_STATEMENT":
                data, meta_data = fd.get_income_statement_annual(symbol=symbol)
            elif function == "BALANCE_SHEET":
                data, meta_data = fd.get_balance_sheet_annual(symbol=symbol)
            elif function == "CASH_FLOW":
                data, meta_data = fd.get_cash_flow_annual(symbol=symbol)
        else:
            return pd.DataFrame()

        # 快取資料
        cache_file = os.path.join(CACHE_DIR, f"alpha_vantage_{function}_{symbol}.csv")
        data.to_csv(cache_file)

        return data
    except Exception as e:
        print(f"獲取 Alpha Vantage 資料時發生錯誤: {e}")
        return pd.DataFrame()


# 資料清洗函數
def clean_data(df, method="ffill"):
    """
    清洗資料，包括缺值填補、日期格式統一、欄位標準化

    Args:
        df (pandas.DataFrame): 要清洗的資料
        method (str): 缺值填補方法，'ffill' 為前向填補，'bfill' 為後向填補

    Returns:
        pandas.DataFrame: 清洗後的資料
    """
    if df.empty:
        return df

    # 複製資料，避免修改原始資料
    df = df.copy()

    # 處理日期欄位
    date_columns = [
        col for col in df.columns if "date" in col.lower() or "time" in col.lower()
    ]
    for col in date_columns:
        if df[col].dtype == "object":
            try:
                df[col] = pd.to_datetime(df[col])
            except BaseException:
                pass

    # 處理缺值
    if method == "ffill":
        df = df.fillna(method="ffill")
    elif method == "bfill":
        df = df.fillna(method="bfill")

    # 標準化欄位名稱
    df.columns = df.columns.str.lower().str.replace(" ", "_")

    return df


# 資料庫相關函數
def save_to_database(df, table_name):
    """
    將資料儲存到 SQLite 資料庫

    Args:
        df (pandas.DataFrame): 要儲存的資料
        table_name (str): 資料表名稱

    Returns:
        bool: 是否成功儲存
    """
    # 若 table_name 為 news，自動轉為 market_info
    if table_name == "news":
        table_name = "market_info"
        # 補齊必要欄位
        if "sentiment" not in df.columns:
            df["sentiment"] = 0.0
        if "data_source" not in df.columns:
            df["data_source"] = "perplexity"
        if "query" not in df.columns:
            df["query"] = ""
        if "url" not in df.columns:
            df["url"] = ""
        if "title" not in df.columns:
            df["title"] = ""
        if "crawl_date" not in df.columns:
            df["crawl_date"] = datetime.datetime.now().strftime("%Y-%m-%d")
        if "source" not in df.columns:
            df["source"] = ""
    try:
        conn = sqlite3.connect(DB_PATH)
        df.to_sql(table_name, conn, if_exists="append", index=False)
        conn.close()
        return True
    except Exception as e:
        print(f"儲存資料到資料庫時發生錯誤: {e}")
        return False


# 定時更新函數
def schedule_fetch(
    stock_ids=None, interval="daily", start_time="08:00", end_time="16:00"
):
    """
    使用 APScheduler 實現每日定時更新，並將資料快取至 CSV/SQLite

    Args:
        stock_ids (list, optional): 股票代號列表，如果為 None 則更新所有股票
        interval (str): 更新間隔，'daily', 'hourly', 'minute'
        start_time (str): 開始時間，格式為 'HH:MM'
        end_time (str): 結束時間，格式為 'HH:MM'

    Returns:
        apscheduler.schedulers.background.BackgroundScheduler: 排程器
    """
    # 初始化排程器
    scheduler = BackgroundScheduler()

    # 定義更新函數
    def update_job():
    """
    update_job
    
    """
        try:
            # 更新日期
            today = datetime.datetime.now().date()
            yesterday = today - datetime.timedelta(days=1)

            # 更新台股資料
            print(f"更新台股資料: {today}")
            update_data(yesterday, today)

            # 更新 FinMind 資料
            if stock_ids:
                for stock_id in stock_ids:
                    print(f"更新 FinMind 資料: {stock_id}")
                    df = fetch_finmind_data(
                        "TaiwanStockPrice",
                        stock_id,
                        yesterday.strftime("%Y-%m-%d"),
                        today.strftime("%Y-%m-%d"),
                    )
                    if not df.empty:
                        df = clean_data(df)
                        save_to_database(df, "stock_price")

            # 更新 Yahoo Finance 資料
            if stock_ids:
                print(f"更新 Yahoo Finance 資料")
                yahoo_data = fetch_yahoo_finance_data(
                    [f"{s}.TW" for s in stock_ids],
                    yesterday.strftime("%Y-%m-%d"),
                    today.strftime("%Y-%m-%d"),
                )

                for stock_id, data in yahoo_data.items():
                    history = data["history"]
                    if not history.empty:
                        history = clean_data(history)
                        history["stock_id"] = stock_id.replace(".TW", "")
                        history = history.reset_index()
                        save_to_database(history, "stock_price")

            # 更新 Alpha Vantage 資料
            if stock_ids and ALPHA_VANTAGE_API_KEY:
                for stock_id in stock_ids:
                    print(f"更新 Alpha Vantage 資料: {stock_id}")
                    # 獲取技術指標
                    for indicator in ["SMA", "RSI", "MACD"]:
                        df = fetch_alpha_vantage_data(
                            indicator, f"{stock_id}.TW", time_period=14
                        )
                        if not df.empty:
                            df = clean_data(df)
                            df["stock_id"] = stock_id
                            df["indicator_name"] = indicator
                            df = df.reset_index()
                            save_to_database(df, "technical_indicator")

                    # 獲取基本面資料
                    df = fetch_alpha_vantage_data("OVERVIEW", f"{stock_id}.TW")
                    if not df.empty:
                        df = clean_data(df)
                        df["stock_id"] = stock_id
                        save_to_database(df, "financial_statement")

            print("資料更新完成")
        except Exception as e:
            print(f"更新資料時發生錯誤: {e}")

    # 設定排程
    if interval == "daily":
        scheduler.add_job(
            update_job,
            CronTrigger(hour=start_time.split(":")[0], minute=start_time.split(":")[1]),
        )
    elif interval == "hourly":
        scheduler.add_job(
            update_job,
            "interval",
            hours=1,
            start_date=f"{datetime.datetime.now().date()} {start_time}",
            end_date=f"{datetime.datetime.now().date()} {end_time}",
        )
    elif interval == "minute":
        scheduler.add_job(
            update_job,
            "interval",
            minutes=1,
            start_date=f"{datetime.datetime.now().date()} {start_time}",
            end_date=f"{datetime.datetime.now().date()} {end_time}",
        )

    # 啟動排程器
    scheduler.start()

    return scheduler


# 儲存資料框到 CSV 檔案
def save_dataframe(df, name):
    """
    將資料框儲存為 CSV 檔案

    Args:
        df (pandas.DataFrame): 要儲存的資料框
        name (str): 檔案名稱（不含副檔名）

    Returns:
        str: 儲存的檔案路徑
    """
    # 確保 data 目錄存在
    data_dir = os.path.join(os.getcwd(), "data")
    os.makedirs(data_dir, exist_ok=True)

    # 設定檔案路徑
    file_path = os.path.join(data_dir, f"{name}.csv")

    # 儲存資料框
    df.to_csv(file_path)
    print(f"已儲存資料至 {file_path}")

    return file_path
