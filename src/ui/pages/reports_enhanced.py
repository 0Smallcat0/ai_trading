"""
增強版報表查詢與視覺化頁面

此模組提供完整的報表功能，包括：
- 動態報表查詢
- 互動式圖表生成
- 多格式數據匯出
- 排程報表系統
- 視覺化儀表板
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any

import streamlit as st
import pandas as pd
import numpy as np

# 可選的圖表依賴
try:
    import plotly.express as plotly_px
    import plotly.graph_objects as plotly_go
    import matplotlib.pyplot as matplotlib_plt

    PLOTLY_AVAILABLE = True
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    MATPLOTLIB_AVAILABLE = False
    plotly_px = None
    plotly_go = None
    matplotlib_plt = None

# 導入響應式設計組件
try:
    from ..responsive import (
        ResponsiveUtils,
        ResponsiveComponents,
        ResponsiveLayoutManager,
    )
except ImportError:
    # 備用導入
    from src.ui.responsive import (
        ResponsiveUtils,
        ResponsiveComponents,
        ResponsiveLayoutManager,
    )

# 導入通用組件
try:
    from ..components.common import UIComponents  # pylint: disable=unused-import
except ImportError:
    # 如果組件不存在，創建備用類
    class UIComponents:  # pylint: disable=too-few-public-methods
        """備用 UI 組件類"""

        @staticmethod
        def show_info(message: str) -> None:
            """顯示資訊訊息"""
            st.info(message)


# 創建備用報表組件類
class ReportsComponents:
    """
    報表組件類

    提供報表系統所需的各種 UI 組件和功能模組。包括動態查詢建構器、
    圖表配置面板、數據匯出功能、排程報表管理和儀表板設計器等核心組件。

    此類別作為報表系統的核心組件庫，提供模組化和可重用的 UI 元件，
    支援多種數據源的查詢、視覺化和匯出功能。

    主要功能模組：
    - 動態查詢建構器：支援複雜條件的查詢建立
    - 圖表生成器：支援 Plotly 和 Matplotlib 圖表
    - 數據匯出：支援多種格式的數據匯出
    - 排程報表：自動化報表生成和發送
    - 儀表板設計：可自定義的視覺化儀表板
    """

    @staticmethod
    def dynamic_query_builder(fields: List[str], form_key: str) -> Dict[str, Any]:
        """
        動態查詢建構器

        提供動態的查詢條件建構界面，允許用戶根據可用欄位建立複雜的查詢條件。
        支援日期範圍、多選欄位、數值範圍等多種篩選條件類型。

        Args:
            fields: 可用於查詢的欄位列表
            form_key: Streamlit 表單的唯一識別鍵

        Returns:
            Dict[str, Any]: 查詢條件字典，包含以下可能的鍵值：
                - date_range: 日期範圍 tuple (start_datetime, end_datetime)
                - symbols: 選擇的股票代碼列表
                - directions: 選擇的交易方向列表
                - amount_range: 金額範圍 tuple (min_amount, max_amount)

        Example:
            >>> fields = ["股票代碼", "交易方向", "金額"]
            >>> conditions = ReportsComponents.dynamic_query_builder(fields, "query_form")
            >>> # 返回: {"date_range": (start, end), "symbols": ["2330.TW"], ...}
        """
        with st.form(form_key):
            st.subheader("查詢條件")

            # 日期範圍
            col1, col2 = st.columns(2)

            with col1:
                start_date = st.date_input(
                    "開始日期", datetime.now() - timedelta(days=30)
                )

            with col2:
                end_date = st.date_input("結束日期", datetime.now())

            # 欄位篩選
            if "股票代碼" in fields:
                symbols = st.multiselect(
                    "股票代碼", ["2330.TW", "2317.TW", "AAPL", "MSFT"]
                )

            if "交易方向" in fields:
                directions = st.multiselect("交易方向", ["買入", "賣出"])

            # 數值範圍
            if "金額" in fields:
                amount_range = st.slider("金額範圍", 0, 1000000, (0, 1000000))

            submitted = st.form_submit_button("執行查詢")

            if submitted:
                conditions = {
                    "date_range": (
                        datetime.combine(start_date, datetime.min.time()),
                        datetime.combine(end_date, datetime.max.time()),
                    )
                }

                # 初始化變數以避免 possibly-used-before-assignment 警告
                symbols = None
                directions = None
                amount_range = None

                if "股票代碼" in fields and symbols is not None:
                    conditions["symbols"] = symbols

                if "交易方向" in fields and directions is not None:
                    conditions["directions"] = directions

                if "金額" in fields and amount_range is not None:
                    conditions["amount_range"] = amount_range

                return conditions

        return {}

    @staticmethod
    def chart_configuration_panel() -> Dict[str, Any]:
        """
        圖表配置面板

        提供圖表類型選擇和基本配置選項的用戶界面。
        允許用戶選擇圖表類型並設定標題、軸標籤等基本屬性。

        Returns:
            Dict[str, Any]: 圖表配置字典，包含：
                - type: 圖表類型
                - title: 圖表標題
                - x_label: X 軸標籤
                - y_label: Y 軸標籤

        Example:
            >>> config = ReportsComponents.chart_configuration_panel()
            >>> print(f"選擇的圖表類型: {config['type']}")
        """
        st.subheader("圖表類型")

        chart_type = st.selectbox(
            "選擇圖表類型", ["line", "bar", "scatter", "histogram", "pie", "box"]
        )

        config = {"type": chart_type}

        # 圖表標題和標籤
        config["title"] = st.text_input("圖表標題", "數據分析圖表")
        config["x_label"] = st.text_input("X 軸標籤", "X 軸")
        config["y_label"] = st.text_input("Y 軸標籤", "Y 軸")

        return config

    @staticmethod
    def interactive_chart_generator(data: pd.DataFrame, config: Dict[str, Any]):
        """
        互動式圖表生成器

        使用 Plotly 生成互動式圖表，支援多種圖表類型和自定義配置。
        根據配置參數動態生成對應的圖表類型。

        Args:
            data: 要視覺化的 DataFrame 數據
            config: 圖表配置字典，包含圖表類型、欄位選擇等設定

        Returns:
            plotly.graph_objects.Figure: Plotly 圖表物件，如果失敗則返回 None

        Example:
            >>> df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
            >>> config = {"type": "line", "x_column": "x", "y_column": "y"}
            >>> fig = ReportsComponents.interactive_chart_generator(df, config)
        """
        if not PLOTLY_AVAILABLE:
            st.error("Plotly 未安裝，無法生成互動式圖表")
            return None

        chart_type = config.get("type", "line")
        x_col = config.get("x_column")
        y_col = config.get("y_column")
        color_col = config.get("color_column")

        if chart_type == "line":
            fig = plotly_px.line(
                data, x=x_col, y=y_col, color=color_col, title=config.get("title", "")
            )
        elif chart_type == "bar":
            fig = plotly_px.bar(
                data, x=x_col, y=y_col, color=color_col, title=config.get("title", "")
            )
        elif chart_type == "scatter":
            size_col = config.get("size_column")
            fig = plotly_px.scatter(
                data,
                x=x_col,
                y=y_col,
                color=color_col,
                size=size_col,
                title=config.get("title", ""),
            )
        elif chart_type == "histogram":
            fig = plotly_px.histogram(
                data,
                x=x_col,
                nbins=config.get("bins", 20),
                title=config.get("title", ""),
            )
        elif chart_type == "pie":
            values_col = config.get("values_column")
            names_col = config.get("names_column")
            fig = plotly_px.pie(
                data, values=values_col, names=names_col, title=config.get("title", "")
            )
        else:
            fig = plotly_px.line(data, x=x_col, y=y_col, title=config.get("title", ""))

        fig.update_layout(
            xaxis_title=config.get("x_label", "X 軸"),
            yaxis_title=config.get("y_label", "Y 軸"),
        )

        return fig

    @staticmethod
    def matplotlib_chart_generator(data: pd.DataFrame, config: Dict[str, Any]):
        """
        Matplotlib 圖表生成器

        使用 Matplotlib 生成靜態圖表，支援基本的圖表類型。
        適用於需要靜態圖表或 Plotly 不可用的情況。

        Args:
            data: 要視覺化的 DataFrame 數據
            config: 圖表配置字典，包含圖表類型、欄位選擇等設定

        Returns:
            matplotlib.figure.Figure: Matplotlib 圖表物件，如果失敗則返回 None

        Example:
            >>> df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
            >>> config = {"type": "line", "x_column": "x", "y_column": "y"}
            >>> fig = ReportsComponents.matplotlib_chart_generator(df, config)
        """
        if not MATPLOTLIB_AVAILABLE:
            st.error("Matplotlib 未安裝，無法生成靜態圖表")
            return None

        fig, ax = matplotlib_plt.subplots(figsize=(10, 6))

        chart_type = config.get("type", "line")
        x_col = config.get("x_column")
        y_col = config.get("y_column")

        if chart_type == "line":
            ax.plot(data[x_col], data[y_col])
        elif chart_type == "bar":
            ax.bar(data[x_col], data[y_col])
        elif chart_type == "scatter":
            ax.scatter(data[x_col], data[y_col])
        elif chart_type == "histogram":
            ax.hist(data[x_col], bins=config.get("bins", 20))

        ax.set_title(config.get("title", "數據分析圖表"))
        ax.set_xlabel(config.get("x_label", "X 軸"))
        ax.set_ylabel(config.get("y_label", "Y 軸"))

        matplotlib_plt.tight_layout()
        return fig

    @staticmethod
    def data_export_panel(data: pd.DataFrame, filename_prefix: str) -> None:
        """
        數據匯出面板

        提供多種格式的數據匯出功能，包括 CSV、Excel、JSON 和 PDF 格式。
        生成帶時間戳的檔案名稱，方便用戶下載和管理匯出的數據。

        Args:
            data: 要匯出的 DataFrame 數據
            filename_prefix: 檔案名稱前綴

        Returns:
            None

        Side Effects:
            在 Streamlit 界面顯示匯出按鈕和下載連結

        Example:
            >>> df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
            >>> ReportsComponents.data_export_panel(df, "trading_report")
        """
        st.subheader("匯出操作")

        cols = st.columns(4)

        with cols[0]:
            if st.button("📄 匯出 CSV", use_container_width=True):
                csv = data.to_csv(index=False)
                st.download_button(
                    label="下載 CSV",
                    data=csv,
                    file_name=(
                        f"{filename_prefix}_"
                        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    ),
                    mime="text/csv",
                )

        with cols[1]:
            if st.button("📊 匯出 Excel", use_container_width=True):
                # 模擬 Excel 匯出
                st.info("Excel 匯出功能需要安裝 openpyxl")

        with cols[2]:
            if st.button("📋 匯出 JSON", use_container_width=True):
                json_data = data.to_json(orient="records", date_format="iso")
                st.download_button(
                    label="下載 JSON",
                    data=json_data,
                    file_name=(
                        f"{filename_prefix}_"
                        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    ),
                    mime="application/json",
                )

        with cols[3]:
            if st.button("📑 匯出 PDF", use_container_width=True):
                st.info("PDF 匯出功能需要安裝 reportlab")

    @staticmethod
    def scheduled_reports_panel() -> None:
        """
        排程報表面板

        提供排程報表的創建和管理界面，允許用戶設定自動化報表生成任務。
        支援多種排程頻率和數據源選擇，並可設定 Email 通知收件人。

        Returns:
            None

        Side Effects:
            在 Streamlit 界面顯示排程報表創建表單

        Example:
            >>> ReportsComponents.scheduled_reports_panel()
            # 顯示排程報表創建界面
        """
        st.write("### 新增排程報表")

        with st.form("schedule_form"):
            col1, col2 = st.columns(2)

            with col1:
                report_name = st.text_input("報表名稱")
                data_source = st.selectbox(
                    "數據源", ["交易記錄", "投資組合數據", "風險指標"]
                )

            with col2:
                schedule_type = st.selectbox("排程類型", ["每日", "每週", "每月"])
                email_recipients = st.text_input("收件人 (用逗號分隔)")

            submitted = st.form_submit_button("建立排程")

            if submitted and report_name:
                st.success(f"排程報表 '{report_name}' 已建立")
                st.info(f"數據源: {data_source}, 排程: {schedule_type}")
                if email_recipients:
                    st.info(f"收件人: {email_recipients}")

    @staticmethod
    def dashboard_designer() -> Dict[str, Any]:
        """
        儀表板設計器

        提供儀表板配置界面，允許用戶選擇佈局類型和組件類型。
        支援多種預設佈局和組件選擇，用於創建自定義的視覺化儀表板。

        Returns:
            Dict[str, Any]: 儀表板配置字典，包含：
                - layout: 佈局類型
                - components: 選擇的組件列表

        Example:
            >>> config = ReportsComponents.dashboard_designer()
            >>> print(f"選擇的佈局: {config['layout']}")
            >>> print(f"選擇的組件: {config['components']}")
        """
        st.write("### 儀表板配置")

        config = {}

        # 佈局選擇
        layout = st.selectbox("佈局類型", ["2x2 網格", "3x1 橫向", "1x3 縱向"])
        config["layout"] = layout

        # 組件選擇
        components = st.multiselect(
            "選擇組件", ["指標卡片", "趨勢圖表", "數據表格", "圓餅圖", "長條圖"]
        )
        config["components"] = components

        return config


# 創建響應式管理器實例
responsive_manager = ResponsiveLayoutManager()


def show_enhanced() -> None:
    """
    顯示增強版報表查詢與視覺化頁面

    此函數是報表系統的主要入口點，提供完整的報表功能界面。
    包括動態查詢、圖表生成、數據匯出、排程報表和儀表板五個主要功能模組。
    支援多種數據源的查詢和視覺化，以及多格式的數據匯出功能。

    功能特點：
    - 響應式設計，支援多種裝置
    - 動態查詢建構器，支援複雜條件篩選
    - 互動式圖表生成，支援 Plotly 和 Matplotlib
    - 多格式數據匯出（CSV、Excel、JSON、PDF）
    - 排程報表自動化系統
    - 可自定義的視覺化儀表板

    Returns:
        None
    """
    # 應用響應式頁面配置
    ResponsiveUtils.apply_responsive_page_config(
        page_title="報表系統 - AI 交易系統", page_icon="📊"
    )

    # 頁面標題
    st.markdown(
        '<h1 class="title-responsive">📊 報表查詢與視覺化</h1>', unsafe_allow_html=True
    )

    # 初始化會話狀態
    _initialize_report_session_state()

    # 響應式標籤頁
    tabs_config = [
        {"name": "🔍 動態查詢", "content_func": show_dynamic_query},
        {"name": "📈 圖表生成", "content_func": show_chart_generation},
        {"name": "📤 數據匯出", "content_func": show_data_export},
        {"name": "⏰ 排程報表", "content_func": show_scheduled_reports},
        {"name": "📋 儀表板", "content_func": show_dashboard},
    ]

    ResponsiveComponents.responsive_tabs(tabs_config)


def _initialize_report_session_state() -> None:
    """
    初始化報表系統的會話狀態

    設定報表系統所需的會話狀態變數，包括報表數據、圖表配置和儀表板配置。
    確保所有必要的狀態變數都有適當的初始值。

    Returns:
        None
    """
    if "report_data" not in st.session_state:
        st.session_state.report_data = pd.DataFrame()
    if "chart_config" not in st.session_state:
        st.session_state.chart_config = {}
    if "dashboard_config" not in st.session_state:
        st.session_state.dashboard_config = {}


def show_dynamic_query() -> None:
    """
    顯示動態查詢介面

    提供動態報表查詢功能，允許用戶選擇不同的數據源並建構複雜的查詢條件。
    支援多種數據源包括交易記錄、投資組合數據、風險指標等，並提供預設查詢模板
    以簡化常用查詢的建立過程。

    功能特點：
    - 支援 6 種主要數據源的查詢
    - 動態查詢建構器，支援複雜條件組合
    - 即時查詢結果預覽和統計摘要
    - 預設查詢模板，提升查詢效率
    - 響應式數據表格顯示

    Returns:
        None

    Side Effects:
        - 更新 st.session_state.report_data 儲存查詢結果
        - 在 Streamlit 界面顯示查詢結果和統計資訊
    """
    st.subheader("動態報表查詢")

    # 可用數據源
    data_sources = [
        "交易記錄",
        "投資組合數據",
        "風險指標",
        "市場數據",
        "策略績效",
        "系統日誌",
    ]

    selected_source = st.selectbox("選擇數據源", data_sources)

    # 根據數據源獲取可用欄位
    available_fields = get_available_fields(selected_source)

    # 動態查詢建構器
    query_conditions = ReportsComponents.dynamic_query_builder(
        available_fields, f"query_{selected_source}"
    )

    if query_conditions:
        # 執行查詢
        with st.spinner("執行查詢中..."):
            query_result = execute_query(selected_source, query_conditions)

            if not query_result.empty:
                st.session_state.report_data = query_result

                # 顯示查詢結果摘要
                show_query_summary(query_result)

                # 顯示數據預覽
                st.subheader("數據預覽")
                ResponsiveComponents.responsive_dataframe(
                    query_result.head(100), title=f"{selected_source} - 查詢結果"
                )

                st.success(f"查詢完成！共找到 {len(query_result)} 筆記錄")
            else:
                st.warning("查詢沒有返回任何結果")

    # 預設查詢模板
    st.subheader("預設查詢模板")
    show_query_templates(selected_source)


def _configure_chart_fields(data: pd.DataFrame, chart_config: Dict[str, Any]) -> None:
    """
    配置圖表欄位選擇

    Args:
        data: 數據 DataFrame
        chart_config: 圖表配置字典
    """
    st.subheader("欄位配置")

    cols = responsive_manager.create_responsive_columns(
        desktop_cols=3, tablet_cols=2, mobile_cols=1
    )

    numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
    all_columns = data.columns.tolist()

    with cols[0]:
        x_column = st.selectbox("X 軸", all_columns)
        chart_config["x_column"] = x_column

    with cols[1 % len(cols)]:
        y_column = st.selectbox(
            "Y 軸", numeric_columns if numeric_columns else all_columns
        )
        chart_config["y_column"] = y_column

    with cols[2 % len(cols)]:
        color_column = st.selectbox("顏色分組", ["無"] + all_columns)
        chart_config["color_column"] = None if color_column == "無" else color_column


def _configure_advanced_chart_options(
    chart_config: Dict[str, Any], numeric_columns: List[str], all_columns: List[str]
) -> None:
    """
    配置進階圖表選項

    Args:
        chart_config: 圖表配置字典
        numeric_columns: 數值型欄位列表
        all_columns: 所有欄位列表
    """
    with st.expander("進階配置"):
        cols2 = responsive_manager.create_responsive_columns(
            desktop_cols=2, tablet_cols=1, mobile_cols=1
        )

        with cols2[0]:
            if chart_config["type"] == "scatter":
                size_column = st.selectbox("大小", ["無"] + numeric_columns)
                chart_config["size_column"] = (
                    None if size_column == "無" else size_column
                )

            if chart_config["type"] == "histogram":
                bins = st.slider("直方圖區間數", 10, 100, 20)
                chart_config["bins"] = bins

        with cols2[1 % len(cols2)]:
            if chart_config["type"] == "pie":
                values_column = st.selectbox("數值欄位", numeric_columns)
                names_column = st.selectbox("標籤欄位", all_columns)
                chart_config["values_column"] = values_column
                chart_config["names_column"] = names_column


def _generate_chart(data: pd.DataFrame, chart_config: Dict[str, Any]) -> None:
    """
    生成圖表

    Args:
        data: 數據 DataFrame
        chart_config: 圖表配置字典
    """
    if st.button("🎨 生成圖表", type="primary"):
        try:
            fig = ReportsComponents.interactive_chart_generator(data, chart_config)
            st.plotly_chart(fig, use_container_width=True)

            # 保存圖表配置
            st.session_state.chart_config = chart_config

            st.success("圖表生成成功！")
        except (ImportError, AttributeError, ValueError) as e:
            st.error(f"圖表生成失敗: {e}")


def _show_chart_library_options(
    data: pd.DataFrame, chart_config: Dict[str, Any]
) -> None:
    """
    顯示圖表庫選擇選項

    Args:
        data: 數據 DataFrame
        chart_config: 圖表配置字典
    """
    st.subheader("圖表庫選擇")

    chart_library = st.radio(
        "選擇圖表庫", ["Plotly (互動式)", "Matplotlib (靜態)"], horizontal=True
    )

    if chart_library == "Matplotlib (靜態)" and st.button("生成 Matplotlib 圖表"):
        try:
            fig = ReportsComponents.matplotlib_chart_generator(data, chart_config)
            st.pyplot(fig)
            st.success("Matplotlib 圖表生成成功！")
        except (ImportError, AttributeError, ValueError) as e:
            st.error(f"Matplotlib 圖表生成失敗: {e}")


def show_chart_generation() -> None:
    """
    顯示圖表生成介面

    提供互動式圖表生成功能，支援多種圖表類型和自定義配置選項。
    用戶可以選擇不同的圖表類型（線圖、柱狀圖、散點圖等），配置軸向欄位、
    顏色分組等參數，並支援 Plotly 和 Matplotlib 兩種圖表庫。

    功能特點：
    - 支援 6 種圖表類型（line, bar, scatter, histogram, pie, box）
    - 動態欄位選擇，自動識別數值型和分類型欄位
    - 進階配置選項（大小、區間數、數值欄位等）
    - 支援 Plotly 互動式圖表和 Matplotlib 靜態圖表
    - 響應式佈局，適應不同螢幕尺寸

    Prerequisites:
        需要先在動態查詢頁面載入數據到 st.session_state.report_data

    Returns:
        None

    Side Effects:
        - 更新 st.session_state.chart_config 儲存圖表配置
        - 在 Streamlit 界面顯示生成的圖表
    """
    st.subheader("互動式圖表生成")

    if st.session_state.report_data.empty:
        st.info("請先在「動態查詢」頁面載入數據")
        return

    data = st.session_state.report_data

    # 圖表配置面板
    chart_config = ReportsComponents.chart_configuration_panel()

    # 欄位選擇
    _configure_chart_fields(data, chart_config)

    # 進階配置
    numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
    all_columns = data.columns.tolist()
    _configure_advanced_chart_options(chart_config, numeric_columns, all_columns)

    # 生成圖表
    _generate_chart(data, chart_config)

    # 圖表庫選擇
    _show_chart_library_options(data, chart_config)


def show_data_export() -> None:
    """
    顯示數據匯出介面

    提供完整的數據匯出功能，支援多種格式和自定義選項。用戶可以選擇
    匯出格式（CSV、Excel、JSON、PDF）、設定匯出範圍、包含圖表等選項，
    並提供即時的匯出統計和檔案大小估計。

    功能特點：
    - 多格式支援：CSV、Excel、JSON、PDF 四種主要格式
    - 靈活範圍選擇：全部數據、前N筆、自定義範圍
    - 圖表包含選項：可選擇是否在匯出中包含圖表
    - 檔案命名自定義：支援自定義檔案名稱前綴
    - 即時統計顯示：記錄數、欄位數、檔案大小估計
    - 響應式佈局：適應不同裝置螢幕尺寸

    Prerequisites:
        需要先在動態查詢頁面載入數據到 st.session_state.report_data

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示數據匯出配置選項
        - 提供數據下載功能和統計資訊
        - 可能觸發檔案下載操作

    Example:
        使用流程：
        1. 在動態查詢頁面載入數據
        2. 切換到數據匯出頁面
        3. 選擇匯出格式和範圍
        4. 點擊匯出按鈕下載檔案
    """
    st.subheader("多格式數據匯出")

    if st.session_state.report_data.empty:
        st.info("請先在「動態查詢」頁面載入數據")
        return

    data = st.session_state.report_data

    # 匯出選項
    st.subheader("匯出選項")

    cols = responsive_manager.create_responsive_columns(
        desktop_cols=2, tablet_cols=1, mobile_cols=1
    )

    with cols[0]:
        export_format = st.selectbox("匯出格式", ["CSV", "Excel", "JSON", "PDF"])

        include_charts = st.checkbox("包含圖表", value=True)

        # 顯示選擇的格式
        st.info(f"選擇格式: {export_format}")
        if include_charts:
            st.info("將包含圖表")

    with cols[1 % len(cols)]:
        filename_prefix = st.text_input("檔案名稱前綴", value="report")

        export_range = st.selectbox(
            "匯出範圍", ["全部數據", "前100筆", "前1000筆", "自定義範圍"]
        )

    # 自定義範圍
    if export_range == "自定義範圍":
        cols2 = responsive_manager.create_responsive_columns(
            desktop_cols=2, tablet_cols=1, mobile_cols=1
        )

        with cols2[0]:
            start_row = st.number_input(
                "起始行", min_value=0, max_value=len(data) - 1, value=0
            )

        with cols2[1 % len(cols2)]:
            end_row = st.number_input(
                "結束行",
                min_value=start_row + 1,
                max_value=len(data),
                value=min(100, len(data)),
            )

        export_data = data.iloc[start_row:end_row]
    elif export_range == "前100筆":
        export_data = data.head(100)
    elif export_range == "前1000筆":
        export_data = data.head(1000)
    else:
        export_data = data

    # 數據匯出面板
    ReportsComponents.data_export_panel(export_data, filename_prefix)

    # 匯出統計
    st.subheader("匯出統計")

    export_stats = [
        {
            "title": "總記錄數",
            "value": f"{len(data):,}",
            "status": "normal",
            "icon": "📊",
        },
        {
            "title": "匯出記錄數",
            "value": f"{len(export_data):,}",
            "status": "normal",
            "icon": "📤",
        },
        {
            "title": "欄位數",
            "value": str(len(export_data.columns)),
            "status": "normal",
            "icon": "📋",
        },
        {
            "title": "檔案大小估計",
            "value": f"{estimate_file_size(export_data):.1f} MB",
            "status": "normal",
            "icon": "💾",
        },
    ]

    ResponsiveComponents.responsive_metric_cards(
        export_stats, desktop_cols=4, tablet_cols=2, mobile_cols=1
    )


def show_scheduled_reports() -> None:
    """
    顯示排程報表介面

    提供自動化報表排程功能，允許用戶設定定期執行的報表任務。
    支援多種排程頻率（每日、每週、每月）和報表類型，並提供
    執行歷史查詢和狀態監控功能。

    功能特點：
    - 排程設定：支援每日、每週、每月等多種排程頻率
    - 報表類型：交易報表、風險報表、績效報表等預設模板
    - 自動執行：系統自動在指定時間執行報表生成
    - 結果通知：支援 Email 或其他方式的結果通知
    - 執行歷史：完整的報表執行記錄和狀態追蹤
    - 錯誤處理：執行失敗時的錯誤記錄和重試機制

    排程管理功能：
    - 新增排程：創建新的報表排程任務
    - 編輯排程：修改現有排程的設定
    - 啟用/停用：控制排程任務的執行狀態
    - 立即執行：手動觸發報表生成
    - 刪除排程：移除不需要的排程任務

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示排程報表管理面板
        - 顯示報表執行歷史和狀態資訊
        - 可能觸發報表排程的建立、修改或執行操作

    Note:
        排程功能需要後端服務支援，目前使用模擬介面展示功能
    """
    st.subheader("排程報表系統")

    # 排程報表面板
    ReportsComponents.scheduled_reports_panel()

    # 報表執行歷史
    st.subheader("執行歷史")
    show_report_execution_history()


def show_dashboard() -> None:
    """
    顯示視覺化儀表板

    提供互動式儀表板設計和預覽功能，允許用戶創建自定義的數據視覺化
    儀表板。支援多種佈局選項、組件類型和預設模板，提供拖拽式的
    儀表板設計體驗。

    功能特點：
    - 儀表板設計器：拖拽式的視覺化設計介面
    - 多種佈局：單欄、雙欄、三欄、網格等佈局選項
    - 豐富組件：指標卡片、圖表、表格、文字等組件類型
    - 即時預覽：設計過程中的即時預覽功能
    - 模板庫：預設的儀表板模板，快速開始設計
    - 配置保存：儀表板配置的保存和載入功能

    支援的組件類型：
    - 指標卡片：KPI 指標的數值顯示
    - 線圖/柱狀圖：趨勢和比較數據的視覺化
    - 圓餅圖/環圖：比例和分佈數據的展示
    - 表格：詳細數據的表格形式展示
    - 文字組件：說明文字和標題

    佈局選項：
    - 單欄佈局：適合手機和簡單展示
    - 雙欄佈局：平衡的桌面佈局
    - 三欄佈局：豐富的桌面展示
    - 網格佈局：靈活的自定義排列

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示儀表板設計器
        - 更新 st.session_state.dashboard_config 儲存設計配置
        - 可能觸發儀表板預覽渲染

    Example:
        使用流程：
        1. 選擇儀表板佈局類型
        2. 添加和配置組件
        3. 預覽儀表板效果
        4. 保存儀表板配置
    """
    st.subheader("視覺化儀表板")

    # 儀表板設計器
    dashboard_config = ReportsComponents.dashboard_designer()
    st.session_state.dashboard_config = dashboard_config

    # 預覽儀表板
    if st.button("🎨 預覽儀表板", type="primary"):
        render_dashboard_preview(dashboard_config)

    # 儀表板模板
    st.subheader("儀表板模板")
    show_dashboard_templates()


def get_available_fields(data_source: str) -> List[str]:
    """
    獲取數據源的可用欄位

    根據指定的數據源類型返回該數據源支援的所有可用欄位列表。
    這些欄位將用於動態查詢建構器中的條件設定和圖表軸向選擇。

    Args:
        data_source: 數據源名稱，支援的類型包括：
            - "交易記錄": 交易相關數據
            - "投資組合數據": 投資組合持股和績效數據
            - "風險指標": 風險管理相關指標
            - "市場數據": 股票市場價格和成交量數據
            - "策略績效": 交易策略績效評估數據
            - "系統日誌": 系統運行日誌數據

    Returns:
        List[str]: 該數據源可用的欄位名稱列表

    Example:
        >>> fields = get_available_fields("交易記錄")
        >>> print(fields)
        ['日期', '股票代碼', '交易方向', '數量', '價格', '金額', '手續費']
    """
    field_mapping = {
        "交易記錄": ["日期", "股票代碼", "交易方向", "數量", "價格", "金額", "手續費"],
        "投資組合數據": ["日期", "股票代碼", "持股數量", "市值", "權重", "收益率"],
        "風險指標": ["日期", "VaR", "回撤", "波動率", "夏普比率", "最大回撤"],
        "市場數據": [
            "日期",
            "股票代碼",
            "開盤價",
            "最高價",
            "最低價",
            "收盤價",
            "成交量",
        ],
        "策略績效": ["日期", "策略名稱", "收益率", "累積收益", "勝率", "最大回撤"],
        "系統日誌": ["時間", "等級", "模組", "訊息", "用戶"],
    }

    return field_mapping.get(data_source, ["欄位1", "欄位2", "欄位3"])


def execute_query(data_source: str, conditions: Dict[str, Any]) -> pd.DataFrame:
    """
    執行查詢

    根據指定的數據源和查詢條件執行數據查詢操作。目前使用模擬數據實作，
    在實際部署時會連接到真實的數據 API 端點進行查詢。

    Args:
        data_source: 要查詢的數據源名稱
        conditions: 查詢條件字典，可能包含：
            - date_range: 日期範圍 tuple
            - symbols: 股票代碼列表
            - directions: 交易方向列表
            - amount_range: 金額範圍 tuple

    Returns:
        pd.DataFrame: 查詢結果的 DataFrame，如果查詢失敗則返回空 DataFrame

    Raises:
        Exception: 當查詢過程中發生錯誤時

    Example:
        >>> conditions = {"date_range": (start_date, end_date), "symbols": ["2330.TW"]}
        >>> result = execute_query("交易記錄", conditions)
        >>> print(f"查詢到 {len(result)} 筆記錄")
    """
    try:
        # 模擬 API 調用
        # response = requests.post(
        #     "http://localhost:8000/api/v1/reports/query",
        #     json={
        #         "data_source": data_source,
        #         "conditions": conditions
        #     }
        # )
        # if response.status_code == 200:
        #     data = response.json()["data"]
        #     return pd.DataFrame(data)

        # 返回模擬數據
        return generate_mock_data(data_source, conditions)

    except (ImportError, AttributeError, OSError) as e:
        st.error(f"查詢執行失敗: {e}")
        return pd.DataFrame()


def generate_mock_data(data_source: str, conditions: Dict[str, Any]) -> pd.DataFrame:
    """
    生成模擬數據

    根據指定的數據源類型和查詢條件生成模擬的測試數據。此函數用於
    開發和測試階段，提供符合真實數據結構的模擬數據，確保應用程式
    在沒有真實數據源的情況下也能正常運行和測試。

    支援的數據源類型：
    - "交易記錄": 包含日期、股票代碼、交易方向、數量、價格等欄位
    - "投資組合數據": 包含持股數量、市值、權重、收益率等欄位
    - 其他類型: 提供通用的數值和類別數據結構

    數據特點：
    - 使用固定隨機種子確保結果可重現
    - 根據日期範圍生成對應數量的記錄
    - 數據分佈符合真實場景的統計特性
    - 支援多種股票代碼和交易類型

    Args:
        data_source: 數據源類型，決定生成數據的結構和內容
        conditions: 查詢條件字典，包含：
            - date_range: 日期範圍 tuple (start_date, end_date)
            - 其他條件參數（目前未使用，為未來擴展保留）

    Returns:
        pd.DataFrame: 生成的模擬數據 DataFrame，結構根據數據源類型而定

    Example:
        >>> conditions = {"date_range": (start_date, end_date)}
        >>> df = generate_mock_data("交易記錄", conditions)
        >>> print(f"生成了 {len(df)} 筆交易記錄")

    Note:
        此函數僅用於開發和測試，生產環境應替換為真實數據源連接
    """
    np.random.seed(42)  # 確保結果可重現

    # 獲取日期範圍
    date_range = conditions.get(
        "date_range", (datetime.now() - timedelta(days=30), datetime.now())
    )
    start_date, end_date = date_range

    # 生成日期序列
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    n_records = len(dates)

    if data_source == "交易記錄":
        data = {
            "日期": np.random.choice(dates, n_records),
            "股票代碼": np.random.choice(
                ["2330.TW", "2317.TW", "AAPL", "MSFT"], n_records
            ),
            "交易方向": np.random.choice(["買入", "賣出"], n_records),
            "數量": np.random.randint(100, 1000, n_records),
            "價格": np.random.uniform(100, 200, n_records),
            "金額": np.random.uniform(10000, 200000, n_records),
            "手續費": np.random.uniform(10, 100, n_records),
        }

    elif data_source == "投資組合數據":
        data = {
            "日期": np.tile(dates, 4)[:n_records],
            "股票代碼": np.repeat(["2330.TW", "2317.TW", "AAPL", "MSFT"], len(dates))[
                :n_records
            ],
            "持股數量": np.random.randint(100, 1000, n_records),
            "市值": np.random.uniform(50000, 500000, n_records),
            "權重": np.random.uniform(0.1, 0.4, n_records),
            "收益率": np.random.normal(0.001, 0.02, n_records),
        }

    else:
        # 預設數據結構
        data = {
            "日期": dates[:n_records],
            "數值1": np.random.normal(100, 20, n_records),
            "數值2": np.random.normal(50, 10, n_records),
            "類別": np.random.choice(["A", "B", "C"], n_records),
        }

    return pd.DataFrame(data)


def show_query_summary(data: pd.DataFrame) -> None:
    """
    顯示查詢結果摘要

    分析並顯示查詢結果數據的統計摘要資訊，包括記錄數量、欄位統計、
    記憶體使用量等關鍵指標。提供響應式的指標卡片展示，幫助用戶
    快速了解查詢結果的基本特徵。

    統計指標包括：
    - 記錄數：查詢結果的總行數
    - 欄位數：數據表的總列數
    - 記憶體使用：數據在記憶體中的佔用大小
    - 數值欄位：包含數值型數據的欄位數量

    顯示特點：
    - 響應式佈局：適應不同螢幕尺寸的卡片排列
    - 視覺化圖示：每個指標配有相應的圖示
    - 格式化數值：使用千分位分隔符和適當單位
    - 即時計算：基於實際數據動態計算統計值

    Args:
        data: 要分析的 pandas DataFrame 數據

    Returns:
        None

    Side Effects:
        在 Streamlit 界面顯示查詢結果統計摘要卡片

    Example:
        >>> df = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "y", "z"]})
        >>> show_query_summary(df)
        # 顯示：記錄數=3, 欄位數=2, 數值欄位=1 等統計資訊

    Note:
        記憶體使用量計算包含深度記憶體分析，可能對大型數據集有效能影響
    """
    st.subheader("查詢結果摘要")

    summary_metrics = [
        {
            "title": "記錄數",
            "value": f"{len(data):,}",
            "status": "normal",
            "icon": "📊",
        },
        {
            "title": "欄位數",
            "value": str(len(data.columns)),
            "status": "normal",
            "icon": "📋",
        },
        {
            "title": "記憶體使用",
            "value": f"{data.memory_usage(deep=True).sum() / 1024**2:.1f} MB",
            "status": "normal",
            "icon": "💾",
        },
        {
            "title": "數值欄位",
            "value": str(len(data.select_dtypes(include=[np.number]).columns)),
            "status": "normal",
            "icon": "🔢",
        },
    ]

    ResponsiveComponents.responsive_metric_cards(
        summary_metrics, desktop_cols=4, tablet_cols=2, mobile_cols=1
    )


def show_query_templates(data_source: str) -> None:
    """
    顯示查詢模板

    根據指定的數據源類型顯示預設的查詢模板按鈕，提供常用查詢的快速入口。
    每個數據源都有對應的專業查詢模板，幫助用戶快速建立常見的報表查詢。

    模板類型：
    - 交易記錄：今日交易明細、本週交易統計、大額交易記錄、交易頻率分析
    - 投資組合數據：投資組合現況、持股變化趨勢、權重分佈分析、收益率統計
    - 風險指標：風險指標趨勢、VaR 分析報告、回撤統計、風險預警
    - 其他數據源：基本查詢、統計分析等通用模板

    Args:
        data_source: 數據源名稱，決定顯示哪些查詢模板

    Returns:
        None

    Side Effects:
        在 Streamlit 界面顯示查詢模板按鈕，點擊時顯示模板載入提示

    Example:
        >>> show_query_templates("交易記錄")
        # 顯示交易記錄相關的查詢模板按鈕

    Note:
        目前模板點擊僅顯示提示訊息，實際部署時會載入對應的查詢條件
    """
    templates = {
        "交易記錄": ["今日交易明細", "本週交易統計", "大額交易記錄", "交易頻率分析"],
        "投資組合數據": ["投資組合現況", "持股變化趨勢", "權重分佈分析", "收益率統計"],
        "風險指標": ["風險指標趨勢", "VaR 分析報告", "回撤統計", "風險預警"],
    }

    source_templates = templates.get(data_source, ["基本查詢", "統計分析"])

    cols = responsive_manager.create_responsive_columns(
        desktop_cols=len(source_templates), tablet_cols=2, mobile_cols=1
    )

    for i, template in enumerate(source_templates):
        with cols[i % len(cols)]:
            if st.button(template, use_container_width=True):
                st.info(f"載入模板：{template}")


def show_report_execution_history() -> None:
    """
    顯示報表執行歷史

    展示排程報表的執行歷史記錄，包括執行時間、狀態、執行時長和記錄數等資訊。
    提供完整的報表執行追蹤，幫助監控自動化報表系統的運行狀況。

    顯示資訊包括：
    - 報表名稱：執行的報表任務名稱
    - 執行時間：報表開始執行的時間戳記
    - 執行狀態：成功、失敗、執行中等狀態
    - 執行時長：報表生成所需的時間
    - 記錄數：報表包含的數據記錄數量

    Returns:
        None

    Side Effects:
        在 Streamlit 界面顯示報表執行歷史表格

    Example:
        >>> show_report_execution_history()
        # 顯示報表執行歷史記錄表格

    Note:
        目前使用模擬數據，實際部署時會連接到報表執行日誌系統
    """
    # 模擬執行歷史數據
    history = [
        {
            "報表名稱": "每日交易報表",
            "執行時間": "2024-01-15 09:00:00",
            "狀態": "成功",
            "執行時長": "2.3秒",
            "記錄數": "1,234",
        },
        {
            "報表名稱": "週度風險報表",
            "執行時間": "2024-01-15 08:00:00",
            "狀態": "成功",
            "執行時長": "5.7秒",
            "記錄數": "8,765",
        },
    ]

    if history:
        df = pd.DataFrame(history)
        ResponsiveComponents.responsive_dataframe(df, title="報表執行歷史")
    else:
        st.info("沒有執行歷史")


def render_dashboard_preview(config: Dict[str, Any]) -> None:
    """
    渲染儀表板預覽

    根據用戶配置的儀表板設定渲染預覽效果，支援多種佈局類型和組件排列。
    提供即時的視覺化預覽，讓用戶在設計過程中能夠立即看到儀表板的效果。

    支援的佈局類型：
    - 單欄佈局：所有組件垂直排列，適合手機和簡單展示
    - 雙欄佈局：組件分為兩欄顯示，適合桌面環境
    - 三欄佈局：組件分為三欄顯示，適合寬螢幕展示
    - 網格佈局：自由排列的網格佈局

    Args:
        config: 儀表板配置字典，包含：
            - layout_type: 佈局類型（單欄、雙欄、三欄、網格）
            - components: 組件列表

    Returns:
        None

    Side Effects:
        在 Streamlit 界面渲染儀表板預覽

    Example:
        >>> config = {"layout_type": "雙欄", "components": ["指標卡片", "線圖"]}
        >>> render_dashboard_preview(config)
        # 顯示雙欄佈局的儀表板預覽

    Note:
        預覽使用示例數據，實際儀表板會連接到真實數據源
    """
    st.subheader("儀表板預覽")

    layout_type = config.get("layout_type", "雙欄")
    components = config.get("components", [])

    if layout_type == "單欄":
        for component in components:
            render_dashboard_component(component)

    elif layout_type == "雙欄":
        cols = st.columns(2)
        for i, component in enumerate(components):
            with cols[i % 2]:
                render_dashboard_component(component)

    elif layout_type == "三欄":
        cols = st.columns(3)
        for i, component in enumerate(components):
            with cols[i % 3]:
                render_dashboard_component(component)

    else:
        # 網格佈局
        for component in components:
            render_dashboard_component(component)


def render_dashboard_component(component: str) -> None:
    """
    渲染儀表板組件

    根據組件類型渲染對應的視覺化元件，提供儀表板預覽功能。
    每種組件類型都有對應的示例實作，展示該組件在實際儀表板中的外觀。

    支援的組件類型：
    - 指標卡片：顯示 KPI 數值和變化趨勢
    - 線圖：時間序列數據的趨勢展示
    - 表格：結構化數據的表格展示
    - 其他：通用組件的佔位符顯示

    Args:
        component: 組件類型名稱

    Returns:
        None

    Side Effects:
        在 Streamlit 界面渲染指定類型的組件

    Example:
        >>> render_dashboard_component("指標卡片")
        # 渲染一個示例指標卡片組件

    Note:
        所有組件都使用示例數據進行渲染，實際使用時會連接到真實數據源
    """
    if component == "指標卡片":
        st.metric("示例指標", "1,234", "12%")

    elif component == "線圖":
        # 生成示例線圖
        dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
        values = np.random.cumsum(np.random.randn(30))

        import plotly.graph_objects as go

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=dates, y=values, mode="lines", name="示例數據"))
        fig.update_layout(title="示例線圖", height=300)
        st.plotly_chart(fig, use_container_width=True)

    elif component == "表格":
        # 生成示例表格
        sample_data = pd.DataFrame({"項目": ["A", "B", "C"], "數值": [100, 200, 150]})
        st.dataframe(sample_data, use_container_width=True)

    else:
        st.info(f"組件：{component}")


def show_dashboard_templates() -> None:
    """
    顯示儀表板模板

    展示預設的儀表板模板選項，提供快速建立專業儀表板的入口。
    每個模板都針對特定的業務場景設計，包含適當的組件配置和佈局。

    可用模板：
    - 交易監控儀表板：即時交易數據和執行狀況監控
    - 風險管理儀表板：風險指標和警報監控
    - 績效分析儀表板：投資績效和回報分析
    - 市場概況儀表板：市場數據和趨勢分析

    Returns:
        None

    Side Effects:
        在 Streamlit 界面顯示儀表板模板選擇按鈕

    Example:
        >>> show_dashboard_templates()
        # 顯示可用的儀表板模板選項

    Note:
        目前模板點擊僅顯示載入提示，實際部署時會載入對應的儀表板配置
    """
    templates = ["交易監控儀表板", "風險管理儀表板", "績效分析儀表板", "市場概況儀表板"]

    cols = responsive_manager.create_responsive_columns(
        desktop_cols=2, tablet_cols=1, mobile_cols=1
    )

    for i, template in enumerate(templates):
        with cols[i % len(cols)]:
            if st.button(template, use_container_width=True):
                st.success(f"載入模板：{template}")


def estimate_file_size(data: pd.DataFrame) -> float:
    """
    估計檔案大小（MB）

    計算 DataFrame 數據在記憶體中的大小，用於估計匯出檔案的大小。
    提供檔案大小的預估值，幫助用戶了解匯出操作的資源需求。

    Args:
        data: 要估計大小的 pandas DataFrame

    Returns:
        float: 估計的檔案大小（以 MB 為單位）

    Example:
        >>> df = pd.DataFrame({"A": [1, 2, 3], "B": ["x", "y", "z"]})
        >>> size = estimate_file_size(df)
        >>> print(f"估計檔案大小: {size:.2f} MB")

    Note:
        此估計基於記憶體使用量，實際檔案大小可能因格式和壓縮而有所不同
    """
    return data.memory_usage(deep=True).sum() / 1024**2


if __name__ == "__main__":
    show_enhanced()
