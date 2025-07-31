"""
即時數據更新組件

提供即時股價、交易狀態等數據的 Streamlit 組件。
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging

from src.ui.utils.websocket_manager import (
    websocket_manager,
    DataType,
    init_websocket_connection,
    create_realtime_stock_widget,
    create_connection_status_widget,
)

logger = logging.getLogger(__name__)


class RealtimeDataManager:
    """即時數據管理器"""

    def __init__(self):
        """初始化即時數據管理器"""
        self.data_history: Dict[str, List[Dict[str, Any]]] = {}
        self.max_history_length = 100

    def add_data_point(self, data_type: str, data: Dict[str, Any]):
        """添加數據點到歷史記錄

        Args:
            data_type: 數據類型
            data: 數據內容
        """
        if data_type not in self.data_history:
            self.data_history[data_type] = []

        # 添加時間戳
        data_with_timestamp = {**data, "timestamp": datetime.now()}

        self.data_history[data_type].append(data_with_timestamp)

        # 限制歷史記錄長度
        if len(self.data_history[data_type]) > self.max_history_length:
            self.data_history[data_type] = self.data_history[data_type][
                -self.max_history_length :
            ]

    def get_history(self, data_type: str) -> List[Dict[str, Any]]:
        """獲取歷史數據

        Args:
            data_type: 數據類型

        Returns:
            歷史數據列表
        """
        return self.data_history.get(data_type, [])


# 全域即時數據管理器
realtime_manager = RealtimeDataManager()


def create_realtime_dashboard():
    """創建即時數據儀表板"""
    st.title("📊 即時數據儀表板")

    # 初始化 WebSocket 連接
    init_websocket_connection()

    # 連接狀態區域
    with st.expander("🔗 連接狀態", expanded=False):
        create_connection_status_widget()

    # 主要內容區域
    tab1, tab2, tab3 = st.tabs(["📈 即時股價", "💼 交易狀態", "📊 歷史趨勢"])

    with tab1:
        create_stock_price_section()

    with tab2:
        create_trading_status_section()

    with tab3:
        create_historical_trends_section()


def create_stock_price_section():
    """創建股價區域"""
    st.subheader("📈 即時股價監控")

    # 股票選擇
    col1, col2 = st.columns([3, 1])

    with col1:
        selected_symbols = st.multiselect(
            "選擇股票",
            ["2330.TW", "2317.TW", "2454.TW", "AAPL", "MSFT", "GOOGL", "TSLA"],
            default=["2330.TW", "2317.TW", "2454.TW"],
        )

    with col2:
        auto_refresh = st.checkbox("自動刷新", value=True)
        refresh_interval = st.selectbox("刷新間隔", [1, 2, 5, 10], index=0)

    if selected_symbols:
        # 即時股價小工具
        create_realtime_stock_widget(selected_symbols)

        # 詳細股價表格
        st.subheader("📋 詳細股價資訊")
        create_stock_price_table(selected_symbols)


def create_stock_price_table(symbols: List[str]):
    """創建股價表格

    Args:
        symbols: 股票代碼列表
    """
    # 創建表格佔位符
    table_placeholder = st.empty()

    def update_price_table(data: Dict[str, Any]):
        """更新價格表格"""
        rows = []
        for symbol in symbols:
            if symbol in data:
                stock_info = data[symbol]
                rows.append(
                    {
                        "股票代碼": symbol,
                        "當前價格": f"${stock_info.get('price', 0):.2f}",
                        "漲跌": f"{stock_info.get('change', 0):+.2f}",
                        "漲跌幅": f"{stock_info.get('change_percent', 0):+.2f}%",
                        "成交量": f"{stock_info.get('volume', 0):,}",
                        "更新時間": stock_info.get("timestamp", "")[:19],
                    }
                )

        if rows:
            df = pd.DataFrame(rows)

            # 添加顏色樣式
            def color_negative_red(val):
                if isinstance(val, str) and val.startswith(("+", "-")):
                    color = "green" if val.startswith("+") else "red"
                    return f"color: {color}"
                return ""

            styled_df = df.style.applymap(color_negative_red, subset=["漲跌", "漲跌幅"])
            table_placeholder.dataframe(styled_df, use_container_width=True)

    # 訂閱股價數據更新
    websocket_manager.subscribe(DataType.STOCK_PRICE, update_price_table)

    # 顯示初始數據
    latest_data = websocket_manager.get_latest_data(DataType.STOCK_PRICE)
    if latest_data:
        update_price_table(latest_data)


def create_trading_status_section():
    """創建交易狀態區域"""
    st.subheader("💼 交易狀態監控")

    # 創建狀態指標
    col1, col2, col3, col4 = st.columns(4)

    # 創建佔位符
    placeholders = {
        "market_status": col1.empty(),
        "active_orders": col2.empty(),
        "portfolio_value": col3.empty(),
        "daily_pnl": col4.empty(),
    }

    def update_trading_status(data: Dict[str, Any]):
        """更新交易狀態"""
        # 市場狀態
        market_status = data.get("market_status", "unknown")
        status_emoji = {
            "open": "🟢",
            "closed": "🔴",
            "pre_market": "🟡",
            "after_hours": "🟠",
        }

        placeholders["market_status"].metric(
            "市場狀態",
            f"{status_emoji.get(market_status, '⚪')} {market_status.title()}",
        )

        # 活躍訂單
        placeholders["active_orders"].metric("活躍訂單", data.get("active_orders", 0))

        # 投資組合價值
        portfolio_value = data.get("portfolio_value", 0)
        placeholders["portfolio_value"].metric(
            "投資組合價值", f"${portfolio_value:,.2f}"
        )

        # 當日損益
        daily_pnl = data.get("daily_pnl", 0)
        pnl_delta = f"{daily_pnl:+,.2f}"
        placeholders["daily_pnl"].metric(
            "當日損益", f"${daily_pnl:,.2f}", delta=pnl_delta
        )

    # 訂閱交易狀態數據
    websocket_manager.subscribe(DataType.TRADING_STATUS, update_trading_status)

    # 顯示初始數據
    latest_data = websocket_manager.get_latest_data(DataType.TRADING_STATUS)
    if latest_data:
        update_trading_status(latest_data)

    # 交易活動日誌
    st.subheader("📝 交易活動日誌")
    create_trading_activity_log()


def create_trading_activity_log():
    """創建交易活動日誌"""
    log_placeholder = st.empty()

    # 模擬交易活動數據
    activities = [
        {
            "時間": "10:30:15",
            "類型": "買入",
            "股票": "2330.TW",
            "數量": 1000,
            "價格": 580.0,
        },
        {
            "時間": "10:25:32",
            "類型": "賣出",
            "股票": "2317.TW",
            "數量": 500,
            "價格": 125.5,
        },
        {
            "時間": "10:20:45",
            "類型": "買入",
            "股票": "2454.TW",
            "數量": 2000,
            "價格": 89.2,
        },
        {
            "時間": "10:15:18",
            "類型": "賣出",
            "股票": "AAPL",
            "數量": 100,
            "價格": 175.3,
        },
    ]

    df = pd.DataFrame(activities)

    # 添加顏色樣式
    def color_trade_type(val):
        if val == "買入":
            return "color: green"
        elif val == "賣出":
            return "color: red"
        return ""

    styled_df = df.style.applymap(color_trade_type, subset=["類型"])
    log_placeholder.dataframe(styled_df, use_container_width=True)


def create_historical_trends_section():
    """創建歷史趨勢區域"""
    st.subheader("📊 歷史趨勢分析")

    # 時間範圍選擇
    col1, col2 = st.columns(2)

    with col1:
        time_range = st.selectbox(
            "時間範圍", ["最近1小時", "最近4小時", "今日", "最近3天"], index=0
        )

    with col2:
        chart_type = st.selectbox("圖表類型", ["線圖", "蠟燭圖", "面積圖"], index=0)

    # 創建趨勢圖表
    create_price_trend_chart(time_range, chart_type)


def create_price_trend_chart(time_range: str, chart_type: str):
    """創建價格趨勢圖表

    Args:
        time_range: 時間範圍
        chart_type: 圖表類型
    """
    # 生成模擬歷史數據
    import numpy as np

    # 根據時間範圍確定數據點數量
    data_points = {
        "最近1小時": 60,
        "最近4小時": 240,
        "今日": 390,  # 6.5小時交易時間
        "最近3天": 1170,
    }

    points = data_points.get(time_range, 60)

    # 生成時間序列
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=points)
    time_series = pd.date_range(start=start_time, end=end_time, periods=points)

    # 生成價格數據（隨機遊走）
    np.random.seed(42)
    base_price = 580.0
    returns = np.random.normal(0, 0.001, points)  # 0.1% 標準差
    prices = [base_price]

    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))

    # 創建 DataFrame
    df = pd.DataFrame(
        {
            "timestamp": time_series,
            "price": prices,
            "volume": np.random.randint(100000, 1000000, points),
        }
    )

    # 根據圖表類型創建圖表
    if chart_type == "線圖":
        fig = px.line(
            df, x="timestamp", y="price", title=f"2330.TW 價格趨勢 ({time_range})"
        )
    elif chart_type == "面積圖":
        fig = px.area(
            df, x="timestamp", y="price", title=f"2330.TW 價格趨勢 ({time_range})"
        )
    else:  # 蠟燭圖
        # 為蠟燭圖生成 OHLC 數據
        df["open"] = df["price"].shift(1).fillna(df["price"])
        df["high"] = df[["open", "price"]].max(axis=1) * (
            1 + np.random.uniform(0, 0.005, points)
        )
        df["low"] = df[["open", "price"]].min(axis=1) * (
            1 - np.random.uniform(0, 0.005, points)
        )
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
        fig.update_layout(title=f"2330.TW 蠟燭圖 ({time_range})")

    # 更新圖表佈局
    fig.update_layout(
        xaxis_title="時間", yaxis_title="價格 (TWD)", height=400, showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # 顯示統計信息
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("最高價", f"${df['price'].max():.2f}")

    with col2:
        st.metric("最低價", f"${df['price'].min():.2f}")

    with col3:
        price_change = df["price"].iloc[-1] - df["price"].iloc[0]
        st.metric("區間漲跌", f"{price_change:+.2f}")

    with col4:
        volatility = df["price"].std()
        st.metric("波動率", f"{volatility:.2f}")


def create_realtime_alerts():
    """創建即時警報組件"""
    st.subheader("🚨 即時警報")

    # 警報設定
    with st.expander("⚙️ 警報設定"):
        col1, col2 = st.columns(2)

        with col1:
            alert_symbol = st.selectbox("監控股票", ["2330.TW", "2317.TW", "2454.TW"])
            price_threshold = st.number_input("價格閾值", value=600.0, step=1.0)

        with col2:
            alert_type = st.selectbox(
                "警報類型", ["價格突破", "價格跌破", "成交量異常"]
            )
            enable_alert = st.checkbox("啟用警報", value=True)

    # 警報歷史
    st.subheader("📋 警報歷史")

    # 模擬警報數據
    alerts = [
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

    df = pd.DataFrame(alerts)
    st.dataframe(df, use_container_width=True)
