"""學習中心組件

此模組整合所有學習中心相關功能，提供統一的學習中心介面：
- 新手中心功能
- 新手教學
- 知識庫
- 學習中心

主要功能：
- 統一的學習中心入口
- 新手引導和教學
- 知識庫管理
- 學習進度追蹤
- 統一的錯誤處理機制

Example:
    >>> from src.ui.components.learning_center import show
    >>> show()  # 顯示學習中心主介面
"""

import logging
from typing import Optional

import streamlit as st

logger = logging.getLogger(__name__)


def show() -> None:
    """顯示學習中心主介面.
    
    整合所有學習中心相關功能到統一的標籤頁介面中。
    提供4個子功能的完整整合，包括錯誤處理和狀態管理。
    
    主要子功能：
    - 新手中心：新手用戶的入門指導和基礎功能介紹
    - 新手教學：逐步的教學指導和實作練習
    - 知識庫：完整的系統知識庫和文檔
    - 學習中心：進階學習資源和課程管理
    
    Returns:
        None
        
    Side Effects:
        - 渲染 Streamlit 界面組件
        - 可能修改 st.session_state 中的相關狀態
        
    Example:
        >>> show()  # 顯示完整的學習中心介面
        
    Note:
        此函數整合了多個原有頁面的功能，保持向後兼容性。
        如果某個子功能不可用，會顯示相應的錯誤訊息。
    """
    try:
        st.title("📚 學習中心")
        st.markdown("---")
        
        # 創建子功能標籤頁
        tab1, tab2, tab3, tab4 = st.tabs([
            "🎯 新手中心",
            "📖 新手教學",
            "📚 知識庫",
            "🎓 學習中心"
        ])
        
        with tab1:
            _show_beginner_hub()
            
        with tab2:
            _show_beginner_tutorial()
            
        with tab3:
            _show_knowledge_base()
            
        with tab4:
            _show_learning_center()
            
    except Exception as e:
        logger.error("顯示學習中心介面時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 學習中心介面載入失敗")
        with st.expander("錯誤詳情"):
            st.code(str(e))


def _show_beginner_hub() -> None:
    """顯示新手中心功能.
    
    調用原有的 beginner_hub 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入新手中心頁面失敗時
    """
    try:
        from src.ui.pages.beginner_hub import show as beginner_hub_show
        beginner_hub_show()
        
    except ImportError as e:
        logger.warning("無法導入新手中心頁面: %s", e)
        st.warning("⚠️ 新手中心功能暫時不可用")
        _show_fallback_beginner_hub()
        
    except Exception as e:
        logger.error("顯示新手中心時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 新手中心功能載入失敗")
        _show_fallback_beginner_hub()


def _show_beginner_tutorial() -> None:
    """顯示新手教學功能.
    
    調用原有的 beginner_tutorial 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入新手教學頁面失敗時
    """
    try:
        from src.ui.pages.beginner_tutorial import show as tutorial_show
        tutorial_show()
        
    except ImportError as e:
        logger.warning("無法導入新手教學頁面: %s", e)
        st.warning("⚠️ 新手教學功能暫時不可用")
        _show_fallback_beginner_tutorial()
        
    except Exception as e:
        logger.error("顯示新手教學時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 新手教學功能載入失敗")
        _show_fallback_beginner_tutorial()


def _show_knowledge_base() -> None:
    """顯示知識庫功能.
    
    調用原有的 knowledge_base 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入知識庫頁面失敗時
    """
    try:
        from src.ui.pages.knowledge_base import show as knowledge_show
        knowledge_show()
        
    except ImportError as e:
        logger.warning("無法導入知識庫頁面: %s", e)
        st.warning("⚠️ 知識庫功能暫時不可用")
        _show_fallback_knowledge_base()
        
    except Exception as e:
        logger.error("顯示知識庫時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 知識庫功能載入失敗")
        _show_fallback_knowledge_base()


def _show_learning_center() -> None:
    """顯示學習中心功能.
    
    調用原有的 learning_center 頁面功能。
    
    Returns:
        None
        
    Raises:
        Exception: 當載入學習中心頁面失敗時
    """
    try:
        from src.ui.pages.learning_center import show as learning_show
        learning_show()
        
    except ImportError as e:
        logger.warning("無法導入學習中心頁面: %s", e)
        st.warning("⚠️ 學習中心功能暫時不可用")
        _show_fallback_learning_center()
        
    except Exception as e:
        logger.error("顯示學習中心時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 學習中心功能載入失敗")
        _show_fallback_learning_center()


# 備用顯示函數
def _show_fallback_beginner_hub() -> None:
    """新手中心的備用顯示函數."""
    st.info("🎯 新手中心功能正在載入中...")
    
    st.markdown("""
    **新手中心** 為新用戶提供完整的入門指導，包括：
    - 🚀 **快速開始**: 系統基本操作和功能介紹
    - 📋 **功能概覽**: 各個模組的功能說明和使用方法
    - 🎯 **實戰演練**: 模擬交易和策略測試
    - 💡 **常見問題**: 新手常見問題和解決方案
    """)
    
    # 顯示快速開始指南
    st.markdown("### 🚀 快速開始指南")
    
    steps = [
        {"步驟": "1", "標題": "系統註冊", "描述": "創建您的交易系統帳戶", "狀態": "✅ 已完成"},
        {"步驟": "2", "標題": "基本設定", "描述": "配置基本的交易參數和偏好", "狀態": "🔄 進行中"},
        {"步驟": "3", "標題": "模擬交易", "描述": "使用模擬資金進行交易練習", "狀態": "⏳ 待開始"},
        {"步驟": "4", "標題": "策略學習", "描述": "學習基本的交易策略和分析方法", "狀態": "⏳ 待開始"}
    ]
    
    for step in steps:
        with st.expander(f"步驟 {step['步驟']}: {step['標題']} - {step['狀態']}"):
            st.write(f"**描述**: {step['描述']}")
            if step['狀態'] == "🔄 進行中":
                if st.button(f"繼續步驟 {step['步驟']}", key=f"continue_{step['步驟']}"):
                    st.info(f"步驟 {step['步驟']} 功能開發中...")


def _show_fallback_beginner_tutorial() -> None:
    """新手教學的備用顯示函數."""
    st.info("📖 新手教學功能正在載入中...")
    st.markdown("**教學內容**：逐步教學、實作練習、進度追蹤")


def _show_fallback_knowledge_base() -> None:
    """知識庫的備用顯示函數."""
    st.info("📚 知識庫功能正在載入中...")
    st.markdown("**知識庫**：系統文檔、API參考、最佳實踐")


def _show_fallback_learning_center() -> None:
    """學習中心的備用顯示函數."""
    st.info("🎓 學習中心功能正在載入中...")
    st.markdown("**學習資源**：進階課程、專家分享、社群討論")
