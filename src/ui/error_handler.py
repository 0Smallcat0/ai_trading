# -*- coding: utf-8 -*-
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
