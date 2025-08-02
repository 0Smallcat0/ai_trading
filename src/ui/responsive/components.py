"""響應式組件模組

此模組提供一系列響應式 UI 組件，用於創建適應不同裝置螢幕尺寸的使用者介面元素。
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional, Callable
from .layout_manager import responsive_manager


class ResponsiveComponents:
    """響應式組件工具類

    提供一系列響應式 UI 組件的靜態方法，用於創建適應不同裝置螢幕尺寸的
    使用者介面元素。所有組件都會根據當前裝置類型自動調整佈局和行為。

    主要組件類型：
    - 指標卡片：響應式的數據展示卡片
    - 圖表容器：自適應尺寸的圖表包裝器
    - 數據表格：手機友善的表格顯示
    - 表單元素：響應式表單佈局
    - 標籤頁：適應不同裝置的導航方式

    設計原則：
    - 手機優先：優先考慮手機裝置的使用體驗
    - 漸進增強：在較大螢幕上提供更豐富的功能
    - 觸控友善：確保所有互動元素適合觸控操作
    - 內容優先：確保核心內容在所有裝置上都能良好顯示

    使用範例：
        >>> metrics = [{"title": "用戶數", "value": "1,234", "status": "success"}]
        >>> ResponsiveComponents.responsive_metric_cards(metrics)
    """

    @staticmethod
    def responsive_metric_cards(
        metrics: List[Dict[str, Any]],
        desktop_cols: int = 4,
        tablet_cols: int = 2,
        mobile_cols: int = 1,
    ) -> None:
        """渲染響應式指標卡片

        根據螢幕尺寸自動調整指標卡片的佈局，在桌面顯示多列，
        在手機上顯示單列。每個指標卡片包含標題、數值、狀態和圖示。

        Args:
            metrics: 指標數據列表，每個元素應包含：
                - title: 指標標題
                - value: 指標數值（字串格式）
                - status: 狀態類型（success/warning/error/info）
                - icon: 圖示（可選）
            desktop_cols: 桌面裝置的列數，預設為 4
            tablet_cols: 平板裝置的列數，預設為 2
            mobile_cols: 手機裝置的列數，預設為 1

        Returns:
            None

        Side Effects:
            在 Streamlit 界面中渲染指標卡片

        Example:
            >>> metrics = [
            ...     {"title": "總收益", "value": "$12,345", "status": "success", "icon": "💰"},
            ...     {"title": "風險等級", "value": "中等", "status": "warning", "icon": "⚠️"}
            ... ]
            >>> ResponsiveComponents.responsive_metric_cards(metrics, desktop_cols=2)
        """
        try:
            # 嘗試導入現有的 UI 組件
            from ..components.common import UIComponents
        except ImportError:
            # 備用實作
            class UIComponents:
                """備用 UI 組件類"""

                @staticmethod
                def status_card(
                    title: str,
                    value: str,
                    status: str = "info",
                    icon: str = "📊",
                    **kwargs,
                ):
                    """狀態卡片備用實作"""
                    # 忽略額外的 kwargs 參數
                    _ = kwargs

                    status_colors = {
                        "success": "🟢",
                        "warning": "🟡",
                        "error": "🔴",
                        "info": "🔵",
                        "normal": "⚪",
                    }
                    color = status_colors.get(status, "🔵")
                    st.metric(
                        label=f"{icon} {title}", value=value, help=f"狀態: {color}"
                    )

        cols_count = responsive_manager.get_columns_config(
            desktop_cols, tablet_cols, mobile_cols
        )
        cols = st.columns(cols_count)

        for i, metric in enumerate(metrics):
            with cols[i % cols_count]:
                UIComponents.status_card(**metric)

    @staticmethod
    def responsive_chart(
        chart_func: Callable, chart_data: Any, title: str = "", **kwargs
    ) -> None:
        """渲染響應式圖表

        Args:
            chart_func: 圖表渲染函數
            chart_data: 圖表數據
            title: 圖表標題
            **kwargs: 額外的圖表參數
        """
        height = responsive_manager.get_chart_height(kwargs.get("height", 400))
        kwargs["height"] = height

        # 添加響應式容器
        st.markdown('<div class="responsive-chart">', unsafe_allow_html=True)

        if title:
            st.subheader(title)

        # 渲染圖表
        chart_func(chart_data, **kwargs)

        st.markdown("</div>", unsafe_allow_html=True)

    @staticmethod
    def responsive_dataframe(
        df: pd.DataFrame, title: Optional[str] = None, **kwargs
    ) -> None:
        """渲染響應式數據框

        Args:
            df: 數據框
            title: 表格標題
            **kwargs: 額外的表格參數
        """
        if title:
            st.subheader(title)

        if responsive_manager.is_mobile:
            # 手機版：使用卡片式顯示
            for idx, row in df.iterrows():
                with st.expander(f"項目 {idx+1}", expanded=False):
                    for col in df.columns:
                        st.markdown(f"**{col}**: {row[col]}")
        else:
            # 桌面/平板版：使用標準表格
            st.dataframe(df, use_container_width=True, **kwargs)

    @staticmethod
    def responsive_form(
        form_config: Dict[str, Any], form_key: str = "responsive_form"
    ) -> Dict[str, Any]:
        """渲染響應式表單

        Args:
            form_config: 表單配置字典，包含：
                - title: 表單標題
                - fields: 欄位列表
            form_key: 表單唯一鍵

        Returns:
            Dict[str, Any]: 表單數據（如果提交）
        """
        title = form_config.get("title", "")
        fields = form_config.get("fields", [])

        if title:
            st.subheader(title)

        # 根據螢幕尺寸調整表單佈局
        cols_count = responsive_manager.get_columns_config(2, 1, 1)

        form_data = {}
        with st.form(form_key):
            if cols_count == 1:
                # 單列佈局
                for field in fields:
                    form_data[field["key"]] = ResponsiveComponents._render_form_field(
                        field
                    )
            else:
                # 多列佈局
                cols = st.columns(cols_count)
                for i, field in enumerate(fields):
                    with cols[i % cols_count]:
                        form_data[field["key"]] = (
                            ResponsiveComponents._render_form_field(field)
                        )

            # 提交按鈕
            button_config = responsive_manager.get_button_config()
            submitted = st.form_submit_button("提交", **button_config)

            if submitted:
                return form_data

        return {}

    @staticmethod
    def _render_form_field(field: Dict[str, Any]) -> Any:
        """渲染表單欄位

        Args:
            field: 欄位配置字典

        Returns:
            Any: 欄位值
        """
        field_type = field.get("type", "text")
        field_label = field["label"]
        field_value = field.get("default", None)

        if field_type == "text":
            return st.text_input(field_label, value=field_value or "")
        elif field_type == "number":
            return st.number_input(field_label, value=field_value or 0)
        elif field_type == "select":
            return st.selectbox(field_label, options=field["options"])
        elif field_type == "multiselect":
            return st.multiselect(field_label, options=field["options"])
        elif field_type == "checkbox":
            return st.checkbox(field_label, value=field_value or False)
        elif field_type == "date":
            return st.date_input(field_label, value=field_value)
        elif field_type == "time":
            return st.time_input(field_label, value=field_value)
        else:
            return st.text_input(field_label, value=field_value or "")

    @staticmethod
    def responsive_tabs(tabs_config: List[Dict[str, Any]]) -> None:
        """渲染響應式標籤頁

        Args:
            tabs_config: 標籤頁配置列表，每個元素包含：
                - name: 標籤頁名稱
                - content_func: 內容渲染函數（可選）
                - content: 靜態內容（可選）
        """
        if responsive_manager.is_mobile:
            # 手機版：使用選擇框代替標籤頁
            tab_names = [tab["name"] for tab in tabs_config]
            selected_tab = st.selectbox("選擇頁面", tab_names)

            # 渲染選中的標籤頁內容
            for tab in tabs_config:
                if tab["name"] == selected_tab:
                    if "content_func" in tab:
                        tab["content_func"]()
                    elif "content" in tab:
                        st.markdown(tab["content"])
        else:
            # 桌面/平板版：使用標準標籤頁
            tab_names = [tab["name"] for tab in tabs_config]
            tabs = st.tabs(tab_names)

            for tab, config in zip(tabs, tabs_config):
                with tab:
                    if "content_func" in config:
                        config["content_func"]()
                    elif "content" in config:
                        st.markdown(config["content"])

    @staticmethod
    def responsive_grid(
        items: List[Dict[str, Any]],
        desktop_cols: int = 4,
        tablet_cols: int = 2,
        mobile_cols: int = 1,
        render_func: Optional[Callable] = None,
    ) -> None:
        """渲染響應式網格

        Args:
            items: 要渲染的項目列表
            desktop_cols: 桌面裝置的列數
            tablet_cols: 平板裝置的列數
            mobile_cols: 手機裝置的列數
            render_func: 自定義渲染函數
        """
        cols_count = responsive_manager.get_columns_config(
            desktop_cols, tablet_cols, mobile_cols
        )
        cols = st.columns(cols_count)

        for i, item in enumerate(items):
            with cols[i % cols_count]:
                if render_func:
                    render_func(item)
                else:
                    st.write(item)
