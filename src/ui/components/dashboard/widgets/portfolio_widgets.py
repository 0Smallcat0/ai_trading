"""
投資組合相關小工具

提供投資組合摘要、資產配置、績效圖表等小工具。
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging

from .base_widget import BaseWidget, WidgetSize

logger = logging.getLogger(__name__)


class PortfolioSummaryWidget(BaseWidget):
    """投資組合摘要小工具"""

    def get_widget_type(self) -> str:
        return "portfolio_summary"

    def get_default_title(self) -> str:
        return "投資組合摘要"

    def get_default_size(self) -> Dict[str, int]:
        return WidgetSize.LARGE

    def render_content(self) -> None:
        """渲染投資組合摘要內容"""
        # 生成模擬投資組合數據
        portfolio_data = self._generate_portfolio_data()

        # 顯示主要指標
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "總價值",
                f"${portfolio_data['total_value']:,.0f}",
                delta=f"{portfolio_data['total_change']:+,.0f}",
            )

        with col2:
            st.metric(
                "當日損益",
                f"${portfolio_data['daily_pnl']:,.0f}",
                delta=f"{portfolio_data['daily_pnl_pct']:+.2f}%",
            )

        with col3:
            st.metric("總報酬率", f"{portfolio_data['total_return']:+.2f}%")

        with col4:
            st.metric("持股數量", f"{portfolio_data['holdings_count']} 檔")

        # 顯示持股明細
        if self.config.get("show_holdings", True):
            st.subheader("主要持股")
            holdings_df = pd.DataFrame(portfolio_data["holdings"])
            st.dataframe(holdings_df, use_container_width=True)

    def _generate_portfolio_data(self) -> Dict[str, Any]:
        """生成模擬投資組合數據"""
        np.random.seed(42)

        # 基本數據
        total_value = np.random.uniform(800000, 1200000)
        daily_pnl = np.random.uniform(-20000, 20000)
        daily_pnl_pct = (daily_pnl / total_value) * 100
        total_return = np.random.uniform(-10, 25)

        # 持股明細
        holdings = [
            {
                "股票代碼": "2330.TW",
                "股票名稱": "台積電",
                "持股": 1000,
                "市值": 580000,
                "損益": 15000,
            },
            {"股票代碼": "2317.TW", "股票名稱": "鴻海", "市值": 125000, "損益": -2500},
            {"股票代碼": "2454.TW", "股票名稱": "聯發科", "市值": 178000, "損益": 8900},
            {"股票代碼": "2412.TW", "股票名稱": "中華電", "市值": 95000, "損益": 1200},
        ]

        return {
            "total_value": total_value,
            "total_change": daily_pnl,
            "daily_pnl": daily_pnl,
            "daily_pnl_pct": daily_pnl_pct,
            "total_return": total_return,
            "holdings_count": len(holdings),
            "holdings": holdings,
        }

    def render_widget_settings(self) -> None:
        """渲染投資組合摘要特定設定"""
        # 顯示持股明細選項
        show_holdings = st.checkbox(
            "顯示持股明細",
            value=self.config.get("show_holdings", True),
            key=f"{self.widget_id}_holdings",
        )
        self.config["show_holdings"] = show_holdings


class AllocationPieWidget(BaseWidget):
    """資產配置圓餅圖小工具"""

    def get_widget_type(self) -> str:
        return "allocation_pie"

    def get_default_title(self) -> str:
        return "資產配置"

    def get_default_size(self) -> Dict[str, int]:
        return WidgetSize.MEDIUM

    def render_content(self) -> None:
        """渲染資產配置圓餅圖內容"""
        allocation_type = self.config.get("allocation_type", "sector")

        # 生成配置數據
        if allocation_type == "sector":
            data = self._generate_sector_allocation()
            title = "行業配置"
        elif allocation_type == "asset_class":
            data = self._generate_asset_class_allocation()
            title = "資產類別配置"
        else:
            data = self._generate_stock_allocation()
            title = "個股配置"

        # 創建圓餅圖
        fig = px.pie(
            values=list(data.values()),
            names=list(data.keys()),
            title=title,
            color_discrete_sequence=px.colors.qualitative.Set3,
        )

        fig.update_layout(
            height=300,
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            margin=dict(l=0, r=0, t=30, b=0),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False, "displaylogo": False},
        )

    def _generate_sector_allocation(self) -> Dict[str, float]:
        """生成行業配置數據"""
        return {"科技": 45.2, "金融": 18.7, "傳產": 15.3, "生技": 12.1, "其他": 8.7}

    def _generate_asset_class_allocation(self) -> Dict[str, float]:
        """生成資產類別配置數據"""
        return {"股票": 70.0, "債券": 20.0, "現金": 8.0, "其他": 2.0}

    def _generate_stock_allocation(self) -> Dict[str, float]:
        """生成個股配置數據"""
        return {
            "台積電": 35.2,
            "鴻海": 12.8,
            "聯發科": 15.6,
            "中華電": 8.9,
            "其他": 27.5,
        }

    def render_widget_settings(self) -> None:
        """渲染資產配置特定設定"""
        # 配置類型選擇
        allocation_options = {
            "sector": "行業配置",
            "asset_class": "資產類別",
            "stock": "個股配置",
        }

        current_type = self.config.get("allocation_type", "sector")

        new_type = st.selectbox(
            "配置類型",
            list(allocation_options.keys()),
            format_func=lambda x: allocation_options[x],
            index=list(allocation_options.keys()).index(current_type),
            key=f"{self.widget_id}_allocation_type",
        )

        if new_type != current_type:
            self.config["allocation_type"] = new_type


class PerformanceChartWidget(BaseWidget):
    """績效圖表小工具"""

    def get_widget_type(self) -> str:
        return "performance_chart"

    def get_default_title(self) -> str:
        return "績效表現"

    def get_default_size(self) -> Dict[str, int]:
        return WidgetSize.LARGE

    def render_content(self) -> None:
        """渲染績效圖表內容"""
        period = self.config.get("period", "1M")
        chart_type = self.config.get("chart_type", "cumulative")

        # 生成績效數據
        data = self._generate_performance_data(period)

        # 創建圖表
        if chart_type == "cumulative":
            fig = self._create_cumulative_chart(data)
        else:
            fig = self._create_comparison_chart(data)

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False, "displaylogo": False},
        )

        # 顯示績效統計
        self._show_performance_stats(data)

    def _generate_performance_data(self, period: str) -> pd.DataFrame:
        """生成績效數據"""
        # 確定時間範圍
        days_map = {"1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365}
        days = days_map.get(period, 30)

        # 生成日期範圍
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days - 1)
        dates = pd.date_range(start=start_date, end=end_date, freq="D")

        # 生成績效數據
        np.random.seed(42)

        # 投資組合報酬
        portfolio_returns = np.random.normal(0.001, 0.015, len(dates))
        portfolio_cumulative = (1 + pd.Series(portfolio_returns)).cumprod() - 1

        # 基準報酬（大盤）
        benchmark_returns = np.random.normal(0.0008, 0.012, len(dates))
        benchmark_cumulative = (1 + pd.Series(benchmark_returns)).cumprod() - 1

        return pd.DataFrame(
            {
                "date": dates,
                "portfolio": portfolio_cumulative * 100,
                "benchmark": benchmark_cumulative * 100,
                "portfolio_daily": pd.Series(portfolio_returns) * 100,
                "benchmark_daily": pd.Series(benchmark_returns) * 100,
            }
        )

    def _create_cumulative_chart(self, data: pd.DataFrame) -> go.Figure:
        """創建累積報酬圖表"""
        fig = go.Figure()

        # 投資組合線
        fig.add_trace(
            go.Scatter(
                x=data["date"],
                y=data["portfolio"],
                mode="lines",
                name="投資組合",
                line=dict(color=self.theme["primary"], width=2),
            )
        )

        # 基準線
        fig.add_trace(
            go.Scatter(
                x=data["date"],
                y=data["benchmark"],
                mode="lines",
                name="大盤指數",
                line=dict(color=self.theme["secondary"], width=2, dash="dash"),
            )
        )

        fig.update_layout(
            height=300,
            xaxis_title="日期",
            yaxis_title="累積報酬率 (%)",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
        )

        return fig

    def _create_comparison_chart(self, data: pd.DataFrame) -> go.Figure:
        """創建比較圖表"""
        # 計算超額報酬
        excess_return = data["portfolio"] - data["benchmark"]

        fig = go.Figure()

        # 超額報酬柱狀圖
        colors = [
            self.theme["success"] if x >= 0 else self.theme["danger"]
            for x in excess_return
        ]

        fig.add_trace(
            go.Bar(
                x=data["date"],
                y=excess_return,
                name="超額報酬",
                marker_color=colors,
                opacity=0.7,
            )
        )

        fig.update_layout(
            height=300,
            xaxis_title="日期",
            yaxis_title="超額報酬率 (%)",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            margin=dict(l=0, r=0, t=0, b=0),
        )

        return fig

    def _show_performance_stats(self, data: pd.DataFrame) -> None:
        """顯示績效統計"""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            portfolio_return = data["portfolio"].iloc[-1]
            st.metric("總報酬", f"{portfolio_return:.2f}%")

        with col2:
            benchmark_return = data["benchmark"].iloc[-1]
            st.metric("基準報酬", f"{benchmark_return:.2f}%")

        with col3:
            excess_return = portfolio_return - benchmark_return
            st.metric("超額報酬", f"{excess_return:+.2f}%")

        with col4:
            volatility = data["portfolio_daily"].std() * np.sqrt(252)
            st.metric("年化波動", f"{volatility:.2f}%")

    def render_widget_settings(self) -> None:
        """渲染績效圖表特定設定"""
        # 時間週期選擇
        period_options = ["1W", "1M", "3M", "6M", "1Y"]
        current_period = self.config.get("period", "1M")

        new_period = st.selectbox(
            "時間週期",
            period_options,
            index=period_options.index(current_period),
            key=f"{self.widget_id}_period",
        )

        if new_period != current_period:
            self.config["period"] = new_period

        # 圖表類型選擇
        chart_options = {"cumulative": "累積報酬", "comparison": "超額報酬"}

        current_chart = self.config.get("chart_type", "cumulative")

        new_chart = st.selectbox(
            "圖表類型",
            list(chart_options.keys()),
            format_func=lambda x: chart_options[x],
            index=list(chart_options.keys()).index(current_chart),
            key=f"{self.widget_id}_chart_type",
        )

        if new_chart != current_chart:
            self.config["chart_type"] = new_chart
