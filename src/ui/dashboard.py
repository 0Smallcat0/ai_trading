"""
儀表板模組

此模組實現了系統儀表板，顯示系統概覽和關鍵指標。
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px


def show_asset_overview():
    """顯示資產概覽"""
    st.subheader("資產概覽")

    # 模擬資產數據
    total_assets = 10500000
    cash = 2500000
    stocks = 8000000

    # 顯示資產總值
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("總資產", f"${total_assets:,}", "+2.5%")
    with col2:
        st.metric("現金", f"${cash:,}", "-1.2%")
    with col3:
        st.metric("股票", f"${stocks:,}", "+3.8%")

    # 資產配置圓餅圖
    asset_data = pd.DataFrame(
        {
            "資產類型": ["台股", "美股", "ETF", "現金"],
            "金額": [5000000, 2000000, 1000000, 2500000],
        }
    )

    fig = px.pie(
        asset_data, names="資產類型", values="金額", title="資產配置", hole=0.4
    )
    st.plotly_chart(fig, use_container_width=True)


def show_today_trades():
    """顯示今日交易"""
    st.subheader("今日交易")

    # 模擬交易數據
    trades = {
        "時間": ["09:01:05", "09:15:30", "10:22:15", "11:05:45", "13:30:22"],
        "股票": ["2330.TW", "2317.TW", "2454.TW", "2330.TW", "2308.TW"],
        "方向": ["買入", "賣出", "買入", "賣出", "買入"],
        "價格": [550.0, 105.5, 880.0, 555.0, 32.5],
        "數量": [1000, 5000, 500, 1000, 10000],
        "金額": [550000, 527500, 440000, 555000, 325000],
        "策略": ["均線交叉", "停利", "突破", "停損", "均值回歸"],
    }

    trades_df = pd.DataFrame(trades)
    st.dataframe(trades_df, use_container_width=True)

    # 交易統計
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("交易筆數", "5")
    with col2:
        st.metric("買入金額", "$1,315,000")
    with col3:
        st.metric("賣出金額", "$1,082,500")


def show_performance_metrics():
    """顯示績效指標"""
    st.subheader("績效指標")

    # 模擬績效數據
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("年化報酬", "18.5%", "+2.3%")
    with col2:
        st.metric("夏普比率", "1.85", "+0.15")
    with col3:
        st.metric("最大回撤", "-12.5%", "+0.5%")
    with col4:
        st.metric("勝率", "65.8%", "+1.2%")

    # 績效走勢圖
    dates = pd.date_range(
        start=datetime.now() - timedelta(days=180), end=datetime.now(), freq="D"
    )

    # 模擬資產曲線
    np.random.seed(42)
    base_value = 10000000
    daily_returns = np.random.normal(0.0005, 0.01, len(dates))
    cumulative_returns = np.cumprod(1 + daily_returns)
    asset_values = base_value * cumulative_returns

    # 模擬基準曲線
    benchmark_returns = np.random.normal(0.0003, 0.008, len(dates))
    benchmark_cumulative = np.cumprod(1 + benchmark_returns)
    benchmark_values = base_value * benchmark_cumulative

    # 創建數據框
    performance_data = pd.DataFrame(
        {"日期": dates, "策略資產": asset_values, "基準指數": benchmark_values}
    )

    # 繪製圖表
    fig = px.line(
        performance_data, x="日期", y=["策略資產", "基準指數"], title="資產走勢對比"
    )
    st.plotly_chart(fig, use_container_width=True)


def show_risk_metrics():
    """顯示風險指標"""
    st.subheader("風險指標")

    # 模擬風險數據
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("波動率", "15.2%", "-0.8%")
    with col2:
        st.metric("Beta", "0.85", "-0.05")
    with col3:
        st.metric("VaR (95%)", "-2.3%", "+0.1%")
    with col4:
        st.metric("CVaR", "-3.1%", "+0.2%")

    # 風險分布圖
    returns = np.random.normal(0.0005, 0.015, 1000)
    returns_df = pd.DataFrame({"日收益率": returns})

    fig = px.histogram(
        returns_df, x="日收益率", nbins=50, title="收益率分布", marginal="box"
    )

    # 添加 VaR 和 CVaR 線
    var_95 = np.percentile(returns, 5)
    cvar_95 = returns[returns <= var_95].mean()

    fig.add_vline(
        x=var_95, line_dash="dash", line_color="red", annotation_text="VaR (95%)"
    )
    fig.add_vline(
        x=cvar_95, line_dash="dash", line_color="darkred", annotation_text="CVaR"
    )

    st.plotly_chart(fig, use_container_width=True)


def show_market_overview():
    """顯示市場概覽"""
    st.subheader("市場概覽")

    # 模擬市場數據
    market_indices = {
        "指數": ["台灣加權", "道瓊工業", "納斯達克", "S&P 500", "上證指數", "日經225"],
        "最新值": [17500.25, 35750.50, 14320.80, 4550.25, 3250.75, 28500.30],
        "漲跌": ["+125.50", "-50.25", "+80.30", "+15.75", "-25.50", "+150.25"],
        "漲跌幅": ["+0.72%", "-0.14%", "+0.56%", "+0.35%", "-0.78%", "+0.53%"],
    }

    market_df = pd.DataFrame(market_indices)

    # 添加顏色
    def color_change(val):
        if val.startswith("+"):
            return "color: green"
        elif val.startswith("-"):
            return "color: red"
        else:
            return ""

    styled_df = market_df.style.applymap(color_change, subset=["漲跌", "漲跌幅"])

    st.dataframe(styled_df, use_container_width=True)

    # 熱門股票
    hot_stocks = {
        "股票": ["台積電", "鴻海", "聯發科", "台達電", "中華電"],
        "代碼": ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2412.TW"],
        "最新價": [550.00, 105.50, 880.00, 280.50, 120.00],
        "漲跌幅": ["+1.85%", "-0.47%", "+2.33%", "+0.54%", "-0.83%"],
        "成交量(張)": [25000, 15000, 8000, 5000, 3000],
    }

    hot_stocks_df = pd.DataFrame(hot_stocks)
    styled_hot_df = hot_stocks_df.style.applymap(color_change, subset=["漲跌幅"])

    st.dataframe(styled_hot_df, use_container_width=True)


def show():
    """顯示儀表板"""
    st.title("儀表板")

    # 顯示當前時間
    st.write(f"最後更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 第一行：資產概覽和今日交易
    col1, col2 = st.columns(2)

    with col1:
        show_asset_overview()

    with col2:
        show_today_trades()

    # 第二行：績效指標和風險指標
    col3, col4 = st.columns(2)

    with col3:
        show_performance_metrics()

    with col4:
        show_risk_metrics()

    # 第三行：市場概覽
    show_market_overview()


if __name__ == "__main__":
    show()
