"""響應式設計工具函數

此模組提供響應式設計相關的工具函數和輔助功能。
"""

import streamlit as st
from typing import Dict, Any, List, Optional, Union
from .breakpoints import ResponsiveBreakpoints


class ResponsiveUtils:
    """響應式設計工具類

    提供響應式設計相關的工具函數和輔助功能，包括裝置檢測、
    樣式計算、佈局輔助等實用功能。

    主要功能：
    - 裝置類型檢測和判斷
    - 響應式尺寸計算
    - 觸控優化檢測
    - 佈局輔助函數
    - 樣式工具函數

    使用範例：
        >>> utils = ResponsiveUtils()
        >>> is_touch = utils.is_touch_device()
        >>> optimal_size = utils.get_optimal_font_size()
    """

    @staticmethod
    def detect_screen_width() -> int:
        """檢測螢幕寬度

        嘗試檢測當前裝置的螢幕寬度。在 Streamlit 環境中，
        這個功能有限，主要通過 session state 模擬。

        Returns:
            int: 螢幕寬度（像素），預設為 1200

        Note:
            在實際部署中，建議整合 JavaScript 來獲取真實的螢幕寬度
        """
        # 在實際應用中，可以通過 JavaScript 組件獲取真實寬度
        return st.session_state.get("screen_width", 1200)

    @staticmethod
    def set_screen_width(width: int) -> None:
        """設定螢幕寬度

        手動設定螢幕寬度，用於測試或模擬不同裝置。

        Args:
            width: 螢幕寬度（像素）
        """
        st.session_state.screen_width = width

    @staticmethod
    def get_device_info() -> Dict[str, Any]:
        """獲取裝置資訊

        Returns:
            Dict[str, Any]: 包含裝置資訊的字典，包含：
                - width: 螢幕寬度
                - device_type: 裝置類型
                - is_mobile: 是否為手機
                - is_tablet: 是否為平板
                - is_desktop: 是否為桌面
        """
        width = ResponsiveUtils.detect_screen_width()
        device_type = ResponsiveBreakpoints.get_device_type(width)

        return {
            "width": width,
            "device_type": device_type,
            "is_mobile": ResponsiveBreakpoints.is_mobile(width),
            "is_tablet": ResponsiveBreakpoints.is_tablet(width),
            "is_desktop": ResponsiveBreakpoints.is_desktop(width),
        }

    @staticmethod
    def is_touch_device() -> bool:
        """檢測是否為觸控裝置

        基於裝置類型推測是否為觸控裝置。手機和平板通常為觸控裝置，
        桌面裝置通常不是（除非是觸控螢幕）。

        Returns:
            bool: 是否為觸控裝置
        """
        device_info = ResponsiveUtils.get_device_info()
        return device_info["is_mobile"] or device_info["is_tablet"]

    @staticmethod
    def get_optimal_font_size(base_size: int = 14) -> int:
        """獲取最佳字體大小

        根據裝置類型計算最佳的字體大小，確保在不同裝置上
        都有良好的可讀性。

        Args:
            base_size: 基礎字體大小（像素）

        Returns:
            int: 最佳字體大小（像素）
        """
        device_info = ResponsiveUtils.get_device_info()

        if device_info["is_mobile"]:
            return max(base_size + 2, 16)  # 手機最小 16px
        elif device_info["is_tablet"]:
            return base_size + 1
        else:
            return base_size

    @staticmethod
    def get_optimal_spacing(base_spacing: int = 16) -> int:
        """獲取最佳間距

        根據裝置類型計算最佳的間距大小。

        Args:
            base_spacing: 基礎間距（像素）

        Returns:
            int: 最佳間距（像素）
        """
        device_info = ResponsiveUtils.get_device_info()

        if device_info["is_mobile"]:
            return base_spacing // 2
        elif device_info["is_tablet"]:
            return int(base_spacing * 0.75)
        else:
            return base_spacing

    @staticmethod
    def get_touch_target_size() -> int:
        """獲取觸控目標大小

        返回適合觸控操作的最小目標大小。根據 Apple 和 Google 的
        設計指南，觸控目標應該至少為 44x44 像素。

        Returns:
            int: 觸控目標大小（像素）
        """
        if ResponsiveUtils.is_touch_device():
            return 48  # 觸控裝置使用較大尺寸
        else:
            return 40  # 非觸控裝置可以稍小

    @staticmethod
    def calculate_grid_columns(
        total_items: int, max_cols: int = 4, min_cols: int = 1
    ) -> int:
        """計算網格列數

        根據項目總數和裝置類型計算最佳的網格列數。

        Args:
            total_items: 項目總數
            max_cols: 最大列數
            min_cols: 最小列數

        Returns:
            int: 建議的列數
        """
        device_info = ResponsiveUtils.get_device_info()

        # 根據裝置類型調整最大列數
        if device_info["is_mobile"]:
            device_max_cols = 1
        elif device_info["is_tablet"]:
            device_max_cols = min(2, max_cols)
        else:
            device_max_cols = max_cols

        # 根據項目數量調整
        if total_items <= min_cols:
            return total_items
        elif total_items <= device_max_cols:
            return total_items
        else:
            return device_max_cols

    @staticmethod
    def format_responsive_text(text: str, max_length: Optional[int] = None) -> str:
        """格式化響應式文字

        根據裝置類型調整文字長度和格式。

        Args:
            text: 原始文字
            max_length: 最大長度（可選）

        Returns:
            str: 格式化後的文字
        """
        device_info = ResponsiveUtils.get_device_info()

        if max_length is None:
            if device_info["is_mobile"]:
                max_length = 30
            elif device_info["is_tablet"]:
                max_length = 50
            else:
                max_length = 80

        if len(text) <= max_length:
            return text
        else:
            return text[: max_length - 3] + "..."

    @staticmethod
    def get_responsive_image_size() -> Dict[str, int]:
        """獲取響應式圖片尺寸

        Returns:
            Dict[str, int]: 包含寬度和高度的字典
        """
        device_info = ResponsiveUtils.get_device_info()

        if device_info["is_mobile"]:
            return {"width": 300, "height": 200}
        elif device_info["is_tablet"]:
            return {"width": 400, "height": 300}
        else:
            return {"width": 600, "height": 400}

    @staticmethod
    def create_responsive_container(content: str, css_class: str = "") -> str:
        """創建響應式容器

        Args:
            content: 容器內容
            css_class: 額外的 CSS 類別

        Returns:
            str: HTML 容器字串
        """
        base_class = "responsive-container"
        full_class = f"{base_class} {css_class}".strip()

        return f'<div class="{full_class}">{content}</div>'

    @staticmethod
    def get_breakpoint_info() -> Dict[str, Any]:
        """獲取斷點資訊

        Returns:
            Dict[str, Any]: 斷點資訊字典
        """
        return {
            "breakpoints": ResponsiveBreakpoints.get_breakpoints(),
            "current_device": ResponsiveUtils.get_device_info(),
            "touch_device": ResponsiveUtils.is_touch_device(),
            "optimal_font_size": ResponsiveUtils.get_optimal_font_size(),
            "touch_target_size": ResponsiveUtils.get_touch_target_size(),
        }

    @staticmethod
    def apply_responsive_page_config(
        page_title: str = "AI 交易系統", page_icon: str = "📈"
    ) -> None:
        """應用響應式頁面配置

        設定 Streamlit 頁面的響應式配置，包括頁面標題、圖示、
        佈局模式和側邊欄狀態。

        Args:
            page_title: 頁面標題
            page_icon: 頁面圖示

        Side Effects:
            - 設定 Streamlit 頁面配置
            - 應用響應式樣式
            - 注入螢幕尺寸檢測腳本
        """
        device_info = ResponsiveUtils.get_device_info()

        st.set_page_config(
            page_title=page_title,
            page_icon=page_icon,
            layout="wide",
            initial_sidebar_state=(
                "expanded" if not device_info["is_mobile"] else "collapsed"
            ),
        )

        # 應用響應式樣式
        from .layout_manager import responsive_manager

        responsive_manager.apply_responsive_styles()

        # 注入螢幕尺寸檢測
        ResponsiveUtils.inject_screen_size_detector()

    @staticmethod
    def inject_screen_size_detector() -> None:
        """注入螢幕尺寸檢測 JavaScript

        在頁面中注入 JavaScript 程式碼，用於即時檢測螢幕尺寸變化。
        通過 postMessage API 將螢幕尺寸資訊傳送給 Streamlit，
        實現真實的響應式斷點檢測。

        功能特點：
        - 即時檢測：監聽 window.resize 事件
        - 自動分類：根據寬度自動判斷裝置類型
        - 雙向通訊：使用 postMessage 與 Streamlit 通訊
        - 初始化檢測：頁面載入時立即執行檢測

        Returns:
            None

        Side Effects:
            在頁面中注入 JavaScript 程式碼，可能更新 st.session_state

        Note:
            此功能需要瀏覽器支援 JavaScript 和 postMessage API
            在不支援的環境中會回退到預設的斷點檢測
        """
        js_code = f"""
        <script>
        function updateScreenSize() {{
            const width = window.innerWidth;
            const height = window.innerHeight;

            // 發送螢幕尺寸到 Streamlit
            window.parent.postMessage({{
                type: 'streamlit:setComponentValue',
                value: {{
                    width: width,
                    height: height,
                    breakpoint: width < {ResponsiveBreakpoints.MOBILE} ? 'mobile' :
                               width < {ResponsiveBreakpoints.TABLET} ? 'tablet' : 'desktop'
                }}
            }}, '*');
        }}

        // 初始檢測
        updateScreenSize();

        // 監聽視窗大小變化
        window.addEventListener('resize', updateScreenSize);
        </script>
        """
        st.markdown(js_code, unsafe_allow_html=True)

    @staticmethod
    def get_responsive_config() -> Dict[str, Any]:
        """獲取完整的響應式配置

        Returns:
            Dict[str, Any]: 完整的響應式配置字典
        """
        device_info = ResponsiveUtils.get_device_info()
        breakpoint_info = ResponsiveUtils.get_breakpoint_info()

        return {
            **breakpoint_info,
            "current_breakpoint": device_info["device_type"],
            "screen_width": device_info["width"],
            "is_mobile": device_info["is_mobile"],
            "is_tablet": device_info["is_tablet"],
            "is_desktop": device_info["is_desktop"],
        }
