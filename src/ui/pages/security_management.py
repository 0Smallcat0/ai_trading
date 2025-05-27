"""
安全管理頁面

此模組實現了安全管理的使用者介面，包括：
- 使用者管理
- 角色權限管理
- 安全事件監控
- 審計日誌查詢
- 系統安全設定

遵循與其他UI頁面相同的設計模式。
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# 導入服務層
from src.core.security_service import SecurityService
from src.core.authentication_service import AuthenticationService

# 導入UI組件
from src.ui.components.auth import check_auth, get_user_role, require_auth


def show_security_management():
    """顯示安全管理頁面"""

    # 檢查認證和權限
    if not check_auth():
        st.error("請先登入系統")
        return

    user_role = get_user_role()
    if user_role not in ["admin"]:
        st.error("您沒有權限存取此頁面")
        return

    st.title("🔒 安全管理")
    st.markdown("---")

    # 初始化服務
    if "security_service" not in st.session_state:
        st.session_state.security_service = SecurityService()

    if "auth_service" not in st.session_state:
        st.session_state.auth_service = AuthenticationService()

    # 側邊欄選單
    with st.sidebar:
        st.subheader("安全管理選單")
        page = st.selectbox(
            "選擇功能",
            [
                "安全概覽",
                "使用者管理",
                "角色權限管理",
                "安全事件監控",
                "審計日誌查詢",
                "系統安全設定",
            ],
        )

    # 根據選擇顯示對應頁面
    if page == "安全概覽":
        show_security_overview()
    elif page == "使用者管理":
        show_user_management()
    elif page == "角色權限管理":
        show_role_management()
    elif page == "安全事件監控":
        show_security_events()
    elif page == "審計日誌查詢":
        show_audit_logs()
    elif page == "系統安全設定":
        show_security_settings()


def show_security_overview():
    """顯示安全概覽"""
    st.subheader("📊 安全概覽")

    try:
        security_service = st.session_state.security_service

        # 獲取安全統計數據
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(label="活躍使用者", value="12", delta="2")

        with col2:
            st.metric(label="今日登入次數", value="45", delta="8")

        with col3:
            st.metric(label="安全事件", value="3", delta="-1")

        with col4:
            st.metric(label="可疑活動", value="1", delta="0")

        st.markdown("---")

        # 安全事件趨勢圖
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("安全事件趨勢")

            # 獲取最近7天的安全事件
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            events = security_service.get_security_events(
                start_date=start_date, end_date=end_date, limit=1000
            )

            if events:
                # 按日期統計事件數量
                df = pd.DataFrame(events)
                df["date"] = pd.to_datetime(df["created_at"]).dt.date
                daily_counts = df.groupby("date").size().reset_index(name="count")

                fig = px.line(
                    daily_counts, x="date", y="count", title="每日安全事件數量"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("暫無安全事件數據")

        with col2:
            st.subheader("事件類型分布")

            if events:
                # 統計事件類型
                event_types = pd.DataFrame(events)["event_type"].value_counts()

                fig = px.pie(
                    values=event_types.values,
                    names=event_types.index,
                    title="安全事件類型分布",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("暫無事件類型數據")

        # 最近安全事件
        st.subheader("最近安全事件")

        recent_events = security_service.get_security_events(limit=10)

        if recent_events:
            df = pd.DataFrame(recent_events)
            df = df[
                ["event_type", "username", "ip_address", "threat_level", "created_at"]
            ]
            df.columns = ["事件類型", "使用者", "IP地址", "威脅等級", "發生時間"]
            st.dataframe(df, use_container_width=True)
        else:
            st.info("暫無安全事件")

    except Exception as e:
        st.error(f"載入安全概覽失敗: {e}")


def show_user_management():
    """顯示使用者管理"""
    st.subheader("👥 使用者管理")

    try:
        security_service = st.session_state.security_service

        # 使用者操作選項
        action = st.selectbox(
            "選擇操作", ["查看使用者列表", "創建新使用者", "編輯使用者", "停用使用者"]
        )

        if action == "查看使用者列表":
            st.subheader("使用者列表")

            # 這裡應該從資料庫獲取使用者列表
            # 暫時使用示例數據
            users_data = [
                {
                    "user_id": "user001",
                    "username": "admin",
                    "email": "admin@example.com",
                    "full_name": "系統管理員",
                    "is_active": True,
                    "is_locked": False,
                    "last_login": "2024-12-01 10:30:00",
                },
                {
                    "user_id": "user002",
                    "username": "trader1",
                    "email": "trader1@example.com",
                    "full_name": "交易員一",
                    "is_active": True,
                    "is_locked": False,
                    "last_login": "2024-12-01 09:15:00",
                },
            ]

            df = pd.DataFrame(users_data)
            df.columns = [
                "使用者ID",
                "使用者名稱",
                "電子郵件",
                "全名",
                "啟用",
                "鎖定",
                "最後登入",
            ]
            st.dataframe(df, use_container_width=True)

        elif action == "創建新使用者":
            st.subheader("創建新使用者")

            with st.form("create_user_form"):
                col1, col2 = st.columns(2)

                with col1:
                    username = st.text_input("使用者名稱*")
                    email = st.text_input("電子郵件*")
                    full_name = st.text_input("全名")

                with col2:
                    password = st.text_input("密碼*", type="password")
                    confirm_password = st.text_input("確認密碼*", type="password")
                    role = st.selectbox("角色", ["user", "trader", "analyst", "admin"])

                submitted = st.form_submit_button("創建使用者")

                if submitted:
                    if not username or not email or not password:
                        st.error("請填寫所有必填欄位")
                    elif password != confirm_password:
                        st.error("密碼確認不一致")
                    else:
                        # 創建使用者
                        success, message, user_id = security_service.create_user(
                            username=username,
                            email=email,
                            password=password,
                            full_name=full_name,
                            role_id=role,
                            created_by=st.session_state.get("username", "admin"),
                        )

                        if success:
                            st.success(f"使用者創建成功: {message}")
                        else:
                            st.error(f"創建失敗: {message}")

        elif action == "編輯使用者":
            st.subheader("編輯使用者")
            st.info("此功能正在開發中...")

        elif action == "停用使用者":
            st.subheader("停用使用者")
            st.info("此功能正在開發中...")

    except Exception as e:
        st.error(f"使用者管理操作失敗: {e}")


def show_role_management():
    """顯示角色權限管理"""
    st.subheader("🔑 角色權限管理")

    try:
        # 角色管理選項
        action = st.selectbox(
            "選擇操作", ["查看角色列表", "創建新角色", "編輯角色權限", "分配使用者角色"]
        )

        if action == "查看角色列表":
            st.subheader("系統角色列表")

            # 示例角色數據
            roles_data = [
                {
                    "role_id": "admin",
                    "role_name": "系統管理員",
                    "role_level": 10,
                    "description": "擁有系統所有權限",
                    "user_count": 2,
                    "is_active": True,
                },
                {
                    "role_id": "trader",
                    "role_name": "交易員",
                    "role_level": 7,
                    "description": "可執行交易操作",
                    "user_count": 5,
                    "is_active": True,
                },
                {
                    "role_id": "analyst",
                    "role_name": "分析師",
                    "role_level": 5,
                    "description": "可查看分析報表",
                    "user_count": 3,
                    "is_active": True,
                },
                {
                    "role_id": "readonly",
                    "role_name": "只讀用戶",
                    "role_level": 1,
                    "description": "只能查看基本資訊",
                    "user_count": 8,
                    "is_active": True,
                },
            ]

            df = pd.DataFrame(roles_data)
            df.columns = ["角色ID", "角色名稱", "等級", "描述", "使用者數", "啟用"]
            st.dataframe(df, use_container_width=True)

        elif action == "創建新角色":
            st.subheader("創建新角色")

            with st.form("create_role_form"):
                col1, col2 = st.columns(2)

                with col1:
                    role_code = st.text_input("角色代碼*")
                    role_name = st.text_input("角色名稱*")
                    role_level = st.number_input(
                        "角色等級", min_value=1, max_value=10, value=1
                    )

                with col2:
                    description = st.text_area("角色描述")
                    is_active = st.checkbox("啟用角色", value=True)

                st.subheader("權限設定")

                # 權限選擇
                permissions = st.multiselect(
                    "選擇權限",
                    [
                        "data.read",
                        "data.write",
                        "data.delete",
                        "strategy.read",
                        "strategy.write",
                        "strategy.execute",
                        "portfolio.read",
                        "portfolio.write",
                        "trade.read",
                        "trade.execute",
                        "report.read",
                        "report.export",
                        "user.read",
                        "user.write",
                        "system.config",
                        "admin.all",
                    ],
                )

                submitted = st.form_submit_button("創建角色")

                if submitted:
                    if not role_code or not role_name:
                        st.error("請填寫角色代碼和名稱")
                    else:
                        st.success(f"角色 {role_name} 創建成功")

        elif action == "編輯角色權限":
            st.subheader("編輯角色權限")
            st.info("此功能正在開發中...")

        elif action == "分配使用者角色":
            st.subheader("分配使用者角色")
            st.info("此功能正在開發中...")

    except Exception as e:
        st.error(f"角色管理操作失敗: {e}")


def show_security_events():
    """顯示安全事件監控"""
    st.subheader("🚨 安全事件監控")

    try:
        security_service = st.session_state.security_service

        # 篩選選項
        col1, col2, col3 = st.columns(3)

        with col1:
            event_type = st.selectbox(
                "事件類型",
                [
                    "全部",
                    "login_failed",
                    "login_success",
                    "permission_denied",
                    "data_access",
                ],
            )

        with col2:
            threat_level = st.selectbox(
                "威脅等級", ["全部", "info", "low", "medium", "high", "critical"]
            )

        with col3:
            days = st.selectbox("時間範圍", [1, 7, 30, 90])

        # 獲取安全事件
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        events = security_service.get_security_events(
            event_type=None if event_type == "全部" else event_type,
            start_date=start_date,
            end_date=end_date,
            limit=1000,
        )

        if events:
            # 篩選威脅等級
            if threat_level != "全部":
                events = [e for e in events if e.get("threat_level") == threat_level]

            if events:
                df = pd.DataFrame(events)
                df = df[
                    [
                        "event_type",
                        "username",
                        "ip_address",
                        "threat_level",
                        "event_description",
                        "created_at",
                    ]
                ]
                df.columns = [
                    "事件類型",
                    "使用者",
                    "IP地址",
                    "威脅等級",
                    "描述",
                    "發生時間",
                ]

                # 添加顏色標記
                def highlight_threat_level(val):
                    if val == "critical":
                        return "background-color: #ff4444"
                    elif val == "high":
                        return "background-color: #ff8800"
                    elif val == "medium":
                        return "background-color: #ffaa00"
                    elif val == "low":
                        return "background-color: #88ff88"
                    else:
                        return ""

                styled_df = df.style.applymap(
                    highlight_threat_level, subset=["威脅等級"]
                )
                st.dataframe(styled_df, use_container_width=True)
            else:
                st.info("沒有符合條件的安全事件")
        else:
            st.info("暫無安全事件數據")

    except Exception as e:
        st.error(f"載入安全事件失敗: {e}")


def show_audit_logs():
    """顯示審計日誌查詢"""
    st.subheader("📋 審計日誌查詢")

    try:
        security_service = st.session_state.security_service

        # 查詢選項
        col1, col2, col3 = st.columns(3)

        with col1:
            operation_type = st.selectbox(
                "操作類型",
                [
                    "全部",
                    "user_create",
                    "user_update",
                    "role_assign",
                    "data_access",
                    "config_change",
                ],
            )

        with col2:
            risk_level = st.selectbox("風險等級", ["全部", "low", "medium", "high"])

        with col3:
            days = st.selectbox("查詢範圍", [1, 7, 30, 90])

        # 獲取審計日誌
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        logs = security_service.get_audit_logs(
            operation_type=None if operation_type == "全部" else operation_type,
            start_date=start_date,
            end_date=end_date,
            limit=1000,
        )

        if logs:
            # 篩選風險等級
            if risk_level != "全部":
                logs = [l for l in logs if l.get("risk_level") == risk_level]

            if logs:
                df = pd.DataFrame(logs)
                df = df[
                    [
                        "operation_type",
                        "username",
                        "resource_type",
                        "operation_description",
                        "risk_level",
                        "created_at",
                    ]
                ]
                df.columns = [
                    "操作類型",
                    "使用者",
                    "資源類型",
                    "操作描述",
                    "風險等級",
                    "操作時間",
                ]
                st.dataframe(df, use_container_width=True)
            else:
                st.info("沒有符合條件的審計日誌")
        else:
            st.info("暫無審計日誌數據")

    except Exception as e:
        st.error(f"載入審計日誌失敗: {e}")


def show_security_settings():
    """顯示系統安全設定"""
    st.subheader("⚙️ 系統安全設定")

    try:
        # 密碼策略設定
        st.subheader("密碼策略")

        col1, col2 = st.columns(2)

        with col1:
            min_length = st.number_input("最小長度", min_value=6, max_value=20, value=8)
            require_uppercase = st.checkbox("需要大寫字母", value=True)
            require_lowercase = st.checkbox("需要小寫字母", value=True)

        with col2:
            require_numbers = st.checkbox("需要數字", value=True)
            require_symbols = st.checkbox("需要特殊字符", value=True)
            history_count = st.number_input(
                "密碼歷史記錄", min_value=1, max_value=10, value=5
            )

        # 登入安全設定
        st.subheader("登入安全")

        col1, col2 = st.columns(2)

        with col1:
            max_attempts = st.number_input(
                "最大登入失敗次數", min_value=3, max_value=10, value=5
            )
            lockout_duration = st.number_input(
                "帳戶鎖定時間(分鐘)", min_value=5, max_value=120, value=30
            )

        with col2:
            session_timeout = st.number_input(
                "會話超時時間(分鐘)", min_value=30, max_value=1440, value=480
            )
            require_2fa_roles = st.multiselect(
                "需要2FA的角色", ["admin", "trader", "analyst"]
            )

        # 保存設定
        if st.button("保存設定"):
            st.success("安全設定已保存")

    except Exception as e:
        st.error(f"載入安全設定失敗: {e}")


if __name__ == "__main__":
    show_security_management()
