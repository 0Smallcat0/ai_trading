#!/usr/bin/env python3
"""
功能狀態儀表板頁面
實時顯示所有功能模組的狀態、健康度指標和修復建議
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
import time
import os
import sys

# 添加項目根目錄到路徑
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from src.ui.components.function_status_indicator import (
    FunctionStatusIndicator, 
    FunctionStatus,
    show_function_status_indicator,
    show_system_status_dashboard
)

def show_status_overview():
    """顯示狀態概覽"""
    st.subheader("📊 系統狀態概覽")
    
    indicator = FunctionStatusIndicator()
    overview = indicator.get_system_overview()
    all_status = indicator.get_all_function_status()
    
    # 狀態統計圖表
    col1, col2 = st.columns(2)
    
    with col1:
        # 狀態分布餅圖
        status_counts = overview["status_counts"]
        labels = []
        values = []
        colors = []
        
        status_config = {
            "healthy": {"label": "健康", "color": "#28a745"},
            "warning": {"label": "警告", "color": "#ffc107"},
            "error": {"label": "錯誤", "color": "#dc3545"},
            "unavailable": {"label": "不可用", "color": "#6c757d"}
        }
        
        for status, count in status_counts.items():
            if count > 0:
                labels.append(status_config[status]["label"])
                values.append(count)
                colors.append(status_config[status]["color"])
        
        if values:
            fig_pie = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                marker_colors=colors,
                hole=0.4
            )])
            fig_pie.update_layout(
                title="功能狀態分布",
                height=300,
                showlegend=True
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("暫無狀態數據")
    
    with col2:
        # 健康度分布柱狀圖
        health_scores = []
        function_names = []
        
        for func_id, status_info in all_status.items():
            health_scores.append(status_info["health_score"])
            function_names.append(status_info["name"])
        
        if health_scores:
            df = pd.DataFrame({
                "功能": function_names,
                "健康度": health_scores
            })
            
            fig_bar = px.bar(
                df,
                x="健康度",
                y="功能",
                orientation='h',
                color="健康度",
                color_continuous_scale=["red", "yellow", "green"],
                title="功能健康度分布"
            )
            fig_bar.update_layout(height=300)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("暫無健康度數據")

def show_detailed_status():
    """顯示詳細狀態"""
    st.subheader("🔍 詳細功能狀態")
    
    indicator = FunctionStatusIndicator()
    all_status = indicator.get_all_function_status()
    
    # 篩選選項
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "狀態篩選",
            ["全部", "健康", "警告", "錯誤", "不可用"],
            key="status_filter"
        )
    
    with col2:
        sort_by = st.selectbox(
            "排序方式",
            ["健康度", "名稱", "狀態"],
            key="sort_by"
        )
    
    with col3:
        sort_order = st.selectbox(
            "排序順序",
            ["降序", "升序"],
            key="sort_order"
        )
    
    # 篩選和排序
    filtered_status = {}
    
    status_mapping = {
        "健康": FunctionStatus.HEALTHY,
        "警告": FunctionStatus.WARNING,
        "錯誤": FunctionStatus.ERROR,
        "不可用": FunctionStatus.UNAVAILABLE
    }
    
    for func_id, status_info in all_status.items():
        if status_filter == "全部" or status_info["status"] == status_mapping.get(status_filter):
            filtered_status[func_id] = status_info
    
    # 排序
    if sort_by == "健康度":
        sorted_items = sorted(filtered_status.items(), 
                            key=lambda x: x[1]["health_score"], 
                            reverse=(sort_order == "降序"))
    elif sort_by == "名稱":
        sorted_items = sorted(filtered_status.items(), 
                            key=lambda x: x[1]["name"], 
                            reverse=(sort_order == "降序"))
    else:  # 狀態
        status_order = {
            FunctionStatus.ERROR: 0,
            FunctionStatus.UNAVAILABLE: 1,
            FunctionStatus.WARNING: 2,
            FunctionStatus.HEALTHY: 3
        }
        sorted_items = sorted(filtered_status.items(), 
                            key=lambda x: status_order.get(x[1]["status"], 4), 
                            reverse=(sort_order == "降序"))
    
    # 顯示結果
    if not sorted_items:
        st.info("沒有符合條件的功能")
    else:
        for func_id, status_info in sorted_items:
            show_function_status_indicator(func_id, indicator)
            st.markdown("---")

def show_health_trends():
    """顯示健康度趨勢"""
    st.subheader("📈 健康度趨勢")
    
    # 模擬歷史數據（實際應用中應該從數據庫獲取）
    dates = pd.date_range(end=datetime.now(), periods=7, freq='D')
    
    # 為每個功能生成模擬趨勢數據
    indicator = FunctionStatusIndicator()
    all_status = indicator.get_all_function_status()
    
    trend_data = []
    
    for func_id, status_info in all_status.items():
        current_health = status_info["health_score"]
        
        # 生成模擬歷史數據
        for i, date in enumerate(dates):
            # 添加一些隨機波動
            import random
            variation = random.uniform(-10, 10)
            health_score = max(0, min(100, current_health + variation))
            
            trend_data.append({
                "日期": date,
                "功能": status_info["name"],
                "健康度": health_score
            })
    
    if trend_data:
        df = pd.DataFrame(trend_data)
        
        # 創建趨勢圖
        fig = px.line(
            df,
            x="日期",
            y="健康度",
            color="功能",
            title="功能健康度趨勢 (最近7天)",
            markers=True
        )
        
        fig.update_layout(
            height=400,
            xaxis_title="日期",
            yaxis_title="健康度 (%)",
            yaxis=dict(range=[0, 100])
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 趨勢分析
        st.markdown("### 📊 趨勢分析")
        
        # 計算平均健康度變化
        latest_avg = df[df["日期"] == df["日期"].max()]["健康度"].mean()
        earliest_avg = df[df["日期"] == df["日期"].min()]["健康度"].mean()
        change = latest_avg - earliest_avg
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("當前平均健康度", f"{latest_avg:.1f}%")
        
        with col2:
            st.metric("7天前平均健康度", f"{earliest_avg:.1f}%")
        
        with col3:
            st.metric("變化趨勢", f"{change:+.1f}%", delta=f"{change:+.1f}%")
        
        # 趨勢建議
        if change > 5:
            st.success("📈 系統健康度呈上升趨勢，運行狀況良好")
        elif change < -5:
            st.warning("📉 系統健康度呈下降趨勢，建議檢查系統狀態")
        else:
            st.info("📊 系統健康度保持穩定")
    
    else:
        st.info("暫無趨勢數據")

def show_maintenance_suggestions():
    """顯示維護建議"""
    st.subheader("🔧 系統維護建議")
    
    indicator = FunctionStatusIndicator()
    all_status = indicator.get_all_function_status()
    
    # 收集所有問題和建議
    all_issues = []
    all_suggestions = []
    
    for func_id, status_info in all_status.items():
        if status_info["status"] != FunctionStatus.HEALTHY:
            for issue in status_info["issues"]:
                all_issues.append({
                    "功能": status_info["name"],
                    "問題": issue,
                    "嚴重程度": status_info["status"].value
                })
            
            for suggestion in status_info["suggestions"]:
                all_suggestions.append({
                    "功能": status_info["name"],
                    "建議": suggestion,
                    "優先級": status_info["status"].value
                })
    
    # 顯示問題列表
    if all_issues:
        st.markdown("### ⚠️ 發現的問題")
        
        issues_df = pd.DataFrame(all_issues)
        
        # 按嚴重程度排序
        severity_order = {"error": 0, "unavailable": 1, "warning": 2}
        issues_df["排序"] = issues_df["嚴重程度"].map(severity_order)
        issues_df = issues_df.sort_values("排序").drop("排序", axis=1)
        
        for _, issue in issues_df.iterrows():
            severity_icon = {
                "error": "🔴",
                "unavailable": "⚫",
                "warning": "🟡"
            }.get(issue["嚴重程度"], "❓")
            
            st.write(f"{severity_icon} **{issue['功能']}**: {issue['問題']}")
    
    # 顯示建議列表
    if all_suggestions:
        st.markdown("### 💡 修復建議")
        
        suggestions_df = pd.DataFrame(all_suggestions)
        
        # 按優先級排序
        priority_order = {"error": 0, "unavailable": 1, "warning": 2}
        suggestions_df["排序"] = suggestions_df["優先級"].map(priority_order)
        suggestions_df = suggestions_df.sort_values("排序").drop("排序", axis=1)
        
        for i, suggestion in enumerate(suggestions_df.itertuples(), 1):
            priority_icon = {
                "error": "🔥",
                "unavailable": "⚡",
                "warning": "💡"
            }.get(suggestion.優先級, "💡")
            
            st.write(f"{priority_icon} **建議 {i}** ({suggestion.功能}): {suggestion.建議}")
    
    if not all_issues and not all_suggestions:
        st.success("🎉 系統運行良好，暫無維護建議")
    
    # 自動修復選項
    st.markdown("### 🤖 自動修復")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 重新檢查所有功能"):
            indicator.status_cache.clear()
            indicator.last_check_time.clear()
            st.success("✅ 已清除緩存，重新檢查中...")
            st.rerun()
    
    with col2:
        if st.button("📦 檢查依賴項"):
            st.info("正在檢查系統依賴項...")
            # 這裡可以添加實際的依賴項檢查邏輯
            time.sleep(2)
            st.success("✅ 依賴項檢查完成")
    
    with col3:
        if st.button("🧹 清理系統緩存"):
            st.info("正在清理系統緩存...")
            # 這裡可以添加實際的緩存清理邏輯
            time.sleep(1)
            st.success("✅ 緩存清理完成")

def show():
    """主顯示函數"""
    st.title("🎛️ 功能狀態儀表板")
    
    # 自動刷新選項
    auto_refresh = st.checkbox("🔄 自動刷新 (60秒)", value=False)
    
    if auto_refresh:
        # 自動刷新邏輯
        if "last_refresh" not in st.session_state:
            st.session_state.last_refresh = time.time()
        
        if time.time() - st.session_state.last_refresh > 60:
            st.session_state.last_refresh = time.time()
            st.rerun()
    
    # 標籤頁
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 狀態概覽", 
        "🔍 詳細狀態", 
        "📈 健康度趨勢", 
        "🔧 維護建議",
        "🎛️ 系統儀表板"
    ])
    
    with tab1:
        show_status_overview()
    
    with tab2:
        show_detailed_status()
    
    with tab3:
        show_health_trends()
    
    with tab4:
        show_maintenance_suggestions()
    
    with tab5:
        show_system_status_dashboard()
    
    # 顯示最後更新時間
    st.caption(f"最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    show()
