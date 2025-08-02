"""
AI 模型推論模組

此模組提供模型推論的完整功能，包括：
- 單一樣本推論
- 批量推論
- 實時推論
- 推論結果分析
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any

from .base import get_ai_model_service, safe_strftime, create_info_card


def show_model_inference():
    """顯示模型推論頁面"""
    st.header("🔮 模型推論")
    
    # 獲取可用模型
    service = get_ai_model_service()
    models = service.get_models()
    active_models = [m for m in models if m.get('status') == 'active']
    
    if not active_models:
        st.warning("⚠️ 沒有可用的活躍模型")
        return
    
    # 模型選擇
    model_options = {f"{m['name']} ({m['id']})": m for m in active_models}
    selected_model_key = st.selectbox("選擇模型", options=list(model_options.keys()))
    selected_model = model_options[selected_model_key]
    
    # 推論模式選擇
    inference_modes = {
        "單一樣本推論": "single",
        "批量推論": "batch",
        "實時推論": "realtime"
    }
    
    selected_mode = st.selectbox("推論模式", options=list(inference_modes.keys()))
    mode_key = inference_modes[selected_mode]
    
    # 根據模式顯示對應介面
    if mode_key == "single":
        show_single_inference(selected_model, service)
    elif mode_key == "batch":
        show_batch_inference(selected_model, service)
    elif mode_key == "realtime":
        show_realtime_inference(selected_model, service)


def show_single_inference(model: Dict, service):
    """顯示單一樣本推論介面"""
    st.subheader("🎯 單一樣本推論")
    
    create_info_card(
        "單一樣本推論",
        "輸入單一樣本的特徵值，獲得模型預測結果和置信度。",
        "🎯"
    )
    
    # 特徵輸入表單
    with st.form("single_inference_form"):
        st.write("**輸入特徵值：**")
        
        # 模擬特徵欄位
        features = ['price', 'volume', 'ma_5', 'ma_20', 'rsi', 'macd']
        feature_values = {}
        
        col1, col2 = st.columns(2)
        
        for i, feature in enumerate(features):
            with col1 if i % 2 == 0 else col2:
                feature_values[feature] = st.number_input(
                    f"{feature}",
                    value=0.0,
                    format="%.4f"
                )
        
        # 推論按鈕
        submitted = st.form_submit_button("🔮 開始推論", use_container_width=True)
        
        if submitted:
            _perform_single_inference(model, feature_values, service)


def show_batch_inference(model: Dict, service):
    """顯示批量推論介面"""
    st.subheader("📊 批量推論")
    
    create_info_card(
        "批量推論",
        "上傳包含多個樣本的檔案，進行批量預測並下載結果。",
        "📊"
    )
    
    # 檔案上傳
    uploaded_file = st.file_uploader(
        "上傳資料檔案",
        type=['csv', 'xlsx'],
        help="檔案應包含模型所需的特徵欄位"
    )
    
    if uploaded_file is not None:
        try:
            # 讀取檔案
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.write("**資料預覽：**")
            st.dataframe(df.head(), use_container_width=True)
            
            # 批量推論設定
            col1, col2 = st.columns(2)
            
            with col1:
                batch_size = st.number_input("批次大小", min_value=1, max_value=1000, value=100)
                include_confidence = st.checkbox("包含置信度", value=True)
            
            with col2:
                output_format = st.selectbox("輸出格式", ["CSV", "Excel", "JSON"])
                add_timestamp = st.checkbox("添加時間戳", value=True)
            
            # 開始批量推論
            if st.button("🚀 開始批量推論", use_container_width=True):
                _perform_batch_inference(model, df, batch_size, include_confidence, 
                                       output_format, add_timestamp, service)
                
        except Exception as e:
            st.error(f"❌ 檔案讀取失敗: {e}")


def show_realtime_inference(model: Dict, service):
    """顯示實時推論介面"""
    st.subheader("⚡ 實時推論")
    
    create_info_card(
        "實時推論",
        "連接即時資料流，進行持續的模型推論和監控。",
        "⚡"
    )
    
    # 實時推論設定
    col1, col2 = st.columns(2)
    
    with col1:
        data_source = st.selectbox(
            "資料來源",
            ["模擬資料流", "WebSocket", "Kafka", "Redis Stream"]
        )
        
        update_interval = st.slider(
            "更新間隔 (秒)",
            min_value=1,
            max_value=60,
            value=5
        )
    
    with col2:
        max_records = st.number_input(
            "最大記錄數",
            min_value=10,
            max_value=1000,
            value=100
        )
        
        auto_scroll = st.checkbox("自動滾動", value=True)
    
    # 控制按鈕
    col1, col2, col3 = st.columns(3)
    
    with col1:
        start_button = st.button("▶️ 開始", use_container_width=True)
    
    with col2:
        stop_button = st.button("⏸️ 停止", use_container_width=True)
    
    with col3:
        clear_button = st.button("🗑️ 清除", use_container_width=True)
    
    # 實時結果顯示區域
    if start_button:
        _start_realtime_inference(model, data_source, update_interval, max_records, service)


def _perform_single_inference(model: Dict, features: Dict, service) -> None:
    """執行單一樣本推論"""
    try:
        with st.spinner("正在進行推論..."):
            # 模擬推論結果
            result = service.predict(model['id'], features)
            
            st.success("✅ 推論完成！")
            
            # 顯示結果
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("預測結果", f"{result['predictions'][0]:.4f}")
                st.metric("置信度", f"{result['confidence']:.3f}")
            
            with col2:
                # 顯示特徵重要性（模擬）
                feature_importance = {
                    'price': 0.35,
                    'volume': 0.25,
                    'ma_5': 0.20,
                    'ma_20': 0.15,
                    'rsi': 0.03,
                    'macd': 0.02
                }
                
                st.write("**特徵貢獻度：**")
                for feature, importance in feature_importance.items():
                    st.write(f"- {feature}: {importance:.3f}")
            
            # 推論歷史
            if 'inference_history' not in st.session_state:
                st.session_state.inference_history = []
            
            st.session_state.inference_history.append({
                'timestamp': datetime.now(),
                'model': model['name'],
                'prediction': result['predictions'][0],
                'confidence': result['confidence']
            })
            
            # 顯示推論歷史
            if st.session_state.inference_history:
                st.subheader("📈 推論歷史")
                history_df = pd.DataFrame(st.session_state.inference_history)
                st.dataframe(history_df, use_container_width=True)
                
    except Exception as e:
        st.error(f"❌ 推論失敗: {e}")


def _perform_batch_inference(model: Dict, df: pd.DataFrame, batch_size: int, 
                           include_confidence: bool, output_format: str, 
                           add_timestamp: bool, service) -> None:
    """執行批量推論"""
    try:
        with st.spinner(f"正在處理 {len(df)} 個樣本..."):
            # 模擬批量推論
            predictions = np.random.random(len(df))
            confidences = np.random.uniform(0.7, 0.95, len(df))
            
            # 準備結果資料框
            result_df = df.copy()
            result_df['prediction'] = predictions
            
            if include_confidence:
                result_df['confidence'] = confidences
            
            if add_timestamp:
                result_df['inference_timestamp'] = datetime.now()
            
            st.success(f"✅ 批量推論完成！處理了 {len(df)} 個樣本")
            
            # 顯示結果預覽
            st.subheader("📊 結果預覽")
            st.dataframe(result_df.head(10), use_container_width=True)
            
            # 提供下載
            _provide_download(result_df, output_format, model['name'])
            
    except Exception as e:
        st.error(f"❌ 批量推論失敗: {e}")


def _start_realtime_inference(model: Dict, data_source: str, interval: int, 
                            max_records: int, service) -> None:
    """開始實時推論"""
    st.info(f"🔄 實時推論已啟動 - 資料來源: {data_source}")
    
    # 創建實時資料顯示區域
    placeholder = st.empty()
    
    # 模擬實時資料
    if 'realtime_data' not in st.session_state:
        st.session_state.realtime_data = []
    
    # 生成新的資料點
    new_data = {
        'timestamp': datetime.now(),
        'prediction': np.random.random(),
        'confidence': np.random.uniform(0.7, 0.95),
        'features': {
            'price': np.random.uniform(100, 200),
            'volume': np.random.uniform(1000, 10000)
        }
    }
    
    st.session_state.realtime_data.append(new_data)
    
    # 限制記錄數量
    if len(st.session_state.realtime_data) > max_records:
        st.session_state.realtime_data = st.session_state.realtime_data[-max_records:]
    
    # 顯示實時資料
    with placeholder.container():
        st.subheader("📊 實時推論結果")
        
        if st.session_state.realtime_data:
            df = pd.DataFrame([
                {
                    '時間': safe_strftime(d['timestamp']),
                    '預測值': f"{d['prediction']:.4f}",
                    '置信度': f"{d['confidence']:.3f}",
                    '價格': f"{d['features']['price']:.2f}",
                    '成交量': f"{d['features']['volume']:.0f}"
                }
                for d in st.session_state.realtime_data[-10:]  # 只顯示最近10筆
            ])
            
            st.dataframe(df, use_container_width=True)


def _provide_download(df: pd.DataFrame, format_type: str, model_name: str) -> None:
    """提供結果下載"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"inference_results_{model_name}_{timestamp}"
    
    if format_type == "CSV":
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 下載 CSV",
            data=csv,
            file_name=f"{filename}.csv",
            mime="text/csv"
        )
    
    elif format_type == "Excel":
        # 注意：實際實作需要安裝 openpyxl
        st.info("Excel 下載功能需要安裝 openpyxl 套件")
    
    elif format_type == "JSON":
        json_str = df.to_json(orient='records', indent=2)
        st.download_button(
            label="📥 下載 JSON",
            data=json_str,
            file_name=f"{filename}.json",
            mime="application/json"
        )
