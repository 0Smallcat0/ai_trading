#!/usr/bin/env python3
"""
高級監控頁面
提供詳細日誌記錄、性能監控、異常追蹤的Web界面
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import os
import sys

# 添加項目根目錄到路徑
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from src.ui.themes.modern_theme_manager import apply_modern_theme
from src.core.advanced_monitoring_service import (
    AdvancedMonitoringService,
    LogLevel,
    AlertType
)

def initialize_monitoring_service():
    """初始化監控服務"""
    if "monitoring_service" not in st.session_state:
        try:
            st.session_state.monitoring_service = AdvancedMonitoringService()
            st.session_state.monitoring_service.start_monitoring()
        except Exception as e:
            st.error(f"監控服務初始化失敗: {e}")
            return None
    
    return st.session_state.monitoring_service

def show_system_health(monitoring_service, theme_manager):
    """顯示系統健康狀態"""
    st.subheader("🏥 系統健康狀態")
    
    health_data = monitoring_service.get_system_health()
    
    # 健康分數顯示
    health_score = health_data["health_score"]
    status = health_data["status"]
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # 健康分數
        score_color = "#28a745" if health_score >= 80 else "#ffc107" if health_score >= 60 else "#dc3545"
        theme_manager.create_metric_card(
            "健康分數",
            f"{health_score}%",
            f"狀態: {status}"
        )
    
    with col2:
        theme_manager.create_metric_card(
            "CPU使用率",
            f"{health_data['metrics'].get('cpu_usage', 0):.1f}%",
            "系統負載"
        )
    
    with col3:
        theme_manager.create_metric_card(
            "內存使用率",
            f"{health_data['metrics'].get('memory_usage', 0):.1f}%",
            "內存狀態"
        )
    
    with col4:
        theme_manager.create_metric_card(
            "活躍警報",
            str(health_data["active_alerts"]),
            "需要關注"
        )
    
    # 健康狀態圖表
    if health_data["monitoring_active"]:
        # 創建健康分數歷史圖表（模擬數據）
        times = pd.date_range(end=datetime.now(), periods=50, freq='1min')
        health_history = np.random.normal(health_score, 5, 50)
        health_history = np.clip(health_history, 0, 100)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=times,
            y=health_history,
            mode='lines+markers',
            name='健康分數',
            line=dict(color='#1f77b4', width=2)
        ))
        
        # 添加健康閾值線
        fig.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="健康")
        fig.add_hline(y=60, line_dash="dash", line_color="orange", annotation_text="警告")
        
        fig.update_layout(
            title="系統健康分數趨勢",
            xaxis_title="時間",
            yaxis_title="健康分數",
            height=300,
            yaxis=dict(range=[0, 100])
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("⚠️ 監控服務未啟動")

def show_performance_metrics(monitoring_service, theme_manager):
    """顯示性能指標"""
    st.subheader("📊 性能指標")
    
    # 獲取性能摘要
    performance_summary = monitoring_service.get_performance_summary(hours=1)
    
    if not performance_summary:
        st.info("暫無性能數據")
        return
    
    # 性能指標卡片
    metrics_cols = st.columns(len(performance_summary))
    
    for i, (metric_name, data) in enumerate(performance_summary.items()):
        with metrics_cols[i % len(metrics_cols)]:
            theme_manager.create_metric_card(
                metric_name.replace('_', ' ').title(),
                f"{data['current']:.1f}{data['unit']}",
                f"平均: {data['average']:.1f}{data['unit']}"
            )
    
    # 性能趨勢圖表
    st.markdown("### 📈 性能趨勢")
    
    # 創建多指標圖表
    fig = go.Figure()
    
    # 模擬性能數據
    times = pd.date_range(end=datetime.now(), periods=60, freq='1min')
    
    for metric_name, data in performance_summary.items():
        if metric_name in ['cpu_usage', 'memory_usage', 'disk_usage']:
            # 生成模擬趨勢數據
            np.random.seed(hash(metric_name) % 2**32)
            trend_data = np.random.normal(data['current'], data['current'] * 0.1, 60)
            trend_data = np.clip(trend_data, 0, 100)
            
            fig.add_trace(go.Scatter(
                x=times,
                y=trend_data,
                mode='lines',
                name=metric_name.replace('_', ' ').title(),
                line=dict(width=2)
            ))
    
    fig.update_layout(
        title="系統資源使用率趨勢",
        xaxis_title="時間",
        yaxis_title="使用率 (%)",
        height=400,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_alerts_management(monitoring_service, theme_manager):
    """顯示警報管理"""
    st.subheader("🚨 警報管理")
    
    alerts = list(monitoring_service.alerts.values())
    
    if not alerts:
        st.success("🎉 當前無活躍警報")
        return
    
    # 警報統計
    active_alerts = [a for a in alerts if not a.resolved]
    resolved_alerts = [a for a in alerts if a.resolved]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        theme_manager.create_metric_card("活躍警報", str(len(active_alerts)), "需要處理")
    
    with col2:
        theme_manager.create_metric_card("已解決警報", str(len(resolved_alerts)), "歷史記錄")
    
    with col3:
        if active_alerts:
            critical_count = sum(1 for a in active_alerts if a.severity == "critical")
            theme_manager.create_metric_card("嚴重警報", str(critical_count), "優先處理")
        else:
            theme_manager.create_metric_card("嚴重警報", "0", "系統正常")
    
    # 警報列表
    if active_alerts:
        st.markdown("### 🔴 活躍警報")
        
        for alert in sorted(active_alerts, key=lambda x: x.timestamp, reverse=True):
            severity_colors = {
                "critical": "#dc3545",
                "high": "#fd7e14", 
                "medium": "#ffc107",
                "low": "#28a745"
            }
            
            severity_color = severity_colors.get(alert.severity, "#6c757d")
            
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"""
                    <div style="border-left: 4px solid {severity_color}; padding-left: 1rem;">
                        <h4 style="color: {severity_color}; margin: 0;">{alert.title}</h4>
                        <p style="margin: 0.5rem 0;">{alert.message}</p>
                        <small>時間: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')} | 來源: {alert.source}</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.write(f"**嚴重程度**")
                    st.write(alert.severity.upper())
                
                with col3:
                    if st.button("✅ 解決", key=f"resolve_{alert.id}"):
                        if monitoring_service.resolve_alert(alert.id):
                            st.success("警報已解決")
                            st.rerun()
                
                st.markdown("---")
    
    # 已解決警報（摺疊顯示）
    if resolved_alerts:
        with st.expander(f"📋 已解決警報 ({len(resolved_alerts)}個)"):
            for alert in sorted(resolved_alerts, key=lambda x: x.resolution_time or x.timestamp, reverse=True)[:10]:
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**{alert.title}**: {alert.message}")
                    st.caption(f"發生時間: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                
                with col2:
                    if alert.resolution_time:
                        duration = alert.resolution_time - alert.timestamp
                        st.caption(f"解決用時: {duration}")

def show_log_viewer(monitoring_service, theme_manager):
    """顯示日誌查看器"""
    st.subheader("📋 日誌查看器")
    
    # 日誌過濾選項
    col1, col2, col3 = st.columns(3)
    
    with col1:
        log_level = st.selectbox(
            "日誌級別",
            ["全部"] + [level.value for level in LogLevel],
            key="log_level_filter"
        )
    
    with col2:
        module_filter = st.text_input("模組過濾", placeholder="輸入模組名稱")
    
    with col3:
        log_limit = st.number_input("顯示條數", min_value=10, max_value=1000, value=100)
    
    # 獲取日誌
    level_filter = None if log_level == "全部" else LogLevel(log_level)
    module_filter = module_filter if module_filter else None
    
    log_entries = monitoring_service.get_log_entries(
        level=level_filter,
        module=module_filter,
        limit=log_limit
    )
    
    if not log_entries:
        st.info("暫無日誌記錄")
        return
    
    # 日誌統計
    level_counts = {}
    for entry in log_entries:
        level_counts[entry.level.value] = level_counts.get(entry.level.value, 0) + 1
    
    st.markdown("### 📊 日誌統計")
    
    stats_cols = st.columns(len(level_counts))
    for i, (level, count) in enumerate(level_counts.items()):
        with stats_cols[i]:
            level_colors = {
                "DEBUG": "#6c757d",
                "INFO": "#17a2b8",
                "WARNING": "#ffc107",
                "ERROR": "#dc3545",
                "CRITICAL": "#721c24"
            }
            
            color = level_colors.get(level, "#6c757d")
            st.markdown(f"""
            <div style="text-align: center; padding: 1rem; border: 2px solid {color}; border-radius: 5px;">
                <h3 style="color: {color}; margin: 0;">{count}</h3>
                <p style="margin: 0;">{level}</p>
            </div>
            """, unsafe_allow_html=True)
    
    # 日誌列表
    st.markdown("### 📝 日誌記錄")
    
    for entry in log_entries:
        level_colors = {
            LogLevel.DEBUG: "#6c757d",
            LogLevel.INFO: "#17a2b8", 
            LogLevel.WARNING: "#ffc107",
            LogLevel.ERROR: "#dc3545",
            LogLevel.CRITICAL: "#721c24"
        }
        
        color = level_colors.get(entry.level, "#6c757d")
        
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 4])
            
            with col1:
                st.markdown(f"<span style='color: {color}; font-weight: bold;'>{entry.level.value}</span>", 
                           unsafe_allow_html=True)
            
            with col2:
                st.write(entry.timestamp.strftime('%H:%M:%S'))
                st.caption(entry.module)
            
            with col3:
                st.write(entry.message)
                if entry.exception:
                    with st.expander("查看異常詳情"):
                        st.code(entry.exception)
            
            st.markdown("---")

def show_exception_tracking(monitoring_service, theme_manager):
    """顯示異常追蹤"""
    st.subheader("🐛 異常追蹤")
    
    exception_tracker = monitoring_service.exception_tracker
    error_patterns = monitoring_service.error_patterns
    
    if not exception_tracker and not error_patterns:
        st.success("🎉 暫無異常記錄")
        return
    
    # 異常統計
    if exception_tracker:
        st.markdown("### 📊 模組異常統計")
        
        # 轉換為DataFrame
        exception_data = [
            {"模組": module, "異常次數": count}
            for module, count in exception_tracker.items()
        ]
        
        df = pd.DataFrame(exception_data)
        df = df.sort_values("異常次數", ascending=False)
        
        # 創建柱狀圖
        fig = px.bar(
            df.head(10),
            x="異常次數",
            y="模組",
            orientation='h',
            title="模組異常次數排行 (Top 10)"
        )
        
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
        
        # 詳細表格
        st.dataframe(df, use_container_width=True)
    
    # 錯誤模式
    if error_patterns:
        st.markdown("### 🔍 錯誤模式分析")
        
        pattern_data = []
        for pattern_key, pattern_info in error_patterns.items():
            module, message = pattern_key.split(':', 1)
            pattern_data.append({
                "模組": module,
                "錯誤消息": message,
                "出現次數": pattern_info["count"],
                "首次出現": pattern_info["first_seen"].strftime('%Y-%m-%d %H:%M:%S'),
                "最後出現": pattern_info["last_seen"].strftime('%Y-%m-%d %H:%M:%S')
            })
        
        pattern_df = pd.DataFrame(pattern_data)
        pattern_df = pattern_df.sort_values("出現次數", ascending=False)
        
        st.dataframe(pattern_df, use_container_width=True)

def show():
    """主顯示函數"""
    # 應用現代化主題
    theme_manager = apply_modern_theme()
    
    # 初始化監控服務
    monitoring_service = initialize_monitoring_service()
    
    if not monitoring_service:
        st.error("監控服務不可用")
        return
    
    # 主標題
    theme_manager.create_modern_header(
        "🔍 高級監控系統",
        "全面的系統性能監控、日誌分析和異常追蹤"
    )
    
    # 自動刷新選項
    auto_refresh = st.sidebar.checkbox("🔄 自動刷新 (30秒)", value=False)
    
    if auto_refresh:
        if "last_refresh" not in st.session_state:
            st.session_state.last_refresh = time.time()
        
        if time.time() - st.session_state.last_refresh > 30:
            st.session_state.last_refresh = time.time()
            st.rerun()
    
    # 監控控制
    st.sidebar.markdown("### 🎛️ 監控控制")
    
    if monitoring_service.monitoring_active:
        st.sidebar.success("✅ 監控服務運行中")
        if st.sidebar.button("⏹️ 停止監控"):
            monitoring_service.stop_monitoring()
            st.rerun()
    else:
        st.sidebar.warning("⚠️ 監控服務已停止")
        if st.sidebar.button("▶️ 啟動監控"):
            monitoring_service.start_monitoring()
            st.rerun()
    
    # 標籤頁
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏥 系統健康", "📊 性能指標", "🚨 警報管理", "📋 日誌查看", "🐛 異常追蹤"
    ])
    
    with tab1:
        show_system_health(monitoring_service, theme_manager)
    
    with tab2:
        show_performance_metrics(monitoring_service, theme_manager)
    
    with tab3:
        show_alerts_management(monitoring_service, theme_manager)
    
    with tab4:
        show_log_viewer(monitoring_service, theme_manager)
    
    with tab5:
        show_exception_tracking(monitoring_service, theme_manager)
    
    # 顯示最後更新時間
    st.caption(f"最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    show()
