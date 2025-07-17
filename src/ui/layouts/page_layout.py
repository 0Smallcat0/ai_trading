"""
Web UI 頁面佈局模組

此模組提供 Web UI 的頁面佈局和配置，包括：
- 頁面配置設定
- 響應式設計
- 統一的頁面結構

主要功能：
- 設定 Streamlit 頁面配置
- 應用響應式 CSS 樣式
- 提供統一的頁面模板
- 管理頁面主題和樣式

Example:
    >>> from src.ui.layouts.page_layout import setup_page_config, apply_responsive_design
    >>> setup_page_config()
    >>> apply_responsive_design()
"""

import logging
from typing import Dict, Any, Optional

import streamlit as st

logger = logging.getLogger(__name__)


def setup_page_config() -> None:
    """設定 Streamlit 頁面配置.

    Note:
        此函數應該在其他 Streamlit 組件之前調用

    Example:
        >>> setup_page_config()
    """
    try:
        st.set_page_config(
            page_title="AI 股票自動交易系統",
            page_icon="📈",
            layout="wide",
            initial_sidebar_state="collapsed",  # 修復：設定側邊欄為摺疊狀態
            menu_items={
                'Get Help': 'https://github.com/your-repo/help',
                'Report a bug': 'https://github.com/your-repo/issues',
                'About': """
                # AI 股票自動交易系統

                這是一個基於人工智慧的股票自動交易系統，提供：
                - 數據分析和特徵工程
                - 機器學習模型訓練
                - 策略回測和優化
                - 實盤和模擬交易
                - 風險管理和監控

                版本: v2.0
                """
            }
        )

        # 添加 CSS 樣式完全隱藏側邊欄
        _hide_sidebar_css()
        
        logger.debug("頁面配置設定完成")

    except Exception as e:
        logger.error("設定頁面配置時發生錯誤: %s", e, exc_info=True)


def _hide_sidebar_css() -> None:
    """添加 CSS 樣式完全隱藏側邊欄.

    使用 CSS 隱藏 Streamlit 的側邊欄元素，確保完全無側邊欄的介面。

    Returns:
        None

    Example:
        >>> _hide_sidebar_css()  # 隱藏側邊欄
    """
    try:
        # CSS 樣式隱藏側邊欄相關元素
        hide_sidebar_style = """
        <style>
        /* 隱藏側邊欄 */
        .css-1d391kg {
            display: none !important;
        }

        /* 隱藏側邊欄摺疊按鈕 */
        .css-1rs6os {
            display: none !important;
        }

        /* 隱藏側邊欄容器 */
        section[data-testid="stSidebar"] {
            display: none !important;
        }

        /* 隱藏側邊欄控制按鈕 */
        button[kind="header"] {
            display: none !important;
        }

        /* 調整主內容區域，移除側邊欄空間 */
        .main .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: none !important;
        }

        /* 確保主內容區域使用全寬 */
        .stApp > div:first-child {
            margin-left: 0 !important;
        }
        </style>
        """

        st.markdown(hide_sidebar_style, unsafe_allow_html=True)
        logger.debug("側邊欄 CSS 隱藏樣式已應用")

    except Exception as e:
        logger.error("應用側邊欄隱藏樣式時發生錯誤: %s", e, exc_info=True)


def apply_responsive_design() -> None:
    """應用響應式設計樣式.

    Note:
        此函數會注入 CSS 樣式到頁面中

    Example:
        >>> apply_responsive_design()
    """
    try:
        # 響應式 CSS 樣式
        responsive_css = """
        <style>
        /* 主要容器樣式 */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 100%;
        }
        
        /* 側邊欄樣式 */
        .sidebar .sidebar-content {
            background-color: #f0f2f6;
            border-radius: 10px;
            padding: 1rem;
        }
        
        /* 標題樣式 */
        h1, h2, h3 {
            color: #1f77b4;
            font-family: 'Arial', sans-serif;
        }
        
        /* 按鈕樣式 */
        .stButton > button {
            background-color: #1f77b4;
            color: white;
            border-radius: 5px;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            background-color: #1565c0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        
        /* 成功訊息樣式 */
        .stSuccess {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 5px;
            padding: 0.75rem;
            color: #155724;
        }
        
        /* 錯誤訊息樣式 */
        .stError {
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            border-radius: 5px;
            padding: 0.75rem;
            color: #721c24;
        }
        
        /* 警告訊息樣式 */
        .stWarning {
            background-color: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 5px;
            padding: 0.75rem;
            color: #856404;
        }
        
        /* 資訊訊息樣式 */
        .stInfo {
            background-color: #d1ecf1;
            border: 1px solid #bee5eb;
            border-radius: 5px;
            padding: 0.75rem;
            color: #0c5460;
        }
        
        /* 表格樣式 */
        .dataframe {
            border: 1px solid #ddd;
            border-radius: 5px;
            overflow: hidden;
        }
        
        .dataframe th {
            background-color: #f8f9fa;
            font-weight: bold;
            text-align: center;
        }
        
        /* 圖表容器樣式 */
        .plotly-graph-div {
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* 指標卡片樣式 */
        .metric-card {
            background-color: white;
            padding: 1rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #1f77b4;
        }
        
        /* 響應式設計 */
        @media (max-width: 768px) {
            .main .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }
            
            .sidebar .sidebar-content {
                padding: 0.5rem;
            }
        }
        
        /* 隱藏 Streamlit 預設元素 */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* 自定義滾動條 */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
        </style>
        """
        
        st.markdown(responsive_css, unsafe_allow_html=True)
        logger.debug("響應式設計樣式已應用")

    except Exception as e:
        logger.error("應用響應式設計時發生錯誤: %s", e, exc_info=True)


def show_page_header(title: str, description: Optional[str] = None, icon: str = "📊") -> None:
    """顯示頁面標題和描述.

    Args:
        title: 頁面標題
        description: 頁面描述
        icon: 頁面圖示

    Example:
        >>> show_page_header("儀表板", "系統總覽和即時監控", "📊")
    """
    try:
        st.markdown(f"# {icon} {title}")
        
        if description:
            st.markdown(f"*{description}*")
        
        st.markdown("---")

    except Exception as e:
        logger.error("顯示頁面標題時發生錯誤: %s", e, exc_info=True)


def show_loading_spinner(message: str = "載入中...") -> None:
    """顯示載入動畫.

    Args:
        message: 載入訊息

    Example:
        >>> show_loading_spinner("正在載入數據...")
    """
    try:
        with st.spinner(message):
            pass

    except Exception as e:
        logger.error("顯示載入動畫時發生錯誤: %s", e, exc_info=True)


def show_error_page(error_message: str, details: Optional[str] = None) -> None:
    """顯示錯誤頁面.

    Args:
        error_message: 錯誤訊息
        details: 錯誤詳情

    Example:
        >>> show_error_page("頁面載入失敗", "模組導入錯誤")
    """
    try:
        st.error(f"❌ {error_message}")
        
        if details:
            with st.expander("錯誤詳情"):
                st.code(details)
        
        st.markdown("---")
        st.info("請嘗試重新整理頁面或聯繫系統管理員")

    except Exception as e:
        logger.error("顯示錯誤頁面時發生錯誤: %s", e, exc_info=True)


def show_coming_soon_page(feature_name: str) -> None:
    """顯示功能開發中頁面.

    Args:
        feature_name: 功能名稱

    Example:
        >>> show_coming_soon_page("高級分析")
    """
    try:
        st.markdown("## 🚧 功能開發中")
        st.info(f"**{feature_name}** 功能正在開發中，敬請期待！")
        
        st.markdown("---")
        st.markdown("### 📋 開發計劃")
        st.markdown("""
        - ✅ 基礎架構設計
        - 🔄 核心功能開發
        - ⏳ 測試和優化
        - ⏳ 用戶介面完善
        """)

    except Exception as e:
        logger.error("顯示開發中頁面時發生錯誤: %s", e, exc_info=True)


def create_metric_card(title: str, value: str, delta: Optional[str] = None) -> None:
    """創建指標卡片.

    Args:
        title: 指標標題
        value: 指標值
        delta: 變化值

    Example:
        >>> create_metric_card("總收益", "12.5%", "+2.3%")
    """
    try:
        st.metric(
            label=title,
            value=value,
            delta=delta
        )

    except Exception as e:
        logger.error("創建指標卡片時發生錯誤: %s", e, exc_info=True)


def show_footer() -> None:
    """顯示頁面底部資訊.

    Example:
        >>> show_footer()
    """
    try:
        st.markdown("---")
        st.markdown(
            """
            <div style='text-align: center; color: #666; font-size: 0.8em;'>
                AI 股票自動交易系統 v2.0 | 
                © 2024 All Rights Reserved | 
                <a href='#' style='color: #1f77b4;'>使用說明</a> | 
                <a href='#' style='color: #1f77b4;'>技術支援</a>
            </div>
            """,
            unsafe_allow_html=True
        )

    except Exception as e:
        logger.error("顯示頁面底部時發生錯誤: %s", e, exc_info=True)


def apply_custom_theme(theme_name: str = "default") -> None:
    """應用自定義主題.

    Args:
        theme_name: 主題名稱

    Example:
        >>> apply_custom_theme("dark")
    """
    try:
        themes = {
            "default": {
                "primary_color": "#1f77b4",
                "background_color": "#ffffff",
                "text_color": "#262730"
            },
            "dark": {
                "primary_color": "#ff6b6b",
                "background_color": "#0e1117",
                "text_color": "#fafafa"
            },
            "green": {
                "primary_color": "#00cc88",
                "background_color": "#ffffff",
                "text_color": "#262730"
            }
        }
        
        theme = themes.get(theme_name, themes["default"])
        
        # 應用主題樣式
        theme_css = f"""
        <style>
        .stApp {{
            background-color: {theme["background_color"]};
            color: {theme["text_color"]};
        }}
        
        .stButton > button {{
            background-color: {theme["primary_color"]};
        }}
        </style>
        """
        
        st.markdown(theme_css, unsafe_allow_html=True)
        logger.debug("已應用主題: %s", theme_name)

    except Exception as e:
        logger.error("應用自定義主題時發生錯誤: %s", e, exc_info=True)
