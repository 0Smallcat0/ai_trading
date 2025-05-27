"""
響應式資料管理頁面

此模組展示如何將現有的資料管理頁面改造為響應式設計，
支援手機、平板和桌面等不同螢幕尺寸的最佳顯示效果。
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# 導入響應式設計組件
from ..responsive import (
    ResponsiveComponents,
    ResponsiveUtils,
    responsive_manager,
    apply_responsive_design,
    get_responsive_columns,
    is_mobile_device,
)

# 導入現有組件
from ..components.common import UIComponents
from ..components.charts import line_chart, candlestick_chart


def show_responsive():
    """顯示響應式資料管理頁面"""
    # 應用響應式頁面配置
    ResponsiveUtils.apply_responsive_page_config(
        page_title="資料管理 - AI 交易系統", page_icon="📊"
    )

    # 頁面標題
    st.markdown(
        '<h1 class="title-responsive">📊 資料管理與更新</h1>', unsafe_allow_html=True
    )

    # 顯示響應式配置資訊（開發模式）
    if st.checkbox("顯示響應式配置", value=False):
        config = ResponsiveUtils.get_responsive_config()
        st.json(config)

    # 響應式標籤頁
    tabs_config = [
        {"name": "📊 資料來源", "content_func": show_data_sources_responsive},
        {"name": "🔄 資料更新", "content_func": show_data_update_responsive},
        {"name": "🔍 資料查詢", "content_func": show_data_query_responsive},
        {"name": "📈 品質監控", "content_func": show_data_quality_responsive},
    ]

    ResponsiveComponents.responsive_tabs(tabs_config)


def show_data_sources_responsive():
    """顯示響應式資料來源管理"""
    st.subheader("資料來源管理")

    # 模擬資料來源狀態
    data_sources = get_mock_data_sources()

    # 響應式指標卡片
    metrics = [
        {
            "title": "總資料來源",
            "value": len(data_sources),
            "status": "normal",
            "icon": "📊",
        },
        {
            "title": "正常運行",
            "value": sum(1 for ds in data_sources if ds["status"] == "正常"),
            "status": "success",
            "icon": "✅",
        },
        {
            "title": "需要注意",
            "value": sum(1 for ds in data_sources if ds["status"] == "警告"),
            "status": "warning",
            "icon": "⚠️",
        },
        {
            "title": "離線狀態",
            "value": sum(1 for ds in data_sources if ds["status"] == "離線"),
            "status": "error",
            "icon": "❌",
        },
    ]

    ResponsiveComponents.responsive_metric_cards(
        metrics, desktop_cols=4, tablet_cols=2, mobile_cols=1
    )

    # 響應式資料來源表格
    st.subheader("資料來源詳情")

    # 準備表格資料
    df = pd.DataFrame(data_sources)

    # 使用響應式表格組件
    ResponsiveComponents.responsive_dataframe(df, title="資料來源狀態表")

    # 響應式操作按鈕
    st.subheader("操作選項")

    if is_mobile_device():
        # 手機版：垂直排列按鈕
        if st.button("🔄 刷新所有資料來源", use_container_width=True):
            st.success("資料來源已刷新")

        if st.button("📊 查看詳細統計", use_container_width=True):
            show_data_source_statistics()

        if st.button("⚙️ 配置資料來源", use_container_width=True):
            show_data_source_config()
    else:
        # 桌面/平板版：水平排列按鈕
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🔄 刷新所有資料來源"):
                st.success("資料來源已刷新")

        with col2:
            if st.button("📊 查看詳細統計"):
                show_data_source_statistics()

        with col3:
            if st.button("⚙️ 配置資料來源"):
                show_data_source_config()


def show_data_update_responsive():
    """顯示響應式資料更新管理"""
    st.subheader("資料更新管理")

    # 響應式表單
    form_config = {
        "title": "資料更新設定",
        "fields": [
            {
                "key": "update_type",
                "label": "更新類型",
                "type": "select",
                "options": ["全量更新", "增量更新", "指定標的更新"],
            },
            {
                "key": "data_types",
                "label": "資料類型",
                "type": "multiselect",
                "options": ["股價資料", "基本面資料", "技術指標", "新聞資料"],
            },
            {
                "key": "start_date",
                "label": "開始日期",
                "type": "date",
                "default": datetime.now() - timedelta(days=30),
            },
            {
                "key": "end_date",
                "label": "結束日期",
                "type": "date",
                "default": datetime.now(),
            },
        ],
    }

    form_data = ResponsiveComponents.responsive_form(form_config, "data_update_form")

    if form_data:
        st.success("資料更新任務已啟動！")
        st.json(form_data)


def show_data_query_responsive():
    """顯示響應式資料查詢"""
    st.subheader("資料查詢")

    # 響應式查詢表單
    cols = responsive_manager.create_responsive_columns(
        desktop_cols=3, tablet_cols=2, mobile_cols=1
    )

    with cols[0]:
        symbol = st.selectbox("股票代碼", ["2330.TW", "2317.TW", "AAPL", "MSFT"])

    with cols[1 % len(cols)]:
        data_type = st.selectbox("資料類型", ["股價", "基本面", "技術指標"])

    with cols[2 % len(cols)]:
        period = st.selectbox("時間週期", ["1天", "1週", "1月", "3月"])

    # 查詢按鈕
    if st.button("🔍 查詢資料", use_container_width=is_mobile_device()):
        # 生成模擬資料
        mock_data = generate_mock_chart_data(symbol, data_type)

        # 響應式圖表
        chart_height = responsive_manager.get_chart_height(400)

        if data_type == "股價":
            fig = px.line(
                mock_data,
                x="date",
                y="close",
                title=f"{symbol} 股價走勢",
                height=chart_height,
            )
            st.plotly_chart(fig, use_container_width=True)

        # 響應式資料表格
        ResponsiveComponents.responsive_dataframe(mock_data.head(10), title="查詢結果")


def show_data_quality_responsive():
    """顯示響應式資料品質監控"""
    st.subheader("資料品質監控")

    # 品質指標
    quality_metrics = [
        {"title": "完整性", "value": "98.5%", "status": "success", "icon": "✅"},
        {"title": "準確性", "value": "97.2%", "status": "success", "icon": "🎯"},
        {"title": "及時性", "value": "95.8%", "status": "warning", "icon": "⏰"},
        {"title": "一致性", "value": "99.1%", "status": "success", "icon": "🔄"},
    ]

    ResponsiveComponents.responsive_metric_cards(
        quality_metrics, desktop_cols=4, tablet_cols=2, mobile_cols=2
    )

    # 品質趨勢圖表
    quality_trend_data = generate_quality_trend_data()

    chart_height = responsive_manager.get_chart_height(350)
    fig = px.line(
        quality_trend_data,
        x="date",
        y=["completeness", "accuracy", "timeliness"],
        title="資料品質趨勢",
        height=chart_height,
    )

    st.plotly_chart(fig, use_container_width=True)


def get_mock_data_sources() -> List[Dict[str, Any]]:
    """獲取模擬資料來源"""
    return [
        {
            "name": "Yahoo Finance",
            "type": "股價API",
            "status": "正常",
            "last_update": "2024-01-15 09:30:00",
            "api_status": "正常",
            "data_quality": "98.5%",
        },
        {
            "name": "FinMind",
            "type": "基本面API",
            "status": "正常",
            "last_update": "2024-01-15 08:00:00",
            "api_status": "正常",
            "data_quality": "97.2%",
        },
        {
            "name": "Alpha Vantage",
            "type": "財報API",
            "status": "警告",
            "last_update": "2024-01-14 18:00:00",
            "api_status": "速率限制",
            "data_quality": "95.8%",
        },
        {
            "name": "新聞API",
            "type": "新聞資料",
            "status": "離線",
            "last_update": "2024-01-13 12:00:00",
            "api_status": "連接失敗",
            "data_quality": "N/A",
        },
    ]


def generate_mock_chart_data(symbol: str, data_type: str) -> pd.DataFrame:
    """生成模擬圖表資料"""
    import numpy as np

    dates = pd.date_range(start="2024-01-01", end="2024-01-15", freq="D")

    if data_type == "股價":
        base_price = 100
        prices = base_price + np.cumsum(np.random.randn(len(dates)) * 2)

        return pd.DataFrame(
            {
                "date": dates,
                "close": prices,
                "volume": np.random.randint(1000000, 5000000, len(dates)),
            }
        )
    else:
        return pd.DataFrame(
            {"date": dates, "value": np.random.randn(len(dates)) * 10 + 50}
        )


def generate_quality_trend_data() -> pd.DataFrame:
    """生成品質趨勢資料"""
    import numpy as np

    dates = pd.date_range(start="2024-01-01", end="2024-01-15", freq="D")

    return pd.DataFrame(
        {
            "date": dates,
            "completeness": 95 + np.random.randn(len(dates)) * 2,
            "accuracy": 96 + np.random.randn(len(dates)) * 1.5,
            "timeliness": 94 + np.random.randn(len(dates)) * 3,
        }
    )


def show_data_source_statistics():
    """顯示資料來源統計"""
    st.info("📊 資料來源統計功能")


def show_data_source_config():
    """顯示資料來源配置"""
    st.info("⚙️ 資料來源配置功能")


if __name__ == "__main__":
    show_responsive()
