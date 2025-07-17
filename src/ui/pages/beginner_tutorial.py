#!/usr/bin/env python3
"""
新手引導教程
5分鐘互動式入門流程，幫助新用戶快速上手AI交易系統
"""

import streamlit as st
import time
from datetime import datetime
import os
import sys

# 添加項目根目錄到路徑
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

def initialize_tutorial_state():
    """初始化教程狀態"""
    if "tutorial_step" not in st.session_state:
        st.session_state.tutorial_step = 0
    if "tutorial_completed_steps" not in st.session_state:
        st.session_state.tutorial_completed_steps = set()
    if "tutorial_start_time" not in st.session_state:
        st.session_state.tutorial_start_time = datetime.now()

def show_progress_bar():
    """顯示進度條"""
    total_steps = 6
    current_step = st.session_state.tutorial_step
    progress = min(current_step / total_steps, 1.0)
    
    st.progress(progress)
    st.caption(f"步驟 {current_step}/{total_steps} - 預計剩餘時間: {max(0, 5 - int((datetime.now() - st.session_state.tutorial_start_time).total_seconds() / 60))} 分鐘")

def step_0_welcome():
    """步驟0：歡迎頁面"""
    st.title("🎉 歡迎使用AI交易系統！")
    
    st.markdown("""
    ### 👋 您好！歡迎來到AI智能交易平台
    
    這個5分鐘的互動式教程將帶您：
    
    ✅ **了解系統功能** - 探索核心功能模組  
    ✅ **學習基本操作** - 掌握常用操作流程  
    ✅ **體驗實際功能** - 親手操作真實功能  
    ✅ **獲得使用技巧** - 學習最佳實踐方法  
    
    ### 🚀 開始前的準備
    
    請確保您已經：
    - ✅ 成功啟動系統
    - ✅ 看到此頁面正常顯示
    - ✅ 準備好5分鐘的學習時間
    """)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 開始教程", type="primary", use_container_width=True):
            st.session_state.tutorial_step = 1
            st.session_state.tutorial_completed_steps.add(0)
            st.rerun()
    
    st.info("💡 **提示**: 您可以隨時點擊左側邊欄的其他功能來探索系統，教程進度會自動保存")

def step_1_system_overview():
    """步驟1：系統概覽"""
    st.title("📊 系統功能概覽")
    
    st.markdown("""
    ### 🎯 AI交易系統的核心功能
    
    我們的系統包含以下主要模組：
    """)
    
    # 功能模組展示
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 📈 數據管理
        - 實時股價數據獲取
        - 歷史數據存儲和管理
        - 數據清理和驗證
        
        #### 🔬 特徵工程
        - 技術指標計算
        - 高級特徵提取
        - 特徵選擇和優化
        
        #### 🎯 策略管理
        - 交易策略創建
        - 策略參數配置
        - 策略性能評估
        """)
    
    with col2:
        st.markdown("""
        #### 📊 回測分析
        - 歷史數據回測
        - 策略表現分析
        - 風險指標計算
        
        #### 💼 投資組合管理
        - 資產配置優化
        - 風險管理控制
        - 投資組合監控
        
        #### 🤖 AI模型管理
        - 機器學習模型訓練
        - 模型預測和評估
        - 模型版本管理
        """)
    
    # 互動元素
    st.markdown("### 🎮 互動體驗")
    
    selected_module = st.selectbox(
        "選擇一個您最感興趣的功能模組：",
        ["數據管理", "特徵工程", "策略管理", "回測分析", "投資組合管理", "AI模型管理"]
    )
    
    module_descriptions = {
        "數據管理": "這是系統的基礎，負責獲取和管理所有交易相關的數據",
        "特徵工程": "將原始數據轉換為有用的特徵，是AI模型的重要輸入",
        "策略管理": "創建和管理交易策略，是系統的核心功能之一",
        "回測分析": "使用歷史數據測試策略表現，評估策略的有效性",
        "投資組合管理": "管理多個資產的投資組合，優化風險和收益",
        "AI模型管理": "使用機器學習技術預測市場趨勢和價格變化"
    }
    
    st.info(f"💡 **{selected_module}**: {module_descriptions[selected_module]}")
    
    # 導航按鈕
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("⬅️ 上一步"):
            st.session_state.tutorial_step = 0
            st.rerun()
    
    with col3:
        if st.button("下一步 ➡️", type="primary"):
            st.session_state.tutorial_step = 2
            st.session_state.tutorial_completed_steps.add(1)
            st.rerun()

def step_2_navigation():
    """步驟2：導航學習"""
    st.title("🧭 學習系統導航")
    
    st.markdown("""
    ### 📍 如何在系統中導航
    
    讓我們學習如何在系統中快速找到您需要的功能：
    """)
    
    # 導航說明
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("""
        #### 🎛️ 主要導航方式
        
        1. **左側邊欄** - 主要功能入口
           - 點擊不同功能模組
           - 快速切換頁面
        
        2. **頂部標籤** - 子功能導航
           - 在同一模組內切換
           - 訪問相關功能
        
        3. **快捷按鈕** - 常用操作
           - 一鍵執行功能
           - 快速設置選項
        """)
    
    with col2:
        st.markdown("""
        #### 🔍 實用導航技巧
        
        - **搜索功能**: 使用Ctrl+F快速查找
        - **書籤功能**: 收藏常用頁面
        - **歷史記錄**: 查看最近訪問的頁面
        - **快捷鍵**: 使用鍵盤快捷鍵
        
        #### 💡 新手建議
        
        - 先從"系統狀態"開始了解系統
        - 然後嘗試"數據管理"功能
        - 最後探索高級功能
        """)
    
    # 互動練習
    st.markdown("### 🎯 導航練習")
    
    st.info("👆 **練習**: 請嘗試點擊左側邊欄的不同功能，然後回到這個教程頁面")
    
    # 檢查用戶是否完成練習
    if st.button("✅ 我已經嘗試了導航"):
        st.success("太棒了！您已經掌握了基本導航技巧")
        st.balloons()
    
    # 導航按鈕
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("⬅️ 上一步"):
            st.session_state.tutorial_step = 1
            st.rerun()
    
    with col3:
        if st.button("下一步 ➡️", type="primary"):
            st.session_state.tutorial_step = 3
            st.session_state.tutorial_completed_steps.add(2)
            st.rerun()

def step_3_hands_on():
    """步驟3：實際操作體驗"""
    st.title("🛠️ 實際操作體驗")
    
    st.markdown("""
    ### 🎮 讓我們動手試試！
    
    現在我們來體驗一些實際功能，這將幫助您更好地理解系統的工作方式。
    """)
    
    # 選擇體驗功能
    experience_option = st.radio(
        "選擇您想要體驗的功能：",
        [
            "📊 查看系統狀態",
            "📈 模擬數據獲取",
            "🎯 創建簡單策略",
            "🔮 AI模型預測"
        ]
    )
    
    if experience_option == "📊 查看系統狀態":
        st.markdown("#### 🔍 系統狀態檢查")
        
        if st.button("檢查系統狀態"):
            with st.spinner("檢查中..."):
                time.sleep(2)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("系統狀態", "🟢 正常")
            with col2:
                st.metric("模組數量", "8/8")
            with col3:
                st.metric("健康度", "95%")
            
            st.success("✅ 系統運行正常！")
    
    elif experience_option == "📈 模擬數據獲取":
        st.markdown("#### 📊 數據獲取體驗")
        
        stock_symbol = st.selectbox("選擇股票代碼：", ["2330.TW", "2317.TW", "2454.TW"])
        
        if st.button("獲取股價數據"):
            with st.spinner("獲取數據中..."):
                time.sleep(2)
            
            # 模擬數據
            import pandas as pd
            import numpy as np
            
            dates = pd.date_range(end=datetime.now(), periods=5)
            data = pd.DataFrame({
                "日期": dates.strftime("%Y-%m-%d"),
                "開盤價": np.random.uniform(100, 110, 5),
                "收盤價": np.random.uniform(100, 110, 5),
                "成交量": np.random.randint(1000, 5000, 5)
            })
            
            st.dataframe(data)
            st.success(f"✅ 成功獲取 {stock_symbol} 的數據！")
    
    elif experience_option == "🎯 創建簡單策略":
        st.markdown("#### 🎯 策略創建體驗")
        
        strategy_name = st.text_input("策略名稱：", "我的第一個策略")
        strategy_type = st.selectbox("策略類型：", ["移動平均", "RSI", "布林帶"])
        
        if st.button("創建策略"):
            with st.spinner("創建中..."):
                time.sleep(2)
            
            st.success(f"✅ 策略 '{strategy_name}' 創建成功！")
            st.info(f"策略類型: {strategy_type}")
    
    elif experience_option == "🔮 AI模型預測":
        st.markdown("#### 🤖 AI預測體驗")
        
        model_type = st.selectbox("選擇模型：", ["LSTM股價預測", "隨機森林分類", "情感分析"])
        
        if st.button("執行預測"):
            with st.spinner("AI預測中..."):
                time.sleep(3)
            
            # 模擬預測結果
            if model_type == "LSTM股價預測":
                prediction = np.random.uniform(100, 200)
                st.metric("預測價格", f"${prediction:.2f}")
            elif model_type == "隨機森林分類":
                prediction = np.random.choice(["買入", "賣出", "持有"])
                st.metric("預測動作", prediction)
            else:
                sentiment = np.random.choice(["正面", "負面", "中性"])
                st.metric("市場情感", sentiment)
            
            st.success("✅ AI預測完成！")
    
    # 導航按鈕
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("⬅️ 上一步"):
            st.session_state.tutorial_step = 2
            st.rerun()
    
    with col3:
        if st.button("下一步 ➡️", type="primary"):
            st.session_state.tutorial_step = 4
            st.session_state.tutorial_completed_steps.add(3)
            st.rerun()

def step_4_best_practices():
    """步驟4：最佳實踐"""
    st.title("💡 使用技巧和最佳實踐")
    
    st.markdown("""
    ### 🎯 讓您更高效地使用系統
    
    基於我們的經驗，這些技巧將幫助您更好地使用AI交易系統：
    """)
    
    # 技巧分類
    tab1, tab2, tab3 = st.tabs(["🚀 入門技巧", "⚡ 效率提升", "🛡️ 風險管理"])
    
    with tab1:
        st.markdown("""
        #### 🌟 新手必知技巧
        
        1. **從簡單開始**
           - 先熟悉基本功能
           - 使用預設參數開始
           - 逐步學習高級功能
        
        2. **定期檢查系統狀態**
           - 每天查看系統健康度
           - 確保數據源正常
           - 監控模型表現
        
        3. **保存重要設置**
           - 備份策略配置
           - 記錄成功的參數
           - 建立個人使用手冊
        """)
    
    with tab2:
        st.markdown("""
        #### ⚡ 提高使用效率
        
        1. **使用快捷功能**
           - 收藏常用頁面
           - 設置自動刷新
           - 使用批量操作
        
        2. **優化工作流程**
           - 建立標準操作流程
           - 使用模板和預設
           - 自動化重複任務
        
        3. **數據管理技巧**
           - 定期清理舊數據
           - 使用數據篩選功能
           - 設置數據更新提醒
        """)
    
    with tab3:
        st.markdown("""
        #### 🛡️ 風險管理要點
        
        1. **謹慎使用AI預測**
           - 理解模型限制
           - 結合多個指標
           - 不要完全依賴單一模型
        
        2. **回測驗證策略**
           - 使用足夠的歷史數據
           - 考慮不同市場環境
           - 定期重新評估策略
        
        3. **設置安全措施**
           - 設置止損點
           - 分散投資風險
           - 定期檢查投資組合
        """)
    
    # 互動檢查清單
    st.markdown("### ✅ 最佳實踐檢查清單")
    
    checklist_items = [
        "我已經了解系統的主要功能",
        "我知道如何導航到不同的功能模組",
        "我已經嘗試了基本的操作功能",
        "我理解了風險管理的重要性",
        "我會定期檢查系統狀態"
    ]
    
    completed_items = 0
    for item in checklist_items:
        if st.checkbox(item):
            completed_items += 1
    
    progress = completed_items / len(checklist_items)
    st.progress(progress)
    st.caption(f"完成度: {completed_items}/{len(checklist_items)}")
    
    if completed_items == len(checklist_items):
        st.success("🎉 太棒了！您已經掌握了所有最佳實踐！")
    
    # 導航按鈕
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button("⬅️ 上一步"):
            st.session_state.tutorial_step = 3
            st.rerun()
    
    with col3:
        if st.button("下一步 ➡️", type="primary"):
            st.session_state.tutorial_step = 5
            st.session_state.tutorial_completed_steps.add(4)
            st.rerun()

def step_5_completion():
    """步驟5：完成教程"""
    st.title("🎉 恭喜！教程完成")
    
    # 計算用時
    elapsed_time = (datetime.now() - st.session_state.tutorial_start_time).total_seconds() / 60
    
    st.markdown(f"""
    ### 🏆 您已經成功完成了新手教程！
    
    **用時**: {elapsed_time:.1f} 分鐘  
    **完成步驟**: {len(st.session_state.tutorial_completed_steps)}/5
    
    ### 🎯 您現在已經學會了：
    
    ✅ **系統功能概覽** - 了解各個功能模組的作用  
    ✅ **導航技巧** - 快速找到需要的功能  
    ✅ **實際操作** - 親手體驗核心功能  
    ✅ **最佳實踐** - 高效安全地使用系統  
    
    ### 🚀 接下來您可以：
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        #### 🎮 立即開始使用
        
        - 📊 查看實時市場數據
        - 🎯 創建您的第一個交易策略
        - 📈 進行歷史數據回測
        - 🤖 嘗試AI模型預測
        """)
    
    with col2:
        st.markdown("""
        #### 📚 深入學習
        
        - 📖 閱讀詳細文檔
        - 🎥 觀看進階教程
        - 💬 加入用戶社群
        - 🆘 聯繫技術支援
        """)
    
    # 快速開始按鈕
    st.markdown("### 🚀 快速開始")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 數據管理", use_container_width=True):
            st.session_state.current_view = "data_management"
            st.rerun()
    
    with col2:
        if st.button("🎯 策略管理", use_container_width=True):
            st.session_state.current_view = "strategy_management"
            st.rerun()
    
    with col3:
        if st.button("📈 回測分析", use_container_width=True):
            st.session_state.current_view = "backtest_analysis"
            st.rerun()
    
    with col4:
        if st.button("🤖 AI模型", use_container_width=True):
            st.session_state.current_view = "ai_model_management"
            st.rerun()
    
    # 反饋收集
    st.markdown("### 💬 您的反饋")
    
    with st.expander("📝 教程反饋 (可選)"):
        rating = st.select_slider(
            "教程評分：",
            options=[1, 2, 3, 4, 5],
            value=5,
            format_func=lambda x: "⭐" * x
        )
        
        feedback = st.text_area("您的建議和意見：")
        
        if st.button("提交反饋"):
            st.success("感謝您的反饋！這將幫助我們改進教程。")
    
    # 重新開始選項
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔄 重新開始教程"):
            # 重置教程狀態
            st.session_state.tutorial_step = 0
            st.session_state.tutorial_completed_steps = set()
            st.session_state.tutorial_start_time = datetime.now()
            st.rerun()
    
    with col2:
        if st.button("🏠 返回主頁", type="primary"):
            st.session_state.current_view = "dashboard"
            st.rerun()

def show():
    """主顯示函數"""
    initialize_tutorial_state()
    
    # 顯示進度條
    show_progress_bar()
    
    # 根據步驟顯示對應內容
    step_functions = [
        step_0_welcome,
        step_1_system_overview,
        step_2_navigation,
        step_3_hands_on,
        step_4_best_practices,
        step_5_completion
    ]
    
    current_step = st.session_state.tutorial_step
    if 0 <= current_step < len(step_functions):
        step_functions[current_step]()
    else:
        st.error("教程步驟錯誤，請重新開始")
        if st.button("重新開始"):
            st.session_state.tutorial_step = 0
            st.rerun()

if __name__ == "__main__":
    show()
