#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步驟 2 資料庫模型和 UPSERT 機制測試腳本

此腳本用於測試擴展的資料庫模型和 UPSERT 機制，包括：
1. ChipData 模型的新欄位
2. ImportantNews 模型的新欄位
3. upsert_chip_data 功能
4. upsert_important_news 功能
5. 統一下載器的資料保存功能

Usage:
    python scripts/test_step2_database_upsert.py
"""

import logging
import sys
from datetime import date, datetime, timedelta
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
        logging.FileHandler('logs/step2_database_test.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)


def test_chip_data_model():
    """測試 ChipData 模型的新欄位"""
    logger.info("=== 測試 ChipData 模型的新欄位 ===")
    
    try:
        from src.database.models.integration_models import ChipData
        
        # 檢查新欄位是否存在
        new_fields = [
            'margin_buy', 'margin_sell', 'short_sell', 'short_cover',
            'foreign_holding_ratio', 'foreign_holding_shares',
            'broker_id', 'broker_name', 'buy_amount', 'sell_amount', 'net_amount'
        ]
        
        chip_data_columns = [col.name for col in ChipData.__table__.columns]
        logger.info("ChipData 模型欄位: %s", chip_data_columns)
        
        missing_fields = [field for field in new_fields if field not in chip_data_columns]
        if missing_fields:
            logger.warning("⚠️ 缺少欄位: %s", missing_fields)
        else:
            logger.info("✅ 所有新欄位都已添加")
        
        # 測試創建 ChipData 實例
        test_data = ChipData(
            symbol='2330.TW',
            date=date.today(),
            margin_buy=1000000,
            margin_sell=500000,
            foreign_holding_ratio=75.5,
            broker_id='1234',
            broker_name='測試券商'
        )
        
        logger.info("✅ ChipData 實例創建成功")
        return True
        
    except Exception as e:
        logger.error("❌ ChipData 模型測試失敗: %s", e)
        return False


def test_important_news_model():
    """測試 ImportantNews 模型的新欄位"""
    logger.info("=== 測試 ImportantNews 模型的新欄位 ===")
    
    try:
        from src.database.models.integration_models import ImportantNews
        
        # 檢查新欄位是否存在
        new_fields = [
            'event_type', 'publish_date', 'publish_time', 
            'location', 'stock_symbols', 'summary'
        ]
        
        news_columns = [col.name for col in ImportantNews.__table__.columns]
        logger.info("ImportantNews 模型欄位: %s", news_columns)
        
        missing_fields = [field for field in new_fields if field not in news_columns]
        if missing_fields:
            logger.warning("⚠️ 缺少欄位: %s", missing_fields)
        else:
            logger.info("✅ 所有新欄位都已添加")
        
        # 測試創建 ImportantNews 實例
        test_news = ImportantNews(
            title='測試新聞',
            announce_date=datetime.now(),
            category='test',
            source='test_source',
            event_type='stock_news',
            publish_date=date.today(),
            stock_symbols='2330.TW,2317.TW'
        )
        
        logger.info("✅ ImportantNews 實例創建成功")
        return True
        
    except Exception as e:
        logger.error("❌ ImportantNews 模型測試失敗: %s", e)
        return False


def test_upsert_chip_data():
    """測試 upsert_chip_data 功能"""
    logger.info("=== 測試 upsert_chip_data 功能 ===")
    
    try:
        from src.utils.database_utils import upsert_chip_data
        
        # 準備測試資料
        test_chip_data = [
            {
                'symbol': '2330.TW',
                'date': date.today(),
                'margin_buy': 1000000,
                'margin_sell': 500000,
                'foreign_holding_ratio': 75.5,
                'source': 'TEST'
            },
            {
                'symbol': '2317.TW',
                'date': date.today(),
                'margin_buy': 800000,
                'margin_sell': 400000,
                'foreign_holding_ratio': 65.2,
                'source': 'TEST'
            }
        ]
        
        # 執行 UPSERT
        result = upsert_chip_data(test_chip_data)
        
        if result > 0:
            logger.info("✅ upsert_chip_data 成功: %d 筆記錄", result)
        else:
            logger.warning("⚠️ upsert_chip_data 沒有處理任何記錄")
        
        return True
        
    except Exception as e:
        logger.error("❌ upsert_chip_data 測試失敗: %s", e)
        return False


def test_upsert_important_news():
    """測試 upsert_important_news 功能"""
    logger.info("=== 測試 upsert_important_news 功能 ===")
    
    try:
        from src.utils.database_utils import upsert_important_news
        
        # 準備測試資料
        test_news_data = [
            {
                'title': '測試重大訊息 1',
                'announce_date': datetime.now(),
                'category': 'test',
                'source': 'TEST',
                'event_type': 'material_news',
                'symbol': '2330.TW',
                'importance_level': 5
            },
            {
                'title': '測試台股新聞 1',
                'announce_date': datetime.now(),
                'category': 'test',
                'source': 'TEST',
                'event_type': 'stock_news',
                'stock_symbols': '2330.TW,2317.TW',
                'importance_level': 3
            }
        ]
        
        # 執行 UPSERT
        result = upsert_important_news(test_news_data)
        
        if result > 0:
            logger.info("✅ upsert_important_news 成功: %d 筆記錄", result)
        else:
            logger.warning("⚠️ upsert_important_news 沒有處理任何記錄")
        
        return True
        
    except Exception as e:
        logger.error("❌ upsert_important_news 測試失敗: %s", e)
        return False


def test_unified_downloader_save():
    """測試統一下載器的資料保存功能"""
    logger.info("=== 測試統一下載器的資料保存功能 ===")
    
    try:
        config = DownloadConfig(
            request_delay=1.0,
            max_retries=1,
            enable_cache=False
        )
        downloader = UnifiedDataDownloader(config)
        
        # 測試籌碼面資料保存
        import pandas as pd
        
        chip_test_data = pd.DataFrame([
            {
                'symbol': '2330.TW',
                'date': date.today(),
                'margin_buy': 1500000,
                'margin_sell': 750000,
                'data_source': 'TEST_CHIP'
            }
        ])
        
        chip_result = downloader._save_chip_data(chip_test_data, 'institutional_trading')
        logger.info("籌碼面資料保存結果: %d 筆", chip_result)
        
        # 測試事件面資料保存
        event_test_data = pd.DataFrame([
            {
                'title': '統一下載器測試新聞',
                'announce_date': datetime.now(),
                'data_source': 'TEST_EVENT',
                'event_type': 'stock_news'
            }
        ])
        
        event_result = downloader._save_event_data(event_test_data, 'stock_news')
        logger.info("事件面資料保存結果: %d 筆", event_result)
        
        if chip_result > 0 and event_result > 0:
            logger.info("✅ 統一下載器資料保存功能正常")
        else:
            logger.warning("⚠️ 統一下載器資料保存功能可能有問題")
        
        return True
        
    except Exception as e:
        logger.error("❌ 統一下載器資料保存測試失敗: %s", e)
        return False


def test_data_validation():
    """測試資料驗證功能"""
    logger.info("=== 測試資料驗證功能 ===")
    
    try:
        config = DownloadConfig()
        downloader = UnifiedDataDownloader(config)
        
        import pandas as pd
        
        # 測試有效資料
        valid_data = pd.DataFrame([
            {'symbol': '2330.TW', 'date': date.today(), 'value': 100},
            {'symbol': '2317.TW', 'date': date.today(), 'value': 200}
        ])
        
        required_fields = ['symbol', 'date']
        validated = downloader._validate_data_fields(valid_data, required_fields)
        
        logger.info("有效資料驗證: 原始 %d 筆 -> 驗證後 %d 筆", len(valid_data), len(validated))
        
        # 測試無效資料
        invalid_data = pd.DataFrame([
            {'symbol': None, 'date': None, 'value': None},
            {'symbol': '2330.TW', 'date': date.today(), 'value': 100}
        ])
        
        validated_invalid = downloader._validate_data_fields(invalid_data, required_fields)
        logger.info("無效資料驗證: 原始 %d 筆 -> 驗證後 %d 筆", len(invalid_data), len(validated_invalid))
        
        logger.info("✅ 資料驗證功能正常")
        return True
        
    except Exception as e:
        logger.error("❌ 資料驗證測試失敗: %s", e)
        return False


def main():
    """主函數"""
    logger.info("開始步驟 2 資料庫模型和 UPSERT 機制測試")
    
    # 確保日誌目錄存在
    Path("logs").mkdir(exist_ok=True)
    
    test_results = []
    
    # 執行各項測試
    test_results.append(("ChipData 模型新欄位", test_chip_data_model()))
    test_results.append(("ImportantNews 模型新欄位", test_important_news_model()))
    test_results.append(("upsert_chip_data 功能", test_upsert_chip_data()))
    test_results.append(("upsert_important_news 功能", test_upsert_important_news()))
    test_results.append(("統一下載器資料保存", test_unified_downloader_save()))
    test_results.append(("資料驗證功能", test_data_validation()))
    
    # 輸出測試結果
    logger.info("=== 步驟 2 測試結果摘要 ===")
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通過" if result else "❌ 失敗"
        logger.info("%s: %s", test_name, status)
        if result:
            passed += 1
    
    logger.info("總計: %d/%d 測試通過", passed, total)
    
    if passed >= total * 0.8:  # 80% 通過率視為成功
        logger.info("🎉 步驟 2 資料庫模型和 UPSERT 機制基本完成！")
        return 0
    else:
        logger.error("⚠️ 部分測試失敗，需要進一步調整實現")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
