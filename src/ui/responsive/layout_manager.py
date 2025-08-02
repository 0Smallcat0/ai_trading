"""響應式佈局管理器

此模組負責管理整個應用程式的響應式佈局行為。
"""

import streamlit as st
from typing import List, Any, Dict, Optional
from .breakpoints import ResponsiveBreakpoints
from .css_manager import ResponsiveCSS


class ResponsiveLayoutManager:
    """響應式佈局管理器

    負責管理整個應用程式的響應式佈局行為，包括斷點檢測、樣式應用、
    列數配置等核心功能。此類別是響應式設計系統的核心控制器，
    提供統一的介面來處理不同裝置的佈局需求。

    主要功能：
    - 自動檢測當前裝置類型（手機、平板、桌面）
    - 動態應用對應的響應式樣式
    - 提供智能的列數配置建議
    - 管理斷點狀態和裝置特性
    - 整合 Streamlit 特定的響應式覆蓋樣式

    屬性：
        current_breakpoint: 當前斷點類型（mobile/tablet/desktop）
        is_mobile: 是否為手機裝置
        is_tablet: 是否為平板裝置
        is_desktop: 是否為桌面裝置

    使用範例：
        >>> manager = ResponsiveLayoutManager()
        >>> manager.apply_responsive_styles()
        >>> cols = manager.get_columns_config(desktop=4, tablet=2, mobile=1)
    """

    def __init__(self):
        """初始化響應式佈局管理器

        建立響應式佈局管理器實例，自動檢測當前裝置類型並設定相關屬性。
        初始化過程包括斷點檢測、裝置類型判斷和狀態設定。

        Side Effects:
            - 設定 self.current_breakpoint 為檢測到的斷點類型
            - 設定 is_mobile、is_tablet、is_desktop 布林屬性
            - 可能修改 st.session_state.screen_width（如果不存在）
        """
        self.current_breakpoint = self._detect_breakpoint()
        self.is_mobile = self.current_breakpoint == "mobile"
        self.is_tablet = self.current_breakpoint == "tablet"
        self.is_desktop = self.current_breakpoint == "desktop"

    def _detect_breakpoint(self) -> str:
        """檢測當前斷點類型

        根據螢幕寬度檢測當前裝置應該使用的斷點類型。目前使用簡化版本，
        通過 session state 模擬螢幕寬度檢測。在實際應用中，可以通過
        JavaScript 獲取真實的螢幕寬度進行更精確的檢測。

        Returns:
            str: 斷點類型，可能的值為：
                - "mobile": 螢幕寬度 < 768px
                - "tablet": 螢幕寬度 768px-1024px
                - "desktop": 螢幕寬度 > 1024px

        Note:
            目前使用 session state 模擬，預設寬度為 1200px（桌面）
            實際部署時建議整合 JavaScript 進行真實寬度檢測
        """
        # 在實際應用中，這裡可以通過 JavaScript 獲取真實的螢幕寬度
        # 這裡使用 session state 來模擬
        if "screen_width" not in st.session_state:
            st.session_state.screen_width = 1200  # 預設為桌面

        width = st.session_state.screen_width
        return ResponsiveBreakpoints.get_device_type(width)

    def apply_responsive_styles(self) -> None:
        """應用響應式樣式

        將完整的響應式 CSS 樣式應用到當前 Streamlit 應用程式中。
        包括基礎響應式樣式和 Streamlit 特定的樣式覆蓋，確保所有
        UI 組件都能正確響應不同裝置的螢幕尺寸。

        應用的樣式包括：
        - 基礎響應式網格系統
        - 響應式卡片和按鈕樣式
        - Streamlit 組件的響應式覆蓋
        - 觸控優化和無障礙支援
        - 深色模式和高對比度支援

        Returns:
            None

        Side Effects:
            在 Streamlit 應用程式中注入 CSS 樣式
        """
        # 應用基礎響應式樣式
        st.markdown(ResponsiveCSS.get_base_styles(), unsafe_allow_html=True)

        # 應用 Streamlit 特定樣式
        st.markdown(ResponsiveCSS.get_streamlit_overrides(), unsafe_allow_html=True)

    def get_columns_config(
        self, desktop: int = 4, tablet: int = 2, mobile: int = 1
    ) -> int:
        """根據螢幕尺寸獲取列數配置

        根據當前檢測到的裝置類型，返回適合的列數配置。這個方法是
        響應式佈局的核心，確保在不同裝置上都能提供最佳的使用體驗。

        Args:
            desktop: 桌面裝置的列數，預設為 4
            tablet: 平板裝置的列數，預設為 2
            mobile: 手機裝置的列數，預設為 1

        Returns:
            int: 適合當前裝置的列數配置

        Example:
            >>> manager = ResponsiveLayoutManager()
            >>> cols_count = manager.get_columns_config(desktop=3, tablet=2, mobile=1)
            >>> columns = st.columns(cols_count)
        """
        if self.is_mobile:
            return mobile
        elif self.is_tablet:
            return tablet
        else:
            return desktop

    def create_responsive_columns(
        self, desktop_cols: int = 4, tablet_cols: int = 2, mobile_cols: int = 1
    ) -> List[Any]:
        """創建響應式列佈局

        根據當前裝置類型創建適當數量的 Streamlit 列，實現響應式佈局。
        在不同裝置上自動調整列數以提供最佳的使用體驗。

        Args:
            desktop_cols: 桌面裝置的列數，預設為 4
            tablet_cols: 平板裝置的列數，預設為 2
            mobile_cols: 手機裝置的列數，預設為 1

        Returns:
            List[Any]: Streamlit 列物件列表

        Example:
            >>> manager = ResponsiveLayoutManager()
            >>> cols = manager.create_responsive_columns(3, 2, 1)
            >>> with cols[0]:
            ...     st.write("第一列內容")
        """
        cols_count = self.get_columns_config(desktop_cols, tablet_cols, mobile_cols)
        return st.columns(cols_count)

    def get_chart_height(self, default: int = 400) -> int:
        """根據螢幕尺寸獲取圖表高度

        Args:
            default: 預設高度

        Returns:
            int: 適合當前裝置的圖表高度
        """
        if self.is_mobile:
            return min(default, 300)
        elif self.is_tablet:
            return min(default, 350)
        else:
            return default

    def get_button_config(self) -> Dict[str, Any]:
        """獲取按鈕配置

        Returns:
            Dict[str, Any]: 按鈕配置字典
        """
        if self.is_mobile:
            return {"use_container_width": True, "type": "primary"}
        else:
            return {"use_container_width": False, "type": "secondary"}

    def render_mobile_friendly_table(
        self,
        data: List[Dict[str, Any]],
        headers: List[str],
        title: Optional[str] = None,
    ):
        """渲染行動裝置友善的表格

        Args:
            data: 表格資料
            headers: 表頭列表
            title: 表格標題
        """
        if title:
            st.subheader(title)

        if self.is_mobile:
            # 手機版：使用卡片式顯示
            for i, row in enumerate(data):
                with st.expander(f"項目 {i+1}", expanded=False):
                    for header in headers:
                        if header in row:
                            st.markdown(f"**{header}**: {row[header]}")
        else:
            # 桌面/平板版：使用標準表格
            import pandas as pd

            df = pd.DataFrame(data)
            if headers:
                df = df[headers]
            st.dataframe(df, use_container_width=True)

    def create_responsive_sidebar(self, content_func: callable):
        """創建響應式側邊欄

        Args:
            content_func: 側邊欄內容函數
        """
        if self.is_mobile:
            # 手機版：使用摺疊式側邊欄
            with st.expander("📱 選單", expanded=False):
                content_func()
        else:
            # 桌面/平板版：使用標準側邊欄
            with st.sidebar:
                content_func()


# 全域響應式管理器實例
responsive_manager = ResponsiveLayoutManager()
