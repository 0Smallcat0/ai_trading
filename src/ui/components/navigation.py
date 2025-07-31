"""
Web UI 導航組件模組

此模組提供 Web UI 的導航相關組件，包括：
- 側邊欄導航
- 頁面選單
- 權限控制的頁面訪問

主要功能：
- 實現響應式側邊欄導航
- 提供基於角色的頁面過濾
- 管理頁面路由和選擇
- 支援多種導航樣式

Example:
    >>> from src.ui.components.navigation import show_sidebar, get_available_pages
    >>> selected_page = show_sidebar()
    >>> pages = get_available_pages("admin")
"""

import logging
from typing import Optional, Dict, Any, List

import streamlit as st

# 嘗試導入 streamlit_option_menu
try:
    from streamlit_option_menu import option_menu
    OPTION_MENU_AVAILABLE = True
except ImportError:
    OPTION_MENU_AVAILABLE = False
    logging.warning("streamlit_option_menu 不可用，將使用備用導航方案")

logger = logging.getLogger(__name__)


def get_page_config() -> Dict[str, Dict[str, Any]]:
    """獲取頁面配置.

    Returns:
        Dict[str, Dict[str, Any]]: 頁面配置字典

    Example:
        >>> config = get_page_config()
        >>> print(config["dashboard"]["title"])
        '儀表板'
    """
    return {
        "dashboard": {
            "title": "儀表板",
            "icon": "📊",
            "module": "realtime_dashboard",
            "roles": ["admin", "trader", "analyst", "demo"],
            "description": "系統總覽和即時監控"
        },
        "data_management": {
            "title": "數據管理",
            "icon": "📈",
            "module": "data_management",
            "roles": ["admin", "analyst"],
            "description": "數據載入、清理和管理"
        },
        "feature_engineering": {
            "title": "特徵工程",
            "icon": "🔧",
            "module": "feature_engineering",
            "roles": ["admin", "analyst"],
            "description": "技術指標和特徵計算"
        },
        "advanced_technical_analysis": {
            "title": "進階技術分析",
            "icon": "📈",
            "module": "advanced_technical_analysis",
            "roles": ["admin", "trader", "analyst"],
            "description": "Williams %R、Stochastic、CCI、ATR 等進階技術指標"
        },
        "strategy_management": {
            "title": "策略管理",
            "icon": "🎯",
            "module": "strategy_management",
            "roles": ["admin", "trader", "analyst"],
            "description": "交易策略開發和管理"
        },
        "ai_models": {
            "title": "AI 模型",
            "icon": "🤖",
            "module": "ai_models",
            "roles": ["admin", "analyst"],
            "description": "機器學習模型訓練"
        },
        "rl_strategy_management": {
            "title": "RL 策略管理",
            "icon": "🧠",
            "module": "rl_strategy_management",
            "roles": ["admin", "trader", "analyst"],
            "description": "強化學習策略管理和訓練"
        },
        "backtest": {
            "title": "回測分析",
            "icon": "📉",
            "module": "backtest",
            "roles": ["admin", "trader", "analyst", "demo"],
            "description": "策略回測和績效分析"
        },
        "portfolio_management": {
            "title": "投資組合",
            "icon": "💼",
            "module": "portfolio_management",
            "roles": ["admin", "trader", "analyst"],
            "description": "投資組合管理和優化"
        },
        "learning_center": {
            "title": "學習中心",
            "icon": "🎓",
            "module": "learning_center",
            "roles": ["admin", "trader", "analyst", "demo"],
            "description": "交互式量化交易學習"
        },
        "knowledge_base": {
            "title": "知識庫",
            "icon": "📚",
            "module": "knowledge_base",
            "roles": ["admin", "trader", "analyst", "demo"],
            "description": "金融量化知識資源"
        },
        "risk_management": {
            "title": "風險管理",
            "icon": "⚠️",
            "module": "risk_management",
            "roles": ["admin", "trader"],
            "description": "風險控制和管理"
        },
        "trade_execution": {
            "title": "交易執行",
            "icon": "⚡",
            "module": "trade_execution",
            "roles": ["admin", "trader"],
            "description": "實盤和模擬交易"
        },
        "system_monitoring": {
            "title": "系統監控",
            "icon": "🖥️",
            "module": "system_monitoring",
            "roles": ["admin"],
            "description": "系統狀態和性能監控"
        },
        "reports": {
            "title": "報告中心",
            "icon": "📋",
            "module": "reports",
            "roles": ["admin", "trader", "analyst", "demo"],
            "description": "各類報告和分析"
        }
    }


def get_available_pages(user_role: str) -> Dict[str, Dict[str, Any]]:
    """根據用戶角色獲取可用頁面.

    Args:
        user_role: 用戶角色

    Returns:
        Dict[str, Dict[str, Any]]: 可用頁面配置

    Example:
        >>> pages = get_available_pages("trader")
        >>> print(len(pages))  # 顯示可用頁面數量
    """
    try:
        all_pages = get_page_config()
        available_pages = {}

        for page_key, page_config in all_pages.items():
            if user_role in page_config.get("roles", []):
                available_pages[page_key] = page_config

        logger.debug("用戶 %s 可訪問 %d 個頁面", user_role, len(available_pages))
        return available_pages

    except Exception as e:
        logger.error("獲取可用頁面時發生錯誤: %s", e, exc_info=True)
        return {}


def show_sidebar() -> Optional[str]:
    """顯示側邊欄導航.

    Returns:
        Optional[str]: 選中的頁面名稱

    Example:
        >>> selected_page = show_sidebar()
        >>> if selected_page:
        ...     print(f"選中頁面: {selected_page}")
    """
    try:
        # 獲取用戶角色
        user_role = st.session_state.get("user_role", "")
        username = st.session_state.get("username", "")

        if not user_role:
            return None

        # 獲取可用頁面
        available_pages = get_available_pages(user_role)

        if not available_pages:
            st.warning("沒有可用的頁面")
            return None

        # 顯示用戶資訊
        _show_user_info(username, user_role)

        # 顯示導航選單
        if OPTION_MENU_AVAILABLE:
            selected_page = _show_option_menu(available_pages)
        else:
            selected_page = _show_selectbox_menu(available_pages)

        # 顯示登出按鈕
        _show_logout_button()

        return selected_page

    except Exception as e:
        logger.error("顯示側邊欄時發生錯誤: %s", e, exc_info=True)
        return None


def _show_user_info(username: str, user_role: str) -> None:
    """顯示用戶資訊.

    Args:
        username: 用戶名
        user_role: 用戶角色

    Example:
        >>> _show_user_info("admin", "admin")
    """
    try:
        # 修復：移除 st.sidebar，改為主頁面顯示（此函數已不再使用）
        st.markdown("---")
        st.markdown("### 👤 用戶資訊")
        st.markdown(f"**用戶**: {username}")
        st.markdown(f"**角色**: {user_role}")
        st.markdown("---")

    except Exception as e:
        logger.error("顯示用戶資訊時發生錯誤: %s", e, exc_info=True)


def _show_option_menu(available_pages: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """使用 option_menu 顯示導航選單.

    Args:
        available_pages: 可用頁面配置

    Returns:
        Optional[str]: 選中的頁面名稱

    Example:
        >>> pages = get_available_pages("admin")
        >>> selected = _show_option_menu(pages)
    """
    try:
        page_names = list(available_pages.keys())
        page_titles = [page["title"] for page in available_pages.values()]
        page_icons = [page["icon"] for page in available_pages.values()]

        # 修復：移除 st.sidebar，改為主頁面顯示
        selected_index = option_menu(
            menu_title="📋 功能選單",
            options=page_titles,
            icons=page_icons,
            menu_icon="cast",
            default_index=0,
            orientation="horizontal",  # 改為水平方向適合主頁面
            styles={
                "container": {"padding": "0!important", "background-color": "#fafafa"},
                "icon": {"color": "orange", "font-size": "18px"},
                "nav-link": {
                    "font-size": "16px",
                    "text-align": "center",  # 水平佈局使用居中對齊
                    "margin": "0px",
                    "--hover-color": "#eee",
                },
                "nav-link-selected": {"background-color": "#02ab21"},
            },
        )

        if 0 <= selected_index < len(page_names):
            return page_names[selected_index]
        
        return None

    except Exception as e:
        logger.error("顯示 option_menu 時發生錯誤: %s", e, exc_info=True)
        return None


def _show_selectbox_menu(available_pages: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """使用 selectbox 顯示導航選單（備用方案）.

    Args:
        available_pages: 可用頁面配置

    Returns:
        Optional[str]: 選中的頁面名稱

    Example:
        >>> pages = get_available_pages("admin")
        >>> selected = _show_selectbox_menu(pages)
    """
    try:
        st.sidebar.markdown("### 📋 功能選單")
        
        page_options = {}
        for page_key, page_config in available_pages.items():
            display_name = f"{page_config['icon']} {page_config['title']}"
            page_options[display_name] = page_key

        if not page_options:
            return None

        selected_display = st.sidebar.selectbox(
            "選擇功能",
            options=list(page_options.keys()),
            index=0
        )

        return page_options.get(selected_display)

    except Exception as e:
        logger.error("顯示 selectbox 選單時發生錯誤: %s", e, exc_info=True)
        return None


def _show_logout_button() -> None:
    """顯示登出按鈕.

    Example:
        >>> _show_logout_button()
    """
    try:
        st.sidebar.markdown("---")
        if st.sidebar.button("🚪 登出", use_container_width=True):
            from .auth_component import logout_user
            logout_user()

    except Exception as e:
        logger.error("顯示登出按鈕時發生錯誤: %s", e, exc_info=True)


def check_page_permission(page_key: str, user_role: str) -> bool:
    """檢查頁面訪問權限.

    Args:
        page_key: 頁面鍵值
        user_role: 用戶角色

    Returns:
        bool: 是否有權限訪問

    Example:
        >>> has_permission = check_page_permission("admin_panel", "admin")
        >>> print(has_permission)
        True
    """
    try:
        page_config = get_page_config()
        page = page_config.get(page_key)
        
        if not page:
            return False

        return user_role in page.get("roles", [])

    except Exception as e:
        logger.error("檢查頁面權限時發生錯誤: %s", e, exc_info=True)
        return False


def get_page_module_name(page_key: str) -> Optional[str]:
    """獲取頁面對應的模組名稱.

    Args:
        page_key: 頁面鍵值

    Returns:
        Optional[str]: 模組名稱

    Example:
        >>> module_name = get_page_module_name("dashboard")
        >>> print(module_name)
        'realtime_dashboard'
    """
    try:
        page_config = get_page_config()
        page = page_config.get(page_key)
        
        if page:
            return page.get("module")
        
        return None

    except Exception as e:
        logger.error("獲取頁面模組名稱時發生錯誤: %s", e, exc_info=True)
        return None
