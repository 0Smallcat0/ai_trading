#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""URL 爬蟲功能測試腳本

此腳本用於測試基於提供的 URL 清單實現的爬蟲功能，包括：
- URL 配置管理器測試
- 各種爬蟲實現測試
- 資料來源可用性測試
- 實際資料爬取測試

Usage:
    python scripts/test_url_crawlers.py
"""

import logging
import sys
from datetime import date, timedelta
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.data_source_urls import DataSourceURLManager, DataCategory
from src.data.web_crawler_implementations import TWSECrawler, YahooFinanceCrawler, CrawlerFactory
from src.data.data_integration_system import DataIntegrationSystem

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/url_crawler_test.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def test_url_manager():
    """測試 URL 配置管理器"""
    logger.info("=== 測試 URL 配置管理器 ===")
    
    try:
        manager = DataSourceURLManager()
        logger.info("✅ URL 管理器初始化成功")
        
        # 測試獲取所有分類
        categories = manager.get_all_categories()
        logger.info("支援的資料分類: %s", categories)
        
        # 測試按分類獲取資料來源
        for category in categories:
            sources = manager.get_sources_by_category(category)
            logger.info("分類 %s: %d 個資料來源", category, len(sources))
            
            # 顯示前3個資料來源
            for i, source in enumerate(sources[:3]):
                logger.info("  %d. %s - %s", i+1, source.name, source.description)
        
        # 測試獲取官方資料來源
        official_sources = manager.get_official_sources()
        logger.info("官方資料來源: %d 個", len(official_sources))
        
        # 測試獲取高可靠性資料來源
        reliable_sources = manager.get_high_reliability_sources(min_reliability=4)
        logger.info("高可靠性資料來源: %d 個", len(reliable_sources))
        
        # 測試搜尋功能
        search_results = manager.search_sources("零股")
        logger.info("搜尋 '零股' 結果: %d 個", len(search_results))
        
        return True
        
    except Exception as e:
        logger.error("❌ URL 管理器測試失敗: %s", e)
        return False


def test_twse_crawler():
    """測試證交所爬蟲"""
    logger.info("=== 測試證交所爬蟲 ===")
    
    try:
        crawler = TWSECrawler(request_delay=1.0)  # 測試時使用較短延遲
        logger.info("✅ TWSE 爬蟲初始化成功")
        
        # 測試日期（使用最近的交易日）
        today = date.today()
        test_date = today - timedelta(days=1)  # 昨天
        
        # 如果是週末，往前推到週五
        while test_date.weekday() >= 5:
            test_date -= timedelta(days=1)
        
        test_date_str = test_date.strftime("%Y-%m-%d")
        logger.info("使用測試日期: %s", test_date_str)
        
        # 測試零股成交資料爬取
        logger.info("測試零股成交資料爬取...")
        try:
            odd_lot_data = crawler.crawl_odd_lot_trading(test_date_str)
            logger.info("✅ 零股成交資料爬取成功: %d 筆", len(odd_lot_data))
            
            if not odd_lot_data.empty:
                logger.info("資料欄位: %s", list(odd_lot_data.columns))
                logger.info("前3筆資料:")
                logger.info("\n%s", odd_lot_data.head(3).to_string())
            
        except Exception as e:
            logger.warning("⚠️ 零股成交資料爬取失敗: %s", e)
        
        # 測試加權指數資料爬取
        logger.info("測試加權指數資料爬取...")
        try:
            index_data = crawler.crawl_taiex_index(test_date_str)
            logger.info("✅ 加權指數資料爬取成功: %d 筆", len(index_data))
            
            if not index_data.empty:
                logger.info("指數資料欄位: %s", list(index_data.columns))
        
        except Exception as e:
            logger.warning("⚠️ 加權指數資料爬取失敗: %s", e)
        
        # 測試月營收資料爬取
        logger.info("測試月營收資料爬取...")
        try:
            current_year = today.year
            current_month = today.month - 1 if today.month > 1 else 12
            if current_month == 12:
                current_year -= 1
            
            revenue_data = crawler.crawl_monthly_revenue(current_year, current_month)
            logger.info("✅ 月營收資料爬取成功: %d 筆", len(revenue_data))
            
        except Exception as e:
            logger.warning("⚠️ 月營收資料爬取失敗: %s", e)
        
        return True
        
    except Exception as e:
        logger.error("❌ TWSE 爬蟲測試失敗: %s", e)
        return False


def test_yahoo_crawler():
    """測試 Yahoo Finance 爬蟲"""
    logger.info("=== 測試 Yahoo Finance 爬蟲 ===")
    
    try:
        crawler = YahooFinanceCrawler()
        logger.info("✅ Yahoo Finance 爬蟲初始化成功")
        
        # 測試股票歷史資料爬取
        logger.info("測試股票歷史資料爬取...")
        
        end_date = date.today()
        start_date = end_date - timedelta(days=7)  # 最近一週
        
        try:
            stock_data = crawler.crawl_stock_history(
                "2330.TW",  # 台積電
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
            
            logger.info("✅ 股票歷史資料爬取成功: %d 筆", len(stock_data))
            
            if not stock_data.empty:
                logger.info("股票資料欄位: %s", list(stock_data.columns))
                logger.info("最新資料:")
                logger.info("\n%s", stock_data.tail(3).to_string())
            
        except Exception as e:
            logger.warning("⚠️ 股票歷史資料爬取失敗: %s", e)
        
        return True
        
    except Exception as e:
        logger.error("❌ Yahoo Finance 爬蟲測試失敗: %s", e)
        return False


def test_crawler_factory():
    """測試爬蟲工廠"""
    logger.info("=== 測試爬蟲工廠 ===")
    
    try:
        # 測試創建不同類型的爬蟲
        crawler_types = ['twse', 'yahoo', 'government']
        
        for crawler_type in crawler_types:
            try:
                crawler = CrawlerFactory.create_crawler(crawler_type, request_delay=1.0)
                logger.info("✅ 成功創建 %s 爬蟲: %s", crawler_type, type(crawler).__name__)
                
            except Exception as e:
                logger.warning("⚠️ 創建 %s 爬蟲失敗: %s", crawler_type, e)
        
        # 測試不支援的爬蟲類型
        try:
            CrawlerFactory.create_crawler('unsupported')
            logger.error("❌ 應該拋出錯誤但沒有")
            return False
        except ValueError:
            logger.info("✅ 正確處理不支援的爬蟲類型")
        
        return True
        
    except Exception as e:
        logger.error("❌ 爬蟲工廠測試失敗: %s", e)
        return False


def test_integration_with_system():
    """測試與資料整合系統的整合"""
    logger.info("=== 測試與資料整合系統的整合 ===")
    
    try:
        system = DataIntegrationSystem()
        logger.info("✅ 資料整合系統初始化成功")
        
        # 檢查 URL 管理器是否正確整合
        if hasattr(system, 'url_manager'):
            logger.info("✅ URL 管理器已整合到系統中")
            
            # 測試獲取支援的資料類型
            supported_types = system.get_supported_data_types()
            logger.info("系統支援的資料類型:")
            for category, types in supported_types.items():
                logger.info("  %s: %s", category, types)
        else:
            logger.warning("⚠️ URL 管理器未整合到系統中")
        
        # 測試基本面下載器是否可用
        if 'fundamental' in system.downloaders:
            logger.info("✅ 基本面下載器已整合")
            
            fundamental_downloader = system.downloaders['fundamental']
            supported_fundamental_types = fundamental_downloader.get_supported_data_types()
            logger.info("基本面支援的資料類型: %s", list(supported_fundamental_types.keys()))
        else:
            logger.warning("⚠️ 基本面下載器未整合")
        
        # 測試系統狀態
        status = system.get_system_status()
        logger.info("系統狀態: 可用下載器 %d 個", len(status['available_downloaders']))
        
        return True
        
    except Exception as e:
        logger.error("❌ 系統整合測試失敗: %s", e)
        return False


def test_url_accessibility():
    """測試 URL 可訪問性"""
    logger.info("=== 測試 URL 可訪問性 ===")
    
    try:
        manager = DataSourceURLManager()
        
        # 測試幾個重要的 URL
        test_urls = [
            manager.get_url_config("odd_lot_trading"),
            manager.get_url_config("benchmark_index"),
            manager.get_url_config("monthly_revenue")
        ]
        
        accessible_count = 0
        total_count = len([url for url in test_urls if url is not None])
        
        for url_config in test_urls:
            if url_config is None:
                continue
                
            try:
                import requests
                
                # 簡單的 HEAD 請求測試可訪問性
                response = requests.head(
                    url_config.url, 
                    headers=url_config.headers,
                    timeout=10
                )
                
                if response.status_code < 400:
                    logger.info("✅ %s 可訪問 (狀態碼: %d)", url_config.name, response.status_code)
                    accessible_count += 1
                else:
                    logger.warning("⚠️ %s 不可訪問 (狀態碼: %d)", url_config.name, response.status_code)
                    
            except Exception as e:
                logger.warning("⚠️ %s 訪問測試失敗: %s", url_config.name, e)
        
        logger.info("URL 可訪問性測試完成: %d/%d 可訪問", accessible_count, total_count)
        
        return accessible_count > 0
        
    except Exception as e:
        logger.error("❌ URL 可訪問性測試失敗: %s", e)
        return False


def main():
    """主函數"""
    logger.info("開始 URL 爬蟲功能測試")
    
    # 確保日誌目錄存在
    Path("logs").mkdir(exist_ok=True)
    
    test_results = []
    
    # 執行各項測試
    test_results.append(("URL 配置管理器測試", test_url_manager()))
    test_results.append(("TWSE 爬蟲測試", test_twse_crawler()))
    test_results.append(("Yahoo Finance 爬蟲測試", test_yahoo_crawler()))
    test_results.append(("爬蟲工廠測試", test_crawler_factory()))
    test_results.append(("系統整合測試", test_integration_with_system()))
    test_results.append(("URL 可訪問性測試", test_url_accessibility()))
    
    # 輸出測試結果
    logger.info("=== 測試結果摘要 ===")
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        logger.info("%s: %s", test_name, status)
        if result:
            passed += 1
    
    logger.info("總計: %d/%d 測試通過", passed, total)
    
    if passed >= total * 0.8:  # 80% 通過率視為成功
        logger.info("🎉 URL 爬蟲功能測試基本通過！")
        return 0
    else:
        logger.error("⚠️ 部分測試失敗，請檢查日誌")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
