"""風險指標顯示模組

此模組提供風險指標的監控和顯示功能，包括：
- 投資組合總覽
- 風險指標卡片
- 風險視覺化圖表
- VaR 和回撤分析

Author: AI Trading System
Version: 1.0.0
"""

from typing import Dict, Any
import streamlit as st
import numpy as np
import plotly.graph_objects as go

from src.ui.pages.risk_management.utils import (
    get_risk_management_service,
    get_mock_risk_metrics,
    format_currency,
)


def show_risk_indicators() -> None:
    """顯示風險指標

    提供完整的風險指標監控界面，包括投資組合總覽、風險指標卡片、
    VaR 分析和風險視覺化圖表。

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示風險指標儀表板
        - 可能從風險管理服務獲取實時數據
    """
    st.subheader("📊 風險指標監控")

    # 獲取風險管理服務
    risk_service = get_risk_management_service()

    # 獲取風險指標數據
    if risk_service:
        try:
            # 嘗試從服務層獲取實際風險指標
            calculated_metrics = risk_service.calculate_risk_metrics()
            if calculated_metrics:
                # 將計算結果轉換為顯示格式
                risk_metrics = {
                    "portfolio_value": 1000000,  # 這應該從投資組合服務獲取
                    "cash_amount": 150000,
                    "invested_amount": 850000,
                    "current_positions": 8,
                    "daily_pnl": np.random.normal(1200, 8000),
                    "daily_pnl_percent": np.random.normal(0.12, 0.8),
                    **calculated_metrics,
                }
            else:
                risk_metrics = get_mock_risk_metrics()
        except Exception as e:
            st.warning(f"無法獲取實際風險指標，使用模擬數據: {e}")
            risk_metrics = get_mock_risk_metrics()
    else:
        risk_metrics = get_mock_risk_metrics()

    # 顯示各個部分
    _show_portfolio_overview(risk_metrics)
    _show_risk_metrics_cards(risk_metrics)
    _show_risk_visualizations(risk_metrics)


def _show_portfolio_overview(risk_metrics: Dict[str, Any]) -> None:
    """顯示投資組合總覽儀表板。

    展示投資組合的核心指標，包括總價值、現金部位、投資部位、
    持倉數量和當日損益等關鍵資訊。

    Args:
        risk_metrics (Dict[str, Any]): 風險指標字典，包含以下鍵值：
            - portfolio_value (float): 投資組合總價值
            - cash_amount (float): 現金部位金額
            - invested_amount (float): 投資部位金額
            - current_positions (int): 當前持倉數量
            - daily_pnl (float): 當日損益金額
            - daily_pnl_percent (float): 當日損益百分比

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示 5 個指標卡片
        - 計算並顯示現金比例和投資比例

    Example:
        >>> metrics = {
        ...     "portfolio_value": 1000000,
        ...     "cash_amount": 150000,
        ...     "invested_amount": 850000,
        ...     "current_positions": 8,
        ...     "daily_pnl": 5000,
        ...     "daily_pnl_percent": 0.5
        ... }
        >>> _show_portfolio_overview(metrics)
    """
    st.write("### 📈 投資組合總覽")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "投資組合價值",
            format_currency(risk_metrics["portfolio_value"]),
            f"{risk_metrics['daily_pnl']:+,.0f}",
        )

    with col2:
        cash_ratio = risk_metrics["cash_amount"] / risk_metrics["portfolio_value"] * 100
        st.metric(
            "現金部位",
            format_currency(risk_metrics["cash_amount"]),
            f"{cash_ratio:.1f}%",
        )

    with col3:
        invested_ratio = (
            risk_metrics["invested_amount"] / risk_metrics["portfolio_value"] * 100
        )
        st.metric(
            "投資部位",
            format_currency(risk_metrics["invested_amount"]),
            f"{invested_ratio:.1f}%",
        )

    with col4:
        st.metric("持倉數量", f"{risk_metrics['current_positions']}", "")

    with col5:
        st.metric(
            "今日損益",
            f"{risk_metrics['daily_pnl_percent']:+.2f}%",
            format_currency(risk_metrics["daily_pnl"]),
        )


def _show_risk_metrics_cards(risk_metrics: Dict[str, Any]) -> None:
    """顯示風險指標卡片"""
    st.divider()

    # 風險指標
    col1, col2 = st.columns(2)

    with col1:
        st.write("### 🎯 風險指標")

        # VaR 指標
        st.write("**風險值 (VaR)**")
        col_var1, col_var2 = st.columns(2)

        with col_var1:
            st.metric("95% VaR (1日)", format_currency(risk_metrics["var_95_1day"]))
            st.metric("95% CVaR (1日)", format_currency(risk_metrics["cvar_95_1day"]))

        with col_var2:
            var_pct = (
                risk_metrics["var_95_1day"] / risk_metrics["portfolio_value"] * 100
            )
            cvar_pct = (
                risk_metrics["cvar_95_1day"] / risk_metrics["portfolio_value"] * 100
            )
            st.metric("VaR 比例", f"{var_pct:.2f}%")
            st.metric("CVaR 比例", f"{cvar_pct:.2f}%")

        # 回撤指標
        st.write("**回撤分析**")
        col_dd1, col_dd2 = st.columns(2)

        with col_dd1:
            st.metric("最大回撤", f"{risk_metrics['max_drawdown']:.2f}%")
            st.metric("當前回撤", f"{risk_metrics['current_drawdown']:.2f}%")

        with col_dd2:
            # 回撤狀態指示
            if abs(risk_metrics["current_drawdown"]) > 10:
                st.error("⚠️ 回撤過大")
            elif abs(risk_metrics["current_drawdown"]) > 5:
                st.warning("⚠️ 回撤警告")
            else:
                st.success("✅ 回撤正常")

        # 其他風險指標
        st.write("**其他指標**")
        col_other1, col_other2 = st.columns(2)

        with col_other1:
            st.metric("年化波動率", f"{risk_metrics['volatility']:.2f}%")
            st.metric("夏普比率", f"{risk_metrics['sharpe_ratio']:.2f}")
            st.metric("Beta 係數", f"{risk_metrics['beta']:.2f}")

        with col_other2:
            st.metric("市場相關性", f"{risk_metrics['correlation_with_market']:.2f}")
            st.metric("追蹤誤差", f"{risk_metrics['tracking_error']:.2f}%")
            st.metric("平均相關性", f"{risk_metrics['avg_correlation']:.2f}")

    with col2:
        _show_risk_charts(risk_metrics)


def _show_risk_charts(risk_metrics: Dict[str, Any]) -> None:
    """顯示風險圖表"""
    st.write("### 📊 風險視覺化")

    # 回撤走勢圖
    st.write("**回撤走勢**")
    fig_drawdown = go.Figure()

    fig_drawdown.add_trace(
        go.Scatter(
            x=risk_metrics["dates"],
            y=risk_metrics["drawdown_series"],
            mode="lines",
            name="回撤",
            fill="tonexty",
            line=dict(color="red", width=2),
        )
    )

    fig_drawdown.update_layout(
        title="投資組合回撤走勢",
        xaxis_title="日期",
        yaxis_title="回撤 (%)",
        template="plotly_white",
        height=300,
    )

    st.plotly_chart(fig_drawdown, use_container_width=True)

    # 收益率分布
    st.write("**收益率分布**")
    fig_hist = go.Figure()

    fig_hist.add_trace(
        go.Histogram(
            x=risk_metrics["returns_series"] * 100,
            nbinsx=30,
            name="收益率分布",
            marker_color="blue",
            opacity=0.7,
        )
    )

    # 添加 VaR 線
    var_line = np.percentile(risk_metrics["returns_series"], 5) * 100
    fig_hist.add_vline(
        x=var_line,
        line_dash="dash",
        line_color="red",
        annotation_text=f"95% VaR: {var_line:.2f}%",
    )

    fig_hist.update_layout(
        title="日收益率分布",
        xaxis_title="收益率 (%)",
        yaxis_title="頻率",
        template="plotly_white",
        height=300,
    )

    st.plotly_chart(fig_hist, use_container_width=True)


def _show_risk_visualizations(risk_metrics: Dict[str, Any]) -> None:
    """顯示額外的風險視覺化"""
    st.divider()
    st.write("### 📈 風險分析圖表")

    col1, col2 = st.columns(2)

    with col1:
        # 風險分解圖
        st.write("**風險分解**")
        risk_components = {
            "市場風險": 45,
            "信用風險": 25,
            "流動性風險": 15,
            "操作風險": 10,
            "其他風險": 5,
        }

        fig_pie = go.Figure(
            data=[
                go.Pie(
                    labels=list(risk_components.keys()),
                    values=list(risk_components.values()),
                    hole=0.3,
                )
            ]
        )

        fig_pie.update_layout(
            title="風險分解",
            height=300,
        )

        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        # 風險趨勢
        st.write("**風險趨勢**")
        dates = risk_metrics["dates"][-30:]  # 最近30天
        var_trend = np.random.uniform(0.02, 0.05, 30)

        fig_trend = go.Figure()
        fig_trend.add_trace(
            go.Scatter(
                x=dates,
                y=var_trend * 100,
                mode="lines+markers",
                name="VaR 趨勢",
                line=dict(color="orange", width=2),
            )
        )

        fig_trend.update_layout(
            title="VaR 趨勢 (30天)",
            xaxis_title="日期",
            yaxis_title="VaR (%)",
            template="plotly_white",
            height=300,
        )

        st.plotly_chart(fig_trend, use_container_width=True)


def show_risk_summary() -> None:
    """顯示風險摘要

    提供簡化的風險指標摘要，適用於儀表板概覽。

    Returns:
        None
    """
    risk_metrics = get_mock_risk_metrics()

    # 計算風險評分
    risk_score = 100
    if abs(risk_metrics.get("current_drawdown", 0)) > 10:
        risk_score -= 30
    elif abs(risk_metrics.get("current_drawdown", 0)) > 5:
        risk_score -= 15

    if (
        risk_metrics.get("var_95_1day", 0) / risk_metrics.get("portfolio_value", 1)
        > 0.03
    ):
        risk_score -= 20

    # 風險等級
    if risk_score >= 80:
        risk_level = "低風險"
        risk_color = "🟢"
    elif risk_score >= 60:
        risk_level = "中等風險"
        risk_color = "🟡"
    else:
        risk_level = "高風險"
        risk_color = "🔴"

    st.metric("風險評分", f"{risk_score}/100", f"{risk_color} {risk_level}")
