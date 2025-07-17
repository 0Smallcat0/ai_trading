# -*- coding: utf-8 -*-
"""
數據源模組 - 整合版

此模組提供多種數據源的統一接口，整合了原始項目和新開發的數據處理能力。

支持的數據源：
- Yahoo Finance (現有)
- 台灣證交所 (TWSE) (現有)
- 券商接口 (現有)
- 新聞情緒數據 (現有)
- Tushare (整合自原始項目)
- Wind (整合自原始項目)
- BaoStock (整合自原始項目)

主要功能：
- 多數據源統一接口
- 實時和歷史數據獲取
- 數據清洗和預處理
- 數據緩存和存儲
- 數據質量檢查
- 實時數據流處理
- 數據源容錯和切換

整合特色：
- 保留現有項目的數據源支持
- 增強實時數據處理能力
- 提供統一的數據管理接口
- 支持多數據源並行獲取
"""

# 現有數據源組件
from .data_collector import DataCollector
from .yahoo_adapter import YahooAdapter
from .broker_adapter import BrokerAdapter, MockBrokerAdapter
from .twse_crawler import TWSECrawler
from .mcp_crawler import MCPCrawler
from .news_sentiment_collector import NewsSentimentCollector
from .market_data_collector import MarketDataCollector
from .realtime_quote_collector import RealtimeQuoteCollector
from .financial_statement_collector import FinancialStatementCollector
from .data_collection_system import DataCollectionSystem

# 整合自原始項目的數據源（將逐步實現）
# from .legacy_sources import TushareSource, WindSource, BaoStockSource

# 增強功能
from .unified_data_manager import UnifiedDataManager

__all__ = [
    # 現有組件
    'DataCollector',
    'YahooAdapter',
    'BrokerAdapter',
    'MockBrokerAdapter',
    'TWSECrawler',
    'MCPCrawler',
    'NewsSentimentCollector',
    'MarketDataCollector',
    'RealtimeQuoteCollector',
    'FinancialStatementCollector',
    'DataCollectionSystem',

    # 整合組件（將逐步添加）
    # 'TushareSource',
    # 'WindSource',
    # 'BaoStockSource',

    # 增強組件
    'UnifiedDataManager'
]

# 版本信息
__version__ = "2.0.0"  # 整合版本
__integration_date__ = "2025-01-14"
__legacy_support__ = True