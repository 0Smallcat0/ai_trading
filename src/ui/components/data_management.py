"""
數據處理組件 (重構版)

此模組提供數據處理的統一入口點，直接調用重構後的數據處理頁面。
重構後的頁面提供兩個核心功能：
1. 資料更新 - 手動更新和批量更新功能
2. 資料檢視 - 股票搜尋和圖表顯示功能

主要特點：
- 簡化的介面設計
- 專注於核心功能
- 完整的錯誤處理
- 直接調用重構後的頁面

Example:
    使用方式：
    ```python
    from src.ui.components.data_management import show
    show()  # 顯示重構後的數據處理介面
    ```

Note:
    此組件直接調用 src.ui.pages.data_management 的 show() 函數，
    移除了複雜的標籤頁結構，提供更簡潔的用戶體驗。
"""

import logging

import streamlit as st

logger = logging.getLogger(__name__)


def show() -> None:
    """顯示數據處理主介面.

    直接調用重構後的數據處理頁面，提供兩個核心功能：
    1. 資料更新 - 手動更新和批量更新功能
    2. 資料檢視 - 股票搜尋和圖表顯示功能

    Side Effects:
        - 渲染 Streamlit 界面組件
        - 可能修改 st.session_state 中的相關狀態

    Example:
        >>> show()  # 顯示重構後的數據處理介面

    Note:
        此函數直接調用重構後的數據處理頁面，移除了複雜的標籤頁結構。
    """
    try:
        # 直接調用重構後的數據處理頁面
        from src.ui.pages.data_management import show as data_management_show
        data_management_show()

    except ImportError as e:
        logger.error("無法導入數據處理頁面: %s", e, exc_info=True)
        st.error("❌ 數據處理頁面不可用")
        st.info("請檢查 src.ui.pages.data_management 模組是否正確安裝")
        with st.expander("錯誤詳情"):
            st.code(str(e))

    except Exception as e:
        logger.error("顯示數據處理介面時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 數據處理介面載入失敗")
        with st.expander("錯誤詳情"):
            st.code(str(e))


def get_module_info() -> dict:
    """
    獲取數據處理模組資訊

    Returns:
        dict: 包含模組版本、功能和狀態的資訊字典
    """
    return {
        "name": "數據處理組件",
        "version": "3.0.0",
        "description": "重構後的數據處理組件，直接調用簡化的數據處理頁面",
        "features": [
            "資料更新 - 手動更新和批量更新功能",
            "資料檢視 - 股票搜尋和圖表顯示功能",
        ],
        "status": "已重構完成",
    }


if __name__ == "__main__":
    # 用於測試組件
    show()