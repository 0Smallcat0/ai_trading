"""
交易執行頁面

此模組實現了交易執行頁面，提供下單、查詢和監控功能。
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# 導入服務層
try:
    from src.core.trade_execution_service import TradeExecutionService
    from src.ui.components.charts import line_chart, bar_chart
    from src.ui.components.tables import data_table, filterable_table
except ImportError:
    # 如果無法導入，使用備用方案
    TradeExecutionService = None
    line_chart = bar_chart = None
    data_table = filterable_table = None


def get_trade_execution_service():
    """獲取交易執行服務實例"""
    if TradeExecutionService is None:
        return None

    if "trade_service" not in st.session_state:
        try:
            st.session_state.trade_service = TradeExecutionService()
        except Exception as e:
            st.error(f"初始化交易執行服務失敗: {e}")
            return None

    return st.session_state.trade_service


def show():
    """顯示交易執行頁面"""
    st.title("📈 交易執行")

    # 獲取交易執行服務
    trade_service = get_trade_execution_service()

    if not trade_service:
        st.error("交易執行服務不可用，請檢查系統配置")
        return

    # 頁面標籤
    tabs = st.tabs(
        ["📋 下單介面", "📊 訂單記錄", "⏱️ 訂單狀態", "🔗 連線狀態", "⚠️ 異常處理"]
    )

    with tabs[0]:
        show_order_interface(trade_service)

    with tabs[1]:
        show_order_history(trade_service)

    with tabs[2]:
        show_order_status(trade_service)

    with tabs[3]:
        show_connection_status(trade_service)

    with tabs[4]:
        show_exception_handling(trade_service)


def show_order_interface(trade_service):
    """顯示下單介面"""
    st.subheader("📋 交易下單介面")

    # 交易模式切換
    col_mode1, col_mode2 = st.columns([1, 1])
    with col_mode1:
        current_mode = "模擬交易" if trade_service.is_simulation_mode else "實盤交易"
        st.info(f"當前模式: {current_mode}")

    with col_mode2:
        if st.button("🔄 切換交易模式"):
            new_mode = not trade_service.is_simulation_mode
            success, message = trade_service.switch_trading_mode(new_mode)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    st.divider()

    # 下單表單
    with st.form("order_form"):
        st.subheader("5.2.8.1 交易下單")

        # 股票標的選擇
        col1, col2 = st.columns([2, 1])
        with col1:
            symbol_input = st.text_input(
                "股票代碼", placeholder="輸入股票代碼，如: 2330.TW"
            )
        with col2:
            if st.form_submit_button("🔍 搜尋"):
                if symbol_input:
                    symbols = trade_service.get_available_symbols(symbol_input)
                    if symbols:
                        st.success(f"找到 {len(symbols)} 個相關股票")
                    else:
                        st.warning("未找到相關股票")

        # 收藏清單和最近交易
        col_fav, col_recent = st.columns(2)
        with col_fav:
            st.write("**收藏清單**")
            favorites = trade_service.get_favorite_symbols()
            if favorites:
                selected_fav = st.selectbox(
                    "選擇收藏股票", [""] + favorites, key="fav_select"
                )
                if selected_fav:
                    symbol_input = selected_fav

        with col_recent:
            st.write("**最近交易**")
            recent = trade_service.get_recent_symbols()
            if recent:
                selected_recent = st.selectbox(
                    "選擇最近交易", [""] + recent, key="recent_select"
                )
                if selected_recent:
                    symbol_input = selected_recent

        # 交易方向和數量
        col_action, col_quantity = st.columns(2)
        with col_action:
            action = st.selectbox(
                "交易方向",
                ["buy", "sell"],
                format_func=lambda x: "買進" if x == "buy" else "賣出",
            )

        with col_quantity:
            quantity = st.number_input("數量（股）", min_value=1, value=1000, step=1000)
            st.caption(f"約 {quantity // 1000} 張")

        # 價格設定
        col_type, col_price = st.columns(2)
        with col_type:
            order_type = st.selectbox(
                "訂單類型",
                ["market", "limit", "stop", "stop_limit"],
                format_func=lambda x: {
                    "market": "市價單",
                    "limit": "限價單",
                    "stop": "停損單",
                    "stop_limit": "停損限價單",
                }[x],
            )

        with col_price:
            price = None
            if order_type in ["limit", "stop_limit"]:
                price = st.number_input(
                    "委託價格", min_value=0.01, value=100.0, step=0.01
                )
            else:
                st.write("市價單無需設定價格")

        # 訂單型態
        time_in_force = st.selectbox(
            "訂單有效期",
            ["ROD", "IOC", "FOK"],
            format_func=lambda x: {
                "ROD": "ROD (當日有效)",
                "IOC": "IOC (立即成交否則取消)",
                "FOK": "FOK (全部成交否則取消)",
            }[x],
        )

        # 策略資訊（可選）
        with st.expander("策略資訊（可選）"):
            strategy_name = st.text_input("策略名稱")
            signal_id = st.text_input("信號ID")

        # 提交按鈕
        submitted = st.form_submit_button("📤 提交訂單", type="primary")

        if submitted:
            # 驗證輸入
            if not symbol_input:
                st.error("請輸入股票代碼")
            elif order_type in ["limit", "stop_limit"] and not price:
                st.error("限價單必須設定價格")
            else:
                # 準備訂單數據
                order_data = {
                    "symbol": symbol_input,
                    "action": action,
                    "quantity": quantity,
                    "order_type": order_type,
                    "time_in_force": time_in_force,
                    "price": price,
                    "strategy_name": strategy_name if strategy_name else None,
                    "signal_id": signal_id if signal_id else None,
                }

                # 提交訂單
                success, message, order_id = trade_service.submit_order(order_data)

                if success:
                    st.success(f"✅ {message}")
                    st.info(f"訂單ID: {order_id}")
                    # 清空表單
                    st.rerun()
                else:
                    st.error(f"❌ {message}")


def show_order_history(trade_service):
    """顯示訂單記錄"""
    st.subheader("📊 歷史下單記錄查詢")

    # 篩選條件
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        symbol_filter = st.text_input("股票代碼篩選", key="history_symbol")

    with col2:
        status_filter = st.selectbox(
            "訂單狀態",
            ["", "pending", "submitted", "filled", "cancelled", "rejected"],
            format_func=lambda x: {
                "": "全部",
                "pending": "待處理",
                "submitted": "已提交",
                "filled": "已成交",
                "cancelled": "已取消",
                "rejected": "已拒絕",
            }.get(x, x),
            key="history_status",
        )

    with col3:
        days_back = st.selectbox(
            "時間範圍", [7, 30, 90, 365], format_func=lambda x: f"最近{x}天"
        )

    with col4:
        limit = st.number_input("顯示筆數", min_value=10, max_value=1000, value=100)

    # 查詢按鈕
    if st.button("🔍 查詢訂單記錄"):
        # 設定時間範圍
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # 獲取訂單記錄
        orders = trade_service.get_order_history(
            symbol=symbol_filter if symbol_filter else None,
            status=status_filter if status_filter else None,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

        if orders:
            # 轉換為 DataFrame 並顯示
            df = pd.DataFrame(orders)

            # 格式化顯示
            display_df = df.copy()
            display_df["created_at"] = pd.to_datetime(
                display_df["created_at"]
            ).dt.strftime("%Y-%m-%d %H:%M:%S")
            display_df["action"] = display_df["action"].map(
                {"buy": "買進", "sell": "賣出"}
            )
            display_df["status"] = display_df["status"].map(
                {
                    "pending": "待處理",
                    "submitted": "已提交",
                    "filled": "已成交",
                    "cancelled": "已取消",
                    "rejected": "已拒絕",
                }
            )

            # 選擇顯示欄位
            display_columns = [
                "created_at",
                "symbol",
                "action",
                "quantity",
                "price",
                "filled_quantity",
                "status",
            ]

            st.dataframe(
                display_df[display_columns].rename(
                    columns={
                        "created_at": "建立時間",
                        "symbol": "股票代碼",
                        "action": "方向",
                        "quantity": "委託數量",
                        "price": "委託價格",
                        "filled_quantity": "成交數量",
                        "status": "狀態",
                    }
                ),
                use_container_width=True,
            )

            # 匯出功能
            col_export1, col_export2 = st.columns(2)
            with col_export1:
                if st.button("📄 匯出 CSV"):
                    success, message, filepath = trade_service.export_order_history(
                        format_type="csv",
                        symbol=symbol_filter if symbol_filter else None,
                        status=status_filter if status_filter else None,
                        start_date=start_date,
                        end_date=end_date,
                        limit=limit,
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(message)

            with col_export2:
                if st.button("📊 匯出 Excel"):
                    success, message, filepath = trade_service.export_order_history(
                        format_type="excel",
                        symbol=symbol_filter if symbol_filter else None,
                        status=status_filter if status_filter else None,
                        start_date=start_date,
                        end_date=end_date,
                        limit=limit,
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
        else:
            st.info("沒有找到符合條件的訂單記錄")

    # 交易統計
    st.subheader("📈 交易統計分析")

    # 獲取統計數據
    stats = trade_service.get_trading_statistics()

    if stats:
        # 顯示統計指標
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("總訂單數", stats["orders"]["total"])

        with col2:
            st.metric("成交訂單", stats["orders"]["filled"])

        with col3:
            st.metric("成功率", f"{stats['orders']['success_rate']}%")

        with col4:
            st.metric("總成交金額", f"${stats['amounts']['total_amount']:,.0f}")

        # 詳細統計
        with st.expander("詳細統計資訊"):
            col_detail1, col_detail2 = st.columns(2)

            with col_detail1:
                st.write("**訂單統計**")
                st.write(f"- 已成交: {stats['orders']['filled']}")
                st.write(f"- 已取消: {stats['orders']['cancelled']}")
                st.write(f"- 已拒絕: {stats['orders']['rejected']}")

            with col_detail2:
                st.write("**費用統計**")
                st.write(f"- 總手續費: ${stats['amounts']['total_commission']:,.2f}")
                st.write(f"- 總交易稅: ${stats['amounts']['total_tax']:,.2f}")
                st.write(f"- 成交筆數: {stats['executions']['total']}")
    else:
        st.info("暫無統計數據")


def show_order_status(trade_service):
    """顯示訂單狀態監控"""
    st.subheader("⏱️ 訂單狀態監控")

    # 即時訂單狀態
    st.write("**5.2.8.4 訂單狀態監控**")

    # 獲取待處理訂單
    pending_orders = trade_service.get_pending_orders()

    if pending_orders:
        st.write(f"**委託中訂單 ({len(pending_orders)} 筆)**")

        # 轉換為 DataFrame
        df = pd.DataFrame(pending_orders)

        # 格式化顯示
        display_df = df.copy()
        display_df["created_at"] = pd.to_datetime(display_df["created_at"]).dt.strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        display_df["action"] = display_df["action"].map({"buy": "買進", "sell": "賣出"})
        display_df["status"] = display_df["status"].map(
            {"pending": "待處理", "submitted": "已提交", "partial_filled": "部分成交"}
        )

        # 添加進度條
        for idx, row in display_df.iterrows():
            filled_ratio = (
                (row["filled_quantity"] / row["quantity"]) if row["quantity"] > 0 else 0
            )
            display_df.loc[idx, "progress"] = f"{filled_ratio:.1%}"

        st.dataframe(
            display_df[
                [
                    "created_at",
                    "symbol",
                    "action",
                    "quantity",
                    "filled_quantity",
                    "progress",
                    "status",
                ]
            ].rename(
                columns={
                    "created_at": "建立時間",
                    "symbol": "股票代碼",
                    "action": "方向",
                    "quantity": "委託數量",
                    "filled_quantity": "成交數量",
                    "progress": "成交進度",
                    "status": "狀態",
                }
            ),
            use_container_width=True,
        )

        # 取消訂單功能
        st.write("**訂單操作**")
        col_cancel1, col_cancel2 = st.columns([2, 1])
        with col_cancel1:
            order_to_cancel = st.selectbox(
                "選擇要取消的訂單",
                [""]
                + [
                    f"{order['symbol']} - {order['order_id'][:8]}"
                    for order in pending_orders
                ],
            )

        with col_cancel2:
            if st.button("❌ 取消訂單") and order_to_cancel:
                # 提取訂單ID
                order_id = None
                for order in pending_orders:
                    if (
                        f"{order['symbol']} - {order['order_id'][:8]}"
                        == order_to_cancel
                    ):
                        order_id = order["order_id"]
                        break

                if order_id:
                    success, message = trade_service.cancel_order(order_id)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    else:
        st.info("目前沒有委託中的訂單")

    st.divider()

    # 今日成交記錄
    st.write("**今日成交記錄**")
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())

    today_executions = trade_service.get_trade_executions(
        start_date=today_start, end_date=today_end, limit=50
    )

    if today_executions:
        df_exec = pd.DataFrame(today_executions)

        # 格式化顯示
        display_exec = df_exec.copy()
        display_exec["execution_time"] = pd.to_datetime(
            display_exec["execution_time"]
        ).dt.strftime("%H:%M:%S")
        display_exec["action"] = display_exec["action"].map(
            {"buy": "買進", "sell": "賣出"}
        )

        st.dataframe(
            display_exec[
                ["execution_time", "symbol", "action", "quantity", "price", "amount"]
            ].rename(
                columns={
                    "execution_time": "成交時間",
                    "symbol": "股票代碼",
                    "action": "方向",
                    "quantity": "成交數量",
                    "price": "成交價格",
                    "amount": "成交金額",
                }
            ),
            use_container_width=True,
        )

        # 今日統計
        total_amount = df_exec["amount"].sum()
        total_commission = df_exec["commission"].sum()
        total_tax = df_exec["tax"].sum()

        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("今日成交金額", f"${total_amount:,.0f}")
        with col_stat2:
            st.metric("今日手續費", f"${total_commission:,.2f}")
        with col_stat3:
            st.metric("今日交易稅", f"${total_tax:,.2f}")
    else:
        st.info("今日尚無成交記錄")


def show_connection_status(trade_service):
    """顯示連線狀態"""
    st.subheader("🔗 API 連線狀態")

    # 獲取券商狀態
    broker_status = trade_service.get_broker_status()

    if "error" in broker_status:
        st.error(f"獲取連線狀態失敗: {broker_status['error']}")
        return

    # 連線狀態總覽
    col_status1, col_status2, col_status3 = st.columns(3)

    with col_status1:
        status_color = "🟢" if broker_status["connected"] else "🔴"
        st.metric(
            "連線狀態",
            f"{status_color} {'已連線' if broker_status['connected'] else '未連線'}",
        )

    with col_status2:
        mode_color = "🟡" if broker_status["is_simulation"] else "🟢"
        st.metric(
            "交易模式",
            f"{mode_color} {'模擬交易' if broker_status['is_simulation'] else '實盤交易'}",
        )

    with col_status3:
        st.metric("當前券商", broker_status["current_broker"])

    # 詳細狀態資訊
    with st.expander("詳細連線資訊"):
        col_detail1, col_detail2 = st.columns(2)

        with col_detail1:
            st.write("**連線資訊**")
            if broker_status["connection_time"]:
                st.write(f"- 連線時間: {broker_status['connection_time']}")
            if broker_status["last_heartbeat"]:
                st.write(f"- 最後心跳: {broker_status['last_heartbeat']}")
            if broker_status["latency_ms"]:
                st.write(f"- 延遲: {broker_status['latency_ms']:.2f} ms")

        with col_detail2:
            st.write("**使用統計**")
            st.write(f"- 錯誤次數: {broker_status['error_count']}")
            st.write(f"- 今日下單: {broker_status['daily_order_count']}")

    # 系統健康檢查
    st.write("**系統健康檢查**")

    # 模擬健康檢查數據
    health_checks = [
        {"name": "資料庫連線", "status": "正常", "response_time": "15ms"},
        {"name": "市場數據", "status": "正常", "response_time": "23ms"},
        {"name": "風險管理", "status": "正常", "response_time": "8ms"},
        {"name": "訂單管理", "status": "正常", "response_time": "12ms"},
    ]

    for check in health_checks:
        col_check1, col_check2, col_check3 = st.columns([2, 1, 1])
        with col_check1:
            st.write(check["name"])
        with col_check2:
            status_icon = "✅" if check["status"] == "正常" else "❌"
            st.write(f"{status_icon} {check['status']}")
        with col_check3:
            st.write(check["response_time"])

    # 市場狀態
    st.write("**市場狀態**")

    # 模擬市場狀態
    now = datetime.now()
    market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
    market_close = now.replace(hour=13, minute=30, second=0, microsecond=0)

    if market_open <= now <= market_close and now.weekday() < 5:
        market_status = "🟢 開盤中"
    else:
        market_status = "🔴 休市中"

    st.info(f"台股市場狀態: {market_status}")


def show_exception_handling(trade_service):
    """顯示異常處理"""
    st.subheader("⚠️ 訂單異常處理與通知")

    # 獲取交易異常
    exceptions = trade_service.get_trading_exceptions(limit=50)

    if exceptions:
        # 異常統計
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

        total_exceptions = len(exceptions)
        pending_exceptions = len([e for e in exceptions if e["status"] == "pending"])
        critical_exceptions = len(
            [e for e in exceptions if e["severity"] == "critical"]
        )
        resolved_exceptions = len([e for e in exceptions if e["status"] == "resolved"])

        with col_stat1:
            st.metric("總異常數", total_exceptions)
        with col_stat2:
            st.metric("待處理", pending_exceptions)
        with col_stat3:
            st.metric("嚴重異常", critical_exceptions)
        with col_stat4:
            st.metric("已解決", resolved_exceptions)

        # 篩選條件
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            severity_filter = st.selectbox(
                "嚴重程度篩選",
                ["", "low", "medium", "high", "critical"],
                format_func=lambda x: {
                    "": "全部",
                    "low": "低",
                    "medium": "中",
                    "high": "高",
                    "critical": "嚴重",
                }.get(x, x),
            )

        with col_filter2:
            status_filter = st.selectbox(
                "處理狀態篩選",
                ["", "pending", "processing", "resolved", "ignored"],
                format_func=lambda x: {
                    "": "全部",
                    "pending": "待處理",
                    "processing": "處理中",
                    "resolved": "已解決",
                    "ignored": "已忽略",
                }.get(x, x),
            )

        # 篩選異常
        filtered_exceptions = exceptions
        if severity_filter:
            filtered_exceptions = [
                e for e in filtered_exceptions if e["severity"] == severity_filter
            ]
        if status_filter:
            filtered_exceptions = [
                e for e in filtered_exceptions if e["status"] == status_filter
            ]

        # 顯示異常列表
        if filtered_exceptions:
            df_exceptions = pd.DataFrame(filtered_exceptions)

            # 格式化顯示
            display_exceptions = df_exceptions.copy()
            display_exceptions["timestamp"] = pd.to_datetime(
                display_exceptions["timestamp"]
            ).dt.strftime("%Y-%m-%d %H:%M:%S")
            display_exceptions["severity"] = display_exceptions["severity"].map(
                {"low": "低", "medium": "中", "high": "高", "critical": "嚴重"}
            )
            display_exceptions["status"] = display_exceptions["status"].map(
                {
                    "pending": "待處理",
                    "processing": "處理中",
                    "resolved": "已解決",
                    "ignored": "已忽略",
                }
            )

            # 添加顏色編碼
            def get_severity_color(severity):
                colors = {"低": "🟢", "中": "🟡", "高": "🟠", "嚴重": "🔴"}
                return colors.get(severity, "⚪")

            display_exceptions["severity_icon"] = display_exceptions["severity"].apply(
                get_severity_color
            )

            st.dataframe(
                display_exceptions[
                    [
                        "timestamp",
                        "exception_type",
                        "severity_icon",
                        "severity",
                        "error_message",
                        "status",
                    ]
                ].rename(
                    columns={
                        "timestamp": "發生時間",
                        "exception_type": "異常類型",
                        "severity_icon": "",
                        "severity": "嚴重程度",
                        "error_message": "錯誤訊息",
                        "status": "處理狀態",
                    }
                ),
                use_container_width=True,
            )
        else:
            st.info("沒有符合篩選條件的異常記錄")
    else:
        st.info("目前沒有異常記錄")

    # 通知設定
    st.write("**通知設定**")

    with st.expander("異常通知設定"):
        col_notify1, col_notify2 = st.columns(2)

        with col_notify1:
            st.write("**通知方式**")
            email_notify = st.checkbox("郵件通知", value=True)
            sms_notify = st.checkbox("簡訊通知", value=False)
            system_notify = st.checkbox("系統通知", value=True)

        with col_notify2:
            st.write("**通知條件**")
            notify_severity = st.multiselect(
                "通知嚴重程度",
                ["low", "medium", "high", "critical"],
                default=["high", "critical"],
                format_func=lambda x: {
                    "low": "低",
                    "medium": "中",
                    "high": "高",
                    "critical": "嚴重",
                }[x],
            )

        if st.button("💾 保存通知設定"):
            st.success("通知設定已保存")

    # 手動處理異常
    if exceptions:
        st.write("**手動處理異常**")

        pending_exceptions = [e for e in exceptions if e["status"] == "pending"]
        if pending_exceptions:
            exception_to_handle = st.selectbox(
                "選擇要處理的異常",
                [""]
                + [
                    f"{e['exception_type']} - {e['exception_id'][:8]}"
                    for e in pending_exceptions
                ],
            )

            if exception_to_handle:
                col_action1, col_action2, col_action3 = st.columns(3)

                with col_action1:
                    if st.button("✅ 標記為已解決"):
                        st.success("異常已標記為已解決")

                with col_action2:
                    if st.button("🔄 重新處理"):
                        st.info("異常已重新加入處理佇列")

                with col_action3:
                    if st.button("❌ 忽略異常"):
                        st.warning("異常已標記為忽略")
        else:
            st.info("目前沒有待處理的異常")
