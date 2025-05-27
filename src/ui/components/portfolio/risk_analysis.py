"""
投資組合風險分析組件

提供 VaR 計算、壓力測試、風險分解等風險管理功能。
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Any, Optional
import logging

from src.ui.utils.portfolio_analytics import (
    PortfolioAnalytics,
    VaRMethod,
    RiskDecomposition,
)

logger = logging.getLogger(__name__)


class RiskAnalysisComponent:
    """風險分析組件類"""

    def __init__(self):
        """初始化風險分析組件"""
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

    def render_risk_dashboard(self, portfolio_data: Dict[str, Any]) -> None:
        """渲染風險分析儀表板

        Args:
            portfolio_data: 投資組合數據
        """
        st.subheader("🛡️ 風險分析儀表板")

        # 生成模擬數據
        returns_data = self._generate_portfolio_returns(portfolio_data)
        weights = self._get_portfolio_weights(portfolio_data)

        # 創建標籤頁
        tab1, tab2, tab3, tab4 = st.tabs(
            ["VaR 分析", "壓力測試", "風險分解", "Monte Carlo 模擬"]
        )

        with tab1:
            self._render_var_analysis(returns_data)

        with tab2:
            self._render_stress_testing(returns_data, weights)

        with tab3:
            self._render_risk_decomposition(weights)

        with tab4:
            self._render_monte_carlo_simulation(returns_data)

    def _render_var_analysis(self, returns: pd.Series) -> None:
        """渲染 VaR 分析"""
        st.write("### 📊 風險值 (Value at Risk) 分析")

        # VaR 設定
        col1, col2, col3 = st.columns(3)

        with col1:
            confidence_level = st.selectbox(
                "信心水準",
                [0.90, 0.95, 0.99],
                index=1,
                format_func=lambda x: f"{x*100:.0f}%",
            )

        with col2:
            var_method = st.selectbox(
                "計算方法",
                [VaRMethod.HISTORICAL, VaRMethod.PARAMETRIC, VaRMethod.MONTE_CARLO],
                format_func=lambda x: {
                    VaRMethod.HISTORICAL: "歷史模擬法",
                    VaRMethod.PARAMETRIC: "參數法",
                    VaRMethod.MONTE_CARLO: "Monte Carlo 法",
                }[x],
            )

        with col3:
            time_horizon = st.selectbox(
                "時間範圍", [1, 5, 10, 22], index=0, format_func=lambda x: f"{x} 天"
            )

        # 計算 VaR
        var_1day = self.analytics.calculate_var(returns, confidence_level, var_method)
        var_horizon = var_1day * np.sqrt(time_horizon)
        expected_shortfall = self.analytics.calculate_expected_shortfall(
            returns, confidence_level
        )

        # 顯示結果
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                f"VaR ({confidence_level*100:.0f}%)",
                f"{var_horizon:.2%}",
                help=f"{time_horizon}天期的風險值",
            )

        with col2:
            st.metric(
                "預期損失 (ES)", f"{expected_shortfall:.2%}", help="超過VaR時的預期損失"
            )

        with col3:
            portfolio_value = 1000000  # 假設投資組合價值
            var_amount = portfolio_value * var_horizon
            st.metric(
                "潛在損失金額",
                f"${var_amount:,.0f}",
                help="以投資組合價值計算的潛在損失",
            )

        # VaR 分佈圖
        self._plot_var_distribution(returns, confidence_level, var_1day)

    def _plot_var_distribution(
        self, returns: pd.Series, confidence_level: float, var: float
    ) -> None:
        """繪製 VaR 分佈圖"""
        fig = go.Figure()

        # 報酬率分佈直方圖
        fig.add_trace(
            go.Histogram(
                x=returns,
                nbinsx=50,
                name="報酬率分佈",
                opacity=0.7,
                marker_color=self.theme["primary"],
            )
        )

        # VaR 線
        fig.add_vline(
            x=-var,
            line_dash="dash",
            line_color=self.theme["danger"],
            annotation_text=f"VaR ({confidence_level*100:.0f}%): {var:.2%}",
        )

        fig.update_layout(
            title="投資組合報酬率分佈與 VaR",
            xaxis_title="日報酬率",
            yaxis_title="頻率",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)

    def _render_stress_testing(self, returns: pd.Series, weights: np.ndarray) -> None:
        """渲染壓力測試"""
        st.write("### ⚠️ 壓力測試")

        # 預設壓力情境
        stress_scenarios = {
            "2008 金融危機": {
                "股票": -0.30,
                "債券": -0.10,
                "商品": -0.25,
                "現金": 0.00,
            },
            "COVID-19 疫情": {"股票": -0.35, "債券": 0.05, "商品": -0.20, "現金": 0.00},
            "利率急升": {"股票": -0.15, "債券": -0.20, "商品": 0.10, "現金": 0.02},
            "通膨飆升": {"股票": -0.10, "債券": -0.15, "商品": 0.25, "現金": -0.05},
        }

        # 選擇壓力情境
        selected_scenarios = st.multiselect(
            "選擇壓力情境",
            list(stress_scenarios.keys()),
            default=list(stress_scenarios.keys())[:2],
        )

        if selected_scenarios:
            # 計算壓力測試結果
            stress_results = {}
            for scenario in selected_scenarios:
                # 簡化計算：假設投資組合包含這些資產類別
                portfolio_shock = (
                    weights[0] * stress_scenarios[scenario]["股票"]
                    + weights[1] * stress_scenarios[scenario]["債券"]
                    + (weights[2] if len(weights) > 2 else 0)
                    * stress_scenarios[scenario]["商品"]
                )
                stress_results[scenario] = portfolio_shock

            # 顯示結果
            self._plot_stress_test_results(stress_results)

            # 詳細結果表格
            st.write("#### 壓力測試詳細結果")
            results_df = pd.DataFrame(
                [
                    {
                        "情境": scenario,
                        "投資組合衝擊": f"{impact:.2%}",
                        "潛在損失": f"${1000000 * abs(impact):,.0f}",
                        "風險等級": self._get_risk_level(impact),
                    }
                    for scenario, impact in stress_results.items()
                ]
            )

            st.dataframe(results_df, use_container_width=True)

    def _plot_stress_test_results(self, stress_results: Dict[str, float]) -> None:
        """繪製壓力測試結果"""
        scenarios = list(stress_results.keys())
        impacts = list(stress_results.values())

        # 設定顏色
        colors = [
            (
                self.theme["danger"]
                if impact < -0.2
                else self.theme["warning"] if impact < -0.1 else self.theme["success"]
            )
            for impact in impacts
        ]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=scenarios,
                    y=impacts,
                    marker_color=colors,
                    text=[f"{impact:.1%}" for impact in impacts],
                    textposition="auto",
                )
            ]
        )

        fig.update_layout(
            title="壓力測試結果",
            xaxis_title="壓力情境",
            yaxis_title="投資組合衝擊",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=400,
        )

        # 添加零線
        fig.add_hline(y=0, line_dash="dash", line_color=self.theme["text"], opacity=0.5)

        st.plotly_chart(fig, use_container_width=True)

    def _render_risk_decomposition(self, weights: np.ndarray) -> None:
        """渲染風險分解"""
        st.write("### 🔍 風險分解分析")

        # 生成共變異數矩陣
        cov_matrix = self._generate_covariance_matrix(len(weights))

        # 計算風險分解
        risk_decomp = self.analytics.decompose_risk(weights, cov_matrix)

        # 風險分解圓餅圖
        col1, col2 = st.columns(2)

        with col1:
            self._plot_risk_decomposition_pie(risk_decomp)

        with col2:
            self._display_risk_metrics(risk_decomp)

        # 風險貢獻分析
        self._plot_risk_contribution(weights, cov_matrix)

    def _plot_risk_decomposition_pie(self, risk_decomp: RiskDecomposition) -> None:
        """繪製風險分解圓餅圖"""
        labels = ["市場風險", "信用風險", "流動性風險", "操作風險"]
        values = [
            risk_decomp.market_risk,
            risk_decomp.credit_risk,
            risk_decomp.liquidity_risk,
            risk_decomp.operational_risk,
        ]

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.3,
                    marker_colors=[
                        self.theme["primary"],
                        self.theme["secondary"],
                        self.theme["warning"],
                        self.theme["danger"],
                    ],
                )
            ]
        )

        fig.update_layout(
            title="風險分解",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)

    def _display_risk_metrics(self, risk_decomp: RiskDecomposition) -> None:
        """顯示風險指標"""
        st.write("#### 風險指標")

        st.metric("總風險", f"{risk_decomp.total_risk:.2%}")
        st.metric("分散化比率", f"{risk_decomp.diversification_ratio:.2f}")

        st.write("#### 風險組成")
        st.write(f"• 市場風險: {risk_decomp.market_risk:.2%}")
        st.write(f"• 信用風險: {risk_decomp.credit_risk:.2%}")
        st.write(f"• 流動性風險: {risk_decomp.liquidity_risk:.2%}")
        st.write(f"• 操作風險: {risk_decomp.operational_risk:.2%}")

    def _plot_risk_contribution(
        self, weights: np.ndarray, cov_matrix: np.ndarray
    ) -> None:
        """繪製風險貢獻圖"""
        st.write("#### 個別資產風險貢獻")

        # 計算邊際風險貢獻
        portfolio_vol = self.analytics._portfolio_volatility(weights, cov_matrix)
        marginal_contrib = np.dot(cov_matrix, weights) / portfolio_vol
        risk_contrib = weights * marginal_contrib

        # 創建資產標籤
        asset_labels = [f"資產 {i+1}" for i in range(len(weights))]

        fig = go.Figure(
            data=[
                go.Bar(
                    x=asset_labels,
                    y=risk_contrib,
                    marker_color=self.theme["primary"],
                    text=[f"{contrib:.3f}" for contrib in risk_contrib],
                    textposition="auto",
                )
            ]
        )

        fig.update_layout(
            title="各資產風險貢獻",
            xaxis_title="資產",
            yaxis_title="風險貢獻",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=300,
        )

        st.plotly_chart(fig, use_container_width=True)

    def _render_monte_carlo_simulation(self, returns: pd.Series) -> None:
        """渲染 Monte Carlo 模擬"""
        st.write("### 🎲 Monte Carlo 模擬")

        # 模擬參數
        col1, col2, col3 = st.columns(3)

        with col1:
            num_simulations = st.selectbox("模擬次數", [1000, 5000, 10000], index=2)

        with col2:
            time_horizon = st.selectbox(
                "模擬期間 (天)",
                [22, 63, 252],
                index=0,
                format_func=lambda x: f"{x} 天 ({'1個月' if x==22 else '3個月' if x==63 else '1年'})",
            )

        with col3:
            if st.button("🔄 執行模擬"):
                self._run_monte_carlo_simulation(returns, num_simulations, time_horizon)

    def _run_monte_carlo_simulation(
        self, returns: pd.Series, num_sims: int, horizon: int
    ) -> None:
        """執行 Monte Carlo 模擬"""
        # 計算參數
        mean_return = returns.mean()
        volatility = returns.std()

        # 執行模擬
        np.random.seed(42)  # 確保結果可重現
        simulated_returns = []

        for _ in range(num_sims):
            # 生成隨機報酬率路徑
            random_returns = np.random.normal(mean_return, volatility, horizon)
            cumulative_return = (1 + pd.Series(random_returns)).prod() - 1
            simulated_returns.append(cumulative_return)

        simulated_returns = np.array(simulated_returns)

        # 顯示結果
        self._display_monte_carlo_results(simulated_returns, horizon)
        self._plot_monte_carlo_distribution(simulated_returns)

    def _display_monte_carlo_results(
        self, simulated_returns: np.ndarray, horizon: int
    ) -> None:
        """顯示 Monte Carlo 結果"""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("平均報酬", f"{np.mean(simulated_returns):.2%}")

        with col2:
            st.metric("標準差", f"{np.std(simulated_returns):.2%}")

        with col3:
            st.metric("5% VaR", f"{np.percentile(simulated_returns, 5):.2%}")

        with col4:
            loss_prob = np.mean(simulated_returns < 0) * 100
            st.metric("虧損機率", f"{loss_prob:.1f}%")

    def _plot_monte_carlo_distribution(self, simulated_returns: np.ndarray) -> None:
        """繪製 Monte Carlo 分佈圖"""
        fig = go.Figure()

        # 分佈直方圖
        fig.add_trace(
            go.Histogram(
                x=simulated_returns,
                nbinsx=50,
                name="模擬報酬分佈",
                opacity=0.7,
                marker_color=self.theme["primary"],
            )
        )

        # 添加統計線
        mean_return = np.mean(simulated_returns)
        var_5 = np.percentile(simulated_returns, 5)

        fig.add_vline(
            x=mean_return,
            line_dash="dash",
            line_color=self.theme["success"],
            annotation_text=f"平均: {mean_return:.2%}",
        )
        fig.add_vline(
            x=var_5,
            line_dash="dash",
            line_color=self.theme["danger"],
            annotation_text=f"5% VaR: {var_5:.2%}",
        )

        fig.update_layout(
            title="Monte Carlo 模擬結果分佈",
            xaxis_title="累積報酬率",
            yaxis_title="頻率",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)

    def _generate_portfolio_returns(self, portfolio_data: Dict[str, Any]) -> pd.Series:
        """生成投資組合報酬率數據"""
        # 生成模擬的日報酬率數據
        np.random.seed(42)
        n_days = 252
        mean_return = 0.0008  # 日平均報酬率
        volatility = 0.015  # 日波動率

        returns = np.random.normal(mean_return, volatility, n_days)
        dates = pd.date_range(end=pd.Timestamp.now(), periods=n_days, freq="D")

        return pd.Series(returns, index=dates)

    def _get_portfolio_weights(self, portfolio_data: Dict[str, Any]) -> np.ndarray:
        """獲取投資組合權重"""
        # 模擬投資組合權重
        return np.array([0.6, 0.3, 0.1])  # 股票、債券、商品

    def _generate_covariance_matrix(self, n_assets: int) -> np.ndarray:
        """生成共變異數矩陣"""
        np.random.seed(42)
        # 生成隨機相關矩陣
        A = np.random.randn(n_assets, n_assets)
        corr_matrix = np.dot(A, A.T)

        # 標準化為相關矩陣
        d = np.sqrt(np.diag(corr_matrix))
        corr_matrix = corr_matrix / np.outer(d, d)

        # 轉換為共變異數矩陣
        volatilities = np.random.uniform(0.1, 0.3, n_assets)
        cov_matrix = np.outer(volatilities, volatilities) * corr_matrix

        return cov_matrix

    def _get_risk_level(self, impact: float) -> str:
        """獲取風險等級"""
        if impact < -0.2:
            return "🔴 高風險"
        elif impact < -0.1:
            return "🟡 中風險"
        elif impact < 0:
            return "🟢 低風險"
        else:
            return "✅ 正面影響"
