"""互動式圖表頁面

提供高度互動的 Plotly 圖表展示和分析功能。

此模組提供以下功能：
- 圖表聯動演示
- 進階K線圖分析
- 技術指標分析（MACD、布林通道、KD指標）
- 多時間框架分析
- 相關性分析
- 績效比較
- 成交量分析

主要類別：
    無

主要函數：
    show_interactive_charts: 主要頁面顯示函數
    show_linked_charts_demo: 顯示圖表聯動演示
    show_advanced_candlestick: 顯示進階K線圖
    show_technical_indicators: 顯示技術指標分析
    show_multi_timeframe_analysis: 顯示多時間框架分析
    show_correlation_analysis: 顯示相關性分析
    show_performance_comparison: 顯示績效比較
    show_volume_analysis: 顯示成交量分析

使用範例：
    from src.ui.pages.interactive_charts import show_interactive_charts
    show_interactive_charts()

注意事項：
    - 依賴 interactive_charts 組件進行圖表渲染
    - 需要適當的認證權限
    - 支援多種圖表主題和互動功能
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict
import logging

from src.ui.components.interactive_charts import (
    create_linked_charts_demo,
    create_enhanced_candlestick_chart,
    create_correlation_heatmap,
    create_performance_comparison_chart,
    create_volume_profile_chart,
    create_multi_timeframe_chart,
    create_advanced_technical_indicators,
    generate_sample_stock_data,
    ChartTheme,
)
from src.ui.components.auth import require_auth

logger = logging.getLogger(__name__)


@require_auth
def show_interactive_charts():
    """顯示互動式圖表頁面"""
    st.set_page_config(
        page_title="互動式圖表",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 頁面標題
    st.title("📊 互動式圖表分析")
    st.markdown("---")

    # 側邊欄導航
    with st.sidebar:
        st.header("📈 圖表類型")

        chart_type = st.selectbox(
            "選擇圖表類型",
            [
                "圖表聯動演示",
                "進階K線圖",
                "技術指標分析",
                "多時間框架",
                "相關性分析",
                "績效比較",
                "成交量分析",
            ],
            index=0,
        )

        st.markdown("---")

        # 數據設定
        st.subheader("⚙️ 數據設定")

        data_days = st.slider(
            "數據天數", min_value=30, max_value=365, value=180, step=30
        )

        refresh_data = st.button("🔄 刷新數據", type="secondary")
        if refresh_data:
            st.success("數據已刷新")
            st.rerun()
        # TODO: Implement data refresh functionality

    # 主要內容區域
    if chart_type == "圖表聯動演示":
        show_linked_charts_demo()
    elif chart_type == "進階K線圖":
        show_advanced_candlestick()
    elif chart_type == "技術指標分析":
        show_technical_indicators(data_days)
    elif chart_type == "多時間框架":
        show_multi_timeframe_analysis(data_days)
    elif chart_type == "相關性分析":
        show_correlation_analysis(data_days)
    elif chart_type == "績效比較":
        show_performance_comparison(data_days)
    elif chart_type == "成交量分析":
        show_volume_analysis(data_days)


def show_linked_charts_demo():
    """顯示圖表聯動演示"""
    st.subheader("🔗 圖表聯動演示")

    st.info(
        """
    **功能特色：**
    - 🎯 多圖表聯動效果
    - 🎨 主題切換功能
    - ⚙️ 互動控制選項
    - 📊 多種圖表類型
    """
    )

    # 使用組件中的聯動演示
    create_linked_charts_demo()


def show_advanced_candlestick():
    """顯示進階K線圖"""
    st.subheader("📈 進階K線圖分析")

    # 控制選項
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        symbol = st.selectbox(
            "股票代碼", ["2330.TW", "2317.TW", "2454.TW", "AAPL", "MSFT"], index=0
        )

    with col2:
        show_volume = st.checkbox("顯示成交量", value=True)

    with col3:
        show_indicators = st.checkbox("顯示技術指標", value=True)

    with col4:
        chart_height = st.slider("圖表高度", 400, 800, 600, 50)

    # 生成數據
    data = generate_sample_stock_data(symbol=symbol, days=252)

    # 創建圖表
    fig = create_enhanced_candlestick_chart(
        data=data,
        chart_id="advanced_candlestick",
        title=f"{symbol} 進階K線圖",
        height=chart_height,
        show_volume=show_volume,
        show_indicators=show_indicators,
    )

    # 顯示圖表
    st.plotly_chart(fig, use_container_width=True)

    # 顯示統計信息
    show_stock_statistics(data)


def show_technical_indicators(data_days: int):
    """顯示技術指標分析"""
    st.subheader("📊 技術指標分析")

    # 股票選擇
    symbol = st.selectbox(
        "選擇股票", ["2330.TW", "2317.TW", "2454.TW"], key="tech_symbol"
    )

    # 生成數據
    data = generate_sample_stock_data(symbol=symbol, days=data_days)

    # 計算技術指標
    indicators = create_advanced_technical_indicators(data)

    # 創建標籤頁
    tab1, tab2, tab3 = st.tabs(["MACD", "布林通道", "KD指標"])

    with tab1:
        show_macd_analysis(data, indicators)

    with tab2:
        show_bollinger_bands_analysis(data, indicators)

    with tab3:
        show_kd_analysis(data, indicators)


def show_macd_analysis(data: pd.DataFrame, indicators: dict):
    """顯示MACD分析"""

    theme = ChartTheme.get_theme(st.session_state.chart_config["theme"])

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.1,
        subplot_titles=["價格與MACD", "MACD柱狀圖"],
        row_heights=[0.7, 0.3],
    )

    # 價格線
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["close"],
            mode="lines",
            name="收盤價",
            line={"color": theme["primary"]},
        ),
        row=1,
        col=1,
    )

    # MACD線
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=indicators["macd"],
            mode="lines",
            name="MACD",
            line={"color": theme["secondary"]},
        ),
        row=2,
        col=1,
    )

    # 信號線
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=indicators["macd_signal"],
            mode="lines",
            name="信號線",
            line={"color": theme["warning"]},
        ),
        row=2,
        col=1,
    )

    # MACD柱狀圖
    colors = [
        theme["success"] if x >= 0 else theme["danger"]
        for x in indicators["macd_histogram"]
    ]

    fig.add_trace(
        go.Bar(
            x=data.index,
            y=indicators["macd_histogram"],
            name="MACD柱狀圖",
            marker_color=colors,
            opacity=0.7,
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        height=600,
        plot_bgcolor=theme["background"],
        paper_bgcolor=theme["background"],
        font_color=theme["text"],
    )

    st.plotly_chart(fig, use_container_width=True)


def show_bollinger_bands_analysis(data: pd.DataFrame, indicators: dict):
    """顯示布林通道分析"""

    theme = ChartTheme.get_theme(st.session_state.chart_config["theme"])

    fig = go.Figure()

    # 上軌
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=indicators["bb_upper"],
            mode="lines",
            name="上軌",
            line={"color": theme["danger"], "dash": "dash"},
        )
    )

    # 中軌（移動平均）
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=indicators["bb_middle"],
            mode="lines",
            name="中軌(MA20)",
            line={"color": theme["primary"]},
        )
    )

    # 下軌
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=indicators["bb_lower"],
            mode="lines",
            name="下軌",
            line={"color": theme["success"], "dash": "dash"},
            fill="tonexty",
            fillcolor="rgba(0,100,80,0.1)",
        )
    )

    # 價格線
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["close"],
            mode="lines",
            name="收盤價",
            line={"color": theme["text"], "width": 2},
        )
    )

    fig.update_layout(
        title="布林通道分析",
        height=500,
        plot_bgcolor=theme["background"],
        paper_bgcolor=theme["background"],
        font_color=theme["text"],
    )

    st.plotly_chart(fig, use_container_width=True)


def show_kd_analysis(data: pd.DataFrame, indicators: dict):
    """顯示KD指標分析"""

    theme = ChartTheme.get_theme(st.session_state.chart_config["theme"])

    fig = go.Figure()

    # K線
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=indicators["k"],
            mode="lines",
            name="K值",
            line={"color": theme["primary"], "width": 2},
        )
    )

    # D線
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=indicators["d"],
            mode="lines",
            name="D值",
            line={"color": theme["secondary"], "width": 2},
        )
    )

    # 超買超賣線
    fig.add_hline(
        y=80, line_dash="dash", line_color=theme["danger"], annotation_text="超買線(80)"
    )
    fig.add_hline(
        y=20,
        line_dash="dash",
        line_color=theme["success"],
        annotation_text="超賣線(20)",
    )

    fig.update_layout(
        title="KD指標分析",
        yaxis_title="KD值",
        height=400,
        plot_bgcolor=theme["background"],
        paper_bgcolor=theme["background"],
        font_color=theme["text"],
        yaxis={"range": [0, 100]},
    )

    st.plotly_chart(fig, use_container_width=True)


def show_multi_timeframe_analysis(data_days: int):
    """顯示多時間框架分析"""
    st.subheader("⏰ 多時間框架分析")

    symbol = st.selectbox(
        "選擇股票", ["2330.TW", "2317.TW", "2454.TW"], key="mtf_symbol"
    )

    # 生成數據
    data = generate_sample_stock_data(symbol=symbol, days=data_days)

    # 創建多時間框架圖表
    fig = create_multi_timeframe_chart(data)

    st.plotly_chart(fig, use_container_width=True)

    # 分析說明
    st.info(
        """
    **多時間框架分析說明：**
    - 📅 **日線圖**：短期趨勢和交易信號
    - 📊 **週線圖**：中期趨勢確認
    - 📈 **月線圖**：長期趨勢判斷
    """
    )


def show_correlation_analysis(data_days: int):
    """顯示相關性分析"""
    st.subheader("🔗 股票相關性分析")

    # 生成多股票數據
    symbols = ["2330.TW", "2317.TW", "2454.TW", "2412.TW", "2308.TW"]
    stock_data = {}

    for symbol in symbols:
        stock_data[symbol] = generate_sample_stock_data(
            symbol=symbol, days=data_days, start_price=np.random.uniform(100, 600)
        )

    # 準備相關性數據
    price_data = pd.DataFrame(
        {symbol: data["close"] for symbol, data in stock_data.items()}
    )

    # 創建相關性熱力圖
    fig = create_correlation_heatmap(price_data, title="台股相關性分析")

    st.plotly_chart(fig, use_container_width=True)

    # 顯示相關性統計
    show_correlation_statistics(price_data)


def show_performance_comparison(data_days: int):
    """顯示績效比較"""
    st.subheader("📊 投資組合績效比較")

    # 生成多股票數據
    symbols = ["2330.TW", "2317.TW", "2454.TW"]
    performance_data = {}

    for symbol in symbols:
        data = generate_sample_stock_data(
            symbol=symbol, days=data_days, start_price=np.random.uniform(100, 600)
        )
        performance_data[symbol] = data["close"]

    # 創建績效比較圖
    fig = create_performance_comparison_chart(performance_data)

    st.plotly_chart(fig, use_container_width=True)

    # 顯示績效統計
    show_performance_statistics(performance_data)


def show_volume_analysis(data_days: int):
    """顯示成交量分析"""
    st.subheader("📊 成交量分析")

    symbol = st.selectbox(
        "選擇股票", ["2330.TW", "2317.TW", "2454.TW"], key="volume_symbol"
    )

    # 生成數據
    data = generate_sample_stock_data(symbol=symbol, days=data_days)

    # 創建成交量分佈圖
    fig = create_volume_profile_chart(data, title=f"{symbol} 成交量分佈分析")

    st.plotly_chart(fig, use_container_width=True)

    # 顯示成交量統計
    show_volume_statistics(data)


def show_stock_statistics(data: pd.DataFrame):
    """顯示股票統計信息"""
    st.subheader("📈 統計信息")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("最高價", f"${data['high'].max():.2f}")

    with col2:
        st.metric("最低價", f"${data['low'].min():.2f}")

    with col3:
        volatility = data["close"].pct_change().std() * np.sqrt(252) * 100
        st.metric("年化波動率", f"{volatility:.1f}%")

    with col4:
        total_return = (data["close"].iloc[-1] / data["close"].iloc[0] - 1) * 100
        st.metric("總報酬率", f"{total_return:+.1f}%")


def show_correlation_statistics(data: pd.DataFrame):
    """顯示相關性統計"""
    st.subheader("📊 相關性統計")

    corr_matrix = data.corr()

    # 找出最高和最低相關性
    corr_values = []
    for i, col_i in enumerate(corr_matrix.columns):
        for j in range(i + 1, len(corr_matrix.columns)):
            col_j = corr_matrix.columns[j]
            corr_values.append(
                {
                    "pair": f"{col_i} - {col_j}",
                    "correlation": corr_matrix.iloc[i, j],
                }
            )

    corr_df = pd.DataFrame(corr_values).sort_values("correlation", ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        st.write("**最高相關性**")
        st.dataframe(corr_df.head(3), use_container_width=True)

    with col2:
        st.write("**最低相關性**")
        st.dataframe(corr_df.tail(3), use_container_width=True)


def show_performance_statistics(data: Dict[str, pd.Series]):
    """顯示績效統計"""
    st.subheader("📊 績效統計")

    stats = []
    for symbol, prices in data.items():
        returns = prices.pct_change().dropna()
        total_return = (prices.iloc[-1] / prices.iloc[0] - 1) * 100
        volatility = returns.std() * np.sqrt(252) * 100
        sharpe = (returns.mean() * 252) / (returns.std() * np.sqrt(252))

        stats.append(
            {
                "股票": symbol,
                "總報酬率(%)": f"{total_return:.2f}",
                "年化波動率(%)": f"{volatility:.2f}",
                "夏普比率": f"{sharpe:.2f}",
            }
        )

    stats_df = pd.DataFrame(stats)
    st.dataframe(stats_df, use_container_width=True)


def show_volume_statistics(data: pd.DataFrame):
    """顯示成交量統計"""
    st.subheader("📊 成交量統計")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("平均成交量", f"{data['volume'].mean():,.0f}")

    with col2:
        st.metric("最大成交量", f"{data['volume'].max():,.0f}")

    with col3:
        st.metric("最小成交量", f"{data['volume'].min():,.0f}")

    with col4:
        volume_volatility = data["volume"].std() / data["volume"].mean()
        st.metric("成交量變異係數", f"{volume_volatility:.2f}")


if __name__ == "__main__":
    show_interactive_charts()
