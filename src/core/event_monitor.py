"""
重大新聞與異常監控模組

此模組負責監控市場重大新聞和異常事件，
並在發生重要事件時發出警報，以便及時調整交易策略。

主要功能：
- 新聞監控
- 異常價格監控
- 異常交易量監控
- 事件通知
"""

import time
import pandas as pd
import logging
import threading
import requests
import feedparser
import asyncio
from datetime import datetime, timedelta
from typing import Callable
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from snownlp import SnowNLP
from FinMind.data import DataLoader
import psutil
import gc

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("event_monitor.log"), logging.StreamHandler()],
)
logger = logging.getLogger("event_monitor")


class EventType:
    """事件類型常數"""

    NEWS = "news"
    PRICE_ANOMALY = "price_anomaly"
    VOLUME_ANOMALY = "volume_anomaly"
    MARKET_CRASH = "market_crash"
    MARKET_RALLY = "market_rally"
    EARNINGS_ANNOUNCEMENT = "earnings_announcement"
    DIVIDEND_ANNOUNCEMENT = "dividend_announcement"
    MERGER_ACQUISITION = "merger_acquisition"
    REGULATORY_ANNOUNCEMENT = "regulatory_announcement"


class Event:
    """事件類，用於表示監控到的事件"""

    def __init__(
        self,
        event_type,
        stock_id=None,
        timestamp=None,
        content=None,
        source=None,
        severity=None,
    ):
        """
        初始化事件

        Args:
            event_type (str): 事件類型
            stock_id (str, optional): 股票代號
            timestamp (datetime, optional): 事件時間戳
            content (str, optional): 事件內容
            source (str, optional): 事件來源
            severity (str, optional): 事件嚴重程度
        """
        self.event_type = event_type
        self.stock_id = stock_id
        self.timestamp = timestamp or datetime.now()
        self.content = content
        self.source = source
        self.severity = severity

    def to_dict(self):
        """
        將事件轉換為字典

        Returns:
            dict: 事件字典
        """
        return {
            "event_type": self.event_type,
            "stock_id": self.stock_id,
            "timestamp": self.timestamp,
            "content": self.content,
            "source": self.source,
            "severity": self.severity,
        }

    @classmethod
    def from_dict(cls, event_dict):
        """
        從字典創建事件

        Args:
            event_dict (dict): 事件字典

        Returns:
            Event: 事件物件
        """
        return cls(
            event_type=event_dict["event_type"],
            stock_id=event_dict["stock_id"],
            timestamp=event_dict["timestamp"],
            content=event_dict["content"],
            source=event_dict["source"],
            severity=event_dict["severity"],
        )


class EventMonitor:
    """事件監控類，用於監控各種事件"""

    def __init__(
        self,
        price_df=None,
        volume_df=None,
        news_sources=None,
        price_threshold=0.05,
        volume_threshold=3.0,
        check_interval=60,
        notification_channels=None,
    ):
        """
        初始化事件監控器

        Args:
            price_df (pandas.DataFrame, optional): 價格資料
            volume_df (pandas.DataFrame, optional): 成交量資料
            news_sources (list, optional): 新聞來源列表
            price_threshold (float): 價格異常閾值
            volume_threshold (float): 成交量異常閾值
            check_interval (int): 檢查間隔（秒）
            notification_channels (list, optional): 通知渠道列表
        """
        self.price_df = price_df
        self.volume_df = volume_df
        self.news_sources = news_sources or [
            "https://news.cnyes.com/news/cat/tw_stock",
            "https://www.moneydj.com/kmdj/news/newsreallist.aspx?index=1",
            "https://www.twse.com.tw/zh/news/newsBoard",
        ]
        self.price_threshold = price_threshold
        self.volume_threshold = volume_threshold
        self.check_interval = check_interval
        self.notification_channels = notification_channels or ["log"]

        self.running = False
        self.monitor_thread = None
        self.events = []
        self.last_check_time = datetime.now()
        self.async_task = None

    def start(self):
        """
        啟動監控

        Returns:
            bool: 是否成功啟動
        """
        if self.running:
            logger.warning("監控已經在運行中")
            return False

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

                # 更新最後檢查時間
                self.last_check_time = datetime.now()

                # 等待下一次檢查
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"監控循環發生錯誤: {e}")
                time.sleep(10)

    def _check_price_anomaly(self):
        """檢查價格異常"""
        if self.price_df is None:
            return

        # 獲取最新價格
        latest_prices = self.price_df.iloc[-1]

        # 獲取前一天價格
        previous_prices = self.price_df.iloc[-2] if len(self.price_df) > 1 else None

        if previous_prices is None:
            return

        # 計算價格變化率
        price_changes = (latest_prices - previous_prices) / previous_prices

        # 檢查異常
        for stock_id, change in price_changes.items():
            if abs(change) > self.price_threshold:
                # 創建事件
                event = Event(
                    event_type=EventType.PRICE_ANOMALY,
                    stock_id=stock_id,
                    content=f"價格異常變化: {change:.2%}",
                    severity=(
                        "high" if abs(change) > self.price_threshold * 2 else "medium"
                    ),
                )

                # 添加事件
                self.events.append(event)

                # 發送通知
                self._send_notification(event)

    def _check_volume_anomaly(self):
        """檢查成交量異常"""
        if self.volume_df is None:
            return

        # 獲取最新成交量
        latest_volumes = self.volume_df.iloc[-1]

        # 計算過去 5 天的平均成交量
        avg_volumes = (
            self.volume_df.iloc[-6:-1].mean() if len(self.volume_df) > 5 else None
        )

        if avg_volumes is None:
            return

        # 計算成交量變化率
        volume_changes = latest_volumes / avg_volumes

        # 檢查異常
        for stock_id, change in volume_changes.items():
            if change > self.volume_threshold:
                # 創建事件
                event = Event(
                    event_type=EventType.VOLUME_ANOMALY,
                    stock_id=stock_id,
                    content=f"成交量異常變化: {change:.2f}倍",
                    severity="high" if change > self.volume_threshold * 2 else "medium",
                )

                # 添加事件
                self.events.append(event)

                # 發送通知
                self._send_notification(event)

    def _check_news(self):
        """檢查新聞"""
        for source in self.news_sources:
            try:
                # 獲取新聞
                news_list = self._fetch_news(source)

                # 檢查新聞
                for news in news_list:
                    # 檢查是否為重要新聞
                    if self._is_important_news(news):
                        # 創建事件
                        event = Event(
                            event_type=EventType.NEWS,
                            stock_id=news.get("stock_id"),
                            content=news.get("title"),
                            source=source,
                            severity=news.get("severity", "medium"),
                        )

                        # 添加事件
                        self.events.append(event)

                        # 發送通知
                        self._send_notification(event)
            except Exception as e:
                logger.error(f"獲取新聞時發生錯誤: {e}")

    def _fetch_news(self, source):
        """
        獲取新聞

        Args:
            source (str): 新聞來源

        Returns:
            list: 新聞列表
        """
        # 這裡簡化了新聞獲取的邏輯，實際實現可能需要更複雜的爬蟲
        try:
            response = requests.get(source, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(response.text, "html.parser")

            # 根據不同的新聞來源，使用不同的解析邏輯
            if "cnyes.com" in source:
                return self._parse_cnyes_news(soup)
            elif "moneydj.com" in source:
                return self._parse_moneydj_news(soup)
            elif "twse.com.tw" in source:
                return self._parse_twse_news(soup)
            else:
                return []
        except Exception as e:
            logger.error(f"獲取新聞時發生錯誤: {e}")
            return []

    def _parse_cnyes_news(self, soup):
        """
        解析鉅亨網新聞

        Args:
            soup (BeautifulSoup): BeautifulSoup 物件

        Returns:
            list: 新聞列表
        """
        news_list = []

        # 獲取新聞列表
        news_items = soup.select("div._2bFl")

        for item in news_items:
            try:
                # 獲取標題
                title_elem = item.select_one("a")
                if not title_elem:
                    continue

                title = title_elem.text.strip()
                url = (
                    "https://news.cnyes.com" + title_elem["href"]
                    if title_elem.has_attr("href")
                    else ""
                )

                # 獲取時間
                time_elem = item.select_one("time")
                timestamp = datetime.now()
                if time_elem and time_elem.has_attr("datetime"):
                    timestamp = datetime.fromisoformat(time_elem["datetime"])

                # 創建新聞
                news = {
                    "title": title,
                    "url": url,
                    "timestamp": timestamp,
                    "source": "鉅亨網",
                }

                news_list.append(news)
            except Exception as e:
                logger.error(f"解析鉅亨網新聞時發生錯誤: {e}")

        return news_list

    def _parse_moneydj_news(self, soup):
        """
        解析 MoneyDJ 新聞

        Args:
            soup (BeautifulSoup): BeautifulSoup 物件

        Returns:
            list: 新聞列表
        """
        news_list = []

        # 獲取新聞列表
        news_items = soup.select("table.forumtable tr")

        for item in news_items[1:]:  # 跳過表頭
            try:
                # 獲取標題
                title_elem = item.select_one("td:nth-child(3) a")
                if not title_elem:
                    continue

                title = title_elem.text.strip()
                url = (
                    "https://www.moneydj.com" + title_elem["href"]
                    if title_elem.has_attr("href")
                    else ""
                )

                # 獲取時間
                time_elem = item.select_one("td:nth-child(4)")
                timestamp = datetime.now()
                if time_elem:
                    try:
                        timestamp = datetime.strptime(
                            time_elem.text.strip(), "%Y-%m-%d %H:%M:%S"
                        )
                    except BaseException:
                        pass

                # 創建新聞
                news = {
                    "title": title,
                    "url": url,
                    "timestamp": timestamp,
                    "source": "MoneyDJ",
                }

                news_list.append(news)
            except Exception as e:
                logger.error(f"解析 MoneyDJ 新聞時發生錯誤: {e}")

        return news_list

    def _parse_twse_news(self, soup):
        """
        解析證交所新聞

        Args:
            soup (BeautifulSoup): BeautifulSoup 物件

        Returns:
            list: 新聞列表
        """
        news_list = []

        # 獲取新聞列表
        news_items = soup.select("table.grid tr")

        for item in news_items[1:]:  # 跳過表頭
            try:
                # 獲取標題
                title_elem = item.select_one("td:nth-child(2) a")
                if not title_elem:
                    continue

                title = title_elem.text.strip()
                url = (
                    "https://www.twse.com.tw" + title_elem["href"]
                    if title_elem.has_attr("href")
                    else ""
                )

                # 獲取時間
                time_elem = item.select_one("td:nth-child(3)")
                timestamp = datetime.now()
                if time_elem:
                    try:
                        timestamp = datetime.strptime(
                            time_elem.text.strip(), "%Y/%m/%d"
                        )
                    except BaseException:
                        pass

                # 創建新聞
                news = {
                    "title": title,
                    "url": url,
                    "timestamp": timestamp,
                    "source": "證交所",
                }

                news_list.append(news)
            except Exception as e:
                logger.error(f"解析證交所新聞時發生錯誤: {e}")

        return news_list

    def _is_important_news(self, news):
        """
        判斷是否為重要新聞

        Args:
            news (dict): 新聞

        Returns:
            bool: 是否為重要新聞
        """
        # 檢查新聞標題是否包含關鍵字
        important_keywords = [
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

        title = news.get("title", "")

        for keyword in important_keywords:
            if keyword in title:
                # 設定新聞嚴重程度
                if any(
                    k in title
                    for k in [
                        "重大",
                        "緊急",
                        "立即",
                        "破產",
                        "接管",
                        "停牌",
                        "下市",
                        "下櫃",
                    ]
                ):
                    news["severity"] = "high"
                else:
                    news["severity"] = "medium"

                # 嘗試從標題中提取股票代號
                import re

                stock_id_match = re.search(r"(\d{4,6})", title)
                if stock_id_match:
                    news["stock_id"] = stock_id_match.group(1)

                return True

        return False

    def _send_notification(self, event):
        """
        發送通知

        Args:
            event (Event): 事件
        """
        # 根據不同的通知渠道發送通知
        for channel in self.notification_channels:
            if channel == "log":
                # 記錄到日誌
                logger.info(
                    f"事件: {event.event_type}, 股票: {event.stock_id}, 內容: {event.content}, 嚴重程度: {event.severity}"
                )
            elif channel == "email":
                # 發送電子郵件
                self._send_email(event)
            elif channel == "line":
                # 發送 Line 通知
                self._send_line(event)
            elif channel == "telegram":
                # 發送 Telegram 通知
                self._send_telegram(event)

    def _send_email(self, event):
        """
        發送電子郵件通知

        Args:
            event (Event): 事件
        """
        # 這裡簡化了電子郵件發送的邏輯，實際實現可能需要更複雜的郵件發送功能
        logger.info(
            f"發送電子郵件通知: {event.event_type}, {event.stock_id}, {event.content}"
        )

    def _send_line(self, event):
        """
        發送 Line 通知

        Args:
            event (Event): 事件
        """
        # 這裡簡化了 Line 通知發送的邏輯，實際實現可能需要使用 Line Notify API
        logger.info(
            f"發送 Line 通知: {event.event_type}, {event.stock_id}, {event.content}"
        )

    def _send_telegram(self, event):
        """
        發送 Telegram 通知

        Args:
            event (Event): 事件
        """
        # 這裡簡化了 Telegram 通知發送的邏輯，實際實現可能需要使用 Telegram Bot API
        logger.info(
            f"發送 Telegram 通知: {event.event_type}, {event.stock_id}, {event.content}"
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
            logger.error(f"使用 FinMind 獲取新聞時發生錯誤: {e}")

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
                        import re

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
                    logger.error(f"使用 RSS 獲取新聞時發生錯誤: {e}")

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
    process = psutil.Process()
    mem_gb = process.memory_info().rss / (1024**3)
    if mem_gb > threshold_gb:
        gc.collect()
        with open("memory_monitor.log", "a", encoding="utf-8") as f:
            f.write(
                f"[MemoryMonitor] {datetime.datetime.now()} 釋放快取, 當前記憶體: {mem_gb:.2f}GB\n"
            )


# 可在主循環或定時調用 monitor_memory()
