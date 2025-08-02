"""
Fallback implementation for src/ui/components/common.py
This file has been replaced by src/ui/components/layout.py
"""

import streamlit as st
import logging

logger = logging.getLogger(__name__)

def show():
    """Fallback show function"""
    st.warning("⚠️ 此功能已遷移到中文版本組件")
    st.info(f"請使用: src/ui/components/layout.py")
    logger.warning(f"使用了已棄用的模組: src/ui/components/common.py")

# 提供常見的fallback函數
def create_enhanced_candlestick_chart(*args, **kwargs):
    """Fallback for chart functions"""
    st.warning("⚠️ 圖表功能已遷移，請使用中文版本組件")
    return None

def generate_sample_stock_data(*args, **kwargs):
    """Fallback for data functions"""
    st.warning("⚠️ 數據功能已遷移，請使用中文版本組件")
    return None

# 其他常見的fallback
BacktestReports = None
UIComponents = None
ChartTheme = None
