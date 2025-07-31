"""
Web UI 頁面渲染器模組

此模組提供 Web UI 的頁面渲染功能，包括：
- 動態頁面載入
- 模組導入管理
- 錯誤處理和回退

主要功能：
- 動態載入頁面模組
- 處理模組導入錯誤
- 提供頁面渲染介面
- 管理頁面狀態和快取

Example:
    >>> from src.ui.utils.page_renderer import render_page
    >>> render_page("dashboard", "admin")
"""

import logging
import importlib
from typing import Optional, Dict, Any

import streamlit as st

try:
    from src.ui.layouts.page_layout import show_error_page, show_coming_soon_page
    from src.ui.components.navigation import get_page_module_name, check_page_permission
except ImportError:
    # 備用導入方案
    try:
        from ui.layouts.page_layout import show_error_page, show_coming_soon_page
        from ui.components.navigation import get_page_module_name, check_page_permission
    except ImportError:
        # 如果都失敗，提供簡化的替代函數
        def show_error_page(error_msg: str, details: str = ""):
            st.error(f"錯誤: {error_msg}")
            if details:
                with st.expander("詳細信息"):
                    st.code(details)

        def show_coming_soon_page(page_name: str):
            st.info(f"頁面 '{page_name}' 正在開發中，敬請期待！")

        def get_page_module_name(page_key: str) -> str:
            return f"src.ui.pages.{page_key}"

        def check_page_permission(page_key: str, user_role: str) -> bool:
            """檢查頁面權限 (備用實現).

            Args:
                page_key: 頁面鍵值
                user_role: 用戶角色

            Returns:
                bool: 是否有權限訪問
            """
            # 定義角色權限映射
            role_permissions = {
                "admin": ["system_monitoring", "data_management", "strategy_management",
                         "risk_management", "trade_execution", "ai_model_management",
                         "backtest_system", "learning_center", "modern_dashboard", "market_monitoring"],
                "trader": ["trade_execution", "strategy_management", "risk_management",
                          "market_monitoring", "backtest_system"],
                "analyst": ["data_management", "backtest_system", "ai_model_management",
                           "market_monitoring", "learning_center"],
                "demo": ["learning_center", "modern_dashboard", "market_monitoring"]
            }
            return page_key in role_permissions.get(user_role, [])

logger = logging.getLogger(__name__)


def check_page_permission(page_key: str, user_role: str) -> bool:
    """檢查頁面權限 (完整實現).

    基於用戶角色檢查是否有權限訪問指定頁面。

    Args:
        page_key: 頁面鍵值
        user_role: 用戶角色

    Returns:
        bool: 是否有權限訪問

    Example:
        >>> has_permission = check_page_permission("system_monitoring", "admin")
        >>> print(has_permission)
        True

        >>> has_permission = check_page_permission("system_monitoring", "demo")
        >>> print(has_permission)
        False
    """
    try:
        # 定義角色權限映射 (更新為12個功能分類)
        role_permissions = {
            "admin": [
                "system_status_monitoring", "security_permission_management", "multi_agent_system_management",
                "data_management", "strategy_development", "ai_decision_support",
                "portfolio_management", "risk_management", "trade_execution",
                "ai_model_management", "backtest_analysis", "learning_center",
                "advanced_technical_analysis"
            ],
            "trader": [
                "trade_execution", "strategy_development", "risk_management",
                "portfolio_management", "backtest_analysis", "advanced_technical_analysis"
            ],
            "analyst": [
                "data_management", "backtest_analysis", "ai_model_management",
                "ai_decision_support", "learning_center", "advanced_technical_analysis"
            ],
            "demo": [
                "learning_center", "data_management", "backtest_analysis"
            ]
        }

        # 檢查權限
        allowed_pages = role_permissions.get(user_role, [])
        has_permission = page_key in allowed_pages

        logger.debug(
            "權限檢查: 用戶角色=%s, 頁面=%s, 權限=%s",
            user_role, page_key, has_permission
        )

        return has_permission

    except Exception as e:
        logger.error("檢查頁面權限時發生錯誤: %s", e, exc_info=True)
        return False


def get_role_permissions(user_role: str) -> list:
    """獲取角色的所有權限.

    Args:
        user_role: 用戶角色

    Returns:
        list: 該角色可訪問的頁面清單

    Example:
        >>> permissions = get_role_permissions("trader")
        >>> print(permissions)
        ['trade_execution', 'strategy_management', 'risk_management', 'market_monitoring', 'backtest_system']
    """
    role_permissions = {
        "admin": [
            "system_status_monitoring", "security_permission_management", "multi_agent_system_management",
            "data_management", "strategy_development", "ai_decision_support",
            "portfolio_management", "risk_management", "trade_execution",
            "ai_model_management", "backtest_analysis", "learning_center"
        ],
        "trader": [
            "trade_execution", "strategy_development", "risk_management",
            "portfolio_management", "backtest_analysis"
        ],
        "analyst": [
            "data_management", "backtest_analysis", "ai_model_management",
            "ai_decision_support", "learning_center"
        ],
        "demo": [
            "learning_center", "data_management", "backtest_analysis"
        ]
    }

    return role_permissions.get(user_role, [])


def _show_permission_denied(page_key: str, user_role: str) -> None:
    """顯示權限拒絕提示.

    當用戶沒有權限訪問頁面時，顯示友善的提示信息。

    Args:
        page_key: 頁面鍵值
        user_role: 用戶角色

    Example:
        >>> _show_permission_denied("system_monitoring", "demo")
    """
    try:
        # 頁面名稱映射 (更新為13個功能分類)
        page_names = {
            "system_status_monitoring": "🖥️ 系統狀態監控",
            "security_permission_management": "🔐 安全與權限管理",
            "multi_agent_system_management": "🤖 多代理系統管理",
            "data_management": "📊 數據管理",
            "strategy_development": "🎯 策略開發",
            "ai_decision_support": "🧠 AI決策支援",
            "portfolio_management": "💼 投資組合管理",
            "risk_management": "⚠️ 風險管理",
            "trade_execution": "💰 交易執行",
            "ai_model_management": "🤖 AI模型管理",
            "backtest_analysis": "📈 回測分析",
            "learning_center": "📚 學習中心",
            "advanced_technical_analysis": "📈 進階技術分析"
        }

        # 角色名稱映射
        role_names = {
            "admin": "管理員",
            "trader": "交易員",
            "analyst": "分析師",
            "demo": "示範用戶"
        }

        page_name = page_names.get(page_key, page_key)
        role_name = role_names.get(user_role, user_role)

        st.error(f"🚫 權限不足")
        st.warning(f"您的角色「{role_name}」無權限訪問「{page_name}」功能")

        # 顯示當前角色可訪問的功能
        allowed_pages = get_role_permissions(user_role)
        if allowed_pages:
            st.info("**您可以訪問以下功能：**")

            allowed_names = [page_names.get(page, page) for page in allowed_pages]
            for name in allowed_names:
                st.markdown(f"- {name}")

        # 提供升級權限的指引
        st.markdown("---")
        st.markdown("### 💡 如何獲得更多權限？")

        if user_role == "demo":
            st.info("""
            **示範用戶權限有限**，如需更多功能請：
            - 聯繫系統管理員申請正式帳戶
            - 或使用其他角色的示範帳戶進行測試
            """)
        else:
            st.info("""
            **需要更多權限？**
            - 聯繫系統管理員 (admin@trading-system.com)
            - 申請角色升級或功能授權
            - 查看用戶手冊了解各角色權限說明
            """)

        # 顯示所有角色權限對比
        with st.expander("📋 查看所有角色權限對比", expanded=False):
            st.markdown("### 角色權限對比表")

            all_roles = ["admin", "trader", "analyst", "demo"]
            all_pages = list(page_names.keys())

            # 創建權限對比表
            permission_data = []
            for page in all_pages:
                row = {"功能": page_names[page]}
                for role in all_roles:
                    has_permission = check_page_permission(page, role)
                    row[role_names[role]] = "✅" if has_permission else "❌"
                permission_data.append(row)

            import pandas as pd
            df = pd.DataFrame(permission_data)
            st.dataframe(df, use_container_width=True)

    except Exception as e:
        logger.error("顯示權限拒絕提示時發生錯誤: %s", e, exc_info=True)
        st.error("❌ 您沒有權限訪問此頁面")


def render_page(page_key: str, user_role: str) -> None:
    """渲染指定頁面.

    Args:
        page_key: 頁面鍵值
        user_role: 用戶角色

    Example:
        >>> render_page("system_monitoring", "admin")
    """
    try:
        # 檢查頁面權限
        if not check_page_permission(page_key, user_role):
            _show_permission_denied(page_key, user_role)
            return

        # 首先嘗試載入組件
        success = _load_and_render_component(page_key)

        if success:
            return

        # 如果組件載入失敗，嘗試載入原有頁面
        module_name = get_page_module_name(page_key)
        if not module_name:
            show_error_page("頁面配置錯誤", f"找不到頁面 '{page_key}' 的模組配置")
            return

        # 載入並渲染頁面
        success = _load_and_render_page(module_name, page_key)

        if not success:
            show_coming_soon_page(page_key)

    except Exception as e:
        logger.error("渲染頁面 %s 時發生錯誤: %s", page_key, e, exc_info=True)
        show_error_page("頁面載入失敗", str(e))


def _load_and_render_component(page_key: str) -> bool:
    """載入並渲染組件.

    Args:
        page_key: 頁面鍵值

    Returns:
        bool: 是否成功載入

    Example:
        >>> success = _load_and_render_component("system_monitoring")
        >>> print(success)
        True
    """
    try:
        # 定義組件映射 (更新為13個功能分類，新增進階圖表)
        component_mapping = {
            "system_status_monitoring": "src.ui.components.system_status_monitoring",
            "security_permission_management": "src.ui.components.security_permission_management",
            "multi_agent_system_management": "src.ui.components.multi_agent_system_management",
            "data_management": "src.ui.components.data_management_ui",
            "strategy_development": "src.ui.components.strategy_development",
            "ai_decision_support": "src.ui.components.ai_decision_support",
            "portfolio_management": "src.ui.components.portfolio_management",
            "risk_management": "src.ui.components.risk_management",
            "trade_execution": "src.ui.components.trade_execution",
            "ai_model_management": "src.ui.components.ai_model_management",
            "backtest_analysis": "src.ui.components.backtest_analysis",
            "learning_center": "src.ui.components.learning_center",
            "advanced_charts": "src.ui.pages.advanced_charts"
        }

        # 檢查是否有對應的組件
        if page_key not in component_mapping:
            return False

        component_module_name = component_mapping[page_key]

        # 嘗試導入組件模組
        component_module = _import_page_module(component_module_name)

        if not component_module:
            logger.warning("無法導入組件模組: %s", component_module_name)
            return False

        # 檢查組件是否有 show 函數
        if hasattr(component_module, 'show'):
            logger.debug("渲染組件: %s", component_module_name)
            component_module.show()
            return True
        else:
            logger.warning("組件模組 %s 缺少 show() 函數", component_module_name)
            return False

    except Exception as e:
        logger.error("載入組件 %s 時發生錯誤: %s", page_key, e, exc_info=True)
        return False


def _load_and_render_page(module_name: str, page_key: str) -> bool:
    """載入並渲染頁面模組.

    Args:
        module_name: 模組名稱
        page_key: 頁面鍵值

    Returns:
        bool: 是否成功載入

    Example:
        >>> success = _load_and_render_page("dashboard", "dashboard")
        >>> print(success)
        True
    """
    try:
        # 嘗試從不同路徑導入模組
        page_module = _import_page_module(module_name)
        
        if not page_module:
            logger.warning("無法導入頁面模組: %s", module_name)
            return False

        # 檢查模組是否有 show 函數
        if hasattr(page_module, 'show'):
            logger.debug("渲染頁面: %s", module_name)
            page_module.show()
            return True
        elif hasattr(page_module, 'main'):
            logger.debug("渲染頁面 (main): %s", module_name)
            page_module.main()
            return True
        else:
            logger.warning("頁面模組 %s 缺少 show() 或 main() 函數", module_name)
            return False

    except Exception as e:
        logger.error("載入頁面模組 %s 時發生錯誤: %s", module_name, e, exc_info=True)
        return False


def _import_page_module(module_name: str):
    """導入頁面模組.

    Args:
        module_name: 模組名稱

    Returns:
        模組物件或 None

    Example:
        >>> module = _import_page_module("dashboard")
        >>> print(module is not None)
        True
    """
    # 嘗試的導入路徑列表
    import_paths = [
        f"src.ui.pages.{module_name}",
        f"ui.pages.{module_name}",
        f"pages.{module_name}",
        module_name
    ]

    for import_path in import_paths:
        try:
            logger.debug("嘗試導入: %s", import_path)
            module = importlib.import_module(import_path)
            logger.debug("成功導入: %s", import_path)
            return module
        except ImportError as e:
            logger.debug("導入失敗 %s: %s", import_path, e)
            continue
        except Exception as e:
            logger.error("導入 %s 時發生意外錯誤: %s", import_path, e)
            continue

    return None


def show_default_dashboard() -> None:
    """顯示預設儀表板.

    Example:
        >>> show_default_dashboard()
    """
    try:
        st.markdown("# 📊 系統儀表板")
        st.markdown("歡迎使用 AI 股票自動交易系統！")
        st.markdown("---")

        # 系統狀態概覽
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("系統狀態", "正常", "✅")
        
        with col2:
            st.metric("活躍策略", "3", "+1")
        
        with col3:
            st.metric("今日收益", "2.5%", "+0.8%")
        
        with col4:
            st.metric("風險等級", "中等", "⚠️")

        st.markdown("---")

        # 快速操作
        st.markdown("## 🚀 快速操作")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📈 查看數據", use_container_width=True):
                st.info("請從左側選單選擇 '數據管理' 功能")
        
        with col2:
            if st.button("🎯 策略管理", use_container_width=True):
                st.info("請從左側選單選擇 '策略管理' 功能")
        
        with col3:
            if st.button("📉 回測分析", use_container_width=True):
                st.info("請從左側選單選擇 '回測分析' 功能")

        # 系統資訊
        st.markdown("---")
        st.markdown("## ℹ️ 系統資訊")
        
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.markdown("""
            **系統版本**: v2.0  
            **最後更新**: 2024-01-13  
            **運行時間**: 24小時  
            **數據來源**: 即時市場數據  
            """)
        
        with info_col2:
            st.markdown("""
            **支援市場**: 台股、美股  
            **交易模式**: 模擬、實盤  
            **風險控制**: 啟用  
            **監控狀態**: 正常  
            """)

        # 最近活動
        st.markdown("---")
        st.markdown("## 📋 最近活動")
        
        activities = [
            {"time": "10:30", "action": "策略執行", "status": "成功", "details": "動量策略買入 AAPL"},
            {"time": "10:15", "action": "數據更新", "status": "成功", "details": "更新市場數據"},
            {"time": "09:45", "action": "風險檢查", "status": "正常", "details": "投資組合風險在可控範圍"},
            {"time": "09:30", "action": "系統啟動", "status": "成功", "details": "交易系統正常啟動"}
        ]

        for activity in activities:
            status_icon = "✅" if activity["status"] == "成功" else "⚠️" if activity["status"] == "正常" else "❌"
            st.markdown(f"**{activity['time']}** {status_icon} {activity['action']} - {activity['details']}")

    except Exception as e:
        logger.error("顯示預設儀表板時發生錯誤: %s", e, exc_info=True)
        show_error_page("儀表板載入失敗", str(e))


def get_page_cache_key(page_key: str, user_role: str) -> str:
    """獲取頁面快取鍵值.

    Args:
        page_key: 頁面鍵值
        user_role: 用戶角色

    Returns:
        str: 快取鍵值

    Example:
        >>> cache_key = get_page_cache_key("dashboard", "admin")
        >>> print(cache_key)
        'page_dashboard_admin'
    """
    return f"page_{page_key}_{user_role}"


def clear_page_cache(page_key: Optional[str] = None) -> None:
    """清除頁面快取.

    Args:
        page_key: 頁面鍵值，如果為 None 則清除所有頁面快取

    Example:
        >>> clear_page_cache("dashboard")  # 清除特定頁面快取
        >>> clear_page_cache()  # 清除所有頁面快取
    """
    try:
        if page_key:
            # 清除特定頁面的快取
            cache_keys = [key for key in st.session_state.keys() 
                         if key.startswith(f"page_{page_key}_")]
        else:
            # 清除所有頁面快取
            cache_keys = [key for key in st.session_state.keys() 
                         if key.startswith("page_")]

        for key in cache_keys:
            del st.session_state[key]

        logger.debug("已清除 %d 個頁面快取", len(cache_keys))

    except Exception as e:
        logger.error("清除頁面快取時發生錯誤: %s", e, exc_info=True)


def preload_common_modules() -> None:
    """預載入常用模組.

    Example:
        >>> preload_common_modules()
    """
    try:
        common_modules = [
            "realtime_dashboard",
            "backtest",
            "strategy_management",
            "portfolio_management"
        ]

        for module_name in common_modules:
            try:
                _import_page_module(module_name)
                logger.debug("預載入模組成功: %s", module_name)
            except Exception as e:
                logger.debug("預載入模組失敗 %s: %s", module_name, e)

    except Exception as e:
        logger.error("預載入常用模組時發生錯誤: %s", e, exc_info=True)


def validate_page_module(module_name: str) -> bool:
    """驗證頁面模組是否有效.

    Args:
        module_name: 模組名稱

    Returns:
        bool: 是否有效

    Example:
        >>> is_valid = validate_page_module("dashboard")
        >>> print(is_valid)
        True
    """
    try:
        module = _import_page_module(module_name)
        
        if not module:
            return False

        # 檢查是否有必要的函數
        return hasattr(module, 'show') or hasattr(module, 'main')

    except Exception as e:
        logger.error("驗證頁面模組 %s 時發生錯誤: %s", module_name, e, exc_info=True)
        return False
