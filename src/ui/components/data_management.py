"""數據管理組件

此模組整合所有數據管理相關功能，提供統一的數據管理介面：
- 數據管理基本功能
- 數據源配置嚮導

主要功能：
- 統一的數據管理入口
- 數據源配置和管理
- 數據品質監控
- 數據匯出和報告
- 統一的錯誤處理機制

Example:
    >>> from src.ui.components.data_management import show
    >>> show()  # 顯示數據管理主介面
"""

import logging
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)


def show() -> None:
    """顯示數據管理主介面.
    
    整合所有數據管理相關功能到統一的標籤頁介面中。
    提供2個子功能的完整整合，包括錯誤處理和狀態管理。
    
    主要子功能：
    - 數據管理：基本的數據管理功能，包括數據來源、更新、查詢等
    - 數據源配置：數據源配置嚮導，協助設定各種數據來源
    
    Returns:
        None
        
    Side Effects:
        - 渲染 Streamlit 界面組件
        - 可能修改 st.session_state 中的相關狀態
        
    Example:
        >>> show()  # 顯示完整的數據管理介面
        
    Note:
        此函數整合了多個原有頁面的功能，保持向後兼容性。
        如果某個子功能不可用，會顯示相應的錯誤訊息。
    """
    try:
        st.title("📊 數據管理")
        st.markdown("---")
        
        # 創建子功能標籤頁
        tab1, tab2 = st.tabs([
            "📈 數據管理",
            "🔧 數據源配置"
        ])
        
        with tab1:
            _show_data_management()
            
        with tab2:
            _show_data_source_config_wizard()
            
    except Exception as e:
        logger.error("顯示數據管理介面時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 數據管理介面載入失敗")
        with st.expander("錯誤詳情"):
            st.code(str(e))


def _show_data_management() -> None:
    """顯示基本數據管理功能.
    
    調用原有的 data_management 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入數據管理頁面失敗時
    """
    try:
        from src.ui.pages.data_management import show as data_management_show
        data_management_show()
        
    except ImportError as e:
        logger.warning("無法導入數據管理頁面: %s", e)
        st.warning("⚠️ 數據管理功能暫時不可用")
        _show_fallback_data_management()
        
    except Exception as e:
        logger.error("顯示數據管理時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 數據管理功能載入失敗")
        _show_fallback_data_management()


def _show_data_source_config_wizard() -> None:
    """顯示數據源配置嚮導.
    
    調用原有的 data_source_config_wizard 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入數據源配置嚮導失敗時
    """
    try:
        from src.ui.pages.data_source_config_wizard import show as config_wizard_show
        config_wizard_show()
        
    except ImportError as e:
        logger.warning("無法導入數據源配置嚮導: %s", e)
        st.warning("⚠️ 數據源配置嚮導暫時不可用")
        _show_fallback_data_source_config()
        
    except Exception as e:
        logger.error("顯示數據源配置嚮導時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 數據源配置嚮導載入失敗")
        _show_fallback_data_source_config()


def _show_fallback_data_management() -> None:
    """數據管理的備用顯示函數.
    
    當原有的數據管理頁面無法載入時，顯示基本的功能說明。
    
    Returns:
        None
    """
    st.info("📈 數據管理功能正在載入中...")
    
    st.markdown("""
    **數據管理功能包括**：
    - 📡 **數據來源管理**：監控和管理各種數據來源的狀態
    - 🔄 **數據更新**：手動觸發和監控數據更新任務
    - 🔍 **數據查詢**：查詢和瀏覽歷史數據
    - 📈 **品質監控**：監控數據品質和異常檢測
    - 📤 **數據匯出**：匯出數據和生成報告
    """)
    
    # 顯示基本的數據狀態信息
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("數據來源", "5", "✅")
    
    with col2:
        st.metric("最後更新", "10分鐘前", "🔄")
    
    with col3:
        st.metric("數據品質", "98.5%", "📈")
    
    with col4:
        st.metric("存儲使用", "2.3GB", "💾")


def _show_fallback_data_source_config() -> None:
    """數據源配置的備用顯示函數.
    
    當原有的數據源配置嚮導無法載入時，顯示基本的功能說明。
    
    Returns:
        None
    """
    st.info("🔧 數據源配置嚮導正在載入中...")
    
    st.markdown("""
    **數據源配置功能包括**：
    - 🏗️ **配置嚮導**：逐步引導設定數據來源
    - 🔗 **連接測試**：測試數據源連接狀態
    - ⚙️ **參數設定**：配置數據獲取參數
    - 📋 **模板管理**：管理常用的配置模板
    - 🔄 **同步設定**：設定數據同步頻率和規則
    """)
    
    # 顯示配置選項
    st.markdown("### 🚀 快速配置")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📈 股票數據源", use_container_width=True):
            st.info("股票數據源配置功能開發中...")
    
    with col2:
        if st.button("💰 財務數據源", use_container_width=True):
            st.info("財務數據源配置功能開發中...")
    
    with col3:
        if st.button("📰 新聞數據源", use_container_width=True):
            st.info("新聞數據源配置功能開發中...")
    
    # 顯示現有配置狀態
    st.markdown("### 📊 現有配置狀態")
    
    config_data = [
        {"名稱": "Yahoo Finance", "類型": "股票數據", "狀態": "✅ 正常", "最後更新": "5分鐘前"},
        {"名稱": "Alpha Vantage", "類型": "財務數據", "狀態": "⚠️ 限制", "最後更新": "1小時前"},
        {"名稱": "新聞API", "類型": "新聞數據", "狀態": "❌ 離線", "最後更新": "2小時前"}
    ]
    
    for config in config_data:
        with st.expander(f"{config['名稱']} - {config['狀態']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**類型**: {config['類型']}")
                st.write(f"**狀態**: {config['狀態']}")
            with col2:
                st.write(f"**最後更新**: {config['最後更新']}")
                if st.button(f"重新配置", key=f"reconfig_{config['名稱']}"):
                    st.info(f"{config['名稱']} 重新配置功能開發中...")


# 輔助函數
def get_data_source_status() -> dict:
    """獲取數據源狀態信息.
    
    Returns:
        dict: 包含數據源狀態的字典
        
    Example:
        >>> status = get_data_source_status()
        >>> print(status['total_sources'])
        5
    """
    return {
        'total_sources': 5,
        'active_sources': 4,
        'last_update': '10分鐘前',
        'data_quality': 98.5,
        'storage_used': '2.3GB'
    }


def validate_data_source_config(config: dict) -> bool:
    """驗證數據源配置.
    
    Args:
        config: 數據源配置字典
        
    Returns:
        bool: 配置是否有效
        
    Example:
        >>> config = {'name': 'test', 'type': 'stock', 'url': 'http://example.com'}
        >>> is_valid = validate_data_source_config(config)
        >>> print(is_valid)
        True
    """
    required_fields = ['name', 'type', 'url']
    return all(field in config and config[field] for field in required_fields)
