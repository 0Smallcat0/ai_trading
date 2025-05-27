"""
增強版安全管理頁面 - Phase 5.1

此模組實現了完整的權限與安全管理功能，包括用戶管理、角色配置、API 安全、
審計日誌查看等企業級安全功能。
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
from typing import Dict, List, Any, Optional

from src.ui.components.common import UIComponents
from src.ui.components.layout import FormLayout, DashboardLayout


class SecurityManagement:
    """安全管理類"""

    def __init__(self):
        """初始化安全管理"""
        self.init_session_state()

    def init_session_state(self):
        """初始化會話狀態"""
        if "users" not in st.session_state:
            st.session_state.users = self.get_default_users()

        if "roles" not in st.session_state:
            st.session_state.roles = self.get_default_roles()

        if "api_keys" not in st.session_state:
            st.session_state.api_keys = self.get_default_api_keys()

        if "audit_logs" not in st.session_state:
            st.session_state.audit_logs = self.get_default_audit_logs()

    def get_default_users(self) -> List[Dict]:
        """獲取預設用戶列表"""
        return [
            {
                "id": 1,
                "username": "admin",
                "email": "admin@trading.com",
                "role": "admin",
                "status": "active",
                "last_login": "2024-12-20 10:30:00",
                "created_at": "2024-01-01 00:00:00",
                "login_attempts": 0,
            },
            {
                "id": 2,
                "username": "trader1",
                "email": "trader1@trading.com",
                "role": "user",
                "status": "active",
                "last_login": "2024-12-20 09:15:00",
                "created_at": "2024-01-15 00:00:00",
                "login_attempts": 0,
            },
            {
                "id": 3,
                "username": "analyst1",
                "email": "analyst1@trading.com",
                "role": "readonly",
                "status": "active",
                "last_login": "2024-12-19 16:45:00",
                "created_at": "2024-02-01 00:00:00",
                "login_attempts": 0,
            },
            {
                "id": 4,
                "username": "guest",
                "email": "guest@trading.com",
                "role": "readonly",
                "status": "inactive",
                "last_login": "2024-12-15 14:20:00",
                "created_at": "2024-03-01 00:00:00",
                "login_attempts": 3,
            },
        ]

    def get_default_roles(self) -> List[Dict]:
        """獲取預設角色列表"""
        return [
            {
                "name": "admin",
                "display_name": "系統管理員",
                "description": "擁有所有系統權限",
                "permissions": [
                    "user_management",
                    "role_management",
                    "system_config",
                    "data_management",
                    "strategy_management",
                    "trading",
                    "monitoring",
                    "reports",
                    "api_access",
                ],
                "level": 3,
            },
            {
                "name": "user",
                "display_name": "一般用戶",
                "description": "可以進行交易和策略管理",
                "permissions": [
                    "data_management",
                    "strategy_management",
                    "trading",
                    "monitoring",
                    "reports",
                ],
                "level": 2,
            },
            {
                "name": "readonly",
                "display_name": "只讀用戶",
                "description": "只能查看資料和報表",
                "permissions": ["monitoring", "reports"],
                "level": 1,
            },
        ]

    def get_default_api_keys(self) -> List[Dict]:
        """獲取預設 API 金鑰列表"""
        return [
            {
                "id": 1,
                "name": "主要交易 API",
                "key": "ak_live_****1234",
                "type": "trading",
                "status": "active",
                "created_at": "2024-01-01 00:00:00",
                "last_used": "2024-12-20 10:30:00",
                "usage_count": 15420,
                "rate_limit": "1000/min",
            },
            {
                "id": 2,
                "name": "資料獲取 API",
                "key": "ak_data_****5678",
                "type": "data",
                "status": "active",
                "created_at": "2024-01-01 00:00:00",
                "last_used": "2024-12-20 10:25:00",
                "usage_count": 89234,
                "rate_limit": "5000/min",
            },
            {
                "id": 3,
                "name": "測試環境 API",
                "key": "ak_test_****9999",
                "type": "testing",
                "status": "inactive",
                "created_at": "2024-06-01 00:00:00",
                "last_used": "2024-12-15 14:20:00",
                "usage_count": 234,
                "rate_limit": "100/min",
            },
        ]

    def get_default_audit_logs(self) -> List[Dict]:
        """獲取預設審計日誌"""
        return [
            {
                "timestamp": "2024-12-20 10:30:15",
                "user": "admin",
                "action": "LOGIN",
                "resource": "system",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "status": "success",
                "details": "管理員登入成功",
            },
            {
                "timestamp": "2024-12-20 10:25:30",
                "user": "trader1",
                "action": "CREATE_ORDER",
                "resource": "trading",
                "ip_address": "192.168.1.101",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "status": "success",
                "details": "創建買入訂單 AAPL 100股",
            },
            {
                "timestamp": "2024-12-20 10:20:45",
                "user": "analyst1",
                "action": "VIEW_REPORT",
                "resource": "reports",
                "ip_address": "192.168.1.102",
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "status": "success",
                "details": "查看月度績效報告",
            },
            {
                "timestamp": "2024-12-20 10:15:20",
                "user": "guest",
                "action": "LOGIN_FAILED",
                "resource": "system",
                "ip_address": "192.168.1.200",
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "status": "failed",
                "details": "登入失敗：密碼錯誤",
            },
        ]

    def show_user_management(self):
        """顯示用戶管理"""
        st.markdown("### 👥 用戶管理")

        # 用戶統計
        users = st.session_state.users
        active_users = len([u for u in users if u["status"] == "active"])
        inactive_users = len([u for u in users if u["status"] == "inactive"])

        metrics = [
            {
                "title": "總用戶數",
                "value": str(len(users)),
                "status": "normal",
                "icon": "👥",
            },
            {
                "title": "活躍用戶",
                "value": str(active_users),
                "status": "success",
                "icon": "✅",
            },
            {
                "title": "停用用戶",
                "value": str(inactive_users),
                "status": "warning" if inactive_users > 0 else "normal",
                "icon": "⏸️",
            },
            {
                "title": "管理員",
                "value": str(len([u for u in users if u["role"] == "admin"])),
                "status": "info",
                "icon": "🔑",
            },
        ]

        UIComponents.metric_grid(metrics, columns=4)

        # 用戶列表
        st.markdown("#### 用戶列表")

        # 搜尋和篩選
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            search_term = st.text_input("搜尋用戶", placeholder="輸入用戶名或郵箱")

        with col2:
            role_filter = st.selectbox(
                "角色篩選", ["全部", "admin", "user", "readonly"]
            )

        with col3:
            status_filter = st.selectbox("狀態篩選", ["全部", "active", "inactive"])

        # 篩選用戶
        filtered_users = users

        if search_term:
            filtered_users = [
                u
                for u in filtered_users
                if search_term.lower() in u["username"].lower()
                or search_term.lower() in u["email"].lower()
            ]

        if role_filter != "全部":
            filtered_users = [u for u in filtered_users if u["role"] == role_filter]

        if status_filter != "全部":
            filtered_users = [u for u in filtered_users if u["status"] == status_filter]

        # 顯示用戶表格
        if filtered_users:
            df = pd.DataFrame(filtered_users)
            df = df[
                ["username", "email", "role", "status", "last_login", "login_attempts"]
            ]
            df.columns = ["用戶名", "郵箱", "角色", "狀態", "最後登入", "登入嘗試"]

            st.dataframe(df, use_container_width=True)
        else:
            st.info("沒有找到符合條件的用戶")

        # 用戶操作
        st.markdown("#### 用戶操作")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("➕ 新增用戶", type="primary"):
                st.session_state.show_add_user_form = True

        with col2:
            if st.button("📊 用戶統計報告"):
                self.show_user_statistics()

        # 新增用戶表單
        if st.session_state.get("show_add_user_form", False):
            self.show_add_user_form()

    def show_add_user_form(self):
        """顯示新增用戶表單"""
        st.markdown("#### 新增用戶")

        with st.form("add_user_form"):
            col1, col2 = st.columns(2)

            with col1:
                username = st.text_input("用戶名*", help="用戶登入名稱")
                email = st.text_input("郵箱*", help="用戶郵箱地址")
                role = st.selectbox("角色*", ["user", "readonly", "admin"])

            with col2:
                password = st.text_input("密碼*", type="password", help="初始密碼")
                confirm_password = st.text_input("確認密碼*", type="password")
                status = st.selectbox("狀態", ["active", "inactive"])

            col_submit, col_cancel = st.columns(2)

            with col_submit:
                submitted = st.form_submit_button("創建用戶", type="primary")

            with col_cancel:
                cancelled = st.form_submit_button("取消")

            if submitted:
                # 驗證表單
                if not all([username, email, password, confirm_password]):
                    st.error("請填寫所有必填欄位")
                elif password != confirm_password:
                    st.error("密碼確認不一致")
                elif any(u["username"] == username for u in st.session_state.users):
                    st.error("用戶名已存在")
                elif any(u["email"] == email for u in st.session_state.users):
                    st.error("郵箱已存在")
                else:
                    # 創建新用戶
                    new_user = {
                        "id": max([u["id"] for u in st.session_state.users]) + 1,
                        "username": username,
                        "email": email,
                        "role": role,
                        "status": status,
                        "last_login": "從未登入",
                        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "login_attempts": 0,
                    }

                    st.session_state.users.append(new_user)
                    st.success(f"用戶 {username} 創建成功！")
                    st.session_state.show_add_user_form = False
                    st.rerun()

            if cancelled:
                st.session_state.show_add_user_form = False
                st.rerun()

    def show_role_management(self):
        """顯示角色管理"""
        st.markdown("### 🔑 角色管理")

        roles = st.session_state.roles

        # 角色概覽
        st.markdown("#### 角色概覽")

        for role in roles:
            with st.expander(
                f"{role['display_name']} ({role['name']})", expanded=False
            ):
                st.markdown(f"**描述**: {role['description']}")
                st.markdown(f"**權限等級**: {role['level']}")
                st.markdown("**權限列表**:")

                permissions_display = {
                    "user_management": "👥 用戶管理",
                    "role_management": "🔑 角色管理",
                    "system_config": "⚙️ 系統配置",
                    "data_management": "📊 資料管理",
                    "strategy_management": "🎯 策略管理",
                    "trading": "⚡ 交易執行",
                    "monitoring": "📡 系統監控",
                    "reports": "📋 報表查詢",
                    "api_access": "🔌 API 存取",
                }

                for perm in role["permissions"]:
                    st.markdown(f"- {permissions_display.get(perm, perm)}")

    def show_api_security(self):
        """顯示 API 安全管理"""
        st.markdown("### 🔌 API 安全管理")

        api_keys = st.session_state.api_keys

        # API 金鑰統計
        active_keys = len([k for k in api_keys if k["status"] == "active"])
        total_usage = sum([k["usage_count"] for k in api_keys])

        metrics = [
            {
                "title": "API 金鑰總數",
                "value": str(len(api_keys)),
                "status": "normal",
                "icon": "🔑",
            },
            {
                "title": "活躍金鑰",
                "value": str(active_keys),
                "status": "success",
                "icon": "✅",
            },
            {
                "title": "總使用次數",
                "value": f"{total_usage:,}",
                "status": "info",
                "icon": "📊",
            },
            {"title": "今日請求", "value": "2,847", "status": "normal", "icon": "📈"},
        ]

        UIComponents.metric_grid(metrics, columns=4)

        # API 金鑰列表
        st.markdown("#### API 金鑰列表")

        df = pd.DataFrame(api_keys)
        df = df[
            ["name", "key", "type", "status", "rate_limit", "usage_count", "last_used"]
        ]
        df.columns = [
            "名稱",
            "金鑰",
            "類型",
            "狀態",
            "速率限制",
            "使用次數",
            "最後使用",
        ]

        st.dataframe(df, use_container_width=True)

        # API 使用統計圖表
        st.markdown("#### API 使用統計")

        # 模擬 API 使用資料
        dates = pd.date_range(start="2024-12-01", periods=20, freq="D")
        api_usage = {
            "日期": dates,
            "交易 API": np.random.randint(800, 1200, 20),
            "資料 API": np.random.randint(3000, 5000, 20),
            "測試 API": np.random.randint(50, 150, 20),
        }

        df_usage = pd.DataFrame(api_usage)

        fig = px.line(
            df_usage,
            x="日期",
            y=["交易 API", "資料 API", "測試 API"],
            title="API 使用趨勢",
            labels={"value": "請求次數", "variable": "API 類型"},
        )

        st.plotly_chart(fig, use_container_width=True)

    def show_audit_logs(self):
        """顯示審計日誌"""
        st.markdown("### 📋 審計日誌")

        logs = st.session_state.audit_logs

        # 日誌篩選
        col1, col2, col3 = st.columns(3)

        with col1:
            user_filter = st.selectbox(
                "用戶篩選", ["全部"] + list(set([log["user"] for log in logs]))
            )

        with col2:
            action_filter = st.selectbox(
                "操作篩選", ["全部"] + list(set([log["action"] for log in logs]))
            )

        with col3:
            status_filter = st.selectbox("狀態篩選", ["全部", "success", "failed"])

        # 篩選日誌
        filtered_logs = logs

        if user_filter != "全部":
            filtered_logs = [log for log in filtered_logs if log["user"] == user_filter]

        if action_filter != "全部":
            filtered_logs = [
                log for log in filtered_logs if log["action"] == action_filter
            ]

        if status_filter != "全部":
            filtered_logs = [
                log for log in filtered_logs if log["status"] == status_filter
            ]

        # 顯示日誌
        if filtered_logs:
            df = pd.DataFrame(filtered_logs)
            df = df[
                [
                    "timestamp",
                    "user",
                    "action",
                    "resource",
                    "ip_address",
                    "status",
                    "details",
                ]
            ]
            df.columns = ["時間", "用戶", "操作", "資源", "IP 地址", "狀態", "詳情"]

            st.dataframe(df, use_container_width=True)
        else:
            st.info("沒有找到符合條件的日誌")

        # 日誌統計
        st.markdown("#### 日誌統計")

        # 操作類型分佈
        action_counts = {}
        for log in logs:
            action = log["action"]
            action_counts[action] = action_counts.get(action, 0) + 1

        fig = px.pie(
            values=list(action_counts.values()),
            names=list(action_counts.keys()),
            title="操作類型分佈",
        )

        st.plotly_chart(fig, use_container_width=True)

    def show_user_statistics(self):
        """顯示用戶統計"""
        st.markdown("#### 📊 用戶統計報告")

        users = st.session_state.users

        # 角色分佈
        role_counts = {}
        for user in users:
            role = user["role"]
            role_counts[role] = role_counts.get(role, 0) + 1

        col1, col2 = st.columns(2)

        with col1:
            fig = px.pie(
                values=list(role_counts.values()),
                names=list(role_counts.keys()),
                title="用戶角色分佈",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # 狀態分佈
            status_counts = {}
            for user in users:
                status = user["status"]
                status_counts[status] = status_counts.get(status, 0) + 1

            fig = px.bar(
                x=list(status_counts.keys()),
                y=list(status_counts.values()),
                title="用戶狀態分佈",
            )
            st.plotly_chart(fig, use_container_width=True)


def show_security_management():
    """顯示安全管理主頁面"""
    security_mgr = SecurityManagement()

    # 標籤頁
    tab1, tab2, tab3, tab4 = st.tabs(
        ["👥 用戶管理", "🔑 角色管理", "🔌 API 安全", "📋 審計日誌"]
    )

    with tab1:
        security_mgr.show_user_management()

    with tab2:
        security_mgr.show_role_management()

    with tab3:
        security_mgr.show_api_security()

    with tab4:
        security_mgr.show_audit_logs()


if __name__ == "__main__":
    show_security_management()
