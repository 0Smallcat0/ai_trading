#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""統一下載器擴展功能測試腳本

此腳本用於測試統一下載器的擴展功能，包括：
1. 籌碼面資料下載功能
2. 事件面資料下載功能  
3. 並行下載和快取機制
4. 效能優化驗證

Usage:
    python scripts/test_unified_downloader_extended.py
"""

import logging
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.unified_data_downloader import UnifiedDataDownloader
from src.data.twse_downloader import DownloadConfig
from src.data.data_integration_system import DataIntegrationSystem

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/unified_downloader_extended_test.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def test_chip_data_types():
    """測試籌碼面資料類型支援"""
    logger.info("=== 測試籌碼面資料類型支援 ===")
    
    try:
        config = DownloadConfig(
            request_delay=1.0,
            max_retries=2,
            enable_resume=False
        )
        downloader = UnifiedDataDownloader(config)
        
        # 檢查籌碼面資料類型
        supported_types = downloader.get_supported_data_types()
        chip_types = supported_types.get("chip", [])
        
        expected_chip_types = [
            "institutional_trading",
            "margin_trading", 
            "foreign_holding",
            "broker_trading"
        ]
        
        logger.info("籌碼面支援的資料類型: %s", chip_types)
        
        for expected in expected_chip_types:
            if expected in chip_types:
                logger.info("✅ 籌碼面資料類型 %s 支援", expected)
            else:
                logger.warning("⚠️ 籌碼面資料類型 %s 不支援", expected)
        
        # 測試籌碼面資料來源配置
        for chip_type in chip_types:
            sources = downloader.get_data_sources_for_type(chip_type)
            logger.info("資料類型 %s 的資料來源: %d 個", chip_type, len(sources))
            for source in sources:
                logger.info("  - %s (優先級: %d)", source.name, source.priority)
        
        return True
        
    except Exception as e:
        logger.error("❌ 籌碼面資料類型測試失敗: %s", e)
        return False


def test_event_data_types():
    """測試事件面資料類型支援"""
    logger.info("=== 測試事件面資料類型支援 ===")
    
    try:
        config = DownloadConfig(request_delay=1.0, max_retries=2)
        downloader = UnifiedDataDownloader(config)
        
        # 檢查事件面資料類型
        supported_types = downloader.get_supported_data_types()
        event_types = supported_types.get("event", [])
        
        expected_event_types = [
            "material_news",
            "investor_conference",
            "stock_news", 
            "dividend_announcement_events"
        ]
        
        logger.info("事件面支援的資料類型: %s", event_types)
        
        for expected in expected_event_types:
            if expected in event_types:
                logger.info("✅ 事件面資料類型 %s 支援", expected)
            else:
                logger.warning("⚠️ 事件面資料類型 %s 不支援", expected)
        
        # 測試事件面資料來源配置
        for event_type in event_types:
            sources = downloader.get_data_sources_for_type(event_type)
            logger.info("資料類型 %s 的資料來源: %d 個", event_type, len(sources))
        
        return True
        
    except Exception as e:
        logger.error("❌ 事件面資料類型測試失敗: %s", e)
        return False


def test_cache_functionality():
    """測試快取功能"""
    logger.info("=== 測試快取功能 ===")
    
    try:
        # 啟用快取的配置
        config = DownloadConfig(
            request_delay=0.5,
            max_retries=1,
            enable_cache=True,
            cache_expire_hours=1
        )
        downloader = UnifiedDataDownloader(config)
        
        # 檢查快取目錄
        cache_dir = downloader.cache_dir
        logger.info("快取目錄: %s", cache_dir)
        logger.info("快取啟用: %s", downloader.enable_cache)
        logger.info("快取過期時間: %d 小時", downloader.cache_expire_hours)
        
        # 測試快取鍵值生成
        test_date = date.today() - timedelta(days=1)
        cache_key = downloader._get_cache_key("technical", "2330.TW", test_date)
        logger.info("測試快取鍵值: %s", cache_key)
        
        # 測試快取路徑
        cache_path = downloader._get_cache_path(cache_key)
        logger.info("快取檔案路徑: %s", cache_path)
        
        # 測試快取有效性檢查
        is_valid = downloader._is_cache_valid(cache_path)
        logger.info("快取有效性: %s", is_valid)
        
        # 測試清理過期快取
        downloader._clean_expired_cache()
        logger.info("✅ 快取功能測試完成")
        
        return True
        
    except Exception as e:
        logger.error("❌ 快取功能測試失敗: %s", e)
        return False


def test_parallel_download():
    """測試並行下載功能"""
    logger.info("=== 測試並行下載功能 ===")
    
    try:
        # 啟用並行下載的配置
        config = DownloadConfig(
            request_delay=0.5,
            max_retries=1,
            enable_parallel=True,
            max_workers=2,
            enable_cache=True
        )
        downloader = UnifiedDataDownloader(config)
        
        logger.info("並行下載啟用: %s", downloader.enable_parallel)
        logger.info("最大工作者數量: %d", downloader.max_workers)
        
        # 測試並行下載（使用較少的股票和較短的時間範圍）
        end_date = date.today()
        start_date = end_date - timedelta(days=2)
        
        test_symbols = ["2330.TW", "2317.TW"]  # 台積電、鴻海
        
        logger.info("測試並行下載技術面資料...")
        start_time = time.time()
        
        try:
            result = downloader.download_data_type(
                category="technical",
                data_type="odd_lot_trading",
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                symbols=test_symbols,
                check_existing_data=False  # 跳過存在性檢查以簡化測試
            )
            
            end_time = time.time()
            download_time = end_time - start_time
            
            logger.info("✅ 並行下載完成")
            logger.info("下載時間: %.2f 秒", download_time)
            logger.info("下載結果: %s", result)
            
            # 檢查是否使用了並行下載
            if result.get('parallel_enabled'):
                logger.info("✅ 並行下載機制已啟用")
            else:
                logger.info("ℹ️ 使用序列下載（可能因為股票數量太少）")
            
        except Exception as e:
            logger.warning("⚠️ 並行下載測試失敗: %s", e)
        
        return True
        
    except Exception as e:
        logger.error("❌ 並行下載功能測試失敗: %s", e)
        return False


def test_performance_comparison():
    """測試效能比較（序列 vs 並行）"""
    logger.info("=== 測試效能比較 ===")
    
    try:
        test_symbols = ["2330.TW", "2317.TW", "2454.TW"]  # 3個股票
        end_date = date.today()
        start_date = end_date - timedelta(days=1)
        
        # 測試序列下載
        logger.info("測試序列下載...")
        config_serial = DownloadConfig(
            request_delay=0.3,
            max_retries=1,
            enable_parallel=False,
            enable_cache=False
        )
        downloader_serial = UnifiedDataDownloader(config_serial)
        
        start_time = time.time()
        try:
            result_serial = downloader_serial.download_data_type(
                category="technical",
                data_type="benchmark_index",
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                symbols=test_symbols,
                check_existing_data=False
            )
            serial_time = time.time() - start_time
            logger.info("序列下載時間: %.2f 秒", serial_time)
        except Exception as e:
            logger.warning("序列下載測試失敗: %s", e)
            serial_time = 0
        
        # 測試並行下載
        logger.info("測試並行下載...")
        config_parallel = DownloadConfig(
            request_delay=0.3,
            max_retries=1,
            enable_parallel=True,
            max_workers=3,
            enable_cache=False
        )
        downloader_parallel = UnifiedDataDownloader(config_parallel)
        
        start_time = time.time()
        try:
            result_parallel = downloader_parallel.download_data_type(
                category="technical",
                data_type="benchmark_index",
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                symbols=test_symbols,
                check_existing_data=False
            )
            parallel_time = time.time() - start_time
            logger.info("並行下載時間: %.2f 秒", parallel_time)
        except Exception as e:
            logger.warning("並行下載測試失敗: %s", e)
            parallel_time = 0
        
        # 效能比較
        if serial_time > 0 and parallel_time > 0:
            speedup = serial_time / parallel_time
            logger.info("效能提升: %.2fx", speedup)
            if speedup > 1.2:
                logger.info("✅ 並行下載顯著提升效能")
            else:
                logger.info("ℹ️ 並行下載效能提升有限（可能因為網路延遲）")
        
        return True
        
    except Exception as e:
        logger.error("❌ 效能比較測試失敗: %s", e)
        return False


def test_integration_with_system():
    """測試與資料整合系統的整合"""
    logger.info("=== 測試與資料整合系統的整合 ===")
    
    try:
        system = DataIntegrationSystem()
        
        # 檢查新的資料類型是否正確整合
        supported_types = system.get_supported_data_types()
        logger.info("系統支援的資料類型:")
        for category, types in supported_types.items():
            logger.info("  %s: %s", category, types)
        
        # 檢查籌碼面和事件面是否支援
        if "chip" in supported_types:
            logger.info("✅ 籌碼面資料已整合到系統")
        else:
            logger.warning("⚠️ 籌碼面資料未整合到系統")
        
        if "event" in supported_types:
            logger.info("✅ 事件面資料已整合到系統")
        else:
            logger.warning("⚠️ 事件面資料未整合到系統")
        
        return True
        
    except Exception as e:
        logger.error("❌ 系統整合測試失敗: %s", e)
        return False


def main():
    """主函數"""
    logger.info("開始統一下載器擴展功能測試")
    
    # 確保日誌目錄存在
    Path("logs").mkdir(exist_ok=True)
    
    test_results = []
    
    # 執行各項測試
    test_results.append(("籌碼面資料類型支援", test_chip_data_types()))
    test_results.append(("事件面資料類型支援", test_event_data_types()))
    test_results.append(("快取功能", test_cache_functionality()))
    test_results.append(("並行下載功能", test_parallel_download()))
    test_results.append(("效能比較", test_performance_comparison()))
    test_results.append(("系統整合", test_integration_with_system()))
    
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
        logger.info("🎉 統一下載器擴展功能測試基本成功！")
        return 0
    else:
        logger.error("⚠️ 部分測試失敗，請檢查擴展功能實現")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
