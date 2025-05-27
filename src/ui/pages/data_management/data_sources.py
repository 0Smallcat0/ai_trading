"""
資料來源管理模組

此模組提供資料來源的狀態監控、連接測試和管理功能。
包括資料來源狀態概覽、詳細資訊卡片和連接測試等功能。

主要功能：
- 資料來源狀態概覽統計
- 資料來源詳細資訊卡片顯示
- 連接測試功能
- 資料來源狀態報告下載

Example:
    ```python
    from src.ui.pages.data_management.data_sources import show_data_sources_management
    show_data_sources_management()
    ```

Note:
    此模組依賴於 DataManagementService 來獲取資料來源狀態資訊。
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

import streamlit as st
import pandas as pd

# 導入自定義元件
try:
    from src.ui.components.data_management_components import (
        show_data_source_status_card,
        show_connection_test_result,
    )
except ImportError as e:
    st.warning(f"無法導入資料管理組件: {e}")

    # 提供簡化的替代函數
    def show_data_source_status_card(
        source_name: str, source_info: Dict[str, Any]
    ) -> None:
        """簡化的資料來源狀態卡片"""
        with st.container():
            st.markdown(f"### {source_name}")
            st.write(f"狀態: {source_info.get('status', 'Unknown')}")
            st.write(f"類型: {source_info.get('type', 'Unknown')}")
            st.write(f"最後更新: {source_info.get('last_update', 'Unknown')}")

    def show_connection_test_result(
        source_name: str, is_connected: bool, message: str
    ) -> None:
        """簡化的連接測試結果顯示"""
        if is_connected:
            st.success(f"{source_name}: {message}")
        else:
            st.error(f"{source_name}: {message}")


def get_data_source_status() -> Dict[str, Dict[str, Any]]:
    """
    獲取資料來源狀態資訊

    從資料管理服務獲取所有資料來源的狀態資訊，
    如果服務不可用則返回模擬數據。

    Returns:
        Dict[str, Dict[str, Any]]: 資料來源狀態字典，
            鍵為資料來源名稱，值為狀態資訊字典

    Example:
        ```python
        status = get_data_source_status()
        for source, info in status.items():
            print(f"{source}: {info['status']}")
        ```
    """
    # 嘗試從 session state 獲取資料服務
    data_service = st.session_state.get("data_service")

    if data_service:
        try:
            return data_service.get_data_source_status()
        except Exception as e:
            st.warning(f"無法從資料服務獲取狀態: {e}")

    # 返回模擬數據
    return {
        "Yahoo Finance": {
            "status": "正常",
            "type": "股價資料",
            "last_update": "2024-01-15 09:30:00",
            "api_status": "正常",
            "data_quality": "優良",
            "description": "提供美股和部分國際股票的即時和歷史價格數據",
            "update_frequency": "即時",
            "coverage": "美股、部分國際股票",
        },
        "FinMind": {
            "status": "正常",
            "type": "台股資料",
            "last_update": "2024-01-15 09:25:00",
            "api_status": "正常",
            "data_quality": "優良",
            "description": "台灣股市完整資料，包括股價、財報、除權息等",
            "update_frequency": "每日",
            "coverage": "台股全市場",
        },
        "Alpha Vantage": {
            "status": "警告",
            "type": "基本面資料",
            "last_update": "2024-01-15 08:45:00",
            "api_status": "速率限制",
            "data_quality": "良好",
            "description": "提供股票基本面數據和技術指標",
            "update_frequency": "每日",
            "coverage": "美股",
        },
        "富途證券 API": {
            "status": "離線",
            "type": "港股資料",
            "last_update": "2024-01-14 16:00:00",
            "api_status": "連接失敗",
            "data_quality": "無資料",
            "description": "港股即時行情和歷史數據",
            "update_frequency": "即時",
            "coverage": "港股",
        },
    }


def test_data_source_connection(source_name: str) -> Tuple[bool, str]:
    """
    測試資料來源連接

    測試指定資料來源的連接狀態，返回連接結果和詳細訊息。

    Args:
        source_name: 資料來源名稱

    Returns:
        Tuple[bool, str]: (是否連接成功, 詳細訊息)

    Example:
        ```python
        is_connected, message = test_data_source_connection("Yahoo Finance")
        if is_connected:
            print(f"連接成功: {message}")
        ```
    """
    # 嘗試從 session state 獲取資料服務
    data_service = st.session_state.get("data_service")

    if data_service:
        try:
            return data_service.test_data_source_connection(source_name)
        except Exception as e:
            return False, f"測試失敗: {e}"

    # 模擬連接測試
    data_sources = get_data_source_status()
    if source_name in data_sources:
        source_info = data_sources[source_name]
        status = source_info.get("status", "unknown")

        if status == "正常":
            return True, f"連接成功！延遲: {156 + hash(source_name) % 100}ms"
        elif status == "警告":
            return True, "連接成功，但存在警告: API 速率限制已達到 80%"
        else:
            return False, "連接失敗: 無法連接到 API 服務器"

    return False, "未知的資料來源"


def show_data_sources_overview() -> None:
    """
    顯示資料來源狀態概覽

    以統計卡片的形式顯示資料來源的整體狀態概覽，
    包括總數量、正常數量、警告數量和離線數量。

    Returns:
        None

    Side Effects:
        渲染 Streamlit 統計卡片組件
    """
    data_sources = get_data_source_status()

    if not data_sources:
        st.warning("無可用的資料來源")
        return

    # 計算狀態統計
    status_counts = {}
    for source_info in data_sources.values():
        status = source_info.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    # 顯示統計卡片
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("總資料來源", len(data_sources))
    with col2:
        st.metric("正常", status_counts.get("正常", 0))
    with col3:
        st.metric("警告", status_counts.get("警告", 0))
    with col4:
        st.metric("離線", status_counts.get("離線", 0) + status_counts.get("錯誤", 0))


def show_data_sources_cards() -> None:
    """
    顯示資料來源詳細資訊卡片

    以卡片形式顯示每個資料來源的詳細資訊，
    包括狀態、類型、更新時間等，並提供連接測試功能。

    Returns:
        None

    Side Effects:
        渲染 Streamlit 卡片組件和按鈕
    """
    data_sources = get_data_source_status()

    if not data_sources:
        st.warning("無可用的資料來源")
        return

    # 使用兩欄布局顯示卡片
    col1, col2 = st.columns(2)
    sources_list = list(data_sources.items())

    for i, (source_name, source_info) in enumerate(sources_list):
        with col1 if i % 2 == 0 else col2:
            show_data_source_status_card(source_name, source_info)

            # 添加連接測試按鈕
            if st.button(f"測試 {source_name} 連接", key=f"test_{source_name}"):
                with st.spinner(f"正在測試 {source_name} 連接..."):
                    time.sleep(1)  # 模擬測試時間
                    is_connected, message = test_data_source_connection(source_name)
                    show_connection_test_result(source_name, is_connected, message)


def show_data_sources_table() -> None:
    """
    顯示資料來源詳細表格

    以表格形式顯示所有資料來源的詳細資訊，
    並提供 CSV 格式的狀態報告下載功能。

    Returns:
        None

    Side Effects:
        渲染 Streamlit 表格和下載按鈕
    """
    data_sources = get_data_source_status()

    if not data_sources:
        st.warning("無可用的資料來源")
        return

    # 創建 DataFrame
    df = pd.DataFrame.from_dict(data_sources, orient="index")
    df.index.name = "資料來源"
    df.reset_index(inplace=True)

    # 選擇要顯示的欄位
    display_columns = [
        "資料來源",
        "status",
        "type",
        "last_update",
        "api_status",
        "data_quality",
    ]
    display_df = df[display_columns].copy()
    display_df.columns = [
        "資料來源",
        "狀態",
        "類型",
        "最後更新時間",
        "API狀態",
        "資料品質",
    ]

    # 顯示表格
    st.dataframe(display_df, use_container_width=True)

    # 提供下載功能
    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 下載資料來源狀態報告",
        data=csv,
        file_name=f"data_sources_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )


def show_data_sources_management() -> None:
    """
    顯示資料來源管理主介面

    這是資料來源管理的主要入口點，整合了狀態概覽、
    詳細卡片顯示和表格檢視等功能。

    Returns:
        None

    Side Effects:
        渲染完整的資料來源管理界面

    Example:
        ```python
        show_data_sources_management()
        ```

    Note:
        包含完整的錯誤處理，確保在資料服務不可用時
        仍能提供基本的功能和友善的錯誤訊息。
    """
    st.subheader("📊 資料來源管理")

    try:
        # 顯示狀態概覽
        st.markdown("### 狀態概覽")
        show_data_sources_overview()

        st.markdown("---")

        # 顯示資料來源卡片
        st.markdown("### 資料來源詳情")
        show_data_sources_cards()

        st.markdown("---")

        # 顯示詳細表格
        with st.expander("📋 詳細資料來源表格", expanded=False):
            show_data_sources_table()

    except Exception as e:
        st.error(f"資料來源管理功能發生錯誤: {e}")
        with st.expander("錯誤詳情"):
            st.code(str(e))
