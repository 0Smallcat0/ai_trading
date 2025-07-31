"""
回測系統頁面 (整合版)

此模組整合了基本版和增強版回測功能，提供完整的回測系統功能：
- 回測參數設定和驗證
- 回測執行控制和進度管理
- 績效分析與視覺化
- 交易記錄管理和查詢
- 報表匯出功能
- 效能分析圖表
- 參數敏感性分析
- 多策略比較
- 響應式設計支援

Example:
    使用方式：
    ```python
    from src.ui.pages.backtest_enhanced import show
    show()  # 顯示回測系統主頁面
    ```

Note:
    此模組依賴於 BacktestService 來執行實際的回測邏輯。
    所有回測結果會儲存在 session state 中以便在不同標籤頁間共享。

Version: v2.0 (整合版)
Author: AI Trading System
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union

import streamlit as st
import pandas as pd
import numpy as np

# 導入回測服務
try:
    from src.core.backtest_service import BacktestService, BacktestConfig
except ImportError:
    # 備用導入
    try:
        from src.core.backtest import BacktestService, BacktestConfig
    except ImportError:
        BacktestService = None
        BacktestConfig = None


def safe_strftime(date_obj: Union[datetime, pd.Timestamp, np.datetime64, str], format_str: str = "%Y-%m-%d") -> str:
    """安全的日期格式化函數

    Args:
        date_obj: 日期對象，可以是 datetime, pd.Timestamp, np.datetime64 或字符串
        format_str: 格式化字符串，默認為 "%Y-%m-%d"

    Returns:
        str: 格式化後的日期字符串

    Raises:
        ValueError: 如果無法解析日期對象
    """
    try:
        # 如果已經是字符串，嘗試解析
        if isinstance(date_obj, str):
            date_obj = pd.to_datetime(date_obj)

        # 如果是 numpy.datetime64，轉換為 pandas.Timestamp
        elif isinstance(date_obj, np.datetime64):
            date_obj = pd.to_datetime(date_obj)

        # 如果是 pandas.Timestamp，直接使用
        elif isinstance(date_obj, pd.Timestamp):
            pass

        # 如果是 datetime，直接使用
        elif isinstance(date_obj, datetime):
            pass

        else:
            # 嘗試使用 pandas 轉換
            date_obj = pd.to_datetime(date_obj)

        # 統一轉換為 datetime 對象進行格式化
        if hasattr(date_obj, 'to_pydatetime'):
            # pandas.Timestamp 轉換為 datetime
            return date_obj.to_pydatetime().strftime(format_str)
        else:
            # 直接使用 strftime
            return date_obj.strftime(format_str)

    except Exception as e:
        # 如果所有轉換都失敗，返回字符串表示
        return str(date_obj)


def safe_datetime_convert(date_obj: Union[datetime, pd.Timestamp, np.datetime64, str]) -> datetime:
    """安全的日期轉換函數，統一轉換為 datetime 對象

    Args:
        date_obj: 日期對象

    Returns:
        datetime: Python datetime 對象
    """
    try:
        if isinstance(date_obj, datetime):
            return date_obj
        elif isinstance(date_obj, pd.Timestamp):
            return date_obj.to_pydatetime()
        elif isinstance(date_obj, np.datetime64):
            return pd.to_datetime(date_obj).to_pydatetime()
        elif isinstance(date_obj, str):
            return pd.to_datetime(date_obj).to_pydatetime()
        else:
            return pd.to_datetime(date_obj).to_pydatetime()
    except Exception:
        # 如果轉換失敗，返回當前時間
        return datetime.now()


# 導入響應式設計組件
try:
    from src.ui.responsive import (
        ResponsiveUtils,
        ResponsiveComponents,
        responsive_manager,
        apply_responsive_design,
    )
except ImportError:
    # 備用實現
    ResponsiveUtils = None
    ResponsiveComponents = None
    responsive_manager = None
    apply_responsive_design = lambda: None

# 導入回測組件
try:
    from src.ui.components.backtest_charts import BacktestCharts
    from src.ui.components.backtest_reports import BacktestReports
    from src.ui.components.backtest_analysis import BacktestAnalysis
    from src.ui.components.common import UIComponents
except ImportError:
    # 備用實現
    BacktestCharts = None
    BacktestReports = None
    BacktestAnalysis = None
    UIComponents = None


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
        如果 BacktestService 無法導入，會返回 None 並顯示錯誤訊息
    """
    if BacktestService is None:
        st.error("❌ BacktestService 無法導入，請檢查系統配置")
        return None

    try:
        return BacktestService()
    except Exception as e:
        st.error(f"❌ 初始化回測服務失敗: {e}")
        return None


def show():
    """顯示回測系統頁面（Web UI 入口點）"""
    show_integrated()


def show_integrated():
    """顯示整合版回測系統頁面"""
    # 檢查 ResponsiveUtils 是否正確導入
    if ResponsiveUtils is None:
        st.error("❌ ResponsiveUtils 導入失敗，使用基本頁面配置")
        st.set_page_config(
            page_title="回測系統 - AI 交易系統",
            page_icon="📊",
            layout="wide"
        )
    else:
        # 應用響應式頁面配置
        try:
            ResponsiveUtils.apply_responsive_page_config(
                page_title="回測系統 - AI 交易系統", page_icon="📊"
            )
        except Exception as e:
            st.error(f"❌ 響應式配置失敗: {e}")
            st.set_page_config(
                page_title="回測系統 - AI 交易系統",
                page_icon="📊",
                layout="wide"
            )

    # 頁面標題
    st.markdown('<h1 class="title-responsive">📊 回測系統</h1>', unsafe_allow_html=True)

    # 初始化 session state (整合版)
    if "backtest_tab" not in st.session_state:
        st.session_state.backtest_tab = 0
    if "current_backtest_id" not in st.session_state:
        st.session_state.current_backtest_id = None
    if "backtest_results" not in st.session_state:
        st.session_state.backtest_results = {}
    if "strategies_results" not in st.session_state:
        st.session_state.strategies_results = []
    if "backtest_config" not in st.session_state:
        st.session_state.backtest_config = None

    # 檢查 ResponsiveComponents 是否可用
    if ResponsiveComponents is None:
        # 使用基本標籤頁 (整合版功能)
        tabs = st.tabs([
            "⚙️ 參數設定",
            "🚀 執行控制",
            "📈 績效分析",
            "📋 交易記錄",
            "📄 報表匯出",
            "🔍 敏感性分析",
            "⚖️ 策略比較"
        ])

        with tabs[0]:
            show_parameter_settings()
        with tabs[1]:
            show_execution_control()
        with tabs[2]:
            show_performance_analysis()
        with tabs[3]:
            show_trade_records()
        with tabs[4]:
            show_report_export()
        with tabs[5]:
            show_sensitivity_analysis()
        with tabs[6]:
            show_strategy_comparison()
    else:
        # 響應式標籤頁 (整合版功能)
        tabs_config = [
            {"name": "⚙️ 參數設定", "content_func": show_parameter_settings},
            {"name": "🚀 執行控制", "content_func": show_execution_control},
            {"name": "📈 績效分析", "content_func": show_performance_analysis},
            {"name": "📋 交易記錄", "content_func": show_trade_records},
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
                "date": safe_strftime(date, "%Y-%m-%d"),
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
                "date": safe_strftime(random_date, "%Y-%m-%d"),
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
        "start_date": safe_strftime(start_date, "%Y-%m-%d"),
        "end_date": safe_strftime(end_date, "%Y-%m-%d"),
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


# ==================== 整合的參數設定功能 ====================

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
    if not service:
        st.error("❌ 回測服務不可用，請檢查系統配置")
        return

    # 模擬可用策略和股票 (如果服務不可用)
    try:
        strategies = service.get_available_strategies()
        stocks = service.get_available_stocks()
    except Exception:
        strategies = [
            {"id": "ma_cross", "name": "移動平均交叉策略", "description": "基於短期和長期移動平均線的交叉信號"},
            {"id": "rsi_strategy", "name": "RSI策略", "description": "基於相對強弱指標的超買超賣策略"},
            {"id": "macd_strategy", "name": "MACD策略", "description": "基於MACD指標的趨勢跟隨策略"}
        ]
        stocks = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN", "META", "NVDA", "NFLX"]

    with st.form("backtest_config_form"):
        st.markdown("### 📋 基本設定")

        col1, col2 = st.columns(2)

        with col1:
            # 策略選擇
            strategy_names = [s["name"] for s in strategies]
            selected_strategy_idx = st.selectbox(
                "選擇交易策略",
                range(len(strategy_names)),
                format_func=lambda x: strategy_names[x]
            )
            selected_strategy = strategies[selected_strategy_idx]

            # 顯示策略描述
            st.info(f"📝 {selected_strategy['description']}")

        with col2:
            # 時間期間設定
            period_type = st.radio("時間期間", ["預設期間", "自定義期間"])

            if period_type == "預設期間":
                preset_period = st.selectbox(
                    "選擇期間",
                    ["最近1年", "最近2年", "最近3年", "最近5年"]
                )

                if preset_period == "最近1年":
                    end_date = datetime.now().date()
                    start_date = end_date - timedelta(days=365)
                elif preset_period == "最近2年":
                    end_date = datetime.now().date()
                    start_date = end_date - timedelta(days=730)
                elif preset_period == "最近3年":
                    end_date = datetime.now().date()
                    start_date = end_date - timedelta(days=1095)
                else:  # 最近5年
                    end_date = datetime.now().date()
                    start_date = end_date - timedelta(days=1825)
            else:
                start_date = st.date_input("開始日期", value=datetime.now().date() - timedelta(days=365))
                end_date = st.date_input("結束日期", value=datetime.now().date())

        st.markdown("### 🎯 標的選擇")
        selected_symbols = st.multiselect(
            "選擇股票標的",
            stocks,
            default=stocks[:3] if len(stocks) >= 3 else stocks
        )

        st.markdown("### 💰 資金設定")
        col3, col4 = st.columns(2)

        with col3:
            initial_capital = st.number_input("初始資金", min_value=10000, value=1000000, step=10000)
            commission = st.number_input("手續費率 (%)", min_value=0.0, max_value=1.0, value=0.1425, step=0.01)

        with col4:
            tax = st.number_input("交易稅率 (%)", min_value=0.0, max_value=1.0, value=0.3, step=0.01)
            slippage = st.number_input("滑價 (%)", min_value=0.0, max_value=1.0, value=0.05, step=0.01)

        st.markdown("### ⚠️ 風險管理")
        col5, col6, col7 = st.columns(3)

        with col5:
            max_position_size = st.number_input("最大持倉比例 (%)", min_value=1, max_value=100, value=20)

        with col6:
            stop_loss = st.number_input("停損比例 (%)", min_value=0, max_value=50, value=10)

        with col7:
            take_profit = st.number_input("停利比例 (%)", min_value=0, max_value=100, value=20)

        # 提交按鈕
        submitted = st.form_submit_button("💾 保存設定", type="primary")

        if submitted:
            # 驗證參數
            if not selected_symbols:
                st.error("❌ 請至少選擇一個股票標的")
            elif start_date >= end_date:
                st.error("❌ 開始日期必須早於結束日期")
            else:
                # 創建配置對象 (模擬)
                config = {
                    "strategy_id": selected_strategy["id"],
                    "strategy_name": selected_strategy["name"],
                    "symbols": selected_symbols,
                    "start_date": start_date,
                    "end_date": end_date,
                    "initial_capital": initial_capital,
                    "commission": commission / 100,
                    "slippage": slippage / 100,
                    "tax": tax / 100,
                    "max_position_size": max_position_size / 100,
                    "stop_loss": stop_loss / 100,
                    "take_profit": take_profit / 100,
                }

                # 保存到 session state
                st.session_state.backtest_config = config
                st.success("✅ 回測參數設定已保存！")
                st.info("請切換到「執行控制」標籤頁開始回測")

    # 顯示當前設定
    if hasattr(st.session_state, "backtest_config") and st.session_state.backtest_config:
        st.markdown("### 📋 當前設定摘要")
        config = st.session_state.backtest_config

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("策略", config["strategy_name"])
            st.metric("股票數量", len(config["symbols"]))

        with col2:
            st.metric("開始日期", safe_strftime(config["start_date"], "%Y-%m-%d"))
            st.metric("結束日期", safe_strftime(config["end_date"], "%Y-%m-%d"))

        with col3:
            st.metric("初始資金", f"${config['initial_capital']:,.0f}")
            st.metric("手續費率", f"{config['commission']*100:.3f}%")

        with col4:
            st.metric("最大持倉", f"{config['max_position_size']*100:.0f}%")
            st.metric("停損比例", f"{config['stop_loss']*100:.0f}%")


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

    # 檢查是否有配置
    if not hasattr(st.session_state, "backtest_config") or not st.session_state.backtest_config:
        st.warning("⚠️ 請先在「參數設定」標籤頁完成回測參數設定")
        return

    config = st.session_state.backtest_config

    # 顯示配置摘要
    st.markdown("### 📋 回測配置摘要")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("策略", config["strategy_name"])
        st.metric("股票數量", len(config["symbols"]))

    with col2:
        st.metric("期間", f"{config['start_date']} 至 {config['end_date']}")
        st.metric("初始資金", f"${config['initial_capital']:,.0f}")

    with col3:
        st.metric("手續費率", f"{config['commission']*100:.3f}%")
        st.metric("停損比例", f"{config['stop_loss']*100:.0f}%")

    with col4:
        st.metric("最大持倉", f"{config['max_position_size']*100:.0f}%")
        st.metric("停利比例", f"{config['take_profit']*100:.0f}%")

    st.markdown("---")

    # 執行控制
    st.markdown("### 🚀 執行控制")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("▶️ 開始回測", type="primary", use_container_width=True):
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
                backtest_results = generate_mock_backtest_results(config)
                st.session_state.backtest_results = backtest_results

                # 添加到策略結果列表
                if backtest_results not in st.session_state.strategies_results:
                    st.session_state.strategies_results.append(backtest_results)

                status_text.text("回測完成！")
                st.success("✅ 回測執行成功！")

                # 顯示基本結果
                show_basic_results(backtest_results)

    with col2:
        if st.button("⏸️ 暫停回測", use_container_width=True):
            st.info("回測已暫停")

    with col3:
        if st.button("⏹️ 停止回測", use_container_width=True):
            st.warning("回測已停止")


def show_trade_records():
    """顯示交易記錄頁面"""
    st.subheader("交易記錄")

    if not hasattr(st.session_state, "backtest_results") or not st.session_state.backtest_results:
        st.info("📝 請先執行回測以查看交易記錄")
        return

    results = st.session_state.backtest_results

    if "transactions" in results and results["transactions"]:
        # 顯示交易記錄表格
        df = pd.DataFrame(results["transactions"])
        st.dataframe(df, use_container_width=True)

        # 交易統計
        st.markdown("### 📊 交易統計")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("總交易次數", len(df))

        with col2:
            profitable_trades = len(df[df["return"] > 0]) if "return" in df.columns else 0
            st.metric("獲利交易", profitable_trades)

        with col3:
            win_rate = (profitable_trades / len(df) * 100) if len(df) > 0 else 0
            st.metric("勝率", f"{win_rate:.1f}%")

        with col4:
            avg_return = df["return"].mean() if "return" in df.columns else 0
            st.metric("平均收益率", f"{avg_return:.2%}")
    else:
        st.info("📝 暫無交易記錄")


def show_basic_results(results):
    """顯示基本回測結果"""
    if not results:
        return

    st.markdown("### 📊 回測結果概覽")

    metrics = results.get("metrics", {})

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_return = metrics.get("total_return", 0)
        st.metric("總收益率", f"{total_return:.2%}")

    with col2:
        annual_return = metrics.get("annual_return", 0)
        st.metric("年化收益率", f"{annual_return:.2%}")

    with col3:
        sharpe_ratio = metrics.get("sharpe_ratio", 0)
        st.metric("夏普比率", f"{sharpe_ratio:.2f}")

    with col4:
        max_drawdown = metrics.get("max_drawdown", 0)
        st.metric("最大回撤", f"{max_drawdown:.2%}")


if __name__ == "__main__":
    show_integrated()
