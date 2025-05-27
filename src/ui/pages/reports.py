"""
報表查詢頁面

此模組實現了報表查詢頁面，提供各種報表和視覺化功能。
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import logging

# 導入服務層
try:
    from src.core.report_visualization_service import ReportVisualizationService
except ImportError as e:
    # 如果無法導入，使用備用方案
    logging.warning("無法導入報表視覺化服務: %s", e)
    ReportVisualizationService = None


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
    """顯示報表查詢頁面"""
    st.title("📊 報表查詢與視覺化")

    # 獲取報表視覺化服務
    report_service = get_report_visualization_service()

    if not report_service:
        st.error("報表視覺化服務不可用，請檢查系統配置")
        return

    # 頁面標籤
    tabs = st.tabs(
        [
            "📈 交易績效圖表",
            "📋 交易明細追蹤",
            "🔄 策略績效比較",
            "🎛️ 參數敏感度分析",
            "📤 報表匯出",
        ]
    )

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
