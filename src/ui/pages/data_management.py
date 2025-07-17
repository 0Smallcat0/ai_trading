"""
資料管理頁面 - 重構版本

此模組作為資料管理系統的主要入口點，整合各個子模組功能。
已重構為模組化架構，將原本的大型檔案拆分為專門的功能模組。

主要功能包括：
- 資料來源狀態監控和管理 (data_sources.py)
- 多種資料類型的更新和同步 (data_update.py)
- 靈活的資料查詢和篩選 (data_query.py)
- 資料品質監控和異常檢測 (data_quality.py)
- 資料清理和匯出工具 (data_export.py)
- 完整的更新日誌追蹤

模組結構：
    - data_sources.py: 資料來源管理功能
    - data_update.py: 資料更新和同步邏輯
    - data_query.py: 資料查詢和篩選功能
    - data_quality.py: 資料品質監控和驗證
    - data_export.py: 資料匯出和報告工具

Example:
    使用方式：
    ```python
    from src.ui.pages.data_management import show
    show()  # 顯示資料管理主頁面
    ```

Note:
    此模組依賴於 DataManagementService 來執行實際的資料管理邏輯。
    所有資料操作都會記錄在更新日誌中以便追蹤。

    重構後的模組化設計確保每個檔案不超過300行，
    提高程式碼可維護性和可讀性。
"""

from typing import Optional

import streamlit as st

# 導入資料處理模組
try:
    from src.core.data_management_service import DataManagementService
except ImportError as e:
    st.error(f"無法導入必要的模組: {e}")
    DataManagementService = None

# 導入子模組功能
try:
    from src.ui.pages.data_management.data_export import show_data_export_tools
    from src.ui.pages.data_management.data_quality import show_data_quality_monitoring
    from src.ui.pages.data_management.data_query import show_data_query_interface
    from src.ui.pages.data_management.data_sources import show_data_sources_management
    from src.ui.pages.data_management.data_update import show_data_update_management
except ImportError as e:
    st.error(f"資料管理子模組導入失敗: {e}")

    # 提供錯誤處理的替代函數
    def show_data_sources_management() -> None:
        st.error("資料來源管理模組不可用")

    def show_data_update_management() -> None:
        st.error("資料更新管理模組不可用")

    def show_data_query_interface() -> None:
        st.error("資料查詢介面模組不可用")

    def show_data_quality_monitoring() -> None:
        st.error("資料品質監控模組不可用")

    def show_data_export_tools() -> None:
        st.error("資料匯出工具模組不可用")


def initialize_data_service() -> Optional[DataManagementService]:
    """
    初始化資料管理服務

    Returns:
        Optional[DataManagementService]: 資料管理服務實例，如果初始化失敗則返回 None

    Example:
        ```python
        service = initialize_data_service()
        if service:
            print("資料管理服務初始化成功")
        ```
    """
    if "data_service" not in st.session_state:
        try:
            if DataManagementService:
                st.session_state.data_service = DataManagementService()
            else:
                st.session_state.data_service = None
        except Exception as e:
            st.error(f"初始化資料管理服務失敗: {e}")
            st.session_state.data_service = None

    if "update_task_id" not in st.session_state:
        st.session_state.update_task_id = None

    return st.session_state.data_service


def show() -> None:
    """
    顯示資料管理主頁面

    這是資料管理系統的主要入口點，提供完整的資料管理功能界面。
    使用標籤頁組織不同的功能模組，確保界面清晰易用。

    主要功能標籤：
    - 資料來源: 管理和監控各種資料來源的狀態
    - 資料更新: 手動觸發和監控資料更新任務
    - 資料查詢: 查詢和瀏覽歷史資料
    - 品質監控: 監控資料品質和異常檢測
    - 資料匯出: 匯出資料和生成報告

    Returns:
        None

    Side Effects:
        渲染完整的資料管理界面，包括所有子模組功能

    Example:
        ```python
        show()  # 顯示完整的資料管理界面
        ```

    Note:
        包含完整的錯誤處理，確保在子模組不可用時
        仍能提供基本的功能和友善的錯誤訊息。
    """
    st.title("📊 資料管理系統")

    # 初始化資料管理服務
    data_service = initialize_data_service()

    # 顯示服務狀態
    if data_service:
        st.success("✅ 資料管理服務已就緒")
    else:
        st.warning("⚠️ 資料管理服務未初始化，部分功能可能不可用")

    # 創建標籤頁
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📡 資料來源", "🔄 資料更新", "🔍 資料查詢", "📈 品質監控", "📤 資料匯出"]
    )

    # 資料來源管理標籤
    with tab1:
        try:
            show_data_sources_management()
        except Exception as e:
            st.error(f"資料來源管理功能發生錯誤: {e}")
            with st.expander("錯誤詳情"):
                st.code(str(e))

    # 資料更新管理標籤
    with tab2:
        try:
            show_data_update_management()
        except Exception as e:
            st.error(f"資料更新管理功能發生錯誤: {e}")
            with st.expander("錯誤詳情"):
                st.code(str(e))

    # 資料查詢標籤
    with tab3:
        try:
            show_data_query_interface()
        except Exception as e:
            st.error(f"資料查詢功能發生錯誤: {e}")
            with st.expander("錯誤詳情"):
                st.code(str(e))

    # 品質監控標籤
    with tab4:
        try:
            show_data_quality_monitoring()
        except Exception as e:
            st.error(f"品質監控功能發生錯誤: {e}")
            with st.expander("錯誤詳情"):
                st.code(str(e))

    # 資料匯出標籤
    with tab5:
        try:
            show_data_export_tools()
        except Exception as e:
            st.error(f"資料匯出功能發生錯誤: {e}")
            with st.expander("錯誤詳情"):
                st.code(str(e))


def get_module_info() -> dict:
    """
    獲取模組資訊

    Returns:
        dict: 包含模組版本、功能和狀態的資訊字典

    Example:
        ```python
        info = get_module_info()
        print(f"模組版本: {info['version']}")
        ```
    """
    return {
        "name": "資料管理系統",
        "version": "2.0.0",
        "description": "重構版資料管理系統，採用模組化架構",
        "modules": [
            "data_sources - 資料來源管理",
            "data_update - 資料更新管理",
            "data_query - 資料查詢介面",
            "data_quality - 資料品質監控",
            "data_export - 資料匯出工具",
        ],
        "features": [
            "模組化架構設計",
            "完整的錯誤處理",
            "100% 類型註解覆蓋",
            "Google Style 文檔字符串",
            "統一的異常處理模式",
        ],
        "status": "已重構完成",
    }


if __name__ == "__main__":
    # 用於測試模組
    show()
