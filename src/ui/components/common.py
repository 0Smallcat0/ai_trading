"""
通用 UI 組件庫

此模組提供可重用的 Streamlit UI 組件，確保整個應用程式的一致性和可維護性。
包含卡片、指標、狀態指示器、載入動畫等通用組件。
"""

from typing import Any, Dict, List, Optional, Union

import streamlit as st


class UIComponents:
    """通用 UI 組件類"""

    @staticmethod
    def status_card(
        title: str,
        value: Union[str, int, float],
        status: str = "normal",
        description: Optional[str] = None,
        icon: Optional[str] = None,
        trend: Optional[Dict[str, Any]] = None,
    ):
        """
        顯示狀態卡片

        Args:
            title: 卡片標題
            value: 主要數值
            status: 狀態 ("normal", "warning", "error", "success")
            description: 描述文字
            icon: 圖示 emoji
            trend: 趨勢資訊 {"direction": "up/down", "value": float, "period": str}
        """
        # 狀態顏色映射
        status_colors = {
            "normal": "#1f77b4",
            "success": "#2ca02c",
            "warning": "#ff7f0e",
            "error": "#d62728",
        }

        color = status_colors.get(status, "#1f77b4")

        # 建立卡片 HTML
        card_html = f"""
        <div style="
            background: white;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid {color};
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        ">
            <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                {f'<span style="font-size: 1.2rem; margin-right: 0.5rem;">{icon}</span>' if icon else ''}
                <h4 style="margin: 0; color: #333; font-size: 0.9rem; font-weight: 600;">
                    {title}
                </h4>
            </div>
            <div style="font-size: 1.8rem; font-weight: bold; color: {color}; margin-bottom: 0.5rem;">
                {value}
            </div>
            {f'<div style="font-size: 0.8rem; color: #666;">{description}</div>' if description else ''}
            {_format_trend(trend) if trend else ''}
        </div>
        """

        st.markdown(card_html, unsafe_allow_html=True)

    @staticmethod
    def metric_grid(metrics: List[Dict[str, Any]], columns: int = 4):
        """
        顯示指標網格

        Args:
            metrics: 指標列表，每個指標包含 title, value, status 等
            columns: 每行顯示的列數
        """
        cols = st.columns(columns)

        for i, metric in enumerate(metrics):
            with cols[i % columns]:
                UIComponents.status_card(**metric)

    @staticmethod
    def progress_indicator(
        current: int,
        total: int,
        title: str = "進度",
        show_percentage: bool = True,
        color: str = "#1f77b4",
    ):
        """
        顯示進度指示器

        Args:
            current: 當前進度
            total: 總數
            title: 標題
            show_percentage: 是否顯示百分比
            color: 進度條顏色
        """
        percentage = (current / total) * 100 if total > 0 else 0

        progress_html = f"""
        <div style="margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                <span style="font-weight: 600; color: #333;">{title}</span>
                {f'<span style="color: #666;">{current}/{total} ({percentage:.1f}%)</span>' if show_percentage else ''}
            </div>
            <div style="
                background: #f0f0f0;
                border-radius: 10px;
                height: 8px;
                overflow: hidden;
            ">
                <div style="
                    background: {color};
                    height: 100%;
                    width: {percentage}%;
                    transition: width 0.3s ease;
                "></div>
            </div>
        </div>
        """

        st.markdown(progress_html, unsafe_allow_html=True)

    @staticmethod
    def alert_box(
        message: str,
        alert_type: str = "info",
        title: Optional[str] = None,
        dismissible: bool = False,
    ):
        """
        顯示警告框

        Args:
            message: 警告訊息
            alert_type: 警告類型 ("info", "success", "warning", "error")
            title: 警告標題
            dismissible: 是否可關閉
        """
        # 警告類型配置
        alert_configs = {
            "info": {"color": "#0ea5e9", "bg": "#e0f2fe", "icon": "ℹ️"},
            "success": {"color": "#10b981", "bg": "#d1fae5", "icon": "✅"},
            "warning": {"color": "#f59e0b", "bg": "#fef3c7", "icon": "⚠️"},
            "error": {"color": "#ef4444", "bg": "#fee2e2", "icon": "❌"},
        }

        config = alert_configs.get(alert_type, alert_configs["info"])

        alert_html = f"""
        <div style="
            background: {config['bg']};
            border: 1px solid {config['color']};
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 1rem;
            display: flex;
            align-items: flex-start;
        ">
            <span style="font-size: 1.2rem; margin-right: 0.5rem;">{config['icon']}</span>
            <div style="flex: 1;">
                {f'<div style="font-weight: 600; color: {config["color"]}; margin-bottom: 0.25rem;">{title}</div>' if title else ''}
                <div style="color: #374151;">{message}</div>
            </div>
            {f'<button style="background: none; border: none; font-size: 1.2rem; cursor: pointer; color: {config["color"]};">×</button>' if dismissible else ''}
        </div>
        """

        st.markdown(alert_html, unsafe_allow_html=True)

    @staticmethod
    def loading_spinner(text: str = "載入中...", size: str = "medium"):
        """
        顯示載入動畫

        Args:
            text: 載入文字
            size: 大小 ("small", "medium", "large")
        """
        sizes = {
            "small": "20px",
            "medium": "40px",
            "large": "60px",
        }

        spinner_size = sizes.get(size, "40px")

        spinner_html = f"""
        <div style="
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 2rem;
        ">
            <div style="
                width: {spinner_size};
                height: {spinner_size};
                border: 3px solid #f3f3f3;
                border-top: 3px solid #1f77b4;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            "></div>
            <div style="margin-top: 1rem; color: #666; font-size: 0.9rem;">
                {text}
            </div>
        </div>
        <style>
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        </style>
        """

        st.markdown(spinner_html, unsafe_allow_html=True)

    @staticmethod
    def data_table_with_actions(
        data: List[Dict[str, Any]],
        columns: List[str],
        actions: Optional[List[Dict[str, Any]]] = None,
        key: str = "table",
    ):
        """
        顯示帶操作按鈕的資料表格

        Args:
            data: 資料列表
            columns: 要顯示的欄位
            actions: 操作按鈕配置
            key: 組件唯一鍵
        """
        if not data:
            st.info("暫無資料")
            return

        # 建立表格
        for i, row in enumerate(data):
            cols = st.columns(len(columns) + (1 if actions else 0))

            # 顯示資料欄位
            for j, col in enumerate(columns):
                with cols[j]:
                    st.write(row.get(col, ""))

            # 顯示操作按鈕
            if actions:
                with cols[-1]:
                    for action in actions:
                        if st.button(
                            action["label"],
                            key=f"{key}_{action['name']}_{i}",
                            help=action.get("help", ""),
                        ):
                            if "callback" in action:
                                action["callback"](row)

    @staticmethod
    def sidebar_navigation(
        pages: List[Dict[str, str]],
        current_page: str,
        key: str = "nav",
    ) -> str:
        """
        側邊欄導航

        Args:
            pages: 頁面列表 [{"name": "頁面名稱", "icon": "🏠", "key": "home"}]
            current_page: 當前頁面
            key: 組件唯一鍵

        Returns:
            str: 選中的頁面鍵
        """
        st.sidebar.markdown("### 📊 系統導航")

        selected_page = current_page

        for page in pages:
            is_current = page["key"] == current_page

            # 建立按鈕樣式
            button_style = (
                """
            background: #1f77b4;
            color: white;
            border: none;
            border-radius: 0.25rem;
            """
                if is_current
                else """
            background: transparent;
            color: #333;
            border: 1px solid #ddd;
            border-radius: 0.25rem;
            """
            )

            if st.sidebar.button(
                f"{page.get('icon', '')} {page['name']}",
                key=f"{key}_{page['key']}",
                help=page.get("description", ""),
                use_container_width=True,
            ):
                selected_page = page["key"]

        return selected_page


def _format_trend(trend: Dict[str, Any]) -> str:
    """格式化趨勢資訊"""
    if not trend:
        return ""

    direction = trend.get("direction", "")
    value = trend.get("value", 0)
    period = trend.get("period", "")

    # 趨勢圖示和顏色
    if direction == "up":
        icon = "📈"
        color = "#10b981"
        sign = "+"
    elif direction == "down":
        icon = "📉"
        color = "#ef4444"
        sign = ""
    else:
        icon = "➡️"
        color = "#6b7280"
        sign = ""

    return f"""
    <div style="
        display: flex;
        align-items: center;
        font-size: 0.8rem;
        color: {color};
        margin-top: 0.5rem;
    ">
        <span style="margin-right: 0.25rem;">{icon}</span>
        <span>{sign}{value}% {period}</span>
    </div>
    """


# 全域樣式
def apply_custom_css():
    """應用自定義 CSS 樣式"""
    st.markdown(
        """
    <style>
    /* 主要容器樣式 */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* 側邊欄樣式 */
    .sidebar .sidebar-content {
        background: #f8f9fa;
    }

    /* 按鈕樣式 */
    .stButton > button {
        border-radius: 0.25rem;
        border: 1px solid #ddd;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        border-color: #1f77b4;
        color: #1f77b4;
    }

    /* 指標樣式 */
    .metric-container {
        background: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* 表格樣式 */
    .dataframe {
        border: none !important;
    }

    .dataframe th {
        background: #f8f9fa !important;
        border: none !important;
    }

    /* 隱藏 Streamlit 預設元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
        unsafe_allow_html=True,
    )
