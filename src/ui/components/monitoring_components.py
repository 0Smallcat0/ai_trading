"""
系統監控組件

此模組提供系統監控的各種組件，包括：
- 系統資源監控組件
- 交易效能追蹤組件
- 日誌管理組件
- 警報系統組件
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import psutil
import time

# 導入響應式設計組件
from ..responsive import ResponsiveComponents, responsive_manager


class MonitoringComponents:
    """系統監控組件類"""

    @staticmethod
    def system_resources_dashboard(resource_data: Dict[str, Any]) -> None:
        """
        系統資源監控儀表板

        Args:
            resource_data: 系統資源數據
        """
        # 基本資源指標
        resource_metrics = [
            {
                "title": "CPU 使用率",
                "value": f"{resource_data.get('cpu_percent', 0):.1f}%",
                "status": MonitoringComponents._get_resource_status(
                    resource_data.get("cpu_percent", 0), 80, 90
                ),
                "icon": "🖥️",
            },
            {
                "title": "記憶體使用率",
                "value": f"{resource_data.get('memory_percent', 0):.1f}%",
                "status": MonitoringComponents._get_resource_status(
                    resource_data.get("memory_percent", 0), 80, 90
                ),
                "icon": "💾",
            },
            {
                "title": "磁碟使用率",
                "value": f"{resource_data.get('disk_percent', 0):.1f}%",
                "status": MonitoringComponents._get_resource_status(
                    resource_data.get("disk_percent", 0), 85, 95
                ),
                "icon": "💿",
            },
            {
                "title": "網路延遲",
                "value": f"{resource_data.get('network_latency', 0):.0f}ms",
                "status": MonitoringComponents._get_latency_status(
                    resource_data.get("network_latency", 0)
                ),
                "icon": "🌐",
            },
        ]

        ResponsiveComponents.responsive_metric_cards(
            resource_metrics, desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

        # 詳細資源資訊
        st.subheader("詳細資源資訊")

        detailed_metrics = [
            {
                "title": "可用記憶體",
                "value": f"{resource_data.get('memory_available', 0) / 1024**3:.1f} GB",
                "status": "normal",
                "icon": "📊",
            },
            {
                "title": "磁碟可用空間",
                "value": f"{resource_data.get('disk_free', 0) / 1024**3:.1f} GB",
                "status": "normal",
                "icon": "💽",
            },
            {
                "title": "網路上傳",
                "value": f"{resource_data.get('network_sent', 0) / 1024**2:.1f} MB/s",
                "status": "normal",
                "icon": "📤",
            },
            {
                "title": "網路下載",
                "value": f"{resource_data.get('network_recv', 0) / 1024**2:.1f} MB/s",
                "status": "normal",
                "icon": "📥",
            },
        ]

        ResponsiveComponents.responsive_metric_cards(
            detailed_metrics, desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

    @staticmethod
    def _get_resource_status(
        value: float, warning_threshold: float, error_threshold: float
    ) -> str:
        """獲取資源狀態"""
        if value >= error_threshold:
            return "error"
        elif value >= warning_threshold:
            return "warning"
        else:
            return "success"

    @staticmethod
    def _get_latency_status(latency: float) -> str:
        """獲取延遲狀態"""
        if latency > 100:
            return "error"
        elif latency > 50:
            return "warning"
        else:
            return "success"

    @staticmethod
    def performance_tracking_dashboard(performance_data: Dict[str, Any]) -> None:
        """
        交易效能追蹤儀表板

        Args:
            performance_data: 效能數據
        """
        # 效能指標
        perf_metrics = [
            {
                "title": "訂單延遲",
                "value": f"{performance_data.get('order_latency', 0):.1f}ms",
                "status": MonitoringComponents._get_latency_status(
                    performance_data.get("order_latency", 0)
                ),
                "icon": "⚡",
            },
            {
                "title": "成交率",
                "value": f"{performance_data.get('fill_rate', 0):.1f}%",
                "status": (
                    "success"
                    if performance_data.get("fill_rate", 0) > 95
                    else "warning"
                ),
                "icon": "🎯",
            },
            {
                "title": "系統吞吐量",
                "value": f"{performance_data.get('throughput', 0):.0f} TPS",
                "status": (
                    "success"
                    if performance_data.get("throughput", 0) > 100
                    else "warning"
                ),
                "icon": "🚀",
            },
            {
                "title": "API 回應時間",
                "value": f"{performance_data.get('api_response_time', 0):.0f}ms",
                "status": MonitoringComponents._get_latency_status(
                    performance_data.get("api_response_time", 0)
                ),
                "icon": "🔗",
            },
        ]

        ResponsiveComponents.responsive_metric_cards(
            perf_metrics, desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

        # 效能趨勢圖表
        MonitoringComponents._render_performance_charts(performance_data)

    @staticmethod
    def _render_performance_charts(performance_data: Dict[str, Any]) -> None:
        """渲染效能圖表"""
        # 使用響應式列佈局
        cols = responsive_manager.create_responsive_columns(
            desktop_cols=2, tablet_cols=1, mobile_cols=1
        )

        with cols[0]:
            # 延遲趨勢圖
            MonitoringComponents._render_latency_trend()

        with cols[1 % len(cols)]:
            # 吞吐量趨勢圖
            MonitoringComponents._render_throughput_trend()

    @staticmethod
    def _render_latency_trend() -> None:
        """渲染延遲趨勢圖"""
        # 生成模擬延遲數據
        times = pd.date_range(end=datetime.now(), periods=60, freq="T")
        latencies = np.random.normal(25, 10, 60)
        latencies = np.clip(latencies, 5, 100)  # 限制在合理範圍內

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=times,
                y=latencies,
                mode="lines+markers",
                name="訂單延遲",
                line=dict(color="blue", width=2),
                marker=dict(size=4),
            )
        )

        # 添加警戒線
        fig.add_hline(
            y=50, line_dash="dash", line_color="orange", annotation_text="警告線 (50ms)"
        )
        fig.add_hline(
            y=100, line_dash="dash", line_color="red", annotation_text="危險線 (100ms)"
        )

        height = responsive_manager.get_chart_height(300)
        fig.update_layout(
            title="訂單延遲趨勢",
            xaxis_title="時間",
            yaxis_title="延遲 (ms)",
            height=height,
            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def _render_throughput_trend() -> None:
        """渲染吞吐量趨勢圖"""
        # 生成模擬吞吐量數據
        times = pd.date_range(end=datetime.now(), periods=60, freq="T")
        throughput = np.random.normal(150, 30, 60)
        throughput = np.clip(throughput, 50, 300)  # 限制在合理範圍內

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=times,
                y=throughput,
                mode="lines+markers",
                name="系統吞吐量",
                line=dict(color="green", width=2),
                marker=dict(size=4),
                fill="tonexty",
            )
        )

        height = responsive_manager.get_chart_height(300)
        fig.update_layout(
            title="系統吞吐量趨勢",
            xaxis_title="時間",
            yaxis_title="吞吐量 (TPS)",
            height=height,
            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def log_management_panel(logs: List[Dict[str, Any]]) -> None:
        """
        日誌管理面板

        Args:
            logs: 日誌列表
        """
        if not logs:
            st.info("沒有日誌記錄")
            return

        # 日誌統計
        log_stats = MonitoringComponents._calculate_log_stats(logs)

        stats_metrics = [
            {
                "title": "總日誌數",
                "value": str(log_stats["total_logs"]),
                "status": "normal",
                "icon": "📝",
            },
            {
                "title": "錯誤日誌",
                "value": str(log_stats["error_logs"]),
                "status": "error" if log_stats["error_logs"] > 0 else "success",
                "icon": "❌",
            },
            {
                "title": "警告日誌",
                "value": str(log_stats["warning_logs"]),
                "status": "warning" if log_stats["warning_logs"] > 0 else "success",
                "icon": "⚠️",
            },
            {
                "title": "今日新增",
                "value": str(log_stats["today_logs"]),
                "status": "normal",
                "icon": "📅",
            },
        ]

        ResponsiveComponents.responsive_metric_cards(
            stats_metrics, desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

        # 日誌篩選
        st.subheader("日誌篩選")

        cols = responsive_manager.create_responsive_columns(
            desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

        with cols[0]:
            level_filter = st.selectbox(
                "日誌等級", ["全部", "INFO", "WARNING", "ERROR", "DEBUG"]
            )

        with cols[1 % len(cols)]:
            module_filter = st.selectbox(
                "模組", ["全部", "trading", "risk", "data", "api"]
            )

        with cols[2 % len(cols)]:
            start_time = st.time_input(
                "開始時間", datetime.now().replace(hour=0, minute=0)
            )

        with cols[3 % len(cols)]:
            end_time = st.time_input("結束時間", datetime.now())

        # 篩選日誌
        filtered_logs = MonitoringComponents._filter_logs(
            logs, level_filter, module_filter, start_time, end_time
        )

        # 日誌表格
        st.subheader("日誌記錄")

        if filtered_logs:
            df = pd.DataFrame(filtered_logs)

            # 添加顏色標記
            def style_log_level(val):
                if val == "ERROR":
                    return "background-color: #f8d7da"
                elif val == "WARNING":
                    return "background-color: #fff3cd"
                elif val == "INFO":
                    return "background-color: #d4edda"
                return ""

            if "level" in df.columns:
                styled_df = df.style.applymap(style_log_level, subset=["level"])
                ResponsiveComponents.responsive_dataframe(styled_df, title="系統日誌")
            else:
                ResponsiveComponents.responsive_dataframe(df, title="系統日誌")
        else:
            st.info("沒有符合條件的日誌")

    @staticmethod
    def _calculate_log_stats(logs: List[Dict[str, Any]]) -> Dict[str, int]:
        """計算日誌統計"""
        stats = {
            "total_logs": len(logs),
            "error_logs": 0,
            "warning_logs": 0,
            "today_logs": 0,
        }

        today = datetime.now().strftime("%Y-%m-%d")

        for log in logs:
            level = log.get("level", "")
            timestamp = log.get("timestamp", "")

            if level == "ERROR":
                stats["error_logs"] += 1
            elif level == "WARNING":
                stats["warning_logs"] += 1

            if timestamp.startswith(today):
                stats["today_logs"] += 1

        return stats

    @staticmethod
    def _filter_logs(
        logs: List[Dict[str, Any]],
        level_filter: str,
        module_filter: str,
        start_time: time,
        end_time: time,
    ) -> List[Dict[str, Any]]:
        """篩選日誌"""
        filtered = logs.copy()

        # 等級篩選
        if level_filter != "全部":
            filtered = [log for log in filtered if log.get("level") == level_filter]

        # 模組篩選
        if module_filter != "全部":
            filtered = [log for log in filtered if log.get("module") == module_filter]

        # 時間篩選（簡化實作）
        # 實際應用中需要更複雜的時間解析

        return filtered

    @staticmethod
    def alert_system_panel(alerts: List[Dict[str, Any]]) -> None:
        """
        警報系統面板

        Args:
            alerts: 警報列表
        """
        if not alerts:
            st.info("沒有系統警報")
            return

        # 警報統計
        alert_stats = MonitoringComponents._calculate_alert_stats(alerts)

        stats_metrics = [
            {
                "title": "總警報數",
                "value": str(alert_stats["total_alerts"]),
                "status": "normal",
                "icon": "🚨",
            },
            {
                "title": "嚴重警報",
                "value": str(alert_stats["critical_alerts"]),
                "status": "error" if alert_stats["critical_alerts"] > 0 else "success",
                "icon": "🔴",
            },
            {
                "title": "未確認",
                "value": str(alert_stats["unacknowledged_alerts"]),
                "status": (
                    "warning" if alert_stats["unacknowledged_alerts"] > 0 else "success"
                ),
                "icon": "⏳",
            },
            {
                "title": "已解決",
                "value": str(alert_stats["resolved_alerts"]),
                "status": "success",
                "icon": "✅",
            },
        ]

        ResponsiveComponents.responsive_metric_cards(
            stats_metrics, desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

        # 警報列表
        st.subheader("警報詳情")

        df = pd.DataFrame(alerts)
        if not df.empty:
            ResponsiveComponents.responsive_dataframe(df, title="系統警報")

        # 警報操作
        if alerts:
            st.subheader("警報操作")

            cols = responsive_manager.create_responsive_columns(
                desktop_cols=3, tablet_cols=2, mobile_cols=1
            )

            with cols[0]:
                if st.button("✅ 確認所有警報", use_container_width=True):
                    st.success("所有警報已確認")

            with cols[1 % len(cols)]:
                if st.button("🔕 靜音警報", use_container_width=True):
                    st.info("警報已靜音")

            with cols[2 % len(cols)]:
                if st.button("🗑️ 清除已解決", use_container_width=True):
                    st.success("已解決的警報已清除")

    @staticmethod
    def _calculate_alert_stats(alerts: List[Dict[str, Any]]) -> Dict[str, int]:
        """計算警報統計"""
        stats = {
            "total_alerts": len(alerts),
            "critical_alerts": 0,
            "unacknowledged_alerts": 0,
            "resolved_alerts": 0,
        }

        for alert in alerts:
            severity = alert.get("severity", "")
            status = alert.get("status", "")
            acknowledged = alert.get("acknowledged", False)

            if severity == "critical":
                stats["critical_alerts"] += 1

            if not acknowledged:
                stats["unacknowledged_alerts"] += 1

            if status == "resolved":
                stats["resolved_alerts"] += 1

        return stats

    @staticmethod
    def health_report_generator(system_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成系統健康度報告

        Args:
            system_data: 系統數據

        Returns:
            健康度報告
        """
        # 計算健康度評分
        health_score = MonitoringComponents._calculate_health_score(system_data)

        # 生成建議
        recommendations = MonitoringComponents._generate_recommendations(system_data)

        # 系統狀態
        if health_score >= 90:
            status = "優秀"
            status_color = "success"
        elif health_score >= 70:
            status = "良好"
            status_color = "warning"
        else:
            status = "需要關注"
            status_color = "error"

        return {
            "health_score": health_score,
            "status": status,
            "status_color": status_color,
            "recommendations": recommendations,
            "generated_at": datetime.now().isoformat(),
        }

    @staticmethod
    def _calculate_health_score(system_data: Dict[str, Any]) -> int:
        """計算系統健康度評分"""
        score = 100

        # CPU 使用率影響
        cpu_usage = system_data.get("cpu_percent", 0)
        if cpu_usage > 90:
            score -= 20
        elif cpu_usage > 80:
            score -= 10

        # 記憶體使用率影響
        memory_usage = system_data.get("memory_percent", 0)
        if memory_usage > 90:
            score -= 20
        elif memory_usage > 80:
            score -= 10

        # 網路延遲影響
        latency = system_data.get("network_latency", 0)
        if latency > 100:
            score -= 15
        elif latency > 50:
            score -= 5

        # 錯誤率影響
        error_rate = system_data.get("error_rate", 0)
        if error_rate > 5:
            score -= 25
        elif error_rate > 1:
            score -= 10

        return max(0, score)

    @staticmethod
    def _generate_recommendations(system_data: Dict[str, Any]) -> List[str]:
        """生成系統優化建議"""
        recommendations = []

        cpu_usage = system_data.get("cpu_percent", 0)
        memory_usage = system_data.get("memory_percent", 0)
        latency = system_data.get("network_latency", 0)

        if cpu_usage > 80:
            recommendations.append("CPU 使用率過高，建議優化計算密集型任務")

        if memory_usage > 80:
            recommendations.append("記憶體使用率過高，建議清理緩存或增加記憶體")

        if latency > 50:
            recommendations.append("網路延遲較高，建議檢查網路連接或優化 API 調用")

        if not recommendations:
            recommendations.append("系統運行良好，繼續保持")

        return recommendations
