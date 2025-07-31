"""
UI 輔助工具模組

此模組提供 Streamlit UI 開發的輔助函數和工具。

主要功能：
- 通用 UI 組件
- 數據格式化工具
- 狀態管理輔助
- 樣式和佈局工具

Example:
    >>> from src.utils.ui_helpers import format_currency, create_metric_card
    >>> format_currency(1234.56)  # "$1,234.56"
    >>> create_metric_card("總收益", 1234.56, "success")
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def format_currency(
    amount: Union[int, float], 
    currency: str = "TWD", 
    precision: int = 2
) -> str:
    """格式化貨幣顯示
    
    Args:
        amount: 金額
        currency: 貨幣代碼
        precision: 小數位數
        
    Returns:
        str: 格式化後的貨幣字串
    """
    try:
        if currency == "TWD":
            return f"NT${amount:,.{precision}f}"
        elif currency == "USD":
            return f"${amount:,.{precision}f}"
        else:
            return f"{currency} {amount:,.{precision}f}"
    except (ValueError, TypeError):
        return "N/A"


def format_percentage(value: Union[int, float], precision: int = 2) -> str:
    """格式化百分比顯示
    
    Args:
        value: 數值
        precision: 小數位數
        
    Returns:
        str: 格式化後的百分比字串
    """
    try:
        return f"{value:.{precision}f}%"
    except (ValueError, TypeError):
        return "N/A"


def format_number(value: Union[int, float], precision: int = 2) -> str:
    """格式化數字顯示
    
    Args:
        value: 數值
        precision: 小數位數
        
    Returns:
        str: 格式化後的數字字串
    """
    try:
        return f"{value:,.{precision}f}"
    except (ValueError, TypeError):
        return "N/A"


def create_metric_card(
    title: str,
    value: Union[str, int, float],
    status: str = "normal",
    delta: Optional[Union[str, int, float]] = None,
    help_text: Optional[str] = None
):
    """創建指標卡片
    
    Args:
        title: 標題
        value: 主要數值
        status: 狀態 ("normal", "success", "warning", "error")
        delta: 變化值
        help_text: 幫助文字
    """
    # 狀態顏色映射
    status_colors = {
        "normal": "#1f77b4",
        "success": "#2ca02c", 
        "warning": "#ff7f0e",
        "error": "#d62728"
    }
    
    # 狀態圖示映射
    status_icons = {
        "normal": "📊",
        "success": "✅",
        "warning": "⚠️", 
        "error": "❌"
    }
    
    color = status_colors.get(status, status_colors["normal"])
    icon = status_icons.get(status, status_icons["normal"])
    
    # 格式化數值
    if isinstance(value, (int, float)):
        formatted_value = format_number(value)
    else:
        formatted_value = str(value)
    
    # 格式化變化值
    delta_str = ""
    if delta is not None:
        if isinstance(delta, (int, float)):
            delta_str = f" ({delta:+.2f})"
        else:
            delta_str = f" ({delta})"
    
    # 顯示指標
    st.metric(
        label=f"{icon} {title}",
        value=formatted_value + delta_str,
        help=help_text
    )


def create_status_indicator(
    status: str,
    message: str = "",
    show_icon: bool = True
):
    """創建狀態指示器
    
    Args:
        status: 狀態 ("success", "warning", "error", "info")
        message: 狀態訊息
        show_icon: 是否顯示圖示
    """
    status_config = {
        "success": {"func": st.success, "icon": "✅"},
        "warning": {"func": st.warning, "icon": "⚠️"},
        "error": {"func": st.error, "icon": "❌"},
        "info": {"func": st.info, "icon": "ℹ️"}
    }
    
    config = status_config.get(status, status_config["info"])
    
    if show_icon and message:
        display_message = f"{config['icon']} {message}"
    else:
        display_message = message
    
    config["func"](display_message)


def create_progress_bar(
    progress: float,
    text: str = "",
    show_percentage: bool = True
):
    """創建進度條
    
    Args:
        progress: 進度值 (0.0 - 1.0)
        text: 進度文字
        show_percentage: 是否顯示百分比
    """
    # 確保進度值在有效範圍內
    progress = max(0.0, min(1.0, progress))
    
    if show_percentage:
        percentage_text = f" ({progress:.1%})"
    else:
        percentage_text = ""
    
    if text:
        st.text(f"{text}{percentage_text}")
    
    st.progress(progress)


def create_data_table(
    data: pd.DataFrame,
    title: Optional[str] = None,
    height: Optional[int] = None,
    use_container_width: bool = True
):
    """創建數據表格
    
    Args:
        data: 數據框
        title: 表格標題
        height: 表格高度
        use_container_width: 是否使用容器寬度
    """
    if title:
        st.subheader(title)
    
    st.dataframe(
        data,
        height=height,
        use_container_width=use_container_width
    )


def create_chart_container(
    chart_func: Callable,
    title: Optional[str] = None,
    height: Optional[int] = None,
    **kwargs
):
    """創建圖表容器
    
    Args:
        chart_func: 圖表函數
        title: 圖表標題
        height: 圖表高度
        **kwargs: 傳遞給圖表函數的參數
    """
    if title:
        st.subheader(title)
    
    try:
        chart = chart_func(**kwargs)
        if height:
            st.plotly_chart(chart, use_container_width=True, height=height)
        else:
            st.plotly_chart(chart, use_container_width=True)
    except Exception as e:
        logger.error(f"創建圖表失敗: {e}")
        st.error("圖表載入失敗")


def safe_session_state_get(key: str, default: Any = None) -> Any:
    """安全獲取 session state 值
    
    Args:
        key: 鍵值
        default: 預設值
        
    Returns:
        Any: session state 值或預設值
    """
    return st.session_state.get(key, default)


def safe_session_state_set(key: str, value: Any):
    """安全設置 session state 值
    
    Args:
        key: 鍵值
        value: 值
    """
    try:
        st.session_state[key] = value
    except Exception as e:
        logger.error(f"設置 session state 失敗: {e}")


def initialize_session_state(defaults: Dict[str, Any]):
    """初始化 session state
    
    Args:
        defaults: 預設值字典
    """
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def create_sidebar_section(title: str, content_func: Callable, **kwargs):
    """創建側邊欄區段
    
    Args:
        title: 區段標題
        content_func: 內容函數
        **kwargs: 傳遞給內容函數的參數
    """
    with st.sidebar:
        st.subheader(title)
        try:
            content_func(**kwargs)
        except Exception as e:
            logger.error(f"側邊欄區段 '{title}' 載入失敗: {e}")
            st.error("區段載入失敗")


def create_expandable_section(
    title: str,
    content_func: Callable,
    expanded: bool = False,
    **kwargs
):
    """創建可展開區段
    
    Args:
        title: 區段標題
        content_func: 內容函數
        expanded: 是否預設展開
        **kwargs: 傳遞給內容函數的參數
    """
    with st.expander(title, expanded=expanded):
        try:
            content_func(**kwargs)
        except Exception as e:
            logger.error(f"可展開區段 '{title}' 載入失敗: {e}")
            st.error("區段載入失敗")


def show_loading_spinner(text: str = "載入中..."):
    """顯示載入動畫
    
    Args:
        text: 載入文字
    """
    return st.spinner(text)


def create_alert_box(
    message: str,
    alert_type: str = "info",
    dismissible: bool = False
):
    """創建警告框
    
    Args:
        message: 警告訊息
        alert_type: 警告類型 ("info", "success", "warning", "error")
        dismissible: 是否可關閉
    """
    if dismissible:
        # 使用 session state 來控制顯示狀態
        alert_key = f"alert_{hash(message)}"
        if not st.session_state.get(f"{alert_key}_dismissed", False):
            col1, col2 = st.columns([10, 1])
            with col1:
                create_status_indicator(alert_type, message)
            with col2:
                if st.button("✕", key=f"{alert_key}_close"):
                    st.session_state[f"{alert_key}_dismissed"] = True
                    st.rerun()
    else:
        create_status_indicator(alert_type, message)


# 常用的預設值字典
DEFAULT_SESSION_STATE = {
    'page_loaded': False,
    'user_preferences': {},
    'cache_timestamp': datetime.now(),
    'error_count': 0
}


__all__ = [
    'format_currency',
    'format_percentage', 
    'format_number',
    'create_metric_card',
    'create_status_indicator',
    'create_progress_bar',
    'create_data_table',
    'create_chart_container',
    'safe_session_state_get',
    'safe_session_state_set',
    'initialize_session_state',
    'create_sidebar_section',
    'create_expandable_section',
    'show_loading_spinner',
    'create_alert_box',
    'DEFAULT_SESSION_STATE'
]
