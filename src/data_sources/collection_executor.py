"""資料收集執行器模組

此模組負責執行實際的資料收集任務，包括：
- 立即收集所有資料
- 分別收集不同類型的資料
- 錯誤處理和日誌記錄

Example:
    >>> executor = CollectionExecutor(config, collectors, symbols)
    >>> executor.collect_all_data()
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class CollectionExecutor:
    """資料收集執行器
    
    負責執行各種資料收集任務。
    """

    def __init__(
        self,
        config: Dict[str, Any],
        collectors: Dict[str, Any],
        symbols: List[str]
    ):
        """初始化資料收集執行器
        
        Args:
            config: 配置字典
            collectors: 收集器字典
            symbols: 股票代碼列表
        """
        self.config = config
        self.collectors = collectors
        self.symbols = symbols

    def collect_all_data(self) -> None:
        """立即收集所有資料"""
        logger.info("開始收集所有資料")

        self._collect_market_data()
        self._collect_financial_statement_data()
        self._collect_news_sentiment_data()

        logger.info("所有資料收集任務已觸發")

    def _collect_market_data(self) -> None:
        """收集市場資料"""
        if "market_data" not in self.collectors:
            return

        logger.info("開始收集市場資料")
        try:
            # 收集日線資料
            self.collectors["market_data"].trigger_now(
                self.symbols, data_type="daily"
            )
            logger.info("已觸發市場日線資料收集")

            # 檢查是否需要收集分鐘資料
            self._collect_minute_data_if_needed()

        except Exception as e:
            logger.error("收集市場資料時發生錯誤: %s", e)

    def _collect_minute_data_if_needed(self) -> None:
        """如果需要則收集分鐘資料"""
        market_config = self.config["collectors"]["market_data"]
        minute_schedule = market_config["schedule"].get("minute", {})
        
        if minute_schedule.get("enabled", False):
            minute_symbols = minute_schedule.get("symbols", self.symbols)
            self.collectors["market_data"].trigger_now(
                minute_symbols, data_type="minute", interval="1m"
            )
            logger.info("已觸發市場分鐘資料收集")

    def _collect_financial_statement_data(self) -> None:
        """收集財務報表資料"""
        if "financial_statement" not in self.collectors:
            return

        logger.info("開始收集財務報表資料")
        try:
            self.collectors["financial_statement"].trigger_now(
                self.symbols, data_type="company_info"
            )
            logger.info("已觸發財務報表資料收集")
        except Exception as e:
            logger.error("收集財務報表資料時發生錯誤: %s", e)

    def _collect_news_sentiment_data(self) -> None:
        """收集新聞情緒資料"""
        if "news_sentiment" not in self.collectors:
            return

        logger.info("開始收集新聞情緒資料")
        try:
            self.collectors["news_sentiment"].trigger_now(self.symbols, days=1)
            logger.info("已觸發新聞情緒資料收集")
        except Exception as e:
            logger.error("收集新聞情緒資料時發生錯誤: %s", e)

    def collect_market_data_only(self) -> None:
        """僅收集市場資料"""
        logger.info("開始收集市場資料")
        self._collect_market_data()

    def collect_financial_data_only(self) -> None:
        """僅收集財務資料"""
        logger.info("開始收集財務資料")
        self._collect_financial_statement_data()

    def collect_news_data_only(self) -> None:
        """僅收集新聞資料"""
        logger.info("開始收集新聞資料")
        self._collect_news_sentiment_data()

    def collect_by_symbol(self, symbol: str) -> None:
        """收集特定股票的所有資料
        
        Args:
            symbol: 股票代碼
        """
        logger.info("開始收集 %s 的資料", symbol)
        symbols = [symbol]

        # 收集市場資料
        if "market_data" in self.collectors:
            try:
                self.collectors["market_data"].trigger_now(
                    symbols, data_type="daily"
                )
                logger.info("已觸發 %s 的市場資料收集", symbol)
            except Exception as e:
                logger.error("收集 %s 市場資料時發生錯誤: %s", symbol, e)

        # 收集財務報表資料
        if "financial_statement" in self.collectors:
            try:
                self.collectors["financial_statement"].trigger_now(
                    symbols, data_type="company_info"
                )
                logger.info("已觸發 %s 的財務報表資料收集", symbol)
            except Exception as e:
                logger.error("收集 %s 財務報表資料時發生錯誤: %s", symbol, e)

        # 收集新聞情緒資料
        if "news_sentiment" in self.collectors:
            try:
                self.collectors["news_sentiment"].trigger_now(symbols, days=1)
                logger.info("已觸發 %s 的新聞情緒資料收集", symbol)
            except Exception as e:
                logger.error("收集 %s 新聞情緒資料時發生錯誤: %s", symbol, e)

    def get_collection_statistics(self) -> Dict[str, Any]:
        """獲取收集統計資訊
        
        Returns:
            Dict[str, Any]: 統計資訊字典
        """
        stats = {
            "total_symbols": len(self.symbols),
            "enabled_collectors": [],
            "collector_stats": {}
        }

        # 統計啟用的收集器
        for collector_name, collector_config in self.config["collectors"].items():
            if collector_config.get("enabled", False):
                stats["enabled_collectors"].append(collector_name)

        # 統計各收集器的狀態
        for name, collector in self.collectors.items():
            stats["collector_stats"][name] = {
                "success_count": getattr(collector, "success_count", 0),
                "error_count": getattr(collector, "error_count", 0),
                "last_run_time": getattr(collector, "last_run_time", None),
                "last_run_status": getattr(collector, "last_run_status", None)
            }

        return stats
