#!/usr/bin/env python3
"""
AI模型管理頁面
提供AI模型的創建、訓練、預測和管理功能
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import json
import os
import sys

# 添加項目根目錄到路徑
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

def initialize_ai_service():
    """初始化AI模型服務"""
    try:
        from src.core.ai_model_service import AIModelService
        return AIModelService()
    except Exception as e:
        st.error(f"AI模型服務初始化失敗: {e}")
        return None

def show_service_status(ai_service):
    """顯示服務狀態"""
    if not ai_service:
        st.error("❌ AI模型服務不可用")
        return
    
    status = ai_service.get_service_status()
    
    st.subheader("🔍 服務狀態")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("服務狀態", "🟢 運行中" if status["status"] == "running" else "🔴 停止")
    
    with col2:
        st.metric("模型數量", status["models_count"])
    
    with col3:
        st.metric("訓練任務", status["active_training_tasks"])
    
    with col4:
        components_status = sum(status["components"].values())
        total_components = len(status["components"])
        st.metric("組件可用性", f"{components_status}/{total_components}")
    
    # 顯示組件詳情
    with st.expander("📋 組件詳情"):
        for component, available in status["components"].items():
            status_icon = "✅" if available else "❌"
            st.write(f"{status_icon} {component}: {'可用' if available else '不可用'}")

def show_model_list(ai_service):
    """顯示模型列表"""
    if not ai_service:
        return
    
    st.subheader("📚 模型列表")
    
    # 篩選選項
    col1, col2, col3 = st.columns(3)
    
    with col1:
        model_type_filter = st.selectbox(
            "模型類型",
            ["全部", "time_series", "classification", "nlp", "regression"],
            key="model_type_filter"
        )
    
    with col2:
        status_filter = st.selectbox(
            "狀態篩選",
            ["全部", "ready", "training", "created", "failed"],
            key="status_filter"
        )
    
    with col3:
        if st.button("🔄 刷新列表"):
            st.rerun()
    
    # 獲取模型列表
    try:
        models = ai_service.list_models(
            model_type=None if model_type_filter == "全部" else model_type_filter
        )
        
        if status_filter != "全部":
            models = [m for m in models if m.get("status") == status_filter]
        
        if not models:
            st.info("📭 暫無模型")
            return
        
        # 顯示模型卡片
        for model in models:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                
                with col1:
                    st.write(f"**{model['name']}**")
                    st.caption(model.get('description', '無描述'))
                
                with col2:
                    status_color = {
                        "ready": "🟢",
                        "training": "🟡",
                        "created": "🔵",
                        "failed": "🔴"
                    }.get(model.get('status'), "⚪")
                    st.write(f"{status_color} {model.get('status', 'unknown')}")
                
                with col3:
                    accuracy = model.get('accuracy', 0)
                    if accuracy > 0:
                        st.metric("準確率", f"{accuracy:.2%}")
                    else:
                        st.write("未評估")
                
                with col4:
                    if st.button("📊 詳情", key=f"detail_{model['id']}"):
                        st.session_state.selected_model = model['id']
                        st.session_state.show_model_detail = True
                
                st.markdown("---")
    
    except Exception as e:
        st.error(f"獲取模型列表失敗: {e}")

def show_model_detail(ai_service, model_id):
    """顯示模型詳情"""
    if not ai_service:
        return
    
    try:
        model_info = ai_service.get_model_info(model_id)
        if not model_info:
            st.error("模型不存在")
            return
        
        st.subheader(f"📊 模型詳情: {model_info['name']}")
        
        # 基本信息
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**基本信息**")
            st.write(f"ID: {model_info['id']}")
            st.write(f"類型: {model_info.get('model_type', 'unknown')}")
            st.write(f"狀態: {model_info.get('status', 'unknown')}")
            st.write(f"創建時間: {model_info.get('created_at', 'unknown')}")
        
        with col2:
            st.write("**性能指標**")
            try:
                performance = ai_service.get_model_performance(model_id)
                st.metric("準確率", f"{performance['accuracy']:.2%}")
                st.metric("精確率", f"{performance['precision']:.2%}")
                st.metric("召回率", f"{performance['recall']:.2%}")
            except:
                st.write("性能指標不可用")
        
        # 特徵信息
        if 'features' in model_info:
            st.write("**輸入特徵**")
            features_df = pd.DataFrame({
                "特徵名稱": model_info['features']
            })
            st.dataframe(features_df, use_container_width=True)
        
        # 操作按鈕
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔮 進行預測"):
                st.session_state.show_prediction = True
        
        with col2:
            if model_info.get('status') == 'created':
                if st.button("🎯 開始訓練"):
                    st.session_state.show_training = True
        
        with col3:
            if st.button("🗑️ 刪除模型"):
                if ai_service.delete_model(model_id):
                    st.success("模型已刪除")
                    st.session_state.show_model_detail = False
                    st.rerun()
                else:
                    st.error("刪除失敗")
    
    except Exception as e:
        st.error(f"獲取模型詳情失敗: {e}")

def show_create_model(ai_service):
    """顯示創建模型界面"""
    if not ai_service:
        return
    
    st.subheader("🆕 創建新模型")
    
    with st.form("create_model_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            model_name = st.text_input("模型名稱", placeholder="例如：股價預測模型")
            model_type = st.selectbox(
                "模型類型",
                ["time_series", "classification", "regression", "nlp"]
            )
        
        with col2:
            description = st.text_area("模型描述", placeholder="描述模型的用途和特點")
        
        # 模型參數
        st.write("**模型參數**")
        
        if model_type == "time_series":
            lookback_window = st.number_input("回看窗口", min_value=1, max_value=100, value=30)
            prediction_horizon = st.number_input("預測範圍", min_value=1, max_value=30, value=1)
            parameters = {
                "lookback_window": lookback_window,
                "prediction_horizon": prediction_horizon
            }
        
        elif model_type == "classification":
            n_estimators = st.number_input("樹的數量", min_value=10, max_value=1000, value=100)
            max_depth = st.number_input("最大深度", min_value=1, max_value=50, value=10)
            parameters = {
                "n_estimators": n_estimators,
                "max_depth": max_depth
            }
        
        else:
            parameters = {}
        
        submitted = st.form_submit_button("🚀 創建模型")
        
        if submitted:
            if not model_name:
                st.error("請輸入模型名稱")
                return
            
            try:
                model_config = {
                    "name": model_name,
                    "model_type": model_type,
                    "description": description,
                    "parameters": parameters
                }
                
                model_info = ai_service.create_new_model(model_config)
                st.success(f"模型創建成功！ID: {model_info['id']}")
                
                # 清除表單並刷新
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"創建模型失敗: {e}")

def show_prediction_interface(ai_service, model_id):
    """顯示預測界面"""
    if not ai_service:
        return
    
    st.subheader("🔮 模型預測")
    
    model_info = ai_service.get_model_info(model_id)
    if not model_info:
        st.error("模型不存在")
        return
    
    st.write(f"使用模型: **{model_info['name']}**")
    
    # 輸入數據
    with st.form("prediction_form"):
        st.write("**輸入數據**")
        
        # 根據模型類型顯示不同的輸入界面
        if model_info.get('model_type') == 'time_series':
            col1, col2 = st.columns(2)
            with col1:
                open_price = st.number_input("開盤價", value=100.0)
                high_price = st.number_input("最高價", value=105.0)
            with col2:
                low_price = st.number_input("最低價", value=95.0)
                close_price = st.number_input("收盤價", value=102.0)
            
            volume = st.number_input("成交量", value=1000000)
            
            input_data = {
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume
            }
        
        else:
            # 通用輸入界面
            input_text = st.text_area("輸入數據 (JSON格式)", 
                                    value='{"feature1": 1.0, "feature2": 2.0}')
            try:
                input_data = json.loads(input_text)
            except:
                input_data = {}
        
        predict_button = st.form_submit_button("🎯 開始預測")
        
        if predict_button:
            try:
                with st.spinner("預測中..."):
                    result = ai_service.predict(model_id, input_data)
                
                st.success("預測完成！")
                
                # 顯示預測結果
                st.write("**預測結果**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'prediction' in result:
                        st.metric("預測值", f"{result['prediction']:.2f}")
                    if 'class' in result:
                        st.metric("預測類別", result['class'])
                
                with col2:
                    if 'confidence' in result:
                        st.metric("置信度", f"{result['confidence']:.2%}")
                    if 'trend' in result:
                        st.metric("趨勢", result['trend'])
                
                # 顯示完整結果
                with st.expander("完整結果"):
                    st.json(result)
            
            except Exception as e:
                st.error(f"預測失敗: {e}")

def show():
    """主顯示函數"""
    st.title("🤖 AI模型管理")
    
    # 初始化AI服務
    ai_service = initialize_ai_service()
    
    # 側邊欄導航
    with st.sidebar:
        st.subheader("🧭 導航")
        
        page = st.radio(
            "選擇功能",
            ["服務狀態", "模型列表", "創建模型"],
            key="ai_model_page"
        )
    
    # 顯示對應頁面
    if page == "服務狀態":
        show_service_status(ai_service)
    
    elif page == "模型列表":
        show_model_list(ai_service)
        
        # 顯示模型詳情
        if st.session_state.get("show_model_detail") and st.session_state.get("selected_model"):
            st.markdown("---")
            show_model_detail(ai_service, st.session_state.selected_model)
            
            # 顯示預測界面
            if st.session_state.get("show_prediction"):
                st.markdown("---")
                show_prediction_interface(ai_service, st.session_state.selected_model)
    
    elif page == "創建模型":
        show_create_model(ai_service)

if __name__ == "__main__":
    show()
