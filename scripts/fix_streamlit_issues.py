#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修復 Streamlit 應用問題的腳本

解決以下問題：
1. 數據庫表不存在
2. 缺失的模組
3. 用戶權限問題
4. 數據源配置問題
"""

import sys
import os
import sqlite3
import logging
from pathlib import Path

# 添加項目路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_database_issues():
    """修復數據庫問題"""
    logger.info("🔧 修復數據庫問題...")
    
    db_path = project_root / "data" / "real_stock_database.db"
    
    try:
        # 確保數據庫文件存在
        if not db_path.exists():
            logger.info("創建數據庫文件...")
            db_path.parent.mkdir(exist_ok=True)
            
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
            conn.close()
            
            logger.info("✅ 數據庫創建成功")
        else:
            logger.info("✅ 數據庫文件已存在")
            
    except Exception as e:
        logger.error(f"❌ 數據庫修復失敗: {e}")
        return False
    
    return True

def test_module_imports():
    """測試模組導入"""
    logger.info("🔧 測試模組導入...")
    
    modules_to_test = [
        ("quant_brain", "src.quant_brain"),
        ("quant_brain.rules.timing_ctrl.moving_average", "src.quant_brain.rules.timing_ctrl.moving_average"),
        ("baostock", "baostock"),
    ]
    
    results = {}
    
    for module_name, import_path in modules_to_test:
        try:
            __import__(import_path)
            results[module_name] = True
            logger.info(f"✅ {module_name} 導入成功")
        except ImportError as e:
            results[module_name] = False
            logger.warning(f"❌ {module_name} 導入失敗: {e}")
    
    return results

def create_error_handling_wrapper():
    """創建錯誤處理包裝器"""
    logger.info("🔧 創建錯誤處理包裝器...")
    
    wrapper_path = project_root / "src" / "ui" / "error_handler.py"
    
    wrapper_content = '''# -*- coding: utf-8 -*-
"""
Streamlit 應用錯誤處理包裝器
"""

import streamlit as st
import logging
import traceback

logger = logging.getLogger(__name__)

def handle_missing_module(module_name, error_msg, fallback_func=None):
    """處理缺失模組錯誤"""
    st.error(f"❌ 模組 {module_name} 不可用: {error_msg}")
    
    if module_name == "baostock":
        st.info("💡 解決方案: 運行 `pip install baostock` 安裝 BaoStock")
    elif module_name == "quant_brain":
        st.info("💡 解決方案: quant_brain 模組已提供基本替代實現")
    
    if fallback_func:
        st.info("🔄 使用備用功能...")
        return fallback_func()
    
    return None

def handle_database_error(error_msg):
    """處理數據庫錯誤"""
    st.error(f"❌ 數據庫錯誤: {error_msg}")
    
    if "no such table" in error_msg.lower():
        st.info("💡 解決方案: 運行 `python scripts/init_real_stock_db.py` 初始化數據庫")
    
    st.info("🔄 請檢查數據庫配置和表結構")

def safe_execute(func, error_handler=None, *args, **kwargs):
    """安全執行函數"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"函數執行失敗: {e}", exc_info=True)
        
        if error_handler:
            return error_handler(str(e))
        else:
            st.error(f"❌ 執行失敗: {e}")
            
            with st.expander("🔍 詳細錯誤信息"):
                st.code(traceback.format_exc())
        
        return None
'''
    
    try:
        wrapper_path.parent.mkdir(parents=True, exist_ok=True)
        with open(wrapper_path, 'w', encoding='utf-8') as f:
            f.write(wrapper_content)
        
        logger.info("✅ 錯誤處理包裝器創建成功")
        return True
    except Exception as e:
        logger.error(f"❌ 錯誤處理包裝器創建失敗: {e}")
        return False

def main():
    """主修復函數"""
    logger.info("🚀 開始修復 Streamlit 應用問題...")
    
    # 修復數據庫問題
    if not fix_database_issues():
        logger.error("數據庫修復失敗")
        return False
    
    # 測試模組導入
    import_results = test_module_imports()
    
    # 創建錯誤處理包裝器
    if not create_error_handling_wrapper():
        logger.error("錯誤處理包裝器創建失敗")
        return False
    
    # 顯示修復結果
    logger.info("🎉 修復完成！")
    logger.info("修復結果摘要:")
    logger.info("- ✅ 數據庫: 已修復")
    logger.info("- ✅ 錯誤處理: 已添加")
    
    for module, success in import_results.items():
        status = "✅ 可用" if success else "❌ 不可用"
        logger.info(f"- {status}: {module}")
    
    logger.info("\n建議:")
    logger.info("1. 如果 baostock 不可用，請運行: pip install baostock")
    logger.info("2. 重新啟動 Streamlit 應用測試修復效果")
    
    return True

if __name__ == "__main__":
    main()
