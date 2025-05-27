"""圖表元件

此模組提供各種圖表元件，用於數據視覺化。
"""

from typing import Optional, Union, List
from dataclasses import dataclass
import logging

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# 條件導入 streamlit
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False
    # 提供模擬的 streamlit 功能

    class MockStreamlit:
        """模擬 Streamlit 功能的類別"""

        @staticmethod
        def plotly_chart(fig, use_container_width=True):
            """模擬 streamlit plotly_chart 功能"""
            del fig, use_container_width  # 避免未使用變數警告

        @staticmethod
        def error(message):
            """模擬 streamlit error 功能"""
            logging.error("Streamlit error: %s", message)

    st = MockStreamlit()


@dataclass
class ChartConfig:
    """圖表配置類"""
    title: str = "圖表"
    height: int = 400
    width: Optional[int] = None
    template: str = "plotly_white"
    show_legend: bool = True
    use_container_width: bool = True


@dataclass
class CandlestickConfig(ChartConfig):
    """K線圖配置類"""
    open_col: str = "開盤價"
    high_col: str = "最高價"
    low_col: str = "最低價"
    close_col: str = "收盤價"
    date_col: str = "日期"
    volume_col: Optional[str] = None
    title: str = "K線圖"
    height: int = 600


def line_chart(
    data: pd.DataFrame,
    x: Optional[str] = None,
    y: Optional[Union[str, List[str]]] = None,
    config: Optional[ChartConfig] = None
) -> go.Figure:
    """繪製折線圖

    Args:
        data: 數據
        x: X軸欄位名稱
        y: Y軸欄位名稱或列表
        config: 圖表配置

    Returns:
        Plotly圖表對象

    Raises:
        ValueError: 當數據為空或格式不正確時
    """
    if config is None:
        config = ChartConfig(title="折線圖")

    try:
        if data.empty:
            raise ValueError("數據不能為空")

        fig = px.line(
            data, x=x, y=y, title=config.title,
            height=config.height, width=config.width
        )
        fig.update_layout(
            xaxis_title=x,
            yaxis_title=y if isinstance(y, str) else "值",
            legend_title="指標",
            template=config.template,
            showlegend=config.show_legend,
        )
        st.plotly_chart(fig, use_container_width=config.use_container_width)
        return fig
    except Exception as e:
        logging.error("折線圖生成失敗: %s", e)
        st.error(f"圖表生成失敗: {e}")
        raise ValueError("折線圖生成失敗") from e


def bar_chart(
    data: pd.DataFrame,
    x: Optional[str] = None,
    y: Optional[Union[str, List[str]]] = None,
    color: Optional[str] = None,
    config: Optional[ChartConfig] = None
) -> go.Figure:
    """繪製柱狀圖

    Args:
        data: 數據
        x: X軸欄位名稱
        y: Y軸欄位名稱或列表
        color: 顏色欄位
        config: 圖表配置

    Returns:
        Plotly圖表對象

    Raises:
        ValueError: 當數據為空或格式不正確時
    """
    if config is None:
        config = ChartConfig(title="柱狀圖")

    try:
        if data.empty:
            raise ValueError("數據不能為空")

        fig = px.bar(
            data, x=x, y=y, title=config.title,
            height=config.height, width=config.width, color=color
        )
        fig.update_layout(
            xaxis_title=x,
            yaxis_title=y if isinstance(y, str) else "值",
            legend_title="類別",
            template=config.template,
            showlegend=config.show_legend,
        )
        st.plotly_chart(fig, use_container_width=config.use_container_width)
        return fig
    except Exception as e:
        logging.error("柱狀圖生成失敗: %s", e)
        st.error(f"圖表生成失敗: {e}")
        raise ValueError("柱狀圖生成失敗") from e


def candlestick_chart(
    data: pd.DataFrame,
    config: Optional[CandlestickConfig] = None
) -> go.Figure:
    """繪製K線圖

    Args:
        data: 數據
        config: K線圖配置

    Returns:
        Plotly圖表對象

    Raises:
        ValueError: 當數據為空或缺少必要欄位時
    """
    if config is None:
        config = CandlestickConfig()
    try:
        if data.empty:
            raise ValueError("數據不能為空")

        # 檢查必要欄位
        required_cols = [
            config.date_col, config.open_col, config.high_col,
            config.low_col, config.close_col
        ]
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"缺少必要欄位: {missing_cols}")

        fig = go.Figure()

        # 添加K線
        fig.add_trace(
            go.Candlestick(
                x=data[config.date_col],
                open=data[config.open_col],
                high=data[config.high_col],
                low=data[config.low_col],
                close=data[config.close_col],
                name="K線",
            )
        )

        # 如果有成交量數據，添加成交量圖
        if config.volume_col and config.volume_col in data.columns:
            fig.add_trace(
                go.Bar(
                    x=data[config.date_col],
                    y=data[config.volume_col],
                    name="成交量",
                    marker_color="rgba(0, 0, 255, 0.3)",
                    opacity=0.3,
                    yaxis="y2",
                )
            )

            # 設置雙Y軸
            fig.update_layout(
                yaxis2={
                    "title": "成交量", "overlaying": "y",
                    "side": "right", "showgrid": False
                }
            )

        # 更新佈局
        fig.update_layout(
            title=config.title,
            xaxis_title="日期",
            yaxis_title="價格",
            height=config.height,
            width=config.width,
            template=config.template,
            showlegend=config.show_legend,
            xaxis_rangeslider_visible=False,
        )

        st.plotly_chart(fig, use_container_width=config.use_container_width)
        return fig
    except Exception as e:
        logging.error("K線圖生成失敗: %s", e)
        st.error(f"圖表生成失敗: {e}")
        raise ValueError("K線圖生成失敗") from e


def pie_chart(
    data: pd.DataFrame,
    names: Optional[str] = None,
    values: Optional[str] = None,
    config: Optional[ChartConfig] = None
) -> go.Figure:
    """繪製圓餅圖

    Args:
        data: 數據
        names: 類別欄位名稱
        values: 數值欄位名稱
        config: 圖表配置

    Returns:
        Plotly圖表對象

    Raises:
        ValueError: 當數據為空或格式不正確時
    """
    if config is None:
        config = ChartConfig(title="圓餅圖")

    try:
        if data.empty:
            raise ValueError("數據不能為空")

        fig = px.pie(
            data, names=names, values=values, title=config.title,
            height=config.height, width=config.width
        )
        fig.update_layout(
            legend_title="類別",
            template=config.template,
            showlegend=config.show_legend
        )
        st.plotly_chart(fig, use_container_width=config.use_container_width)
        return fig
    except Exception as e:
        logging.error("圓餅圖生成失敗: %s", e)
        st.error(f"圖表生成失敗: {e}")
        raise ValueError("圓餅圖生成失敗") from e


def heatmap(
    data: pd.DataFrame,
    config: Optional[ChartConfig] = None
) -> go.Figure:
    """繪製熱力圖

    Args:
        data: 數據
        config: 圖表配置

    Returns:
        Plotly圖表對象

    Raises:
        ValueError: 當數據為空或格式不正確時
    """
    if config is None:
        config = ChartConfig(title="熱力圖")

    try:
        if data.empty:
            raise ValueError("數據不能為空")

        fig = px.imshow(
            data, title=config.title,
            height=config.height, width=config.width
        )
        fig.update_layout(
            template=config.template,
            showlegend=config.show_legend
        )
        st.plotly_chart(fig, use_container_width=config.use_container_width)
        return fig
    except Exception as e:
        logging.error("熱力圖生成失敗: %s", e)
        st.error(f"圖表生成失敗: {e}")
        raise ValueError("熱力圖生成失敗") from e
