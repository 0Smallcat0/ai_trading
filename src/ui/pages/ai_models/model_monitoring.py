"""
AI 模型監控模組

此模組提供模型監控功能，包括：
- 實時效能監控
- 歷史分析
- 效能比較
- 異常檢測
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .base import get_ai_model_service, safe_strftime, create_info_card


def show_model_performance_monitoring():
    """顯示模型效能監控頁面"""
    st.header("📊 模型效能監控")
    
    # 監控功能選擇
    monitoring_options = {
        "實時監控": "realtime",
        "歷史分析": "historical",
        "效能比較": "comparison",
        "異常檢測": "anomaly"
    }
    
    selected_option = st.selectbox("監控功能", options=list(monitoring_options.keys()))
    option_key = monitoring_options[selected_option]
    
    # 根據選擇顯示對應功能
    if option_key == "realtime":
        show_realtime_monitoring()
    elif option_key == "historical":
        show_historical_analysis()
    elif option_key == "comparison":
        show_performance_comparison()
    elif option_key == "anomaly":
        show_anomaly_detection()


def show_realtime_monitoring():
    """顯示實時監控"""
    st.subheader("⚡ 實時效能監控")
    
    create_info_card(
        "實時監控",
        "監控模型的即時效能指標，包括預測準確率、響應時間和資源使用情況。",
        "⚡"
    )
    
    # 獲取模型列表
    service = get_ai_model_service()
    models = service.get_models()
    active_models = [m for m in models if m.get('status') == 'active']
    
    if not active_models:
        st.warning("⚠️ 沒有活躍的模型可供監控")
        return
    
    # 模型選擇
    model_options = {f"{m['name']} ({m['id']})": m for m in active_models}
    selected_models = st.multiselect(
        "選擇要監控的模型",
        options=list(model_options.keys()),
        default=list(model_options.keys())[:3]  # 預設選擇前3個
    )
    
    if not selected_models:
        st.info("請選擇至少一個模型進行監控")
        return
    
    # 監控設定
    col1, col2, col3 = st.columns(3)
    
    with col1:
        refresh_interval = st.selectbox("刷新間隔", ["5秒", "10秒", "30秒", "1分鐘"], index=1)
    
    with col2:
        metric_type = st.selectbox("主要指標", ["準確率", "響應時間", "吞吐量", "錯誤率"])
    
    with col3:
        auto_refresh = st.checkbox("自動刷新", value=True)
    
    # 顯示實時指標
    _show_realtime_metrics(selected_models, model_options, metric_type)
    
    # 實時圖表
    _show_realtime_charts(selected_models, model_options)


def show_historical_analysis():
    """顯示歷史分析"""
    st.subheader("📈 歷史效能分析")
    
    create_info_card(
        "歷史分析",
        "分析模型在過去一段時間內的效能趨勢和變化模式。",
        "📈"
    )
    
    # 時間範圍選擇
    col1, col2 = st.columns(2)
    
    with col1:
        time_range = st.selectbox(
            "時間範圍",
            ["過去24小時", "過去7天", "過去30天", "過去3個月", "自定義"]
        )
    
    with col2:
        if time_range == "自定義":
            date_range = st.date_input(
                "選擇日期範圍",
                value=(datetime.now() - timedelta(days=7), datetime.now()),
                max_value=datetime.now()
            )
    
    # 分析維度選擇
    analysis_dimensions = st.multiselect(
        "分析維度",
        ["準確率趨勢", "響應時間分佈", "預測量統計", "錯誤率變化", "資源使用情況"],
        default=["準確率趨勢", "響應時間分佈"]
    )
    
    if st.button("🔍 開始分析", use_container_width=True):
        _perform_historical_analysis(time_range, analysis_dimensions)


def show_performance_comparison():
    """顯示效能比較"""
    st.subheader("⚖️ 模型效能比較")
    
    create_info_card(
        "效能比較",
        "比較不同模型在相同時間段內的效能表現。",
        "⚖️"
    )
    
    # 獲取模型列表
    service = get_ai_model_service()
    models = service.get_models()
    
    # 模型選擇
    model_options = {f"{m['name']} ({m['id']})": m for m in models}
    selected_models = st.multiselect(
        "選擇要比較的模型",
        options=list(model_options.keys()),
        default=list(model_options.keys())[:2]
    )
    
    if len(selected_models) < 2:
        st.info("請選擇至少兩個模型進行比較")
        return
    
    # 比較指標選擇
    comparison_metrics = st.multiselect(
        "比較指標",
        ["準確率", "F1分數", "精確率", "召回率", "響應時間", "吞吐量"],
        default=["準確率", "響應時間"]
    )
    
    # 時間範圍
    comparison_period = st.selectbox(
        "比較時間段",
        ["過去24小時", "過去7天", "過去30天"]
    )
    
    if st.button("📊 開始比較", use_container_width=True):
        _perform_model_comparison(selected_models, comparison_metrics, comparison_period)


def show_anomaly_detection():
    """顯示異常檢測"""
    st.subheader("🚨 異常檢測")
    
    create_info_card(
        "異常檢測",
        "自動檢測模型效能中的異常情況，包括準確率下降、響應時間異常等。",
        "🚨"
    )
    
    # 異常檢測設定
    col1, col2 = st.columns(2)
    
    with col1:
        detection_sensitivity = st.slider(
            "檢測敏感度",
            min_value=1,
            max_value=10,
            value=5,
            help="數值越高，檢測越敏感"
        )
        
        alert_threshold = st.number_input(
            "警報閾值",
            min_value=0.1,
            max_value=1.0,
            value=0.8,
            step=0.1,
            help="準確率低於此值時觸發警報"
        )
    
    with col2:
        detection_window = st.selectbox(
            "檢測時間窗口",
            ["過去1小時", "過去6小時", "過去24小時"]
        )
        
        enable_notifications = st.checkbox("啟用通知", value=True)
    
    # 異常類型選擇
    anomaly_types = st.multiselect(
        "檢測異常類型",
        ["準確率異常", "響應時間異常", "錯誤率異常", "資料漂移", "模型退化"],
        default=["準確率異常", "響應時間異常"]
    )
    
    if st.button("🔍 開始檢測", use_container_width=True):
        _perform_anomaly_detection(detection_sensitivity, alert_threshold, 
                                 detection_window, anomaly_types)


def _show_realtime_metrics(selected_models: List[str], model_options: Dict, metric_type: str):
    """顯示實時指標"""
    st.subheader("📊 即時效能指標")
    
    # 為每個選中的模型顯示指標
    cols = st.columns(min(len(selected_models), 4))
    
    for i, model_key in enumerate(selected_models):
        model = model_options[model_key]
        
        with cols[i % 4]:
            # 生成模擬指標
            accuracy = np.random.uniform(0.75, 0.95)
            response_time = np.random.uniform(50, 200)
            throughput = np.random.uniform(100, 1000)
            error_rate = np.random.uniform(0.01, 0.05)
            
            st.metric(
                f"{model['name']}",
                f"{accuracy:.3f}" if metric_type == "準確率" else f"{response_time:.0f}ms",
                delta=f"+{np.random.uniform(0.001, 0.01):.3f}" if metric_type == "準確率" else f"-{np.random.uniform(1, 10):.0f}ms"
            )
            
            # 狀態指示器
            status_color = "🟢" if accuracy > 0.8 else "🟡" if accuracy > 0.7 else "🔴"
            st.write(f"狀態: {status_color}")


def _show_realtime_charts(selected_models: List[str], model_options: Dict):
    """顯示實時圖表"""
    st.subheader("📈 實時效能圖表")
    
    # 生成模擬時間序列資料
    time_points = pd.date_range(
        start=datetime.now() - timedelta(hours=1),
        end=datetime.now(),
        freq='1min'
    )
    
    fig = go.Figure()
    
    for model_key in selected_models:
        model = model_options[model_key]
        
        # 生成模擬準確率資料
        accuracy_data = np.random.uniform(0.75, 0.95, len(time_points))
        accuracy_data = pd.Series(accuracy_data).rolling(window=5).mean()  # 平滑化
        
        fig.add_trace(go.Scatter(
            x=time_points,
            y=accuracy_data,
            mode='lines+markers',
            name=model['name'],
            line=dict(width=2)
        ))
    
    fig.update_layout(
        title="模型準確率實時趨勢",
        xaxis_title="時間",
        yaxis_title="準確率",
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, use_container_width=True)


def _perform_historical_analysis(time_range: str, dimensions: List[str]):
    """執行歷史分析"""
    with st.spinner("正在分析歷史資料..."):
        st.success("✅ 歷史分析完成！")
        
        # 生成模擬歷史資料
        if "準確率趨勢" in dimensions:
            _show_accuracy_trend()
        
        if "響應時間分佈" in dimensions:
            _show_response_time_distribution()


def _perform_model_comparison(models: List[str], metrics: List[str], period: str):
    """執行模型比較"""
    with st.spinner("正在比較模型效能..."):
        st.success("✅ 模型比較完成！")
        
        # 生成比較圖表
        _show_model_comparison_chart(models, metrics)


def _perform_anomaly_detection(sensitivity: int, threshold: float, window: str, types: List[str]):
    """執行異常檢測"""
    with st.spinner("正在檢測異常..."):
        # 模擬異常檢測結果
        anomalies_found = np.random.choice([True, False], p=[0.3, 0.7])
        
        if anomalies_found:
            st.warning("⚠️ 檢測到異常情況！")
            
            # 顯示異常詳情
            anomaly_data = {
                "時間": [datetime.now() - timedelta(minutes=30), datetime.now() - timedelta(minutes=15)],
                "模型": ["模型A", "模型B"],
                "異常類型": ["準確率異常", "響應時間異常"],
                "嚴重程度": ["中等", "高"],
                "描述": ["準確率下降至0.65", "響應時間超過500ms"]
            }
            
            anomaly_df = pd.DataFrame(anomaly_data)
            st.dataframe(anomaly_df, use_container_width=True)
            
        else:
            st.success("✅ 未檢測到異常情況")


def _show_accuracy_trend():
    """顯示準確率趨勢"""
    st.subheader("📈 準確率趨勢分析")
    
    # 生成模擬資料
    dates = pd.date_range(start=datetime.now() - timedelta(days=7), end=datetime.now(), freq='1H')
    accuracy = 0.85 + np.random.normal(0, 0.05, len(dates))
    accuracy = np.clip(accuracy, 0.7, 0.95)
    
    fig = px.line(
        x=dates,
        y=accuracy,
        title="過去7天準確率趨勢",
        labels={'x': '時間', 'y': '準確率'}
    )
    
    st.plotly_chart(fig, use_container_width=True)


def _show_response_time_distribution():
    """顯示響應時間分佈"""
    st.subheader("⏱️ 響應時間分佈")
    
    # 生成模擬響應時間資料
    response_times = np.random.lognormal(mean=4, sigma=0.5, size=1000)
    
    fig = px.histogram(
        x=response_times,
        nbins=50,
        title="響應時間分佈",
        labels={'x': '響應時間 (ms)', 'y': '頻次'}
    )
    
    st.plotly_chart(fig, use_container_width=True)


def _show_model_comparison_chart(models: List[str], metrics: List[str]):
    """顯示模型比較圖表"""
    st.subheader("📊 模型效能比較")
    
    # 生成比較資料
    comparison_data = []
    for model in models:
        for metric in metrics:
            if metric == "準確率":
                value = np.random.uniform(0.75, 0.95)
            elif metric == "響應時間":
                value = np.random.uniform(50, 200)
            else:
                value = np.random.uniform(0.7, 0.9)
            
            comparison_data.append({
                "模型": model.split(" (")[0],  # 移除ID部分
                "指標": metric,
                "數值": value
            })
    
    df = pd.DataFrame(comparison_data)
    
    fig = px.bar(
        df,
        x="模型",
        y="數值",
        color="指標",
        barmode="group",
        title="模型效能比較"
    )
    
    st.plotly_chart(fig, use_container_width=True)
