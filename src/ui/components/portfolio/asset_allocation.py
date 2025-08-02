"""
資產配置優化組件

提供 MPT 優化、效率前緣、多目標優化等資產配置功能。
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, List, Any, Optional, Tuple
import logging

from src.ui.utils.portfolio_analytics import PortfolioAnalytics, OptimizationObjective

logger = logging.getLogger(__name__)


class AssetAllocationComponent:
    """資產配置優化組件類"""

    def __init__(self):
        """初始化資產配置組件"""
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

    def render_allocation_optimizer(self, portfolio_data: Dict[str, Any]) -> None:
        """渲染資產配置優化器

        Args:
            portfolio_data: 投資組合數據
        """
        st.subheader("⚖️ 資產配置優化")

        # 創建標籤頁
        tab1, tab2, tab3, tab4 = st.tabs(
            ["效率前緣", "投資組合優化", "相關性分析", "再平衡策略"]
        )

        with tab1:
            self._render_efficient_frontier()

        with tab2:
            self._render_portfolio_optimization()

        with tab3:
            self._render_correlation_analysis()

        with tab4:
            self._render_rebalancing_strategy()

    def _render_efficient_frontier(self) -> None:
        """渲染效率前緣"""
        st.write("### 📈 效率前緣分析")

        # 參數設定
        col1, col2 = st.columns(2)

        with col1:
            num_assets = st.slider("資產數量", 3, 10, 5)
            num_points = st.slider("前緣點數", 50, 200, 100)

        with col2:
            risk_free_rate = st.number_input("無風險利率 (%)", 0.0, 10.0, 2.0) / 100
            self.analytics.risk_free_rate = risk_free_rate

        # 生成模擬數據
        expected_returns, cov_matrix, asset_names = self._generate_asset_data(
            num_assets
        )

        if st.button("🔄 計算效率前緣"):
            # 計算效率前緣
            frontier_returns, frontier_volatility, frontier_weights = (
                self.analytics.calculate_efficient_frontier(
                    expected_returns, cov_matrix, num_points
                )
            )

            if len(frontier_returns) > 0:
                # 繪製效率前緣
                self._plot_efficient_frontier(
                    frontier_returns,
                    frontier_volatility,
                    expected_returns,
                    cov_matrix,
                    asset_names,
                )

                # 顯示最佳投資組合
                self._display_optimal_portfolios(
                    frontier_returns, frontier_volatility, frontier_weights, asset_names
                )
            else:
                st.error("效率前緣計算失敗，請檢查輸入參數")

    def _plot_efficient_frontier(
        self,
        frontier_returns: np.ndarray,
        frontier_volatility: np.ndarray,
        expected_returns: np.ndarray,
        cov_matrix: np.ndarray,
        asset_names: List[str],
    ) -> None:
        """繪製效率前緣圖"""
        fig = go.Figure()

        # 效率前緣
        fig.add_trace(
            go.Scatter(
                x=frontier_volatility,
                y=frontier_returns,
                mode="lines",
                name="效率前緣",
                line=dict(color=self.theme["primary"], width=3),
            )
        )

        # 個別資產
        individual_vols = np.sqrt(np.diag(cov_matrix))
        fig.add_trace(
            go.Scatter(
                x=individual_vols,
                y=expected_returns,
                mode="markers",
                name="個別資產",
                marker=dict(size=10, color=self.theme["secondary"], symbol="diamond"),
                text=asset_names,
                textposition="top center",
            )
        )

        # 最大夏普比率投資組合
        max_sharpe_result = self.analytics.optimize_portfolio(
            expected_returns, cov_matrix, OptimizationObjective.MAX_SHARPE
        )

        if max_sharpe_result["success"]:
            fig.add_trace(
                go.Scatter(
                    x=[max_sharpe_result["volatility"]],
                    y=[max_sharpe_result["expected_return"]],
                    mode="markers",
                    name="最大夏普比率",
                    marker=dict(size=15, color=self.theme["success"], symbol="star"),
                )
            )

        # 最小波動率投資組合
        min_vol_result = self.analytics.optimize_portfolio(
            expected_returns, cov_matrix, OptimizationObjective.MIN_VOLATILITY
        )

        if min_vol_result["success"]:
            fig.add_trace(
                go.Scatter(
                    x=[min_vol_result["volatility"]],
                    y=[min_vol_result["expected_return"]],
                    mode="markers",
                    name="最小波動率",
                    marker=dict(
                        size=15, color=self.theme["warning"], symbol="triangle-up"
                    ),
                )
            )

        fig.update_layout(
            title="投資組合效率前緣",
            xaxis_title="波動率 (風險)",
            yaxis_title="預期報酬率",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=500,
            hovermode="closest",
        )

        st.plotly_chart(fig, use_container_width=True)

    def _display_optimal_portfolios(
        self,
        frontier_returns: np.ndarray,
        frontier_volatility: np.ndarray,
        frontier_weights: np.ndarray,
        asset_names: List[str],
    ) -> None:
        """顯示最佳投資組合"""
        st.write("#### 🎯 最佳投資組合")

        # 找到最大夏普比率點
        sharpe_ratios = (
            frontier_returns - self.analytics.risk_free_rate
        ) / frontier_volatility
        max_sharpe_idx = np.argmax(sharpe_ratios)

        # 找到最小波動率點
        min_vol_idx = np.argmin(frontier_volatility)

        col1, col2 = st.columns(2)

        with col1:
            st.write("**最大夏普比率投資組合**")
            max_sharpe_weights = frontier_weights[max_sharpe_idx]

            weights_df = pd.DataFrame(
                {
                    "資產": asset_names,
                    "權重": max_sharpe_weights,
                    "權重%": [f"{w:.1%}" for w in max_sharpe_weights],
                }
            )

            st.dataframe(weights_df, use_container_width=True)

            st.metric("預期報酬率", f"{frontier_returns[max_sharpe_idx]:.2%}")
            st.metric("波動率", f"{frontier_volatility[max_sharpe_idx]:.2%}")
            st.metric("夏普比率", f"{sharpe_ratios[max_sharpe_idx]:.3f}")

        with col2:
            st.write("**最小波動率投資組合**")
            min_vol_weights = frontier_weights[min_vol_idx]

            weights_df = pd.DataFrame(
                {
                    "資產": asset_names,
                    "權重": min_vol_weights,
                    "權重%": [f"{w:.1%}" for w in min_vol_weights],
                }
            )

            st.dataframe(weights_df, use_container_width=True)

            st.metric("預期報酬率", f"{frontier_returns[min_vol_idx]:.2%}")
            st.metric("波動率", f"{frontier_volatility[min_vol_idx]:.2%}")
            st.metric("夏普比率", f"{sharpe_ratios[min_vol_idx]:.3f}")

    def _render_portfolio_optimization(self) -> None:
        """渲染投資組合優化"""
        st.write("### 🎯 投資組合優化")

        # 優化參數
        col1, col2 = st.columns(2)

        with col1:
            num_assets = st.slider("資產數量", 3, 10, 5, key="opt_assets")

            objective = st.selectbox(
                "優化目標",
                [
                    OptimizationObjective.MAX_SHARPE,
                    OptimizationObjective.MIN_VOLATILITY,
                    OptimizationObjective.RISK_PARITY,
                    OptimizationObjective.MAX_DIVERSIFICATION,
                ],
                format_func=lambda x: {
                    OptimizationObjective.MAX_SHARPE: "最大夏普比率",
                    OptimizationObjective.MIN_VOLATILITY: "最小波動率",
                    OptimizationObjective.RISK_PARITY: "風險平價",
                    OptimizationObjective.MAX_DIVERSIFICATION: "最大分散化",
                }[x],
            )

        with col2:
            max_weight = st.slider("單一資產最大權重 (%)", 10, 100, 50) / 100
            min_weight = st.slider("單一資產最小權重 (%)", 0, 20, 0) / 100

        # 約束條件
        constraints = {
            "max_weight": max_weight,
            "min_weight": {i: min_weight for i in range(num_assets)},
        }

        # 生成數據
        expected_returns, cov_matrix, asset_names = self._generate_asset_data(
            num_assets
        )

        if st.button("🔄 執行優化"):
            # 執行優化
            result = self.analytics.optimize_portfolio(
                expected_returns, cov_matrix, objective, constraints
            )

            if result["success"]:
                self._display_optimization_result(result, asset_names)
                self._plot_optimization_weights(result["weights"], asset_names)
            else:
                st.error(f"優化失敗: {result.get('message', '未知錯誤')}")

    def _display_optimization_result(
        self, result: Dict[str, Any], asset_names: List[str]
    ) -> None:
        """顯示優化結果"""
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("預期報酬率", f"{result['expected_return']:.2%}")

        with col2:
            st.metric("波動率", f"{result['volatility']:.2%}")

        with col3:
            st.metric("夏普比率", f"{result['sharpe_ratio']:.3f}")

        # 權重分配表
        st.write("#### 最佳權重分配")
        weights_df = pd.DataFrame(
            {
                "資產": asset_names,
                "權重": result["weights"],
                "權重%": [f"{w:.1%}" for w in result["weights"]],
            }
        )

        st.dataframe(weights_df, use_container_width=True)

    def _plot_optimization_weights(
        self, weights: np.ndarray, asset_names: List[str]
    ) -> None:
        """繪製優化權重圖"""
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=asset_names,
                    values=weights,
                    hole=0.3,
                    marker_colors=px.colors.qualitative.Set3[: len(asset_names)],
                )
            ]
        )

        fig.update_layout(
            title="最佳權重分配",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)

    def _render_correlation_analysis(self) -> None:
        """渲染相關性分析"""
        st.write("### 🔗 相關性分析")

        # 參數設定
        col1, col2 = st.columns(2)

        with col1:
            num_assets = st.slider("資產數量", 3, 15, 8, key="corr_assets")
            window_size = st.selectbox("滾動窗口", [30, 60, 90, 120], index=1)

        with col2:
            correlation_threshold = st.slider("相關性閾值", 0.0, 1.0, 0.7)

        # 生成相關性數據
        correlation_matrix, asset_names = self._generate_correlation_data(num_assets)

        # 相關性熱力圖
        self._plot_correlation_heatmap(correlation_matrix, asset_names)

        # 高相關性警告
        self._display_correlation_warnings(
            correlation_matrix, asset_names, correlation_threshold
        )

        # 動態相關性分析
        self._plot_dynamic_correlation(asset_names[:3], window_size)

    def _plot_correlation_heatmap(
        self, corr_matrix: np.ndarray, asset_names: List[str]
    ) -> None:
        """繪製相關性熱力圖"""
        fig = go.Figure(
            data=go.Heatmap(
                z=corr_matrix,
                x=asset_names,
                y=asset_names,
                colorscale="RdBu",
                zmid=0,
                text=np.round(corr_matrix, 2),
                texttemplate="%{text}",
                textfont={"size": 10},
                hoverongaps=False,
            )
        )

        fig.update_layout(
            title="資產相關性矩陣",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=500,
        )

        st.plotly_chart(fig, use_container_width=True)

    def _display_correlation_warnings(
        self, corr_matrix: np.ndarray, asset_names: List[str], threshold: float
    ) -> None:
        """顯示高相關性警告"""
        high_corr_pairs = []

        for i in range(len(asset_names)):
            for j in range(i + 1, len(asset_names)):
                if abs(corr_matrix[i, j]) > threshold:
                    high_corr_pairs.append(
                        {
                            "資產1": asset_names[i],
                            "資產2": asset_names[j],
                            "相關係數": f"{corr_matrix[i, j]:.3f}",
                            "風險等級": (
                                "🔴 高" if abs(corr_matrix[i, j]) > 0.8 else "🟡 中"
                            ),
                        }
                    )

        if high_corr_pairs:
            st.warning(f"⚠️ 發現 {len(high_corr_pairs)} 對高相關性資產")
            st.dataframe(pd.DataFrame(high_corr_pairs), use_container_width=True)
        else:
            st.success("✅ 所有資產相關性都在合理範圍內")

    def _plot_dynamic_correlation(
        self, asset_names: List[str], window_size: int
    ) -> None:
        """繪製動態相關性"""
        st.write("#### 動態相關性分析")

        # 生成時間序列相關性數據
        dates = pd.date_range(end=pd.Timestamp.now(), periods=252, freq="D")

        # 模擬滾動相關性
        np.random.seed(42)
        rolling_corr = (
            0.3
            + 0.4 * np.sin(np.linspace(0, 4 * np.pi, len(dates)))
            + 0.1 * np.random.randn(len(dates))
        )

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=dates,
                y=rolling_corr,
                mode="lines",
                name=f"{asset_names[0]} vs {asset_names[1]}",
                line=dict(color=self.theme["primary"], width=2),
            )
        )

        # 添加閾值線
        fig.add_hline(
            y=0.7,
            line_dash="dash",
            line_color=self.theme["danger"],
            annotation_text="高相關性閾值",
        )

        fig.update_layout(
            title=f"滾動相關性 ({window_size}天窗口)",
            xaxis_title="日期",
            yaxis_title="相關係數",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=300,
        )

        st.plotly_chart(fig, use_container_width=True)

    def _render_rebalancing_strategy(self) -> None:
        """渲染再平衡策略"""
        st.write("### ⚖️ 再平衡策略")

        # 策略參數
        col1, col2 = st.columns(2)

        with col1:
            rebalance_threshold = st.slider("再平衡閾值 (%)", 1, 20, 5) / 100
            transaction_cost = st.slider("交易成本 (%)", 0.0, 2.0, 0.1) / 100

        with col2:
            rebalance_frequency = st.selectbox(
                "再平衡頻率", ["閾值觸發", "月度", "季度", "年度"]
            )

        # 模擬當前投資組合
        current_weights = np.array([0.35, 0.25, 0.20, 0.15, 0.05])
        target_weights = np.array([0.30, 0.30, 0.20, 0.15, 0.05])
        asset_names = [f"資產 {i+1}" for i in range(len(current_weights))]

        # 計算再平衡建議
        transaction_costs = np.full(len(current_weights), transaction_cost)
        rebalance_result = self.analytics.suggest_rebalancing(
            current_weights, target_weights, rebalance_threshold, transaction_costs
        )

        # 顯示結果
        self._display_rebalancing_result(rebalance_result, asset_names)

        # 繪製權重比較圖
        self._plot_weight_comparison(current_weights, target_weights, asset_names)

    def _display_rebalancing_result(
        self, result: Dict[str, Any], asset_names: List[str]
    ) -> None:
        """顯示再平衡結果"""
        if result["needs_rebalancing"]:
            st.warning("⚠️ 建議進行再平衡")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("最大偏離度", f"{result['max_deviation']:.1%}")

            with col2:
                st.metric("交易筆數", result["number_of_trades"])

            with col3:
                st.metric("總交易成本", f"{result['total_transaction_cost']:.2%}")

            # 交易建議表
            if result["trades"]:
                st.write("#### 交易建議")
                trades_data = []

                for trade in result["trades"]:
                    trades_data.append(
                        {
                            "資產": asset_names[trade["asset_index"]],
                            "當前權重": f"{trade['current_weight']:.1%}",
                            "目標權重": f"{trade['target_weight']:.1%}",
                            "交易量": f"{trade['trade_amount']:+.1%}",
                            "動作": (
                                "🟢 買入" if trade["action"] == "buy" else "🔴 賣出"
                            ),
                            "交易成本": f"{trade['trade_cost']:.3%}",
                        }
                    )

                st.dataframe(pd.DataFrame(trades_data), use_container_width=True)
        else:
            st.success("✅ 當前配置在目標範圍內，無需再平衡")

    def _plot_weight_comparison(
        self,
        current_weights: np.ndarray,
        target_weights: np.ndarray,
        asset_names: List[str],
    ) -> None:
        """繪製權重比較圖"""
        fig = go.Figure()

        x = np.arange(len(asset_names))

        fig.add_trace(
            go.Bar(
                x=asset_names,
                y=current_weights,
                name="當前權重",
                marker_color=self.theme["primary"],
                opacity=0.7,
            )
        )

        fig.add_trace(
            go.Bar(
                x=asset_names,
                y=target_weights,
                name="目標權重",
                marker_color=self.theme["secondary"],
                opacity=0.7,
            )
        )

        fig.update_layout(
            title="當前權重 vs 目標權重",
            xaxis_title="資產",
            yaxis_title="權重",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=400,
            barmode="group",
        )

        st.plotly_chart(fig, use_container_width=True)

    def _generate_asset_data(
        self, num_assets: int
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """生成資產數據"""
        np.random.seed(42)

        # 生成預期報酬率
        expected_returns = np.random.uniform(0.05, 0.15, num_assets)

        # 生成共變異數矩陣
        A = np.random.randn(num_assets, num_assets)
        cov_matrix = np.dot(A, A.T) * 0.01  # 縮放到合理範圍

        # 資產名稱
        asset_names = [f"資產 {i+1}" for i in range(num_assets)]

        return expected_returns, cov_matrix, asset_names

    def _generate_correlation_data(
        self, num_assets: int
    ) -> Tuple[np.ndarray, List[str]]:
        """生成相關性數據"""
        np.random.seed(42)

        # 生成隨機相關矩陣
        A = np.random.randn(num_assets, num_assets)
        corr_matrix = np.dot(A, A.T)

        # 標準化為相關矩陣
        d = np.sqrt(np.diag(corr_matrix))
        corr_matrix = corr_matrix / np.outer(d, d)

        # 確保對角線為1
        np.fill_diagonal(corr_matrix, 1.0)

        asset_names = [f"資產 {i+1}" for i in range(num_assets)]

        return corr_matrix, asset_names
