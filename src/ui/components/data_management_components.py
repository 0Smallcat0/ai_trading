"""
資料管理專用 UI 組件

此模組提供資料管理頁面專用的 UI 組件，包括：
- 資料來源狀態顯示
- 更新進度條
- 資料品質指標
- 狀態指示器
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


def show_data_source_status_card(source_name: str, source_info: Dict[str, Any]):
    """顯示資料來源狀態卡片"""
    status = source_info.get("status", "unknown")

    # 狀態顏色映射
    status_colors = {
        "正常": "#28a745",
        "警告": "#ffc107",
        "離線": "#dc3545",
        "錯誤": "#dc3545",
        "unknown": "#6c757d",
    }

    # 狀態圖示映射
    status_icons = {
        "正常": "✅",
        "警告": "⚠️",
        "離線": "❌",
        "錯誤": "❌",
        "unknown": "❓",
    }

    color = status_colors.get(status, "#6c757d")
    icon = status_icons.get(status, "❓")

    with st.container():
        st.markdown(
            f"""
        <div style="
            border: 1px solid {color};
            border-radius: 8px;
            padding: 16px;
            margin: 8px 0;
            background-color: {color}15;
        ">
            <h4 style="margin: 0; color: {color};">
                {icon} {source_name}
            </h4>
            <p style="margin: 8px 0 0 0; color: #666;">
                <strong>狀態:</strong> {status}<br>
                <strong>類型:</strong> {source_info.get('type', 'N/A')}<br>
                <strong>最後更新:</strong> {source_info.get('last_update', 'N/A')}<br>
                <strong>資料品質:</strong> {source_info.get('data_quality', 'N/A')}
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )


def show_update_progress(task_status: Dict[str, Any]):
    """顯示更新進度"""
    if not task_status:
        st.warning("無法獲取更新狀態")
        return

    status = task_status.get("status", "unknown")
    progress = task_status.get("progress", 0)
    message = task_status.get("message", "")

    # 顯示狀態
    if status == "running":
        st.info(f"🔄 更新進行中: {message}")
        st.progress(progress / 100)
    elif status == "completed":
        st.success("✅ 更新完成")
        st.progress(1.0)

        # 顯示結果摘要
        results = task_status.get("results", {})
        if results:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("處理記錄數", results.get("processed_records", 0))
            with col2:
                st.metric("新增記錄數", results.get("new_records", 0))
            with col3:
                st.metric("更新記錄數", results.get("updated_records", 0))
            with col4:
                st.metric("錯誤記錄數", results.get("error_records", 0))
    elif status == "error":
        st.error(f"❌ 更新失敗: {message}")
    else:
        st.warning(f"⚠️ 未知狀態: {status}")


def show_data_quality_metrics(quality_data):
    """顯示資料品質指標

    Args:
        quality_data: 品質數據，可以是字典或列表格式
    """
    if not quality_data:
        st.warning("無資料品質資訊")
        return

    # 處理不同的數據格式
    if isinstance(quality_data, list):
        # 如果是列表格式，轉換為適合顯示的格式
        if not quality_data:
            st.warning("無資料品質資訊")
            return

        # 準備資料（列表格式）
        metrics_df = pd.DataFrame(quality_data)

        # 重命名列以符合顯示需求
        column_mapping = {
            'data_type': '資料類型',
            'completeness': '完整性',
            'accuracy': '準確性',
            'timeliness': '時效性',
            'consistency': '一致性'
        }

        # 重命名存在的列
        for old_col, new_col in column_mapping.items():
            if old_col in metrics_df.columns:
                metrics_df = metrics_df.rename(columns={old_col: new_col})

    elif isinstance(quality_data, dict):
        # 如果是字典格式，使用原有邏輯
        metrics_df = pd.DataFrame(
            {
                "資料類型": list(quality_data.keys()),
                "完整性": [
                    float(str(v.get("completeness", "0")).rstrip("%"))
                    for v in quality_data.values()
                ],
                "準確性": [
                    float(str(v.get("accuracy", "0")).rstrip("%"))
                    for v in quality_data.values()
                ],
                "時效性": [
                    float(str(v.get("timeliness", "0")).rstrip("%"))
                    for v in quality_data.values()
                ],
            }
        )
    else:
        st.error("不支援的資料格式")
        return

    # 顯示指標卡片
    st.subheader("資料品質概覽")

    col1, col2, col3 = st.columns(3)
    with col1:
        avg_completeness = metrics_df["完整性"].mean()
        st.metric("平均完整性", f"{avg_completeness:.1f}%")
    with col2:
        avg_accuracy = metrics_df["準確性"].mean()
        st.metric("平均準確性", f"{avg_accuracy:.1f}%")
    with col3:
        avg_timeliness = metrics_df["時效性"].mean()
        st.metric("平均時效性", f"{avg_timeliness:.1f}%")

    # 顯示詳細表格
    st.subheader("詳細品質指標")
    st.dataframe(metrics_df, use_container_width=True)

    # 顯示品質圖表
    st.subheader("品質指標圖表")

    # 雷達圖
    fig = go.Figure()

    for data_type in metrics_df["資料類型"]:
        row = metrics_df[metrics_df["資料類型"] == data_type].iloc[0]
        fig.add_trace(
            go.Scatterpolar(
                r=[row["完整性"], row["準確性"], row["時效性"], row["完整性"]],
                theta=["完整性", "準確性", "時效性", "完整性"],
                fill="toself",
                name=data_type,
            )
        )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        title="資料品質雷達圖",
    )

    st.plotly_chart(fig, use_container_width=True)


def show_connection_test_result(source_name: str, is_connected: bool, message: str):
    """顯示連接測試結果"""
    if is_connected:
        st.success(f"✅ {source_name} 連接成功！{message}")
    else:
        st.error(f"❌ {source_name} 連接失敗：{message}")


def show_data_statistics(stats: Dict[str, Any]):
    """顯示資料統計資訊"""
    if not stats:
        st.info("暫無統計資料")
        return

    st.subheader("資料統計")

    # 顯示統計卡片
    cols = st.columns(len(stats))
    for i, (key, value) in enumerate(stats.items()):
        with cols[i]:
            st.metric(key, value)


def show_update_form(
    data_types: List[str], symbols: List[Dict[str, str]], data_sources: List[str]
) -> Optional[Dict[str, Any]]:
    """顯示資料更新表單"""
    with st.form("data_update_form"):
        st.subheader("資料更新設定")

        col1, col2 = st.columns(2)

        with col1:
            # 更新類型
            update_type = st.radio(
                "更新類型",
                ["全量更新", "增量更新", "指定標的更新", "指定區間更新"],
                help="選擇資料更新的方式",
            )

            # 資料類型
            selected_data_types = st.multiselect(
                "資料類型",
                data_types,
                default=[data_types[0]] if data_types else [],
                help="選擇要更新的資料類型",
            )

            # 資料來源
            selected_sources = st.multiselect(
                "資料來源",
                data_sources,
                default=[data_sources[0]] if data_sources else [],
                help="選擇要使用的資料來源",
            )

        with col2:
            # 根據更新類型顯示不同選項
            selected_symbols = []
            start_date = None
            end_date = None

            if update_type == "指定標的更新":
                symbol_options = [f"{s['symbol']} - {s['name']}" for s in symbols]
                selected_stocks = st.multiselect(
                    "選擇股票",
                    symbol_options,
                    default=[symbol_options[0]] if symbol_options else [],
                    help="選擇要更新的股票",
                )
                selected_symbols = [s.split(" - ")[0] for s in selected_stocks]

                # 手動輸入其他股票代碼
                custom_symbols = st.text_input(
                    "其他股票代碼 (多個代碼請用逗號分隔)",
                    "",
                    help="輸入其他未列出的股票代碼",
                )
                if custom_symbols:
                    additional_symbols = [s.strip() for s in custom_symbols.split(",")]
                    selected_symbols.extend(additional_symbols)

            if update_type in ["指定區間更新", "增量更新"]:
                start_date = st.date_input(
                    "開始日期",
                    datetime.now() - timedelta(days=30),
                    help="選擇資料更新的開始日期",
                )
                end_date = st.date_input(
                    "結束日期", datetime.now(), help="選擇資料更新的結束日期"
                )

        # 高級選項
        with st.expander("高級選項"):
            use_cache = st.checkbox(
                "使用快取", value=True, help="使用快取可以加速資料更新"
            )
            retry_count = st.number_input(
                "重試次數",
                min_value=0,
                max_value=10,
                value=3,
                help="API 請求失敗時的重試次數",
            )
            parallel_jobs = st.slider(
                "並行任務數",
                min_value=1,
                max_value=10,
                value=4,
                help="同時執行的更新任務數量",
            )

        # 提交按鈕
        submitted = st.form_submit_button("開始更新", type="primary")

        if submitted:
            # 驗證表單
            if not selected_data_types:
                st.error("請選擇至少一種資料類型")
                return None

            if not selected_sources:
                st.error("請選擇至少一個資料來源")
                return None

            if update_type == "指定標的更新" and not selected_symbols:
                st.error("請選擇至少一個股票代碼")
                return None

            if update_type in ["指定區間更新", "增量更新"]:
                if not start_date or not end_date:
                    st.error("請選擇開始和結束日期")
                    return None
                if start_date > end_date:
                    st.error("開始日期不能晚於結束日期")
                    return None

            # 返回配置
            return {
                "update_type": update_type,
                "data_types": selected_data_types,
                "sources": selected_sources,
                "symbols": selected_symbols,
                "start_date": start_date,
                "end_date": end_date,
                "use_cache": use_cache,
                "retry_count": retry_count,
                "parallel_jobs": parallel_jobs,
            }

    return None


def show_error_list(errors: List[Dict[str, Any]]):
    """顯示錯誤列表"""
    if not errors:
        st.success("✅ 無錯誤記錄")
        return

    st.subheader(f"錯誤記錄 ({len(errors)} 筆)")

    # 轉換為 DataFrame
    error_df = pd.DataFrame(errors)

    # 顯示錯誤統計
    if "severity" in error_df.columns:
        severity_counts = error_df["severity"].value_counts()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("嚴重錯誤", severity_counts.get("critical", 0))
        with col2:
            st.metric("一般錯誤", severity_counts.get("error", 0))
        with col3:
            st.metric("警告", severity_counts.get("warning", 0))

    # 顯示錯誤表格
    st.dataframe(error_df, use_container_width=True)
