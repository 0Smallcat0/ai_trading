#!/usr/bin/env python3
"""
數據管理頁面 - 重定向到中文版本組件

此檔案已被重構，功能已遷移到 src/ui/components/data_management_ui.py
提供向後兼容性支援。

遷移說明：
- 原有功能已整合到中文版本組件中
- 提供更好的用戶體驗和功能
- 保持API兼容性
"""

import streamlit as st
import logging
from typing import Optional, Dict, Any

# Setup logging
logger = logging.getLogger(__name__)

def show() -> None:
    """數據管理頁面主函數 - 重定向到中文版本組件"""
    try:
        # 重定向到中文版本組件
        from src.ui.components.data_management_ui import show as show_data_management_ui
        
        st.info("📢 數據管理功能已遷移到新的中文版本組件")
        st.markdown("---")
        
        # 調用中文版本組件
        show_data_management_ui()
        
    except ImportError as e:
        logger.error(f"無法導入中文版本數據管理組件: {e}")
        st.error("❌ 數據管理功能暫時不可用")
        st.info("請聯繫系統管理員或使用其他數據管理工具")
        
        # 提供基本的錯誤信息
        with st.expander("錯誤詳情"):
            st.code(str(e))
    
    except Exception as e:
        logger.error(f"數據管理頁面發生錯誤: {e}")
        st.error("❌ 數據管理頁面載入失敗")
        
        with st.expander("錯誤詳情"):
            st.code(str(e))

# 向後兼容性函數
def get_core_modules() -> Optional[Dict[str, Any]]:
    """向後兼容性函數 - 重定向到中文版本組件"""
    st.warning("⚠️ 此函數已過時，請使用中文版本組件")
    return None

def get_stock_data_from_db(*args, **kwargs) -> None:
    """向後兼容性函數 - 重定向到中文版本組件"""
    st.warning("⚠️ 此函數已過時，請使用中文版本組件")

def calculate_basic_technical_indicators(*args, **kwargs) -> None:
    """向後兼容性函數 - 重定向到中文版本組件"""
    st.warning("⚠️ 此函數已過時，請使用中文版本組件")

def show_basic_chart(*args, **kwargs) -> None:
    """向後兼容性函數 - 重定向到中文版本組件"""
    st.warning("⚠️ 此函數已過時，請使用中文版本組件")

def show_technical_indicators(*args, **kwargs) -> None:
    """向後兼容性函數 - 重定向到中文版本組件"""
    st.warning("⚠️ 此函數已過時，請使用中文版本組件")

def show_sample_stock_search(*args, **kwargs) -> None:
    """向後兼容性函數 - 重定向到中文版本組件"""
    st.warning("⚠️ 此函數已過時，請使用中文版本組件")

def show_stock_search(*args, **kwargs) -> None:
    """向後兼容性函數 - 重定向到中文版本組件"""
    st.warning("⚠️ 此函數已過時，請使用中文版本組件")

def main() -> None:
    """向後兼容性函數 - 重定向到中文版本組件"""
    show()

if __name__ == "__main__":
    show()
