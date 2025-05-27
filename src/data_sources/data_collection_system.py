"""
資料收集系統模組

此模組整合了所有資料收集器，提供統一的介面來管理資料收集任務，包括：
- 排程管理
- 資料收集任務協調
- 錯誤處理與通知
- 資料驗證與儲存

支援多種資料類型和來源的收集，並提供靈活的配置選項。
"""

import json
import logging
import os
import threading
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import pandas as pd

from src.config import CACHE_DIR, DATA_DIR, DB_PATH
from src.data_sources.data_collector import DataCollector, RetryStrategy
from src.data_sources.financial_statement_collector import FinancialStatementCollector
from src.data_sources.market_data_collector import MarketDataCollector
from src.data_sources.news_sentiment_collector import NewsSentimentCollector
from src.data_sources.realtime_quote_collector import RealtimeQuoteCollector

# 設定日誌
logger = logging.getLogger(__name__)


class DataCollectionSystem:
    """
    資料收集系統

    整合所有資料收集器，提供統一的介面來管理資料收集任務。
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        symbols: Optional[List[str]] = None,
    ):
        """
        初始化資料收集系統

        Args:
            config_path: 配置檔案路徑，如果為 None 則使用預設配置
            symbols: 股票代碼列表，如果為 None 則從配置檔案讀取
        """
        # 初始化配置
        self.config = self._load_config(config_path)
        self.symbols = symbols or self.config.get("symbols", [])

        # 初始化收集器
        self.collectors = {}
        self._init_collectors()

        # 初始化狀態
        self.running = False
        self.last_run_time = {}
        self.error_count = {}
        self.success_count = {}

    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        載入配置

        Args:
            config_path: 配置檔案路徑

        Returns:
            Dict[str, Any]: 配置
        """
        default_config = {
            "symbols": ["2330.TW", "2317.TW", "2454.TW", "2412.TW", "2308.TW"],
            "collectors": {
                "market_data": {
                    "enabled": True,
                    "source": "yahoo",
                    "use_cache": True,
                    "cache_expiry_days": 1,
                    "schedule": {
                        "daily": "18:00",
                        "minute": {
                            "enabled": True,
                            "interval": 60,  # 分鐘
                            "symbols": ["2330.TW", "2317.TW"]  # 特定股票才收集分鐘資料
                        }
                    }
                },
                "realtime_quote": {
                    "enabled": False,
                    "source": "yahoo",
                    "symbols": ["2330.TW", "2317.TW"]  # 特定股票才收集即時報價
                },
                "financial_statement": {
                    "enabled": True,
                    "source": "yahoo",
                    "use_cache": True,
                    "cache_expiry_days": 30,
                    "schedule": {
                        "daily": "19:00"
                    }
                },
                "news_sentiment": {
                    "enabled": True,
                    "source": "mcp",
                    "use_cache": True,
                    "cache_expiry_days": 1,
                    "sentiment_model": "simple",
                    "schedule": {
                        "daily": "20:00"
                    }
                }
            }
        }

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                logger.info(f"已從 {config_path} 載入配置")
                return config
            except Exception as e:
                logger.error(f"載入配置檔案 {config_path} 時發生錯誤: {e}")
                return default_config
        else:
            logger.info("使用預設配置")
            return default_config

    def _init_collectors(self):
        """初始化所有收集器"""
        # 初始化市場資料收集器
        market_config = self.config["collectors"]["market_data"]
        if market_config["enabled"]:
            self.collectors["market_data"] = MarketDataCollector(
                source=market_config["source"],
                use_cache=market_config["use_cache"],
                cache_expiry_days=market_config["cache_expiry_days"],
            )
            logger.info(f"已初始化市場資料收集器: {market_config['source']}")

        # 初始化即時報價收集器
        realtime_config = self.config["collectors"]["realtime_quote"]
        if realtime_config["enabled"]:
            self.collectors["realtime_quote"] = RealtimeQuoteCollector(
                source=realtime_config["source"],
            )
            logger.info(f"已初始化即時報價收集器: {realtime_config['source']}")

        # 初始化財務報表收集器
        financial_config = self.config["collectors"]["financial_statement"]
        if financial_config["enabled"]:
            self.collectors["financial_statement"] = FinancialStatementCollector(
                source=financial_config["source"],
                use_cache=financial_config["use_cache"],
                cache_expiry_days=financial_config["cache_expiry_days"],
            )
            logger.info(f"已初始化財務報表收集器: {financial_config['source']}")

        # 初始化新聞情緒收集器
        news_config = self.config["collectors"]["news_sentiment"]
        if news_config["enabled"]:
            self.collectors["news_sentiment"] = NewsSentimentCollector(
                source=news_config["source"],
                use_cache=news_config["use_cache"],
                cache_expiry_days=news_config["cache_expiry_days"],
                sentiment_model=news_config["sentiment_model"],
            )
            logger.info(f"已初始化新聞情緒收集器: {news_config['source']}")

    def setup_schedules(self):
        """設定所有收集器的排程"""
        # 設定市場資料收集器排程
        if "market_data" in self.collectors:
            market_config = self.config["collectors"]["market_data"]
            collector = self.collectors["market_data"]

            # 設定日線資料收集排程
            if "daily" in market_config["schedule"]:
                time_str = market_config["schedule"]["daily"]
                collector.schedule_daily(time_str, self.symbols, data_type="daily")
                logger.info(f"已設定市場日線資料收集排程: 每日 {time_str}")

            # 設定分鐘資料收集排程
            if "minute" in market_config["schedule"] and market_config["schedule"]["minute"]["enabled"]:
                minute_config = market_config["schedule"]["minute"]
                interval = minute_config["interval"]
                minute_symbols = minute_config.get("symbols", self.symbols)
                collector.schedule_interval(interval, "minutes", minute_symbols, data_type="minute", interval="1m")
                logger.info(f"已設定市場分鐘資料收集排程: 每 {interval} 分鐘")

        # 設定財務報表收集器排程
        if "financial_statement" in self.collectors:
            financial_config = self.config["collectors"]["financial_statement"]
            collector = self.collectors["financial_statement"]

            # 設定財務報表收集排程
            if "daily" in financial_config["schedule"]:
                time_str = financial_config["schedule"]["daily"]
                collector.schedule_daily(time_str, self.symbols, data_type="company_info")
                logger.info(f"已設定財務報表收集排程: 每日 {time_str}")

        # 設定新聞情緒收集器排程
        if "news_sentiment" in self.collectors:
            news_config = self.config["collectors"]["news_sentiment"]
            collector = self.collectors["news_sentiment"]

            # 設定新聞情緒收集排程
            if "daily" in news_config["schedule"]:
                time_str = news_config["schedule"]["daily"]
                collector.schedule_daily(time_str, self.symbols, days=1)
                logger.info(f"已設定新聞情緒收集排程: 每日 {time_str}")

    def start(self):
        """啟動資料收集系統"""
        if self.running:
            logger.warning("資料收集系統已在運行中")
            return

        self.running = True
        logger.info("啟動資料收集系統")

        # 啟動所有收集器的排程器
        for name, collector in self.collectors.items():
            if hasattr(collector, "start_scheduler"):
                collector.start_scheduler()
                logger.info(f"已啟動 {name} 收集器的排程器")

        # 啟動即時報價收集器
        if "realtime_quote" in self.collectors:
            realtime_config = self.config["collectors"]["realtime_quote"]
            realtime_symbols = realtime_config.get("symbols", self.symbols)
            self.collectors["realtime_quote"].start()
            self.collectors["realtime_quote"].collect(realtime_symbols)
            logger.info(f"已啟動即時報價收集器，訂閱 {len(realtime_symbols)} 檔股票")

    def stop(self):
        """停止資料收集系統"""
        if not self.running:
            logger.warning("資料收集系統未在運行中")
            return

        self.running = False
        logger.info("停止資料收集系統")

        # 停止所有收集器的排程器
        for name, collector in self.collectors.items():
            if hasattr(collector, "stop_scheduler"):
                collector.stop_scheduler()
                logger.info(f"已停止 {name} 收集器的排程器")

        # 停止即時報價收集器
        if "realtime_quote" in self.collectors:
            self.collectors["realtime_quote"].stop()
            logger.info("已停止即時報價收集器")

    def collect_all(self):
        """立即收集所有資料"""
        logger.info("開始收集所有資料")

        # 收集市場資料
        if "market_data" in self.collectors:
            logger.info("開始收集市場資料")
            try:
                self.collectors["market_data"].trigger_now(self.symbols, data_type="daily")
                logger.info("已觸發市場日線資料收集")

                # 檢查是否需要收集分鐘資料
                market_config = self.config["collectors"]["market_data"]
                if "minute" in market_config["schedule"] and market_config["schedule"]["minute"]["enabled"]:
                    minute_symbols = market_config["schedule"]["minute"].get("symbols", self.symbols)
                    self.collectors["market_data"].trigger_now(minute_symbols, data_type="minute", interval="1m")
                    logger.info("已觸發市場分鐘資料收集")
            except Exception as e:
                logger.error(f"收集市場資料時發生錯誤: {e}")

        # 收集財務報表資料
        if "financial_statement" in self.collectors:
            logger.info("開始收集財務報表資料")
            try:
                self.collectors["financial_statement"].trigger_now(self.symbols, data_type="company_info")
                logger.info("已觸發財務報表資料收集")
            except Exception as e:
                logger.error(f"收集財務報表資料時發生錯誤: {e}")

        # 收集新聞情緒資料
        if "news_sentiment" in self.collectors:
            logger.info("開始收集新聞情緒資料")
            try:
                self.collectors["news_sentiment"].trigger_now(self.symbols, days=1)
                logger.info("已觸發新聞情緒資料收集")
            except Exception as e:
                logger.error(f"收集新聞情緒資料時發生錯誤: {e}")

        logger.info("所有資料收集任務已觸發")

    def get_status(self) -> Dict[str, Any]:
        """
        獲取資料收集系統狀態

        Returns:
            Dict[str, Any]: 系統狀態
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

        return status

    def save_config(self, config_path: str):
        """
        儲存配置到檔案

        Args:
            config_path: 配置檔案路徑
        """
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            logger.info(f"已儲存配置到 {config_path}")
        except Exception as e:
            logger.error(f"儲存配置到 {config_path} 時發生錯誤: {e}")

    def update_symbols(self, symbols: List[str]):
        """
        更新股票代碼列表

        Args:
            symbols: 新的股票代碼列表
        """
        self.symbols = symbols
        logger.info(f"已更新股票代碼列表，共 {len(symbols)} 檔股票")
"""
