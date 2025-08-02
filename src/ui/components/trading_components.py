"""
交易執行組件

此模組提供交易執行系統的各種組件，包括：
- 交易訂單介面組件
- 歷史記錄查詢組件
- 訂單監控組件
- 批量操作組件
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json

# 導入響應式設計組件
from ..responsive import ResponsiveComponents, responsive_manager


class TradingComponents:
    """交易執行組件類"""

    @staticmethod
    def order_form(
        order_type: str = "market", form_key: str = "trading_order_form"
    ) -> Optional[Dict[str, Any]]:
        """
        交易訂單表單

        Args:
            order_type: 訂單類型
            form_key: 表單鍵值

        Returns:
            訂單數據，如果未提交則返回 None
        """
        # 根據訂單類型配置表單欄位
        base_fields = [
            {
                "key": "symbol",
                "label": "股票代碼",
                "type": "select",
                "options": [
                    "2330.TW",
                    "2317.TW",
                    "2454.TW",
                    "AAPL",
                    "MSFT",
                    "GOOGL",
                    "TSLA",
                ],
            },
            {
                "key": "action",
                "label": "交易方向",
                "type": "select",
                "options": ["買入", "賣出"],
            },
            {"key": "quantity", "label": "數量", "type": "number", "default": 100},
        ]

        # 根據訂單類型添加特定欄位
        if order_type in ["limit", "stop_limit"]:
            base_fields.append(
                {"key": "price", "label": "價格", "type": "number", "default": 100.0}
            )

        if order_type in ["stop", "stop_limit"]:
            base_fields.append(
                {
                    "key": "stop_price",
                    "label": "停損價格",
                    "type": "number",
                    "default": 95.0,
                }
            )

        if order_type == "conditional":
            base_fields.extend(
                [
                    {
                        "key": "condition_type",
                        "label": "條件類型",
                        "type": "select",
                        "options": ["價格突破", "技術指標", "時間條件"],
                    },
                    {
                        "key": "condition_value",
                        "label": "條件值",
                        "type": "number",
                        "default": 105.0,
                    },
                ]
            )

        # 通用欄位
        base_fields.extend(
            [
                {
                    "key": "time_in_force",
                    "label": "有效期",
                    "type": "select",
                    "options": ["當日有效", "取消前有效", "立即成交或取消"],
                },
                {"key": "notes", "label": "備註", "type": "text", "default": ""},
            ]
        )

        form_config = {"title": f"{order_type.upper()} 訂單", "fields": base_fields}

        return ResponsiveComponents.responsive_form(form_config, form_key)

    @staticmethod
    def order_monitoring_panel(orders: List[Dict[str, Any]]) -> None:
        """
        訂單監控面板

        Args:
            orders: 訂單列表
        """
        if not orders:
            st.info("目前沒有活躍訂單")
            return

        # 訂單統計
        order_stats = TradingComponents._calculate_order_stats(orders)

        stats_metrics = [
            {
                "title": "總訂單數",
                "value": str(order_stats["total_orders"]),
                "status": "normal",
                "icon": "📋",
            },
            {
                "title": "待成交",
                "value": str(order_stats["pending_orders"]),
                "status": "warning" if order_stats["pending_orders"] > 0 else "success",
                "icon": "⏳",
            },
            {
                "title": "已成交",
                "value": str(order_stats["filled_orders"]),
                "status": "success",
                "icon": "✅",
            },
            {
                "title": "已取消",
                "value": str(order_stats["cancelled_orders"]),
                "status": "error" if order_stats["cancelled_orders"] > 0 else "normal",
                "icon": "❌",
            },
        ]

        ResponsiveComponents.responsive_metric_cards(
            stats_metrics, desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

        # 訂單列表
        st.subheader("訂單詳情")

        # 轉換為 DataFrame
        df = pd.DataFrame(orders)
        if not df.empty:
            # 重新排序列
            column_order = [
                "created_at",
                "symbol",
                "action",
                "order_type",
                "quantity",
                "price",
                "status",
            ]
            df = df.reindex(columns=[col for col in column_order if col in df.columns])

            # 添加狀態顏色
            def style_status(val):
                if val == "已成交":
                    return "background-color: #d4edda"
                elif val == "待成交":
                    return "background-color: #fff3cd"
                elif val == "已取消":
                    return "background-color: #f8d7da"
                return ""

            styled_df = df.style.applymap(style_status, subset=["status"])
            ResponsiveComponents.responsive_dataframe(styled_df, title="訂單監控")

    @staticmethod
    def _calculate_order_stats(orders: List[Dict[str, Any]]) -> Dict[str, int]:
        """計算訂單統計"""
        stats = {
            "total_orders": len(orders),
            "pending_orders": 0,
            "filled_orders": 0,
            "cancelled_orders": 0,
        }

        for order in orders:
            status = order.get("status", "")
            if status == "待成交":
                stats["pending_orders"] += 1
            elif status == "已成交":
                stats["filled_orders"] += 1
            elif status == "已取消":
                stats["cancelled_orders"] += 1

        return stats

    @staticmethod
    def trading_history_panel(
        transactions: List[Dict[str, Any]], date_range: Tuple[datetime, datetime] = None
    ) -> None:
        """
        交易歷史面板

        Args:
            transactions: 交易記錄列表
            date_range: 日期範圍篩選
        """
        if not transactions:
            st.info("沒有交易記錄")
            return

        # 篩選日期範圍
        if date_range:
            start_date, end_date = date_range
            transactions = [
                t
                for t in transactions
                if start_date
                <= datetime.strptime(t.get("date", ""), "%Y-%m-%d %H:%M:%S")
                <= end_date
            ]

        # 交易統計
        trade_stats = TradingComponents._calculate_trade_stats(transactions)

        stats_metrics = [
            {
                "title": "總交易次數",
                "value": str(trade_stats["total_trades"]),
                "status": "normal",
                "icon": "📊",
            },
            {
                "title": "買入次數",
                "value": str(trade_stats["buy_trades"]),
                "status": "success",
                "icon": "📈",
            },
            {
                "title": "賣出次數",
                "value": str(trade_stats["sell_trades"]),
                "status": "error",
                "icon": "📉",
            },
            {
                "title": "總成交金額",
                "value": f"${trade_stats['total_amount']:,.0f}",
                "status": "normal",
                "icon": "💰",
            },
        ]

        ResponsiveComponents.responsive_metric_cards(
            stats_metrics, desktop_cols=4, tablet_cols=2, mobile_cols=1
        )

        # 交易記錄表格
        st.subheader("交易記錄")

        df = pd.DataFrame(transactions)
        if not df.empty:
            ResponsiveComponents.responsive_dataframe(df, title="歷史交易記錄")

        # 交易分析圖表
        if len(transactions) > 0:
            TradingComponents._render_trading_charts(transactions)

    @staticmethod
    def _calculate_trade_stats(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """計算交易統計"""
        stats = {
            "total_trades": len(transactions),
            "buy_trades": 0,
            "sell_trades": 0,
            "total_amount": 0,
        }

        for trade in transactions:
            action = trade.get("action", "")
            amount = trade.get("amount", 0)

            if action == "買入":
                stats["buy_trades"] += 1
            elif action == "賣出":
                stats["sell_trades"] += 1

            stats["total_amount"] += amount

        return stats

    @staticmethod
    def _render_trading_charts(transactions: List[Dict[str, Any]]) -> None:
        """渲染交易分析圖表"""
        st.subheader("交易分析圖表")

        # 使用響應式列佈局
        cols = responsive_manager.create_responsive_columns(
            desktop_cols=2, tablet_cols=1, mobile_cols=1
        )

        with cols[0]:
            # 交易量分佈圖
            TradingComponents._render_volume_distribution(transactions)

        with cols[1 % len(cols)]:
            # 交易時間分佈圖
            TradingComponents._render_time_distribution(transactions)

    @staticmethod
    def _render_volume_distribution(transactions: List[Dict[str, Any]]) -> None:
        """渲染交易量分佈圖"""
        # 提取交易量數據
        volumes = [t.get("quantity", 0) for t in transactions]

        if volumes:
            fig = px.histogram(
                x=volumes,
                nbins=20,
                title="交易量分佈",
                labels={"x": "交易量", "y": "頻次"},
            )

            height = responsive_manager.get_chart_height(300)
            fig.update_layout(height=height)

            st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def _render_time_distribution(transactions: List[Dict[str, Any]]) -> None:
        """渲染交易時間分佈圖"""
        # 提取交易時間數據
        times = []
        for t in transactions:
            try:
                dt = datetime.strptime(t.get("date", ""), "%Y-%m-%d %H:%M:%S")
                times.append(dt.hour)
            except:
                continue

        if times:
            fig = px.histogram(
                x=times,
                nbins=24,
                title="交易時間分佈",
                labels={"x": "小時", "y": "交易次數"},
            )

            height = responsive_manager.get_chart_height(300)
            fig.update_layout(height=height)

            st.plotly_chart(fig, use_container_width=True)

    @staticmethod
    def batch_operations_panel() -> None:
        """批量操作面板"""
        st.subheader("批量操作")

        # 批量操作選項
        operation_type = st.selectbox(
            "選擇操作類型", ["批量下單", "批量撤單", "投資組合調整", "風險平衡"]
        )

        if operation_type == "批量下單":
            TradingComponents._show_batch_order_form()
        elif operation_type == "批量撤單":
            TradingComponents._show_batch_cancel_form()
        elif operation_type == "投資組合調整":
            TradingComponents._show_portfolio_rebalance_form()
        else:
            TradingComponents._show_risk_balance_form()

    @staticmethod
    def _show_batch_order_form() -> None:
        """顯示批量下單表單"""
        st.write("### 批量下單")

        # 上傳 CSV 檔案
        uploaded_file = st.file_uploader("上傳訂單 CSV 檔案", type=["csv"])

        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.write("預覽訂單：")
                st.dataframe(df)

                if st.button("執行批量下單", type="primary"):
                    st.success(f"已提交 {len(df)} 筆訂單")
            except Exception as e:
                st.error(f"檔案格式錯誤: {e}")

        # 手動輸入
        st.write("或手動輸入多筆訂單：")

        num_orders = st.number_input("訂單數量", min_value=1, max_value=10, value=3)

        orders = []
        for i in range(num_orders):
            with st.expander(f"訂單 {i+1}"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    symbol = st.selectbox(
                        f"股票代碼 {i+1}",
                        ["2330.TW", "AAPL", "MSFT"],
                        key=f"symbol_{i}",
                    )

                with col2:
                    action = st.selectbox(
                        f"方向 {i+1}", ["買入", "賣出"], key=f"action_{i}"
                    )

                with col3:
                    quantity = st.number_input(
                        f"數量 {i+1}", min_value=1, value=100, key=f"quantity_{i}"
                    )

                orders.append(
                    {"symbol": symbol, "action": action, "quantity": quantity}
                )

        if st.button("提交批量訂單", type="primary"):
            st.success(f"已提交 {len(orders)} 筆訂單")

    @staticmethod
    def _show_batch_cancel_form() -> None:
        """顯示批量撤單表單"""
        st.write("### 批量撤單")

        # 模擬待撤銷訂單
        pending_orders = [
            {"id": "ORD001", "symbol": "2330.TW", "action": "買入", "quantity": 100},
            {"id": "ORD002", "symbol": "AAPL", "action": "賣出", "quantity": 50},
            {"id": "ORD003", "symbol": "MSFT", "action": "買入", "quantity": 200},
        ]

        if pending_orders:
            st.write("選擇要撤銷的訂單：")

            selected_orders = []
            for order in pending_orders:
                if st.checkbox(
                    f"{order['id']} - {order['symbol']} {order['action']} {order['quantity']}"
                ):
                    selected_orders.append(order)

            if selected_orders and st.button("撤銷選中訂單", type="primary"):
                st.success(f"已撤銷 {len(selected_orders)} 筆訂單")
        else:
            st.info("沒有待撤銷的訂單")

    @staticmethod
    def _show_portfolio_rebalance_form() -> None:
        """顯示投資組合調整表單"""
        st.write("### 投資組合調整")

        # 目標配置
        st.write("設定目標配置：")

        target_allocation = {
            "2330.TW": st.slider("台積電 (%)", 0, 50, 20),
            "2317.TW": st.slider("鴻海 (%)", 0, 30, 15),
            "AAPL": st.slider("蘋果 (%)", 0, 30, 25),
            "MSFT": st.slider("微軟 (%)", 0, 30, 20),
            "現金": st.slider("現金 (%)", 0, 50, 20),
        }

        total_allocation = sum(target_allocation.values())

        if total_allocation != 100:
            st.warning(f"總配置比例為 {total_allocation}%，請調整至 100%")
        else:
            if st.button("執行投資組合調整", type="primary"):
                st.success("投資組合調整指令已提交")

    @staticmethod
    def _show_risk_balance_form() -> None:
        """顯示風險平衡表單"""
        st.write("### 風險平衡")

        # 風險平衡選項
        balance_method = st.selectbox(
            "平衡方法", ["等權重", "風險平價", "最小變異數", "最大夏普比率"]
        )

        # 約束條件
        st.write("約束條件：")
        max_weight = st.slider("單一資產最大權重 (%)", 5, 50, 20)
        min_weight = st.slider("單一資產最小權重 (%)", 0, 10, 2)

        if st.button("執行風險平衡", type="primary"):
            st.success(f"使用 {balance_method} 方法執行風險平衡")

    @staticmethod
    def trading_mode_switcher(current_mode: str = "模擬") -> str:
        """
        交易模式切換器

        Args:
            current_mode: 當前模式

        Returns:
            選擇的模式
        """
        st.subheader("交易模式")

        mode = st.radio(
            "選擇交易模式",
            ["模擬交易", "實盤交易"],
            index=0 if current_mode == "模擬" else 1,
            horizontal=True,
        )

        if mode == "實盤交易":
            st.warning("⚠️ 您正在切換到實盤交易模式，所有訂單將使用真實資金執行！")

            # 安全確認
            confirm = st.checkbox("我確認要切換到實盤交易模式")

            if not confirm:
                mode = "模擬交易"
                st.info("請確認後才能切換到實盤交易模式")

        # 顯示當前模式狀態
        if mode == "模擬交易":
            st.success("🎮 當前為模擬交易模式")
        else:
            st.error("💰 當前為實盤交易模式")

        return mode
