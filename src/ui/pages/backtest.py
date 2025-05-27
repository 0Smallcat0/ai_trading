"""
回測系統頁面

此模組實現完整的回測系統功能，包括：
- 回測參數設定和驗證
- 回測執行控制和進度管理
- 績效分析與視覺化
- 交易記錄管理和查詢
- 報表匯出功能

Example:
    使用方式：
    ```python
    from src.ui.pages.backtest import show
    show()  # 顯示回測系統主頁面
    ```

Note:
    此模組依賴於 BacktestService 來執行實際的回測邏輯。
    所有回測結果會儲存在 session state 中以便在不同標籤頁間共享。
"""

import time
from datetime import datetime, timedelta

import streamlit as st
import pandas as pd

# 導入回測服務
from ...core.backtest_service import BacktestService, BacktestConfig


# 初始化回測服務
@st.cache_resource
def get_backtest_service():
    """獲取回測服務實例。

    使用 Streamlit 的 cache_resource 裝飾器來確保服務實例在會話間共享，
    避免重複初始化造成的效能問題。

    Returns:
        BacktestService: 回測服務實例，提供完整的回測功能

    Example:
        ```python
        service = get_backtest_service()
        strategies = service.get_available_strategies()
        ```

    Note:
        此函數會被 Streamlit 快取，確保在整個應用程式生命週期中
        只會建立一個 BacktestService 實例。
    """
    return BacktestService()


def show():
    """顯示回測系統主頁面。

    建立完整的回測系統使用者介面，包含五個主要功能標籤頁：
    參數設定、執行控制、績效分析、交易記錄和報表匯出。

    此函數會初始化必要的 session state 變數，並建立標籤頁結構
    來組織不同的回測功能模組。

    Example:
        ```python
        from src.ui.pages.backtest import show
        show()  # 在 Streamlit 應用中顯示回測系統
        ```

    Note:
        - 使用 session state 來維護回測狀態和當前回測 ID
        - 所有子功能都透過獨立的函數來實現，保持程式碼模組化
        - 標籤頁設計讓使用者能夠輕鬆在不同功能間切換
    """
    st.header("📊 回測系統")

    # 初始化 session state
    if "backtest_tab" not in st.session_state:
        st.session_state.backtest_tab = 0
    if "current_backtest_id" not in st.session_state:
        st.session_state.current_backtest_id = None

    # 創建標籤頁
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["⚙️ 參數設定", "🚀 執行控制", "📈 績效分析", "📋 交易記錄", "📄 報表匯出"]
    )

    with tab1:
        show_parameter_settings()

    with tab2:
        show_execution_control()

    with tab3:
        show_performance_analysis()

    with tab4:
        show_trade_records()

    with tab5:
        show_report_export()


def _render_strategy_selection(strategies):
    """渲染策略選擇區塊。

    Args:
        strategies (List[Dict]): 可用策略清單

    Returns:
        Dict: 選中的策略資訊
    """
    strategy_options = [(s["id"], f"{s['name']} ({s['type']})") for s in strategies]
    selected_strategy_idx = st.selectbox(
        "選擇策略",
        options=range(len(strategy_options)),
        format_func=lambda x: strategy_options[x][1],
        help="選擇要進行回測的交易策略",
    )

    selected_strategy = strategies[selected_strategy_idx]

    # 顯示策略詳情
    with st.expander("策略詳情"):
        st.write(f"**描述**: {selected_strategy['description']}")
        st.write(f"**類型**: {selected_strategy['type']}")

        if "parameters" in selected_strategy:
            st.write("**參數設定**:")
            for param, config in selected_strategy["parameters"].items():
                st.write(f"- {param}: {config}")

    return selected_strategy


def _render_time_period_selection():
    """渲染時間期間選擇區塊。

    Returns:
        Tuple[datetime.date, datetime.date]: 開始日期和結束日期
    """
    st.markdown("#### 📅 回測期間")

    # 預設期間選項
    PERIOD_OPTIONS = {
        "自定義": None,
        "最近1年": 365,
        "最近3年": 365 * 3,
        "最近5年": 365 * 5,
        "最近10年": 365 * 10,
    }

    selected_period = st.selectbox("預設期間", options=list(PERIOD_OPTIONS.keys()))

    if PERIOD_OPTIONS[selected_period]:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=PERIOD_OPTIONS[selected_period])
    else:
        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input(
                "開始日期",
                value=datetime.now().date() - timedelta(days=365),
                max_value=datetime.now().date(),
            )
        with col_end:
            end_date = st.date_input(
                "結束日期",
                value=datetime.now().date(),
                min_value=start_date,
                max_value=datetime.now().date(),
            )

    return start_date, end_date


def _render_stock_selection(stocks):
    """渲染股票選擇區塊。

    Args:
        stocks (List[Dict]): 可用股票清單

    Returns:
        List[str]: 選中的股票代碼清單
    """
    col1, col2 = st.columns([2, 1])

    with col1:
        # 按交易所分組
        exchanges = sorted(list(set(s["exchange"] for s in stocks)))
        selected_exchange = st.selectbox("交易所", options=["全部"] + exchanges)

        # 過濾股票
        if selected_exchange == "全部":
            filtered_stocks = stocks
        else:
            filtered_stocks = [s for s in stocks if s["exchange"] == selected_exchange]

        # 股票多選
        stock_options = [f"{s['symbol']} - {s['name']}" for s in filtered_stocks]
        selected_stocks = st.multiselect(
            "選擇股票",
            options=stock_options,
            default=stock_options[:3] if len(stock_options) >= 3 else stock_options,
            help="選擇要進行回測的股票，可多選",
        )

        # 提取股票代碼
        selected_symbols = [
            stock_option.split(" - ")[0] for stock_option in selected_stocks
        ]

    with col2:
        st.markdown("#### 📊 選擇統計")
        st.metric("已選股票數", len(selected_symbols))

        if selected_symbols:
            # 按交易所統計
            exchange_counts = {}
            for symbol in selected_symbols:
                stock = next((s for s in stocks if s["symbol"] == symbol), None)
                if stock:
                    exchange = stock["exchange"]
                    exchange_counts[exchange] = exchange_counts.get(exchange, 0) + 1

            for exchange, count in exchange_counts.items():
                st.write(f"- {exchange}: {count}")

    return selected_symbols


def _render_financial_settings():
    """渲染資金設定區塊。

    Returns:
        Tuple[float, float, float, float]: 初始資金、手續費、稅率、滑點率
    """
    st.markdown("### 💰 資金設定")

    col1, col2, col3 = st.columns(3)

    with col1:
        initial_capital = st.number_input(
            "初始資金",
            min_value=10000,
            max_value=100000000,
            value=1000000,
            step=10000,
            help="回測開始時的資金額度",
        )

    with col2:
        commission = (
            st.number_input(
                "手續費率 (%)",
                min_value=0.0,
                max_value=1.0,
                value=0.1425,
                step=0.001,
                format="%.4f",
                help="每筆交易的手續費率",
            )
            / 100
        )

        tax = (
            st.number_input(
                "證券交易稅 (%)",
                min_value=0.0,
                max_value=1.0,
                value=0.3,
                step=0.01,
                format="%.3f",
                help="賣出時的證券交易稅率",
            )
            / 100
        )

    with col3:
        slippage = (
            st.number_input(
                "滑點率 (%)",
                min_value=0.0,
                max_value=1.0,
                value=0.1,
                step=0.01,
                format="%.3f",
                help="交易時的價格滑點",
            )
            / 100
        )

    return initial_capital, commission, tax, slippage


def _render_risk_management():
    """渲染風險管理設定區塊。

    Returns:
        Tuple[float, float, float]: 最大持倉比例、停損比例、停利比例
    """
    st.markdown("### ⚠️ 風險管理")

    col1, col2, col3 = st.columns(3)

    with col1:
        max_position_size = (
            st.slider(
                "最大持倉比例 (%)",
                min_value=1,
                max_value=100,
                value=20,
                help="單一股票的最大持倉比例",
            )
            / 100
        )

    with col2:
        stop_loss = (
            st.number_input(
                "停損比例 (%)",
                min_value=0.0,
                max_value=50.0,
                value=5.0,
                step=0.1,
                help="自動停損的虧損比例",
            )
            / 100
        )

    with col3:
        take_profit = (
            st.number_input(
                "停利比例 (%)",
                min_value=0.0,
                max_value=100.0,
                value=10.0,
                step=0.1,
                help="自動停利的獲利比例",
            )
            / 100
        )

    return max_position_size, stop_loss, take_profit


def _validate_and_save_config(
    selected_strategy,
    selected_symbols,
    start_date,
    end_date,
    initial_capital,
    commission,
    tax,
    slippage,
    max_position_size,
    stop_loss,
    take_profit,
):
    """驗證並保存回測配置。

    Args:
        selected_strategy (Dict): 選中的策略
        selected_symbols (List[str]): 選中的股票代碼
        start_date (datetime.date): 開始日期
        end_date (datetime.date): 結束日期
        initial_capital (float): 初始資金
        commission (float): 手續費率
        tax (float): 稅率
        slippage (float): 滑點率
        max_position_size (float): 最大持倉比例
        stop_loss (float): 停損比例
        take_profit (float): 停利比例

    Returns:
        bool: 是否成功保存配置
    """
    # 驗證輸入
    if not selected_symbols:
        st.error("請至少選擇一個股票")
        return False

    if start_date >= end_date:
        st.error("開始日期必須早於結束日期")
        return False

    # 創建回測配置
    config = BacktestConfig(
        strategy_id=selected_strategy["id"],
        strategy_name=selected_strategy["name"],
        symbols=selected_symbols,
        start_date=datetime.combine(start_date, datetime.min.time()),
        end_date=datetime.combine(end_date, datetime.min.time()),
        initial_capital=initial_capital,
        commission=commission,
        slippage=slippage,
        tax=tax,
        max_position_size=max_position_size,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )

    # 驗證配置
    service = get_backtest_service()
    is_valid, error_msg = service.validate_backtest_config(config)

    if is_valid:
        # 保存到 session state
        st.session_state.backtest_config = config
        st.success("✅ 回測參數設定已保存！")
        st.info("請切換到「執行控制」標籤頁開始回測")
        return True
    else:
        st.error(f"❌ 參數驗證失敗: {error_msg}")
        return False


def _display_current_config():
    """顯示當前回測配置摘要。"""
    if hasattr(st.session_state, "backtest_config"):
        st.markdown("---")
        st.markdown("### 📋 當前設定")

        config = st.session_state.backtest_config

        col1, col2, col3 = st.columns(3)

        with col1:
            st.write(f"**策略**: {config.strategy_name}")
            st.write(f"**股票數量**: {len(config.symbols)}")
            st.write(f"**回測期間**: {(config.end_date - config.start_date).days} 天")

        with col2:
            st.write(f"**初始資金**: {config.initial_capital:,.0f}")
            st.write(f"**手續費率**: {config.commission:.4%}")
            st.write(f"**滑點率**: {config.slippage:.3%}")

        with col3:
            st.write(f"**最大持倉**: {config.max_position_size:.1%}")
            st.write(f"**停損比例**: {config.stop_loss:.1%}")
            st.write(f"**停利比例**: {config.take_profit:.1%}")


def show_parameter_settings():
    """顯示回測參數設定頁面。

    提供完整的回測參數設定介面，包括策略選擇、時間期間設定、
    標的選擇、資金設定和風險管理參數。使用者可以透過表單
    設定所有回測參數，並進行驗證後保存到 session state。

    主要功能包括：
    - 策略選擇和詳情顯示
    - 回測期間設定（預設期間或自定義）
    - 股票標的選擇（支援多選和交易所篩選）
    - 資金和交易成本設定
    - 風險管理參數設定
    - 參數驗證和保存

    Example:
        此函數通常在回測系統的參數設定標籤頁中被呼叫：
        ```python
        with tab1:
            show_parameter_settings()
        ```

    Note:
        - 所有參數會被封裝成 BacktestConfig 物件
        - 參數驗證失敗時會顯示錯誤訊息
        - 成功設定的參數會保存在 st.session_state.backtest_config
        - 支援即時顯示當前設定摘要
    """
    st.subheader("回測參數設定")

    service = get_backtest_service()

    # 獲取可用策略和股票
    strategies = service.get_available_strategies()
    stocks = service.get_available_stocks()

    with st.form("backtest_config_form"):
        st.markdown("### 📋 基本設定")

        col1, col2 = st.columns(2)

        with col1:
            selected_strategy = _render_strategy_selection(strategies)

        with col2:
            start_date, end_date = _render_time_period_selection()

        st.markdown("### 🎯 標的選擇")
        selected_symbols = _render_stock_selection(stocks)

        initial_capital, commission, tax, slippage = _render_financial_settings()
        max_position_size, stop_loss, take_profit = _render_risk_management()

        # 提交按鈕
        submitted = st.form_submit_button("💾 保存設定", type="primary")

        if submitted:
            _validate_and_save_config(
                selected_strategy,
                selected_symbols,
                start_date,
                end_date,
                initial_capital,
                commission,
                tax,
                slippage,
                max_position_size,
                stop_loss,
                take_profit,
            )

    # 顯示當前設定
    _display_current_config()


def show_execution_control():
    """顯示回測執行控制頁面。

    提供回測執行的控制介面，包括配置摘要顯示、回測啟動、
    進度監控、狀態管理和歷史記錄查看等功能。

    主要功能包括：
    - 顯示當前回測配置摘要
    - 啟動新的回測任務
    - 監控回測執行進度
    - 管理回測狀態（取消、重新開始）
    - 查看回測歷史記錄
    - 提供快速操作功能

    Returns:
        None: 如果沒有設定回測配置，會顯示警告並提前返回

    Example:
        此函數通常在回測系統的執行控制標籤頁中被呼叫：
        ```python
        with tab2:
            show_execution_control()
        ```

    Note:
        - 需要先在參數設定頁面完成配置才能使用
        - 支援即時進度更新和自動刷新
        - 提供回測狀態的完整生命週期管理
        - 包含錯誤處理和使用者友善的狀態提示
    """
    st.subheader("回測執行控制")

    service = get_backtest_service()

    # 檢查是否有配置
    if not hasattr(st.session_state, "backtest_config"):
        st.warning("⚠️ 請先在「參數設定」標籤頁完成回測參數設定")
        return

    config = st.session_state.backtest_config

    # 顯示配置摘要
    st.markdown("### 📋 回測配置摘要")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("策略", config.strategy_name)
        st.metric("股票數量", len(config.symbols))

    with col2:
        st.metric("初始資金", f"{config.initial_capital:,.0f}")
        st.metric("回測天數", f"{(config.end_date - config.start_date).days}")

    with col3:
        st.metric("手續費率", f"{config.commission:.4%}")
        st.metric("停損比例", f"{config.stop_loss:.1%}")

    with col4:
        st.metric("滑點率", f"{config.slippage:.3%}")
        st.metric("停利比例", f"{config.take_profit:.1%}")

    st.markdown("---")

    # 執行控制
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown("### 🚀 執行控制")

        # 檢查是否有正在運行的回測
        if st.session_state.current_backtest_id:
            status = service.get_backtest_status(st.session_state.current_backtest_id)

            if status["status"] in ["created", "running"]:
                st.info(f"📊 回測進行中: {status['message']}")

                # 顯示進度條
                progress = status.get("progress", 0)
                st.progress(progress / 100)
                st.write(f"進度: {progress:.1f}%")

                # 取消按鈕
                if st.button("⏹️ 取消回測", type="secondary"):
                    if service.cancel_backtest(st.session_state.current_backtest_id):
                        st.success("回測已取消")
                        st.session_state.current_backtest_id = None
                        st.rerun()
                    else:
                        st.error("取消回測失敗")

                # 自動刷新
                time.sleep(2)
                st.rerun()

            elif status["status"] == "completed":
                st.success("✅ 回測已完成！")
                st.info("請切換到「績效分析」標籤頁查看結果")

                if st.button("🔄 開始新回測"):
                    st.session_state.current_backtest_id = None
                    st.rerun()

            elif status["status"] == "failed":
                st.error(f"❌ 回測失敗: {status['message']}")

                if st.button("🔄 重新開始"):
                    st.session_state.current_backtest_id = None
                    st.rerun()

            elif status["status"] == "cancelled":
                st.warning("⚠️ 回測已取消")

                if st.button("🔄 重新開始"):
                    st.session_state.current_backtest_id = None
                    st.rerun()
        else:
            # 開始回測按鈕
            if st.button("🚀 開始回測", type="primary", use_container_width=True):
                try:
                    backtest_id = service.start_backtest(config)
                    st.session_state.current_backtest_id = backtest_id
                    st.success(f"✅ 回測已啟動！ID: {backtest_id}")
                    st.rerun()
                except (ValueError, RuntimeError) as e:
                    st.error(f"❌ 啟動回測失敗: {str(e)}")
                except ConnectionError as e:
                    st.error(f"❌ 連接服務失敗: {str(e)}")
                except Exception as e:
                    st.error(f"❌ 未知錯誤: {str(e)}")
                    st.exception(e)

    with col2:
        st.markdown("### 📊 回測歷史")

        # 獲取回測歷史
        backtest_list = service.get_backtest_list(limit=10)

        if backtest_list:
            for bt in backtest_list[:5]:  # 顯示最近5個
                status_emoji = {
                    "completed": "✅",
                    "running": "🔄",
                    "failed": "❌",
                    "cancelled": "⚠️",
                    "created": "📝",
                }.get(bt["status"], "❓")

                st.write(f"{status_emoji} {bt['strategy_name']}")
                st.caption(f"ID: {bt['id'][:8]}...")

                if bt["status"] == "completed" and bt.get("total_return"):
                    st.caption(f"報酬率: {bt['total_return']:.2f}%")
        else:
            st.info("尚無回測歷史")

    with col3:
        st.markdown("### ⚙️ 快速操作")

        if st.button("📋 查看所有回測", use_container_width=True):
            st.session_state.show_all_backtests = True

        if st.button("🗑️ 清理失敗回測", use_container_width=True):
            # 清理失敗的回測
            all_backtests = service.get_backtest_list()
            failed_backtests = [bt for bt in all_backtests if bt["status"] == "failed"]
            for bt in failed_backtests:
                service.delete_backtest(bt["id"])
            st.success(f"已清理 {len(failed_backtests)} 個失敗回測")


def show_performance_analysis():
    """顯示績效分析頁面。

    提供完整的回測績效分析介面，包括關鍵績效指標顯示、
    回測結果選擇和數據刷新功能。

    主要功能包括：
    - 選擇已完成的回測結果進行分析
    - 顯示關鍵績效指標（報酬率、夏普比率、最大回撤等）
    - 提供數據刷新功能
    - 處理無結果的情況

    Returns:
        None: 如果沒有已完成的回測結果，會顯示警告並提前返回

    Example:
        此函數通常在回測系統的績效分析標籤頁中被呼叫：
        ```python
        with tab3:
            show_performance_analysis()
        ```

    Note:
        - 只顯示狀態為 'completed' 的回測結果
        - 績效指標包括總報酬率、年化報酬率、夏普比率、最大回撤、
          勝率、盈虧比、總交易次數和平均持倉天數
        - 支援結果載入失敗的錯誤處理
    """
    st.subheader("績效分析")

    service = get_backtest_service()

    # 選擇要分析的回測
    backtest_list = service.get_backtest_list(limit=20)
    completed_backtests = [bt for bt in backtest_list if bt["status"] == "completed"]

    if not completed_backtests:
        st.warning("⚠️ 沒有已完成的回測結果可供分析")
        return

    # 回測選擇
    col1, col2 = st.columns([3, 1])

    with col1:
        backtest_options = [
            f"{bt['strategy_name']} - {bt['created_at'][:19]}"
            for bt in completed_backtests
        ]
        selected_idx = st.selectbox(
            "選擇回測結果",
            options=range(len(backtest_options)),
            format_func=lambda x: backtest_options[x],
        )

        selected_backtest = completed_backtests[selected_idx]

    with col2:
        st.metric("回測狀態", selected_backtest["status"])
        if st.button("🔄 刷新數據"):
            st.rerun()

    # 獲取詳細結果
    results = service.get_backtest_results(selected_backtest["id"])

    if not results:
        st.error("❌ 無法載入回測結果")
        return

    metrics = results.get("metrics", {})

    # 關鍵績效指標
    st.markdown("### 📊 關鍵績效指標")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_return = metrics.get("total_return", 0)
        st.metric(
            "總報酬率",
            f"{total_return:.2f}%",
            delta=f"{total_return:.2f}%" if total_return != 0 else None,
        )

        annual_return = metrics.get("annual_return", 0)
        st.metric("年化報酬率", f"{annual_return:.2f}%")

    with col2:
        sharpe_ratio = metrics.get("sharpe_ratio", 0)
        st.metric("夏普比率", f"{sharpe_ratio:.2f}")

        max_drawdown = metrics.get("max_drawdown", 0)
        st.metric("最大回撤", f"{max_drawdown:.2f}%")

    with col3:
        win_rate = metrics.get("win_rate", 0)
        st.metric("勝率", f"{win_rate:.1f}%")

        profit_ratio = metrics.get("profit_ratio", 0)
        st.metric("盈虧比", f"{profit_ratio:.2f}")

    with col4:
        total_trades = metrics.get("total_trades", 0)
        st.metric("總交易次數", f"{total_trades}")

        avg_duration = metrics.get("avg_trade_duration", 0)
        st.metric("平均持倉天數", f"{avg_duration:.1f}")


def show_trade_records():
    """顯示交易記錄頁面。

    提供回測交易記錄的查看介面，使用者可以選擇已完成的回測
    結果來查看詳細的交易記錄和相關統計資訊。

    主要功能包括：
    - 選擇已完成的回測結果
    - 顯示詳細的交易記錄
    - 提供交易統計和分析
    - 處理無結果的情況

    Returns:
        None: 如果沒有已完成的回測結果，會顯示警告並提前返回

    Example:
        此函數通常在回測系統的交易記錄標籤頁中被呼叫：
        ```python
        with tab4:
            show_trade_records()
        ```

    Note:
        - 只顯示狀態為 'completed' 的回測結果
        - 支援結果載入失敗的錯誤處理
        - 交易記錄包括買賣時間、價格、數量、損益等詳細資訊
    """
    st.subheader("交易記錄")

    service = get_backtest_service()

    # 選擇要查看的回測
    backtest_list = service.get_backtest_list(limit=20)
    completed_backtests = [bt for bt in backtest_list if bt["status"] == "completed"]

    if not completed_backtests:
        st.warning("⚠️ 沒有已完成的回測結果可供查看")
        return

    # 回測選擇
    backtest_options = [
        f"{bt['strategy_name']} - {bt['created_at'][:19]}" for bt in completed_backtests
    ]
    selected_idx = st.selectbox(
        "選擇回測結果",
        options=range(len(backtest_options)),
        format_func=lambda x: backtest_options[x],
    )

    selected_backtest = completed_backtests[selected_idx]

    # 獲取詳細結果
    results = service.get_backtest_results(selected_backtest["id"])

    if not results:
        st.error("❌ 無法載入回測結果")
        return

    trades = results.get("trades", [])

    if not trades:
        st.warning("⚠️ 此回測沒有交易記錄")
        return

    # 顯示交易記錄表格
    st.markdown("### 📋 交易明細")

    # 創建DataFrame
    df_data = []
    for trade in trades:
        df_data.append(
            {
                "股票代碼": trade.get("symbol", ""),
                "進場日期": trade.get("entry_date", ""),
                "出場日期": trade.get("exit_date", ""),
                "進場價格": f"{trade.get('entry_price', 0):.2f}",
                "出場價格": f"{trade.get('exit_price', 0):.2f}",
                "數量": f"{trade.get('quantity', 0):.0f}",
                "損益": f"{trade.get('profit', 0):.2f}",
                "損益率": f"{trade.get('profit_pct', 0):.2f}%",
                "持倉天數": f"{trade.get('hold_days', 0)}",
            }
        )

    df = pd.DataFrame(df_data)
    st.dataframe(df, use_container_width=True)


def show_report_export():
    """顯示報表匯出頁面。

    提供回測結果的多格式匯出功能，使用者可以選擇已完成的回測
    結果並以不同格式（JSON、CSV、Excel、HTML）匯出報表。

    主要功能包括：
    - 選擇已完成的回測結果
    - 提供多種匯出格式選擇
    - 生成下載連結
    - 處理無結果的情況

    支援的匯出格式：
    - JSON: 完整的結構化數據
    - CSV: 交易記錄表格格式
    - Excel: 多工作表格式，包含績效指標和交易記錄
    - HTML: 網頁格式報表

    Returns:
        None: 如果沒有已完成的回測結果，會顯示警告並提前返回

    Example:
        此函數通常在回測系統的報表匯出標籤頁中被呼叫：
        ```python
        with tab5:
            show_report_export()
        ```

    Note:
        - 只顯示狀態為 'completed' 的回測結果
        - 匯出功能依賴於 BacktestService.export_results 方法
        - 每種格式都會生成對應的下載按鈕
    """
    st.subheader("報表匯出")

    service = get_backtest_service()

    # 選擇要匯出的回測
    backtest_list = service.get_backtest_list(limit=20)
    completed_backtests = [bt for bt in backtest_list if bt["status"] == "completed"]

    if not completed_backtests:
        st.warning("⚠️ 沒有已完成的回測結果可供匯出")
        return

    # 回測選擇
    backtest_options = [
        f"{bt['strategy_name']} - {bt['created_at'][:19]}" for bt in completed_backtests
    ]
    selected_idx = st.selectbox(
        "選擇回測結果",
        options=range(len(backtest_options)),
        format_func=lambda x: backtest_options[x],
    )

    selected_backtest = completed_backtests[selected_idx]

    # 匯出格式選擇
    st.markdown("### 📄 選擇匯出格式")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📄 匯出 JSON", use_container_width=True):
            data = service.export_results(selected_backtest["id"], "json")
            if data:
                st.download_button(
                    "下載 JSON 檔案",
                    data,
                    f"backtest_{selected_backtest['id'][:8]}.json",
                    "application/json",
                )

    with col2:
        if st.button("📊 匯出 CSV", use_container_width=True):
            data = service.export_results(selected_backtest["id"], "csv")
            if data:
                st.download_button(
                    "下載 CSV 檔案",
                    data,
                    f"backtest_{selected_backtest['id'][:8]}.csv",
                    "text/csv",
                )

    with col3:
        if st.button("📈 匯出 Excel", use_container_width=True):
            data = service.export_results(selected_backtest["id"], "excel")
            if data:
                st.download_button(
                    "下載 Excel 檔案",
                    data,
                    f"backtest_{selected_backtest['id'][:8]}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

    with col4:
        if st.button("🌐 匯出 HTML", use_container_width=True):
            data = service.export_results(selected_backtest["id"], "html")
            if data:
                st.download_button(
                    "下載 HTML 檔案",
                    data,
                    f"backtest_{selected_backtest['id'][:8]}.html",
                    "text/html",
                )
