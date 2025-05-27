"""即時數據儀表板頁面

提供即時股價、交易狀態等數據的監控介面。

此模組提供以下功能：
- 即時股價監控和顯示
- 交易狀態追蹤
- 市場概覽和投資組合監控
- 互動式圖表分析
- 警報中心管理

主要類別：
    無

主要函數：
    show_realtime_dashboard: 主要頁面顯示函數
    show_connection_status: 顯示 WebSocket 連接狀態
    main_content_area: 主要內容區域渲染
    create_top_metrics: 創建頂部指標卡片
    create_market_overview: 創建市場概覽
    create_portfolio_overview: 創建投資組合概覽
    create_chart_analysis: 創建圖表分析
    create_alerts_center: 創建警報中心

使用範例：
    from src.ui.pages.realtime_dashboard import show_realtime_dashboard
    show_realtime_dashboard()

注意事項：
    - 需要 WebSocket 連接支援即時數據更新
    - 依賴 websocket_manager 進行數據管理
    - 需要適當的認證權限
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta
import time
import logging

# Note: Realtime components are available but not used in this implementation
from src.ui.utils.websocket_manager import (
    websocket_manager,
    DataType,
)
from src.ui.components.auth import require_auth

logger = logging.getLogger(__name__)


@require_auth
def show_realtime_dashboard():
    """顯示即時數據儀表板頁面"""
    st.set_page_config(
        page_title="即時數據儀表板",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 頁面標題
    st.title("📊 即時數據儀表板")
    st.markdown("---")

    # 側邊欄設定
    with st.sidebar:
        st.header("⚙️ 設定")

        # 自動刷新設定
        auto_refresh = st.checkbox("自動刷新", value=True, key="auto_refresh")
        refresh_interval = st.slider("刷新間隔 (秒)", 1, 30, 5, key="refresh_interval")

        # 數據源設定
        st.subheader("📡 數據源")
        data_source = st.selectbox(
            "選擇數據源", ["模擬數據", "即時數據", "歷史回放"], index=0
        )
        if data_source:
            st.info(f"當前數據源：{data_source}")
        # TODO: Implement data source switching logic

        # 監控設定
        st.subheader("👁️ 監控設定")
        enable_alerts = st.checkbox("啟用警報", value=True)
        sound_alerts = st.checkbox("聲音警報", value=False)
        if enable_alerts:
            st.success("警報系統已啟用")
        if sound_alerts:
            st.info("聲音警報已開啟")
        # TODO: Implement alert configuration logic

        # 顯示設定
        st.subheader("🎨 顯示設定")
        theme = st.selectbox("主題", ["淺色", "深色", "自動"], index=0)
        chart_style = st.selectbox("圖表風格", ["現代", "經典", "簡約"], index=0)
        if theme and chart_style:
            st.info(f"當前設定：{theme}主題，{chart_style}風格")
        # TODO: Implement theme and chart style switching logic

        # 連接狀態
        st.subheader("🔗 連接狀態")
        show_connection_status()

    # 主要內容
    main_content_area()

    # 自動刷新邏輯
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()


def show_connection_status():
    """顯示連接狀態"""
    try:
        status_info = websocket_manager.get_connection_status()
        status = status_info.get("status", "unknown")

        # 狀態顏色和圖標
        status_config = {
            "connected": {"color": "green", "icon": "🟢", "text": "已連接"},
            "connecting": {"color": "orange", "icon": "🟡", "text": "連接中"},
            "reconnecting": {"color": "orange", "icon": "🟡", "text": "重連中"},
            "disconnected": {"color": "red", "icon": "🔴", "text": "已斷開"},
            "error": {"color": "red", "icon": "🔴", "text": "錯誤"},
        }

        config = status_config.get(
            status, {"color": "gray", "icon": "⚪", "text": "未知"}
        )

        st.markdown(
            f"""
        <div style="padding: 10px; border-radius: 5px; background-color: {config['color']}20;">
            <p style="margin: 0; color: {config['color']};">
                {config['icon']} {config['text']}
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # 詳細信息
        with st.expander("詳細信息"):
            st.json(status_info)

    except Exception as e:
        st.error(f"無法獲取連接狀態: {e}")


def main_content_area():
    """主要內容區域"""
    # 頂部指標卡片
    create_top_metrics()

    st.markdown("---")

    # 主要儀表板
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📈 市場概覽", "💼 投資組合", "📊 圖表分析", "🚨 警報中心"]
    )

    with tab1:
        create_market_overview()

    with tab2:
        create_portfolio_overview()

    with tab3:
        create_chart_analysis()

    with tab4:
        create_alerts_center()


def create_top_metrics():
    """創建頂部指標卡片"""
    col1, col2, col3, col4, col5 = st.columns(5)

    # 獲取最新數據
    stock_data = websocket_manager.get_latest_data(DataType.STOCK_PRICE)
    trading_data = websocket_manager.get_latest_data(DataType.TRADING_STATUS)

    with col1:
        if stock_data and "2330.TW" in stock_data:
            price = stock_data["2330.TW"].get("price", 0)
            change_pct = stock_data["2330.TW"].get("change_percent", 0)
            st.metric("台積電", f"${price:.1f}", f"{change_pct:+.2f}%")
        else:
            st.metric("台積電", "載入中...", "")

    with col2:
        if trading_data:
            portfolio_value = trading_data.get("portfolio_value", 0)
            st.metric("投資組合", f"${portfolio_value:,.0f}", "")
        else:
            st.metric("投資組合", "載入中...", "")

    with col3:
        if trading_data:
            daily_pnl = trading_data.get("daily_pnl", 0)
            st.metric("當日損益", f"${daily_pnl:,.0f}", f"{daily_pnl:+,.0f}")
        else:
            st.metric("當日損益", "載入中...", "")

    with col4:
        if trading_data:
            active_orders = trading_data.get("active_orders", 0)
            st.metric("活躍訂單", f"{active_orders}", "")
        else:
            st.metric("活躍訂單", "載入中...", "")

    with col5:
        if trading_data:
            market_status = trading_data.get("market_status", "unknown")
            status_emoji = {
                "open": "🟢 開盤",
                "closed": "🔴 收盤",
                "pre_market": "🟡 盤前",
                "after_hours": "🟠 盤後",
            }
            st.metric("市場狀態", status_emoji.get(market_status, "⚪ 未知"), "")
        else:
            st.metric("市場狀態", "載入中...", "")


def create_market_overview():
    """創建市場概覽"""
    st.subheader("📈 市場概覽")

    # 股票選擇
    col1, col2 = st.columns([3, 1])

    with col1:
        selected_symbols = st.multiselect(
            "選擇股票",
            ["2330.TW", "2317.TW", "2454.TW", "AAPL", "MSFT", "GOOGL", "TSLA"],
            default=["2330.TW", "2317.TW", "2454.TW"],
            key="market_symbols",
        )

    with col2:
        view_mode = st.selectbox("顯示模式", ["表格", "卡片"], key="market_view")

    if selected_symbols:
        stock_data = websocket_manager.get_latest_data(DataType.STOCK_PRICE)

        if stock_data:
            if view_mode == "表格":
                create_stock_table(selected_symbols, stock_data)
            else:
                create_stock_cards(selected_symbols, stock_data)
        else:
            st.info("正在載入股價數據...")


def create_stock_table(symbols, stock_data):
    """創建股票表格"""
    rows = []
    for symbol in symbols:
        if symbol in stock_data:
            info = stock_data[symbol]
            rows.append(
                {
                    "股票代碼": symbol,
                    "當前價格": f"${info.get('price', 0):.2f}",
                    "漲跌": f"{info.get('change', 0):+.2f}",
                    "漲跌幅": f"{info.get('change_percent', 0):+.2f}%",
                    "成交量": f"{info.get('volume', 0):,}",
                    "更新時間": info.get("timestamp", "")[:19],
                }
            )

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True)


def create_stock_cards(symbols, stock_data):
    """創建股票卡片"""
    cols = st.columns(min(len(symbols), 3))

    for i, symbol in enumerate(symbols):
        col_idx = i % 3

        if symbol in stock_data:
            info = stock_data[symbol]

            with cols[col_idx]:
                change = info.get("change", 0)
                change_pct = info.get("change_percent", 0)

                # 顏色設定
                color = "green" if change >= 0 else "red"
                arrow = "↗️" if change >= 0 else "↘️"

                card_style = (
                    f"padding: 15px; border-radius: 10px; "
                    f"border: 2px solid {color}; margin: 5px 0;"
                )
                st.markdown(
                    f"""
                <div style="{card_style}">
                    <h4 style="margin: 0; color: {color};">{arrow} {symbol}</h4>
                    <h2 style="margin: 5px 0;">${info.get('price', 0):.2f}</h2>
                    <p style="margin: 0; color: {color};">
                        {change:+.2f} ({change_pct:+.2f}%)
                    </p>
                    <small>成交量: {info.get('volume', 0):,}</small>
                </div>
                """,
                    unsafe_allow_html=True,
                )


def create_portfolio_overview():
    """創建投資組合概覽"""
    st.subheader("💼 投資組合概覽")

    # 投資組合摘要
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 資產配置")

        # 模擬投資組合數據
        portfolio_data = {"股票": 60, "債券": 25, "現金": 10, "其他": 5}

        fig = px.pie(
            values=list(portfolio_data.values()),
            names=list(portfolio_data.keys()),
            title="資產配置比例",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📈 績效表現")

        # 模擬績效數據
        performance_data = {"今日": 1.2, "本週": -0.8, "本月": 3.5, "本年": 12.3}

        for period, return_pct in performance_data.items():
            color = "green" if return_pct >= 0 else "red"
            st.markdown(
                f"""
            <div style="padding: 10px; margin: 5px 0; border-left: 4px solid {color};">
                <strong>{period}</strong>:
                <span style="color: {color};">{return_pct:+.1f}%</span>
            </div>
            """,
                unsafe_allow_html=True,
            )


def create_chart_analysis():
    """創建圖表分析"""
    st.subheader("📊 圖表分析")

    # 圖表設定
    col1, col2, col3 = st.columns(3)

    with col1:
        chart_symbol = st.selectbox(
            "選擇股票", ["2330.TW", "2317.TW", "2454.TW"], key="chart_symbol"
        )

    with col2:
        time_range = st.selectbox(
            "時間範圍", ["1小時", "4小時", "1天", "1週"], key="chart_timerange"
        )

    with col3:
        chart_type = st.selectbox(
            "圖表類型", ["線圖", "蠟燭圖", "面積圖"], key="chart_type"
        )

    # 創建圖表
    create_interactive_chart(chart_symbol, time_range, chart_type)


def create_interactive_chart(symbol, time_range, chart_type):
    """創建互動式圖表"""

    # 生成模擬數據
    points = {"1小時": 60, "4小時": 240, "1天": 390, "1週": 2730}
    num_points = points.get(time_range, 60)

    # 時間序列
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=num_points)
    time_series = pd.date_range(start=start_time, end=end_time, periods=num_points)

    # 價格數據
    np.random.seed(42)
    base_price = 580.0
    returns = np.random.normal(0, 0.001, num_points)
    prices = [base_price]

    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))

    df = pd.DataFrame(
        {
            "timestamp": time_series,
            "price": prices,
            "volume": np.random.randint(100000, 1000000, num_points),
        }
    )

    # 根據圖表類型創建圖表
    if chart_type == "線圖":
        fig = px.line(df, x="timestamp", y="price", title=f"{symbol} 價格走勢")
    elif chart_type == "面積圖":
        fig = px.area(df, x="timestamp", y="price", title=f"{symbol} 價格走勢")
    else:  # 蠟燭圖
        df["open"] = df["price"].shift(1).fillna(df["price"])
        df["high"] = df[["open", "price"]].max(axis=1) * 1.005
        df["low"] = df[["open", "price"]].min(axis=1) * 0.995
        df["close"] = df["price"]

        fig = go.Figure(
            data=go.Candlestick(
                x=df["timestamp"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
            )
        )
        fig.update_layout(title=f"{symbol} 蠟燭圖")

    # 更新圖表佈局
    fig.update_layout(
        height=500, xaxis_title="時間", yaxis_title="價格", showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)


def create_alerts_center():
    """創建警報中心"""
    st.subheader("🚨 警報中心")

    # 警報設定
    with st.expander("⚙️ 警報設定", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            alert_symbol = st.selectbox("監控股票", ["2330.TW", "2317.TW", "2454.TW"])
            alert_type = st.selectbox(
                "警報類型", ["價格突破", "價格跌破", "成交量異常"]
            )

        with col2:
            threshold_value = st.number_input("閾值", value=600.0, step=1.0)
            enable_sound = st.checkbox("聲音警報")

        with col3:
            enable_email = st.checkbox("郵件通知")
            enable_sms = st.checkbox("簡訊通知")

        # TODO: Implement alert creation logic using these variables

        if st.button("新增警報", type="primary"):
            # 使用所有設定變數
            notification_methods = []
            if enable_sound:
                notification_methods.append("聲音")
            if enable_email:
                notification_methods.append("郵件")
            if enable_sms:
                notification_methods.append("簡訊")

            notification_text = (
                "、".join(notification_methods) if notification_methods else "無"
            )
            st.success(
                f"已新增 {alert_symbol} {alert_type} 警報\n"
                f"閾值：{threshold_value}\n"
                f"通知方式：{notification_text}"
            )

    # 活躍警報
    st.subheader("🔔 活躍警報")

    active_alerts = [
        {"股票": "2330.TW", "類型": "價格突破", "閾值": "600", "狀態": "監控中"},
        {"股票": "2317.TW", "類型": "成交量異常", "閾值": "200%", "狀態": "監控中"},
    ]

    if active_alerts:
        df = pd.DataFrame(active_alerts)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("目前沒有活躍的警報")

    # 警報歷史
    st.subheader("📋 警報歷史")

    alert_history = [
        {
            "時間": "10:35:22",
            "股票": "2330.TW",
            "類型": "價格突破",
            "內容": "價格突破 600 元",
            "狀態": "已處理",
        },
        {
            "時間": "10:20:15",
            "股票": "2317.TW",
            "類型": "成交量異常",
            "內容": "成交量超過平均值 200%",
            "狀態": "待處理",
        },
        {
            "時間": "09:45:33",
            "股票": "2454.TW",
            "類型": "價格跌破",
            "內容": "價格跌破 85 元",
            "狀態": "已處理",
        },
    ]

    df_history = pd.DataFrame(alert_history)
    st.dataframe(df_history, use_container_width=True)


if __name__ == "__main__":
    show_realtime_dashboard()
