"""Web UI 主模組 (性能優化版)

此模組是 Streamlit Web 應用程式的主入口點，整合各個 UI 組件：
- 用戶認證和權限管理
- 頁面路由和導航
- 整體 UI 佈局和樣式
- 性能優化和懶加載

主要功能：
- 提供統一的應用程式入口
- 整合認證、導航和頁面渲染組件
- 管理應用程式狀態和配置
- 應用響應式設計和主題
- 智能性能優化 (目標: <2秒加載時間)

使用方式：
    streamlit run src/ui/web_ui.py

Example:
    >>> # 啟動 Web 應用程式
    >>> python -m streamlit run src/ui/web_ui.py
"""

import logging
import time
import streamlit as st

try:
    from src.ui.components.auth_component import check_auth, show_login
    from src.ui.layouts.page_layout import setup_page_config, apply_responsive_design
    from src.ui.utils.page_renderer import render_page, show_default_dashboard
    from src.ui.utils.performance_optimizer import (
        performance_optimizer,
        optimize_page_load,
        enable_performance_optimizations,
        smart_state_manager,
        create_performance_dashboard
    )
    from src.ui.utils.lazy_loader import lazy_loader, lazy_component
    from src.ui.utils.cache_manager import cache_manager, optimize_memory_usage
except ImportError:
    # 備用導入方案
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))

    try:
        from src.ui.components.auth_component import check_auth, show_login
        from src.ui.layouts.page_layout import (
            setup_page_config, apply_responsive_design
        )
        from src.ui.utils.page_renderer import (
            render_page, show_default_dashboard
        )
        from src.ui.utils.performance_optimizer import (
            performance_optimizer,
            optimize_page_load,
            enable_performance_optimizations,
            smart_state_manager,
            create_performance_dashboard
        )
        from src.ui.utils.lazy_loader import lazy_loader, lazy_component
        from src.ui.utils.cache_manager import cache_manager, optimize_memory_usage
    except ImportError:
        # 備用導入方案
        try:
            from ui.components.auth_component import check_auth, show_login
            from ui.layouts.page_layout import (
                setup_page_config, apply_responsive_design
            )
            from ui.utils.page_renderer import (
                render_page, show_default_dashboard
            )
            from ui.utils.performance_optimizer import (
                performance_optimizer,
                optimize_page_load,
                enable_performance_optimizations,
                smart_state_manager,
                create_performance_dashboard
            )
            from ui.utils.lazy_loader import lazy_loader, lazy_component
            from ui.utils.cache_manager import cache_manager, optimize_memory_usage
        except ImportError:
            # 提供簡化的替代函數
            def check_auth():
                return True, "user"

            def show_login():
                st.info("登入功能暫時不可用")

            def show_sidebar_fallback():
                """向後相容性回退函數"""
                return "dashboard"

            def setup_page_config():
                st.set_page_config(
                    page_title="AI Trading System",
                    page_icon="📈",
                    layout="wide"
                )

            def apply_responsive_design():
                pass

            def render_page(page_key, user_role):
                st.info(f"頁面 '{page_key}' 正在載入中...")

            def show_default_dashboard():
                st.title("📊 AI Trading System Dashboard")
                st.info("系統儀表板正在載入中...")

            def preload_common_modules():
                pass

            # 性能優化相關的簡化函數
            class MockPerformanceOptimizer:
                """模擬性能優化器"""
                target_load_time = 2.0

                def optimize_session_state(self):
                    """優化 session state"""

            performance_optimizer = MockPerformanceOptimizer()

            def optimize_page_load(func):
                return func

            def enable_performance_optimizations():
                pass

            class MockStateManager:
                def cleanup_old_state(self):
                    pass

                def batch_update(self, updates):
                    for key, value in updates.items():
                        st.session_state[key] = value
                    return list(updates.keys())

            smart_state_manager = MockStateManager()

            def create_performance_dashboard():
                st.info("性能監控面板暫時不可用")

            class MockLazyLoader:
                """模擬懶加載器"""
                def load_component(self, name):
                    """載入組件"""

            lazy_loader = MockLazyLoader()

            def lazy_component(name):
                def decorator(func):
                    return func
                return decorator

logger = logging.getLogger(__name__)


@optimize_page_load
def main() -> None:
    """主應用程式入口點 (性能優化版).

    Example:
        >>> main()  # 啟動 Web 應用程式
    """
    start_time = time.time()

    try:
        # 初始化性能優化
        initialize_performance_optimizations()

        # 設定頁面配置（必須在其他 Streamlit 組件之前）
        setup_page_config()

        # 應用響應式設計
        apply_responsive_design()

        # 智能初始化 session state
        initialize_session_state_optimized()

        # 預載入關鍵組件
        preload_critical_components()

        # 暫時跳過登入功能，直接以開發者身份進入
        authenticated = True
        user_role = "admin"  # 給予管理員權限方便開發

        # 直接顯示主應用程式介面
        show_main_app_optimized(user_role)

        # 記錄總加載時間
        total_time = time.time() - start_time
        if total_time > performance_optimizer.target_load_time:
            logger.warning(
                "頁面加載時間 %.2fs 超過目標 %.2fs",
                total_time, performance_optimizer.target_load_time
            )

    except Exception as e:
        logger.error("主應用程式啟動失敗: %s", e, exc_info=True)
        st.error("❌ 應用程式啟動失敗，請重新整理頁面")

        # 顯示性能診斷信息（僅在開發模式）
        if st.session_state.get("debug_mode", False):
            with st.expander("🔧 性能診斷"):
                create_performance_dashboard()

def show_main_app(user_role: str) -> None:
    """顯示主應用程式介面 (整合版 - 無側邊欄).

    Args:
        user_role: 用戶角色

    Example:
        >>> show_main_app("admin")
    """
    try:
        # 顯示整合的主介面 (取代側邊欄)
        selected_page = show_main_interface()

        # 渲染選中的頁面
        if selected_page:
            render_page(selected_page, user_role)
        else:
            # 顯示預設儀表板
            show_default_dashboard()

    except Exception as e:
        logger.error("顯示主應用程式時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 應用程式載入失敗")


def run_web_ui() -> None:
    """運行 Web UI 應用程式.

    Note:
        此函數是外部調用的主要入口點

    Example:
        >>> from src.ui.web_ui import run_web_ui
        >>> run_web_ui()
    """
    try:
        logger.info("啟動 Web UI 應用程式")
        main()
        
    except Exception as e:
        logger.error("Web UI 應用程式運行失敗: %s", e, exc_info=True)
        st.error("❌ 系統啟動失敗，請聯繫系統管理員")


def initialize_session_state() -> None:
    """初始化 session state (舊版本，保持向後兼容).

    Example:
        >>> initialize_session_state()
    """
    initialize_session_state_optimized()


def initialize_session_state_optimized() -> None:
    """智能初始化 session state (性能優化版).

    使用批量更新和智能狀態管理，減少不必要的重新渲染。
    """
    try:
        # 準備批量更新
        updates = {}

        # 初始化認證相關狀態
        if "authenticated" not in st.session_state:
            updates["authenticated"] = False

        if "user_role" not in st.session_state:
            updates["user_role"] = ""

        if "username" not in st.session_state:
            updates["username"] = ""

        # 初始化應用程式狀態
        if "current_page" not in st.session_state:
            updates["current_page"] = "dashboard"

        if "app_initialized" not in st.session_state:
            updates["app_initialized"] = True

        # 初始化性能相關狀態
        if "performance_mode" not in st.session_state:
            updates["performance_mode"] = "optimized"

        if "lazy_loading_enabled" not in st.session_state:
            updates["lazy_loading_enabled"] = True

        if "debug_mode" not in st.session_state:
            updates["debug_mode"] = False

        # 批量更新狀態
        if updates:
            updated_keys = smart_state_manager.batch_update(updates)
            logger.debug(
                "Session state 初始化完成，更新了 %d 個狀態", len(updated_keys)
            )

    except Exception as e:
        logger.error("初始化 session state 時發生錯誤: %s", e, exc_info=True)


def get_app_info() -> dict:
    """獲取應用程式資訊.

    Returns:
        dict: 應用程式資訊字典

    Example:
        >>> info = get_app_info()
        >>> print(info["version"])
        'v2.0'
    """
    return {
        "name": "AI 股票自動交易系統",
        "version": "v2.0",
        "description": "基於人工智慧的股票自動交易系統",
        "author": "AI Trading Team",
        "license": "MIT",
        "features": [
            "數據分析和特徵工程",
            "機器學習模型訓練",
            "策略回測和優化",
            "實盤和模擬交易",
            "風險管理和監控"
        ]
    }


def check_system_requirements() -> bool:
    """檢查系統需求.

    Returns:
        bool: 是否滿足系統需求

    Example:
        >>> requirements_met = check_system_requirements()
        >>> print(requirements_met)
        True
    """
    try:
        # 檢查必要的套件
        required_packages = [
            "streamlit",
            "pandas",
            "numpy"
        ]
        
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            logger.error("缺少必要套件: %s", missing_packages)
            st.error(f"❌ 缺少必要套件: {', '.join(missing_packages)}")
            return False
        
        return True

    except Exception as e:
        logger.error("檢查系統需求時發生錯誤: %s", e, exc_info=True)
        return False


def initialize_performance_optimizations() -> None:
    """初始化性能優化設定"""
    try:
        # 啟用基本性能優化
        enable_performance_optimizations()

        # 設定快取策略
        cache_manager.max_memory_size = 200 * 1024 * 1024  # 200MB

        # 註冊關鍵組件到懶加載器
        register_critical_components()

        # 優化記憶體使用
        optimize_memory_usage()

        logger.info("性能優化初始化完成")

    except Exception as e:
        logger.error("性能優化初始化失敗: %s", e, exc_info=True)


def register_critical_components() -> None:
    """註冊關鍵組件到懶加載器"""
    try:
        # 註冊高優先級組件
        @lazy_component("dashboard", priority=10, preload=True, cache_ttl=600)
        def load_dashboard():
            try:
                # 嘗試導入現代化儀表板組件
                from src.ui.components import modern_dashboard
                return modern_dashboard
            except ImportError:
                try:
                    # 備用：嘗試導入基本儀表板
                    from src.ui import dashboard
                    return dashboard
                except ImportError:
                    logger.warning("載入組件 dashboard 失敗: 使用絕對導入")
                    return None

        @lazy_component("navigation", priority=9, preload=True, cache_ttl=300)
        def load_navigation():
            try:
                from src.ui.components import navigation
                return navigation
            except ImportError:
                logger.warning("載入組件 navigation 失敗: 使用絕對導入")
                return None

        @lazy_component("auth", priority=8, preload=True, cache_ttl=1800)
        def load_auth():
            try:
                from src.ui.components import auth_component
                return auth_component
            except ImportError:
                logger.warning("載入組件 auth 失敗: 使用絕對導入")
                return None

        logger.debug("關鍵組件註冊完成")

    except Exception as e:
        logger.error("註冊關鍵組件失敗: %s", e, exc_info=True)


def preload_critical_components() -> None:
    """預載入關鍵組件"""
    try:
        critical_components = ["dashboard", "navigation", "auth"]
        lazy_loader.preload_components(critical_components)
        logger.debug("關鍵組件預載入完成")

    except Exception as e:
        logger.error("預載入關鍵組件失敗: %s", e, exc_info=True)


def show_main_app_optimized(user_role: str) -> None:
    """顯示主應用程式介面 (性能優化版 - 整合版無側邊欄)

    Args:
        user_role: 用戶角色
    """
    try:
        # 定期優化 session state
        if st.session_state.get("auto_optimization", True):
            performance_optimizer.optimize_session_state()

        # 顯示整合的主介面（懶加載）
        selected_page = show_main_interface()

        # 渲染選中的頁面（懶加載）
        if selected_page:
            render_page(selected_page, user_role)
        else:
            # 顯示默認儀表板（懶加載）
            show_default_dashboard()

        # 在開發模式下顯示性能監控 (整合到主介面)
        if st.session_state.get("debug_mode", False):
            with st.expander("🔧 性能監控", expanded=False):
                if st.checkbox("顯示性能監控"):
                    create_performance_dashboard()

    except Exception as e:
        logger.error("顯示主應用程式介面失敗: %s", e, exc_info=True)
        st.error("❌ 載入應用程式介面時發生錯誤")


def show_main_interface() -> str:
    """顯示整合的主介面 (取代側邊欄功能).

    整合所有原側邊欄功能到主介面中，包括：
    - 系統導航和狀態
    - 用戶資訊和設置
    - 功能選單和快速操作

    Returns:
        str: 選中的頁面名稱

    Example:
        >>> selected_page = show_main_interface()
        >>> print(f"選中頁面: {selected_page}")
    """
    try:
        # 頂部導航區域 (3欄佈局)
        with st.container():
            col1, col2, col3 = st.columns([2, 4, 2])

            with col1:
                # 系統狀態指示器
                show_system_status_indicator()

            with col2:
                # 主要功能選單
                selected_page = show_main_navigation_menu()

            with col3:
                # 用戶資訊和快速操作
                show_user_info_and_actions()

        # 設定預設值：刷新間隔30秒，啟用懶加載
        if 'refresh_interval' not in st.session_state:
            st.session_state.refresh_interval = 30
        if 'lazy_loading_enabled' not in st.session_state:
            st.session_state.lazy_loading_enabled = True

        # 返回選中的頁面
        return selected_page or "dashboard"

    except Exception as e:
        logger.error("顯示主介面時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 主介面載入失敗")
        return "dashboard"


def show_system_status_indicator() -> None:
    """顯示系統狀態指示器.

    顯示系統運行狀態、連接狀態等關鍵指標。
    """
    try:
        st.markdown("### 🚦 系統狀態")

        # 系統運行狀態
        if st.session_state.get("system_healthy", True):
            st.success("✅ 系統運行正常")
        else:
            st.error("❌ 系統異常")

        # 連接狀態
        connection_status = st.session_state.get("connection_status", "connected")
        if connection_status == "connected":
            st.info("🔗 已連接")
        else:
            st.warning("⚠️ 連接異常")

    except Exception as e:
        logger.error("顯示系統狀態指示器時發生錯誤: %s", e, exc_info=True)
        st.error("狀態指示器載入失敗")


def show_main_navigation_menu() -> str:
    """顯示主要功能選單.

    提供主要功能頁面的導航選擇，整合12個功能分類。

    Returns:
        str: 選中的頁面名稱
    """
    try:
        st.markdown("### 🧭 功能導航")

        # 獲取用戶角色和可用頁面
        user_role = st.session_state.get("user_role", "user")

        # 定義13個功能分類 (重新設計的架構，新增進階圖表)
        available_pages = {
            "system_status_monitoring": {"title": "🖥️ 系統狀態監控", "icon": "🖥️"},
            "security_permission_management": {"title": "🔐 安全與權限管理", "icon": "🔐"},
            "multi_agent_system_management": {"title": "🤖 多代理系統管理", "icon": "🤖"},
            "data_management": {"title": "📊 數據管理", "icon": "📊"},
            "strategy_development": {"title": "🎯 策略開發", "icon": "🎯"},
            "ai_decision_support": {"title": "🧠 AI決策支援", "icon": "🧠"},
            "portfolio_management": {"title": "💼 投資組合管理", "icon": "💼"},
            "risk_management": {"title": "⚠️ 風險管理", "icon": "⚠️"},
            "trade_execution": {"title": "💰 交易執行", "icon": "💰"},
            "ai_model_management": {"title": "🤖 AI模型管理", "icon": "🤖"},
            "backtest_analysis": {"title": "📈 回測分析", "icon": "📈"},
            "learning_center": {"title": "📚 學習中心", "icon": "📚"},
            "advanced_charts": {"title": "🚀 進階圖表分析", "icon": "🚀"}
        }

        # 根據用戶角色過濾頁面 (完整權限實現)
        try:
            from src.ui.utils.page_renderer import check_page_permission
            # 過濾用戶有權限的頁面
            filtered_pages = {}
            for page_key, page_info in available_pages.items():
                if check_page_permission(page_key, user_role):
                    filtered_pages[page_key] = page_info

            # 確保至少有一些基本頁面可用
            if not filtered_pages:
                logger.warning(f"用戶角色 {user_role} 沒有可用頁面，使用預設頁面")
                filtered_pages = {
                    "system_status_monitoring": available_pages["system_status_monitoring"],
                    "data_management": available_pages["data_management"],
                    "learning_center": available_pages["learning_center"]
                }
            available_pages = filtered_pages

        except (ImportError, Exception) as e:
            logger.warning(f"權限檢查失敗，使用備用權限: {e}")
            # 備用權限檢查 (更新為12個功能分類)
            if user_role == "demo":
                available_pages = {k: v for k, v in available_pages.items()
                                 if k in ["learning_center", "data_management", "backtest_analysis"]}
            elif user_role == "trader":
                available_pages = {k: v for k, v in available_pages.items()
                                 if k in ["trade_execution", "strategy_development", "risk_management",
                                         "portfolio_management", "backtest_analysis"]}
            elif user_role == "analyst":
                available_pages = {k: v for k, v in available_pages.items()
                                 if k in ["data_management", "backtest_analysis", "ai_model_management",
                                         "ai_decision_support", "learning_center"]}
            else:
                # 管理員或未知角色，給予所有權限
                pass

        # 檢查是否有可用頁面
        if not available_pages:
            st.error("❌ 沒有可用的功能頁面")
            logger.error(f"用戶角色 {user_role} 沒有可用頁面")
            return "system_status_monitoring"

        # 創建選項列表 (使用單一表情符號格式)
        page_options = [f"{page['icon']} {page['title'][2:]}"  # 移除標題中的表情符號，只保留選項中的
                       for page in available_pages.values()]
        page_keys = list(available_pages.keys())

        logger.info(f"可用頁面數量: {len(available_pages)}, 用戶角色: {user_role}")

        # 獲取當前選中的頁面 (更新預設為新的系統狀態監控)
        current_page = st.session_state.get("current_page", "system_status_monitoring")
        current_index = page_keys.index(current_page) if current_page in page_keys else 0

        # 顯示選擇框
        selected_index = st.selectbox(
            "選擇功能模組",
            range(len(page_options)),
            index=current_index,
            format_func=lambda i: page_options[i],
            key="main_navigation_selector"
        )

        selected_page = page_keys[selected_index]

        # 修復：立即更新 session state 並觸發重新渲染
        if selected_page != current_page:
            st.session_state.current_page = selected_page
            logger.debug("功能切換: %s -> %s", current_page, selected_page)
            # 立即觸發重新渲染，解決雙擊切換問題
            st.rerun()

        return selected_page

    except Exception as e:
        logger.error("顯示主要功能選單時發生錯誤: %s", e, exc_info=True)
        st.error("功能選單載入失敗")
        return "system_status_monitoring"


def show_user_info_and_actions() -> None:
    """顯示用戶資訊和快速操作.

    整合用戶資訊顯示和常用快速操作按鈕。
    """
    try:
        # 用戶資訊
        username = st.session_state.get("username", "訪客")
        user_role = st.session_state.get("user_role", "user")

        st.markdown("### 👤 用戶資訊")
        st.markdown(f"**用戶**: {username}")
        st.markdown(f"**角色**: {user_role}")

        # 快速操作按鈕
        st.markdown("**⚡ 快速操作**")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔄 刷新", key="quick_refresh", help="刷新當前頁面"):
                st.rerun()

        with col2:
            if st.button("🚪 登出", key="quick_logout", help="登出系統"):
                # 清除認證狀態
                st.session_state.authenticated = False
                st.session_state.username = ""
                st.session_state.user_role = ""
                st.rerun()

    except Exception as e:
        logger.error("顯示用戶資訊和操作時發生錯誤: %s", e, exc_info=True)
        st.error("用戶資訊載入失敗")


def show_status_bar() -> None:
    """顯示底部狀態欄.

    顯示系統運行狀態、最後更新時間等信息。
    """
    try:
        st.markdown("---")

        # 創建狀態欄
        col1, col2, col3 = st.columns([2, 2, 2])

        with col1:
            st.caption(f"🕒 最後更新: {st.session_state.get('last_update', '未知')}")

        with col2:
            connection_status = st.session_state.get("connection_status", "connected")
            status_text = "🔗 已連接" if connection_status == "connected" else "⚠️ 連接異常"
            st.caption(status_text)

        with col3:
            st.caption(f"📊 性能模式: {st.session_state.get('performance_mode', 'optimized')}")

    except Exception as e:
        logger.error("顯示狀態欄時發生錯誤: %s", e, exc_info=True)


# 向後相容性：保留原有的 show_sidebar 函數但重定向到新實現
def show_sidebar() -> str:
    """向後相容性函數 - 重定向到新的主介面實現.

    注意: 此函數已被 show_main_interface() 取代，
    保留此函數僅為向後相容性。

    Returns:
        str: 選中的頁面名稱
    """
    logger.warning("show_sidebar() 已被棄用，請使用 show_main_interface()")
    return show_main_interface()


# 如果直接運行此檔案，啟動應用程式
if __name__ == "__main__":
    try:
        # 初始化 session state
        initialize_session_state()
        
        # 檢查系統需求
        if check_system_requirements():
            # 運行主應用程式
            run_web_ui()
        
    except Exception as e:
        logger.error("應用程式啟動失敗: %s", e, exc_info=True)
        st.error("❌ 系統啟動失敗，請重新整理頁面或聯繫系統管理員")


# 向後相容性
__all__ = ['main', 'run_web_ui', 'get_app_info']
