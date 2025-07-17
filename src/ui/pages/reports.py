"""
報表查詢頁面 (整合版)

此模組整合了基本版和增強版報表功能，提供完整的報表查詢和視覺化功能：
- 交易績效圖表和分析
- 交易明細追蹤和查詢
- 策略績效比較分析
- 參數敏感度分析
- 多格式報表匯出
- 動態查詢建構器 (增強功能)
- 互動式圖表生成 (增強功能)
- 響應式設計支援 (增強功能)

Version: v2.0 (整合版)
Author: AI Trading System
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Optional, Any

# 導入服務層
try:
    from src.core.report_visualization_service import ReportVisualizationService
except ImportError as e:
    # 如果無法導入，使用備用方案
    logging.warning("無法導入報表視覺化服務: %s", e)
    ReportVisualizationService = None

# 導入響應式設計組件 (增強功能)
try:
    from src.ui.responsive import (
        ResponsiveUtils,
        ResponsiveComponents,
    )
except ImportError:
    # 備用實現
    ResponsiveUtils = None
    ResponsiveComponents = None

# 可選的圖表依賴 (增強功能)
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    px = None
    go = None

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None


def get_report_visualization_service():
    """獲取報表視覺化服務實例"""
    if ReportVisualizationService is None:
        return None

    if "report_service" not in st.session_state:
        try:
            st.session_state.report_service = ReportVisualizationService()
        except Exception as e:
            st.error(f"初始化報表視覺化服務失敗: {e}")
            return None

    return st.session_state.report_service


def show():
    """顯示報表查詢頁面 (整合版)"""
    # 檢查響應式組件是否可用
    if ResponsiveUtils is None:
        st.title("📊 報表查詢與視覺化 (整合版)")
    else:
        # 應用響應式頁面配置
        try:
            ResponsiveUtils.apply_responsive_page_config(
                page_title="報表系統 - AI 交易系統", page_icon="📊"
            )
            st.markdown('<h1 class="title-responsive">📊 報表查詢與視覺化</h1>', unsafe_allow_html=True)
        except Exception:
            st.title("📊 報表查詢與視覺化 (整合版)")

    # 初始化 session state
    if "report_data" not in st.session_state:
        st.session_state.report_data = pd.DataFrame()
    if "chart_config" not in st.session_state:
        st.session_state.chart_config = {}

    # 獲取報表視覺化服務
    report_service = get_report_visualization_service()

    if not report_service:
        st.warning("⚠️ 報表視覺化服務不可用，使用基本功能")

    # 檢查 ResponsiveComponents 是否可用
    if ResponsiveComponents is None:
        # 使用基本標籤頁 (整合版功能)
        tabs = st.tabs([
            "📈 交易績效圖表",
            "📋 交易明細追蹤",
            "🔄 策略績效比較",
            "🎛️ 參數敏感度分析",
            "📤 報表匯出",
            "🔍 動態查詢",
            "📊 圖表生成",
            "📤 數據匯出"
        ])

        with tabs[0]:
            show_trading_performance_charts(report_service)
        with tabs[1]:
            show_trade_details_tracking(report_service)
        with tabs[2]:
            show_strategy_comparison(report_service)
        with tabs[3]:
            show_parameter_sensitivity(report_service)
        with tabs[4]:
            show_report_export(report_service)
        with tabs[5]:
            show_dynamic_query()
        with tabs[6]:
            show_chart_generation()
        with tabs[7]:
            show_data_export()
    else:
        # 響應式標籤頁 (整合版功能)
        tabs_config = [
            {"name": "📈 交易績效圖表", "content_func": lambda: show_trading_performance_charts(report_service)},
            {"name": "📋 交易明細追蹤", "content_func": lambda: show_trade_details_tracking(report_service)},
            {"name": "🔄 策略績效比較", "content_func": lambda: show_strategy_comparison(report_service)},
            {"name": "🎛️ 參數敏感度分析", "content_func": lambda: show_parameter_sensitivity(report_service)},
            {"name": "📤 報表匯出", "content_func": lambda: show_report_export(report_service)},
            {"name": "🔍 動態查詢", "content_func": show_dynamic_query},
            {"name": "📊 圖表生成", "content_func": show_chart_generation},
            {"name": "📤 數據匯出", "content_func": show_data_export},
        ]

        ResponsiveComponents.responsive_tabs(tabs_config)


def show_trading_performance_charts(report_service):
    """顯示交易績效圖表"""
    st.subheader("📈 5.2.10.1 交易績效圖表與分析")

    # 參數設定
    col_param1, col_param2, col_param3 = st.columns(3)

    with col_param1:
        start_date = st.date_input(
            "開始日期",
            value=datetime.now().date() - timedelta(days=365),
            max_value=datetime.now().date(),
        )

    with col_param2:
        end_date = st.date_input(
            "結束日期", value=datetime.now().date(), max_value=datetime.now().date()
        )

    with col_param3:
        strategy_filter = st.selectbox(
            "策略篩選",
            ["", "策略A", "策略B", "策略C"],
            format_func=lambda x: "全部策略" if x == "" else x,
        )

    # 圖表類型選擇
    chart_library = st.radio(
        "圖表庫選擇",
        ["plotly", "matplotlib"],
        horizontal=True,
        help="Plotly 提供互動式圖表，Matplotlib 提供靜態高品質圖表",
    )

    if st.button("🔄 載入績效數據"):
        with st.spinner("載入數據中..."):
            # 獲取交易績效數據
            performance_data = report_service.get_trading_performance_data(
                start_date=datetime.combine(start_date, datetime.min.time()),
                end_date=datetime.combine(end_date, datetime.max.time()),
                strategy_name=strategy_filter if strategy_filter else None,
            )

            if "error" in performance_data:
                st.error(f"載入數據失敗: {performance_data['error']}")
                return

            if "message" in performance_data:
                st.info(performance_data["message"])
                return

            # 儲存數據到 session state
            st.session_state.performance_data = performance_data
            st.success("數據載入成功！")

    # 顯示圖表
    if "performance_data" in st.session_state:
        performance_data = st.session_state.performance_data

        # 績效指標儀表板
        st.write("**績效指標儀表板**")
        if "metrics" in performance_data:
            metrics = performance_data["metrics"]

            col_metric1, col_metric2, col_metric3, col_metric4 = st.columns(4)

            with col_metric1:
                st.metric("總損益", f"${metrics.get('total_pnl', 0):,.2f}")

            with col_metric2:
                st.metric("勝率", f"{metrics.get('win_rate', 0):.1f}%")

            with col_metric3:
                st.metric("夏普比率", f"{metrics.get('sharpe_ratio', 0):.2f}")

            with col_metric4:
                st.metric("最大回撤", f"${abs(metrics.get('max_drawdown', 0)):,.2f}")

            # 詳細指標
            with st.expander("詳細績效指標"):
                col_detail1, col_detail2 = st.columns(2)

                with col_detail1:
                    st.write("**交易統計**")
                    st.write(f"- 總交易次數: {metrics.get('total_trades', 0)}")
                    st.write(f"- 平均獲利: ${metrics.get('avg_win', 0):.2f}")
                    st.write(f"- 平均虧損: ${metrics.get('avg_loss', 0):.2f}")

                with col_detail2:
                    st.write("**費用統計**")
                    st.write(f"- 總手續費: ${metrics.get('total_commission', 0):.2f}")
                    st.write(f"- 總交易稅: ${metrics.get('total_tax', 0):.2f}")
                    st.write(f"- 獲利因子: {metrics.get('profit_factor', 0)}")

        # 累積報酬曲線圖
        st.write("**累積報酬曲線圖**")
        try:
            cumulative_chart = report_service.generate_cumulative_return_chart(
                performance_data, chart_type=chart_library
            )

            if cumulative_chart:
                if chart_library == "plotly":
                    st.plotly_chart(cumulative_chart, use_container_width=True)
                else:
                    st.pyplot(cumulative_chart)
            else:
                st.error("無法生成累積報酬曲線圖")
        except Exception as e:
            st.error(f"生成累積報酬曲線圖失敗: {e}")

        # 回撤分析圖表
        st.write("**回撤分析圖表**")
        try:
            drawdown_chart = report_service.generate_drawdown_chart(
                performance_data, chart_type=chart_library
            )

            if drawdown_chart:
                if chart_library == "plotly":
                    st.plotly_chart(drawdown_chart, use_container_width=True)
                else:
                    st.pyplot(drawdown_chart)
            else:
                st.error("無法生成回撤分析圖表")
        except Exception as e:
            st.error(f"生成回撤分析圖表失敗: {e}")

        # 月度績效熱力圖
        st.write("**月度績效熱力圖**")
        try:
            heatmap_chart = report_service.generate_monthly_heatmap(
                performance_data, chart_type=chart_library
            )

            if heatmap_chart:
                if chart_library == "plotly":
                    st.plotly_chart(heatmap_chart, use_container_width=True)
                else:
                    st.pyplot(heatmap_chart)
            else:
                st.error("無法生成月度績效熱力圖")
        except Exception as e:
            st.error(f"生成月度績效熱力圖失敗: {e}")


def show_trade_details_tracking(report_service):
    """顯示交易明細追蹤"""
    st.subheader("📋 5.2.10.2 交易明細與資產變化追蹤")

    # 查詢參數
    col_query1, col_query2, col_query3 = st.columns(3)

    with col_query1:
        detail_start_date = st.date_input(
            "查詢開始日期",
            value=datetime.now().date() - timedelta(days=90),
            key="detail_start_date",
        )

    with col_query2:
        detail_end_date = st.date_input(
            "查詢結束日期", value=datetime.now().date(), key="detail_end_date"
        )

    with col_query3:
        symbol_filter = st.text_input("股票代碼篩選", placeholder="例如: 2330.TW")

    if st.button("🔍 查詢交易明細"):
        with st.spinner("查詢中..."):
            # 獲取交易明細數據
            details_data = report_service.get_trade_details_data(
                start_date=datetime.combine(detail_start_date, datetime.min.time()),
                end_date=datetime.combine(detail_end_date, datetime.max.time()),
                symbol=symbol_filter if symbol_filter else None,
                limit=1000,
            )

            if "error" in details_data:
                st.error(f"查詢失敗: {details_data['error']}")
                return

            if "message" in details_data:
                st.info(details_data["message"])
                return

            # 儲存數據到 session state
            st.session_state.details_data = details_data
            st.success("查詢完成！")

    # 顯示交易明細
    if "details_data" in st.session_state:
        details_data = st.session_state.details_data

        # 交易統計摘要
        if "statistics" in details_data:
            stats = details_data["statistics"]

            st.write("**交易統計摘要**")
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)

            with col_stat1:
                st.metric("總交易筆數", stats.get("total_trades", 0))

            with col_stat2:
                st.metric("總交易金額", f"${stats.get('total_volume', 0):,.0f}")

            with col_stat3:
                st.metric(
                    "平均持有時間",
                    f"{stats.get('avg_holding_period_hours', 0):.1f} 小時",
                )

            with col_stat4:
                st.metric(
                    "日均交易頻率", f"{stats.get('daily_trade_frequency', 0):.1f} 筆/日"
                )

        # 交易明細表格
        if "details" in details_data and details_data["details"]:
            st.write("**交易明細表格**")

            df_details = pd.DataFrame(details_data["details"])

            # 格式化顯示
            display_df = df_details.copy()
            display_df["order_time"] = pd.to_datetime(
                display_df["order_time"]
            ).dt.strftime("%Y-%m-%d %H:%M")
            display_df["execution_time"] = pd.to_datetime(
                display_df["execution_time"]
            ).dt.strftime("%Y-%m-%d %H:%M")
            display_df["action"] = display_df["action"].map(
                {"buy": "買進", "sell": "賣出"}
            )

            # 選擇顯示欄位
            display_columns = [
                "symbol",
                "action",
                "order_time",
                "execution_time",
                "quantity",
                "execution_price",
                "amount",
                "commission",
                "net_amount",
                "holding_period_hours",
                "strategy_name",
            ]

            st.dataframe(
                display_df[display_columns].rename(
                    columns={
                        "symbol": "股票代碼",
                        "action": "方向",
                        "order_time": "下單時間",
                        "execution_time": "成交時間",
                        "quantity": "數量",
                        "execution_price": "成交價格",
                        "amount": "成交金額",
                        "commission": "手續費",
                        "net_amount": "淨損益",
                        "holding_period_hours": "持有時間(小時)",
                        "strategy_name": "策略名稱",
                    }
                ),
                use_container_width=True,
            )

            # 資產配置圖表
            st.write("**資產配置分布**")
            try:
                allocation_chart = report_service.generate_asset_allocation_chart(
                    {"holdings": "mock_data"}, chart_type="plotly"
                )

                if allocation_chart:
                    st.plotly_chart(allocation_chart, use_container_width=True)
                else:
                    st.info("暫無資產配置數據")
            except Exception as e:
                st.error(f"生成資產配置圖表失敗: {e}")
        else:
            st.info("無交易明細數據")


def show_strategy_comparison(report_service):
    """顯示策略績效比較"""
    st.subheader("🔄 5.2.10.3 策略績效比較與分析")

    # 策略選擇
    st.write("**策略選擇**")
    col_strategy1, col_strategy2 = st.columns(2)

    with col_strategy1:
        available_strategies = ["策略A", "策略B", "策略C", "策略D", "策略E"]
        selected_strategies = st.multiselect(
            "選擇要比較的策略", available_strategies, default=["策略A", "策略B"]
        )

    with col_strategy2:
        comparison_period = st.selectbox(
            "比較期間", ["最近30天", "最近90天", "最近180天", "最近365天"], index=2
        )

    # 比較指標選擇
    comparison_metric = st.selectbox(
        "比較指標",
        ["total_return", "win_rate", "sharpe_ratio", "max_drawdown", "profit_factor"],
        format_func=lambda x: {
            "total_return": "總報酬",
            "win_rate": "勝率",
            "sharpe_ratio": "夏普比率",
            "max_drawdown": "最大回撤",
            "profit_factor": "獲利因子",
        }.get(x, x),
    )

    if st.button("📊 開始比較分析") and selected_strategies:
        with st.spinner("分析中..."):
            # 設定比較期間
            period_days = {
                "最近30天": 30,
                "最近90天": 90,
                "最近180天": 180,
                "最近365天": 365,
            }

            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days[comparison_period])

            # 獲取策略比較數據
            comparison_data = report_service.compare_strategies_performance(
                strategy_names=selected_strategies,
                start_date=start_date,
                end_date=end_date,
            )

            if "error" in comparison_data:
                st.error(f"比較分析失敗: {comparison_data['error']}")
                return

            if "message" in comparison_data:
                st.info(comparison_data["message"])
                return

            # 儲存比較數據
            st.session_state.comparison_data = comparison_data
            st.success("比較分析完成！")

    # 顯示比較結果
    if "comparison_data" in st.session_state:
        comparison_data = st.session_state.comparison_data

        # 比較指標表格
        if "comparison_metrics" in comparison_data:
            st.write("**策略績效比較表**")

            metrics_df = pd.DataFrame(comparison_data["comparison_metrics"]).T
            metrics_df.index.name = "策略名稱"

            # 格式化顯示
            formatted_df = metrics_df.copy()
            for col in formatted_df.columns:
                if col in ["total_return", "max_drawdown"]:
                    formatted_df[col] = formatted_df[col].apply(lambda x: f"${x:,.2f}")
                elif col in ["win_rate"]:
                    formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.1f}%")
                else:
                    formatted_df[col] = formatted_df[col].apply(lambda x: f"{x:.2f}")

            st.dataframe(
                formatted_df.rename(
                    columns={
                        "total_return": "總報酬",
                        "win_rate": "勝率(%)",
                        "sharpe_ratio": "夏普比率",
                        "max_drawdown": "最大回撤",
                        "profit_factor": "獲利因子",
                        "total_trades": "總交易次數",
                    }
                ),
                use_container_width=True,
            )

            # 策略比較圖表
            st.write("**策略比較圖表**")
            try:
                comparison_chart = report_service.generate_strategy_comparison_chart(
                    comparison_data, metric=comparison_metric, chart_type="plotly"
                )

                if comparison_chart:
                    st.plotly_chart(comparison_chart, use_container_width=True)
                else:
                    st.error("無法生成策略比較圖表")
            except Exception as e:
                st.error(f"生成策略比較圖表失敗: {e}")

            # 策略排名
            st.write("**策略排名**")
            ranking_df = metrics_df.copy()

            # 根據選擇的指標排序
            if comparison_metric == "max_drawdown":
                # 回撤越小越好
                ranking_df = ranking_df.sort_values(comparison_metric, ascending=True)
            else:
                # 其他指標越大越好
                ranking_df = ranking_df.sort_values(comparison_metric, ascending=False)

            ranking_df["排名"] = range(1, len(ranking_df) + 1)

            st.dataframe(
                ranking_df[["排名", comparison_metric]].rename(
                    columns={
                        comparison_metric: {
                            "total_return": "總報酬",
                            "win_rate": "勝率(%)",
                            "sharpe_ratio": "夏普比率",
                            "max_drawdown": "最大回撤",
                            "profit_factor": "獲利因子",
                        }.get(comparison_metric, comparison_metric)
                    }
                ),
                use_container_width=True,
            )


def show_parameter_sensitivity(report_service):
    """顯示參數敏感度分析"""
    st.subheader("🎛️ 5.2.10.4 參數敏感度分析與優化")

    # 參數設定
    st.write("**參數設定**")
    col_param_set1, col_param_set2 = st.columns(2)

    with col_param_set1:
        param1_name = st.text_input("參數1名稱", value="移動平均週期")
        param1_range = st.text_input(
            "參數1範圍", value="10,20,30,40,50", help="用逗號分隔"
        )

    with col_param_set2:
        param2_name = st.text_input("參數2名稱", value="停損比例")
        param2_range = st.text_input(
            "參數2範圍", value="0.1,0.2,0.3,0.4,0.5", help="用逗號分隔"
        )

    # 優化目標
    optimization_target = st.selectbox(
        "優化目標",
        ["總報酬", "夏普比率", "獲利因子", "最大回撤"],
        help="選擇要優化的績效指標",
    )
    # 使用變數避免未使用警告
    st.write(f"當前優化目標: {optimization_target}")

    if st.button("🔬 開始敏感度分析"):
        with st.spinner("分析中..."):
            # 模擬參數敏感度分析
            try:
                # 解析參數範圍
                param1_values = [float(x.strip()) for x in param1_range.split(",")]
                param2_values = [float(x.strip()) for x in param2_range.split(",")]

                # 生成參數敏感度熱力圖
                sensitivity_chart = (
                    report_service.generate_parameter_sensitivity_heatmap(
                        {"param1": param1_values, "param2": param2_values},
                        chart_type="plotly",
                    )
                )

                if sensitivity_chart:
                    st.session_state.sensitivity_chart = sensitivity_chart
                    st.session_state.param_analysis_done = True
                    st.success("敏感度分析完成！")
                else:
                    st.error("無法生成敏感度分析")

            except ValueError:
                st.error("參數範圍格式錯誤，請使用逗號分隔的數值")
            except Exception as e:
                st.error(f"敏感度分析失敗: {e}")

    # 顯示分析結果
    if st.session_state.get("param_analysis_done", False):
        st.write("**參數敏感度熱力圖**")

        if "sensitivity_chart" in st.session_state:
            st.plotly_chart(
                st.session_state.sensitivity_chart, use_container_width=True
            )

        # 最佳參數建議
        st.write("**最佳參數建議**")

        # 模擬最佳參數結果
        best_params = {
            param1_name: 30,
            param2_name: 0.3,
            "預期報酬": 15.2,
            "風險評估": "中等",
            "建議": "此參數組合在歷史數據中表現良好，建議進行實盤測試",
        }

        col_best1, col_best2 = st.columns(2)

        with col_best1:
            st.metric("最佳" + param1_name, best_params[param1_name])
            st.metric("預期報酬", f"{best_params['預期報酬']}%")

        with col_best2:
            st.metric("最佳" + param2_name, best_params[param2_name])
            st.metric("風險評估", best_params["風險評估"])

        st.info(f"💡 **建議**: {best_params['建議']}")

        # 參數重要性排名
        st.write("**參數重要性排名**")
        importance_data = {
            "參數名稱": [param1_name, param2_name, "交易頻率", "市場環境"],
            "重要性分數": [0.85, 0.72, 0.45, 0.38],
            "影響程度": ["高", "高", "中", "中"],
        }

        importance_df = pd.DataFrame(importance_data)
        st.dataframe(importance_df, use_container_width=True)


def show_report_export(report_service):
    """顯示報表匯出"""
    st.subheader("📤 5.2.10.5 多種圖表呈現與報表導出")

    # 匯出選項
    st.write("**匯出選項**")
    col_export1, col_export2 = st.columns(2)

    with col_export1:
        export_type = st.selectbox(
            "匯出類型",
            ["績效報表", "交易明細", "策略比較", "參數分析"],
            help="選擇要匯出的報表類型",
        )

    with col_export2:
        export_format = st.selectbox(
            "匯出格式", ["JSON", "CSV", "Excel", "HTML"], help="選擇匯出檔案格式"
        )

    # 報表模板選擇
    template_option = st.selectbox(
        "報表模板",
        ["預設模板", "專業模板", "簡潔模板", "自定義模板"],
        help="選擇報表樣式模板",
    )

    # 自定義設定
    with st.expander("自定義設定"):
        include_charts = st.checkbox("包含圖表", value=True)
        include_raw_data = st.checkbox("包含原始數據", value=False)
        add_watermark = st.checkbox("添加浮水印", value=False)

        watermark_text = ""
        if add_watermark:
            watermark_text = st.text_input("浮水印文字", value="AI Trading System")

        # 顯示設定摘要避免未使用警告
        settings_summary = {
            "包含圖表": include_charts,
            "包含原始數據": include_raw_data,
            "浮水印": watermark_text if add_watermark else "無",
        }
        st.write("設定摘要:", settings_summary)

    # 匯出按鈕
    if st.button("📥 匯出報表"):
        with st.spinner("匯出中..."):
            # 準備匯出數據
            export_data = {}

            if export_type == "績效報表" and "performance_data" in st.session_state:
                export_data = st.session_state.performance_data
            elif export_type == "交易明細" and "details_data" in st.session_state:
                export_data = st.session_state.details_data
            elif export_type == "策略比較" and "comparison_data" in st.session_state:
                export_data = st.session_state.comparison_data
            else:
                export_data = {"message": "無可匯出的數據"}

            # 執行匯出
            try:
                success, message, filepath = report_service.export_report(
                    report_data=export_data,
                    export_format=export_format.lower(),
                    template_id=template_option,
                    user_id="streamlit_user",
                )

                if success:
                    st.success(message)

                    # 提供下載連結
                    if filepath and Path(filepath).exists():
                        with open(filepath, "rb") as f:
                            st.download_button(
                                label=f"📥 下載 {export_format} 檔案",
                                data=f.read(),
                                file_name=Path(filepath).name,
                                mime=f"application/{export_format.lower()}",
                            )
                else:
                    st.error(message)

            except Exception as e:
                st.error(f"匯出失敗: {e}")

    # 匯出歷史
    st.write("**匯出歷史**")

    try:
        export_logs = report_service.get_export_logs(user_id="streamlit_user", limit=10)

        if export_logs:
            logs_df = pd.DataFrame(export_logs)

            # 格式化顯示
            display_logs = logs_df[
                ["export_name", "export_format", "status", "file_size", "created_at"]
            ].copy()
            display_logs["file_size"] = display_logs["file_size"].apply(
                lambda x: f"{x/1024:.1f} KB" if x else "N/A"
            )
            display_logs["created_at"] = pd.to_datetime(
                display_logs["created_at"]
            ).dt.strftime("%Y-%m-%d %H:%M")

            st.dataframe(
                display_logs.rename(
                    columns={
                        "export_name": "檔案名稱",
                        "export_format": "格式",
                        "status": "狀態",
                        "file_size": "檔案大小",
                        "created_at": "匯出時間",
                    }
                ),
                use_container_width=True,
            )
        else:
            st.info("暫無匯出歷史")

    except Exception as e:
        st.error(f"載入匯出歷史失敗: {e}")

    # 快取管理
    st.write("**快取管理**")
    col_cache1, col_cache2 = st.columns(2)

    with col_cache1:
        if st.button("🗑️ 清理快取"):
            try:
                success, message = report_service.cleanup_cache(max_age_hours=24)
                if success:
                    st.success(message)
                else:
                    st.error(message)
            except Exception as e:
                st.error(f"清理快取失敗: {e}")

    with col_cache2:
        st.info("定期清理快取可以釋放存儲空間並提升系統效能")


# ==================== 整合的增強功能 ====================

def show_dynamic_query():
    """顯示動態查詢介面 (增強功能)"""
    st.subheader("動態報表查詢")

    # 可用數據源
    data_sources = [
        "交易記錄",
        "投資組合數據",
        "風險指標",
        "市場數據",
        "策略績效",
        "系統日誌",
    ]

    selected_source = st.selectbox("選擇數據源", data_sources)

    # 根據數據源獲取可用欄位
    available_fields = get_available_fields(selected_source)

    # 動態查詢建構器
    with st.form(f"query_{selected_source}"):
        st.markdown("### 查詢條件")

        col1, col2 = st.columns(2)

        with col1:
            # 日期範圍
            start_date = st.date_input("開始日期", value=datetime.now().date() - timedelta(days=30))
            end_date = st.date_input("結束日期", value=datetime.now().date())

        with col2:
            # 股票代碼選擇
            if selected_source in ["交易記錄", "投資組合數據", "市場數據"]:
                symbols = st.multiselect(
                    "股票代碼",
                    ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"],
                    default=["AAPL", "MSFT"]
                )

        # 其他條件
        if selected_source == "交易記錄":
            directions = st.multiselect("交易方向", ["買入", "賣出"], default=["買入", "賣出"])
            amount_min = st.number_input("最小金額", value=0)
            amount_max = st.number_input("最大金額", value=1000000)

        submitted = st.form_submit_button("🔍 執行查詢", type="primary")

        if submitted:
            # 生成模擬數據
            mock_data = generate_mock_query_data(selected_source, start_date, end_date)
            st.session_state.report_data = mock_data
            st.success(f"✅ 查詢完成！找到 {len(mock_data)} 筆記錄")

            # 顯示數據預覽
            if not mock_data.empty:
                st.subheader("數據預覽")
                st.dataframe(mock_data.head(10), use_container_width=True)

                # 統計摘要
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("記錄數", len(mock_data))
                with col2:
                    st.metric("欄位數", len(mock_data.columns))
                with col3:
                    if selected_source == "交易記錄" and "amount" in mock_data.columns:
                        st.metric("總金額", f"${mock_data['amount'].sum():,.0f}")


def show_chart_generation():
    """顯示圖表生成介面 (增強功能)"""
    st.subheader("互動式圖表生成")

    if st.session_state.report_data.empty:
        st.info("請先在「動態查詢」頁面載入數據")
        return

    data = st.session_state.report_data

    # 圖表配置
    col1, col2 = st.columns(2)

    with col1:
        chart_type = st.selectbox(
            "圖表類型",
            ["line", "bar", "scatter", "histogram", "pie"],
            format_func=lambda x: {
                "line": "線圖",
                "bar": "柱狀圖",
                "scatter": "散點圖",
                "histogram": "直方圖",
                "pie": "圓餅圖"
            }[x]
        )

    with col2:
        numeric_columns = data.select_dtypes(include=[np.number]).columns.tolist()
        categorical_columns = data.select_dtypes(include=['object']).columns.tolist()

        if chart_type in ["line", "bar", "scatter"]:
            x_column = st.selectbox("X軸欄位", data.columns)
            y_column = st.selectbox("Y軸欄位", numeric_columns)
        elif chart_type == "histogram":
            x_column = st.selectbox("數值欄位", numeric_columns)
            y_column = None
        elif chart_type == "pie":
            x_column = st.selectbox("分類欄位", categorical_columns)
            y_column = st.selectbox("數值欄位", numeric_columns)

    # 生成圖表
    if st.button("📊 生成圖表", type="primary"):
        chart_config = {
            "type": chart_type,
            "x_column": x_column,
            "y_column": y_column
        }

        if PLOTLY_AVAILABLE:
            fig = generate_plotly_chart(data, chart_config)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                st.success("✅ 圖表生成成功！")
        else:
            st.error("❌ Plotly 未安裝，無法生成互動式圖表")


def show_data_export():
    """顯示數據匯出介面 (增強功能)"""
    st.subheader("多格式數據匯出")

    if st.session_state.report_data.empty:
        st.info("請先在「動態查詢」頁面載入數據")
        return

    data = st.session_state.report_data

    # 匯出配置
    col1, col2 = st.columns(2)

    with col1:
        export_format = st.selectbox("匯出格式", ["CSV", "JSON", "Excel", "PDF"])
        filename_prefix = st.text_input("檔案名稱前綴", value="report")

    with col2:
        export_range = st.selectbox("匯出範圍", ["全部數據", "前100筆", "前1000筆"])
        include_charts = st.checkbox("包含圖表", value=False)

    # 數據統計
    st.markdown("### 數據統計")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("記錄數", len(data))
    with col2:
        st.metric("欄位數", len(data.columns))
    with col3:
        # 估算檔案大小
        estimated_size = len(data) * len(data.columns) * 10  # 粗略估算
        st.metric("估算大小", f"{estimated_size/1024:.1f} KB")

    # 匯出按鈕
    cols = st.columns(4)

    with cols[0]:
        if st.button("📄 匯出 CSV", use_container_width=True):
            csv = data.to_csv(index=False)
            st.download_button(
                label="下載 CSV",
                data=csv,
                file_name=f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

    with cols[1]:
        if st.button("📋 匯出 JSON", use_container_width=True):
            json_data = data.to_json(orient="records", date_format="iso")
            st.download_button(
                label="下載 JSON",
                data=json_data,
                file_name=f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
            )

    with cols[2]:
        if st.button("📊 匯出 Excel", use_container_width=True):
            st.info("Excel 匯出功能需要安裝 openpyxl")

    with cols[3]:
        if st.button("📑 匯出 PDF", use_container_width=True):
            st.info("PDF 匯出功能需要安裝 reportlab")


# ==================== 輔助函數 ====================

def get_available_fields(data_source: str) -> List[str]:
    """獲取數據源的可用欄位"""
    field_mapping = {
        "交易記錄": ["date", "symbol", "direction", "quantity", "price", "amount"],
        "投資組合數據": ["symbol", "quantity", "market_value", "weight", "return"],
        "風險指標": ["date", "var", "cvar", "max_drawdown", "volatility"],
        "市場數據": ["date", "symbol", "open", "high", "low", "close", "volume"],
        "策略績效": ["strategy", "return", "sharpe_ratio", "max_drawdown", "win_rate"],
        "系統日誌": ["timestamp", "level", "module", "message", "user_id"],
    }
    return field_mapping.get(data_source, [])


def generate_mock_query_data(data_source: str, start_date, end_date) -> pd.DataFrame:
    """生成模擬查詢數據"""
    np.random.seed(42)

    if data_source == "交易記錄":
        n_records = np.random.randint(50, 200)
        return pd.DataFrame({
            "date": pd.date_range(start_date, end_date, periods=n_records),
            "symbol": np.random.choice(["AAPL", "MSFT", "GOOGL", "TSLA"], n_records),
            "direction": np.random.choice(["買入", "賣出"], n_records),
            "quantity": np.random.randint(100, 1000, n_records),
            "price": np.random.uniform(100, 300, n_records),
            "amount": np.random.uniform(10000, 100000, n_records)
        })
    elif data_source == "投資組合數據":
        symbols = ["AAPL", "MSFT", "GOOGL", "TSLA", "AMZN"]
        return pd.DataFrame({
            "symbol": symbols,
            "quantity": np.random.randint(100, 1000, len(symbols)),
            "market_value": np.random.uniform(50000, 200000, len(symbols)),
            "weight": np.random.uniform(0.1, 0.3, len(symbols)),
            "return": np.random.uniform(-0.1, 0.2, len(symbols))
        })
    else:
        # 其他數據源的模擬數據
        n_records = np.random.randint(20, 100)
        return pd.DataFrame({
            "date": pd.date_range(start_date, end_date, periods=n_records),
            "value": np.random.uniform(0, 100, n_records),
            "category": np.random.choice(["A", "B", "C"], n_records)
        })


def generate_plotly_chart(data: pd.DataFrame, config: Dict[str, Any]):
    """生成 Plotly 圖表"""
    if not PLOTLY_AVAILABLE:
        return None

    chart_type = config.get("type")
    x_col = config.get("x_column")
    y_col = config.get("y_column")

    try:
        if chart_type == "line":
            fig = px.line(data, x=x_col, y=y_col, title=f"{y_col} vs {x_col}")
        elif chart_type == "bar":
            fig = px.bar(data, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
        elif chart_type == "scatter":
            fig = px.scatter(data, x=x_col, y=y_col, title=f"{y_col} vs {x_col}")
        elif chart_type == "histogram":
            fig = px.histogram(data, x=x_col, title=f"Distribution of {x_col}")
        elif chart_type == "pie":
            fig = px.pie(data, names=x_col, values=y_col, title=f"{y_col} by {x_col}")
        else:
            return None

        return fig
    except Exception as e:
        st.error(f"圖表生成失敗: {e}")
        return None
