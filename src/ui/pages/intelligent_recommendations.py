#!/usr/bin/env python3
"""
智能推薦系統頁面
提供策略推薦、參數優化建議、風險提醒功能的Web界面
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

from src.ui.themes.modern_theme_manager import apply_modern_theme
from src.core.intelligent_recommendation_service import (
    IntelligentRecommendationService,
    RecommendationType,
    RecommendationPriority
)

def initialize_recommendation_service():
    """初始化推薦服務"""
    try:
        return IntelligentRecommendationService()
    except Exception as e:
        st.error(f"推薦服務初始化失敗: {e}")
        return None

def show_user_profile_setup():
    """顯示用戶畫像設置"""
    st.sidebar.markdown("### 👤 用戶畫像設置")
    
    risk_tolerance = st.sidebar.selectbox(
        "風險偏好",
        ["low", "medium", "high"],
        index=1,
        format_func=lambda x: {"low": "保守型", "medium": "平衡型", "high": "積極型"}[x]
    )
    
    investment_horizon = st.sidebar.selectbox(
        "投資期限",
        ["short_term", "medium_term", "long_term"],
        index=1,
        format_func=lambda x: {"short_term": "短期", "medium_term": "中期", "long_term": "長期"}[x]
    )
    
    experience_level = st.sidebar.selectbox(
        "經驗水平",
        ["beginner", "intermediate", "advanced"],
        index=1,
        format_func=lambda x: {"beginner": "新手", "intermediate": "中級", "advanced": "高級"}[x]
    )
    
    capital_size = st.sidebar.selectbox(
        "資金規模",
        ["small", "medium", "large"],
        index=1,
        format_func=lambda x: {"small": "小額", "medium": "中等", "large": "大額"}[x]
    )
    
    return {
        "risk_tolerance": risk_tolerance,
        "investment_horizon": investment_horizon,
        "experience_level": experience_level,
        "capital_size": capital_size
    }

def show_strategy_recommendations(recommendations, theme_manager):
    """顯示策略推薦"""
    st.subheader("🎯 策略推薦")
    
    if not recommendations:
        st.info("暫無策略推薦")
        return
    
    for i, rec in enumerate(recommendations):
        with st.expander(f"推薦 {i+1}: {rec['strategy_name']} (評分: {rec['score']:.2f})", expanded=i==0):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write(f"**描述**: {rec['description']}")
                
                # 推薦理由
                if rec.get('reasons'):
                    st.write("**推薦理由**:")
                    for reason in rec['reasons']:
                        st.write(f"• {reason}")
                
                # 推薦參數
                if rec.get('recommended_parameters'):
                    st.write("**建議參數**:")
                    params_df = pd.DataFrame([
                        {"參數": k, "建議值": v} 
                        for k, v in rec['recommended_parameters'].items()
                    ])
                    st.dataframe(params_df, use_container_width=True)
            
            with col2:
                # 關鍵指標
                theme_manager.create_metric_card(
                    "預期收益",
                    f"{rec['expected_return']:.1%}",
                    f"風險等級: {rec['risk_level']}"
                )
                
                # 優先級指示器
                priority_colors = {
                    "critical": "🔴",
                    "high": "🟠", 
                    "medium": "🟡",
                    "low": "🟢"
                }
                priority_icon = priority_colors.get(rec['priority'].value, "⚪")
                st.write(f"**優先級**: {priority_icon} {rec['priority'].value.upper()}")
                
                # 操作按鈕
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button("📋 詳細信息", key=f"detail_{i}"):
                        st.session_state[f"show_detail_{i}"] = True
                
                with col_btn2:
                    if st.button("✅ 採用策略", key=f"adopt_{i}"):
                        st.success(f"已採用策略: {rec['strategy_name']}")
            
            # 反饋區域
            st.markdown("---")
            col_feedback1, col_feedback2, col_feedback3 = st.columns(3)
            
            with col_feedback1:
                if st.button("👍 有用", key=f"helpful_{i}"):
                    st.success("感謝您的反饋！")
            
            with col_feedback2:
                if st.button("👎 無用", key=f"not_helpful_{i}"):
                    st.info("我們會改進推薦算法")
            
            with col_feedback3:
                if st.button("💬 建議", key=f"suggest_{i}"):
                    st.text_area("您的建議", key=f"suggestion_{i}")

def show_risk_alerts(risk_alerts, theme_manager):
    """顯示風險提醒"""
    st.subheader("⚠️ 風險提醒")
    
    if not risk_alerts:
        st.success("🎉 當前無風險警告")
        return
    
    # 按優先級分組
    critical_alerts = [a for a in risk_alerts if a['priority'] == RecommendationPriority.CRITICAL]
    high_alerts = [a for a in risk_alerts if a['priority'] == RecommendationPriority.HIGH]
    medium_alerts = [a for a in risk_alerts if a['priority'] == RecommendationPriority.MEDIUM]
    
    # 顯示嚴重警告
    if critical_alerts:
        st.error("🚨 嚴重風險警告")
        for alert in critical_alerts:
            st.error(f"**{alert['title']}**: {alert['message']}")
            if alert.get('suggestions'):
                st.write("**建議措施**:")
                for suggestion in alert['suggestions']:
                    st.write(f"• {suggestion}")
    
    # 顯示高風險警告
    if high_alerts:
        st.warning("⚠️ 高風險警告")
        for alert in high_alerts:
            st.warning(f"**{alert['title']}**: {alert['message']}")
            if alert.get('suggestions'):
                with st.expander("查看建議措施"):
                    for suggestion in alert['suggestions']:
                        st.write(f"• {suggestion}")
    
    # 顯示中等風險警告
    if medium_alerts:
        st.info("ℹ️ 中等風險提醒")
        for alert in medium_alerts:
            with st.expander(f"{alert['title']}"):
                st.write(alert['message'])
                if alert.get('suggestions'):
                    st.write("**建議措施**:")
                    for suggestion in alert['suggestions']:
                        st.write(f"• {suggestion}")

def show_opportunities(opportunities, theme_manager):
    """顯示投資機會"""
    st.subheader("🎯 投資機會")
    
    if not opportunities:
        st.info("暫無特殊投資機會")
        return
    
    for i, opp in enumerate(opportunities):
        priority_colors = {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#ffc107",
            "low": "#28a745"
        }
        
        priority_color = priority_colors.get(opp['priority'].value, "#6c757d")
        
        with st.container():
            st.markdown(f"""
            <div style="border-left: 4px solid {priority_color}; padding-left: 1rem; margin-bottom: 1rem;">
                <h4 style="color: {priority_color}; margin: 0;">{opp['title']}</h4>
                <p style="margin: 0.5rem 0;">{opp['message']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if opp.get('suggestions'):
                with st.expander("查看具體建議"):
                    for suggestion in opp['suggestions']:
                        st.write(f"• {suggestion}")
            
            # 操作按鈕
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📊 詳細分析", key=f"opp_detail_{i}"):
                    st.info("詳細分析功能開發中...")
            
            with col2:
                if st.button("⭐ 關注機會", key=f"opp_follow_{i}"):
                    st.success("已添加到關注列表")

def show_recommendation_dashboard(theme_manager):
    """顯示推薦儀表板"""
    st.subheader("📊 推薦概覽")
    
    # 模擬統計數據
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        theme_manager.create_metric_card("策略推薦", "5", "+2 新增")
    
    with col2:
        theme_manager.create_metric_card("風險警告", "2", "中等風險")
    
    with col3:
        theme_manager.create_metric_card("投資機會", "3", "+1 新增")
    
    with col4:
        theme_manager.create_metric_card("採用率", "75%", "+5%")
    
    # 推薦分布圖
    st.markdown("### 📈 推薦分布")
    
    recommendation_data = {
        "類型": ["策略推薦", "風險警告", "投資機會", "參數優化"],
        "數量": [5, 2, 3, 4],
        "採用率": [0.8, 0.9, 0.6, 0.7]
    }
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='推薦數量',
        x=recommendation_data["類型"],
        y=recommendation_data["數量"],
        yaxis='y',
        offsetgroup=1
    ))
    
    fig.add_trace(go.Scatter(
        name='採用率',
        x=recommendation_data["類型"],
        y=[x*10 for x in recommendation_data["採用率"]],  # 縮放以適應圖表
        yaxis='y2',
        mode='lines+markers',
        line=dict(color='red')
    ))
    
    fig.update_layout(
        title='推薦類型分布與採用率',
        xaxis=dict(title='推薦類型'),
        yaxis=dict(title='推薦數量', side='left'),
        yaxis2=dict(title='採用率 (%)', side='right', overlaying='y', range=[0, 10]),
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_parameter_optimization():
    """顯示參數優化建議"""
    st.subheader("⚙️ 參數優化建議")
    
    # 模擬參數優化數據
    optimization_data = [
        {
            "策略": "動量策略",
            "參數": "lookback_period",
            "當前值": 20,
            "建議值": 15,
            "預期改善": "+15%"
        },
        {
            "策略": "均值回歸",
            "參數": "deviation_threshold",
            "當前值": 2.0,
            "建議值": 1.8,
            "預期改善": "+12%"
        }
    ]
    
    for opt in optimization_data:
        with st.expander(f"{opt['策略']} - {opt['參數']}優化"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("當前值", opt['當前值'])
            
            with col2:
                st.metric("建議值", opt['建議值'])
            
            with col3:
                st.metric("預期改善", opt['預期改善'])
            
            if st.button(f"應用優化", key=f"apply_{opt['策略']}_{opt['參數']}"):
                st.success(f"已應用 {opt['策略']} 的 {opt['參數']} 優化")

def show():
    """主顯示函數"""
    # 應用現代化主題
    theme_manager = apply_modern_theme()
    
    # 初始化推薦服務
    rec_service = initialize_recommendation_service()
    
    if not rec_service:
        st.error("推薦服務不可用")
        return
    
    # 主標題
    theme_manager.create_modern_header(
        "🧠 智能推薦系統",
        "基於AI的個性化投資建議和風險提醒"
    )
    
    # 用戶畫像設置
    user_profile = show_user_profile_setup()
    
    # 生成推薦
    if st.sidebar.button("🔄 生成推薦", type="primary"):
        with st.spinner("正在分析並生成推薦..."):
            # 模擬用戶數據
            user_data = {
                "risk_tolerance": user_profile["risk_tolerance"],
                "investment_horizon": user_profile["investment_horizon"],
                "experience_level": user_profile["experience_level"],
                "portfolio": {
                    "current_drawdown": 0.08,
                    "volatility": 0.15,
                    "holdings": [
                        {"symbol": "2330.TW", "weight": 0.4},
                        {"symbol": "2317.TW", "weight": 0.3},
                        {"symbol": "2454.TW", "weight": 0.3}
                    ]
                }
            }
            
            recommendations = rec_service.generate_comprehensive_recommendations(user_data)
            st.session_state.recommendations = recommendations
    
    # 顯示推薦結果
    if "recommendations" in st.session_state:
        recommendations = st.session_state.recommendations
        
        # 標籤頁
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 概覽", "🎯 策略推薦", "⚠️ 風險提醒", "🎯 投資機會", "⚙️ 參數優化"
        ])
        
        with tab1:
            show_recommendation_dashboard(theme_manager)
        
        with tab2:
            show_strategy_recommendations(
                recommendations["recommendations"]["strategies"], 
                theme_manager
            )
        
        with tab3:
            show_risk_alerts(
                recommendations["recommendations"]["risk_alerts"], 
                theme_manager
            )
        
        with tab4:
            show_opportunities(
                recommendations["recommendations"]["opportunities"], 
                theme_manager
            )
        
        with tab5:
            show_parameter_optimization()
    
    else:
        st.info("👆 請點擊左側邊欄的「生成推薦」按鈕開始獲取個性化建議")

if __name__ == "__main__":
    show()
