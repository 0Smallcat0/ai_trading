"""
Web UI 增強版主程式 - Phase 5.1

此模組實現了基於 Streamlit 的增強版 Web 用戶介面，整合新的布局系統、主題配置和響應式設計。
提供完整的交易系統管理功能，包含權限控制、效能優化和用戶體驗提升。
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import time
import os
import sys
from typing import Dict, Any, Optional, Tuple

# 添加專案根目錄到 Python 路徑
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 導入新的布局和組件系統
from src.ui.components.layout import (
    PageLayout,
    DashboardLayout,
    DEFAULT_NAVIGATION,
    Theme,
)
from src.ui.components.common import UIComponents, apply_custom_css

# 導入響應式設計系統
from src.ui.responsive import ResponsiveUtils, responsive_manager, ResponsiveComponents

# 導入效能優化和快取管理
from src.ui.utils import (
    cache_manager,
    performance_optimizer,
    optimize_page_load,
    optimize_query,
    optimize_render,
    enable_performance_optimizations,
    create_performance_dashboard,
    get_cache_dashboard_data,
)

# 導入頁面模組
try:
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
    )
    from src.ui.components import auth
except ImportError:
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
    )
    from src.ui.components import auth


class AITradingSystemUI:
    """AI 交易系統 Web UI 主類"""

    def __init__(self):
        """初始化 UI 系統"""
        self.layout = PageLayout(title="AI 交易系統", icon="🤖", wide_mode=True)

        # 啟用效能優化
        enable_performance_optimizations()

        # 初始化會話狀態
        self._init_session_state()

        # 頁面配置
        self.pages = {
            "overview": {
                "name": "系統總覽",
                "icon": "🏠",
                "function": self.show_overview,
                "min_role": "readonly",
                "description": "系統狀態和關鍵指標總覽",
            },
            "data_management": {
                "name": "資料管理",
                "icon": "📊",
                "function": data_management.show,
                "min_role": "user",
                "description": "資料來源管理和資料更新",
            },
            "feature_engineering": {
                "name": "特徵工程",
                "icon": "⚙️",
                "function": feature_engineering.show,
                "min_role": "user",
                "description": "特徵計算和特徵選擇",
            },
            "strategy_management": {
                "name": "策略管理",
                "icon": "🎯",
                "function": strategy_management.show,
                "min_role": "user",
                "description": "交易策略配置和管理",
            },
            "ai_models": {
                "name": "AI 模型",
                "icon": "🤖",
                "function": ai_models.show,
                "min_role": "user",
                "description": "AI 模型訓練和管理",
            },
            "backtest": {
                "name": "回測系統",
                "icon": "📈",
                "function": backtest.show,
                "min_role": "user",
                "description": "策略回測和效能分析",
            },
            "portfolio_management": {
                "name": "投資組合",
                "icon": "💼",
                "function": portfolio_management.show,
                "min_role": "user",
                "description": "投資組合監控和管理",
            },
            "risk_management": {
                "name": "風險管理",
                "icon": "🛡️",
                "function": risk_management.show,
                "min_role": "user",
                "description": "風險控制和監控",
            },
            "trade_execution": {
                "name": "交易執行",
                "icon": "⚡",
                "function": trade_execution.show,
                "min_role": "user",
                "description": "訂單執行和監控",
            },
            "system_monitoring": {
                "name": "系統監控",
                "icon": "📡",
                "function": system_monitoring.show,
                "min_role": "readonly",
                "description": "系統狀態和效能監控",
            },
            "reports": {
                "name": "報表分析",
                "icon": "📋",
                "function": reports.show,
                "min_role": "readonly",
                "description": "報表查詢和視覺化分析",
            },
            "security_management": {
                "name": "安全管理",
                "icon": "🔒",
                "function": security_management.show_security_management,
                "min_role": "admin",
                "description": "用戶權限和安全設定",
            },
        }

        # 用戶角色配置
        self.user_roles = {
            "admin": {"name": "管理員", "level": 3},
            "user": {"name": "一般用戶", "level": 2},
            "readonly": {"name": "只讀用戶", "level": 1},
        }

    def _init_session_state(self):
        """初始化會話狀態"""
        if "authenticated" not in st.session_state:
            st.session_state.authenticated = False
            st.session_state.user_role = None
            st.session_state.username = None
            st.session_state.current_page = "overview"
            st.session_state.theme = "light"
            st.session_state.user_preferences = {}

    def check_authentication(self) -> Tuple[bool, str]:
        """
        檢查用戶認證狀態

        Returns:
            Tuple[bool, str]: (是否已認證, 用戶角色)
        """
        return st.session_state.authenticated, st.session_state.user_role

    def check_permission(self, page_id: str, user_role: str) -> bool:
        """
        檢查用戶權限

        Args:
            page_id: 頁面 ID
            user_role: 用戶角色

        Returns:
            bool: 是否有權限
        """
        if page_id not in self.pages:
            return False

        min_role = self.pages[page_id]["min_role"]
        min_level = self.user_roles.get(min_role, {}).get("level", 0)
        user_level = self.user_roles.get(user_role, {}).get("level", 0)

        return user_level >= min_level

    def show_login(self):
        """顯示登入頁面"""
        st.markdown("# 🤖 AI 交易系統")
        st.markdown("### 請登入以繼續")

        # 使用增強的登入表單
        with st.container():
            col1, col2, col3 = st.columns([1, 2, 1])

            with col2:
                with st.form("login_form"):
                    st.markdown("#### 用戶登入")

                    username = st.text_input("用戶名", placeholder="請輸入用戶名")
                    password = st.text_input(
                        "密碼", type="password", placeholder="請輸入密碼"
                    )

                    col_login, col_demo = st.columns(2)

                    with col_login:
                        login_clicked = st.form_submit_button(
                            "登入", type="primary", use_container_width=True
                        )

                    with col_demo:
                        demo_clicked = st.form_submit_button(
                            "演示模式", use_container_width=True
                        )

                    if login_clicked:
                        # 簡化的認證邏輯（實際應用中應該連接真實的認證系統）
                        if username and password:
                            # 從環境變數讀取認證資訊，提供開發環境預設值
                            import os

                            admin_user = os.getenv("ADMIN_USERNAME", "admin")
                            admin_pass = os.getenv(
                                "ADMIN_PASSWORD", "admin123"
                            )  # 更安全的預設密碼
                            user_user = os.getenv("USER_USERNAME", "user")
                            user_pass = os.getenv(
                                "USER_PASSWORD", "user123"
                            )  # 更安全的預設密碼

                            # 檢查生產環境是否使用了不安全的預設密碼
                            if os.getenv("ENVIRONMENT") == "production":
                                if admin_pass == "admin123" or user_pass == "user123":
                                    st.error(
                                        "⚠️ 生產環境檢測到不安全的預設密碼，請設定環境變數"
                                    )
                                    return

                            if username == admin_user and password == admin_pass:
                                st.session_state.authenticated = True
                                st.session_state.user_role = "admin"
                                st.session_state.username = username
                                st.success("登入成功！")
                                time.sleep(1)
                                st.rerun()
                            elif username == user_user and password == user_pass:
                                st.session_state.authenticated = True
                                st.session_state.user_role = "user"
                                st.session_state.username = username
                                st.success("登入成功！")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("用戶名或密碼錯誤")
                        else:
                            st.error("請輸入用戶名和密碼")

                    if demo_clicked:
                        st.session_state.authenticated = True
                        st.session_state.user_role = "readonly"
                        st.session_state.username = "demo_user"
                        st.success("進入演示模式！")
                        time.sleep(1)
                        st.rerun()

                # 顯示演示帳號資訊
                with st.expander("演示帳號資訊"):
                    import os

                    admin_user = os.getenv("ADMIN_USERNAME", "admin")
                    user_user = os.getenv("USER_USERNAME", "user")

                    st.markdown(
                        f"""
                    **管理員帳號**: {admin_user} / [從環境變數設定]
                    **一般用戶**: {user_user} / [從環境變數設定]
                    **演示模式**: 點擊演示模式按鈕（只讀權限）

                    ⚠️ **安全提醒**: 生產環境請設定 ADMIN_PASSWORD 和 USER_PASSWORD 環境變數
                    """
                    )

    def show_overview(self):
        """顯示系統總覽頁面"""
        # 系統狀態指標
        st.markdown("## 📊 系統狀態總覽")

        # 關鍵指標
        metrics = [
            {
                "title": "系統狀態",
                "value": "正常運行",
                "status": "success",
                "icon": "✅",
                "description": "所有服務正常",
            },
            {
                "title": "活躍策略",
                "value": "12",
                "status": "normal",
                "icon": "🎯",
                "trend": {"direction": "up", "value": 8.5, "period": "本週"},
            },
            {
                "title": "今日交易",
                "value": "156",
                "status": "success",
                "icon": "⚡",
                "trend": {"direction": "up", "value": 12.3, "period": "較昨日"},
            },
            {
                "title": "總收益率",
                "value": "+15.8%",
                "status": "success",
                "icon": "📈",
                "trend": {"direction": "up", "value": 2.1, "period": "本月"},
            },
        ]

        # 使用響應式指標卡片
        ResponsiveComponents.responsive_metric_cards(
            metrics, desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

        # 圖表區域
        st.markdown("## 📈 效能圖表")

        # 使用響應式列佈局
        cols = responsive_manager.create_responsive_columns(
            desktop_cols=2, tablet_cols=1, mobile_cols=1
        )

        with cols[0]:
            # 收益率趨勢圖
            dates = pd.date_range(start="2024-01-01", periods=30, freq="D")
            returns = np.cumsum(np.random.normal(0.001, 0.02, 30))

            chart_height = responsive_manager.get_chart_height(400)
            fig = px.line(
                x=dates,
                y=returns,
                title="累積收益率趨勢",
                labels={"x": "日期", "y": "收益率"},
            )
            fig.update_layout(height=chart_height)
            st.plotly_chart(fig, use_container_width=True)

        with cols[1 % len(cols)]:
            # 策略分佈圓餅圖
            strategies = ["動量策略", "均值回歸", "機器學習", "套利策略"]
            values = [35, 25, 30, 10]

            chart_height = responsive_manager.get_chart_height(400)
            fig = px.pie(values=values, names=strategies, title="策略資產分佈")
            fig.update_layout(height=chart_height)
            st.plotly_chart(fig, use_container_width=True)

        # 最近活動
        st.markdown("## 📋 最近活動")

        recent_activities = [
            {"時間": "10:30", "活動": "策略 A 買入 TSLA", "狀態": "成功"},
            {"時間": "10:25", "活動": "模型重新訓練完成", "狀態": "成功"},
            {"時間": "10:20", "活動": "風險警報：VIX 上升", "狀態": "警告"},
            {"時間": "10:15", "活動": "策略 B 賣出 AAPL", "狀態": "成功"},
        ]

        # 使用響應式表格
        ResponsiveComponents.responsive_dataframe(
            pd.DataFrame(recent_activities), title=None
        )

        # 效能監控區域
        if st.session_state.user_role == "admin":
            st.markdown("## 🚀 系統效能監控")

            # 快取統計
            cache_stats = get_cache_dashboard_data()

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "快取命中率",
                    cache_stats["cache_stats"]["hit_rate"],
                    f"共 {cache_stats['cache_stats']['cache_items']} 項目",
                )

            with col2:
                st.metric(
                    "記憶體使用",
                    cache_stats["cache_stats"]["memory_usage"],
                    "快取記憶體",
                )

            with col3:
                if st.button("清理快取"):
                    cache_manager.clear()
                    st.success("快取已清理")
                    st.rerun()

            # 效能儀表板
            create_performance_dashboard()

    @optimize_page_load
    def run(self):
        """運行 Web UI"""
        # 檢查認證狀態
        authenticated, user_role = self.check_authentication()

        if not authenticated:
            self.show_login()
            return

        # 渲染側邊欄導航
        navigation_config = {
            "pages": [
                {
                    "name": page_info["name"],
                    "key": page_id,
                    "icon": page_info["icon"],
                    "description": page_info["description"],
                }
                for page_id, page_info in self.pages.items()
                if self.check_permission(page_id, user_role)
            ]
        }

        self.layout.render_sidebar(navigation_config)

        # 獲取當前頁面
        current_page = st.session_state.get("current_page", "overview")

        # 檢查頁面權限
        if current_page not in self.pages:
            current_page = "overview"
            st.session_state.current_page = current_page

        if not self.check_permission(current_page, user_role):
            st.error("您沒有權限訪問此頁面")
            return

        # 渲染頁面標題
        page_info = self.pages[current_page]
        self.layout.render_header(
            subtitle=page_info["description"],
            actions=[
                {
                    "label": "🔄 刷新",
                    "key": "refresh",
                    "help": "刷新頁面資料",
                    "callback": lambda: st.rerun(),
                }
            ],
        )

        # 渲染頁面內容
        try:
            page_info["function"]()
        except Exception as e:
            st.error(f"載入頁面時發生錯誤: {e}")
            with st.expander("錯誤詳情"):
                st.code(str(e))


def main():
    """主函數"""
    ui = AITradingSystemUI()
    ui.run()


if __name__ == "__main__":
    main()
