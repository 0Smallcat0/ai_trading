"""
AI 模型清單管理模組

此模組提供模型清單的管理功能，包括：
- 模型清單顯示和篩選
- 模型上傳和匯入
- 模型基本資訊編輯
- 模型狀態管理
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional

from .base import get_ai_model_service, safe_strftime, create_status_badge, format_model_metrics


def show_model_list():
    """顯示模型清單頁面
    
    提供模型的清單檢視，包括：
    - 模型基本資訊表格
    - 搜尋和篩選功能
    - 模型操作按鈕
    - 批量操作功能
    """
    st.header("📋 模型清單")
    
    # 獲取服務實例
    service = get_ai_model_service()
    
    # 控制面板
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        search_term = st.text_input("🔍 搜尋模型", placeholder="輸入模型名稱或ID...")
    
    with col2:
        status_filter = st.selectbox(
            "狀態篩選",
            options=["全部", "active", "training", "inactive", "error"],
            index=0
        )
    
    with col3:
        type_filter = st.selectbox(
            "類型篩選", 
            options=["全部", "classification", "regression", "clustering"],
            index=0
        )
    
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)  # 空行對齊
        if st.button("🔄 重新整理", use_container_width=True):
            st.rerun()
    
    # 獲取模型列表
    try:
        models = service.get_models()
        
        # 應用篩選
        filtered_models = _apply_filters(models, search_term, status_filter, type_filter)
        
        if not filtered_models:
            st.info("📭 沒有找到符合條件的模型")
            return
        
        # 顯示統計資訊
        _show_model_statistics(filtered_models)
        
        # 顯示模型表格
        _show_model_table(filtered_models, service)
        
        # 批量操作
        _show_batch_operations(filtered_models, service)
        
    except Exception as e:
        st.error(f"❌ 載入模型清單失敗: {e}")


def show_model_upload_form(uploaded_file):
    """顯示模型上傳表單
    
    Args:
        uploaded_file: Streamlit 上傳的檔案物件
    """
    st.header("📤 模型上傳")
    
    if uploaded_file is None:
        st.info("請選擇要上傳的模型檔案")
        return
    
    # 檔案資訊
    st.subheader("📄 檔案資訊")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**檔案名稱**: {uploaded_file.name}")
        st.write(f"**檔案大小**: {uploaded_file.size / 1024 / 1024:.2f} MB")
    
    with col2:
        st.write(f"**檔案類型**: {uploaded_file.type}")
        st.write(f"**上傳時間**: {safe_strftime(datetime.now())}")
    
    # 模型配置表單
    st.subheader("⚙️ 模型配置")
    
    with st.form("model_upload_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            model_name = st.text_input("模型名稱*", placeholder="輸入模型名稱")
            model_type = st.selectbox("模型類型*", ["classification", "regression", "clustering"])
            algorithm = st.text_input("演算法*", placeholder="例如: RandomForest, XGBoost")
        
        with col2:
            version = st.text_input("版本", value="1.0.0", placeholder="例如: 1.0.0")
            description = st.text_area("描述", placeholder="模型描述...")
            tags = st.text_input("標籤", placeholder="用逗號分隔，例如: 股票,預測,機器學習")
        
        # 進階設定
        with st.expander("🔧 進階設定"):
            auto_deploy = st.checkbox("自動部署", value=False)
            enable_monitoring = st.checkbox("啟用監控", value=True)
            max_memory = st.number_input("最大記憶體 (MB)", min_value=128, max_value=8192, value=512)
            timeout = st.number_input("超時時間 (秒)", min_value=1, max_value=300, value=30)
        
        # 提交按鈕
        submitted = st.form_submit_button("📤 上傳模型", use_container_width=True)
        
        if submitted:
            # 驗證必填欄位
            if not all([model_name, model_type, algorithm]):
                st.error("❌ 請填寫所有必填欄位（標記*的欄位）")
                return
            
            # 準備模型資料
            model_data = {
                'name': model_name,
                'type': model_type,
                'algorithm': algorithm,
                'version': version,
                'description': description,
                'tags': [tag.strip() for tag in tags.split(',') if tag.strip()],
                'file_name': uploaded_file.name,
                'file_size': uploaded_file.size,
                'auto_deploy': auto_deploy,
                'enable_monitoring': enable_monitoring,
                'max_memory': max_memory,
                'timeout': timeout,
                'uploaded_at': datetime.now().isoformat()
            }
            
            # 上傳模型
            _upload_model(model_data, uploaded_file)


def _apply_filters(models: List[Dict], search_term: str, status_filter: str, type_filter: str) -> List[Dict]:
    """應用篩選條件
    
    Args:
        models: 模型列表
        search_term: 搜尋關鍵字
        status_filter: 狀態篩選
        type_filter: 類型篩選
        
    Returns:
        篩選後的模型列表
    """
    filtered = models
    
    # 搜尋篩選
    if search_term:
        filtered = [
            model for model in filtered
            if search_term.lower() in model.get('name', '').lower() or
               search_term.lower() in model.get('id', '').lower()
        ]
    
    # 狀態篩選
    if status_filter != "全部":
        filtered = [model for model in filtered if model.get('status') == status_filter]
    
    # 類型篩選
    if type_filter != "全部":
        filtered = [model for model in filtered if model.get('type') == type_filter]
    
    return filtered


def _show_model_statistics(models: List[Dict]) -> None:
    """顯示模型統計資訊
    
    Args:
        models: 模型列表
    """
    col1, col2, col3, col4 = st.columns(4)
    
    total_models = len(models)
    active_models = len([m for m in models if m.get('status') == 'active'])
    training_models = len([m for m in models if m.get('status') == 'training'])
    avg_accuracy = np.mean([m.get('accuracy', 0) for m in models if m.get('accuracy')])
    
    with col1:
        st.metric("總模型數", total_models)
    
    with col2:
        st.metric("活躍模型", active_models, f"{active_models/total_models*100:.1f}%")
    
    with col3:
        st.metric("訓練中", training_models)
    
    with col4:
        st.metric("平均準確率", f"{avg_accuracy:.3f}" if avg_accuracy > 0 else "N/A")


def _show_model_table(models: List[Dict], service) -> None:
    """顯示模型表格
    
    Args:
        models: 模型列表
        service: AI 模型服務實例
    """
    st.subheader("📊 模型詳細資訊")
    
    # 準備表格資料
    table_data = []
    for model in models:
        table_data.append({
            'ID': model.get('id', 'N/A'),
            '名稱': model.get('name', 'N/A'),
            '類型': model.get('type', 'N/A'),
            '狀態': model.get('status', 'unknown'),
            '準確率': f"{model.get('accuracy', 0):.3f}" if model.get('accuracy') else 'N/A',
            '創建時間': safe_strftime(model.get('created_at', datetime.now())),
            '操作': model.get('id', '')
        })
    
    # 顯示表格
    df = pd.DataFrame(table_data)
    
    # 使用 st.data_editor 提供互動功能
    edited_df = st.data_editor(
        df,
        column_config={
            "狀態": st.column_config.SelectboxColumn(
                "狀態",
                options=["active", "training", "inactive", "error"],
                required=True
            ),
            "操作": st.column_config.Column("操作", disabled=True)
        },
        disabled=["ID", "名稱", "類型", "準確率", "創建時間", "操作"],
        hide_index=True,
        use_container_width=True
    )
    
    # 處理狀態變更
    if not df.equals(edited_df):
        _handle_status_changes(df, edited_df, service)


def _show_batch_operations(models: List[Dict], service) -> None:
    """顯示批量操作
    
    Args:
        models: 模型列表
        service: AI 模型服務實例
    """
    st.subheader("🔧 批量操作")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🚀 批量啟動", use_container_width=True):
            _batch_activate_models(models, service)
    
    with col2:
        if st.button("⏸️ 批量停止", use_container_width=True):
            _batch_deactivate_models(models, service)
    
    with col3:
        if st.button("📊 匯出清單", use_container_width=True):
            _export_model_list(models)
    
    with col4:
        if st.button("🗑️ 批量刪除", use_container_width=True, type="secondary"):
            _batch_delete_models(models, service)


def _upload_model(model_data: Dict, uploaded_file) -> None:
    """上傳模型
    
    Args:
        model_data: 模型資料
        uploaded_file: 上傳的檔案
    """
    try:
        with st.spinner("正在上傳模型..."):
            service = get_ai_model_service()
            result = service.create_model(model_data)
            
            if result.get('success'):
                st.success(f"✅ 模型上傳成功！模型ID: {result.get('model_id')}")
                st.balloons()
            else:
                st.error(f"❌ 模型上傳失敗: {result.get('error', '未知錯誤')}")
                
    except Exception as e:
        st.error(f"❌ 上傳過程中發生錯誤: {e}")


def _handle_status_changes(original_df: pd.DataFrame, edited_df: pd.DataFrame, service) -> None:
    """處理狀態變更
    
    Args:
        original_df: 原始資料框
        edited_df: 編輯後的資料框
        service: AI 模型服務實例
    """
    # 找出變更的行
    changes = original_df.compare(edited_df)
    if not changes.empty:
        st.info("檢測到狀態變更，正在更新...")
        # 這裡可以實作實際的狀態更新邏輯


def _batch_activate_models(models: List[Dict], service) -> None:
    """批量啟動模型"""
    st.info("批量啟動功能開發中...")


def _batch_deactivate_models(models: List[Dict], service) -> None:
    """批量停止模型"""
    st.info("批量停止功能開發中...")


def _export_model_list(models: List[Dict]) -> None:
    """匯出模型清單"""
    df = pd.DataFrame(models)
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 下載 CSV",
        data=csv,
        file_name=f"model_list_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )


def _batch_delete_models(models: List[Dict], service) -> None:
    """批量刪除模型"""
    st.warning("⚠️ 批量刪除功能需要管理員權限")
