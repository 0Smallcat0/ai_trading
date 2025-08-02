#!/usr/bin/env python3
"""
現代化增強儀表板
基於現有自定義儀表板，添加現代化主題和響應式設計
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import sys

# 添加項目根目錄到路徑
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from src.ui.themes.modern_theme_manager import apply_modern_theme, create_modern_layout

def show_enhanced_dashboard():
    """顯示增強版現代化儀表板"""
    # 應用現代化主題
    theme_manager = apply_modern_theme()
    create_modern_layout()
    
    # 主標題
    theme_manager.create_modern_header(
        "🚀 現代化交易儀表板",
        "智能化、響應式的交易系統監控中心"
    )
    
    # 快速統計卡片
    show_quick_stats(theme_manager)
    
    # 主要內容區域
    col1, col2 = st.columns([2, 1])
    
    with col1:
        show_main_charts(theme_manager)
    
    with col2:
        show_side_panels(theme_manager)
    
    # 底部功能區
    show_bottom_section(theme_manager)

def show_quick_stats(theme_manager):
    """顯示快速統計"""
    st.markdown("### 📊 實時概覽")
    
    cols = theme_manager.get_responsive_columns(4, 2, 1)
    
    with cols[0]:
        theme_manager.create_metric_card(
            "投資組合價值",
            "$125,430",
            "+$2,340 (+1.9%)",
            "positive"
        )
    
    with cols[1]:
        theme_manager.create_metric_card(
            "今日損益",
            "+$1,234",
            "+0.98%",
            "positive"
        )
    
    with cols[2]:
        theme_manager.create_metric_card(
            "活躍策略",
            "8",
            "+2 新增",
            "normal"
        )
    
    with cols[3]:
        theme_manager.create_metric_card(
            "系統健康度",
            "95%",
            "優秀",
            "positive"
        )

def show_main_charts(theme_manager):
    """顯示主要圖表"""
    # 投資組合表現圖表
    st.markdown("### 📈 投資組合表現")
    
    # 生成模擬數據
    dates = pd.date_range(end=datetime.now(), periods=90, freq='D')
    np.random.seed(42)
    
    # 投資組合數據
    portfolio_returns = np.random.normal(0.001, 0.02, 90)
    portfolio_cumulative = (1 + portfolio_returns).cumprod()
    portfolio_value = 100000 * portfolio_cumulative
    
    # 基準數據
    benchmark_returns = np.random.normal(0.0005, 0.015, 90)
    benchmark_cumulative = (1 + benchmark_returns).cumprod()
    benchmark_value = 100000 * benchmark_cumulative
    
    fig = go.Figure()
    
    # 添加投資組合線
    fig.add_trace(go.Scatter(
        x=dates,
        y=portfolio_value,
        mode='lines',
        name='我的投資組合',
        line=dict(color='#1f77b4', width=3),
        fill='tonexty' if len(fig.data) > 0 else None
    ))
    
    # 添加基準線
    fig.add_trace(go.Scatter(
        x=dates,
        y=benchmark_value,
        mode='lines',
        name='市場基準',
        line=dict(color='#ff7f0e', width=2, dash='dash')
    ))
    
    # 添加移動平均線
    portfolio_ma = pd.Series(portfolio_value).rolling(window=7).mean()
    fig.add_trace(go.Scatter(
        x=dates,
        y=portfolio_ma,
        mode='lines',
        name='7日移動平均',
        line=dict(color='#2ca02c', width=1),
        opacity=0.7
    ))
    
    fig.update_layout(
        title="90天表現對比",
        xaxis_title="日期",
        yaxis_title="價值 ($)",
        height=400,
        showlegend=True,
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    # 使用圖表容器
    theme_manager.create_chart_container(
        lambda: st.plotly_chart(fig, use_container_width=True)
    )
    
    # 策略表現對比
    st.markdown("### 🎯 策略表現對比")
    
    strategy_data = {
        "策略名稱": ["動量策略", "均值回歸", "AI預測", "價值投資", "技術分析"],
        "年化收益": [15.2, 8.7, 22.1, 12.4, 9.8],
        "夏普比率": [1.2, 0.8, 1.8, 1.1, 0.9],
        "最大回撤": [-8.5, -5.2, -12.1, -6.8, -7.3]
    }
    
    df = pd.DataFrame(strategy_data)
    
    # 創建氣泡圖
    fig_bubble = px.scatter(
        df,
        x="年化收益",
        y="夏普比率",
        size=[abs(x) for x in df["最大回撤"]],
        color="策略名稱",
        hover_data=["最大回撤"],
        title="策略風險收益分析"
    )
    
    fig_bubble.update_layout(
        height=350,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    theme_manager.create_chart_container(
        lambda: st.plotly_chart(fig_bubble, use_container_width=True)
    )

def show_side_panels(theme_manager):
    """顯示側邊面板"""
    # 市場動態
    st.markdown("### 🌍 市場動態")
    
    market_data = [
        {"name": "台股加權", "value": "17,234", "change": "+1.2%", "status": "up"},
        {"name": "上證指數", "value": "3,245", "change": "-0.8%", "status": "down"},
        {"name": "恆生指數", "value": "18,567", "change": "+0.5%", "status": "up"},
        {"name": "日經225", "value": "28,934", "change": "+1.8%", "status": "up"}
    ]
    
    for market in market_data:
        with st.container():
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**{market['name']}**")
                st.write(market['value'])
            
            with col2:
                color = "🟢" if market['status'] == "up" else "🔴"
                st.write(f"{color} {market['change']}")
    
    st.markdown("---")
    
    # AI洞察
    st.markdown("### 🤖 AI智能洞察")
    
    insights = [
        {
            "type": "機會",
            "text": "檢測到科技股低估機會",
            "confidence": 85,
            "icon": "🎯"
        },
        {
            "type": "風險",
            "text": "市場波動性增加",
            "confidence": 78,
            "icon": "⚠️"
        },
        {
            "type": "建議",
            "text": "建議調整倉位配置",
            "confidence": 92,
            "icon": "💡"
        }
    ]
    
    for insight in insights:
        with st.container():
            st.write(f"{insight['icon']} **{insight['type']}**")
            st.write(insight['text'])
            
            # 置信度進度條
            progress_color = "#2ca02c" if insight['confidence'] > 80 else "#ff7f0e" if insight['confidence'] > 60 else "#d62728"
            st.progress(insight['confidence'] / 100)
            st.caption(f"置信度: {insight['confidence']}%")
            st.markdown("---")
    
    # 最近交易
    st.markdown("### 📋 最近交易")
    
    trades = [
        {"time": "15:45", "symbol": "2330.TW", "action": "賣出", "qty": 200, "status": "✅"},
        {"time": "14:20", "symbol": "2454.TW", "action": "買入", "qty": 800, "status": "⏳"},
        {"time": "11:15", "symbol": "2317.TW", "action": "賣出", "qty": 500, "status": "✅"},
        {"time": "10:30", "symbol": "2330.TW", "action": "買入", "qty": 1000, "status": "✅"}
    ]
    
    for trade in trades:
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            st.caption(trade['time'])
        
        with col2:
            action_color = "🟢" if trade['action'] == "買入" else "🔴"
            st.write(f"{action_color} {trade['action']}")
            st.caption(f"{trade['symbol']} x{trade['qty']}")
        
        with col3:
            st.write(trade['status'])

def show_bottom_section(theme_manager):
    """顯示底部功能區"""
    st.markdown("---")
    
    # 功能狀態監控
    st.markdown("### 🎛️ 系統狀態監控")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**核心服務狀態**")
        
        services = [
            {"name": "數據管理", "status": "healthy"},
            {"name": "策略執行", "status": "healthy"},
            {"name": "風險控制", "status": "warning"},
            {"name": "AI模型", "status": "healthy"}
        ]
        
        for service in services:
            theme_manager.create_status_badge(service['status'], service['name'])
    
    with col2:
        st.markdown("**性能指標**")
        
        # 簡化的性能圖表
        perf_data = {
            "指標": ["CPU", "內存", "網絡", "磁盤"],
            "使用率": [45, 67, 23, 34]
        }
        
        fig_perf = go.Figure(data=[
            go.Bar(
                x=perf_data["指標"],
                y=perf_data["使用率"],
                marker_color=['#2ca02c' if x < 50 else '#ff7f0e' if x < 80 else '#d62728' for x in perf_data["使用率"]]
            )
        ])
        
        fig_perf.update_layout(
            title="系統資源使用率",
            height=200,
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=30, b=0, l=0, r=0)
        )
        
        st.plotly_chart(fig_perf, use_container_width=True)
    
    # 快速操作按鈕
    st.markdown("### ⚡ 快速操作")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔄 刷新數據", use_container_width=True):
            st.success("數據已刷新")
    
    with col2:
        if st.button("📊 生成報告", use_container_width=True):
            st.info("報告生成中...")
    
    with col3:
        if st.button("⚙️ 系統設置", use_container_width=True):
            st.session_state.current_view = "system_settings"
            st.rerun()
    
    with col4:
        if st.button("🆘 技術支援", use_container_width=True):
            st.info("技術支援聯繫方式已發送")

def show():
    """主顯示函數"""
    show_enhanced_dashboard()

if __name__ == "__main__":
    show()
