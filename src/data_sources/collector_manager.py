"""收集器管理模組

此模組負責管理各種資料收集器的初始化、啟動和停止，包括：
- 收集器初始化
- 排程設定
- 狀態管理

Example:
    >>> manager = CollectorManager(config)
    >>> manager.initialize_collectors()
    >>> manager.start_all()
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.data_sources.financial_statement_collector import FinancialStatementCollector
from src.data_sources.market_data_collector import MarketDataCollector
from src.data_sources.news_sentiment_collector import NewsSentimentCollector
from src.data_sources.realtime_quote_collector import RealtimeQuoteCollector

logger = logging.getLogger(__name__)


class CollectorManager:
    """收集器管理器
    
    負責管理所有資料收集器的生命週期。
    """

    def __init__(self, config: Dict[str, Any], symbols: List[str]):
        """初始化收集器管理器

        Args:
            config: 配置字典
            symbols: 股票代碼列表
        """
        self.config = config
        self.symbols = symbols
        self.collectors = {}
        self.running = False

        # 從 UnifiedDataManager 遷移：性能統計和智能選擇
        self.source_performance = {}
        self._init_performance_tracking()

    def initialize_collectors(self) -> None:
        """初始化所有收集器"""
        self._init_market_data_collector()
        self._init_realtime_quote_collector()
        self._init_financial_statement_collector()
        self._init_news_sentiment_collector()

    def _init_market_data_collector(self) -> None:
        """初始化市場資料收集器"""
        market_config = self.config["collectors"]["market_data"]
        if market_config["enabled"]:
            self.collectors["market_data"] = MarketDataCollector(
                source=market_config["source"],
                use_cache=market_config["use_cache"],
                cache_expiry_days=market_config["cache_expiry_days"],
            )
            logger.info("已初始化市場資料收集器: %s", market_config["source"])

    def _init_realtime_quote_collector(self) -> None:
        """初始化即時報價收集器"""
        realtime_config = self.config["collectors"]["realtime_quote"]
        if realtime_config["enabled"]:
            self.collectors["realtime_quote"] = RealtimeQuoteCollector(
                source=realtime_config["source"],
            )
            logger.info("已初始化即時報價收集器: %s", realtime_config["source"])

    def _init_financial_statement_collector(self) -> None:
        """初始化財務報表收集器"""
        financial_config = self.config["collectors"]["financial_statement"]
        if financial_config["enabled"]:
            self.collectors["financial_statement"] = FinancialStatementCollector(
                source=financial_config["source"],
                use_cache=financial_config["use_cache"],
                cache_expiry_days=financial_config["cache_expiry_days"],
            )
            logger.info("已初始化財務報表收集器: %s", financial_config["source"])

    def _init_news_sentiment_collector(self) -> None:
        """初始化新聞情緒收集器"""
        news_config = self.config["collectors"]["news_sentiment"]
        if news_config["enabled"]:
            self.collectors["news_sentiment"] = NewsSentimentCollector(
                source=news_config["source"],
                use_cache=news_config["use_cache"],
                cache_expiry_days=news_config["cache_expiry_days"],
                sentiment_model=news_config["sentiment_model"],
            )
            logger.info("已初始化新聞情緒收集器: %s", news_config["source"])

    def setup_schedules(self) -> None:
        """設定所有收集器的排程"""
        self._setup_market_data_schedule()
        self._setup_financial_statement_schedule()
        self._setup_news_sentiment_schedule()

    def _setup_market_data_schedule(self) -> None:
        """設定市場資料收集器排程"""
        if "market_data" not in self.collectors:
            return

        market_config = self.config["collectors"]["market_data"]
        collector = self.collectors["market_data"]

        # 設定日線資料收集排程
        if "daily" in market_config["schedule"]:
            time_str = market_config["schedule"]["daily"]
            collector.schedule_daily(time_str, self.symbols, data_type="daily")
            logger.info("已設定市場日線資料收集排程: 每日 %s", time_str)

        # 設定分鐘資料收集排程
        minute_schedule = market_config["schedule"].get("minute", {})
        if minute_schedule.get("enabled", False):
            interval = minute_schedule["interval"]
            minute_symbols = minute_schedule.get("symbols", self.symbols)
            collector.schedule_interval(
                interval, "minutes", minute_symbols,
                data_type="minute", interval="1m"
            )
            logger.info("已設定市場分鐘資料收集排程: 每 %d 分鐘", interval)

    def _setup_financial_statement_schedule(self) -> None:
        """設定財務報表收集器排程"""
        if "financial_statement" not in self.collectors:
            return

        financial_config = self.config["collectors"]["financial_statement"]
        collector = self.collectors["financial_statement"]

        # 設定財務報表收集排程
        if "daily" in financial_config["schedule"]:
            time_str = financial_config["schedule"]["daily"]
            collector.schedule_daily(
                time_str, self.symbols, data_type="company_info"
            )
            logger.info("已設定財務報表收集排程: 每日 %s", time_str)

    def _setup_news_sentiment_schedule(self) -> None:
        """設定新聞情緒收集器排程"""
        if "news_sentiment" not in self.collectors:
            return

        news_config = self.config["collectors"]["news_sentiment"]
        collector = self.collectors["news_sentiment"]

        # 設定新聞情緒收集排程
        if "daily" in news_config["schedule"]:
            time_str = news_config["schedule"]["daily"]
            collector.schedule_daily(time_str, self.symbols, days=1)
            logger.info("已設定新聞情緒收集排程: 每日 %s", time_str)

    def start_all(self) -> None:
        """啟動所有收集器"""
        if self.running:
            logger.warning("收集器管理器已在運行中")
            return

        self.running = True
        logger.info("啟動所有收集器")

        # 啟動所有收集器的排程器
        for name, collector in self.collectors.items():
            if hasattr(collector, "start_scheduler"):
                collector.start_scheduler()
                logger.info("已啟動 %s 收集器的排程器", name)

        # 啟動即時報價收集器
        self._start_realtime_quote_collector()

    def _start_realtime_quote_collector(self) -> None:
        """啟動即時報價收集器"""
        if "realtime_quote" not in self.collectors:
            return

        realtime_config = self.config["collectors"]["realtime_quote"]
        realtime_symbols = realtime_config.get("symbols", self.symbols)
        self.collectors["realtime_quote"].start()
        self.collectors["realtime_quote"].collect(realtime_symbols)
        logger.info("已啟動即時報價收集器，訂閱 %d 檔股票", len(realtime_symbols))

    def stop_all(self) -> None:
        """停止所有收集器"""
        if not self.running:
            logger.warning("收集器管理器未在運行中")
            return

        self.running = False
        logger.info("停止所有收集器")

        # 停止所有收集器的排程器
        for name, collector in self.collectors.items():
            if hasattr(collector, "stop_scheduler"):
                collector.stop_scheduler()
                logger.info("已停止 %s 收集器的排程器", name)

        # 停止即時報價收集器
        if "realtime_quote" in self.collectors:
            self.collectors["realtime_quote"].stop()
            logger.info("已停止即時報價收集器")

    def get_status(self) -> Dict[str, Any]:
        """獲取所有收集器狀態
        
        Returns:
            Dict[str, Any]: 收集器狀態字典
        """
        status = {
            "running": self.running,
            "collectors": {},
            "symbols": self.symbols,
            "symbol_count": len(self.symbols),
        }

        # 收集各收集器狀態
        for name, collector in self.collectors.items():
            collector_status = {
                "last_run_time": getattr(collector, "last_run_time", None),
                "last_run_status": getattr(collector, "last_run_status", None),
                "error_count": getattr(collector, "error_count", 0),
                "success_count": getattr(collector, "success_count", 0),
            }
            status["collectors"][name] = collector_status

        # 添加性能統計
        status["performance"] = self.source_performance
        return status

    def _init_performance_tracking(self) -> None:
        """初始化性能追蹤

        從 UnifiedDataManager 遷移的功能，用於追蹤各收集器的性能。
        """
        collector_types = ["market_data", "realtime_quote", "financial_statement", "news_sentiment"]
        for collector_type in collector_types:
            self.source_performance[collector_type] = {
                "success": 0,
                "failure": 0,
                "avg_time": 0.0,
                "last_success": None,
                "last_failure": None,
            }

    def update_performance_stats(self, collector_name: str, success: bool, execution_time: float) -> None:
        """更新收集器性能統計

        從 UnifiedDataManager 遷移的功能。

        Args:
            collector_name: 收集器名稱
            success: 是否成功
            execution_time: 執行時間（秒）
        """
        if collector_name not in self.source_performance:
            self.source_performance[collector_name] = {
                "success": 0,
                "failure": 0,
                "avg_time": 0.0,
                "last_success": None,
                "last_failure": None,
            }

        stats = self.source_performance[collector_name]

        if success:
            stats["success"] += 1
            stats["last_success"] = datetime.now()
            # 更新平均執行時間
            total_success = stats["success"]
            stats["avg_time"] = ((stats["avg_time"] * (total_success - 1)) + execution_time) / total_success
        else:
            stats["failure"] += 1
            stats["last_failure"] = datetime.now()

        logger.debug("更新 %s 性能統計: 成功=%d, 失敗=%d, 平均時間=%.2fs",
                     collector_name, stats["success"], stats["failure"], stats["avg_time"])

    def get_best_collector(self, data_type: str) -> Optional[str]:
        """根據性能統計選擇最佳收集器

        從 UnifiedDataManager 遷移的智能選擇功能。

        Args:
            data_type: 資料類型

        Returns:
            Optional[str]: 最佳收集器名稱，如果沒有可用收集器則返回 None
        """
        # 根據資料類型映射到收集器
        type_mapping = {
            "price": ["market_data"],
            "realtime": ["realtime_quote"],
            "fundamental": ["financial_statement"],
            "news": ["news_sentiment"],
        }

        available_collectors = type_mapping.get(data_type, list(self.collectors.keys()))

        # 過濾出實際存在且啟用的收集器
        valid_collectors = [
            name for name in available_collectors
            if name in self.collectors and name in self.source_performance
        ]

        if not valid_collectors:
            return None

        # 計算每個收集器的評分
        best_collector = None
        best_score = -1

        for collector_name in valid_collectors:
            score = self._calculate_collector_score(collector_name)
            if score > best_score:
                best_score = score
                best_collector = collector_name

        logger.debug("為資料類型 %s 選擇最佳收集器: %s (評分: %.2f)",
                     data_type, best_collector, best_score)
        return best_collector

    def _calculate_collector_score(self, collector_name: str) -> float:
        """計算收集器評分

        從 UnifiedDataManager 遷移的評分算法。

        Args:
            collector_name: 收集器名稱

        Returns:
            float: 收集器評分（0-1之間，越高越好）
        """
        stats = self.source_performance.get(collector_name, {})

        success_count = stats.get("success", 0)
        failure_count = stats.get("failure", 0)
        avg_time = stats.get("avg_time", 0.0)

        total_requests = success_count + failure_count
        if total_requests == 0:
            return 0.5  # 沒有歷史記錄，給予中等評分

        # 成功率權重 (70%)
        success_rate = success_count / total_requests
        success_score = success_rate * 0.7

        # 速度權重 (30%) - 越快越好，但設定上限避免除零
        speed_score = 0.3
        if avg_time > 0:
            # 假設理想執行時間為1秒，超過則扣分
            speed_score = min(0.3, 0.3 * (1.0 / max(avg_time, 0.1)))

        total_score = success_score + speed_score

        logger.debug("收集器 %s 評分: 成功率=%.2f, 速度=%.2f, 總分=%.2f",
                     collector_name, success_score, speed_score, total_score)

        return total_score
