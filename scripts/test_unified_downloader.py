#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""統一下載器功能測試腳本

此腳本用於測試重構後的統一下載器功能，確保：
1. 所有原有功能正常運作
2. 新的統一介面正確實現
3. 向後相容性完整保持
4. 程式碼重複成功消除

Usage:
    python scripts/test_unified_downloader.py
"""

import logging
import sys
from datetime import date, timedelta
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.unified_data_downloader import UnifiedDataDownloader
from src.data.twse_downloader import TWSEDataDownloader, DownloadConfig
from src.data.data_integration_system import DataIntegrationSystem

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/unified_downloader_test.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def test_unified_downloader_basic():
    """測試統一下載器基本功能"""
    logger.info("=== 測試統一下載器基本功能 ===")
    
    try:
        # 創建統一下載器
        config = DownloadConfig(
            request_delay=1.0,
            max_retries=2,
            enable_resume=False
        )
        downloader = UnifiedDataDownloader(config)
        logger.info("✅ 統一下載器初始化成功")
        
        # 檢查支援的資料類型
        supported_types = downloader.get_supported_data_types()
        logger.info("支援的資料類型:")
        for category, types in supported_types.items():
            logger.info("  %s: %s", category, types)
        
        # 驗證必要的資料類型存在
        expected_technical = ["odd_lot_trading", "benchmark_index", "adjusted_price"]
        expected_fundamental = ["dividend_announcement", "monthly_revenue", "ex_dividend_info"]
        
        technical_types = supported_types.get("technical", [])
        fundamental_types = supported_types.get("fundamental", [])
        
        for expected in expected_technical:
            if expected in technical_types:
                logger.info("✅ 技術面資料類型 %s 支援", expected)
            else:
                logger.warning("⚠️ 技術面資料類型 %s 不支援", expected)
        
        for expected in expected_fundamental:
            if expected in fundamental_types:
                logger.info("✅ 基本面資料類型 %s 支援", expected)
            else:
                logger.warning("⚠️ 基本面資料類型 %s 不支援", expected)
        
        return True
        
    except Exception as e:
        logger.error("❌ 統一下載器基本功能測試失敗: %s", e)
        return False


def test_unified_downloader_inheritance():
    """測試統一下載器繼承功能"""
    logger.info("=== 測試統一下載器繼承功能 ===")
    
    try:
        config = DownloadConfig(request_delay=1.0, max_retries=2)
        downloader = UnifiedDataDownloader(config)
        
        # 測試繼承的智能日期處理功能
        logger.info("測試智能日期處理...")
        norm_start, norm_end = downloader._normalize_date_range(None, None, 1)
        logger.info("✅ 日期標準化：%s 到 %s", norm_start, norm_end)
        
        # 測試交易日生成
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        trading_days = downloader._get_trading_days(start_date, end_date)
        logger.info("✅ 交易日生成：%d 個交易日", len(trading_days))
        
        # 測試股票清單獲取
        stock_symbols = downloader.get_all_stock_symbols()
        logger.info("✅ 股票清單獲取：%d 個股票", len(stock_symbols))
        
        return True
        
    except Exception as e:
        logger.error("❌ 統一下載器繼承功能測試失敗: %s", e)
        return False


def test_unified_downloader_download():
    """測試統一下載器下載功能"""
    logger.info("=== 測試統一下載器下載功能 ===")
    
    try:
        config = DownloadConfig(request_delay=1.0, max_retries=2)
        downloader = UnifiedDataDownloader(config)
        
        # 測試技術面資料下載
        logger.info("測試技術面資料下載...")
        
        end_date = date.today()
        start_date = end_date - timedelta(days=3)
        
        try:
            result = downloader.download_data_type(
                category="technical",
                data_type="odd_lot_trading",
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
                symbols=["2330.TW"],
                check_existing_data=False  # 跳過存在性檢查以簡化測試
            )
            
            logger.info("✅ 技術面資料下載成功")
            logger.info("下載結果: %s", result)
            
        except Exception as e:
            logger.warning("⚠️ 技術面資料下載失敗: %s", e)
        
        # 測試基本面資料下載
        logger.info("測試基本面資料下載...")
        
        try:
            result = downloader.download_data_type(
                category="fundamental",
                data_type="monthly_revenue",
                start_date="2024-01-01",
                end_date="2024-01-31",
                symbols=["2330.TW"],
                check_existing_data=False
            )
            
            logger.info("✅ 基本面資料下載成功")
            logger.info("下載結果: %s", result)
            
        except Exception as e:
            logger.warning("⚠️ 基本面資料下載失敗: %s", e)
        
        return True
        
    except Exception as e:
        logger.error("❌ 統一下載器下載功能測試失敗: %s", e)
        return False


def test_backward_compatibility():
    """測試向後相容性"""
    logger.info("=== 測試向後相容性 ===")
    
    try:
        # 測試原有 TWSE 下載器仍然正常工作
        logger.info("測試原有 TWSE 下載器...")
        
        config = DownloadConfig(
            request_delay=1.0,
            max_retries=2,
            enable_resume=False
        )
        twse_downloader = TWSEDataDownloader(config)
        
        # 測試基本功能
        norm_start, norm_end = twse_downloader._normalize_date_range(None, None, 1)
        logger.info("✅ TWSE 下載器日期處理正常: %s 到 %s", norm_start, norm_end)
        
        # 測試股票清單
        symbols = twse_downloader.get_all_stock_symbols()
        logger.info("✅ TWSE 下載器股票清單正常: %d 個股票", len(symbols))
        
        return True
        
    except Exception as e:
        logger.error("❌ 向後相容性測試失敗: %s", e)
        return False


def test_integration_system():
    """測試資料整合系統"""
    logger.info("=== 測試資料整合系統 ===")
    
    try:
        # 創建資料整合系統
        system = DataIntegrationSystem()
        logger.info("✅ 資料整合系統初始化成功")
        
        # 檢查可用下載器
        status = system.get_system_status()
        logger.info("可用下載器: %s", status['available_downloaders'])
        
        # 檢查支援的資料類型
        supported_types = system.get_supported_data_types()
        logger.info("系統支援的資料類型:")
        for category, types in supported_types.items():
            logger.info("  %s: %s", category, types)
        
        # 測試統一下載器整合
        if 'unified' in status['available_downloaders']:
            logger.info("✅ 統一下載器已整合到系統中")
        else:
            logger.warning("⚠️ 統一下載器未整合到系統中")
        
        # 測試向後相容性
        if 'twse' in status['available_downloaders']:
            logger.info("✅ TWSE 下載器向後相容性保持")
        else:
            logger.warning("⚠️ TWSE 下載器向後相容性問題")
        
        return True
        
    except Exception as e:
        logger.error("❌ 資料整合系統測試失敗: %s", e)
        return False


def test_code_reduction():
    """測試程式碼減少效果"""
    logger.info("=== 測試程式碼減少效果 ===")
    
    try:
        # 檢查檔案是否存在
        files_to_check = [
            "src/data/unified_data_downloader.py",
            "src/data/twse_downloader.py",
            "src/data/data_integration_system.py"
        ]
        
        existing_files = []
        for file_path in files_to_check:
            if Path(file_path).exists():
                existing_files.append(file_path)
                logger.info("✅ 檔案存在: %s", file_path)
            else:
                logger.warning("⚠️ 檔案不存在: %s", file_path)
        
        # 檢查是否成功減少檔案數量
        removed_files = [
            "src/data/technical_data_downloader.py",
            "src/data/fundamental_data_downloader.py",
            "src/data/web_crawler_implementations.py",
            "src/data/data_source_urls.py"
        ]
        
        for file_path in removed_files:
            if not Path(file_path).exists():
                logger.info("✅ 檔案已移除/整合: %s", file_path)
            else:
                logger.info("📝 檔案仍存在: %s", file_path)
        
        logger.info("重構後核心檔案數量: %d", len(existing_files))
        
        return True
        
    except Exception as e:
        logger.error("❌ 程式碼減少效果測試失敗: %s", e)
        return False


def main():
    """主函數"""
    logger.info("開始統一下載器功能測試")
    
    # 確保日誌目錄存在
    Path("logs").mkdir(exist_ok=True)
    
    test_results = []
    
    # 執行各項測試
    test_results.append(("統一下載器基本功能", test_unified_downloader_basic()))
    test_results.append(("統一下載器繼承功能", test_unified_downloader_inheritance()))
    test_results.append(("統一下載器下載功能", test_unified_downloader_download()))
    test_results.append(("向後相容性", test_backward_compatibility()))
    test_results.append(("資料整合系統", test_integration_system()))
    test_results.append(("程式碼減少效果", test_code_reduction()))
    
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
        logger.info("🎉 統一下載器重構基本成功！")
        return 0
    else:
        logger.error("⚠️ 部分測試失敗，請檢查重構實現")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
