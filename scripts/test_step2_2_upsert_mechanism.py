#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步驟 2.2 UPSERT 機制測試腳本

此腳本用於測試增強的 UPSERT 機制，包括：
1. PostgreSQL ON CONFLICT DO UPDATE 語法測試
2. 通用 UPSERT 邏輯測試
3. 批量 UPSERT 效能測試
4. 錯誤處理和回滾測試

Usage:
    python scripts/test_step2_2_upsert_mechanism.py
"""

import sys
import os
import logging
from datetime import date, datetime, timedelta
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
        logging.FileHandler('logs/test_step2_2_upsert_mechanism.log')
    ]
)
logger = logging.getLogger(__name__)

# 確保日誌目錄存在
os.makedirs('logs', exist_ok=True)

def test_chip_data_upsert_basic():
    """測試籌碼面資料基本 UPSERT 功能"""
    logger.info("=== 測試籌碼面資料基本 UPSERT 功能 ===")
    
    try:
        from src.utils.database_utils import upsert_chip_data
        
        # 準備測試資料
        test_data = [
            {
                'symbol': '2330.TW',
                'date': date.today(),
                'foreign_buy': 1000000,
                'foreign_sell': 800000,
                'investment_trust_buy': 500000,
                'investment_trust_sell': 300000,
                'dealer_buy': 200000,
                'dealer_sell': 150000,
                'margin_buy': 100000,
                'margin_sell': 80000,
                'short_sell': 50000,
                'short_cover': 30000,
                'foreign_holding_ratio': 75.5,
                'source': 'TEST_BASIC'
            },
            {
                'symbol': '2317.TW',
                'date': date.today(),
                'foreign_buy': 800000,
                'foreign_sell': 600000,
                'margin_buy': 80000,
                'margin_sell': 60000,
                'foreign_holding_ratio': 65.2,
                'source': 'TEST_BASIC'
            }
        ]
        
        # 執行 UPSERT
        start_time = time.time()
        result = upsert_chip_data(test_data)
        end_time = time.time()
        
        if result > 0:
            logger.info("✅ 基本 UPSERT 成功: %d 筆記錄，耗時: %.3f 秒", result, end_time - start_time)
            return True
        else:
            logger.error("❌ 基本 UPSERT 失敗: 沒有處理任何記錄")
            return False
        
    except Exception as e:
        logger.error("❌ 基本 UPSERT 測試失敗: %s", e)
        return False


def test_chip_data_upsert_update():
    """測試籌碼面資料更新功能"""
    logger.info("=== 測試籌碼面資料更新功能 ===")
    
    try:
        from src.utils.database_utils import upsert_chip_data
        
        # 準備更新資料（相同的 symbol 和 date）
        update_data = [
            {
                'symbol': '2330.TW',
                'date': date.today(),
                'foreign_buy': 1200000,  # 更新值
                'foreign_sell': 900000,  # 更新值
                'investment_trust_buy': 600000,  # 更新值
                'margin_buy': 120000,  # 更新值
                'foreign_holding_ratio': 76.8,  # 更新值
                'source': 'TEST_UPDATE'
            }
        ]
        
        # 執行更新 UPSERT
        start_time = time.time()
        result = upsert_chip_data(update_data)
        end_time = time.time()
        
        if result > 0:
            logger.info("✅ 更新 UPSERT 成功: %d 筆記錄，耗時: %.3f 秒", result, end_time - start_time)
            return True
        else:
            logger.error("❌ 更新 UPSERT 失敗: 沒有處理任何記錄")
            return False
        
    except Exception as e:
        logger.error("❌ 更新 UPSERT 測試失敗: %s", e)
        return False


def test_important_news_upsert_basic():
    """測試重要新聞基本 UPSERT 功能"""
    logger.info("=== 測試重要新聞基本 UPSERT 功能 ===")
    
    try:
        from src.utils.database_utils import upsert_important_news
        
        # 準備測試資料
        test_data = [
            {
                'title': '台積電發布第三季財報',
                'announce_date': datetime.now(),
                'category': 'financial',
                'source': 'TEST_NEWS',
                'event_type': 'material_news',
                'symbol': '2330.TW',
                'importance_level': 5,
                'content': '台積電公布第三季營收創新高...',
                'stock_symbols': '2330.TW'
            },
            {
                'title': '鴻海法說會預告',
                'announce_date': datetime.now(),
                'category': 'corporate_event',
                'source': 'TEST_NEWS',
                'event_type': 'investor_conference',
                'symbol': '2317.TW',
                'importance_level': 4,
                'location': '台北國際會議中心',
                'stock_symbols': '2317.TW'
            }
        ]
        
        # 執行 UPSERT
        start_time = time.time()
        result = upsert_important_news(test_data)
        end_time = time.time()
        
        if result > 0:
            logger.info("✅ 新聞基本 UPSERT 成功: %d 筆記錄，耗時: %.3f 秒", result, end_time - start_time)
            return True
        else:
            logger.error("❌ 新聞基本 UPSERT 失敗: 沒有處理任何記錄")
            return False
        
    except Exception as e:
        logger.error("❌ 新聞基本 UPSERT 測試失敗: %s", e)
        return False


def test_important_news_upsert_update():
    """測試重要新聞更新功能"""
    logger.info("=== 測試重要新聞更新功能 ===")
    
    try:
        from src.utils.database_utils import upsert_important_news
        
        # 準備更新資料（相同的 title, announce_date, source）
        update_data = [
            {
                'title': '台積電發布第三季財報',
                'announce_date': datetime.now(),
                'category': 'financial',
                'source': 'TEST_NEWS',
                'event_type': 'material_news',
                'symbol': '2330.TW',
                'importance_level': 5,
                'content': '台積電公布第三季營收創新高，EPS 達到歷史新高...',  # 更新內容
                'summary': '台積電Q3財報亮眼',  # 新增摘要
                'is_processed': True  # 更新處理狀態
            }
        ]
        
        # 執行更新 UPSERT
        start_time = time.time()
        result = upsert_important_news(update_data)
        end_time = time.time()
        
        if result > 0:
            logger.info("✅ 新聞更新 UPSERT 成功: %d 筆記錄，耗時: %.3f 秒", result, end_time - start_time)
            return True
        else:
            logger.error("❌ 新聞更新 UPSERT 失敗: 沒有處理任何記錄")
            return False
        
    except Exception as e:
        logger.error("❌ 新聞更新 UPSERT 測試失敗: %s", e)
        return False


def test_batch_upsert_performance():
    """測試批量 UPSERT 效能"""
    logger.info("=== 測試批量 UPSERT 效能 ===")
    
    try:
        from src.utils.database_utils import upsert_chip_data, upsert_important_news
        
        # 準備大批量籌碼面資料
        chip_batch_data = []
        for i in range(100):  # 100 筆記錄
            chip_batch_data.append({
                'symbol': f'TEST{i:04d}.TW',
                'date': date.today() - timedelta(days=i % 30),
                'foreign_buy': 1000000 + i * 1000,
                'foreign_sell': 800000 + i * 800,
                'margin_buy': 100000 + i * 100,
                'foreign_holding_ratio': 50.0 + (i % 50),
                'source': 'TEST_BATCH'
            })
        
        # 測試籌碼面批量 UPSERT
        start_time = time.time()
        chip_result = upsert_chip_data(chip_batch_data)
        chip_time = time.time() - start_time
        
        # 準備大批量新聞資料
        news_batch_data = []
        for i in range(50):  # 50 筆記錄
            news_batch_data.append({
                'title': f'測試新聞標題 {i}',
                'announce_date': datetime.now() - timedelta(hours=i),
                'category': 'test',
                'source': 'TEST_BATCH',
                'event_type': 'stock_news',
                'importance_level': (i % 5) + 1,
                'content': f'測試新聞內容 {i}...'
            })
        
        # 測試新聞批量 UPSERT
        start_time = time.time()
        news_result = upsert_important_news(news_batch_data)
        news_time = time.time() - start_time
        
        logger.info("✅ 批量 UPSERT 效能測試完成:")
        logger.info("  籌碼面資料: %d 筆，耗時: %.3f 秒，平均: %.3f 秒/筆", 
                   chip_result, chip_time, chip_time / chip_result if chip_result > 0 else 0)
        logger.info("  新聞資料: %d 筆，耗時: %.3f 秒，平均: %.3f 秒/筆", 
                   news_result, news_time, news_time / news_result if news_result > 0 else 0)
        
        return chip_result > 0 and news_result > 0
        
    except Exception as e:
        logger.error("❌ 批量 UPSERT 效能測試失敗: %s", e)
        return False


def test_error_handling():
    """測試錯誤處理機制"""
    logger.info("=== 測試錯誤處理機制 ===")
    
    try:
        from src.utils.database_utils import upsert_chip_data, upsert_important_news
        
        # 測試空資料列表
        empty_result = upsert_chip_data([])
        if empty_result == 0:
            logger.info("✅ 空資料列表處理正確")
        else:
            logger.error("❌ 空資料列表處理錯誤")
            return False
        
        # 測試無效資料
        invalid_data = [
            {
                'symbol': '2330.TW',
                # 缺少必要的 date 欄位
                'foreign_buy': 1000000
            }
        ]
        
        try:
            invalid_result = upsert_chip_data(invalid_data)
            logger.info("⚠️ 無效資料處理: %d 筆記錄", invalid_result)
        except Exception as e:
            logger.info("✅ 無效資料正確拋出異常: %s", type(e).__name__)
        
        return True
        
    except Exception as e:
        logger.error("❌ 錯誤處理測試失敗: %s", e)
        return False


def main():
    """主測試函數"""
    logger.info("開始執行步驟 2.2 UPSERT 機制測試")
    
    test_results = []
    
    # 執行各項測試
    test_functions = [
        ("籌碼面資料基本 UPSERT", test_chip_data_upsert_basic),
        ("籌碼面資料更新 UPSERT", test_chip_data_upsert_update),
        ("重要新聞基本 UPSERT", test_important_news_upsert_basic),
        ("重要新聞更新 UPSERT", test_important_news_upsert_update),
        ("批量 UPSERT 效能", test_batch_upsert_performance),
        ("錯誤處理機制", test_error_handling)
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
        status = "通過" if result else "失敗"
        logger.info("  %s: %s", test_name, status)
        if result:
            passed += 1
    
    logger.info("\n總計: %d/%d 測試通過 (%.1f%%)", passed, total, (passed/total)*100)
    
    if passed == total:
        logger.info("所有測試都通過！步驟 2.2 UPSERT 機制實現成功")
        return True
    else:
        logger.warning("部分測試失敗，需要進一步檢查和修正")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
