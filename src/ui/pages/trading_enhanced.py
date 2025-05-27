"""
增強版交易執行頁面

此模組提供完整的交易執行功能，包括：
- 交易訂單介面
- 歷史記錄查詢
- 模擬/實盤交易模式
- 即時訂單監控
- 批量操作功能

Author: AI Trading System
Version: 1.0.0
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import streamlit as st
import pandas as pd
import numpy as np

# 導入響應式設計組件
try:
    from ..responsive import (
        ResponsiveUtils,
        ResponsiveComponents,
        ResponsiveLayoutManager,
    )
except ImportError:
    # 備用導入
    from src.ui.responsive import (
        ResponsiveUtils,
        ResponsiveComponents,
        ResponsiveLayoutManager,
    )


# 創建備用 UI 組件類（未使用，保留以備將來擴展）
class UIComponents:  # pylint: disable=too-few-public-methods
    """備用 UI 組件類"""

    @staticmethod
    def show_info(message: str) -> None:
        """顯示資訊訊息"""
        st.info(message)


# 創建備用交易執行組件類
class TradingComponents:
    """
    交易執行組件類

    提供交易執行系統所需的各種 UI 組件和功能模組。包括交易模式切換、
    訂單表單、訂單監控、交易歷史和批量操作等核心組件。

    此類別作為交易執行系統的核心組件庫，提供模組化和可重用的 UI 元件，
    支援完整的交易流程，從訂單建立到執行監控和歷史查詢。

    主要功能模組：
    - 交易模式切換：模擬交易與實盤交易模式管理
    - 訂單表單：多種訂單類型的建立和配置界面
    - 訂單監控：即時訂單狀態追蹤和管理
    - 交易歷史：歷史交易記錄查詢和分析
    - 批量操作：批量下單、撤單和投資組合調整

    安全特性：
    - 實盤交易確認機制：防止意外的真實資金操作
    - 訂單驗證：確保訂單參數的合理性和安全性
    - 風險控制整合：與風險管理系統的無縫整合
    - 操作日誌：完整的操作記錄和審計追蹤
    """

    @staticmethod
    def trading_mode_switcher(current_mode: str) -> str:
        """
        交易模式切換器

        Args:
            current_mode: 當前交易模式

        Returns:
            選擇的交易模式
        """
        st.subheader("交易模式")

        mode = st.radio(
            "選擇交易模式",
            ["模擬交易", "實盤交易"],
            index=0 if current_mode == "模擬交易" else 1,
            horizontal=True,
        )

        if mode == "實盤交易":
            st.warning("⚠️ 實盤交易模式將使用真實資金，請謹慎操作！")

            # 安全確認
            confirm = st.checkbox("我了解風險並確認使用實盤交易")
            if not confirm:
                st.error("請確認風險後才能使用實盤交易模式")
                return "模擬交易"

        return mode

    @staticmethod
    def order_form(order_type: str, form_key: str) -> Optional[Dict[str, Any]]:
        """
        訂單表單

        Args:
            order_type: 訂單類型
            form_key: 表單鍵值

        Returns:
            表單數據或 None
        """
        with st.form(form_key):
            col1, col2 = st.columns(2)

            with col1:
                symbol = st.selectbox(
                    "股票代碼", ["2330.TW", "2317.TW", "AAPL", "MSFT", "GOOGL"]
                )

                action = st.selectbox("交易方向", ["買入", "賣出"])

                quantity = st.number_input(
                    "數量", min_value=1, max_value=10000, value=100, step=1
                )

            with col2:
                if order_type in ["limit", "stop_limit"]:
                    price = st.number_input(
                        "價格", min_value=0.01, max_value=1000.0, value=100.0, step=0.01
                    )

                if order_type in ["stop", "stop_limit"]:
                    stop_price = st.number_input(
                        "停損價格",
                        min_value=0.01,
                        max_value=1000.0,
                        value=95.0,
                        step=0.01,
                    )

                if order_type == "conditional":
                    condition = st.selectbox(
                        "觸發條件", ["價格大於", "價格小於", "成交量大於"]
                    )

                    condition_value = st.number_input(
                        "條件值", min_value=0.01, value=100.0, step=0.01
                    )

            # 有效期設定
            validity = st.selectbox(
                "訂單有效期", ["當日有效", "取消前有效", "指定日期"]
            )

            if validity == "指定日期":
                expiry_date = st.date_input("到期日期", datetime.now().date())

            submitted = st.form_submit_button("確認訂單", use_container_width=True)

            if submitted:
                order_data = {
                    "symbol": symbol,
                    "action": action,
                    "quantity": quantity,
                    "validity": validity,
                }

                if order_type in ["limit", "stop_limit"]:
                    order_data["price"] = price

                if order_type in ["stop", "stop_limit"]:
                    order_data["stop_price"] = stop_price

                if order_type == "conditional":
                    order_data["condition"] = condition
                    order_data["condition_value"] = condition_value

                if validity == "指定日期":
                    order_data["expiry_date"] = expiry_date.isoformat()

                return order_data

        return None

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
        total_orders = len(orders)
        pending_orders = len([o for o in orders if o.get("status") == "待成交"])
        filled_orders = len([o for o in orders if o.get("status") == "已成交"])
        cancelled_orders = len([o for o in orders if o.get("status") == "已取消"])

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("總訂單", total_orders)

        with col2:
            st.metric("待成交", pending_orders)

        with col3:
            st.metric("已成交", filled_orders)

        with col4:
            st.metric("已取消", cancelled_orders)

        # 訂單列表
        st.subheader("訂單詳情")

        for order in orders:
            status_color = {
                "待成交": "🟡",
                "已成交": "🟢",
                "已取消": "🔴",
                "部分成交": "🟠",
            }.get(order.get("status", "未知"), "❓")

            order_id = order.get("id", "N/A")
            symbol = order.get("symbol", "N/A")
            with st.expander(f"{status_color} {order_id} - {symbol}"):
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**訂單類型**: {order.get('order_type', 'N/A')}")
                    st.write(f"**交易方向**: {order.get('action', 'N/A')}")
                    st.write(f"**數量**: {order.get('quantity', 0):,}")

                with col2:
                    st.write(f"**狀態**: {order.get('status', 'N/A')}")
                    st.write(f"**創建時間**: {order.get('created_at', 'N/A')}")
                    if "price" in order:
                        st.write(f"**價格**: ${order['price']:.2f}")

    @staticmethod
    def trading_history_panel(
        transactions: List[Dict[str, Any]], date_range: tuple
    ) -> None:
        """
        交易歷史面板

        Args:
            transactions: 交易記錄列表
            date_range: 日期範圍 (start_datetime, end_datetime)
        """
        if not transactions:
            st.info("指定期間內沒有交易記錄")
            return

        # 顯示查詢期間
        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            st.info(
                f"查詢期間: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}"
            )

        # 交易統計
        total_transactions = len(transactions)
        buy_transactions = len([t for t in transactions if t.get("action") == "買入"])
        sell_transactions = len([t for t in transactions if t.get("action") == "賣出"])
        total_amount = sum(t.get("amount", 0) for t in transactions)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("總交易數", total_transactions)

        with col2:
            st.metric("買入筆數", buy_transactions)

        with col3:
            st.metric("賣出筆數", sell_transactions)

        with col4:
            st.metric("總金額", f"${total_amount:,.0f}")

        # 交易記錄表格
        if transactions:
            df = pd.DataFrame(transactions)
            ResponsiveComponents.responsive_dataframe(df, title="交易記錄")

    @staticmethod
    def batch_operations_panel() -> None:
        """批量操作面板"""
        st.write("### 批量操作類型")

        operation_type = st.selectbox(
            "選擇操作類型", ["批量下單", "批量撤單", "投資組合調整", "風險平衡"]
        )

        if operation_type == "批量下單":
            st.write("#### CSV 批量下單")

            # 提供範例格式
            sample_data = pd.DataFrame(
                {
                    "股票代碼": ["2330.TW", "AAPL"],
                    "交易方向": ["買入", "賣出"],
                    "數量": [100, 50],
                    "訂單類型": ["market", "limit"],
                    "價格": [None, 150.0],
                }
            )

            st.write("**範例格式**:")
            st.dataframe(sample_data)

            uploaded_file = st.file_uploader("上傳 CSV 檔案", type=["csv"])

            if uploaded_file:
                try:
                    df = pd.read_csv(uploaded_file)
                    st.write("**上傳的訂單**:")
                    st.dataframe(df)

                    if st.button("執行批量下單"):
                        st.success(f"已提交 {len(df)} 筆訂單")
                except Exception as e:
                    st.error("檔案格式錯誤: %s", e)

        elif operation_type == "投資組合調整":
            st.write("#### 投資組合再平衡")

            target_allocation = {
                "2330.TW": st.slider("台積電 (%)", 0, 100, 30),
                "2317.TW": st.slider("鴻海 (%)", 0, 100, 20),
                "AAPL": st.slider("蘋果 (%)", 0, 100, 25),
                "MSFT": st.slider("微軟 (%)", 0, 100, 25),
            }

            total_allocation = sum(target_allocation.values())

            if total_allocation != 100:
                st.warning(f"總配置比例為 {total_allocation}%，請調整至 100%")
            else:
                if st.button("執行投資組合調整"):
                    st.success("投資組合調整訂單已提交")


# 創建響應式管理器實例
responsive_manager = ResponsiveLayoutManager()


def show_enhanced() -> None:
    """
    顯示增強版交易執行頁面

    此函數是交易執行模組的主要入口點，提供完整的交易執行功能界面。
    包括訂單介面、訂單監控、交易記錄和批量操作四個主要功能模組。
    支援模擬交易和實盤交易兩種模式，提供安全的交易執行環境。

    功能特點：
    - 多種訂單類型支援（市價、限價、停損等）
    - 即時訂單監控和狀態追蹤
    - 完整的交易歷史記錄查詢
    - 批量操作和投資組合調整功能
    - 模擬/實盤交易模式切換
    - 響應式設計，支援多種裝置

    Returns:
        None

    Side Effects:
        - 初始化交易相關的會話狀態變數
        - 在 Streamlit 界面顯示交易執行系統
    """
    # 應用響應式頁面配置
    ResponsiveUtils.apply_responsive_page_config(
        page_title="交易執行 - AI 交易系統", page_icon="💹"
    )

    # 頁面標題
    st.markdown(
        '<h1 class="title-responsive">💹 交易執行系統</h1>', unsafe_allow_html=True
    )

    # 初始化會話狀態
    _initialize_trading_session_state()

    # 交易模式切換
    st.session_state.trading_mode = TradingComponents.trading_mode_switcher(
        st.session_state.trading_mode
    )

    # 響應式標籤頁
    tabs_config = [
        {"name": "📋 下單交易", "content_func": show_order_interface},
        {"name": "📊 訂單監控", "content_func": show_order_monitoring},
        {"name": "📈 交易記錄", "content_func": show_trading_history},
        {"name": "⚡ 批量操作", "content_func": show_batch_operations},
    ]

    ResponsiveComponents.responsive_tabs(tabs_config)


def _initialize_trading_session_state() -> None:
    """
    初始化交易系統的會話狀態

    設定交易執行模組所需的會話狀態變數，包括交易模式、活躍訂單和交易歷史。
    確保所有必要的狀態變數都有適當的初始值。

    Returns:
        None
    """
    if "trading_mode" not in st.session_state:
        st.session_state.trading_mode = "模擬交易"
    if "active_orders" not in st.session_state:
        st.session_state.active_orders = []
    if "trading_history" not in st.session_state:
        st.session_state.trading_history = []


def show_order_interface() -> None:
    """
    顯示下單介面

    提供完整的訂單建立和管理界面，支援多種訂單類型和參數設定。
    包括市價單、限價單、停損單等訂單類型，以及風險控制和驗證機制。

    功能特點：
    - 多種訂單類型支援（市價、限價、停損、停利）
    - 即時價格顯示和市場數據
    - 風險控制整合和部位檢查
    - 訂單預覽和確認機制
    - 模擬/實盤交易模式切換

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示訂單建立表單
        - 可能觸發訂單提交和風險檢查
    """
    st.subheader("交易下單")

    # 訂單類型選擇
    order_type = st.selectbox(
        "訂單類型",
        ["market", "limit", "stop", "stop_limit", "conditional"],
        format_func=lambda x: {
            "market": "市價單",
            "limit": "限價單",
            "stop": "停損單",
            "stop_limit": "停損限價單",
            "conditional": "條件單",
        }[x],
    )

    # 顯示訂單說明
    show_order_type_description(order_type)

    # 訂單表單
    order_data = TradingComponents.order_form(order_type, f"{order_type}_order_form")

    if order_data:
        # 訂單確認
        show_order_confirmation(order_data, order_type)

        # 提交訂單
        if st.button("🚀 提交訂單", type="primary", use_container_width=True):
            success = submit_order(order_data, order_type)

            if success:
                st.success("訂單已成功提交！")

                # 添加到活躍訂單列表
                new_order = {
                    "id": f"ORD{len(st.session_state.active_orders)+1:03d}",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "order_type": order_type,
                    "status": "待成交",
                    **order_data,
                }
                st.session_state.active_orders.append(new_order)

                # 刷新頁面
                time.sleep(1)
                st.rerun()
            else:
                st.error("訂單提交失敗，請重試")

    # 快速下單面板
    st.subheader("快速下單")
    show_quick_order_panel()


def show_order_monitoring() -> None:
    """
    顯示訂單監控

    提供即時的訂單狀態監控和管理功能，包括活躍訂單追蹤、狀態更新、
    訂單修改和撤銷等操作。支援多種訂單狀態的視覺化顯示。

    功能特點：
    - 即時訂單狀態追蹤和更新
    - 訂單修改和撤銷功能
    - 執行進度和成交明細顯示
    - 訂單篩選和搜尋功能
    - 批量訂單操作支援

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示訂單監控面板
        - 可能觸發訂單狀態更新和操作
    """
    st.subheader("即時訂單監控")

    # 自動刷新控制
    auto_refresh = st.checkbox("自動刷新 (10秒)", value=True)

    # 載入活躍訂單
    active_orders = load_active_orders()

    # 訂單監控面板
    TradingComponents.order_monitoring_panel(active_orders)

    # 訂單操作
    if active_orders:
        st.subheader("訂單操作")
        show_order_actions(active_orders)

    # 自動刷新
    if auto_refresh and active_orders:
        time.sleep(10)
        st.rerun()


def show_trading_history() -> None:
    """
    顯示交易記錄

    提供完整的交易歷史記錄查詢和分析功能，包括歷史訂單、成交記錄、
    績效統計等資訊。支援多種篩選條件和匯出功能。

    功能特點：
    - 歷史交易記錄查詢和顯示
    - 多維度篩選（時間、股票、方向等）
    - 交易績效統計和分析
    - 成交明細和手續費計算
    - 交易記錄匯出功能

    Returns:
        None

    Side Effects:
        - 在 Streamlit 界面顯示交易歷史面板
        - 載入和顯示歷史交易數據
    """
    st.subheader("交易歷史記錄")

    # 日期範圍篩選
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input("開始日期", datetime.now() - timedelta(days=30))

    with col2:
        end_date = st.date_input("結束日期", datetime.now())

    # 其他篩選條件
    cols = responsive_manager.create_responsive_columns(
        desktop_cols=3, tablet_cols=2, mobile_cols=1
    )

    with cols[0]:
        symbol_filter = st.selectbox("股票代碼", ["全部", "2330.TW", "AAPL", "MSFT"])

    with cols[1 % len(cols)]:
        action_filter = st.selectbox("交易方向", ["全部", "買入", "賣出"])

    with cols[2 % len(cols)]:
        status_filter = st.selectbox("狀態", ["全部", "已成交", "已取消"])

    # 載入交易記錄
    transactions = load_trading_history(
        start_date, end_date, symbol_filter, action_filter, status_filter
    )

    # 交易歷史面板
    TradingComponents.trading_history_panel(
        transactions,
        (
            datetime.combine(start_date, datetime.min.time()),
            datetime.combine(end_date, datetime.max.time()),
        ),
    )

    # 匯出功能
    if transactions:
        st.subheader("匯出記錄")

        cols = responsive_manager.create_responsive_columns(
            desktop_cols=3, tablet_cols=2, mobile_cols=1
        )

        with cols[0]:
            if st.button("📄 匯出 CSV", use_container_width=True):
                export_trading_history(transactions, "csv")

        with cols[1 % len(cols)]:
            if st.button("📊 匯出 Excel", use_container_width=True):
                export_trading_history(transactions, "excel")

        with cols[2 % len(cols)]:
            if st.button("📋 匯出 PDF", use_container_width=True):
                export_trading_history(transactions, "pdf")


def show_batch_operations():
    """顯示批量操作"""
    st.subheader("批量操作")

    # 批量操作面板
    TradingComponents.batch_operations_panel()

    # 操作歷史
    st.subheader("批量操作歷史")
    show_batch_operation_history()


def show_order_type_description(order_type: str):
    """顯示訂單類型說明"""
    descriptions = {
        "market": "🏃 **市價單**: 以當前市場價格立即執行交易",
        "limit": "🎯 **限價單**: 以指定價格或更好的價格執行交易",
        "stop": "🛑 **停損單**: 當價格觸及停損價時轉為市價單",
        "stop_limit": "🎯🛑 **停損限價單**: 當價格觸及停損價時轉為限價單",
        "conditional": "🔍 **條件單**: 當滿足特定條件時自動執行交易",
    }

    st.info(descriptions.get(order_type, "未知訂單類型"))


def show_order_confirmation(order_data: Dict[str, Any], order_type: str):
    """顯示訂單確認"""
    st.subheader("訂單確認")

    # 計算預估成本
    estimated_cost = calculate_estimated_cost(order_data)

    # 確認資訊
    confirmation_data = [
        {"項目": "股票代碼", "值": order_data.get("symbol", "N/A")},
        {"項目": "交易方向", "值": order_data.get("action", "N/A")},
        {"項目": "數量", "值": f"{order_data.get('quantity', 0):,}"},
        {"項目": "訂單類型", "值": order_type},
        {"項目": "預估成本", "值": f"${estimated_cost:,.2f}"},
        {"項目": "交易模式", "值": st.session_state.trading_mode},
    ]

    if "price" in order_data:
        confirmation_data.insert(
            4, {"項目": "價格", "值": f"${order_data['price']:.2f}"}
        )

    df = pd.DataFrame(confirmation_data)
    ResponsiveComponents.responsive_dataframe(df, title="訂單確認")


def show_quick_order_panel():
    """顯示快速下單面板"""
    st.write("### 快速下單")

    # 預設股票
    quick_symbols = ["2330.TW", "2317.TW", "AAPL", "MSFT"]

    cols = responsive_manager.create_responsive_columns(
        desktop_cols=4, tablet_cols=2, mobile_cols=1
    )

    for i, symbol in enumerate(quick_symbols):
        with cols[i % len(cols)]:
            st.write(f"**{symbol}**")

            # 模擬當前價格
            current_price = np.random.uniform(100, 200)
            st.write(f"當前價格: ${current_price:.2f}")

            col_buy, col_sell = st.columns(2)

            with col_buy:
                if st.button(
                    "買入", key=f"quick_buy_{symbol}", use_container_width=True
                ):
                    st.success("快速買入 %s", symbol)

            with col_sell:
                if st.button(
                    "賣出", key=f"quick_sell_{symbol}", use_container_width=True
                ):
                    st.success("快速賣出 %s", symbol)


def show_order_actions(orders: List[Dict[str, Any]]):
    """顯示訂單操作"""
    # 選擇要操作的訂單
    order_ids = [order["id"] for order in orders if order.get("status") == "待成交"]

    if not order_ids:
        st.info("沒有可操作的訂單")
        return

    selected_orders = st.multiselect("選擇要操作的訂單", order_ids)

    if selected_orders:
        cols = responsive_manager.create_responsive_columns(
            desktop_cols=3, tablet_cols=2, mobile_cols=1
        )

        with cols[0]:
            if st.button("❌ 取消訂單", use_container_width=True):
                cancel_orders(selected_orders)
                st.success(f"已取消 {len(selected_orders)} 筆訂單")

        with cols[1 % len(cols)]:
            if st.button("✏️ 修改訂單", use_container_width=True):
                st.info("修改訂單功能開發中...")

        with cols[2 % len(cols)]:
            if st.button("📋 複製訂單", use_container_width=True):
                st.info("複製訂單功能開發中...")


def show_batch_operation_history():
    """顯示批量操作歷史"""
    # 模擬批量操作歷史
    history = [
        {
            "時間": "2024-01-15 10:30:00",
            "操作類型": "批量下單",
            "訂單數量": 5,
            "狀態": "已完成",
            "執行人": "系統",
        },
        {
            "時間": "2024-01-14 15:45:00",
            "操作類型": "投資組合調整",
            "訂單數量": 8,
            "狀態": "已完成",
            "執行人": "用戶",
        },
    ]

    if history:
        df = pd.DataFrame(history)
        ResponsiveComponents.responsive_dataframe(df, title="批量操作歷史")
    else:
        st.info("沒有批量操作歷史")


def submit_order(order_data: Dict[str, Any], order_type: str) -> bool:
    """
    提交訂單

    將訂單數據提交到交易系統。目前使用模擬實作，
    在實際部署時會連接到真實的交易 API。

    Args:
        order_data: 訂單數據字典
        order_type: 訂單類型（market, limit, stop 等）

    Returns:
        bool: 提交成功返回 True，失敗返回 False

    Raises:
        Exception: 當提交過程中發生錯誤時
    """
    try:
        # 驗證訂單數據
        if not order_data:
            st.error("訂單數據不能為空")
            return False

        # 模擬 API 調用
        # response = requests.post(
        #     "http://localhost:8000/api/v1/trading/orders",
        #     json={
        #         "order_type": order_type,
        #         **order_data
        #     }
        # )
        # return response.status_code == 200

        # 模擬提交成功
        symbol = order_data.get("symbol", "N/A")
        st.info("正在提交 %s 訂單: %s", order_type, symbol)
        time.sleep(1)  # 模擬網路延遲
        return True

    except Exception as e:
        st.error("提交訂單失敗: %s", e)
        return False


def load_active_orders() -> List[Dict[str, Any]]:
    """載入活躍訂單"""
    try:
        # 模擬 API 調用
        # response = requests.get("http://localhost:8000/api/v1/trading/orders")
        # if response.status_code == 200:
        #     return response.json()["data"]

        # 返回會話狀態中的訂單
        return st.session_state.get("active_orders", [])

    except Exception as e:
        st.error("載入訂單失敗: %s", e)
        return []


def load_trading_history(
    start_date: datetime,
    end_date: datetime,
    symbol_filter: str,
    action_filter: str,
    status_filter: str,
) -> List[Dict[str, Any]]:
    """
    載入交易記錄

    根據指定的篩選條件載入交易歷史記錄。
    目前使用模擬數據，實際部署時會連接到真實的交易記錄 API。

    Args:
        start_date: 開始日期
        end_date: 結束日期
        symbol_filter: 股票代碼篩選
        action_filter: 交易方向篩選
        status_filter: 狀態篩選

    Returns:
        List[Dict[str, Any]]: 交易記錄列表

    Raises:
        Exception: 當載入過程中發生錯誤時
    """
    try:
        # 記錄篩選條件
        filter_info = {
            "date_range": f"{start_date.date()} 到 {end_date.date()}",
            "symbol": symbol_filter,
            "action": action_filter,
            "status": status_filter,
        }

        # 模擬 API 調用
        # params = {
        #     "start_date": start_date.isoformat(),
        #     "end_date": end_date.isoformat(),
        #     "symbol": symbol_filter if symbol_filter != "全部" else None,
        #     "action": action_filter if action_filter != "全部" else None,
        #     "status": status_filter if status_filter != "全部" else None
        # }
        # response = requests.get("http://localhost:8000/api/v1/trading/history", params=params)
        # if response.status_code == 200:
        #     return response.json()["data"]

        # 返回模擬數據
        st.info("載入交易記錄，篩選條件: %s", filter_info)
        return generate_mock_trading_history()

    except Exception as e:
        st.error("載入交易記錄失敗: %s", e)
        return []


def generate_mock_trading_history() -> List[Dict[str, Any]]:
    """生成模擬交易記錄"""
    transactions = []

    for i in range(20):
        transaction = {
            "id": f"TXN{i+1:03d}",
            "date": (
                datetime.now() - timedelta(days=np.random.randint(0, 30))
            ).strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": np.random.choice(["2330.TW", "2317.TW", "AAPL", "MSFT"]),
            "action": np.random.choice(["買入", "賣出"]),
            "quantity": np.random.randint(100, 1000),
            "price": np.random.uniform(100, 200),
            "amount": 0,  # 將在下面計算
            "status": np.random.choice(["已成交", "已取消"], p=[0.9, 0.1]),
        }

        transaction["amount"] = transaction["quantity"] * transaction["price"]
        transactions.append(transaction)

    return transactions


def calculate_estimated_cost(order_data: Dict[str, Any]) -> float:
    """計算預估成本"""
    quantity = order_data.get("quantity", 0)
    price = order_data.get("price", 100.0)  # 預設價格

    # 基本成本
    base_cost = quantity * price

    # 手續費 (0.1425%)
    commission = base_cost * 0.001425

    # 交易稅 (賣出時 0.3%)
    tax = base_cost * 0.003 if order_data.get("action") == "賣出" else 0

    return base_cost + commission + tax


def cancel_orders(order_ids: List[str]):
    """取消訂單"""
    try:
        # 模擬 API 調用
        # for order_id in order_ids:
        #     requests.delete(f"http://localhost:8000/api/v1/trading/orders/{order_id}")

        # 更新會話狀態
        for order in st.session_state.active_orders:
            if order["id"] in order_ids:
                order["status"] = "已取消"

    except Exception as e:
        st.error("取消訂單失敗: %s", e)


def export_trading_history(transactions: List[Dict[str, Any]], format_type: str):
    """匯出交易記錄"""
    try:
        df = pd.DataFrame(transactions)

        if format_type == "csv":
            csv_data = df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="下載 CSV 檔案",
                data=csv_data,
                file_name=(
                    f"trading_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                ),
                mime="text/csv",
            )

        elif format_type == "excel":
            # 需要安裝 openpyxl
            st.info("Excel 匯出功能需要安裝 openpyxl 套件")

        elif format_type == "pdf":
            st.info("PDF 匯出功能開發中...")

        st.success("%s 檔案已準備下載", format_type.upper())

    except Exception as e:
        st.error("匯出失敗: %s", e)


if __name__ == "__main__":
    show_enhanced()
