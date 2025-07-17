"""
AI 模型管理基礎模組

此模組包含 AI 模型管理的基礎功能和工具函數。

主要功能：
- 日期格式化工具
- AI 模型服務獲取
- 主頁面顯示
- 共用工具函數
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, Union

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px


def safe_strftime(date_obj: Union[datetime, pd.Timestamp, np.datetime64, str], format_str: str = "%Y-%m-%d %H:%M") -> str:
    """安全的日期格式化函數
    
    Args:
        date_obj: 日期物件
        format_str: 格式化字串
        
    Returns:
        格式化後的日期字串
        
    Examples:
        >>> safe_strftime(datetime.now())
        '2025-07-18 10:30'
        >>> safe_strftime("2025-07-18")
        '2025-07-18 00:00'
    """
    try:
        if isinstance(date_obj, str):
            date_obj = pd.to_datetime(date_obj)
        elif isinstance(date_obj, np.datetime64):
            date_obj = pd.to_datetime(date_obj)
        elif isinstance(date_obj, pd.Timestamp):
            pass
        elif isinstance(date_obj, datetime):
            pass
        else:
            date_obj = pd.to_datetime(date_obj)

        if hasattr(date_obj, 'to_pydatetime'):
            return date_obj.to_pydatetime().strftime(format_str)
        else:
            return date_obj.strftime(format_str)
    except Exception as e:
        st.warning(f"日期格式化失敗: {e}")
        return str(date_obj)


def get_ai_model_service():
    """獲取 AI 模型管理服務實例
    
    Returns:
        AIModelManagementService: AI 模型管理服務實例
        
    Note:
        如果無法導入真實服務，將返回模擬服務實例
    """
    try:
        from src.core.ai_model_management_service import AIModelManagementService
        return AIModelManagementService()
    except ImportError:
        # 備用導入或創建模擬服務
        class MockAIModelManagementService:
            """模擬 AI 模型管理服務"""
            
            def __init__(self):
                self.models = []
                
            def get_models(self):
                """獲取模型列表"""
                return [
                    {
                        'id': 'model_1',
                        'name': '示例模型 1',
                        'type': 'classification',
                        'status': 'active',
                        'accuracy': 0.85,
                        'created_at': datetime.now() - timedelta(days=5)
                    },
                    {
                        'id': 'model_2', 
                        'name': '示例模型 2',
                        'type': 'regression',
                        'status': 'training',
                        'accuracy': 0.78,
                        'created_at': datetime.now() - timedelta(days=2)
                    }
                ]
                
            def create_model(self, model_data):
                """創建新模型"""
                return {'success': True, 'model_id': f'model_{len(self.models) + 1}'}
                
            def train_model(self, model_id, config):
                """訓練模型"""
                return {'success': True, 'training_id': f'training_{model_id}'}
                
            def predict(self, model_id, data):
                """模型預測"""
                return {'predictions': [0.5, 0.7, 0.3], 'confidence': 0.85}
                
            def explain_prediction(self, model_id, data, method='shap'):
                """解釋預測結果"""
                return {
                    'feature_importance': {'feature_1': 0.3, 'feature_2': 0.7},
                    'explanation': '基於特徵重要性的解釋'
                }
        
        st.warning("⚠️ 無法載入 AI 模型管理服務，使用模擬服務")
        return MockAIModelManagementService()


def show():
    """顯示 AI 模型管理主頁面
    
    此函數是 AI 模型管理頁面的主要入口點，提供：
    - 頁面標題和導航
    - 功能模組選擇
    - 子頁面路由
    """
    st.title("🤖 AI 模型管理")
    st.markdown("---")
    
    # 側邊欄導航
    with st.sidebar:
        st.header("📋 功能選單")
        
        page_options = {
            "模型清單": "model_list",
            "模型訓練": "model_training", 
            "模型推論": "model_inference",
            "模型解釋性": "model_interpretability",
            "效能監控": "model_monitoring",
            "模型管理": "model_management"
        }
        
        selected_page = st.selectbox(
            "選擇功能",
            options=list(page_options.keys()),
            key="ai_models_page_selector"
        )
        
        # 顯示當前時間
        st.markdown("---")
        st.markdown(f"**當前時間**: {safe_strftime(datetime.now())}")
        
        # 顯示系統狀態
        st.markdown("**系統狀態**: 🟢 正常運行")
    
    # 主要內容區域
    page_key = page_options[selected_page]
    
    if page_key == "model_list":
        from .model_list import show_model_list
        show_model_list()
        
    elif page_key == "model_training":
        from .model_training import show_model_training_enhanced
        show_model_training_enhanced()
        
    elif page_key == "model_inference":
        from .model_inference import show_model_inference
        show_model_inference()
        
    elif page_key == "model_interpretability":
        from .model_interpretability import show_model_interpretability
        show_model_interpretability()
        
    elif page_key == "model_monitoring":
        from .model_monitoring import show_model_performance_monitoring
        show_model_performance_monitoring()
        
    elif page_key == "model_management":
        from .model_management import show_model_management_enhanced
        show_model_management_enhanced()
    
    # 頁腳資訊
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("活躍模型", "12", "↑2")
    
    with col2:
        st.metric("訓練中模型", "3", "↓1")
        
    with col3:
        st.metric("今日預測次數", "1,247", "↑156")


def create_info_card(title: str, content: str, icon: str = "ℹ️") -> None:
    """創建資訊卡片
    
    Args:
        title: 卡片標題
        content: 卡片內容
        icon: 圖示
    """
    st.markdown(f"""
    <div style="
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    ">
        <h4 style="margin: 0; color: #1f77b4;">{icon} {title}</h4>
        <p style="margin: 0.5rem 0 0 0;">{content}</p>
    </div>
    """, unsafe_allow_html=True)


def create_status_badge(status: str) -> str:
    """創建狀態徽章
    
    Args:
        status: 狀態字串
        
    Returns:
        HTML 格式的狀態徽章
    """
    color_map = {
        'active': '#28a745',
        'training': '#ffc107', 
        'inactive': '#6c757d',
        'error': '#dc3545',
        'pending': '#17a2b8'
    }
    
    color = color_map.get(status.lower(), '#6c757d')
    
    return f"""
    <span style="
        background-color: {color};
        color: white;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
        font-weight: bold;
    ">{status.upper()}</span>
    """


def format_model_metrics(metrics: Dict) -> str:
    """格式化模型指標
    
    Args:
        metrics: 模型指標字典
        
    Returns:
        格式化後的指標字串
    """
    formatted = []
    for key, value in metrics.items():
        if isinstance(value, float):
            formatted.append(f"{key}: {value:.3f}")
        else:
            formatted.append(f"{key}: {value}")
    
    return " | ".join(formatted)


def validate_model_config(config: Dict) -> Tuple[bool, str]:
    """驗證模型配置
    
    Args:
        config: 模型配置字典
        
    Returns:
        Tuple[bool, str]: (是否有效, 錯誤訊息)
    """
    required_fields = ['name', 'type', 'algorithm']
    
    for field in required_fields:
        if field not in config or not config[field]:
            return False, f"缺少必要欄位: {field}"
    
    if config['type'] not in ['classification', 'regression', 'clustering']:
        return False, "模型類型必須是 classification, regression 或 clustering"
    
    return True, ""
