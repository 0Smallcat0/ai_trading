"""響應式 CSS 樣式管理器

此模組提供完整的響應式 CSS 樣式生成和管理功能。
"""

from .breakpoints import ResponsiveBreakpoints


class ResponsiveCSS:
    """響應式 CSS 樣式管理器

    提供完整的響應式 CSS 樣式生成和管理功能。包含基礎響應式樣式、
    Streamlit 特定的樣式覆蓋，以及針對不同裝置的優化樣式。

    主要功能：
    - 基礎響應式樣式（網格、卡片、按鈕等）
    - Streamlit 組件的響應式覆蓋樣式
    - 多裝置適配（手機、平板、桌面）
    - 觸控優化和無障礙支援
    - 深色模式和高對比度支援

    使用範例：
        >>> css = ResponsiveCSS.get_base_styles()
        >>> st.markdown(css, unsafe_allow_html=True)
    """

    @staticmethod
    def get_base_styles() -> str:
        """獲取基礎響應式樣式

        生成包含完整響應式設計的 CSS 樣式字串，包括網格系統、卡片、
        按鈕、表格、圖表容器等基礎組件的響應式樣式。

        Returns:
            str: 完整的 CSS 樣式字串，包含所有基礎響應式樣式

        Features:
            - 響應式網格系統（1-4 列）
            - 響應式卡片和按鈕設計
            - 觸控優化的最小尺寸
            - 多裝置媒體查詢
            - 無障礙和深色模式支援
        """
        try:
            from .css_components import CSSComponents
            from .css_media_queries import CSSMediaQueries

            return f"""
            <style>
            {CSSComponents.get_base_components()}
            {CSSMediaQueries.get_mobile_styles()}
            {CSSMediaQueries.get_tablet_styles()}
            {CSSMediaQueries.get_desktop_styles()}
            {CSSMediaQueries.get_accessibility_styles()}
            </style>
            """
        except ImportError:
            # 備用實作
            return ResponsiveCSS._get_fallback_styles()

    @staticmethod
    def get_streamlit_overrides() -> str:
        """獲取 Streamlit 特定的響應式覆蓋樣式

        生成針對 Streamlit 組件的響應式 CSS 覆蓋樣式，確保 Streamlit 的
        內建組件（按鈕、輸入框、表格等）能夠正確響應不同裝置的螢幕尺寸。

        Returns:
            str: Streamlit 組件的響應式覆蓋 CSS 樣式字串
        """
        try:
            from .css_streamlit import CSSStreamlit
            return CSSStreamlit.get_streamlit_overrides()
        except ImportError:
            # 備用實作
            return ResponsiveCSS._get_fallback_streamlit_styles()

    @staticmethod
    def _get_fallback_styles() -> str:
        """備用樣式實作"""
        return f"""
        <style>
        /* 基礎響應式樣式 */
        .responsive-container {{
            width: 100%;
            max-width: 100%;
            margin: 0 auto;
            padding: 0 1rem;
        }}

        /* 響應式網格 */
        .responsive-grid {{
            display: grid;
            gap: 1rem;
            width: 100%;
        }}

        .responsive-grid-1 {{ grid-template-columns: 1fr; }}
        .responsive-grid-2 {{ grid-template-columns: repeat(2, 1fr); }}
        .responsive-grid-3 {{ grid-template-columns: repeat(3, 1fr); }}
        .responsive-grid-4 {{ grid-template-columns: repeat(4, 1fr); }}

        /* 手機版調整 */
        @media (max-width: {ResponsiveBreakpoints.MOBILE - 1}px) {{
            .responsive-grid-2,
            .responsive-grid-3,
            .responsive-grid-4 {{
                grid-template-columns: 1fr;
            }}
        }}

        /* 平板版調整 */
        @media (min-width: {ResponsiveBreakpoints.MOBILE}px) and (max-width: {ResponsiveBreakpoints.TABLET - 1}px) {{
            .responsive-grid-3,
            .responsive-grid-4 {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
        </style>
        """

    @staticmethod
    def _get_fallback_streamlit_styles() -> str:
        """備用 Streamlit 樣式實作"""
        return f"""
        <style>
        /* Streamlit 響應式覆蓋 */
        .stButton > button {{
            width: 100%;
            min-height: 44px;
        }}

        @media (max-width: {ResponsiveBreakpoints.MOBILE - 1}px) {{
            .stButton > button {{
                min-height: 48px;
                font-size: 16px;
            }}
        }}
        </style>
        """
