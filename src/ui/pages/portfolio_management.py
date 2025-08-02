"""
投資組合管理頁面 (整合版)

此模組整合了基本版和進階版投資組合管理功能，提供完整的投資組合管理系統：
- 投資組合清單和概覽
- 持倉調整和資產配置
- 績效比較和分析
- 風險分析儀表板 (進階功能)
- 資產配置優化器 (進階功能)
- 績效歸因分析 (進階功能)
- 再平衡建議系統 (進階功能)
- 整合分析報告 (進階功能)

Version: v2.0 (整合版)
Author: AI Trading System
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from typing import Dict, List, Optional
import sys
import os

# 添加項目根目錄到 Python 路徑
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from src.ui.components.charts import line_chart, bar_chart, pie_chart
    from src.ui.components.tables import data_table, filterable_table
    from src.core.portfolio import (
        EqualWeightPortfolio,
        MeanVariancePortfolio,
        RiskParityPortfolio,
        MaxSharpePortfolio,
        MinVariancePortfolio,
        simulate_portfolios,
    )
except ImportError:
    # 如果無法導入，使用備用方案
    line_chart = bar_chart = pie_chart = None
    data_table = filterable_table = None
    EqualWeightPortfolio = MeanVariancePortfolio = None
    RiskParityPortfolio = MaxSharpePortfolio = None
    MinVariancePortfolio = simulate_portfolios = None

# 導入進階功能組件 (整合版新增)
try:
    from src.ui.components.portfolio.risk_analysis import RiskAnalysisComponent
    from src.ui.components.portfolio.asset_allocation import AssetAllocationComponent
    from src.ui.components.portfolio.performance_attribution import (
        PerformanceAttributionComponent,
    )
    from src.ui.components.portfolio.rebalancing import RebalancingComponent
except ImportError:
    # 備用實現
    RiskAnalysisComponent = None
    AssetAllocationComponent = None
    PerformanceAttributionComponent = None
    RebalancingComponent = None


@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_mock_portfolio_data():
    """獲取模擬投資組合數據 (緩存版本)"""
    portfolios = [
        {
            "組合名稱": "主要投資組合",
            "總價值": 1500000,
            "現金": 150000,
            "股票價值": 1350000,
            "今日損益": 25000,
            "今日損益率": 1.69,
            "總損益": 150000,
            "總損益率": 11.11,
            "創建日期": "2024-01-15",
            "最後更新": "2024-12-19",
        },
        {
            "組合名稱": "成長型組合",
            "總價值": 800000,
            "現金": 50000,
            "股票價值": 750000,
            "今日損益": -8000,
            "今日損益率": -0.99,
            "總損益": 80000,
            "總損益率": 11.11,
            "創建日期": "2024-03-01",
            "最後更新": "2024-12-19",
        },
        {
            "組合名稱": "穩健型組合",
            "總價值": 600000,
            "現金": 100000,
            "股票價值": 500000,
            "今日損益": 3000,
            "今日損益率": 0.50,
            "總損益": 50000,
            "總損益率": 9.09,
            "創建日期": "2024-02-10",
            "最後更新": "2024-12-19",
        },
    ]
    return pd.DataFrame(portfolios)


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_mock_holdings_data(portfolio_name: str):
    """獲取模擬持倉數據 (緩存版本)"""
    if portfolio_name == "主要投資組合":
        holdings = [
            {
                "股票代碼": "2330.TW",
                "股票名稱": "台積電",
                "持股數量": 2000,
                "平均成本": 580,
                "現價": 625,
                "市值": 1250000,
                "權重": 83.33,
                "損益": 90000,
                "損益率": 7.76,
            },
            {
                "股票代碼": "2317.TW",
                "股票名稱": "鴻海",
                "股票數量": 1000,
                "平均成本": 100,
                "現價": 105,
                "市值": 105000,
                "權重": 7.00,
                "損益": 5000,
                "損益率": 5.00,
            },
            {
                "股票代碼": "2454.TW",
                "股票名稱": "聯發科",
                "持股數量": 200,
                "平均成本": 750,
                "現價": 800,
                "市值": 160000,
                "權重": 10.67,
                "損益": 10000,
                "損益率": 6.67,
            },
        ]
    elif portfolio_name == "成長型組合":
        holdings = [
            {
                "股票代碼": "2454.TW",
                "股票名稱": "聯發科",
                "持股數量": 500,
                "平均成本": 750,
                "現價": 800,
                "市值": 400000,
                "權重": 53.33,
                "損益": 25000,
                "損益率": 6.67,
            },
            {
                "股票代碼": "2308.TW",
                "股票名稱": "台達電",
                "持股數量": 800,
                "平均成本": 300,
                "現價": 320,
                "市值": 256000,
                "權重": 34.13,
                "損益": 16000,
                "損益率": 6.67,
            },
            {
                "股票代碼": "6505.TW",
                "股票名稱": "台塑化",
                "持股數量": 1000,
                "平均成本": 90,
                "現價": 94,
                "市值": 94000,
                "權重": 12.53,
                "損益": 4000,
                "損益率": 4.44,
            },
        ]
    else:  # 穩健型組合
        holdings = [
            {
                "股票代碼": "2412.TW",
                "股票名稱": "中華電",
                "持股數量": 2000,
                "平均成本": 120,
                "現價": 125,
                "市值": 250000,
                "權重": 50.00,
                "損益": 10000,
                "損益率": 4.17,
            },
            {
                "股票代碼": "2882.TW",
                "股票名稱": "國泰金",
                "持股數量": 3000,
                "平均成本": 50,
                "現價": 52,
                "市值": 156000,
                "權重": 31.20,
                "損益": 6000,
                "損益率": 4.00,
            },
            {
                "股票代碼": "0050.TW",
                "股票名稱": "元大台灣50",
                "持股數量": 800,
                "平均成本": 115,
                "現價": 118,
                "市值": 94400,
                "權重": 18.88,
                "損益": 2400,
                "損益率": 2.61,
            },
        ]
    return pd.DataFrame(holdings)


def get_mock_performance_data(portfolio_name: str, days: int = 30):
    """獲取模擬績效數據"""
    np.random.seed(hash(portfolio_name) % 1000)
    dates = pd.date_range(end=datetime.now(), periods=days, freq="D")

    # 根據組合類型設置不同的收益率特性
    if portfolio_name == "主要投資組合":
        daily_returns = np.random.normal(0.0008, 0.015, days)
    elif portfolio_name == "成長型組合":
        daily_returns = np.random.normal(0.0012, 0.025, days)
    else:  # 穩健型組合
        daily_returns = np.random.normal(0.0005, 0.008, days)

    # 計算累積收益
    cumulative_returns = np.cumprod(1 + daily_returns)

    # 設置初始價值
    if portfolio_name == "主要投資組合":
        initial_value = 1350000
    elif portfolio_name == "成長型組合":
        initial_value = 720000
    else:
        initial_value = 550000

    portfolio_values = initial_value * cumulative_returns

    return pd.DataFrame(
        {
            "日期": dates,
            "組合價值": portfolio_values,
            "日收益率": daily_returns,
            "累積收益率": cumulative_returns - 1,
        }
    )


def show():
    """顯示投資組合管理頁面"""
    st.title("📊 投資組合管理")

    # 檢查是否有進階組件可用
    has_advanced_components = all([
        RiskAnalysisComponent, AssetAllocationComponent,
        PerformanceAttributionComponent, RebalancingComponent
    ])

    if has_advanced_components:
        # 整合版標籤頁 (包含進階功能)
        tabs = st.tabs([
            "📋 組合清單",
            "⚖️ 持倉調整",
            "🎯 資產配置",
            "📈 績效比較",
            "🛡️ 風險分析",
            "🔧 配置優化",
            "📊 績效歸因",
            "⚖️ 再平衡"
        ])

        with tabs[0]:
            show_portfolio_list()
        with tabs[1]:
            show_position_adjustment()
        with tabs[2]:
            show_asset_allocation()
        with tabs[3]:
            show_performance_comparison()
        with tabs[4]:
            show_risk_analysis_dashboard()
        with tabs[5]:
            show_asset_allocation_optimizer()
        with tabs[6]:
            show_performance_attribution()
        with tabs[7]:
            show_rebalancing_system()
    else:
        # 基本版標籤頁
        st.info("⚠️ 進階組件不可用，使用基本功能")
        tabs = st.tabs(["📋 組合清單", "⚖️ 持倉調整", "🎯 資產配置", "📈 績效比較"])

        with tabs[0]:
            show_portfolio_list()
        with tabs[1]:
            show_position_adjustment()
        with tabs[2]:
            show_asset_allocation()
        with tabs[3]:
            show_performance_comparison()


def show_portfolio_list():
    """顯示組合清單"""
    st.subheader("📋 投資組合清單")

    # 獲取投資組合數據
    portfolios_df = get_mock_portfolio_data()

    # 顯示總覽卡片
    col1, col2, col3, col4 = st.columns(4)

    total_value = portfolios_df["總價值"].sum()
    total_pnl = portfolios_df["總損益"].sum()
    total_pnl_pct = (total_pnl / (total_value - total_pnl)) * 100
    avg_pnl_pct = portfolios_df["今日損益率"].mean()

    with col1:
        st.metric(
            "總資產價值",
            f"${total_value:,.0f}",
            f"{portfolios_df['今日損益'].sum():+,.0f}",
        )

    with col2:
        st.metric("總損益", f"${total_pnl:,.0f}", f"{total_pnl_pct:+.2f}%")

    with col3:
        st.metric("組合數量", len(portfolios_df), "")

    with col4:
        st.metric("平均今日收益率", f"{avg_pnl_pct:.2f}%", "")

    st.divider()

    # 投資組合列表
    st.subheader("投資組合詳情")

    # 格式化數據顯示
    display_df = portfolios_df.copy()
    for col in ["總價值", "現金", "股票價值", "今日損益", "總損益"]:
        display_df[col] = display_df[col].apply(lambda x: f"${x:,.0f}")

    for col in ["今日損益率", "總損益率"]:
        display_df[col] = display_df[col].apply(lambda x: f"{x:+.2f}%")

    # 使用可編輯表格
    edited_df = data_table(
        display_df,
        height=300,
        column_config={
            "組合名稱": st.column_config.TextColumn("組合名稱", width="medium"),
            "總價值": st.column_config.TextColumn("總價值", width="small"),
            "今日損益": st.column_config.TextColumn("今日損益", width="small"),
            "今日損益率": st.column_config.TextColumn("今日損益率", width="small"),
            "總損益": st.column_config.TextColumn("總損益", width="small"),
            "總損益率": st.column_config.TextColumn("總損益率", width="small"),
        },
    )

    # 選擇組合查看詳情
    st.subheader("組合詳情")
    selected_portfolio = st.selectbox(
        "選擇要查看的投資組合",
        portfolios_df["組合名稱"].tolist(),
        key="portfolio_selector",
    )

    if selected_portfolio:
        show_portfolio_details(selected_portfolio)


def show_portfolio_details(portfolio_name: str):
    """顯示投資組合詳情"""
    col1, col2 = st.columns([2, 1])

    with col1:
        # 持倉明細
        st.subheader("📈 持倉明細")
        holdings_df = get_mock_holdings_data(portfolio_name)

        # 格式化顯示
        display_holdings = holdings_df.copy()
        for col in ["平均成本", "現價"]:
            display_holdings[col] = display_holdings[col].apply(lambda x: f"${x:.2f}")
        for col in ["市值", "損益"]:
            display_holdings[col] = display_holdings[col].apply(lambda x: f"${x:,.0f}")
        for col in ["權重", "損益率"]:
            display_holdings[col] = display_holdings[col].apply(lambda x: f"{x:.2f}%")

        st.dataframe(display_holdings, use_container_width=True, hide_index=True)

        # 績效圖表
        st.subheader("📊 績效走勢")
        performance_df = get_mock_performance_data(portfolio_name, 30)

        # 使用 Plotly 繪製圖表
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=performance_df["日期"],
                y=performance_df["組合價值"],
                mode="lines",
                name="組合價值",
                line=dict(color="blue", width=2),
            )
        )

        fig.update_layout(
            title=f"{portfolio_name} - 30日績效走勢",
            xaxis_title="日期",
            yaxis_title="組合價值 ($)",
            template="plotly_white",
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 權重分布圓餅圖
        st.subheader("🥧 權重分布")

        # 準備圓餅圖數據
        pie_data = holdings_df[["股票名稱", "權重"]].copy()

        fig_pie = go.Figure(
            data=[
                go.Pie(labels=pie_data["股票名稱"], values=pie_data["權重"], hole=0.3)
            ]
        )

        fig_pie.update_layout(title="持倉權重分布", template="plotly_white", height=400)

        st.plotly_chart(fig_pie, use_container_width=True)

        # 績效指標
        st.subheader("📊 績效指標")
        performance_df = get_mock_performance_data(portfolio_name, 30)

        # 計算績效指標
        total_return = performance_df["累積收益率"].iloc[-1] * 100
        volatility = performance_df["日收益率"].std() * np.sqrt(252) * 100
        sharpe_ratio = (performance_df["日收益率"].mean() * 252) / (
            performance_df["日收益率"].std() * np.sqrt(252)
        )
        max_drawdown = (
            (performance_df["組合價值"] / performance_df["組合價值"].cummax()) - 1
        ).min() * 100

        st.metric("總收益率", f"{total_return:.2f}%")
        st.metric("年化波動率", f"{volatility:.2f}%")
        st.metric("夏普比率", f"{sharpe_ratio:.2f}")
        st.metric("最大回撤", f"{max_drawdown:.2f}%")


def show_position_adjustment():
    """顯示持倉調整"""
    st.subheader("⚖️ 持倉調整")

    # 選擇要調整的投資組合
    portfolios_df = get_mock_portfolio_data()
    selected_portfolio = st.selectbox(
        "選擇要調整的投資組合",
        portfolios_df["組合名稱"].tolist(),
        key="adjustment_portfolio_selector",
    )

    if selected_portfolio:
        col1, col2 = st.columns([3, 1])

        with col1:
            st.subheader("當前持倉")
            holdings_df = get_mock_holdings_data(selected_portfolio)

            # 創建可編輯的持倉表格
            edited_holdings = st.data_editor(
                holdings_df,
                column_config={
                    "股票代碼": st.column_config.TextColumn("股票代碼", disabled=True),
                    "股票名稱": st.column_config.TextColumn("股票名稱", disabled=True),
                    "持股數量": st.column_config.NumberColumn(
                        "持股數量", min_value=0, step=1
                    ),
                    "平均成本": st.column_config.NumberColumn(
                        "平均成本", disabled=True, format="$%.2f"
                    ),
                    "現價": st.column_config.NumberColumn(
                        "現價", disabled=True, format="$%.2f"
                    ),
                    "市值": st.column_config.NumberColumn(
                        "市值", disabled=True, format="$%.0f"
                    ),
                    "權重": st.column_config.NumberColumn(
                        "權重", disabled=True, format="%.2f%%"
                    ),
                    "損益": st.column_config.NumberColumn(
                        "損益", disabled=True, format="$%.0f"
                    ),
                    "損益率": st.column_config.NumberColumn(
                        "損益率", disabled=True, format="%.2f%%"
                    ),
                },
                use_container_width=True,
                hide_index=True,
                key="holdings_editor",
            )

            # 新增持倉
            st.subheader("新增持倉")
            with st.form("add_position_form"):
                col_a, col_b, col_c = st.columns(3)

                with col_a:
                    new_symbol = st.text_input("股票代碼", placeholder="例如: 2330.TW")
                    new_name = st.text_input("股票名稱", placeholder="例如: 台積電")

                with col_b:
                    new_shares = st.number_input("持股數量", min_value=0, step=1)
                    new_price = st.number_input(
                        "買入價格", min_value=0.0, step=0.01, format="%.2f"
                    )

                with col_c:
                    st.write("")  # 空白佔位
                    add_position = st.form_submit_button("新增持倉", type="primary")

                if (
                    add_position
                    and new_symbol
                    and new_name
                    and new_shares > 0
                    and new_price > 0
                ):
                    st.success(
                        f"已新增持倉: {new_symbol} {new_name}, 數量: {new_shares}, 價格: ${new_price:.2f}"
                    )

        with col2:
            st.subheader("調整操作")

            # 快速調整選項
            st.write("**快速調整**")

            if st.button("等權重分配", use_container_width=True):
                st.info("已將所有持倉調整為等權重分配")

            if st.button("清空所有持倉", use_container_width=True, type="secondary"):
                st.warning("已清空所有持倉")

            # 批量調整
            st.write("**批量調整**")
            adjustment_pct = st.slider("調整比例", -50, 50, 0, 5, format="%d%%")

            if st.button("應用調整", use_container_width=True):
                if adjustment_pct != 0:
                    st.info(f"已將所有持倉按 {adjustment_pct:+d}% 調整")

            # 風險控制
            st.write("**風險控制**")
            max_position_weight = st.slider(
                "單一持倉最大權重", 5, 50, 20, 5, format="%d%%"
            )

            if st.button("應用權重限制", use_container_width=True):
                st.info(f"已將單一持倉權重限制在 {max_position_weight}% 以內")

            # 保存變更
            st.divider()
            if st.button("💾 保存變更", use_container_width=True, type="primary"):
                st.success("持倉調整已保存！")


def show_asset_allocation():
    """顯示資產配置"""
    st.subheader("🎯 資產配置建議")

    # 配置參數
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("配置參數")

        # 選擇股票池
        st.write("**股票池選擇**")
        stock_universe = st.multiselect(
            "選擇股票",
            [
                "2330.TW 台積電",
                "2317.TW 鴻海",
                "2454.TW 聯發科",
                "2308.TW 台達電",
                "2412.TW 中華電",
                "2882.TW 國泰金",
                "1301.TW 台塑",
                "2881.TW 富邦金",
            ],
            default=[
                "2330.TW 台積電",
                "2317.TW 鴻海",
                "2454.TW 聯發科",
                "2308.TW 台達電",
            ],
        )

        # 配置方法
        st.write("**配置方法**")
        allocation_method = st.selectbox(
            "選擇配置方法",
            [
                "等權重配置",
                "風險平價配置",
                "均值方差最佳化",
                "最大夏普比率",
                "最小方差",
            ],
        )

        # 風險參數
        st.write("**風險參數**")
        if allocation_method == "均值方差最佳化":
            risk_aversion = st.slider("風險厭惡係數", 0.1, 5.0, 1.0, 0.1)
        elif allocation_method == "最大夏普比率":
            risk_free_rate = st.slider("無風險利率 (%)", 0.0, 5.0, 2.0, 0.1) / 100

        # 約束條件
        st.write("**約束條件**")
        max_weight = st.slider("單一股票最大權重 (%)", 10, 50, 30, 5) / 100
        min_weight = st.slider("單一股票最小權重 (%)", 0, 10, 5, 1) / 100

        # 生成配置
        if st.button("🎯 生成配置建議", type="primary", use_container_width=True):
            st.session_state.allocation_generated = True

    with col2:
        st.subheader("配置結果")

        if (
            hasattr(st.session_state, "allocation_generated")
            and st.session_state.allocation_generated
        ):
            # 模擬配置結果
            if stock_universe:
                # 生成模擬權重
                np.random.seed(42)
                n_stocks = len(stock_universe)

                if allocation_method == "等權重配置":
                    weights = np.ones(n_stocks) / n_stocks
                elif allocation_method == "風險平價配置":
                    # 模擬風險平價權重
                    weights = np.random.dirichlet(np.ones(n_stocks) * 2)
                else:
                    # 其他方法的模擬權重
                    weights = np.random.dirichlet(np.ones(n_stocks))

                # 應用約束條件
                weights = np.clip(weights, min_weight, max_weight)
                weights = weights / weights.sum()  # 重新標準化

                # 創建結果DataFrame
                allocation_df = pd.DataFrame(
                    {
                        "股票": [stock.split()[0] for stock in stock_universe],
                        "股票名稱": [
                            stock.split()[1] if len(stock.split()) > 1 else stock
                            for stock in stock_universe
                        ],
                        "建議權重": weights,
                        "建議權重(%)": weights * 100,
                    }
                )

                # 顯示配置表格
                st.write("**權重分配**")
                display_allocation = allocation_df[
                    ["股票", "股票名稱", "建議權重(%)"]
                ].copy()
                display_allocation["建議權重(%)"] = display_allocation[
                    "建議權重(%)"
                ].apply(lambda x: f"{x:.2f}%")

                st.dataframe(
                    display_allocation, use_container_width=True, hide_index=True
                )

                # 權重分布圖
                fig_allocation = go.Figure(
                    data=[
                        go.Pie(
                            labels=allocation_df["股票名稱"],
                            values=allocation_df["建議權重"],
                            hole=0.3,
                        )
                    ]
                )

                fig_allocation.update_layout(
                    title=f"{allocation_method} - 權重分布",
                    template="plotly_white",
                    height=400,
                )

                st.plotly_chart(fig_allocation, use_container_width=True)

                # 預期績效指標
                st.write("**預期績效指標**")
                col_a, col_b = st.columns(2)

                # 模擬績效指標
                expected_return = np.random.uniform(8, 15)
                expected_volatility = np.random.uniform(12, 25)
                expected_sharpe = expected_return / expected_volatility

                with col_a:
                    st.metric("預期年化收益率", f"{expected_return:.2f}%")
                    st.metric("預期年化波動率", f"{expected_volatility:.2f}%")

                with col_b:
                    st.metric("預期夏普比率", f"{expected_sharpe:.2f}")
                    st.metric("最大回撤預估", f"{np.random.uniform(8, 20):.2f}%")

                # 應用配置
                st.divider()
                if st.button("✅ 應用此配置", type="primary", use_container_width=True):
                    st.success("配置已應用到投資組合！")
            else:
                st.warning("請先選擇股票池")
        else:
            st.info("點擊「生成配置建議」來查看資產配置結果")

            # 顯示不同配置方法的說明
            st.write("**配置方法說明**")

            method_descriptions = {
                "等權重配置": "將資金平均分配給所有選定的股票，適合初學者或不確定市場方向時使用。",
                "風險平價配置": "根據各股票的風險貢獻度分配權重，風險較低的股票獲得較高權重。",
                "均值方差最佳化": "基於現代投資組合理論，在給定風險水平下最大化預期收益。",
                "最大夏普比率": "尋找風險調整後收益最高的投資組合配置。",
                "最小方差": "以最小化投資組合整體風險為目標的配置方法。",
            }

            for method, description in method_descriptions.items():
                with st.expander(f"📖 {method}"):
                    st.write(description)


def show_performance_comparison():
    """顯示績效比較"""
    st.subheader("📈 投資組合績效比較")

    # 比較設置
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("比較設置")

        # 選擇要比較的投資組合
        portfolios_df = get_mock_portfolio_data()
        selected_portfolios = st.multiselect(
            "選擇要比較的投資組合",
            portfolios_df["組合名稱"].tolist(),
            default=portfolios_df["組合名稱"].tolist(),
        )

        # 時間範圍
        st.write("**時間範圍**")
        time_period = st.selectbox(
            "選擇時間範圍",
            ["最近30天", "最近90天", "最近180天", "最近1年", "自創建以來"],
        )

        # 比較基準
        st.write("**比較基準**")
        benchmark = st.selectbox(
            "選擇比較基準", ["無", "台灣加權指數", "標普500", "納斯達克", "自定義基準"]
        )

        # 績效指標
        st.write("**顯示指標**")
        show_returns = st.checkbox("收益率曲線", value=True)
        show_drawdown = st.checkbox("回撤分析", value=True)
        show_metrics = st.checkbox("績效指標表", value=True)
        show_correlation = st.checkbox("相關性分析", value=False)

        # 更新比較
        if st.button("🔄 更新比較", type="primary", use_container_width=True):
            st.session_state.comparison_updated = True

    with col2:
        st.subheader("比較結果")

        if selected_portfolios and len(selected_portfolios) > 0:
            # 獲取時間範圍對應的天數
            days_map = {
                "最近30天": 30,
                "最近90天": 90,
                "最近180天": 180,
                "最近1年": 365,
                "自創建以來": 365,
            }
            days = days_map.get(time_period, 30)

            # 收益率曲線比較
            if show_returns:
                st.write("**📊 收益率曲線比較**")

                fig_comparison = go.Figure()

                for portfolio in selected_portfolios:
                    performance_df = get_mock_performance_data(portfolio, days)

                    fig_comparison.add_trace(
                        go.Scatter(
                            x=performance_df["日期"],
                            y=performance_df["累積收益率"] * 100,
                            mode="lines",
                            name=portfolio,
                            line=dict(width=2),
                        )
                    )

                # 添加基準指數（如果選擇）
                if benchmark != "無":
                    # 模擬基準數據
                    benchmark_data = get_mock_performance_data(
                        f"基準_{benchmark}", days
                    )
                    fig_comparison.add_trace(
                        go.Scatter(
                            x=benchmark_data["日期"],
                            y=benchmark_data["累積收益率"] * 100,
                            mode="lines",
                            name=benchmark,
                            line=dict(width=2, dash="dash", color="gray"),
                        )
                    )

                fig_comparison.update_layout(
                    title="累積收益率比較",
                    xaxis_title="日期",
                    yaxis_title="累積收益率 (%)",
                    template="plotly_white",
                    height=400,
                    legend=dict(
                        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                    ),
                )

                st.plotly_chart(fig_comparison, use_container_width=True)

            # 回撤分析
            if show_drawdown:
                st.write("**📉 回撤分析**")

                fig_drawdown = go.Figure()

                for portfolio in selected_portfolios:
                    performance_df = get_mock_performance_data(portfolio, days)

                    # 計算回撤
                    cumulative_values = performance_df["組合價值"]
                    running_max = cumulative_values.cummax()
                    drawdown = (cumulative_values / running_max - 1) * 100

                    fig_drawdown.add_trace(
                        go.Scatter(
                            x=performance_df["日期"],
                            y=drawdown,
                            mode="lines",
                            name=f"{portfolio} 回撤",
                            fill=(
                                "tonexty"
                                if portfolio == selected_portfolios[0]
                                else None
                            ),
                            line=dict(width=2),
                        )
                    )

                fig_drawdown.update_layout(
                    title="回撤分析",
                    xaxis_title="日期",
                    yaxis_title="回撤 (%)",
                    template="plotly_white",
                    height=300,
                )

                st.plotly_chart(fig_drawdown, use_container_width=True)

            # 績效指標表
            if show_metrics:
                st.write("**📋 績效指標比較**")

                metrics_data = []
                for portfolio in selected_portfolios:
                    performance_df = get_mock_performance_data(portfolio, days)

                    # 計算績效指標
                    total_return = performance_df["累積收益率"].iloc[-1] * 100
                    volatility = performance_df["日收益率"].std() * np.sqrt(252) * 100
                    sharpe_ratio = (performance_df["日收益率"].mean() * 252) / (
                        performance_df["日收益率"].std() * np.sqrt(252)
                    )

                    # 計算最大回撤
                    cumulative_values = performance_df["組合價值"]
                    running_max = cumulative_values.cummax()
                    max_drawdown = ((cumulative_values / running_max) - 1).min() * 100

                    # 計算勝率（正收益日數比例）
                    win_rate = (performance_df["日收益率"] > 0).mean() * 100

                    metrics_data.append(
                        {
                            "投資組合": portfolio,
                            "總收益率 (%)": f"{total_return:.2f}",
                            "年化波動率 (%)": f"{volatility:.2f}",
                            "夏普比率": f"{sharpe_ratio:.2f}",
                            "最大回撤 (%)": f"{max_drawdown:.2f}",
                            "勝率 (%)": f"{win_rate:.2f}",
                        }
                    )

                metrics_df = pd.DataFrame(metrics_data)
                st.dataframe(metrics_df, use_container_width=True, hide_index=True)

            # 相關性分析
            if show_correlation and len(selected_portfolios) > 1:
                st.write("**🔗 相關性分析**")

                # 構建收益率矩陣
                returns_matrix = pd.DataFrame()
                for portfolio in selected_portfolios:
                    performance_df = get_mock_performance_data(portfolio, days)
                    returns_matrix[portfolio] = performance_df["日收益率"]

                # 計算相關性矩陣
                correlation_matrix = returns_matrix.corr()

                # 繪製熱力圖
                fig_corr = go.Figure(
                    data=go.Heatmap(
                        z=correlation_matrix.values,
                        x=correlation_matrix.columns,
                        y=correlation_matrix.columns,
                        colorscale="RdBu",
                        zmid=0,
                        text=correlation_matrix.round(3).values,
                        texttemplate="%{text}",
                        textfont={"size": 12},
                        hoverongaps=False,
                    )
                )

                fig_corr.update_layout(
                    title="投資組合相關性矩陣", template="plotly_white", height=400
                )

                st.plotly_chart(fig_corr, use_container_width=True)

                # 相關性解釋
                st.info(
                    """
                **相關性解釋：**
                - 1.0：完全正相關
                - 0.0：無相關性
                - -1.0：完全負相關
                - 相關性越低，分散化效果越好
                """
                )

        else:
            st.warning("請選擇至少一個投資組合進行比較")


# ==================== 整合的進階功能 ====================

def show_risk_analysis_dashboard():
    """顯示風險分析儀表板 (進階功能)"""
    st.subheader("🛡️ 風險分析儀表板")

    if RiskAnalysisComponent is None:
        st.error("❌ 風險分析組件不可用")
        return

    # 選擇投資組合
    portfolios_df = get_mock_portfolio_data()
    selected_portfolio = st.selectbox(
        "選擇投資組合進行風險分析",
        portfolios_df["組合名稱"].tolist(),
        key="risk_analysis_portfolio"
    )

    if selected_portfolio:
        # 載入投資組合數據
        portfolio_data = load_portfolio_data_for_analysis(selected_portfolio)

        # 渲染風險分析儀表板
        risk_component = RiskAnalysisComponent()
        risk_component.render_risk_dashboard(portfolio_data)


def show_asset_allocation_optimizer():
    """顯示資產配置優化器 (進階功能)"""
    st.subheader("🔧 資產配置優化器")

    if AssetAllocationComponent is None:
        st.error("❌ 資產配置組件不可用")
        return

    # 選擇投資組合
    portfolios_df = get_mock_portfolio_data()
    selected_portfolio = st.selectbox(
        "選擇投資組合進行配置優化",
        portfolios_df["組合名稱"].tolist(),
        key="allocation_optimizer_portfolio"
    )

    if selected_portfolio:
        # 載入投資組合數據
        portfolio_data = load_portfolio_data_for_analysis(selected_portfolio)

        # 渲染資產配置優化器
        allocation_component = AssetAllocationComponent()
        allocation_component.render_allocation_optimizer(portfolio_data)


def show_performance_attribution():
    """顯示績效歸因分析 (進階功能)"""
    st.subheader("📊 績效歸因分析")

    if PerformanceAttributionComponent is None:
        st.error("❌ 績效歸因組件不可用")
        return

    # 選擇投資組合
    portfolios_df = get_mock_portfolio_data()
    selected_portfolio = st.selectbox(
        "選擇投資組合進行績效歸因",
        portfolios_df["組合名稱"].tolist(),
        key="performance_attribution_portfolio"
    )

    if selected_portfolio:
        # 載入投資組合數據
        portfolio_data = load_portfolio_data_for_analysis(selected_portfolio)

        # 渲染績效歸因分析
        attribution_component = PerformanceAttributionComponent()
        attribution_component.render_performance_attribution(portfolio_data)


def show_rebalancing_system():
    """顯示再平衡建議系統 (進階功能)"""
    st.subheader("⚖️ 再平衡建議系統")

    if RebalancingComponent is None:
        st.error("❌ 再平衡組件不可用")
        return

    # 選擇投資組合
    portfolios_df = get_mock_portfolio_data()
    selected_portfolio = st.selectbox(
        "選擇投資組合進行再平衡分析",
        portfolios_df["組合名稱"].tolist(),
        key="rebalancing_portfolio"
    )

    if selected_portfolio:
        # 載入投資組合數據
        portfolio_data = load_portfolio_data_for_analysis(selected_portfolio)

        # 渲染再平衡建議系統
        rebalancing_component = RebalancingComponent()
        rebalancing_component.render_rebalancing_system(portfolio_data)


def load_portfolio_data_for_analysis(portfolio_name: str) -> Dict[str, Any]:
    """載入投資組合數據用於進階分析

    Args:
        portfolio_name: 投資組合名稱

    Returns:
        包含分析所需數據的字典
    """
    # 生成模擬數據用於進階分析
    holdings_df = get_mock_holdings_data(portfolio_name)
    performance_df = get_mock_performance_data(portfolio_name, 252)  # 一年數據

    # 計算基本指標
    total_value = holdings_df["市值"].sum()
    total_return = performance_df["累積收益率"].iloc[-1]
    annual_volatility = performance_df["日收益率"].std() * np.sqrt(252)
    sharpe_ratio = (performance_df["日收益率"].mean() * 252) / annual_volatility
    max_drawdown = ((performance_df["組合價值"] / performance_df["組合價值"].cummax()) - 1).min()

    return {
        "name": portfolio_name,
        "total_value": total_value,
        "daily_change": np.random.uniform(-5000, 5000),
        "annual_return": total_return,
        "return_vs_benchmark": np.random.uniform(-0.05, 0.05),
        "annual_volatility": annual_volatility,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "holdings": holdings_df,
        "performance": performance_df,
        "risk_metrics": {
            "var_95": np.random.uniform(0.02, 0.05),
            "cvar_95": np.random.uniform(0.03, 0.07),
            "beta": np.random.uniform(0.8, 1.2),
            "alpha": np.random.uniform(-0.02, 0.02)
        }
    }


if __name__ == "__main__":
    show()
