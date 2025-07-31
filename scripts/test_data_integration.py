#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台股資料整合系統測試腳本

此腳本用於測試台股資料整合系統的各項功能，包括：
- 系統初始化測試
- 單一資料類型下載測試
- 批量下載測試
- 向後相容性測試
- 錯誤處理測試
- 系統狀態監控測試

Usage:
    python scripts/test_data_integration.py
"""

import logging
import sys
from datetime import date, timedelta
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.data.data_integration_system import DataIntegrationSystem, SystemConfig
from src.data.technical_data_downloader import TechnicalDataDownloader
from src.data.twse_downloader import TWSEDataDownloader, DownloadConfig

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/data_integration_test.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def test_system_initialization():
    """測試系統初始化"""
    logger.info("=== 測試系統初始化 ===")
    
    try:
        # 測試預設配置初始化
        system = DataIntegrationSystem()
        logger.info("✅ 預設配置初始化成功")
        
        # 檢查系統狀態
        status = system.get_system_status()
        logger.info("系統狀態: %s", status['status'])
        logger.info("可用下載器: %s", status['available_downloaders'])
        
        # 測試自定義配置初始化
        custom_config = SystemConfig(
            max_workers=1,
            default_request_delay=1.0,
            enable_auto_retry=True
        )
        custom_system = DataIntegrationSystem(custom_config)
        logger.info("✅ 自定義配置初始化成功")
        
        # 檢查支援的資料類型
        supported_types = system.get_supported_data_types()
        logger.info("支援的資料類型: %s", supported_types)
        
        return True
        
    except Exception as e:
        logger.error("❌ 系統初始化測試失敗: %s", e)
        return False


def test_technical_data_download():
    """測試技術面資料下載"""
    logger.info("=== 測試技術面資料下載 ===")
    
    try:
        system = DataIntegrationSystem()
        
        # 測試日期範圍
        end_date = date.today()
        start_date = end_date - timedelta(days=7)  # 最近一週
        
        # 測試盤後零股成交資訊下載
        logger.info("測試盤後零股成交資訊下載...")
        result = system.download_data(
            category="technical",
            data_type="odd_lot_trading",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            symbols=["2330.TW"],  # 只測試台積電
            check_existing_data=True,
            show_progress=False
        )
        
        logger.info("✅ 盤後零股成交下載完成")
        logger.info("結果: %s", result)
        
        # 測試回測基準指數下載
        logger.info("測試回測基準指數下載...")
        result = system.download_data(
            category="technical",
            data_type="benchmark_index",
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            symbols=["^TWII"],  # 台灣加權指數
            check_existing_data=True,
            show_progress=False
        )
        
        logger.info("✅ 基準指數下載完成")
        logger.info("結果: %s", result)
        
        return True
        
    except Exception as e:
        logger.error("❌ 技術面資料下載測試失敗: %s", e)
        return False


def test_batch_download():
    """測試批量下載功能"""
    logger.info("=== 測試批量下載功能 ===")
    
    try:
        system = DataIntegrationSystem()
        
        # 定義批量下載任務
        tasks = [
            {
                "category": "technical",
                "data_type": "odd_lot_trading",
                "symbols": ["2330.TW"],
                "check_existing_data": True,
                "show_progress": False
            },
            {
                "category": "technical", 
                "data_type": "benchmark_index",
                "symbols": ["^TWII"],
                "check_existing_data": True,
                "show_progress": False
            },
            {
                "category": "technical",
                "data_type": "adjusted_price",
                "symbols": ["2317.TW"],
                "check_existing_data": True,
                "show_progress": False
            }
        ]
        
        logger.info("開始批量下載 %d 個任務...", len(tasks))
        results = system.batch_download(tasks, max_workers=2)
        
        # 統計結果
        successful_tasks = sum(1 for r in results if r.get('status') == 'success')
        failed_tasks = sum(1 for r in results if r.get('status') == 'failed')
        
        logger.info("✅ 批量下載完成")
        logger.info("成功任務: %d, 失敗任務: %d", successful_tasks, failed_tasks)
        
        # 顯示詳細結果
        for i, result in enumerate(results, 1):
            status = result.get('status', 'unknown')
            task_info = result.get('task', {})
            logger.info("任務 %d (%s): %s", i, task_info.get('data_type', 'unknown'), status)
            
            if status == 'failed':
                logger.warning("失敗原因: %s", result.get('error', 'unknown'))
        
        return successful_tasks > 0
        
    except Exception as e:
        logger.error("❌ 批量下載測試失敗: %s", e)
        return False


def test_backward_compatibility():
    """測試向後相容性"""
    logger.info("=== 測試向後相容性 ===")
    
    try:
        system = DataIntegrationSystem()
        
        # 測試原有 TWSE 下載器功能
        logger.info("測試 TWSE 下載器向後相容性...")
        
        end_date = date.today()
        start_date = end_date - timedelta(days=7)
        
        result = system.download_data(
            category="twse",
            data_type="stock_prices",  # 這個參數在 TWSE 下載器中會被忽略
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            symbols=["2330.TW"],
            check_existing_data=True,
            show_progress=False
        )
        
        logger.info("✅ TWSE 下載器相容性測試通過")
        logger.info("結果: %s", result)
        
        # 測試直接使用原有下載器
        logger.info("測試直接使用原有下載器...")
        
        config = DownloadConfig(
            request_delay=1.0,
            max_retries=2,
            enable_resume=False
        )
        
        original_downloader = TWSEDataDownloader(config)
        original_result = original_downloader.download_all_stocks(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            symbols=["2330.TW"],
            check_existing_data=True,
            show_progress=False
        )
        
        logger.info("✅ 原有下載器直接使用測試通過")
        logger.info("原有下載器結果: %s", original_result)
        
        return True
        
    except Exception as e:
        logger.error("❌ 向後相容性測試失敗: %s", e)
        return False


def test_error_handling():
    """測試錯誤處理"""
    logger.info("=== 測試錯誤處理 ===")
    
    try:
        system = DataIntegrationSystem()
        
        # 測試不支援的資料分類
        logger.info("測試不支援的資料分類...")
        try:
            system.download_data(
                category="unsupported_category",
                data_type="test_type"
            )
            logger.error("❌ 應該拋出錯誤但沒有")
            return False
        except ValueError as e:
            logger.info("✅ 正確捕獲不支援分類錯誤: %s", e)
        
        # 測試不支援的資料類型
        logger.info("測試不支援的資料類型...")
        try:
            system.download_data(
                category="technical",
                data_type="unsupported_data_type"
            )
            logger.error("❌ 應該拋出錯誤但沒有")
            return False
        except Exception as e:
            logger.info("✅ 正確捕獲不支援資料類型錯誤: %s", e)
        
        # 測試無效日期範圍
        logger.info("測試無效日期範圍...")
        try:
            system.download_data(
                category="technical",
                data_type="odd_lot_trading",
                start_date="2024-12-31",
                end_date="2024-01-01"  # 結束日期早於開始日期
            )
            logger.error("❌ 應該拋出錯誤但沒有")
            return False
        except Exception as e:
            logger.info("✅ 正確捕獲無效日期範圍錯誤: %s", e)
        
        return True
        
    except Exception as e:
        logger.error("❌ 錯誤處理測試失敗: %s", e)
        return False


def test_system_monitoring():
    """測試系統監控功能"""
    logger.info("=== 測試系統監控功能 ===")
    
    try:
        system = DataIntegrationSystem()
        
        # 測試系統狀態獲取
        logger.info("測試系統狀態獲取...")
        status = system.get_system_status()
        
        required_keys = ['status', 'config', 'available_downloaders', 'source_manager']
        for key in required_keys:
            if key not in status:
                logger.error("❌ 系統狀態缺少必要欄位: %s", key)
                return False
        
        logger.info("✅ 系統狀態獲取正常")
        logger.info("系統啟動時間: %s", status['status']['system_start_time'])
        logger.info("可用下載器數量: %d", len(status['available_downloaders']))
        
        # 測試支援資料類型獲取
        logger.info("測試支援資料類型獲取...")
        supported_types = system.get_supported_data_types()
        
        if not supported_types:
            logger.error("❌ 沒有獲取到支援的資料類型")
            return False
        
        logger.info("✅ 支援資料類型獲取正常")
        for category, types in supported_types.items():
            logger.info("分類 %s: %d 種資料類型", category, len(types))
        
        return True
        
    except Exception as e:
        logger.error("❌ 系統監控測試失敗: %s", e)
        return False


def test_individual_downloaders():
    """測試個別下載器功能"""
    logger.info("=== 測試個別下載器功能 ===")
    
    try:
        # 測試技術面下載器
        logger.info("測試技術面下載器...")
        
        config = DownloadConfig(
            request_delay=1.0,
            max_retries=2,
            enable_resume=False
        )
        
        technical_downloader = TechnicalDataDownloader(config)
        
        # 檢查下載器基本資訊
        category = technical_downloader.get_data_category()
        supported_types = technical_downloader.get_supported_data_types()
        
        logger.info("✅ 技術面下載器初始化成功")
        logger.info("資料分類: %s", category.value)
        logger.info("支援資料類型: %s", list(supported_types.keys()))
        
        # 測試參數驗證
        logger.info("測試參數驗證...")
        try:
            start_date, end_date, symbols = technical_downloader.validate_data_type_params(
                "odd_lot_trading",
                start_date="2024-01-01",
                end_date="2024-01-31",
                symbols=["2330.TW"]
            )
            logger.info("✅ 參數驗證通過")
            logger.info("標準化日期範圍: %s 到 %s", start_date, end_date)
            logger.info("驗證後股票數量: %d", len(symbols))
            
        except Exception as e:
            logger.error("❌ 參數驗證失敗: %s", e)
            return False
        
        return True
        
    except Exception as e:
        logger.error("❌ 個別下載器測試失敗: %s", e)
        return False


def main():
    """主函數"""
    logger.info("開始台股資料整合系統測試")
    
    # 確保日誌目錄存在
    Path("logs").mkdir(exist_ok=True)
    
    test_results = []
    
    # 執行各項測試
    test_results.append(("系統初始化測試", test_system_initialization()))
    test_results.append(("個別下載器測試", test_individual_downloaders()))
    test_results.append(("技術面資料下載測試", test_technical_data_download()))
    test_results.append(("批量下載測試", test_batch_download()))
    test_results.append(("向後相容性測試", test_backward_compatibility()))
    test_results.append(("錯誤處理測試", test_error_handling()))
    test_results.append(("系統監控測試", test_system_monitoring()))
    
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
        logger.info("🎉 所有測試通過！台股資料整合系統功能正常")
        return 0
    else:
        logger.error("⚠️ 部分測試失敗，請檢查日誌")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
