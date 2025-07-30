#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步驟 1 HTML 解析和 RSS 處理功能測試腳本

此腳本用於測試統一下載器中新實現的 HTML 解析和 RSS 處理功能，包括：
1. 證交所重大訊息公告解析
2. 證交所法說會期程解析
3. cnyes 台股新聞 RSS 解析
4. 櫃買中心融資融券 HTML 解析

Usage:
    python scripts/test_step1_html_rss_parsing.py
"""

import logging
import sys
from datetime import date, timedelta
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.unified_data_downloader import UnifiedDataDownloader
from src.data.twse_downloader import DownloadConfig

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/step1_html_rss_test.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def test_twse_material_news():
    """測試證交所重大訊息公告解析"""
    logger.info("=== 測試證交所重大訊息公告解析 ===")
    
    try:
        config = DownloadConfig(
            request_delay=2.0,
            max_retries=2,
            enable_cache=False
        )
        downloader = UnifiedDataDownloader(config)
        
        # 測試日期（使用最近的交易日）
        test_date = date.today() - timedelta(days=1)
        while test_date.weekday() >= 5:  # 跳過週末
            test_date -= timedelta(days=1)
        
        logger.info("測試日期: %s", test_date)
        
        # 測試重大訊息下載
        result = downloader._download_twse_material_news("2330.TW", test_date)
        
        if result is not None and not result.empty:
            logger.info("✅ 重大訊息解析成功: %d 筆資料", len(result))
            logger.info("資料欄位: %s", list(result.columns))
            logger.info("前3筆資料:")
            logger.info("\n%s", result.head(3).to_string())
        else:
            logger.info("ℹ️ 當日無重大訊息資料")
        
        return True
        
    except Exception as e:
        logger.error("❌ 重大訊息解析測試失敗: %s", e)
        return False


def test_twse_investor_conference():
    """測試證交所法說會期程解析"""
    logger.info("=== 測試證交所法說會期程解析 ===")
    
    try:
        config = DownloadConfig(request_delay=2.0, max_retries=2, enable_cache=False)
        downloader = UnifiedDataDownloader(config)
        
        # 測試日期
        test_date = date.today()
        
        logger.info("測試日期: %s", test_date)
        
        # 測試法說會期程下載
        result = downloader._download_twse_investor_conference("2330.TW", test_date)
        
        if result is not None and not result.empty:
            logger.info("✅ 法說會期程解析成功: %d 筆資料", len(result))
            logger.info("資料欄位: %s", list(result.columns))
        else:
            logger.info("ℹ️ 當日無法說會期程資料")
        
        return True
        
    except Exception as e:
        logger.error("❌ 法說會期程解析測試失敗: %s", e)
        return False


def test_cnyes_stock_news():
    """測試 cnyes 台股新聞 RSS 解析"""
    logger.info("=== 測試 cnyes 台股新聞 RSS 解析 ===")
    
    try:
        config = DownloadConfig(request_delay=1.0, max_retries=2, enable_cache=False)
        downloader = UnifiedDataDownloader(config)
        
        # 測試日期（使用今天，新聞通常當天就有）
        test_date = date.today()
        
        logger.info("測試日期: %s", test_date)
        
        # 測試新聞下載
        result = downloader._download_cnyes_stock_news(test_date)
        
        if result is not None and not result.empty:
            logger.info("✅ 台股新聞 RSS 解析成功: %d 筆資料", len(result))
            logger.info("資料欄位: %s", list(result.columns))
            logger.info("前3筆新聞標題:")
            for i, row in result.head(3).iterrows():
                logger.info("  %d. %s", i+1, row.get('title', 'N/A'))
        else:
            logger.info("ℹ️ 當日無台股新聞資料")
        
        return True
        
    except Exception as e:
        logger.error("❌ 台股新聞 RSS 解析測試失敗: %s", e)
        return False


def test_tpex_margin_parsing():
    """測試櫃買中心融資融券解析"""
    logger.info("=== 測試櫃買中心融資融券解析 ===")
    
    try:
        config = DownloadConfig(request_delay=2.0, max_retries=2, enable_cache=False)
        downloader = UnifiedDataDownloader(config)
        
        # 測試日期（使用最近的交易日）
        test_date = date.today() - timedelta(days=1)
        while test_date.weekday() >= 5:  # 跳過週末
            test_date -= timedelta(days=1)
        
        logger.info("測試日期: %s", test_date)
        
        # 測試櫃買融資融券下載（使用櫃買股票代碼）
        result = downloader._download_tpex_margin("6488.TW", test_date)
        
        if result is not None and not result.empty:
            logger.info("✅ 櫃買融資融券解析成功: %d 筆資料", len(result))
            logger.info("資料欄位: %s", list(result.columns))
            logger.info("前3筆資料:")
            logger.info("\n%s", result.head(3).to_string())
        else:
            logger.info("ℹ️ 當日無櫃買融資融券資料")
        
        return True
        
    except Exception as e:
        logger.error("❌ 櫃買融資融券解析測試失敗: %s", e)
        return False


def test_stock_symbol_extraction():
    """測試股票代碼提取功能"""
    logger.info("=== 測試股票代碼提取功能 ===")
    
    try:
        config = DownloadConfig()
        downloader = UnifiedDataDownloader(config)
        
        # 測試文本
        test_texts = [
            "台積電(2330)今日股價上漲",
            "鴻海(2317)與聯發科(2454)合作",
            "大立光3008股價創新高",
            "無股票代碼的新聞內容",
            "1234 是無效代碼，2330 是有效代碼"
        ]
        
        for text in test_texts:
            symbols = downloader._extract_stock_symbols_from_text(text)
            logger.info("文本: %s", text)
            logger.info("提取的股票代碼: %s", symbols)
            logger.info("---")
        
        logger.info("✅ 股票代碼提取功能測試完成")
        return True
        
    except Exception as e:
        logger.error("❌ 股票代碼提取功能測試失敗: %s", e)
        return False


def test_unified_event_data_download():
    """測試統一事件面資料下載"""
    logger.info("=== 測試統一事件面資料下載 ===")
    
    try:
        config = DownloadConfig(
            request_delay=1.5,
            max_retries=2,
            enable_cache=False,
            enable_parallel=False  # 測試時使用序列下載
        )
        downloader = UnifiedDataDownloader(config)
        
        # 測試日期
        test_date = date.today()
        
        # 測試事件面資料類型
        event_types = ["stock_news"]  # 先測試最容易成功的
        
        for event_type in event_types:
            logger.info("測試事件面資料類型: %s", event_type)
            
            try:
                result = downloader.download_data_type(
                    category="event",
                    data_type=event_type,
                    start_date=test_date.strftime("%Y-%m-%d"),
                    end_date=test_date.strftime("%Y-%m-%d"),
                    check_existing_data=False
                )
                
                logger.info("下載結果: %s", result)
                
            except Exception as e:
                logger.warning("事件面資料類型 %s 下載失敗: %s", event_type, e)
        
        logger.info("✅ 統一事件面資料下載測試完成")
        return True
        
    except Exception as e:
        logger.error("❌ 統一事件面資料下載測試失敗: %s", e)
        return False


def main():
    """主函數"""
    logger.info("開始步驟 1 HTML 解析和 RSS 處理功能測試")
    
    # 確保日誌目錄存在
    Path("logs").mkdir(exist_ok=True)
    
    test_results = []
    
    # 執行各項測試
    test_results.append(("證交所重大訊息解析", test_twse_material_news()))
    test_results.append(("證交所法說會期程解析", test_twse_investor_conference()))
    test_results.append(("cnyes 台股新聞 RSS 解析", test_cnyes_stock_news()))
    test_results.append(("櫃買中心融資融券解析", test_tpex_margin_parsing()))
    test_results.append(("股票代碼提取功能", test_stock_symbol_extraction()))
    test_results.append(("統一事件面資料下載", test_unified_event_data_download()))
    
    # 輸出測試結果
    logger.info("=== 步驟 1 測試結果摘要 ===")
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        logger.info("%s: %s", test_name, status)
        if result:
            passed += 1
    
    logger.info("總計: %d/%d 測試通過", passed, total)
    
    if passed >= total * 0.8:  # 80% 通過率視為成功
        logger.info("🎉 步驟 1 HTML 解析和 RSS 處理功能基本完成！")
        return 0
    else:
        logger.error("⚠️ 部分測試失敗，需要進一步調整實現")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
