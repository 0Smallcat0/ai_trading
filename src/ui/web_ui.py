"""Web UI 主模組

此模組實現了基於 Streamlit 的 Web 使用者介面，提供系統的所有功能操作。

主要功能：
- 用戶認證和權限管理
- 多頁面導航系統
- 響應式設計支援
- 統一的錯誤處理

Example:
    啟動 Web UI：
    ```python
    from src.ui.web_ui import run_web_ui
    run_web_ui()
    ```

Note:
    此模組依賴於 Streamlit 和相關 UI 組件，確保所有依賴已正確安裝。
"""

from typing import Tuple, Optional, Dict, Any
import logging

import streamlit as st

# 嘗試導入 streamlit_option_menu，如果失敗則提供備用方案
try:
    from streamlit_option_menu import option_menu

    OPTION_MENU_AVAILABLE = True
except ImportError:
    OPTION_MENU_AVAILABLE = False
    logging.warning("streamlit_option_menu 不可用，將使用備用導航方案")

# 導入頁面模組和組件
PAGES_AVAILABLE = True
AUTH_AVAILABLE = True

try:
    # 嘗試相對導入
    from .pages import (
        data_management,
        feature_engineering,
        strategy_management,
        ai_models,
        backtest,
        portfolio_management,
        risk_management,
        trade_execution,
        system_monitoring,
        reports,
        security_management,
        realtime_dashboard,
        interactive_charts,
        custom_dashboard,
        portfolio_management_advanced,
    )
    from .components import auth

    logging.info("成功導入所有頁面模組（相對導入）")
except ImportError as e:
    logging.warning("相對導入失敗: %s，嘗試絕對導入", e)
    try:
        # 嘗試絕對導入
        from src.ui.pages import (
            data_management,
            feature_engineering,
            strategy_management,
            ai_models,
            backtest,
            portfolio_management,
            risk_management,
            trade_execution,
            system_monitoring,
            reports,
            security_management,
            realtime_dashboard,
            interactive_charts,
            custom_dashboard,
            portfolio_management_advanced,
        )
        from src.ui.components import auth

        logging.info("成功導入所有頁面模組（絕對導入）")
    except ImportError as import_error:
        logging.error("無法導入頁面模組: %s", import_error)
        PAGES_AVAILABLE = False
        AUTH_AVAILABLE = False

        # 創建備用模組
        class MockModule:
            """備用模組類，當實際模組不可用時使用"""

            @staticmethod
            def show(*args, **kwargs):
                """備用顯示方法

                Args:
                    *args: 位置參數（未使用）
                    **kwargs: 關鍵字參數（未使用）
                """
                # 忽略未使用的參數
                _ = args, kwargs
                st.error("此功能模組暫時不可用，請檢查系統配置")

        # 創建備用頁面模組
        data_management = MockModule()
        feature_engineering = MockModule()
        strategy_management = MockModule()
        ai_models = MockModule()
        backtest = MockModule()
        portfolio_management = MockModule()
        risk_management = MockModule()
        trade_execution = MockModule()
        system_monitoring = MockModule()
        reports = MockModule()
        security_management = MockModule()
        realtime_dashboard = MockModule()
        interactive_charts = MockModule()
        custom_dashboard = MockModule()
        portfolio_management_advanced = MockModule()

        # 創建備用認證模組
        class MockAuth:
            """備用認證模組"""

            @staticmethod
            def login_form():
                st.error("認證系統暫時不可用")
                return False

        auth = MockAuth()

# 頁面配置將在 run_web_ui() 函數中設定

# 用戶角色與權限
USER_ROLES = {"admin": "管理員", "user": "一般用戶", "readonly": "只讀用戶"}

# 頁面配置
PAGES = {
    "realtime_dashboard": {
        "name": "即時儀表板",
        "icon": "speedometer2",
        "function": realtime_dashboard.show_realtime_dashboard,
        "min_role": "readonly",
    },
    "interactive_charts": {
        "name": "互動式圖表",
        "icon": "bar-chart",
        "function": interactive_charts.show_interactive_charts,
        "min_role": "readonly",
    },
    "custom_dashboard": {
        "name": "自定義儀表板",
        "icon": "grid-3x3",
        "function": custom_dashboard.show_custom_dashboard,
        "min_role": "user",
    },
    "data_management": {
        "name": "資料管理",
        "icon": "database",
        "function": data_management.show,
        "min_role": "user",
    },
    "feature_engineering": {
        "name": "特徵工程",
        "icon": "gear",
        "function": feature_engineering.show,
        "min_role": "user",
    },
    "strategy_management": {
        "name": "策略管理",
        "icon": "diagram-3",
        "function": strategy_management.show,
        "min_role": "user",
    },
    "ai_models": {
        "name": "AI 模型",
        "icon": "cpu",
        "function": ai_models.show,
        "min_role": "user",
    },
    "backtest": {
        "name": "回測",
        "icon": "arrow-repeat",
        "function": backtest.show,
        "min_role": "user",
    },
    "portfolio_management": {
        "name": "投資組合",
        "icon": "pie-chart",
        "function": portfolio_management.show,
        "min_role": "user",
    },
    "portfolio_management_advanced": {
        "name": "進階投資組合",
        "icon": "graph-up-arrow",
        "function": portfolio_management_advanced.show_portfolio_management_advanced,
        "min_role": "user",
    },
    "risk_management": {
        "name": "風險管理",
        "icon": "shield",
        "function": risk_management.show,
        "min_role": "user",
    },
    "trade_execution": {
        "name": "交易執行",
        "icon": "currency-exchange",
        "function": trade_execution.show,
        "min_role": "user",
    },
    "system_monitoring": {
        "name": "系統監控",
        "icon": "activity",
        "function": system_monitoring.show,
        "min_role": "readonly",
    },
    "reports": {
        "name": "報表查詢",
        "icon": "file-earmark-text",
        "function": reports.show,
        "min_role": "readonly",
    },
    "security_management": {
        "name": "安全管理",
        "icon": "shield-lock",
        "function": security_management.show_security_management,
        "min_role": "admin",
    },
}


def check_auth() -> Tuple[bool, str]:
    """檢查用戶認證狀態

    Returns:
        Tuple[bool, str]: (是否已認證, 用戶角色)
    """
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_role = None

    return st.session_state.authenticated, st.session_state.user_role


def show_login() -> None:
    """顯示登入頁面

    使用認證組件顯示用戶登入表單，處理用戶認證流程。

    Note:
        可能修改 st.session_state 中的認證相關狀態
    """
    auth.login_form()


def show_sidebar() -> Optional[str]:
    """顯示側邊欄導航

    在側邊欄中顯示用戶資訊、導航選單和登出按鈕。
    只有在用戶已認證的情況下才顯示完整的導航功能。
    支援 option_menu 和備用選擇框兩種導航方式。

    Returns:
        Optional[str]: 用戶選擇的頁面名稱，如果未選擇則返回 None

    Note:
        當 streamlit_option_menu 不可用時，會自動切換到標準選擇框。
        可能修改 st.session_state 中的認證狀態（登出時）。
    """
    with st.sidebar:
        st.title("AI 股票自動交易系統")

        # 顯示用戶資訊
        if st.session_state.get("authenticated", False):
            username = st.session_state.get("username", "未知用戶")
            user_role = st.session_state.get("user_role", "unknown")

            st.write(f"歡迎, {username}")
            st.write(f"角色: {USER_ROLES.get(user_role, '未知')}")

            # 選單 - 根據可用性選擇導航方式
            page_names = [page_info["name"] for page_info in PAGES.values()]

            if OPTION_MENU_AVAILABLE:
                try:
                    selected = option_menu(
                        "主選單",
                        options=page_names,
                        icons=[page_info["icon"] for page_info in PAGES.values()],
                        menu_icon="list",
                        default_index=0,
                    )
                except Exception as e:
                    logging.error("option_menu 執行錯誤: %s", e)
                    # 降級到標準選擇框
                    selected = st.selectbox("選擇頁面", page_names, index=0)
            else:
                # 使用標準選擇框作為備用方案
                selected = st.selectbox("選擇頁面", page_names, index=0)

            # 登出按鈕
            if st.button("登出", key="logout_button"):
                try:
                    st.session_state.authenticated = False
                    st.session_state.user_role = None
                    st.session_state.username = None
                    st.rerun()
                except Exception as e:
                    logging.error("登出過程發生錯誤: %s", e)
                    st.error("登出失敗，請重新整理頁面")

            return selected

    return None


def run_web_ui() -> None:
    """運行 Web UI 主應用程式

    這是 Web UI 的主要入口點，負責：
    1. 設定頁面配置和響應式設計
    2. 檢查用戶認證狀態
    3. 顯示登入頁面或主要應用介面
    4. 處理頁面路由和權限控制
    5. 統一的錯誤處理和日誌記錄

    Raises:
        Exception: 當發生無法處理的錯誤時

    Note:
        - 設定 Streamlit 頁面配置
        - 可能修改 st.session_state 中的各種狀態
        - 渲染 Streamlit 界面組件
        - 記錄操作日誌
    """
    try:
        # 設定頁面配置
        _setup_page_config()

        # 應用響應式設計
        _apply_responsive_design()

        # 檢查認證狀態
        authenticated, user_role = check_auth()

        if not authenticated:
            _show_login_page()
            return

        # 顯示主應用界面
        _show_main_application(user_role)

    except Exception as e:
        logging.error("Web UI 運行時發生嚴重錯誤: %s", e, exc_info=True)
        st.error("系統發生錯誤，請重新整理頁面或聯繫管理員")

        # 在開發模式下顯示詳細錯誤信息
        if st.session_state.get("debug_mode", False):
            with st.expander("錯誤詳情（開發模式）"):
                st.code(str(e))


def _setup_page_config() -> None:
    """設定 Streamlit 頁面配置

    配置頁面標題、圖示、佈局等基本設定。
    如果配置已經設定過，會忽略重複設定的錯誤。

    Raises:
        Exception: 當頁面配置設定失敗時
    """
    try:
        st.set_page_config(
            page_title="AI 股票自動交易系統",
            page_icon="📈",
            layout="wide",
            initial_sidebar_state="expanded",
            menu_items={
                "Get Help": "https://github.com/your-repo/help",
                "Report a bug": "https://github.com/your-repo/issues",
                "About": "AI 股票自動交易系統 v1.0",
            },
        )
        logging.info("頁面配置設定成功")
    except Exception as e:
        # 頁面配置已經設定過或其他錯誤
        if "set_page_config" in str(e):
            logging.debug("頁面配置已經設定過，跳過重複設定")
        else:
            logging.warning("頁面配置設定時發生警告: %s", e)


def _apply_responsive_design() -> None:
    """應用響應式設計樣式

    嘗試導入並應用響應式設計組件。
    如果響應式模組不可用，會記錄警告但不影響基本功能。
    """
    try:
        from .responsive import apply_responsive_design

        apply_responsive_design()
        logging.info("響應式設計樣式應用成功")
    except ImportError:
        logging.warning("響應式設計模組不可用，使用基本樣式")
    except Exception as e:
        logging.error("應用響應式設計時發生錯誤: %s", e)


def _show_login_page() -> None:
    """顯示登入頁面

    處理用戶登入流程，包括錯誤處理和狀態管理。
    """
    try:
        if AUTH_AVAILABLE:
            show_login()
        else:
            st.error("認證系統暫時不可用，請稍後再試")
            st.info("如果問題持續存在，請聯繫系統管理員")
    except Exception as e:
        logging.error("顯示登入頁面時發生錯誤: %s", e)
        st.error("登入系統發生錯誤，請重新整理頁面")


def _show_main_application(user_role: str) -> None:
    """顯示主應用程式界面

    Args:
        user_role: 用戶角色

    處理主應用程式的顯示邏輯，包括側邊欄導航和頁面路由。
    """
    try:
        # 顯示側邊欄並獲取選擇的頁面
        selected_page_name = show_sidebar()

        # 根據選擇顯示對應頁面
        if selected_page_name:
            _render_selected_page(selected_page_name, user_role)
        else:
            _show_default_dashboard()

    except Exception as e:
        logging.error("顯示主應用程式時發生錯誤: %s", e)
        st.error("載入頁面時發生錯誤")


def _render_selected_page(selected_page_name: str, user_role: str) -> None:
    """渲染選中的頁面

    Args:
        selected_page_name: 選中的頁面名稱
        user_role: 用戶角色
    """
    # 找到對應的頁面 ID
    selected_page_id = next(
        (
            page_id
            for page_id, page in PAGES.items()
            if page["name"] == selected_page_name
        ),
        None,
    )

    if not selected_page_id:
        st.error("找不到所選頁面")
        return

    page = PAGES[selected_page_id]

    # 檢查權限
    if not _check_page_permission(page, user_role):
        st.error("您沒有權限訪問此頁面")
        return

    # 顯示頁面
    try:
        st.title(page["name"])

        # 檢查頁面功能是否可用
        if PAGES_AVAILABLE or hasattr(page["function"], "__call__"):
            page["function"]()
        else:
            st.error("此頁面功能暫時不可用")

    except Exception as e:
        logging.error("渲染頁面 %s 時發生錯誤: %s", selected_page_name, e)
        st.error(f"載入 {selected_page_name} 頁面時發生錯誤")


def _check_page_permission(page: Dict[str, Any], user_role: str) -> bool:
    """檢查頁面訪問權限

    Args:
        page: 頁面配置字典
        user_role: 用戶角色

    Returns:
        bool: 是否有權限訪問
    """
    role_levels = {"admin": 3, "user": 2, "readonly": 1}
    min_role_level = role_levels.get(page.get("min_role", "readonly"), 0)
    user_role_level = role_levels.get(user_role, 0)

    return user_role_level >= min_role_level


def _show_default_dashboard() -> None:
    """顯示預設儀表板

    當沒有選擇特定頁面時顯示的預設內容。
    """
    st.title("AI 股票自動交易系統")
    st.markdown("---")

    # 系統狀態概覽
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("系統狀態", "正常運行", "✅")

    with col2:
        st.metric(
            "頁面模組",
            "已載入" if PAGES_AVAILABLE else "部分不可用",
            "✅" if PAGES_AVAILABLE else "⚠️",
        )

    with col3:
        st.metric(
            "認證系統",
            "已啟用" if AUTH_AVAILABLE else "不可用",
            "✅" if AUTH_AVAILABLE else "❌",
        )

    # 快速導航
    st.subheader("快速導航")
    st.info("請使用左側選單選擇要使用的功能模組")

    # 系統資訊
    with st.expander("系統資訊"):
        st.write("**版本**: 1.0.0")
        st.write("**框架**: Streamlit")
        st.write("**響應式設計**: 支援")
        st.write("**多用戶支援**: 是")


def main() -> None:
    """主函數，用於 Poetry 腳本入口點

    這是通過 Poetry 腳本啟動應用程式的入口點。
    在 pyproject.toml 中配置為 'start = "src.ui.web_ui:main"'。

    Example:
        通過命令行啟動：
        $ poetry run start
    """
    run_web_ui()


if __name__ == "__main__":
    main()
