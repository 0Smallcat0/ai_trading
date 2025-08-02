#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
風險管理資料庫 Schema 修正腳本

修正 risk_parameters 和 risk_control_status 表格缺少的欄位問題。
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
        
        # SQLite 查詢表格結構
        result = session.execute(text(f"PRAGMA table_info({table_name})"))
        columns = [row[1] for row in result.fetchall()]  # row[1] 是欄位名稱
        return column_name in columns
        
    except Exception as e:
        logger.error("檢查欄位失敗: %s.%s - %s", table_name, column_name, e)
        return False


def add_column_if_not_exists(session, table_name: str, column_name: str, column_type: str, default_value: str = None):
    """如果欄位不存在則添加
    
    Args:
        session: 資料庫會話
        table_name: 表格名稱
        column_name: 欄位名稱
        column_type: 欄位類型
        default_value: 預設值
    """
    try:
        from sqlalchemy import text
        
        if not check_column_exists(session, table_name, column_name):
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            if default_value:
                sql += f" DEFAULT {default_value}"
            
            session.execute(text(sql))
            logger.info("添加欄位: %s.%s (%s)", table_name, column_name, column_type)
        else:
            logger.debug("欄位已存在: %s.%s", table_name, column_name)
            
    except Exception as e:
        logger.error("添加欄位失敗: %s.%s - %s", table_name, column_name, e)
        raise


def fix_risk_parameters_table():
    """修正 risk_parameters 表格"""
    logger.info("=== 開始修正 risk_parameters 表格 ===")
    
    try:
        from src.utils.database_utils import get_database_session
        
        with get_database_session() as session:
            # 檢查表格是否存在
            from sqlalchemy import text
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='risk_parameters'"))
            if not result.fetchone():
                logger.info("risk_parameters 表格不存在，創建表格...")
                create_risk_parameters_table(session)
                return
            
            # 添加缺少的欄位
            missing_columns = [
                ('parameter_type', 'TEXT', "'string'"),
                ('category', 'TEXT', "'general'"),
                ('description', 'TEXT', "''"),
                ('is_system', 'INTEGER', '0'),
                ('is_active', 'INTEGER', '1'),
                ('min_value', 'TEXT', 'NULL'),
                ('max_value', 'TEXT', 'NULL'),
                ('default_value', 'TEXT', 'NULL'),
                ('updated_at', 'TIMESTAMP', 'NULL'),
                ('created_at', 'TIMESTAMP', 'CURRENT_TIMESTAMP')
            ]
            
            for column_name, column_type, default_value in missing_columns:
                add_column_if_not_exists(session, 'risk_parameters', column_name, column_type, default_value)
            
            session.commit()
            logger.info("✅ risk_parameters 表格修正完成")
            
    except Exception as e:
        logger.error("❌ risk_parameters 表格修正失敗: %s", e)
        raise


def fix_risk_control_status_table():
    """修正 risk_control_status 表格"""
    logger.info("=== 開始修正 risk_control_status 表格 ===")
    
    try:
        from src.utils.database_utils import get_database_session
        
        with get_database_session() as session:
            # 檢查表格是否存在
            from sqlalchemy import text
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='risk_control_status'"))
            if not result.fetchone():
                logger.info("risk_control_status 表格不存在，創建表格...")
                create_risk_control_status_table(session)
                return
            
            # 添加缺少的欄位
            missing_columns = [
                ('control_type', 'TEXT', "'general'"),
                ('is_enabled', 'INTEGER', '1'),
                ('is_master_enabled', 'INTEGER', '1'),
                ('emergency_stop', 'INTEGER', '0'),
                ('status_name', 'TEXT', 'NULL'),
                ('is_active', 'INTEGER', '1'),
                ('last_triggered', 'TIMESTAMP', 'NULL'),
                ('trigger_count', 'INTEGER', '0'),
                ('description', 'TEXT', "''"),
                ('created_at', 'TIMESTAMP', 'CURRENT_TIMESTAMP'),
                ('updated_at', 'TIMESTAMP', 'NULL')
            ]
            
            for column_name, column_type, default_value in missing_columns:
                add_column_if_not_exists(session, 'risk_control_status', column_name, column_type, default_value)
            
            session.commit()
            logger.info("✅ risk_control_status 表格修正完成")
            
    except Exception as e:
        logger.error("❌ risk_control_status 表格修正失敗: %s", e)
        raise


def create_risk_parameters_table(session):
    """創建 risk_parameters 表格"""
    from sqlalchemy import text
    
    create_sql = """
    CREATE TABLE IF NOT EXISTS risk_parameters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parameter_name TEXT NOT NULL UNIQUE,
        parameter_value TEXT NOT NULL,
        parameter_type TEXT DEFAULT 'string',
        category TEXT DEFAULT 'general',
        description TEXT DEFAULT '',
        is_system INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        min_value TEXT,
        max_value TEXT,
        default_value TEXT,
        updated_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    
    session.execute(text(create_sql))
    logger.info("創建 risk_parameters 表格")


def create_risk_control_status_table(session):
    """創建 risk_control_status 表格"""
    from sqlalchemy import text
    
    create_sql = """
    CREATE TABLE IF NOT EXISTS risk_control_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        control_name TEXT NOT NULL UNIQUE,
        control_type TEXT DEFAULT 'general',
        is_enabled INTEGER DEFAULT 1,
        is_master_enabled INTEGER DEFAULT 1,
        emergency_stop INTEGER DEFAULT 0,
        status_name TEXT,
        is_active INTEGER DEFAULT 1,
        last_triggered TIMESTAMP,
        trigger_count INTEGER DEFAULT 0,
        description TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP
    )
    """
    
    session.execute(text(create_sql))
    logger.info("創建 risk_control_status 表格")


def verify_schema_fix():
    """驗證 Schema 修正結果"""
    logger.info("=== 驗證 Schema 修正結果 ===")
    
    try:
        from src.utils.database_utils import get_database_session
        
        with get_database_session() as session:
            # 驗證 risk_parameters 表格
            required_risk_params_columns = [
                'parameter_name', 'parameter_value', 'parameter_type', 'category',
                'description', 'is_system', 'is_active', 'min_value', 'max_value',
                'default_value', 'updated_at', 'created_at'
            ]
            
            missing_risk_params = []
            for column in required_risk_params_columns:
                if not check_column_exists(session, 'risk_parameters', column):
                    missing_risk_params.append(column)
            
            if missing_risk_params:
                logger.error("risk_parameters 表格仍缺少欄位: %s", missing_risk_params)
                return False
            else:
                logger.info("✅ risk_parameters 表格欄位驗證通過")
            
            # 驗證 risk_control_status 表格
            required_risk_control_columns = [
                'control_name', 'control_type', 'is_enabled', 'is_master_enabled',
                'emergency_stop', 'status_name', 'is_active', 'last_triggered',
                'trigger_count', 'description', 'created_at', 'updated_at'
            ]
            
            missing_risk_control = []
            for column in required_risk_control_columns:
                if not check_column_exists(session, 'risk_control_status', column):
                    missing_risk_control.append(column)
            
            if missing_risk_control:
                logger.error("risk_control_status 表格仍缺少欄位: %s", missing_risk_control)
                return False
            else:
                logger.info("✅ risk_control_status 表格欄位驗證通過")
            
            logger.info("🎉 所有風險管理表格 Schema 修正驗證通過")
            return True
            
    except Exception as e:
        logger.error("驗證 Schema 修正結果失敗: %s", e)
        return False


def fix_database_file(db_path: str):
    """修正指定的資料庫檔案"""
    logger.info(f"=== 修正資料庫檔案: {db_path} ===")

    if not os.path.exists(db_path):
        logger.info(f"資料庫檔案不存在，跳過: {db_path}")
        return True

    # 臨時修改環境變數以使用指定的資料庫
    original_db_url = os.environ.get('DB_URL')
    try:
        os.environ['DB_URL'] = f"sqlite:///{db_path}"

        # 修正表格
        fix_risk_parameters_table()
        fix_risk_control_status_table()

        # 驗證修正結果
        if verify_schema_fix():
            logger.info(f"✅ 資料庫檔案 {db_path} 修正成功")
            return True
        else:
            logger.error(f"❌ 資料庫檔案 {db_path} 修正驗證失敗")
            return False

    except Exception as e:
        logger.error(f"❌ 修正資料庫檔案 {db_path} 失敗: %s", e)
        return False
    finally:
        # 恢復原始環境變數
        if original_db_url:
            os.environ['DB_URL'] = original_db_url
        elif 'DB_URL' in os.environ:
            del os.environ['DB_URL']


def main():
    """主函數"""
    logger.info("開始執行風險管理資料庫 Schema 修正")

    # 需要修正的資料庫檔案列表
    database_files = [
        "data/market_data.db",
        "data/trading_system.db",
        "trading_system.db"  # 相對路徑版本
    ]

    success_count = 0
    total_count = 0

    try:
        for db_file in database_files:
            total_count += 1
            if fix_database_file(db_file):
                success_count += 1

        if success_count > 0:
            logger.info(f"🎉 成功修正 {success_count}/{total_count} 個資料庫檔案")
            return True
        else:
            logger.error("❌ 沒有成功修正任何資料庫檔案")
            return False

    except Exception as e:
        logger.error("❌ 風險管理資料庫 Schema 修正失敗: %s", e)
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
