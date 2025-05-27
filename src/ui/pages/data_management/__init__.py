"""
資料管理模組

此模組提供完整的資料管理功能，包括資料來源管理、資料更新、
資料查詢、資料品質監控和資料匯出等功能。

模組結構：
- data_sources.py: 資料來源管理功能
- data_update.py: 資料更新和同步邏輯
- data_query.py: 資料查詢和篩選功能
- data_quality.py: 資料品質監控和驗證
- data_export.py: 資料匯出和報告工具

主要功能：
- 資料來源狀態監控和管理
- 多種資料類型的更新和同步
- 靈活的資料查詢和篩選
- 資料品質監控和異常檢測
- 資料清理和匯出工具
- 完整的更新日誌追蹤

Example:
    使用方式：
    ```python
    from src.ui.pages.data_management import show
    show()  # 顯示資料管理主頁面
    ```

Note:
    此模組依賴於 DataManagementService 來執行實際的資料管理邏輯。
    所有資料操作都會記錄在更新日誌中以便追蹤。
"""

from typing import Optional

# 導入各子模組的主要函數
try:
    from .data_sources import show_data_sources_management
    from .data_update import show_data_update_management
    from .data_query import show_data_query_interface
    from .data_quality import show_data_quality_monitoring
    from .data_export import show_data_export_tools
except ImportError as e:
    # 如果子模組導入失敗，提供錯誤處理
    import streamlit as st

    st.error(f"資料管理子模組導入失敗: {e}")

    # 提供空的替代函數
    def show_data_sources_management():
        st.error("資料來源管理模組不可用")

    def show_data_update_management():
        st.error("資料更新管理模組不可用")

    def show_data_query_interface():
        st.error("資料查詢介面模組不可用")

    def show_data_quality_monitoring():
        st.error("資料品質監控模組不可用")

    def show_data_export_tools():
        st.error("資料匯出工具模組不可用")


def show() -> None:
    """
    顯示資料管理主頁面

    這是資料管理模組的主要入口點，提供完整的資料管理功能介面。
    使用標籤頁組織不同的功能模組，確保使用者體驗的一致性。

    主要功能標籤頁：
    1. 資料來源 - 資料來源狀態監控和管理
    2. 資料更新 - 手動和自動資料更新功能
    3. 資料查詢 - 靈活的資料查詢和篩選
    4. 資料品質 - 資料品質監控和驗證
    5. 資料匯出 - 資料匯出和報告工具

    Returns:
        None

    Side Effects:
        - 渲染 Streamlit 界面組件
        - 可能修改 st.session_state 中的相關狀態

    Example:
        ```python
        from src.ui.pages.data_management import show
        show()
        ```

    Note:
        此函數整合了所有資料管理子模組，提供統一的使用者介面。
        如果某個子模組不可用，會顯示相應的錯誤訊息。
    """
    import streamlit as st

    st.title("📊 資料管理")
    st.markdown("---")

    # 創建標籤頁
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📈 資料來源", "🔄 資料更新", "🔍 資料查詢", "✅ 資料品質", "📤 資料匯出"]
    )

    # 資料來源管理
    with tab1:
        try:
            show_data_sources_management()
        except Exception as e:
            st.error(f"資料來源管理功能發生錯誤: {e}")
            with st.expander("錯誤詳情"):
                st.code(str(e))

    # 資料更新管理
    with tab2:
        try:
            show_data_update_management()
        except Exception as e:
            st.error(f"資料更新管理功能發生錯誤: {e}")
            with st.expander("錯誤詳情"):
                st.code(str(e))

    # 資料查詢介面
    with tab3:
        try:
            show_data_query_interface()
        except Exception as e:
            st.error(f"資料查詢功能發生錯誤: {e}")
            with st.expander("錯誤詳情"):
                st.code(str(e))

    # 資料品質監控
    with tab4:
        try:
            show_data_quality_monitoring()
        except Exception as e:
            st.error(f"資料品質監控功能發生錯誤: {e}")
            with st.expander("錯誤詳情"):
                st.code(str(e))

    # 資料匯出工具
    with tab5:
        try:
            show_data_export_tools()
        except Exception as e:
            st.error(f"資料匯出功能發生錯誤: {e}")
            with st.expander("錯誤詳情"):
                st.code(str(e))


# 為了向後兼容，保留原始函數名稱
def show_data_management() -> None:
    """
    向後兼容的函數名稱

    這是為了保持與現有代碼的兼容性而提供的別名函數。
    實際功能由 show() 函數提供。

    Returns:
        None

    Deprecated:
        建議使用 show() 函數替代此函數
    """
    show()
