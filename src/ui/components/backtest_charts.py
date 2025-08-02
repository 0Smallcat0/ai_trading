"""
回測圖表組件

此模組提供回測系統的各種圖表組件，包括：
- 累積收益率曲線
- 回撤分析圖
- 滾動夏普比率
- 月度收益熱力圖
- 收益分佈直方圖
- 風險收益散點圖
- 交易頻率分析
- 持倉時間分析
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import calendar

# 導入響應式設計組件
from ..responsive import ResponsiveComponents, responsive_manager


class BacktestCharts:
    """回測圖表組件類"""

    @staticmethod
    def cumulative_returns_chart(
        portfolio_data: pd.DataFrame,
        benchmark_data: Optional[pd.DataFrame] = None,
        title: str = "累積收益率曲線",
    ) -> go.Figure:
        """
        繪製累積收益率曲線圖

        Args:
            portfolio_data: 投資組合數據，包含 date 和 cumulative_return 欄位
            benchmark_data: 基準數據（可選）
            title: 圖表標題

        Returns:
            Plotly 圖表物件
        """
        fig = go.Figure()

        # 添加投資組合收益率曲線
        fig.add_trace(
            go.Scatter(
                x=portfolio_data["date"],
                y=portfolio_data["cumulative_return"] * 100,
                mode="lines",
                name="投資組合",
                line=dict(color="#1f77b4", width=2),
                hovertemplate="日期: %{x}<br>累積收益率: %{y:.2f}%<extra></extra>",
            )
        )

        # 添加基準線（如果提供）
        if benchmark_data is not None:
            fig.add_trace(
                go.Scatter(
                    x=benchmark_data["date"],
                    y=benchmark_data["cumulative_return"] * 100,
                    mode="lines",
                    name="基準",
                    line=dict(color="#ff7f0e", width=2, dash="dash"),
                    hovertemplate="日期: %{x}<br>基準收益率: %{y:.2f}%<extra></extra>",
                )
            )

        # 添加零線
        fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)

        # 設定圖表佈局
        height = responsive_manager.get_chart_height(400)
        fig.update_layout(
            title=title,
            xaxis_title="日期",
            yaxis_title="累積收益率 (%)",
            height=height,
            hovermode="x unified",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )

        return fig

    @staticmethod
    def drawdown_chart(
        portfolio_data: pd.DataFrame, title: str = "回撤分析圖"
    ) -> go.Figure:
        """
        繪製回撤分析圖

        Args:
            portfolio_data: 投資組合數據，包含 date 和 drawdown 欄位
            title: 圖表標題

        Returns:
            Plotly 圖表物件
        """
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=("投資組合價值", "回撤"),
            row_heights=[0.7, 0.3],
        )

        # 上圖：投資組合價值
        fig.add_trace(
            go.Scatter(
                x=portfolio_data["date"],
                y=portfolio_data["portfolio_value"],
                mode="lines",
                name="投資組合價值",
                line=dict(color="#1f77b4", width=2),
                hovertemplate="日期: %{x}<br>價值: %{y:,.0f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

        # 下圖：回撤
        fig.add_trace(
            go.Scatter(
                x=portfolio_data["date"],
                y=portfolio_data["drawdown"] * 100,
                mode="lines",
                fill="tonexty",
                name="回撤",
                line=dict(color="#d62728", width=1),
                fillcolor="rgba(214, 39, 40, 0.3)",
                hovertemplate="日期: %{x}<br>回撤: %{y:.2f}%<extra></extra>",
            ),
            row=2,
            col=1,
        )

        # 添加最大回撤標記
        max_drawdown_idx = portfolio_data["drawdown"].idxmin()
        max_drawdown_date = portfolio_data.loc[max_drawdown_idx, "date"]
        max_drawdown_value = portfolio_data.loc[max_drawdown_idx, "drawdown"] * 100

        fig.add_annotation(
            x=max_drawdown_date,
            y=max_drawdown_value,
            text=f"最大回撤: {max_drawdown_value:.2f}%",
            showarrow=True,
            arrowhead=2,
            arrowcolor="red",
            row=2,
            col=1,
        )

        # 設定圖表佈局
        height = responsive_manager.get_chart_height(500)
        fig.update_layout(
            title=title, height=height, hovermode="x unified", showlegend=False
        )

        fig.update_xaxes(title_text="日期", row=2, col=1)
        fig.update_yaxes(title_text="投資組合價值", row=1, col=1)
        fig.update_yaxes(title_text="回撤 (%)", row=2, col=1)

        return fig

    @staticmethod
    def rolling_sharpe_chart(
        portfolio_data: pd.DataFrame, window: int = 252, title: str = "滾動夏普比率"
    ) -> go.Figure:
        """
        繪製滾動夏普比率圖

        Args:
            portfolio_data: 投資組合數據，包含 date 和 daily_return 欄位
            window: 滾動視窗大小（天數）
            title: 圖表標題

        Returns:
            Plotly 圖表物件
        """
        # 計算滾動夏普比率
        returns = portfolio_data["daily_return"]
        rolling_mean = returns.rolling(window=window).mean()
        rolling_std = returns.rolling(window=window).std()
        rolling_sharpe = (rolling_mean / rolling_std) * np.sqrt(252)  # 年化

        fig = go.Figure()

        # 添加滾動夏普比率曲線
        fig.add_trace(
            go.Scatter(
                x=portfolio_data["date"][window - 1 :],
                y=rolling_sharpe[window - 1 :],
                mode="lines",
                name=f"{window}日滾動夏普比率",
                line=dict(color="#2ca02c", width=2),
                hovertemplate="日期: %{x}<br>夏普比率: %{y:.3f}<extra></extra>",
            )
        )

        # 添加參考線
        fig.add_hline(
            y=1.0,
            line_dash="dash",
            line_color="orange",
            annotation_text="良好水準 (1.0)",
        )
        fig.add_hline(
            y=2.0,
            line_dash="dash",
            line_color="green",
            annotation_text="優秀水準 (2.0)",
        )

        # 設定圖表佈局
        height = responsive_manager.get_chart_height(400)
        fig.update_layout(
            title=title,
            xaxis_title="日期",
            yaxis_title="夏普比率",
            height=height,
            hovermode="x unified",
        )

        return fig

    @staticmethod
    def monthly_returns_heatmap(
        portfolio_data: pd.DataFrame, title: str = "月度收益熱力圖"
    ) -> go.Figure:
        """
        繪製月度收益熱力圖

        Args:
            portfolio_data: 投資組合數據，包含 date 和 daily_return 欄位
            title: 圖表標題

        Returns:
            Plotly 圖表物件
        """
        # 準備數據
        df = portfolio_data.copy()
        df["date"] = pd.to_datetime(df["date"])
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month

        # 計算月度收益率
        monthly_returns = (
            df.groupby(["year", "month"])["daily_return"]
            .apply(lambda x: (1 + x).prod() - 1)
            .reset_index()
        )

        # 創建透視表
        pivot_table = (
            monthly_returns.pivot(index="year", columns="month", values="daily_return")
            * 100
        )

        # 月份名稱
        month_names = [calendar.month_abbr[i] for i in range(1, 13)]

        # 創建熱力圖
        fig = go.Figure(
            data=go.Heatmap(
                z=pivot_table.values,
                x=month_names,
                y=pivot_table.index,
                colorscale="RdYlGn",
                zmid=0,
                hovertemplate="年份: %{y}<br>月份: %{x}<br>收益率: %{z:.2f}%<extra></extra>",
                colorbar=dict(title="收益率 (%)"),
            )
        )

        # 設定圖表佈局
        height = responsive_manager.get_chart_height(400)
        fig.update_layout(
            title=title, xaxis_title="月份", yaxis_title="年份", height=height
        )

        return fig

    @staticmethod
    def returns_distribution_chart(
        portfolio_data: pd.DataFrame, title: str = "收益分佈直方圖"
    ) -> go.Figure:
        """
        繪製收益分佈直方圖

        Args:
            portfolio_data: 投資組合數據，包含 daily_return 欄位
            title: 圖表標題

        Returns:
            Plotly 圖表物件
        """
        returns = portfolio_data["daily_return"] * 100

        fig = go.Figure()

        # 添加直方圖
        fig.add_trace(
            go.Histogram(
                x=returns,
                nbinsx=50,
                name="收益分佈",
                opacity=0.7,
                marker_color="skyblue",
                hovertemplate="收益率: %{x:.2f}%<br>頻次: %{y}<extra></extra>",
            )
        )

        # 添加統計線
        mean_return = returns.mean()
        std_return = returns.std()

        fig.add_vline(
            x=mean_return,
            line_dash="dash",
            line_color="red",
            annotation_text=f"平均: {mean_return:.2f}%",
        )
        fig.add_vline(
            x=mean_return + std_return,
            line_dash="dot",
            line_color="orange",
            annotation_text=f"+1σ: {mean_return + std_return:.2f}%",
        )
        fig.add_vline(
            x=mean_return - std_return,
            line_dash="dot",
            line_color="orange",
            annotation_text=f"-1σ: {mean_return - std_return:.2f}%",
        )

        # 設定圖表佈局
        height = responsive_manager.get_chart_height(400)
        fig.update_layout(
            title=title,
            xaxis_title="日收益率 (%)",
            yaxis_title="頻次",
            height=height,
            showlegend=False,
        )

        return fig

    @staticmethod
    def risk_return_scatter(
        strategies_data: List[Dict[str, Any]], title: str = "風險收益散點圖"
    ) -> go.Figure:
        """
        繪製風險收益散點圖

        Args:
            strategies_data: 策略數據列表，每個包含 name, annual_return, volatility
            title: 圖表標題

        Returns:
            Plotly 圖表物件
        """
        fig = go.Figure()

        # 添加散點
        for strategy in strategies_data:
            fig.add_trace(
                go.Scatter(
                    x=[strategy["volatility"] * 100],
                    y=[strategy["annual_return"] * 100],
                    mode="markers+text",
                    name=strategy["name"],
                    text=[strategy["name"]],
                    textposition="top center",
                    marker=dict(size=12, opacity=0.7),
                    hovertemplate=f'策略: {strategy["name"]}<br>'
                    + f"年化收益率: %{{y:.2f}}%<br>"
                    + f"波動率: %{{x:.2f}}%<extra></extra>",
                )
            )

        # 設定圖表佈局
        height = responsive_manager.get_chart_height(400)
        fig.update_layout(
            title=title,
            xaxis_title="波動率 (%)",
            yaxis_title="年化收益率 (%)",
            height=height,
            showlegend=False,
        )

        return fig

    @staticmethod
    def trading_frequency_chart(
        transactions_data: pd.DataFrame, title: str = "交易頻率分析"
    ) -> go.Figure:
        """
        繪製交易頻率分析圖

        Args:
            transactions_data: 交易數據，包含 date 和 action 欄位
            title: 圖表標題

        Returns:
            Plotly 圖表物件
        """
        # 準備數據
        df = transactions_data.copy()
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.to_period("M")

        # 計算月度交易次數
        monthly_trades = (
            df.groupby(["month", "action"]).size().reset_index(name="count")
        )
        monthly_trades["month_str"] = monthly_trades["month"].astype(str)

        fig = go.Figure()

        # 添加買入交易
        buy_data = monthly_trades[monthly_trades["action"] == "buy"]
        fig.add_trace(
            go.Bar(
                x=buy_data["month_str"],
                y=buy_data["count"],
                name="買入",
                marker_color="green",
                hovertemplate="月份: %{x}<br>買入次數: %{y}<extra></extra>",
            )
        )

        # 添加賣出交易
        sell_data = monthly_trades[monthly_trades["action"] == "sell"]
        fig.add_trace(
            go.Bar(
                x=sell_data["month_str"],
                y=sell_data["count"],
                name="賣出",
                marker_color="red",
                hovertemplate="月份: %{x}<br>賣出次數: %{y}<extra></extra>",
            )
        )

        # 設定圖表佈局
        height = responsive_manager.get_chart_height(400)
        fig.update_layout(
            title=title,
            xaxis_title="月份",
            yaxis_title="交易次數",
            height=height,
            barmode="group",
        )

        return fig

    @staticmethod
    def holding_period_chart(
        positions_data: pd.DataFrame, title: str = "持倉時間分析"
    ) -> go.Figure:
        """
        繪製持倉時間分析圖

        Args:
            positions_data: 持倉數據，包含 symbol 和 holding_days 欄位
            title: 圖表標題

        Returns:
            Plotly 圖表物件
        """
        # 計算持倉時間分佈
        holding_days = positions_data["holding_days"]

        # 定義時間區間
        bins = [0, 1, 7, 30, 90, 180, 365, float("inf")]
        labels = ["當日", "1-7天", "1-4週", "1-3月", "3-6月", "6-12月", "超過1年"]

        # 分組統計
        holding_groups = pd.cut(holding_days, bins=bins, labels=labels, right=False)
        group_counts = holding_groups.value_counts().sort_index()

        fig = go.Figure()

        # 添加柱狀圖
        fig.add_trace(
            go.Bar(
                x=group_counts.index,
                y=group_counts.values,
                marker_color="lightblue",
                hovertemplate="持倉期間: %{x}<br>次數: %{y}<extra></extra>",
            )
        )

        # 設定圖表佈局
        height = responsive_manager.get_chart_height(400)
        fig.update_layout(
            title=title,
            xaxis_title="持倉期間",
            yaxis_title="交易次數",
            height=height,
            showlegend=False,
        )

        return fig

    @staticmethod
    def render_performance_charts(
        backtest_results: Dict[str, Any], chart_types: List[str] = None
    ) -> None:
        """
        渲染效能分析圖表

        Args:
            backtest_results: 回測結果數據
            chart_types: 要顯示的圖表類型列表
        """
        if chart_types is None:
            chart_types = [
                "cumulative_returns",
                "drawdown",
                "rolling_sharpe",
                "monthly_heatmap",
                "returns_distribution",
                "trading_frequency",
                "holding_period",
            ]

        # 準備數據
        portfolio_data = pd.DataFrame(backtest_results.get("portfolio_data", []))
        transactions_data = pd.DataFrame(backtest_results.get("transactions", []))
        positions_data = pd.DataFrame(backtest_results.get("positions", []))

        # 使用響應式佈局
        cols = responsive_manager.create_responsive_columns(
            desktop_cols=2, tablet_cols=1, mobile_cols=1
        )

        chart_idx = 0

        # 累積收益率曲線
        if "cumulative_returns" in chart_types and not portfolio_data.empty:
            with cols[chart_idx % len(cols)]:
                fig = BacktestCharts.cumulative_returns_chart(portfolio_data)
                st.plotly_chart(fig, use_container_width=True)
            chart_idx += 1

        # 回撤分析圖
        if "drawdown" in chart_types and not portfolio_data.empty:
            with cols[chart_idx % len(cols)]:
                fig = BacktestCharts.drawdown_chart(portfolio_data)
                st.plotly_chart(fig, use_container_width=True)
            chart_idx += 1

        # 滾動夏普比率
        if "rolling_sharpe" in chart_types and not portfolio_data.empty:
            with cols[chart_idx % len(cols)]:
                fig = BacktestCharts.rolling_sharpe_chart(portfolio_data)
                st.plotly_chart(fig, use_container_width=True)
            chart_idx += 1

        # 月度收益熱力圖
        if "monthly_heatmap" in chart_types and not portfolio_data.empty:
            with cols[chart_idx % len(cols)]:
                fig = BacktestCharts.monthly_returns_heatmap(portfolio_data)
                st.plotly_chart(fig, use_container_width=True)
            chart_idx += 1

        # 收益分佈直方圖
        if "returns_distribution" in chart_types and not portfolio_data.empty:
            with cols[chart_idx % len(cols)]:
                fig = BacktestCharts.returns_distribution_chart(portfolio_data)
                st.plotly_chart(fig, use_container_width=True)
            chart_idx += 1

        # 交易頻率分析
        if "trading_frequency" in chart_types and not transactions_data.empty:
            with cols[chart_idx % len(cols)]:
                fig = BacktestCharts.trading_frequency_chart(transactions_data)
                st.plotly_chart(fig, use_container_width=True)
            chart_idx += 1

        # 持倉時間分析
        if "holding_period" in chart_types and not positions_data.empty:
            with cols[chart_idx % len(cols)]:
                fig = BacktestCharts.holding_period_chart(positions_data)
                st.plotly_chart(fig, use_container_width=True)
            chart_idx += 1
