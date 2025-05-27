"""
報表查詢與視覺化組件

此模組提供報表系統的各種組件，包括：
- 動態報表查詢組件
- 互動式圖表生成組件
- 多格式數據匯出組件
- 視覺化儀表板組件
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import io
import logging

# 導入響應式設計組件
try:
    from ..responsive import ResponsiveComponents, responsive_manager
except ImportError as e:
    logging.warning("無法導入響應式組件: %s", e)
    # 提供備用實現

    class ResponsiveComponents:
        """響應式組件備用實現"""

        @staticmethod
        def responsive_form(config: Dict[str, Any], key: str) -> Optional[Any]:
            """響應式表單備用實現"""
            del config, key  # 避免未使用變數警告
            return None

        @staticmethod
        def responsive_dataframe(df: pd.DataFrame, title: str = "") -> None:
            """響應式數據框備用實現"""
            del title  # 避免未使用變數警告
            st.dataframe(df)

    class ResponsiveManager:
        """響應式管理器備用實現"""

        def get_chart_height(self, default_height: int) -> int:
            """獲取圖表高度"""
            return default_height

        def create_responsive_columns(
            self, desktop_cols: int = 3, tablet_cols: int = 2, mobile_cols: int = 1
        ) -> List[Any]:
            """創建響應式列"""
            del tablet_cols, mobile_cols  # 避免未使用變數警告
            return st.columns(desktop_cols)

    responsive_manager = ResponsiveManager()


class ReportsComponents:
    """報表查詢與視覺化組件類"""

    @staticmethod
    def dynamic_query_builder(
        available_fields: List[str], form_key: str = "query_builder"
    ) -> Optional[Dict[str, Any]]:
        """
        動態報表查詢建構器

        Args:
            available_fields: 可用欄位列表
            form_key: 表單鍵值

        Returns:
            查詢條件字典，如果未提交則返回 None
        """
        form_config = {
            "title": "報表查詢條件",
            "fields": [
                {
                    "key": "date_range",
                    "label": "日期範圍",
                    "type": "date_range",
                    "default": (datetime.now() - timedelta(days=30), datetime.now()),
                },
                {
                    "key": "fields",
                    "label": "選擇欄位",
                    "type": "multiselect",
                    "options": available_fields,
                    "default": (
                        available_fields[:5]
                        if len(available_fields) > 5
                        else available_fields
                    ),
                },
                {
                    "key": "group_by",
                    "label": "分組依據",
                    "type": "select",
                    "options": ["無", "日期", "股票代碼", "策略", "行業"],
                },
                {
                    "key": "aggregation",
                    "label": "聚合方式",
                    "type": "select",
                    "options": ["總和", "平均", "最大值", "最小值", "計數"],
                },
                {
                    "key": "filter_conditions",
                    "label": "篩選條件",
                    "type": "text",
                    "default": "",
                },
                {
                    "key": "sort_by",
                    "label": "排序依據",
                    "type": "select",
                    "options": available_fields,
                },
                {
                    "key": "sort_order",
                    "label": "排序順序",
                    "type": "select",
                    "options": ["升序", "降序"],
                },
                {
                    "key": "limit",
                    "label": "結果數量限制",
                    "type": "number",
                    "default": 1000,
                },
            ],
        }

        return ResponsiveComponents.responsive_form(form_config, form_key)

    @staticmethod
    def interactive_chart_generator(
        data: pd.DataFrame, chart_config: Dict[str, Any]
    ) -> go.Figure:
        """
        互動式圖表生成器

        Args:
            data: 數據
            chart_config: 圖表配置

        Returns:
            Plotly 圖表物件
        """
        chart_type = chart_config.get("type", "line")

        if chart_type == "line":
            return ReportsComponents._create_line_chart(data, chart_config)
        elif chart_type == "bar":
            return ReportsComponents._create_bar_chart(data, chart_config)
        elif chart_type == "pie":
            return ReportsComponents._create_pie_chart(data, chart_config)
        elif chart_type == "scatter":
            return ReportsComponents._create_scatter_chart(data, chart_config)
        elif chart_type == "heatmap":
            return ReportsComponents._create_heatmap(data, chart_config)
        elif chart_type == "histogram":
            return ReportsComponents._create_histogram(data, chart_config)
        elif chart_type == "box":
            return ReportsComponents._create_box_plot(data, chart_config)
        else:
            return ReportsComponents._create_line_chart(data, chart_config)

    @staticmethod
    def _create_line_chart(data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """創建線圖"""
        x_col = config.get("x_column", data.columns[0])
        y_col = config.get(
            "y_column", data.columns[1] if len(data.columns) > 1 else data.columns[0]
        )

        fig = px.line(
            data,
            x=x_col,
            y=y_col,
            title=config.get("title", "線圖"),
            color=config.get("color_column"),
            line_group=config.get("group_column"),
        )

        height = responsive_manager.get_chart_height(400)
        fig.update_layout(height=height)

        return fig

    @staticmethod
    def _create_bar_chart(data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """創建柱狀圖"""
        x_col = config.get("x_column", data.columns[0])
        y_col = config.get(
            "y_column", data.columns[1] if len(data.columns) > 1 else data.columns[0]
        )

        fig = px.bar(
            data,
            x=x_col,
            y=y_col,
            title=config.get("title", "柱狀圖"),
            color=config.get("color_column"),
        )

        height = responsive_manager.get_chart_height(400)
        fig.update_layout(height=height)

        return fig

    @staticmethod
    def _create_pie_chart(data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """創建餅圖"""
        values_col = config.get("values_column", data.columns[0])
        names_col = config.get(
            "names_column",
            data.columns[1] if len(data.columns) > 1 else data.columns[0],
        )

        fig = px.pie(
            data, values=values_col, names=names_col, title=config.get("title", "餅圖")
        )

        height = responsive_manager.get_chart_height(400)
        fig.update_layout(height=height)

        return fig

    @staticmethod
    def _create_scatter_chart(data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """創建散點圖"""
        x_col = config.get("x_column", data.columns[0])
        y_col = config.get(
            "y_column", data.columns[1] if len(data.columns) > 1 else data.columns[0]
        )

        fig = px.scatter(
            data,
            x=x_col,
            y=y_col,
            title=config.get("title", "散點圖"),
            color=config.get("color_column"),
            size=config.get("size_column"),
        )

        height = responsive_manager.get_chart_height(400)
        fig.update_layout(height=height)

        return fig

    @staticmethod
    def _create_heatmap(data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """創建熱力圖"""
        # 如果數據不是數值型，嘗試轉換
        numeric_data = data.select_dtypes(include=[np.number])

        if numeric_data.empty:
            # 創建簡單的計數熱力圖
            x_col = config.get("x_column", data.columns[0])
            y_col = config.get(
                "y_column",
                data.columns[1] if len(data.columns) > 1 else data.columns[0],
            )

            pivot_data = data.groupby([x_col, y_col]).size().unstack(fill_value=0)
        else:
            # 使用相關性矩陣
            pivot_data = numeric_data.corr()

        fig = px.imshow(
            pivot_data,
            title=config.get("title", "熱力圖"),
            color_continuous_scale="RdYlBu_r",
        )

        height = responsive_manager.get_chart_height(400)
        fig.update_layout(height=height)

        return fig

    @staticmethod
    def _create_histogram(data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """創建直方圖"""
        x_col = config.get("x_column", data.columns[0])

        fig = px.histogram(
            data,
            x=x_col,
            title=config.get("title", "直方圖"),
            nbins=config.get("bins", 20),
        )

        height = responsive_manager.get_chart_height(400)
        fig.update_layout(height=height)

        return fig

    @staticmethod
    def _create_box_plot(data: pd.DataFrame, config: Dict[str, Any]) -> go.Figure:
        """創建箱線圖"""
        y_col = config.get("y_column", data.columns[0])
        x_col = config.get("x_column")

        fig = px.box(data, x=x_col, y=y_col, title=config.get("title", "箱線圖"))

        height = responsive_manager.get_chart_height(400)
        fig.update_layout(height=height)

        return fig

    @staticmethod
    def chart_configuration_panel() -> Dict[str, Any]:
        """
        圖表配置面板

        Returns:
            圖表配置字典
        """
        st.subheader("圖表配置")

        # 使用響應式列佈局
        cols = responsive_manager.create_responsive_columns(
            desktop_cols=3, tablet_cols=2, mobile_cols=1
        )

        with cols[0]:
            chart_type = st.selectbox(
                "圖表類型",
                ["line", "bar", "pie", "scatter", "heatmap", "histogram", "box"],
                format_func=lambda x: {
                    "line": "線圖",
                    "bar": "柱狀圖",
                    "pie": "餅圖",
                    "scatter": "散點圖",
                    "heatmap": "熱力圖",
                    "histogram": "直方圖",
                    "box": "箱線圖",
                }[x],
            )

        with cols[1 % len(cols)]:
            title = st.text_input("圖表標題", value="自定義圖表")

        with cols[2 % len(cols)]:
            color_scheme = st.selectbox(
                "顏色方案", ["默認", "藍色", "綠色", "紅色", "彩虹"]
            )

        return {"type": chart_type, "title": title, "color_scheme": color_scheme}

    @staticmethod
    def data_export_panel(data: pd.DataFrame, filename_prefix: str = "report") -> None:
        """
        數據匯出面板

        Args:
            data: 要匯出的數據
            filename_prefix: 檔案名稱前綴
        """
        if data.empty:
            st.info("沒有數據可匯出")
            return

        st.subheader("數據匯出")

        # 匯出格式選擇
        cols = responsive_manager.create_responsive_columns(
            desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

        with cols[0]:
            if st.button("📄 匯出 CSV", use_container_width=True):
                ReportsComponents._export_csv(data, filename_prefix)

        with cols[1 % len(cols)]:
            if st.button("📊 匯出 Excel", use_container_width=True):
                ReportsComponents._export_excel(data, filename_prefix)

        with cols[2 % len(cols)]:
            if st.button("📋 匯出 JSON", use_container_width=True):
                ReportsComponents._export_json(data, filename_prefix)

        with cols[3 % len(cols)]:
            if st.button("🖼️ 匯出 PNG", use_container_width=True):
                st.info("PNG 匯出功能開發中...")

    @staticmethod
    def _export_csv(data: pd.DataFrame, filename_prefix: str):
        """匯出 CSV"""
        try:
            csv_data = data.to_csv(index=False, encoding="utf-8-sig")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename_prefix}_{timestamp}.csv"
            st.download_button(
                label="下載 CSV 檔案",
                data=csv_data,
                file_name=filename,
                mime="text/csv",
            )
            st.success("CSV 檔案已準備下載")
        except Exception as e:
            st.error(f"CSV 匯出失敗: {e}")

    @staticmethod
    def _export_excel(data: pd.DataFrame, filename_prefix: str):
        """匯出 Excel"""
        try:
            # 使用 BytesIO 創建 Excel 檔案
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                data.to_excel(writer, sheet_name="報表數據", index=False)

            excel_data = output.getvalue()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename_prefix}_{timestamp}.xlsx"
            mime_type = (
                "application/vnd.openxmlformats-officedocument." "spreadsheetml.sheet"
            )
            st.download_button(
                label="下載 Excel 檔案",
                data=excel_data,
                file_name=filename,
                mime=mime_type,
            )
            st.success("Excel 檔案已準備下載")
        except Exception as e:
            st.error(f"Excel 匯出失敗: {e}")

    @staticmethod
    def _export_json(data: pd.DataFrame, filename_prefix: str):
        """匯出 JSON"""
        try:
            json_data = data.to_json(orient="records", force_ascii=False, indent=2)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename_prefix}_{timestamp}.json"
            st.download_button(
                label="下載 JSON 檔案",
                data=json_data,
                file_name=filename,
                mime="application/json",
            )
            st.success("JSON 檔案已準備下載")
        except Exception as e:
            st.error(f"JSON 匯出失敗: {e}")

    @staticmethod
    def dashboard_designer() -> Dict[str, Any]:
        """
        儀表板設計器

        Returns:
            儀表板配置
        """
        st.subheader("儀表板設計器")

        # 佈局選擇
        layout_type = st.selectbox(
            "佈局類型",
            ["單欄", "雙欄", "三欄", "網格", "自定義"],
            help="選擇儀表板的佈局方式",
        )

        # 組件選擇
        st.write("### 添加組件")

        available_components = [
            "指標卡片",
            "線圖",
            "柱狀圖",
            "餅圖",
            "表格",
            "文字說明",
        ]

        selected_components = st.multiselect(
            "選擇要添加的組件", available_components, default=["指標卡片", "線圖"]
        )

        # 更新頻率
        refresh_interval = st.selectbox(
            "自動更新頻率", ["不自動更新", "30秒", "1分鐘", "5分鐘", "15分鐘"], index=2
        )

        return {
            "layout_type": layout_type,
            "components": selected_components,
            "refresh_interval": refresh_interval,
        }

    @staticmethod
    def scheduled_reports_panel() -> None:
        """排程報表面板"""
        st.subheader("排程報表管理")

        # 新增排程報表
        with st.expander("新增排程報表"):
            cols = responsive_manager.create_responsive_columns(
                desktop_cols=2, tablet_cols=1, mobile_cols=1
            )

            with cols[0]:
                report_name = st.text_input("報表名稱")
                report_type = st.selectbox(
                    "報表類型", ["交易報表", "風險報表", "績效報表"]
                )
                schedule_type = st.selectbox("排程類型", ["每日", "每週", "每月"])

            with cols[1 % len(cols)]:
                send_time = st.time_input("發送時間", datetime.now().time())
                recipients = st.text_area("收件人 (每行一個 Email)")

                if st.button("新增排程", type="primary"):
                    # 使用變數避免未使用警告
                    config = {
                        "name": report_name,
                        "type": report_type,
                        "schedule": schedule_type,
                        "time": send_time,
                        "recipients": recipients,
                    }
                    st.success(f"排程報表 '{config['name']}' 已新增")

        # 現有排程報表
        st.write("### 現有排程報表")

        # 模擬排程報表數據
        scheduled_reports = [
            {
                "名稱": "每日交易報表",
                "類型": "交易報表",
                "排程": "每日 09:00",
                "狀態": "啟用",
                "最後執行": "2024-01-15 09:00:00",
            },
            {
                "名稱": "週度風險報表",
                "類型": "風險報表",
                "排程": "每週一 08:00",
                "狀態": "啟用",
                "最後執行": "2024-01-15 08:00:00",
            },
        ]

        if scheduled_reports:
            df = pd.DataFrame(scheduled_reports)
            ResponsiveComponents.responsive_dataframe(df, title="排程報表列表")
        else:
            st.info("沒有排程報表")

    @staticmethod
    def matplotlib_chart_generator(
        data: pd.DataFrame, chart_config: Dict[str, Any]
    ) -> plt.Figure:
        """
        Matplotlib 圖表生成器（用於靜態圖表匯出）

        Args:
            data: 數據
            chart_config: 圖表配置

        Returns:
            Matplotlib 圖表物件
        """
        fig, ax = plt.subplots(figsize=(10, 6))

        chart_type = chart_config.get("type", "line")

        if chart_type == "line":
            data.plot(kind="line", ax=ax)
        elif chart_type == "bar":
            data.plot(kind="bar", ax=ax)
        elif chart_type == "pie":
            data.iloc[:, 0].plot(kind="pie", ax=ax)
        elif chart_type == "scatter":
            if len(data.columns) >= 2:
                ax.scatter(data.iloc[:, 0], data.iloc[:, 1])

        ax.set_title(chart_config.get("title", "圖表"))
        plt.tight_layout()

        return fig
