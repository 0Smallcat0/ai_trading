"""風險管理組件

此模組提供風險管理系統的各種組件，包括：
- 風險參數設定組件
- 實時風險監控組件
- 風險控制機制組件
- 警報管理組件
"""

from datetime import datetime
from typing import Dict, List, Optional, Any

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# 導入響應式設計組件
from ..responsive import ResponsiveComponents, responsive_manager


class RiskComponents:
    """風險管理組件類"""

    @staticmethod
    def risk_parameter_form(
        current_params: Dict[str, Any], form_key: str = "risk_params_form"
    ) -> Optional[Dict[str, Any]]:
        """風險參數設定表單

        Args:
            current_params: 當前風險參數
            form_key: 表單鍵值

        Returns:
            Optional[Dict[str, Any]]: 更新後的參數字典，如果未提交則返回 None
        """
        form_config = {
            "title": "風險參數設定",
            "fields": [
                {
                    "key": "stop_loss_type",
                    "label": "停損類型",
                    "type": "select",
                    "options": ["percent", "atr", "trailing", "support_resistance"],
                    "default": current_params.get("stop_loss_type", "percent"),
                },
                {
                    "key": "stop_loss_value",
                    "label": "停損值 (%)",
                    "type": "number",
                    "default": current_params.get("stop_loss_value", 5.0),
                },
                {
                    "key": "take_profit_type",
                    "label": "停利類型",
                    "type": "select",
                    "options": ["percent", "target", "risk_reward", "trailing"],
                    "default": current_params.get("take_profit_type", "percent"),
                },
                {
                    "key": "take_profit_value",
                    "label": "停利值 (%)",
                    "type": "number",
                    "default": current_params.get("take_profit_value", 10.0),
                },
                {
                    "key": "max_position_size",
                    "label": "最大單一部位比例 (%)",
                    "type": "number",
                    "default": current_params.get("max_position_size", 10.0),
                },
                {
                    "key": "max_portfolio_risk",
                    "label": "最大投資組合風險 (%)",
                    "type": "number",
                    "default": current_params.get("max_portfolio_risk", 2.0),
                },
                {
                    "key": "var_confidence_level",
                    "label": "VaR 信心水準 (%)",
                    "type": "number",
                    "default": current_params.get("var_confidence_level", 95.0),
                },
                {
                    "key": "max_correlation",
                    "label": "最大相關性",
                    "type": "number",
                    "default": current_params.get("max_correlation", 0.7),
                },
            ],
        }

        return ResponsiveComponents.responsive_form(form_config, form_key)

    @staticmethod
    def risk_metrics_dashboard(risk_metrics: Dict[str, Any]) -> None:
        """
        風險指標儀表板

        Args:
            risk_metrics: 風險指標數據
        """
        # 基本風險指標卡片
        basic_metrics = [
            {
                "title": "投資組合價值",
                "value": f"${risk_metrics.get('portfolio_value', 0):,.0f}",
                "status": "normal",
                "icon": "💰",
            },
            {
                "title": "當前回撤",
                "value": f"{risk_metrics.get('current_drawdown', 0):.2%}",
                "status": (
                    "error"
                    if risk_metrics.get("current_drawdown", 0) < -0.1
                    else (
                        "warning"
                        if risk_metrics.get("current_drawdown", 0) < -0.05
                        else "success"
                    )
                ),
                "icon": "📉",
            },
            {
                "title": "VaR (95%)",
                "value": "${:,.0f}".format(
                    abs(
                        risk_metrics.get("var_95", 0)
                        * risk_metrics.get("portfolio_value", 0)
                    )
                ),
                "status": (
                    "warning"
                    if abs(risk_metrics.get("var_95", 0)) > 0.03
                    else "success"
                ),
                "icon": "⚠️",
            },
            {
                "title": "夏普比率",
                "value": f"{risk_metrics.get('sharpe_ratio', 0):.2f}",
                "status": (
                    "success"
                    if risk_metrics.get("sharpe_ratio", 0) > 1.0
                    else "warning"
                ),
                "icon": "📊",
            },
        ]

        ResponsiveComponents.responsive_metric_cards(
            basic_metrics, desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

        # 詳細風險指標
        st.subheader("詳細風險指標")

        detailed_metrics = [
            {
                "title": "波動率",
                "value": f"{risk_metrics.get('volatility', 0):.2%}",
                "status": "normal",
                "icon": "📈",
            },
            {
                "title": "最大回撤",
                "value": f"{risk_metrics.get('max_drawdown', 0):.2%}",
                "status": (
                    "error"
                    if risk_metrics.get("max_drawdown", 0) < -0.15
                    else "warning"
                ),
                "icon": "📉",
            },
            {
                "title": "集中度風險",
                "value": f"{risk_metrics.get('concentration_risk', 0):.1%}",
                "status": (
                    "warning"
                    if risk_metrics.get("concentration_risk", 0) > 0.3
                    else "success"
                ),
                "icon": "🎯",
            },
            {
                "title": "平均相關性",
                "value": f"{risk_metrics.get('avg_correlation', 0):.2f}",
                "status": (
                    "warning"
                    if risk_metrics.get("avg_correlation", 0) > 0.7
                    else "success"
                ),
                "icon": "🔗",
            },
        ]

        ResponsiveComponents.responsive_metric_cards(
            detailed_metrics, desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

    @staticmethod
    def risk_monitoring_charts(risk_data: Dict[str, Any]) -> None:
        """
        風險監控圖表

        Args:
            risk_data: 風險數據
        """
        # 使用響應式列佈局
        cols = responsive_manager.create_responsive_columns(
            desktop_cols=2, tablet_cols=1, mobile_cols=1
        )

        with cols[0]:
            # VaR 趨勢圖
            RiskComponents._render_var_trend_chart(risk_data)

        with cols[1 % len(cols)]:
            # 回撤分析圖
            RiskComponents._render_drawdown_chart(risk_data)

        # 第二行圖表
        cols2 = responsive_manager.create_responsive_columns(
            desktop_cols=2, tablet_cols=1, mobile_cols=1
        )

        with cols2[0]:
            # 行業曝險圖
            RiskComponents._render_sector_exposure_chart(risk_data)

        with cols2[1 % len(cols2)]:
            # 相關性熱力圖
            RiskComponents._render_correlation_heatmap(risk_data)

    @staticmethod
    def _render_var_trend_chart(
        risk_data: Dict[str, Any]
    ) -> None:  # pylint: disable=unused-argument
        """渲染 VaR 趨勢圖"""
        # 生成模擬 VaR 數據
        dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
        var_95 = np.random.uniform(0.02, 0.05, 30)
        var_99 = var_95 * 1.5

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=dates,
                y=var_95 * 100,
                mode="lines",
                name="VaR 95%",
                line={"color": "orange", "width": 2},
            )
        )

        fig.add_trace(
            go.Scatter(
                x=dates,
                y=var_99 * 100,
                mode="lines",
                name="VaR 99%",
                line={"color": "red", "width": 2},
            )
        )

        # 添加警戒線
        fig.add_hline(
            y=3.0, line_dash="dash", line_color="red", annotation_text="警戒線 (3%)"
        )

        height = responsive_manager.get_chart_height(350)
        fig.update_layout(
            title="VaR 趨勢分析",
            xaxis_title="日期",
            yaxis_title="VaR (%)",
            height=height,
            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def _render_drawdown_chart(
        risk_data: Dict[str, Any]
    ) -> None:  # pylint: disable=unused-argument
        """渲染回撤分析圖"""
        # 生成模擬回撤數據
        dates = pd.date_range(end=datetime.now(), periods=252, freq="D")
        returns = np.random.normal(0.0008, 0.015, 252)
        cumulative_returns = np.cumprod(1 + returns)
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns / peak - 1) * 100

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=dates,
                y=drawdown,
                mode="lines",
                fill="tonexty",
                name="回撤",
                line={"color": "red", "width": 1},
                fillcolor="rgba(255, 0, 0, 0.3)",
            )
        )

        # 標記最大回撤
        max_dd_idx = np.argmin(drawdown)
        fig.add_annotation(
            x=dates[max_dd_idx],
            y=drawdown[max_dd_idx],
            text=f"最大回撤: {drawdown[max_dd_idx]:.2f}%",
            showarrow=True,
            arrowhead=2,
            arrowcolor="red",
        )

        height = responsive_manager.get_chart_height(350)
        fig.update_layout(
            title="回撤分析",
            xaxis_title="日期",
            yaxis_title="回撤 (%)",
            height=height,
            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def _render_sector_exposure_chart(
        risk_data: Dict[str, Any]
    ) -> None:  # pylint: disable=unused-argument
        """渲染行業曝險圖"""
        # 模擬行業曝險數據
        sectors = ["科技", "金融", "醫療", "消費", "能源", "工業"]
        exposures = [35, 25, 15, 15, 5, 5]

        fig = px.pie(values=exposures, names=sectors, title="行業曝險分佈")

        height = responsive_manager.get_chart_height(350)
        fig.update_layout(height=height)

        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def _render_correlation_heatmap(
        risk_data: Dict[str, Any]
    ) -> None:  # pylint: disable=unused-argument
        """渲染相關性熱力圖"""
        # 模擬相關性矩陣
        symbols = ["2330.TW", "2317.TW", "2454.TW", "AAPL", "MSFT"]
        correlation_matrix = np.random.uniform(0.3, 0.9, (5, 5))
        np.fill_diagonal(correlation_matrix, 1.0)

        fig = px.imshow(
            correlation_matrix,
            x=symbols,
            y=symbols,
            color_continuous_scale="RdYlBu_r",
            title="持倉相關性分析",
        )

        height = responsive_manager.get_chart_height(350)
        fig.update_layout(height=height)

        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def risk_control_panel(
        control_status: Dict[str, Any]
    ) -> None:  # pylint: disable=unused-argument
        """
        風險控制面板

        Args:
            control_status: 風控機制狀態
        """
        st.subheader("風險控制機制")

        # 風控機制狀態
        controls = [
            {
                "name": "停損機制",
                "enabled": True,
                "status": "正常",
                "last_triggered": "2024-01-10",
            },
            {
                "name": "部位限制",
                "enabled": True,
                "status": "正常",
                "last_triggered": "從未",
            },
            {
                "name": "VaR 監控",
                "enabled": True,
                "status": "警告",
                "last_triggered": "2024-01-14",
            },
            {
                "name": "回撤保護",
                "enabled": True,
                "status": "正常",
                "last_triggered": "2024-01-12",
            },
            {
                "name": "相關性檢查",
                "enabled": False,
                "status": "停用",
                "last_triggered": "從未",
            },
            {
                "name": "緊急停止",
                "enabled": True,
                "status": "待命",
                "last_triggered": "從未",
            },
        ]

        # 使用響應式表格顯示
        df = pd.DataFrame(controls)
        ResponsiveComponents.responsive_dataframe(df, title="風控機制狀態")

        # 控制按鈕
        st.subheader("快速控制")

        cols = responsive_manager.create_responsive_columns(
            desktop_cols=3, tablet_cols=2, mobile_cols=1
        )

        with cols[0]:
            if st.button(
                "🛑 緊急停止所有交易", type="primary", use_container_width=True
            ):
                st.warning("緊急停止功能已觸發！")

        with cols[1 % len(cols)]:
            if st.button("⚠️ 啟用保守模式", use_container_width=True):
                st.info("保守模式已啟用")

        with cols[2 % len(cols)]:
            if st.button("🔄 重置風控狀態", use_container_width=True):
                st.success("風控狀態已重置")

    @staticmethod
    def risk_alerts_panel(alerts: List[Dict[str, Any]]) -> None:
        """
        風險警報面板

        Args:
            alerts: 警報列表
        """
        st.subheader("風險警報")

        if not alerts:
            st.info("目前沒有風險警報")
            return

        # 警報統計
        alert_stats = [
            {
                "title": "總警報數",
                "value": str(len(alerts)),
                "status": "normal",
                "icon": "🚨",
            },
            {
                "title": "高嚴重度",
                "value": str(sum(1 for a in alerts if a.get("severity") == "高")),
                "status": "error",
                "icon": "🔴",
            },
            {
                "title": "未處理",
                "value": str(
                    sum(1 for a in alerts if not a.get("acknowledged", False))
                ),
                "status": "warning",
                "icon": "⏳",
            },
            {
                "title": "今日新增",
                "value": str(
                    sum(
                        1
                        for a in alerts
                        if a.get("created_at", "").startswith(
                            datetime.now().strftime("%Y-%m-%d")
                        )
                    )
                ),
                "status": "normal",
                "icon": "📅",
            },
        ]

        ResponsiveComponents.responsive_metric_cards(
            alert_stats, desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

        # 警報列表
        st.subheader("警報詳情")

        # 轉換為 DataFrame 並使用響應式表格
        df = pd.DataFrame(alerts)
        if not df.empty:
            # 重新排序列
            column_order = [
                "created_at",
                "alert_type",
                "severity",
                "title",
                "symbol",
                "status",
            ]
            df = df.reindex(columns=[col for col in column_order if col in df.columns])

            ResponsiveComponents.responsive_dataframe(df, title="警報記錄")

        # 批量操作
        if len(alerts) > 0:
            st.subheader("批量操作")

            cols = responsive_manager.create_responsive_columns(
                desktop_cols=2, tablet_cols=1, mobile_cols=1
            )

            with cols[0]:
                if st.button("✅ 確認所有警報", use_container_width=True):
                    st.success("所有警報已確認")

            with cols[1 % len(cols)]:
                if st.button("🗑️ 清除已解決警報", use_container_width=True):
                    st.success("已解決的警報已清除")
