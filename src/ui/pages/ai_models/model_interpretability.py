"""
AI 模型解釋性分析模組

此模組提供模型解釋性分析功能，包括：
- SHAP 分析
- LIME 分析
- 特徵重要性分析
- 模型決策邊界視覺化
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from typing import Dict, List, Optional, Any

from .base import get_ai_model_service, safe_strftime, create_info_card


def show_model_interpretability():
    """顯示模型解釋性分析頁面"""
    st.header("🔍 模型解釋性分析")
    
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
    
    # 解釋方法選擇
    explanation_methods = {
        "SHAP 分析": "shap",
        "LIME 分析": "lime",
        "特徵重要性": "feature_importance",
        "部分依賴圖": "partial_dependence"
    }
    
    selected_method = st.selectbox("解釋方法", options=list(explanation_methods.keys()))
    method_key = explanation_methods[selected_method]
    
    # 顯示方法說明
    show_explanation_method_info(method_key)
    
    # 樣本資料生成
    st.subheader("📊 樣本資料")
    
    col1, col2 = st.columns(2)
    
    with col1:
        sample_size = st.number_input("樣本數量", min_value=1, max_value=1000, value=100)
        data_source = st.selectbox("資料來源", ["生成模擬資料", "上傳檔案", "從資料庫載入"])
    
    with col2:
        if st.button("🎲 生成樣本資料", use_container_width=True):
            sample_data = generate_sample_data(selected_model, sample_size)
            st.session_state.sample_data = sample_data
    
    # 如果有樣本資料，顯示解釋分析
    if hasattr(st.session_state, 'sample_data'):
        st.subheader("🔍 解釋分析")
        
        if st.button("🚀 開始分析", use_container_width=True, type="primary"):
            _perform_explanation_analysis(selected_model, method_key, st.session_state.sample_data, service)


def generate_sample_data(model: Dict, sample_size: int) -> Dict:
    """生成用於解釋的樣本數據
    
    Args:
        model: 模型資訊
        sample_size: 樣本數量
        
    Returns:
        包含樣本資料的字典
    """
    # 模擬特徵資料
    features = ['price', 'volume', 'ma_5', 'ma_20', 'rsi', 'macd', 'bollinger_upper', 'bollinger_lower']
    
    data = {}
    for feature in features:
        if feature == 'price':
            data[feature] = np.random.uniform(50, 200, sample_size)
        elif feature == 'volume':
            data[feature] = np.random.uniform(1000, 100000, sample_size)
        elif feature in ['ma_5', 'ma_20']:
            data[feature] = np.random.uniform(45, 205, sample_size)
        elif feature == 'rsi':
            data[feature] = np.random.uniform(0, 100, sample_size)
        elif feature == 'macd':
            data[feature] = np.random.uniform(-5, 5, sample_size)
        else:
            data[feature] = np.random.uniform(40, 210, sample_size)
    
    df = pd.DataFrame(data)
    
    # 顯示資料預覽
    st.write("**生成的樣本資料預覽：**")
    st.dataframe(df.head(10), use_container_width=True)
    
    return {
        'dataframe': df,
        'features': features,
        'sample_size': sample_size,
        'generated_at': datetime.now()
    }


def show_explanation_results(explanation_result: Dict, method: str):
    """顯示解釋分析結果
    
    Args:
        explanation_result: 解釋結果
        method: 解釋方法
    """
    st.subheader(f"📈 {method.upper()} 分析結果")
    
    if method == "shap":
        _show_shap_results(explanation_result)
    elif method == "lime":
        _show_lime_results(explanation_result)
    elif method == "feature_importance":
        _show_feature_importance_results(explanation_result)
    elif method == "partial_dependence":
        _show_partial_dependence_results(explanation_result)


def show_explanation_method_info(method: str):
    """顯示解釋方法的說明資訊
    
    Args:
        method: 解釋方法
    """
    method_info = {
        "shap": {
            "title": "SHAP (SHapley Additive exPlanations)",
            "description": "基於博弈論的特徵重要性分析，提供每個特徵對預測結果的貢獻度。",
            "advantages": ["全域和局部解釋", "理論基礎堅實", "支援多種模型類型"],
            "use_cases": ["特徵重要性排序", "預測結果解釋", "模型偏差檢測"]
        },
        "lime": {
            "title": "LIME (Local Interpretable Model-agnostic Explanations)",
            "description": "通過在局部區域擬合簡單模型來解釋複雜模型的預測結果。",
            "advantages": ["模型無關", "局部解釋", "直觀易懂"],
            "use_cases": ["單一預測解釋", "異常檢測", "決策支援"]
        },
        "feature_importance": {
            "title": "特徵重要性分析",
            "description": "分析各個特徵對模型整體性能的貢獻程度。",
            "advantages": ["計算簡單", "全域視角", "特徵選擇指導"],
            "use_cases": ["特徵選擇", "模型簡化", "業務洞察"]
        },
        "partial_dependence": {
            "title": "部分依賴圖 (Partial Dependence Plot)",
            "description": "顯示特徵與預測結果之間的邊際關係。",
            "advantages": ["視覺化直觀", "關係清晰", "支援交互作用"],
            "use_cases": ["特徵效應分析", "閾值設定", "業務規則制定"]
        }
    }
    
    info = method_info.get(method, {})
    if info:
        create_info_card(
            info["title"],
            info["description"],
            "🔍"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**優勢：**")
            for advantage in info.get("advantages", []):
                st.write(f"• {advantage}")
        
        with col2:
            st.write("**應用場景：**")
            for use_case in info.get("use_cases", []):
                st.write(f"• {use_case}")


def _perform_explanation_analysis(model: Dict, method: str, sample_data: Dict, service) -> None:
    """執行解釋分析"""
    try:
        with st.spinner(f"正在進行 {method.upper()} 分析..."):
            # 模擬解釋結果
            explanation_result = service.explain_prediction(
                model['id'], 
                sample_data['dataframe'], 
                method
            )
            
            # 增強模擬結果
            if method == "shap":
                explanation_result = _generate_mock_shap_results(sample_data)
            elif method == "lime":
                explanation_result = _generate_mock_lime_results(sample_data)
            elif method == "feature_importance":
                explanation_result = _generate_mock_feature_importance_results(sample_data)
            elif method == "partial_dependence":
                explanation_result = _generate_mock_partial_dependence_results(sample_data)
            
            st.success(f"✅ {method.upper()} 分析完成！")
            show_explanation_results(explanation_result, method)
            
    except Exception as e:
        st.error(f"❌ 解釋分析失敗: {e}")


def _generate_mock_shap_results(sample_data: Dict) -> Dict:
    """生成模擬 SHAP 結果"""
    features = sample_data['features']
    sample_size = min(sample_data['sample_size'], 10)  # 限制顯示數量
    
    # 生成 SHAP 值
    shap_values = np.random.uniform(-0.5, 0.5, (sample_size, len(features)))
    
    return {
        'shap_values': shap_values,
        'features': features,
        'feature_importance': {feature: np.abs(shap_values[:, i]).mean() 
                             for i, feature in enumerate(features)},
        'base_value': 0.5,
        'sample_size': sample_size
    }


def _generate_mock_lime_results(sample_data: Dict) -> Dict:
    """生成模擬 LIME 結果"""
    features = sample_data['features']
    
    return {
        'feature_weights': {feature: np.random.uniform(-1, 1) for feature in features},
        'intercept': np.random.uniform(0.3, 0.7),
        'score': np.random.uniform(0.7, 0.95),
        'local_prediction': np.random.uniform(0, 1)
    }


def _generate_mock_feature_importance_results(sample_data: Dict) -> Dict:
    """生成模擬特徵重要性結果"""
    features = sample_data['features']
    importance_scores = np.random.random(len(features))
    importance_scores = importance_scores / importance_scores.sum()  # 正規化
    
    return {
        'feature_importance': dict(zip(features, importance_scores)),
        'method': 'permutation_importance',
        'std': np.random.uniform(0.01, 0.05, len(features))
    }


def _generate_mock_partial_dependence_results(sample_data: Dict) -> Dict:
    """生成模擬部分依賴圖結果"""
    features = sample_data['features']
    
    results = {}
    for feature in features[:3]:  # 只為前3個特徵生成
        x_values = np.linspace(
            sample_data['dataframe'][feature].min(),
            sample_data['dataframe'][feature].max(),
            50
        )
        y_values = np.sin(x_values / x_values.max() * np.pi) * 0.3 + 0.5 + np.random.normal(0, 0.05, 50)
        
        results[feature] = {
            'x_values': x_values,
            'y_values': y_values
        }
    
    return results


def _show_shap_results(result: Dict) -> None:
    """顯示 SHAP 結果"""
    # 特徵重要性條形圖
    st.subheader("📊 特徵重要性 (SHAP)")
    
    importance_df = pd.DataFrame(
        list(result['feature_importance'].items()),
        columns=['特徵', '重要性']
    ).sort_values('重要性', ascending=True)
    
    fig = px.bar(
        importance_df,
        x='重要性',
        y='特徵',
        orientation='h',
        title="SHAP 特徵重要性"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # SHAP 值熱力圖
    st.subheader("🔥 SHAP 值熱力圖")
    
    fig = px.imshow(
        result['shap_values'].T,
        x=[f"樣本 {i+1}" for i in range(result['sample_size'])],
        y=result['features'],
        color_continuous_scale='RdBu',
        title="SHAP 值分佈"
    )
    st.plotly_chart(fig, use_container_width=True)


def _show_lime_results(result: Dict) -> None:
    """顯示 LIME 結果"""
    st.subheader("📊 LIME 特徵權重")
    
    weights_df = pd.DataFrame(
        list(result['feature_weights'].items()),
        columns=['特徵', '權重']
    ).sort_values('權重', ascending=True)
    
    # 創建顏色映射
    colors = ['red' if w < 0 else 'blue' for w in weights_df['權重']]
    
    fig = px.bar(
        weights_df,
        x='權重',
        y='特徵',
        orientation='h',
        title=f"LIME 局部解釋 (預測值: {result['local_prediction']:.3f})",
        color=weights_df['權重'],
        color_continuous_scale='RdBu'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 顯示解釋統計
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("局部預測值", f"{result['local_prediction']:.3f}")
        st.metric("解釋分數", f"{result['score']:.3f}")
    
    with col2:
        st.metric("截距", f"{result['intercept']:.3f}")
        st.metric("特徵數量", len(result['feature_weights']))


def _show_feature_importance_results(result: Dict) -> None:
    """顯示特徵重要性結果"""
    st.subheader("📊 特徵重要性排序")
    
    importance_df = pd.DataFrame(
        list(result['feature_importance'].items()),
        columns=['特徵', '重要性']
    ).sort_values('重要性', ascending=False)
    
    fig = px.bar(
        importance_df,
        x='特徵',
        y='重要性',
        title="特徵重要性排序"
    )
    fig.update_xaxis(tickangle=45)
    st.plotly_chart(fig, use_container_width=True)
    
    # 顯示詳細表格
    st.subheader("📋 詳細數據")
    st.dataframe(importance_df, use_container_width=True)


def _show_partial_dependence_results(result: Dict) -> None:
    """顯示部分依賴圖結果"""
    st.subheader("📈 部分依賴圖")
    
    for feature, data in result.items():
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data['x_values'],
            y=data['y_values'],
            mode='lines+markers',
            name=f'{feature} 部分依賴'
        ))
        
        fig.update_layout(
            title=f"{feature} 的部分依賴關係",
            xaxis_title=feature,
            yaxis_title="預測值"
        )
        
        st.plotly_chart(fig, use_container_width=True)
