"""風險管理圖表組件

此模組提供風險管理相關的圖表組件，包括：
- VaR 分析圖表
- 回撤走勢圖
- 風險分解圖
- 相關性熱圖

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, Any, List, Optional
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta


def var_analysis_chart(
    returns_data: np.ndarray,
    confidence_level: float = 95.0,
    title: str = "VaR 分析圖表",
) -> go.Figure:
    """VaR 分析圖表

    Args:
        returns_data: 收益率數據陣列
        confidence_level: 信心水準 (%)
        title: 圖表標題

    Returns:
        go.Figure: Plotly 圖表物件
    """
    # 計算 VaR
    var_value = np.percentile(returns_data, 100 - confidence_level)

    # 創建直方圖
    fig = go.Figure()

    # 添加收益率分布直方圖
    fig.add_trace(
        go.Histogram(
            x=returns_data * 100,
            nbinsx=50,
            name="收益率分布",
            marker_color="lightblue",
            opacity=0.7,
        )
    )

    # 添加 VaR 線
    fig.add_vline(
        x=var_value * 100,
        line_dash="dash",
        line_color="red",
        line_width=2,
        annotation_text=f"{confidence_level}% VaR: {var_value*100:.2f}%",
    )

    # 添加平均值線
    mean_return = np.mean(returns_data)
    fig.add_vline(
        x=mean_return * 100,
        line_dash="dot",
        line_color="green",
        line_width=2,
        annotation_text=f"平均: {mean_return*100:.2f}%",
    )

    fig.update_layout(
        title=title,
        xaxis_title="收益率 (%)",
        yaxis_title="頻率",
        template="plotly_white",
        height=400,
    )

    return fig


def drawdown_chart(
    dates: List[datetime], drawdown_series: np.ndarray, title: str = "投資組合回撤走勢"
) -> go.Figure:
    """回撤走勢圖

    Args:
        dates: 日期列表
        drawdown_series: 回撤數據陣列
        title: 圖表標題

    Returns:
        go.Figure: Plotly 圖表物件
    """
    fig = go.Figure()

    # 添加回撤線
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=drawdown_series,
            mode="lines",
            name="回撤",
            fill="tonexty",
            line=dict(color="red", width=2),
            fillcolor="rgba(255, 0, 0, 0.1)",
        )
    )

    # 添加零線
    fig.add_hline(y=0, line_dash="dash", line_color="black", line_width=1)

    # 標記最大回撤點
    max_dd_idx = np.argmin(drawdown_series)
    max_dd_value = drawdown_series[max_dd_idx]
    max_dd_date = dates[max_dd_idx]

    fig.add_trace(
        go.Scatter(
            x=[max_dd_date],
            y=[max_dd_value],
            mode="markers",
            name=f"最大回撤: {max_dd_value:.2f}%",
            marker=dict(color="red", size=10, symbol="circle"),
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="日期",
        yaxis_title="回撤 (%)",
        template="plotly_white",
        height=400,
    )

    return fig


def risk_decomposition_pie_chart(
    risk_components: Dict[str, float], title: str = "風險分解"
) -> go.Figure:
    """風險分解餅圖

    Args:
        risk_components: 風險組成字典 {風險類型: 比例}
        title: 圖表標題

    Returns:
        go.Figure: Plotly 圖表物件
    """
    fig = go.Figure(
        data=[
            go.Pie(
                labels=list(risk_components.keys()),
                values=list(risk_components.values()),
                hole=0.3,
                textinfo="label+percent",
                textposition="outside",
            )
        ]
    )

    fig.update_layout(title=title, template="plotly_white", height=400)

    return fig


def correlation_heatmap(
    correlation_matrix: pd.DataFrame, title: str = "資產相關性熱圖"
) -> go.Figure:
    """相關性熱圖

    Args:
        correlation_matrix: 相關性矩陣 DataFrame
        title: 圖表標題

    Returns:
        go.Figure: Plotly 圖表物件
    """
    fig = go.Figure(
        data=go.Heatmap(
            z=correlation_matrix.values,
            x=correlation_matrix.columns,
            y=correlation_matrix.index,
            colorscale="RdBu",
            zmid=0,
            text=correlation_matrix.values,
            texttemplate="%{text:.2f}",
            textfont={"size": 10},
            hoverongaps=False,
        )
    )

    fig.update_layout(title=title, template="plotly_white", height=500)

    return fig


def risk_trend_chart(
    dates: List[datetime],
    risk_metrics: Dict[str, np.ndarray],
    title: str = "風險指標趨勢",
) -> go.Figure:
    """風險指標趨勢圖

    Args:
        dates: 日期列表
        risk_metrics: 風險指標字典 {指標名稱: 數據陣列}
        title: 圖表標題

    Returns:
        go.Figure: Plotly 圖表物件
    """
    fig = go.Figure()

    colors = ["blue", "red", "green", "orange", "purple"]

    for i, (metric_name, metric_data) in enumerate(risk_metrics.items()):
        color = colors[i % len(colors)]

        fig.add_trace(
            go.Scatter(
                x=dates,
                y=metric_data,
                mode="lines+markers",
                name=metric_name,
                line=dict(color=color, width=2),
                marker=dict(size=4),
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="日期",
        yaxis_title="風險值",
        template="plotly_white",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def portfolio_composition_chart(
    holdings: Dict[str, float], title: str = "投資組合組成"
) -> go.Figure:
    """投資組合組成圖

    Args:
        holdings: 持倉字典 {股票代碼: 權重}
        title: 圖表標題

    Returns:
        go.Figure: Plotly 圖表物件
    """
    # 排序並取前10大持倉
    sorted_holdings = dict(
        sorted(holdings.items(), key=lambda x: x[1], reverse=True)[:10]
    )

    fig = go.Figure(
        data=[
            go.Bar(
                x=list(sorted_holdings.keys()),
                y=list(sorted_holdings.values()),
                marker_color="lightblue",
                text=[f"{v:.1f}%" for v in sorted_holdings.values()],
                textposition="outside",
            )
        ]
    )

    fig.update_layout(
        title=title,
        xaxis_title="股票代碼",
        yaxis_title="權重 (%)",
        template="plotly_white",
        height=400,
    )

    return fig


def risk_gauge_chart(risk_score: float, title: str = "風險評分") -> go.Figure:
    """風險評分儀表圖

    Args:
        risk_score: 風險評分 (0-100)
        title: 圖表標題

    Returns:
        go.Figure: Plotly 圖表物件
    """
    # 確定風險等級和顏色
    if risk_score >= 80:
        color = "green"
        level = "低風險"
    elif risk_score >= 60:
        color = "yellow"
        level = "中等風險"
    elif risk_score >= 40:
        color = "orange"
        level = "高風險"
    else:
        color = "red"
        level = "極高風險"

    fig = go.Figure(
        go.Indicator(
            mode="gauge+number+delta",
            value=risk_score,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": title},
            delta={"reference": 70},
            gauge={
                "axis": {"range": [None, 100]},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, 40], "color": "lightgray"},
                    {"range": [40, 60], "color": "gray"},
                    {"range": [60, 80], "color": "lightgreen"},
                    {"range": [80, 100], "color": "green"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 90,
                },
            },
        )
    )

    fig.update_layout(
        height=300,
        annotations=[
            dict(
                text=level,
                x=0.5,
                y=0.1,
                showarrow=False,
                font=dict(size=16, color=color),
            )
        ],
    )

    return fig


def multi_metric_dashboard(metrics: Dict[str, Any], layout: str = "grid") -> None:
    """多指標儀表板

    Args:
        metrics: 指標字典
        layout: 佈局方式 ("grid", "tabs", "accordion")
    """
    if layout == "grid":
        cols = st.columns(len(metrics))
        for i, (metric_name, metric_data) in enumerate(metrics.items()):
            with cols[i]:
                st.metric(
                    metric_name,
                    metric_data.get("value", "N/A"),
                    metric_data.get("delta", None),
                )

    elif layout == "tabs":
        tabs = st.tabs(list(metrics.keys()))
        for i, (metric_name, metric_data) in enumerate(metrics.items()):
            with tabs[i]:
                st.metric(
                    metric_name,
                    metric_data.get("value", "N/A"),
                    metric_data.get("delta", None),
                )
                if "chart" in metric_data:
                    st.plotly_chart(metric_data["chart"], use_container_width=True)

    elif layout == "accordion":
        for metric_name, metric_data in metrics.items():
            with st.expander(metric_name):
                st.metric(
                    metric_name,
                    metric_data.get("value", "N/A"),
                    metric_data.get("delta", None),
                )
                if "chart" in metric_data:
                    st.plotly_chart(metric_data["chart"], use_container_width=True)


def create_sample_data() -> Dict[str, Any]:
    """創建示例數據

    Returns:
        Dict[str, Any]: 示例數據字典
    """
    np.random.seed(42)

    # 生成示例收益率數據
    returns = np.random.normal(0.001, 0.02, 252)
    dates = pd.date_range(end=datetime.now(), periods=252, freq="D")

    # 計算回撤
    cumulative_returns = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative_returns)
    drawdown = (cumulative_returns / running_max - 1) * 100

    # 風險組成
    risk_components = {
        "市場風險": 45,
        "信用風險": 25,
        "流動性風險": 15,
        "操作風險": 10,
        "其他風險": 5,
    }

    # 相關性矩陣
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
    correlation_matrix = pd.DataFrame(
        np.random.uniform(0.3, 0.9, (5, 5)), index=symbols, columns=symbols
    )
    np.fill_diagonal(correlation_matrix.values, 1.0)

    return {
        "returns": returns,
        "dates": dates,
        "drawdown": drawdown,
        "risk_components": risk_components,
        "correlation_matrix": correlation_matrix,
    }
