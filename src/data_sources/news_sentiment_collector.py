"""新聞情緒收集器模組

此模組提供收集新聞和情緒分析資料的功能，包括：
- 新聞資料收集
- 情緒分析
- 資料驗證與儲存

支援從多個新聞來源收集資料，並使用 NLP 模型進行情緒分析。
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

try:
    from src.config import DB_PATH
except ImportError:
    DB_PATH = "data/trading.db"

try:
    from src.data_sources.data_collector import DataCollector, RetryStrategy
except ImportError:
    # 如果無法導入，提供基本實現
    class DataCollector:
        def __init__(self, **kwargs):
            del kwargs  # 避免未使用參數警告

    class RetryStrategy:
        def __init__(self, **kwargs):
            del kwargs  # 避免未使用參數警告


try:
    from src.data_sources.mcp_crawler import McpCrawler
except ImportError:
    McpCrawler = None

try:
    from src.database.schema import NewsSentiment
except ImportError:
    NewsSentiment = None

# 設定日誌
logger = logging.getLogger(__name__)


class NewsSentimentCollector(DataCollector):
    """新聞情緒收集器

    負責收集新聞資料並進行情緒分析，支援多來源資料整合。
    """

    def __init__(
        self,
        source: str = "mcp",
        use_cache: bool = True,
        cache_expiry_days: int = 1,
        *,
        retry_strategy: Optional[RetryStrategy] = None,
        sentiment_model: str = "simple",  # 可選 'simple', 'nltk', 'transformers'
    ):
        """初始化新聞情緒收集器

        Args:
            source: 資料來源，預設為 'mcp'
            use_cache: 是否使用快取
            cache_expiry_days: 快取過期天數
            retry_strategy: 重試策略
            sentiment_model: 情緒分析模型
        """
        super().__init__(
            name=f"NewsSentimentCollector_{source}",
            source=source,
            use_cache=use_cache,
            cache_expiry_days=cache_expiry_days,
            retry_strategy=retry_strategy,
        )

        self.sentiment_model = sentiment_model

        # 初始化資料適配器
        if source == "mcp":
            try:
                self.crawler = McpCrawler()
            except NameError:
                logger.warning("McpCrawler 未定義，使用模擬爬蟲")
                self.crawler = self._create_mock_crawler()
        else:
            logger.warning(f"不支援的資料來源: {source}，使用模擬爬蟲")
            self.crawler = self._create_mock_crawler()

        # 初始化資料庫連接
        self.engine = create_engine(f"sqlite:///{DB_PATH}")
        self.Session = sessionmaker(bind=self.engine)

    def _create_mock_crawler(self):
        """創建模擬爬蟲"""
        class MockCrawler:
            def __init__(self):
                self.name = "MockCrawler"

            def get_news(self, *args, **kwargs):
                """模擬獲取新聞"""
                return []

            def is_available(self):
                """檢查可用性"""
                return True

        return MockCrawler()

        # 初始化情緒分析模型
        self._init_sentiment_model()

    def _init_sentiment_model(self):
        """初始化情緒分析模型"""
        if self.sentiment_model == "simple":
            # 簡單的基於關鍵字的情緒分析
            self.positive_keywords = [
                "漲",
                "上漲",
                "成長",
                "獲利",
                "盈餘",
                "增加",
                "看好",
                "利多",
                "突破",
                "創新高",
                "強勢",
                "買進",
                "推薦",
                "看漲",
                "樂觀",
            ]
            self.negative_keywords = [
                "跌",
                "下跌",
                "衰退",
                "虧損",
                "虧損",
                "減少",
                "看壞",
                "利空",
                "跌破",
                "創新低",
                "弱勢",
                "賣出",
                "不推薦",
                "看跌",
                "悲觀",
            ]
        elif self.sentiment_model == "nltk":
            # 使用 NLTK 進行情緒分析
            try:
                import nltk
                from nltk.sentiment import SentimentIntensityAnalyzer

                # 下載必要的資源
                nltk.download("vader_lexicon", quiet=True)

                # 初始化分析器
                self.sentiment_analyzer = SentimentIntensityAnalyzer()
            except ImportError:
                logger.error("無法載入 NLTK，請安裝: pip install nltk")
                self.sentiment_model = "simple"
                self._init_sentiment_model()
        elif self.sentiment_model == "transformers":
            # 使用 Transformers 進行情緒分析
            try:
                from transformers import pipeline

                # 初始化情緒分析管道
                self.sentiment_analyzer = pipeline("sentiment-analysis")
            except ImportError:
                logger.error("無法載入 Transformers，請安裝: pip install transformers")
                self.sentiment_model = "simple"
                self._init_sentiment_model()
        else:
            logger.warning(
                "不支援的情緒分析模型: %s，使用簡單模型", self.sentiment_model
            )
            self.sentiment_model = "simple"
            self._init_sentiment_model()

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """分析文本情緒

        Args:
            text: 要分析的文本

        Returns:
            Dict[str, Any]: 情緒分析結果，包含 sentiment_score, sentiment_label
        """
        if self.sentiment_model == "simple":
            return self._analyze_simple_sentiment(text)
        if self.sentiment_model == "nltk":
            return self._analyze_nltk_sentiment(text)
        if self.sentiment_model == "transformers":
            return self._analyze_transformers_sentiment(text)

        logger.error("不支援的情緒分析模型: %s", self.sentiment_model)
        return self._get_neutral_result()

    def _analyze_simple_sentiment(self, text: str) -> Dict[str, Any]:
        """使用簡單關鍵字方法分析情緒"""
        positive_count = sum(1 for keyword in self.positive_keywords if keyword in text)
        negative_count = sum(1 for keyword in self.negative_keywords if keyword in text)

        total = positive_count + negative_count
        if not total:
            sentiment_score = 0.0
        else:
            sentiment_score = (positive_count - negative_count) / total

        if sentiment_score > 0.1:
            sentiment_label = "positive"
        elif sentiment_score < -0.1:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"

        return {
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": 1 if not total else 0,
        }

    def _analyze_nltk_sentiment(self, text: str) -> Dict[str, Any]:
        """使用 NLTK 分析情緒"""
        scores = self.sentiment_analyzer.polarity_scores(text)

        sentiment_score = scores["compound"]
        if sentiment_score >= 0.05:
            sentiment_label = "positive"
        elif sentiment_score <= -0.05:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"

        return {
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "positive_count": 1 if sentiment_label == "positive" else 0,
            "negative_count": 1 if sentiment_label == "negative" else 0,
            "neutral_count": 1 if sentiment_label == "neutral" else 0,
        }

    def _analyze_transformers_sentiment(self, text: str) -> Dict[str, Any]:
        """使用 Transformers 分析情緒"""
        result = self.sentiment_analyzer(text)[0]

        label = result["label"].lower()
        score = result["score"]

        if "positive" in label:
            sentiment_score = score
            sentiment_label = "positive"
        elif "negative" in label:
            sentiment_score = -score
            sentiment_label = "negative"
        else:
            sentiment_score = 0.0
            sentiment_label = "neutral"

        return {
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "positive_count": 1 if sentiment_label == "positive" else 0,
            "negative_count": 1 if sentiment_label == "negative" else 0,
            "neutral_count": 1 if sentiment_label == "neutral" else 0,
        }

    def _get_neutral_result(self) -> Dict[str, Any]:
        """獲取中性情緒結果"""
        return {
            "sentiment_score": 0.0,
            "sentiment_label": "neutral",
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 1,
        }

    def collect_news(
        self,
        symbols: List[str],
        days: int = 1,
        save_to_db: bool = True,
        max_workers: int = 5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """收集新聞資料

        Args:
            symbols: 股票代碼列表
            days: 收集的天數
            save_to_db: 是否儲存到資料庫
            max_workers: 最大工作執行緒數

        Returns:
            Dict[str, List[Dict[str, Any]]]: 股票代碼到新聞列表的映射
        """
        logger.info("開始收集 %d 檔股票的新聞資料", len(symbols))

        results = {}

        # 使用執行緒池並行獲取資料
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任務
            future_to_symbol = {
                executor.submit(
                    self._collect_news_for_symbol,
                    symbol,
                    days,
                ): symbol
                for symbol in symbols
            }

            # 獲取結果
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                try:
                    news_list = future.result()
                    if news_list:
                        results[symbol] = news_list
                        logger.info(
                            "成功收集 %s 的新聞資料，共 %d 筆", symbol, len(news_list)
                        )

                        # 儲存到資料庫
                        if save_to_db:
                            self._save_news_to_db(symbol, news_list)
                    else:
                        logger.warning("收集 %s 的新聞資料為空", symbol)
                except Exception as e:
                    logger.error("收集 %s 的新聞資料時發生錯誤: %s", symbol, e)

        logger.info("完成收集新聞資料，成功收集 %d 檔股票", len(results))
        return results

    def _collect_news_for_symbol(self, symbol: str, days: int) -> List[Dict[str, Any]]:
        """收集單一股票的新聞資料

        Args:
            symbol: 股票代碼
            days: 收集的天數

        Returns:
            List[Dict[str, Any]]: 新聞列表
        """
        # 檢查快取
        today = datetime.now().date()
        start_date = (today - timedelta(days=days)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        cache_path = self._get_cache_path("news", symbol, start_date, end_date)

        if self.use_cache and self._is_cache_valid(cache_path):
            logger.info("從快取讀取 %s 的新聞資料", symbol)
            return pd.read_json(cache_path).to_dict("records")

        # 從資料來源獲取資料
        if self.source == "mcp":
            try:
                # 使用 MCP 爬蟲獲取新聞
                news_list = self.crawler.get_stock_news(symbol, days=days)

                # 進行情緒分析
                for news in news_list:
                    if "content" in news:
                        sentiment = self.analyze_sentiment(news["content"])
                        news.update(sentiment)

                # 儲存到快取
                if self.use_cache and news_list:
                    pd.DataFrame(news_list).to_json(cache_path, orient="records")

                return news_list
            except Exception as e:
                logger.error("從 MCP 獲取 %s 的新聞資料時發生錯誤: %s", symbol, e)
                return []
        else:
            raise ValueError(f"不支援的資料來源: {self.source}")

    def _save_news_to_db(self, symbol: str, news_list: List[Dict[str, Any]]) -> None:
        """將新聞資料儲存到資料庫

        Args:
            symbol: 股票代碼
            news_list: 新聞列表
        """
        if not news_list:
            return

        session = self.Session()
        try:
            # 按日期分組
            news_by_date = {}
            for news in news_list:
                if isinstance(news["date"], str):
                    news_date = datetime.strptime(news["date"], "%Y-%m-%d").date()
                else:
                    news_date = news["date"]
                if news_date not in news_by_date:
                    news_by_date[news_date] = []
                news_by_date[news_date].append(news)

            # 處理每一天的新聞
            for news_date, daily_news in news_by_date.items():
                # 計算情緒統計
                sentiment_scores = [
                    news.get("sentiment_score", 0)
                    for news in daily_news
                    if "sentiment_score" in news
                ]
                positive_count = sum(
                    news.get("positive_count", 0)
                    for news in daily_news
                    if "positive_count" in news
                )
                negative_count = sum(
                    news.get("negative_count", 0)
                    for news in daily_news
                    if "negative_count" in news
                )
                neutral_count = sum(
                    news.get("neutral_count", 0)
                    for news in daily_news
                    if "neutral_count" in news
                )

                # 計算平均情緒分數
                if sentiment_scores:
                    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
                else:
                    avg_sentiment = 0

                # 生成新聞摘要
                news_summary = "\n".join(
                    [
                        f"{i+1}. {news.get('title', 'No Title')}"
                        for i, news in enumerate(daily_news[:5])
                    ]
                )

                # 生成新聞來源列表
                news_sources = [
                    {"title": news.get("title", "No Title"), "url": news.get("url", "")}
                    for news in daily_news
                ]

                # 檢查是否已存在相同的記錄
                existing = (
                    session.query(NewsSentiment)
                    .filter(
                        NewsSentiment.symbol == symbol,
                        NewsSentiment.date == news_date,
                    )
                    .first()
                )

                if existing:
                    # 更新現有記錄
                    existing.sentiment_score = avg_sentiment
                    existing.positive_count = positive_count
                    existing.negative_count = negative_count
                    existing.neutral_count = neutral_count
                    existing.news_summary = news_summary
                    existing.news_sources = news_sources
                    existing.updated_at = datetime.now()
                else:
                    # 創建新記錄
                    sentiment = NewsSentiment(
                        symbol=symbol,
                        date=news_date,
                        sentiment_score=avg_sentiment,
                        positive_count=positive_count,
                        negative_count=negative_count,
                        neutral_count=neutral_count,
                        news_summary=news_summary,
                        news_sources=news_sources,
                    )
                    session.add(sentiment)

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error("儲存 %s 的新聞資料到資料庫時發生錯誤: %s", symbol, e)
        finally:
            session.close()

    def collect(
        self, symbols: List[str], days: int = 1, **kwargs
    ) -> Dict[str, List[Dict[str, Any]]]:
        """收集資料的實現方法

        Args:
            symbols: 股票代碼列表
            days: 收集的天數
            **kwargs: 其他參數，將傳遞給對應的收集方法

        Returns:
            Dict[str, List[Dict[str, Any]]]: 收集的資料
        """
        return self.collect_news(symbols, days, **kwargs)
