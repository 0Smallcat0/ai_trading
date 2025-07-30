#!/usr/bin/env python3
"""
安全的session state包裝器
確保所有session state訪問都是安全的
"""

import streamlit as st

def safe_get_session_state(key, default_value=None):
    """安全獲取session state值"""
    if key not in st.session_state:
        st.session_state[key] = default_value
    return st.session_state[key]

def safe_set_session_state(key, value):
    """安全設置session state值"""
    st.session_state[key] = value

def initialize_all_session_states():
    """初始化所有必要的session state變數"""
    defaults = {
        'stock_search_results': [],
        'selected_stocks': [],
        'recent_selections': [],
        'batch_progress': None,
        'batch_running': False,
        'current_stock_data': None,
        'last_update_time': None,
        'search_query': '',
        'selected_market': '全部',
        'selected_industry': '全部'
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# 自動初始化
initialize_all_session_states()
