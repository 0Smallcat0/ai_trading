#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TWSE 股價資料下載測試腳本

此腳本用於測試 TWSE 股價資料下載器的功能。
提供小規模的測試下載，驗證下載器的各項功能。

Usage:
    python scripts/test_twse_download.py
"""

import logging
import sys
from datetime import date, timedelta
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.twse_downloader import TWSEDataDownloader, DownloadConfig

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/twse_download_test.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def test_basic_functionality():
    """測試基本功能"""
    logger.info("=== 測試基本功能 ===")
    
    try:
        # 創建下載器
        config = DownloadConfig(
            request_delay=1.0,  # 測試時使用較短間隔
            max_retries=2,
            enable_resume=False  # 測試時不啟用恢復功能
        )
        downloader = TWSEDataDownloader(config)
        logger.info("✅ 下載器創建成功")
        
        # 測試獲取股票清單
        symbols = downloader.get_all_stock_symbols()
        logger.info("✅ 獲取股票清單成功，共 %d 個股票", len(symbols))
        logger.info("前10個股票: %s", symbols[:10])
        
        # 測試月份範圍生成
        end_date = date.today()
        start_date = end_date - timedelta(days=90)  # 最近3個月
        
        month_ranges = downloader._generate_month_ranges(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        logger.info("✅ 月份範圍生成成功，共 %d 個月份", len(month_ranges))
        
        return True
        
    except Exception as e:
        logger.error("❌ 基本功能測試失敗: %s", e)
        return False


def test_smart_download():
    """測試智能下載功能"""
    logger.info("=== 測試智能下載功能 ===")

    try:
        # 創建下載器
        config = DownloadConfig(
            request_delay=1.0,  # 測試時使用較短間隔
            max_retries=2,
            enable_resume=False
        )
        downloader = TWSEDataDownloader(config)

        # 測試日期處理功能
        logger.info("測試智能日期處理...")
        norm_start, norm_end = downloader._normalize_date_range(None, None, 1)
        logger.info("✅ 日期標準化：%s 到 %s", norm_start, norm_end)

        # 測試交易日生成
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        trading_days = downloader._get_trading_days(start_date, end_date)
        logger.info("✅ 交易日生成：%d 個交易日", len(trading_days))

        # 選擇少數幾個主要股票進行測試
        test_symbols = ["2330.TW"]  # 只測試台積電

        logger.info("開始測試智能下載：")
        logger.info("股票: %s", test_symbols)
        logger.info("日期範圍: %s 到 %s", start_date, end_date)

        # 測試增量下載（檢查已存在資料）
        result1 = downloader.download_all_stocks(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            symbols=test_symbols,
            check_existing_data=True,
            force_redownload=False,
            show_progress=False
        )

        logger.info("✅ 增量下載完成")
        logger.info("第一次下載結果: %s", result1)

        # 測試強制重新下載
        result2 = downloader.download_all_stocks(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            symbols=test_symbols,
            check_existing_data=False,
            force_redownload=True,
            show_progress=False
        )

        logger.info("✅ 強制重新下載完成")
        logger.info("第二次下載結果: %s", result2)

        # 檢查結果
        total_records = result1.get('successful_records', 0) + result1.get('skipped_records', 0)
        if total_records > 0:
            logger.info("✅ 智能下載功能正常，處理了 %d 筆記錄", total_records)
            return True
        else:
            logger.warning("⚠️ 智能下載沒有處理任何記錄")
            return False

    except Exception as e:
        logger.error("❌ 智能下載測試失敗: %s", e)
        return False

def test_small_download():
    """測試小規模下載（向後相容性測試）"""
    logger.info("=== 測試小規模下載（向後相容性） ===")

    try:
        # 創建下載器
        config = DownloadConfig(
            request_delay=1.0,
            max_retries=2,
            enable_resume=False
        )
        downloader = TWSEDataDownloader(config)

        # 選擇少數幾個主要股票進行測試
        test_symbols = ["2330.TW"]  # 只測試台積電

        # 下載最近1個月的資料（使用預設參數）
        result = downloader.download_all_stocks(
            years_back=1,  # 使用新的參數
            symbols=test_symbols,
            show_progress=False
        )

        logger.info("✅ 向後相容性測試完成")
        logger.info("下載結果: %s", result)

        # 檢查結果
        total_processed = result.get('successful_records', 0) + result.get('skipped_records', 0)
        if total_processed > 0:
            logger.info("✅ 向後相容性良好，處理了 %d 筆記錄", total_processed)
            return True
        else:
            logger.warning("⚠️ 向後相容性測試沒有處理任何記錄")
            return False

    except Exception as e:
        logger.error("❌ 向後相容性測試失敗: %s", e)
        return False


def test_data_completeness():
    """測試資料完整性檢查"""
    logger.info("=== 測試資料完整性檢查 ===")
    
    try:
        downloader = TWSEDataDownloader()
        
        # 檢查測試股票的資料完整性
        test_symbols = ["2330.TW", "2317.TW"]
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        missing_data = downloader.check_data_completeness(
            symbols=test_symbols,
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d")
        )
        
        logger.info("✅ 資料完整性檢查完成")
        
        if missing_data:
            logger.info("發現缺失資料:")
            for symbol, missing_dates in missing_data.items():
                logger.info("  %s: %d 個缺失日期", symbol, len(missing_dates))
                if len(missing_dates) <= 5:
                    logger.info("    缺失日期: %s", missing_dates)
        else:
            logger.info("✅ 所有測試股票的資料都完整")
        
        return True
        
    except Exception as e:
        logger.error("❌ 資料完整性檢查失敗: %s", e)
        return False


def main():
    """主函數"""
    logger.info("開始 TWSE 股價資料下載器測試")
    
    # 確保日誌目錄存在
    Path("logs").mkdir(exist_ok=True)
    
    test_results = []
    
    # 執行各項測試
    test_results.append(("基本功能測試", test_basic_functionality()))
    test_results.append(("智能下載功能測試", test_smart_download()))
    test_results.append(("向後相容性測試", test_small_download()))
    test_results.append(("資料完整性檢查測試", test_data_completeness()))
    
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
    
    if passed == total:
        logger.info("🎉 所有測試通過！TWSE 下載器功能正常")
        return 0
    else:
        logger.error("⚠️ 部分測試失敗，請檢查日誌")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
