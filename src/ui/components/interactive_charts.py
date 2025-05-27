"""
互動式圖表組件

提供高度互動的 Plotly 圖表，支援縮放、篩選、鑽取、聯動等功能。
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
import logging
import json

logger = logging.getLogger(__name__)


class ChartTheme:
    """圖表主題配置"""

    THEMES = {
        "light": {
            "background": "#FFFFFF",
            "grid": "#E5E5E5",
            "text": "#333333",
            "primary": "#1f77b4",
            "secondary": "#ff7f0e",
            "success": "#2ca02c",
            "danger": "#d62728",
            "warning": "#ff7f0e",
        },
        "dark": {
            "background": "#1E1E1E",
            "grid": "#404040",
            "text": "#FFFFFF",
            "primary": "#00D4FF",
            "secondary": "#FF6B35",
            "success": "#00C851",
            "danger": "#FF4444",
            "warning": "#FFBB33",
        },
        "professional": {
            "background": "#F8F9FA",
            "grid": "#DEE2E6",
            "text": "#212529",
            "primary": "#007BFF",
            "secondary": "#6C757D",
            "success": "#28A745",
            "danger": "#DC3545",
            "warning": "#FFC107",
        },
    }

    @classmethod
    def get_theme(cls, theme_name: str) -> Dict[str, str]:
        """獲取主題配置

        Args:
            theme_name: 主題名稱

        Returns:
            主題配置字典
        """
        return cls.THEMES.get(theme_name, cls.THEMES["light"])


class InteractiveChartManager:
    """互動式圖表管理器"""

    def __init__(self):
        """初始化圖表管理器"""
        self.chart_registry: Dict[str, Dict[str, Any]] = {}
        self.chart_links: Dict[str, List[str]] = {}
        self.selected_data: Dict[str, Any] = {}

        # 初始化 session state
        if "chart_config" not in st.session_state:
            st.session_state.chart_config = {
                "theme": "light",
                "show_crossfilter": True,
                "enable_zoom": True,
                "show_toolbar": True,
                "animation_duration": 500,
            }

    def register_chart(
        self,
        chart_id: str,
        chart_type: str,
        data_source: str,
        update_callback: Optional[Callable] = None,
    ):
        """註冊圖表

        Args:
            chart_id: 圖表唯一標識
            chart_type: 圖表類型
            data_source: 數據源
            update_callback: 更新回調函數
        """
        self.chart_registry[chart_id] = {
            "type": chart_type,
            "data_source": data_source,
            "update_callback": update_callback,
            "last_update": datetime.now(),
        }

        if chart_id not in self.chart_links:
            self.chart_links[chart_id] = []

    def link_charts(self, source_chart: str, target_charts: List[str]):
        """建立圖表聯動關係

        Args:
            source_chart: 源圖表ID
            target_charts: 目標圖表ID列表
        """
        if source_chart in self.chart_registry:
            self.chart_links[source_chart] = target_charts

    def update_chart_selection(self, chart_id: str, selected_data: Dict[str, Any]):
        """更新圖表選擇數據

        Args:
            chart_id: 圖表ID
            selected_data: 選擇的數據
        """
        self.selected_data[chart_id] = selected_data

        # 觸發聯動圖表更新
        if chart_id in self.chart_links:
            for target_chart in self.chart_links[chart_id]:
                if target_chart in self.chart_registry:
                    callback = self.chart_registry[target_chart].get("update_callback")
                    if callback:
                        callback(selected_data)


# 全域圖表管理器
chart_manager = InteractiveChartManager()


def create_enhanced_candlestick_chart(
    data: pd.DataFrame,
    chart_id: str = "candlestick_main",
    title: str = "股價走勢圖",
    height: int = 600,
    show_volume: bool = True,
    show_indicators: bool = True,
) -> go.Figure:
    """創建增強的K線圖

    Args:
        data: 包含 OHLCV 數據的 DataFrame
        chart_id: 圖表ID
        title: 圖表標題
        height: 圖表高度
        show_volume: 是否顯示成交量
        show_indicators: 是否顯示技術指標

    Returns:
        Plotly 圖表對象
    """
    theme = ChartTheme.get_theme(st.session_state.chart_config["theme"])

    # 創建子圖
    rows = 1
    if show_volume:
        rows += 1
    if show_indicators:
        rows += 1

    subplot_titles = [title]
    if show_volume:
        subplot_titles.append("成交量")
    if show_indicators:
        subplot_titles.append("技術指標")

    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=subplot_titles,
        row_heights=(
            [0.6, 0.2, 0.2] if rows == 3 else [0.7, 0.3] if rows == 2 else [1.0]
        ),
    )

    # K線圖
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data["open"],
            high=data["high"],
            low=data["low"],
            close=data["close"],
            name="K線",
            increasing_line_color=theme["success"],
            decreasing_line_color=theme["danger"],
        ),
        row=1,
        col=1,
    )

    # 移動平均線
    if len(data) >= 20:
        ma20 = data["close"].rolling(window=20).mean()
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=ma20,
                mode="lines",
                name="MA20",
                line=dict(color=theme["primary"], width=1),
            ),
            row=1,
            col=1,
        )

    if len(data) >= 60:
        ma60 = data["close"].rolling(window=60).mean()
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=ma60,
                mode="lines",
                name="MA60",
                line=dict(color=theme["secondary"], width=1),
            ),
            row=1,
            col=1,
        )

    # 成交量圖
    if show_volume and "volume" in data.columns:
        colors = [
            theme["success"] if close >= open else theme["danger"]
            for close, open in zip(data["close"], data["open"])
        ]

        fig.add_trace(
            go.Bar(
                x=data.index,
                y=data["volume"],
                name="成交量",
                marker_color=colors,
                opacity=0.7,
            ),
            row=2 if show_volume else 1,
            col=1,
        )

    # 技術指標 (RSI)
    if show_indicators and len(data) >= 14:
        rsi = calculate_rsi(data["close"], window=14)
        indicator_row = 3 if show_volume else 2

        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=rsi,
                mode="lines",
                name="RSI",
                line=dict(color=theme["warning"], width=2),
            ),
            row=indicator_row,
            col=1,
        )

        # RSI 超買超賣線
        fig.add_hline(
            y=70,
            line_dash="dash",
            line_color=theme["danger"],
            opacity=0.5,
            row=indicator_row,
            col=1,
        )
        fig.add_hline(
            y=30,
            line_dash="dash",
            line_color=theme["success"],
            opacity=0.5,
            row=indicator_row,
            col=1,
        )

    # 更新佈局
    fig.update_layout(
        height=height,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        plot_bgcolor=theme["background"],
        paper_bgcolor=theme["background"],
        font_color=theme["text"],
        hovermode="x unified",
        dragmode="zoom" if st.session_state.chart_config["enable_zoom"] else "pan",
    )

    # 更新軸
    fig.update_xaxes(gridcolor=theme["grid"], showgrid=True, zeroline=False)

    fig.update_yaxes(gridcolor=theme["grid"], showgrid=True, zeroline=False)

    # 註冊圖表
    chart_manager.register_chart(chart_id, "candlestick", "stock_data")

    return fig


def calculate_rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    """計算 RSI 指標

    Args:
        prices: 價格序列
        window: 計算窗口

    Returns:
        RSI 值序列
    """
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()

    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return rsi


def create_correlation_heatmap(
    data: pd.DataFrame,
    chart_id: str = "correlation_heatmap",
    title: str = "相關性熱力圖",
) -> go.Figure:
    """創建相關性熱力圖

    Args:
        data: 數據 DataFrame
        chart_id: 圖表ID
        title: 圖表標題

    Returns:
        Plotly 圖表對象
    """
    theme = ChartTheme.get_theme(st.session_state.chart_config["theme"])

    # 計算相關性矩陣
    corr_matrix = data.corr()

    # 創建熱力圖
    fig = go.Figure(
        data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.columns,
            colorscale="RdBu",
            zmid=0,
            text=np.round(corr_matrix.values, 2),
            texttemplate="%{text}",
            textfont={"size": 10},
            hoverongaps=False,
        )
    )

    fig.update_layout(
        title=title,
        plot_bgcolor=theme["background"],
        paper_bgcolor=theme["background"],
        font_color=theme["text"],
        height=500,
    )

    # 註冊圖表
    chart_manager.register_chart(chart_id, "heatmap", "correlation_data")

    return fig


def create_performance_comparison_chart(
    data: Dict[str, pd.Series],
    chart_id: str = "performance_comparison",
    title: str = "績效比較圖",
) -> go.Figure:
    """創建績效比較圖

    Args:
        data: 包含多個資產績效數據的字典
        chart_id: 圖表ID
        title: 圖表標題

    Returns:
        Plotly 圖表對象
    """
    theme = ChartTheme.get_theme(st.session_state.chart_config["theme"])

    fig = go.Figure()

    colors = [
        theme["primary"],
        theme["secondary"],
        theme["success"],
        theme["danger"],
        theme["warning"],
    ]

    for i, (name, series) in enumerate(data.items()):
        # 計算累積報酬率
        cumulative_returns = (1 + series.pct_change()).cumprod() - 1

        fig.add_trace(
            go.Scatter(
                x=series.index,
                y=cumulative_returns * 100,
                mode="lines",
                name=name,
                line=dict(color=colors[i % len(colors)], width=2),
                hovertemplate=f"<b>{name}</b><br>"
                + "日期: %{x}<br>"
                + "累積報酬: %{y:.2f}%<extra></extra>",
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="日期",
        yaxis_title="累積報酬率 (%)",
        plot_bgcolor=theme["background"],
        paper_bgcolor=theme["background"],
        font_color=theme["text"],
        hovermode="x unified",
        height=400,
    )

    fig.update_xaxes(gridcolor=theme["grid"], showgrid=True)
    fig.update_yaxes(gridcolor=theme["grid"], showgrid=True)

    # 註冊圖表
    chart_manager.register_chart(chart_id, "line", "performance_data")

    return fig


def create_volume_profile_chart(
    data: pd.DataFrame, chart_id: str = "volume_profile", title: str = "成交量分佈圖"
) -> go.Figure:
    """創建成交量分佈圖

    Args:
        data: 包含價格和成交量的 DataFrame
        chart_id: 圖表ID
        title: 圖表標題

    Returns:
        Plotly 圖表對象
    """
    theme = ChartTheme.get_theme(st.session_state.chart_config["theme"])

    # 計算價格區間的成交量分佈
    price_min = data["low"].min()
    price_max = data["high"].max()
    price_bins = np.linspace(price_min, price_max, 50)

    volume_profile = []
    for i in range(len(price_bins) - 1):
        bin_low = price_bins[i]
        bin_high = price_bins[i + 1]

        # 找出在此價格區間內的成交量
        mask = (data["low"] <= bin_high) & (data["high"] >= bin_low)
        volume_in_bin = data.loc[mask, "volume"].sum()

        volume_profile.append(
            {"price": (bin_low + bin_high) / 2, "volume": volume_in_bin}
        )

    profile_df = pd.DataFrame(volume_profile)

    # 創建水平柱狀圖
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=profile_df["volume"],
            y=profile_df["price"],
            orientation="h",
            name="成交量分佈",
            marker_color=theme["primary"],
            opacity=0.7,
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="成交量",
        yaxis_title="價格",
        plot_bgcolor=theme["background"],
        paper_bgcolor=theme["background"],
        font_color=theme["text"],
        height=500,
    )

    fig.update_xaxes(gridcolor=theme["grid"], showgrid=True)
    fig.update_yaxes(gridcolor=theme["grid"], showgrid=True)

    # 註冊圖表
    chart_manager.register_chart(chart_id, "bar", "volume_data")

    return fig


def create_chart_controls() -> Dict[str, Any]:
    """創建圖表控制面板

    Returns:
        控制選項字典
    """
    st.sidebar.subheader("📊 圖表設定")

    # 主題選擇
    theme = st.sidebar.selectbox(
        "主題",
        options=list(ChartTheme.THEMES.keys()),
        index=list(ChartTheme.THEMES.keys()).index(
            st.session_state.chart_config["theme"]
        ),
        format_func=lambda x: {
            "light": "淺色主題",
            "dark": "深色主題",
            "professional": "專業主題",
        }[x],
    )

    # 互動選項
    show_crossfilter = st.sidebar.checkbox(
        "啟用十字線", value=st.session_state.chart_config["show_crossfilter"]
    )

    enable_zoom = st.sidebar.checkbox(
        "啟用縮放", value=st.session_state.chart_config["enable_zoom"]
    )

    show_toolbar = st.sidebar.checkbox(
        "顯示工具列", value=st.session_state.chart_config["show_toolbar"]
    )

    # 動畫設定
    animation_duration = st.sidebar.slider(
        "動畫持續時間 (ms)",
        min_value=0,
        max_value=2000,
        value=st.session_state.chart_config["animation_duration"],
        step=100,
    )

    # 更新配置
    config = {
        "theme": theme,
        "show_crossfilter": show_crossfilter,
        "enable_zoom": enable_zoom,
        "show_toolbar": show_toolbar,
        "animation_duration": animation_duration,
    }

    # 檢查是否有變更
    if config != st.session_state.chart_config:
        st.session_state.chart_config = config
        st.rerun()

    return config


def create_chart_selector() -> Dict[str, bool]:
    """創建圖表選擇器

    Returns:
        圖表顯示選項字典
    """
    st.sidebar.subheader("📈 圖表選擇")

    chart_options = {
        "candlestick": st.sidebar.checkbox("K線圖", value=True),
        "volume": st.sidebar.checkbox("成交量圖", value=True),
        "indicators": st.sidebar.checkbox("技術指標", value=True),
        "correlation": st.sidebar.checkbox("相關性熱力圖", value=False),
        "performance": st.sidebar.checkbox("績效比較", value=False),
        "volume_profile": st.sidebar.checkbox("成交量分佈", value=False),
    }

    return chart_options


def generate_sample_stock_data(
    symbol: str = "2330.TW", days: int = 252, start_price: float = 580.0
) -> pd.DataFrame:
    """生成模擬股價數據

    Args:
        symbol: 股票代碼
        days: 天數
        start_price: 起始價格

    Returns:
        包含 OHLCV 數據的 DataFrame
    """
    np.random.seed(42)

    # 生成日期範圍
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days - 1)
    dates = pd.date_range(start=start_date, end=end_date, freq="D")

    # 生成價格數據（隨機遊走）
    returns = np.random.normal(0.001, 0.02, len(dates))  # 平均0.1%日報酬，2%波動率

    prices = [start_price]
    for ret in returns[1:]:
        prices.append(prices[-1] * (1 + ret))

    # 生成 OHLC 數據
    data = []
    for i, (date, close) in enumerate(zip(dates, prices)):
        if i == 0:
            open_price = close
        else:
            open_price = prices[i - 1]

        # 生成高低價
        daily_range = abs(np.random.normal(0, 0.01)) * close
        high = max(open_price, close) + daily_range * np.random.uniform(0, 1)
        low = min(open_price, close) - daily_range * np.random.uniform(0, 1)

        # 生成成交量
        volume = int(np.random.lognormal(15, 0.5))  # 對數正態分佈

        data.append(
            {
                "date": date,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
        )

    df = pd.DataFrame(data)
    df.set_index("date", inplace=True)

    return df


def create_linked_charts_demo():
    """創建圖表聯動演示"""
    st.subheader("📊 互動式圖表聯動演示")

    # 生成示例數據
    symbols = ["2330.TW", "2317.TW", "2454.TW"]
    stock_data = {}

    for symbol in symbols:
        stock_data[symbol] = generate_sample_stock_data(
            symbol=symbol, days=180, start_price=np.random.uniform(100, 600)
        )

    # 創建圖表控制
    col1, col2 = st.columns([1, 3])

    with col1:
        config = create_chart_controls()
        chart_options = create_chart_selector()

        # 股票選擇
        selected_symbol = st.selectbox("選擇股票", options=symbols, index=0)

    with col2:
        # 主要K線圖
        if chart_options["candlestick"]:
            st.subheader(f"📈 {selected_symbol} K線圖")

            main_data = stock_data[selected_symbol]
            candlestick_fig = create_enhanced_candlestick_chart(
                data=main_data,
                chart_id="main_candlestick",
                title=f"{selected_symbol} 股價走勢",
                show_volume=chart_options["volume"],
                show_indicators=chart_options["indicators"],
            )

            # 顯示圖表
            st.plotly_chart(
                candlestick_fig,
                use_container_width=True,
                config={
                    "displayModeBar": config["show_toolbar"],
                    "displaylogo": False,
                    "modeBarButtonsToRemove": ["pan2d", "lasso2d"],
                },
            )

        # 相關性熱力圖
        if chart_options["correlation"]:
            st.subheader("🔥 股票相關性分析")

            # 準備相關性數據
            price_data = pd.DataFrame(
                {symbol: data["close"] for symbol, data in stock_data.items()}
            )

            correlation_fig = create_correlation_heatmap(
                data=price_data, chart_id="correlation_main", title="股票價格相關性"
            )

            st.plotly_chart(correlation_fig, use_container_width=True)

        # 績效比較圖
        if chart_options["performance"]:
            st.subheader("📊 績效比較分析")

            performance_data = {
                symbol: data["close"] for symbol, data in stock_data.items()
            }

            performance_fig = create_performance_comparison_chart(
                data=performance_data, chart_id="performance_main", title="股票績效比較"
            )

            st.plotly_chart(performance_fig, use_container_width=True)

        # 成交量分佈圖
        if chart_options["volume_profile"]:
            st.subheader("📊 成交量分佈分析")

            volume_fig = create_volume_profile_chart(
                data=stock_data[selected_symbol],
                chart_id="volume_profile_main",
                title=f"{selected_symbol} 成交量分佈",
            )

            st.plotly_chart(volume_fig, use_container_width=True)


def create_advanced_technical_indicators(data: pd.DataFrame) -> Dict[str, pd.Series]:
    """創建進階技術指標

    Args:
        data: 股價數據

    Returns:
        技術指標字典
    """
    indicators = {}

    # MACD
    exp1 = data["close"].ewm(span=12).mean()
    exp2 = data["close"].ewm(span=26).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9).mean()
    histogram = macd - signal

    indicators["macd"] = macd
    indicators["macd_signal"] = signal
    indicators["macd_histogram"] = histogram

    # 布林通道
    sma20 = data["close"].rolling(window=20).mean()
    std20 = data["close"].rolling(window=20).std()

    indicators["bb_upper"] = sma20 + (std20 * 2)
    indicators["bb_middle"] = sma20
    indicators["bb_lower"] = sma20 - (std20 * 2)

    # KD指標
    low_min = data["low"].rolling(window=9).min()
    high_max = data["high"].rolling(window=9).max()

    rsv = (data["close"] - low_min) / (high_max - low_min) * 100
    indicators["k"] = rsv.ewm(com=2).mean()
    indicators["d"] = indicators["k"].ewm(com=2).mean()

    return indicators


def create_multi_timeframe_chart(
    data: pd.DataFrame, timeframes: List[str] = ["1D", "1W", "1M"]
) -> go.Figure:
    """創建多時間框架圖表

    Args:
        data: 原始數據
        timeframes: 時間框架列表

    Returns:
        多時間框架圖表
    """
    theme = ChartTheme.get_theme(st.session_state.chart_config["theme"])

    fig = make_subplots(
        rows=len(timeframes),
        cols=1,
        shared_xaxes=True,
        subplot_titles=[f"{tf} 時間框架" for tf in timeframes],
        vertical_spacing=0.05,
    )

    for i, tf in enumerate(timeframes):
        # 重新採樣數據
        if tf == "1D":
            resampled = data
        elif tf == "1W":
            resampled = (
                data.resample("W")
                .agg(
                    {
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "volume": "sum",
                    }
                )
                .dropna()
            )
        elif tf == "1M":
            resampled = (
                data.resample("M")
                .agg(
                    {
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "volume": "sum",
                    }
                )
                .dropna()
            )

        # 添加K線圖
        fig.add_trace(
            go.Candlestick(
                x=resampled.index,
                open=resampled["open"],
                high=resampled["high"],
                low=resampled["low"],
                close=resampled["close"],
                name=f"K線 {tf}",
                increasing_line_color=theme["success"],
                decreasing_line_color=theme["danger"],
            ),
            row=i + 1,
            col=1,
        )

    fig.update_layout(
        height=800,
        showlegend=False,
        plot_bgcolor=theme["background"],
        paper_bgcolor=theme["background"],
        font_color=theme["text"],
    )

    return fig
