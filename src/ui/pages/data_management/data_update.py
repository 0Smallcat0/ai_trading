"""
資料更新管理模組

此模組提供資料更新的管理功能，包括手動觸發更新、
監控更新進度、管理更新任務等功能。

主要功能：
- 手動觸發資料更新
- 更新進度監控和顯示
- 更新任務管理（開始、取消、重新開始）
- 更新配置設定和確認
- 自動刷新進度狀態

Example:
    ```python
    from src.ui.pages.data_management.data_update import show_data_update_management
    show_data_update_management()
    ```

Note:
    此模組依賴於 DataManagementService 來執行實際的資料更新邏輯。
"""

import time
from datetime import datetime, date
from typing import Dict, Any, Optional, List

import streamlit as st

# 導入自定義元件
try:
    from src.ui.components.data_management_components import (
        show_update_progress,
        show_update_form,
    )
except ImportError as e:
    st.warning(f"無法導入資料管理組件: {e}")
    
    # 提供簡化的替代函數
    def show_update_progress(task_status: Dict[str, Any]) -> None:
        """簡化的更新進度顯示"""
        st.write(f"任務狀態: {task_status.get('status', 'Unknown')}")
        progress = task_status.get('progress', 0)
        st.progress(progress / 100 if progress <= 100 else 1.0)
        
    def show_update_form(data_types: List[str], symbols: List[str], 
                        data_sources: List[str]) -> Optional[Dict[str, Any]]:
        """簡化的更新表單"""
        st.subheader("更新設定")
        
        update_type = st.selectbox("更新類型", ["完整更新", "增量更新"])
        selected_data_types = st.multiselect("資料類型", data_types)
        selected_sources = st.multiselect("資料來源", data_sources)
        
        if selected_data_types and selected_sources:
            return {
                "update_type": update_type,
                "data_types": selected_data_types,
                "sources": selected_sources,
                "symbols": [],
                "start_date": None,
                "end_date": None,
            }
        return None


def get_available_data_types() -> List[Dict[str, str]]:
    """
    獲取可用的資料類型清單
    
    提供系統支援的所有資料類型的詳細資訊，包括資料描述、
    來源、更新頻率和儲存位置等完整資訊。
    
    Returns:
        List[Dict[str, str]]: 資料類型清單，每個元素包含以下欄位：
            - id: 資料類型唯一識別碼
            - name: 資料類型顯示名稱
            - description: 詳細描述
            - sources: 支援的資料來源清單
            - frequency: 更新頻率
            - storage: 資料庫儲存位置
            
    Example:
        ```python
        data_types = get_available_data_types()
        for dt in data_types:
            print(f"{dt['name']}: {dt['description']}")
        ```
    """
    # 嘗試從資料服務獲取
    data_service = st.session_state.get('data_service')
    if data_service:
        try:
            return data_service.get_data_types()
        except Exception as e:
            st.warning(f"無法從資料服務獲取資料類型: {e}")
    
    # 返回模擬數據
    return [
        {
            "id": "price",
            "name": "股價資料",
            "description": "股票的開高低收量等基本價格數據",
            "sources": ["Yahoo Finance", "FinMind", "富途證券 API"],
            "frequency": "每日/分鐘/Tick",
            "storage": "market_daily/market_minute/market_tick 表",
        },
        {
            "id": "fundamental",
            "name": "基本面資料",
            "description": "公司財務報表、本益比、股息等基本面數據",
            "sources": ["Alpha Vantage", "FinMind"],
            "frequency": "季度/年度",
            "storage": "fundamental 表",
        },
        {
            "id": "technical",
            "name": "技術指標",
            "description": "各種技術分析指標，如 MA、RSI、MACD 等",
            "sources": ["內部計算"],
            "frequency": "依據原始數據",
            "storage": "technical_indicator 表",
        },
        {
            "id": "news",
            "name": "新聞資料",
            "description": "市場新聞和公告，包括情緒分析結果",
            "sources": ["新聞 API"],
            "frequency": "即時/每小時",
            "storage": "news_sentiment 表",
        },
        {
            "id": "financial",
            "name": "財報資料",
            "description": "詳細的財務報表數據，包括資產負債表、損益表等",
            "sources": ["Alpha Vantage", "FinMind"],
            "frequency": "季度",
            "storage": "financial_statement 表",
        },
    ]


def get_available_symbols() -> List[str]:
    """
    獲取可用的股票代碼清單
    
    Returns:
        List[str]: 股票代碼清單
        
    Example:
        ```python
        symbols = get_available_symbols()
        print(f"可用股票: {len(symbols)} 檔")
        ```
    """
    # 嘗試從資料服務獲取
    data_service = st.session_state.get('data_service')
    if data_service:
        try:
            return data_service.get_available_symbols()
        except Exception as e:
            st.warning(f"無法從資料服務獲取股票清單: {e}")
    
    # 返回模擬數據
    return [
        "2330.TW", "2317.TW", "2454.TW", "2308.TW", "2412.TW",
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"
    ]


def start_update_task(update_config: Dict[str, Any]) -> Optional[str]:
    """
    啟動資料更新任務
    
    Args:
        update_config: 更新配置字典
        
    Returns:
        Optional[str]: 任務ID，如果啟動失敗則返回 None
        
    Example:
        ```python
        config = {"update_type": "完整更新", "data_types": ["股價資料"]}
        task_id = start_update_task(config)
        ```
    """
    data_service = st.session_state.get('data_service')
    if data_service:
        try:
            return data_service.start_data_update(update_config)
        except Exception as e:
            st.error(f"啟動更新任務失敗: {e}")
            return None
    
    # 模擬任務ID
    return f"task_{int(time.time())}"


def get_update_status(task_id: str) -> Optional[Dict[str, Any]]:
    """
    獲取更新任務狀態
    
    Args:
        task_id: 任務ID
        
    Returns:
        Optional[Dict[str, Any]]: 任務狀態字典，如果任務不存在則返回 None
        
    Example:
        ```python
        status = get_update_status("task_123")
        if status:
            print(f"進度: {status['progress']}%")
        ```
    """
    data_service = st.session_state.get('data_service')
    if data_service:
        try:
            return data_service.get_update_status(task_id)
        except Exception as e:
            st.warning(f"獲取任務狀態失敗: {e}")
            return None
    
    # 模擬任務狀態
    if not hasattr(st.session_state, 'mock_task_progress'):
        st.session_state.mock_task_progress = 0
    
    st.session_state.mock_task_progress += 10
    if st.session_state.mock_task_progress >= 100:
        return {
            "status": "completed",
            "progress": 100,
            "message": "更新完成",
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    else:
        return {
            "status": "running",
            "progress": st.session_state.mock_task_progress,
            "message": f"正在更新... ({st.session_state.mock_task_progress}%)",
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }


def show_update_configuration_form() -> Optional[Dict[str, Any]]:
    """
    顯示更新配置表單
    
    Returns:
        Optional[Dict[str, Any]]: 更新配置字典，如果配置不完整則返回 None
        
    Side Effects:
        渲染 Streamlit 表單組件
    """
    # 獲取可用選項
    data_types = [dt["name"] for dt in get_available_data_types()]
    symbols = get_available_symbols()
    
    # 獲取資料來源
    data_service = st.session_state.get('data_service')
    if data_service:
        try:
            data_sources = list(data_service.get_data_source_status().keys())
        except Exception:
            data_sources = ["Yahoo Finance", "FinMind", "Alpha Vantage"]
    else:
        data_sources = ["Yahoo Finance", "FinMind", "Alpha Vantage"]
    
    # 使用自定義表單組件或簡化版本
    return show_update_form(data_types, symbols, data_sources)


def show_update_progress_monitor() -> None:
    """
    顯示更新進度監控
    
    監控當前正在進行的更新任務，顯示進度並提供控制選項。
    
    Returns:
        None
        
    Side Effects:
        可能修改 st.session_state.update_task_id
        可能觸發頁面重新運行
    """
    task_id = st.session_state.get('update_task_id')
    if not task_id:
        return
    
    task_status = get_update_status(task_id)
    if not task_status:
        st.session_state.update_task_id = None
        return
    
    st.subheader("📊 更新進度")
    show_update_progress(task_status)
    
    # 如果任務完成，提供重新開始選項
    if task_status.get("status") in ["completed", "error"]:
        if st.button("🔄 開始新的更新任務"):
            st.session_state.update_task_id = None
            st.rerun()
        return
    else:
        # 任務仍在進行中，提供取消選項
        if st.button("⏹️ 取消更新"):
            st.session_state.update_task_id = None
            st.warning("更新任務已取消")
            st.rerun()
        
        # 自動刷新頁面以更新進度
        time.sleep(2)
        st.rerun()


def show_data_update_management() -> None:
    """
    顯示資料更新管理主介面
    
    這是資料更新管理的主要入口點，整合了更新任務監控、
    配置設定和任務控制等功能。
    
    Returns:
        None
        
    Side Effects:
        渲染完整的資料更新管理界面
        可能啟動新的更新任務
        
    Example:
        ```python
        show_data_update_management()
        ```
        
    Note:
        包含完整的錯誤處理和任務生命週期管理。
    """
    st.subheader("🔄 資料更新管理")
    
    # 檢查資料服務是否可用
    data_service = st.session_state.get('data_service')
    if not data_service:
        st.error("資料管理服務未初始化")
        return
    
    try:
        # 檢查是否有正在進行的更新任務
        if st.session_state.get('update_task_id'):
            show_update_progress_monitor()
            return
        
        # 顯示更新配置表單
        st.subheader("⚙️ 更新設定")
        update_config = show_update_configuration_form()
        
        if update_config:
            # 顯示配置摘要
            st.subheader("📋 更新配置摘要")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**更新類型**: {update_config['update_type']}")
                st.write(f"**資料類型**: {', '.join(update_config['data_types'])}")
                st.write(f"**資料來源**: {', '.join(update_config['sources'])}")
            
            with col2:
                if update_config.get("symbols"):
                    symbols = update_config["symbols"]
                    st.write(f"**股票代碼**: {', '.join(symbols[:5])}")
                    if len(symbols) > 5:
                        st.write(f"... 等共 {len(symbols)} 檔")
                
                if update_config.get("start_date") and update_config.get("end_date"):
                    st.write(
                        f"**日期範圍**: {update_config['start_date']} 至 {update_config['end_date']}"
                    )
            
            # 確認並開始更新
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("✅ 確認並開始更新", type="primary"):
                    # 啟動更新任務
                    task_id = start_update_task(update_config)
                    if task_id:
                        st.session_state.update_task_id = task_id
                        st.success("更新任務已啟動！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("啟動更新任務失敗")
            
            with col2:
                if st.button("🔄 重設配置"):
                    st.rerun()
                    
    except Exception as e:
        st.error(f"資料更新管理功能發生錯誤: {e}")
        with st.expander("錯誤詳情"):
            st.code(str(e))
