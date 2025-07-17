"""
系統監控頁面 (整合版)

此模組整合了基本版和增強版系統監控功能，提供完整的系統監控解決方案：
- 系統狀態監控和性能指標
- 實時數據監控和警報管理
- 增強的監控儀表板 (整合功能)
- 智能警報和通知系統 (整合功能)

Version: v2.0 (整合版)
Author: AI Trading System
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import time
from datetime import datetime, timedelta

# 導入服務層
try:
    from src.core.system_monitoring_service import SystemMonitoringService
    from src.ui.components.charts import line_chart, bar_chart
    from src.ui.components.tables import data_table, filterable_table
except ImportError:
    # 如果無法導入，使用備用方案
    SystemMonitoringService = None
    line_chart = bar_chart = None
    data_table = filterable_table = None


def get_system_monitoring_service():
    """獲取系統監控服務實例"""
    if SystemMonitoringService is None:
        return None

    if "monitoring_service" not in st.session_state:
        try:
            st.session_state.monitoring_service = SystemMonitoringService()
        except Exception as e:
            st.error(f"初始化系統監控服務失敗: {e}")
            return None

    return st.session_state.monitoring_service


def show():
    """顯示系統監控頁面"""
    st.title("🖥️ 系統監控與日誌")

    # 自動刷新控制
    col_refresh1, col_refresh2, col_refresh3 = st.columns([2, 2, 4])

    with col_refresh1:
        auto_refresh = st.checkbox("🔄 自動刷新", value=False, key="system_monitoring_auto_refresh")

    with col_refresh2:
        if auto_refresh:
            refresh_interval = st.selectbox(
                "刷新間隔",
                options=[5, 10, 15, 30, 60],
                index=3,  # 默認30秒
                format_func=lambda x: f"{x}秒",
                key="system_monitoring_refresh_interval"
            )
        else:
            refresh_interval = 30

    with col_refresh3:
        if st.button("🔄 立即刷新", type="primary"):
            st.rerun()

    # 自動刷新邏輯
    if auto_refresh:
        if "last_system_monitoring_refresh" not in st.session_state:
            st.session_state.last_system_monitoring_refresh = time.time()

        current_time = time.time()
        time_since_refresh = current_time - st.session_state.last_system_monitoring_refresh

        if time_since_refresh >= refresh_interval:
            st.session_state.last_system_monitoring_refresh = current_time
            st.rerun()
        else:
            # 顯示倒計時
            remaining_time = refresh_interval - time_since_refresh
            st.info(f"⏱️ 下次自動刷新: {remaining_time:.0f}秒後")

    # 獲取系統監控服務
    monitoring_service = get_system_monitoring_service()

    if not monitoring_service:
        st.error("系統監控服務不可用，請檢查系統配置")
        return

    # 頁面標籤
    tabs = st.tabs(
        [
            "📊 系統狀態",
            "💰 交易績效",
            "📋 系統日誌",
            "🔒 審計記錄",
            "⚠️ 警報管理",
            "📈 報告分析",
        ]
    )

    with tabs[0]:
        show_system_status(monitoring_service)

    with tabs[1]:
        show_trading_performance(monitoring_service)

    with tabs[2]:
        show_system_logs(monitoring_service)

    with tabs[3]:
        show_audit_logs(monitoring_service)

    with tabs[4]:
        show_alert_management(monitoring_service)

    with tabs[5]:
        show_reports_analysis(monitoring_service)


def show_system_status(monitoring_service):
    """顯示系統運行狀態"""
    st.subheader("📊 5.2.9.1 系統運行狀態監控")

    # 監控控制
    col_control1, col_control2, col_control3 = st.columns([1, 1, 2])

    with col_control1:
        if st.button("🚀 啟動監控"):
            success, message = monitoring_service.start_monitoring()
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    with col_control2:
        if st.button("⏹️ 停止監控"):
            success, message = monitoring_service.stop_monitoring()
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    with col_control3:
        if st.button("🔄 收集指標"):
            success, message, metrics = monitoring_service.collect_system_metrics()
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    st.divider()

    # 實時系統指標
    st.subheader("📊 實時系統指標")

    # 獲取實時系統指標
    try:
        import psutil

        # 獲取實時數據
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()

        # 顯示實時指標
        col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)

        with col_metric1:
            cpu_color = "🟢" if cpu_percent < 70 else "🟡" if cpu_percent < 90 else "🔴"
            st.metric(
                f"{cpu_color} CPU 使用率",
                f"{cpu_percent:.1f}%",
                delta=None
            )

        with col_metric2:
            memory_color = "🟢" if memory.percent < 70 else "🟡" if memory.percent < 90 else "🔴"
            st.metric(
                f"{memory_color} 內存使用率",
                f"{memory.percent:.1f}%",
                delta=f"可用: {memory.available / (1024**3):.1f}GB"
            )

        with col_metric3:
            disk_percent = (disk.used / disk.total) * 100
            disk_color = "🟢" if disk_percent < 70 else "🟡" if disk_percent < 90 else "🔴"
            st.metric(
                f"{disk_color} 磁盤使用率",
                f"{disk_percent:.1f}%",
                delta=f"可用: {disk.free / (1024**3):.1f}GB"
            )

        with col_metric4:
            network_mb_sent = network.bytes_sent / (1024**2)
            network_mb_recv = network.bytes_recv / (1024**2)
            st.metric(
                "🌐 網絡流量",
                f"↑{network_mb_sent:.1f}MB",
                delta=f"↓{network_mb_recv:.1f}MB"
            )

        # 顯示更新時間
        st.caption(f"📅 最後更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    except ImportError:
        st.warning("⚠️ psutil 模組不可用，無法顯示實時系統指標")
    except Exception as e:
        st.error(f"❌ 獲取系統指標失敗: {e}")

    st.divider()

    # 系統狀態總覽
    status = monitoring_service.get_system_status()

    if "error" in status:
        st.error(f"獲取系統狀態失敗: {status['error']}")
        return

    # 狀態指標卡片
    col_status1, col_status2, col_status3, col_status4 = st.columns(4)

    with col_status1:
        monitoring_status = "🟢 運行中" if status["monitoring_active"] else "🔴 已停止"
        st.metric("監控狀態", monitoring_status)

    with col_status2:
        health_score = status.get("health_score", 0)
        health_color = (
            "🟢" if health_score >= 80 else "🟡" if health_score >= 60 else "🔴"
        )
        st.metric("健康分數", f"{health_color} {health_score}")

    with col_status3:
        active_alerts = status.get("alerts", {}).get("active_count", 0)
        alert_color = (
            "🟢" if active_alerts == 0 else "🟡" if active_alerts < 5 else "🔴"
        )
        st.metric("活躍警報", f"{alert_color} {active_alerts}")

    with col_status4:
        uptime = status.get("uptime", "未知")
        st.metric("系統運行時間", uptime)

    # 系統資源監控
    st.subheader("系統資源使用情況")

    resources = status.get("system_resources", {})

    col_res1, col_res2, col_res3 = st.columns(3)

    with col_res1:
        cpu_usage = resources.get("cpu_usage", 0)
        st.metric("CPU 使用率", f"{cpu_usage:.1f}%")
        st.progress(cpu_usage / 100)

    with col_res2:
        memory_usage = resources.get("memory_usage", 0)
        st.metric("記憶體使用率", f"{memory_usage:.1f}%")
        st.progress(memory_usage / 100)

    with col_res3:
        disk_usage = resources.get("disk_usage", 0)
        st.metric("磁碟使用率", f"{disk_usage:.1f}%")
        st.progress(disk_usage / 100)

    # API 連線狀態
    st.subheader("API 連線狀態監控")

    api_status = monitoring_service.get_api_connection_status()

    if "error" not in api_status:
        apis = api_status.get("apis", [])
        summary = api_status.get("summary", {})

        # 連線摘要
        col_api1, col_api2, col_api3 = st.columns(3)

        with col_api1:
            st.metric("總 API 數", summary.get("total", 0))

        with col_api2:
            st.metric("已連線", summary.get("connected", 0))

        with col_api3:
            connection_rate = summary.get("connection_rate", 0)
            st.metric("連線率", f"{connection_rate:.1f}%")

        # API 詳細狀態
        if apis:
            df_apis = pd.DataFrame(apis)
            df_apis["狀態"] = df_apis["status"].map(
                {
                    "connected": "🟢 已連線",
                    "disconnected": "🔴 未連線",
                    "error": "⚠️ 錯誤",
                }
            )
            df_apis["延遲"] = df_apis["latency"].apply(
                lambda x: f"{x:.1f} ms" if x is not None else "N/A"
            )

            st.dataframe(
                df_apis[["name", "狀態", "延遲", "last_check"]].rename(
                    columns={"name": "API 名稱", "last_check": "最後檢查"}
                ),
                use_container_width=True,
            )

    # 效能指標
    st.subheader("效能指標監控")

    # 獲取最近的效能數據
    performance_data = monitoring_service.get_performance_metrics(limit=20)

    if performance_data:
        df_perf = pd.DataFrame(performance_data)

        # 響應時間趨勢圖
        if "response_time" in df_perf.columns:
            fig = px.line(
                df_perf,
                x="timestamp",
                y="response_time",
                color="module_name",
                title="響應時間趨勢",
            )
            fig.update_layout(
                xaxis_title="時間", yaxis_title="響應時間 (ms)", height=400
            )
            st.plotly_chart(fig, use_container_width=True)

        # 模組效能統計
        if "module_name" in df_perf.columns:
            module_stats = (
                df_perf.groupby("module_name")
                .agg({"response_time": ["mean", "max"], "error_count": "sum"})
                .round(2)
            )

            st.write("**模組效能統計**")
            st.dataframe(module_stats, use_container_width=True)
    else:
        st.info("暫無效能數據")


def show_trading_performance(monitoring_service):
    """顯示交易績效監控"""
    st.subheader("💰 5.2.9.2 交易績效與資金監控")

    # 獲取交易績效摘要
    performance_summary = monitoring_service.get_trading_performance_summary()

    if "error" in performance_summary:
        st.error(f"獲取交易績效失敗: {performance_summary['error']}")
        return

    # 今日交易摘要
    st.write("**今日交易摘要**")

    col_trade1, col_trade2, col_trade3, col_trade4 = st.columns(4)

    with col_trade1:
        st.metric("總訂單數", performance_summary.get("today_orders", 0))

    with col_trade2:
        st.metric("成交訂單", performance_summary.get("filled_orders", 0))

    with col_trade3:
        win_rate = performance_summary.get("win_rate", 0)
        st.metric("成功率", f"{win_rate:.1f}%")

    with col_trade4:
        total_amount = performance_summary.get("total_amount", 0)
        st.metric("成交金額", f"${total_amount:,.0f}")

    # 資金變化追蹤
    st.write("**資金變化追蹤**")

    col_fund1, col_fund2, col_fund3 = st.columns(3)

    with col_fund1:
        total_commission = performance_summary.get("total_commission", 0)
        st.metric("總手續費", f"${total_commission:,.2f}")

    with col_fund2:
        net_amount = performance_summary.get("net_amount", 0)
        st.metric("淨收益", f"${net_amount:,.2f}")

    with col_fund3:
        last_update = performance_summary.get("last_update", "")
        if last_update:
            update_time = datetime.fromisoformat(last_update.replace("Z", "+00:00"))
            st.metric("最後更新", update_time.strftime("%H:%M:%S"))

    # 模擬投資組合監控數據
    st.write("**投資組合監控**")

    # 創建模擬數據
    portfolio_data = [
        {
            "股票代碼": "2330.TW",
            "持股數量": 1000,
            "平均成本": 580.5,
            "現價": 595.0,
            "未實現損益": 14500,
        },
        {
            "股票代碼": "2317.TW",
            "持股數量": 2000,
            "平均成本": 95.2,
            "現價": 98.5,
            "未實現損益": 6600,
        },
        {
            "股票代碼": "2454.TW",
            "持股數量": 500,
            "平均成本": 420.0,
            "現價": 415.0,
            "未實現損益": -2500,
        },
    ]

    df_portfolio = pd.DataFrame(portfolio_data)
    df_portfolio["市值"] = df_portfolio["持股數量"] * df_portfolio["現價"]
    df_portfolio["報酬率"] = (
        (df_portfolio["現價"] - df_portfolio["平均成本"])
        / df_portfolio["平均成本"]
        * 100
    ).round(2)

    st.dataframe(df_portfolio, use_container_width=True)

    # 持倉分布圖
    if not df_portfolio.empty:
        fig = px.pie(df_portfolio, values="市值", names="股票代碼", title="持倉分布")
        st.plotly_chart(fig, use_container_width=True)


def show_system_logs(monitoring_service):
    """顯示系統日誌"""
    st.subheader("📋 5.2.9.3 日誌管理與查詢系統")

    # 日誌查詢篩選條件
    col_filter1, col_filter2, col_filter3, col_filter4 = st.columns(4)

    with col_filter1:
        log_level = st.selectbox(
            "日誌等級",
            ["", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            format_func=lambda x: "全部" if x == "" else x,
        )

    with col_filter2:
        module_filter = st.text_input("模組篩選", placeholder="輸入模組名稱")

    with col_filter3:
        days_back = st.selectbox(
            "時間範圍", [1, 7, 30, 90], format_func=lambda x: f"最近{x}天"
        )

    with col_filter4:
        limit = st.number_input("顯示筆數", min_value=10, max_value=1000, value=100)

    # 關鍵字搜尋
    keyword = st.text_input("關鍵字搜尋", placeholder="搜尋日誌內容...")

    # 查詢按鈕
    if st.button("🔍 查詢日誌"):
        # 設定時間範圍
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # 獲取系統日誌
        logs = monitoring_service.get_system_logs(
            level=log_level if log_level else None,
            module=module_filter if module_filter else None,
            start_date=start_date,
            end_date=end_date,
            keyword=keyword if keyword else None,
            limit=limit,
        )

        if logs:
            # 轉換為 DataFrame 並顯示
            df_logs = pd.DataFrame(logs)

            # 格式化顯示
            display_df = df_logs.copy()
            display_df["timestamp"] = pd.to_datetime(
                display_df["timestamp"]
            ).dt.strftime("%Y-%m-%d %H:%M:%S")

            # 添加等級顏色
            level_colors = {
                "DEBUG": "🔵",
                "INFO": "🟢",
                "WARNING": "🟡",
                "ERROR": "🔴",
                "CRITICAL": "🟣",
            }
            display_df["等級"] = display_df["level"].apply(
                lambda x: f"{level_colors.get(x, '⚪')} {x}"
            )

            # 選擇顯示欄位
            display_columns = ["timestamp", "等級", "module", "message"]

            st.dataframe(
                display_df[display_columns].rename(
                    columns={"timestamp": "時間", "module": "模組", "message": "訊息"}
                ),
                use_container_width=True,
            )

            # 日誌統計
            st.write("**日誌統計**")
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

            level_counts = df_logs["level"].value_counts()

            with col_stat1:
                st.metric("總日誌數", len(df_logs))

            with col_stat2:
                error_count = level_counts.get("ERROR", 0) + level_counts.get(
                    "CRITICAL", 0
                )
                st.metric("錯誤日誌", error_count)

            with col_stat3:
                warning_count = level_counts.get("WARNING", 0)
                st.metric("警告日誌", warning_count)

            with col_stat4:
                info_count = level_counts.get("INFO", 0)
                st.metric("資訊日誌", info_count)

            # 日誌等級分布圖
            if not level_counts.empty:
                fig = px.bar(
                    x=level_counts.index,
                    y=level_counts.values,
                    title="日誌等級分布",
                    labels={"x": "日誌等級", "y": "數量"},
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("沒有找到符合條件的日誌記錄")


def show_audit_logs(monitoring_service):
    """顯示審計日誌"""
    st.subheader("🔒 資安審計紀錄")

    # 審計日誌篩選條件
    col_audit1, col_audit2, col_audit3, col_audit4 = st.columns(4)

    with col_audit1:
        user_filter = st.text_input("使用者篩選", placeholder="輸入使用者ID")

    with col_audit2:
        action_filter = st.text_input("操作篩選", placeholder="輸入操作類型")

    with col_audit3:
        risk_level = st.selectbox(
            "風險等級",
            ["", "low", "medium", "high"],
            format_func=lambda x: {
                "": "全部",
                "low": "低",
                "medium": "中",
                "high": "高",
            }.get(x, x),
        )

    with col_audit4:
        audit_days = st.selectbox(
            "時間範圍", [1, 7, 30], format_func=lambda x: f"最近{x}天"
        )

    # 查詢審計日誌
    if st.button("🔍 查詢審計日誌"):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=audit_days)

        audit_logs = monitoring_service.get_audit_logs(
            user_id=user_filter if user_filter else None,
            action=action_filter if action_filter else None,
            risk_level=risk_level if risk_level else None,
            start_date=start_date,
            end_date=end_date,
            limit=100,
        )

        if audit_logs:
            df_audit = pd.DataFrame(audit_logs)

            # 格式化顯示
            display_audit = df_audit.copy()
            display_audit["timestamp"] = pd.to_datetime(
                display_audit["timestamp"]
            ).dt.strftime("%Y-%m-%d %H:%M:%S")

            # 添加風險等級顏色
            risk_colors = {"low": "🟢", "medium": "🟡", "high": "🔴"}
            display_audit["風險等級"] = display_audit["risk_level"].apply(
                lambda x: f"{risk_colors.get(x, '⚪')} {x}" if x else "N/A"
            )

            # 添加狀態顏色
            status_colors = {"success": "✅", "failure": "❌", "error": "⚠️"}
            display_audit["狀態"] = display_audit["status"].apply(
                lambda x: f"{status_colors.get(x, '⚪')} {x}"
            )

            st.dataframe(
                display_audit[
                    [
                        "timestamp",
                        "username",
                        "action",
                        "resource",
                        "狀態",
                        "風險等級",
                        "ip_address",
                    ]
                ].rename(
                    columns={
                        "timestamp": "時間",
                        "username": "使用者",
                        "action": "操作",
                        "resource": "資源",
                        "ip_address": "IP地址",
                    }
                ),
                use_container_width=True,
            )

            # 審計統計
            st.write("**審計統計**")
            col_audit_stat1, col_audit_stat2, col_audit_stat3 = st.columns(3)

            with col_audit_stat1:
                st.metric("總操作數", len(df_audit))

            with col_audit_stat2:
                failed_ops = len(df_audit[df_audit["status"] == "failure"])
                st.metric("失敗操作", failed_ops)

            with col_audit_stat3:
                high_risk_ops = len(df_audit[df_audit["risk_level"] == "high"])
                st.metric("高風險操作", high_risk_ops)
        else:
            st.info("沒有找到符合條件的審計記錄")


def show_alert_management(monitoring_service):
    """顯示警報管理"""
    st.subheader("⚠️ 5.2.9.4 警報與通知系統")

    # 警報控制
    col_alert1, col_alert2 = st.columns(2)

    with col_alert1:
        if st.button("🔍 檢查警報"):
            triggered_alerts = monitoring_service.check_alerts()
            if triggered_alerts:
                st.warning(f"觸發了 {len(triggered_alerts)} 個新警報")
                for alert in triggered_alerts:
                    st.error(f"⚠️ {alert['rule_name']}: {alert['message']}")
            else:
                st.success("沒有觸發新警報")

    with col_alert2:
        if st.button("🧹 清理舊數據"):
            success, message = monitoring_service.cleanup_old_data(days_to_keep=30)
            if success:
                st.success(message)
            else:
                st.error(message)

    # 警報記錄查詢
    st.write("**警報記錄查詢**")

    col_alert_filter1, col_alert_filter2, col_alert_filter3 = st.columns(3)

    with col_alert_filter1:
        alert_status = st.selectbox(
            "警報狀態",
            ["", "active", "acknowledged", "resolved"],
            format_func=lambda x: {
                "": "全部",
                "active": "活躍",
                "acknowledged": "已確認",
                "resolved": "已解決",
            }.get(x, x),
        )

    with col_alert_filter2:
        alert_severity = st.selectbox(
            "嚴重程度",
            ["", "low", "medium", "high", "critical"],
            format_func=lambda x: {
                "": "全部",
                "low": "低",
                "medium": "中",
                "high": "高",
                "critical": "嚴重",
            }.get(x, x),
        )

    with col_alert_filter3:
        alert_days = st.selectbox(
            "時間範圍", [1, 7, 30], format_func=lambda x: f"最近{x}天"
        )

    if st.button("🔍 查詢警報"):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=alert_days)

        alerts = monitoring_service.get_alert_records(
            status=alert_status if alert_status else None,
            severity=alert_severity if alert_severity else None,
            start_date=start_date,
            end_date=end_date,
            limit=50,
        )

        if alerts:
            df_alerts = pd.DataFrame(alerts)

            # 格式化顯示
            display_alerts = df_alerts.copy()
            display_alerts["timestamp"] = pd.to_datetime(
                display_alerts["timestamp"]
            ).dt.strftime("%Y-%m-%d %H:%M:%S")

            # 添加嚴重程度顏色
            severity_colors = {
                "low": "🟢",
                "medium": "🟡",
                "high": "🟠",
                "critical": "🔴",
            }
            display_alerts["嚴重程度"] = display_alerts["severity"].apply(
                lambda x: f"{severity_colors.get(x, '⚪')} {x}"
            )

            # 添加狀態顏色
            status_colors = {"active": "🔴", "acknowledged": "🟡", "resolved": "🟢"}
            display_alerts["狀態"] = display_alerts["status"].apply(
                lambda x: f"{status_colors.get(x, '⚪')} {x}"
            )

            st.dataframe(
                display_alerts[
                    [
                        "timestamp",
                        "title",
                        "嚴重程度",
                        "狀態",
                        "current_value",
                        "threshold_value",
                    ]
                ].rename(
                    columns={
                        "timestamp": "時間",
                        "title": "警報標題",
                        "current_value": "當前值",
                        "threshold_value": "閾值",
                    }
                ),
                use_container_width=True,
            )

            # 警報操作
            st.write("**警報操作**")

            active_alerts = [alert for alert in alerts if alert["status"] == "active"]
            if active_alerts:
                alert_to_handle = st.selectbox(
                    "選擇要處理的警報",
                    [""]
                    + [
                        f"{alert['title']} - {alert['alert_id'][:8]}"
                        for alert in active_alerts
                    ],
                )

                if alert_to_handle:
                    col_op1, col_op2 = st.columns(2)

                    with col_op1:
                        if st.button("✅ 確認警報"):
                            alert_id = None
                            for alert in active_alerts:
                                if (
                                    f"{alert['title']} - {alert['alert_id'][:8]}"
                                    == alert_to_handle
                                ):
                                    alert_id = alert["alert_id"]
                                    break

                            if alert_id:
                                success, message = monitoring_service.acknowledge_alert(
                                    alert_id, "system_user"
                                )
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)

                    with col_op2:
                        if st.button("🔧 解決警報"):
                            alert_id = None
                            for alert in active_alerts:
                                if (
                                    f"{alert['title']} - {alert['alert_id'][:8]}"
                                    == alert_to_handle
                                ):
                                    alert_id = alert["alert_id"]
                                    break

                            if alert_id:
                                success, message = monitoring_service.resolve_alert(
                                    alert_id, "system_user"
                                )
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
            else:
                st.info("目前沒有活躍的警報")
        else:
            st.info("沒有找到符合條件的警報記錄")


def show_reports_analysis(monitoring_service):
    """顯示報告分析"""
    st.subheader("📈 5.2.9.5 報告與分析")

    # 報告生成
    st.write("**系統運行報告生成**")

    col_report1, col_report2, col_report3 = st.columns(3)

    with col_report1:
        report_type = st.selectbox(
            "報告類型",
            ["daily", "weekly", "monthly"],
            format_func=lambda x: {
                "daily": "日報",
                "weekly": "週報",
                "monthly": "月報",
            }[x],
        )

    with col_report2:
        export_format = st.selectbox("匯出格式", ["json", "csv"])

    with col_report3:
        if st.button("📊 生成報告"):
            report = monitoring_service.generate_system_report(report_type=report_type)

            if "error" not in report:
                st.success("報告生成成功")

                # 顯示報告摘要
                st.write("**報告摘要**")

                period = report.get("period", {})
                start_date = period.get("start_date", "")
                end_date = period.get("end_date", "")
                st.write(f"報告期間: {start_date} 至 {end_date}")

                # 系統指標摘要
                metrics_summary = report.get("system_metrics", {})
                if "cpu_usage" in metrics_summary:
                    col_summary1, col_summary2, col_summary3 = st.columns(3)

                    with col_summary1:
                        cpu_avg = metrics_summary["cpu_usage"].get("avg", 0)
                        st.metric("平均CPU使用率", f"{cpu_avg}%")

                    with col_summary2:
                        memory_avg = metrics_summary["memory_usage"].get("avg", 0)
                        st.metric("平均記憶體使用率", f"{memory_avg}%")

                    with col_summary3:
                        disk_avg = metrics_summary["disk_usage"].get("avg", 0)
                        st.metric("平均磁碟使用率", f"{disk_avg}%")

                # 警報摘要
                alerts_summary = report.get("alerts_summary", {})
                if "total_alerts" in alerts_summary:
                    st.write("**警報摘要**")
                    col_alert_summary1, col_alert_summary2, col_alert_summary3 = (
                        st.columns(3)
                    )

                    with col_alert_summary1:
                        st.metric("總警報數", alerts_summary.get("total_alerts", 0))

                    with col_alert_summary2:
                        st.metric("嚴重警報", alerts_summary.get("critical_alerts", 0))

                    with col_alert_summary3:
                        st.metric(
                            "未解決警報", alerts_summary.get("unresolved_alerts", 0)
                        )

                # 匯出報告
                if st.button("💾 匯出報告"):
                    success, message, filepath = monitoring_service.export_report(
                        report, export_format
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
            else:
                st.error(f"生成報告失敗: {report['error']}")

    # 數據清理
    st.write("**數據管理**")

    col_cleanup1, col_cleanup2 = st.columns(2)

    with col_cleanup1:
        days_to_keep = st.number_input("保留天數", min_value=7, max_value=365, value=30)

    with col_cleanup2:
        if st.button("🗑️ 清理舊數據"):
            success, message = monitoring_service.cleanup_old_data(days_to_keep)
            if success:
                st.success(message)
            else:
                st.error(message)
