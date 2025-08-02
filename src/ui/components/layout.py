"""
布局和主題系統

此模組提供統一的布局管理和主題系統，確保整個應用程式的視覺一致性。
包含頁面布局、導航系統、主題配置等功能。
"""

from typing import Any, Dict, List, Optional, Callable
import streamlit as st
from datetime import datetime

from .common import UIComponents, apply_custom_css
from ..responsive import (
    responsive_manager,
    ResponsiveComponents,
    apply_responsive_design,
)


class Theme:
    """主題配置類"""

    # 顏色配置
    COLORS = {
        "primary": "#1f77b4",
        "secondary": "#ff7f0e",
        "success": "#2ca02c",
        "warning": "#ff7f0e",
        "error": "#d62728",
        "info": "#17a2b8",
        "light": "#f8f9fa",
        "dark": "#343a40",
        "muted": "#6c757d",
    }

    # 字體配置
    FONTS = {
        "primary": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
        "monospace": "Monaco, Consolas, 'Courier New', monospace",
    }

    # 間距配置
    SPACING = {
        "xs": "0.25rem",
        "sm": "0.5rem",
        "md": "1rem",
        "lg": "1.5rem",
        "xl": "2rem",
        "xxl": "3rem",
    }


class PageLayout:
    """頁面布局管理器"""

    def __init__(self, title: str, icon: str = "📊", wide_mode: bool = True):
        """
        初始化頁面布局

        Args:
            title: 頁面標題
            icon: 頁面圖示
            wide_mode: 是否使用寬屏模式
        """
        self.title = title
        self.icon = icon
        self.wide_mode = wide_mode

        # 設定頁面配置
        if wide_mode:
            st.set_page_config(
                page_title=title,
                page_icon=icon,
                layout="wide",
                initial_sidebar_state="expanded",
            )

        # 應用自定義樣式
        apply_custom_css()

        # 應用響應式設計
        apply_responsive_design()

    def render_header(
        self, subtitle: Optional[str] = None, actions: Optional[List[Dict]] = None
    ):
        """
        渲染頁面標題

        Args:
            subtitle: 副標題
            actions: 操作按鈕列表
        """
        # 建立標題區域
        header_col1, header_col2 = st.columns([3, 1])

        with header_col1:
            st.markdown(f"# {self.icon} {self.title}")
            if subtitle:
                st.markdown(f"*{subtitle}*")

        with header_col2:
            if actions:
                for action in actions:
                    if st.button(
                        action["label"],
                        key=action.get("key", action["label"]),
                        help=action.get("help", ""),
                        type=action.get("type", "secondary"),
                    ):
                        if "callback" in action:
                            action["callback"]()

        st.markdown("---")

    def render_sidebar(self, navigation_config: Optional[Dict] = None):
        """
        渲染側邊欄

        Args:
            navigation_config: 導航配置
        """
        # 修復：移除 st.sidebar，改為主頁面顯示
        with st.expander("🤖 AI 交易系統", expanded=False):
            # 系統標題
            st.markdown("## 🤖 AI 交易系統")
            st.markdown("---")

            # 系統狀態
            self._render_system_status()

            # 導航選單
            if navigation_config:
                self._render_navigation(navigation_config)

            # 用戶資訊
            self._render_user_info()

    def _render_system_status(self):
        """渲染系統狀態"""
        st.markdown("### 📊 系統狀態")

        # 模擬系統狀態
        status_data = {
            "API 服務": {"status": "正常", "color": "success"},
            "資料庫": {"status": "正常", "color": "success"},
            "交易連接": {"status": "正常", "color": "success"},
            "監控系統": {"status": "正常", "color": "success"},
        }

        for service, info in status_data.items():
            color = Theme.COLORS.get(info["color"], Theme.COLORS["muted"])
            st.markdown(
                f'<div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">'
                f"<span>{service}</span>"
                f'<span style="color: {color};">●</span>'
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")

    def _render_navigation(self, config: Dict):
        """渲染導航選單"""
        st.markdown("### 🧭 功能導航")

        pages = config.get("pages", [])
        current_page = st.session_state.get("current_page", "")

        for page in pages:
            is_current = page["key"] == current_page

            if st.button(
                f"{page.get('icon', '📄')} {page['name']}",
                key=f"nav_{page['key']}",
                help=page.get("description", ""),
                use_container_width=True,
                type="primary" if is_current else "secondary",
            ):
                st.session_state.current_page = page["key"]
                if "callback" in page:
                    page["callback"]()
                st.rerun()

        st.markdown("---")

    def _render_user_info(self):
        """渲染用戶資訊"""
        st.markdown("### 👤 用戶資訊")

        # 模擬用戶資訊
        user_info = st.session_state.get(
            "user_info",
            {
                "name": "管理員",
                "role": "系統管理員",
                "last_login": datetime.now().strftime("%Y-%m-%d %H:%M"),
            },
        )

        st.markdown(f"**用戶**: {user_info['name']}")
        st.markdown(f"**角色**: {user_info['role']}")
        st.markdown(f"**登入時間**: {user_info['last_login']}")

        if st.button("🚪 登出", use_container_width=True):
            # 清除會話狀態
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


class DashboardLayout:
    """儀表板布局管理器"""

    @staticmethod
    def render_metrics_row(metrics: List[Dict[str, Any]], columns: int = 4):
        """
        渲染指標行

        Args:
            metrics: 指標資料列表
            columns: 列數
        """
        cols = st.columns(columns)

        for i, metric in enumerate(metrics):
            with cols[i % columns]:
                UIComponents.status_card(**metric)

    @staticmethod
    def render_chart_grid(charts: List[Dict[str, Any]], columns: int = 2):
        """
        渲染圖表網格

        Args:
            charts: 圖表配置列表
            columns: 列數
        """
        cols = st.columns(columns)

        for i, chart in enumerate(charts):
            with cols[i % columns]:
                st.markdown(f"### {chart['title']}")

                if chart["type"] == "plotly":
                    st.plotly_chart(chart["figure"], use_container_width=True)
                elif chart["type"] == "dataframe":
                    st.dataframe(chart["data"], use_container_width=True)
                elif chart["type"] == "metric":
                    st.metric(chart["label"], chart["value"], chart.get("delta", None))

    @staticmethod
    def render_tabs_layout(tabs_config: List[Dict[str, Any]]):
        """
        渲染標籤頁布局

        Args:
            tabs_config: 標籤頁配置
        """
        tab_names = [tab["name"] for tab in tabs_config]
        tabs = st.tabs(tab_names)

        for i, (tab, config) in enumerate(zip(tabs, tabs_config)):
            with tab:
                if "content_func" in config:
                    config["content_func"]()
                elif "content" in config:
                    st.markdown(config["content"])


class FormLayout:
    """表單布局管理器"""

    @staticmethod
    def render_form_section(
        title: str,
        fields: List[Dict[str, Any]],
        columns: int = 2,
        form_key: str = "form",
    ) -> Dict[str, Any]:
        """
        渲染表單區段

        Args:
            title: 區段標題
            fields: 欄位配置列表
            columns: 列數
            form_key: 表單鍵

        Returns:
            Dict[str, Any]: 表單資料
        """
        st.markdown(f"### {title}")

        form_data = {}

        with st.form(form_key):
            # 建立欄位網格
            cols = st.columns(columns)

            for i, field in enumerate(fields):
                with cols[i % columns]:
                    field_type = field.get("type", "text")
                    field_key = field["key"]
                    field_label = field["label"]
                    field_value = field.get("default", None)

                    if field_type == "text":
                        form_data[field_key] = st.text_input(
                            field_label,
                            value=field_value or "",
                            help=field.get("help", ""),
                        )
                    elif field_type == "number":
                        form_data[field_key] = st.number_input(
                            field_label,
                            value=field_value or 0,
                            min_value=field.get("min_value"),
                            max_value=field.get("max_value"),
                            help=field.get("help", ""),
                        )
                    elif field_type == "select":
                        form_data[field_key] = st.selectbox(
                            field_label,
                            options=field["options"],
                            index=field.get("default_index", 0),
                            help=field.get("help", ""),
                        )
                    elif field_type == "multiselect":
                        form_data[field_key] = st.multiselect(
                            field_label,
                            options=field["options"],
                            default=field.get("default", []),
                            help=field.get("help", ""),
                        )
                    elif field_type == "checkbox":
                        form_data[field_key] = st.checkbox(
                            field_label,
                            value=field_value or False,
                            help=field.get("help", ""),
                        )
                    elif field_type == "date":
                        form_data[field_key] = st.date_input(
                            field_label,
                            value=field_value,
                            help=field.get("help", ""),
                        )
                    elif field_type == "time":
                        form_data[field_key] = st.time_input(
                            field_label,
                            value=field_value,
                            help=field.get("help", ""),
                        )

            # 提交按鈕
            submitted = st.form_submit_button("提交", type="primary")

            if submitted:
                return form_data

        return {}


class ResponsiveLayout:
    """響應式布局管理器（已棄用，請使用 responsive.py 中的新實作）"""

    @staticmethod
    def auto_columns(items: List[Any], max_columns: int = 4, min_width: int = 300):
        """
        自動調整列數的響應式布局

        Args:
            items: 要顯示的項目列表
            max_columns: 最大列數
            min_width: 最小寬度（像素）
        """
        # 使用新的響應式管理器
        from ..responsive import responsive_manager

        num_items = len(items)
        columns = responsive_manager.get_columns_config(
            desktop=min(max_columns, num_items), tablet=min(2, num_items), mobile=1
        )

        cols = st.columns(columns)

        for i, item in enumerate(items):
            with cols[i % columns]:
                yield item

    @staticmethod
    def mobile_friendly_table(data: List[Dict], key: str = "table"):
        """
        行動裝置友善的表格顯示

        Args:
            data: 表格資料
            key: 組件鍵
        """
        # 使用新的響應式組件
        from ..responsive import ResponsiveComponents
        import pandas as pd

        if not data:
            st.info("暫無資料")
            return

        ResponsiveComponents.responsive_dataframe(pd.DataFrame(data), title=None)


# 預設導航配置
DEFAULT_NAVIGATION = {
    "pages": [
        {"name": "總覽", "key": "overview", "icon": "🏠", "description": "系統總覽"},
        {"name": "資料管理", "key": "data", "icon": "📊", "description": "資料管理"},
        {
            "name": "策略管理",
            "key": "strategy",
            "icon": "🎯",
            "description": "策略管理",
        },
        {
            "name": "AI 模型",
            "key": "ai_models",
            "icon": "🤖",
            "description": "AI 模型管理",
        },
        {
            "name": "回測系統",
            "key": "backtest",
            "icon": "📈",
            "description": "回測系統",
        },
        {
            "name": "投資組合",
            "key": "portfolio",
            "icon": "💼",
            "description": "投資組合管理",
        },
        {"name": "風險管理", "key": "risk", "icon": "🛡️", "description": "風險管理"},
        {"name": "交易執行", "key": "trading", "icon": "⚡", "description": "交易執行"},
        {
            "name": "系統監控",
            "key": "monitoring",
            "icon": "📡",
            "description": "系統監控",
        },
        {"name": "報表分析", "key": "reports", "icon": "📋", "description": "報表分析"},
    ]
}
