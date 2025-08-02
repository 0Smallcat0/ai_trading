#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
初始化真實股票數據庫
創建 real_stock_database.db 和必要的表結構
"""

import sqlite3
import os
import logging
from pathlib import Path

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_real_stock_database():
    """創建真實股票數據庫和表結構"""
    
    # 確保 data 目錄存在
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    db_path = data_dir / "real_stock_database.db"
    
    try:
        # 連接數據庫（如果不存在會自動創建）
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 創建 real_stock_data 表
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS real_stock_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            date DATE NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume BIGINT,
            source TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(symbol, date, source)
        )
        """
        
        cursor.execute(create_table_sql)
        
        # 創建索引以提高查詢性能
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_symbol ON real_stock_data(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_date ON real_stock_data(date)",
            "CREATE INDEX IF NOT EXISTS idx_symbol_date ON real_stock_data(symbol, date)",
            "CREATE INDEX IF NOT EXISTS idx_source ON real_stock_data(source)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        # 提交更改
        conn.commit()
        
        logger.info(f"✅ 成功創建數據庫: {db_path}")
        logger.info("✅ 成功創建 real_stock_data 表和索引")
        
        # 驗證表結構
        cursor.execute("PRAGMA table_info(real_stock_data)")
        columns = cursor.fetchall()
        logger.info(f"表結構: {[col[1] for col in columns]}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ 創建數據庫失敗: {e}")
        return False

def insert_sample_data():
    """插入一些示例數據用於測試"""
    db_path = Path("data") / "real_stock_database.db"
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 插入示例數據
        sample_data = [
            ('2330.TW', '2024-01-15', 580.0, 585.0, 575.0, 582.0, 25000000, 'TWSE'),
            ('2317.TW', '2024-01-15', 120.0, 122.0, 118.0, 121.0, 15000000, 'TWSE'),
            ('2454.TW', '2024-01-15', 95.0, 97.0, 94.0, 96.0, 8000000, 'TWSE'),
        ]
        
        insert_sql = """
        INSERT OR IGNORE INTO real_stock_data 
        (symbol, date, open, high, low, close, volume, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        cursor.executemany(insert_sql, sample_data)
        conn.commit()
        
        # 檢查插入的數據
        cursor.execute("SELECT COUNT(*) FROM real_stock_data")
        count = cursor.fetchone()[0]
        logger.info(f"✅ 插入示例數據，總記錄數: {count}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ 插入示例數據失敗: {e}")
        return False

if __name__ == "__main__":
    print("🚀 初始化真實股票數據庫...")
    
    # 創建數據庫和表
    if create_real_stock_database():
        print("✅ 數據庫創建成功")
        
        # 插入示例數據
        if insert_sample_data():
            print("✅ 示例數據插入成功")
        else:
            print("❌ 示例數據插入失敗")
    else:
        print("❌ 數據庫創建失敗")
    
    print("🎉 初始化完成")
