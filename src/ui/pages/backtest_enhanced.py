"""
增強版回測系統頁面

此模組提供完整的回測系統功能，包括：
- 效能分析圖表
- 報告生成和匯出
- 參數敏感性分析
- 多策略比較
"""

import streamlit as st
import pandas as pd
import numpy as np
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import requests
import time

# 導入響應式設計組件
from ..responsive import (
    ResponsiveUtils,
    ResponsiveComponents,
    responsive_manager,
    apply_responsive_design,
)

# 導入回測組件
from ..components.backtest_charts import BacktestCharts
from ..components.backtest_reports import BacktestReports
from ..components.backtest_analysis import BacktestAnalysis
from ..components.common import UIComponents


def show_enhanced():
    """顯示增強版回測系統頁面"""
    # 應用響應式頁面配置
    ResponsiveUtils.apply_responsive_page_config(
        page_title="回測系統 - AI 交易系統", page_icon="📊"
    )

    # 頁面標題
    st.markdown('<h1 class="title-responsive">📊 回測系統</h1>', unsafe_allow_html=True)

    # 初始化會話狀態
    if "backtest_results" not in st.session_state:
        st.session_state.backtest_results = {}
    if "strategies_results" not in st.session_state:
        st.session_state.strategies_results = []

    # 響應式標籤頁
    tabs_config = [
        {"name": "🚀 執行回測", "content_func": show_backtest_execution},
        {"name": "📈 效能分析", "content_func": show_performance_analysis},
        {"name": "📄 報告匯出", "content_func": show_report_export},
        {"name": "🔍 敏感性分析", "content_func": show_sensitivity_analysis},
        {"name": "⚖️ 策略比較", "content_func": show_strategy_comparison},
    ]

    ResponsiveComponents.responsive_tabs(tabs_config)


def show_backtest_execution():
    """顯示回測執行介面"""
    st.subheader("回測執行")

    # 回測配置表單
    form_config = {
        "title": "回測配置",
        "fields": [
            {
                "key": "strategy_name",
                "label": "策略名稱",
                "type": "select",
                "options": ["動量策略", "均值回歸策略", "機器學習策略", "套利策略"],
            },
            {
                "key": "symbols",
                "label": "股票代碼",
                "type": "multiselect",
                "options": ["2330.TW", "2317.TW", "AAPL", "MSFT", "GOOGL", "TSLA"],
            },
            {
                "key": "start_date",
                "label": "開始日期",
                "type": "date",
                "default": datetime.now() - timedelta(days=365),
            },
            {
                "key": "end_date",
                "label": "結束日期",
                "type": "date",
                "default": datetime.now(),
            },
            {
                "key": "initial_capital",
                "label": "初始資金",
                "type": "number",
                "default": 1000000,
            },
        ],
    }

    form_data = ResponsiveComponents.responsive_form(
        form_config, "backtest_config_form"
    )

    if form_data:
        # 執行回測
        with st.spinner("正在執行回測..."):
            progress_bar = st.progress(0)
            status_text = st.empty()

            # 模擬回測執行過程
            for i in range(101):
                progress_bar.progress(i)
                if i < 30:
                    status_text.text("正在載入數據...")
                elif i < 60:
                    status_text.text("正在執行策略...")
                elif i < 90:
                    status_text.text("正在計算指標...")
                else:
                    status_text.text("正在生成報告...")
                time.sleep(0.02)

            # 生成模擬回測結果
            backtest_results = generate_mock_backtest_results(form_data)
            st.session_state.backtest_results = backtest_results

            # 添加到策略結果列表
            if backtest_results not in st.session_state.strategies_results:
                st.session_state.strategies_results.append(backtest_results)

            status_text.text("回測完成！")
            st.success("回測執行成功！")

            # 顯示基本結果
            show_basic_results(backtest_results)


def show_performance_analysis():
    """顯示效能分析"""
    st.subheader("效能分析圖表")

    if not st.session_state.backtest_results:
        st.info("請先執行回測以查看效能分析")
        return

    # 圖表選擇
    chart_options = {
        "cumulative_returns": "累積收益率曲線",
        "drawdown": "回撤分析圖",
        "rolling_sharpe": "滾動夏普比率",
        "monthly_heatmap": "月度收益熱力圖",
        "returns_distribution": "收益分佈直方圖",
        "trading_frequency": "交易頻率分析",
        "holding_period": "持倉時間分析",
    }

    selected_charts = st.multiselect(
        "選擇要顯示的圖表",
        options=list(chart_options.keys()),
        default=list(chart_options.keys()),
        format_func=lambda x: chart_options[x],
    )

    if selected_charts:
        # 渲染選中的圖表
        BacktestCharts.render_performance_charts(
            st.session_state.backtest_results, selected_charts
        )

    # 圖表匯出功能
    st.subheader("圖表匯出")

    cols = responsive_manager.create_responsive_columns(
        desktop_cols=3, tablet_cols=2, mobile_cols=1
    )

    with cols[0]:
        if st.button("匯出為 PNG", use_container_width=True):
            st.info("PNG 匯出功能開發中...")

    with cols[1 % len(cols)]:
        if st.button("匯出為 SVG", use_container_width=True):
            st.info("SVG 匯出功能開發中...")

    with cols[2 % len(cols)]:
        if st.button("匯出為 HTML", use_container_width=True):
            st.info("HTML 匯出功能開發中...")


def show_report_export():
    """顯示報告匯出功能"""
    st.subheader("報告生成與匯出")

    if not st.session_state.backtest_results:
        st.info("請先執行回測以生成報告")
        return

    # 檢查依賴項
    reports = BacktestReports()
    dependencies = reports.check_dependencies()

    # 顯示依賴項狀態
    st.subheader("依賴項狀態")

    dep_metrics = [
        {
            "title": "ReportLab (PDF)",
            "value": "✅ 可用" if dependencies["reportlab"] else "❌ 未安裝",
            "status": "success" if dependencies["reportlab"] else "error",
        },
        {
            "title": "XlsxWriter (Excel)",
            "value": "✅ 可用" if dependencies["xlsxwriter"] else "❌ 未安裝",
            "status": "success" if dependencies["xlsxwriter"] else "error",
        },
        {
            "title": "Jinja2 (HTML)",
            "value": "✅ 可用" if dependencies["jinja2"] else "❌ 未安裝",
            "status": "success" if dependencies["jinja2"] else "error",
        },
    ]

    ResponsiveComponents.responsive_metric_cards(
        dep_metrics, desktop_cols=3, tablet_cols=2, mobile_cols=1
    )

    # 報告匯出選項
    st.subheader("匯出選項")

    cols = responsive_manager.create_responsive_columns(
        desktop_cols=3, tablet_cols=2, mobile_cols=1
    )

    with cols[0]:
        if st.button(
            "📄 匯出 PDF 報告",
            use_container_width=True,
            disabled=not dependencies["reportlab"],
        ):
            if dependencies["reportlab"]:
                try:
                    with st.spinner("正在生成 PDF 報告..."):
                        pdf_data = reports.generate_pdf_report(
                            st.session_state.backtest_results
                        )

                        st.download_button(
                            label="下載 PDF 報告",
                            data=pdf_data,
                            file_name=f"backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf",
                        )
                        st.success("PDF 報告生成成功！")
                except Exception as e:
                    st.error(f"PDF 報告生成失敗：{e}")
            else:
                st.error("請安裝 reportlab 套件")

    with cols[1 % len(cols)]:
        if st.button(
            "📊 匯出 Excel 報告",
            use_container_width=True,
            disabled=not dependencies["xlsxwriter"],
        ):
            if dependencies["xlsxwriter"]:
                try:
                    with st.spinner("正在生成 Excel 報告..."):
                        excel_data = reports.generate_excel_report(
                            st.session_state.backtest_results
                        )

                        st.download_button(
                            label="下載 Excel 報告",
                            data=excel_data,
                            file_name=f"backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        )
                        st.success("Excel 報告生成成功！")
                except Exception as e:
                    st.error(f"Excel 報告生成失敗：{e}")
            else:
                st.error("請安裝 xlsxwriter 套件")

    with cols[2 % len(cols)]:
        if st.button(
            "🌐 匯出 HTML 報告",
            use_container_width=True,
            disabled=not dependencies["jinja2"],
        ):
            if dependencies["jinja2"]:
                try:
                    with st.spinner("正在生成 HTML 報告..."):
                        html_data = reports.generate_html_report(
                            st.session_state.backtest_results
                        )

                        st.download_button(
                            label="下載 HTML 報告",
                            data=html_data.encode("utf-8"),
                            file_name=f"backtest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
                            mime="text/html",
                        )
                        st.success("HTML 報告生成成功！")
                except Exception as e:
                    st.error(f"HTML 報告生成失敗：{e}")
            else:
                st.error("請安裝 jinja2 套件")

    # 報告預覽
    if dependencies["jinja2"]:
        st.subheader("HTML 報告預覽")

        if st.button("預覽 HTML 報告"):
            try:
                html_content = reports.generate_html_report(
                    st.session_state.backtest_results
                )
                st.components.v1.html(html_content, height=600, scrolling=True)
            except Exception as e:
                st.error(f"預覽生成失敗：{e}")


def show_sensitivity_analysis():
    """顯示參數敏感性分析"""
    st.subheader("參數敏感性分析")

    st.info("參數敏感性分析功能開發中...")

    # 模擬參數配置
    st.subheader("參數配置")

    param_form_config = {
        "title": "敏感性分析參數",
        "fields": [
            {
                "key": "param1",
                "label": "參數1 (移動平均週期)",
                "type": "select",
                "options": [5, 10, 15, 20, 25, 30],
            },
            {
                "key": "param2",
                "label": "參數2 (停損比例)",
                "type": "select",
                "options": [0.02, 0.03, 0.05, 0.08, 0.10],
            },
            {
                "key": "metric",
                "label": "評估指標",
                "type": "select",
                "options": ["total_return", "sharpe_ratio", "max_drawdown"],
            },
        ],
    }

    param_form_data = ResponsiveComponents.responsive_form(
        param_form_config, "sensitivity_form"
    )

    if param_form_data:
        st.success("參數敏感性分析配置已設定")

        # 這裡可以添加實際的敏感性分析邏輯
        st.info("執行敏感性分析...")


def show_strategy_comparison():
    """顯示策略比較"""
    st.subheader("多策略比較分析")

    if len(st.session_state.strategies_results) < 2:
        st.info("需要至少2個策略結果才能進行比較分析")
        return

    # 執行策略比較
    comparison_results = BacktestAnalysis.compare_strategies(
        st.session_state.strategies_results
    )

    if comparison_results:
        # 顯示策略排名表格
        BacktestAnalysis.render_strategy_ranking_table(comparison_results)

        # 顯示雷達圖
        st.subheader("策略比較雷達圖")
        radar_fig = BacktestAnalysis.render_strategy_comparison_radar(
            comparison_results
        )
        st.plotly_chart(radar_fig, use_container_width=True)

        # 顯示相關性矩陣
        st.subheader("指標相關性分析")
        correlation_matrix = comparison_results["correlation_matrix"]

        import plotly.express as px

        fig = px.imshow(
            correlation_matrix,
            text_auto=True,
            aspect="auto",
            title="策略指標相關性矩陣",
        )

        height = responsive_manager.get_chart_height(400)
        fig.update_layout(height=height)
        st.plotly_chart(fig, use_container_width=True)


def show_basic_results(backtest_results: Dict[str, Any]):
    """顯示基本回測結果"""
    st.subheader("回測結果摘要")

    metrics = backtest_results.get("metrics", {})

    # 使用響應式指標卡片
    result_metrics = [
        {
            "title": "總回報率",
            "value": f"{metrics.get('total_return', 0):.2%}",
            "status": "success" if metrics.get("total_return", 0) > 0 else "error",
        },
        {
            "title": "年化回報率",
            "value": f"{metrics.get('annual_return', 0):.2%}",
            "status": "success" if metrics.get("annual_return", 0) > 0 else "error",
        },
        {
            "title": "夏普比率",
            "value": f"{metrics.get('sharpe_ratio', 0):.3f}",
            "status": "success" if metrics.get("sharpe_ratio", 0) > 1 else "warning",
        },
        {
            "title": "最大回撤",
            "value": f"{metrics.get('max_drawdown', 0):.2%}",
            "status": "warning" if metrics.get("max_drawdown", 0) > 0.1 else "success",
        },
    ]

    ResponsiveComponents.responsive_metric_cards(
        result_metrics, desktop_cols=4, tablet_cols=2, mobile_cols=1
    )


def generate_mock_backtest_results(config: Dict[str, Any]) -> Dict[str, Any]:
    """生成模擬回測結果"""
    # 生成模擬的投資組合數據
    start_date = config.get("start_date", datetime.now() - timedelta(days=365))
    end_date = config.get("end_date", datetime.now())

    dates = pd.date_range(start=start_date, end=end_date, freq="D")

    # 模擬價格走勢
    initial_value = config.get("initial_capital", 1000000)
    returns = np.random.normal(0.0005, 0.02, len(dates))  # 日收益率
    cumulative_returns = np.cumprod(1 + returns) - 1
    portfolio_values = initial_value * (1 + cumulative_returns)

    # 計算回撤
    peak = np.maximum.accumulate(portfolio_values)
    drawdown = (portfolio_values - peak) / peak

    portfolio_data = []
    for i, date in enumerate(dates):
        portfolio_data.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "portfolio_value": portfolio_values[i],
                "daily_return": returns[i],
                "cumulative_return": cumulative_returns[i],
                "drawdown": drawdown[i],
            }
        )

    # 生成模擬交易記錄
    transactions = []
    symbols = config.get("symbols", ["2330.TW"])

    for i in range(50):  # 生成50筆交易
        random_date = np.random.choice(dates)
        random_symbol = np.random.choice(symbols)
        action = np.random.choice(["buy", "sell"])
        quantity = np.random.randint(100, 1000)
        price = np.random.uniform(50, 200)

        transactions.append(
            {
                "date": random_date.strftime("%Y-%m-%d"),
                "symbol": random_symbol,
                "action": action,
                "quantity": quantity,
                "price": price,
                "amount": quantity * price,
            }
        )

    # 計算績效指標
    total_return = (portfolio_values[-1] - initial_value) / initial_value
    annual_return = (1 + total_return) ** (252 / len(dates)) - 1
    volatility = np.std(returns) * np.sqrt(252)
    sharpe_ratio = annual_return / volatility if volatility > 0 else 0
    max_drawdown = np.min(drawdown)

    # 計算其他指標
    win_trades = sum(1 for r in returns if r > 0)
    win_rate = win_trades / len(returns)

    return {
        "strategy_name": config.get("strategy_name", "Unknown"),
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "initial_capital": initial_value,
        "final_capital": portfolio_values[-1],
        "portfolio_data": portfolio_data,
        "transactions": transactions,
        "positions": [],  # 可以添加持倉數據
        "metrics": {
            "total_return": total_return,
            "annual_return": annual_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "volatility": volatility,
            "win_rate": win_rate,
            "profit_factor": 1.5,  # 模擬值
            "total_trades": len(transactions),
            "avg_trade_return": total_return / len(transactions) if transactions else 0,
        },
    }


if __name__ == "__main__":
    show_enhanced()
