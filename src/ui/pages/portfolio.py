"""
投資組合管理頁面

此模組實現完整的投資組合管理功能，包括：
- 投資組合展示和管理
- 手動權重調整
- 資產配置建議
- 組合績效比較
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# 導入投資組合服務
from ...core.portfolio_service import PortfolioService, Portfolio, PortfolioHolding


# 初始化投資組合服務
@st.cache_resource
def get_portfolio_service():
    """獲取投資組合服務實例"""
    return PortfolioService()


def show():
    """顯示投資組合管理主頁面"""
    st.header("📊 投資組合管理")

    # 初始化 session state
    if "selected_portfolio_id" not in st.session_state:
        st.session_state.selected_portfolio_id = None
    if "portfolio_tab" not in st.session_state:
        st.session_state.portfolio_tab = 0

    # 創建標籤頁
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📋 組合管理", "⚙️ 手動調整", "🎯 配置建議", "📈 績效比較"]
    )

    with tab1:
        show_portfolio_management()

    with tab2:
        show_manual_adjustment()

    with tab3:
        show_allocation_suggestions()

    with tab4:
        show_performance_comparison()


def show_portfolio_management():
    """顯示投資組合管理頁面"""
    st.subheader("投資組合管理")

    service = get_portfolio_service()

    # 側邊欄：投資組合操作
    with st.sidebar:
        st.markdown("### 📋 投資組合操作")

        # 創建新投資組合
        if st.button("➕ 創建新投資組合", use_container_width=True):
            st.session_state.show_create_form = True

        # 獲取投資組合列表
        portfolios = service.get_portfolio_list()

        if portfolios:
            st.markdown("### 📂 現有投資組合")

            for portfolio in portfolios:
                col1, col2 = st.columns([3, 1])

                with col1:
                    if st.button(
                        f"📊 {portfolio['name']}",
                        key=f"select_{portfolio['id']}",
                        use_container_width=True,
                    ):
                        st.session_state.selected_portfolio_id = portfolio["id"]
                        st.rerun()

                with col2:
                    if st.button("🗑️", key=f"delete_{portfolio['id']}"):
                        if service.delete_portfolio(portfolio["id"]):
                            st.success("投資組合已刪除")
                            st.rerun()
                        else:
                            st.error("刪除失敗")

                st.caption(
                    f"市值: {portfolio['total_value']:,.0f} | 持倉: {portfolio['holdings_count']}"
                )
        else:
            st.info("尚無投資組合")

    # 主要內容區域
    if st.session_state.get("show_create_form", False):
        show_create_portfolio_form()
    elif st.session_state.selected_portfolio_id:
        show_portfolio_details()
    else:
        show_portfolio_overview()


def show_create_portfolio_form():
    """顯示創建投資組合表單"""
    st.markdown("### ➕ 創建新投資組合")

    service = get_portfolio_service()

    with st.form("create_portfolio_form"):
        col1, col2 = st.columns(2)

        with col1:
            portfolio_name = st.text_input(
                "投資組合名稱", placeholder="例如：成長型投資組合"
            )
            portfolio_description = st.text_area(
                "描述", placeholder="投資組合的投資策略和目標..."
            )

        with col2:
            total_value = st.number_input(
                "初始投資金額",
                min_value=10000,
                max_value=100000000,
                value=1000000,
                step=10000,
            )

        st.markdown("### 📈 選擇股票")

        # 獲取可用股票
        available_stocks = service.get_available_stocks()

        # 按交易所分組
        exchanges = sorted(list(set(s["exchange"] for s in available_stocks)))
        selected_exchange = st.selectbox("交易所", options=["全部"] + exchanges)

        # 過濾股票
        if selected_exchange == "全部":
            filtered_stocks = available_stocks
        else:
            filtered_stocks = [
                s for s in available_stocks if s["exchange"] == selected_exchange
            ]

        # 股票選擇
        selected_stocks = st.multiselect(
            "選擇股票",
            options=[f"{s['symbol']} - {s['name']}" for s in filtered_stocks],
            default=[f"{s['symbol']} - {s['name']}" for s in filtered_stocks[:5]],
        )

        # 權重分配方式
        weight_method = st.radio(
            "權重分配方式",
            options=["等權重", "自定義權重", "市值權重"],
            horizontal=True,
        )

        # 自定義權重設定
        custom_weights = {}
        if weight_method == "自定義權重" and selected_stocks:
            st.markdown("#### 設定權重")

            total_weight = 0
            for stock_option in selected_stocks:
                symbol = stock_option.split(" - ")[0]
                weight = st.slider(
                    f"{symbol} 權重 (%)",
                    min_value=0,
                    max_value=100,
                    value=int(100 / len(selected_stocks)),
                    key=f"weight_{symbol}",
                )
                custom_weights[symbol] = weight / 100
                total_weight += weight

            if abs(total_weight - 100) > 1:
                st.warning(f"⚠️ 權重總和為 {total_weight}%，建議調整至 100%")

        # 提交按鈕
        submitted = st.form_submit_button("🚀 創建投資組合", type="primary")

        if submitted:
            if not portfolio_name:
                st.error("請輸入投資組合名稱")
                return

            if not selected_stocks:
                st.error("請至少選擇一個股票")
                return

            # 準備持倉資料
            holdings_data = []

            for stock_option in selected_stocks:
                symbol = stock_option.split(" - ")[0]
                stock_info = next(s for s in available_stocks if s["symbol"] == symbol)

                # 計算權重
                if weight_method == "等權重":
                    weight = 1.0 / len(selected_stocks)
                elif weight_method == "自定義權重":
                    weight = custom_weights.get(symbol, 0)
                else:  # 市值權重（簡化為等權重）
                    weight = 1.0 / len(selected_stocks)

                # 計算數量
                market_value = weight * total_value
                quantity = market_value / stock_info["price"]

                holdings_data.append(
                    {
                        "symbol": symbol,
                        "name": stock_info["name"],
                        "quantity": quantity,
                        "price": stock_info["price"],
                        "sector": stock_info["sector"],
                        "exchange": stock_info["exchange"],
                    }
                )

            # 創建投資組合
            try:
                portfolio_id = service.create_portfolio(
                    name=portfolio_name,
                    description=portfolio_description,
                    holdings=holdings_data,
                )

                st.success(f"✅ 投資組合已創建！ID: {portfolio_id}")
                st.session_state.selected_portfolio_id = portfolio_id
                st.session_state.show_create_form = False
                st.rerun()

            except Exception as e:
                st.error(f"❌ 創建失敗: {str(e)}")

    # 取消按鈕
    if st.button("❌ 取消"):
        st.session_state.show_create_form = False
        st.rerun()


def show_portfolio_details():
    """顯示投資組合詳細資訊"""
    service = get_portfolio_service()
    portfolio = service.get_portfolio(st.session_state.selected_portfolio_id)

    if not portfolio:
        st.error("❌ 無法載入投資組合")
        return

    # 投資組合標題
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown(f"### 📊 {portfolio.name}")
        st.caption(portfolio.description)

    with col2:
        if st.button("📝 編輯"):
            st.session_state.show_edit_form = True

    with col3:
        if st.button("📋 複製"):
            new_name = f"{portfolio.name} (副本)"
            new_id = service.copy_portfolio(portfolio.id, new_name)
            if new_id:
                st.success("投資組合已複製")
                st.rerun()

    # 基本資訊
    st.markdown("### 📋 基本資訊")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("總市值", f"{portfolio.total_value:,.0f}")

    with col2:
        st.metric("持倉數量", len(portfolio.holdings))

    with col3:
        st.metric("創建日期", portfolio.created_at.strftime("%Y-%m-%d"))

    with col4:
        st.metric("更新日期", portfolio.updated_at.strftime("%Y-%m-%d"))

    # 持倉明細
    st.markdown("### 📈 持倉明細")

    if portfolio.holdings:
        # 創建持倉表格
        holdings_data = []
        for holding in portfolio.holdings:
            holdings_data.append(
                {
                    "股票代碼": holding.symbol,
                    "股票名稱": holding.name,
                    "數量": f"{holding.quantity:.0f}",
                    "價格": f"{holding.price:.2f}",
                    "市值": f"{holding.market_value:,.0f}",
                    "權重": f"{holding.weight:.2%}",
                    "行業": holding.sector,
                    "交易所": holding.exchange,
                }
            )

        holdings_df = pd.DataFrame(holdings_data)
        st.dataframe(holdings_df, use_container_width=True)

        # 權重分配視覺化
        st.markdown("### 📊 權重分配")

        col1, col2 = st.columns(2)

        with col1:
            # 圓餅圖
            fig_pie = px.pie(
                values=[h.weight for h in portfolio.holdings],
                names=[h.symbol for h in portfolio.holdings],
                title="權重分配 (圓餅圖)",
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col2:
            # 長條圖
            fig_bar = px.bar(
                x=[h.symbol for h in portfolio.holdings],
                y=[h.weight * 100 for h in portfolio.holdings],
                title="權重分配 (長條圖)",
                labels={"x": "股票代碼", "y": "權重 (%)"},
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # 績效指標
        st.markdown("### 📊 績效指標")

        metrics = service.calculate_portfolio_metrics(portfolio)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("年化報酬率", f"{metrics['annual_return']:.2%}")

        with col2:
            st.metric("年化波動率", f"{metrics['volatility']:.2%}")

        with col3:
            st.metric("夏普比率", f"{metrics['sharpe_ratio']:.2f}")

        with col4:
            st.metric("最大回撤", f"{metrics['max_drawdown']:.2%}")

        # 匯出功能
        st.markdown("### 📥 匯出功能")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📄 匯出 JSON"):
                data = service.export_portfolio_data(portfolio.id, "json")
                if data:
                    st.download_button(
                        "下載 JSON 檔案",
                        data,
                        f"portfolio_{portfolio.id[:8]}.json",
                        "application/json",
                    )

        with col2:
            if st.button("📊 匯出 CSV"):
                data = service.export_portfolio_data(portfolio.id, "csv")
                if data:
                    st.download_button(
                        "下載 CSV 檔案",
                        data,
                        f"portfolio_{portfolio.id[:8]}.csv",
                        "text/csv",
                    )

        with col3:
            if st.button("📈 匯出 Excel"):
                data = service.export_portfolio_data(portfolio.id, "excel")
                if data:
                    st.download_button(
                        "下載 Excel 檔案",
                        data,
                        f"portfolio_{portfolio.id[:8]}.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )

    else:
        st.info("此投資組合沒有持倉")


def show_portfolio_overview():
    """顯示投資組合總覽"""
    st.markdown("### 📊 投資組合總覽")

    service = get_portfolio_service()
    portfolios = service.get_portfolio_list()

    if not portfolios:
        st.info("🎯 尚無投資組合，請點擊左側「創建新投資組合」開始使用")
        return

    # 總覽統計
    total_value = sum(p["total_value"] for p in portfolios)
    total_holdings = sum(p["holdings_count"] for p in portfolios)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("投資組合數量", len(portfolios))

    with col2:
        st.metric("總市值", f"{total_value:,.0f}")

    with col3:
        st.metric("總持倉數", total_holdings)

    # 投資組合列表
    st.markdown("### 📋 投資組合列表")

    for portfolio in portfolios:
        with st.expander(f"📊 {portfolio['name']}"):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.write(f"**市值**: {portfolio['total_value']:,.0f}")

            with col2:
                st.write(f"**持倉數**: {portfolio['holdings_count']}")

            with col3:
                st.write(f"**創建**: {portfolio['created_at'][:10]}")

            with col4:
                if st.button("查看詳情", key=f"view_{portfolio['id']}"):
                    st.session_state.selected_portfolio_id = portfolio["id"]
                    st.rerun()


def show_manual_adjustment():
    """顯示手動調整頁面"""
    st.subheader("手動調整")

    service = get_portfolio_service()

    # 選擇投資組合
    portfolios = service.get_portfolio_list()

    if not portfolios:
        st.warning("⚠️ 請先創建投資組合")
        return

    # 投資組合選擇
    portfolio_options = [f"{p['name']} (ID: {p['id'][:8]}...)" for p in portfolios]
    selected_idx = st.selectbox(
        "選擇投資組合",
        options=range(len(portfolio_options)),
        format_func=lambda x: portfolio_options[x],
    )

    selected_portfolio = portfolios[selected_idx]
    portfolio = service.get_portfolio(selected_portfolio["id"])

    if not portfolio or not portfolio.holdings:
        st.warning("⚠️ 此投資組合沒有持倉")
        return

    st.markdown("---")

    # 當前權重顯示
    st.markdown("### 📊 當前權重配置")

    col1, col2 = st.columns([2, 1])

    with col1:
        # 權重調整滑桿
        st.markdown("#### 🎛️ 權重調整")

        new_weights = {}
        total_weight = 0

        for holding in portfolio.holdings:
            weight_pct = st.slider(
                f"{holding.symbol} - {holding.name}",
                min_value=0.0,
                max_value=100.0,
                value=holding.weight * 100,
                step=0.1,
                key=f"weight_slider_{holding.symbol}",
                help=f"當前權重: {holding.weight:.2%}",
            )
            new_weights[holding.symbol] = weight_pct / 100
            total_weight += weight_pct

        # 權重總和檢查
        if abs(total_weight - 100) > 0.1:
            st.warning(f"⚠️ 權重總和為 {total_weight:.1f}%，將自動正規化至 100%")

        # 快速調整按鈕
        st.markdown("#### ⚡ 快速調整")

        col_btn1, col_btn2, col_btn3 = st.columns(3)

        with col_btn1:
            if st.button("⚖️ 等權重", use_container_width=True):
                equal_weight = 100 / len(portfolio.holdings)
                for holding in portfolio.holdings:
                    st.session_state[f"weight_slider_{holding.symbol}"] = equal_weight
                st.rerun()

        with col_btn2:
            if st.button("🔄 重置", use_container_width=True):
                for holding in portfolio.holdings:
                    st.session_state[f"weight_slider_{holding.symbol}"] = (
                        holding.weight * 100
                    )
                st.rerun()

        with col_btn3:
            if st.button("📊 隨機分配", use_container_width=True):
                import random

                random_weights = [random.uniform(5, 30) for _ in portfolio.holdings]
                total_random = sum(random_weights)
                for i, holding in enumerate(portfolio.holdings):
                    normalized_weight = (random_weights[i] / total_random) * 100
                    st.session_state[f"weight_slider_{holding.symbol}"] = (
                        normalized_weight
                    )
                st.rerun()

    with col2:
        # 即時預覽
        st.markdown("#### 📈 調整預覽")

        # 計算調整後的市值
        adjusted_holdings = []
        for holding in portfolio.holdings:
            new_weight = new_weights[holding.symbol]
            new_market_value = new_weight * portfolio.total_value
            new_quantity = new_market_value / holding.price if holding.price > 0 else 0

            adjusted_holdings.append(
                {
                    "股票": holding.symbol,
                    "原權重": f"{holding.weight:.1%}",
                    "新權重": f"{new_weight:.1%}",
                    "變化": f"{(new_weight - holding.weight):.1%}",
                    "新市值": f"{new_market_value:,.0f}",
                }
            )

        preview_df = pd.DataFrame(adjusted_holdings)
        st.dataframe(preview_df, use_container_width=True)

        # 權重變化圖表
        symbols = [h.symbol for h in portfolio.holdings]
        old_weights = [h.weight * 100 for h in portfolio.holdings]
        new_weights_list = [new_weights[symbol] * 100 for symbol in symbols]

        fig = go.Figure()

        fig.add_trace(
            go.Bar(name="原權重", x=symbols, y=old_weights, marker_color="lightblue")
        )

        fig.add_trace(
            go.Bar(name="新權重", x=symbols, y=new_weights_list, marker_color="orange")
        )

        fig.update_layout(
            title="權重變化比較",
            xaxis_title="股票代碼",
            yaxis_title="權重 (%)",
            barmode="group",
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)

    # 應用調整
    st.markdown("---")

    col1, col2 = st.columns([3, 1])

    with col1:
        adjustment_reason = st.text_input(
            "調整原因",
            placeholder="例如：重新平衡投資組合、調整風險配置...",
            value="手動權重調整",
        )

    with col2:
        if st.button("✅ 應用調整", type="primary", use_container_width=True):
            if adjustment_reason.strip():
                # 正規化權重
                total = sum(new_weights.values())
                if total > 0:
                    normalized_weights = {k: v / total for k, v in new_weights.items()}

                    success = service.update_portfolio_weights(
                        portfolio.id, normalized_weights, adjustment_reason
                    )

                    if success:
                        st.success("✅ 權重調整已應用！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ 調整失敗")
                else:
                    st.error("❌ 權重總和不能為零")
            else:
                st.error("❌ 請輸入調整原因")


def show_allocation_suggestions():
    """顯示配置建議頁面"""
    st.subheader("配置建議")

    service = get_portfolio_service()

    # 選擇投資組合
    portfolios = service.get_portfolio_list()

    if not portfolios:
        st.warning("⚠️ 請先創建投資組合")
        return

    # 投資組合選擇
    portfolio_options = [f"{p['name']} (ID: {p['id'][:8]}...)" for p in portfolios]
    selected_idx = st.selectbox(
        "選擇投資組合",
        options=range(len(portfolio_options)),
        format_func=lambda x: portfolio_options[x],
    )

    selected_portfolio = portfolios[selected_idx]
    portfolio = service.get_portfolio(selected_portfolio["id"])

    if not portfolio or not portfolio.holdings:
        st.warning("⚠️ 此投資組合沒有持倉")
        return

    symbols = portfolio.get_symbols()

    st.markdown("---")

    # 配置建議選項
    st.markdown("### 🎯 配置建議選項")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📊 基本配置策略")

        if st.button("⚖️ 等權重配置", use_container_width=True):
            weights = service.optimize_equal_weight(symbols)
            service.save_optimization_suggestion(portfolio.id, "等權重配置", weights)
            st.success("✅ 等權重配置建議已生成")
            st.rerun()

        if st.button("🛡️ 風險平衡配置", use_container_width=True):
            with st.spinner("正在計算風險平衡配置..."):
                weights = service.optimize_risk_parity(symbols)
                service.save_optimization_suggestion(
                    portfolio.id, "風險平衡配置", weights
                )
                st.success("✅ 風險平衡配置建議已生成")
                st.rerun()

        if st.button("📉 最小變異數配置", use_container_width=True):
            with st.spinner("正在計算最小變異數配置..."):
                weights = service.optimize_minimum_variance(symbols)
                service.save_optimization_suggestion(
                    portfolio.id, "最小變異數配置", weights
                )
                st.success("✅ 最小變異數配置建議已生成")
                st.rerun()

    with col2:
        st.markdown("#### 📈 進階配置策略")

        if st.button("🚀 最大夏普比率配置", use_container_width=True):
            with st.spinner("正在計算最大夏普比率配置..."):
                weights = service.optimize_maximum_sharpe(symbols)
                service.save_optimization_suggestion(
                    portfolio.id, "最大夏普比率配置", weights
                )
                st.success("✅ 最大夏普比率配置建議已生成")
                st.rerun()

        # 均值變異數最佳化
        target_return = (
            st.number_input(
                "目標年化報酬率 (%)",
                min_value=0.0,
                max_value=50.0,
                value=10.0,
                step=0.5,
            )
            / 100
        )

        if st.button("🎯 均值變異數最佳化", use_container_width=True):
            with st.spinner("正在計算均值變異數最佳化..."):
                weights = service.optimize_mean_variance(symbols, target_return)
                service.save_optimization_suggestion(
                    portfolio.id, "均值變異數最佳化", weights
                )
                st.success("✅ 均值變異數最佳化建議已生成")
                st.rerun()

    # 顯示建議歷史
    st.markdown("### 📋 配置建議歷史")

    suggestions = service.get_optimization_suggestions(portfolio.id)

    if suggestions:
        for suggestion in suggestions:
            with st.expander(
                f"🎯 {suggestion['suggestion_type']} - {suggestion['created_at'][:19]}"
            ):
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    # 建議權重表格
                    suggestion_data = []
                    for symbol, weight in suggestion["suggested_weights"].items():
                        current_weight = next(
                            (
                                h.weight
                                for h in portfolio.holdings
                                if h.symbol == symbol
                            ),
                            0,
                        )
                        suggestion_data.append(
                            {
                                "股票": symbol,
                                "當前權重": f"{current_weight:.2%}",
                                "建議權重": f"{weight:.2%}",
                                "變化": f"{(weight - current_weight):.2%}",
                            }
                        )

                    suggestion_df = pd.DataFrame(suggestion_data)
                    st.dataframe(suggestion_df, use_container_width=True)

                with col2:
                    st.metric("預期報酬率", f"{suggestion['expected_return']:.2%}")
                    st.metric("預期風險", f"{suggestion['expected_risk']:.2%}")

                with col3:
                    st.metric("夏普比率", f"{suggestion['sharpe_ratio']:.2f}")

                    if not suggestion["is_applied"]:
                        if st.button(
                            "✅ 應用建議",
                            key=f"apply_{suggestion['suggestion_type']}",
                            use_container_width=True,
                        ):
                            success = service.apply_optimization_suggestion(
                                portfolio.id, suggestion["suggestion_type"]
                            )
                            if success:
                                st.success("✅ 建議已應用")
                                st.rerun()
                            else:
                                st.error("❌ 應用失敗")
                    else:
                        st.success("✅ 已應用")
    else:
        st.info("尚無配置建議，請點擊上方按鈕生成建議")


def show_performance_comparison():
    """顯示績效比較頁面"""
    st.subheader("績效比較")

    service = get_portfolio_service()
    portfolios = service.get_portfolio_list()

    if len(portfolios) < 2:
        st.warning("⚠️ 至少需要兩個投資組合才能進行比較")
        return

    # 選擇要比較的投資組合
    st.markdown("### 📊 選擇比較對象")

    portfolio_options = [f"{p['name']} (ID: {p['id'][:8]}...)" for p in portfolios]
    selected_portfolios = st.multiselect(
        "選擇投資組合",
        options=range(len(portfolio_options)),
        format_func=lambda x: portfolio_options[x],
        default=list(range(min(3, len(portfolios)))),  # 預設選擇前3個
    )

    if len(selected_portfolios) < 2:
        st.info("請至少選擇兩個投資組合進行比較")
        return

    # 獲取比較結果
    portfolio_ids = [portfolios[i]["id"] for i in selected_portfolios]
    comparison_data = service.compare_portfolios(portfolio_ids)

    if not comparison_data.get("portfolios"):
        st.error("❌ 無法載入投資組合資料")
        return

    st.markdown("---")

    # 基本資訊比較
    st.markdown("### 📋 基本資訊比較")

    basic_info_data = []
    for portfolio_info in comparison_data["portfolios"]:
        basic_info_data.append(
            {
                "投資組合": portfolio_info["name"],
                "總市值": f"{portfolio_info['total_value']:,.0f}",
                "持倉數量": portfolio_info["holdings_count"],
                "ID": portfolio_info["id"][:8] + "...",
            }
        )

    basic_df = pd.DataFrame(basic_info_data)
    st.dataframe(basic_df, use_container_width=True)

    # 績效指標比較
    st.markdown("### 📊 績效指標比較")

    metrics_comparison = comparison_data.get("metrics_comparison", {})

    if metrics_comparison:
        # 創建指標比較表格
        metrics_df_data = []

        for metric_name, portfolio_values in metrics_comparison.items():
            row = {"指標": metric_name}
            for portfolio_name, value in portfolio_values.items():
                if isinstance(value, float):
                    if (
                        "return" in metric_name.lower()
                        or "volatility" in metric_name.lower()
                    ):
                        row[portfolio_name] = f"{value:.2%}"
                    else:
                        row[portfolio_name] = f"{value:.3f}"
                else:
                    row[portfolio_name] = str(value)
            metrics_df_data.append(row)

        metrics_df = pd.DataFrame(metrics_df_data)
        st.dataframe(metrics_df, use_container_width=True)

        # 視覺化比較
        st.markdown("### 📈 視覺化比較")

        # 選擇要比較的指標
        available_metrics = list(metrics_comparison.keys())
        selected_metrics = st.multiselect(
            "選擇要比較的指標",
            options=available_metrics,
            default=available_metrics[:4],  # 預設選擇前4個指標
        )

        if selected_metrics:
            # 雷達圖
            fig = go.Figure()

            for portfolio_info in comparison_data["portfolios"]:
                portfolio_name = portfolio_info["name"]
                values = []

                for metric in selected_metrics:
                    value = metrics_comparison[metric][portfolio_name]
                    # 正規化數值用於雷達圖顯示
                    if isinstance(value, (int, float)):
                        values.append(abs(value))
                    else:
                        values.append(0)

                fig.add_trace(
                    go.Scatterpolar(
                        r=values,
                        theta=selected_metrics,
                        fill="toself",
                        name=portfolio_name,
                    )
                )

            fig.update_layout(
                polar=dict(
                    radialaxis=dict(
                        visible=True,
                        range=[
                            0,
                            max(
                                [
                                    max(metrics_comparison[m].values())
                                    for m in selected_metrics
                                    if isinstance(
                                        list(metrics_comparison[m].values())[0],
                                        (int, float),
                                    )
                                ]
                            ),
                        ],
                    )
                ),
                showlegend=True,
                title="投資組合績效比較 (雷達圖)",
            )

            st.plotly_chart(fig, use_container_width=True)

    # 相關性分析
    if comparison_data.get("correlation_matrix"):
        st.markdown("### 🔗 投資組合相關性分析")

        correlation_df = pd.DataFrame(comparison_data["correlation_matrix"])

        # 相關性熱力圖
        fig = px.imshow(
            correlation_df.values,
            x=correlation_df.columns,
            y=correlation_df.index,
            color_continuous_scale="RdBu",
            aspect="auto",
            title="投資組合報酬率相關性矩陣",
        )

        # 添加數值標註
        for i in range(len(correlation_df.index)):
            for j in range(len(correlation_df.columns)):
                fig.add_annotation(
                    x=j,
                    y=i,
                    text=f"{correlation_df.iloc[i, j]:.2f}",
                    showarrow=False,
                    font=dict(
                        color=(
                            "white" if abs(correlation_df.iloc[i, j]) > 0.5 else "black"
                        )
                    ),
                )

        st.plotly_chart(fig, use_container_width=True)

        # 相關性解釋
        avg_correlation = correlation_df.values[
            np.triu_indices_from(correlation_df.values, k=1)
        ].mean()

        st.info(
            f"""
        📊 **相關性分析結果**:
        - 平均相關性: {avg_correlation:.3f}
        - 相關性越接近1表示投資組合走勢越相似
        - 相關性越接近0表示投資組合走勢越獨立
        - 負相關性表示投資組合走勢相反
        """
        )

    # 匯出比較報告
    st.markdown("### 📥 匯出比較報告")

    if st.button("📄 匯出比較報告 (JSON)"):
        import json

        report_data = json.dumps(comparison_data, ensure_ascii=False, indent=2)
        st.download_button(
            "下載比較報告",
            report_data.encode("utf-8"),
            f"portfolio_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "application/json",
        )
