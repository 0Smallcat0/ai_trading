"""
策略管理頁面

此模組實現了策略管理頁面，提供策略瀏覽、編輯、參數調整和版本控制功能。
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time

# 導入策略管理服務和組件
from src.core.strategy_management_service import StrategyManagementService
from src.ui.components.strategy_components import show_strategy_card


# 簡化的通知函數
def show_notification(message, type="info"):
    if type == "success":
        st.success(message)
    elif type == "error":
        st.error(message)
    elif type == "warning":
        st.warning(message)
    else:
        st.info(message)


@st.cache_resource
def get_strategy_service():
    """獲取策略管理服務實例"""
    return StrategyManagementService()


def get_mock_strategies():
    """獲取模擬策略列表（用於演示）"""
    service = get_strategy_service()

    # 嘗試從服務獲取策略，如果沒有則創建一些示例策略
    strategies = service.list_strategies()

    if not strategies:
        # 創建一些示例策略
        example_strategies = [
            {
                "name": "移動平均線交叉策略",
                "type": "技術分析策略",
                "description": "使用短期和長期移動平均線交叉產生交易訊號",
                "author": "系統",
                "parameters": {"short_window": 5, "long_window": 20},
                "risk_parameters": {
                    "stop_loss": 0.05,
                    "take_profit": 0.1,
                    "max_position_size": 0.2,
                },
            },
            {
                "name": "RSI策略",
                "type": "技術分析策略",
                "description": "使用相對強弱指數(RSI)判斷超買超賣",
                "author": "系統",
                "parameters": {"window": 14, "overbought": 70, "oversold": 30},
                "risk_parameters": {
                    "stop_loss": 0.05,
                    "take_profit": 0.1,
                    "max_position_size": 0.2,
                },
            },
        ]

        for strategy_data in example_strategies:
            try:
                service.create_strategy(**strategy_data)
            except Exception as e:
                st.error(f"創建示例策略失敗: {e}")

        # 重新獲取策略列表
        strategies = service.list_strategies()

    return strategies


# 策略類型定義
STRATEGY_TYPES = {
    "技術分析策略": [
        "移動平均線交叉策略",
        "RSI策略",
        "MACD策略",
        "布林通道策略",
        "KD指標策略",
        "突破策略",
        "趨勢跟蹤策略",
        "動量策略",
        "均值回歸策略",
    ],
    "基本面策略": [
        "價值投資策略",
        "成長投資策略",
        "股息策略",
        "財報分析策略",
        "產業分析策略",
        "基本面評分策略",
    ],
    "套利策略": [
        "配對交易策略",
        "統計套利策略",
        "價差套利策略",
        "合約轉換套利策略",
        "ETF套利策略",
    ],
    "AI策略": [
        "機器學習策略",
        "深度學習策略",
        "強化學習策略",
        "集成學習策略",
        "自然語言處理策略",
        "情緒分析策略",
    ],
    "混合策略": [
        "技術+基本面混合策略",
        "技術+AI混合策略",
        "多策略組合策略",
        "自適應策略",
    ],
}

# 策略模板（簡化版本以避免語法錯誤）
STRATEGY_TEMPLATES = {
    "移動平均線交叉策略": {
        "code": "# 移動平均線交叉策略代碼模板\n# 這裡將包含完整的策略實現代碼",
        "parameters": {
            "short_window": {
                "type": "int",
                "default": 5,
                "min": 1,
                "max": 50,
                "description": "短期移動平均線窗口大小",
            },
            "long_window": {
                "type": "int",
                "default": 20,
                "min": 5,
                "max": 200,
                "description": "長期移動平均線窗口大小",
            },
        },
        "risk_parameters": {
            "stop_loss": {
                "type": "float",
                "default": 0.05,
                "min": 0.01,
                "max": 0.2,
                "description": "停損百分比",
            },
            "take_profit": {
                "type": "float",
                "default": 0.1,
                "min": 0.02,
                "max": 0.5,
                "description": "停利百分比",
            },
            "max_position_size": {
                "type": "float",
                "default": 0.2,
                "min": 0.01,
                "max": 1.0,
                "description": "最大倉位大小（佔總資金比例）",
            },
        },
        "description": "移動平均線交叉策略是一種經典的技術分析策略，通過比較短期和長期移動平均線的交叉來產生交易訊號。",
    },
    "RSI策略": {
        "code": "# RSI策略代碼模板\n# 這裡將包含完整的RSI策略實現代碼",
        "parameters": {
            "window": {
                "type": "int",
                "default": 14,
                "min": 2,
                "max": 50,
                "description": "RSI計算窗口大小",
            },
            "overbought": {
                "type": "float",
                "default": 70,
                "min": 50,
                "max": 90,
                "description": "超買閾值",
            },
            "oversold": {
                "type": "float",
                "default": 30,
                "min": 10,
                "max": 50,
                "description": "超賣閾值",
            },
        },
        "risk_parameters": {
            "stop_loss": {
                "type": "float",
                "default": 0.05,
                "min": 0.01,
                "max": 0.2,
                "description": "停損百分比",
            },
            "take_profit": {
                "type": "float",
                "default": 0.1,
                "min": 0.02,
                "max": 0.5,
                "description": "停利百分比",
            },
            "max_position_size": {
                "type": "float",
                "default": 0.2,
                "min": 0.01,
                "max": 1.0,
                "description": "最大倉位大小（佔總資金比例）",
            },
        },
        "description": "RSI策略是一種基於動量指標的交易策略，通過計算相對強弱指數來判斷市場是否處於超買或超賣狀態。",
    },
}


def get_mock_strategies():
    """獲取模擬策略列表"""
    strategies = [
        {
            "id": "strategy_001",
            "name": "移動平均線交叉策略",
            "type": "技術分析策略",
            "description": "使用短期和長期移動平均線交叉產生交易訊號",
            "author": "系統",
            "created_at": "2023-01-15",
            "updated_at": "2023-06-20",
            "version": "1.2.0",
            "status": "啟用",
            "performance": {
                "sharpe_ratio": 1.35,
                "max_drawdown": 0.15,
                "win_rate": 0.62,
                "profit_factor": 1.8,
            },
            "parameters": {"short_window": 5, "long_window": 20},
            "risk_parameters": {
                "stop_loss": 0.05,
                "take_profit": 0.1,
                "max_position_size": 0.2,
            },
        },
        {
            "id": "strategy_002",
            "name": "RSI策略",
            "type": "技術分析策略",
            "description": "使用相對強弱指數(RSI)判斷超買超賣",
            "author": "系統",
            "created_at": "2023-02-10",
            "updated_at": "2023-07-05",
            "version": "1.1.0",
            "status": "啟用",
            "performance": {
                "sharpe_ratio": 1.22,
                "max_drawdown": 0.18,
                "win_rate": 0.58,
                "profit_factor": 1.65,
            },
            "parameters": {"window": 14, "overbought": 70, "oversold": 30},
            "risk_parameters": {
                "stop_loss": 0.05,
                "take_profit": 0.1,
                "max_position_size": 0.2,
            },
        },
        {
            "id": "strategy_003",
            "name": "布林通道策略",
            "type": "技術分析策略",
            "description": "使用布林通道上下軌作為交易訊號",
            "author": "系統",
            "created_at": "2023-03-05",
            "updated_at": "2023-08-15",
            "version": "1.0.5",
            "status": "啟用",
            "performance": {
                "sharpe_ratio": 1.18,
                "max_drawdown": 0.2,
                "win_rate": 0.55,
                "profit_factor": 1.6,
            },
            "parameters": {"window": 20, "num_std": 2},
            "risk_parameters": {
                "stop_loss": 0.05,
                "take_profit": 0.1,
                "max_position_size": 0.15,
            },
        },
        {
            "id": "strategy_004",
            "name": "價值投資策略",
            "type": "基本面策略",
            "description": "基於本益比、股價淨值比等基本面指標進行選股",
            "author": "使用者",
            "created_at": "2023-04-20",
            "updated_at": "2023-09-10",
            "version": "1.3.0",
            "status": "啟用",
            "performance": {
                "sharpe_ratio": 1.45,
                "max_drawdown": 0.12,
                "win_rate": 0.65,
                "profit_factor": 2.1,
            },
            "parameters": {"max_pe": 15, "max_pb": 1.5, "min_dividend_yield": 0.03},
            "risk_parameters": {
                "stop_loss": 0.1,
                "take_profit": 0.3,
                "max_position_size": 0.1,
            },
        },
        {
            "id": "strategy_005",
            "name": "配對交易策略",
            "type": "套利策略",
            "description": "利用相關性高的股票對進行配對交易",
            "author": "使用者",
            "created_at": "2023-05-15",
            "updated_at": "2023-10-05",
            "version": "1.0.0",
            "status": "測試中",
            "performance": {
                "sharpe_ratio": 1.05,
                "max_drawdown": 0.08,
                "win_rate": 0.6,
                "profit_factor": 1.5,
            },
            "parameters": {
                "lookback_period": 60,
                "entry_threshold": 2,
                "exit_threshold": 0.5,
            },
            "risk_parameters": {
                "stop_loss": 0.05,
                "take_profit": 0.1,
                "max_position_size": 0.1,
            },
        },
        {
            "id": "strategy_006",
            "name": "機器學習策略",
            "type": "AI策略",
            "description": "使用XGBoost模型預測股價走勢",
            "author": "使用者",
            "created_at": "2023-06-10",
            "updated_at": "2023-11-20",
            "version": "2.0.0",
            "status": "測試中",
            "performance": {
                "sharpe_ratio": 1.6,
                "max_drawdown": 0.22,
                "win_rate": 0.57,
                "profit_factor": 1.9,
            },
            "parameters": {
                "n_estimators": 100,
                "max_depth": 5,
                "learning_rate": 0.1,
                "prediction_threshold": 0.6,
            },
            "risk_parameters": {
                "stop_loss": 0.08,
                "take_profit": 0.15,
                "max_position_size": 0.15,
            },
        },
        {
            "id": "strategy_007",
            "name": "技術+基本面混合策略",
            "type": "混合策略",
            "description": "結合技術指標和基本面指標的混合策略",
            "author": "使用者",
            "created_at": "2023-07-25",
            "updated_at": "2023-12-15",
            "version": "1.5.0",
            "status": "停用",
            "performance": {
                "sharpe_ratio": 1.55,
                "max_drawdown": 0.17,
                "win_rate": 0.63,
                "profit_factor": 2.0,
            },
            "parameters": {
                "technical_weight": 0.6,
                "fundamental_weight": 0.4,
                "min_score": 0.7,
            },
            "risk_parameters": {
                "stop_loss": 0.07,
                "take_profit": 0.12,
                "max_position_size": 0.2,
            },
        },
    ]
    return strategies


def show_strategy_list():
    """顯示策略清單頁面"""
    st.subheader("策略清單")

    # 獲取策略服務
    service = get_strategy_service()
    strategy_types = service.get_strategy_types()

    # 過濾選項
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # 選擇策略類型
        all_types = ["所有類型"] + list(strategy_types.keys())
        selected_type = st.selectbox("策略類型", options=all_types, index=0)

    with col2:
        # 選擇策略狀態
        statuses = ["所有狀態", "draft", "active", "testing", "disabled", "archived"]
        status_labels = ["所有狀態", "草稿", "啟用", "測試中", "停用", "已歸檔"]
        selected_status_idx = st.selectbox(
            "策略狀態",
            options=range(len(status_labels)),
            format_func=lambda x: status_labels[x],
            index=0,
        )
        selected_status = (
            statuses[selected_status_idx] if selected_status_idx > 0 else None
        )

    with col3:
        # 搜尋策略
        search_query = st.text_input("搜尋策略", placeholder="輸入策略名稱或描述")

    with col4:
        # 排序選項
        sort_options = ["更新時間", "創建時間", "名稱", "效能"]
        sort_by = st.selectbox("排序方式", options=sort_options, index=0)

    # 獲取策略列表
    try:
        strategies = service.list_strategies(
            strategy_type=selected_type if selected_type != "所有類型" else None,
            status=selected_status,
            search_query=search_query if search_query else None,
        )
    except Exception as e:
        st.error(f"獲取策略列表失敗: {e}")
        strategies = []

    # 排序策略
    if strategies and sort_by:
        if sort_by == "更新時間":
            strategies.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        elif sort_by == "創建時間":
            strategies.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        elif sort_by == "名稱":
            strategies.sort(key=lambda x: x.get("name", ""))
        elif sort_by == "效能":
            strategies.sort(
                key=lambda x: x.get("performance", {}).get("sharpe_ratio", 0),
                reverse=True,
            )

    # 顯示策略數量和統計
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("總策略數", len(strategies))
    with col2:
        active_count = len([s for s in strategies if s.get("status") == "active"])
        st.metric("啟用策略", active_count)
    with col3:
        testing_count = len([s for s in strategies if s.get("status") == "testing"])
        st.metric("測試中策略", testing_count)
    with col4:
        avg_performance = (
            np.mean(
                [s.get("performance", {}).get("sharpe_ratio", 0) for s in strategies]
            )
            if strategies
            else 0
        )
        st.metric("平均夏普比率", f"{avg_performance:.2f}")

    # 顯示策略列表
    if strategies:
        for strategy in strategies:
            with st.expander(
                f"{strategy['name']} - {strategy['type']} - {strategy.get('status', 'draft')}"
            ):
                # 使用新的策略卡片組件
                show_strategy_card(strategy, key_prefix=f"list_{strategy['id']}")

                # 操作按鈕
                st.markdown("---")
                col1, col2, col3, col4, col5, col6 = st.columns(6)

                with col1:
                    if st.button("編輯策略", key=f"edit_{strategy['id']}"):
                        st.session_state.selected_strategy = strategy
                        st.session_state.current_tab = "edit"

                with col2:
                    if st.button("版本控制", key=f"version_{strategy['id']}"):
                        st.session_state.selected_strategy = strategy
                        st.session_state.current_tab = "version"

                with col3:
                    if st.button("效能分析", key=f"performance_{strategy['id']}"):
                        st.session_state.selected_strategy = strategy
                        st.session_state.current_tab = "performance"

                with col4:
                    if st.button("參數優化", key=f"optimize_{strategy['id']}"):
                        st.session_state.selected_strategy = strategy
                        st.session_state.current_tab = "optimize"

                with col5:
                    if st.button("複製策略", key=f"copy_{strategy['id']}"):
                        try:
                            new_name = f"{strategy['name']}_副本"
                            service.create_strategy(
                                name=new_name,
                                strategy_type=strategy["type"],
                                description=f"複製自 {strategy['name']}",
                                code=strategy.get("code", ""),
                                parameters=strategy.get("parameters", {}),
                                risk_parameters=strategy.get("risk_parameters", {}),
                                author="使用者",
                            )
                            st.success(f"策略已複製為: {new_name}")
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"複製策略失敗: {e}")

                with col6:
                    if st.button("刪除策略", key=f"delete_{strategy['id']}"):
                        if st.session_state.get(
                            f"confirm_delete_{strategy['id']}", False
                        ):
                            try:
                                service.delete_strategy(strategy["id"])
                                st.success("策略已刪除")
                                st.experimental_rerun()
                            except Exception as e:
                                st.error(f"刪除策略失敗: {e}")
                        else:
                            st.session_state[f"confirm_delete_{strategy['id']}"] = True
                            st.warning("再次點擊確認刪除")

    else:
        st.info("目前沒有策略，請先創建策略。")

    # 新增策略按鈕
    st.markdown("---")
    if st.button("➕ 創建新策略", type="primary"):
        st.session_state.current_tab = "create"
        st.experimental_rerun()


def show_strategy_version_control():
    """顯示策略版本控制頁面"""
    st.subheader("📋 策略版本控制")

    if (
        "selected_strategy" not in st.session_state
        or not st.session_state.selected_strategy
    ):
        st.warning("請先選擇一個策略")
        return

    strategy = st.session_state.selected_strategy
    service = get_strategy_service()

    st.write(f"**策略名稱**: {strategy['name']}")
    st.write(f"**當前版本**: {strategy.get('version', '1.0.0')}")

    # 獲取版本歷史
    try:
        versions = service.get_strategy_versions(strategy["id"])
    except Exception as e:
        st.error(f"獲取版本歷史失敗: {e}")
        versions = []

    # 版本操作選項
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("創建新版本"):
            st.session_state.show_version_create = True

    with col2:
        if st.button("比較版本"):
            st.session_state.show_version_compare = True

    with col3:
        if st.button("回滾版本"):
            st.session_state.show_version_rollback = True

    # 版本歷史表格
    if versions:
        st.subheader("版本歷史")

        version_data = []
        for version in versions:
            version_data.append(
                {
                    "版本": version.get("version", ""),
                    "創建時間": version.get("created_at", ""),
                    "創建者": version.get("created_by", ""),
                    "變更說明": version.get("change_log", ""),
                    "狀態": (
                        "當前"
                        if version.get("version") == strategy.get("version")
                        else "歷史"
                    ),
                }
            )

        df = pd.DataFrame(version_data)
        st.dataframe(df, use_container_width=True)

        # 版本操作
        selected_version = st.selectbox(
            "選擇版本進行操作",
            options=[v.get("version", "") for v in versions],
            index=0,
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("查看版本詳情"):
                selected_version_data = next(
                    (v for v in versions if v.get("version") == selected_version), None
                )
                if selected_version_data:
                    st.json(selected_version_data)

        with col2:
            if st.button("下載版本"):
                # 實現版本下載功能
                st.info("版本下載功能開發中...")

        with col3:
            if st.button("恢復到此版本"):
                try:
                    service.rollback_strategy(
                        strategy["id"], selected_version, author="使用者"
                    )
                    st.success(f"已恢復到版本 {selected_version}")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"版本恢復失敗: {e}")

    else:
        st.info("此策略尚無版本歷史")

    # 創建新版本對話框
    if st.session_state.get("show_version_create", False):
        with st.expander("創建新版本", expanded=True):
            change_log = st.text_area(
                "變更說明", placeholder="請描述此版本的主要變更..."
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.button("確認創建"):
                    if change_log:
                        try:
                            new_version = service.update_strategy(
                                strategy["id"], change_log=change_log, author="使用者"
                            )
                            st.success(f"新版本 {new_version} 創建成功")
                            st.session_state.show_version_create = False
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"創建版本失敗: {e}")
                    else:
                        st.warning("請填寫變更說明")

            with col2:
                if st.button("取消"):
                    st.session_state.show_version_create = False
                    st.experimental_rerun()


def show_strategy_performance_analysis():
    """顯示策略效能分析頁面"""
    st.subheader("📊 策略效能分析")

    if (
        "selected_strategy" not in st.session_state
        or not st.session_state.selected_strategy
    ):
        st.warning("請先選擇一個策略")
        return

    strategy = st.session_state.selected_strategy
    service = get_strategy_service()

    st.write(f"**策略名稱**: {strategy['name']}")

    # 效能分析選項
    analysis_type = st.selectbox(
        "分析類型",
        options=["基本效能指標", "風險分析", "回測結果", "市場條件分析", "策略比較"],
        index=0,
    )

    if analysis_type == "基本效能指標":
        show_basic_performance_metrics(strategy)
    elif analysis_type == "風險分析":
        show_risk_analysis(strategy)
    elif analysis_type == "回測結果":
        show_backtest_results(strategy)
    elif analysis_type == "市場條件分析":
        show_market_condition_analysis(strategy)
    elif analysis_type == "策略比較":
        show_strategy_comparison(strategy)


def show_basic_performance_metrics(strategy):
    """顯示基本效能指標"""
    st.subheader("基本效能指標")

    # 模擬效能數據
    performance = strategy.get("performance", {})

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        sharpe_ratio = performance.get("sharpe_ratio", 0)
        st.metric("夏普比率", f"{sharpe_ratio:.2f}", delta=f"{sharpe_ratio-1:.2f}")

    with col2:
        max_drawdown = performance.get("max_drawdown", 0)
        st.metric("最大回撤", f"{max_drawdown:.1%}", delta=f"{max_drawdown-0.2:.1%}")

    with col3:
        win_rate = performance.get("win_rate", 0)
        st.metric("勝率", f"{win_rate:.1%}", delta=f"{win_rate-0.5:.1%}")

    with col4:
        profit_factor = performance.get("profit_factor", 0)
        st.metric("獲利因子", f"{profit_factor:.2f}", delta=f"{profit_factor-1.5:.2f}")

    # 效能趨勢圖
    st.subheader("效能趨勢")

    # 生成模擬數據
    dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq="D")
    cumulative_returns = np.cumsum(np.random.normal(0.001, 0.02, len(dates)))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=cumulative_returns,
            mode="lines",
            name="累積收益率",
            line=dict(color="blue", width=2),
        )
    )

    fig.update_layout(
        title="策略累積收益率", xaxis_title="日期", yaxis_title="累積收益率", height=400
    )

    st.plotly_chart(fig, use_container_width=True)


def show_risk_analysis(strategy):
    """顯示風險分析"""
    st.subheader("風險分析")

    performance = strategy.get("performance", {})

    # 風險指標
    col1, col2, col3 = st.columns(3)

    with col1:
        var_95 = np.random.uniform(0.02, 0.05)
        st.metric("VaR (95%)", f"{var_95:.2%}")

    with col2:
        cvar_95 = np.random.uniform(0.03, 0.07)
        st.metric("CVaR (95%)", f"{cvar_95:.2%}")

    with col3:
        volatility = np.random.uniform(0.15, 0.25)
        st.metric("年化波動率", f"{volatility:.1%}")

    # 風險分解圖
    st.subheader("風險分解")

    risk_components = {
        "市場風險": 0.6,
        "流動性風險": 0.2,
        "信用風險": 0.1,
        "操作風險": 0.1,
    }

    fig = go.Figure(
        data=[
            go.Pie(
                labels=list(risk_components.keys()),
                values=list(risk_components.values()),
                hole=0.3,
            )
        ]
    )

    fig.update_layout(title="風險組成分析", height=400)
    st.plotly_chart(fig, use_container_width=True)


def show_backtest_results(strategy):
    """顯示回測結果"""
    st.subheader("回測結果")

    # 回測參數設定
    col1, col2, col3 = st.columns(3)

    with col1:
        start_date = st.date_input("開始日期", value=pd.to_datetime("2023-01-01"))

    with col2:
        end_date = st.date_input("結束日期", value=pd.to_datetime("2023-12-31"))

    with col3:
        initial_capital = st.number_input("初始資金", value=100000, min_value=10000)

    if st.button("執行回測"):
        with st.spinner("正在執行回測..."):
            # 模擬回測過程
            import time

            time.sleep(2)

            # 顯示回測結果
            st.success("回測完成！")

            # 模擬回測數據
            dates = pd.date_range(start=start_date, end=end_date, freq="D")
            returns = np.random.normal(0.001, 0.02, len(dates))
            cumulative_returns = np.cumprod(1 + returns)

            # 回測結果圖表
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=cumulative_returns * initial_capital,
                    mode="lines",
                    name="策略淨值",
                    line=dict(color="green", width=2),
                )
            )

            # 基準比較
            benchmark_returns = np.random.normal(0.0005, 0.015, len(dates))
            benchmark_cumulative = np.cumprod(1 + benchmark_returns)

            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=benchmark_cumulative * initial_capital,
                    mode="lines",
                    name="基準指數",
                    line=dict(color="red", width=2, dash="dash"),
                )
            )

            fig.update_layout(
                title="回測結果 - 策略 vs 基準",
                xaxis_title="日期",
                yaxis_title="淨值",
                height=500,
            )

            st.plotly_chart(fig, use_container_width=True)

            # 回測統計
            final_return = (cumulative_returns[-1] - 1) * 100
            benchmark_return = (benchmark_cumulative[-1] - 1) * 100

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("總收益率", f"{final_return:.2f}%")

            with col2:
                st.metric("基準收益率", f"{benchmark_return:.2f}%")

            with col3:
                st.metric("超額收益", f"{final_return - benchmark_return:.2f}%")

            with col4:
                max_dd = np.max(
                    np.maximum.accumulate(cumulative_returns) - cumulative_returns
                ) / np.maximum.accumulate(cumulative_returns)
                st.metric("最大回撤", f"{np.max(max_dd):.2%}")


def show_market_condition_analysis(strategy):
    """顯示市場條件分析"""
    st.subheader("市場條件分析")

    # 不同市場條件下的表現
    market_conditions = {
        "牛市": {"return": 0.15, "volatility": 0.12, "sharpe": 1.25},
        "熊市": {"return": -0.08, "volatility": 0.25, "sharpe": -0.32},
        "震盪市": {"return": 0.03, "volatility": 0.18, "sharpe": 0.17},
        "高波動": {"return": 0.08, "volatility": 0.35, "sharpe": 0.23},
    }

    # 創建市場條件表現表格
    condition_data = []
    for condition, metrics in market_conditions.items():
        condition_data.append(
            {
                "市場條件": condition,
                "年化收益率": f"{metrics['return']:.1%}",
                "年化波動率": f"{metrics['volatility']:.1%}",
                "夏普比率": f"{metrics['sharpe']:.2f}",
            }
        )

    df = pd.DataFrame(condition_data)
    st.dataframe(df, use_container_width=True)

    # 市場條件表現圖表
    fig = go.Figure()

    conditions = list(market_conditions.keys())
    returns = [market_conditions[c]["return"] for c in conditions]

    fig.add_trace(
        go.Bar(
            x=conditions,
            y=returns,
            name="年化收益率",
            marker_color=["green" if r > 0 else "red" for r in returns],
        )
    )

    fig.update_layout(
        title="不同市場條件下的策略表現",
        xaxis_title="市場條件",
        yaxis_title="年化收益率",
        height=400,
    )

    st.plotly_chart(fig, use_container_width=True)


def show_strategy_comparison(strategy):
    """顯示策略比較"""
    st.subheader("策略比較")

    service = get_strategy_service()

    # 獲取所有策略用於比較
    try:
        all_strategies = service.list_strategies()
        strategy_options = [
            s["name"] for s in all_strategies if s["id"] != strategy["id"]
        ]
    except:
        strategy_options = []

    if not strategy_options:
        st.info("沒有其他策略可供比較")
        return

    # 選擇比較策略
    selected_strategies = st.multiselect(
        "選擇要比較的策略",
        options=strategy_options,
        default=(
            strategy_options[:2] if len(strategy_options) >= 2 else strategy_options
        ),
    )

    if selected_strategies:
        # 創建比較表格
        comparison_data = []

        # 當前策略
        perf = strategy.get("performance", {})
        comparison_data.append(
            {
                "策略名稱": strategy["name"],
                "夏普比率": perf.get("sharpe_ratio", 0),
                "最大回撤": perf.get("max_drawdown", 0),
                "勝率": perf.get("win_rate", 0),
                "獲利因子": perf.get("profit_factor", 0),
            }
        )

        # 比較策略
        for strategy_name in selected_strategies:
            comp_strategy = next(
                (s for s in all_strategies if s["name"] == strategy_name), None
            )
            if comp_strategy:
                comp_perf = comp_strategy.get("performance", {})
                comparison_data.append(
                    {
                        "策略名稱": strategy_name,
                        "夏普比率": comp_perf.get("sharpe_ratio", 0),
                        "最大回撤": comp_perf.get("max_drawdown", 0),
                        "勝率": comp_perf.get("win_rate", 0),
                        "獲利因子": comp_perf.get("profit_factor", 0),
                    }
                )

        df = pd.DataFrame(comparison_data)
        st.dataframe(df, use_container_width=True)

        # 比較圖表
        fig = go.Figure()

        metrics = ["夏普比率", "勝率", "獲利因子"]
        for metric in metrics:
            fig.add_trace(
                go.Bar(
                    name=metric,
                    x=df["策略名稱"],
                    y=df[metric],
                    text=df[metric].round(2),
                    textposition="auto",
                )
            )

        fig.update_layout(
            title="策略效能比較",
            xaxis_title="策略",
            yaxis_title="指標值",
            barmode="group",
            height=500,
        )

        st.plotly_chart(fig, use_container_width=True)


def show_strategy_parameter_optimization():
    """顯示策略參數優化頁面"""
    st.subheader("🔧 策略參數優化")

    if (
        "selected_strategy" not in st.session_state
        or not st.session_state.selected_strategy
    ):
        st.warning("請先選擇一個策略")
        return

    strategy = st.session_state.selected_strategy
    service = get_strategy_service()

    st.write(f"**策略名稱**: {strategy['name']}")

    # 優化方法選擇
    optimization_method = st.selectbox(
        "優化方法", options=["網格搜索", "隨機搜索", "貝葉斯優化", "遺傳算法"], index=0
    )

    # 優化目標選擇
    optimization_target = st.selectbox(
        "優化目標",
        options=["夏普比率", "總收益率", "最大回撤", "獲利因子", "勝率"],
        index=0,
    )

    # 參數範圍設定
    st.subheader("參數範圍設定")

    current_params = strategy.get("parameters", {})
    param_ranges = {}

    if current_params:
        for param_name, current_value in current_params.items():
            st.write(f"**{param_name}** (當前值: {current_value})")

            col1, col2, col3 = st.columns(3)

            with col1:
                min_val = st.number_input(
                    f"最小值",
                    value=(
                        float(current_value) * 0.5
                        if isinstance(current_value, (int, float))
                        else 0.0
                    ),
                    key=f"min_{param_name}",
                )

            with col2:
                max_val = st.number_input(
                    f"最大值",
                    value=(
                        float(current_value) * 2.0
                        if isinstance(current_value, (int, float))
                        else 1.0
                    ),
                    key=f"max_{param_name}",
                )

            with col3:
                step = st.number_input(
                    f"步長",
                    value=(
                        float(current_value) * 0.1
                        if isinstance(current_value, (int, float))
                        else 0.1
                    ),
                    key=f"step_{param_name}",
                )

            param_ranges[param_name] = {
                "min": min_val,
                "max": max_val,
                "step": step,
                "current": current_value,
            }

    # 優化設定
    st.subheader("優化設定")

    col1, col2 = st.columns(2)

    with col1:
        max_iterations = st.number_input(
            "最大迭代次數", value=100, min_value=10, max_value=1000
        )

    with col2:
        cv_folds = st.number_input("交叉驗證折數", value=5, min_value=2, max_value=10)

    # 執行優化
    if st.button("🚀 開始優化", type="primary"):
        if not param_ranges:
            st.warning("請先設定參數範圍")
            return

        with st.spinner("正在執行參數優化..."):
            # 模擬優化過程
            progress_bar = st.progress(0)
            status_text = st.empty()

            optimization_results = []

            for i in range(max_iterations):
                # 模擬優化步驟
                import time

                time.sleep(0.05)  # 模擬計算時間

                # 生成隨機參數組合
                test_params = {}
                for param_name, param_range in param_ranges.items():
                    test_params[param_name] = np.random.uniform(
                        param_range["min"], param_range["max"]
                    )

                # 模擬評估結果
                if optimization_target == "夏普比率":
                    score = np.random.normal(1.2, 0.3)
                elif optimization_target == "總收益率":
                    score = np.random.normal(0.15, 0.05)
                elif optimization_target == "最大回撤":
                    score = -np.random.uniform(0.05, 0.25)  # 負值因為要最小化
                elif optimization_target == "獲利因子":
                    score = np.random.normal(1.8, 0.4)
                else:  # 勝率
                    score = np.random.uniform(0.4, 0.8)

                optimization_results.append(
                    {
                        "iteration": i + 1,
                        "parameters": test_params.copy(),
                        "score": score,
                    }
                )

                # 更新進度
                progress = (i + 1) / max_iterations
                progress_bar.progress(progress)
                status_text.text(
                    f"優化進度: {i+1}/{max_iterations} - 當前最佳{optimization_target}: {max(optimization_results, key=lambda x: x['score'])['score']:.4f}"
                )

            # 優化完成
            st.success("參數優化完成！")

            # 找出最佳參數
            best_result = max(optimization_results, key=lambda x: x["score"])

            st.subheader("優化結果")

            col1, col2 = st.columns(2)

            with col1:
                st.write("**最佳參數組合:**")
                for param_name, param_value in best_result["parameters"].items():
                    current_val = param_ranges[param_name]["current"]
                    improvement = (
                        ((param_value - current_val) / current_val * 100)
                        if current_val != 0
                        else 0
                    )
                    st.write(
                        f"- {param_name}: {param_value:.4f} (原值: {current_val}, 變化: {improvement:+.1f}%)"
                    )

            with col2:
                st.metric(
                    f"最佳{optimization_target}",
                    f"{best_result['score']:.4f}",
                    delta=f"{best_result['score'] - strategy.get('performance', {}).get(optimization_target.lower().replace(' ', '_'), 0):.4f}",
                )

            # 優化過程圖表
            st.subheader("優化過程")

            iterations = [r["iteration"] for r in optimization_results]
            scores = [r["score"] for r in optimization_results]

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=iterations,
                    y=scores,
                    mode="markers+lines",
                    name=optimization_target,
                    line=dict(color="blue", width=1),
                    marker=dict(size=4),
                )
            )

            # 標記最佳點
            fig.add_trace(
                go.Scatter(
                    x=[best_result["iteration"]],
                    y=[best_result["score"]],
                    mode="markers",
                    name="最佳結果",
                    marker=dict(size=12, color="red", symbol="star"),
                )
            )

            fig.update_layout(
                title=f"{optimization_target}優化過程",
                xaxis_title="迭代次數",
                yaxis_title=optimization_target,
                height=400,
            )

            st.plotly_chart(fig, use_container_width=True)

            # 參數敏感性分析
            st.subheader("參數敏感性分析")

            if len(param_ranges) > 1:
                # 創建參數相關性熱圖
                param_names = list(param_ranges.keys())
                correlation_matrix = np.random.rand(len(param_names), len(param_names))
                correlation_matrix = (
                    correlation_matrix + correlation_matrix.T
                ) / 2  # 使矩陣對稱
                np.fill_diagonal(correlation_matrix, 1)  # 對角線設為1

                fig = go.Figure(
                    data=go.Heatmap(
                        z=correlation_matrix,
                        x=param_names,
                        y=param_names,
                        colorscale="RdBu",
                        zmid=0,
                    )
                )

                fig.update_layout(title="參數相關性分析", height=400)

                st.plotly_chart(fig, use_container_width=True)

            # 應用最佳參數
            if st.button("應用最佳參數"):
                try:
                    # 更新策略參數
                    service.update_strategy(
                        strategy["id"],
                        parameters=best_result["parameters"],
                        change_log=f"應用參數優化結果 - {optimization_target}: {best_result['score']:.4f}",
                        author="系統優化",
                    )
                    st.success("最佳參數已應用到策略中！")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"應用參數失敗: {e}")


def show():
    """顯示策略管理主頁面"""
    st.header("📈 策略管理")

    # 初始化 session state
    if "selected_strategy" not in st.session_state:
        st.session_state.selected_strategy = None
    if "current_tab" not in st.session_state:
        st.session_state.current_tab = "list"

    # 創建標籤頁
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📋 策略清單", "📝 策略編輯", "📋 版本控制", "📊 效能分析", "🔧 參數優化"]
    )

    with tab1:
        show_strategy_list()

    with tab2:
        if (
            st.session_state.current_tab == "edit"
            and st.session_state.selected_strategy
        ):
            show_strategy_editor()
        else:
            st.info("請從策略清單中選擇要編輯的策略")

    with tab3:
        if (
            st.session_state.current_tab == "version"
            and st.session_state.selected_strategy
        ):
            show_strategy_version_control()
        else:
            st.info("請從策略清單中選擇要管理版本的策略")

    with tab4:
        if (
            st.session_state.current_tab == "performance"
            and st.session_state.selected_strategy
        ):
            show_strategy_performance_analysis()
        else:
            st.info("請從策略清單中選擇要分析效能的策略")

    with tab5:
        if (
            st.session_state.current_tab == "optimize"
            and st.session_state.selected_strategy
        ):
            show_strategy_parameter_optimization()
        else:
            st.info("請從策略清單中選擇要優化參數的策略")


def show_strategy_editor():
    """顯示策略編輯器（簡化版本）"""
    st.subheader("策略編輯器")

    if not st.session_state.selected_strategy:
        st.warning("請先選擇一個策略")
        return

    strategy = st.session_state.selected_strategy

    st.write(f"**編輯策略**: {strategy['name']}")

    # 基本資訊編輯
    with st.expander("基本資訊", expanded=True):
        name = st.text_input("策略名稱", value=strategy.get("name", ""))
        description = st.text_area("策略描述", value=strategy.get("description", ""))
        strategy_type = st.selectbox(
            "策略類型",
            options=list(STRATEGY_TYPES.keys()),
            index=list(STRATEGY_TYPES.keys()).index(
                strategy.get("type", "技術分析策略")
            ),
        )

    # 參數編輯
    with st.expander("策略參數", expanded=True):
        current_params = strategy.get("parameters", {})
        new_params = {}

        for param_name, param_value in current_params.items():
            new_params[param_name] = st.number_input(
                param_name,
                value=(
                    float(param_value) if isinstance(param_value, (int, float)) else 0.0
                ),
            )

    # 風險參數編輯
    with st.expander("風險參數", expanded=True):
        current_risk_params = strategy.get("risk_parameters", {})
        new_risk_params = {}

        for param_name, param_value in current_risk_params.items():
            new_risk_params[param_name] = st.number_input(
                param_name,
                value=(
                    float(param_value) if isinstance(param_value, (int, float)) else 0.0
                ),
                key=f"risk_{param_name}",
            )

    # 保存按鈕
    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 保存變更", type="primary"):
            try:
                service = get_strategy_service()
                service.update_strategy(
                    strategy["id"],
                    name=name,
                    description=description,
                    strategy_type=strategy_type,
                    parameters=new_params,
                    risk_parameters=new_risk_params,
                    change_log="手動編輯策略",
                    author="使用者",
                )
                st.success("策略已更新！")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"更新策略失敗: {e}")

    with col2:
        if st.button("🔙 返回清單"):
            st.session_state.current_tab = "list"
            st.session_state.selected_strategy = None
            st.experimental_rerun()
