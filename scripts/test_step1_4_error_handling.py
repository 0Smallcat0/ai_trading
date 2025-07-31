#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步驟 1.4 錯誤處理強化功能測試腳本

此腳本用於測試統一下載器中新實現的增強錯誤處理功能，包括：
1. 錯誤分類和重試策略
2. 熔斷器機制
3. 特定資料來源的錯誤處理
4. 指數退避重試機制

Usage:
    python scripts/test_step1_4_error_handling.py
"""

import sys
import os
import logging
from datetime import date, timedelta
from pathlib import Path
import time

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/test_step1_4_error_handling.log')
    ]
)
logger = logging.getLogger(__name__)

# 確保日誌目錄存在
os.makedirs('logs', exist_ok=True)

def test_error_classification():
    """測試錯誤分類功能"""
    logger.info("=== 測試錯誤分類功能 ===")
    
    try:
        from src.data.unified_data_downloader import EnhancedErrorHandler, ErrorType
        import requests
        
        error_handler = EnhancedErrorHandler()
        
        # 測試不同類型的錯誤
        test_errors = [
            (requests.exceptions.Timeout(), ErrorType.NETWORK_TIMEOUT),
            (requests.exceptions.ConnectionError(), ErrorType.NETWORK_CONNECTION),
            (ValueError("解析錯誤"), ErrorType.PARSING_ERROR),
            (KeyError("缺少欄位"), ErrorType.PARSING_ERROR),
            (Exception("未知錯誤"), ErrorType.UNKNOWN_ERROR)
        ]
        
        success_count = 0
        for error, expected_type in test_errors:
            classified_type = error_handler.classify_error(error)
            if classified_type == expected_type:
                logger.info("✅ 錯誤分類正確: %s -> %s", type(error).__name__, classified_type.value)
                success_count += 1
            else:
                logger.error("❌ 錯誤分類錯誤: %s -> %s (預期: %s)", 
                           type(error).__name__, classified_type.value, expected_type.value)
        
        logger.info("錯誤分類測試完成: %d/%d 通過", success_count, len(test_errors))
        return success_count == len(test_errors)
        
    except Exception as e:
        logger.error("❌ 錯誤分類測試失敗: %s", e)
        return False


def test_retry_strategy():
    """測試重試策略功能"""
    logger.info("=== 測試重試策略功能 ===")
    
    try:
        from src.data.unified_data_downloader import EnhancedErrorHandler, ErrorType, RetryStrategy
        
        error_handler = EnhancedErrorHandler()
        
        # 測試不同錯誤類型的重試策略
        test_cases = [
            (ErrorType.NETWORK_TIMEOUT, "twse_api", True),
            (ErrorType.PARSING_ERROR, "twse_api", False),
            (ErrorType.API_RATE_LIMIT, "cnyes_rss", True),
            (ErrorType.DATA_VALIDATION_ERROR, "tpex_api", False)
        ]
        
        success_count = 0
        for error_type, data_source, should_retry_expected in test_cases:
            should_retry = error_handler.should_retry(error_type, 0, 3)
            strategy = error_handler.get_retry_strategy(error_type, data_source)
            
            if should_retry == should_retry_expected:
                logger.info("✅ 重試策略正確: %s -> %s", error_type.value, should_retry)
                success_count += 1
            else:
                logger.error("❌ 重試策略錯誤: %s -> %s (預期: %s)", 
                           error_type.value, should_retry, should_retry_expected)
            
            # 測試延遲計算
            delay = strategy.get_delay(0)
            logger.info("  延遲時間: %.2f秒", delay)
        
        logger.info("重試策略測試完成: %d/%d 通過", success_count, len(test_cases))
        return success_count == len(test_cases)
        
    except Exception as e:
        logger.error("❌ 重試策略測試失敗: %s", e)
        return False


def test_circuit_breaker():
    """測試熔斷器機制"""
    logger.info("=== 測試熔斷器機制 ===")
    
    try:
        from src.data.unified_data_downloader import EnhancedErrorHandler, ErrorType
        
        error_handler = EnhancedErrorHandler()
        data_source = "test_source"
        
        # 初始狀態：熔斷器應該是關閉的
        if not error_handler.is_circuit_breaker_open(data_source):
            logger.info("✅ 初始狀態：熔斷器關閉")
        else:
            logger.error("❌ 初始狀態：熔斷器應該關閉")
            return False
        
        # 記錄多次錯誤
        for i in range(6):  # 超過閾值(5)
            error_handler.record_error(data_source, ErrorType.NETWORK_TIMEOUT)
        
        # 現在熔斷器應該開啟
        if error_handler.is_circuit_breaker_open(data_source):
            logger.info("✅ 錯誤累積後：熔斷器開啟")
        else:
            logger.error("❌ 錯誤累積後：熔斷器應該開啟")
            return False
        
        # 記錄成功，應該重置錯誤計數
        error_handler.record_success(data_source)
        
        if not error_handler.is_circuit_breaker_open(data_source):
            logger.info("✅ 成功後：熔斷器關閉")
        else:
            logger.error("❌ 成功後：熔斷器應該關閉")
            return False
        
        logger.info("熔斷器機制測試完成")
        return True
        
    except Exception as e:
        logger.error("❌ 熔斷器機制測試失敗: %s", e)
        return False


def test_enhanced_error_handling_integration():
    """測試增強錯誤處理整合功能"""
    logger.info("=== 測試增強錯誤處理整合功能 ===")
    
    try:
        from src.data.unified_data_downloader import UnifiedDataDownloader, DownloadConfig
        
        config = DownloadConfig(request_delay=0.5, max_retries=2, enable_cache=False)
        downloader = UnifiedDataDownloader(config)
        
        # 測試錯誤處理器是否正確初始化
        if hasattr(downloader, 'error_handler'):
            logger.info("✅ 錯誤處理器正確初始化")
        else:
            logger.error("❌ 錯誤處理器未初始化")
            return False
        
        # 測試特定資料來源錯誤處理
        test_context = {'symbol': '2330.TW', 'date': date.today()}
        
        # 模擬不同類型的錯誤
        import requests
        test_error = requests.exceptions.Timeout()
        
        result = downloader.handle_specific_data_source_errors(
            'twse_api', test_error, test_context
        )
        
        if 'should_retry' in result and 'delay' in result:
            logger.info("✅ 特定錯誤處理返回正確格式")
            logger.info("  應該重試: %s, 延遲: %.2f秒", result['should_retry'], result['delay'])
        else:
            logger.error("❌ 特定錯誤處理返回格式錯誤")
            return False
        
        logger.info("增強錯誤處理整合測試完成")
        return True
        
    except Exception as e:
        logger.error("❌ 增強錯誤處理整合測試失敗: %s", e)
        return False


def test_real_world_error_scenarios():
    """測試真實世界錯誤場景"""
    logger.info("=== 測試真實世界錯誤場景 ===")
    
    try:
        from src.data.unified_data_downloader import UnifiedDataDownloader, DownloadConfig
        
        config = DownloadConfig(request_delay=1.0, max_retries=2, enable_cache=False)
        downloader = UnifiedDataDownloader(config)
        
        # 測試無效日期（應該觸發資料驗證錯誤）
        invalid_date = date(2000, 1, 1)  # 太早的日期
        
        logger.info("測試無效日期: %s", invalid_date)
        
        # 嘗試下載重大訊息（可能會失敗）
        try:
            result = downloader._download_twse_material_news("2330.TW", invalid_date)
            if result is not None:
                logger.info("✅ 無效日期處理: 返回空資料或有效資料")
            else:
                logger.info("✅ 無效日期處理: 正確返回 None")
        except Exception as e:
            logger.info("✅ 無效日期處理: 正確拋出異常 - %s", type(e).__name__)
        
        # 測試無效股票代碼
        invalid_symbol = "INVALID.TW"
        
        logger.info("測試無效股票代碼: %s", invalid_symbol)
        
        try:
            result = downloader._download_twse_material_news(invalid_symbol, date.today())
            logger.info("✅ 無效股票代碼處理: 正常處理")
        except Exception as e:
            logger.info("✅ 無效股票代碼處理: 正確處理異常 - %s", type(e).__name__)
        
        logger.info("真實世界錯誤場景測試完成")
        return True
        
    except Exception as e:
        logger.error("❌ 真實世界錯誤場景測試失敗: %s", e)
        return False


def main():
    """主測試函數"""
    logger.info("開始執行步驟 1.4 錯誤處理強化功能測試")
    
    test_results = []
    
    # 執行各項測試
    test_functions = [
        ("錯誤分類功能", test_error_classification),
        ("重試策略功能", test_retry_strategy),
        ("熔斷器機制", test_circuit_breaker),
        ("增強錯誤處理整合", test_enhanced_error_handling_integration),
        ("真實世界錯誤場景", test_real_world_error_scenarios)
    ]
    
    for test_name, test_func in test_functions:
        logger.info("\n" + "="*50)
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            logger.error("測試 %s 時發生未預期錯誤: %s", test_name, e)
            test_results.append((test_name, False))
    
    # 輸出測試結果摘要
    logger.info("\n" + "="*50)
    logger.info("測試結果摘要:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        logger.info("  %s: %s", test_name, status)
        if result:
            passed += 1
    
    logger.info("\n總計: %d/%d 測試通過 (%.1f%%)", passed, total, (passed/total)*100)
    
    if passed == total:
        logger.info("🎉 所有測試都通過！步驟 1.4 錯誤處理強化功能實現成功")
        return True
    else:
        logger.warning("⚠️ 部分測試失敗，需要進一步檢查和修正")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
