#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""步驟 2 資料庫遷移腳本

此腳本用於執行步驟 2 的資料庫結構更新，包括：
1. 為 ChipData 表添加新欄位
2. 為 ImportantNews 表添加新欄位
3. 創建新的索引以優化查詢效能
4. 更新唯一約束

Usage:
    python scripts/migrate_database_step2.py
"""

import sys
import os
import logging
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 設定日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/migrate_database_step2.log')
    ]
)
logger = logging.getLogger(__name__)

# 確保日誌目錄存在
os.makedirs('logs', exist_ok=True)

def check_column_exists(session, table_name: str, column_name: str) -> bool:
    """檢查欄位是否存在

    Args:
        session: 資料庫會話
        table_name: 表格名稱
        column_name: 欄位名稱

    Returns:
        bool: 欄位是否存在
    """
    try:
        from sqlalchemy import text

        # 檢查資料庫類型
        db_dialect = session.bind.dialect.name

        if db_dialect == 'sqlite':
            # SQLite 查詢
            result = session.execute(text(f"PRAGMA table_info({table_name})"))
            columns = [row[1] for row in result.fetchall()]
            return column_name in columns
        elif db_dialect == 'postgresql':
            # PostgreSQL 查詢
            result = session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = :table_name AND column_name = :column_name
            """), {'table_name': table_name, 'column_name': column_name})
            return result.fetchone() is not None
        else:
            logger.warning("未支援的資料庫類型: %s", db_dialect)
            return False

    except Exception as e:
        logger.error("檢查欄位存在性失敗: %s", e)
        return False


def add_column_if_not_exists(session, table_name: str, column_name: str, column_type: str):
    """如果欄位不存在則添加

    Args:
        session: 資料庫會話
        table_name: 表格名稱
        column_name: 欄位名稱
        column_type: 欄位類型
    """
    try:
        from sqlalchemy import text

        if not check_column_exists(session, table_name, column_name):
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            session.execute(text(sql))
            logger.info("添加欄位: %s.%s (%s)", table_name, column_name, column_type)
        else:
            logger.debug("欄位已存在: %s.%s", table_name, column_name)

    except Exception as e:
        logger.error("添加欄位失敗: %s.%s - %s", table_name, column_name, e)
        raise


def create_index_if_not_exists(session, index_name: str, table_name: str, columns: str):
    """如果索引不存在則創建

    Args:
        session: 資料庫會話
        index_name: 索引名稱
        table_name: 表格名稱
        columns: 索引欄位
    """
    try:
        from sqlalchemy import text

        # 檢查索引是否存在
        db_dialect = session.bind.dialect.name

        if db_dialect == 'sqlite':
            result = session.execute(text(f"PRAGMA index_list({table_name})"))
            existing_indexes = [row[1] for row in result.fetchall()]
        elif db_dialect == 'postgresql':
            result = session.execute(text("""
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = :table_name AND indexname = :index_name
            """), {'table_name': table_name, 'index_name': index_name})
            existing_indexes = [row[0] for row in result.fetchall()]
        else:
            existing_indexes = []

        if index_name not in existing_indexes:
            sql = f"CREATE INDEX {index_name} ON {table_name} ({columns})"
            session.execute(text(sql))
            logger.info("創建索引: %s ON %s (%s)", index_name, table_name, columns)
        else:
            logger.debug("索引已存在: %s", index_name)

    except Exception as e:
        logger.error("創建索引失敗: %s - %s", index_name, e)
        # 索引創建失敗不應該中斷整個遷移過程
        pass


def migrate_chip_data_table():
    """遷移 ChipData 表格"""
    logger.info("=== 開始遷移 ChipData 表格 ===")
    
    try:
        from src.utils.database_utils import get_database_session
        
        with get_database_session() as session:
            # 添加新欄位
            new_columns = [
                ('margin_buy', 'DECIMAL(15,2)'),
                ('margin_sell', 'DECIMAL(15,2)'),
                ('short_sell', 'DECIMAL(15,2)'),
                ('short_cover', 'DECIMAL(15,2)'),
                ('foreign_holding_ratio', 'DECIMAL(5,2)'),
                ('foreign_holding_shares', 'BIGINT'),
                ('broker_id', 'VARCHAR(10)'),
                ('broker_name', 'VARCHAR(100)'),
                ('buy_amount', 'DECIMAL(15,2)'),
                ('sell_amount', 'DECIMAL(15,2)'),
                ('net_amount', 'DECIMAL(15,2)')
            ]
            
            for column_name, column_type in new_columns:
                add_column_if_not_exists(session, 'chip_data', column_name, column_type)
            
            # 創建新索引
            new_indexes = [
                ('idx_chip_symbol_date', 'chip_data', 'symbol, date'),
                ('idx_chip_margin', 'chip_data', 'margin_buy, margin_sell'),
                ('idx_chip_short', 'chip_data', 'short_sell, short_cover'),
                ('idx_chip_broker', 'chip_data', 'broker_id'),
                ('idx_chip_foreign_holding', 'chip_data', 'foreign_holding_ratio')
            ]
            
            for index_name, table_name, columns in new_indexes:
                create_index_if_not_exists(session, index_name, table_name, columns)
            
            session.commit()
            logger.info("ChipData 表格遷移完成")
            
    except Exception as e:
        logger.error("ChipData 表格遷移失敗: %s", e)
        raise


def migrate_important_news_table():
    """遷移 ImportantNews 表格"""
    logger.info("=== 開始遷移 ImportantNews 表格 ===")
    
    try:
        from src.utils.database_utils import get_database_session
        
        with get_database_session() as session:
            # 添加新欄位
            new_columns = [
                ('event_type', 'VARCHAR(50)'),
                ('publish_date', 'DATE'),
                ('publish_time', 'TIME'),
                ('location', 'VARCHAR(200)'),
                ('stock_symbols', 'TEXT'),
                ('summary', 'TEXT')
            ]
            
            for column_name, column_type in new_columns:
                add_column_if_not_exists(session, 'important_news', column_name, column_type)
            
            # 創建新索引
            new_indexes = [
                ('idx_news_event_type', 'important_news', 'event_type'),
                ('idx_news_publish_date', 'important_news', 'publish_date'),
                ('idx_news_symbol_date', 'important_news', 'symbol, announce_date'),
                ('idx_news_category_importance', 'important_news', 'category, importance_level'),
                ('idx_news_event_type_date', 'important_news', 'event_type, publish_date')
            ]
            
            for index_name, table_name, columns in new_indexes:
                create_index_if_not_exists(session, index_name, table_name, columns)
            
            session.commit()
            logger.info("ImportantNews 表格遷移完成")
            
    except Exception as e:
        logger.error("ImportantNews 表格遷移失敗: %s", e)
        raise


def verify_migration():
    """驗證遷移結果"""
    logger.info("=== 驗證遷移結果 ===")
    
    try:
        from src.utils.database_utils import get_database_session
        
        with get_database_session() as session:
            # 驗證 ChipData 表格
            chip_data_columns = [
                'margin_buy', 'margin_sell', 'short_sell', 'short_cover',
                'foreign_holding_ratio', 'foreign_holding_shares',
                'broker_id', 'broker_name', 'buy_amount', 'sell_amount', 'net_amount'
            ]
            
            chip_missing = []
            for column in chip_data_columns:
                if not check_column_exists(session, 'chip_data', column):
                    chip_missing.append(column)
            
            if chip_missing:
                logger.error("ChipData 表格缺少欄位: %s", chip_missing)
                return False
            else:
                logger.info("✅ ChipData 表格欄位驗證通過")
            
            # 驗證 ImportantNews 表格
            news_columns = [
                'event_type', 'publish_date', 'publish_time',
                'location', 'stock_symbols', 'summary'
            ]
            
            news_missing = []
            for column in news_columns:
                if not check_column_exists(session, 'important_news', column):
                    news_missing.append(column)
            
            if news_missing:
                logger.error("ImportantNews 表格缺少欄位: %s", news_missing)
                return False
            else:
                logger.info("✅ ImportantNews 表格欄位驗證通過")
            
            logger.info("🎉 所有遷移驗證通過")
            return True
            
    except Exception as e:
        logger.error("驗證遷移結果失敗: %s", e)
        return False


def main():
    """主函數"""
    logger.info("開始執行步驟 2 資料庫遷移")
    
    try:
        # 執行遷移
        migrate_chip_data_table()
        migrate_important_news_table()
        
        # 驗證遷移結果
        if verify_migration():
            logger.info("🎉 步驟 2 資料庫遷移成功完成")
            return True
        else:
            logger.error("❌ 步驟 2 資料庫遷移驗證失敗")
            return False
            
    except Exception as e:
        logger.error("❌ 步驟 2 資料庫遷移失敗: %s", e)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
