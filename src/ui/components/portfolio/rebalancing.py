"""
智能再平衡建議組件

提供多策略再平衡、交易成本優化、稅務效率等再平衡功能。
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
from enum import Enum

from src.ui.utils.portfolio_analytics import PortfolioAnalytics

logger = logging.getLogger(__name__)


class RebalancingStrategy(Enum):
    """再平衡策略枚舉"""

    THRESHOLD = "threshold"
    TIME_BASED = "time_based"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    CUSTOM = "custom"


class RebalancingComponent:
    """再平衡建議組件類"""

    def __init__(self):
        """初始化再平衡組件"""
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

    def render_rebalancing_system(self, portfolio_data: Dict[str, Any]) -> None:
        """渲染再平衡建議系統

        Args:
            portfolio_data: 投資組合數據
        """
        st.subheader("⚖️ 智能再平衡建議系統")

        # 創建標籤頁
        tab1, tab2, tab3, tab4 = st.tabs(
            ["再平衡分析", "策略回測", "交易成本優化", "稅務效率"]
        )

        with tab1:
            self._render_rebalancing_analysis()

        with tab2:
            self._render_strategy_backtest()

        with tab3:
            self._render_cost_optimization()

        with tab4:
            self._render_tax_efficiency()

    def _render_rebalancing_analysis(self) -> None:
        """渲染再平衡分析"""
        st.write("### 📊 再平衡需求分析")

        # 策略參數設定
        col1, col2 = st.columns(2)

        with col1:
            strategy = st.selectbox(
                "再平衡策略",
                [
                    RebalancingStrategy.THRESHOLD,
                    RebalancingStrategy.TIME_BASED,
                    RebalancingStrategy.VOLATILITY_ADJUSTED,
                    RebalancingStrategy.CUSTOM,
                ],
                format_func=lambda x: {
                    RebalancingStrategy.THRESHOLD: "閾值觸發",
                    RebalancingStrategy.TIME_BASED: "定期再平衡",
                    RebalancingStrategy.VOLATILITY_ADJUSTED: "波動率調整",
                    RebalancingStrategy.CUSTOM: "自定義規則",
                }[x],
            )

            threshold = st.slider("偏離閾值 (%)", 1, 20, 5) / 100

        with col2:
            transaction_cost = st.slider("交易成本 (%)", 0.0, 2.0, 0.1) / 100
            min_trade_size = st.slider("最小交易金額", 1000, 50000, 5000)

        # 生成當前投資組合數據
        current_portfolio, target_portfolio = self._generate_portfolio_data()

        # 計算再平衡建議
        rebalance_result = self._calculate_rebalancing_recommendation(
            current_portfolio, target_portfolio, threshold, transaction_cost
        )

        # 顯示分析結果
        self._display_rebalancing_summary(rebalance_result)

        # 視覺化權重偏離
        self._plot_weight_deviation(current_portfolio, target_portfolio)

        # 詳細交易建議
        self._display_trading_recommendations(rebalance_result, min_trade_size)

    def _display_rebalancing_summary(self, result: Dict[str, Any]) -> None:
        """顯示再平衡摘要"""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            needs_rebalancing = "是" if result["needs_rebalancing"] else "否"
            color = "normal" if not result["needs_rebalancing"] else "inverse"
            st.metric("需要再平衡", needs_rebalancing)

        with col2:
            st.metric("最大偏離度", f"{result['max_deviation']:.1%}")

        with col3:
            st.metric("建議交易數", result.get("number_of_trades", 0))

        with col4:
            st.metric("預估交易成本", f"{result.get('total_transaction_cost', 0):.2%}")

        # 再平衡緊急程度
        urgency = self._assess_rebalancing_urgency(result["max_deviation"])
        st.info(f"🎯 再平衡緊急程度: {urgency}")

    def _plot_weight_deviation(
        self, current: Dict[str, float], target: Dict[str, float]
    ) -> None:
        """繪製權重偏離圖"""
        assets = list(current.keys())
        current_weights = [current[asset] for asset in assets]
        target_weights = [target[asset] for asset in assets]
        deviations = [current[asset] - target[asset] for asset in assets]

        fig = make_subplots(
            rows=2,
            cols=1,
            subplot_titles=("當前權重 vs 目標權重", "權重偏離度"),
            vertical_spacing=0.15,
        )

        # 權重比較
        fig.add_trace(
            go.Bar(
                x=assets,
                y=current_weights,
                name="當前權重",
                marker_color=self.theme["primary"],
                opacity=0.7,
            ),
            row=1,
            col=1,
        )

        fig.add_trace(
            go.Bar(
                x=assets,
                y=target_weights,
                name="目標權重",
                marker_color=self.theme["secondary"],
                opacity=0.7,
            ),
            row=1,
            col=1,
        )

        # 偏離度
        colors = [
            self.theme["success"] if d >= 0 else self.theme["danger"]
            for d in deviations
        ]
        fig.add_trace(
            go.Bar(
                x=assets,
                y=deviations,
                name="權重偏離",
                marker_color=colors,
                text=[f"{d:+.1%}" for d in deviations],
                textposition="auto",
            ),
            row=2,
            col=1,
        )

        fig.update_layout(
            height=600,
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            showlegend=True,
        )

        fig.update_yaxes(title_text="權重", row=1, col=1)
        fig.update_yaxes(title_text="偏離度", row=2, col=1)
        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color=self.theme["text"],
            opacity=0.5,
            row=2,
            col=1,
        )

        st.plotly_chart(fig, use_container_width=True)

    def _display_trading_recommendations(
        self, result: Dict[str, Any], min_trade_size: float
    ) -> None:
        """顯示交易建議"""
        if result["needs_rebalancing"] and result.get("trades"):
            st.write("#### 📋 詳細交易建議")

            trades_data = []
            for trade in result["trades"]:
                if (
                    abs(trade["trade_amount"]) * 1000000 >= min_trade_size
                ):  # 假設投資組合價值100萬
                    trades_data.append(
                        {
                            "資產": trade.get(
                                "asset_name", f"資產 {trade['asset_index']+1}"
                            ),
                            "當前權重": f"{trade['current_weight']:.1%}",
                            "目標權重": f"{trade['target_weight']:.1%}",
                            "偏離度": f"{trade['trade_amount']:+.1%}",
                            "交易動作": (
                                "🟢 買入" if trade["action"] == "buy" else "🔴 賣出"
                            ),
                            "交易金額": f"${abs(trade['trade_amount']) * 1000000:,.0f}",
                            "交易成本": f"${trade['trade_cost'] * 1000000:,.0f}",
                            "優先級": self._get_trade_priority(
                                abs(trade["trade_amount"])
                            ),
                        }
                    )

            if trades_data:
                trades_df = pd.DataFrame(trades_data)
                st.dataframe(trades_df, use_container_width=True)

                # 交易執行建議
                st.write("#### 💡 執行建議")
                high_priority = sum(1 for t in trades_data if t["優先級"] == "🔴 高")
                medium_priority = sum(1 for t in trades_data if t["優先級"] == "🟡 中")

                if high_priority > 0:
                    st.warning(f"⚠️ 有 {high_priority} 筆高優先級交易需要立即執行")
                if medium_priority > 0:
                    st.info(f"ℹ️ 有 {medium_priority} 筆中優先級交易建議在本週內執行")
            else:
                st.info("所有偏離都低於最小交易金額，建議暫時不進行再平衡")

    def _render_strategy_backtest(self) -> None:
        """渲染策略回測"""
        st.write("### 📈 再平衡策略回測")

        # 回測參數
        col1, col2 = st.columns(2)

        with col1:
            backtest_period = st.selectbox(
                "回測期間", ["1年", "2年", "3年", "5年"], index=1
            )
            rebalance_frequency = st.selectbox(
                "再平衡頻率", ["月度", "季度", "半年度", "年度"], index=1
            )

        with col2:
            threshold_range = st.slider("閾值範圍 (%)", 1, 20, (3, 10))
            include_costs = st.checkbox("包含交易成本", value=True)

        if st.button("🔄 執行回測"):
            # 生成回測結果
            backtest_results = self._run_strategy_backtest(
                backtest_period, rebalance_frequency, threshold_range, include_costs
            )

            # 顯示回測結果
            self._display_backtest_results(backtest_results)

            # 繪製績效比較圖
            self._plot_backtest_performance(backtest_results)

    def _display_backtest_results(self, results: Dict[str, Any]) -> None:
        """顯示回測結果"""
        st.write("#### 📊 回測績效摘要")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("年化報酬率", f"{results['annual_return']:.2%}")

        with col2:
            st.metric("年化波動率", f"{results['annual_volatility']:.2%}")

        with col3:
            st.metric("夏普比率", f"{results['sharpe_ratio']:.3f}")

        with col4:
            st.metric("最大回撤", f"{results['max_drawdown']:.2%}")

        # 策略比較表
        st.write("#### 🔍 策略比較")
        comparison_df = pd.DataFrame(results["strategy_comparison"])
        st.dataframe(comparison_df, use_container_width=True)

    def _plot_backtest_performance(self, results: Dict[str, Any]) -> None:
        """繪製回測績效圖"""
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            subplot_titles=("累積報酬比較", "回撤分析"),
            vertical_spacing=0.1,
        )

        # 累積報酬
        for strategy, performance in results["cumulative_returns"].items():
            fig.add_trace(
                go.Scatter(
                    x=results["dates"],
                    y=performance,
                    mode="lines",
                    name=strategy,
                    line=dict(width=2),
                ),
                row=1,
                col=1,
            )

        # 回撤分析
        for strategy, drawdown in results["drawdowns"].items():
            fig.add_trace(
                go.Scatter(
                    x=results["dates"],
                    y=drawdown,
                    mode="lines",
                    name=f"{strategy} 回撤",
                    fill=(
                        "tonexty"
                        if strategy == list(results["drawdowns"].keys())[0]
                        else None
                    ),
                    showlegend=False,
                ),
                row=2,
                col=1,
            )

        fig.update_layout(
            height=600,
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
        )

        fig.update_yaxes(title_text="累積報酬率", row=1, col=1)
        fig.update_yaxes(title_text="回撤", row=2, col=1)
        fig.update_xaxes(title_text="日期", row=2, col=1)

        st.plotly_chart(fig, use_container_width=True)

    def _render_cost_optimization(self) -> None:
        """渲染交易成本優化"""
        st.write("### 💰 交易成本優化")

        # 成本參數設定
        col1, col2 = st.columns(2)

        with col1:
            bid_ask_spread = st.slider("買賣價差 (%)", 0.01, 1.0, 0.1) / 100
            commission_rate = st.slider("手續費率 (%)", 0.01, 0.5, 0.1) / 100

        with col2:
            market_impact = st.slider("市場衝擊成本 (%)", 0.0, 0.5, 0.05) / 100
            portfolio_value = st.number_input("投資組合價值", 100000, 10000000, 1000000)

        # 成本分析
        cost_analysis = self._analyze_trading_costs(
            bid_ask_spread, commission_rate, market_impact, portfolio_value
        )

        # 顯示成本分解
        self._display_cost_breakdown(cost_analysis)

        # 成本優化建議
        self._display_cost_optimization_suggestions(cost_analysis)

    def _display_cost_breakdown(self, analysis: Dict[str, Any]) -> None:
        """顯示成本分解"""
        st.write("#### 💸 交易成本分解")

        # 成本圓餅圖
        labels = ["買賣價差", "手續費", "市場衝擊", "其他成本"]
        values = [
            analysis["bid_ask_cost"],
            analysis["commission_cost"],
            analysis["market_impact_cost"],
            analysis["other_costs"],
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
            title="交易成本組成",
            plot_bgcolor=self.theme["background"],
            paper_bgcolor=self.theme["background"],
            font_color=self.theme["text"],
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)

        # 成本明細表
        cost_df = pd.DataFrame(
            {
                "成本類型": labels,
                "金額": [f"${v:,.0f}" for v in values],
                "佔比": [f"{v/sum(values)*100:.1f}%" for v in values],
            }
        )

        st.dataframe(cost_df, use_container_width=True)

    def _display_cost_optimization_suggestions(self, analysis: Dict[str, Any]) -> None:
        """顯示成本優化建議"""
        st.write("#### 💡 成本優化建議")

        suggestions = []

        if analysis["bid_ask_cost"] > analysis["total_cost"] * 0.4:
            suggestions.append("🎯 買賣價差佔比較高，建議使用限價單減少價差成本")

        if analysis["market_impact_cost"] > analysis["total_cost"] * 0.3:
            suggestions.append("📊 市場衝擊成本較高，建議分批執行大額交易")

        if analysis["commission_cost"] > analysis["total_cost"] * 0.2:
            suggestions.append("💼 手續費佔比較高，考慮尋找更優惠的券商費率")

        suggestions.append("⏰ 建議在市場流動性較好的時段執行交易")
        suggestions.append("🔄 考慮使用演算法交易減少市場衝擊")

        for suggestion in suggestions:
            st.write(f"• {suggestion}")

    def _render_tax_efficiency(self) -> None:
        """渲染稅務效率"""
        st.write("### 🏛️ 稅務效率優化")

        # 稅務參數
        col1, col2 = st.columns(2)

        with col1:
            short_term_tax_rate = st.slider("短期資本利得稅率 (%)", 0, 50, 25) / 100
            long_term_tax_rate = st.slider("長期資本利得稅率 (%)", 0, 30, 15) / 100

        with col2:
            holding_period_threshold = st.slider("長期持有門檻 (天)", 180, 730, 365)
            enable_tax_loss_harvesting = st.checkbox("啟用稅損收割", value=True)

        # 稅務分析
        tax_analysis = self._analyze_tax_efficiency(
            short_term_tax_rate,
            long_term_tax_rate,
            holding_period_threshold,
            enable_tax_loss_harvesting,
        )

        # 顯示稅務影響
        self._display_tax_impact(tax_analysis)

        # 稅務優化建議
        self._display_tax_optimization_strategies(tax_analysis)

    def _display_tax_impact(self, analysis: Dict[str, Any]) -> None:
        """顯示稅務影響"""
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("預估稅負", f"${analysis['estimated_tax']:,.0f}")

        with col2:
            st.metric("稅後報酬率", f"{analysis['after_tax_return']:.2%}")

        with col3:
            st.metric("稅務效率", f"{analysis['tax_efficiency']:.1%}")

        # 稅損收割機會
        if analysis["tax_loss_opportunities"]:
            st.write("#### 🎯 稅損收割機會")

            opportunities_df = pd.DataFrame(analysis["tax_loss_opportunities"])
            st.dataframe(opportunities_df, use_container_width=True)

    def _display_tax_optimization_strategies(self, analysis: Dict[str, Any]) -> None:
        """顯示稅務優化策略"""
        st.write("#### 📋 稅務優化策略")

        strategies = [
            "🕐 優先賣出持有超過一年的獲利部位，享受長期資本利得優惠稅率",
            "📉 實現虧損部位進行稅損收割，抵銷資本利得",
            "🔄 避免在年底前實現大額短期資本利得",
            "💼 考慮使用稅務遞延帳戶進行頻繁交易",
            "📊 定期檢視持股的稅務成本基礎",
        ]

        for strategy in strategies:
            st.write(f"• {strategy}")

    def _generate_portfolio_data(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """生成投資組合數據"""
        assets = ["股票A", "股票B", "債券C", "REITs D", "商品E"]

        # 當前權重（模擬市場波動後的權重）
        np.random.seed(42)
        current_weights = np.random.dirichlet([1, 1, 1, 1, 1]) * np.random.uniform(
            0.8, 1.2, 5
        )
        current_weights = current_weights / current_weights.sum()

        # 目標權重
        target_weights = np.array([0.3, 0.25, 0.2, 0.15, 0.1])

        current_portfolio = dict(zip(assets, current_weights))
        target_portfolio = dict(zip(assets, target_weights))

        return current_portfolio, target_portfolio

    def _calculate_rebalancing_recommendation(
        self,
        current: Dict[str, float],
        target: Dict[str, float],
        threshold: float,
        transaction_cost: float,
    ) -> Dict[str, Any]:
        """計算再平衡建議"""
        current_weights = np.array(list(current.values()))
        target_weights = np.array(list(target.values()))
        transaction_costs = np.full(len(current_weights), transaction_cost)

        return self.analytics.suggest_rebalancing(
            current_weights, target_weights, threshold, transaction_costs
        )

    def _assess_rebalancing_urgency(self, max_deviation: float) -> str:
        """評估再平衡緊急程度"""
        if max_deviation > 0.15:
            return "🔴 緊急 - 建議立即執行"
        elif max_deviation > 0.10:
            return "🟡 中等 - 建議本週內執行"
        elif max_deviation > 0.05:
            return "🟢 低 - 可在下次定期再平衡時執行"
        else:
            return "✅ 無需要 - 當前配置良好"

    def _get_trade_priority(self, deviation: float) -> str:
        """獲取交易優先級"""
        if deviation > 0.10:
            return "🔴 高"
        elif deviation > 0.05:
            return "🟡 中"
        else:
            return "🟢 低"

    def _run_strategy_backtest(
        self,
        period: str,
        frequency: str,
        threshold_range: Tuple[float, float],
        include_costs: bool,
    ) -> Dict[str, Any]:
        """執行策略回測"""
        # 模擬回測結果
        np.random.seed(42)

        dates = pd.date_range(end=pd.Timestamp.now(), periods=252, freq="D")

        # 生成不同策略的績效
        strategies = ["無再平衡", "閾值再平衡", "定期再平衡", "波動率調整"]

        cumulative_returns = {}
        drawdowns = {}
        strategy_comparison = []

        for i, strategy in enumerate(strategies):
            # 生成報酬率序列
            daily_returns = np.random.normal(
                0.0008 + i * 0.0001, 0.015 - i * 0.001, len(dates)
            )
            cumulative = (1 + pd.Series(daily_returns)).cumprod() - 1

            # 計算回撤
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / (1 + running_max)

            cumulative_returns[strategy] = cumulative.values
            drawdowns[strategy] = drawdown.values

            # 計算績效指標
            annual_return = np.mean(daily_returns) * 252
            annual_vol = np.std(daily_returns) * np.sqrt(252)
            sharpe = annual_return / annual_vol
            max_dd = np.min(drawdown)

            strategy_comparison.append(
                {
                    "策略": strategy,
                    "年化報酬": f"{annual_return:.2%}",
                    "年化波動": f"{annual_vol:.2%}",
                    "夏普比率": f"{sharpe:.3f}",
                    "最大回撤": f"{max_dd:.2%}",
                }
            )

        return {
            "dates": dates,
            "cumulative_returns": cumulative_returns,
            "drawdowns": drawdowns,
            "strategy_comparison": strategy_comparison,
            "annual_return": np.mean(
                [float(s["年化報酬"].rstrip("%")) / 100 for s in strategy_comparison]
            ),
            "annual_volatility": np.mean(
                [float(s["年化波動"].rstrip("%")) / 100 for s in strategy_comparison]
            ),
            "sharpe_ratio": np.mean(
                [float(s["夏普比率"]) for s in strategy_comparison]
            ),
            "max_drawdown": np.mean(
                [float(s["最大回撤"].rstrip("%")) / 100 for s in strategy_comparison]
            ),
        }

    def _analyze_trading_costs(
        self,
        bid_ask_spread: float,
        commission_rate: float,
        market_impact: float,
        portfolio_value: float,
    ) -> Dict[str, Any]:
        """分析交易成本"""
        # 假設需要交易的金額為投資組合的10%
        trade_amount = portfolio_value * 0.1

        bid_ask_cost = trade_amount * bid_ask_spread
        commission_cost = trade_amount * commission_rate
        market_impact_cost = trade_amount * market_impact
        other_costs = trade_amount * 0.01  # 其他雜費

        total_cost = bid_ask_cost + commission_cost + market_impact_cost + other_costs

        return {
            "bid_ask_cost": bid_ask_cost,
            "commission_cost": commission_cost,
            "market_impact_cost": market_impact_cost,
            "other_costs": other_costs,
            "total_cost": total_cost,
            "cost_ratio": total_cost / trade_amount,
        }

    def _analyze_tax_efficiency(
        self,
        short_term_rate: float,
        long_term_rate: float,
        holding_threshold: int,
        enable_harvesting: bool,
    ) -> Dict[str, Any]:
        """分析稅務效率"""
        # 模擬稅務分析結果
        np.random.seed(42)

        estimated_tax = np.random.uniform(5000, 25000)
        after_tax_return = np.random.uniform(0.06, 0.12)
        tax_efficiency = (1 - estimated_tax / 100000) * 100

        tax_loss_opportunities = []
        if enable_harvesting:
            tax_loss_opportunities = [
                {
                    "資產": "股票B",
                    "未實現虧損": "$-3,500",
                    "持有天數": 45,
                    "建議": "可考慮實現虧損",
                },
                {
                    "資產": "債券C",
                    "未實現虧損": "$-1,200",
                    "持有天數": 120,
                    "建議": "小額虧損，可暫緩",
                },
            ]

        return {
            "estimated_tax": estimated_tax,
            "after_tax_return": after_tax_return,
            "tax_efficiency": tax_efficiency,
            "tax_loss_opportunities": tax_loss_opportunities,
        }
