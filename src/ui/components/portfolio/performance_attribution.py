"""
績效歸因分析組件

提供 Brinson 歸因、多層級歸因、基準比較等績效分析功能。
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta

from src.ui.utils.portfolio_analytics import PortfolioAnalytics

logger = logging.getLogger(__name__)


class PerformanceAttributionComponent:
    """績效歸因分析組件類"""

    def __init__(self):
        """初始化績效歸因組件"""
        self.analytics = PortfolioAnalytics()
        self.theme = self._get_theme()

    def _get_theme(self) -> Dict[str, str]:
        """獲取當前主題配置"""
        if st.session_state.get("theme", "light") == "dark":
            return {
                "background": "#1E1E1E",
                "text": "#FFFFFF",
                "primary": "#00D4FF",
                "secondary": "#FF6B35",
                "success": "#00C851",
                "danger": "#FF4444",
                "warning": "#FFBB33",
            }
        else:
            return {
                "background": "#FFFFFF",
                "text": "#333333",
                "primary": "#1f77b4",
                "secondary": "#ff7f0e",
                "success": "#2ca02c",
                "danger": "#d62728",
                "warning": "#ff7f0e",
            }

    def render_attribution_analysis(self, portfolio_data: Dict[str, Any]) -> None:
        """渲染績效歸因分析

        Args:
            portfolio_data: 投資組合數據
        """
        st.subheader("📊 績效歸因分析")

        # 創建標籤頁
        tab1, tab2, tab3, tab4 = st.tabs(
            ["Brinson 歸因", "多層級歸因", "基準比較", "時間序列分析"]
        )

        with tab1:
            self._render_brinson_attribution()

        with tab2:
            self._render_multilevel_attribution()

        with tab3:
            self._render_benchmark_comparison()

        with tab4:
            self._render_time_series_attribution()

    def render_performance_attribution(self, portfolio_data: Dict[str, Any]) -> None:
        """渲染績效歸因分析 (別名方法，與 render_attribution_analysis 相同)

        Args:
            portfolio_data: 投資組合數據，包含持倉、權重、報酬等信息
        """
        # 調用主要的歸因分析方法
        self.render_attribution_analysis(portfolio_data)

    def _render_brinson_attribution(self) -> None:
        """渲染 Brinson 歸因分析"""
        st.write("### 🎯 Brinson 績效歸因")

        # 參數設定
        col1, col2 = st.columns(2)

        with col1:
            analysis_period = st.selectbox(
                "分析期間", ["1個月", "3個月", "6個月", "1年"], index=2
            )

        with col2:
            sector_count = st.slider("行業數量", 3, 10, 6)

        # 生成模擬數據
        (
            portfolio_weights,
            benchmark_weights,
            portfolio_returns,
            benchmark_returns,
            sector_names,
        ) = self._generate_brinson_data(sector_count)

        # 計算 Brinson 歸因
        attribution_result = self.analytics.brinson_attribution(
            portfolio_weights, benchmark_weights, portfolio_returns, benchmark_returns
        )

        # 顯示歸因結果
        self._display_brinson_results(attribution_result)

        # 繪製歸因分解圖
        self._plot_brinson_attribution(attribution_result, sector_names)

        # 詳細分析表
        self._display_detailed_attribution(
            portfolio_weights,
            benchmark_weights,
            portfolio_returns,
            benchmark_returns,
            sector_names,
        )

    def _display_brinson_results(self, result: Dict[str, float]) -> None:
        """顯示 Brinson 歸因結果"""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "資產配置效應",
                f"{result['allocation_effect']:.2%}",
                help="由於資產配置不同於基準所產生的超額報酬",
            )

        with col2:
            st.metric(
                "選股效應",
                f"{result['selection_effect']:.2%}",
                help="由於個股選擇能力所產生的超額報酬",
            )

        with col3:
            st.metric(
                "交互效應",
                f"{result['interaction_effect']:.2%}",
                help="資產配置與選股效應的交互作用",
            )

        with col4:
            st.metric(
                "總超額報酬",
                f"{result['total_excess_return']:.2%}",
                help="相對於基準的總超額報酬",
            )

    def _plot_brinson_attribution(
        self, result: Dict[str, float], sector_names: List[str]
    ) -> None:
        """繪製 Brinson 歸因圖"""
        effects = ["資產配置效應", "選股效應", "交互效應"]
        values = [
            result["allocation_effect"],
            result["selection_effect"],
            result["interaction_effect"],
        ]

        # 設定顏色
        colors = [
            self.theme["success"] if v >= 0 else self.theme["danger"] for v in values
        ]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=effects,
                    y=values,
                    marker_color=colors,
                    text=[f"{v:.2%}" for v in values],
                    textposition="auto",
                )
            ]
        )

        fig.update_layout(
            title="Brinson 績效歸因分解",
            xaxis_title="歸因效應",
            yaxis_title="超額報酬貢獻",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=400,
        )

        # 添加零線
        fig.add_hline(y=0, line_dash="dash", line_color=self.theme["text"], opacity=0.5)

        st.plotly_chart(fig, use_container_width=True)

    def _display_detailed_attribution(
        self,
        portfolio_weights: np.ndarray,
        benchmark_weights: np.ndarray,
        portfolio_returns: np.ndarray,
        benchmark_returns: np.ndarray,
        sector_names: List[str],
    ) -> None:
        """顯示詳細歸因分析表"""
        st.write("#### 詳細歸因分析")

        # 計算各行業的歸因效應
        weight_diff = portfolio_weights - benchmark_weights
        return_diff = portfolio_returns - benchmark_returns

        allocation_contrib = weight_diff * benchmark_returns
        selection_contrib = benchmark_weights * return_diff
        interaction_contrib = weight_diff * return_diff

        # 創建詳細表格
        detailed_df = pd.DataFrame(
            {
                "行業": sector_names,
                "投資組合權重": [f"{w:.1%}" for w in portfolio_weights],
                "基準權重": [f"{w:.1%}" for w in benchmark_weights],
                "權重差異": [f"{w:+.1%}" for w in weight_diff],
                "投資組合報酬": [f"{r:.2%}" for r in portfolio_returns],
                "基準報酬": [f"{r:.2%}" for r in benchmark_returns],
                "報酬差異": [f"{r:+.2%}" for r in return_diff],
                "配置貢獻": [f"{c:+.2%}" for c in allocation_contrib],
                "選股貢獻": [f"{c:+.2%}" for c in selection_contrib],
                "交互貢獻": [f"{c:+.2%}" for c in interaction_contrib],
            }
        )

        st.dataframe(detailed_df, use_container_width=True)

    def _render_multilevel_attribution(self) -> None:
        """渲染多層級歸因"""
        st.write("### 🏗️ 多層級歸因分析")

        # 歸因層級選擇
        attribution_levels = st.multiselect(
            "選擇歸因層級",
            ["GICS 行業", "風格因子", "個股層級", "國家/地區"],
            default=["GICS 行業", "風格因子"],
        )

        if attribution_levels:
            # 為每個層級創建分析
            for level in attribution_levels:
                with st.expander(f"📈 {level} 歸因分析", expanded=True):
                    self._render_level_attribution(level)

    def _render_level_attribution(self, level: str) -> None:
        """渲染特定層級的歸因分析"""
        if level == "GICS 行業":
            self._render_sector_attribution()
        elif level == "風格因子":
            self._render_style_attribution()
        elif level == "個股層級":
            self._render_stock_attribution()
        elif level == "國家/地區":
            self._render_country_attribution()

    def _render_sector_attribution(self) -> None:
        """渲染行業歸因"""
        # 生成 GICS 行業數據
        sectors = [
            "資訊科技",
            "金融",
            "醫療保健",
            "消費必需品",
            "工業",
            "通訊服務",
            "消費非必需品",
            "能源",
        ]

        # 模擬行業歸因數據
        np.random.seed(42)
        sector_attribution = np.random.normal(0, 0.02, len(sectors))

        # 繪製行業歸因圖
        colors = [
            self.theme["success"] if attr >= 0 else self.theme["danger"]
            for attr in sector_attribution
        ]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=sectors,
                    y=sector_attribution,
                    marker_color=colors,
                    text=[f"{attr:+.2%}" for attr in sector_attribution],
                    textposition="auto",
                )
            ]
        )

        fig.update_layout(
            title="GICS 行業歸因貢獻",
            xaxis_title="行業",
            yaxis_title="歸因貢獻",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=300,
        )

        fig.add_hline(y=0, line_dash="dash", line_color=self.theme["text"], opacity=0.5)

        st.plotly_chart(fig, use_container_width=True)

    def _render_style_attribution(self) -> None:
        """渲染風格因子歸因"""
        style_factors = ["價值", "成長", "品質", "動能", "低波動", "小型股"]

        # 模擬風格因子歸因
        np.random.seed(43)
        style_attribution = np.random.normal(0, 0.015, len(style_factors))

        # 創建雷達圖
        fig = go.Figure()

        fig.add_trace(
            go.Scatterpolar(
                r=np.abs(style_attribution),
                theta=style_factors,
                fill="toself",
                name="風格因子暴露",
                line_color=self.theme["primary"],
            )
        )

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True, range=[0, max(np.abs(style_attribution)) * 1.2]
                )
            ),
            title="風格因子歸因分析",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)

        # 風格因子表格
        style_df = pd.DataFrame(
            {
                "風格因子": style_factors,
                "歸因貢獻": [f"{attr:+.2%}" for attr in style_attribution],
                "貢獻排名": range(1, len(style_factors) + 1),
            }
        )

        # 按貢獻排序
        style_df = style_df.reindex(
            style_df["歸因貢獻"]
            .str.replace("%", "")
            .astype(float)
            .abs()
            .sort_values(ascending=False)
            .index
        )
        style_df["貢獻排名"] = range(1, len(style_factors) + 1)

        st.dataframe(style_df, use_container_width=True)

    def _render_stock_attribution(self) -> None:
        """渲染個股歸因"""
        # 模擬前10大持股的歸因貢獻
        stocks = [f"股票 {i+1}" for i in range(10)]

        np.random.seed(44)
        stock_attribution = np.random.normal(0, 0.01, len(stocks))
        stock_weights = np.random.uniform(0.02, 0.08, len(stocks))

        # 按歸因貢獻排序
        sorted_indices = np.argsort(stock_attribution)[::-1]

        stock_df = pd.DataFrame(
            {
                "股票": [stocks[i] for i in sorted_indices],
                "權重": [f"{stock_weights[i]:.1%}" for i in sorted_indices],
                "歸因貢獻": [f"{stock_attribution[i]:+.2%}" for i in sorted_indices],
                "貢獻類型": [
                    "正貢獻" if stock_attribution[i] >= 0 else "負貢獻"
                    for i in sorted_indices
                ],
            }
        )

        st.dataframe(stock_df, use_container_width=True)

    def _render_country_attribution(self) -> None:
        """渲染國家/地區歸因"""
        countries = ["美國", "中國", "日本", "德國", "英國", "法國", "台灣", "韓國"]

        np.random.seed(45)
        country_attribution = np.random.normal(0, 0.01, len(countries))

        # 世界地圖視覺化（簡化版）
        colors = [
            self.theme["success"] if attr >= 0 else self.theme["danger"]
            for attr in country_attribution
        ]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=countries,
                    y=country_attribution,
                    marker_color=colors,
                    text=[f"{attr:+.2%}" for attr in country_attribution],
                    textposition="auto",
                )
            ]
        )

        fig.update_layout(
            title="國家/地區歸因貢獻",
            xaxis_title="國家/地區",
            yaxis_title="歸因貢獻",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=300,
        )

        fig.add_hline(y=0, line_dash="dash", line_color=self.theme["text"], opacity=0.5)

        st.plotly_chart(fig, use_container_width=True)

    def _render_benchmark_comparison(self) -> None:
        """渲染基準比較分析"""
        st.write("### 📈 基準比較分析")

        # 基準選擇
        benchmarks = st.multiselect(
            "選擇比較基準",
            ["MSCI 世界指數", "S&P 500", "台灣加權指數", "MSCI 新興市場", "自定義基準"],
            default=["MSCI 世界指數", "S&P 500"],
        )

        if benchmarks:
            # 生成比較數據
            comparison_data = self._generate_benchmark_comparison_data(benchmarks)

            # 績效比較表
            self._display_benchmark_comparison_table(comparison_data)

            # 累積報酬圖
            self._plot_cumulative_returns_comparison(comparison_data)

            # 風險調整後績效
            self._display_risk_adjusted_metrics(comparison_data)

    def _display_benchmark_comparison_table(self, data: Dict[str, Any]) -> None:
        """顯示基準比較表"""
        st.write("#### 績效比較摘要")

        comparison_df = pd.DataFrame(data["summary"])
        st.dataframe(comparison_df, use_container_width=True)

    def _plot_cumulative_returns_comparison(self, data: Dict[str, Any]) -> None:
        """繪製累積報酬比較圖"""
        fig = go.Figure()

        for benchmark, returns in data["cumulative_returns"].items():
            fig.add_trace(
                go.Scatter(
                    x=data["dates"],
                    y=returns,
                    mode="lines",
                    name=benchmark,
                    line=dict(width=2),
                )
            )

        fig.update_layout(
            title="累積報酬比較",
            xaxis_title="日期",
            yaxis_title="累積報酬率",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=400,
            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True)

    def _display_risk_adjusted_metrics(self, data: Dict[str, Any]) -> None:
        """顯示風險調整後指標"""
        st.write("#### 風險調整後績效指標")

        metrics_df = pd.DataFrame(data["risk_metrics"])
        st.dataframe(metrics_df, use_container_width=True)

    def _render_time_series_attribution(self) -> None:
        """渲染時間序列歸因"""
        st.write("### 📅 時間序列歸因分析")

        # 時間範圍選擇
        col1, col2 = st.columns(2)

        with col1:
            frequency = st.selectbox("分析頻率", ["日", "週", "月", "季"], index=2)

        with col2:
            lookback_period = st.selectbox(
                "回顧期間", ["6個月", "1年", "2年", "3年"], index=1
            )

        # 生成時間序列歸因數據
        ts_data = self._generate_time_series_attribution_data(
            frequency, lookback_period
        )

        # 繪製時間序列歸因圖
        self._plot_time_series_attribution(ts_data, frequency)

        # 歸因穩定性分析
        self._analyze_attribution_stability(ts_data)

    def _plot_time_series_attribution(
        self, data: Dict[str, Any], frequency: str
    ) -> None:
        """繪製時間序列歸因圖"""
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            subplot_titles=("歸因效應時間序列", "累積歸因貢獻"),
            vertical_spacing=0.1,
        )

        # 歸因效應時間序列
        for effect, values in data["attribution_series"].items():
            fig.add_trace(
                go.Scatter(
                    x=data["dates"],
                    y=values,
                    mode="lines",
                    name=effect,
                    line=dict(width=2),
                ),
                row=1,
                col=1,
            )

        # 累積歸因
        for effect, values in data["cumulative_attribution"].items():
            fig.add_trace(
                go.Scatter(
                    x=data["dates"],
                    y=values,
                    mode="lines",
                    name=f"{effect} (累積)",
                    line=dict(width=2, dash="dash"),
                    showlegend=False,
                ),
                row=2,
                col=1,
            )

        fig.update_layout(
            title=f"{frequency}度歸因分析時間序列",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=600,
        )

        fig.update_xaxes(title_text="日期", row=2, col=1)
        fig.update_yaxes(title_text="歸因貢獻", row=1, col=1)
        fig.update_yaxes(title_text="累積貢獻", row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)

    def _analyze_attribution_stability(self, data: Dict[str, Any]) -> None:
        """分析歸因穩定性"""
        st.write("#### 歸因穩定性分析")

        stability_metrics = {}

        for effect, values in data["attribution_series"].items():
            values_array = np.array(values)
            stability_metrics[effect] = {
                "平均值": np.mean(values_array),
                "標準差": np.std(values_array),
                "變異係數": (
                    np.std(values_array) / np.abs(np.mean(values_array))
                    if np.mean(values_array) != 0
                    else np.inf
                ),
                "正值比例": np.mean(values_array > 0),
            }

        stability_df = pd.DataFrame(stability_metrics).T
        stability_df = stability_df.round(4)

        st.dataframe(stability_df, use_container_width=True)

        # 穩定性評級
        st.write("#### 穩定性評級")
        for effect, metrics in stability_metrics.items():
            cv = metrics["變異係數"]
            if cv < 0.5:
                rating = "🟢 高穩定性"
            elif cv < 1.0:
                rating = "🟡 中等穩定性"
            else:
                rating = "🔴 低穩定性"

            st.write(f"• **{effect}**: {rating} (變異係數: {cv:.2f})")

    def _generate_brinson_data(
        self, sector_count: int
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, List[str]]:
        """生成 Brinson 歸因數據"""
        np.random.seed(42)

        # 生成權重
        portfolio_weights = np.random.dirichlet(np.ones(sector_count))
        benchmark_weights = np.random.dirichlet(np.ones(sector_count))

        # 生成報酬率
        portfolio_returns = np.random.normal(0.08, 0.15, sector_count)
        benchmark_returns = np.random.normal(0.06, 0.12, sector_count)

        # 行業名稱
        sector_names = [f"行業 {i+1}" for i in range(sector_count)]

        return (
            portfolio_weights,
            benchmark_weights,
            portfolio_returns,
            benchmark_returns,
            sector_names,
        )

    def _generate_benchmark_comparison_data(
        self, benchmarks: List[str]
    ) -> Dict[str, Any]:
        """生成基準比較數據"""
        np.random.seed(42)

        # 生成日期
        dates = pd.date_range(end=pd.Timestamp.now(), periods=252, freq="D")

        # 生成累積報酬
        cumulative_returns = {}
        summary_data = []
        risk_metrics_data = []

        for i, benchmark in enumerate(benchmarks):
            # 生成報酬率序列
            daily_returns = np.random.normal(
                0.0008 + i * 0.0002, 0.015 + i * 0.002, len(dates)
            )
            cumulative = (1 + pd.Series(daily_returns)).cumprod() - 1
            cumulative_returns[benchmark] = cumulative.values

            # 計算摘要統計
            annual_return = np.mean(daily_returns) * 252
            annual_vol = np.std(daily_returns) * np.sqrt(252)
            sharpe = annual_return / annual_vol
            max_dd = np.min(cumulative - cumulative.expanding().max())

            summary_data.append(
                {
                    "基準": benchmark,
                    "年化報酬": f"{annual_return:.2%}",
                    "年化波動": f"{annual_vol:.2%}",
                    "最大回撤": f"{max_dd:.2%}",
                }
            )

            risk_metrics_data.append(
                {
                    "基準": benchmark,
                    "夏普比率": f"{sharpe:.3f}",
                    "VaR (95%)": f"{np.percentile(daily_returns, 5):.2%}",
                    "偏度": f"{pd.Series(daily_returns).skew():.3f}",
                    "峰度": f"{pd.Series(daily_returns).kurtosis():.3f}",
                }
            )

        return {
            "dates": dates,
            "cumulative_returns": cumulative_returns,
            "summary": summary_data,
            "risk_metrics": risk_metrics_data,
        }

    def _generate_time_series_attribution_data(
        self, frequency: str, lookback: str
    ) -> Dict[str, Any]:
        """生成時間序列歸因數據"""
        np.random.seed(42)

        # 確定期間長度
        period_map = {"6個月": 126, "1年": 252, "2年": 504, "3年": 756}
        n_days = period_map.get(lookback, 252)

        # 確定頻率
        freq_map = {"日": 1, "週": 5, "月": 22, "季": 66}
        freq_days = freq_map.get(frequency, 22)

        n_periods = n_days // freq_days
        dates = pd.date_range(
            end=pd.Timestamp.now(), periods=n_periods, freq=f"{freq_days}D"
        )

        # 生成歸因時間序列
        allocation_effect = np.random.normal(0.001, 0.01, n_periods)
        selection_effect = np.random.normal(0.002, 0.015, n_periods)
        interaction_effect = np.random.normal(0, 0.005, n_periods)

        # 計算累積歸因
        cumulative_allocation = np.cumsum(allocation_effect)
        cumulative_selection = np.cumsum(selection_effect)
        cumulative_interaction = np.cumsum(interaction_effect)

        return {
            "dates": dates,
            "attribution_series": {
                "資產配置效應": allocation_effect,
                "選股效應": selection_effect,
                "交互效應": interaction_effect,
            },
            "cumulative_attribution": {
                "資產配置效應": cumulative_allocation,
                "選股效應": cumulative_selection,
                "交互效應": cumulative_interaction,
            },
        }
