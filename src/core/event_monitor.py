"""
重大新聞與異常監控模組

此模組負責監控市場重大新聞和異常事件，
並在發生重要事件時發出警報，以便及時調整交易策略。

主要功能：
- 新聞監控
- 異常價格監控
- 異常交易量監控
- 事件通知
- 複雜事件處理
- 事件關聯分析
- 異常檢測
"""

import asyncio
import gc
import logging
import os
import re
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

import feedparser
import pandas as pd
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# 可選依賴導入 - psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

# 可選依賴導入
try:
    from FinMind.data import DataLoader
    FINMIND_AVAILABLE = True
except ImportError:
    FINMIND_AVAILABLE = False
    DataLoader = None

try:
    from snownlp import SnowNLP
    SNOWNLP_AVAILABLE = True
except ImportError:
    SNOWNLP_AVAILABLE = False
    SnowNLP = None

from .events.anomaly_detector import ValueAnomalyDetector

# 導入事件處理引擎
from .events.event import Event, EventSeverity, EventSource, EventType
from .events.event_aggregator import SubjectAggregator
from .events.event_bus import event_bus
from .events.event_correlation import SubjectCorrelator
from .events.event_processor import EventProcessor, processor_registry
from .events.event_store import event_store

# 載入環境變數
load_dotenv()


# 常數定義
class MonitorConstants:
    """監控系統常數"""

    # 預設閾值
    DEFAULT_PRICE_THRESHOLD = 0.05  # 5% 價格變化閾值
    DEFAULT_VOLUME_THRESHOLD = 2.0  # 2倍成交量變化閾值
    DEFAULT_CHECK_INTERVAL = 60  # 60秒檢查間隔

    # 情緒分析閾值
    NEGATIVE_SENTIMENT_THRESHOLD = -0.7
    POSITIVE_SENTIMENT_THRESHOLD = 0.7

    # 事件嚴重程度閾值
    HIGH_SEVERITY_MULTIPLIER = 2.0

    # 新聞來源
    DEFAULT_NEWS_SOURCES = [
        "https://news.cnyes.com/news/cat/tw_stock",
        "https://www.moneydj.com/kmdj/news/newsviewer.aspx",
        "https://www.twse.com.tw/zh/news/newsListing",
    ]

    # 通知渠道
    DEFAULT_NOTIFICATION_CHANNELS = ["log"]

    # 效能相關
    MAX_EVENTS_IN_MEMORY = 1000
    GC_INTERVAL = 300  # 5分鐘垃圾回收間隔
    REQUEST_TIMEOUT = 30  # 30秒請求超時

    # 重要新聞關鍵字
    IMPORTANT_KEYWORDS = [
        "盈餘",
        "財報",
        "營收",
        "獲利",
        "虧損",
        "配息",
        "配股",
        "除權",
        "除息",
        "合併",
        "收購",
        "策略聯盟",
        "重大投資",
        "重大交易",
        "重大訊息",
        "重大事件",
        "董事會",
        "股東會",
        "增資",
        "減資",
        "私募",
        "下市",
        "下櫃",
        "停牌",
        "恢復交易",
        "財務危機",
        "破產",
        "重整",
        "接管",
        "解散",
        "清算",
        "裁員",
        "裁撤",
        "關廠",
        "罰款",
        "訴訟",
        "糾紛",
        "違約",
        "違法",
        "調查",
        "檢調",
        "約談",
        "搜索",
        "疫情",
        "天災",
        "事故",
        "火災",
        "爆炸",
        "污染",
        "罷工",
        "抗議",
        "抵制",
        "升息",
        "降息",
        "升評",
        "降評",
        "信評",
        "評等",
        "評級",
        "評價",
        "評比",
        "漲停",
        "跌停",
        "暴漲",
        "暴跌",
        "崩盤",
        "熔斷",
        "恐慌",
        "瘋狂",
        "狂熱",
        "創新高",
        "創新低",
        "突破",
        "跌破",
        "反彈",
        "反轉",
        "回檔",
        "修正",
        "整理",
        "利多",
        "利空",
        "買進",
        "賣出",
        "加碼",
        "減碼",
        "進場",
        "出場",
        "建倉",
        "出清",
    ]

    # 高嚴重程度關鍵字
    HIGH_SEVERITY_KEYWORDS = [
        "重大",
        "緊急",
        "立即",
        "破產",
        "接管",
        "停牌",
        "下市",
        "下櫃",
    ]


class MonitorConfig:
    """監控配置類"""

    def __init__(
        self,
        price_threshold: float = MonitorConstants.DEFAULT_PRICE_THRESHOLD,
        volume_threshold: float = MonitorConstants.DEFAULT_VOLUME_THRESHOLD,
        check_interval: int = MonitorConstants.DEFAULT_CHECK_INTERVAL,
        news_sources: Optional[List[str]] = None,
        notification_channels: Optional[List[str]] = None,
        use_event_engine: bool = True,
    ):
        """
        初始化監控配置

        Args:
            price_threshold: 價格變化閾值
            volume_threshold: 成交量變化閾值
            check_interval: 檢查間隔（秒）
            news_sources: 新聞來源列表
            notification_channels: 通知渠道列表
            use_event_engine: 是否使用事件引擎
        """
        self.price_threshold = price_threshold
        self.volume_threshold = volume_threshold
        self.check_interval = check_interval
        self.news_sources = news_sources or MonitorConstants.DEFAULT_NEWS_SOURCES.copy()
        self.notification_channels = (
            notification_channels
            or MonitorConstants.DEFAULT_NOTIFICATION_CHANNELS.copy()
        )
        self.use_event_engine = use_event_engine


# 設定日誌目錄
log_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs"
)
os.makedirs(log_dir, exist_ok=True)

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, "event_monitor.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class NewsProcessor(ABC):
    """新聞處理器抽象基類"""

    @abstractmethod
    def can_process(self, source: str) -> bool:
        """
        檢查是否可以處理指定來源的新聞

        Args:
            source: 新聞來源URL

        Returns:
            bool: 是否可以處理
        """
        raise NotImplementedError("子類必須實現 can_process 方法")

    @abstractmethod
    def parse_news(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        解析新聞內容

        Args:
            soup: BeautifulSoup 物件

        Returns:
            List[Dict[str, str]]: 新聞列表
        """
        raise NotImplementedError("子類必須實現 parse_news 方法")


class CnyesNewsProcessor(NewsProcessor):
    """鉅亨網新聞處理器"""

    def can_process(self, source: str) -> bool:
        """檢查是否可以處理鉅亨網新聞"""
        return "cnyes.com" in source

    def parse_news(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """解析鉅亨網新聞"""
        news_list = []
        try:
            # 查找新聞項目
            news_items = soup.find_all("div", class_="news-item")

            for item in news_items:
                title_element = item.find("h3")
                if title_element:
                    title = title_element.get_text(strip=True)

                    # 提取連結
                    link_element = title_element.find("a")
                    link = link_element.get("href") if link_element else ""

                    # 提取時間
                    time_element = item.find("time")
                    publish_time = (
                        time_element.get_text(strip=True) if time_element else ""
                    )

                    # 提取摘要
                    summary_element = item.find("p", class_="summary")
                    summary = (
                        summary_element.get_text(strip=True) if summary_element else ""
                    )

                    # 嘗試從標題中提取股票代號
                    stock_id_match = re.search(r"(\d{4,6})", title)
                    stock_id = stock_id_match.group(1) if stock_id_match else ""

                    news_list.append(
                        {
                            "title": title,
                            "link": link,
                            "publish_time": publish_time,
                            "summary": summary,
                            "stock_id": stock_id,
                            "source": "鉅亨網",
                        }
                    )
        except Exception as e:
            logger.error("解析鉅亨網新聞時發生錯誤: %s", e)

        return news_list


class MoneyDJNewsProcessor(NewsProcessor):
    """MoneyDJ新聞處理器"""

    def can_process(self, source: str) -> bool:
        """檢查是否可以處理MoneyDJ新聞"""
        return "moneydj.com" in source

    def parse_news(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """解析MoneyDJ新聞"""
        news_list = []
        try:
            # 查找新聞項目
            news_items = soup.find_all("tr", class_="news-row")

            for item in news_items:
                title_element = item.find("td", class_="title")
                if title_element:
                    title_link = title_element.find("a")
                    if title_link:
                        title = title_link.get_text(strip=True)
                        link = title_link.get("href", "")

                        # 提取時間
                        time_element = item.find("td", class_="time")
                        publish_time = (
                            time_element.get_text(strip=True) if time_element else ""
                        )

                        # 嘗試從標題中提取股票代號
                        stock_id_match = re.search(r"(\d{4,6})", title)
                        stock_id = stock_id_match.group(1) if stock_id_match else ""

                        news_list.append(
                            {
                                "title": title,
                                "link": link,
                                "publish_time": publish_time,
                                "summary": "",
                                "stock_id": stock_id,
                                "source": "MoneyDJ",
                            }
                        )
        except Exception as e:
            logger.error("解析 MoneyDJ 新聞時發生錯誤: %s", e)

        return news_list


class TWSENewsProcessor(NewsProcessor):
    """證交所新聞處理器"""

    def can_process(self, source: str) -> bool:
        """檢查是否可以處理證交所新聞"""
        return "twse.com.tw" in source

    def parse_news(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """解析證交所新聞"""
        news_list = []
        try:
            # 查找新聞項目
            news_items = soup.find_all("tr")

            for item in news_items[1:]:  # 跳過標題行
                cells = item.find_all("td")
                if len(cells) >= 3:
                    # 提取日期
                    date_cell = cells[0]
                    publish_time = date_cell.get_text(strip=True)

                    # 提取標題和連結
                    title_cell = cells[1]
                    title_link = title_cell.find("a")
                    if title_link:
                        title = title_link.get_text(strip=True)
                        link = title_link.get("href", "")

                        # 嘗試從標題中提取股票代號
                        stock_id_match = re.search(r"(\d{4,6})", title)
                        stock_id = stock_id_match.group(1) if stock_id_match else ""

                        news_list.append(
                            {
                                "title": title,
                                "link": link,
                                "publish_time": publish_time,
                                "summary": "",
                                "stock_id": stock_id,
                                "source": "證交所",
                            }
                        )
        except Exception as e:
            logger.error("解析證交所新聞時發生錯誤: %s", e)

        return news_list


class NewsProcessorFactory:
    """新聞處理器工廠"""

    def __init__(self):
        """初始化新聞處理器工廠"""
        self.processors = [
            CnyesNewsProcessor(),
            MoneyDJNewsProcessor(),
            TWSENewsProcessor(),
        ]

    def get_processor(self, source: str) -> Optional[NewsProcessor]:
        """
        根據來源獲取對應的新聞處理器

        Args:
            source: 新聞來源URL

        Returns:
            Optional[NewsProcessor]: 新聞處理器，如果沒有找到則返回None
        """
        for processor in self.processors:
            if processor.can_process(source):
                return processor
        return None


class EventMonitor:
    """事件監控類，用於監控各種事件"""

    def __init__(
        self,
        config: Optional[MonitorConfig] = None,
        price_df: Optional[pd.DataFrame] = None,
        volume_df: Optional[pd.DataFrame] = None,
    ):
        """
        初始化事件監控器

        Args:
            config: 監控配置物件
            price_df: 價格資料
            volume_df: 成交量資料
        """
        # 使用配置物件或建立預設配置
        self.config = config or MonitorConfig()

        # 資料框
        self.price_df = price_df
        self.volume_df = volume_df

        # 狀態管理
        self.running = False
        self.monitor_thread = None
        self.events = []
        self.last_check_time = datetime.now()
        self.async_task = None
        self.last_gc_time = datetime.now()

        # 新聞處理器工廠
        self.news_processor_factory = NewsProcessorFactory()

        # 初始化事件處理引擎
        if self.config.use_event_engine:
            self._init_event_engine()

    def _init_event_engine(self):
        """初始化事件處理引擎"""
        try:
            # 啟動事件總線
            event_bus.start()

            # 啟動事件存儲
            event_store.start()

            # 創建事件處理器
            self._create_event_processors()

            logger.info("事件處理引擎已初始化")
        except Exception as e:
            logger.error("初始化事件處理引擎時發生錯誤: %s", e)
            self.use_event_engine = False

    def _create_event_processors(self):
        """創建事件處理器"""
        try:
            # 創建價格異常檢測器
            price_detector = ValueAnomalyDetector(
                name="price_anomaly_detector",
                event_types=[EventType.MARKET_DATA],
                data_field="price",
                threshold=3.0,
            )
            processor_registry.register(price_detector)

            # 創建成交量異常檢測器
            volume_detector = ValueAnomalyDetector(
                name="volume_anomaly_detector",
                event_types=[EventType.MARKET_DATA],
                data_field="volume",
                threshold=3.0,
            )
            processor_registry.register(volume_detector)

            # 創建新聞情緒分析器
            class SentimentProcessor(EventProcessor):
                """
                新聞情緒分析處理器

                分析新聞事件的情緒並生成相應的警報事件。
                """

                def __init__(self, name, event_types, monitor):
                    """
                    初始化情緒分析處理器

                    Args:
                        name: 處理器名稱
                        event_types: 處理的事件類型
                        monitor: 監控器實例
                    """
                    super().__init__(name, event_types)
                    self.monitor = monitor

                def process_event(self, event):
                    """
                    處理事件

                    Args:
                        event: 要處理的事件
                    """
                    if event.event_type != EventType.NEWS:
                        return None

                    # 分析情緒
                    text = event.message or ""
                    if "content" in event.data:
                        text += " " + event.data["content"]

                    sentiment_score = self.monitor.analyze_sentiment(text)

                    # 更新事件數據
                    event.data["sentiment_score"] = sentiment_score

                    # 如果情緒分數低於 -0.7，生成警報事件
                    if sentiment_score < -0.7:
                        return Event(
                            event_type=EventType.COMPOSITE_EVENT,
                            source=EventSource.MONITORING,
                            severity=EventSeverity.WARNING,
                            subject=event.subject,
                            message=f"負面新聞: {event.message} (情緒分數: {sentiment_score:.2f})",
                            data={
                                "sentiment_score": sentiment_score,
                                "original_event_id": event.id,
                            },
                            tags=["sentiment", "negative", "news"],
                            related_events=[event.id],
                        )

                    return None

            sentiment_processor = SentimentProcessor(
                name="sentiment_processor", event_types=[EventType.NEWS], monitor=self
            )
            processor_registry.register(sentiment_processor)

            # 創建事件聚合器
            news_aggregator = SubjectAggregator(
                name="news_aggregator",
                event_types=[EventType.NEWS],
                window_size=300,
                threshold=3,
            )
            processor_registry.register(news_aggregator)

            # 創建事件關聯分析器
            correlator = SubjectCorrelator(
                name="subject_correlator",
                event_types=[
                    EventType.PRICE_ANOMALY,
                    EventType.VOLUME_ANOMALY,
                    EventType.NEWS,
                ],
                window_size=600,
                threshold=2,
            )
            processor_registry.register(correlator)

            # 啟動所有處理器
            processor_registry.start_all()

            logger.info("事件處理器已創建並啟動")
        except Exception as e:
            logger.error("創建事件處理器時發生錯誤: %s", e)

    def start(self):
        """
        啟動監控

        Returns:
            bool: 是否成功啟動
        """
        if self.running:
            logger.warning("監控已經在運行中")
            return False

        # 啟動事件處理引擎
        if self.use_event_engine and not event_bus.get_stats()["running"]:
            event_bus.start()
            event_store.start()
            processor_registry.start_all()

        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

        logger.info("事件監控已啟動")
        return True

    def stop(self):
        """
        停止監控

        Returns:
            bool: 是否成功停止
        """
        if not self.running:
            logger.warning("監控尚未啟動")
            return False

        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)

        # 停止事件處理引擎
        if self.use_event_engine:
            try:
                processor_registry.stop_all()
                event_store.stop()
                event_bus.stop()
                logger.info("事件處理引擎已停止")
            except Exception as e:
                logger.error("停止事件處理引擎時發生錯誤: %s", e)

        logger.info("事件監控已停止")
        return True

    def _monitor_loop(self):
        """監控循環"""
        while self.running:
            try:
                # 檢查價格異常
                self._check_price_anomaly()

                # 檢查成交量異常
                self._check_volume_anomaly()

                # 檢查新聞
                self._check_news()

                # 記憶體管理
                self._manage_memory()

                # 更新最後檢查時間
                self.last_check_time = datetime.now()

                # 等待下一次檢查
                time.sleep(self.config.check_interval)
            except Exception as e:
                logger.error("監控循環發生錯誤: %s", e)
                time.sleep(10)

    def _manage_memory(self):
        """記憶體管理"""
        current_time = datetime.now()

        # 定期垃圾回收
        if (
            current_time - self.last_gc_time
        ).total_seconds() > MonitorConstants.GC_INTERVAL:
            # 清理過多的事件記錄
            if len(self.events) > MonitorConstants.MAX_EVENTS_IN_MEMORY:
                # 保留最新的事件
                self.events = self.events[-MonitorConstants.MAX_EVENTS_IN_MEMORY // 2 :]
                logger.info("清理事件記錄，保留最新 %d 個事件", len(self.events))

            # 執行垃圾回收
            gc.collect()
            self.last_gc_time = current_time

            # 記錄記憶體使用情況
            if PSUTIL_AVAILABLE:
                process = psutil.Process()
                memory_info = process.memory_info()
                logger.debug(
                    "記憶體使用: RSS=%d MB, VMS=%d MB",
                    memory_info.rss // 1024 // 1024,
                    memory_info.vms // 1024 // 1024,
                )
            else:
                logger.debug("psutil 不可用，跳過記憶體監控")

    def _check_price_anomaly(self):
        """檢查價格異常"""
        if self.price_df is None or len(self.price_df) < 2:
            return

        try:
            # 獲取最新價格和前一天價格
            latest_prices = self.price_df.iloc[-1]
            previous_prices = self.price_df.iloc[-2]

            # 計算價格變化率
            price_changes = (latest_prices - previous_prices) / previous_prices

            # 檢查異常
            for stock_id, change in price_changes.items():
                if abs(change) > self.config.price_threshold:
                    self._create_price_anomaly_event(
                        stock_id, change, latest_prices, previous_prices
                    )
        except Exception as e:
            logger.error("檢查價格異常時發生錯誤: %s", e)

    def _create_price_anomaly_event(
        self,
        stock_id: str,
        change: float,
        latest_prices: pd.Series,
        previous_prices: pd.Series,
    ):
        """
        創建價格異常事件

        Args:
            stock_id: 股票代號
            change: 價格變化率
            latest_prices: 最新價格
            previous_prices: 前一天價格
        """
        # 判斷嚴重程度
        is_high_severity = (
            abs(change)
            > self.config.price_threshold * MonitorConstants.HIGH_SEVERITY_MULTIPLIER
        )

        if self.config.use_event_engine:
            # 使用新的事件處理引擎
            event = Event(
                event_type=EventType.PRICE_ANOMALY,
                source=EventSource.MARKET_DATA,
                subject=stock_id,
                severity=(
                    EventSeverity.ERROR if is_high_severity else EventSeverity.WARNING
                ),
                message=f"價格異常變化: {change:.2%}",
                data={
                    "stock_id": stock_id,
                    "price": float(latest_prices[stock_id]),
                    "previous_price": float(previous_prices[stock_id]),
                    "change": float(change),
                    "threshold": self.config.price_threshold,
                },
                tags=["price", "anomaly", "market"],
            )
            event_bus.publish(event)
        else:
            # 使用舊的事件處理方式
            event = Event(
                event_type=EventType.PRICE_ANOMALY,
                stock_id=stock_id,
                content=f"價格異常變化: {change:.2%}",
                severity="high" if is_high_severity else "medium",
            )
            self.events.append(event)
            self._send_notification(event)

    def _check_volume_anomaly(self):
        """檢查成交量異常"""
        if self.volume_df is None or len(self.volume_df) < 6:
            return

        try:
            # 獲取最新成交量和平均成交量
            latest_volumes = self.volume_df.iloc[-1]
            avg_volumes = self.volume_df.iloc[-6:-1].mean()

            # 計算成交量變化率
            volume_changes = latest_volumes / avg_volumes

            # 檢查異常
            for stock_id, change in volume_changes.items():
                if change > self.config.volume_threshold:
                    self._create_volume_anomaly_event(
                        stock_id, change, latest_volumes, avg_volumes
                    )
        except Exception as e:
            logger.error("檢查成交量異常時發生錯誤: %s", e)

    def _create_volume_anomaly_event(
        self,
        stock_id: str,
        change: float,
        latest_volumes: pd.Series,
        avg_volumes: pd.Series,
    ):
        """
        創建成交量異常事件

        Args:
            stock_id: 股票代號
            change: 成交量變化率
            latest_volumes: 最新成交量
            avg_volumes: 平均成交量
        """
        # 判斷嚴重程度
        is_high_severity = (
            change
            > self.config.volume_threshold * MonitorConstants.HIGH_SEVERITY_MULTIPLIER
        )

        if self.config.use_event_engine:
            # 使用新的事件處理引擎
            event = Event(
                event_type=EventType.VOLUME_ANOMALY,
                source=EventSource.MARKET_DATA,
                subject=stock_id,
                severity=(
                    EventSeverity.ERROR if is_high_severity else EventSeverity.WARNING
                ),
                message=f"成交量異常變化: {change:.2f}倍",
                data={
                    "stock_id": stock_id,
                    "volume": float(latest_volumes[stock_id]),
                    "avg_volume": float(avg_volumes[stock_id]),
                    "change": float(change),
                    "threshold": self.config.volume_threshold,
                },
                tags=["volume", "anomaly", "market"],
            )
            event_bus.publish(event)
        else:
            # 使用舊的事件處理方式
            event = Event(
                event_type=EventType.VOLUME_ANOMALY,
                stock_id=stock_id,
                content=f"成交量異常變化: {change:.2f}倍",
                severity="high" if is_high_severity else "medium",
            )
            self.events.append(event)
            self._send_notification(event)

    def _check_news(self):
        """檢查新聞"""
        for source in self.config.news_sources:
            try:
                # 獲取新聞
                news_list = self._fetch_news(source)

                # 檢查新聞
                for news in news_list:
                    # 檢查是否為重要新聞
                    if self._is_important_news(news):
                        self._create_news_event(news, source)
            except Exception as e:
                logger.error("獲取新聞時發生錯誤: %s", e)

    def _create_news_event(self, news: Dict[str, str], source: str):
        """
        創建新聞事件

        Args:
            news: 新聞資料
            source: 新聞來源
        """
        # 判斷嚴重程度
        is_high_severity = news.get("severity") == "high"

        if self.config.use_event_engine:
            # 使用新的事件處理引擎
            event = Event(
                event_type=EventType.NEWS,
                source=EventSource.NEWS_FEED,
                subject=news.get("stock_id", "market"),
                severity=(
                    EventSeverity.ERROR if is_high_severity else EventSeverity.WARNING
                ),
                message=news.get("title", ""),
                data={
                    "stock_id": news.get("stock_id"),
                    "title": news.get("title"),
                    "content": news.get("content", ""),
                    "url": news.get("url", ""),
                    "source": source,
                    "timestamp": self._format_timestamp(news.get("timestamp")),
                },
                tags=["news", "important", news.get("severity", "medium")],
            )
            event_bus.publish(event)
        else:
            # 使用舊的事件處理方式
            event = Event(
                event_type=EventType.NEWS,
                stock_id=news.get("stock_id"),
                content=news.get("title"),
                source=source,
                severity=news.get("severity", "medium"),
            )
            self.events.append(event)
            self._send_notification(event)

    def _format_timestamp(self, timestamp) -> str:
        """
        格式化時間戳

        Args:
            timestamp: 時間戳

        Returns:
            str: 格式化後的時間戳
        """
        if isinstance(timestamp, datetime):
            return timestamp.isoformat()
        if timestamp:
            return str(timestamp)
        return datetime.now().isoformat()

    def _fetch_news(self, source: str) -> List[Dict[str, str]]:
        """
        獲取新聞

        Args:
            source: 新聞來源URL

        Returns:
            List[Dict[str, str]]: 新聞列表
        """
        try:
            # 發送請求
            response = requests.get(
                source,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=MonitorConstants.REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            # 解析HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # 使用新聞處理器工廠獲取對應的處理器
            processor = self.news_processor_factory.get_processor(source)
            if processor:
                return processor.parse_news(soup)

            logger.warning("未找到適合的新聞處理器: %s", source)
            return []
        except requests.RequestException as e:
            logger.error("請求新聞時發生錯誤: %s", e)
            return []
        except Exception as e:
            logger.error("獲取新聞時發生錯誤: %s", e)
            return []

    def _is_important_news(self, news: Dict[str, str]) -> bool:
        """
        判斷是否為重要新聞

        Args:
            news: 新聞資料

        Returns:
            bool: 是否為重要新聞
        """
        title = news.get("title", "")

        # 檢查新聞標題是否包含重要關鍵字
        for keyword in MonitorConstants.IMPORTANT_KEYWORDS:
            if keyword in title:
                # 設定新聞嚴重程度
                news["severity"] = self._determine_news_severity(title)

                # 嘗試從標題中提取股票代號
                stock_id_match = re.search(r"(\d{4,6})", title)
                if stock_id_match:
                    news["stock_id"] = stock_id_match.group(1)

                return True

        return False

    def _determine_news_severity(self, title: str) -> str:
        """
        判斷新聞嚴重程度

        Args:
            title: 新聞標題

        Returns:
            str: 嚴重程度 ("high" 或 "medium")
        """
        for keyword in MonitorConstants.HIGH_SEVERITY_KEYWORDS:
            if keyword in title:
                return "high"
        return "medium"

    def _send_notification(self, event):
        """
        發送通知

        Args:
            event: 事件物件
        """
        # 根據不同的通知渠道發送通知
        for channel in self.config.notification_channels:
            try:
                if channel == "log":
                    self._send_log_notification(event)
                elif channel == "email":
                    self._send_email(event)
                elif channel == "line":
                    self._send_line(event)
                elif channel == "telegram":
                    self._send_telegram(event)
                else:
                    logger.warning("未知的通知渠道: %s", channel)
            except Exception as e:
                logger.error("發送 %s 通知時發生錯誤: %s", channel, e)

    def _send_log_notification(self, event):
        """
        發送日誌通知

        Args:
            event: 事件物件
        """
        # 記錄到日誌
        logger.info(
            "事件: %s, 股票: %s, 內容: %s, 嚴重程度: %s",
            event.event_type,
            getattr(event, "stock_id", "N/A"),
            getattr(event, "content", getattr(event, "message", "N/A")),
            getattr(event, "severity", "N/A"),
        )

    def _send_email(self, event):
        """
        發送電子郵件通知

        Args:
            event (Event): 事件
        """
        # 這裡簡化了電子郵件發送的邏輯，實際實現可能需要更複雜的郵件發送功能
        logger.info(
            "發送電子郵件通知: %s, %s, %s",
            event.event_type,
            event.stock_id,
            event.content,
        )

    def _send_line(self, event):
        """
        發送 Line 通知

        Args:
            event (Event): 事件
        """
        # 這裡簡化了 Line 通知發送的邏輯，實際實現可能需要使用 Line Notify API
        logger.info(
            "發送 Line 通知: %s, %s, %s",
            event.event_type,
            event.stock_id,
            event.content,
        )

    def _send_telegram(self, event):
        """
        發送 Telegram 通知

        Args:
            event (Event): 事件
        """
        # 這裡簡化了 Telegram 通知發送的邏輯，實際實現可能需要使用 Telegram Bot API
        logger.info(
            "發送 Telegram 通知: %s, %s, %s",
            event.event_type,
            event.stock_id,
            event.content,
        )

    def get_events(
        self, event_type=None, stock_id=None, start_time=None, end_time=None
    ):
        """
        獲取事件列表

        Args:
            event_type (str, optional): 事件類型
            stock_id (str, optional): 股票代號
            start_time (datetime, optional): 開始時間
            end_time (datetime, optional): 結束時間

        Returns:
            list: 事件列表
        """
        filtered_events = self.events

        # 過濾事件類型
        if event_type:
            filtered_events = [e for e in filtered_events if e.event_type == event_type]

        # 過濾股票代號
        if stock_id:
            filtered_events = [e for e in filtered_events if e.stock_id == stock_id]

        # 過濾時間範圍
        if start_time:
            filtered_events = [e for e in filtered_events if e.timestamp >= start_time]

        if end_time:
            filtered_events = [e for e in filtered_events if e.timestamp <= end_time]

        return filtered_events

    def fetch_recent_news(self, keywords=None, max_news=10):
        """
        拉取指定關鍵字的最新新聞

        Args:
            keywords (list, optional): 關鍵字列表，如果為 None，則拉取所有新聞
            max_news (int): 最大新聞數量

        Returns:
            list: 新聞列表，每個新聞是一個字典，包含標題、內容、來源、時間等資訊
        """
        news_list = []

        # 方法一：使用 FinMind 獲取新聞
        try:
            if not FINMIND_AVAILABLE:
                logger.warning("FinMind 未安裝，跳過新聞獲取")
                return []

            # 初始化 FinMind API
            api = DataLoader()

            # 獲取台股新聞
            news_data = api.taiwan_stock_news(
                stock_id="",  # 空字串表示獲取所有股票的新聞
                start_date=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                end_date=datetime.now().strftime("%Y-%m-%d"),
            )

            # 過濾關鍵字
            if keywords:
                filtered_news = []
                for _, row in news_data.iterrows():
                    if any(keyword in row["title"] for keyword in keywords):
                        filtered_news.append(
                            {
                                "title": row["title"],
                                "content": row.get("content", ""),
                                "source": "FinMind",
                                "url": row.get("link", ""),
                                "timestamp": pd.to_datetime(row["date"]),
                                "stock_id": row.get("stock_id", ""),
                            }
                        )
                news_list.extend(filtered_news[:max_news])
        except Exception as e:
            logger.error("使用 FinMind 獲取新聞時發生錯誤: %s", e)

        # 方法二：使用 RSS 獲取新聞
        if len(news_list) < max_news:
            rss_feeds = [
                "https://news.cnyes.com/rss/news/tw_stock_news.xml",  # 鉅亨網台股新聞
                "https://www.moneydj.com/KMDJ/RSS/RSS.aspx?svc=StockNews&ftype=1",  # MoneyDJ 股市新聞
                "https://www.twse.com.tw/rss/news.xml",  # 證交所新聞
            ]

            for feed_url in rss_feeds:
                try:
                    feed = feedparser.parse(feed_url)

                    for entry in feed.entries[:max_news]:
                        # 過濾關鍵字
                        if keywords and not any(
                            keyword in entry.title for keyword in keywords
                        ):
                            continue

                        # 解析時間
                        try:
                            published_time = datetime(*entry.published_parsed[:6])
                        except BaseException:
                            published_time = datetime.now()

                        # 提取股票代號
                        stock_id = ""
                        stock_id_match = re.search(r"(\d{4,6})", entry.title)
                        if stock_id_match:
                            stock_id = stock_id_match.group(1)

                        news_list.append(
                            {
                                "title": entry.title,
                                "content": entry.get("summary", ""),
                                "source": feed.feed.title,
                                "url": entry.link,
                                "timestamp": published_time,
                                "stock_id": stock_id,
                            }
                        )

                        if len(news_list) >= max_news:
                            break
                except Exception as e:
                    logger.error("使用 RSS 獲取新聞時發生錯誤: %s", e)

        return news_list

    def analyze_sentiment(self, text):
        """
        分析文本情緒

        Args:
            text (str): 要分析的文本

        Returns:
            float: 情緒分數，範圍為 -1 到 1，負數表示負面情緒，正數表示正面情緒
        """
        try:
            if not SNOWNLP_AVAILABLE:
                logger.warning("SnowNLP 未安裝，返回中性情緒分數")
                return 0.0

            # 使用 SnowNLP 進行情緒分析
            # SnowNLP 的情緒分數範圍是 0-1，0 表示負面，1 表示正面
            # 我們將其轉換為 -1 到 1 的範圍
            s = SnowNLP(text)
            sentiment_score = (s.sentiments * 2) - 1
            return sentiment_score
        except Exception as e:
            logger.error(f"分析情緒時發生錯誤: {e}")
            return 0.0  # 返回中性情緒

    def detect_price_spike(self, df, pct_threshold):
        """
        找出日內價格跳動超過閾值的時點

        Args:
            df (pandas.DataFrame): 價格資料，索引為時間戳，列為股票代號
            pct_threshold (float): 價格跳動閾值，例如 0.05 表示 5%

        Returns:
            List[datetime]: 價格跳動超過閾值的時點列表
        """
        if df is None or df.empty:
            return []

        spike_times = []

        try:
            # 計算價格變化百分比
            pct_change = df.pct_change()

            # 找出超過閾值的時點
            for time_idx in pct_change.index[
                1:
            ]:  # 跳過第一個時點，因為它的變化率是 NaN
                # 檢查是否有任何股票在這個時點的價格變化超過閾值
                if (pct_change.loc[time_idx].abs() > pct_threshold).any():
                    spike_times.append(time_idx)
        except Exception as e:
            logger.error(f"檢測價格跳動時發生錯誤: {e}")

        return spike_times


def detect_spikes(df, threshold=3.0, window=20):
    """
    檢測價格或成交量的異常尖峰

    Args:
        df (pandas.DataFrame): 價格或成交量資料，索引為日期，列為股票代號
        threshold (float): 異常閾值，表示標準差的倍數
        window (int): 移動窗口大小

    Returns:
        pandas.DataFrame: 異常尖峰資料，包含股票代號、日期、值、z-score
    """
    if df is None or df.empty:
        return pd.DataFrame()

    # 初始化結果
    spikes = []

    # 對每個股票進行處理
    for col in df.columns:
        series = df[col].dropna()

        if len(series) < window:
            continue

        # 計算移動平均和標準差
        rolling_mean = series.rolling(window=window).mean()
        rolling_std = series.rolling(window=window).std()

        # 計算 z-score
        z_scores = (series - rolling_mean) / rolling_std

        # 找出超過閾值的點
        spike_idx = z_scores[abs(z_scores) > threshold].index

        for idx in spike_idx:
            spikes.append(
                {
                    "stock_id": col,
                    "date": idx,
                    "value": series[idx],
                    "z_score": z_scores[idx],
                }
            )

    # 轉換為 DataFrame
    if spikes:
        return pd.DataFrame(spikes)
    else:
        return pd.DataFrame()


async def start_event_loop(
    callback: Callable, price_df=None, volume_df=None, interval=60
):
    """
    啟動事件監控的異步循環

    Args:
        callback (Callable): 當觸發條件成立時的回調函數，接收 signals 參數
        price_df (pandas.DataFrame, optional): 價格資料
        volume_df (pandas.DataFrame, optional): 成交量資料
        interval (int): 檢查間隔（秒）

    Returns:
        EventMonitor: 事件監控器
    """
    # 創建事件監控器
    monitor = EventMonitor(
        price_df=price_df, volume_df=volume_df, check_interval=interval
    )

    # 啟動監控
    monitor.start()

    # 定義異步監控循環
    async def async_monitor_loop():
        while monitor.running:
            try:
                # 拉取最新新聞
                news_list = monitor.fetch_recent_news()

                # 初始化訊號
                signals = pd.DataFrame()

                # 分析新聞情緒
                for news in news_list:
                    # 結合標題和內容進行情緒分析
                    text = news["title"]
                    if "content" in news and news["content"]:
                        text += " " + news["content"]

                    # 分析情緒
                    sentiment_score = monitor.analyze_sentiment(text)
                    news["sentiment_score"] = sentiment_score

                    # 如果情緒分數低於 -0.7，觸發回調
                    if (
                        sentiment_score < -0.7
                        and "stock_id" in news
                        and news["stock_id"]
                    ):
                        stock_id = news["stock_id"]
                        # 創建事件
                        event = Event(
                            event_type=EventType.NEWS,
                            stock_id=stock_id,
                            content=f"負面新聞: {news['title']} (情緒分數: {sentiment_score:.2f})",
                            source=news.get("source", ""),
                            severity="high",
                        )
                        monitor.events.append(event)
                        monitor._send_notification(event)
                        # robust signals DataFrame 賦值
                        if stock_id not in signals.index:
                            signals.loc[stock_id] = {
                                "sell_signal": 1,
                                "reason": f"負面新聞: {news['title']}",
                            }
                        else:
                            signals.at[stock_id, "sell_signal"] = 1
                            signals.at[stock_id, "reason"] = (
                                f"負面新聞: {news['title']}"
                            )

                # 檢測價格異常跳動
                if monitor.price_df is not None:
                    # 獲取最近的價格數據
                    recent_prices = (
                        monitor.price_df.iloc[-24:]
                        if len(monitor.price_df) > 24
                        else monitor.price_df
                    )

                    # 檢測價格跳動
                    spike_times = monitor.detect_price_spike(
                        recent_prices, monitor.price_threshold
                    )

                    # 如果有價格跳動，觸發回調
                    if spike_times:
                        for time_idx in spike_times:
                            # 找出在這個時點價格變化超過閾值的股票
                            pct_change = recent_prices.pct_change().loc[time_idx]
                            for stock_id, change in pct_change.items():
                                if abs(change) > monitor.price_threshold:
                                    # 創建事件
                                    event = Event(
                                        event_type=EventType.PRICE_ANOMALY,
                                        stock_id=stock_id,
                                        content=f"價格異常跳動: {change:.2%} at {time_idx}",
                                        severity=(
                                            "high"
                                            if abs(change) > monitor.price_threshold * 2
                                            else "medium"
                                        ),
                                    )
                                    monitor.events.append(event)
                                    monitor._send_notification(event)
                                    # robust signals DataFrame 賦值
                                    if change < -monitor.price_threshold:
                                        if stock_id not in signals.index:
                                            signals.loc[stock_id] = {
                                                "sell_signal": 1,
                                                "reason": f"價格大幅下跌: {change:.2%}",
                                            }
                                        else:
                                            signals.at[stock_id, "sell_signal"] = 1
                                            signals.at[stock_id, "reason"] = (
                                                f"價格大幅下跌: {change:.2%}"
                                            )

                # 檢測成交量異常
                if monitor.volume_df is not None:
                    # 獲取最近的成交量數據
                    recent_volumes = (
                        monitor.volume_df.iloc[-24:]
                        if len(monitor.volume_df) > 24
                        else monitor.volume_df
                    )

                    # 檢測成交量異常
                    volume_spikes = detect_spikes(
                        recent_volumes, threshold=monitor.volume_threshold
                    )

                    # 如果有成交量異常，觸發回調
                    if not volume_spikes.empty:
                        for _, row in volume_spikes.iterrows():
                            stock_id = row["stock_id"]
                            z_score = row["z_score"]

                            # 創建事件
                            event = Event(
                                event_type=EventType.VOLUME_ANOMALY,
                                stock_id=stock_id,
                                content=f"成交量異常: z-score = {z_score:.2f}",
                                severity=(
                                    "high"
                                    if abs(z_score) > monitor.volume_threshold * 2
                                    else "medium"
                                ),
                            )
                            monitor.events.append(event)
                            monitor._send_notification(event)

                            # 如果是大幅增加的成交量，可能是拋售訊號
                            if z_score > monitor.volume_threshold * 2:
                                # 檢查價格是否下跌
                                if (
                                    monitor.price_df is not None
                                    and stock_id in monitor.price_df.columns
                                ):
                                    price_change = (
                                        monitor.price_df[stock_id].pct_change().iloc[-1]
                                    )
                                    if price_change < 0:
                                        if stock_id not in signals.index:
                                            signals.loc[stock_id] = {
                                                "sell_signal": 1,
                                                "reason": f"成交量大增且價格下跌: {price_change:.2%}",
                                            }
                                        else:
                                            signals.at[stock_id, "sell_signal"] = 1
                                            signals.at[stock_id, "reason"] = (
                                                f"成交量大增且價格下跌: {price_change:.2%}"
                                            )

                # 如果有訊號，觸發回調
                if not signals.empty and callback is not None:
                    # 添加日期索引
                    signals["date"] = datetime.now()
                    signals.set_index("date", append=True, inplace=True)
                    signals = signals.reorder_levels(["stock_id", "date"])

                    # 調用回調函數
                    await callback(signals)

                # 等待下一次檢查
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"監控循環發生錯誤: {e}")
                await asyncio.sleep(10)

    # 創建並返回異步任務
    loop = asyncio.get_event_loop()
    monitor.async_task = loop.create_task(async_monitor_loop())

    return monitor


def start(callback=None):
    """
    啟動事件監控的主函數

    Args:
        callback (function, optional): 當發現重要事件時的回調函數

    Returns:
        EventMonitor: 事件監控器
    """
    # 創建事件監控器
    monitor = EventMonitor()

    # 定義監控循環
    def monitor_loop():
        """
        監控循環函數

        持續監控新聞和市場事件。
        """
        while monitor.running:
            try:
                # 拉取最新新聞
                news_list = monitor.fetch_recent_news()

                # 分析新聞情緒
                for news in news_list:
                    # 結合標題和內容進行情緒分析
                    text = news["title"]
                    if "content" in news and news["content"]:
                        text += " " + news["content"]

                    # 分析情緒
                    sentiment_score = monitor.analyze_sentiment(text)
                    news["sentiment_score"] = sentiment_score

                    # 如果情緒分數低於 -0.7，觸發回調
                    if sentiment_score < -0.7:
                        event = Event(
                            event_type=EventType.NEWS,
                            stock_id=news.get("stock_id", ""),
                            content=f"負面新聞: {news['title']} (情緒分數: {sentiment_score:.2f})",
                            source=news.get("source", ""),
                            severity="high",
                        )
                        monitor.events.append(event)
                        monitor._send_notification(event)

                        if callback is not None:
                            callback(event)

                # 檢測價格異常跳動
                if monitor.price_df is not None:
                    # 獲取最近的價格數據
                    recent_prices = (
                        monitor.price_df.iloc[-24:]
                        if len(monitor.price_df) > 24
                        else monitor.price_df
                    )

                    # 檢測價格跳動
                    spike_times = monitor.detect_price_spike(
                        recent_prices, monitor.price_threshold
                    )

                    # 如果有價格跳動，觸發回調
                    if spike_times:
                        for time_idx in spike_times:
                            # 找出在這個時點價格變化超過閾值的股票
                            pct_change = recent_prices.pct_change().loc[time_idx]
                            for stock_id, change in pct_change.items():
                                if abs(change) > monitor.price_threshold:
                                    event = Event(
                                        event_type=EventType.PRICE_ANOMALY,
                                        stock_id=stock_id,
                                        content=f"價格異常跳動: {change:.2%} at {time_idx}",
                                        severity=(
                                            "high"
                                            if abs(change) > monitor.price_threshold * 2
                                            else "medium"
                                        ),
                                    )
                                    monitor.events.append(event)
                                    monitor._send_notification(event)

                                    if callback is not None:
                                        callback(event)

                # 等待下一次檢查
                time.sleep(monitor.check_interval)
            except Exception as e:
                logger.error(f"監控循環發生錯誤: {e}")
                time.sleep(10)

    # 設置監控循環
    monitor._monitor_loop = monitor_loop

    # 啟動監控
    monitor.start()

    return monitor


def monitor_memory(threshold_gb=8):
    """
    監控記憶體使用量，超過閾值自動釋放快取並記錄狀態
    """
    if not PSUTIL_AVAILABLE:
        logger.warning("psutil 不可用，跳過記憶體監控")
        return

    process = psutil.Process()
    mem_gb = process.memory_info().rss / (1024**3)
    if mem_gb > threshold_gb:
        gc.collect()
        with open("memory_monitor.log", "a", encoding="utf-8") as f:
            f.write(
                f"[MemoryMonitor] {datetime.datetime.now()} 釋放快取, 當前記憶體: {mem_gb:.2f}GB\n"
            )


# 可在主循環或定時調用 monitor_memory()
