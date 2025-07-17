# -*- coding: utf-8 -*-
"""
新手中心頁面

此模組提供新手友好的整合界面，包括：
- 新手導航中心
- 學習路徑指引
- 快速操作入口
- 進度追蹤
- 個人化推薦

Author: AI Trading System
Version: 1.0.0
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 導入新手功能模組
try:
    from src.ui.onboarding import (
        show_quick_start_guide,
        show_setup_wizard,
        show_demo_strategies,
        show_practice_mode,
        show_progress_dashboard,
        show_decision_logger,
        show_performance_analyzer,
        show_mistake_analyzer
    )

    from src.ui.simplified import (
        show_strategy_templates,
        show_one_click_backtest,
        show_risk_level_selector,
        show_simple_config_panel
    )

    from src.education import (
        show_trading_basics,
        show_strategy_explainer,
        show_risk_education,
        show_error_prevention
    )
except ImportError:
    # 如果相對導入失敗，嘗試絕對導入
    from src.ui.onboarding import (
        show_quick_start_guide,
        show_setup_wizard,
        show_demo_strategies,
        show_practice_mode,
        show_progress_dashboard,
        show_decision_logger,
        show_performance_analyzer,
        show_mistake_analyzer
    )

    from src.ui.simplified import (
        show_strategy_templates,
        show_one_click_backtest,
        show_risk_level_selector,
        show_simple_config_panel
    )

    from src.education import (
        show_trading_basics,
        show_strategy_explainer,
        show_risk_education,
        show_error_prevention
    )


def show():
    """顯示新手中心頁面（Web UI 入口點）"""
    show_beginner_hub()


def show_beginner_hub():
    """
    顯示新手中心頁面

    提供新手友好的整合界面，包括導航中心、學習路徑、
    快速操作和進度追蹤功能。
    
    Side Effects:
        - 在 Streamlit 界面顯示新手中心
        - 提供各種新手功能的入口
    """
    st.set_page_config(
        page_title="新手中心 - AI 交易系統",
        page_icon="🎓",
        layout="wide"
    )
    
    # 頁面標題
    st.title("🎓 新手中心")
    st.markdown("歡迎來到 AI 交易系統！這裡是您量化交易學習之旅的起點。")
    
    # 初始化用戶進度
    if 'user_progress' not in st.session_state:
        st.session_state.user_progress = {
            'setup_completed': False,
            'first_strategy_created': False,
            'first_backtest_completed': False,
            'risk_assessment_completed': False,
            'education_modules_completed': set(),
            'total_learning_time': 0,
            'last_activity': None
        }
    
    # 側邊欄：快速導航
    with st.sidebar:
        st.subheader("🧭 快速導航")
        
        # 學習階段選擇
        learning_stage = st.selectbox(
            "選擇學習階段",
            ["🌱 入門階段", "📚 學習階段", "🎯 實踐階段", "🚀 進階階段"],
            help="根據您的經驗選擇合適的學習階段"
        )
        
        # 根據階段顯示相應功能
        if learning_stage == "🌱 入門階段":
            st.write("**推薦功能：**")
            if st.button("📖 快速入門指南"):
                st.session_state.selected_function = "quick_start_guide"
            if st.button("⚙️ 系統設定精靈"):
                st.session_state.selected_function = "setup_wizard"
            if st.button("🎚️ 風險等級評估"):
                st.session_state.selected_function = "risk_level_selector"
        
        elif learning_stage == "📚 學習階段":
            st.write("**推薦功能：**")
            if st.button("📚 量化交易基礎"):
                st.session_state.selected_function = "trading_basics"
            if st.button("🧠 策略邏輯解釋"):
                st.session_state.selected_function = "strategy_explainer"
            if st.button("🛡️ 風險管理教育"):
                st.session_state.selected_function = "risk_education"
        
        elif learning_stage == "🎯 實踐階段":
            st.write("**推薦功能：**")
            if st.button("🎯 策略模板"):
                st.session_state.selected_function = "strategy_templates"
            if st.button("🎮 模擬交易"):
                st.session_state.selected_function = "practice_mode"
            if st.button("🚀 一鍵回測"):
                st.session_state.selected_function = "one_click_backtest"
        
        else:  # 進階階段
            st.write("**推薦功能：**")
            if st.button("⚙️ 參數設定"):
                st.session_state.selected_function = "simple_config_panel"
            if st.button("🚨 錯誤預防"):
                st.session_state.selected_function = "error_prevention"
            if st.button("📊 進度儀表板"):
                st.session_state.selected_function = "progress_dashboard"
        
        # 學習統計
        st.subheader("📈 學習統計")
        progress = st.session_state.user_progress
        
        completed_modules = len(progress['education_modules_completed'])
        total_modules = 12  # 假設總共12個學習模組
        
        st.metric("完成模組", f"{completed_modules}/{total_modules}")
        st.metric("學習時間", f"{progress['total_learning_time']} 分鐘")
        
        # 進度條
        progress_percentage = completed_modules / total_modules
        st.progress(progress_percentage)
        
        # 成就徽章
        st.subheader("🏆 成就徽章")
        
        achievements = []
        if progress['setup_completed']:
            achievements.append("⚙️ 系統設定完成")
        if progress['first_strategy_created']:
            achievements.append("🎯 首個策略創建")
        if progress['first_backtest_completed']:
            achievements.append("📊 首次回測完成")
        if progress['risk_assessment_completed']:
            achievements.append("🛡️ 風險評估完成")
        
        for achievement in achievements:
            st.success(achievement)
        
        if not achievements:
            st.info("開始學習以獲得成就徽章！")
    
    # 主要內容區域
    if 'selected_function' not in st.session_state:
        # 顯示主頁面
        show_main_dashboard()
    else:
        # 顯示選擇的功能
        function_name = st.session_state.selected_function
        
        # 返回按鈕
        if st.button("← 返回新手中心"):
            del st.session_state.selected_function
            st.rerun()
        
        # 根據選擇顯示對應功能
        function_map = {
            "quick_start_guide": show_quick_start_guide,
            "setup_wizard": show_setup_wizard,
            "demo_strategies": show_demo_strategies,
            "practice_mode": show_practice_mode,
            "progress_dashboard": show_progress_dashboard,
            "decision_logger": show_decision_logger,
            "performance_analyzer": show_performance_analyzer,
            "mistake_analyzer": show_mistake_analyzer,
            "strategy_templates": show_strategy_templates,
            "one_click_backtest": show_one_click_backtest,
            "risk_level_selector": show_risk_level_selector,
            "simple_config_panel": show_simple_config_panel,
            "trading_basics": show_trading_basics,
            "strategy_explainer": show_strategy_explainer,
            "risk_education": show_risk_education,
            "error_prevention": show_error_prevention
        }
        
        if function_name in function_map:
            function_map[function_name]()
        else:
            st.error(f"功能 {function_name} 尚未實現")


def show_main_dashboard():
    """顯示新手中心主儀表板"""
    
    # 歡迎區域
    st.subheader("👋 歡迎使用 AI 交易系統")
    
    # 檢查用戶是否為新用戶
    progress = st.session_state.user_progress
    is_new_user = not any([
        progress['setup_completed'],
        progress['first_strategy_created'],
        progress['first_backtest_completed']
    ])
    
    if is_new_user:
        st.info("""
        🎉 **歡迎新用戶！** 
        
        我們為您準備了完整的學習路徑，從基礎概念到實際操作，
        讓您輕鬆掌握量化交易的精髓。建議您從「快速入門指南」開始！
        """)
        
        # 新用戶快速開始
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📖 開始學習", type="primary"):
                st.session_state.selected_function = "quick_start_guide"
                st.rerun()
        
        with col2:
            if st.button("⚙️ 系統設定"):
                st.session_state.selected_function = "setup_wizard"
                st.rerun()
        
        with col3:
            if st.button("🎚️ 風險評估"):
                st.session_state.selected_function = "risk_level_selector"
                st.rerun()
    
    else:
        # 老用戶歡迎回來
        last_activity = progress.get('last_activity')
        if last_activity:
            st.success(f"歡迎回來！上次活動時間：{last_activity}")
        
        # 推薦下一步
        st.subheader("🎯 推薦下一步")
        
        recommendations = get_personalized_recommendations(progress)
        
        for rec in recommendations:
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**{rec['title']}**")
                    st.write(rec['description'])
                
                with col2:
                    if st.button(rec['action'], key=rec['key']):
                        st.session_state.selected_function = rec['function']
                        st.rerun()
    
    # 功能模組展示
    st.subheader("🛠️ 功能模組")
    
    # 創建功能卡片
    modules = [
        {
            "category": "🌱 入門引導",
            "items": [
                {"name": "快速入門指南", "desc": "5分鐘了解系統基本操作", "func": "quick_start_guide"},
                {"name": "系統設定精靈", "desc": "一步步完成系統配置", "func": "setup_wizard"},
                {"name": "風險等級評估", "desc": "評估您的風險承受能力", "func": "risk_level_selector"}
            ]
        },
        {
            "category": "📚 學習教育",
            "items": [
                {"name": "量化交易基礎", "desc": "從零開始學習量化交易", "func": "trading_basics"},
                {"name": "策略邏輯解釋", "desc": "深入理解策略運作原理", "func": "strategy_explainer"},
                {"name": "風險管理教育", "desc": "學習如何控制投資風險", "func": "risk_education"}
            ]
        },
        {
            "category": "🎯 實踐操作",
            "items": [
                {"name": "策略模板", "desc": "選擇預設策略快速開始", "func": "strategy_templates"},
                {"name": "模擬交易", "desc": "在安全環境中練習交易", "func": "practice_mode"},
                {"name": "一鍵回測", "desc": "快速驗證策略效果", "func": "one_click_backtest"}
            ]
        },
        {
            "category": "🚀 進階工具",
            "items": [
                {"name": "參數設定面板", "desc": "簡化的策略參數配置", "func": "simple_config_panel"},
                {"name": "錯誤預防系統", "desc": "避免常見的交易錯誤", "func": "error_prevention"},
                {"name": "進度追蹤儀表板", "desc": "監控您的學習進度", "func": "progress_dashboard"}
            ]
        },
        {
            "category": "📊 操作歷史與學習",
            "items": [
                {"name": "交易決策記錄器", "desc": "記錄和分析交易決策過程", "func": "decision_logger"},
                {"name": "績效分析報告", "desc": "深入分析交易績效表現", "func": "performance_analyzer"},
                {"name": "錯誤分析工具", "desc": "識別和改正交易錯誤", "func": "mistake_analyzer"}
            ]
        }
    ]
    
    for module in modules:
        with st.expander(module["category"], expanded=False):
            cols = st.columns(len(module["items"]))
            
            for i, item in enumerate(module["items"]):
                with cols[i]:
                    st.write(f"**{item['name']}**")
                    st.write(item['desc'])
                    
                    if st.button("開始使用", key=f"btn_{item['func']}"):
                        st.session_state.selected_function = item['func']
                        st.rerun()
    
    # 學習路徑圖
    st.subheader("🗺️ 建議學習路徑")
    
    # 創建學習路徑流程圖
    learning_path = [
        "📖 快速入門指南",
        "⚙️ 系統設定精靈", 
        "🎚️ 風險等級評估",
        "📚 量化交易基礎",
        "🧠 策略邏輯解釋",
        "🎯 策略模板選擇",
        "🎮 模擬交易練習",
        "🚀 一鍵回測驗證",
        "🛡️ 風險管理學習",
        "⚙️ 參數設定優化",
        "🚨 錯誤預防學習",
        "📊 進度追蹤分析"
    ]
    
    # 顯示學習路徑
    cols = st.columns(4)
    for i, step in enumerate(learning_path):
        col_idx = i % 4
        with cols[col_idx]:
            # 檢查是否已完成
            is_completed = check_step_completion(i, progress)
            status = "✅" if is_completed else "⏳"
            
            st.write(f"{i+1}. {status} {step}")
    
    # 每日提示
    st.subheader("💡 今日提示")
    
    tips = [
        "量化交易的核心是紀律性，制定規則並嚴格執行。",
        "分散投資是降低風險的最有效方法之一。",
        "回測結果不等於未來表現，要保持理性預期。",
        "情緒是交易的最大敵人，學會控制情緒很重要。",
        "持續學習和改進是成功交易者的共同特質。",
        "風險管理比獲利能力更重要。",
        "簡單的策略往往比複雜的策略更有效。"
    ]
    
    # 根據日期選擇提示
    today = datetime.now()
    tip_index = today.day % len(tips)
    
    st.info(f"💡 **今日提示**: {tips[tip_index]}")
    
    # 更新最後活動時間
    st.session_state.user_progress['last_activity'] = datetime.now().strftime("%Y-%m-%d %H:%M")


def get_personalized_recommendations(progress):
    """根據用戶進度生成個人化推薦"""
    recommendations = []
    
    if not progress['setup_completed']:
        recommendations.append({
            'title': '完成系統設定',
            'description': '設定您的交易參數和偏好',
            'action': '開始設定',
            'function': 'setup_wizard',
            'key': 'rec_setup'
        })
    
    if not progress['risk_assessment_completed']:
        recommendations.append({
            'title': '進行風險評估',
            'description': '了解您的風險承受能力',
            'action': '開始評估',
            'function': 'risk_level_selector',
            'key': 'rec_risk'
        })
    
    if not progress['first_strategy_created']:
        recommendations.append({
            'title': '創建第一個策略',
            'description': '從預設模板開始您的量化交易',
            'action': '選擇策略',
            'function': 'strategy_templates',
            'key': 'rec_strategy'
        })
    
    if not progress['first_backtest_completed']:
        recommendations.append({
            'title': '進行第一次回測',
            'description': '驗證您的策略效果',
            'action': '開始回測',
            'function': 'one_click_backtest',
            'key': 'rec_backtest'
        })
    
    # 如果基本步驟都完成了，推薦進階功能
    if all([
        progress['setup_completed'],
        progress['risk_assessment_completed'],
        progress['first_strategy_created']
    ]):
        recommendations.append({
            'title': '學習錯誤預防',
            'description': '避免常見的交易錯誤',
            'action': '開始學習',
            'function': 'error_prevention',
            'key': 'rec_error'
        })
    
    return recommendations[:3]  # 最多顯示3個推薦


def check_step_completion(step_index, progress):
    """檢查學習步驟是否完成"""
    completion_map = {
        0: True,  # 快速入門指南（假設已看過）
        1: progress['setup_completed'],
        2: progress['risk_assessment_completed'],
        3: 'trading_basics' in progress['education_modules_completed'],
        4: 'strategy_explainer' in progress['education_modules_completed'],
        5: progress['first_strategy_created'],
        6: 'practice_mode' in progress['education_modules_completed'],
        7: progress['first_backtest_completed'],
        8: 'risk_education' in progress['education_modules_completed'],
        9: 'simple_config' in progress['education_modules_completed'],
        10: 'error_prevention' in progress['education_modules_completed'],
        11: 'progress_dashboard' in progress['education_modules_completed']
    }
    
    return completion_map.get(step_index, False)


if __name__ == "__main__":
    show_beginner_hub()
